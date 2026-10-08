# Arranque público de meta-harness

<!-- tipo: herramienta · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

`instalar.sh` instala el comando `harness` desde el repositorio público. Es corto (< 120 líneas), legible y no tiene sorpresas.

## Flujo real

```sh
curl -fsSL https://<host>/<organizacion>/meta-harness/releases/download/vX.Y.Z/instalar.sh | sh -s -- --version X.Y.Z
```

Sin `--version` toma la última etiqueta `X.Y.Z` del repositorio. Lo que hace, en este orden:

1. Comprueba prerrequisitos: `git` y `python3` >= 3.12. Si falta algo, dice qué y con qué comando instalarlo, **sin instalarlo**, y sale sin escribir nada.
2. **Muestra el plan** (qué descargará, qué versión, dónde instalará) y pide confirmación si hay terminal. `--si` la omite. Sin terminal y sin `--si`, solo muestra el plan y sale.
3. Descarga `meta-harness-X.Y.Z.tar.gz` y su `.sha256` publicado, y **compara la suma sha256**. Si no coincide, aborta sin instalar y sin dejar temporales.
4. Instala en `~/.local/share/meta-harness/X.Y.Z` y crea el enlace `~/.local/bin/harness`. No modifica el PATH: solo avisa si hace falta agregar `~/.local/bin`. Un `harness` ajeno que no sea enlace no se pisa.

Nunca usa privilegios de administrador, nunca pide ni guarda credenciales.

## Verificación manual de la suma

No tienes que fiarte del script: descarga ambos archivos y compara tú mismo.

```sh
sha256sum -c meta-harness-X.Y.Z.tar.gz.sha256     # macOS: shasum -a 256 -c ...
```

Si prefieres revisar antes de ejecutar, descarga `instalar.sh`, léelo y ejecútalo con `sh instalar.sh`. Recomendado: contrasta la suma publicada con una segunda fuente (la página de la versión).

## Por qué no se ejecuta nada de una instancia sin mostrar el plan

Este script es **público y genérico**: no contiene ni ejecuta nada de ninguna instancia privada. Instalar una instancia es un paso aparte (`instalador/instalar-instancia.py <repositorio>`): comprueba primero que tienes acceso (con tus credenciales ya existentes), muestra el plan y espera tu confirmación antes de clonar; un `restaurar.sh` de la instancia nunca se ejecuta con `--si`. Un script que baja y ejecuta código ajeno sin que lo veas es justo el riesgo de `curl | sh`; por eso todo paso muestra el plan antes de escribir.

## Pruebas sin red

`--origen meta-harness-X.Y.Z.tar.gz` usa un archivo local y su `meta-harness-X.Y.Z.tar.gz.sha256` en lugar de descargar. Variables: `MH_REPO`, `MH_URL_BASE`, `MH_PYTHON`. 

## Al publicar el repositorio central (un solo lugar)

El script lee la URL base de **una sola variable**: `MH_REPO` (o `MH_URL_BASE` para fijar directamente la carpeta de descargas). Su valor por defecto está en **una sola línea** de `instalar.sh`:

```sh
REPO="${MH_REPO:-https://github.com/catrroberrtt/meta-harness}"
```

Un fork cambia esa línea (y nada más) o define `MH_REPO` / `MH_URL_BASE`. La guarda `*ORGANIZACION*` del script sigue evitando descargar si alguien deja el marcador de una plantilla sin reemplazar.

```sh
python3 -m unittest bootstrap/tests/test_bootstrap.py
```
