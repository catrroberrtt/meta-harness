#!/usr/bin/env python3
"""Hook UserPromptSubmit: ante un pedido de análisis o evaluación, recuerda el orden de lectura.

Máximo una vez cada 30 minutos por sesión. Nunca bloquea y nunca rompe la sesión. El identificador de sesión no se usa nunca
como ruta: se reduce a su huella, así que un valor hostil («../../x») no escribe fuera de la carpeta temporal.
"""
import hashlib
import json
import os
import re
import sys
import tempfile
import time

import _comandos as c

PIDE_ANALISIS = re.compile(r"anali[zc]|investig|revis[aáe]|verific|audit|evalu|viabil|qué falta|que falta|estado de|pendiente|cómo funciona|como funciona", re.I)


def main():
    d = c.leer_evento()
    prompt = d.get("prompt")
    if not isinstance(prompt, str) or not PIDE_ANALISIS.search(prompt[:20000]):
        return 0
    huella = hashlib.sha256(str(d.get("session_id", "s")).encode("utf8", "replace")).hexdigest()[:16]
    marca = os.path.join(tempfile.gettempdir(), f".entorno-doc-{huella}")
    if os.path.exists(marca) and time.time() - os.path.getmtime(marca) < 1800:
        return 0
    open(marca, "w").close()
    msg = ("ORDEN DE LECTURA: 1) documentación primero (python3 scripts/buscar-documentacion.py \"<tema>\"), "
           "2) luego el código, 3) luego los datos en solo lectura, 4) recién entonces evaluar. "
           "No digas «no sé» ni preguntes lo que esas fuentes contestan; pregunta solo lo que ninguna resuelve.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
