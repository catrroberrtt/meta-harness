# GitHub Copilot (agente de VS Code y Copilot CLI): formato exacto de configuración (contraste con la fuente)

<!-- tipo: estandar · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: documentación oficial (URLs en el documento) -->

## Fuentes y método

Leídas el 2026-10-07, solo lectura (no se ejecutó ni instaló ningún agente), en su **fuente Markdown cruda** de los repositorios oficiales de documentación:

- Documentación de VS Code (publicada en `https://code.visualstudio.com/docs/...`): fuente en `https://raw.githubusercontent.com/microsoft/vscode-docs/main/docs/<ruta>.md`, rama `main` (cada página trae `DateApproved: 10/7/2026` en su cabecera). Páginas: `agent-customization/custom-instructions`, `hooks`, `custom-agents`, `prompt-files`, `agent-skills`, `mcp-servers`; `agents/reference/hooks-reference`, `agents/reference/mcp-configuration`; `agents/run/approvals`, `tools`, `security`, `agent-sandboxing`, `subagents`.
- Documentación de GitHub Copilot CLI y del agente en la nube (publicada en `https://docs.github.com/en/copilot/...`): fuente en `https://raw.githubusercontent.com/github/docs/main/content/copilot/<ruta>.md`, commit `7b807926df3ccb7f3d1bcd4ad1c652fb42b0931d` en la fecha de lectura. Páginas: `reference/hooks-reference`, `how-tos/copilot-cli/customize-copilot/{use-hooks,add-custom-instructions,add-mcp-servers,create-custom-agents-for-cli}`, `how-tos/copilot-cli/automate-copilot-cli/run-cli-programmatically`, `reference/copilot-cli-reference/{cli-command-reference,cli-config-dir-reference,cli-programmatic-reference}`.

Limitación: las páginas se leyeron como fuente Markdown, no renderizadas; contienen etiquetas de plantilla (`{% data variables... %}`) que se omiten al citar. No se localizó un esquema JSON publicado para los archivos de hooks (se buscó en las páginas de referencia de hooks de ambos orígenes; solo traen tablas de campos).

### Hallazgo estructural: tres superficies que comparten archivos pero no comportamiento

La página de hooks de VS Code lo dice así (literal): «Some harnesses discover the same hook files, such as `.github/hooks/*.json` or `.claude/settings.json`. This file compatibility does not make their behavior identical. Supported events, event names, matchers, command properties, tool names, payloads, and output decisions can differ.»

1. **VS Code, arnés «Local»** (corre en el host de extensiones): sus propios hooks PascalCase, formato propio.
2. **VS Code, sesión «Copilot» en Agent Host**: «uses the same SDK hook implementation as Copilot CLI» (se usa la referencia de GitHub; hay que comprobar que el evento exista en la versión de VS Code).
3. **Copilot CLI** (producto distinto de la extensión; ejecutable `copilot`) y agente en la nube.

Cada ítem de abajo indica a cuál se refiere.

---

## 1. Archivo de instrucciones del proyecto

**Estado: confirmado con fuente** (`https://code.visualstudio.com/docs/copilot/customization/custom-instructions`, fuente `agent-customization/custom-instructions.md`; Copilot CLI: `.../how-tos/copilot-cli/customize-copilot/add-custom-instructions.md`; 2026-10-07).

- Nombre y ubicación: `.github/copilot-instructions.md` en la raíz del repositorio. **También lee `AGENTS.md`** (formato «cross-agent») y `CLAUDE.md`. Tabla literal de VS Code, agente Local: proyecto «`.github/copilot-instructions.md`, `AGENTS.md`, or `CLAUDE.md`»; dirigidas «`.github/instructions/**/*.instructions.md` or Markdown files in `.claude/rules`».
- Jerarquía: «Applicable instruction sources are additive. Do not depend on a file order or precedence rule to resolve conflicts». Las fuentes se suman; no hay orden de precedencia garantizado.
- Interruptores del agente Local (ajustes de VS Code): `chat.useAgentsMdFile`, `chat.useClaudeMdFile`, `chat.includeApplyingInstructions`, `github.copilot.chat.codeGeneration.useInstructionFiles`; `chat.useNestedAgentsMdFiles` («disabled by default») para `AGENTS.md` anidados.
- Personal: `~/.copilot/copilot-instructions.md`; organización: ajustes de la organización en GitHub.
- Copilot CLI (tabla literal): `$HOME/.copilot/copilot-instructions.md`, `$HOME/.copilot/instructions/**/*.instructions.md`, `.github/copilot-instructions.md`, `.github/instructions/**/*.instructions.md`, `AGENTS.md`, `CLAUDE.md` (y `.claude/CLAUDE.md`), `GEMINI.md`, y directorios de la variable `COPILOT_CUSTOM_INSTRUCTIONS_DIRS`. Descubre en la raíz, el directorio actual, los intermedios y los directorios del archivo en uso. Se desactiva con `--no-custom-instructions`.
- Importación: en la CLI, dentro de `.github/copilot-instructions.md`, `AGENTS.md` o `CLAUDE.md`, `@ruta/relativa` incluye otro archivo («File references are not expanded in `GEMINI.md` or `*.instructions.md` files»; no se cargan rutas absolutas ni `~/`). En VS Code, enlaces Markdown relativos al archivo. Para `AGENTS.md` en VS Code: no se pudo confirmar que `@archivo` se expanda.
- Las instrucciones **no** se usan en las sugerencias en línea al escribir.
- Límite de tamaño: **no se pudo confirmar** (se buscó en ambas páginas).

Ejemplo literal (VS Code):

```markdown
# Project instructions

## Architecture

* Add HTTP handlers under `src/api/routes`.
* Keep database access in `src/repositories` so handlers remain independently testable.

## Validation

* Run `npm test -- <changed-package>` after changing application code.
* Add or update tests for every behavior change.
```

## 2. Reglas por ruta o patrón

**Estado: confirmado con fuente** (misma página, 2026-10-07).

Archivos `*.instructions.md` en `.github/instructions/` (búsqueda recursiva); en la CLI también `~/.copilot/instructions/`. Claves de cabecera (tabla literal): `name` (opcional), `description` (opcional; permite carga «on-demand»), `applyTo` («Glob pattern that automatically applies the instructions to matching files, relative to the workspace root. Use `**` to match all files»). Para reglas de Claude (`.claude/rules`) se usa `paths` (arreglo de globos; por defecto `**`) en lugar de `applyTo`. Si faltan `description` y `applyTo`, el archivo se adjunta a mano. Ejemplo literal:

```markdown
---
name: 'Python testing'
description: 'Use when creating or updating Python unit tests.'
applyTo: '**/*.py'
---
# Python testing

* Use `pytest` fixtures from `tests/conftest.py` instead of creating duplicate setup helpers.
* Name tests `test_<behavior>_<condition>`.
* Run `python -m pytest <test-file>` after changing a test.
```

- En VS Code el archivo «se adjunta» cuando el patrón coincide con un archivo que el agente **crea o modifica**; en la CLI, «Path-specific instructions are included only when their `applyTo` value matches a file that Copilot CLI is working with». Sintaxis de varios patrones separados por coma, o exclusión del arnés (`excludeAgent`): **no se pudo confirmar** en estas páginas.
- Ajuste `chat.instructionsFilesLocations` obsoleto (solo Local).

## 3. Hooks que pueden denegar una acción

**Estado: parcialmente confirmado.** En VS Code la experiencia está en **Preview** (título literal: «Configure agent hooks in VS Code (Preview)»; «The VS Code hooks experience is in Preview. Individual provider implementations might have a different lifecycle status. For example, hooks in the Copilot SDK are generally available.»). Hay restricción empresarial posible: «Your organization might restrict which hooks can run».

### Qué se confirma y qué no

| Afirmación | Estado |
|---|---|
| Los hooks del arnés Local de VS Code existen, bloquean con `permissionDecision: "deny"` o salida 2 | Confirmado, **en Preview** (puede cambiar) |
| Los hooks de Copilot CLI / sesiones Copilot en Agent Host existen y bloquean | Confirmado; la página de referencia de GitHub no marca Preview, el aviso de VS Code dice que SDK es «generally available» |
| Que un mismo archivo sirva a la vez al arnés Local y a la CLI con el mismo efecto | **No se pudo confirmar** (la fuente dice lo contrario: comportamiento no idéntico) |
| Estabilidad de nombres de herramienta entre arneses | No: «Tool names and input schemas differ between harnesses» |

### 3A. VS Code, arnés Local (`https://code.visualstudio.com/docs/copilot/customization/hooks` y `.../agents/reference/hooks-reference`, 2026-10-07)

Archivos (tabla literal): espacio de trabajo `.github/hooks/*.json`; Claude `.claude/settings.json`, `.claude/settings.local.json` (requiere `chat.useClaudeHooks`, desactivado por defecto); usuario `~/.copilot/hooks/*.json`; agente propio: clave `hooks` en la cabecera de `.agent.md` (Preview; requiere `chat.useHooks` y espacio de confianza); complemento `hooks.json`. Ajustes: `chat.useHooks` (activado por defecto), `chat.hookFilesLocations`. Los hooks del espacio de trabajo están sujetos a «Workspace Trust».

Eventos (ocho): `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `SubagentStart`, `SubagentStop`, `Stop`. Formato literal:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "type": "command",
        "command": "./scripts/validate-tool.sh",
        "windows": "powershell -File scripts\\validate-tool.ps1",
        "timeout": 15
      }
    ]
  }
}
```

Propiedades: `type` (`"command"`), `command`, `windows`, `linux`, `osx`, `cwd`, `env`, `timeout` («The default is 30 seconds»). **Importante:** el analizador de Local acepta también el formato Claude pero «ignores matcher values, so every command for the event runs»; el guion debe filtrar él mismo por `tool_name`.

Entrada: JSON por stdin con `timestamp`, `cwd`, `session_id`, `hook_event_name`, `transcript_path`; en `PreToolUse`: `tool_name`, `tool_input`, `tool_use_id`.

```json
{
  "tool_name": "<local-tool-name>",
  "tool_input": {},
  "tool_use_id": "tool-123"
}
```

Respuesta que bloquea (literal; valores `allow`, `deny`, `ask`; con varios hooks gana el más restrictivo):

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Destructive command blocked by policy.",
    "additionalContext": "Production files are read-only."
  }
}
```

Códigos de salida (tabla literal): `0` éxito (se procesa stdout); `2` «Treat stderr as a blocking error and provide it to the model»; «Any other value: Show a non-blocking warning to the user and continue processing». También `continue: false` + `stopReason` detiene toda la ejecución del agente.

**Si el hook falla: continúa (falla abierto)** con códigos distintos de 2. Comportamiento al agotar `timeout`: **no se pudo confirmar** para Local. Los nombres de herramienta de Local no están en la página: hay que inspeccionarlos en el panel de registros del agente («Open the agent debug logs to inspect the Local tool schema»).

Sobre `chat.tools.terminal.autoApprove` (`approvals.md`, literal): «A `false` rule requires approval. It does not block the command. To block a terminal tool call in the Local harness, use a Preview `PreToolUse` hook that returns `permissionDecision: "deny"`.»

### 3B. Copilot CLI y sesiones Copilot en Agent Host (`https://docs.github.com/en/copilot/reference/hooks-reference`, fuente `reference/hooks-reference.md`, 2026-10-07)

Archivos, en orden de carga: políticas (`/etc/github-copilot/policy.d/*.json`; `C:\ProgramData\GitHub\Copilot\policy.d\*.json`; registro de Windows), `.github/hooks/*.json` del repositorio, `~/.copilot/hooks/*.json` (o `$COPILOT_HOME/hooks/`), bloque `hooks` en `.github/copilot/settings.json` / `settings.local.json` y en `~/.copilot/settings.json`, y complementos; también lee `.claude/settings.json` del repositorio. Los hooks de política «cannot be disabled by `disableAllHooks`». Estructura literal:

```json
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "bash": "YOUR_BASH_COMMAND",
        "powershell": "YOUR_POWERSHELL_COMMAND",
        "cwd": "OPTIONAL/WORKING/DIRECTORY",
        "env": { "VAR": "VALUE" },
        "timeoutSec": 30
      }
    ]
  }
}
```

Variante sin shell (solo CLI): `"exec": "YOUR_EXECUTABLE", "args": ["YOUR_ARGUMENT"]`. Tipos: `command`, `http` (POST JSON; `https://` obligatorio para `preToolUse`), `prompt` (solo `sessionStart`; no se dispara en `-p`). Eventos: `sessionStart`, `sessionEnd`, `userPromptSubmitted`, `userPromptTransformed`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `permissionRequest`, `agentStop`, `subagentStart`, `subagentStop`, `preCompact`, `notification`, `errorOccurred`. Con nombre en PascalCase el hook usa la carga útil «compatible con VS Code» (campos snake_case).

Entrada de `preToolUse` (literal, formato camelCase):

```typescript
{
    sessionId: string;
    timestamp: number;
    cwd: string;
    toolName: string;
    toolArgs: unknown;
}
```

Respuesta que bloquea: JSON por stdout con `permissionDecision` (`"allow"`, `"deny"`, `"ask"`), `permissionDecisionReason` («Required when decision is `"deny"`») y `modifiedArgs`. Códigos de salida (tabla literal): `0` éxito; `2` «Treated as a warning by default … For `permissionRequest` and `preToolUse`, exit `2` is treated as a deny … even if that JSON reports `permissionDecision: "allow"`»; otros distintos de cero: «Logged as a hook failure. The run continues (fail-open). **Exception: `preToolUse` is fail-closed**».

**Si el hook falla** (literal): «Command `preToolUse` hooks are **fail-closed** on errors—a crash or non-zero exit (including exit `2`) denies the tool call … Command hook **timeouts are always fail-open, even for `preToolUse` and admin-deployed policy hooks**». Hooks HTTP de `preToolUse`: fail-open. Salida vacía o JSON ilegible: «falls through to default behavior». Si hay varios hooks y alguno devuelve `deny`, se bloquea.

Filtro: `matcher` (regex anclada `^(?:PATTERN)$`) sobre `toolName` (`bash`, `powershell`, `view`, `create`, `edit`, `glob`, `grep`, `web_fetch`, `task`, `ask_user`). Con `PreToolUse` en PascalCase, se aplica semántica de Claude y los nombres cambian (`Bash`, `Read`, `Write`, `Edit`, ...). Cobertura de herramientas MCP en el filtro: **no se pudo confirmar** (la tabla de nombres no las incluye).

## 4. Comandos personalizados

**Estado: confirmado con fuente, con aviso de obsolescencia** (`https://code.visualstudio.com/docs/copilot/customization/prompt-files`, 2026-10-07).

- Archivos de instrucciones de tarea: `.github/prompts/*.prompt.md` (o perfil de usuario). Se invocan escribiendo `/nombre`. Cabecera (tabla literal): `description`, `name`, `argument-hint`, `agent` (`ask`, `agent`, `plan` o agente propio), `model`, `tools`. Variables `${input:variableName}`; referencias `#file:` y `#tool:<nombre>`. Ejemplo literal:

```markdown
---
agent: 'ask'
model: Claude Sonnet 4
description: 'Perform a REST API security review'
---
Perform a REST API security review and provide a TODO list of security issues to address.
```

- **Aviso literal:** «Prompt files are deprecated for Agent Host sessions and aren't loaded by Agent Host. They continue to work with the Local agent for now, but the Local agent will be removed in a future release.» La migración es a skills.
- Copilot CLI: no tiene archivos de comandos propios; trata como alternativa a skills archivos `.md` en `.claude/commands/` (`argument-hint`, `description`, `allowed-tools`, `disable-model-invocation`; menor prioridad que un skill del mismo nombre) (`cli-command-reference.md`).

## 5. Skills (`SKILL.md`)

**Estado: confirmado con fuente** (`https://code.visualstudio.com/docs/copilot/customization/agent-skills`; CLI: `cli-command-reference.md`; 2026-10-07).

- Proyecto: `.github/skills/`, `.claude/skills/`, `.agents/skills/`; personal: `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/` (la CLI coincide; admite `--add-dir` y padres en monorepositorio). Carga progresiva. «`.github/skills/`» si hay nombres repetidos entre raíces: manda la raíz principal.
- Cabecera (tabla literal): `name` (obligatorio; «Only lowercase letters, numbers, and hyphens … Must match the parent directory name. Maximum 64 characters. Names with invalid characters cause the skill to silently fail to load»), `description` (obligatorio; máximo 1024), `argument-hint`, `user-invocable` (por defecto `true`), `disable-model-invocation` (por defecto `false`), `context` (`fork`; marcado como característica en prueba).
- Un skill funciona como comando con `/nombre` (se oculta con `user-invocable: false`).

## 6. Registro de servidores MCP

**Estado: confirmado con fuente** (`https://code.visualstudio.com/docs/copilot/customization/mcp-servers`, `.../agents/reference/mcp-configuration`; CLI: `add-mcp-servers.md`; 2026-10-07).

- VS Code: `.vscode/mcp.json` con objeto superior `servers`; formato portable `.mcp.json` en la raíz con `mcpServers`; usuario: `mcp.json` del perfil, o `~/.copilot/mcp-config.json` / `$COPILOT_HOME/mcp-config.json` con `mcpServers`. El Agent Host lee el formato portable directamente y VS Code le reenvía lo de `.vscode/mcp.json` salvo servidores con `${input:...}`.
- CLI: `.mcp.json` (desde el directorio de trabajo hasta la raíz git), `.github/mcp.json`, `~/.copilot/mcp-config.json`; precedencia: `--additional-mcp-config` > proyecto > usuario. Requiere carpeta de confianza. Migración de `.vscode/mcp.json`: cambiar la clave `servers` por `mcpServers`.
- Campos stdio (VS Code; tabla literal): `type` (`"stdio"`), `command`, `args`, `cwd`, `env`, `envFile`, `sandboxEnabled` (macOS y Linux). HTTP/SSE: `type` (`"http"`, `"sse"`), `url`, `headers`, `oauth` (`clientId`). Sección `inputs` y `${input:id}` para secretos; `sandbox` hermano con `filesystem.allowWrite|denyRead|denyWrite` y `network.allowedDomains|deniedDomains`.

```json
{
    "servers": {
        "context7": {
            "type": "http",
            "url": "https://mcp.context7.com/mcp"
        }
    }
}
```

- CLI (literal): `{"mcpServers": {"playwright": {"type": "local", "command": "npx", "args": ["@playwright/mcp@latest"], "env": {}, "tools": ["*"]}, "context7": {"type": "http", "url": "https://mcp.context7.com/mcp", "headers": {...}, "tools": ["*"]}}}`. Nota: en la CLI `type` es `"local"`, en VS Code `"stdio"`; **diferencia de esquema** a respetar al generar.
- Interpolación `${env:...}` en la configuración de la CLI: **no se pudo confirmar**.

## 7. Permisos, modos, sandbox y listas de comandos

**Estado: confirmado con fuente**, distinto por superficie.

### VS Code (`approvals.md`, `security.md`, `agent-sandboxing.md`; 2026-10-07)

- Niveles de permisos: «Manual permissions» (por defecto), «Assisted permissions» (un modelo juzga; solo Agent Host), «Allow all» (`chat.permissions.default`). Autopilot en Agent Host.
- Terminal: `chat.tools.terminal.autoApprove`, ejemplo literal:

```jsonc
{
  // Allow the `mkdir` command
  "mkdir": true,
  // Allow `git status` and commands starting with `git show`
  "/^git (status|show\\b.*)$/": true,

  // Always require approval for the `del` command
  "del": false,
  // Always require approval for commands containing "dangerous"
  "/dangerous/": false
}
```

  Una regla `false` **exige aprobación, no bloquea**. Otros: `chat.tools.eligibleForAutoApproval`, `chat.tools.urls.autoApprove`, `chat.tools.edits.autoApprove` (globos, p. ej. `"**/.env": false`), `chat.tools.global.autoApprove` (peligroso), `chat.tools.terminal.enableAutoApprove`.
- Roles integrados: `ask`, `agent`, `plan`; `plan` y `ask` como modo solo lectura: el detalle de herramientas no se leyó.
- Sandbox del Agent Host: aplica a comandos de terminal y sus hijos; macOS sin requisitos, Linux/WSL2 requiere `bubblewrap` y `socat`, Windows «Experimental». Literal: «Turning on sandboxing does not block outbound network access by default. `chat.agent.sandbox.network.allowNetwork` defaults to `true`.» Sandbox de servidores MCP: `sandboxEnabled` (sección 6).

### Copilot CLI (`cli-command-reference.md`, 2026-10-07)

- Banderas: `--allow-tool=TOOL ...`, `--deny-tool=TOOL ...`, `--allow-all-tools`, `--allow-all-paths`, `--allow-all-urls`, `--allow-all`/`--yolo`, `--sandbox` (sandbox de shell del sistema operativo, por sesión). Variable `COPILOT_ALLOW_ALL`. Comando `/permissions [default|assisted|allow-all|show]`.
- Patrones `Kind(argumento)` (tabla literal): `read`, `shell`, `url`, `write`, `NOMBRE-DE-SERVIDOR-MCP`. Ejemplos literales:

```shell
copilot --allow-tool='shell(git:*)' --deny-tool='shell(git push)'
copilot --deny-tool='write(secret.txt)'
```

- «Deny rules always take precedence over allow rules, even when `--allow-all` is set.» Con `permissions.disableBypassPermissionsMode` en política se anulan las banderas de permiso total (cierra ante valor desconocido).
- Modo solo lectura: `--plan` / `--mode plan`; agentes integrados `code-review`, `security-review` («Will not modify code»).

## 8. Ejecución no interactiva para CI

**Estado: confirmado con fuente solo para Copilot CLI** (`.../how-tos/copilot-cli/automate-copilot-cli/run-cli-programmatically.md` y `cli-programmatic-reference.md`, 2026-10-07). La extensión de VS Code no tiene modo no interactivo documentado (se buscó en las páginas de VS Code leídas).

```yaml
- name: Generate test coverage report
  env:
    COPILOT_GITHUB_TOKEN: ${{ secrets.PERSONAL_ACCESS_TOKEN }}
  run: |
    copilot -p "Run the test suite and produce a coverage summary" \
      -s --allow-tool='shell(npm:*), write' --no-ask-user
```

- Banderas: `-p`/`--prompt`, `-s` (silencioso), `--no-ask-user`, `--model`, `--allow-tool`, `--deny-tool`, `--allow-url`, `--share`, `--output-format json` (JSONL), `--sandbox`. Entrada por tubería (se ignora si hay `-p`). Variable `COPILOT_TASK_WAIT_TIMEOUT_SECONDS` (por defecto 600).
- Hooks en `-p`: los de tipo `prompt` **no** se disparan en modo no interactivo (literal); que `preToolUse` sí se evalúe en `-p` **no se pudo confirmar** con una frase explícita.
- Códigos de salida de `copilot -p`: **no se pudo confirmar** (la tabla de códigos documentada es del subcomando `copilot workflow run`: 0, 1, 2, 130).
- Comportamiento ante un permiso sin conceder en `-p`: **no se pudo confirmar** con una frase explícita; el reglamento documentado es dar permisos mínimos con `--allow-tool`.

## 9. Subagentes

**Estado: confirmado con fuente** (`https://code.visualstudio.com/docs/copilot/customization/custom-agents`, `.../agents/run/subagents`; CLI: `cli-command-reference.md`, `create-custom-agents-for-cli.md`; 2026-10-07).

- VS Code: agentes propios `.github/agents/*.agent.md` (también detecta `.md` en esa carpeta), `.claude/agents`, usuario `~/.copilot/agents` o `~/.claude/agents`. Cabecera (tabla literal): `description`, `name`, `argument-hint`, `tools`, `agents` («A list of agent names that are available as subagents … Use `*` to allow all agents, or an empty array `[]` to prevent any subagent use»; requiere la herramienta `agent` en `tools`), `model`, `user-invocable`, `disable-model-invocation`, `target`, `mcp-servers`, `handoffs`, `hooks` (Preview). Ejemplo literal de subagente:

```markdown
---
name: Codebase Researcher
description: Find relevant code and explain existing patterns
user-invocable: false
tools: ['read', 'search']
---
Research the requested topic without changing files.
Return relevant file paths, existing patterns, and unanswered questions.
```

- Local: herramienta `runSubagent`; el subagente no hereda la conversación; sin anidamiento por defecto (`chat.subagents.allowInvocationsFromSubagents` = `false`; profundidad máxima 5). Paralelismo en VS Code: **no se pudo confirmar** con una frase explícita.
- CLI: `.github/agents/`, `~/.copilot/agents/`; cabecera: `description` (obligatoria), `tools`, `model`, `models`, `modelPolicy`, `reasoningEffort`, `infer`, `mcp-servers`, `include-custom-instructions`, `name`. Integrados `code-review`, `explore` («Safe to run in parallel»), `general-purpose`, `research`, `rubber-duck`, `security-review`, `task`. Bandera `--agent`; `--fleet` para subagentes en paralelo en `-p`.

---

## Lo que un adaptador puede generar con seguridad hoy

Solo lo confirmado arriba.

1. `.github/copilot-instructions.md` y/o `AGENTS.md` en la raíz (Markdown plano). Para la CLI, `@ruta` relativa para importar.
2. Reglas por ruta: `.github/instructions/<nombre>.instructions.md` con `applyTo` (un solo patrón) y, opcionalmente, `name`/`description`.
3. Skills: `.github/skills/<nombre>/SKILL.md` con `name` (igual al directorio, minúsculas-números-guiones, ≤ 64) y `description` (≤ 1024). Es la vía de «comandos» recomendada.
4. Subagentes: `.github/agents/<nombre>.agent.md` con `description`, `tools`, `name`; para la CLI solo `description` es obligatorio.
5. MCP: `.vscode/mcp.json` (`servers`, `type: stdio|http|sse`) para VS Code, o `.mcp.json` (`mcpServers`; en la CLI `type: local|http`) para el formato portable; secretos con `inputs`/`${input:}` en VS Code; nunca valores en el archivo.
6. Permisos de la CLI: `--deny-tool` / `--allow-tool` con `Kind(argumento)`, en línea de comandos o scripts de CI.
7. Ejecución en CI: `copilot -p '...' -s --allow-tool='...' --no-ask-user` (con `COPILOT_GITHUB_TOKEN`).
8. Hook de bloqueo (ver diseño), marcado como Preview en VS Code, con prueba real previa.

## Lo que no debe generarse todavía

- Archivos `.prompt.md` para sesiones de Agent Host (obsoletos); usar skills.
- Un único archivo de hooks que se espere que funcione igual en el arnés Local de VS Code y en la CLI (formatos distintos: sin `version` y `command`/`timeout` en Local; `version: 1`, `bash`/`powershell`/`timeoutSec` en la CLI).
- Dependencia de que un hook de Local falle cerrado, de su comportamiento al expirar, o de que `matcher` funcione en Local (se ignora).
- Hooks de agente propio (`hooks` en `.agent.md`) como control de seguridad (Preview).
- `${env:...}` en la configuración MCP de la CLI.
- Reglas `autoApprove` con `false` como si bloquearan (solo piden aprobación).
- Cualquier supuesto sobre códigos de salida de `copilot -p`, `preToolUse` en `-p`, límites de tamaño de instrucciones, paralelismo de subagentes en VS Code, o nombres de herramienta del arnés Local sin inspeccionar los registros.

### Diseño del hook de bloqueo de datos

Objetivo: impedir que el agente lea, escriba o vuelque datos sensibles antes de que ocurra. Diseño propio, no copiado; solo usa campos confirmados arriba.

**Capa 1, declarativa (no depende de que un guion funcione).**
- CLI: `--deny-tool='read(.env)'`, `--deny-tool='write(.env)'`, `--deny-tool='shell(mysqldump)'` (la denegación prevalece incluso con `--allow-all`); en política de la organización, `permissions.disableBypassPermissionsMode`.
- VS Code: `chat.tools.edits.autoApprove` con `"**/.env": false` (exige aprobación, no bloquea); sandbox del Agent Host para limitar sistema de archivos y red de comandos.

**Capa 2, hook (una variante por superficie).**
- **CLI y sesiones Copilot en Agent Host:** `.github/hooks/<nombre>.json` con `version: 1`, evento `preToolUse`, `matcher` regex amplia (`.*`), comando con `bash`/`powershell` y `timeoutSec` bajo. El guion lee `toolName` y `toolArgs` (camelCase), compara rutas y comandos con una lista de patrones y responde por stdout con `{"permissionDecision":"deny","permissionDecisionReason":"..."}` y salida `0`, o sale con `2`. Esta superficie es **cerrada ante errores** (cualquier salida distinta de cero deniega), salvo **tiempo agotado, que deja pasar**: por eso el guion debe ser rápido y sin llamadas de red.
- **Arnés Local de VS Code (Preview):** `.github/hooks/<nombre>.json` sin `version`, evento `PreToolUse`, comando con `windows`/`linux`/`osx` si hace falta y `timeout`. Como `matcher` se ignora, el guion filtra por `tool_name` por sí mismo. Responde con `hookSpecificOutput.permissionDecision: "deny"` o sale con `2`. Esta superficie es **abierta ante errores** (otra salida distinta de 0 y 2 solo avisa): el guion debe envolver todo en un `try/except` general que termine con `exit 2` ante cualquier fallo.
- Antes de fijar nombres de herramienta: registrar una carga útil real en cada superficie (en Local, el panel de registros del agente; en la CLI, un hook de bitácora `postToolUse`) y probar `bash`, `view`/`read`, `edit`/`create` y una herramienta MCP.
- Tratar las llamadas de herramientas MCP como no cubiertas hasta verificarlo: la tabla de nombres de la CLI no las lista.
