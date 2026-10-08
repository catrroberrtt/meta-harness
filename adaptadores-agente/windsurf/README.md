# Adaptador de Windsurf (Devin Desktop)

<!-- tipo: herramienta · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: windsurf/FORMATO.md y MATRIZ.md (Windsurf) -->

Windsurf son **dos agentes** con archivos distintos; los de uno no los lee el otro. El adaptador genera cada uno por separado, solo lo «confirmado con fuente» en `FORMATO.md`, y dice cuál tocar.

## Cómo se elige el agente

El marco no pasa opciones a `generar`, así que la variante es el nombre del adaptador:

| `--agentes` | Genera |
|---|---|
| `windsurf` (por defecto; el único que se detecta solo) | Ambos, y un paso para la persona que explica cuál usar |
| `windsurf-devin-local` | Solo Devin Local |
| `windsurf-cascade` | Solo Cascade |

Las pestañas nuevas arrancan en Devin Local; Cascade queda para conversaciones antiguas. Si solo usas uno, regenera con su nombre y borra el archivo del otro.

## Qué escribe (todo dentro de la instancia)

| Archivo | Contenido |
|---|---|
| `AGENTS.md` | Lo genera el núcleo; ambos agentes lo leen sin configuración. **No** se genera `.devin/rules/*.md`: una regla `always_on` repetiría su contenido. |
| `.devin/hooks.json` (Cascade) | `{"hooks": {"pre_run_command": [{command, show_output}]}}`. Solo los `pre_*` bloquean, con salida 2. |
| `.devin/hooks.v1.json` (Devin Local) | `{"PreToolUse": [{matcher: "^exec$", hooks: [{type, command, timeout}]}]}`: el objeto de hooks es el archivo entero, sin clave envoltorio. Bloquea con salida 2 o `{"decision":"block"}`. |
| `.devin/hooks/` | `block-db-access.sh` (generado por `instalador/generar-politicas.py`, que se reutiliza), `guardia-datos.py` (puente `--formato windsurf-cascade\|windsurf-devin`) y un lanzador por agente (`lanzar-cascade.sh`, `lanzar-devin-local.sh`). |

La marca del harness va como **comentario de shell al final de `command`** (JSON no admite comentarios, y una clave extra no está confirmada en el objeto de Devin Local).

## Control por hook: siempre «degradado»

Ambos agentes **fallan abiertos**: solo la salida 2 bloquea. El script deniega él mismo ante cualquier error propio (entrada ilegible, falta de `jq`/`bash`/`git`/`python3`, fallo del hook de política) y el comando registrado deniega si falta el lanzador, pero el control se informa como capa de aviso, nunca barrera. Solo vigila el shell (`pre_run_command`, `exec`). Si la política no declara ambientes no se escribe ningún archivo de hook.

Imposición real (ver `degradaciones()`): rol de solo lectura en la base de datos, `permissions.deny` de Devin Local (se imprime como **paso para la persona**, no se escribe `.devin/config.json`), sandbox, protección de ramas e integración continua. En Cascade la lista de comandos denegados solo exige aprobación.

## Reglas

Un archivo escrito a mano (sin marca) no se pisa: se genera `<nombre>.generado.<ext>` al lado y se avisa. Es idempotente. Lo global (`~/.codeium/windsurf`, `~/.config/devin`, `/etc/devin`) nunca se escribe. Requiere `sh`, `python3`, `bash`, `jq` y `git`; no se genera la variante `powershell`.

Pruebas: `python3 -B -m unittest adaptadores-agente/tests/test_windsurf.py`.
