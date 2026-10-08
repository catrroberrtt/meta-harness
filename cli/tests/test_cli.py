"""Pruebas del comando `harness` (asistente, doctor, estado, instalar). Todo en carpetas temporales; sin red, sin git de escritura."""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "cli"))
sys.dont_write_bytecode = True
import harness_cli as hc  # noqa: E402

CLI = RAIZ / "cli" / "harness"


def arbol_hash(carpeta):
    h = hashlib.sha256()
    for p in sorted(Path(carpeta).rglob("*")):
        h.update(str(p.relative_to(carpeta)).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def archivos(carpeta):
    return sorted(str(p.relative_to(carpeta)) for p in Path(carpeta).rglob("*") if p.is_file())


class Entrada:
    """input() simulado: devuelve respuestas en orden; al agotarse lanza `al_final` (EOFError o KeyboardInterrupt)."""

    def __init__(self, respuestas, al_final=EOFError):
        self.respuestas, self.al_final, self.prompts = list(respuestas), al_final, []

    def __call__(self, prompt=""):
        self.prompts.append(prompt)
        if not self.respuestas:
            raise self.al_final()
        r = self.respuestas.pop(0)
        if isinstance(r, type) and issubclass(r, BaseException):
            raise r()
        return r


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mh-cli-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.vacia = self.tmp / "nuevo"
        self.vacia.mkdir()
        (self.vacia / "README.md").write_text("# idea de producto\n", encoding="utf8")
        self.inst = self.tmp / "nuevo-harness"

    def correr(self, argv, respuestas=(), interactivo=True, al_final=EOFError):
        ent = Entrada(respuestas, al_final)
        buf = StringIO()
        codigo = hc.main(list(argv), entrada=ent, salida=buf, interactivo=interactivo)
        return codigo, buf.getvalue(), ent

    def asistente_b(self, respuestas, extra=(), **kw):
        return self.correr(["--carpeta", str(self.vacia), *extra], respuestas, **kw)


class TestDeteccion(Base):
    def test_a_codigo_y_historial(self):
        p = self.tmp / "app"
        (p / "src").mkdir(parents=True)
        (p / "src" / "main.py").write_text("print(1)\n")
        (p / "package.json").write_text("{}")
        (p / ".git").mkdir()
        with mock.patch.object(hc, "contar_commits", return_value=57):
            d = hc.detectar_caso(p)
        self.assertEqual((d["caso"], d["confianza"]), ("A", "alta"))
        self.assertIn("código", d["porque"])
        self.assertIn("57 commits", d["porque"])
        self.assertTrue(any("57 commits" in l for l in d["miro"]))

    def test_a_solo_base_o_manifiesto(self):
        p = self.tmp / "solo-manifiesto"
        p.mkdir()
        (p / "pyproject.toml").write_text("[project]\nname='x'\n")
        self.assertEqual(hc.detectar_caso(p)["caso"], "A")

    def test_b_vacia_y_casi_vacia(self):
        vacia = self.tmp / "vacia"
        vacia.mkdir()
        d = hc.detectar_caso(vacia)
        self.assertEqual((d["caso"], d["confianza"]), ("B", "alta"))
        self.assertIn("vacía o casi vacía", d["porque"])
        d = hc.detectar_caso(self.vacia)
        self.assertEqual((d["caso"], d["confianza"]), ("B", "alta"))

    def test_c_origen_declarado_por_carpeta(self):
        p = self.tmp / "replica"
        (p / "origen").mkdir(parents=True)
        (p / "origen" / "esquema.sql").write_text("CREATE TABLE t (id INT);\n")
        d = hc.detectar_caso(p)
        self.assertEqual((d["caso"], d["confianza"]), ("C", "alta"))
        self.assertIn("origen declarado", d["porque"])

    def test_c_origen_declarado_en_acceso(self):
        p = self.tmp / "replica2"
        p.mkdir()
        (p / "acceso.local.toml").write_text('[origen]\nmetodo = "descripcion"\nruta = "/algun/sitio"\n')
        d = hc.detectar_caso(p)
        self.assertEqual(d["caso"], "C")
        self.assertTrue(any("/algun/sitio" in l for l in d["miro"]))

    def test_volcado_sql_sin_codigo_es_duda(self):
        p = self.tmp / "volcado"
        p.mkdir()
        for i in range(4):
            (p / f"t{i}.sql").write_text("CREATE TABLE a (id INT);\n")
        d = hc.detectar_caso(p)
        self.assertEqual((d["caso"], d["confianza"]), ("C", "duda"))

    def test_explica_que_miro_en_la_salida(self):
        c, out, _ = self.asistente_b([EOFError], interactivo=False)
        self.assertIn("Qué miré", out)
        self.assertIn("Archivos visibles", out)
        self.assertIn("Conclusión: caso B", out)

    def test_duda_se_pregunta_con_se_intento(self):
        p = self.tmp / "dudosa"
        p.mkdir()
        for i in range(4):
            (p / f"t{i}.sql").write_text("CREATE TABLE a (id INT);\n")
        ent = Entrada(["B", EOFError])
        buf = StringIO()
        hc.main(["--carpeta", str(p)], entrada=ent, salida=buf, interactivo=True)
        out = buf.getvalue()
        self.assertIn("Pregunta 1: ¿Qué caso es?", out)
        self.assertIn("Se intentó:", out)
        self.assertIn("mejor suposición es C", out)

    def test_duda_sin_terminal_no_adivina(self):
        p = self.tmp / "dudosa2"
        p.mkdir()
        (p / "a.sql").write_text("CREATE TABLE a (id INT);\n")
        (p / "b.sql").write_text("CREATE TABLE b (id INT);\n")
        (p / "c.sql").write_text("CREATE TABLE c (id INT);\n")
        (p / "d.sql").write_text("CREATE TABLE d (id INT);\n")
        antes = arbol_hash(self.tmp)
        buf = StringIO()
        c = hc.main(["--carpeta", str(p), "--si"], salida=buf, interactivo=False)
        self.assertEqual(c, 2)
        self.assertIn("--caso", buf.getvalue())
        self.assertEqual(antes, arbol_hash(self.tmp))


class TestFlujoInteractivo(Base):
    def test_una_pregunta_por_vez_con_se_intento(self):
        c, out, ent = self.asistente_b(["", "", "", "n"])
        self.assertEqual(c, 0, out)
        preguntas = [l for l in out.splitlines() if l.startswith("Pregunta ")]
        self.assertEqual(len(preguntas), 3)
        self.assertEqual(out.count("  Se intentó:"), 3)
        # cada pregunta lee exactamente una respuesta (3 preguntas + la confirmación)
        self.assertEqual(len(ent.prompts), 4)
        # orden: pregunta, intento, respuesta
        pos = [out.index(f"Pregunta {i}:") for i in (1, 2, 3)]
        self.assertEqual(pos, sorted(pos))
        self.assertIn("Lo que entendí, lo que falta y lo que haré", out)
        self.assertIn("¿Lo aplico? [s/N]", out)

    def test_sin_responder_s_no_escribe_la_instancia(self):
        for resp in ("n", "", "no"):
            shutil.rmtree(self.inst, ignore_errors=True)
            c, out, _ = self.asistente_b(["", "", "", resp])
            self.assertEqual(c, 0)
            self.assertIn("No apliqué nada", out)
            self.assertFalse((self.inst / "harness.lock").exists())
            self.assertEqual(archivos(self.inst), [".harness/sesion.json"])      # solo el avance, sin secretos
        self.assertEqual(archivos(self.vacia), ["README.md"])                   # las entradas jamás se tocan

    def test_con_s_crea_la_instancia(self):
        c, out, _ = self.asistente_b(["", "", "", "s"])
        self.assertEqual(c, 0, out)
        for r in ("harness.lock", "politicas.toml", "convenciones.toml", ".harness/estado.json", ".harness/piso.md"):
            self.assertTrue((self.inst / r).exists(), r)
        self.assertIn("Aplicado:", out)
        ses = json.loads((self.inst / ".harness" / "sesion.json").read_text())
        self.assertEqual(ses["estado"], "terminada")
        self.assertEqual(archivos(self.vacia), ["README.md"])

    def test_ctrl_c_antes_de_elegir_instancia_no_escribe_nada(self):
        antes = arbol_hash(self.tmp)
        c, out, _ = self.asistente_b([""], al_final=KeyboardInterrupt)
        self.assertEqual(c, 130)
        self.assertIn("No se instaló nada", out)
        self.assertEqual(antes, arbol_hash(self.tmp))

    def test_ctrl_c_o_eof_a_mitad_no_deja_instancia_a_medias(self):
        for fin in (KeyboardInterrupt, EOFError):
            shutil.rmtree(self.inst, ignore_errors=True)
            c, out, _ = self.asistente_b(["", ""], al_final=fin)       # entradas + instancia; corta en «notas»
            self.assertIn(c, (130, 1))
            self.assertIn("No se instaló nada", out)
            self.assertEqual(archivos(self.inst), [".harness/sesion.json"])
            self.assertFalse((self.inst / "harness.lock").exists())

    def test_retomar_conserva_respuestas_y_no_reprgunta(self):
        c, _, _ = self.asistente_b(["", "", KeyboardInterrupt])
        self.assertEqual(c, 130)
        ses = json.loads((self.inst / ".harness" / "sesion.json").read_text())
        self.assertEqual(ses["respuestas"]["instancia"], str(self.inst))
        self.assertIn("entradas", ses["respuestas"])
        c, out, ent = self.asistente_b(["s", "", "s"])        # continuar, notas, aplicar
        self.assertEqual(c, 0, out)
        self.assertIn("Encontré una sesión sin terminar", out)
        self.assertIn("Ya respondido antes", out)
        self.assertEqual(out.count("Pregunta "), 1)           # solo «notas»; entradas e instancia no se repiten
        self.assertTrue((self.inst / "harness.lock").exists())

    def test_retomar_diciendo_no_empieza_de_nuevo(self):
        self.asistente_b(["", "", KeyboardInterrupt])
        c, out, _ = self.asistente_b(["n", "", "", "", "n"])
        self.assertEqual(out.count("Pregunta "), 3)

    def test_sesion_nunca_guarda_secretos(self):
        falso = "hunter2-CLAVE-FALSA"
        c, out, _ = self.asistente_b(["", "", f"mi password es {falso}", "n"])
        self.assertEqual(c, 0, out)
        self.assertIn("parece un secreto", out)
        for f in self.inst.rglob("*"):
            if f.is_file():
                self.assertNotIn(falso, f.read_text(errors="ignore"), f)
        ses = json.loads((self.inst / ".harness" / "sesion.json").read_text())
        self.assertNotIn("notas", ses["respuestas"])
        self.assertIn("notas", ses["omitidas"])
        # una URL con usuario y clave tampoco se guarda
        shutil.rmtree(self.inst)
        self.asistente_b(["", "", "https://usuario:clave123@host/x", "n"])
        self.assertNotIn("clave123", (self.inst / ".harness" / "sesion.json").read_text())

    def test_sin_entradas_no_empieza_y_dice_que_falta(self):
        vacia = self.tmp / "hueca"
        vacia.mkdir()
        c, out, _ = self.correr(["--carpeta", str(vacia)], [""])
        self.assertEqual(c, 2)
        self.assertIn("Sin la información de partida no empiezo", out)
        self.assertIn("--documentacion", out)

    def test_caso_a_sin_accesos_se_detiene_diciendo_que_pedir(self):
        p = self.tmp / "app"
        p.mkdir()
        (p / "main.py").write_text("print(1)\n")
        antes = arbol_hash(p)
        c, out, _ = self.correr(["--carpeta", str(p)], ["", "", "", ""])      # instancia por defecto; sin acceso, sin política, sin notas
        self.assertEqual(c, 2, out)
        self.assertIn("No puedo orquestar todavía", out)
        self.assertIn("ningún ambiente de datos", out)
        self.assertIn("No instalo nada", out)
        self.assertEqual(antes, arbol_hash(p))                         # el proyecto no se toca
        self.assertFalse((self.tmp / "app-harness" / "harness.lock").exists())

    def test_caso_c_replica_y_crea_registro_de_mejoras(self):
        p = self.tmp / "replica"
        (p / "origen").mkdir(parents=True)
        (p / "origen" / "esquema.sql").write_text("CREATE TABLE cliente (id INT PRIMARY KEY, nombre VARCHAR(40));\n")
        c, out, _ = self.correr(["--carpeta", str(p)], ["", "", "", "s"])
        self.assertEqual(c, 0, out)
        self.assertIn("caso C", out)
        inst = self.tmp / "replica-harness"
        self.assertTrue((inst / "mejoras.md").exists() or (p / "mejoras.md").exists())
        self.assertTrue((inst / "harness.lock").exists() or (p / "harness.lock").exists())


class TestSinInterfaz(Base):
    def test_sin_terminal_muestra_el_plan_y_sale_sin_escribir(self):
        antes = arbol_hash(self.tmp)
        c, out, ent = self.asistente_b([], interactivo=False)
        self.assertEqual(c, 0, out)
        self.assertEqual(ent.prompts, [])                               # no pregunta
        self.assertIn("Plan del instalador", out)
        self.assertIn("[crear] harness.lock", out)
        self.assertIn("sin escribir", out)
        self.assertEqual(antes, arbol_hash(self.tmp))

    def test_no_interactivo_aunque_haya_terminal(self):
        c, out, ent = self.asistente_b([], ["--no-interactivo"], interactivo=True)
        self.assertEqual((c, ent.prompts), (0, []))
        self.assertFalse(self.inst.exists())

    def test_json(self):
        antes = arbol_hash(self.tmp)
        c, out, _ = self.asistente_b([], ["--json"], interactivo=True)
        d = json.loads(out)
        self.assertEqual((c, d["caso"], d["modo"], d["aplicado"]), (0, "B", "init", False))
        self.assertIn("harness.lock", d["plan"])
        self.assertEqual(antes, arbol_hash(self.tmp))

    def test_si_aplica_y_segunda_corrida_es_identica(self):
        c, out, _ = self.asistente_b([], ["--si"], interactivo=False)
        self.assertEqual(c, 0, out)
        self.assertTrue((self.inst / "harness.lock").exists())
        # sin terminal no se guarda sesión
        self.assertFalse((self.inst / ".harness" / "sesion.json").exists())
        h1 = arbol_hash(self.tmp)
        c2, out2, _ = self.asistente_b([], ["--si"], interactivo=False)
        self.assertEqual(c2, 0, out2)
        self.assertEqual(h1, arbol_hash(self.tmp))
        # y en modo plan, tampoco cambia nada
        c3, _, _ = self.asistente_b([], interactivo=False)
        self.assertEqual((c3, h1), (0, arbol_hash(self.tmp)))

    def test_sin_color_si_no_es_terminal(self):
        c, out, _ = self.asistente_b([], interactivo=False)
        self.assertNotIn("\033[", out)
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            class Falso(StringIO):
                def isatty(self):
                    return True
            self.assertFalse(hc.Salida(Falso()).color)
        with mock.patch.dict(os.environ, {"TERM": "xterm"}, clear=False):
            os.environ.pop("NO_COLOR", None)
            class Falso2(StringIO):
                def isatty(self):
                    return True
            self.assertTrue(hc.Salida(Falso2()).color)


class FalsoHarness(Base):
    """Un harness mínimo (VERSION + las dos herramientas que usa doctor) para probar doctor sin depender del real."""

    def setUp(self):
        super().setUp()
        self.h = self.tmp / "h"
        (self.h / "instalador").mkdir(parents=True)
        (self.h / "herramientas").mkdir()
        (self.h / "VERSION").write_text("1.2.0\n")
        shutil.copy(RAIZ / "instalador" / "comprobar-version.py", self.h / "instalador")
        shutil.copy(RAIZ / "herramientas" / "harness-frescura.py", self.h / "herramientas")
        (self.h / "doc.md").write_text("<!-- tipo: guia -->\n<!-- revisado: 2099-01-01 · vence: 90d · fuente: prueba -->\n# doc\n")
        self.i = self.tmp / "instancia"
        self.i.mkdir()
        (self.i / "harness.lock").write_text('version = "1.2.0"\nfuente = "local"\n')

    def doctor(self, *extra):
        buf = StringIO()
        c = hc.main(["doctor", str(self.i), "--harness", str(self.h), *extra], salida=buf)
        return c, buf.getvalue()


class TestDoctor(FalsoHarness):
    def test_sin_problemas(self):
        c, out = self.doctor()
        self.assertEqual(c, 0, out)
        self.assertIn("RESULTADO: todo bien", out)
        self.assertIn("Herramienta requerida presente: git", out)
        self.assertIn("Herramienta opcional gh", out)

    def test_lock_atrasado_sugiere_update(self):
        (self.i / "harness.lock").write_text('version = "1.0.0"\nfuente = "local"\n')
        c, out = self.doctor()
        self.assertEqual(c, 1)
        self.assertIn("PROBLEMA", out)
        self.assertIn("harness update", out)

    def test_documento_vencido(self):
        (self.h / "viejo.md").write_text("<!-- tipo: guia -->\n<!-- revisado: 2020-01-01 · vence: 30d · fuente: x -->\n")
        c, out = self.doctor()
        self.assertEqual(c, 1)
        self.assertIn("viejo.md", out)
        self.assertIn("Qué hacer", out)

    def test_herramienta_requerida_ausente(self):
        real = shutil.which
        with mock.patch.object(hc.shutil, "which", lambda n: None if n == "git" else real(n)):
            c, out = self.doctor()
        self.assertEqual(c, 1)
        self.assertIn("Falta la herramienta requerida: git", out)

    def test_opcional_ausente_solo_se_informa(self):
        real = shutil.which
        with mock.patch.object(hc.shutil, "which", lambda n: None if n == "gh" else real(n)):
            c, out = self.doctor()
        self.assertEqual(c, 0)
        self.assertIn("Herramienta opcional gh: no está", out)

    def test_acceso_con_aspecto_de_secreto_no_imprime_el_valor(self):
        (self.i / "acceso.local.toml").write_text('[nube]\nmetodo = "claves_entorno"\ntoken = "valor-que-no-debe-salir"\n')
        c, out = self.doctor()
        self.assertEqual(c, 1)
        self.assertIn("nube.token", out)
        self.assertNotIn("valor-que-no-debe-salir", out)

    def test_acceso_limpio_pasa(self):
        (self.i / "acceso.local.toml").write_text('[nube]\nmetodo = "perfil_sso"\nperfil = "mi-perfil"\n[documentacion]\nmetodo = "carpeta_repo"\n')
        c, out = self.doctor()
        self.assertEqual(c, 0, out)

    def test_json(self):
        c, out = self.doctor("--json")
        self.assertEqual(c, 0)
        self.assertTrue(all(f["nivel"] in ("ok", "info", "problema") for f in json.loads(out)))

    def test_segunda_corrida_identica(self):
        self.assertEqual(self.doctor(), self.doctor())


class TestEstadoInstalarUpdate(Base):
    def instalar(self):
        c, out, _ = self.asistente_b([], ["--si"], interactivo=False)
        self.assertEqual(c, 0, out)

    def test_estado(self):
        self.instalar()
        buf = StringIO()
        c = hc.main(["estado", str(self.inst)], salida=buf)
        out = buf.getvalue()
        self.assertEqual(c, 0, out)
        self.assertIn("Modo: init (partida B)", out)
        self.assertIn("Piso (spec 7.2)", out)
        self.assertIn("Pendiente:", out)
        (self.inst / "politicas.toml").write_text("# cambiada\n")
        buf = StringIO()
        hc.main(["estado", str(self.inst)], salida=buf)
        self.assertIn("politicas.toml (modificado localmente)", buf.getvalue())

    def test_estado_de_carpeta_que_no_es_instancia(self):
        buf = StringIO()
        c = hc.main(["estado", str(self.vacia)], salida=buf)
        self.assertEqual(c, 1)
        self.assertIn("no es una instancia", buf.getvalue())

    def test_update_plan_y_aplicar(self):
        self.instalar()
        h = arbol_hash(self.inst)
        buf = StringIO()
        c = hc.main(["update", str(self.inst)], salida=buf)
        self.assertEqual(c, 0, buf.getvalue())
        self.assertEqual(h, arbol_hash(self.inst))
        c = hc.main(["update", str(self.inst), "--aplicar"], salida=StringIO())
        self.assertEqual(c, 0)
        h2 = arbol_hash(self.inst)       # puede refrescar .harness/piso.md (ya no hay acceso declarado); lo demás no cambia
        hc.main(["update", str(self.inst), "--aplicar"], salida=StringIO())
        self.assertEqual(h2, arbol_hash(self.inst))

    def test_instalar_local_delega_en_el_instalador_y_solo_planea(self):
        destino = self.tmp / "otra"
        buf = StringIO()
        c = hc.main(["instalar", str(destino), "--partida", "B", "--acceso", str(self._acceso())], salida=buf)
        self.assertEqual(c, 0, buf.getvalue())
        self.assertIn("NO se escribio nada", buf.getvalue())
        self.assertFalse(destino.exists())
        c = hc.main(["instalar", str(destino), "--partida", "B", "--acceso", str(self._acceso()), "--aplicar"], salida=StringIO())
        self.assertEqual(c, 0)
        self.assertTrue((destino / "harness.lock").exists())

    def _acceso(self):
        a = self.tmp / "acc.toml"
        a.write_text(f'[documentacion]\nmetodo = "carpeta_repo"\ncarpeta = "{self.vacia}"\n')
        return a

    def test_instalar_remoto_es_punto_de_extension(self):
        # sin acceso (doble) el remoto termina en 3 y sin crear nada; el punto de extensión DESCARGADORES sigue disponible
        buf = StringIO()
        with mock.patch.dict(hc.HOOKS_REMOTO, {"comprobar": lambda r: (False, "denied")}):
            c = hc.main(["instalar", "https://ejemplo.invalid/org/instancia.git", "--destino", str(self.tmp / "d")], salida=buf)
        self.assertEqual(c, 3)
        self.assertIn("SIN ACCESO", buf.getvalue())
        casi = self.tmp / "descargada"
        casi.mkdir()
        with mock.patch.object(hc, "DESCARGADORES", [lambda o: casi if "ejemplo" in o else None]):
            self.assertEqual(hc.resolver_instancia("https://ejemplo.invalid/x.git"), casi.resolve())


class TestInstalarRemoto(Base):
    """`harness instalar <repositorio>`: usa instalar-instancia.py; un repositorio local de /tmp hace de «remoto»."""

    def setUp(self):
        super().setUp()
        import subprocess
        self.remoto = self.tmp / "remoto"
        self.remoto.mkdir()
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        (self.remoto / "harness.lock").write_text('version = "0.0.1"\n')
        for c in (["init", "-q"], ["add", "."], ["commit", "-qm", "x"]):
            subprocess.run(["git", "-C", str(self.remoto), *c], check=True, capture_output=True, env=env)
        self.llamadas, self.comprobadas, self.destino = [], [], self.tmp / "clon"

    def ejecutar(self, cmd):
        self.llamadas.append(list(cmd))
        if cmd[:2] == ["git", "clone"]:   # clona del repositorio local en lugar de la red
            import subprocess
            return subprocess.run(["git", "clone", "-q", str(self.remoto), cmd[-1]], capture_output=True, text=True)
        return mock.Mock(returncode=0, stdout="update hecho", stderr="")

    def instalar(self, origen, ok=True, motivo="", extra=(), respuestas=("s",), terminal=True):
        def comprobar(repo):
            self.comprobadas.append(repo)
            return ok, motivo
        hooks = {"comprobar": comprobar, "ejecutar": self.ejecutar, "es_terminal": terminal,
                 "preguntar": Entrada(respuestas)}
        buf = StringIO()
        with mock.patch.dict(hc.HOOKS_REMOTO, hooks):
            c = hc.main(["instalar", origen, "--destino", str(self.destino), *extra], salida=buf)
        return c, buf.getvalue()

    def test_owner_nombre_se_resuelve_y_avisa(self):
        c, t = self.instalar("acme/instancia", ok=False, motivo="permission denied (publickey)")
        self.assertEqual(self.comprobadas, ["git@github.com:acme/instancia.git"])
        self.assertIn("se interpretó como git@github.com:acme/instancia.git", t)
        self.assertEqual(c, 3)

    def test_carpeta_local_existente_no_es_repositorio(self):
        (self.tmp / "acme" / "instancia").mkdir(parents=True)
        old = os.getcwd()
        os.chdir(self.tmp)
        try:
            self.assertFalse(hc.es_repositorio("acme/instancia"))
        finally:
            os.chdir(old)
        for r in ("https://h/x.git", "ssh://git@h/x", "git@h:o/x.git", "acme/otra"):
            self.assertTrue(hc.es_repositorio(r), r)
        self.assertFalse(hc.es_repositorio("./acme/otra"))

    def test_con_acceso_muestra_plan_clona_y_llama_a_update(self):
        c, t = self.instalar("https://ejemplo.invalid/acme/instancia.git")
        self.assertEqual(c, 0, t)
        self.assertLess(t.index("PLAN"), t.index("Clonado en"))
        self.assertIn("Acceso al repositorio: OK", t)
        self.assertTrue((self.destino / "harness.lock").is_file())
        update = [l for l in self.llamadas if "update" in l]
        self.assertEqual(len(update), 1)
        self.assertIn("--aplicar", update[0])
        self.assertIn("update hecho", t)

    def test_cancelar_no_clona(self):
        c, t = self.instalar("acme/instancia", respuestas=("n",))
        self.assertEqual(c, 0)
        self.assertEqual(self.llamadas, [])
        self.assertFalse(self.destino.exists())

    def test_sin_terminal_y_sin_si_solo_plan(self):
        c, t = self.instalar("acme/instancia", terminal=False)
        self.assertEqual((c, self.llamadas), (0, []))
        self.assertIn("solo se mostro el plan", t)
        self.assertFalse(self.destino.exists())

    def test_si_acepta_sin_preguntar(self):
        c, t = self.instalar("acme/instancia", extra=("--si",), respuestas=())
        self.assertEqual(c, 0, t)
        self.assertTrue(self.destino.exists())

    def test_sin_acceso_exit_3_y_no_crea_nada(self):
        c, t = self.instalar("acme/instancia", ok=False, motivo="repositorio no encontrado")
        self.assertEqual(c, 3)
        self.assertIn("SIN ACCESO", t)
        self.assertIn("Que pedir y a quien", t)
        self.assertEqual(self.llamadas, [])
        self.assertFalse(self.destino.exists())
        self.assertNotIn("acceso-github.sh", t)   # el motivo no es falta de llave: sin sugerencia

    def test_url_con_token_se_limpia_en_toda_salida(self):
        secreto = "ghp_SECRETO123"
        url = f"https://usuario:{secreto}@ejemplo.invalid/acme/instancia.git"
        for ok, motivo in ((True, ""), (False, f"fatal: https://usuario:{secreto}@ejemplo.invalid denied")):
            self.llamadas.clear(); self.comprobadas.clear()
            c, t = self.instalar(url, ok=ok, motivo=motivo, extra=("--si",))
            self.assertNotIn(secreto, t)
            self.assertNotIn("usuario:" + "ghp", t); self.assertNotIn("usuario@", t)
            self.assertIn("se descartó el usuario:token", t)
            self.assertTrue(all(secreto not in x for x in self.comprobadas))
            self.assertTrue(all(secreto not in " ".join(l) for l in self.llamadas))
            if self.destino.exists():
                shutil.rmtree(self.destino)

    def test_sugerencia_de_acceso_github_se_imprime_y_no_se_ejecuta(self):
        c, t = self.instalar("acme/instancia", ok=False, motivo="git@github.com: Permission denied (publickey).")
        self.assertEqual(c, 3)
        self.assertIn("acceso-github.sh", t)
        self.assertIn("--repositorio git@github.com:acme/instancia.git", t)
        self.assertIn("no lo ejecuto yo", t)
        self.assertEqual(self.llamadas, [])
        with mock.patch.object(hc, "correr") as correr, mock.patch("subprocess.run") as run:
            with mock.patch.dict(hc.HOOKS_REMOTO, {"comprobar": lambda r: (False, "Permission denied (publickey)")}):
                hc.main(["instalar", "acme/instancia", "--destino", str(self.destino)], salida=StringIO())
        correr.assert_not_called()
        run.assert_not_called()


class TestEjecutable(unittest.TestCase):
    def test_help_por_el_script(self):
        import subprocess
        r = subprocess.run([sys.executable, str(CLI), "--help"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("harness doctor", r.stdout)
        self.assertTrue(os.access(CLI, os.X_OK))

    def test_stdin_no_terminal_no_pregunta(self):
        import subprocess
        d = Path(tempfile.mkdtemp(prefix="mh-cli-"))
        self.addCleanup(shutil.rmtree, d, True)
        (d / "n").mkdir()
        (d / "n" / "README.md").write_text("# idea\n")
        r = subprocess.run([sys.executable, str(CLI), "--carpeta", str(d / "n")], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("sin escribir", r.stdout)
        self.assertEqual(sorted(p.name for p in d.iterdir()), ["n"])
        self.assertEqual(os.listdir(d / "n"), ["README.md"])


if __name__ == "__main__":
    unittest.main()
