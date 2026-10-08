#!/bin/sh
# Arranque de meta-harness. Uso: curl -fsSL <url>/instalar.sh | sh -s -- [--version X.Y.Z] [--si]
# Muestra el plan ANTES de escribir, comprueba el sha256 de lo descargado y no pide privilegios de administrador ni credenciales.
# Opciones: --version X.Y.Z  --si (sin preguntar)  --origen ARCHIVO.tar.gz (local, con ARCHIVO.tar.gz.sha256; sin red)
set -eu
# UNICO lugar donde vive la URL del repositorio central (un fork la cambia aqui, o define MH_REPO / MH_URL_BASE, o usa --origen).
REPO="${MH_REPO:-https://github.com/catrroberrtt/meta-harness}"   # repositorio publico (git)
BASE="${MH_URL_BASE:-$REPO/releases/download}"                    # <BASE>/vX.Y.Z/meta-harness-X.Y.Z.tar.gz[.sha256]
PY="${MH_PYTHON:-python3}"
VERSION="" SI=0 ORIGEN=""
while [ $# -gt 0 ]; do
  case "$1" in
    --version) VERSION="${2:?falta X.Y.Z}"; shift 2 ;;
    --si) SI=1; shift ;;
    --origen) ORIGEN="${2:?falta el archivo}"; shift 2 ;;
    *) echo "Opcion desconocida: $1" >&2; exit 2 ;;
  esac
done
SIN_PUBLICAR="El repositorio central aún no está publicado: define MH_URL_BASE o usa --origen. No se descargo ni se instalo nada."
if [ -z "$ORIGEN" ]; then   # con el marcador sin reemplazar no se intenta ninguna descarga
  case "$BASE" in *ORGANIZACION*) echo "$SIN_PUBLICAR" >&2; exit 1 ;; esac
  case "$REPO:$VERSION" in *ORGANIZACION*:) echo "$SIN_PUBLICAR" >&2; exit 1 ;; esac
fi
falta=0
command -v git >/dev/null 2>&1 || { echo "FALTA git. Instalalo con tu gestor de paquetes (ej.: apt install git | brew install git)." >&2; falta=1; }
if command -v "$PY" >/dev/null 2>&1; then
  "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null || { echo "FALTA Python >= 3.12 (hay: $("$PY" -V 2>&1)). Ej.: apt install python3.12 | brew install python@3.12." >&2; falta=1; }
else echo "FALTA python3 >= 3.12. Ej.: apt install python3 | brew install python@3.12." >&2; falta=1; fi
[ "$falta" = 0 ] || { echo "No se instalo nada. Instala lo que falta (este script no lo hace) y repite." >&2; exit 1; }
if [ -z "$VERSION" ] && [ -n "$ORIGEN" ]; then
  VERSION=$(basename "$ORIGEN" | sed -n 's/^meta-harness-\([0-9][0-9.]*[0-9]\)\.tar\.gz$/\1/p')
fi
if [ -z "$VERSION" ]; then   # ultima etiqueta X.Y.Z del repositorio publico
  VERSION=$(GIT_TERMINAL_PROMPT=0 git ls-remote --tags --refs "$REPO" | sed -n 's|.*refs/tags/v\{0,1\}\([0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\)$|\1|p' | sort -t. -k1,1n -k2,2n -k3,3n | tail -n 1) || VERSION=""
fi
case "$VERSION" in [0-9]*.[0-9]*.[0-9]*) ;; *) echo "No pude determinar la version; indicala con --version X.Y.Z." >&2; exit 1 ;; esac
DEST="$HOME/.local/share/meta-harness/$VERSION"
ENLACE="$HOME/.local/bin/harness"
FUENTE="${ORIGEN:-$BASE/v$VERSION/meta-harness-$VERSION.tar.gz}"
echo "PLAN (todavia no se ha escrito nada)"
echo "  Descargar: $FUENTE"
echo "  Comprobar: sha256 contra $FUENTE.sha256 (si no coincide, se aborta)"
echo "  Version:   $VERSION"
echo "  Instalar en: $DEST"
echo "  Enlace:      $ENLACE (no se toca el PATH; sin privilegios de administrador; no se piden credenciales)"
if [ "$SI" != 1 ]; then
  if ( : </dev/tty ) 2>/dev/null; then
    printf "Aplicar este plan? [s/N] " >&2; read -r r </dev/tty || r=""
    case "$r" in s|S|si|SI|y|Y) ;; *) echo "Cancelado. No se escribio nada."; exit 0 ;; esac
  else echo "Sin terminal y sin --si: solo se mostro el plan. No se instalo nada."; exit 0; fi
fi
TMP=$(mktemp -d "${TMPDIR:-/tmp}/meta-harness.XXXXXX"); trap 'rm -rf "$TMP"' EXIT INT TERM
if [ -n "$ORIGEN" ]; then cp "$ORIGEN" "$TMP/a.tar.gz"; cp "$ORIGEN.sha256" "$TMP/a.sha256"
else curl -fsSL -o "$TMP/a.tar.gz" "$FUENTE" && curl -fsSL -o "$TMP/a.sha256" "$FUENTE.sha256"; fi
ESPERADO=$(awk '{print tolower($1); exit}' "$TMP/a.sha256")
if command -v sha256sum >/dev/null 2>&1; then REAL=$(sha256sum "$TMP/a.tar.gz" | awk '{print $1}')
else REAL=$(shasum -a 256 "$TMP/a.tar.gz" | awk '{print $1}'); fi
if [ -z "$ESPERADO" ] || [ "$ESPERADO" != "$REAL" ]; then
  echo "ABORTADO: la suma sha256 NO coincide (esperada: ${ESPERADO:-vacia}; real: $REAL). No se instalo nada." >&2; exit 1
fi
echo "sha256 correcta ($REAL)."
if [ -d "$DEST" ]; then echo "La version $VERSION ya esta instalada en $DEST; solo se actualiza el enlace."
else
  mkdir -p "$(dirname "$DEST")" "$TMP/x"
  tar -xzf "$TMP/a.tar.gz" -C "$TMP/x" --strip-components=1
  mv "$TMP/x" "$DEST"
fi
mkdir -p "$(dirname "$ENLACE")"
if [ -e "$ENLACE" ] && [ ! -L "$ENLACE" ]; then echo "Aviso: $ENLACE existe y no es un enlace; no lo toco." >&2
else ln -sfn "$DEST/cli/harness" "$ENLACE"; fi
echo "Instalado: $DEST"
case ":$PATH:" in *":$(dirname "$ENLACE"):"*) ;; *) echo "Agrega $(dirname "$ENLACE") a tu PATH, por ejemplo: export PATH=\"\$HOME/.local/bin:\$PATH\"" ;; esac
echo "Siguiente paso: harness (asistente)."
