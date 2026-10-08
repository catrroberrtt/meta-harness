import importlib.util, io, json, pathlib, tempfile, unittest, contextlib

spec = importlib.util.spec_from_file_location("equiv", pathlib.Path(__file__).resolve().parent.parent / "harness-equivalencia.py")
eq = importlib.util.module_from_spec(spec); spec.loader.exec_module(eq)


def caso(i, o, n, **k): return {"id": i, "entrada": "e", "salida_origen": o, "salida_nuevo": n, **k}


class Equivalencia(unittest.TestCase):
    def setUp(self): self.t = tempfile.TemporaryDirectory(); self.d = pathlib.Path(self.t.name)
    def tearDown(self): self.t.cleanup()
    def correr(self, nombre, contenido):
        p = self.d / nombre; p.write_text(contenido)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = eq.main([str(p)])
        return rc, out.getvalue()
    def v(self, *casos): return [r["veredicto"] for r in eq.evaluar(list(casos))]

    def test_aceptada_y_sin_aceptar(self):
        casos = [caso("A", "3.30", "3.3"), caso("B", "0.99", "1.00", aceptada_motivo="M-001 aprobada"), caso("C", "error 400", "error 422")]
        self.assertEqual(self.v(*casos), ["equivalente", "diferencia aceptada", "diferencia"])
        rc, out = self.correr("c.json", json.dumps(casos)); self.assertEqual(rc, 1); self.assertIn("C: diferencia", out)
        rc, _ = self.correr("d.json", json.dumps(casos[:2])); self.assertEqual(rc, 0)

    def test_motivo_vacio_no_acepta(self):
        self.assertEqual(self.v(caso("A", "1", "2", aceptada_motivo="  ")), ["diferencia"])

    def test_decimales_exactos(self):
        self.assertEqual(self.v(caso("A", "0.1", "0.10000000000000001")), ["diferencia"])  # con float serían iguales
        rc, _ = self.correr("f.json", '[{"id":"A","salida_origen":0.1,"salida_nuevo":0.10000000000000001}]'); self.assertEqual(rc, 1)
        rc, _ = self.correr("g.json", '[{"id":"A","salida_origen":0.30,"salida_nuevo":"0.3"}]'); self.assertEqual(rc, 0)
        self.assertEqual(self.v(caso("A", "0.1", "0.3")), ["diferencia"])

    def test_tolerancia_por_caso(self):
        self.assertEqual(self.v(caso("A", "10.00", "10.01", tolerancia="0.01")), ["equivalente"])
        self.assertEqual(self.v(caso("A", "10.00", "10.02", tolerancia="0.01")), ["diferencia"])
        self.assertEqual(self.v(caso("A", "10.00", "10.01")), ["diferencia"])  # sin tolerancia: exacto
        with self.assertRaises(ValueError): eq.evaluar([caso("A", "1", "1", tolerancia="abc")])

    def test_estructuras_y_texto(self):
        self.assertEqual(self.v(caso("A", {"t": "1.0", "l": [1, 2]}, {"t": 1, "l": [1, 2]})), ["equivalente"])
        self.assertEqual(self.v(caso("A", {"t": 1}, {"t": 1, "x": 2})), ["diferencia"])
        self.assertEqual(self.v(caso("A", "ok", "OK")), ["diferencia"])
        self.assertEqual(self.v(caso("A", "NaN", "nan")), ["diferencia"])

    def test_csv_y_entrada_invalida(self):
        csv_txt = "id,entrada,salida_origen,salida_nuevo,tolerancia,aceptada_motivo\nA,x,1.50,1.5,,\nB,y,2,3,,por diseño\nC,z,5,6,,\n"
        rc, out = self.correr("c.csv", csv_txt); self.assertEqual(rc, 1); self.assertIn("1 equivalentes, 1 diferencias aceptadas, 1 diferencias sin aceptar", out)
        self.assertEqual(self.correr("v.json", "[]")[0], 2)
        self.assertEqual(self.correr("m.json", '[{"id":"A"}]')[0], 2)


if __name__ == "__main__":
    unittest.main()
