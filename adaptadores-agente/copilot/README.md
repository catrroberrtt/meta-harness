# Adaptador de GitHub Copilot

<!-- tipo: herramienta · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: copilot/FORMATO.md y MATRIZ.md (Copilot) -->

Copilot son **tres superficies que comparten archivos pero no comportamiento**. El adaptador genera los hooks de las dos familias de formato confirmadas, solo lo «confirmado con fuente» en `FORMATO.md`, sin prometer barrera.

## Cómo se elige la superficie

El marco no pasa opciones a `generar`, así que la superficie es el nombre del adaptador:

| `--agentes` | Genera |
|---|---|
| `copilot` (por defecto; el único que se detecta solo) | Ambos archivos de hook |
| `copilot-vscode` | Solo el arnés Local de VS Code (Preview) |
| `copilot-cli` | Solo Copilot CLI y sesiones Copilot del Agent Host (comparten implementación) |

## Qué escribe (todo dentro de la instancia)

| Archivo | Contenido |
|---|---|
| `AGENTS.md` | Lo genera el núcleo; Copilot lo lee. **No** se genera `.github/copilot-instructions.md`: las fuentes de instrucciones se suman sin precedencia garantizada y repetirlo duplicaría el contenido. |
| `.github/hooks/harness-vscode.json` | Local de VS Code: **sin `version`**, `hooks.PreToolUse[]` con `type`, `command`, `timeout`. `matcher` se ignora, por eso no se escribe y filtra el script. |
| `.github/hooks/harness-cli.json` | CLI y Agent Host: `version: 1`, `hooks.preToolUse[]` con `type`, `bash`, `timeoutSec`. |
| `.github/harness-hooks/` | `block-db-access.sh` (generado por `instalador/generar-politicas.py`), `guardia-datos.py` (puente `--formato copilot-local\|copilot-cli`) y un lanzador por superficie. Fuera de `.github/hooks/`, que solo lee `*.json`. |

La marca del harness va como comentario de shell al final del comando.

## Control por hook: siempre «degradado»

- **Local (Preview):** `matcher` ignorado y **falla abierto** ante errores; el script deniega él mismo con salida 2. Los nombres de herramienta no están documentados: se juzga cualquier herramienta con `tool_input.command` de texto.
- **CLI y Agent Host:** `preToolUse` cierra ante errores, pero **el tiempo agotado siempre deja pasar**. Solo se juzgan `bash` y `powershell`.
- `chat.tools.terminal.autoApprove: false` **no bloquea** (solo pide aprobación): no se genera ni se presenta como control.

Imposición real (ver `degradaciones()`): `--deny-tool` de la CLI (gana incluso con `--allow-all`; se imprime como **paso para la persona**), rol de solo lectura en la base de datos, sandbox, protección de ramas e integración continua. Si la política no declara ambientes no se escribe ningún archivo de hook.

## Reglas

Un archivo escrito a mano (sin marca) no se pisa: se genera `<nombre>.generado.<ext>` al lado y se avisa. Es idempotente. Lo global (`~/.copilot`, política de la organización, ajustes `chat.*`) nunca se escribe. Que una superficie lea el archivo de la otra no está confirmado: el hook podría correr dos veces (inocuo). Requiere `sh`, `python3`, `bash`, `jq` y `git`.

Pruebas: `python3 -B -m unittest adaptadores-agente/tests/test_copilot.py`.
