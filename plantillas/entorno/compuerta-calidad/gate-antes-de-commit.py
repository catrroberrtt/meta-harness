#!/usr/bin/env python3
"""Hook PreToolUse (Bash): antes de `git commit` o `git push` recuerda correr la compuerta.

Con [gate].bloquear_commit = true impide el commit si la compuerta no pasó en la última hora. Entiende la línea de comandos
(ver _comandos.py): `git -C . commit`, `bash -c "git commit"` y `echo "$(git commit)"` cuentan; `echo git commit` y
`git commit-tree` no. Nunca rompe la sesión: ante cualquier error interno deja pasar.
"""
import json
import os
import sys
import time
import tomllib

import _comandos as c


def main():
    evento = c.leer_evento()
    cmd = c.comando_de(evento)
    if c.demasiado_largo(cmd):  # no se puede analizar: con «commit» o «push» dentro se trata como si lo fuera
        hay_commit, hay_push = "commit" in cmd, "push" in cmd
    else:
        subs = [c.git_subcomando(s) for s in c.sentencias(cmd)]
        hay_commit, hay_push = "commit" in subs, "push" in subs
    if not (hay_commit or hay_push):
        return 0
    raiz = str(c.raiz_del_entorno())
    ok = os.path.join(raiz, ".entorno", "gate-ok")
    if os.path.exists(ok) and time.time() - os.path.getmtime(ok) < 3600:
        return 0
    try:
        with open(os.path.join(raiz, "entorno.toml"), "rb") as f:
            bloquear = tomllib.load(f).get("gate", {}).get("bloquear_commit", False)
    except Exception:
        bloquear = False
    aviso = "La compuerta (scripts/gate.sh) no ha pasado en la última hora. Córrela antes de commitear o subir."
    if bloquear and hay_commit:
        print(aviso + " (bloquear_commit está activado en entorno.toml)", file=sys.stderr)
        return 2
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": aviso}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
