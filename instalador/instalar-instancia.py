#!/usr/bin/env python3
"""Instalar una instancia privada (R40/R41): comprueba el acceso ANTES de clonar.

Uso: instalar-instancia.py <repositorio-de-la-instancia> [--destino carpeta] [--solo-lectura] [--si]

Flujo: 1) valida el destino (nuevo o vacio, fuera de otro repositorio); 2) comprueba el acceso con las
credenciales que la persona YA tiene (`git ls-remote`, sin preguntar contrasenas); sin permiso se detiene
y dice que pedir y a quien (el comando publico sigue sirviendo para `init`); 3) muestra el plan y pide
confirmacion (sin terminal y sin --si: solo muestra el plan); 4) clona, lee `harness.lock` y lo compara con
el harness instalado; 5) ejecuta `instalar.sh update <destino> --aplicar` (con --solo-lectura, sin --aplicar).
Un `restaurar.sh` de la instancia NUNCA se ejecuta con --si: solo con confirmacion explicita, en terminal.
No guarda ni imprime credenciales: cualquier `usuario:token@` de la URL se descarta y se limpia en toda salida.
Salida: 0 hecho o solo plan; 2 uso/destino invalido; 3 sin acceso; 4 fallo al clonar o actualizar.
Solo biblioteca estandar.
"""
import argparse
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CRED = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s@]+@")


def limpiar(texto):
    """Quita usuario:token@ de cualquier URL con esquema."""
    return CRED.sub(r"\1", texto or "")


def nombre_de(repo):
    base = re.split(r"[/:]", limpiar(repo).rstrip("/"))[-1]
    return re.sub(r"\.git$", "", base) or "instancia"


def acceso_por_defecto(repo, tiempo=20):
    """(ok, motivo). Solo lectura (`git ls-remote`), sin preguntar contrasenas."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="true", SSH_ASKPASS="true")
    try:
        p = subprocess.run(["git", "ls-remote", "--exit-code", "--heads", repo], capture_output=True,
                           text=True, timeout=tiempo, env=env, stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        return False, "no esta instalado git"
    except subprocess.TimeoutExpired:
        return False, "sin respuesta en %s s" % tiempo
    if p.returncode in (0, 2):  # 2: el repositorio responde pero sin ramas
        return True, ""
    return False, limpiar((p.stderr or "").strip().splitlines()[-1] if p.stderr.strip() else "acceso denegado")


def ejecutar_por_defecto(cmd):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(cmd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)


def repo_ancestro(carpeta):
    p = Path(carpeta).resolve().parent
    while True:
        if (p / ".git").exists():
            return p
        if p.parent == p:
            return None
        p = p.parent


def main(argv=None, comprobar=acceso_por_defecto, ejecutar=ejecutar_por_defecto, es_terminal=None,
         preguntar=input, raiz=RAIZ, salida=None):
    out = salida or sys.stdout

    def decir(t=""):
        print(limpiar(t), file=out)

    ap = argparse.ArgumentParser(prog="instalar-instancia.py", add_help=True)
    ap.add_argument("repositorio")
    ap.add_argument("--destino")
    ap.add_argument("--solo-lectura", action="store_true")
    ap.add_argument("--si", action="store_true")
    a = ap.parse_args(argv)
    repo = limpiar(a.repositorio)
    if repo != a.repositorio:
        decir("Aviso: se descarto el usuario:token de la URL; se usan las credenciales que ya tienes en el sistema.")
    nombre = nombre_de(repo)
    destino = Path(a.destino or nombre).expanduser().resolve()
    if destino.exists() and (not destino.is_dir() or any(destino.iterdir())):
        decir("El destino %s ya existe y no esta vacio. Elige otra carpeta con --destino." % destino)
        return 2
    anc = repo_ancestro(destino)
    if anc is not None:
        decir("El destino %s esta dentro de otro repositorio (%s). Elige una carpeta propia con --destino." % (destino, anc))
        return 2
    ok, motivo = comprobar(repo)
    if not ok:
        decir("SIN ACCESO a la instancia %s (%s)." % (nombre, limpiar(motivo) or "sin detalle"))
        decir("No se clono nada. Que pedir y a quien:")
        decir("  - Al responsable del repositorio: permiso de LECTURA sobre `%s` (minimo para usar la instancia)." % nombre)
        decir("  - Permiso de escritura solo si vas a aportar conocimiento a la instancia.")
        decir("  - Despues vuelve a ejecutar este comando; no hace falta darme ninguna clave: uso tu sesion de git/gh/SSH.")
        decir("Mientras tanto, el comando `harness` sigue sirviendo para empezar un proyecto nuevo (`init`).")
        return 3
    version = (raiz / "VERSION").read_text(encoding="utf8").strip()
    tty = sys.stdin.isatty() if es_terminal is None else es_terminal
    decir("PLAN (todavia no se ha escrito nada)")
    decir("  Acceso al repositorio: OK (lectura)")
    decir("  Clonar:   %s" % repo)
    decir("  Destino:  %s" % destino)
    decir("  Harness instalado: %s; tras clonar se leera harness.lock de la instancia y se comparara." % version)
    if a.solo_lectura:
        decir("  Modo solo lectura: se clona y se comprueba la version; no se ejecuta `update --aplicar`.")
    else:
        decir("  Luego: instalar.sh update %s --aplicar (fija y comprueba la version; no toca nada fuera del destino)." % destino)
    decir("  Si la instancia trae `restaurar.sh`, no se ejecuta sin tu confirmacion en terminal.")
    if not a.si:
        if not tty:
            decir("Sin terminal interactiva y sin --si: solo se mostro el plan. No se instalo nada.")
            return 0
        if preguntar("Aplicar este plan? [s/N] ").strip().lower() not in ("s", "si", "y", "yes"):
            decir("Cancelado. No se escribio nada.")
            return 0
    p = ejecutar(["git", "clone", "--quiet", repo, str(destino)])
    if p.returncode != 0:
        decir("Fallo al clonar: %s" % limpiar((p.stderr or "").strip()))
        return 4
    decir("Clonado en %s" % destino)
    lock = destino / "harness.lock"
    if lock.is_file():
        try:
            fijada = tomllib.loads(lock.read_text(encoding="utf8")).get("version", "?")
        except (tomllib.TOMLDecodeError, OSError):
            fijada = "?"
        estado = "coincide con la instalada" if fijada == version else "DIFIERE de la instalada (%s)" % version
        decir("harness.lock fija la version %s: %s." % (fijada, estado))
    else:
        decir("La instancia no trae harness.lock; `update` lo fijara.")
    cmd = ["bash", str(raiz / "instalador" / "instalar.sh"), "update", str(destino)]
    if not a.solo_lectura:
        cmd.append("--aplicar")
    p = ejecutar(cmd)
    decir(limpiar((p.stdout or "").rstrip()))
    if p.returncode != 0:
        decir("`update` termino con codigo %s: %s" % (p.returncode, limpiar((p.stderr or "").strip())))
        return 4
    if (destino / "restaurar.sh").is_file():
        if tty and not a.si and not a.solo_lectura and \
                preguntar("La instancia trae restaurar.sh. Ejecutarlo ahora? [s/N] ").strip().lower() in ("s", "si", "y", "yes"):
            p = ejecutar(["bash", str(destino / "restaurar.sh")])
            decir(limpiar((p.stdout or "").rstrip()))
            return 0 if p.returncode == 0 else 4
        decir("Pendiente: revisa y ejecuta tu mismo `bash %s/restaurar.sh` (no se ejecuta sin confirmacion en terminal)." % destino)
    return 0


if __name__ == "__main__":
    sys.exit(main())
