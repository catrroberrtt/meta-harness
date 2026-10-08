#!/usr/bin/env bash
# Deja listo el acceso a GitHub. Por defecto solo muestra el plan; --aplicar ejecuta con confirmacion en cada paso.
# Uso: acceso-github.sh [--aplicar] [--repositorio <url>] [--salida <carpeta>] [--titulo <texto>]
set -euo pipefail
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Falta python3 (3.11 o superior)." >&2
  exit 1
fi
exec python3 "$AQUI/acceso_github.py" "$@"
