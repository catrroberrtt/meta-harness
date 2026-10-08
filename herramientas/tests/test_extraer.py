"""Pruebas del gate de extracción: lo que NO debe pasar al repositorio y lo que sí."""
import importlib.util, pathlib, tempfile, unittest

spec = importlib.util.spec_from_file_location("extraer", pathlib.Path(__file__).resolve().parent.parent / "harness-extraer.py")
ex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ex)

CAB = "# T\n\n<!-- tipo: perfil · capa: 3 -->\n<!-- revisado: 2026-01-01 · vence: 90d · fuente: prueba -->\n\n"
CLAVE_FALSA = "AK" + "IA" + "ZZ9QWERTY1234567"


class Gate(unittest.TestCase):
    def evaluar(self, cuerpo, patron=None):
        d = pathlib.Path(tempfile.mkdtemp())
        f = d / "doc.md"
        f.write_text(CAB + cuerpo, encoding="utf8")
        return ex.evaluar(f, patron or ex.cargar_patron())

    def test_documento_generico_pasa(self):
        self.assertTrue(self.evaluar("Una regla técnica sin ataduras.\n")["pasa"])

    def test_clave_de_ticket_reprueba_r2(self):
        r = self.evaluar("Se corrigió en ABC-123.\n")
        self.assertFalse(r["pasa"])
        self.assertTrue(r["reglas"]["R2"])

    def test_identificadores_de_regla_no_son_tickets(self):
        for ident in ("RD-4", "ARQ-12", "COD-3", "PAT-0", "SEG-9", "ERR-13", "REC-8", "REN-2", "OBS-1", "PRU-5", "DAT-4"):
            self.assertTrue(self.evaluar(f"Ver `{ident}`.\n")["pasa"], ident)

    def test_numero_de_pr_reprueba(self):
        self.assertFalse(self.evaluar("Llegó con el PR #1087.\n")["pasa"])

    def test_credencial_reprueba_r3(self):
        r = self.evaluar(f"clave {CLAVE_FALSA}\n")
        self.assertFalse(r["pasa"])
        self.assertTrue(r["reglas"]["R3"])

    def test_sin_tipo_reprueba_r1(self):
        d = pathlib.Path(tempfile.mkdtemp())
        f = d / "doc.md"
        f.write_text("# T\n\nsin cabecera de tipo\n", encoding="utf8")
        r = ex.evaluar(f, ex.cargar_patron())
        self.assertFalse(r["pasa"])
        self.assertTrue(r["reglas"]["R1"])

    def test_los_perfiles_del_repositorio_pasan_con_el_patron_generico(self):
        raiz = pathlib.Path(__file__).resolve().parents[2] / "perfiles"
        malos = []
        for doc in sorted(raiz.glob("*/*.md")) + sorted(raiz.glob("*/*/README.md")):
            if "_plantilla" in doc.parts:
                continue
            if not ex.evaluar(doc, ex.cargar_patron())["pasa"]:
                malos.append(str(doc.relative_to(raiz)))
        self.assertEqual(malos, [])


if __name__ == "__main__":
    unittest.main()
