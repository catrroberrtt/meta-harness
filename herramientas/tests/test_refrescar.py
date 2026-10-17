"""Pruebas de harness-refrescar.py: código contra fichas, informe con el contrato del aviso, espejo de la wiki y búsqueda.

<!-- tipo: herramienta · capa: 4 -->
Todo ocurre en carpetas temporales con repositorios git locales; no hay red ni se toca la configuración real del usuario.
"""
import contextlib, importlib.util, io, json, os, pathlib, subprocess, tempfile, unittest

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
spec = importlib.util.spec_from_file_location("harness_refrescar", RAIZ / "herramientas" / "harness-refrescar.py")
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t"))


def repo_falso(base, nombre, archivos):
    r = base / nombre
    r.mkdir(parents=True)
    git(r, "init", "-q", "-b", "main")
    git(r, "remote", "add", "origin", f"git@example.com:org/{nombre}.git")
    for ruta in archivos:
        p = r / ruta
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "init")
    git(r, "update-ref", "refs/remotes/origin/main", "HEAD")
    return r


class Entorno(unittest.TestCase):
    def setUp(self):
        self.t = pathlib.Path(tempfile.mkdtemp())
        (self.t / "fichas").mkdir()
        (self.t / "fichas" / "pagos.md").write_text("# Pagos\nEl módulo pagos calcula cuotas. Usa el módulo reportes una vez.\n")
        repo_falso(self.t / "codigo", "api-demo", ["src/modules/pagos/a.ts", "src/modules/reportes/a.ts", "src/modules/nuevo/a.ts"])
        repo_falso(self.t / "codigo", "fn-correo", ["main.py"])
        repo_falso(self.t / "codigo", "otro-repo", ["main.py"])
        self.cfg = self.t / "refresco.toml"
        self.cfg.write_text(f"""
[conocimiento]
raiz = "{self.t}/fichas"
salida = "{self.t}/novedades.md"
espejo = "{self.t}/espejo"
estado = "{self.t}/estado.json"
[codigo]
raiz = "{self.t}/codigo"
profundidad = 2
remoto = "example\\\\.com[:/]org/"
ramas = ["origin/qas", "origin/main"]
[[codigo.reglas]]
repo = "^api-"
tipo = "módulo"
modo = "subcarpetas"
ruta = "src/modules"
[[codigo.reglas]]
repo = "^fn-"
tipo = "función"
modo = "repo"
""")

    def correr(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = rf.main(["--config", str(self.cfg), *args])
        return rc, out.getvalue()


class TestCodigo(Entorno):
    def test_clasifica_por_menciones_y_respeta_las_reglas(self):
        rc, salida = self.correr("--sin-red")
        self.assertEqual(rc, 0)
        md = (self.t / "novedades.md").read_text()
        sin = md.split("## Código sin ficha (0 menciones)")[1].split("## ")[0]
        poco = md.split("## Código casi sin ficha (1 mención)")[1].split("## ")[0]
        self.assertIn("`nuevo`", sin)
        self.assertIn("`fn-correo`", sin)
        self.assertNotIn("otro-repo", md)  # sin regla no cuenta
        self.assertNotIn("`pagos`", sin)
        self.assertIn("`reportes`", poco)
        self.assertIn("código: 2 sin ficha, 1 con 1 mención", salida)

    def test_el_informe_cumple_el_contrato_del_aviso(self):
        self.correr("--sin-red")
        md = (self.t / "novedades.md").read_text().splitlines()
        self.assertTrue(any(l.startswith("## ") for l in md))
        # las secciones vacías no deben contar como pendiente: no usan viñeta
        vacia = next(i for i, l in enumerate(md) if l.startswith("## Páginas de la wiki"))
        self.assertEqual(md[vacia + 2], "_(ninguno)_")

    def test_simulacro_no_escribe_nada(self):
        rc, salida = self.correr("--sin-red", "--simulacro")
        self.assertEqual(rc, 0)
        self.assertFalse((self.t / "novedades.md").exists())
        self.assertFalse((self.t / "estado.json").exists())
        self.assertIn("simulacro", salida)

    def test_sin_configuracion_avisa_con_claridad(self):
        with self.assertRaises(SystemExit) as e:
            rf.main(["--config", str(self.t / "no-existe.toml")])
        self.assertIn("Falta la configuración", str(e.exception))


class FalsaWiki:
    def __init__(self):
        self.pedidos = []

    def get(self, ruta):
        self.pedidos.append(ruta)
        if "/content/search" in ruta:
            return {"results": [{"id": "11", "title": "Cierre del mes", "version": {"number": 3}, "space": {"key": "OPS"}}]}
        if "/pages/11" in ruta:
            return {"body": {"storage": {"value": "<h2>Pasos</h2><p>Cerrar caja</p><ul><li>uno</li></ul>"}}}
        return None


class TestWiki(Entorno):
    def test_baja_la_pagina_y_no_repite_si_la_version_no_cambio(self):
        espejo = self.t / "espejo"
        api, ultimo = FalsaWiki(), {}
        indice, nuevos = rf.parte_wiki(api, espejo, ultimo, 7, 200)
        self.assertEqual(nuevos, ["11"])
        texto = (espejo / "wiki" / "11.md").read_text()
        self.assertIn("## Pasos", texto)
        self.assertIn("- uno", texto)
        self.assertIn("espacio OPS", texto)
        self.assertIn("wiki_desde", ultimo)
        _, otra_vez = rf.parte_wiki(FalsaWiki(), espejo, {}, 7, 200)
        self.assertEqual(otra_vez, [])

    def test_buscar_en_el_espejo(self):
        espejo = self.t / "espejo"
        rf.parte_wiki(FalsaWiki(), espejo, {}, 7, 200)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rf.buscar(espejo, "cerrar caja")
        self.assertIn("Cierre del mes", out.getvalue())

    def test_pagina_citada_en_las_fichas_no_aparece_como_novedad(self):
        self.assertTrue(rf.citada("Cierre del mes", "11", "texto del cierre del mes completo"))
        self.assertFalse(rf.citada("Otra cosa", "99", "nada que ver"))


if __name__ == "__main__":
    unittest.main()
