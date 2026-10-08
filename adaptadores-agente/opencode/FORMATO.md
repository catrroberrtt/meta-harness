# OpenCode: formato exacto de configuración (contraste con la fuente)

<!-- tipo: estandar · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: documentación oficial (URLs en el documento) -->

## Fuentes y método

Se leyeron, el 2026-10-07, estos orígenes (solo lectura, sin ejecutar ni instalar el agente):

- Fuente de las páginas de documentación, en crudo (los `.mdx` de los que se genera `https://opencode.ai/docs/`): `https://raw.githubusercontent.com/sst/opencode/dev/packages/web/src/content/docs/<pagina>.mdx` (redirige al repositorio oficial `anomalyco/opencode`, rama `dev`, commit `a697115b203395c54a7496dc3d1863fe7b319c0c` en la fecha de lectura). Páginas: `rules`, `plugins`, `agents`, `commands`, `skills`, `mcp-servers`, `permissions`, `cli`, `config`.
- Esquema JSON oficial de la configuración: `https://opencode.ai/config.json` (leído el 2026-10-07).
- Código fuente oficial, solo para el comportamiento de los hooks (no está en la documentación): `packages/opencode/src/plugin/index.ts`, `packages/opencode/src/session/tools.ts` y `packages/opencode/src/session/prompt.ts`, rama `dev`, mismo commit.

Limitación: las páginas se leyeron como fuente `.mdx`, no renderizadas en `opencode.ai/docs`. Todo lo que cita el código fuente (no la documentación) lleva la etiqueta **[código]**: es comportamiento actual de la rama `dev`, no un contrato documentado.

Los ejemplos de abajo están copiados literalmente de la fuente; solo se ha quitado texto circundante.

---

## 1. Archivo de instrucciones del proyecto

**Estado: confirmado con fuente** (`https://opencode.ai/docs/rules/`, 2026-10-07).

- Nombre y ubicación: `AGENTS.md` en la raíz del proyecto. Global: `~/.config/opencode/AGENTS.md`.
- Jerarquía (literal): «When opencode starts, it looks for rule files in this order: 1. Local files by traversing up from the current directory (`AGENTS.md`, `CLAUDE.md`) 2. Global file at `~/.config/opencode/AGENTS.md` 3. Claude Code file at `~/.claude/CLAUDE.md` (unless disabled). The first matching file wins in each category.»
- Alternativa de compatibilidad: `CLAUDE.md` del proyecto solo se usa si no existe `AGENTS.md`. Se desactiva con `OPENCODE_DISABLE_CLAUDE_CODE=1`, `OPENCODE_DISABLE_CLAUDE_CODE_PROMPT=1` u `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`.
- `AGENTS.md` es el nombre principal: no hay que enlazarlo con nada. Para añadir otros archivos: clave `instructions` en `opencode.json`.
- Importaciones: la documentación dice «While opencode doesn't automatically parse file references in `AGENTS.md`». Es decir, `@archivo` dentro de `AGENTS.md` NO se expande solo.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["CONTRIBUTING.md", "docs/guidelines.md", ".cursor/rules/*.md"]
}
```

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["docs/development-standards.md", "test/testing-guidelines.md", "packages/*/AGENTS.md"]
}
```

- `instructions` admite globos y URLs remotas (descarga con tiempo límite de 5 segundos). «All instruction files are combined with your `AGENTS.md` files.»
- Límite de tamaño del archivo: **no se pudo confirmar** (se buscó en `rules.mdx` y `config.mdx`; no aparece).
- El esquema (`https://opencode.ai/config.json`) confirma la clave `instructions` en la raíz.

## 2. Reglas por ruta o patrón

**Estado: no se pudo confirmar** que exista activación por ruta editada.

Se intentó: lectura completa de `rules.mdx` y de `config.mdx`, y revisión de las claves de la raíz del esquema JSON. No hay frontmatter de reglas con `globs` ni equivalente. Lo único cercano, confirmado:

- `instructions` con globos (`packages/*/AGENTS.md`) carga archivos **siempre**, no según el archivo editado.
- El `AGENTS.md` de la raíz aplica «only when you are working in this directory or its sub-directories» (literal), y la búsqueda recorre hacia arriba desde el directorio actual. No se documenta que un `AGENTS.md` anidado se cargue al tocar archivos de un subdirectorio distinto del actual.
- Alternativa documentada para carga bajo demanda: instruir en `AGENTS.md` al agente a leer archivos con su herramienta de lectura (ejemplo de la página `rules`: «CRITICAL: When you encounter a file reference (e.g., @rules/general.md), use your Read tool to load it on a need-to-know basis.»). Es una instrucción al modelo, no un mecanismo del agente.

## 3. Hooks que pueden denegar una acción

**Estado: parcialmente confirmado.** OpenCode no tiene un archivo de hooks declarativo: los hooks son **plugins en JavaScript/TypeScript** (`https://opencode.ai/docs/plugins/`, 2026-10-07).

Dónde van (literal):

- `.opencode/plugins/` - Project-level plugins
- `~/.config/opencode/plugins/` - Global plugins
- o paquetes npm en la clave `plugin` del `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["opencode-helicone-session", "opencode-wakatime", "@my-org/custom-plugin"]
}
```

Orden de carga: configuración global, configuración del proyecto, carpeta global de plugins, carpeta de plugins del proyecto; todos los hooks corren en secuencia.

Eventos y hooks listados en la documentación: `command.executed`, `file.edited`, `file.watcher.updated`, `installation.updated`, `lsp.client.diagnostics`, `lsp.updated`, `message.part.removed`, `message.part.updated`, `message.removed`, `message.updated`, `permission.asked`, `permission.replied`, `server.connected`, `session.created`, `session.compacted`, `session.deleted`, `session.diff`, `session.error`, `session.idle`, `session.status`, `session.updated`, `todo.updated`, `shell.env`, `tool.execute.after`, `tool.execute.before`, `tui.prompt.append`, `tui.command.execute`, `tui.toast.show`. (El hook `experimental.session.compacting` aparece solo en un ejemplo.)

Ejemplo oficial que **bloquea** (literal):

```javascript
export const EnvProtection = async ({ project, client, $, directory, worktree }) => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "read" && output.args.filePath.includes(".env")) {
        throw new Error("Do not read .env files")
      }
    },
  }
}
```

Formato de la entrada que recibe: no es JSON por la entrada estándar; es una función JavaScript con `(input, output)`. En `tool.execute.before`, del ejemplo oficial y del código: `input = { tool, sessionID, callID }` y `output = { args }` (los argumentos de la herramienta, modificables, p. ej. `output.args.command` para `bash`, `output.args.filePath` para `read`). Los nombres de herramienta que aparecen en la documentación son `bash` y `read`. **[código]** `packages/opencode/src/session/tools.ts`.

Formato de la respuesta que bloquea: **lanzar una excepción** (`throw new Error("...")`). No hay códigos de salida ni objeto `permission`. Fuente documental: el ejemplo anterior (documentado como «.env protection»).

Comportamiento si el hook falla: **no documentado**. **[código]** `plugin/index.ts`, función `trigger`: recorre los hooks y hace `yield* Effect.promise(async () => fn(input, output))` **sin captura de errores**; una excepción del hook se propaga y la llamada a la herramienta no llega a ejecutarse (en `tools.ts`, `item.execute` va después de `plugin.trigger("tool.execute.before", ...)` en la misma secuencia). Es decir, por código, un plugin que lanza o falla **bloquea** (cerrado). No hay opción tipo `failClosed` porque no hace falta; tampoco hay documentada una de tipo «abierto». Habría que probarlo con el agente real antes de depender de ello (no se ejecutó nada).

Cobertura de herramientas: **[código]** `tools.ts` dispara `tool.execute.before` para las herramientas del registro, para las herramientas del servidor MCP (bucle sobre `mcp.tools()`), para las de recursos MCP y para la herramienta de subagentes (`task`, también en `prompt.ts`). La documentación no lo afirma.

Otras opciones confirmadas: el evento `permission.asked` existe, pero la documentación no dice que un plugin pueda responder o denegar a través de él. **No se pudo confirmar.**

## 4. Comandos personalizados

**Estado: confirmado con fuente** (`https://opencode.ai/docs/commands/`, 2026-10-07).

- Ubicación: `.opencode/commands/` (proyecto), `~/.config/opencode/commands/` (global), o clave `command` en `opencode.json`. «The markdown file name becomes the command name.»

```md
---
description: Run tests with coverage
agent: build
model: anthropic/claude-3-5-sonnet-20241022
---

Run the full test suite with coverage report and show any failures.
Focus on the failing tests and suggest fixes.
```

```json
{
  "$schema": "https://opencode.ai/config.json",
  "command": {
    "test": {
      "template": "Run the full test suite with coverage report and show any failures.\nFocus on the failing tests and suggest fixes.",
      "description": "Run tests with coverage",
      "agent": "build",
      "model": "anthropic/claude-3-5-sonnet-20241022"
    }
  }
}
```

- Claves: `template` (obligatoria en JSON; en Markdown es el cuerpo), `description`, `agent`, `subtask` (booleano), `model`.
- Marcadores en el cuerpo: `$ARGUMENTS`, `$1`, `$2`, `$3`; salida de shell con `` !`comando` ``; archivos con `@ruta`.
- Un comando personalizado con el nombre de uno integrado lo sustituye.

## 5. Skills

**Estado: confirmado con fuente** (`https://opencode.ai/docs/skills/`, 2026-10-07).

Ubicaciones (literal): `.opencode/skills/<name>/SKILL.md`, `~/.config/opencode/skills/<name>/SKILL.md`, `.claude/skills/<name>/SKILL.md`, `~/.claude/skills/<name>/SKILL.md`, `.agents/skills/<name>/SKILL.md`, `~/.agents/skills/<name>/SKILL.md`. En rutas del proyecto sube desde el directorio actual hasta la raíz del árbol de trabajo de git.

Campos reconocidos: `name` (obligatorio), `description` (obligatorio), `license`, `compatibility`, `metadata` (mapa texto a texto). «Unknown frontmatter fields are ignored.» Reglas de `name`: 1-64 caracteres, regex `^[a-z0-9]+(-[a-z0-9]+)*$`, igual al nombre del directorio. `description`: 1-1024 caracteres.

```markdown
---
name: git-release
description: Create consistent releases and changelogs
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: github
---

## What I do

- Draft release notes from merged PRs
- Propose a version bump
- Provide a copy-pasteable `gh release create` command
```

Permisos de skills (clave `permission.skill` con `allow`, `deny`, `ask` y comodines). Se cargan bajo demanda con la herramienta nativa `skill({ name: "git-release" })`.

## 6. Registro de servidores MCP

**Estado: confirmado con fuente** (`https://opencode.ai/docs/mcp-servers/` y esquema `https://opencode.ai/config.json`, 2026-10-07).

Archivo: `opencode.json` / `opencode.jsonc` (proyecto) o `~/.config/opencode/opencode.json` (global), clave `mcp`. **No** se usa `mcpServers`.

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "my-local-mcp-server": {
      "type": "local",
      // Or ["bun", "x", "my-mcp-command"]
      "command": ["npx", "-y", "my-mcp-command"],
      "enabled": true,
      "environment": {
        "MY_ENV_VAR": "my_env_var_value",
      },
    },
  },
}
```

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "my-remote-mcp": {
      "type": "remote",
      "url": "https://my-mcp-server.com",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer MY_API_KEY"
      }
    }
  }
}
```

- Local: `type` (`"local"`, obligatorio), `command` (**arreglo**, obligatorio), `cwd`, `environment`, `enabled`, `timeout` (ms, por defecto 5000).
- Remoto: `type` (`"remote"`, obligatorio), `url` (obligatorio), `enabled`, `headers`, `oauth` (objeto o `false`), `timeout`.
- El esquema marca `additionalProperties: false` en ambos tipos: una clave desconocida es inválida.
- Interpolación: `mcp-servers.mdx` no la menciona. `config.mdx` documenta de forma general `{env:VARIABLE_NAME}` y `{file:path/to/file}` («Use `{env:VARIABLE_NAME}` to substitute environment variables») en valores del archivo de configuración; que aplique dentro de `mcp.*.headers` **no se pudo confirmar** con un ejemplo oficial.

## 7. Permisos y modos

**Estado: confirmado con fuente** (`https://opencode.ai/docs/permissions/` y `https://opencode.ai/docs/agents/`, 2026-10-07).

Acciones: `"allow"`, `"ask"`, `"deny"`. Clave `permission` en `opencode.json` (global con `"*"` o por herramienta; objeto con patrones; «the last matching rule winning»). Comodines: `*` y `?`.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "permission": {
    "bash": {
      "*": "ask",
      "git *": "allow",
      "npm *": "allow",
      "rm *": "deny",
      "grep *": "allow"
    },
    "edit": {
      "*": "deny",
      "packages/web/src/content/docs/*.mdx": "allow"
    }
  }
}
```

Claves de permiso documentadas: `read`, `edit` (cubre `edit`, `write`, `patch`), `glob`, `grep`, `bash`, `task`, `skill`, `lsp`, `question`, `webfetch`, `websearch`, `external_directory`, `doom_loop` (el esquema añade `list` y `todowrite`). Valores por defecto: casi todo `allow`; `doom_loop` y `external_directory` en `ask`; `read` permitido salvo `*.env` y `*.env.*`.

Modo solo lectura / plan: el agente primario **Plan** viene con `edit` y `bash` en `ask` («By default, all of the following are set to `ask`»); el subagente **explore** es «read-only». Un agente propio de solo lectura:

```markdown
---
description: Code review without edits
mode: subagent
permission:
  edit: deny
  bash: ask
  webfetch: deny
---

Only analyze code and suggest changes.
```

Nota: Plan es `ask`, no `deny`; para solo lectura estricta hay que fijar `edit: deny` y `bash: deny` en el agente (como en el ejemplo `plan` de la página `agents`).

Lista de comandos permitidos: la forma es el objeto de `bash` con patrón por comando (ver arriba). Requiere el comodín final para comandos con argumentos (`"git status *"`).

## 8. Ejecución no interactiva para CI

**Estado: confirmado con fuente** (`https://opencode.ai/docs/cli/`, 2026-10-07).

```bash
opencode run [message..]
```

Banderas confirmadas de `run`: `--command`, `--continue`/`-c`, `--session`/`-s`, `--fork`, `--share`, `--model`/`-m` (`provider/model`), `--agent`, `--file`/`-f`, `--format` (`default` o `json`, «raw JSON events»), `--title`, `--attach`, `--password`/`-p`, `--username`/`-u`, `--dir`, `--port`, `--variant`, `--thinking`, `--auto` («Auto-approve permissions that are not explicitly denied»).

```bash
opencode run --auto "Refactor this module"
```

(de la página `permissions`). Las reglas `deny` siguen vigentes con `--auto`. Variable `OPENCODE_PERMISSION` («Inlined json permissions config») y `OPENCODE_CONFIG_CONTENT` («Inline json config content») permiten inyectar configuración en CI. **No se pudo confirmar:** qué ocurre en `opencode run` sin `--auto` ante un permiso `ask` (se buscó en `cli.mdx` y `permissions.mdx`; no se documenta). Códigos de salida: no documentados.

## 9. Subagentes

**Estado: confirmado con fuente** (`https://opencode.ai/docs/agents/`, 2026-10-07).

Ubicación: `.opencode/agents/*.md` (proyecto), `~/.config/opencode/agents/` (global) o clave `agent` en `opencode.json`. «The markdown file name becomes the agent name.»

```markdown
---
description: Reviews code for quality and best practices
mode: subagent
model: anthropic/claude-sonnet-4-20250514
temperature: 0.1
permission:
  edit: deny
  bash: deny
---

You are in code review mode. Focus on:
```

- Claves: `description` (obligatoria), `mode` (`primary`, `subagent`, `all` según el esquema), `model`, `temperature`, `top_p`, `prompt`, `permission`, `steps`, `disable`, `hidden`, `color`, `options`.
- Integrados: primarios `build` y `plan`; subagentes `general`, `explore`, `scout`. Se invocan con `@general ...` o automáticamente.
- Paralelismo: de `general`, «Use this to run multiple units of work in parallel» (literal). Un límite de concurrencia: no se pudo confirmar. El esquema tiene `subagent_depth` en la raíz (profundidad de subagentes; semántica no leída).

---

## Lo que un adaptador puede generar con seguridad hoy

Solo lo confirmado arriba:

1. `AGENTS.md` en la raíz (y global opcional) con Markdown plano; para añadir otros archivos, `instructions` en `opencode.json` (globos, URLs).
2. Skills en `.opencode/skills/<name>/SKILL.md` o `.agents/skills/<name>/SKILL.md`, con `name` (igual al directorio, regex `^[a-z0-9]+(-[a-z0-9]+)*$`, 1-64) y `description` (1-1024).
3. Comandos en `.opencode/commands/<nombre>.md` con frontmatter `description`, `agent`, `model`, `subtask` y marcadores `$ARGUMENTS`, `$1`.
4. Subagentes en `.opencode/agents/<nombre>.md` con `description`, `mode: subagent`, `permission`.
5. Servidores MCP en `opencode.json`, clave `mcp`, con `type: local` + `command` (arreglo) o `type: remote` + `url`; sin claves fuera del esquema.
6. Permisos en `opencode.json`, clave `permission`, con `allow`/`ask`/`deny` y patrones `bash` (el último que coincide gana: el comodín `"*"` primero).
7. Ejecución en CI con `opencode run --auto "..."` (las reglas `deny` se mantienen), `--format json` para eventos.
8. Plugin de bloqueo `tool.execute.before` que lanza una excepción (patrón de la documentación) **si se acepta** que su efecto de «cerrado ante fallo» solo está respaldado por el código, no por la documentación.

## Lo que no debe generarse todavía

- Reglas por ruta/patrón (no existe mecanismo documentado).
- Cualquier afirmación de «falla abierto/cerrado» de los plugins como contrato (solo observado en el código de la rama `dev`; probar con el agente real antes).
- Hooks basados en `permission.asked` para denegar (no documentado).
- Interpolación `{env:...}` dentro de `mcp.*` (documentada solo de forma general en `config`, sin ejemplo en MCP).
- Dependencia de códigos de salida de `opencode run` o de su comportamiento ante `ask` sin `--auto`.
- Que `@archivo` dentro de `AGENTS.md` se expanda solo (la documentación dice que no).
- Un tope de tamaño de instrucciones o de concurrencia de subagentes.
