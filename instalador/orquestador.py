#!/usr/bin/env python3
"""Orquestador del UNICO COMANDO: de una maquina limpia a una instancia privada lista, con un plan y confirmaciones agrupadas.

Uso: orquestador.py <owner/nombre | URL> [--destino carpeta] [--si] [--plan]

Pasos, en orden (cada uno se salta si ya esta hecho; el avance se guarda en
${XDG_STATE_HOME:-~/.local/state}/meta-harness/instalar-<slug>.json, sin secretos ni rutas de llaves):
  1 ubicacion (avisa si el directorio actual esta en el disco de Windows y trabaja en ~)
  2 paquetes (git, python3, ssh, gh): UN solo `sudo apt update && sudo apt install -y ...`, UNA confirmacion de administrador
  3 acceso a GitHub (instalador/acceso_github.py: sesion con `gh auth login` en ESTA terminal, llave SSH, huella, verificacion)
  4 clonar la instancia (instalar-instancia.py; sin `harness.lock` no se ejecuta `update`)
  5 entorno de la instancia: `.harness/entorno.toml` si existe (contrato en docs/ENTORNO-INSTANCIA.md);
    si no, `scripts/restaurar-entorno.sh` (plan primero, UNA confirmacion, luego --aplicar); si no hay ninguno, termina bien
  6 `harness doctor` y resumen «hecho / omitido / pendiente de ti»

Las bases de datos NO forman parte de la instalacion (ni clientes, ni contenedores, ni respaldos, ni tuneles): el resumen lo recuerda siempre.
Limites: sudo, la sesion de gh en el navegador y cualquier descarga pesada o de red de la instancia SIEMPRE piden confirmacion;
`--si` solo salta las preguntas de bajo riesgo. Sin terminal: se hace lo de bajo riesgo y lo demas queda como pendiente con su comando.
Nunca ejecuta sudo sin confirmar (la contrasena la escribe la persona; el programa no la ve), nunca imprime tokens ni URLs con
credenciales. Todo efecto sobre el sistema pasa por la clase `Sistema`, que se inyecta (pruebas con dobles).
Salida: 0 todo hecho u omitido a proposito; 2 detenido o quedan pendientes de la persona; 3 sin acceso; 4 fallo.
Solo biblioteca estandar.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
AQUI = Path(__file__).resolve().parent
SI = ("s", "si", "sí", "y", "yes")
OWNER_NOMBRE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_.-]+$")
PAQUETE_APT = re.compile(r"^[a-z0-9][a-z0-9.+-]*$")
COMANDO_OK = re.compile(r"^[A-Za-z0-9._+-]+$")
CRED = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s@]+@")
# programa -> paquete apt que lo trae (git, python3, ssh y gh son lo minimo para el acceso y la instancia)
BASE = (("git", "git", "controla las versiones y clona la instancia"),
        ("python3", "python3", "ejecuta el harness"),
        ("ssh", "openssh-client", "habla con GitHub por SSH"),
        ("ssh-keygen", "openssh-client", "crea y comprueba tu llave SSH"),
        ("gh", "gh", "inicia sesion en GitHub y registra tu llave publica"))
ESTADO_VERSION = 1


def cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, AQUI / archivo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ag = cargar("acceso_github_orq", "acceso_github.py")
limpiar = ag.limpiar


def sin_credenciales(texto):
    return CRED.sub(r"\1", texto or "")


class Sistema:
    """Unica puerta hacia el sistema real (comandos, terminal, entorno). Las pruebas la sustituyen por un doble."""

    def __init__(self, home=None, cwd=None, entorno=None):
        self.env = dict(os.environ if entorno is None else entorno)
        self.home = Path(home or self.env.get("HOME") or os.path.expanduser("~"))
        self._cwd = cwd

    def cwd(self):
        return Path(self._cwd or os.getcwd())

    def es_wsl(self):
        return ag.es_wsl_real(self.env)

    def es_root(self):
        return hasattr(os, "geteuid") and os.geteuid() == 0

    def nativo(self, comando):
        """(ruta | None, ruta_de_windows | None): ignora los programas de Windows del PATH de WSL."""
        return ag.buscar_nativo(comando, self.env.get("PATH", ""), self.es_wsl())

    def hay_terminal(self):
        if sys.stdin.isatty():
            return True
        tty = ag.tty_abierta()
        if tty:
            tty.close()
            return True
        return False

    def preguntar(self, texto):
        """Respuesta o None si no hay terminal. Lee de /dev/tty cuando stdin es una tuberia (`curl | sh`)."""
        try:
            if sys.stdin.isatty():
                return input(texto + " ")
            tty = ag.tty_abierta()
            if tty is None:
                return None
            with tty:
                tty.write(texto + " ")
                tty.flush()
                r = tty.readline()
                return r if r else None
        except EOFError:
            return None

    def ejecutar(self, args, cwd=None, interactivo=False, entorno=None):
        """(codigo, salida). interactivo=True: la persona ve y usa la terminal; la salida no se captura."""
        env = dict(self.env)
        env.update(entorno or {})
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            if interactivo:
                tty = None if sys.stdin.isatty() else ag.tty_abierta()
                try:
                    return subprocess.run([str(a) for a in args], cwd=cwd, env=env, stdin=tty).returncode, ""
                finally:
                    if tty:
                        tty.close()
            r = subprocess.run([str(a) for a in args], cwd=cwd, env=env, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL)
            return r.returncode, (r.stdout or "") + (r.stderr or "")
        except (OSError, subprocess.TimeoutExpired) as e:
            return 127, "no se pudo ejecutar: %s" % type(e).__name__


# ------------------------------------------------------------------ contrato .harness/entorno.toml
def _texto(d, clave, errores, donde, obligatorio=True):
    v = d.get(clave)
    if v is None:
        if obligatorio:
            errores.append("%s: falta «%s»." % (donde, clave))
        return None
    if not isinstance(v, str) or not v.strip():
        errores.append("%s: «%s» debe ser un texto no vacio." % (donde, clave))
        return None
    return v.strip()


def _bool(d, clave, defecto, errores, donde):
    v = d.get(clave, defecto)
    if not isinstance(v, bool):
        errores.append("%s: «%s» debe ser true o false (no «%s»)." % (donde, clave, v))
        return defecto
    return v


def _desconocidas(d, permitidas, errores, donde):
    for k in d:
        if k not in permitidas:
            errores.append("%s: clave desconocida «%s» (permitidas: %s)." % (donde, k, ", ".join(sorted(permitidas))))


def ruta_relativa_ok(texto):
    p = Path(texto)
    return not p.is_absolute() and ".." not in p.parts and not texto.startswith("~")


def validar_entorno(datos):
    """(entorno_normalizado, errores). Validacion estricta: claves desconocidas, tipos y rutas que se salen de su base."""
    errores = []
    _desconocidas(datos, {"general", "prerrequisitos", "repositorios", "pasos"}, errores, "entorno.toml")
    gen = datos.get("general", {})
    if not isinstance(gen, dict):
        errores.append("[general] debe ser una tabla.")
        gen = {}
    _desconocidas(gen, {"base_repos"}, errores, "[general]")
    base = gen.get("base_repos", "~/Desktop/Proyectos")
    if not isinstance(base, str) or not base.strip():
        errores.append("[general]: «base_repos» debe ser un texto no vacio.")
        base = "~/Desktop/Proyectos"
    elif base.startswith("~") is False and not Path(base).is_absolute():
        errores.append("[general]: «base_repos» debe ser absoluta o empezar por ~ (recibido «%s»)." % base)
    out = {"base_repos": base, "prerrequisitos": [], "repositorios": [], "pasos": []}
    for clave, permitidas in (("prerrequisitos", None), ("repositorios", None), ("pasos", None)):
        if clave in datos and not isinstance(datos[clave], list):
            errores.append("«%s» debe ser una lista de tablas ([[%s]])." % (clave, clave))
            datos = dict(datos); datos[clave] = []
    for i, e in enumerate(datos.get("prerrequisitos", []), 1):
        d = "[[prerrequisitos]] #%d" % i
        if not isinstance(e, dict):
            errores.append("%s: debe ser una tabla." % d); continue
        _desconocidas(e, {"comando", "para", "instalar_apt", "obligatorio"}, errores, d)
        cmd, para = _texto(e, "comando", errores, d), _texto(e, "para", errores, d)
        if cmd and not COMANDO_OK.match(cmd):
            errores.append("%s: «comando» solo admite letras, numeros y . _ + - (recibido «%s»)." % (d, cmd)); cmd = None
        apt = e.get("instalar_apt")
        paquetes = []
        if apt is not None:
            paquetes = apt.split() if isinstance(apt, str) else apt
            if not isinstance(paquetes, list) or not paquetes or not all(isinstance(x, str) and PAQUETE_APT.match(x) for x in paquetes):
                errores.append("%s: «instalar_apt» debe ser nombres de paquetes apt (texto separado por espacios o lista); recibido «%s»." % (d, apt))
                paquetes = []
        obligatorio = _bool(e, "obligatorio", True, errores, d)
        if cmd and para:
            out["prerrequisitos"].append({"comando": cmd, "para": para, "instalar_apt": paquetes, "obligatorio": obligatorio})
    for i, e in enumerate(datos.get("repositorios", []), 1):
        d = "[[repositorios]] #%d" % i
        if not isinstance(e, dict):
            errores.append("%s: debe ser una tabla." % d); continue
        _desconocidas(e, {"remoto", "destino", "confirmacion"}, errores, d)
        remoto, destino = _texto(e, "remoto", errores, d), _texto(e, "destino", errores, d)
        if remoto and (CRED.search(remoto) or not (OWNER_NOMBRE.match(remoto) or re.match(r"^(https://|ssh://|git@)[^\s]+$", remoto))):
            errores.append("%s: «remoto» debe ser owner/nombre o una URL https/ssh sin credenciales (recibido «%s»)." % (d, sin_credenciales(remoto))); remoto = None
        if destino and not ruta_relativa_ok(destino):
            errores.append("%s: «destino» debe ser una ruta relativa que no salga de la base (recibido «%s»)." % (d, destino)); destino = None
        conf = _bool(e, "confirmacion", True, errores, d)
        if remoto and destino:
            out["repositorios"].append({"remoto": remoto, "destino": destino, "confirmacion": conf})
    vistos = set()
    for i, e in enumerate(datos.get("pasos", []), 1):
        d = "[[pasos]] #%d" % i
        if not isinstance(e, dict):
            errores.append("%s: debe ser una tabla." % d); continue
        _desconocidas(e, {"nombre", "comando", "red", "pesado", "por_defecto", "cwd"}, errores, d)
        nombre = _texto(e, "nombre", errores, d)
        if nombre:
            d = "[[pasos]] #%d («%s»)" % (i, nombre)
            if nombre in vistos:
                errores.append("%s: el nombre esta repetido." % d)
            vistos.add(nombre)
        cmd = e.get("comando")
        if cmd is None:
            errores.append("%s: falta «comando»." % d)
        elif not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) and x for x in cmd):
            errores.append("%s: «comando» debe ser una lista de textos no vacia, sin shell (ej.: [\"npm\", \"install\"])." % d); cmd = None
        red, pesado = _bool(e, "red", False, errores, d), _bool(e, "pesado", False, errores, d)
        pd = e.get("por_defecto", "preguntar")
        if pd not in ("si", "no", "preguntar"):
            errores.append("%s: «por_defecto» debe ser \"si\", \"no\" o \"preguntar\" (recibido «%s»)." % (d, pd)); pd = "preguntar"
        cwd = e.get("cwd", ".")
        if not isinstance(cwd, str) or not ruta_relativa_ok(cwd):
            errores.append("%s: «cwd» debe ser una ruta relativa a la instancia que no salga de ella (recibido «%s»)." % (d, cwd)); cwd = "."
        if nombre and cmd:
            out["pasos"].append({"nombre": nombre, "comando": cmd, "red": red, "pesado": pesado, "por_defecto": pd, "cwd": cwd})
    return out, errores


def leer_entorno(ruta):
    """(entorno | None, errores). Sin ejecutar nada."""
    try:
        datos = tomllib.loads(Path(ruta).read_text(encoding="utf8"))
    except tomllib.TOMLDecodeError as e:
        return None, ["entorno.toml no es TOML valido: %s" % e]
    except (OSError, UnicodeDecodeError) as e:
        return None, ["no se pudo leer entorno.toml: %s" % type(e).__name__]
    ent, errores = validar_entorno(datos)
    return (None if errores else ent), errores


# ------------------------------------------------------------------ orquestador
def slug_de(texto):
    partes = [p for p in re.split(r"[/:]", sin_credenciales(texto).rstrip("/")) if p][-2:]
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", "-".join(partes)).strip("-").removesuffix(".git") or "instancia"


class Orquestador:
    def __init__(self, args, sistema=None, preguntar=None, escribir=print, raiz=RAIZ, acceso=None, hooks_clonar=None, doctor=None):
        self.a = args
        self.s = sistema or Sistema()
        self._preguntar = preguntar or self.s.preguntar
        self._escribir = escribir
        self.raiz = Path(raiz)
        self._acceso = acceso
        self.hooks_clonar = hooks_clonar or {}
        self._doctor = doctor
        self.hecho, self.omitido, self.pendiente = [], [], []
        self.url = self.nombre = None
        self.destino = None

    # ---- utilidades
    def dec(self, t=""):
        self._escribir(limpiar(sin_credenciales(t)))

    def preguntar(self, texto):
        """Respuesta en minusculas, o None sin terminal."""
        r = self._preguntar(limpiar(texto))
        return None if r is None else r.strip().lower()

    def confirmar(self, texto):
        """True solo con un si explicito. Sin terminal: False."""
        return self.preguntar(texto + " [s/N]") in SI

    def pend(self, que, comando=None):
        self.pendiente.append((que, comando))

    # ---- estado (reanudable, sin secretos)
    def ruta_estado(self):
        base = self.s.env.get("XDG_STATE_HOME") or str(self.s.home / ".local" / "state")
        return Path(base) / "meta-harness" / ("instalar-%s.json" % slug_de(self.a.instancia))

    def cargar_estado(self):
        try:
            d = json.loads(self.ruta_estado().read_text(encoding="utf8"))
            if d.get("version") == ESTADO_VERSION and isinstance(d.get("hechos"), list):
                return d
        except (OSError, ValueError):
            pass
        return {"version": ESTADO_VERSION, "hechos": [], "destino": None}

    def guardar_estado(self):
        ruta = self.ruta_estado()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.estado, indent=2, sort_keys=True), encoding="utf8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, ruta)

    def hizo(self, clave):
        return clave in self.estado["hechos"]

    def marcar(self, clave):
        if clave not in self.estado["hechos"]:
            self.estado["hechos"].append(clave)
        self.guardar_estado()

    # ---- entrada
    def resolver(self):
        o = self.a.instancia
        if OWNER_NOMBRE.match(o) and "://" not in o:
            self.url = "git@github.com:%s.git" % o
        else:
            self.url = sin_credenciales(o)
            if self.url != o:
                self.dec("Aviso: se descarto el usuario:token de la URL; se usan las credenciales que ya tienes en el sistema.")
        self.nombre = re.sub(r"\.git$", "", re.split(r"[/:]", self.url.rstrip("/"))[-1]) or "instancia"

    def ubicacion(self):
        cwd = self.s.cwd()
        en_windows = self.s.es_wsl() and bool(ag.RUTA_WINDOWS.match(str(cwd)))
        if en_windows:
            self.dec("AVISO: la carpeta actual (%s) esta en el disco de Windows. Ahi git, permisos y rendimiento fallan en Linux." % cwd)
            self.dec("      Trabajo en tu carpeta de Linux (%s)." % self.s.home)
        base = self.s.home if en_windows else cwd
        if self.a.destino:
            d = Path(self.a.destino).expanduser()
            self.destino = d if d.is_absolute() else base / d
        elif self.estado.get("destino"):
            self.destino = Path(self.estado["destino"])
        else:
            self.destino = base / self.nombre
        return en_windows

    # ---- plan
    def faltantes_base(self):
        """[(programa, paquete, para, solo_windows)] de lo que no existe como programa nativo."""
        falta = []
        for prog, paquete, para in BASE:
            ruta, win = self.s.nativo(prog)
            if not ruta:
                falta.append((prog, paquete, para, win))
        return falta

    def paquetes_de(self, falta):
        orden = []
        for _, p, _, _ in falta:
            if p not in orden:
                orden.append(p)
        return orden

    def comando_apt(self, paquetes):
        pref = [] if self.s.es_root() else ["sudo"]
        texto = "apt update && apt install -y " + " ".join(paquetes)
        return pref + ["sh", "-c", texto] if pref else ["sh", "-c", texto]

    def texto_apt(self, paquetes):
        pref = "" if self.s.es_root() else "sudo "
        return "%sapt update && %sapt install -y %s" % (pref, pref, " ".join(paquetes))

    def mostrar_plan(self, falta, en_windows):
        self.dec("PLAN (todavia no se ha escrito nada)")
        self.dec("  Instancia:  %s" % self.url)
        self.dec("  Carpeta:    %s" % self.destino)
        if falta:
            for prog, paquete, para, win in falta:
                extra = " (solo existe como programa de Windows: %s)" % win if win else ""
                self.dec("  Falta %s (%s)%s" % (prog, para, extra))
            if self.s.nativo("apt")[0]:
                self.dec("  1. Instalar lo que falta con UNA confirmacion de administrador:")
                self.dec("       %s" % self.texto_apt(self.paquetes_de(falta)))
                self.dec("     (te pedira TU contrasena a ti; este programa no la ve y no ejecuta sudo sin tu si)")
            else:
                self.dec("  1. Instalar a mano lo que falta (no hay apt): %s" % ", ".join(self.paquetes_de(falta)))
        else:
            self.dec("  1. Paquetes base (git, python3, ssh, gh): ya estan.")
        self.dec("  2. Acceso a GitHub: sesion con `gh auth login` EN ESTA TERMINAL (codigo de un solo uso + URL; lo apruebas tu en el navegador),")
        self.dec("     llave SSH propia (se reutiliza o se crea; solo se registra la publica), huella de github.com y verificacion.")
        self.dec("  3. Clonar la instancia (si trae harness.lock se fija la version; si no, no se ejecuta `update`).")
        self.dec("  4. Entorno de la instancia: .harness/entorno.toml o scripts/restaurar-entorno.sh. Te mostrare su plan aparte y NO ejecutare")
        self.dec("     nada pesado ni que use la red sin tu confirmacion.")
        self.dec("  5. `harness doctor` y un resumen: hecho / omitido / pendiente de ti.")
        self.dec("  Siempre te pregunto (aunque uses --si): administrador, inicio de sesion en el navegador y descargas pesadas.")
        if self.estado["hechos"]:
            self.dec("  Retomo un intento anterior: ya hecho -> %s." % ", ".join(self.estado["hechos"]))

    # ---- pasos
    def paso_paquetes(self, falta):
        self.dec("\n[1/5] Paquetes base")
        if not falta:
            self.dec("  git, python3, ssh y gh ya estan (como programas de Linux).")
            self.hecho.append("paquetes base ya presentes")
            self.marcar("paquetes")
            return 0
        for prog, _, _, win in falta:
            if win:
                self.dec("  «%s» solo existe como programa de Windows (%s): no sirve dentro de Linux; hay que instalarlo aqui." % (prog, win))
        paquetes = self.paquetes_de(falta)
        if not self.s.nativo("apt")[0]:
            self.dec("  No hay apt. Instala a mano: %s" % ", ".join(paquetes))
            self.pend("instalar los paquetes: %s (con el gestor de tu sistema)" % ", ".join(paquetes))
            return 2
        r = self.instalar_apt(paquetes, "paquetes base")
        if r == 0:
            self.marcar("paquetes")
        return r

    def instalar_apt(self, paquetes, etiqueta):
        """UN solo `sudo apt update && apt install -y ...`, con una confirmacion de administrador (nunca se salta)."""
        if not all(PAQUETE_APT.match(p) for p in paquetes):
            self.dec("  Nombre de paquete no valido: no ejecuto nada.")
            return 4
        texto = self.texto_apt(paquetes)
        self.dec("  Comando (necesita permisos de administrador):")
        self.dec("      %s" % texto)
        self.dec("  Se pedira TU contrasena en esta terminal; este programa no la ve.")
        if not self.confirmar("  ¿Ejecutarlo como administrador?"):
            self.dec("  No se ejecuta. Queda pendiente para ti.")
            self.pend("instalar %s (necesita administrador)" % etiqueta, texto)
            return 2
        codigo, _ = self.s.ejecutar(self.comando_apt(paquetes), interactivo=True)
        if codigo != 0:
            self.dec("  La instalacion termino con codigo %s." % codigo)
            self.pend("instalar %s" % etiqueta, texto)
            return 4
        self.hecho.append("instalados: %s" % ", ".join(paquetes))
        return 0

    def paso_acceso(self):
        self.dec("\n[2/5] Acceso a GitHub")
        if self.hizo("acceso"):
            self.dec("  Ya hecho en un intento anterior: lo salto.")
            self.hecho.append("acceso a GitHub (intento anterior)")
            return 0
        if not self.s.hay_terminal():
            self.dec("  Sin terminal no puedo iniciar sesion ni registrar la llave.")
            self.pend("dejar listo el acceso a GitHub", "bash %s --aplicar --repositorio %s" % (AQUI / "acceso-github.sh", self.url))
            return 2
        if self._acceso:
            codigo = self._acceso(self.url)
        else:
            f = ag.Flujo(ag.Sistema(str(self.s.home)), True, self.url, None, None, self._escribir)
            codigo = f.ejecutar()
        if codigo == 0:
            self.marcar("acceso")
            self.hecho.append("acceso a GitHub (sesion, llave SSH, verificacion)")
            return 0
        self.pend("terminar el acceso a GitHub (el paso que se detuvo te dijo que falta)",
                  "bash %s --aplicar --repositorio %s" % (AQUI / "acceso-github.sh", self.url))
        return 2

    def paso_clonar(self):
        self.dec("\n[3/5] Clonar la instancia")
        if self.hizo("clonar") or (self.destino / ".git").exists():
            self.dec("  Ya esta clonada en %s: la reutilizo." % self.destino)
            self.estado["destino"] = str(self.destino)
            self.marcar("clonar")
            self.hecho.append("instancia clonada en %s" % self.destino)
            return 0
        mod = cargar("instalar_instancia_orq", "instalar-instancia.py")
        buf = []
        argv = [self.url, "--destino", str(self.destino), "--si"]  # el plan ya lo aprobaste arriba
        flujo = _Linea(buf, self.dec)
        codigo = mod.main(argv, raiz=self.raiz, salida=flujo, **self.hooks_clonar)
        flujo.cerrar()
        if codigo != 0:
            self.pend("clonar la instancia", "git clone %s %s" % (self.url, self.destino))
            return 3 if codigo == 3 else 4
        self.estado["destino"] = str(self.destino)
        self.marcar("clonar")
        self.hecho.append("instancia clonada en %s" % self.destino)
        return 0

    # ---- entorno
    def paso_entorno(self):
        self.dec("\n[4/5] Entorno de la instancia")
        toml = self.destino / ".harness" / "entorno.toml"
        restaurar = self.destino / "scripts" / "restaurar-entorno.sh"
        if toml.is_file():
            ent, errores = leer_entorno(toml)
            if errores:
                self.dec("  .harness/entorno.toml no es valido; NO ejecuto nada del entorno. Corrige:")
                for e in errores:
                    self.dec("    - " + e)
                self.pend("corregir .harness/entorno.toml y repetir el mismo comando")
                return 2
            return self.aplicar_entorno(ent)
        if restaurar.is_file():
            return self.restaurar(restaurar)
        self.dec("  La instancia no trae .harness/entorno.toml ni scripts/restaurar-entorno.sh: no hay entorno que preparar.")
        self.omitido.append("entorno (la instancia no declara ninguno)")
        return 0

    def restaurar(self, script):
        if self.hizo("restaurar"):
            self.dec("  Ya restaurado en un intento anterior: lo salto.")
            self.hecho.append("restaurar-entorno (intento anterior)")
            return 0
        codigo, salida = self.s.ejecutar(["bash", script], cwd=self.destino)
        lineas = [l.rstrip() for l in limpiar(sin_credenciales(salida)).splitlines() if l.strip()]
        self.dec("  La instancia trae scripts/restaurar-entorno.sh. Su PLAN (sin --aplicar) dice, en resumen:")
        for l in lineas[:12]:
            self.dec("    | " + l[:160])
        if len(lineas) > 12:
            self.dec("    | ... (%d lineas mas; completo: bash %s)" % (len(lineas) - 12, script))
        cmd = "bash %s --aplicar" % script
        if codigo != 0:
            self.dec("  El plan termino con codigo %s: no lo ejecuto." % codigo)
            self.pend("revisar scripts/restaurar-entorno.sh", "bash %s" % script)
            return 2
        self.dec("  Ejecutarlo con --aplicar instala hooks, memoria, herramientas y repos; el propio script te pregunta lo que sale a la red.")
        self.dec("  OJO: ese script actua sobre tu carpeta personal (HOME: configuracion del agente, hooks, herramientas, repos), no solo sobre")
        self.dec("  la copia clonada en %s. Si solo estas probando, responde N." % self.destino)
        if not self.confirmar("  ¿Ejecutar %s?" % cmd):
            self.dec("  No se ejecuta.")
            self.pend("preparar el entorno de la instancia", cmd)
            return 2
        codigo, _ = self.s.ejecutar(["bash", script, "--aplicar"], cwd=self.destino, interactivo=True)
        if codigo != 0:
            self.dec("  restaurar-entorno.sh --aplicar termino con codigo %s." % codigo)
            self.pend("terminar el entorno de la instancia", cmd)
            return 4
        self.marcar("restaurar")
        self.hecho.append("script de entorno ejecutado (scripts/restaurar-entorno.sh --aplicar; termino con codigo 0)")
        # El codigo 0 no significa "sin pendientes": el script de la instancia lista los suyos y este resumen no los ve.
        self.pend("leer el resumen del propio script de la instancia (arriba): puede listar prerrequisitos o pasos que fallaron aunque su codigo de salida sea 0", None)
        return 0

    def base_repos(self, ent):
        b = Path(ent["base_repos"]).expanduser() if not ent["base_repos"].startswith("~") else self.s.home / ent["base_repos"][2:]
        return b

    def aplicar_entorno(self, ent):
        self.dec("  Leyendo .harness/entorno.toml (valido): %d prerrequisitos, %d repositorios, %d pasos."
                 % (len(ent["prerrequisitos"]), len(ent["repositorios"]), len(ent["pasos"])))
        codigo = 0
        codigo = max(codigo, self.entorno_prerrequisitos(ent["prerrequisitos"]))
        codigo = max(codigo, self.entorno_repositorios(ent))
        codigo = max(codigo, self.entorno_pasos(ent["pasos"]))
        return codigo

    def entorno_prerrequisitos(self, prereqs):
        falta = []
        for p in prereqs:
            ruta, win = self.s.nativo(p["comando"])
            if ruta:
                continue
            if win:
                self.dec("  «%s» solo existe como programa de Windows (%s): no sirve en Linux." % (p["comando"], win))
            falta.append(p)
        if not falta:
            return 0
        self.dec("  Faltan programas: " + ", ".join("%s (%s)" % (p["comando"], p["para"]) for p in falta))
        paquetes = []
        for p in falta:
            for q in p["instalar_apt"]:
                if q not in paquetes:
                    paquetes.append(q)
        resultado = 0
        if paquetes and self.s.nativo("apt")[0]:
            r = self.instalar_apt(paquetes, "los prerrequisitos de la instancia")
            resultado = max(resultado, r)
        for p in falta:
            if self.s.nativo(p["comando"])[0]:
                continue
            if p["obligatorio"]:
                self.pend("instalar «%s» (%s)" % (p["comando"], p["para"]),
                          self.texto_apt(p["instalar_apt"]) if p["instalar_apt"] else None)
                resultado = max(resultado, 2)
            else:
                self.omitido.append("«%s» no esta (opcional: %s)" % (p["comando"], p["para"]))
        return resultado

    def entorno_repositorios(self, ent):
        base = self.base_repos(ent)
        pendientes, resultado = [], 0
        for r in ent["repositorios"]:
            clave = "repo:" + r["destino"]
            destino = base / r["destino"]
            if self.hizo(clave) or (destino / ".git").exists():
                self.marcar(clave)
                self.hecho.append("repositorio %s ya presente" % r["destino"])
                continue
            pendientes.append((r, destino, clave))
        if not pendientes:
            return 0
        con = [x for x in pendientes if x[0]["confirmacion"]]
        autorizados = list(pendientes)
        if con:
            self.dec("  Repositorios a clonar (privados; pueden pesar y usan la red), bajo %s:" % base)
            for r, d, _ in pendientes:
                self.dec("    - %s -> %s%s" % (sin_credenciales(r["remoto"]), r["destino"], "" if r["confirmacion"] else "  (no pide confirmacion)"))
            if not self.confirmar("  ¿Clonar los %d repositorios que piden confirmacion?" % len(con)):
                autorizados = [x for x in pendientes if not x[0]["confirmacion"]]
                for r, d, _ in con:
                    url = "git@github.com:%s.git" % r["remoto"] if OWNER_NOMBRE.match(r["remoto"]) else r["remoto"]
                    self.pend("clonar %s" % r["destino"], "git clone %s %s" % (url, d))
                resultado = 2
        for r, destino, clave in autorizados:
            url = "git@github.com:%s.git" % r["remoto"] if OWNER_NOMBRE.match(r["remoto"]) else sin_credenciales(r["remoto"])
            destino.parent.mkdir(parents=True, exist_ok=True)
            codigo, salida = self.s.ejecutar(["git", "clone", "--quiet", url, str(destino)])
            if codigo != 0:
                self.dec("  Fallo al clonar %s: %s" % (r["destino"], sin_credenciales(salida).strip()[-200:]))
                self.pend("clonar %s" % r["destino"], "git clone %s %s" % (url, destino))
                resultado = max(resultado, 4)
                continue
            self.marcar(clave)
            self.hecho.append("repositorio %s clonado" % r["destino"])
        return resultado

    def entorno_pasos(self, pasos):
        resultado = 0
        cola = []
        for p in pasos:
            clave = "paso:" + p["nombre"]
            if self.hizo(clave):
                self.hecho.append("paso «%s» (intento anterior)" % p["nombre"])
                continue
            if p["por_defecto"] == "no":
                self.omitido.append("paso «%s» (por_defecto = no)" % p["nombre"])
                continue
            cola.append((p, clave))
        riesgosos = [x for x in cola if x[0]["red"] or x[0]["pesado"]]
        comunes = [x for x in cola if x not in riesgosos]
        ejecutar = []
        for p, clave in comunes:
            if p["por_defecto"] == "si" or self.a.si:
                ejecutar.append((p, clave))
            elif self.confirmar("  ¿Ejecutar el paso «%s»? (%s)" % (p["nombre"], " ".join(p["comando"]))):
                ejecutar.append((p, clave))
            else:
                self.omitido.append("paso «%s» (dijiste que no)" % p["nombre"])
        if riesgosos:
            self.dec("  Pasos que usan la red o pesan (siempre piden confirmacion, tambien con --si):")
            for p, _ in riesgosos:
                marcas = ", ".join(m for m, v in (("red", p["red"]), ("pesado", p["pesado"])) if v)
                self.dec("    - %s [%s]: %s" % (p["nombre"], marcas, " ".join(p["comando"])))
            if self.confirmar("  ¿Ejecutar estos %d pasos?" % len(riesgosos)):
                ejecutar += riesgosos
            else:
                for p, _ in riesgosos:
                    self.pend("paso «%s»" % p["nombre"], "cd %s && %s" % (self.destino / p["cwd"], " ".join(p["comando"])))
                resultado = 2
        orden = {p["nombre"]: i for i, p in enumerate(pasos)}
        for p, clave in sorted(ejecutar, key=lambda x: orden[x[0]["nombre"]]):
            cwd = (self.destino / p["cwd"]).resolve()
            if self.destino.resolve() not in (cwd, *cwd.parents):
                self.dec("  «%s»: su cwd se sale de la instancia; no lo ejecuto." % p["nombre"])
                resultado = max(resultado, 4)
                continue
            self.dec("  Ejecutando «%s»: %s" % (p["nombre"], " ".join(p["comando"])))
            codigo, _ = self.s.ejecutar(p["comando"], cwd=cwd, interactivo=True)
            if codigo != 0:
                self.dec("  «%s» termino con codigo %s." % (p["nombre"], codigo))
                self.pend("paso «%s»" % p["nombre"], "cd %s && %s" % (cwd, " ".join(p["comando"])))
                resultado = max(resultado, 4)
            else:
                self.marcar(clave)
                self.hecho.append("paso «%s»" % p["nombre"])
        return resultado

    # ---- final
    def paso_doctor(self):
        self.dec("\n[5/5] harness doctor")
        if self._doctor:
            codigo, salida = self._doctor(self.destino)
        else:
            codigo, salida = self.s.ejecutar([sys.executable, self.raiz / "cli" / "harness_cli.py", "doctor", self.destino])
        self.dec(salida.rstrip() or "(sin salida)")
        (self.hecho if codigo == 0 else self.omitido).append("harness doctor" if codigo == 0 else "harness doctor con avisos (codigo %s)" % codigo)

    def resumen(self):
        self.dec("\nRESUMEN")
        self.dec("  Hecho:")
        for h in self.hecho or ["(nada nuevo)"]:
            self.dec("    + " + h)
        if self.omitido:
            self.dec("  Omitido:")
            for o in self.omitido:
                self.dec("    - " + o)
        if self.pendiente:
            self.dec("  Pendiente de ti:")
            for que, cmd in self.pendiente:
                self.dec("    * " + que)
                if cmd:
                    self.dec("        " + cmd)
            self.dec("  Cuando lo hagas, repite el mismo comando: retoma donde se quedo.")
        else:
            self.dec("  Nada pendiente.")
        self.dec("\n  Acceso a datos (lo das tu)")
        self.dec("    La base de datos es la fuente de evidencia mas fuerte del sistema y NO se instala aqui: cada proyecto accede de forma distinta.")
        self.dec("    Sin tu acceso el entorno trabaja en modo degradado y no afirma nada sobre datos.")
        self.dec("    Para darlo: declara los ambientes en politicas.toml y tu acceso personal en acceso.local.toml (no se versiona),")
        self.dec("    y comprueba con:  python3 instalador/preflight-accesos.py")

    def ejecutar(self):
        self.resolver()
        self.estado = self.cargar_estado()
        en_windows = self.ubicacion()
        falta = self.faltantes_base()
        self.mostrar_plan(falta, en_windows)
        if self.a.plan:
            self.dec("\n(--plan: no se hizo nada.)")
            return 0
        if not self.a.si:
            if not self.s.hay_terminal():
                self.dec("\nSin terminal interactiva y sin --si: solo se mostro el plan. No se instalo nada.")
                return 0
            if self.preguntar("\n¿Aplicar este plan? [s/N]") not in SI:
                self.dec("Cancelado. No se escribio nada.")
                return 0
        if self.hecho_previo():
            self.dec("\nRetomo: salto lo ya hecho (%s)." % ", ".join(self.estado["hechos"]))
        codigo = 0
        for paso, critico in ((lambda: self.paso_paquetes(falta), True), (self.paso_acceso, True),
                              (self.paso_clonar, True), (self.paso_entorno, False)):
            r = paso()
            codigo = max(codigo, r)
            if r and critico:   # sin esto no se puede seguir: se corta y el resumen dice que falta
                break
        if self.destino and (self.destino / ".git").exists():
            self.paso_doctor()
        self.resumen()
        return codigo

    def hecho_previo(self):
        return bool(self.estado["hechos"])


class _Linea:
    """Flujo de texto que reenvia cada linea completa a `decir` (para capturar la salida de instalar-instancia)."""

    def __init__(self, buf, decir):
        self.buf, self.decir = buf, decir
        self.en_plan = False   # su plan propio se omite: el plan unico ya se mostro (y aprobo) al principio

    def write(self, t):
        self.buf.append(t)
        while "\n" in "".join(self.buf):
            junto = "".join(self.buf)
            linea, resto = junto.split("\n", 1)
            self.buf[:] = [resto] if resto else []
            if linea.startswith("PLAN ("):
                self.en_plan = True
                continue
            if self.en_plan and linea.startswith("  "):
                continue
            self.en_plan = False
            self.decir("  " + linea)
        return len(t)

    def flush(self):
        pass

    def cerrar(self):
        resto = "".join(self.buf)
        self.buf[:] = []
        if resto.strip():
            self.decir("  " + resto)


def parser():
    p = argparse.ArgumentParser(prog="orquestador.py", description="Instala una instancia de principio a fin (un plan, confirmaciones agrupadas, reanudable).")
    p.add_argument("instancia", help="owner/nombre o URL del repositorio de la instancia")
    p.add_argument("--destino", help="carpeta donde clonar (por defecto, ./<nombre>, o ~/<nombre> si estas en el disco de Windows)")
    p.add_argument("--si", action="store_true", help="salta SOLO las preguntas de bajo riesgo (no sudo, ni sesion en el navegador, ni descargas pesadas)")
    p.add_argument("--plan", action="store_true", help="solo muestra el plan")
    return p


def main(argv=None, sistema=None, preguntar=None, salida=None, raiz=RAIZ, acceso=None, hooks_clonar=None, doctor=None):
    a = parser().parse_args(argv)
    flujo = salida or sys.stdout
    o = Orquestador(a, sistema, preguntar, lambda t="": print(t, file=flujo), raiz, acceso, hooks_clonar, doctor)
    try:
        return o.ejecutar()
    except KeyboardInterrupt:
        o.dec("\nInterrumpido. Lo hecho queda guardado; repite el mismo comando para retomar.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
