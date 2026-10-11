"""Pruebas de la línea base de seguridad: informativa en proyectos existentes, exigida en sistemas nuevos."""
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
_esp = importlib.util.spec_from_file_location("seguridad_base", RAIZ / "herramientas" / "seguridad_base.py")
SB = importlib.util.module_from_spec(_esp)
_esp.loader.exec_module(SB)


def proyecto(archivos):
    d = tempfile.mkdtemp()
    for ruta, texto in archivos.items():
        f = pathlib.Path(d) / ruta
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(texto, encoding="utf-8")
    return d


def evaluar(archivos, versionados=None):
    d = proyecto(archivos)
    return {r["id"]: r for r in SB.evaluar(SB.inventario(d), SB._lector(d), versionados=versionados)["items"]}


class Catalogo(unittest.TestCase):
    def test_hay_20_ids_unicos_y_regex_validas(self):
        items = SB.cargar()
        self.assertEqual([i["id"] for i in items], [f"SEG-{n:02d}" for n in range(1, 21)])
        import re
        for i in items:
            for k in ("archivo", "contenido", "alerta", "ignorado", "versionados", "alerta_en", "alerta_excluye"):
                for rx in i.get(k, []):
                    re.compile(rx)
            self.assertTrue(i["que"] and i["exigencia"])

    def test_cada_item_tiene_alguna_forma_de_detectarse(self):
        for i in SB.cargar():
            self.assertTrue(any(i.get(k) for k in ("archivo", "contenido", "alerta", "ignorado", "versionados")), i["id"])


class Evaluar(unittest.TestCase):
    def test_proyecto_vacio_no_afirma_que_falte_nada_solo_que_no_vio(self):
        r = evaluar({"README.md": "hola"})
        self.assertTrue(all(x["estado"] in ("sin_evidencia", "confirmar") for x in r.values()))
        self.assertEqual(r["SEG-12"]["estado"], "confirmar")      # solo se confirma en ejecución
        self.assertEqual(r["SEG-10"]["estado"], "sin_evidencia")  # verificable leyendo, y no se vio

    def test_evidencia_con_archivo_y_linea(self):
        r = evaluar({"src/main.ts": "import helmet from 'helmet';\napp.use(helmet());\n", "package.json": '{"dependencies":{"bcrypt":"5"}}'})
        self.assertEqual(r["SEG-18"]["estado"], "indicios")  # no verificable leyendo: queda para confirmar
        self.assertTrue(r["SEG-18"]["evidencia"][0].startswith("src/main.ts:1"))
        self.assertEqual(r["SEG-10"]["estado"], "evidencia")

    def test_secreto_en_codigo_es_alerta(self):
        r = evaluar({"src/cfg.ts": "const apiKey = 'abcdef0123456789abcdef0123';\n"})
        self.assertEqual(r["SEG-01"]["estado"], "alerta")
        self.assertIn("src/cfg.ts:1", r["SEG-01"]["alertas"][0])

    def test_env_versionado_es_alerta_solo_si_git_lo_versiona(self):
        arch = {".env": "A=1\n", ".gitignore": ".env\n"}
        self.assertEqual(evaluar(arch, versionados={"README.md"})["SEG-02"]["estado"], "sin_evidencia")
        self.assertEqual(evaluar(arch, versionados={".env"})["SEG-02"]["estado"], "alerta")
        # sin git no se puede afirmar: queda como indicio a comprobar, nunca como alerta
        self.assertNotEqual(evaluar(arch, versionados=None)["SEG-02"]["estado"], "alerta")

    def test_las_pruebas_y_los_md_no_generan_alertas(self):
        r = evaluar({"src/a.spec.ts": "const apiKey = 'abcdef0123456789abcdef0123';", "docs/x.md": "AKIAABCDEFGHIJKLMNOP"})
        self.assertNotEqual(r["SEG-01"]["estado"], "alerta")

    def test_consulta_concatenada_es_alerta_y_la_migracion_no(self):
        r = evaluar({"src/repo.ts": "db.query(`SELECT * FROM t WHERE a = ${valor}`)\n"})
        self.assertEqual(r["SEG-13"]["estado"], "alerta")
        r2 = evaluar({"src/migrations/1.ts": "q.query(`CREATE TABLE t (a varchar(${LARGO}))`)\n"})
        self.assertNotEqual(r2["SEG-13"]["estado"], "alerta")

    def test_clave_de_servicio_solo_alerta_en_el_frontend(self):
        self.assertEqual(evaluar({"frontend/src/app/cfg.ts": "const k = 'service_role';"})["SEG-03"]["estado"], "alerta")
        self.assertNotEqual(evaluar({"backend/src/cfg.ts": "const k = 'service_role';"})["SEG-03"]["estado"], "alerta")

    def test_resumen_cuenta_todo(self):
        d = proyecto({"a.ts": "x"})
        res = SB.evaluar(SB.inventario(d), SB._lector(d))
        self.assertEqual(sum(res["resumen"].values()), 20)


class Adopt(unittest.TestCase):
    def test_el_analisis_de_un_proyecto_existente_lo_marca_sin_imponerlo(self):
        d = proyecto({"README.md": "x", "package.json": '{"name":"a"}', "src/index.ts": "console.log(1)"})
        out = subprocess.run([sys.executable, str(RAIZ / "herramientas" / "harness-detectar.py"), d], capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("Línea base de seguridad (informativa)", out.stdout)
        self.assertIn("No se exige a un proyecto existente", out.stdout)
        # la sección no altera las propuestas ni agrega «Falta» de seguridad base
        self.assertNotIn("SEG-01** falta", out.stdout)


if __name__ == "__main__":
    unittest.main()
