#!/usr/bin/env bash
# Hook UserPromptSubmit: ante un pedido de análisis o evaluación, recuerda el orden de lectura.
# Máximo una vez cada 30 min por sesión. Nunca bloquea. Solo usa python3.
PROG=$(cat <<'PY'
import json, os, re, sys, time, tempfile
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
prompt = d.get("prompt", "") or ""
sesion = re.sub(r"\W", "_", str(d.get("session_id", "s")))
if not re.search(r"anali[zc]|investig|revis[aáe]|verific|audit|evalu|viabil|qué falta|que falta|estado de|pendiente|cómo funciona|como funciona", prompt, re.I):
    sys.exit(0)
marca = os.path.join(tempfile.gettempdir(), f".entorno-doc-{sesion}")
if os.path.exists(marca) and time.time() - os.path.getmtime(marca) < 1800:
    sys.exit(0)
open(marca, "w").close()
msg = ("ORDEN DE LECTURA: 1) documentación primero (python3 scripts/buscar-documentacion.py \"<tema>\"), "
       "2) luego el código, 3) luego los datos en solo lectura, 4) recién entonces evaluar. "
       "No digas «no sé» ni preguntes lo que esas fuentes contestan; pregunta solo lo que ninguna resuelve.")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": msg}}))
PY
)
python3 -c "$PROG"
exit 0
