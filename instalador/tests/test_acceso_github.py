import importlib.util
import json
import os
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("acceso_github", os.path.join(AQUI, "..", "acceso_github.py"))
ag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ag)

PRIVADA = "-----BEGIN OPENSSH PRIVATE KEY-----\nSECRETO_PRIVADO_XYZ_123\n-----END OPENSSH PRIVATE KEY-----\n"
CUERPO = "AAAAC3NzaC1lZDI1NTE5AAAAIPUBLICA"
PUB = "ssh-ed25519 %s maquina\n" % CUERPO
OFICIAL = "uNiVztksCsDhcc0u9e8BujQXVUpKZIDTMczCvj3tD2s"
META = json.dumps({"ssh_key_fingerprints": {"SHA256_ED25519": OFICIAL}})


class Doble(ag.Sistema):
    """Sistema de mentira: archivos en memoria, comandos guionizados, respuestas en cola."""

    def __init__(self, comandos=(), archivos=None, respuestas=(), respuestas_cmd=None):
        self.home = "/casa"
        self.comandos = set(comandos)
        self.archivos = dict(archivos or {})
        self.respuestas = list(respuestas)
        self.resp = respuestas_cmd or {}
        self.ejecutados = []
        self.preguntas = []
        self.lecturas = []
        self.anexos = []

    def existe(self, c):
        return c in self.comandos

    def ejecutar(self, args, entrada=None, interactivo=False, entorno=None):
        self.ejecutados.append(list(args))
        for n in range(len(args), 0, -1):
            clave = tuple(args[:n])
            if clave in self.resp:
                r = self.resp[clave]
                return r(args) if callable(r) else r
        return 0, ""

    def existe_ruta(self, r):
        return r in self.archivos

    def leer_publica(self, r):
        self.lecturas.append(r)
        if not r.endswith(".pub"):
            raise ValueError("privada")
        return self.archivos.get(r)

    def anexar(self, r, t):
        self.anexos.append((r, t))

    def preguntar(self, t, d=""):
        self.preguntas.append(t)
        return self.respuestas.pop(0) if self.respuestas else d

    def maquina(self):
        return "mi-pc"

    def hoy(self):
        return "2026-01-02"

    def cmds(self):
        return [" ".join(a) for a in self.ejecutados]


def correr(doble, aplicar=True, **kw):
    salida = []
    d = tempfile.mkdtemp()
    f = ag.Flujo(doble, aplicar, salida=kw.pop("salida", d), escribir=salida.append, **kw)
    codigo = f.ejecutar()
    log = os.path.join(d, "acceso-github.log")
    texto_log = ""
    if os.path.exists(log):
        with open(log) as fh:
            texto_log = fh.read()
    return codigo, "\n".join(salida), texto_log, f


SSH_KEYGEN_L = {("ssh-keygen", "-lf"): lambda a: (0, "256 SHA256:HUELLAPROPIA maquina (ED25519)\n") if a[2] != "-" else (0, "256 SHA256:%s github.com (ED25519)\n" % OFICIAL)}
BASE = {("gh", "auth", "status"): (0, ""), **SSH_KEYGEN_L}


class PasoGh(unittest.TestCase):
    def test_apt_actualiza_las_listas_antes_de_instalar(self):
        # Hallazgo de la primera prueba en una maquina real: Ubuntu recien instalado (WSL) no encuentra gh sin `apt update`.
        d = Doble(comandos={"apt"}, respuestas=["s", "s"])
        d.existe = lambda c: c == "apt" or (c == "gh" and ["sudo", "apt", "install", "gh"] in d.ejecutados)
        _, salida, _, _ = correr(d)
        self.assertIn("sudo apt update", salida)
        self.assertLess(d.ejecutados.index(["sudo", "apt", "update"]), d.ejecutados.index(["sudo", "apt", "install", "gh"]))
        self.assertEqual(sum("administrador" in p for p in d.preguntas), 1)   # una sola confirmacion para ambos

    def test_el_plan_muestra_ambos_comandos_y_no_ejecuta(self):
        d = Doble(comandos={"apt"})
        _, salida, _, _ = correr(d, aplicar=False)
        self.assertIn("sudo apt update", salida)
        self.assertIn("sudo apt install gh", salida)
        self.assertEqual(d.ejecutados, [])

    def test_solo_apt_lleva_comando_previo(self):
        self.assertEqual(set(ag.PREVIOS), {"apt"})

    def test_apt_muestra_comando_y_no_ejecuta_sin_confirmacion(self):
        d = Doble(comandos={"apt"}, respuestas=["n"])
        codigo, salida, _, _ = correr(d)
        self.assertIn("sudo apt install gh", salida)
        self.assertNotIn(["sudo", "apt", "install", "gh"], d.ejecutados)
        self.assertEqual(codigo, 2)
        self.assertIn("https://cli.github.com", salida)

    def test_con_confirmacion_ejecuta_y_pide_administrador(self):
        d = Doble(comandos={"apt"}, respuestas=["s", "s"])
        d.existe = lambda c: c == "apt" or (c == "gh" and ["sudo", "apt", "install", "gh"] in d.ejecutados)
        _, salida, _, _ = correr(d)
        self.assertIn(["sudo", "apt", "install", "gh"], d.ejecutados)
        self.assertIn("administrador", salida)
        self.assertEqual(sum("administrador" in p for p in d.preguntas), 1)

    def test_administrador_no_confirmado_no_ejecuta(self):
        d = Doble(comandos={"dnf"}, respuestas=["s", "n"])
        codigo, salida, _, _ = correr(d)
        self.assertEqual(d.ejecutados, [])
        self.assertEqual(codigo, 2)

    def test_brew_no_pide_administrador(self):
        d = Doble(comandos={"brew"}, respuestas=["n"])
        correr(d)
        self.assertFalse(any("administrador" in p for p in d.preguntas))

    def test_sin_gestor_da_instrucciones_a_mano(self):
        d = Doble()
        codigo, salida, _, _ = correr(d)
        self.assertEqual(codigo, 2)
        self.assertIn("a mano", salida)
        self.assertEqual(d.ejecutados, [])

    def test_nunca_curl_pipe_sh(self):
        for g, *_ in ag.GESTORES:
            d = Doble(comandos={g}, respuestas=["s", "s"])
            correr(d)
            self.assertFalse(any("curl" in c or "| sh" in c for c in d.cmds()))


class Sesion(unittest.TestCase):
    def test_sin_sesion_indica_login_y_no_avanza(self):
        d = Doble(comandos={"gh"}, respuestas_cmd={("gh", "auth", "status"): (1, "not logged in")})
        codigo, salida, _, _ = correr(d)
        self.assertEqual(codigo, 2)
        self.assertIn("gh auth login", salida)
        self.assertNotIn(["gh", "auth", "login"], d.ejecutados)
        self.assertFalse(any(c[:2] == ["ssh-keygen", "-t"] for c in d.ejecutados))

    def test_sesion_aparece_tras_esperar(self):
        estado = {"n": 0}

        def st(a):
            estado["n"] += 1
            return (1, "") if estado["n"] == 1 else (0, "")
        d = Doble(comandos={"gh"}, respuestas_cmd={**BASE, ("gh", "auth", "status"): st}, respuestas=["ssh"])
        _, salida, _, _ = correr(d)
        self.assertIn("Sesion detectada", salida)


class Ssh(unittest.TestCase):
    def base(self, archivos, resp=None, respuestas=("ssh", "s", "s", "s", "s", "s", "n")):
        r = {**BASE, ("gh", "api", "user/keys"): (0, "[]"), ("gh", "api", "meta"): (0, META),
             ("ssh-keygen", "-F"): (1, ""), ("ssh-keyscan",): (0, "github.com ssh-ed25519 AAAA\n"),
             ("ssh", "-T"): (1, "Hi x! You've successfully authenticated"), ("git", "config"): (0, "algo")}
        r.update(resp or {})
        return Doble(comandos={"gh", "ssh-add"}, archivos=archivos, respuestas=list(respuestas), respuestas_cmd=r)

    def test_reutiliza_llave_existente_y_no_genera(self):
        d = self.base({"/casa/.ssh/id_ed25519.pub": PUB, "/casa/.ssh/id_ed25519": PRIVADA})
        codigo, salida, _, _ = correr(d)
        self.assertEqual(codigo, 0)
        self.assertIn("reutiliza", salida)
        self.assertFalse(any(c[:2] == ["ssh-keygen", "-t"] for c in d.ejecutados))

    def test_rsa_corta_no_se_usa(self):
        d = self.base({"/casa/.ssh/id_rsa.pub": "ssh-rsa AAAA x\n"}, {("ssh-keygen", "-lf"): lambda a: (0, "2048 SHA256:X x (RSA)\n") if a[2] != "-" else (0, "256 SHA256:%s h (ED25519)" % OFICIAL)})
        d.respuestas = ["ssh", "n"]
        _, salida, _, _ = correr(d)
        self.assertIn("< 3072", salida)
        self.assertIn("Se generara una nueva", salida)

    def test_genera_solo_si_no_hay_ruta_inexistente_titulo(self):
        d = self.base({})
        d.resp[("ssh-keygen", "-t")] = lambda a: (d.archivos.__setitem__(a[-1] + ".pub", PUB) or 0, "")
        codigo, salida, _, _ = correr(d)
        gen = [c for c in d.ejecutados if c[:2] == ["ssh-keygen", "-t"]]
        self.assertEqual(len(gen), 1)
        self.assertEqual(gen[0][-1], "/casa/.ssh/id_ed25519")
        self.assertEqual(gen[0][gen[0].index("-C") + 1], "mi-pc 2026-01-02")
        self.assertIn("frase", salida)
        self.assertIn(["ssh-add", "/casa/.ssh/id_ed25519"], d.ejecutados)

    def test_no_sobrescribe_privada_existente_sin_publica(self):
        d = self.base({"/casa/.ssh/id_ed25519": PRIVADA})
        d.resp[("ssh-keygen", "-t")] = lambda a: (d.archivos.__setitem__(a[-1] + ".pub", PUB) or 0, "")
        _, salida, log, _ = correr(d)
        gen = [c for c in d.ejecutados if c[:2] == ["ssh-keygen", "-t"]][0]
        self.assertEqual(gen[-1], "/casa/.ssh/id_ed25519_github")
        self.assertIn("otro nombre", salida)
        self.assertNotIn("SECRETO_PRIVADO_XYZ_123", salida + log)

    def test_registra_solo_la_publica_con_titulo(self):
        d = self.base({"/casa/.ssh/id_ed25519.pub": PUB, "/casa/.ssh/id_ed25519": PRIVADA})
        _, salida, _, _ = correr(d)
        add = [c for c in d.ejecutados if c[:3] == ["gh", "ssh-key", "add"]]
        self.assertEqual(add, [["gh", "ssh-key", "add", "/casa/.ssh/id_ed25519.pub", "--title", "mi-pc 2026-01-02"]])
        self.assertIn("SHA256:HUELLAPROPIA", salida)
        self.assertTrue(all(l.endswith(".pub") for l in d.lecturas))

    def test_sin_confirmacion_no_registra(self):
        d = self.base({"/casa/.ssh/id_ed25519.pub": PUB}, respuestas=("ssh", "n"))
        codigo, _, _, _ = correr(d)
        self.assertEqual(codigo, 3)
        self.assertFalse(any(c[:3] == ["gh", "ssh-key", "add"] for c in d.ejecutados))

    def test_ya_registrada_no_se_duplica(self):
        d = self.base({"/casa/.ssh/id_ed25519.pub": PUB}, {("gh", "api", "user/keys"): (0, json.dumps([{"key": "ssh-ed25519 " + CUERPO}]))})
        _, salida, _, _ = correr(d)
        self.assertIn("no se duplica", salida)
        self.assertFalse(any(c[:3] == ["gh", "ssh-key", "add"] for c in d.ejecutados))

    def test_github_dice_duplicada(self):
        d = self.base({"/casa/.ssh/id_ed25519.pub": PUB}, {("gh", "ssh-key", "add"): (1, "HTTP 422: key is already in use")})
        codigo, _, _, _ = correr(d)
        self.assertEqual(codigo, 0)

    def test_falta_admin_public_key_propone_refresh(self):
        d = self.base({"/casa/.ssh/id_ed25519.pub": PUB}, {("gh", "ssh-key", "add"): (1, "HTTP 404: Not Found (need admin:public_key scope)")}, respuestas=("ssh", "s", "n"))
        codigo, salida, _, _ = correr(d)
        self.assertEqual(codigo, 2)
        self.assertIn("gh auth refresh -s admin:public_key", salida)
        self.assertNotIn(["gh", "auth", "refresh", "-s", "admin:public_key"], d.ejecutados)

    def test_refresh_confirmado_reintenta(self):
        estado = {"n": 0}

        def add(a):
            estado["n"] += 1
            return (1, "needs admin:public_key scope") if estado["n"] == 1 else (0, "")
        d = self.base({"/casa/.ssh/id_ed25519.pub": PUB}, {("gh", "ssh-key", "add"): add}, respuestas=("ssh", "s", "s", "s", "s", "n"))
        correr(d)
        self.assertIn(["gh", "auth", "refresh", "-s", "admin:public_key"], d.ejecutados)
        self.assertEqual(estado["n"], 2)

    def test_sso_explica_y_se_detiene(self):
        d = self.base({"/casa/.ssh/id_ed25519.pub": PUB}, {("gh", "ssh-key", "add"): (1, "Resource protected by organization SAML enforcement")})
        codigo, salida, _, _ = correr(d)
        self.assertEqual(codigo, 2)
        self.assertIn("Configure SSO", salida)
        self.assertFalse(any(c[0] == "ssh-keyscan" or c[:2] == ["ssh", "-T"] for c in d.ejecutados))


class Servidor(unittest.TestCase):
    def test_huella_distinta_no_acepta(self):
        r = {**BASE, ("gh", "api", "user/keys"): (0, json.dumps([{"key": "ssh-ed25519 " + CUERPO}])), ("gh", "api", "meta"): (0, META),
             ("ssh-keygen", "-F"): (1, ""), ("ssh-keyscan",): (0, "github.com ssh-ed25519 AAAA\n"),
             ("ssh-keygen", "-lf"): lambda a: (0, "256 SHA256:OTRAHUELLA h (ED25519)") if a[2] == "-" else (0, "256 SHA256:P m (ED25519)")}
        d = Doble(comandos={"gh"}, archivos={"/casa/.ssh/id_ed25519.pub": PUB}, respuestas=["ssh", "s", "s"], respuestas_cmd=r)
        codigo, salida, _, _ = correr(d)
        self.assertEqual(codigo, 2)
        self.assertIn("NO coincide", salida)
        self.assertEqual(d.anexos, [])

    def test_sin_oficiales_no_acepta(self):
        r = {**BASE, ("gh", "api", "user/keys"): (0, json.dumps([{"key": "ssh-ed25519 " + CUERPO}])), ("gh", "api", "meta"): (1, "sin red"),
             ("ssh-keygen", "-F"): (1, "")}
        d = Doble(comandos={"gh"}, archivos={"/casa/.ssh/id_ed25519.pub": PUB}, respuestas=["ssh", "s"], respuestas_cmd=r)
        codigo, salida, _, _ = correr(d)
        self.assertEqual(codigo, 2)
        self.assertEqual(d.anexos, [])
        self.assertIn("NO acepto", salida)

    def test_huella_correcta_se_acepta_con_confirmacion(self):
        r = {**BASE, ("gh", "api", "user/keys"): (0, json.dumps([{"key": "ssh-ed25519 " + CUERPO}])), ("gh", "api", "meta"): (0, META),
             ("ssh-keygen", "-F"): (1, ""), ("ssh-keyscan",): (0, "github.com ssh-ed25519 AAAA\n"),
             ("ssh", "-T"): (1, "successfully authenticated"), ("git", "config"): (0, "x")}
        d = Doble(comandos={"gh"}, archivos={"/casa/.ssh/id_ed25519.pub": PUB}, respuestas=["ssh", "s"], respuestas_cmd=r)
        codigo, _, _, _ = correr(d)
        self.assertEqual(codigo, 0)
        self.assertEqual(d.anexos[0][0], "/casa/.ssh/known_hosts")


class Verificacion(unittest.TestCase):
    def verificar(self, ssh=(1, "successfully authenticated"), ls=(0, ""), repo="git@github.com:org/r.git"):
        r = {**BASE, ("gh", "api", "user/keys"): (0, json.dumps([{"key": "ssh-ed25519 " + CUERPO}])), ("gh", "api", "meta"): (0, META),
             ("ssh-keygen", "-F"): (0, ""), ("ssh", "-T"): ssh, ("git", "ls-remote"): ls, ("git", "config"): (0, "x")}
        d = Doble(comandos={"gh"}, archivos={"/casa/.ssh/id_ed25519.pub": PUB}, respuestas=["ssh"], respuestas_cmd=r)
        codigo, salida, _, _ = correr(d, repositorio=repo)
        return codigo, salida, d

    def test_ok(self):
        codigo, salida, d = self.verificar()
        self.assertEqual(codigo, 0)
        self.assertIn(["git", "ls-remote", "git@github.com:org/r.git"], d.ejecutados)

    def test_sin_llave(self):
        codigo, salida, _ = self.verificar(ssh=(255, "git@github.com: Permission denied (publickey)."))
        self.assertEqual(codigo, 2)
        self.assertIn("sin llave", salida)

    def test_red(self):
        _, salida, _ = self.verificar(ssh=(255, "ssh: Could not resolve hostname github.com"))
        self.assertIn("Causa probable: red", salida)

    def test_sin_permiso_en_repositorio(self):
        _, salida, _ = self.verificar(ls=(128, "ERROR: Repository not found."))
        self.assertIn("sin permiso en el repositorio", salida)
        self.assertIn("administra el repositorio", salida)

    def test_sso(self):
        _, salida, _ = self.verificar(ls=(128, "Resource protected by organization SAML enforcement"))
        self.assertIn("sin autorizacion SSO", salida)
        self.assertIn("Configure SSO", salida)

    def test_url_con_credenciales_no_se_usa(self):
        codigo, salida, d = self.verificar(repo="https://usuario:clavesecreta@github.com/o/r.git")
        self.assertEqual(codigo, 1)
        self.assertNotIn("clavesecreta", salida)
        self.assertFalse(any(c[:2] == ["git", "ls-remote"] for c in d.ejecutados))


class Garantias(unittest.TestCase):
    def test_privada_y_tokens_no_aparecen(self):
        archivos = {"/casa/.ssh/id_ed25519.pub": PUB, "/casa/.ssh/id_ed25519": PRIVADA}
        r = {**BASE, ("gh", "api", "user/keys"): (0, "[]"), ("gh", "api", "meta"): (0, META), ("ssh-keygen", "-F"): (0, ""),
             ("gh", "ssh-key", "add"): (1, "error ghp_ABCDEFGHIJKLMNOPQRSTUV %s https://u:pw@github.com/x" % PRIVADA)}
        d = Doble(comandos={"gh"}, archivos=archivos, respuestas=["ssh", "s"], respuestas_cmd=r)
        _, salida, log, _ = correr(d)
        for secreto in ("SECRETO_PRIVADO_XYZ_123", "ghp_ABCDEFGHIJKLMNOPQRSTUV", "u:pw@"):
            self.assertNotIn(secreto, salida)
            self.assertNotIn(secreto, log)
        self.assertTrue(all(l.endswith(".pub") for l in d.lecturas))
        self.assertTrue(log)

    def test_leer_publica_real_rechaza_privada(self):
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, "id")
            with open(p, "w") as fh:
                fh.write(PRIVADA)
            with self.assertRaises(ValueError):
                ag.Sistema(t).leer_publica(p)

    def test_nada_de_tokens_en_argumentos(self):
        d = Doble(comandos={"gh"}, respuestas_cmd={("gh", "auth", "status"): (1, "")})
        correr(d)
        self.assertFalse(any("token" in c.lower() for c in d.cmds()))

    def test_git_config_solo_si_se_acepta(self):
        r = {**BASE, ("gh", "api", "user/keys"): (0, json.dumps([{"key": "ssh-ed25519 " + CUERPO}])), ("gh", "api", "meta"): (0, META),
             ("ssh-keygen", "-F"): (0, ""), ("ssh", "-T"): (1, "successfully authenticated"), ("git", "config"): (1, "")}
        d = Doble(comandos={"gh"}, archivos={"/casa/.ssh/id_ed25519.pub": PUB}, respuestas=["ssh", "n"], respuestas_cmd=r)
        correr(d)
        self.assertFalse(any(c[:3] == ["git", "config", "--global"] and len(c) == 5 for c in d.ejecutados))


class ModoPlan(unittest.TestCase):
    def test_plan_no_ejecuta_nada_ni_pregunta_ni_escribe(self):
        d = Doble(comandos={"apt"}, archivos={"/casa/.ssh/id_ed25519": PRIVADA})
        with tempfile.TemporaryDirectory() as t:
            codigo, salida, log, _ = correr(d, aplicar=False, salida=t)
            self.assertEqual(os.listdir(t), [])
        self.assertEqual(codigo, 0)
        self.assertEqual(d.ejecutados, [])
        self.assertEqual(d.preguntas, [])
        self.assertEqual(d.anexos, [])
        self.assertIn("MODO PLAN", salida)
        self.assertIn("sudo apt install gh", salida)
        self.assertNotIn("SECRETO_PRIVADO_XYZ_123", salida)

    def test_cli_por_defecto_es_plan(self):
        d = Doble(comandos={"gh"})
        salida = []
        self.assertEqual(ag.main([], sistema=d, escribir=salida.append), 0)
        self.assertEqual(d.ejecutados, [])


if __name__ == "__main__":
    unittest.main()
