"""Pruebas del comando `harness erp`: pide lo que falta sin asumir, no escribe sin confirmación, no toca los documentos ni el ERP
y deja la propuesta en la instancia solo con el «sí». Catálogo y negocios inventados (herramientas/tests/erp_fixtures.py); sin red."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "cli"))
sys.path.insert(0, str(RAIZ / "cli" / "tests"))
sys.path.insert(0, str(RAIZ / "herramientas" / "tests"))
sys.dont_write_bytecode = True
import harness_cli as hc  # noqa: E402
from test_cli import Entrada, arbol_hash, archivos  # noqa: E402
import erp_fixtures as F  # noqa: E402

CLI = RAIZ / "cli" / "harness"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mh-cli-erp-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.erp = F.escribir_catalogo(self.tmp / "erp-base")
        self.negocio = F.escribir_negocio(self.tmp / "docs-negocio", "comercio")
        self.inst = self.tmp / "instancia"
        self.inst.mkdir()
        # El registro de fuentes del usuario no debe influir en las pruebas: se apunta a un archivo que no existe.
        self.viejo_registro = os.environ.get("HARNESS_FUENTES")
        os.environ["HARNESS_FUENTES"] = str(self.tmp / "fuentes.toml")
        self.addCleanup(self._restaurar_registro)

    def _restaurar_registro(self):
        if self.viejo_registro is None:
            os.environ.pop("HARNESS_FUENTES", None)
        else:
            os.environ["HARNESS_FUENTES"] = self.viejo_registro

    def erp_cmd(self, *args, respuestas=(), interactivo=False):
        ent = Entrada(respuestas)
        buf = StringIO()
        c = hc.main(["erp", *map(str, args)], entrada=ent, salida=buf, interactivo=interactivo)
        return c, buf.getvalue(), ent

    def comun(self):
        return ["--negocio", self.negocio, "--erp-base", self.erp]


class Entradas(Base):
    def test_sin_carpeta_de_negocio_y_sin_terminal_pide_indicarla(self):
        c, out, _ = self.erp_cmd("--erp-base", self.erp)
        self.assertEqual(c, 2)
        self.assertIn("--negocio", out)
        self.assertIn("no leo nada más ni uso la red", out)

    def test_con_terminal_pregunta_la_carpeta_nunca_la_asume(self):
        c, out, ent = self.erp_cmd("--erp-base", self.erp, respuestas=[str(self.negocio), ""], interactivo=True)
        self.assertEqual(c, 0, out)
        self.assertTrue(any("documentos del negocio" in p for p in ent.prompts))
        self.assertIn("Comercio", out)

    def test_pregunta_tambien_donde_esta_el_erp_y_la_instancia(self):
        c, out, ent = self.erp_cmd(respuestas=[str(self.negocio), str(self.erp), ""], interactivo=True)
        self.assertEqual(c, 0, out)
        self.assertEqual(len(ent.prompts), 3)
        self.assertIn("No indicaste instancia", out)

    def test_respuesta_vacia_no_inventa_una_carpeta(self):
        c, out, _ = self.erp_cmd("--erp-base", self.erp, respuestas=[""], interactivo=True)
        self.assertEqual(c, 2)
        self.assertIn("no adivino", out)

    def test_carpeta_de_negocio_inexistente(self):
        c, out, _ = self.erp_cmd("--negocio", self.tmp / "nada", "--erp-base", self.erp)
        self.assertEqual(c, 2)
        self.assertIn("No existe la carpeta de documentos", out)

    def test_erp_base_sin_catalogo_dice_que_hacer(self):
        c, out, _ = self.erp_cmd("--negocio", self.negocio, "--erp-base", self.tmp)
        self.assertEqual(c, 2)
        self.assertIn("modulos/catalogo.json", out)
        self.assertIn("--erp-base", out)

    def test_falta_erp_base(self):
        c, out, _ = self.erp_cmd("--negocio", self.negocio)
        self.assertEqual(c, 2)
        self.assertIn("--erp-base", out)

    def test_usa_el_erp_registrado_si_no_se_indica(self):
        self.assertEqual(hc.main(["aprender", "fuentes", "agregar", "erp-base", str(self.erp), "--tipo", "erp"], salida=StringIO()), 0)
        c, out, _ = self.erp_cmd("--negocio", self.negocio)
        self.assertEqual(c, 0, out)
        self.assertIn("Uso el ERP estándar registrado", out)

    def test_un_erp_base_explicito_gana_al_registrado(self):
        otro = self.tmp / "otro"
        otro.mkdir()
        self.assertEqual(hc.main(["aprender", "fuentes", "agregar", "erp-base", str(otro), "--tipo", "erp"], salida=StringIO()), 0)
        c, out, _ = self.erp_cmd(*self.comun())
        self.assertEqual(c, 0, out)
        self.assertNotIn("Uso el ERP estándar registrado", out)

    def test_una_respuesta_que_parece_secreto_se_descarta(self):
        c, out, _ = self.erp_cmd("--erp-base", self.erp, respuestas=["password=abcdef"], interactivo=True)
        self.assertEqual(c, 2)
        self.assertIn("parece un secreto", out)

    def test_instancia_inexistente_o_mal_ubicada(self):
        c, out, _ = self.erp_cmd(*self.comun(), "--instancia", self.tmp / "no-existe", "--aplicar")
        self.assertEqual(c, 2)
        self.assertIn("No existe la carpeta de la instancia", out)
        dentro = self.negocio / "instancia"
        dentro.mkdir()
        c, out, _ = self.erp_cmd(*self.comun(), "--instancia", dentro, "--aplicar")
        self.assertEqual(c, 2)
        self.assertIn("dentro de la carpeta de documentos", out)
        self.assertFalse(any(dentro.iterdir()))
        c, out, _ = self.erp_cmd(*self.comun(), "--instancia", self.erp / "modulos", "--aplicar")
        self.assertEqual(c, 2)
        self.assertIn("solo lectura", out)

    def test_senales_alternativas_mal_formadas(self):
        malas = self.tmp / "mal.toml"
        malas.write_text("[senal.x]\nterminos=[[1]]\n", encoding="utf-8")
        c, out, _ = self.erp_cmd(*self.comun(), "--senales", malas)
        self.assertEqual(c, 2)
        self.assertIn("Señales", out)


class Confirmacion(Base):
    def test_sin_instancia_solo_muestra_y_no_escribe_nada_en_ningun_lado(self):
        h_neg, h_erp = arbol_hash(self.negocio), arbol_hash(self.erp)
        c, out, _ = self.erp_cmd(*self.comun())
        self.assertEqual(c, 0, out)
        self.assertIn("Propuesta de ERP", out)
        self.assertIn("no se instaló ni copió nada", out)
        self.assertEqual((h_neg, h_erp), (arbol_hash(self.negocio), arbol_hash(self.erp)))

    def test_con_instancia_pero_sin_terminal_ni_aplicar_muestra_el_plan_y_no_escribe(self):
        c, out, _ = self.erp_cmd(*self.comun(), "--instancia", self.inst)
        self.assertEqual(c, 0, out)
        self.assertIn("crearía: erp/propuesta-erp.md", out)
        self.assertIn("no escribí nada", out)
        self.assertEqual(archivos(self.inst), [])

    def test_responder_no_o_enter_no_escribe(self):
        for resp in ("n", "", "no", "quizás"):
            c, out, ent = self.erp_cmd(*self.comun(), "--instancia", self.inst, respuestas=[resp], interactivo=True)
            self.assertEqual(c, 0, out)
            self.assertIn("¿Escribo la propuesta", ent.prompts[-1])
            self.assertEqual(archivos(self.inst), [], resp)
            self.assertIn("No escribí nada", out)

    def test_ctrl_c_y_fin_de_entrada_no_escriben(self):
        for exc in (KeyboardInterrupt, EOFError):
            ent = Entrada([exc])
            buf = StringIO()
            c = hc.main(["erp", *map(str, self.comun()), "--instancia", str(self.inst)], entrada=ent, salida=buf, interactivo=True)
            self.assertEqual(c, 130)
            self.assertEqual(archivos(self.inst), [])

    def test_responder_si_escribe_cuatro_archivos(self):
        for resp in ("s", "si", "sí"):
            inst = self.tmp / f"i-{resp}"
            inst.mkdir()
            c, out, _ = self.erp_cmd(*self.comun(), "--instancia", inst, respuestas=[resp], interactivo=True)
            self.assertEqual(c, 0, out)
            self.assertEqual(archivos(inst), ["cambios/erp-composicion/especificacion.md", "cambios/erp-composicion/matriz.md",
                                              "erp/propuesta-erp.json", "erp/propuesta-erp.md"])
            self.assertIn("harness trazar", out)
            self.assertIn("aún no existe", out)

    def test_aplicar_escribe_sin_preguntar_y_es_idempotente(self):
        c, out, ent = self.erp_cmd(*self.comun(), "--instancia", self.inst, "--aplicar", interactivo=True)
        self.assertEqual(c, 0, out)
        self.assertEqual(ent.prompts, [])
        self.assertEqual(len(archivos(self.inst)), 4)
        h = arbol_hash(self.inst)
        c, out, _ = self.erp_cmd(*self.comun(), "--instancia", self.inst, "--aplicar")
        self.assertEqual(c, 0)
        self.assertEqual(h, arbol_hash(self.inst))
        self.assertIn("sin cambios", out)

    def test_los_documentos_y_el_erp_quedan_intactos_tras_escribir(self):
        h_neg, h_erp = arbol_hash(self.negocio), arbol_hash(self.erp)
        self.erp_cmd(*self.comun(), "--instancia", self.inst, "--si")
        self.assertEqual((h_neg, h_erp), (arbol_hash(self.negocio), arbol_hash(self.erp)))

    def test_json_una_sola_salida_y_no_escribe_sin_aplicar(self):
        c, out, _ = self.erp_cmd(*self.comun(), "--instancia", self.inst, "--json")
        self.assertEqual(c, 0, out)
        d = json.loads(out)
        self.assertEqual(d["propuesta"]["rubro"]["id"], "comercio")
        self.assertFalse(d["escritura"]["aplicado"])
        self.assertEqual(archivos(self.inst), [])
        c, out, _ = self.erp_cmd(*self.comun(), "--instancia", self.inst, "--json", "--aplicar")
        self.assertTrue(json.loads(out)["escritura"]["aplicado"])
        self.assertEqual(len(archivos(self.inst)), 4)

    def test_la_propuesta_lleva_la_marca_de_la_instancia_solo_como_referencia(self):
        (self.inst / "sitio").mkdir()
        (self.inst / "sitio" / "DISENO.md").write_text("# Ficha de Ejemplo S. A.\nColor base #276eb1.\n", encoding="utf-8")
        self.erp_cmd(*self.comun(), "--instancia", self.inst, "--aplicar")
        j = json.loads((self.inst / "erp" / "propuesta-erp.json").read_text(encoding="utf-8"))
        m = j["entrega_al_compositor"]["marca"]
        self.assertEqual((m["fuente"], m["en_instancia"], m["datos_de_marca_en_este_archivo"]), ("sitio/DISENO.md", True, False))
        self.assertNotIn("276eb1", json.dumps(j))


class Integracion(Base):
    def test_ejecutable_real_y_ayuda(self):
        r = subprocess.run([sys.executable, str(CLI), "erp", "-h"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0)
        self.assertIn("--negocio", r.stdout)
        self.assertIn("Ejemplos", r.stdout)
        r = subprocess.run([sys.executable, str(CLI), "erp", *map(str, self.comun()), "--instancia", str(self.inst)], capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Módulos propuestos: ", r.stdout)
        self.assertEqual(archivos(self.inst), [])

    def test_el_mapa_de_ayuda_nombra_el_comando(self):
        r = subprocess.run([sys.executable, str(CLI), "ayuda"], capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertIn("harness erp --negocio", r.stdout)

    def test_la_propuesta_escrita_pasa_harness_trazar(self):
        self.erp_cmd(*self.comun(), "--instancia", self.inst, "--aplicar")
        buf = StringIO()
        c = hc.main(["trazar", str(self.inst / "cambios" / "erp-composicion"), "--etapa", "especificacion"], salida=buf)
        self.assertEqual(c, 0, buf.getvalue())
        self.assertIn("RESULTADO: OK", buf.getvalue())

    def test_correr_dos_veces_deja_la_misma_propuesta(self):
        self.erp_cmd(*self.comun(), "--instancia", self.inst, "--aplicar")
        j1 = (self.inst / "erp" / "propuesta-erp.json").read_text(encoding="utf-8")
        self.erp_cmd(*self.comun(), "--instancia", self.inst, "--aplicar")
        self.assertEqual(j1, (self.inst / "erp" / "propuesta-erp.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
