import importlib.util, pathlib, tempfile, unittest, os
H = pathlib.Path(__file__).resolve().parent.parent / "web-detectar-herramienta.py"
spec = importlib.util.spec_from_file_location("webd", H); D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)


class T(unittest.TestCase):
    def test_sin_nada(self):
        r = D.detectar(entorno={}, buscar=lambda n: None)
        self.assertEqual((r["disponible"], r["modo"]), ("no", "manual"))

    def test_od_nativo_no_es_la_herramienta(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "od"; f.write_bytes(b"\x7fELF" + b"0" * 100)
            r = D.detectar(entorno={}, buscar=lambda n: str(f) if n == "od" else None)
            self.assertEqual(r["disponible"], "no")

    def test_script_con_huella_de_open_design(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "od"; f.write_text("#!/usr/bin/env node\nimport '../apps/daemon/bin/od.mjs'\n")
            r = D.detectar(entorno={}, buscar=lambda n: str(f) if n == "od" else None)
            self.assertEqual((r["disponible"], r["modo"]), ("sí", "externo")); self.assertIn("no verificado", r["motivo"])

    def test_script_sin_huella_no_se_asume(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "od"; f.write_text("#!/bin/sh\necho hola\n")
            self.assertEqual(D.detectar(entorno={}, buscar=lambda n: str(f) if n == "od" else None)["disponible"], "no")

    def test_variable_fija_la_herramienta(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "mi-herramienta"; f.write_text("#!/bin/sh\n")
            r = D.detectar(entorno={"HARNESS_WEB_HERRAMIENTA": str(f)}, buscar=lambda n: None)
            self.assertEqual(r["disponible"], "sí")


if __name__ == "__main__":
    unittest.main()
