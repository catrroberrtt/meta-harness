"""Pruebas de harness-sincronizar.py: commit, traer y subir con compuerta, sin subir nunca otra cosa que la rama indicada.

<!-- tipo: herramienta · capa: 4 -->
Todo en repositorios temporales con un remoto local desnudo; no usa red ni toca el repositorio real.
"""
import contextlib, importlib.util, io, json, os, pathlib, subprocess, tempfile, unittest

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
spec = importlib.util.spec_from_file_location("harness_sincronizar", RAIZ / "herramientas" / "harness-sincronizar.py")
sy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sy)

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


def g(cwd, *a):
    r = subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, env=ENV)
    return r.stdout.strip()


def correr(*argv):
    sal, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(sal), contextlib.redirect_stderr(err):
        codigo = sy.main(list(argv))
    return codigo, sal.getvalue(), err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        t = pathlib.Path(self.t.name)
        self.remoto = t / "remoto.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.remoto)], check=True)
        self.w = t / "trabajo"
        subprocess.run(["git", "clone", "-q", str(self.remoto), str(self.w)], check=True, capture_output=True)
        g(self.w, "checkout", "-q", "-b", "main")
        (self.w / "README.md").write_text("# Demo\n\nTexto inicial.\n", encoding="utf8")
        g(self.w, "add", "-A")
        g(self.w, "commit", "-q", "-m", "inicial")
        g(self.w, "push", "-q", "-u", "origin", "main")
        self.lista = t / "prohibidos.txt"
        self.lista.write_text("# términos\nzafiro\n", encoding="utf8")
        self.viejo = {k: os.environ.get(k) for k in ("HARNESS_PROHIBIDOS", "HARNESS_CACHE")}
        os.environ["HARNESS_PROHIBIDOS"] = str(self.lista)
        os.environ["HARNESS_CACHE"] = str(t / "cache")
        sy.CACHE = pathlib.Path(os.environ["HARNESS_CACHE"]) / "sync-gate.json"
        self.addCleanup(self.restaurar)

    def restaurar(self):
        for k, v in self.viejo.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def sync(self, *extra, verificador=""):
        return correr("--raiz", str(self.w), "--verificador", verificador, *extra)

    def remoto_head(self):
        return g(self.remoto, "rev-parse", "main")

    def verificador(self, exit_code):
        v = pathlib.Path(self.t.name) / f"verif{exit_code}.sh"
        v.write_text(f"#!/usr/bin/env bash\nexit {exit_code}\n", encoding="utf8")
        return str(v)


class Flujo(Base):
    def test_sin_cambios_no_hace_nada(self):
        c, out, _ = self.sync()
        self.assertEqual(c, 0)
        self.assertIn("nada que sincronizar", out)

    def test_cambio_limpio_se_commitea_y_se_sube(self):
        (self.w / "docs.md").write_text("# Guía\n\nNada sensible aquí.\n", encoding="utf8")
        c, out, err = self.sync()
        self.assertEqual(c, 0, err)
        self.assertEqual(g(self.w, "rev-parse", "HEAD"), self.remoto_head())
        self.assertIn("chore(auto-sync)", g(self.w, "log", "-1", "--format=%s"))
        self.assertEqual(g(self.w, "status", "--porcelain"), "")

    def test_solo_compuerta_no_commitea_ni_sube(self):
        (self.w / "docs.md").write_text("# Guía\n\nTexto.\n", encoding="utf8")
        antes, local = self.remoto_head(), g(self.w, "rev-parse", "HEAD")
        c, out, _ = self.sync("--solo-compuerta")
        self.assertEqual(c, 0)
        self.assertIn("la compuerta de publicación pasa", out)
        self.assertEqual(self.remoto_head(), antes)
        self.assertEqual(g(self.w, "rev-parse", "HEAD"), local)

    def test_simulacro_no_escribe(self):
        (self.w / "docs.md").write_text("x\n", encoding="utf8")
        antes = self.remoto_head()
        c, out, _ = self.sync("--simulacro")
        self.assertEqual(c, 0)
        self.assertIn("simulacro", out)
        self.assertEqual(self.remoto_head(), antes)
        self.assertNotEqual(g(self.w, "status", "--porcelain"), "")

    def test_otra_rama_no_se_sincroniza(self):
        g(self.w, "checkout", "-q", "-b", "trabajo-largo")
        (self.w / "x.md").write_text("x\n", encoding="utf8")
        antes = self.remoto_head()
        c, out, _ = self.sync()
        self.assertEqual(c, 0)
        self.assertIn("no se sincroniza", out)
        self.assertEqual(self.remoto_head(), antes)

    def test_nunca_sube_otras_ramas_ni_etiquetas(self):
        g(self.w, "branch", "historial-local")
        g(self.w, "tag", "v9.9.9")
        (self.w / "docs.md").write_text("# Guía\n\nTexto.\n", encoding="utf8")
        c, _, err = self.sync()
        self.assertEqual(c, 0, err)
        ramas = g(self.remoto, "branch", "--list")
        self.assertNotIn("historial-local", ramas)
        self.assertEqual(g(self.remoto, "tag", "--list"), "")


class Compuerta(Base):
    def test_verificador_que_falla_bloquea(self):
        (self.w / "docs.md").write_text("# Guía\n\nTexto.\n", encoding="utf8")
        antes, local = self.remoto_head(), g(self.w, "rev-parse", "HEAD")
        c, _, err = self.sync(verificador=self.verificador(1))
        self.assertEqual(c, 1)
        self.assertIn("verificar.sh falló", err)
        self.assertEqual(self.remoto_head(), antes)
        self.assertEqual(g(self.w, "rev-parse", "HEAD"), local, "no se commitea si la compuerta falla")

    def test_termino_prohibido_bloquea(self):
        (self.w / "docs.md").write_text("# Guía\n\nEl cliente zafiro pidió esto.\n", encoding="utf8")
        antes = self.remoto_head()
        c, _, err = self.sync()
        self.assertEqual(c, 1)
        self.assertIn("escaneo de publicación", err)
        self.assertEqual(self.remoto_head(), antes)

    def test_sin_lista_de_prohibidos_no_se_publica(self):
        self.lista.unlink()
        (self.w / "docs.md").write_text("# Guía\n\nTexto.\n", encoding="utf8")
        antes = self.remoto_head()
        c, _, err = self.sync()
        self.assertEqual(c, 1)
        self.assertIn("lista de términos prohibidos", err)
        self.assertEqual(self.remoto_head(), antes)

    def test_un_secreto_bloquea(self):
        (self.w / "cfg.md").write_text("# Cfg\n\nclave: AKIAABCDEFGHIJKLMNOP\n", encoding="utf8")  # escaneo-publico: ignorar (dato falso de prueba)
        antes = self.remoto_head()
        c, _, _ = self.sync()
        self.assertEqual(c, 1)
        self.assertEqual(self.remoto_head(), antes)

    def test_silencioso_avisa_con_json_y_sale_0(self):
        (self.w / "docs.md").write_text("# Guía\n\nEl cliente zafiro.\n", encoding="utf8")
        c, out, _ = self.sync("--silencioso")
        self.assertEqual(c, 0)
        self.assertIn("systemMessage", json.loads(out))

    def test_el_resultado_de_la_compuerta_se_reutiliza_si_nada_cambia(self):
        (self.w / "docs.md").write_text("# Guía\n\nTexto.\n", encoding="utf8")
        self.sync("--sin-subir")
        # mismo contenido: la compuerta no vuelve a correr; un verificador que falla ya no importa
        c, _, _ = self.sync(verificador=self.verificador(1))
        self.assertEqual(c, 0)


class Remoto(Base):
    def otro_clon(self):
        o = pathlib.Path(self.t.name) / "otro"
        subprocess.run(["git", "clone", "-q", str(self.remoto), str(o)], check=True, capture_output=True)
        g(o, "checkout", "-q", "main")
        return o

    def test_trae_lo_remoto_antes_de_subir(self):
        o = self.otro_clon()
        (o / "remoto.md").write_text("# R\n\nDesde otra máquina.\n", encoding="utf8")
        g(o, "add", "-A"); g(o, "commit", "-q", "-m", "otra máquina"); g(o, "push", "-q", "origin", "main")
        (self.w / "local.md").write_text("# L\n\nLocal.\n", encoding="utf8")
        c, _, err = self.sync()
        self.assertEqual(c, 0, err)
        self.assertTrue((self.w / "remoto.md").is_file())
        self.assertEqual(g(self.w, "rev-parse", "HEAD"), self.remoto_head())

    def test_conflicto_aborta_y_no_sube(self):
        o = self.otro_clon()
        (o / "README.md").write_text("# Demo\n\nVersión remota.\n", encoding="utf8")
        g(o, "add", "-A"); g(o, "commit", "-q", "-m", "remoto"); g(o, "push", "-q", "origin", "main")
        antes = self.remoto_head()
        (self.w / "README.md").write_text("# Demo\n\nVersión local.\n", encoding="utf8")
        c, _, err = self.sync()
        self.assertEqual(c, 1)
        self.assertIn("conflicto", err)
        self.assertEqual(self.remoto_head(), antes)
        self.assertEqual(g(self.w, "status", "--porcelain"), "", "el merge se abortó limpio")


class Sellos(Base):
    """Cada commit automático anota el árbol sobre el que pasó la compuerta; si el contenido cambia después, el sello se rompe."""

    def automatico(self):
        (self.w / "nota.md").write_text("Contenido que pasa la compuerta.\n", encoding="utf8")
        c, _, _ = self.sync()
        self.assertEqual(c, 0)

    def test_el_commit_automatico_lleva_sello_con_el_arbol(self):
        self.automatico()
        cuerpo = g(self.w, "log", "-1", "--format=%B")
        arbol = g(self.w, "rev-parse", "HEAD^{tree}")
        self.assertIn("Compuerta: compuerta de publicación OK", cuerpo)
        self.assertIn(f"Arbol: {arbol}", cuerpo)

    def test_comprobar_sellos_da_sellado_y_codigo_cero(self):
        self.automatico()
        filas, codigo = sy.comprobar_sellos(self.w)
        self.assertEqual(codigo, 0)
        self.assertEqual(filas[0][0], "SELLADO")

    def test_cambiar_el_contenido_despues_rompe_el_sello(self):
        self.automatico()
        (self.w / "nota.md").write_text("Contenido cambiado DESPUÉS de la compuerta.\n", encoding="utf8")
        g(self.w, "add", "-A")
        g(self.w, "commit", "-q", "--amend", "-C", "HEAD")  # conserva el mensaje con el sello, pero el árbol es otro
        filas, codigo = sy.comprobar_sellos(self.w)
        self.assertEqual(codigo, 1)
        self.assertEqual(filas[0][0], "SELLO ROTO")

    def test_un_commit_automatico_sin_sello_se_senala_sin_romper(self):
        (self.w / "x.md").write_text("x\n", encoding="utf8")
        g(self.w, "add", "-A")
        g(self.w, "commit", "-q", "-m", "chore(auto-sync): 1 archivo(s) · hecho a mano sin pasar por la compuerta")
        filas, codigo = sy.comprobar_sellos(self.w)
        self.assertEqual(filas[0][0], "SIN SELLO")
        self.assertEqual(codigo, 0)

    def test_commits_manuales_no_se_juzgan(self):
        (self.w / "x.md").write_text("x\n", encoding="utf8")
        g(self.w, "add", "-A")
        g(self.w, "commit", "-q", "-m", "docs: trabajo manual")
        self.assertEqual(sy.comprobar_sellos(self.w), ([], 0))

    def test_sello_falsificado_con_arbol_inventado_se_detecta(self):
        (self.w / "x.md").write_text("x\n", encoding="utf8")
        g(self.w, "add", "-A")
        g(self.w, "commit", "-q", "-m", "chore(auto-sync): 1 archivo(s)\n\nCompuerta: compuerta de publicación OK\nArbol: " + "a" * 40)
        filas, codigo = sy.comprobar_sellos(self.w)
        self.assertEqual((filas[0][0], codigo), ("SELLO ROTO", 1))

    def test_comando_de_linea(self):
        self.automatico()
        c, salida, _ = correr("--raiz", str(self.w), "--comprobar-sellos", "5")
        self.assertEqual(c, 0)
        self.assertIn("SELLADO", salida)


if __name__ == "__main__":
    unittest.main()
