#!/usr/bin/env bash
# Instalador del meta harness. Sin red. Por defecto solo muestra el plan; --aplicar escribe.
# Uso: instalar.sh <adopt|init|update|migrar> <carpeta-de-la-instancia> [--partida A|B|C]
#        [--acceso <acceso.local.toml>] [--politica <politicas.toml>] [--proyecto <carpeta>]
#        [--aceptar-degradado] [--aceptar-dentro-de-repo] [--aplicar]
set -euo pipefail
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"
uso() {
  cat <<AYUDA
Uso: instalar.sh <modo> <carpeta-de-la-instancia> [opciones]
Modos:
  adopt    Proyecto empezado (partida A): informe «cómo es este proyecto» y propuesta; no cambia código
  init     Instancia nueva (partida B, o A con --partida A): crea el esqueleto; en B lee la informacion de partida
           y deja .harness/entendimiento.md y preguntas.md (propuesta para validar)
  update   Instancia instalada: actualiza solo lo del harness que nadie modificó
  migrar   Migración (partida C): esqueleto + registro de mejoras + lectura del origen + carpeta de equivalencia
Opciones:
  --partida A|B|C             punto de partida (por defecto según el modo)
  --acceso <archivo>          acceso.local.toml (por defecto el de la instancia)
  --politica <archivo>        politicas.toml (por defecto el de la instancia o el del harness)
  --proyecto <carpeta>        adopt: proyecto a analizar si es otro distinto de la instancia
  --aceptar-degradado         acepta explícitamente el modo degradado (sin datos)
  --aceptar-dentro-de-repo    permite una instancia dentro de otro repositorio
  --harness <raiz>            raíz del harness (por defecto este)
  --aplicar                   escribe; sin esta opción solo se muestra el plan
Versión del harness: $(cat "$RAIZ/VERSION")
AYUDA
}
case "${1:-}" in
  -h|--help|help|"") uso; exit 0 ;;
  adopt|init|update|migrar) ;;
  *) echo "Modo desconocido: $1" >&2; uso >&2; exit 2 ;;
esac
[ -n "${2:-}" ] || { echo "Falta la carpeta de la instancia." >&2; uso >&2; exit 2; }
command -v python3 >/dev/null || { echo "Se necesita python3." >&2; exit 2; }
PYTHONDONTWRITEBYTECODE=1 exec python3 "$AQUI/harness_instalar.py" "$@"
