import datetime as dt, importlib.util, pathlib, tempfile, unittest

spec = importlib.util.spec_from_file_location("frescura", pathlib.Path(__file__).resolve().parent.parent / "harness-frescura.py")
fr = importlib.util.module_from_spec(spec); spec.loader.exec_module(fr)
HOY = dt.date(2026, 1, 1)


def cab(fecha, vence="90d", fuente="un documento"):
    f = f" · fuente: {fuente}" if fuente is not None else ""
    return f"<!-- tipo: guia -->\n<!-- revisado: {fecha} · vence: {vence}{f} -->\n# T\n"


class Frescura(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.raiz = pathlib.Path(self.t.name)
        (self.raiz / ".git").mkdir(); (self.raiz / ".git" / "x.md").write_text("nada")
    def tearDown(self): self.t.cleanup()
    def doc(self, n, txt): (self.raiz / n).write_text(txt)

    def test_al_dia(self):
        self.doc("a.md", cab("2025-12-20"))
        r = fr.analizar(self.raiz, HOY)
        self.assertEqual((r["total"], r["al_dia"], r["vencidos"], r["sin_cabecera"]), (1, ["a.md"], [], []))
        self.assertEqual(fr.main([str(self.raiz), "--hoy", "2026-01-01"]), 0)

    def test_vencido(self):
        self.doc("v.md", cab("2025-01-01"))
        r = fr.analizar(self.raiz, HOY)
        self.assertEqual(r["vencidos"][0]["doc"], "v.md")
        self.assertEqual(fr.main([str(self.raiz), "--hoy", "2026-01-01"]), 1)

    def test_sin_fuente(self):
        self.doc("s.md", cab("2025-12-20", fuente=None)); self.doc("e.md", cab("2025-12-20", fuente=""))
        self.assertEqual(sorted(fr.analizar(self.raiz, HOY)["sin_fuente"]), ["e.md", "s.md"])

    def test_sin_cabecera(self):
        self.doc("n.md", "# nada\n")
        self.assertEqual(fr.analizar(self.raiz, HOY)["sin_cabecera"], ["n.md"])
        self.assertEqual(fr.main([str(self.raiz), "--hoy", "2026-01-01"]), 1)
        self.assertEqual(fr.main([str(self.raiz), "--hoy", "2026-01-01", "--tolerar-sin-cabecera"]), 0)

    def test_tolerar_no_oculta_vencidos(self):
        self.doc("n.md", "x"); self.doc("v.md", cab("2020-01-01"))
        self.assertEqual(fr.main([str(self.raiz), "--hoy", "2026-01-01", "--tolerar-sin-cabecera"]), 1)

    def test_por_vencer_y_limites(self):
        self.doc("p.md", cab("2025-10-10"))   # vence 2026-01-08 -> 7 días
        self.doc("l.md", cab("2025-10-01"))   # vence 2025-12-30 -> -2 vencido
        self.doc("h.md", cab("2025-10-03"))   # vence 2026-01-01 -> 0, vigente hoy
        r = fr.analizar(self.raiz, HOY)
        self.assertEqual([i["doc"] for i in r["por_vencer"]], ["h.md", "p.md"])
        self.assertEqual([i["doc"] for i in r["vencidos"]], ["l.md"])

    def test_fecha_invalida_es_sin_cabecera_y_json(self):
        self.doc("i.md", cab("2025-13-45"))
        self.assertEqual(fr.analizar(self.raiz, HOY)["sin_cabecera"], ["i.md"])
        self.assertEqual(fr.main([str(self.raiz), "--hoy", "2026-01-01", "--json", "--tolerar-sin-cabecera"]), 0)


if __name__ == "__main__": unittest.main()
