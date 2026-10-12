"""Ayudas comunes de los hooks: leer el evento sin romper y entender una línea de comandos. Solo biblioteca estándar.

Por qué existe: buscar «git commit» con una expresión regular sobre el texto se elude con `git -C . commit`, con
`bash -c "git commit"` o con `echo "$(git commit)"`, y da falsos positivos con `echo git commit`. Aquí se separa la línea en
sentencias, se quita lo que no es el programa (variables de entorno, envolturas) y se mira el programa de verdad.
"""
import json
import re
import shlex
import sys

SEPARADORES = {"&&", ";", "||", "|", "&", ";;", "|&"}
ENVOLTURAS = {"env", "command", "sudo", "time", "nice", "nohup", "exec", "builtin"}
GIT_CON_VALOR = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env"}
SHELLS = {"bash", "sh", "zsh", "dash"}
PROFUNDIDAD_MAX = 4
TOPE_COMANDO = 50_000  # separar una línea más larga tarda segundos: un hook no puede colgar la sesión


def raiz_del_entorno():
    """La raíz del entorno: la carpeta que contiene `hooks/`. Se deduce de la ubicación de ESTE archivo, no de una variable del agente ni del
    directorio actual: con `CLAUDE_PROJECT_DIR` ausente (otro agente) y el comando lanzado desde una subcarpeta, un hook que no encuentra su
    configuración falla ABIERTO y deja pasar todo."""
    import pathlib
    return pathlib.Path(__file__).resolve().parent.parent


def leer_evento():
    """El evento del hook como diccionario; cualquier cosa que no lo sea (vacío, lista, basura) es {}."""
    try:
        d = json.load(sys.stdin)
    except Exception:
        return {}
    return d if isinstance(d, dict) else {}


def comando_de(evento):
    ti = evento.get("tool_input")
    c = ti.get("command") if isinstance(ti, dict) else None
    return c if isinstance(c, str) else ""


def demasiado_largo(cmd):
    """True si la línea supera el tope y no se analiza: quien decide debe tratarla con cautela, no darla por inocua."""
    return isinstance(cmd, str) and len(cmd) > TOPE_COMANDO


def tokens(cmd):
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        return list(lex)
    except ValueError:
        return cmd.split()


def _inicio(sentencia):
    """La sentencia sin asignaciones de entorno (VAR=x) ni envolturas (env, sudo, time...) al comienzo."""
    i, tras_envoltura = 0, False
    while i < len(sentencia):
        t = sentencia[i]
        if tras_envoltura and t.startswith("-"):
            i += 1
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", t):
            i += 1
        elif t in ENVOLTURAS:
            i, tras_envoltura = i + 1, True
        else:
            break
    return sentencia[i:]


def sentencias(cmd, nivel=0):
    """Lista de sentencias (cada una, lista de tokens), incluidas las de `bash -c "..."`, `$(...)` y comillas invertidas."""
    if nivel > PROFUNDIDAD_MAX or not isinstance(cmd, str) or len(cmd) > TOPE_COMANDO:
        return []
    out, cur = [], []

    def cerrar():
        nonlocal cur
        if cur:
            out.append(cur)
            cur = []

    for t in tokens(cmd):
        if t in SEPARADORES or t in ("(", ")"):
            cerrar()
        else:
            cur.append(t)
    cerrar()
    extra = []
    for s in out:
        for t in s:
            for m in re.finditer(r"\$\((.*)\)|`([^`]*)`", t):
                extra += sentencias(m.group(1) or m.group(2), nivel + 1)
        p = _inicio(s)
        if p and p[0].rsplit("/", 1)[-1] in SHELLS and "-c" in p[1:]:
            k = p.index("-c")
            if k + 1 < len(p):
                extra += sentencias(p[k + 1], nivel + 1)
    return out + extra


def programa(sentencia):
    s = _inicio(sentencia)
    return (s[0].rsplit("/", 1)[-1], s[1:]) if s else ("", [])


def git_subcomando(sentencia):
    """«commit», «push»... de una sentencia de git, saltando sus opciones globales (-C ruta, -c clave=valor, --no-pager...)."""
    prog, resto = programa(sentencia)
    if prog != "git":
        return None
    i = 0
    while i < len(resto) and resto[i].startswith("-"):
        i += 2 if resto[i] in GIT_CON_VALOR else 1
    return resto[i] if i < len(resto) else None


def git_info(sentencia):
    """(subcomando, destinos): el subcomando de git y los directorios que cambian el repo de destino, EN ORDEN:
    -C <ruta> (se acumulan y son relativos al anterior), --work-tree <ruta>, --git-dir <ruta>."""
    prog, resto = programa(sentencia)
    if prog != "git":
        return None, []
    destinos, i = [], 0
    while i < len(resto) and resto[i].startswith("-"):
        t = resto[i]
        if t == "-C" and i + 1 < len(resto):
            destinos.append(("C", resto[i + 1]))
        elif t in ("--work-tree", "--git-dir") and i + 1 < len(resto):
            destinos.append((t[2:], resto[i + 1]))
        elif t.startswith(("--work-tree=", "--git-dir=")):
            nombre, valor = t[2:].split("=", 1)
            destinos.append((nombre, valor))
        i += 2 if t in GIT_CON_VALOR else 1
    return (resto[i] if i < len(resto) else None), destinos


GESTORES = {"npm", "yarn", "pnpm", "npx"}
FLAGS_DIR = {"--prefix", "--cwd", "--dir", "-C"}


def con_directorio(cmd, cwd):
    """Recorre las sentencias de `cmd` siguiendo `cd`: devuelve [(sentencia, directorio_donde_corre)]. Para npm/yarn/pnpm el directorio
    también sigue a --prefix / --cwd / --dir / -C (con `=` o con valor aparte). Sin esto, un bloqueo que mira solo el directorio actual
    se salta con `cd <repo> && npm install` o `npm --prefix <repo> install`."""
    import os
    def resolver(ruta, base):
        ruta = os.path.expanduser(ruta)
        return os.path.normpath(ruta if os.path.isabs(ruta) else os.path.join(base, ruta))
    actual, out = cwd, []
    for s in sentencias(cmd):
        prog, resto = programa(s)
        if prog == "cd" and resto and not resto[0].startswith("-"):
            actual = resolver(resto[0], actual)
            continue
        donde = actual
        if prog in GESTORES:
            for i, t in enumerate(resto):
                if t in FLAGS_DIR and i + 1 < len(resto):
                    donde = resolver(resto[i + 1], donde)
                elif t.startswith(("--prefix=", "--cwd=", "--dir=")):
                    donde = resolver(t.split("=", 1)[1], donde)
        out.append((s, donde))
    return out
