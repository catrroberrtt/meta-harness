#!/usr/bin/env bash
# Comprueba que el entorno está sano. No modifica nada.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
FALLOS=0
paso() { echo; echo "== $1"; }
mal() { echo "   FALLA: $1"; FALLOS=$((FALLOS+1)); }
paso "1. bash -n de los .sh"
for f in $(find . -name '*.sh' -not -path './.git/*'); do bash -n "$f" || mal "$f"; done
paso "2. sintaxis de los .py"
for f in $(find . -name '*.py' -not -path './.git/*'); do
  python3 -c "import sys; compile(open(sys.argv[1], encoding='utf8').read(), sys.argv[1], 'exec')" "$f" || mal "$f"
done
paso "3. entorno.toml legible y con los campos mínimos"
python3 - <<'PY' || mal "entorno.toml"
import tomllib, sys
d = tomllib.load(open("entorno.toml", "rb"))
for k in ("nombre", "modulos"):
    assert k in d["entorno"], k
print("   ok")
PY
paso "4. cada módulo declarado tiene sus archivos"
python3 - <<'PY' || mal "módulos"
import tomllib, pathlib
mods = tomllib.load(open("entorno.toml", "rb"))["entorno"]["modulos"]
req = {"documentacion-primero": ["scripts/buscar-documentacion.py", "hooks/documentacion-primero.sh"],
       "compuerta-calidad": ["scripts/gate.sh", "hooks/gate-antes-de-commit.sh"],
       "conocimiento": ["knowledge/INDICE.md", "scripts/frescura.py"],
       "escaneo-secretos": ["scripts/escanear-secretos.py"],
       "autoguardado": ["scripts/autoguardar.py", "hooks/autoguardado.sh"],
       "aprendizaje": ["scripts/aprender.py", "knowledge/aprendizaje.md"],
       "publicar-solo-verificado": ["scripts/verificar-publicacion.py", "hooks/publicar-solo-verificado.py", "docs/revisor-independiente.md"]}
faltan = [f for m in mods for f in req.get(m, []) if not pathlib.Path(f).exists()]
assert not faltan, faltan
print("   ok")
PY
paso "5. escaneo de secretos (si el módulo está)"
if [ -f scripts/escanear-secretos.py ]; then python3 scripts/escanear-secretos.py || mal "secretos"; else echo "   (módulo no elegido)"; fi
echo; [ "$FALLOS" -eq 0 ] && { echo "TODO OK"; exit 0; } || { echo "$FALLOS comprobación(es) fallaron"; exit 1; }
