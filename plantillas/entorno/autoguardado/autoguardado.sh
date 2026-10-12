#!/usr/bin/env bash
# Hook Stop: guarda lo hecho en la sesión. La lógica y sus garantías están en scripts/autoguardar.py.
RAIZ="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
python3 "$RAIZ/scripts/autoguardar.py" 1>&2
exit 0
