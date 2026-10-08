# Adaptador de OpenCode

<!-- tipo: herramienta · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: opencode/FORMATO.md y MATRIZ.md (OpenCode) -->

Genera en la **instancia** (nunca en `~`), solo lo «confirmado con fuente» en `FORMATO.md`:

| Archivo | Contenido |
|---|---|
| `AGENTS.md` | Lo genera el núcleo; OpenCode lo lee sin configuración (no hay que enlazarlo). |
| `.opencode/plugins/guardia-datos.js` | Plugin con `tool.execute.before`: si la herramienta es `bash`, ejecuta por subproceso el puente `guardia-datos.py` y **lanza `throw new Error(...)`** con el mensaje de la política si la decisión no es «allow». Lleva la marca del harness en un comentario `//`. |
| `.opencode/guardia/` | `block-db-access.sh` y `filtrar-tramos-de-lectura.py` (los produce `instalador/generar-politicas.py`, que se **reutiliza**) y `guardia-datos.py` (puente de entrada y salida; no calcula nada). |

## Cuándo existe el plugin

Solo si la matriz confirma hooks para OpenCode **y** la política permite generar el hook (ambientes de datos, `hosts_locales`, `alcance.repos`…). Si no, el control por hook queda **degradado** con el motivo, no se escribe nada de `.opencode/` y `degradaciones()` lo dice.

## Qué se sabe y qué no (ver `FORMATO.md` §3)

- Bloquear lanzando una excepción en `tool.execute.before` es el patrón documentado; la entrada es `input {tool, sessionID, callID}` y `output {args}`.
- Que un plugin que falla **bloquee** y que el hook se dispare para MCP y `task` está confirmado solo en el código de la rama `dev`, no en la documentación: probarlo con el agente real.
- No hay `ask` en un plugin: lo que la política marca «confirmar» se **bloquea** con un mensaje que lo explica. `permission.asked` no está documentado como vía para denegar.
- No se generan skills, comandos, subagentes, MCP ni `permission` de `opencode.json` (confirmados en `FORMATO.md`, pero la fuente neutral aún no los produce); no se inventan reglas por ruta (no existen).

## Reglas

Todo archivo generado lleva la marca; si ya existe uno escrito a mano se escribe `<nombre>.generado.<ext>` al lado y se avisa; es idempotente; todo queda dentro de la instancia. Lo global (`~/.config/opencode/…`) se imprime como paso para la persona.

Requiere `python3`, `bash`, `jq` y `git` en el PATH; sin ellos el puente **bloquea** (falla cerrado).

Pruebas: `python3 -B -m unittest adaptadores-agente/tests/test_opencode.py`.
