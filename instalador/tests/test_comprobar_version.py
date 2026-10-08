import importlib.util, pathlib, subprocess, tempfile, unittest

spec = importlib.util.spec_from_file_location("cv", pathlib.Path(__file__).resolve().parent.parent / "comprobar-version.py")
cv = importlib.util.module_from_spec(spec); spec.loader.exec_module(cv)


def g(d, *a): subprocess.run(["git", "-C", str(d), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *a], check=True, capture_output=True)


class Version(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); b = pathlib.Path(self.t.name)
        self.h = b / "h"; self.i = b / "i"; self.h.mkdir(); self.i.mkdir()
        g(self.h, "init", "-q"); (self.h / "VERSION").write_text("0.1.0\n")
        g(self.h, "add", "."); g(self.h, "commit", "-qm", "inicial"); g(self.h, "tag", "v0.1.0")
        (self.h / "VERSION").write_text("0.2.0\n"); g(self.h, "commit", "-qam", "cambio a"); g(self.h, "tag", "v0.2.0")
    def tearDown(self): self.t.cleanup()
    def lock(self, txt): (self.i / "harness.lock").write_text(txt)

    def test_sin_instancia(self):
        r = cv.comprobar(self.h); self.assertEqual((r["estado"], r["ultima_etiqueta"]), ("al_dia", "v0.2.0"))
    def test_al_dia(self):
        self.lock('version = "0.2.0"\nfuente = "ruta"\n')
        self.assertEqual(cv.comprobar(self.h, self.i)["estado"], "al_dia")
    def test_atrasada_lista_commits(self):
        self.lock('version = "0.1.0"\nfuente = "ruta"\n'); r = cv.comprobar(self.h, self.i)
        self.assertEqual((r["estado"], r["codigo"]), ("atrasada", 1)); self.assertEqual(len(r["cambios"]), 1); self.assertIn("cambio a", r["cambios"][0])
    def test_invalidos(self):
        for txt in ("esto no es toml [[", 'version = "abc"\nfuente = "x"\n', 'version = "0.1.0"\n'):
            self.lock(txt); r = cv.comprobar(self.h, self.i); self.assertEqual((r["estado"], r["codigo"]), ("lock_invalido", 2), txt)
    def test_ausente_no_lo_crea(self):
        r = cv.comprobar(self.h, self.i)
        self.assertEqual(r["estado"], "sin_lock"); self.assertIn("version =", "\n".join(r["mensajes"]))
        self.assertFalse((self.i / "harness.lock").exists())
    def test_version_ilegible(self):
        (self.h / "VERSION").write_text("basura"); self.assertEqual(cv.comprobar(self.h)["codigo"], 2)
    def test_sin_git(self):
        d = pathlib.Path(self.t.name) / "sg"; d.mkdir(); (d / "VERSION").write_text("1.0.0")
        self.lock('version = "0.9.0"\nfuente = "x"\n'); r = cv.comprobar(d, self.i)
        self.assertEqual(r["estado"], "atrasada"); self.assertNotIn("cambios", r)


if __name__ == "__main__": unittest.main()
