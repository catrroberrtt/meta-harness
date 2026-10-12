#!/usr/bin/env bash
# Hook PreToolUse (Bash): antes de `git commit` o `git push` recuerda correr la compuerta.
# Con [gate].bloquear_commit = true impide el commit si la compuerta no pasó en la última hora.
PROG=$(cat <<'PY'
import json, os, re, sys, time, tomllib
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
cmd = (d.get("tool_input") or {}).get("command", "") or ""
if not re.search(r"\bgit\s+(commit|push)\b", cmd):
    sys.exit(0)
raiz = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
ok = os.path.join(raiz, ".entorno", "gate-ok")
reciente = os.path.exists(ok) and time.time() - os.path.getmtime(ok) < 3600
if reciente:
    sys.exit(0)
try:
    bloquear = tomllib.load(open(os.path.join(raiz, "entorno.toml"), "rb")).get("gate", {}).get("bloquear_commit", False)
except Exception:
    bloquear = False
aviso = "La compuerta (scripts/gate.sh) no ha pasado en la última hora. Córrela antes de commitear o subir."
if bloquear and re.search(r"\bgit\s+commit\b", cmd):
    print(aviso + " (bloquear_commit está activado en entorno.toml)", file=sys.stderr)
    sys.exit(2)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": aviso}}))
PY
)
python3 -c "$PROG"
exit $?
