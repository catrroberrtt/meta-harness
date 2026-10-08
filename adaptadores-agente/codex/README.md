# Adaptador de Codex CLI

<!-- tipo: herramienta · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: codex/FORMATO.md y MATRIZ.md (Codex) -->

Genera en la **instancia** (nunca en `~`), solo lo «confirmado con fuente» en `FORMATO.md`:

| Archivo | Contenido |
|---|---|
| `AGENTS.md` | Lo genera el núcleo; Codex lo lee sin configuración. Tope combinado de 32 KiB (`project_doc_max_bytes`): si el generado lo supera, el adaptador **avisa**. |
| `.codex/hooks.json` | `{"hooks": {"PreToolUse": [{matcher: "^Bash$", hooks: [{type, command, timeout, statusMessage}]}]}}`. JSON no admite comentarios: la marca va en la clave `_generado_por_el_harness`. |
| `.codex/hooks/` | `block-db-access.sh` y `filtrar-tramos-de-lectura.py` (los produce `instalador/generar-politicas.py`, que se **reutiliza**), `guardia-datos.py` (puente `--formato codex`) y `lanzar.sh` (lanzador POSIX que deniega si falta `python3` o el puente). |
| `.codex/rules/harness.rules` | Solo si la política prohíbe un comando cuyo `regex` es un prefijo literal (p. ej. `^mysqldump`): `prefix_rule(pattern, decision = "forbidden", justification, match)`. Un regex arbitrario no se traduce. |

## Control por hook: siempre «degradado»

**Codex falla abierto**: un hook que falla, se agota, sale con un código distinto de 0 o 2, sale con 2 sin texto en stderr, o no está confiado, deja pasar la acción. Por eso el script deniega él mismo ante cualquier error propio (entrada ilegible, falta de `jq`/`bash`/`git`, fallo del hook de política) con el JSON `hookSpecificOutput.permissionDecision = "deny"`, la razón en stderr y **salida 2**; aun así el adaptador informa «degradado» y lo trata como capa de aviso. La imposición real va en la base de datos (rol de solo lectura), sandbox, hooks gestionados, integración continua y protección de ramas (ver `degradaciones()`).

Si la política no declara ambientes, no se escribe ningún archivo de hook y el control queda «degradado» con el motivo.

## Paso obligatorio para la persona

Un hook nuevo o modificado **no corre hasta que lo confíes**: abre Codex en la carpeta, ejecuta `/hooks`, revísalo y confíalo (se registra por huella: tras cada regeneración con cambios, otra vez). Un proyecto no confiable omite `.codex/` (configuración, hooks y reglas). Que el hook sea gestionado (`requirements.toml`, nivel administrador) es decisión tuya: el adaptador no escribe nada global.

## Qué no cubre

Solo vigila `Bash`: no `apply_patch`, MCP, `write_stdin` ni herramientas alojadas (`WebSearch`). `ask` no está soportado (se deniega). `.rules` es experimental y solo aplica a comandos que salen del sandbox. No genera skills, MCP, subagentes ni `config.toml` (la fuente neutral aún no los produce). La clave de marca en `hooks.json` no está confirmada como admitida: si Codex la rechaza, quítala.

## Reglas

Si ya existe un archivo escrito a mano (sin marca) se escribe `<nombre>.generado.<ext>` al lado y se avisa; es idempotente; todo queda dentro de la instancia. Requiere `sh`, `python3`, `bash`, `jq` y `git` en el PATH.

Pruebas: `python3 -B -m unittest adaptadores-agente/tests/test_codex.py`.
