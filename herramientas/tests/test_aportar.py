"""Pruebas de harness-aportar.py y harness-extraer.py con lecciones e instancia sintéticas.

Ejecutar desde la raíz del harness:  python3 -m unittest herramientas/tests/test_aportar.py
"""
import contextlib, hashlib, importlib.util, io, os, pathlib, re, tempfile, unittest

HERR = pathlib.Path(__file__).resolve().parent.parent


def cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, HERR / archivo)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


aportar = cargar("harness_aportar", "harness-aportar.py")
extraer = cargar("harness_extraer", "harness-extraer.py")

PATRONES = """# patrones de la instancia sintética
\\b(?:api|st|fn)-[a-z0-9-]+-zeta\\b
\\bZT-\\d+\\b
PR\\s?#\\d+
"""
DOMINIO = "# términos del negocio sintético\nfideicomiso\ncuota de socio\n"
PERSONAS = "Marta Quispe\n"

GENERAL = """# Una lista paginada no debe contar con un COUNT por página
<!-- tipo: estandar · capa: 2 -->

Cada página de un listado repetía la consulta de conteo sobre toda la tabla, así que el tiempo crecía con el tamaño del resultado.

## Regla

Calcula el total una sola vez y devuélvelo junto con la página. Si el total no cambia entre páginas, el cliente no debe pedirlo otra vez.

## Cómo revisarlo

Activa el registro de consultas y pide la página 1 y la página 5: debe haber un solo conteo.
"""

CON_REFS = """# Un filtro opcional no declarado en el DTO se ignora sin avisar
<!-- tipo: estandar · capa: 2 -->

Caso real: en ZT-123 el listado de api-core-zeta ignoraba el filtro `estado`. Lo reportó Marta Quispe en PR #45.

## Regla

Todo parámetro de consulta que el servicio lee debe estar declarado en el DTO; el validador descarta lo demás sin error.

## Cómo revisarlo

Pide el listado con el filtro y compara con el listado sin él. Ejemplo local: /home/marta/trabajo/api-core-zeta/src/listado.ts.
"""

NEGOCIO = """# Reglas del fideicomiso
<!-- tipo: metodo · capa: 1 -->

La cuota de socio se cobra el día 5 de cada mes.
La tasa del fideicomiso es 12 % anual y la comisión 2.5 % por operación.
Si el socio paga después del día 10 se cobra una penalidad de S/ 150.
El negocio decidió que el fideicomiso se renueva cada 24 meses.
El monto mínimo de la cuota de socio es S/ 1,500.
"""

MIXTA = """# Redondear al guardar y no al mostrar
<!-- tipo: estandar · capa: 2 -->

Un total calculado con decimales se redondeaba distinto en la pantalla y en el reporte.
Guarda el valor con la precisión de la columna y muestra exactamente lo guardado.
La comparación debe hacerse sobre el valor guardado, nunca sobre el que calcula la pantalla.
Cada prueba debe fijar la precisión que espera.
La cuota de socio se redondea a dos decimales según el fideicomiso.
"""


def escribir(carpeta, nombre, texto):
    p = pathlib.Path(carpeta) / nombre
    p.write_text(texto, encoding="utf8")
    return p


def huella(carpeta):
    h = hashlib.sha256()
    for p in sorted(pathlib.Path(carpeta).rglob("*")):
        h.update(str(p.relative_to(carpeta)).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def correr(modulo, args):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        codigo = modulo.main(args)
    return codigo, buf.getvalue() + err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.pop("HARNESS_PATRON_PROYECTO", None)
        self.tmp = tempfile.TemporaryDirectory()
        t = pathlib.Path(self.tmp.name)
        self.inst = t / "instancia"; self.inst.mkdir()
        escribir(self.inst, "patrones-proyecto.txt", PATRONES)
        escribir(self.inst, "dominio.txt", DOMINIO)
        escribir(self.inst, "personas.txt", PERSONAS)
        self.lec = t / "lecciones"; self.lec.mkdir()
        self.general = escribir(self.lec, "general.md", GENERAL)
        self.refs = escribir(self.lec, "refs.md", CON_REFS)
        self.negocio = escribir(self.lec, "negocio.md", NEGOCIO)
        self.mixta = escribir(self.lec, "mixta.md", MIXTA)
        self.salida = t / "salida"

    def tearDown(self):
        if self._env is not None:
            os.environ["HARNESS_PATRON_PROYECTO"] = self._env
        self.tmp.cleanup()

    def aportar(self, lec, *extra):
        return correr(aportar, [str(lec), "--instancia", str(self.inst), *extra])


class TestClasificacion(Base):
    def test_general_limpia(self):
        c, o = self.aportar(self.general)
        self.assertEqual(c, 0); self.assertIn("VEREDICTO: general\n", o)
        self.assertIn("RAZÓN:", o)

    def test_con_ticket_y_repo_es_general_con_referencias(self):
        c, o = self.aportar(self.refs)
        self.assertIn("VEREDICTO: general (con referencias a anonimizar)", o)
        for esperado in ("ZT-123", "api-core-zeta", "PR #45", "Marta Quispe", "/home/marta"):
            self.assertIn(esperado, o)  # las líneas causantes se muestran

    def test_negocio_se_queda(self):
        c, o = self.aportar(self.negocio, "--salida", str(self.salida))
        self.assertEqual(c, 1); self.assertIn("VEREDICTO: de negocio", o)
        self.assertIn("se queda en la instancia", o)
        self.assertFalse(self.salida.exists())

    def test_mixta_propone_corte(self):
        c, o = self.aportar(self.mixta, "--salida", str(self.salida))
        self.assertEqual(c, 1); self.assertIn("VEREDICTO: mixta", o)
        self.assertIn("SE QUEDA en la instancia", o); self.assertIn("SUBE", o)
        self.assertRegex(o, r"SE QUEDA.*\n\s+L\d+\s+La cuota de socio se redondea")
        self.assertFalse(self.salida.exists())

    def test_dominio_vacio_no_inventa_negocio(self):
        (self.inst / "dominio.txt").unlink()
        c, o = self.aportar(self.mixta)
        self.assertIn("VEREDICTO: general", o)  # sin diccionario de dominio no hay señal: límite documentado


class TestPaquete(Base):
    def test_sin_salida_no_escribe_nada(self):
        antes, antes_l = huella(self.inst), huella(self.lec)
        cwd = os.getcwd(); os.chdir(self.tmp.name)
        try:
            ls = sorted(os.listdir(self.tmp.name))
            self.aportar(self.general); self.aportar(self.refs)
            self.assertEqual(ls, sorted(os.listdir(self.tmp.name)))
        finally:
            os.chdir(cwd)
        self.assertEqual(antes, huella(self.inst)); self.assertEqual(antes_l, huella(self.lec))
        self.assertFalse(self.salida.exists())

    def test_paquete_sin_ninguna_referencia(self):
        antes = huella(self.inst)
        c, o = self.aportar(self.refs, "--salida", str(self.salida))
        self.assertEqual(c, 0, o)
        paquetes = list(self.salida.iterdir()); self.assertEqual(len(paquetes), 1)
        archivos = sorted(p.name for p in paquetes[0].iterdir())
        self.assertEqual(len(archivos), 3); self.assertIn("ORIGEN.md", archivos); self.assertIn("gate.txt", archivos)
        todo = "\n".join(p.read_text(encoding="utf8") for p in paquetes[0].iterdir()) + paquetes[0].name
        for prohibido in (r"ZT-\d+", r"zeta", r"Marta", r"Quispe", r"PR\s?#\d+", r"/home/", r"lecciones", r"refs\.md"):
            self.assertIsNone(re.search(prohibido, todo, re.I), prohibido)
        self.assertIn("<TICKET>", todo); self.assertIn("<repo>", todo); self.assertIn("<persona>", todo)
        self.assertIn("PASA", (paquetes[0] / "gate.txt").read_text(encoding="utf8"))
        self.assertEqual(antes, huella(self.inst))

    def test_paquete_de_la_general(self):
        c, o = self.aportar(self.general, "--salida", str(self.salida))
        self.assertEqual(c, 0, o)
        nombres = [p.name for p in self.salida.iterdir()]
        self.assertEqual(nombres, ["una-lista-paginada-no-debe-contar-con-un-count-por-pagina"])

    def test_no_sobrescribe_un_paquete(self):
        self.aportar(self.general, "--salida", str(self.salida))
        c, o = self.aportar(self.general, "--salida", str(self.salida))
        self.assertEqual(c, 1); self.assertIn("no se sobrescribe", o)

    def test_salida_dentro_de_la_instancia_se_rechaza(self):
        c, o = self.aportar(self.general, "--salida", str(self.inst / "aportes"))
        self.assertEqual(c, 2); self.assertFalse((self.inst / "aportes").exists())

    def test_sin_marca_de_tipo_el_gate_frena_el_paquete(self):
        sin = escribir(self.lec, "sin-marca.md", GENERAL.replace("<!-- tipo: estandar · capa: 2 -->\n", ""))
        c, o = self.aportar(sin, "--salida", str(self.salida))
        self.assertEqual(c, 1); self.assertIn("R1", o); self.assertFalse(self.salida.exists())

    def test_credencial_no_se_arregla_sola(self):
        mala = escribir(self.lec, "cred.md", GENERAL + "\nDB_PASSWORD=hunter2hunter2\n")
        c, o = self.aportar(mala, "--salida", str(self.salida))
        self.assertEqual(c, 1); self.assertIn("R3", o); self.assertFalse(self.salida.exists())


class TestExtraer(Base):
    def test_patron_de_la_instancia(self):
        p = extraer.cargar_patron(self.inst)
        self.assertIn("instancia", p.origen); self.assertTrue(p.search("ver ZT-9"))
        self.assertFalse(p.search("ver ABC-9"))

    def test_patron_generico_sin_archivo(self):
        vacia = pathlib.Path(self.tmp.name) / "vacia"; vacia.mkdir()
        p = extraer.cargar_patron(vacia)
        self.assertIn("genérico", p.origen)
        self.assertTrue(p.search("ticket ABC-123")); self.assertTrue(p.search("PR #12")); self.assertTrue(p.search("ver #123"))
        for libre in ("UTF-8", "SHA-256", "regla RD-8", "ISO-8601", "CVE-2024-1234"):
            self.assertFalse(p.search(libre), libre)

    def test_variable_de_entorno_tiene_prioridad(self):
        f = escribir(self.tmp.name, "otro.txt", "\\bQQ-\\d+\\b\n")
        os.environ["HARNESS_PATRON_PROYECTO"] = str(f)
        try:
            p = extraer.cargar_patron(self.inst)
            self.assertTrue(p.search("QQ-1")); self.assertFalse(p.search("ZT-1"))
        finally:
            del os.environ["HARNESS_PATRON_PROYECTO"]

    def test_pr_con_espacio_no_se_corta_como_comentario(self):
        self.assertTrue(extraer.cargar_patron(self.inst).search("fusionado en PR #77"))

    def test_gate_y_aplicar_copian_sin_sobrescribir(self):
        harness = pathlib.Path(self.tmp.name) / "harness"; harness.mkdir()
        c, o = correr(extraer, [str(self.general), "--instancia", str(self.inst), "--destino", str(harness), "--aplicar"])
        self.assertEqual(c, 0, o); self.assertIn("APLICADO", o)
        copiado = harness / "estandares" / "general.md"
        self.assertTrue(copiado.is_file()); self.assertTrue(self.general.is_file())
        self.assertTrue((harness / ".harness-extraido.json").is_file())
        self.general.write_text(GENERAL + "\nOtra línea.\n", encoding="utf8")
        c, o = correr(extraer, [str(self.general), "--instancia", str(self.inst), "--destino", str(harness), "--aplicar"])
        self.assertIn("no se sobrescribe", o)

    def test_no_pasa_con_referencias_y_no_escribe(self):
        harness = pathlib.Path(self.tmp.name) / "harness"; harness.mkdir()
        c, o = correr(extraer, [str(self.refs), "--instancia", str(self.inst), "--destino", str(harness), "--aplicar"])
        self.assertEqual(c, 1); self.assertIn("R2", o); self.assertEqual(list(harness.iterdir()), [])

    def test_solo_lectura_por_defecto(self):
        antes = huella(self.lec)
        correr(extraer, [str(self.general), str(self.refs), "--instancia", str(self.inst)])
        self.assertEqual(antes, huella(self.lec))


if __name__ == "__main__":
    unittest.main()
