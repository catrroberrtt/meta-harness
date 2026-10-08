"""Pruebas del orquestador (un solo comando). Todo con dobles y carpetas temporales: sin red, sin sudo, sin gh reales."""
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("orq", RAIZ / "instalador" / "orquestador.py")
orq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orq)

TODOS = {"git", "python3", "ssh", "ssh-keygen", "gh", "apt"}
PAQUETE_A_PROGRAMAS = {"git": ["git"], "python3": ["python3"], "openssh-client": ["ssh", "ssh-keygen"], "gh": ["gh"], "nodejs": ["node"]}
SECRETO = "ghp_SECRETO1234567890abcdef"


class Falso(orq.Sistema):
    """Sistema de mentira: programas nativos en un conjunto, comandos guionizados, respuestas en cola."""

    def __init__(self, tmp, nativos=TODOS, windows=None, wsl=False, tty=True, respuestas=(), resp=None, cwd=None, root=False):
        self.env = {"XDG_STATE_HOME": str(tmp / "estado"), "PATH": "/usr/bin"}
        self.home = tmp / "home"
        self.home.mkdir(exist_ok=True)
        self._cwd = cwd or str(tmp / "trabajo")
        self.nativos, self.windows, self.wsl, self.tty, self.root = set(nativos), dict(windows or {}), wsl, tty, root
        self.respuestas, self.resp = list(respuestas), dict(resp or {})
        self.preguntas, self.ejecutados = [], []

    def es_wsl(self):
        return self.wsl

    def es_root(self):
        return self.root

    def nativo(self, c):
        if c in self.nativos:
            return "/usr/bin/" + c, None
        return None, self.windows.get(c)

    def hay_terminal(self):
        return self.tty

    def preguntar(self, texto):
        self.preguntas.append(texto)
        if not self.tty:
            return None
        return self.respuestas.pop(0) if self.respuestas else ""

    def ejecutar(self, args, cwd=None, interactivo=False, entorno=None):
        args = [str(a) for a in args]
        self.ejecutados.append((args, cwd, interactivo))
        if args[:2] == ["sudo", "sh"] or (args[:1] == ["sh"] and "apt install" in " ".join(args)):
            for paquete in re.findall(r"install -y (.*)", args[-1])[0].split():
                self.nativos.update(PAQUETE_A_PROGRAMAS.get(paquete, [paquete]))
        if args[:2] == ["git", "clone"]:
            Path(args[-1], ".git").mkdir(parents=True, exist_ok=True)
        for n in range(len(args), 0, -1):
            if tuple(args[:n]) in self.resp:
                r = self.resp[tuple(args[:n])]
                return r(args) if callable(r) else r
        return 0, ""

    def cmds(self):
        return [" ".join(a) for a, _, _ in self.ejecutados]


def git(cwd, *a):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp(prefix="mh-orq-"))
        self.addCleanup(shutil.rmtree, self.t, True)
        (self.t / "trabajo").mkdir()
        self.eventos = []
        self.remoto = None

    def hacer_remoto(self, archivos):
        self.remoto = self.t / "remoto"
        self.remoto.mkdir()
        git(self.remoto, "init", "-q")
        for rel, texto in archivos.items():
            p = self.remoto / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(texto, encoding="utf8")
        git(self.remoto, "add", "-A")
        git(self.remoto, "commit", "-q", "-m", "i")

    def ejecutar_clone(self, cmd):
        self.eventos.append("clonar")
        if cmd[0] == "git":
            return subprocess.run(["git", "clone", "-q", str(self.remoto), cmd[-1]], capture_output=True, text=True)
        self.eventos.append("update:" + " ".join(map(str, cmd[-3:])))
        return mock.Mock(returncode=0, stdout="update hecho", stderr="")

    def correr(self, sistema=None, argv=("acme/instancia",), acceso_codigo=0, acceso_ok=True, **kw):
        sistema = sistema or Falso(self.t)
        self.sistema = sistema
        salida = []

        def acceso(url):
            self.eventos.append("acceso")
            return acceso_codigo
        hooks = {"comprobar": lambda r: (acceso_ok, "" if acceso_ok else "permission denied"),
                 "ejecutar": self.ejecutar_clone, "es_terminal": False, "preguntar": lambda p: "n"}
        codigo = orq.main(list(argv), sistema=sistema, salida=_Salida(salida), acceso=acceso, hooks_clonar=hooks,
                          doctor=lambda d: (self.eventos.append("doctor") or 0, "doctor ok"), **kw)
        self.texto = "\n".join(salida)
        return codigo, self.texto


class _Salida:
    def __init__(self, lista):
        self.lista = lista

    def write(self, t):
        if t != "\n":
            self.lista.append(t)

    def flush(self):
        pass


class Orden(Base):
    def test_orden_de_los_pasos_y_un_solo_plan(self):
        self.hacer_remoto({"harness.lock": 'version = "0.0.1"\n'})
        sis = Falso(self.t, nativos=TODOS - {"gh"}, respuestas=["s", "s"])   # plan, administrador
        c, t = self.correr(sis)
        self.assertEqual(c, 0, t)
        paquetes = [i for i, x in enumerate(sis.cmds()) if "apt install" in x]
        self.assertEqual(len(paquetes), 1)
        self.assertLess(self.eventos.index("acceso"), self.eventos.index("clonar"))
        self.assertLess(self.eventos.index("clonar"), self.eventos.index("doctor"))
        pos = [t.index(m) for m in ("[1/5]", "[2/5]", "[3/5]", "[4/5]", "[5/5]", "RESUMEN")]
        self.assertEqual(pos, sorted(pos))
        self.assertEqual(t.count("PLAN (todavia"), 1)
        self.assertEqual(len([p for p in sis.preguntas if "Aplicar este plan" in p]), 1)
        self.assertLess(t.index("PLAN"), t.index("[1/5]"))

    def test_sin_terminal_y_sin_si_solo_muestra_el_plan(self):
        sis = Falso(self.t, tty=False)
        c, t = self.correr(sis)
        self.assertEqual(c, 0)
        self.assertIn("solo se mostro el plan", t)
        self.assertEqual(sis.ejecutados, [])
        self.assertFalse((self.t / "estado").exists())
        self.assertEqual(self.eventos, [])

    def test_cancelar_no_hace_nada(self):
        sis = Falso(self.t, respuestas=["n"])
        c, t = self.correr(sis)
        self.assertEqual((c, sis.ejecutados, self.eventos), (0, [], []))
        self.assertIn("Cancelado", t)

    def test_sin_acceso_a_github_corta_y_dice_que_falta(self):
        c, t = self.correr(Falso(self.t, respuestas=["s"]), acceso_codigo=2)
        self.assertEqual(c, 2)
        self.assertNotIn("clonar", self.eventos)
        self.assertIn("Pendiente de ti", t)
        self.assertIn("acceso-github.sh --aplicar --repositorio git@github.com:acme/instancia.git", t)

    def test_sin_permiso_en_la_instancia_devuelve_3(self):
        c, t = self.correr(Falso(self.t, respuestas=["s"]), acceso_ok=False)
        self.assertEqual(c, 3)
        self.assertIn("SIN ACCESO", t)
        self.assertFalse((self.t / "trabajo" / "instancia").exists())


class Paquetes(Base):
    def test_apt_consolidado_con_una_sola_confirmacion_de_administrador(self):
        sis = Falso(self.t, nativos={"python3", "apt"}, respuestas=["s", "s"])
        c, t = self.correr(sis)
        admin = [p for p in sis.preguntas if "administrador" in p]
        self.assertEqual(len(admin), 1)
        sudo = [a for a, _, _ in sis.ejecutados if a[0] == "sudo"]
        self.assertEqual(sudo, [["sudo", "sh", "-c", "apt update && apt install -y git openssh-client gh"]])
        self.assertIn("sudo apt update && sudo apt install -y git openssh-client gh", t)
        self.assertEqual(t.count("sudo apt update"), 2)   # plan + paso; nunca varios comandos sueltos

    def test_sin_confirmacion_no_se_ejecuta_sudo(self):
        for tty, resp in ((True, ["n"]), (True, [""]), (False, [])):
            sis = Falso(self.t, nativos={"python3", "apt"}, respuestas=resp, tty=tty)
            c, t = self.correr(sis, argv=("acme/instancia", "--si"))
            self.assertFalse(any(a[0] == "sudo" or "apt" in a for a, _, _ in sis.ejecutados), (tty, resp))
            self.assertIn("Pendiente de ti", t)
            self.assertIn("sudo apt update && sudo apt install -y git openssh-client gh", t)
            self.assertEqual(c, 2)
            self.assertEqual(self.eventos, [])

    def test_si_no_salta_la_confirmacion_de_administrador(self):
        sis = Falso(self.t, nativos={"python3", "apt"}, respuestas=["n"])
        self.correr(sis, argv=("acme/instancia", "--si"))
        self.assertTrue(any("administrador" in p for p in sis.preguntas))
        self.assertFalse(any("Aplicar este plan" in p for p in sis.preguntas))   # --si solo salta el plan

    def test_como_root_no_usa_sudo(self):
        sis = Falso(self.t, nativos={"python3", "apt"}, respuestas=["s", "s"], root=True)
        self.correr(sis)
        self.assertEqual([a for a, _, _ in sis.ejecutados if "apt" in " ".join(a)][0][0], "sh")

    def test_binarios_de_windows_no_cuentan_como_instalados(self):
        sis = Falso(self.t, nativos={"python3", "apt", "ssh", "ssh-keygen", "gh"}, wsl=True,
                    windows={"git": "/mnt/c/Program Files/Git/cmd/git"}, respuestas=["n"])
        c, t = self.correr(sis)
        self.assertIn("solo existe como programa de Windows", t)
        self.assertIn("Falta git", t)
        sis2 = Falso(self.t, nativos=TODOS, wsl=True)
        o = orq.Orquestador(mock.Mock(instancia="a/b"), sis2)
        self.assertEqual(o.faltantes_base(), [])

    def test_sistema_real_ignora_mnt_en_wsl(self):
        carpeta = self.t / "mnt" / "c" / "bin"
        carpeta.mkdir(parents=True)
        (carpeta / "npm").write_text("#!/bin/sh\n")
        (carpeta / "npm").chmod(0o755)
        s = orq.Sistema(home=self.t, entorno={"PATH": str(carpeta)})
        s.es_wsl = lambda: True
        with mock.patch.object(orq.ag, "RUTA_WINDOWS", re.compile(r"^%s(/|$)" % re.escape(str(self.t / "mnt" / "c")))):
            self.assertEqual(s.nativo("npm"), (None, str(carpeta / "npm")))
            s.es_wsl = lambda: False
            self.assertEqual(s.nativo("npm"), (str(carpeta / "npm"), None))


class Ubicacion(Base):
    def test_cwd_en_disco_de_windows_avisa_y_trabaja_en_home(self):
        self.hacer_remoto({"harness.lock": 'version = "0.0.1"\n'})
        sis = Falso(self.t, wsl=True, cwd="/mnt/c/Users/yo/Desktop", respuestas=["s"])
        c, t = self.correr(sis)
        self.assertIn("disco de Windows", t)
        self.assertTrue((sis.home / "instancia" / "harness.lock").is_file())
        self.assertFalse(Path("/mnt/c/Users/yo/Desktop/instancia").exists())

    def test_cwd_normal_no_avisa(self):
        c, t = self.correr(Falso(self.t, tty=False))
        self.assertNotIn("disco de Windows", t)
        self.assertIn(str(self.t / "trabajo" / "instancia"), t)


class Reanudar(Base):
    def test_reanuda_tras_un_corte_y_no_guarda_secretos(self):
        self.hacer_remoto({"harness.lock": 'version = "0.0.1"\n'})
        sis = Falso(self.t, nativos=TODOS - {"gh"}, respuestas=["s", "s"])
        c, t = self.correr(sis, acceso_codigo=2)    # el acceso se corta
        self.assertEqual(c, 2)
        estado = json.loads((self.t / "estado" / "meta-harness" / "instalar-acme-instancia.json").read_text())
        self.assertNotIn("acceso", estado["hechos"])
        sis = Falso(self.t, nativos=TODOS, respuestas=["s"])
        self.eventos.clear()
        c, t = self.correr(sis, acceso_codigo=0)
        self.assertEqual(c, 0, t)
        self.assertEqual(self.eventos[0], "acceso")
        self.eventos.clear()
        sis = Falso(self.t, nativos=TODOS, respuestas=["s"])
        c, t = self.correr(sis)
        self.assertEqual(self.eventos, ["doctor"])        # acceso y clon ya hechos: no se repiten
        self.assertIn("Retomo", t)
        self.assertIn("Ya hecho en un intento anterior", t)
        crudo = (self.t / "estado" / "meta-harness" / "instalar-acme-instancia.json").read_text()
        self.assertEqual(oct((self.t / "estado" / "meta-harness" / "instalar-acme-instancia.json").stat().st_mode & 0o777), "0o600")
        for prohibido in ("id_ed25519", "PRIVATE", ".ssh", "token", "ghp_", "password"):
            self.assertNotIn(prohibido, crudo)

    def test_url_con_token_no_aparece_en_ninguna_salida_ni_estado(self):
        self.hacer_remoto({"harness.lock": 'version = "0.0.1"\n'})
        url = "https://usuario:%s@ejemplo.invalid/acme/instancia.git" % SECRETO
        sis = Falso(self.t, respuestas=["s"])
        c, t = self.correr(sis, argv=(url,))
        self.assertNotIn(SECRETO, t)
        self.assertNotIn("usuario@", t)
        self.assertNotIn("usuario:" + "ghp", t)
        for p in (self.t / "estado").rglob("*.json"):
            self.assertNotIn(SECRETO, p.read_text())
        self.assertTrue(all(SECRETO not in " ".join(a) for a, _, _ in sis.ejecutados))
        self.assertNotRegex(t, r"gh[pousr]_[A-Za-z0-9]{16,}")


class Clonado(Base):
    def test_instancia_sin_harness_lock_no_ejecuta_update(self):
        self.hacer_remoto({"README.md": "x"})
        c, t = self.correr(Falso(self.t, respuestas=["s"]))
        self.assertEqual(c, 0, t)
        self.assertFalse(any(e.startswith("update") for e in self.eventos))
        self.assertIn("no se ejecuta `update`", t.replace("NO se ejecuta", "no se ejecuta"))

    def test_con_harness_lock_ejecuta_update(self):
        self.hacer_remoto({"harness.lock": 'version = "0.0.1"\n'})
        self.correr(Falso(self.t, respuestas=["s"]))
        self.assertTrue(any(e.startswith("update") for e in self.eventos))


ENTORNO_OK = '''
[general]
base_repos = "~/Proyectos"

[[prerrequisitos]]
comando = "node"
para = "compilar"
instalar_apt = "nodejs npm"
obligatorio = true

[[repositorios]]
remoto = "acme/api"
destino = "tenant/api"

[[repositorios]]
remoto = "acme/docs"
destino = "tenant/docs"
confirmacion = false

[[pasos]]
nombre = "indice"
comando = ["python3", "indexar.py"]
por_defecto = "si"
cwd = "tools"

[[pasos]]
nombre = "descargar"
comando = ["python3", "bajar.py"]
red = true
por_defecto = "si"

[[pasos]]
nombre = "opcional"
comando = ["echo", "hola"]
por_defecto = "no"
'''


class EntornoToml(Base):
    def test_valido_ejecuta_lo_declarado_sin_shell_y_agrupa_confirmaciones(self):
        self.hacer_remoto({".harness/entorno.toml": ENTORNO_OK, "tools/x": "1"})
        sis = Falso(self.t, nativos=TODOS, respuestas=["s", "s", "s", "s", "s"])
        c, t = self.correr(sis, argv=("acme/instancia", "--si"))
        self.assertEqual(c, 0, t)
        inst = self.t / "trabajo" / "instancia"
        ej = {tuple(a): (cwd, inter) for a, cwd, inter in sis.ejecutados}
        self.assertEqual(ej[("python3", "indexar.py")][0], (inst / "tools").resolve())
        self.assertIn(("python3", "bajar.py"), ej)
        self.assertNotIn(("echo", "hola"), ej)                         # por_defecto = no
        self.assertTrue(any(a[:2] == ["git", "clone"] and a[-1].endswith("tenant/api") for a, _, _ in sis.ejecutados))
        self.assertTrue((sis.home / "Proyectos" / "tenant" / "docs" / ".git").exists())
        self.assertFalse(any(a[0] == "sh" and "indexar" in " ".join(a) for a, _, _ in sis.ejecutados))
        self.assertEqual(len([p for p in sis.preguntas if "Clonar" in p]), 1)           # repos agrupados
        self.assertEqual(len([p for p in sis.preguntas if "estos 1 pasos" in p]), 1)    # riesgosos agrupados
        self.assertIn("paso «opcional» (por_defecto = no)", t)

    def test_pesado_o_red_siempre_piden_confirmacion_aunque_haya_si(self):
        self.hacer_remoto({".harness/entorno.toml": ENTORNO_OK, "tools/x": "1"})
        sis = Falso(self.t, nativos=TODOS | {"node"}, respuestas=["n", "n"])   # repos: no; pasos riesgosos: no
        c, t = self.correr(sis, argv=("acme/instancia", "--si"))
        self.assertNotIn(("python3", "bajar.py"), [tuple(a) for a, _, _ in sis.ejecutados])
        self.assertFalse(any(a[:2] == ["git", "clone"] and a[-1].endswith("tenant/api") for a, _, _ in sis.ejecutados))
        self.assertEqual(c, 2)
        self.assertIn("cd %s && python3 bajar.py" % (self.t / "trabajo" / "instancia"), t)
        self.assertIn("git clone git@github.com:acme/api.git", t)
        # sin terminal: igual, queda pendiente
        shutil.rmtree(self.t / "estado")
        shutil.rmtree(self.t / "trabajo" / "instancia")
        sis = Falso(self.t, nativos=TODOS | {"node"}, tty=False)
        c, t = self.correr(sis, argv=("acme/instancia", "--si"))
        self.assertNotIn(("python3", "bajar.py"), [tuple(a) for a, _, _ in sis.ejecutados])

    def test_prerrequisito_faltante_usa_un_apt_con_confirmacion(self):
        self.hacer_remoto({".harness/entorno.toml": ENTORNO_OK})
        sis = Falso(self.t, nativos=TODOS, respuestas=["s", "n", "n"])   # admin: si; repos: no; pasos: no
        self.correr(sis, argv=("acme/instancia", "--si"))
        self.assertIn("sudo sh -c apt update && apt install -y nodejs npm", sis.cmds())

    def test_invalido_da_error_claro_y_no_ejecuta_nada_del_entorno(self):
        malo = ('[[pasos]]\nnombre = "x"\ncomando = "npm install"\nextra = 1\n'
                '[[repositorios]]\nremoto = "acme/api"\ndestino = "../fuera"\n'
                '[[prerrequisitos]]\ncomando = "node"\n')
        self.hacer_remoto({".harness/entorno.toml": malo})
        sis = Falso(self.t, respuestas=["s"])
        c, t = self.correr(sis)
        self.assertEqual(c, 2)
        self.assertIn("no es valido", t)
        self.assertIn("«comando» debe ser una lista", t)
        self.assertIn("clave desconocida «extra»", t)
        self.assertIn("«destino» debe ser una ruta relativa", t)
        self.assertIn("falta «para»", t)
        self.assertEqual([a for a, _, _ in sis.ejecutados if a[0] != "git" or a[:2] == ["git", "clone"]], [])
        self.assertNotIn("Ejecutando", t)

    def test_toml_roto_y_valores_de_tipo_incorrecto(self):
        ent, err = orq.validar_entorno({"pasos": [{"nombre": "a", "comando": ["x"], "red": "si", "por_defecto": "tal"}]})
        self.assertTrue(any("«red» debe ser true o false" in e for e in err))
        self.assertTrue(any("«por_defecto» debe ser" in e for e in err))
        p = self.t / "e.toml"
        p.write_text("[[pasos\n")
        ent, err = orq.leer_entorno(p)
        self.assertIsNone(ent)
        self.assertIn("no es TOML valido", err[0])
        _, err = orq.validar_entorno({"repositorios": [{"remoto": "https://u:%s@h/x.git" % SECRETO, "destino": "a"}]})
        self.assertTrue(err and SECRETO not in " ".join(err))
        _, err = orq.validar_entorno({"pasos": [{"nombre": "a", "comando": ["x"], "cwd": "/etc"}]})
        self.assertTrue(any("«cwd»" in e for e in err))

    def test_ejemplo_de_la_plantilla_es_valido_y_generico(self):
        ruta = RAIZ / "plantillas" / "instancia" / "entorno.toml.ejemplo"
        ent, err = orq.leer_entorno(ruta)
        self.assertEqual(err, [])
        self.assertTrue(ent["pasos"] and ent["repositorios"] and ent["prerrequisitos"])


class Restaurar(Base):
    SCRIPT = '#!/bin/bash\nif [ "$1" = "--aplicar" ]; then echo APLICADO; else echo "plan: hooks"; echo "plan: memoria"; fi\n'

    def test_muestra_plan_y_pide_una_confirmacion_antes_de_aplicar(self):
        self.hacer_remoto({"scripts/restaurar-entorno.sh": self.SCRIPT})
        sis = Falso(self.t, respuestas=["s", "s"], resp={("bash",): lambda a: (0, "plan: hooks\nplan: memoria\n")})
        c, t = self.correr(sis, argv=("acme/instancia", "--si"))
        self.assertEqual(c, 0, t)
        cmds = [(a, i) for a, _, i in sis.ejecutados if a[0] == "bash"]
        self.assertEqual(len(cmds), 2)
        self.assertNotIn("--aplicar", cmds[0][0])
        self.assertFalse(cmds[0][1])
        self.assertEqual(cmds[1][0][-1], "--aplicar")
        self.assertTrue(cmds[1][1])                       # interactivo: el script pregunta lo suyo
        self.assertIn("| plan: hooks", t)
        self.assertEqual(len([p for p in sis.preguntas if "restaurar-entorno" in p]), 1)
        self.assertLess(t.index("| plan: hooks"), t.index("[5/5]"))

    def test_sin_confirmacion_no_aplica_y_queda_pendiente(self):
        self.hacer_remoto({"scripts/restaurar-entorno.sh": self.SCRIPT})
        sis = Falso(self.t, respuestas=["n"])
        c, t = self.correr(sis, argv=("acme/instancia", "--si"))
        self.assertFalse(any(a[-1] == "--aplicar" for a, _, _ in sis.ejecutados))
        self.assertEqual(c, 2)
        self.assertIn("restaurar-entorno.sh --aplicar", t)

    def test_avisa_que_el_script_actua_sobre_home_antes_de_confirmar(self):
        # Hallazgo de la prueba real: con --destino en /tmp, el script igual modifico la configuracion personal.
        self.hacer_remoto({"scripts/restaurar-entorno.sh": self.SCRIPT})
        sis = Falso(self.t, respuestas=["n"])
        c, t = self.correr(sis, argv=("acme/instancia", "--si"))
        self.assertIn("actua sobre tu carpeta personal", t)
        self.assertIn("responde N", t)
        self.assertEqual(len([q for q in sis.preguntas if "restaurar-entorno" in q]), 1)   # se pregunta una vez, con el aviso ya impreso

    def test_codigo_cero_del_script_no_se_presenta_como_nada_pendiente(self):
        # Hallazgo de la prueba real: el script listo un pendiente propio y el resumen dijo "Nada pendiente".
        self.hacer_remoto({"scripts/restaurar-entorno.sh": self.SCRIPT})
        sis = Falso(self.t, respuestas=["s", "s"])
        c, t = self.correr(sis, argv=("acme/instancia", "--si"))
        resumen = t[t.index("RESUMEN"):]
        self.assertNotIn("Nada pendiente", resumen)
        self.assertIn("resumen del propio script de la instancia", resumen)
        self.assertIn("termino con codigo 0", resumen)

    def test_sin_entorno_ni_restaurador_termina_bien(self):
        self.hacer_remoto({"README.md": "x"})
        c, t = self.correr(Falso(self.t, respuestas=["s"]))
        self.assertEqual(c, 0, t)
        self.assertIn("no hay entorno que preparar", t)
        self.assertIn("Nada pendiente", t)
        self.assertIn("Omitido", t)


class Salidas(Base):
    def test_resumen_hecho_omitido_pendiente_y_doctor(self):
        self.hacer_remoto({"README.md": "x"})
        c, t = self.correr(Falso(self.t, respuestas=["s"]))
        for m in ("Hecho:", "Omitido:", "doctor ok"):
            self.assertIn(m, t)
        self.assertNotRegex(t, r"gh[pousr]_|github_pat_|://[^/\s@]+:[^/\s@]+@")


class SinBasesDeDatos(Base):
    PROHIBIDOS = re.compile(r"\b(mysql|mysqldump|mariadb|psql|pg_dump|pg_restore|mongo|mongosh|redis-cli|sqlite3|docker|docker-compose|podman|aws)\b")

    def test_resumen_siempre_trae_el_bloque_de_acceso_a_datos(self):
        self.hacer_remoto({"README.md": "x"})
        for sis, kw in ((Falso(self.t, respuestas=["s"]), {}), (Falso(self.t, nativos={"python3", "apt"}, respuestas=["s", "n"]), {}),
                        (Falso(self.t, respuestas=["s"]), {"acceso_codigo": 2})):
            shutil.rmtree(self.t / "trabajo" / "instancia", ignore_errors=True)
            c, t = self.correr(sis, **kw)
            self.assertIn("Acceso a datos (lo das tu)", t)
            for m in ("NO se instala", "modo degradado", "politicas.toml", "acceso.local.toml", "preflight-accesos.py"):
                self.assertIn(m, t)

    def test_ningun_paso_invoca_clientes_de_bases_docker_ni_aws(self):
        self.hacer_remoto({".harness/entorno.toml": ENTORNO_OK, "tools/x": "1"})
        sis = Falso(self.t, nativos=TODOS | {"node"}, respuestas=["s", "s", "s", "s"])
        self.correr(sis, argv=("acme/instancia", "--si"))
        self.assertTrue(sis.ejecutados)
        for a, _, _ in sis.ejecutados:
            self.assertFalse(self.PROHIBIDOS.search(a[0]), a)
        fuente = (RAIZ / "instalador" / "orquestador.py").read_text()
        codigo = re.sub(r"(\"\"\".*?\"\"\"|#.*|\"[^\"\n]*\")", "", fuente, flags=re.S)
        self.assertFalse(re.search(r"\[\s*[\"'](mysql|psql|docker|aws|mongo)", fuente))
        self.assertNotIn("subprocess.run([\"docker", fuente)


if __name__ == "__main__":
    unittest.main()
