# Adaptador de Cursor

<!-- tipo: herramienta · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: cursor/FORMATO.md y MATRIZ.md (Cursor) -->

Genera en la **instancia** (nunca en `~`), solo lo «confirmado con fuente» en `FORMATO.md`:

| Archivo | Contenido |
|---|---|
| `AGENTS.md` | Lo genera el núcleo; Cursor lo lee en la raíz y subcarpetas (sin frontmatter). |
| `.cursor/rules/harness.mdc` | Regla mínima con la cabecera documentada `alwaysApply: true` que remite a `AGENTS.md`. Siempre `.mdc` (un `.md` se ignora). Sin `globs`. |
| `.cursor/hooks.json` | `{"version": 1, "hooks": {"beforeShellExecution": [{command, timeout, failClosed: true}]}}`. JSON no admite comentarios: la marca va en la clave `_generado_por_el_harness` (mismo mecanismo que el ejemplo de Claude Code). |
| `.cursor/hooks/` | `block-db-access.sh` y `filtrar-tramos-de-lectura.py` (los produce `instalador/generar-politicas.py`, que se **reutiliza**) y `guardia-datos.py`: puente que ejecuta ese hook y traduce su decisión (**salida 2 = denegar**, JSON `permission`). Ante cualquier fallo deniega con salida 2. |

## Cuándo existe el hook

Solo si la matriz confirma hooks para Cursor **y** la política permite generarlo. Si no, no se escriben `hooks.json` ni `hooks/`, el control por hook queda **degradado** con el motivo (la regla `.mdc` sí se genera).

## Qué se sabe y qué no (ver `FORMATO.md` §3)

- `failClosed: true` bloquea además fallo, tiempo agotado, código ≠ 0 y ausencia de salida; un hook de permiso con salida 0 y JSON inválido bloquea aunque sea `false`.
- El hook se registra solo en `beforeShellExecution`, donde `ask` es válido; `preToolUse` no aplica `ask` y `subagentStart` lo trata como `deny`.
- No hay esquema publicado de `hooks.json`: que Cursor ignore la clave de marca **no está confirmado**. Si la rechaza, quítala.
- No se genera `.cursor/commands` (no documentado hoy; sustituto: skills con `disable-model-invocation`), ni skills, MCP, subagentes, permisos de la CLI ni plugins. `permissions.json` del IDE no es un control determinista.
- Qué eventos corren en `agent -p` y en agentes en la nube no está confirmado.

## Reglas

Si ya existe un archivo escrito a mano (sin marca) se escribe `<nombre>.generado.<ext>` al lado y se avisa; es idempotente; todo queda dentro de la instancia. Lo global (`~/.cursor/…`) se imprime como paso para la persona. Requiere `python3`, `bash`, `jq` y `git` en el PATH.

Pruebas: `python3 -B -m unittest adaptadores-agente/tests/test_cursor.py`.
