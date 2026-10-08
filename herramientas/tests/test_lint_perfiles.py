import importlib.util, pathlib, tempfile, unittest, datetime
H = pathlib.Path(__file__).resolve().parent.parent / "harness-lint-perfiles.py"
spec = importlib.util.spec_from_file_location("lint", H); L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
HOY = datetime.date(2026, 10, 7)
CAB = "# T\n<!-- tipo: perfil · capa: 3 -->\n<!-- revisado: 2026-10-07 · vence: 90d · fuente: prueba -->\n\ncuerpo\n"

def crear(base, omitir=None, cab=CAB, sobre=None):
    p = pathlib.Path(base) / "p"
    for rel in L.REQ:
        if rel == omitir: continue
        f = p / rel; f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text((sobre or {}).get(rel, cab), encoding="utf8")
    return p

class T(unittest.TestCase):
    def test_completo(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(L.lint_perfil(crear(d), HOY), [])
    def test_falta_archivo(self):
        with tempfile.TemporaryDirectory() as d:
            e = L.lint_perfil(crear(d, omitir="datos.md"), HOY)
            self.assertEqual(len(e), 1); self.assertIn("datos.md: falta", e[0])
    def test_cabecera_ausente(self):
        with tempfile.TemporaryDirectory() as d:
            e = L.lint_perfil(crear(d, sobre={"seguridad.md": "# T\n\ncuerpo\n"}), HOY)
            self.assertTrue(any("tipo" in x for x in e)); self.assertTrue(any("revisado" in x for x in e))
    def test_vencido(self):
        with tempfile.TemporaryDirectory() as d:
            e = L.lint_perfil(crear(d), datetime.date(2027, 3, 1))
            self.assertTrue(e and all("vencido" in x for x in e))
if __name__ == "__main__": unittest.main()
