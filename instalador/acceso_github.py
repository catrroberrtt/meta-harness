#!/usr/bin/env python3
"""Deja listo el acceso a GitHub, paso a paso, con confirmacion en cada paso.

Uso:
    python3 acceso_github.py [--aplicar] [--repositorio <url>] [--salida <carpeta>] [--titulo <texto>]

Sin --aplicar (modo plan, por defecto) solo muestra lo que haria: no ejecuta ningun comando,
no pregunta, no escribe nada. Con --aplicar recorre los pasos y pide confirmacion antes de cada accion.

Pasos: 1 gh instalado · 2 sesion de gh · 3 metodo (SSH o HTTPS) · 4 llave SSH (reutiliza o genera)
y registro de la llave PUBLICA · 5 permiso admin:public_key y SSO · 6 huella de github.com contra las
oficiales · 7 verificacion de punta a punta · 8 nombre y correo de git (solo si se acepta).

Garantias:
- Nunca lee, imprime ni copia una llave privada: solo se leen archivos que terminan en .pub.
- Nunca imprime tokens ni URLs con credenciales; nunca pasa tokens por argumentos.
- Nunca ejecuta `curl | sh`; nunca ejecuta una instalacion ni pide administrador sin confirmacion.
- Nunca sobrescribe una llave existente.
- Registra en <salida>/acceso-github.log solo acciones y resultados (sin secretos).
- Toda accion sobre el sistema pasa por la clase `Sistema`, que se inyecta (pruebas con dobles).

Codigos de salida: 0 listo · 1 uso incorrecto · 2 detenido: falta algo que otra persona debe dar
o hacer · 3 cancelado por la persona.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import socket
import subprocess
import sys

SI = ("s", "si", "sí", "y", "yes")

# gestor -> (comando de instalacion oficial, necesita administrador)
GESTORES = (
    ("apt", ["sudo", "apt", "install", "gh"], True),
    ("dnf", ["sudo", "dnf", "install", "gh"], True),
    ("yum", ["sudo", "yum", "install", "gh"], True),
    ("pacman", ["sudo", "pacman", "-S", "github-cli"], True),
    ("zypper", ["sudo", "zypper", "install", "gh"], True),
    ("brew", ["brew", "install", "gh"], False),
    ("winget", ["winget", "install", "--id", "GitHub.cli"], False),
    ("choco", ["choco", "install", "gh"], True),
)
CANDIDATAS = ("id_ed25519.pub", "id_ecdsa.pub", "id_ed25519_sk.pub", "id_ecdsa_sk.pub", "id_rsa.pub")
MIN_RSA = 3072

PATRONES_SECRETOS = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(-----END [A-Z ]*PRIVATE KEY-----|$)", re.S), "[llave privada omitida]"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,})"), "[token omitido]"),
    (re.compile(r"(://)[^/\s:@]+(:[^/\s@]*)?@"), r"\1[credenciales omitidas]@"),
)


def limpiar(texto):
    """Quita de cualquier texto tokens, URLs con credenciales y bloques de llave privada."""
    for patron, reemplazo in PATRONES_SECRETOS:
        texto = patron.sub(reemplazo, texto or "")
    return texto


class Sistema:
    """Unica puerta hacia el sistema real. Las pruebas la sustituyen por un doble."""

    def __init__(self, home=None):
        self.home = home or os.path.expanduser("~")

    def existe(self, comando):
        return shutil.which(comando) is not None

    def ejecutar(self, args, entrada=None, interactivo=False, entorno=None):
        """Devuelve (codigo, salida). Con interactivo=True el comando usa la terminal de la persona
        (frases de contrasena, navegador) y la salida no se captura."""
        env = dict(os.environ)
        env.update(entorno or {})
        try:
            if interactivo:
                return subprocess.run(args, env=env).returncode, ""
            r = subprocess.run(args, input=entrada, capture_output=True, text=True, env=env, timeout=120)
            return r.returncode, (r.stdout or "") + (r.stderr or "")
        except (OSError, subprocess.TimeoutExpired) as e:
            return 127, "no se pudo ejecutar: %s" % type(e).__name__

    def existe_ruta(self, ruta):
        return os.path.lexists(ruta)

    def leer_publica(self, ruta):
        if not ruta.endswith(".pub"):
            raise ValueError("solo se leen llaves publicas (.pub)")
        try:
            with open(ruta, encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    def anexar(self, ruta, texto):
        os.makedirs(os.path.dirname(ruta), mode=0o700, exist_ok=True)
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(texto)

    def preguntar(self, texto, defecto=""):
        try:
            r = input(texto + " ")
        except EOFError:
            return defecto
        return r.strip() or defecto

    def maquina(self):
        return socket.gethostname()

    def hoy(self):
        return datetime.date.today().isoformat()


class Flujo:
    def __init__(self, sistema, aplicar=False, repositorio=None, salida=None, titulo=None, escribir=print):
        self.s = sistema
        self.aplicar = aplicar
        self.repositorio = repositorio
        self.salida = salida
        self.titulo = titulo
        self._escribir = escribir
        self.ssh_dir = os.path.join(sistema.home, ".ssh")

    # --- utilidades -------------------------------------------------------------------------
    def dec(self, texto=""):
        self._escribir(limpiar(texto))

    def log(self, accion, resultado):
        if not (self.aplicar and self.salida):
            return
        os.makedirs(self.salida, exist_ok=True)
        marca = datetime.datetime.now().isoformat(timespec="seconds")
        with open(os.path.join(self.salida, "acceso-github.log"), "a", encoding="utf-8") as f:
            f.write("%s | %s | %s\n" % (marca, limpiar(accion), limpiar(resultado)))

    def confirmar(self, texto):
        return self.s.preguntar(texto + " [s/N]", "n").lower() in SI

    def correr(self, args, **kw):
        codigo, salida = self.s.ejecutar(args, **kw)
        self.log("ejecutar: " + " ".join(args[:3]), "codigo %s" % codigo)
        return codigo, limpiar(salida)

    def titulo_llave(self):
        return self.titulo or "%s %s" % (self.s.maquina(), self.s.hoy())

    # --- paso 1: gh -------------------------------------------------------------------------
    def gestor(self):
        for nombre, cmd, admin in GESTORES:
            if self.s.existe(nombre):
                return nombre, cmd, admin
        return None

    def instrucciones_a_mano(self):
        self.dec("Instala la herramienta de GitHub (gh) a mano siguiendo la guia oficial:")
        self.dec("  https://cli.github.com  (apartado Installation de tu sistema) y vuelve a ejecutar este paso.")

    def paso_gh(self):
        self.dec("[1/7] Herramienta gh")
        if self.s.existe("gh"):
            self.dec("  gh ya esta instalado.")
            return 0
        g = self.gestor()
        if not g:
            self.dec("  gh no esta instalado y no se detecto un gestor de paquetes conocido.")
            self.instrucciones_a_mano()
            self.log("gh", "sin gestor: instrucciones a mano")
            return 2
        nombre, cmd, admin = g
        self.dec("  gh no esta instalado. Gestor detectado: %s. Comando completo:" % nombre)
        self.dec("      " + " ".join(cmd))
        if not self.aplicar:
            return 0
        if not self.confirmar("  ¿Ejecutar este comando?"):
            self.instrucciones_a_mano()
            self.log("gh", "instalacion rechazada")
            return 2
        if admin:
            self.dec("  ATENCION: este comando necesita permisos de administrador (te pedira tu contrasena a ti, no a este programa).")
            if not self.confirmar("  ¿Confirmas ejecutarlo con permisos de administrador?"):
                self.instrucciones_a_mano()
                self.log("gh", "administrador no confirmado")
                return 2
        codigo, _ = self.correr(cmd, interactivo=True)
        if codigo != 0 or not self.s.existe("gh"):
            self.dec("  La instalacion no termino bien (codigo %s)." % codigo)
            self.instrucciones_a_mano()
            return 2
        self.dec("  gh instalado.")
        return 0

    # --- paso 2: sesion ---------------------------------------------------------------------
    def paso_sesion(self):
        self.dec("[2/7] Sesion en GitHub")
        codigo, _ = self.correr(["gh", "auth", "status"])
        if codigo == 0:
            self.dec("  Ya hay una sesion iniciada.")
            return 0
        self.dec("  No hay sesion. En otra terminal ejecuta:  gh auth login")
        self.dec("  (inicias sesion tu en el navegador; este programa no ve ni guarda tu contrasena ni tu token).")
        self.s.preguntar("  Pulsa Enter cuando hayas terminado:", "")
        codigo, _ = self.correr(["gh", "auth", "status"])
        if codigo != 0:
            self.dec("  Sigue sin haber sesion. Me detengo; repite cuando hayas ejecutado `gh auth login`.")
            return 2
        self.dec("  Sesion detectada.")
        return 0

    # --- paso 3: metodo ---------------------------------------------------------------------
    def paso_metodo(self):
        self.dec("[3/7] Metodo de acceso")
        r = self.s.preguntar("  ¿SSH (recomendado) o HTTPS por gh? [ssh/https]:", "ssh").lower()
        return "https" if r.startswith("h") else "ssh"

    def https(self):
        self.dec("  Se configurara git para usar las credenciales de gh:  gh auth setup-git")
        if not self.confirmar("  ¿Ejecutarlo?"):
            return 3
        codigo, salida = self.correr(["gh", "auth", "setup-git"])
        if codigo != 0:
            self.dec("  Fallo: " + salida.strip()[:300])
            return 2
        self.dec("  git usara gh como gestor de credenciales.")
        return 0

    # --- paso 4: llave SSH ------------------------------------------------------------------
    def huella(self, ruta_pub):
        codigo, salida = self.correr(["ssh-keygen", "-lf", ruta_pub])
        m = re.match(r"^(\d+)\s+(SHA256:\S+)\s+.*\((\w+)\)\s*$", salida.strip().splitlines()[0] if salida.strip() else "")
        if codigo != 0 or not m:
            return None
        return int(m.group(1)), m.group(2), m.group(3).upper()

    def buscar_llave(self):
        for nombre in CANDIDATAS:
            ruta = os.path.join(self.ssh_dir, nombre)
            if not self.s.existe_ruta(ruta):
                continue
            h = self.huella(ruta)
            if not h:
                continue
            bits, fp, tipo = h
            if tipo == "RSA" and bits < MIN_RSA:
                self.dec("  %s es RSA de %d bits (< %d): no se usa." % (nombre, bits, MIN_RSA))
                continue
            if tipo == "DSA":
                continue
            return ruta, fp
        return None

    def ruta_nueva(self):
        base = os.path.join(self.ssh_dir, "id_ed25519")
        if not self.s.existe_ruta(base) and not self.s.existe_ruta(base + ".pub"):
            return base
        i = 0
        while True:
            ruta = base + "_github" + ("" if i == 0 else "_%d" % (i + 1))
            if not self.s.existe_ruta(ruta) and not self.s.existe_ruta(ruta + ".pub"):
                return ruta
            i += 1

    def generar_llave(self):
        ruta = self.ruta_nueva()
        if ruta != os.path.join(self.ssh_dir, "id_ed25519"):
            self.dec("  Ya existe %s; no se toca. Se usara otro nombre: %s" % (os.path.join(self.ssh_dir, "id_ed25519"), ruta))
        titulo = self.titulo_llave()
        cmd = ["ssh-keygen", "-t", "ed25519", "-C", titulo, "-f", ruta]
        self.dec("  No hay una llave SSH utilizable. Se generara una nueva (ed25519):")
        self.dec("      " + " ".join(cmd))
        self.dec("  ssh-keygen te pedira una frase de contrasena: se recomienda ponerla (la escribes tu, yo no la veo).")
        if not self.confirmar("  ¿Generar la llave?"):
            return None
        codigo, _ = self.correr(cmd, interactivo=True)
        if codigo != 0 or not self.s.existe_ruta(ruta + ".pub"):
            self.dec("  No se pudo generar la llave (codigo %s)." % codigo)
            return None
        if self.s.existe("ssh-add") and self.confirmar("  ¿Añadirla al ssh-agent (ssh-add)?"):
            codigo, _ = self.correr(["ssh-add", ruta], interactivo=True)
            if codigo != 0:
                self.dec("  ssh-add no funciono (¿hay un ssh-agent activo?). No es grave: se puede añadir despues.")
        h = self.huella(ruta + ".pub")
        return (ruta + ".pub", h[1]) if h else None

    def cuerpo(self, texto):
        partes = (texto or "").split()
        return partes[1] if len(partes) >= 2 else None

    def ya_registrada(self, cuerpo):
        codigo, salida = self.correr(["gh", "api", "user/keys"])
        if codigo != 0:
            return False
        try:
            return any(self.cuerpo(k.get("key", "")) == cuerpo for k in json.loads(salida))
        except (ValueError, AttributeError, TypeError):
            return False

    def clasificar_error_registro(self, salida):
        t = salida.lower()
        if "saml" in t or "sso" in t:
            return "sso"
        if "already in use" in t or "already exists" in t or "key is already" in t:
            return "duplicada"
        if "admin:public_key" in t or "scope" in t or "permission" in t or "403" in t or "forbidden" in t:
            return "permiso"
        return "otro"

    def explicar_sso(self):
        self.dec("  La organizacion exige SSO: la llave debe AUTORIZARSE para esa organizacion.")
        self.dec("  Donde: GitHub → Settings → SSH and GPG keys → junto a la llave, «Configure SSO» → «Authorize» la organizacion.")
        self.dec("  Me detengo; autorizala y repite.")

    def paso_ssh(self):
        self.dec("[4/7] Llave SSH")
        llave = self.buscar_llave()
        if llave:
            self.dec("  Se reutiliza la llave existente: %s (huella %s)" % (llave[0], llave[1]))
        else:
            llave = self.generar_llave()
            if not llave:
                return 3
        ruta_pub, fp = llave
        texto = self.s.leer_publica(ruta_pub)
        cuerpo = self.cuerpo(texto)
        if not cuerpo:
            self.dec("  No se pudo leer la llave publica %s." % ruta_pub)
            return 2
        if self.ya_registrada(cuerpo):
            self.dec("  Esta llave ya esta registrada en tu cuenta (misma llave/huella): no se duplica.")
            self.log("registro", "ya registrada")
            return 0
        titulo = self.titulo_llave()
        self.dec("  Se registrara SOLO la llave publica en tu cuenta de GitHub:")
        self.dec("      titulo: %s" % titulo)
        self.dec("      huella: %s" % fp)
        self.dec('      gh ssh-key add %s --title "%s"' % (ruta_pub, titulo))
        if not self.confirmar("  ¿Registrarla?"):
            return 3
        return self.registrar(ruta_pub, titulo)

    def registrar(self, ruta_pub, titulo, reintento=True):
        codigo, salida = self.correr(["gh", "ssh-key", "add", ruta_pub, "--title", titulo])
        if codigo == 0:
            self.dec("  Llave registrada.")
            self.log("registro", "ok")
            return 0
        causa = self.clasificar_error_registro(salida)
        self.log("registro", "fallo: " + causa)
        if causa == "duplicada":
            self.dec("  GitHub dice que la llave ya esta registrada: no se duplica.")
            return 0
        if causa == "sso":
            self.explicar_sso()
            return 2
        if causa == "permiso":
            self.dec("  Tu sesion de gh no tiene el permiso `admin:public_key` para registrar llaves.")
            self.dec("  Se puede ampliar con:  gh auth refresh -s admin:public_key  (se abre el navegador; lo apruebas tu).")
            if reintento and self.confirmar("  ¿Ejecutarlo ahora?"):
                c, _ = self.correr(["gh", "auth", "refresh", "-s", "admin:public_key"], interactivo=True)
                if c == 0:
                    return self.registrar(ruta_pub, titulo, reintento=False)
            return 2
        self.dec("  Fallo al registrar: " + salida.strip()[:300])
        return 2

    # --- paso 6: huella del servidor --------------------------------------------------------
    def oficiales(self):
        codigo, salida = self.correr(["gh", "api", "meta"])
        if codigo != 0:
            return None
        try:
            datos = json.loads(salida).get("ssh_key_fingerprints") or {}
        except (ValueError, AttributeError):
            return None
        valores = {str(v).replace("SHA256:", "") for v in datos.values()}
        return valores or None

    def paso_servidor(self):
        self.dec("[5/7] Huella de github.com")
        known = os.path.join(self.ssh_dir, "known_hosts")
        codigo, _ = self.correr(["ssh-keygen", "-F", "github.com", "-f", known])
        if codigo == 0:
            self.dec("  github.com ya esta en known_hosts.")
            return 0
        oficiales = self.oficiales()
        if not oficiales:
            self.dec("  No pude obtener las huellas oficiales (gh api meta). NO acepto la huella del servidor; reintenta con red y sesion.")
            return 2
        codigo, escaneo = self.correr(["ssh-keyscan", "-t", "ed25519,ecdsa,rsa", "github.com"])
        lineas = [l for l in escaneo.splitlines() if l.strip() and not l.startswith("#")]
        if codigo != 0 or not lineas:
            self.dec("  No pude obtener la huella que presenta el servidor. NO la acepto.")
            return 2
        buenas = []
        for l in lineas:
            c, salida = self.correr(["ssh-keygen", "-lf", "-"], entrada=l + "\n")
            m = re.search(r"SHA256:(\S+)", salida)
            if c != 0 or not m or m.group(1) not in oficiales:
                self.dec("  La huella que presenta el servidor NO coincide con las oficiales de GitHub. NO la acepto (posible interceptacion de la red).")
                self.log("known_hosts", "huella distinta: rechazada")
                return 2
            buenas.append(l)
        self.dec("  La huella del servidor coincide con las oficiales de GitHub.")
        if not self.confirmar("  ¿Añadir github.com a %s?" % known):
            return 3
        self.s.anexar(known, "\n".join(buenas) + "\n")
        self.log("known_hosts", "añadido")
        return 0

    # --- paso 7: verificacion ---------------------------------------------------------------
    def causa_fallo(self, salida):
        t = salida.lower()
        if "saml" in t or "sso" in t:
            return ("sin autorizacion SSO", "Autoriza la llave para la organizacion: GitHub → Settings → SSH and GPG keys → Configure SSO → Authorize. Si no ves la opcion, pidelo a quien administra la organizacion.")
        if "resolve hostname" in t or "timed out" in t or "unreachable" in t or "connection refused" in t or "could not resolve" in t:
            return ("red", "Revisa tu conexion, VPN o proxy; si una red corporativa bloquea el puerto 22, pidele a quien administra la red que lo permita (o usa HTTPS).")
        if "host key verification failed" in t:
            return ("huella del servidor no aceptada", "Ejecuta de nuevo el paso de huella de github.com (compara contra las oficiales) antes de seguir.")
        if "permission denied (publickey" in t or "could not read username" in t or "authentication failed" in t:
            return ("sin llave o sin sesion valida", "Tu llave no esta registrada en tu cuenta o no la usa el agente: repite el registro de la llave publica; para HTTPS ejecuta `gh auth setup-git`.")
        if "repository not found" in t or "not found" in t or "denied" in t or "403" in t or "access" in t:
            return ("sin permiso en el repositorio", "Pide a quien administra el repositorio o la organizacion que te dé acceso de lectura (rol Read) a ese repositorio, y confirma el nombre exacto.")
        return ("causa no identificada", "Revisa el mensaje y pide ayuda a quien administra la organizacion de GitHub.")

    def paso_verificar(self, metodo):
        self.dec("[6/7] Verificacion de punta a punta")
        if metodo == "ssh":
            codigo, salida = self.correr(["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "git@github.com"])
            if "successfully authenticated" in salida.lower():
                self.dec("  ssh -T git@github.com: autenticado.")
            else:
                causa, pedir = self.causa_fallo(salida)
                self.dec("  ssh -T git@github.com fallo. Causa probable: %s." % causa)
                self.dec("  Que hacer / a quien pedir: %s" % pedir)
                return 2
        if self.repositorio:
            if re.search(r"://[^/\s@]+@", self.repositorio):
                self.dec("  La URL del repositorio lleva credenciales: no la uso. Pasa la URL sin usuario ni clave.")
                return 1
            codigo, salida = self.correr(["git", "ls-remote", self.repositorio], entorno={"GIT_TERMINAL_PROMPT": "0"})
            if codigo != 0:
                causa, pedir = self.causa_fallo(salida)
                self.dec("  git ls-remote %s fallo. Causa probable: %s." % (self.repositorio, causa))
                self.dec("  Que hacer / a quien pedir: %s" % pedir)
                return 2
            self.dec("  git ls-remote %s: acceso confirmado." % self.repositorio)
        else:
            self.dec("  (Sin --repositorio: no se comprobo el acceso a un repositorio concreto.)")
        return 0

    # --- paso 8: git config -----------------------------------------------------------------
    def paso_git_config(self):
        self.dec("[7/7] Identidad de git (opcional)")
        faltan = []
        for clave in ("user.name", "user.email"):
            c, v = self.correr(["git", "config", "--global", clave])
            if c != 0 or not v.strip():
                faltan.append(clave)
        if not faltan:
            self.dec("  git ya tiene nombre y correo globales; no se cambia nada.")
            return 0
        if not self.confirmar("  Falta %s en la configuracion global de git. ¿Configurarlos?" % ", ".join(faltan)):
            self.dec("  Se deja sin cambiar.")
            return 0
        for clave in faltan:
            valor = self.s.preguntar("  %s:" % clave, "")
            if valor:
                self.correr(["git", "config", "--global", clave, valor])
        return 0

    # --- orquestacion -----------------------------------------------------------------------
    def plan(self):
        self.dec("MODO PLAN (no se ejecuta nada; usa --aplicar para hacerlo, con confirmacion en cada paso)")
        self.paso_gh()
        self.dec("[2/7] Comprobaria `gh auth status`; si no hay sesion, te indicaria `gh auth login`.")
        self.dec("[3/7] Preguntaria SSH (por defecto) o HTTPS (`gh auth setup-git`).")
        self.dec("[4/7] Buscaria una llave en %s (%s; RSA solo >= %d bits) y la reutilizaria;" % (self.ssh_dir, ", ".join(CANDIDATAS), MIN_RSA))
        self.dec("      si no hay: `ssh-keygen -t ed25519 -C \"<titulo>\"` en una ruta que no exista (tu pones la frase),")
        self.dec("      `ssh-add`, y `gh ssh-key add <llave>.pub --title \"%s\"` mostrando titulo y huella antes." % self.titulo_llave())
        self.dec("      Si falta el permiso: `gh auth refresh -s admin:public_key`. Si la organizacion exige SSO: te explicaria como autorizar la llave.")
        self.dec("[5/7] Compararia la huella de github.com (`ssh-keyscan`) con las oficiales (`gh api meta`) antes de aceptarla.")
        self.dec("[6/7] Verificaria `ssh -T git@github.com`%s." % (" y `git ls-remote %s`" % limpiar(self.repositorio) if self.repositorio else ""))
        self.dec("[7/7] Ofreceria configurar nombre y correo de git solo si faltan y lo aceptas.")
        return 0

    def ejecutar(self):
        if not self.aplicar:
            return self.plan()
        self.log("inicio", "aplicar")
        for paso in (self.paso_gh, self.paso_sesion):
            r = paso()
            if r:
                return r
        metodo = self.paso_metodo()
        if metodo == "https":
            r = self.https()
        else:
            r = self.paso_ssh() or self.paso_servidor()
        if r:
            return r
        r = self.paso_verificar(metodo)
        if r:
            return r
        self.paso_git_config()
        self.dec("Listo: acceso a GitHub verificado.")
        self.log("fin", "ok")
        return 0


def main(argv=None, sistema=None, escribir=print):
    p = argparse.ArgumentParser(description="Deja listo el acceso a GitHub (plan por defecto).")
    p.add_argument("--aplicar", action="store_true", help="ejecuta los pasos, con confirmacion en cada uno")
    p.add_argument("--repositorio", help="URL de un repositorio para comprobar el acceso")
    p.add_argument("--salida", default=".", help="carpeta del registro acceso-github.log (defecto: la actual)")
    p.add_argument("--titulo", help="titulo de la llave (defecto: <maquina> <fecha>)")
    a = p.parse_args(argv)
    f = Flujo(sistema or Sistema(), a.aplicar, a.repositorio, a.salida, a.titulo, escribir)
    try:
        return f.ejecutar()
    except KeyboardInterrupt:
        f.dec("Cancelado.")
        return 3


if __name__ == "__main__":
    sys.exit(main())
