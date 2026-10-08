#!/usr/bin/env bash
# Corre todas las comprobaciones del harness en orden; falla si alguna falla. No modifica nada.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
FALLOS=0
paso() { echo; echo "== $1"; }
ok() { echo "   OK"; }
mal() { echo "   FALLA: $1"; FALLOS=$((FALLOS+1)); }

paso "1. bash -n de todos los .sh"
while IFS= read -r f; do bash -n "$f" || mal "$f"; done < <(find . -name '*.sh' -not -path './.git/*' | sort)
[ "$FALLOS" -eq 0 ] && ok

paso "2. py_compile de todos los .py"
P0=$FALLOS
while IFS= read -r f; do python3 - "$f" <<'PY' || mal "$f"
import sys
compile(open(sys.argv[1], encoding="utf8").read(), sys.argv[1], "exec")  # equivale a py_compile sin escribir .pyc
PY
done < <(find . -name '*.py' -not -path './.git/*' | sort)
[ "$FALLOS" -eq "$P0" ] && ok

paso "3. pruebas unittest"
for d in herramientas/tests instalador/tests; do
  if [ -d "$d" ]; then
    echo " - $d"
    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s "$d" -p 'test_*.py' || mal "unittest en $d"
  fi
done

paso "4. frescura de documentos"
python3 herramientas/harness-frescura.py || mal "harness-frescura"

paso "5. referencias prohibidas (.prohibidos.txt)"
if [ -f .prohibidos.txt ]; then
  PAT=$(grep -v '^\s*\(#\|$\)' .prohibidos.txt)
  if [ -z "$PAT" ]; then echo "   .prohibidos.txt vacío: se omite"
  elif grep -rIniF --exclude-dir=.git --exclude=.prohibidos.txt -f <(printf '%s\n' "$PAT") . ; then mal "hay referencias prohibidas"
  else ok; fi
else
  echo "   no existe .prohibidos.txt (una palabra por línea): paso omitido"
fi

echo
if [ "$FALLOS" -eq 0 ]; then echo "VERIFICACIÓN OK"; else echo "VERIFICACIÓN FALLÓ ($FALLOS)"; exit 1; fi
