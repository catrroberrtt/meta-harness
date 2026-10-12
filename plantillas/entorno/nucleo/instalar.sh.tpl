#!/usr/bin/env bash
# Prepara este entorno. Sin argumentos solo muestra qué hace falta; con --aplicar deja todo listo.
# No instala paquetes, no toca la configuración global del agente y no usa red.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
APLICAR=0; [ "${1:-}" = "--aplicar" ] && APLICAR=1
FALTA=0
req() { if command -v "$1" >/dev/null 2>&1; then echo "  ok     $1"; else echo "  FALTA  $1  ($2)"; FALTA=1; fi; }
echo "Requisitos:"
req git "control de versiones"
req python3 "scripts y hooks"
python3 -c 'import sys,tomllib; sys.exit(0)' 2>/dev/null && echo "  ok     python3 >= 3.11" || { echo "  FALTA  python3 >= 3.11  (módulo tomllib)"; FALTA=1; }
[ "$FALTA" -eq 0 ] || { echo; echo "Instala lo que falta y vuelve a correr este script."; exit 1; }
echo; echo "Plan:"
echo "  - dar permiso de ejecución a scripts/ y hooks/"
[ -d .git ] || echo "  - iniciar un repositorio git aquí"
if [ "$APLICAR" -eq 1 ]; then
  chmod +x scripts/* hooks/* verificar.sh instalar.sh 2>/dev/null
  [ -d .git ] || git init -q -b main
  mkdir -p .entorno
  echo; echo "Listo. Ahora: ./verificar.sh"
else
  echo; echo "Solo se mostró el plan. Para aplicarlo: ./instalar.sh --aplicar"
fi
