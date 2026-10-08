# Contrato `.harness/entorno.toml` de la instancia

<!-- tipo: herramienta · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Archivo **opcional** en la instancia privada. Tras clonarla, `harness instalar owner/nombre` lo lee (`tomllib`) y prepara el entorno. Ejemplo genérico: `plantillas/instancia/entorno.toml.ejemplo`. Sin este archivo se usa `scripts/restaurar-entorno.sh` si existe (ver `UNICO-COMANDO.md`).

**Validación estricta**: claves desconocidas, tipos equivocados, rutas que salen de su base o campos obligatorios ausentes detienen el entorno **entero** con un mensaje por problema, y no se ejecuta nada.

## `[general]`

| Clave | Tipo | Defecto | Significado |
|---|---|---|---|
| `base_repos` | texto | `~/Desktop/Proyectos` | Base de los `destino` de `[[repositorios]]` (absoluta o con `~`). |

## `[[prerrequisitos]]`

| Clave | Tipo | Obligatoria | Significado |
|---|---|---|---|
| `comando` | texto | sí | Programa que debe existir como programa **nativo** (en WSL se ignoran los de `/mnt/<unidad>/`). |
| `para` | texto | sí | Para qué se necesita (se muestra a la persona). |
| `instalar_apt` | texto o lista | no | Paquetes apt. Los de todos los prerrequisitos faltantes se instalan con **un** `sudo apt update && sudo apt install -y ...` y una confirmación de administrador. |
| `obligatorio` | bool | no (`true`) | Si es `false` y falta, solo se informa como omitido. |

## `[[repositorios]]`

| Clave | Tipo | Obligatoria | Significado |
|---|---|---|---|
| `remoto` | texto | sí | `owner/nombre` (GitHub por SSH) o URL https/ssh **sin credenciales**. |
| `destino` | texto | sí | Ruta relativa a `base_repos`; no puede ser absoluta ni contener `..`. |
| `confirmacion` | bool | no (`true`) | Son privados y pesan: los que piden confirmación se preguntan **todos juntos**, siempre (también con `--si`). |

Si `destino` ya tiene `.git` se omite («ya presente»).

## `[[pasos]]`

| Clave | Tipo | Obligatoria | Significado |
|---|---|---|---|
| `nombre` | texto | sí | Único. Identifica el paso en el avance guardado. |
| `comando` | lista de textos | sí | Se ejecuta **sin shell**, p. ej. `["python3", "scripts/x.py"]`. |
| `red` | bool | no (`false`) | Usa la red. |
| `pesado` | bool | no (`false`) | Descarga o tarda mucho. |
| `por_defecto` | `"si"` \| `"no"` \| `"preguntar"` | no (`"preguntar"`) | `no` lo omite. En pasos sin red ni peso, `si` lo ejecuta y `preguntar` pregunta (`--si` lo acepta). |
| `cwd` | texto | no (`"."`) | Carpeta relativa a la instancia; no puede salir de ella. |

Regla dura: un paso con `red = true` o `pesado = true` **nunca** se ejecuta sin confirmación (una sola, agrupada, para todos los de ese tipo), ni con `--si`. Si no se confirma, queda como pendiente con su comando exacto. Un paso que falla no detiene a los demás; queda pendiente. Lo hecho se registra y no se repite al reanudar.

## Bases de datos: fuera del contrato

El orquestador **no** levanta, restaura ni clona bases de datos (ni clientes, contenedores, respaldos, túneles o SSO de datos), y el contrato no trae pasos de bases por defecto. La base es la fuente de evidencia más fuerte y cada proyecto accede distinto: el acceso lo **declara y lo da la persona** (ambientes en `politicas.toml`, acceso personal en `acceso.local.toml`, que no se versiona; se comprueba con `python3 instalador/preflight-accesos.py`). Sin ese acceso el entorno trabaja en modo degradado y no afirma nada sobre datos. El resumen final del comando único lo recuerda siempre en el bloque «Acceso a datos (lo das tú)».
