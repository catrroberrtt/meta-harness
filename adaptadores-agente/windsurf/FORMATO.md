# Windsurf (Devin Desktop): formato exacto de configuración (contraste con la fuente)

<!-- tipo: estandar · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: documentación oficial (URLs en el documento) -->

## Fuentes y método

Leídas el 2026-10-07 en su versión Markdown oficial (cada página publica su fuente con sufijo `.md`). Solo lectura: no se ejecutó ni instaló el agente.

**Destino de la redirección.** `https://docs.windsurf.com/windsurf/cascade/<pagina>` responde `307 Temporary Redirect` a `https://docs.devin.ai/desktop/cascade/<pagina>`; el producto se documenta como **Devin Desktop** (el agente histórico se llama **Cascade**). El índice de `https://docs.windsurf.com/llms.txt` sigue listando las rutas antiguas; el índice del destino es `https://docs.devin.ai/llms.txt` y `https://docs.devin.ai/_llms/en/desktop.md` (102 páginas). Las páginas se leyeron en `https://docs.devin.ai/desktop/...md`.

Páginas de Devin Desktop: `cascade/hooks`, `cascade/memories`, `cascade/agents-md`, `cascade/workflows`, `cascade/skills`, `cascade/mcp`, `cascade/modes`, `terminal`, `devin-local`, `context-awareness/devin-ignore`.

Páginas del agente de línea de comandos (Devin CLI), que **es el agente por defecto del IDE** (ver «Hallazgo estructural»): `https://docs.devin.ai/cli/extensibility/hooks/overview.md`, `.../hooks/lifecycle-hooks.md`, `.../rules.md`, `.../skills/overview.md`, `.../skills/creating-skills.md`, `.../mcp/configuration.md`, `https://docs.devin.ai/cli/reference/permissions.md`, `.../reference/commands.md`, `https://docs.devin.ai/cli/subagents.md`, `https://docs.devin.ai/cli/sandbox.md`.

Limitación: la documentación no publica fecha de revisión por página ni esquema JSON; el esquema de `hooks.json` y de `config.json` no se localizó (se buscó en el índice `llms.txt`; solo hay `analytics-v2-openapi.yaml`, que no trata de hooks). Los nombres exactos vienen de los ejemplos de las páginas.

### Hallazgo estructural: dos agentes con formatos distintos

> «New tabs start with Devin Local when you haven't chosen a preferred agent … New conversations never start on Cascade, but your existing Cascade conversations remain available» (`https://docs.devin.ai/desktop/devin-local.md`, 2026-10-07).

- **Cascade** (agente histórico, «legacy»): hooks `snake_case` en `hooks.json`, reglas con `trigger`, workflows, memorias, listas de comandos.
- **Devin Local** (por defecto): arnés compartido con Devin CLI; hooks `PascalCase` en `.devin/hooks.v1.json`, permisos `allow/ask/deny`, skills, subagentes, sandbox. «Workflows are not available with the Devin Local agent» y «does not persist memories».

Un adaptador debe decidir a cuál apunta; los archivos de hooks de uno **no** los lee el otro (la página de hooks de Cascade lo dice: «The Devin Local agent has its own lifecycle hooks … with a different configuration format»).

---

## 1. Archivo de instrucciones del proyecto

**Estado: confirmado con fuente** (`https://docs.devin.ai/desktop/cascade/agents-md.md` y `https://docs.devin.ai/cli/extensibility/rules.md`, 2026-10-07).

- Nombre: `AGENTS.md` o `agents.md` («Case insensitive»). **Sí lee `AGENTS.md`.**
- Cascade: raíz = regla «always-on»; subdirectorio = regla `glob` con patrón autogenerado `<directorio>/**`. «All `AGENTS.md` files within your workspace and its subdirectories are discovered»; en repositorios git también busca en directorios padre hasta la raíz git. Sin frontmatter.
- Devin Local / CLI: lee `AGENTS.md`, `AGENTS.local.md` (personal, para `.gitignore`), `AGENT.md`, `.windsurfrules` y `CLAUDE.md`, todos tratados como «always-on». La raíz se carga al inicio; los de subdirectorios «are discovered lazily when the agent accesses files in that directory». Global: `~/.config/devin/AGENTS.md` (`%APPDATA%\devin\AGENTS.md` en Windows); también lee `~/.claude/CLAUDE.md`.
- Importaciones de otros formatos (`.cursor/rules/*.md|*.mdc`, `.windsurf/rules`, `.claude/`) mediante la clave `read_config_from`:

```json
{
  "read_config_from": {
    "agents_standard": true,
    "cursor": true,
    "windsurf": true,
    "claude": true
  }
}
```

- Límite de tamaño de `AGENTS.md`: **no se pudo confirmar** (se buscó en `agents-md.md` y `rules.md`). Los límites que sí existen son de reglas con frontmatter (sección 2).
- `@archivo` dentro de `AGENTS.md`: **no se pudo confirmar** (no se menciona en ninguna de las dos páginas).

## 2. Reglas por ruta o patrón

**Estado: confirmado con fuente** para Cascade (`https://docs.devin.ai/desktop/cascade/memories.md`, 2026-10-07); en Devin Local, confirmado que reutiliza el mismo frontmatter (`.../cli/extensibility/rules.md`).

Ubicaciones (literal de la tabla): global `~/.codeium/windsurf/memories/global_rules.md` («Always on. Limited to 6,000 characters»); espacio de trabajo `.devin/rules/*.md` (preferida) o `.windsurf/rules/*.md` («Limited to 12,000 characters per file»; `.windsurfrules` sigue leyéndose); sistema: `/etc/devin/rules/*.md`, `/Library/Application Support/Devin/rules/*.md`, `C:\ProgramData\Devin\rules\*.md` (con alternativa heredada `Windsurf`). Devin CLI añade `~/.devin/rules/*.md` y `.devin/global_rules.md`.

Clave de cabecera: `trigger`. Valores documentados en Cascade: `always_on`, `model_decision` (usa `description`), `glob` (usa `globs`), `manual` (se activa con `@nombre`). Devin CLI documenta además `agent`. Ejemplo literal:

```markdown
---
trigger: glob
globs: **/*.test.ts
---

All test files must use `describe`/`it` blocks and mock external API calls.
```

- Ejemplo de regla importada de Windsurf en la documentación de Devin CLI: `description: "API design rules"` + `trigger: always_on`.
- `globs`: separador múltiple y exclusiones **no se pudieron confirmar**; el único ejemplo de la fuente con varios patrones no existe (ejemplos con un patrón: `*.js`, `src/**/*.ts`).
- Los directorios `.devin/rules` o `.windsurf/rules` se leen «in any sub-directory of your workspace» y en padres hasta la raíz git.
- Reglas con `trigger: always_on` entran completas en el prompt de sistema en cada mensaje (coste de contexto).

## 3. Hooks que pueden denegar una acción

**Estado: confirmado con fuente, en dos implementaciones distintas.** Los hooks no cargan ni corren con el espacio de trabajo en «Restricted Mode».

### 3A. Cascade (`https://docs.devin.ai/desktop/cascade/hooks.md`, 2026-10-07)

Archivos (se **fusionan**; orden: nube → sistema → usuario → espacio de trabajo):

- Sistema: macOS `/Library/Application Support/Devin/hooks.json`; Linux/WSL `/etc/devin/hooks.json`; Windows `C:\ProgramData\Devin\hooks.json` (alternativa heredada `Windsurf`).
- Usuario: `~/.codeium/windsurf/hooks.json` (IDE); `~/.codeium/hooks.json` (JetBrains).
- Espacio de trabajo: `.devin/hooks.json` (el heredado `.windsurf/hooks.json` solo si falta el anterior o no define hooks).

Estructura literal:

```json
{
  "hooks": {
    "pre_read_code": [
      {
        "command": "python3 /path/to/your/script.py",
        "powershell": "python3 C:\\path\\to\\your\\script.py",
        "show_output": true
      }
    ],
    "post_write_code": [
      {
        "command": "python3 /path/to/another/script.py",
        "show_output": true
      }
    ]
  }
}
```

Parámetros: `command` (por `bash -c`), `powershell`, `show_output`, `working_directory`. Doce eventos; **pueden bloquear solo los previos**: `pre_read_code`, `pre_write_code`, `pre_run_command`, `pre_mcp_tool_use`, `pre_user_prompt`. Los demás (`post_read_code`, `post_write_code`, `post_run_command`, `post_mcp_tool_use`, `post_cascade_response`, `post_cascade_response_with_transcript`, `post_setup_worktree`) son informativos.

Entrada: JSON por la entrada estándar con `agent_action_name`, `trajectory_id`, `execution_id`, `timestamp`, `model_name`, `tool_info`. Ejemplos literales de `tool_info`:

```json
{
  "agent_action_name": "pre_run_command",
  "tool_info": {
    "command_line": "npm install package-name",
    "cwd": "/Users/yourname/project"
  }
}
```

```json
{
  "agent_action_name": "pre_read_code",
  "tool_info": {
    "file_path": "/Users/yourname/project/file.py"
  }
}
```

(`pre_write_code` añade `tool_info.edits[].old_string/new_string`; `pre_mcp_tool_use` trae `mcp_server_name`, `mcp_tool_name`, `mcp_tool_arguments`; `pre_user_prompt` trae `user_prompt`. Nota literal: `file_path` «may be a directory path when Cascade reads a directory recursively».)

Respuesta que bloquea: **código de salida `2`**; el agente ve lo escrito en `stderr`. No hay respuesta JSON de decisión. Tabla literal de códigos: `0` éxito (la acción sigue); `2` error bloqueante (en los previos bloquea); «Any other» error (**la acción sigue**).

**Si el hook falla: falla abierto.** Un guion que se cae, que no es JSON válido y sale con 1, o que expira, no bloquea. El ejemplo oficial lo hace explícito: ante `json.JSONDecodeError` usa `sys.exit(1)` (no bloquea). La documentación recomienda «Fail safely … consider whether it should block the action». Comportamiento ante *timeout*: **no se pudo confirmar** (no hay parámetro `timeout` en la tabla de opciones).

Ejemplo oficial que bloquea (extracto literal de «Restricting File Access»):

```python
if not file_path.startswith(ALLOWED_PREFIX):
    print(f"Access denied: Cascade is only allowed to read files under {ALLOWED_PREFIX}", file=sys.stderr)
    sys.exit(2)  # Exit code 2 blocks the action
```

### 3B. Devin Local / Devin CLI (`https://docs.devin.ai/cli/extensibility/hooks/overview.md` y `.../lifecycle-hooks.md`, 2026-10-07)

Archivo: `.devin/hooks.v1.json` («the hooks object is the **entire file** (no wrapper key needed)»); también la clave `"hooks"` en `.devin/config.json`, `.devin/config.local.json`, `~/.config/devin/config.json` (`%APPDATA%\devin\config.json` en Windows) y, si `read_config_from.claude` está activo (por defecto), `.claude/settings.json`, `.claude/settings.local.json`, `~/.claude.json`, `~/.claude/settings.json`. Se buscan en el directorio de trabajo y sus ancestros hasta la raíz del repositorio. Verificación: comando `/hooks`. Migración desde Cascade: `devin migrate hooks` (convierte `.windsurf/hooks.json` en `.devin/hooks.v1.json`).

Eventos: `PreToolUse`, `PostToolUse`, `PermissionRequest`, `UserPromptSubmit`, `Stop`, `PostCompaction`, `SessionStart`, `SessionEnd`. Tipos de hook: `command` y `prompt` (evalúa un mensaje con un modelo). Ejemplo literal:

```json
{
  "PreToolUse": [
    {
      "matcher": "exec",
      "hooks": [
        {
          "type": "command",
          "command": "./scripts/check-command.sh"
        }
      ]
    }
  ]
}
```

Entrada (JSON por stdin; ejemplo literal): `{"hook_event_name":"PreToolUse","tool_name":"exec","tool_input":{"command":"rm -rf /"},"session_id":"3f8d1c2a-...","prompt_id":"b71e9d40-..."}`. Variable de entorno `DEVIN_PROJECT_DIR`. El `matcher` es una **expresión regular** sobre `tool_name` (vacío = todas); no es un glob de permisos (`mcp__github__.*`, no `mcp__github__*`).

Respuesta que bloquea: salida `2` **o** JSON por stdout (literal):

```json
{
  "decision": "block",
  "reason": "Destructive command blocked by policy"
}
```

Otras formas: `hookSpecificOutput.updatedInput` (reescribe argumentos en `PreToolUse`) y `additionalContext`. Códigos: `0` continúa; `2` bloquea; «Other: Error — logged but doesn't block» (**falla abierto**). Timeout: campo `timeout` en segundos; qué ocurre al expirar: **no se pudo confirmar**.

Nombres de herramienta que se pueden filtrar (literal de la tabla): archivos `read`, `write`, `edit`, `apply_patch`, `notebook_read`, `notebook_edit`; búsqueda `grep`, `glob`; shell `exec`, `get_output`, `write_to_process`, `kill_shell`; web `webfetch`; MCP `mcp__<servidor>__<herramienta>`; subagentes `run_subagent`, `read_subagent`. La documentación advierte que los nombres «can vary by CLI mode, model, and enabled integrations»: registrar la carga útil con un hook de prueba antes de fijar filtros.

Cobertura: para Cascade no está confirmado que todo camino de edición (otros procesos, extensiones) pase por `pre_write_code`.

## 4. Comandos personalizados

**Estado: confirmado con fuente** (`https://docs.devin.ai/desktop/cascade/workflows.md`, 2026-10-07), solo para Cascade.

- «Workflows» = comandos de barra: `/<nombre-del-archivo>`; **solo manuales**. Ubicaciones: `.devin/workflows/*.md` (preferida) o `.windsurf/workflows/*.md`; global `~/.codeium/windsurf/global_workflows/*.md`; sistema `/etc/devin/workflows/`. Tope: «Workflow files are limited to 12000 characters each». Un workflow puede llamar a otro («Call /workflow-2»).
- Formato del archivo («a title, description, and a series of steps»): claves exactas de cabecera **no se pudieron confirmar** (la página no muestra un ejemplo de frontmatter).
- Devin Local **no** soporta workflows: se migran a skills (`devin migrate workflows`, o asistente «Devin: Open Cascade Migration Wizard»). Un skill se invoca con `/nombre` (sección 5).

## 5. Skills (`SKILL.md`)

**Estado: confirmado con fuente** (`https://docs.devin.ai/desktop/cascade/skills.md`; Devin Local: `https://docs.devin.ai/cli/extensibility/skills/overview.md` y `creating-skills.md`, 2026-10-07).

- Cascade: `.devin/skills/<nombre>/SKILL.md` (o heredado `.windsurf/skills/`); global `~/.codeium/windsurf/skills/` o `~/.config/devin/skills/` (compartido con la CLI); sistema `/etc/devin/skills/`. También descubre `.agents/skills/`, `~/.agents/skills/` y, con lectura de Claude activada, `.claude/skills/`, `~/.claude/skills/`. Carga progresiva (solo `name` y `description`); invocación con `@nombre`. Campos obligatorios: `name`, `description`; el nombre: minúsculas, números y guiones.

```markdown
---
name: deploy-to-production
description: Guides the deployment process to production with safety checks
---
```

- Devin Local añade al frontmatter (tabla literal «All Frontmatter Fields»): `name` (por defecto el directorio), `description`, `argument-hint`, `model`, `subagent` (booleano), `agent`, `allowed-tools` (lista; **autoaprueba**, no restringe), `permissions` (`allow`/`deny`/`ask`), `triggers` (`user`, `model`). Ejemplo literal:

```markdown
---
name: review
description: Review code changes before committing
allowed-tools:
  - read
  - grep
  - glob
  - exec
---
```

- Límites de longitud de `name` y `description` en Devin: **no se pudieron confirmar** (se buscaron en ambas páginas de skills de la CLI).

## 6. Registro de servidores MCP

**Estado: confirmado con fuente** (`https://docs.devin.ai/desktop/cascade/mcp.md`, `https://docs.devin.ai/cli/extensibility/mcp/configuration.md`, 2026-10-07).

- Cascade: `~/.config/devin/mcp_config.json` (o `$XDG_CONFIG_HOME/devin/mcp_config.json`; Windows `%APPDATA%\devin\mcp_config.json`), clave `mcpServers`. Campos: `command`, `args`, `env` (locales); `serverUrl` o `url`, `headers` (remotos); `disabledTools` (arreglo). Interpolación `${env:VAR_NAME}` en `command`, `args`, `env`, `serverUrl`, `url`, `headers` (variable no definida = cadena vacía; también existe `${file:...}`). Ruta antigua de Windsurf: **no se pudo confirmar** (la página actual solo cita la ruta de `devin`).
- Devin Local: archivos dedicados `.devin/mcp_config.json` (proyecto, versionado), `.devin/mcp_config.local.json` (local, ignorado), `~/.config/devin/mcp_config.json` (usuario); clave `mcpServers`. Campos locales: `command` (obligatorio), `args`, `env`, `disabled`. Remotos: `url` (obligatorio), `transport` (`"http"` por defecto o `"sse"`), `headers`, `oauthClientId`, `oauthClientSecret`, `oauthResource`, `disabled`. Ejemplo literal:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "@company/mcp-server"],
      "env": {
        "API_KEY": "your-key"
      }
    }
  }
}
```

- Permisos MCP en Devin Local: por defecto pide aprobación antes de cualquier herramienta MCP; reglas `mcp__servidor__herramienta`, `mcp__servidor__*`, `mcp__*`.
- Aviso de la fuente: los servidores antes de v3000.3 vivían en la clave `mcpServers` de `config.json` y se migran solos al arrancar.

## 7. Permisos, modos, sandbox y listas de comandos

**Estado: confirmado con fuente**, distinto por agente.

### Cascade (`https://docs.devin.ai/desktop/terminal.md`, `.../cascade/modes.md`, 2026-10-07)

- Niveles de autoejecución: `Disabled`, `Allowlist Only`, `Auto` (solo modelos premium), `Turbo` (todo salvo la lista de denegados).
- Lista permitida: entradas que acaban en ` *` coinciden por prefijo (ejemplo literal: `git *`); lista denegada (`rm *`). **Una entrada denegada no bloquea: «will always ask for permission»**; la denegada prevalece sobre la permitida. Listas de equipo en el portal de administración.
- Modos: `Code`, `Plan`, `Ask` (solo lectura: «search tools only»; «cannot make any changes»).
- Archivo `.devinignore` (sintaxis `.gitignore`): «excluded from indexing and cannot be viewed, edited, or created by Devin»; heredados `.windsurfignore` y `.codeiumignore`; global `~/.codeium/.codeiumignore`. Los archivos de `.gitignore` tampoco los edita el agente. Fuente: `https://docs.devin.ai/desktop/context-awareness/devin-ignore.md`.

### Devin Local (`https://docs.devin.ai/cli/reference/permissions.md`, `https://docs.devin.ai/cli/sandbox.md`, 2026-10-07)

Reglas en la clave `permissions` de `.devin/config.json`, `.devin/config.local.json` o `~/.config/devin/config.json`. Literal:

```json
{
  "permissions": {
    "allow": [
      "Read(src/**)",
      "Exec(npm run)"
    ],
    "deny": [
      "Exec(rm)"
    ]
  }
}
```

Sintaxis: `Read(glob)`, `Write(glob)`, `Exec(prefijo)`, `Fetch(patrón)`, herramienta completa (`edit`, `exec`, `read`, `grep`, `glob`) y `mcp__...`. Orden: denegar > preguntar > permitir > por defecto (preguntar); «A deny rule always wins». Precedencia entre orígenes: organización > sesión > local del proyecto > proyecto > usuario; las reglas deny/ask de la organización no se pueden anular. Modos: `normal` (por defecto), `accept-edits`, `smart` (despliegue gradual), `dangerous`/`bypass`, `autonomous` (requiere `--sandbox`); Plan y Ask aparte. Sandbox (`--sandbox`, vista previa de investigación): macOS seatbelt; Linux `bubblewrap` + `socat`; **Windows no soportado** (la sesión falla); si no se puede aplicar el sandbox «the CLI will refuse to start rather than running unsandboxed» (cierra ante fallo).

## 8. Ejecución no interactiva para CI

**Estado: confirmado con fuente solo para la CLI** (`https://docs.devin.ai/cli/reference/commands.md`, 2026-10-07). **El IDE (Cascade) no tiene modo no interactivo documentado.** Se buscó en las páginas de `desktop/` y en `llms.txt`.

- Producto distinto del IDE: Devin CLI, ejecutable `devin`. Banderas globales literales: `--print [PROMPT]` / `-p` («Print response and exit (non-interactive mode)»), `--prompt-file <FILE>`, `--permission-mode <MODE>` (`DEVIN_PERMISSION_MODE`), `--sandbox` (`DEVIN_SANDBOX`), `--model`, `--continue`/`-c`, `--resume`/`-r`, `--config <PATH>`, `--export [PATH]`, `--respect-workspace-trust [true|false]`.

```bash
devin -p "list all TODO comments"
```

- Advertencia literal: «Non-interactive `--print` mode cannot show the workspace trust prompt, so it fails in an untrusted directory. Pass `--respect-workspace-trust false` to skip the check in scripts and CI.»
- **No se pudo confirmar:** códigos de salida de `devin -p`; si los hooks (`.devin/hooks.v1.json`) se ejecutan en `-p`; qué pasa ante una petición de permiso sin responder en `-p`. Hay un `devin doctor --json`, que no es ejecución de tareas.

## 9. Subagentes

**Estado: confirmado con fuente solo para Devin Local** (`https://docs.devin.ai/cli/subagents.md`, `https://docs.devin.ai/desktop/devin-local.md`, 2026-10-07). Cascade: no hay subagentes documentados («plugins and subagents have no Cascade equivalent at all»); solo conversaciones en paralelo.

- Definición: archivos Markdown bajo `agents/`: `.devin/agents/<nombre>.md` o `.devin/agents/<nombre>/AGENT.md`; también `.agents/agents/`; global `~/.config/devin/agents/`. Frontmatter (tabla literal): `name`, `description`, `model`, `allowed-tools` (alias `tools`; restricción real), `max-nesting`. Ejemplo literal:

```markdown
---
name: reviewer
description: Reviews code changes for correctness and style
model: sonnet
allowed-tools:
  - read
  - grep
  - glob
  - exec
---
```

- Perfiles integrados `subagent_explore` y `subagent_general`. Primer plano y segundo plano (en segundo plano: «Unapproved tools are automatically denied»). Los subagentes no pueden crear subagentes salvo que el perfil fije `max-nesting`. Se habilitan con el conmutador «Subagents (Preview)» en la configuración. Límite de concurrencia: **no se pudo confirmar**.

---

## Lo que un adaptador puede generar con seguridad hoy

Solo lo confirmado arriba. Decidir primero el agente de destino.

1. `AGENTS.md` en la raíz (Markdown plano, sin frontmatter): lo leen Cascade y Devin Local.
2. Reglas por patrón (Cascade y Devin Local): `.devin/rules/<nombre>.md` con `trigger: glob` + `globs:` o `trigger: always_on`; cada archivo ≤ 12 000 caracteres.
3. Skills (ambos): `.devin/skills/<nombre>/SKILL.md` con `name` y `description`; `allowed-tools`/`permissions`/`triggers` solo para Devin Local.
4. MCP para Devin Local: `.devin/mcp_config.json` con `mcpServers` (`command`/`args`/`env` o `url`/`headers`); secretos con `${env:VAR}`; nunca valores en el archivo versionado (usar `.devin/mcp_config.local.json`).
5. Permisos de Devin Local: `permissions.deny` con `Read(...)`, `Write(...)`, `Exec(...)` en `.devin/config.json`.
6. `.devinignore` (sintaxis `.gitignore`) para excluir archivos sensibles de la vista del agente.
7. Subagentes de Devin Local: `.devin/agents/<nombre>.md` con `description`, `allowed-tools`.
8. Hook de bloqueo (ver diseño abajo), con prueba real previa.
9. Ejecución en CI con `devin -p "..."` (producto distinto del IDE), con `--respect-workspace-trust false` solo si el directorio es de confianza para el trabajo.

## Lo que no debe generarse todavía

- Comandos personalizados para Devin Local como archivos propios: no existen fuera de skills; los workflows son solo de Cascade.
- Cualquier dependencia de que un hook falle cerrado, de su comportamiento al expirar o de códigos distintos de `2`.
- Archivos de hooks de un agente esperando que los lea el otro (`hooks.json` de Cascade frente a `hooks.v1.json` de Devin Local).
- Claves de cabecera de workflows de Cascade (no confirmadas).
- Límites de longitud de `name`/`description` de skills en Devin; límite de tamaño de `AGENTS.md`; concurrencia de subagentes.
- Ejecución no interactiva del IDE o supuestos sobre hooks/permisos/códigos de salida en `devin -p`.
- Listas de denegados de Cascade como control duro: solo exigen aprobación.
- Ruta antigua de MCP de Windsurf.

### Diseño del hook de bloqueo de datos

Objetivo: impedir que el agente lea, escriba o vuelque datos sensibles (archivos de entorno, claves, volcados de base de datos) antes de que ocurra. Es un diseño propio, no copiado de la fuente; solo usa campos confirmados arriba.

**Capa 1, declarativa (no depende de que un guion funcione).** En Devin Local, `permissions.deny` con `Read(**/.env*)`, `Read(**/*.pem)`, `Write(**/.env*)`, `Exec(mysqldump)` y similares, más `.devinignore`. En Cascade solo existe `.devinignore` y la lista de denegados (que exige aprobación, no bloquea).

**Capa 2, hook.**

- Devin Local: `.devin/hooks.v1.json`, evento `PreToolUse`, `matcher` regex `^(exec|read|write|edit|apply_patch|grep|glob|mcp__.*)$`. El guion lee el JSON de stdin; de `tool_input` extrae rutas y `command`; compara con una lista de patrones; si coincide imprime `{"decision":"block","reason":"..."}` y sale con `2`.
- Cascade: `hooks.json`, eventos `pre_read_code`, `pre_write_code`, `pre_run_command`, `pre_mcp_tool_use` (y `pre_user_prompt` si se quiere filtrar prompts). El guion usa `tool_info.file_path` o `tool_info.command_line`; bloquea con `sys.exit(2)` y un motivo en `stderr`.
- **Regla de robustez obligatoria, porque ambas implementaciones fallan abiertas:** envolver todo el guion en un `try/except` general que ante cualquier error (JSON ilegible, campo ausente, excepción) termine con `exit 2`, no con `exit 1`. Un guion que sale con `1` deja pasar la acción. Con `PreToolUse` conviene tratar «herramienta desconocida con ruta o comando no analizable» como bloqueo.
- Usar rutas absolutas al guion (recomendación de la fuente) y mantenerlo rápido (la fuente apunta a menos de 100 ms).
- Pruebas antes de publicar: registrar la carga útil real con un hook de bitácora (`PostToolUse` con `matcher` vacío, o `post_*` en Cascade) y comprobar con cada herramienta (`read`, `exec`, MCP, `apply_patch`) que el bloqueo ocurre. Lo no verificado: cobertura de otras vías de edición en Cascade y comportamiento al expirar.
- Complemento: sandbox de Devin Local (`--sandbox`) para limitar el sistema de archivos y la red de los comandos; no cubre las herramientas `edit`/`write` («operate outside the sandbox»).
