"""Pruebas de la opción ERP (herramientas/harness-erp.py): lectura de documentos, señales, propuesta, trazabilidad y escritura.
Catálogo y negocios INVENTADOS (erp_fixtures.py); todo en carpetas temporales; sin red. Con HARNESS_ERP_BASE_PRUEBA=<ruta del ERP estándar>
se añade la comprobación contra el catálogo real (si no está, esa prueba se omite)."""
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
sys.path.insert(0, str(AQUI))
sys.dont_write_bytecode = True
import erp_fixtures as F  # noqa: E402

spec = importlib.util.spec_from_file_location("harness_erp", RAIZ / "herramientas" / "harness-erp.py")
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)
TRAZA = RAIZ / "herramientas" / "harness-trazabilidad.py"


def hash_arbol(carpeta):
    h = hashlib.sha256()
    for p in sorted(pathlib.Path(carpeta).rglob("*")):
        h.update(str(p.relative_to(carpeta)).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="mh-erp-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.erp = F.escribir_catalogo(self.tmp / "erp-base")

    def negocio(self, rubro, nombre=None):
        return F.escribir_negocio(self.tmp / (nombre or f"negocio-{rubro}"), rubro)

    def proponer(self, carpeta):
        return E.generar(carpeta, self.erp)

    @staticmethod
    def ids(p):
        return [m["id"] for m in p["modulos"]]


class Rubros(Base):
    """Negocios inventados de varios rubros: la propuesta incluye lo esperado, respeta requisitos y marca lo no construido."""

    def test_comercio(self):
        p = self.proponer(self.negocio("comercio"))
        self.assertEqual(p["rubro"]["id"], "comercio")
        self.assertEqual(p["producto_partida"]["id"], "comercio")
        self.assertEqual(p["perfil_configuracion"]["id"], "comercio")
        for m in ("almacen", "compras", "ventas", "comprobantes"):
            self.assertIn(m, self.ids(p))
        self.assertIn("contabilidad", self.ids(p))                     # no aparece en el texto: lo trae el cierre de requisitos
        cont = next(m for m in p["modulos"] if m["id"] == "contabilidad")
        self.assertEqual(cont["origen"], "requisito")
        self.assertEqual(sorted(cont["requerido_por"]), ["compras", "ventas"])

    def test_distribucion(self):
        p = self.proponer(self.negocio("distribucion"))
        self.assertEqual(p["rubro"]["id"], "distribucion")
        self.assertTrue({"transporte", "almacen"} <= set(self.ids(p)))
        self.assertIn("comprobantes", self.ids(p))                      # transporte lo requiere

    def test_servicios(self):
        p = self.proponer(self.negocio("servicios"))
        self.assertEqual(p["rubro"]["id"], "servicios")
        self.assertTrue({"proyectos", "gastos-viaje", "tiempos"} <= set(self.ids(p)))
        # proyectos requiere costos y compras; compras requiere almacén y contabilidad: todo el cierre entra
        self.assertTrue({"costos", "compras", "almacen", "contabilidad", "personal", "socios-negocio"} <= set(self.ids(p)))

    def test_industrial(self):
        p = self.proponer(self.negocio("industrial"))
        self.assertEqual(p["rubro"]["id"], "industrial")
        self.assertTrue({"produccion", "calidad", "almacen", "costos"} <= set(self.ids(p)))

    def test_inmobiliario(self):
        p = self.proponer(self.negocio("inmobiliario"))
        self.assertEqual(p["rubro"]["id"], "inmobiliario")
        self.assertTrue({"inmuebles", "cuentas-por-cobrar", "contabilidad"} <= set(self.ids(p)))

    def test_el_nucleo_va_siempre(self):
        for rubro in F.NEGOCIOS:
            p = self.proponer(self.negocio(rubro))
            self.assertEqual(self.ids(p)[:4], ["identidad", "autenticacion", "configuracion", "interfaz"], rubro)
            self.assertTrue(all(m["origen"] == "nucleo" for m in p["modulos"][:4]))

    def test_cierre_de_requisitos_para_todos_los_rubros(self):
        """Propiedad: todo requisito de todo módulo propuesto también está propuesto, y el catálogo no se acorta."""
        cat = E.cargar_catalogo(self.erp)
        for rubro in F.NEGOCIOS:
            p = self.proponer(self.negocio(rubro))
            ids = set(self.ids(p))
            for m in p["modulos"]:
                for q in cat["modulos"][m["id"]]["requiere"]:
                    self.assertIn(q, ids, f"{rubro}: {m['id']} requiere {q}")
            self.assertEqual(p["entrega_al_compositor"]["modulos"], self.ids(p))

    def test_estado_real_y_lo_que_no_existe(self):
        p = self.proponer(self.negocio("comercio"))
        estados = {m["id"]: m["estado"] for m in p["modulos"]}
        self.assertEqual(estados["compras"], "en_construccion")
        self.assertEqual(estados["ventas"], "planeado")
        self.assertEqual(estados["almacen"], "parcial")
        self.assertEqual(estados["identidad"], "hecho")
        no_existe = {m["id"] for m in p["no_existe_aun"]}
        self.assertTrue({"compras", "ventas"} <= no_existe)
        self.assertFalse(no_existe & {"almacen", "identidad", "contabilidad"})        # parciales y hechos no son «no existe»
        self.assertIn("almacen", {m["id"] for m in p["existe_en_parte"]})
        ent = p["entrega_al_compositor"]
        self.assertTrue({"compras", "ventas"} <= set(ent["sin_codigo_aun"]))
        self.assertFalse({"compras", "ventas"} & set(ent["componibles_hoy"]))
        self.assertIn("almacen", ent["componibles_hoy"])
        self.assertTrue(any("NO existen aún" in a for a in p["avisos"]))
        self.assertEqual(sum(p["resumen"]["por_estado"].values()), p["resumen"]["modulos"])

    def test_lo_planeado_no_se_promete_en_el_texto(self):
        md = E.a_md(self.proponer(self.negocio("comercio")))
        self.assertIn("Lo que aún NO existe en el ERP central", md)
        self.assertIn("No se promete", md)
        self.assertRegex(md, r"Ventas \(`ventas`\) \| NO existe: solo está planeado")
        self.assertRegex(md, r"Compras \(`compras`\) \| en construcción")

    def test_producto_de_partida_sin_senal_no_se_incluye(self):
        p = self.proponer(self.negocio("comercio"))
        sin = {m["id"] for m in p["producto_partida"]["modulos_sin_senal"]}
        self.assertTrue(sin)                                            # p. ej. bancos: el producto lo trae pero los documentos no lo piden
        self.assertFalse(sin & set(self.ids(p)))

    def test_cada_modulo_senalado_trae_evidencia_con_archivo_y_linea(self):
        p = self.proponer(self.negocio("comercio"))
        for m in p["modulos"]:
            if m["origen"] == "senal":
                s = next(s for s in p["senales"] if s["id"] == m["senales"][0])
                self.assertTrue(s["evidencia"], m["id"])
                for ev in s["evidencia"]:
                    self.assertEqual(ev["archivo"], "descripcion.md")
                    self.assertIsInstance(ev["linea"], int)
                    self.assertLessEqual(len(ev["fragmento"]), 140 + 2)
                    self.assertTrue(ev["termino"])
        tr = {t["modulo"]: t for t in p["trazabilidad"]}
        self.assertEqual(tr["compras"]["estado_catalogo"], "en_construccion")
        self.assertRegex(tr["compras"]["evidencia"], r"^descripcion\.md:\d+$")
        self.assertIn("núcleo", tr["identidad"]["justificacion"])


class Opcionales(Base):
    def test_sitio_web_ofrece_el_adaptador_sin_ejecutar(self):
        n = self.negocio("comercio")
        (n / "web.md").write_text("Queremos una página web y un sitio corporativo con landing para el catálogo.\n", encoding="utf-8")
        p = self.proponer(n)
        self.assertEqual([o["id"] for o in p["opcionales"]], ["diseno-web"])
        self.assertTrue(p["opcionales"][0]["ofrecido"])
        self.assertFalse(p["opcionales"][0]["ejecutado"])
        self.assertIn("adaptadores/diseno-web", E.a_md(p))

    def test_sin_mencion_no_ofrece_nada(self):
        self.assertEqual(self.proponer(self.negocio("industrial"))["opcionales"], [])

    def test_integraciones_y_correos_se_senalan(self):
        n = self.negocio("comercio")
        (n / "otros.md").write_text("Necesitamos integración con el sistema del banco y enviar correos automáticos a los clientes.\n", encoding="utf-8")
        p = self.proponer(n)
        self.assertTrue({"integraciones", "notificaciones"} <= set(self.ids(p)))
        md = E.a_md(p)
        self.assertIn("Integraciones", md)
        self.assertIn("Correos y avisos", md)
        self.assertTrue(any("integraciones" in a and "no existe" in a for a in p["avisos"]))


    def test_codigos_de_barras_senalan_el_diagnostico_sin_asumir_escaneo(self):
        n = self.negocio("comercio")
        (n / "almacen.md").write_text("En el almacén usamos pistola y etiquetas con código de barras EAN para recibir la mercadería.\n", encoding="utf-8")
        p = self.proponer(n)
        self.assertIn("almacen", self.ids(p))
        self.assertTrue(any("diagnóstico de códigos" in a for a in p["avisos"]))


class Robustez(Base):
    def test_carpeta_vacia_da_solo_el_nucleo_y_lo_dice(self):
        vacia = self.tmp / "vacia"
        vacia.mkdir()
        p = self.proponer(vacia)
        self.assertEqual(self.ids(p), ["identidad", "autenticacion", "configuracion", "interfaz"])
        self.assertIsNone(p["rubro"])
        self.assertEqual(p["producto_partida"]["id"], "a-medida")
        self.assertEqual(p["documentos"]["leidos"], 0)
        self.assertTrue(any("solo el núcleo" in a for a in p["avisos"]))

    def test_binarios_y_formatos_no_leibles_se_listan_sin_romper(self):
        n = self.negocio("comercio")
        (n / "foto.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + os.urandom(64))
        (n / "datos.md").write_bytes(b"\x00\x01\x02\x03 inventario \xff\xfe\x00\x00" * 10)     # .md con contenido binario
        (n / "informe.pdf").write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        (n / "viejo.xls").write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 40)
        (n / "roto.xlsx").write_bytes(b"no soy un zip")
        p = self.proponer(n)
        razones = {x["archivo"]: x["razon"] for x in p["documentos"]["no_leidos"]}
        for f in ("foto.png", "datos.md", "informe.pdf", "viejo.xls", "roto.xlsx"):
            self.assertIn(f, razones, f)
        self.assertIn("binario", razones["datos.md"])
        self.assertEqual(p["documentos"]["leidos"], 1)                 # solo descripcion.md
        self.assertEqual(p["rubro"]["id"], "comercio")                 # y se sigue proponiendo con lo legible

    def test_archivo_enorme_se_salta_por_el_tope_de_lectura(self):
        n = self.negocio("comercio")
        lector = E.cargar_lector()
        (n / "enorme.txt").write_text(("inventario de almacen y kardex. " * 70_000), encoding="utf-8")
        self.assertGreater((n / "enorme.txt").stat().st_size, lector.MAX_BYTES)
        p = self.proponer(n)
        razones = {x["archivo"]: x["razon"] for x in p["documentos"]["no_leidos"]}
        self.assertIn("tope de lectura", razones["enorme.txt"])
        self.assertEqual(p["documentos"]["leidos"], 1)

    def test_tope_total_de_archivos(self):
        n = self.tmp / "muchos"
        n.mkdir()
        for i in range(12):
            (n / f"a{i:02d}.md").write_text("tienda con inventario\n", encoding="utf-8")
        anterior = E.MAX_ARCHIVOS
        E.MAX_ARCHIVOS = 5
        try:
            p = self.proponer(n)
        finally:
            E.MAX_ARCHIVOS = anterior
        self.assertEqual(p["documentos"]["leidos"], 5)
        self.assertTrue(any("tope de" in a for a in p["avisos"]))

    def test_enlaces_simbolicos_no_se_siguen(self):
        n = self.negocio("comercio")
        fuera = self.tmp / "fuera"
        fuera.mkdir()
        (fuera / "secreto.md").write_text("ferretería inventario kardex\n", encoding="utf-8")
        try:
            os.symlink(fuera, n / "enlace-carpeta")
            os.symlink(fuera / "secreto.md", n / "enlace.md")
        except OSError:
            self.skipTest("sin enlaces simbólicos")
        p = self.proponer(n)
        self.assertEqual(p["documentos"]["leidos"], 1)
        self.assertEqual([x["archivo"] for x in p["documentos"]["no_leidos"]], ["enlace.md"])

    def test_hojas_de_calculo_csv_y_xlsx_alimentan_las_senales(self):
        n = self.tmp / "hojas"
        n.mkdir()
        (n / "procesos.csv").write_text("proceso,descripcion\nalmacen,inventario y kardex del almacen\ncompras,orden de compra a proveedores\n", encoding="utf-8")
        p = self.proponer(n)
        self.assertTrue({"almacen", "compras"} <= set(self.ids(p)))
        ev = next(s for s in p["senales"] if s["id"] == "almacen")["evidencia"][0]
        self.assertEqual(ev["archivo"], "procesos.csv")

    def test_tildes_mayusculas_y_plurales(self):
        n = self.tmp / "tildes"
        n.mkdir()
        (n / "t.md").write_text("ÓRDENES DE COMPRA por proveedor.\nSolicitudes de Compra y Adquisiciones.\n", encoding="utf-8")
        p = self.proponer(n)
        self.assertIn("compras", self.ids(p))

    def test_palabra_completa_no_subcadena(self):
        n = self.tmp / "sub"
        n.mkdir()
        (n / "t.md").write_text("estocástico, restock y almacenamiento de sueños; backups, nomina de tareas\n", encoding="utf-8")
        p = self.proponer(n)
        self.assertNotIn("almacen", self.ids(p))

    def test_secretos_se_enmascaran_en_los_fragmentos(self):
        n = self.tmp / "sec"
        n.mkdir()
        (n / "t.md").write_text("Control de inventario y kardex del almacén, password=SuperClave12345 en la hoja.\n"
                                "Más inventario, más kardex, más almacén.\n", encoding="utf-8")
        p = self.proponer(n)
        texto = json.dumps(p, ensure_ascii=False)
        self.assertNotIn("SuperClave12345", texto)
        self.assertIn("almacen", self.ids(p))

    def test_no_modifica_la_carpeta_del_negocio(self):
        n = self.negocio("comercio")
        antes = hash_arbol(n)
        self.proponer(n)
        E.resumen_pantalla(self.proponer(n))
        self.assertEqual(antes, hash_arbol(n))

    def test_no_modifica_el_erp(self):
        n = self.negocio("comercio")
        antes = hash_arbol(self.erp)
        self.proponer(n)
        self.assertEqual(antes, hash_arbol(self.erp))

    def test_carpeta_inexistente_y_catalogo_inexistente(self):
        with self.assertRaises(E.ErrorErp) as c:
            E.generar(self.tmp / "no-existe", self.erp)
        self.assertIn("No existe la carpeta del negocio", str(c.exception))
        with self.assertRaises(E.ErrorErp) as c:
            E.generar(self.negocio("comercio"), self.tmp / "otro-erp")
        self.assertIn("--erp-base", str(c.exception))

    def test_catalogo_mal_formado(self):
        (self.erp / "modulos" / "catalogo.json").write_text("{no es json", encoding="utf-8")
        with self.assertRaises(E.ErrorErp):
            self.proponer(self.negocio("comercio"))
        (self.erp / "modulos" / "catalogo.json").write_text(json.dumps({"modulos": []}), encoding="utf-8")
        with self.assertRaises(E.ErrorErp):
            self.proponer(self.negocio("comercio"))


class Determinismo(Base):
    def test_misma_entrada_misma_salida(self):
        n = self.negocio("comercio")
        a, b = E.generar(n, self.erp), E.generar(n, self.erp)
        self.assertEqual(json.dumps(a, sort_keys=False), json.dumps(b, sort_keys=False))
        self.assertEqual(E.a_md(a), E.a_md(b))
        self.assertEqual(E.especificacion_md(a), E.especificacion_md(b))
        self.assertEqual(E.matriz_md(a), E.matriz_md(b))

    def test_otra_ubicacion_y_otro_orden_de_creacion_dan_lo_mismo(self):
        a = self.negocio("comercio", "uno")
        b = self.tmp / "otro" / "sitio"
        b.mkdir(parents=True)
        for nombre in reversed(sorted(F.NEGOCIOS["comercio"])):
            (b / nombre).write_text(F.NEGOCIOS["comercio"][nombre], encoding="utf-8")
        self.assertEqual(E.generar(a, self.erp), E.generar(b, self.erp))

    def test_sin_rutas_absolutas_ni_fechas(self):
        n = self.negocio("comercio")
        js = json.dumps(E.generar(n, self.erp), ensure_ascii=False) + E.a_md(E.generar(n, self.erp))
        self.assertNotIn(str(self.tmp), js)
        self.assertNotIn(str(RAIZ), js)
        self.assertNotRegex(js, r"\b20\d\d-\d\d-\d\d\b")


class Senales(Base):
    def escribir(self, texto):
        ruta = self.tmp / "senales.toml"
        ruta.write_text(texto, encoding="utf-8")
        return ruta

    def test_el_archivo_por_defecto_es_valido_y_sus_ids_son_unicos(self):
        cfg = E.cargar_senales()
        ids = [(r["clase"], r["id"]) for r in cfg["reglas"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(len([r for r in cfg["reglas"] if r["clase"] == "senal"]), 60)
        for r in cfg["reglas"]:
            for t in r["terminos"]:
                self.assertEqual(t["texto"], t["texto"].lower(), f"{r['id']}: {t['texto']}")
                self.assertEqual(E.sin_tildes(t["texto"]), t["texto"], f"{r['id']} lleva tildes: {t['texto']}")

    def test_termino_mal_formado(self):
        for cuerpo in ('[senal.x]\nmodulos=["almacen"]\nterminos=[["solo texto"]]\n', '[senal.x]\nmodulos=[]\nterminos=[["a", 0]]\n',
                       '[senal.x]\nmodulos=[]\nterminos=[]\n', '[senal.x]\nmodulos=[]\nterminos=[["!!!", 2]]\n', ""):
            with self.assertRaises(E.ErrorErp, msg=cuerpo):
                E.cargar_senales(self.escribir(cuerpo))
        with self.assertRaises(E.ErrorErp):
            E.cargar_senales(self.tmp / "no-existe.toml")

    def test_se_puede_editar_el_archivo_de_senales(self):
        """El comportamiento sale del archivo de datos, no del código: otra palabra, otro módulo."""
        ruta = self.escribir('[umbrales]\nsenal=2\n[senal.alm]\nmodulos=["almacen"]\nterminos=[["trastienda", 2]]\n')
        n = self.tmp / "e"
        n.mkdir()
        (n / "t.md").write_text("Todo está en la trastienda.\n", encoding="utf-8")
        p = E.generar(n, self.erp, ruta)
        self.assertIn("almacen", self.ids(p))
        self.assertEqual(p["senales"][0]["evidencia"][0]["termino"], "trastienda")

    def test_modulo_que_el_catalogo_no_tiene_avisa_una_vez_y_se_ignora(self):
        ruta = self.escribir('[senal.x]\nmodulos=["no-existe", "tampoco"]\nterminos=[["trastienda", 3]]\n[senal.y]\nmodulos=["no-existe"]\nterminos=[["bodega", 3]]\n')
        n = self.tmp / "e"
        n.mkdir()
        (n / "t.md").write_text("trastienda y bodega\n", encoding="utf-8")
        p = E.generar(n, self.erp, ruta)
        avisos = [a for a in p["avisos"] if "no están en este catálogo" in a]
        self.assertEqual(len(avisos), 1)
        self.assertIn("no-existe", avisos[0])
        self.assertEqual(self.ids(p), ["identidad", "autenticacion", "configuracion", "interfaz"])

    def test_umbral_senales_debiles(self):
        n = self.tmp / "d"
        n.mkdir()
        (n / "t.md").write_text("Alguna vez usamos un proveedor.\n", encoding="utf-8")
        p = self.proponer(n)
        self.assertNotIn("compras", self.ids(p))
        self.assertIn("compras", [s["id"] for s in p["senales_debiles"]])

    def test_tope_de_coincidencias_por_termino_y_archivo(self):
        n = self.tmp / "r"
        n.mkdir()
        (n / "t.md").write_text("\n".join(["proveedor"] * 50) + "\n", encoding="utf-8")
        p = E.generar(n, self.erp)
        s = next(s for s in p["senales_debiles"] + p["senales"] if s["id"] == "compras")
        self.assertEqual(s["puntos"], 3)          # peso 1 x tope 3: repetir una palabra no infla la señal

    @unittest.skipUnless(os.environ.get("HARNESS_ERP_BASE_PRUEBA"), "define HARNESS_ERP_BASE_PRUEBA=<ruta del ERP estándar> para comprobar contra el catálogo real")
    def test_las_senales_cubren_modulos_reales_sin_ids_huerfanos(self):
        cat = E.cargar_catalogo(os.environ["HARNESS_ERP_BASE_PRUEBA"])
        cfg = E.cargar_senales()
        self.assertEqual(E.validar_senales(cfg, cat), [])
        senalados = {m for r in cfg["reglas"] for m in r["modulos"]}
        sin = [m for m in cat["orden"] if m not in senalados and not cat["modulos"][m].get("nucleo")]
        self.assertLessEqual(len(sin), 3, f"módulos reales sin ninguna señal: {sin}")


class Escritura(Base):
    def instancia(self):
        i = self.tmp / "instancia"
        i.mkdir()
        return i

    def test_escribe_cuatro_archivos_y_es_idempotente(self):
        inst, p = self.instancia(), self.proponer(self.negocio("comercio"))
        self.assertTrue(all(a == "crear" for _, a in E.estado_escritura(inst, p)))
        self.assertEqual(os.listdir(inst), [])                         # estado_escritura no escribe
        hechas = E.escribir(inst, p)
        self.assertEqual(sorted(r for r, _ in hechas), ["cambios/erp-composicion/especificacion.md", "cambios/erp-composicion/matriz.md",
                                                        "erp/propuesta-erp.json", "erp/propuesta-erp.md"])
        antes = hash_arbol(inst)
        self.assertEqual({a for _, a in E.escribir(inst, p)}, {"igual", "conservar"})
        self.assertEqual(antes, hash_arbol(inst))
        j = json.loads((inst / "erp" / "propuesta-erp.json").read_text(encoding="utf-8"))
        self.assertEqual(j["esquema"], E.ESQUEMA)
        self.assertEqual(j["entrega_al_compositor"]["esquema"], E.ESQUEMA_ENTREGA)

    def test_no_pisa_la_especificacion_editada_pero_si_actualiza_la_propuesta(self):
        inst, p = self.instancia(), self.proponer(self.negocio("comercio"))
        E.escribir(inst, p)
        esp = inst / "cambios" / "erp-composicion" / "especificacion.md"
        esp.write_text(esp.read_text(encoding="utf-8") + "\n- [x] OK explícito de la persona dueña (editado a mano)\n", encoding="utf-8")
        editado = esp.read_text(encoding="utf-8")
        (self.tmp / "negocio-comercio" / "extra.md").write_text("Queremos una página web.\n", encoding="utf-8")
        hechas = dict(E.escribir(inst, self.proponer(self.tmp / "negocio-comercio")))
        self.assertEqual(esp.read_text(encoding="utf-8"), editado)
        self.assertEqual(hechas["cambios/erp-composicion/especificacion.md"], "conservar")
        self.assertEqual(hechas["erp/propuesta-erp.md"], "actualizar")

    def test_instancia_inexistente(self):
        with self.assertRaises(E.ErrorErp):
            E.escribir(self.tmp / "no-existe", self.proponer(self.negocio("comercio")))

    def test_no_escribe_a_traves_de_enlaces(self):
        inst, p = self.instancia(), self.proponer(self.negocio("comercio"))
        destino = self.tmp / "otro-lado"
        destino.mkdir()
        (inst / "erp").mkdir()
        try:
            os.symlink(destino / "x.md", inst / "erp" / "propuesta-erp.md")
        except OSError:
            self.skipTest("sin enlaces simbólicos")
        with self.assertRaises(E.ErrorErp):
            E.escribir(inst, p)
        self.assertFalse((destino / "x.md").exists())


class Trazabilidad(Base):
    """La propuesta se engancha a la matriz del método: cada módulo es un RQ con su señal y su estado."""

    def correr(self, carpeta, etapa):
        r = subprocess.run([sys.executable, str(TRAZA), str(carpeta), "--etapa", etapa, "--json"], capture_output=True, text=True)
        return r.returncode, json.loads(r.stdout) if r.stdout.strip().startswith("{") else r.stdout

    def test_la_especificacion_generada_pasa_la_etapa_de_especificacion(self):
        for rubro in ("comercio", "servicios", "inmobiliario"):
            inst = self.tmp / f"inst-{rubro}"
            inst.mkdir()
            p = self.proponer(self.negocio(rubro))
            E.escribir(inst, p)
            c, d = self.correr(inst / "cambios" / "erp-composicion", "especificacion")
            self.assertEqual(c, 0, (rubro, d))
            self.assertEqual(d["resumen"]["errores"], 0)
            self.assertEqual(d["resumen"]["requisitos"], len(p["modulos"]))
            texto = (inst / "cambios" / "erp-composicion" / "especificacion.md").read_text(encoding="utf-8")
            self.assertEqual(texto.count("\n- RQ-"), len(p["modulos"]))

    def test_delegar_exige_resolver_lo_abierto_y_el_ok(self):
        inst, p = self.tmp / "inst", self.proponer(self.negocio("comercio"))
        inst.mkdir()
        E.escribir(inst, p)
        c, _ = self.correr(inst / "cambios" / "erp-composicion", "delegacion")
        self.assertEqual(c, 1)                                        # hay suposiciones abiertas (lo planeado) y falta el OK: no se promete

    def test_matriz_une_modulo_senal_y_estado(self):
        p = self.proponer(self.negocio("comercio"))
        matriz = E.matriz_md(p)
        filas = [l for l in matriz.splitlines() if l.startswith("| RQ-")]
        self.assertEqual(len(filas), len(p["modulos"]))
        compras = next(l for l in filas if "señal compras" in l)
        self.assertIn("descripcion.md:", compras)
        self.assertIn("catálogo: en_construccion", compras)
        self.assertIn("pendiente", compras)
        for l in filas:
            self.assertEqual(l.count("|"), 9, l)


if __name__ == "__main__":
    unittest.main()
