# Cursor: formato exacto de configuración (contraste con la fuente)

<!-- tipo: estandar · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: documentación oficial (URLs en el documento) -->

## Fuentes y método

Leídas el 2026-10-07 en su versión Markdown oficial (la documentación publica cada página con sufijo `.md`; el índice está en `https://cursor.com/llms.txt`). Solo lectura; no se ejecutó ni instaló el agente.

- `https://cursor.com/docs/rules.md`
- `https://cursor.com/docs/hooks.md` y `https://cursor.com/docs/reference/third-party-hooks.md`
- `https://cursor.com/docs/skills.md`
- `https://cursor.com/docs/subagents.md`
- `https://cursor.com/docs/mcp.md`
- `https://cursor.com/docs/plugins.md` y `https://cursor.com/docs/reference/plugins.md`
- `https://cursor.com/docs/agent/security/run-modes.md`, `https://cursor.com/docs/agent/plan-mode.md`
- `https://cursor.com/docs/cli/using.md`, `.../cli/headless.md`, `.../cli/reference/parameters.md`, `.../cli/reference/permissions.md`, `.../cli/reference/configuration.md`, `.../cli/reference/output-format.md`, `.../cli/changelog.md`

Cambio de rutas respecto a `MATRIZ.md`: las páginas actuales cuelgan de `/docs/rules`, `/docs/hooks`, `/docs/skills`, `/docs/subagents`, `/docs/mcp`, `/docs/plugins` (sin `context/`). Con sufijo `.md`, las rutas antiguas (`context/rules`, etc.) devuelven «Page not found».

No existe un esquema JSON oficial publicado de `hooks.json` que se haya encontrado (se buscó en la documentación y en `llms.txt`); el formato sale de la página de hooks. No se leyó `https://cursor.com/docs/reference/sandbox.md`.

Los ejemplos están copiados literalmente de la fuente.

---

## 1. Archivo de instrucciones del proyecto

**Estado: confirmado con fuente** (`https://cursor.com/docs/rules.md`, `https://cursor.com/docs/cli/using.md`, 2026-10-07).

- Cuatro tipos de reglas: Project Rules (`.cursor/rules`), User Rules (ajustes de Cursor, no son archivos), Team Rules (panel de administración) y `AGENTS.md`.
- `AGENTS.md`: «Place it in your project root as an alternative to `.cursor/rules`»; «Cursor supports AGENTS.md in the project root and subdirectories.» Es Markdown plano, sin frontmatter.
- Jerarquía de anidados (literal): «Instructions from nested `AGENTS.md` files are combined with parent directories, with more specific instructions taking precedence.»
- Orden entre tipos (literal, para Team Rules): «Rules are applied in this order: **Team Rules → Project Rules → User Rules**. All applicable rules are merged; earlier sources take precedence when guidance conflicts.» El lugar de `AGENTS.md` en ese orden no está documentado.
- CLI: «The CLI also reads `AGENTS.md` and `CLAUDE.md` at the project root (if present) and applies them as rules alongside `.cursor/rules`.»

```bash
project/
  AGENTS.md              # Global instructions
  frontend/
    AGENTS.md            # Frontend-specific instructions
    components/
      AGENTS.md          # Component-specific instructions
  backend/
    AGENTS.md            # Backend-specific instructions
```

- Para enlazar: no hay que enlazar nada; `AGENTS.md` se lee por nombre. Referencias a archivos desde una regla: «A file mention like `@migration-template.sql` tells Agent where to look, and Agent reads the file with its tools when it needs the content. The file's contents are not inlined into the prompt.»
- Límite de tamaño duro: **no se pudo confirmar** (se buscó en `rules.md`). Solo recomendación: «Keep rules under 500 lines».

## 2. Reglas por ruta o patrón

**Estado: confirmado con fuente** (`https://cursor.com/docs/rules.md`, 2026-10-07).

- Ubicación: `.cursor/rules/`, con subcarpetas. **Extensión `.mdc` obligatoria** (literal): «Project rules must use the `.mdc` extension. A plain `.md` file in `.cursor/rules` is ignored by the rules system».
- Claves de cabecera: `description`, `globs`, `alwaysApply`. Interacción (tabla literal):

| `alwaysApply` | `description` | `globs`  | Behavior                                                         |
| :------------ | :------------ | :------- | :--------------------------------------------------------------- |
| `true`        | —             | —        | Always included. Globs and description are ignored.              |
| `false`       | —             | provided | Auto-attached when a matching file is in context.                |
| `false`       | provided      | omitted  | Agent reads the description and pulls the rule in when relevant. |
| `false`       | omitted       | omitted  | Included only when you `@`-mention the rule in chat.             |

```md
---
globs: src/components/**/*.tsx
alwaysApply: false
---

- Use named exports, not default exports
- Co-locate styles in a module CSS file next to the component
```

```md
---
description: RPC service conventions and patterns for the backend
alwaysApply: false
---

- Define each service in its own file under `src/services/`
```

```md
---
alwaysApply: true
---

- All source files must include the company copyright header
```

- Valor de `globs`: texto con patrones separados por coma («Separate multiple patterns with commas»), p. ej. `docs/**/*.md, docs/**/*.mdx`. Los ejemplos oficiales usan texto sin comillas; no hay ejemplo oficial con lista YAML para reglas (sí para skills).
- «Auto-attached when a matching file is in context»: se activa por archivos presentes en el contexto, no por «archivos editados».
- Las reglas no afectan a Cursor Tab ni a Inline Edit con User Rules (FAQ de la página).

## 3. Hooks que pueden denegar una acción

**Estado: confirmado con fuente** (`https://cursor.com/docs/hooks.md`, 2026-10-07; CLI: `https://cursor.com/docs/cli/changelog.md`).

Archivo: `<proyecto>/.cursor/hooks.json` o `~/.cursor/hooks.json`; también empresa (`/etc/cursor/hooks.json` en Linux/WSL, `/Library/Application Support/Cursor/hooks.json` en macOS, `C:\ProgramData\Cursor\hooks.json` en Windows) y equipo (panel). Prioridad: Empresa, Equipo, Proyecto, Usuario; se ejecutan todos y las respuestas se fusionan («any `deny` wins over `ask`, and `ask` wins over `allow`»). Cursor recarga el archivo al guardar. Los hooks de proyecto se ejecutan desde la raíz del proyecto, por eso la ruta es `.cursor/hooks/script.sh`.

```json
{
  "version": 1,
  "hooks": {
    "afterFileEdit": [{ "command": ".cursor/hooks/format.sh" }]
  }
}
```

Entrada: JSON por la entrada estándar. Campos comunes a todos: `conversation_id`, `generation_id`, `model`, `model_id`, `model_params`, `hook_event_name`, `cursor_version`, `workspace_roots`, `user_email`, `transcript_path`. Variables de entorno: `CURSOR_PROJECT_DIR`, `CURSOR_VERSION`, `CLAUDE_PROJECT_DIR`, entre otras.

Eventos de agente: `sessionStart`, `sessionEnd`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `subagentStart`, `subagentStop`, `beforeShellExecution`, `afterShellExecution`, `beforeMCPExecution`, `afterMCPExecution`, `beforeReadFile`, `afterFileEdit`, `beforeSubmitPrompt`, `preCompact`, `stop`, `afterAgentResponse`, `afterAgentThought`. De Tab: `beforeTabFileRead`, `afterTabFileEdit`. De aplicación: `workspaceOpen`.

Hooks con permiso (pueden denegar): `beforeShellExecution`, `beforeMCPExecution`, `beforeReadFile`, `beforeTabFileRead`, `subagentStart`, `preToolUse` (literal en «Exit code behavior»).

Opciones por hook (tabla literal): `command` (obligatorio), `type` (`"command"` o `"prompt"`), `timeout` (segundos), `loop_limit` (solo `stop`/`subagentStop`, por defecto 5), `failClosed` (booleano, por defecto `false`), `matcher` (regex).

Códigos de salida (literal):

- Exit code `0` - Hook succeeded, use the JSON output. For permission hooks (`beforeShellExecution`, `beforeMCPExecution`, `beforeReadFile`, `beforeTabFileRead`, `subagentStart`, `preToolUse`), invalid JSON or a response that doesn't match the hook's schema blocks the action.
- Exit code `2` - Block the action (equivalent to returning `permission: "deny"`)
- Other exit codes - Hook failed, action proceeds (fail-open by default)

`failClosed` (literal): «When `true`, hook failures (crash, timeout, non-zero exit code, no output) block the action instead of allowing it through. Permission hooks block on invalid JSON or an invalid response even when this is `false`.»

Ejemplo de entrada y respuesta que bloquea (`beforeShellExecution`, literal):

```json
// beforeShellExecution input
{
  "command": "<full terminal command>",
  "cwd": "<current working directory>",
  "sandbox": false
}

// Output
{
  "permission": "allow" | "deny" | "ask",
  "user_message": "<message shown in client>",
  "agent_message": "<message sent to agent>"
}
```

```json
{
  "continue": true,
  "permission": "deny",
  "user_message": "Git command blocked. Please use the GitHub CLI (gh) tool instead.",
  "agent_message": "The git command '$command' has been blocked by a hook."
}
```

Ejemplo de configuración con filtro (literal):

```json
{
  "version": 1,
  "hooks": {
    "beforeShellExecution": [
      {
        "command": "./scripts/approve-network.sh",
        "timeout": 30,
        "matcher": "curl|wget|nc"
      }
    ]
  }
}
```

`preToolUse` (para cualquier herramienta; el `matcher` filtra por `Shell`, `Read`, `Write`, `Grep`, `Delete`, `Task` y `MCP:<tool_name>`):

```json
// Input
{
  "tool_name": "Shell",
  "tool_input": { "command": "npm install", "working_directory": "/project" },
  "tool_use_id": "abc123",
  "cwd": "/project"
}

// Output
{
  "permission": "allow" | "deny",
  "user_message": "<message shown in client when denied>",
  "agent_message": "<message sent to agent when denied>",
  "updated_input": { "command": "npm ci" }
}
```

Matices por evento (literal): en `preToolUse`, `"ask"` «is accepted by the schema but not enforced»; en `subagentStart`, `"ask"` «is not supported ... and is treated as "deny"»; `beforeReadFile` y `beforeTabFileRead` solo `allow`/`deny`. `beforeMCPExecution` recibe `tool_name`, `tool_input`, `mcp_server_name` y `url` o `command`; la documentación recomienda `failClosed: true` para los críticos de seguridad.

Compatibilidad: Cursor también lee hooks de `.claude/settings.json`, `.claude/settings.local.json` y `~/.claude/settings.json` (ajuste «Include Third-Party Plugins, Skills, and Other Configs», activo por defecto) y acepta la respuesta con `hookSpecificOutput`/`permissionDecision` (`https://cursor.com/docs/reference/third-party-hooks.md`).

Dónde corren: IDE y agentes en la nube (solo hooks de comando; en la nube no corren `sessionStart`, `sessionEnd`, `beforeMCPExecution`, `afterMCPExecution`, Tab ni `workspaceOpen`). CLI: el registro de cambios de la CLI menciona que los hooks se disparan y aceptan cargas por entrada estándar (`https://cursor.com/docs/cli/changelog.md`); la página de hooks no detalla qué eventos corren en la CLI, así que **qué subconjunto de hooks aplica en `agent -p` no se pudo confirmar**.

## 4. Comandos personalizados

**Estado: no se pudo confirmar** la ubicación independiente (`.cursor/commands/`).

Se intentó: lectura de `rules`, `skills`, `plugins`, `reference/plugins`, `cli/reference/slash-commands`; búsqueda de `.cursor/commands` en todas ellas (0 coincidencias); `https://cursor.com/docs/commands.md` y `.../customize/commands.md` devuelven «Page not found»; el índice `llms.txt` ya no lista una página de comandos. Lo que sí está confirmado:

- Plugins: `commands/` dentro del plugin, extensiones `.md`, `.mdc`, `.markdown`, `.txt`, con frontmatter `name` y `description` (`https://cursor.com/docs/reference/plugins.md`):

```markdown
---
name: deploy-staging
description: Deploy the current branch to the staging environment
---

# Deploy to staging
```

- Reemplazo recomendado: skills con `disable-model-invocation: true` («behave like a traditional slash command, where it is only included in context when you explicitly type `/skill-name`»). La habilidad integrada `/migrate-to-skills` convierte «user-level and workspace-level commands», sin decir las rutas.

## 5. Skills

**Estado: confirmado con fuente** (`https://cursor.com/docs/skills.md`, 2026-10-07).

Ubicaciones (tabla literal): `.agents/skills/` y `.cursor/skills/` (proyecto); `~/.agents/skills/` y `~/.cursor/skills/` (usuario). Por compatibilidad también `.claude/skills/`, `.codex/skills/`, `~/.claude/skills/`, `~/.codex/skills/`. Se admiten subcarpetas de categoría y directorios anidados en el repositorio (limitan el alcance a ese directorio).

```markdown
---
name: my-skill
description: Short description of what this skill does and when to use it.
---

# My Skill
```

Campos: `name` (obligatorio, minúsculas, números y guiones, igual a la carpeta), `description` (obligatorio), `paths` (globos, texto con comas o lista), `disable-model-invocation`, `icon`, `color`, `metadata`.

```markdown
---
name: react-component-patterns
description: Conventions for writing React components in this codebase.
paths:
  - "**/*.tsx"
  - "packages/ui/**/*.ts"
---
```

Carpetas opcionales: `scripts/`, `references/`, `assets/`.

## 6. Registro de servidores MCP

**Estado: confirmado con fuente** (`https://cursor.com/docs/mcp.md`, 2026-10-07).

Archivos: `.cursor/mcp.json` (proyecto) y `~/.cursor/mcp.json` (global). Clave raíz `mcpServers`.

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "mcp-server"],
      "env": {
        "API_KEY": "value"
      }
    }
  }
}
```

```json
{
  "mcpServers": {
    "server-name": {
      "url": "http://localhost:3000/mcp",
      "headers": {
        "API_KEY": "value"
      }
    }
  }
}
```

- STDIO: `command`, `args`, `env`, `envFile` (solo STDIO). La tabla de la página marca `type` (`"stdio"`) como obligatorio, pero los ejemplos oficiales lo omiten: **discrepancia interna de la documentación**; generar sin `type` como en los ejemplos.
- Remotos: `url`, `headers`, y `auth` para OAuth estático.
- Interpolación (literal): «Cursor resolves variables in these fields: `command`, `args`, `env`, `url`, and `headers`.» Sintaxis: `${env:NAME}`, `${userHome}`, `${workspaceFolder}`, `${workspaceFolderBasename}`, `${pathSeparator}`, `${/}`.
- La CLI respeta el mismo `mcp.json`; `--approve-mcps` aprueba todos los servidores.

## 7. Permisos y modos

**Estado: confirmado con fuente** (`https://cursor.com/docs/cli/reference/permissions.md`, `.../cli/reference/configuration.md`, `.../agent/security/run-modes.md`, `.../cli/using.md`, 2026-10-07).

CLI: `~/.cursor/cli-config.json` (global) o `<proyecto>/.cursor/cli.json` («Only permissions can be configured at the project level»).

```json
{
  "permissions": {
    "allow": [
      "Shell(ls)",
      "Shell(git)",
      "Read(src/**/*.ts)",
      "Write(package.json)",
      "WebFetch(docs.github.com)",
      "Mcp(datadog:*)"
    ],
    "deny": [
      "Shell(rm)",
      "Read(.env*)",
      "Write(**/*.key)",
      "WebFetch(malicious-site.com)"
    ]
  }
}
```

- Tipos: `Shell(commandBase)` (primer token; admite `comando:argumentos`), `Read(...)`, `Write(...)`, `WebFetch(...)`, `Mcp(servidor:herramienta)`. «Deny rules take precedence over allow rules». El campo `approvalMode` del archivo global acepta `allowlist`, `auto-review` o `unrestricted`.
- Modos de agente (CLI): Plan (`--plan` / `--mode=plan`, Mayús+Tab) y Ask (`--mode=ask`): «Use Ask mode to explore code without making changes». En el IDE, `https://cursor.com/docs/agent/plan-mode.md` describe el modo Plan.
- IDE: modos de ejecución Auto-review, Allowlist y Run Everything; `permissions.json` (`~/.cursor/permissions.json` o `<proyecto>/.cursor/permissions.json`) solo guarda instrucciones en lenguaje natural para el clasificador, **no** una lista determinista:

```json
{
  "autoRun": {
    "allow_instructions": [],
    "block_instructions": [
      "Every AWS CLI command should go through approval first.",
      "Every command that modifies Kubernetes resources should go through approval first."
    ]
  }
}
```

  Auto-review no es un límite de seguridad: la página tiene un apartado titulado «Auto-review is not a security boundary».
- Sandbox: `~/.cursor/sandbox.json` o `<proyecto>/.cursor/sandbox.json` (esquema en `reference/sandbox.md`, no leído).
- Subagentes solo lectura: `readonly: true` (ver 9).

## 8. Ejecución no interactiva para CI

**Estado: confirmado con fuente** (`https://cursor.com/docs/cli/headless.md`, `.../cli/reference/parameters.md`, `.../cli/reference/output-format.md`, 2026-10-07).

```bash
export CURSOR_API_KEY=your_api_key_here
agent -p "Analyze this code"
```

```bash
agent -p --force "Refactor this code to use modern ES6+ syntax"
```

Banderas confirmadas: `-p, --print`, `--output-format <format>` (`text`, `json`, `stream-json`; por defecto `text`; solo con `--print`), `--stream-partial-output`, `-f, --force` / `--yolo` («Force allow commands unless explicitly denied»), `--mode <mode>` (`plan` o `ask`), `--plan`, `--model`, `--resume`, `--continue`, `--sandbox <mode>` (`enabled` o `disabled`), `--approve-mcps`, `--trust` («Trust the workspace without prompting (headless mode only)»), `--workspace`, `--api-key` o `CURSOR_API_KEY`. Sin `--force`, «changes are only proposed, not applied».

Salida `json` en éxito: `{"type":"result","subtype":"success","is_error":false,"duration_ms":...,"result":"...","session_id":"..."}`. «On failure, the process exits with a non-zero code and writes an error message to stderr.» Códigos de salida concretos: no documentados.

## 9. Subagentes

**Estado: confirmado con fuente** (`https://cursor.com/docs/subagents.md`, 2026-10-07).

Ubicaciones (tabla literal): `.cursor/agents/`, `.claude/agents/`, `.codex/agents/` (proyecto); `~/.cursor/agents/`, `~/.claude/agents/`, `~/.codex/agents/` (usuario). «When multiple locations contain subagents with the same name, `.cursor/` takes precedence over `.claude/` or `.codex/`.»

```markdown
---
name: security-auditor
description: Security specialist. Use when implementing auth, payments, or handling sensitive data.
model: inherit
readonly: true
---

You are a security expert auditing code for vulnerabilities.
```

Campos (todos opcionales): `name`, `description`, `model` (`inherit` o ID), `readonly` («restricted write permissions (no file edits, no state-changing shell commands)»), `is_background`. Paralelismo y ejecución en segundo plano: `is_background: true`; en el hook `subagentStart` aparece `is_parallel_worker`. Un tope de concurrencia: no se pudo confirmar.

---

## Lo que un adaptador puede generar con seguridad hoy

Solo lo confirmado arriba:

1. `AGENTS.md` en la raíz y subdirectorios (sin frontmatter); la CLI además lee `CLAUDE.md` de la raíz.
2. Reglas `.cursor/rules/**/*.mdc` con cabecera `description` / `globs` / `alwaysApply` según la tabla de combinaciones (nunca `.md`).
3. `.cursor/hooks.json` con `{"version": 1, "hooks": {...}}`, hooks de comando con `timeout`, `matcher` y, para los de seguridad, `"failClosed": true`; el script devuelve JSON `permission` (`allow`/`deny`) o sale con código 2. Para `beforeMCPExecution` y `beforeShellExecution` también `ask`.
4. Skills en `.cursor/skills/<name>/SKILL.md` (o `.agents/skills/`) con `name` igual a la carpeta, `description`, `paths` opcional, `disable-model-invocation` opcional.
5. `.cursor/mcp.json` con `mcpServers`, STDIO (`command`, `args`, `env`) o remoto (`url`, `headers`) e interpolación `${env:NAME}`.
6. Permisos de la CLI en `.cursor/cli.json` con `permissions.allow` / `permissions.deny` (`Shell()`, `Read()`, `Write()`, `WebFetch()`, `Mcp()`); `deny` prevalece.
7. Subagentes en `.cursor/agents/<nombre>.md` con `name`, `description`, `model`, `readonly`, `is_background`.
8. CI: `agent -p --output-format json` (añadir `--force` solo si debe escribir), con `CURSOR_API_KEY`; `--mode=ask` o `--plan` para solo lectura.

## Lo que no debe generarse todavía

- Comandos personalizados fuera de plugins (`.cursor/commands/` no está documentado hoy); usar skills con `disable-model-invocation: true`.
- Reglas `.md` en `.cursor/rules` (se ignoran) o listas YAML en `globs` (sin ejemplo oficial).
- `permission: "ask"` en `preToolUse` o `subagentStart` (no se aplica o se trata como `deny`).
- Hooks de seguridad sin `failClosed: true`: por defecto un fallo del script (código distinto de 0 y 2, tiempo agotado) deja pasar la acción.
- Suponer qué eventos de hooks corren en `agent -p`, o que los de Tab o de MCP corran en agentes en la nube.
- `permissions.json` del IDE como control determinista (son instrucciones en lenguaje natural para un clasificador).
- Un límite de tamaño de reglas o de `AGENTS.md`, o un tope de concurrencia de subagentes.
- `type: "stdio"` en `mcp.json` (la tabla lo exige pero los ejemplos oficiales lo omiten; no está claro cuál manda).
- Paquetes de plugin (`.cursor-plugin/plugin.json`) hasta leer su referencia completa: solo se confirmó la estructura de carpetas (`rules/`, `skills/`, `agents/`, `commands/`, `hooks/hooks.json`, `mcp.json`).
