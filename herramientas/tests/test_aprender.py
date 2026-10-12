"""Pruebas de harness-aprender.py: registro de fuentes, escaneo idempotente, cola fuera de la fuente y promoción con gate.

<!-- tipo: herramienta · capa: 4 -->
Todo ocurre en carpetas temporales; el registro y la cola reales del usuario no se tocan.
"""
import contextlib, hashlib, importlib.util, io, json, os, pathlib, tempfile, unittest

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
spec = importlib.util.spec_from_file_location("harness_aprender", RAIZ / "herramientas" / "harness-aprender.py")
ap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ap)

TECNICA = """## Paginación de listados

Un listado paginado no debe repetir el conteo total en cada página.
Calcula el total una sola vez y envíalo en la primera respuesta.
Si el total cambia entre páginas, el cliente debe volver a pedirlo.
Los parámetros de orden se validan contra una lista cerrada de columnas.
"""

NEGOCIO = """## Cálculo de la cuota

La cuota se cobra el día cinco de cada mes y la mora se suma al saldo.
La cuota vencida genera mora desde el día siguiente al vencimiento.
Cada cuota pagada reduce el saldo de capital pendiente de la operación.
La mora se calcula sobre la cuota vencida y no sobre el capital total.
"""


DESCRIPTIVA = """## Cómo es el módulo de almacén

El módulo de almacén muestra el stock por ubicación y por lote.
La pantalla principal presenta una tabla con filtros y un resumen superior.
Cada fila abre una ficha con el detalle del producto y sus movimientos.
Los gráficos de la parte superior resumen las entradas y las salidas.
"""


def hash_arbol(raiz):
    h = hashlib.sha256()
    for p in sorted(pathlib.Path(raiz).rglob("*")):
        if p.is_file():
            h.update(p.relative_to(raiz).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def correr(*argv):
    sal, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(sal), contextlib.redirect_stderr(err):
        try:
            codigo = ap.main(list(argv))
        except SystemExit as e:
            codigo = e.code
    return codigo, sal.getvalue(), err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        t = pathlib.Path(self.t.name)
        self.fuente = t / "fuente"
        (self.fuente / "docs").mkdir(parents=True)
        (self.fuente / "docs" / "guia.md").write_text("# Guía\n\n" + TECNICA + "\n" + NEGOCIO, encoding="utf8")
        (self.fuente / "dominio.txt").write_text("cuota\nmora\n", encoding="utf8")
        self.cola = t / "cola"
        self.harness = t / "harness"
        self.harness.mkdir()
        self.viejo = {k: os.environ.get(k) for k in ("HARNESS_FUENTES", "HARNESS_COLA", "HARNESS_PATRON_PROYECTO", "HARNESS_PROHIBIDOS")}
        os.environ["HARNESS_PROHIBIDOS"] = str(t / "no-existe-prohibidos.txt")  # aísla la lista real del usuario
        os.environ["HARNESS_FUENTES"] = str(t / "fuentes.toml")
        os.environ["HARNESS_COLA"] = str(self.cola)
        os.environ.pop("HARNESS_PATRON_PROYECTO", None)
        self.raiz_original, ap.RAIZ = ap.RAIZ, self.harness  # el .prohibidos.txt de pruebas es el de la carpeta temporal
        self.addCleanup(self.restaurar)
        self.assertEqual(correr("fuentes", "agregar", "base", str(self.fuente), "--tipo", "erp", "--incluir", "docs/*.md")[0], 0)

    def restaurar(self):
        ap.RAIZ = self.raiz_original
        for k, v in self.viejo.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def ledger(self):
        return json.loads((self.cola / "ledger.json").read_text(encoding="utf8"))


class Registro(Base):
    def test_listar_y_quitar(self):
        c, out, _ = correr("fuentes", "listar")
        self.assertEqual(c, 0)
        self.assertIn("base [erp]", out)
        self.assertEqual(ap.erp_base_registrado(), str(self.fuente.resolve()))
        self.assertEqual(correr("fuentes", "quitar", "base")[0], 0)
        self.assertIsNone(ap.erp_base_registrado())

    def test_ruta_inexistente_y_nombre_invalido(self):
        self.assertEqual(correr("fuentes", "agregar", "x", "/no/existe", "--tipo", "erp")[0], 2)
        self.assertEqual(correr("fuentes", "agregar", "a b", str(self.fuente), "--tipo", "erp")[0], 2)

    def test_carpeta_exige_incluir(self):
        self.assertEqual(correr("fuentes", "agregar", "c", str(self.fuente), "--tipo", "carpeta")[0], 2)


class Escaneo(Base):
    def test_separa_tecnica_de_negocio_sin_tocar_la_fuente(self):
        antes = hash_arbol(self.fuente)
        c, out, _ = correr("escanear", "--json")
        self.assertEqual(c, 0)
        r = json.loads(out)
        self.assertEqual(len(r["nuevos"]), 1, r)
        self.assertEqual(r["negocio"], 1)
        self.assertEqual(hash_arbol(self.fuente), antes, "la fuente no debe cambiar")
        pend = [d.name for d in (self.cola / "pendientes").iterdir()]
        self.assertEqual(pend, r["nuevos"])
        self.assertTrue((self.cola / "pendientes" / pend[0] / "ORIGEN.md").is_file())
        self.assertTrue((self.cola / "INFORME.md").is_file())

    def test_una_descripcion_general_no_entra_a_la_cola(self):
        doc = self.fuente / "docs" / "guia.md"
        doc.write_text(doc.read_text(encoding="utf8") + "\n" + DESCRIPTIVA, encoding="utf8")
        _, out, _ = correr("escanear", "--json")
        r = json.loads(out)
        self.assertEqual(len(r["nuevos"]), 1, "solo la regla técnica")
        self.assertEqual(r["descriptivas"], 1)

    def test_una_memoria_con_encabezado_yaml_usa_su_nombre(self):
        (self.fuente / "docs" / "feedback_paginar.md").write_text(
            "---\nname: paginar-sin-repetir-el-total\ndescription: x\nmetadata:\n  type: feedback\n---\n\n" + TECNICA.split("\n", 2)[2], encoding="utf8")
        _, out, _ = correr("escanear", "--json")
        nuevos = json.loads(out)["nuevos"]
        self.assertIn("paginar-sin-repetir-el-total", nuevos)

    def test_idempotente_y_reprocesa_si_cambia(self):
        correr("escanear")
        _, out, _ = correr("escanear", "--json")
        r = json.loads(out)
        self.assertEqual(r["nuevos"], [])
        self.assertGreaterEqual(r["sin_cambio"], 2)
        doc = self.fuente / "docs" / "guia.md"
        doc.write_text(doc.read_text(encoding="utf8").replace("una sola vez", "una única vez"), encoding="utf8")
        _, out, _ = correr("escanear", "--json")
        self.assertEqual(len(json.loads(out)["nuevos"]), 1)
        self.assertEqual(len(list((self.cola / "pendientes").iterdir())), 1, "el paquete viejo se reemplaza, no se duplica")

    def test_cola_dentro_de_la_fuente_se_rechaza(self):
        os.environ["HARNESS_COLA"] = str(self.fuente / "docs" / "cola")
        c, _, err = correr("escanear")
        self.assertEqual(c, 2)
        self.assertIn("no puede estar dentro", err)

    def test_max_frecuencia_omite(self):
        correr("escanear")
        _, out, _ = correr("escanear", "--max-frecuencia", "3600")
        self.assertIn("reciente", out)

    def test_silencioso_no_rompe_con_registro_danado(self):
        pathlib.Path(os.environ["HARNESS_FUENTES"]).write_text("esto no es [toml", encoding="utf8")
        c, out, err = correr("escanear", "--silencioso")
        self.assertEqual(c, 1)
        self.assertEqual((out, err), ("", ""))

    def test_termino_prohibido_bloquea_el_aporte(self):
        (self.harness / ".prohibidos.txt").write_text("conteo\n", encoding="utf8")
        _, out, _ = correr("escanear", "--json")
        r = json.loads(out)
        self.assertEqual(r["nuevos"], [])
        self.assertEqual(r["bloqueadas"], 1)


class Cola(Base):
    def primero(self):
        _, out, _ = correr("escanear", "--json")
        return json.loads(out)["nuevos"][0]

    def test_descartar_no_resucita(self):
        ident = self.primero()
        self.assertEqual(correr("descartar", ident)[0], 2, "exige motivo")
        self.assertEqual(correr("descartar", ident, "--motivo", "es del proyecto")[0], 0)
        _, out, _ = correr("escanear", "--json")
        self.assertEqual(json.loads(out)["nuevos"], [])
        self.assertFalse((self.cola / "pendientes" / ident).exists())

    def test_promover_sin_aplicar_no_escribe(self):
        ident = self.primero()
        c, out, _ = correr("promover", ident, "--tipo", "estandar", "--harness", str(self.harness))
        self.assertEqual(c, 0, out)
        self.assertIn("Sin --aplicar no se escribe nada", out)
        self.assertEqual(list(self.harness.iterdir()), [])

    def test_promover_aplicar_copia_y_registra(self):
        ident = self.primero()
        c, out, _ = correr("promover", ident, "--tipo", "estandar", "--harness", str(self.harness), "--aplicar")
        self.assertEqual(c, 0, out)
        destino = self.harness / "estandares" / f"{ident}.md"
        self.assertTrue(destino.is_file())
        texto = destino.read_text(encoding="utf8")
        self.assertIn("<!-- tipo: estandar · capa: 2 -->", texto)
        self.assertIn("<!-- revisado:", texto)
        self.assertEqual(self.ledger()[next(u for u, r in self.ledger().items() if r.get("paquete") == ident)]["estado"], "promovida")
        self.assertIn("No se hizo commit ni push", out)

    def test_promover_bloqueado_por_prohibido_del_harness(self):
        ident = self.primero()
        (self.harness / ".prohibidos.txt").write_text("paginación\n", encoding="utf8")
        c, out, _ = correr("promover", ident, "--tipo", "estandar", "--harness", str(self.harness), "--aplicar")
        self.assertEqual(c, 1)
        self.assertIn("prohibidos", out)
        self.assertFalse((self.harness / "estandares").exists())

    def test_tipo_invalido(self):
        ident = self.primero()
        self.assertEqual(correr("promover", ident, "--tipo", "otro", "--harness", str(self.harness))[0], 2)

    def test_listar_y_ver(self):
        ident = self.primero()
        c, out, _ = correr("listar")
        self.assertEqual(c, 0)
        self.assertIn(ident, out)
        c, out, _ = correr("ver", ident)
        self.assertIn("Nota de origen", out)


if __name__ == "__main__":
    unittest.main()
