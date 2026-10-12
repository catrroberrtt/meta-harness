#!/usr/bin/env bash
# Compuerta antes de entregar: corre los comandos de [gate].comandos y el escaneo de secretos.
# Deja .entorno/gate-ok con la hora si todo pasa. Sin comandos configurados avisa y solo escanea.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
FALLOS=0
mapfile -t CMDS < <(python3 - <<'PY'
import json, tomllib
for c in tomllib.load(open("entorno.toml", "rb")).get("gate", {}).get("comandos", []):
    print(json.dumps(c) if isinstance(c, list) else json.dumps(c.split()))
PY
)
if [ "${#CMDS[@]}" -eq 0 ]; then
  echo "AVISO: [gate].comandos está vacío en entorno.toml; solo se escanean secretos."
fi
for c in "${CMDS[@]}"; do
  echo "== $c"
  python3 - "$c" <<'PY' || FALLOS=$((FALLOS+1))
import json, subprocess, sys
sys.exit(subprocess.call(json.loads(sys.argv[1])))
PY
done
if [ -f scripts/escanear-secretos.py ]; then
  echo "== escaneo de secretos"; python3 scripts/escanear-secretos.py || FALLOS=$((FALLOS+1))
fi
if [ "$FALLOS" -eq 0 ]; then mkdir -p .entorno && date +%s > .entorno/gate-ok; echo "COMPUERTA OK"; exit 0; fi
echo "COMPUERTA FALLÓ ($FALLOS)"
echo "Siguiente: corrige lo que se muestra arriba y vuelve a correr scripts/gate.sh. Si un comando de [gate].comandos no debería estar, edítalo en entorno.toml."
exit 1
