# Gemini CLI: formato exacto de configuración (contraste con la fuente)

<!-- tipo: estandar · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: documentación oficial (URLs en el documento) -->

## Fuentes y método

Leídas el 2026-10-07. Solo lectura: no se ejecutó ni se instaló el agente, no se usaron credenciales.

- Documentación publicada: `https://geminicli.com/docs/` (se consultaron `hooks/` y `cli/gemini-md/`; la herramienta de lectura devuelve resúmenes, por eso el texto literal se tomó de la fuente cruda de abajo).
- **Fuente cruda de la documentación** (los Markdown de los que se genera el sitio): repositorio oficial `google-gemini/gemini-cli`, rama `main`, commit `44d764ee579610bf73c43107f5e0422cd92588b9` en la fecha de lectura, ruta `docs/<página>.md`, vía `https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/<página>.md`. Páginas leídas: `hooks/reference`, `hooks/index`, `hooks/writing-hooks`, `cli/gemini-md`, `cli/custom-commands`, `cli/skills`, `cli/creating-skills`, `cli/headless`, `cli/cli-reference`, `cli/sandbox`, `cli/plan-mode`, `cli/trusted-folders`, `core/subagents`, `tools/mcp-server` (solo búsqueda de claves), `reference/policy-engine`, `reference/configuration`, `reference/tools`.
- No se leyó un esquema JSON de `settings.json`; los nombres de claves salen de `reference/configuration.md`, la referencia oficial. No se leyó código fuente: todo lo de abajo es **documentación**.

Limitación: `main` es la documentación en desarrollo; puede describir comportamiento posterior a la versión instalada. Los ejemplos están copiados literalmente de la fuente; solo se quitó texto circundante.

---

## 1. Archivo de instrucciones del proyecto

**Estado: confirmado con fuente** (`https://geminicli.com/docs/cli/gemini-md/`, fuente `docs/cli/gemini-md.md`, 2026-10-07).

- Nombre por defecto: `GEMINI.md`. Global: `~/.gemini/GEMINI.md`.
- Jerarquía (literal): «1. **Global context file:** `~/.gemini/GEMINI.md`. 2. **Environment and workspace context files:** The CLI searches for `GEMINI.md` files in your configured workspace directories and their parent directories. 3. **Just-in-time (JIT) context files:** When a tool accesses a file or directory, the CLI automatically scans for `GEMINI.md` files in that directory and its ancestors up to a trusted root.» Y: «concatenates the contents of all found files».
- **`AGENTS.md`**: no es nativo. Se lee solo si se configura (literal):

```json
{
  "context": {
    "fileName": ["AGENTS.md", "CONTEXT.md", "GEMINI.md"]
  }
}
```

`context.fileName` es «string | string[]», sin valor por defecto (`undefined`) en `reference/configuration.md`. Va en `.gemini/settings.json` (proyecto) o `~/.gemini/settings.json`; en una carpeta no confiable el de proyecto se ignora (§3).
- Importaciones (literal): `@./components/instructions.md`, `@../shared/style-guide.md` (rutas relativas o absolutas); detalle en `reference/memport.md` (no leída).
- Comandos: `/memory show`, `/memory reload`.
- Límite de tamaño: **no se pudo confirmar** (se buscó «size», «limit», «bytes» en `gemini-md.md`; no aparece).
- Ejemplo mínimo (literal):

```markdown
# Project: My TypeScript Library

## General Instructions

- When you generate new TypeScript code, follow the existing coding style.
- Ensure all new functions and classes have JSDoc comments.
```

## 2. Reglas por ruta o patrón

**Estado: no se pudo confirmar** que exista activación por glob.

Se intentó: lectura de `gemini-md.md`, `policy-engine.md` y `configuration.md`, buscando `globs`, `paths`, `applyTo`. Lo que existe, confirmado: el contexto «just-in-time» carga el `GEMINI.md` del directorio al que una herramienta accede y de sus ancestros hasta una raíz de confianza. Es activación por directorio tocado, sin patrones. Las reglas de políticas (§7) filtran herramientas y argumentos, no contexto.

## 3. Hooks que pueden denegar una acción

**Estado: confirmado con fuente** (`https://geminicli.com/docs/hooks/`; fuente cruda `docs/hooks/reference.md`, `docs/hooks/index.md`, `docs/hooks/writing-hooks.md`, 2026-10-07).

**Archivo de configuración.** Objeto `hooks` dentro de `settings.json`. Orden de prioridad (página `hooks/`): `.gemini/settings.json` (proyecto), `~/.gemini/settings.json` (usuario), `/etc/gemini-cli/settings.json` (sistema), extensiones. Interruptor general: `hooksConfig.enabled` (por defecto `true`), `hooksConfig.disabled` (lista de nombres), `hooksConfig.notifications`.

**Eventos** (11): `SessionStart`, `SessionEnd`, `BeforeAgent`, `AfterAgent`, `BeforeModel`, `AfterModel`, `BeforeToolSelection`, `BeforeTool`, `AfterTool`, `PreCompress`, `Notification`. Pueden bloquear: `BeforeTool` (herramienta), `BeforeAgent`, `BeforeModel`, `AfterModel`, `AfterAgent`. `SessionStart`, `SessionEnd`, `PreCompress` y `Notification` son informativos.

**Configuración que bloquea (literal):**

```json
{
  "hooks": {
    "BeforeTool": [
      {
        "matcher": "write_file|replace",
        "hooks": [
          {
            "name": "security-check",
            "type": "command",
            "command": "$GEMINI_PROJECT_DIR/.gemini/hooks/security.sh",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

Campos: `matcher` (expresión regular para herramientas), `sequential` (booleano), `hooks[]` con `type` (solo `"command"`), `command`, `name`, `timeout` (milisegundos, 60000 por defecto), `description`. Variables: `GEMINI_PROJECT_DIR`, `GEMINI_PLANS_DIR`, `GEMINI_SESSION_ID`, `GEMINI_CWD`, y `CLAUDE_PROJECT_DIR` como alias. Nombres de herramienta para el `matcher`: integradas `read_file`, `write_file`, `replace`, `run_shell_command`, `grep_search`, `glob`, `list_directory`, `read_many_files` (de `reference/tools.md`); MCP con el patrón `mcp_<servidor>_<herramienta>`.

**Entrada que recibe (stdin, JSON).** Base: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `timestamp`. En `BeforeTool` además (literal): `tool_name`, `tool_input` («The raw arguments generated by the model»), `mcp_context` (opcional, para MCP), `original_request_name`.

**Respuesta que bloquea (literal del ejemplo oficial de `writing-hooks.md`):**

```json
{
  "decision": "deny",
  "reason": "Security Policy: Potential secret detected in content.",
  "systemMessage": "🔒 Security scanner blocked operation"
}
```

(el script la imprime con `cat <<EOF ... EOF` y luego `exit 0`). `decision` admite `"deny"` o su alias `"block"`; `reason` «Required if denied. This text is sent **to the agent** as a tool error». `hookSpecificOutput.tool_input` «merges with and overrides» los argumentos. `continue: false` mata el bucle completo del agente.

**Códigos de salida (literal):** «`0`: Success. `stdout` is parsed as JSON. **Preferred for all logic.** `2`: System Block. The action is blocked; `stderr` is used as the rejection reason. `Other`: Warning. A non-fatal failure occurred; the CLI continues with a warning.» Para `BeforeTool`, salida 2: «Prevents execution. Uses `stderr` as the `reason` sent to the agent. **The turn continues.**»

**Si el hook falla: ABIERTO.** Cualquier código distinto de 0 y 2 (excepción del script, `exit 1`) es una advertencia y la acción sigue «using original parameters». Si `stdout` trae texto que no es JSON: «parsing will fail. The CLI will default to "Allow" and treat the entire output as a `systemMessage`» (página `hooks/`, regla «Silence is Mandatory»: ni un `echo` antes del JSON). Qué ocurre al agotarse el `timeout`: **no se pudo confirmar** (se buscó en las tres páginas de hooks).

**Confianza.** «Gemini CLI **fingerprints** project hooks. If a hook's name or command changes (for example, via `git pull`), it is treated as a **new, untrusted hook** and you will be warned before it executes.» Gestión: `/hooks panel`, `/hooks enable-all`, `/hooks disable-all`, `/hooks enable <nombre>`. Además, «Trusted Folders» está **desactivado por defecto**; al activarlo (`security.folderTrust.enabled: true` en `~/.gemini/settings.json`), en una carpeta no confiable «Workspace settings are ignored» (no se carga `.gemini/settings.json` del proyecto, y con él los hooks de proyecto), los servidores MCP no se conectan y no se cargan comandos `.toml`.

Ejemplo de script (de `hooks/writing-hooks.md`): lee `input=$(cat)`, extrae `jq -r '.tool_input.content // .tool_input.new_string // ""'`, y si coincide con `api[_-]?key|password|secret` imprime la denegación anterior y termina con `exit 0`; si no, `echo '{"decision": "allow"}'`.

## 4. Comandos personalizados

**Estado: confirmado con fuente** (`https://geminicli.com/docs/cli/custom-commands/`; fuente `docs/cli/custom-commands.md`, 2026-10-07).

- Ubicación: `~/.gemini/commands/` (usuario) y `<proyecto>/.gemini/commands/`; «the project command will always be used» si coinciden. Las subcarpetas dan espacio de nombres: `git/commit.toml` pasa a `/git:commit`. Recargar con `/commands reload`; listar con `/commands list`.
- Formato TOML: `prompt` (obligatorio), `description` (opcional).
- Marcadores: `{{args}}` (crudo fuera de `!{...}`, escapado dentro), `!{comando}` (el CLI pide confirmar el comando exacto antes de ejecutarlo). `@{archivo}`: no se copió un ejemplo (**parcial**). Sin `{{args}}`, los argumentos se añaden al final del prompt.
- Ejemplo literal:

```toml
# Invoked via: /git:fix "Button is misaligned"

description = "Generates a fix for a given issue."
prompt = "Please provide a code fix for the issue described here: {{args}}."
```

- En una carpeta no confiable (con Trusted Folders activo) no se cargan comandos `.toml`.

## 5. Skills

**Estado: confirmado con fuente** (`https://geminicli.com/docs/cli/skills/` y `.../cli/creating-skills/`; fuentes crudas `docs/cli/skills.md`, `docs/cli/creating-skills.md`, 2026-10-07).

- Basado en el estándar abierto `https://agentskills.io`. Ubicaciones, de menor a mayor precedencia: integradas; de extensiones; de usuario `~/.gemini/skills/` o `~/.agents/skills/`; de espacio de trabajo `.gemini/skills/` o `.agents/skills/`. «Within the same tier (user or workspace), the `.agents/skills/` alias takes precedence over the `.gemini/skills/` directory.»
- Formato: directorio con `SKILL.md`; frontmatter con `name` y `description`; opcionales `scripts/`, `references/`, `assets/`. Literal:

```markdown
---
name: code-reviewer
description:
  Expertise in reviewing code changes for correctness, security, and style. Use
  when the user asks to "review" their code or a PR.
---

# Code Reviewer Instructions
```

- Activación: herramienta `activate_skill` con confirmación del usuario (la carpeta de la skill se añade a las rutas permitidas). Gestión: `/skills list|enable|disable|reload`, `gemini skills install <url-o-ruta>`. Límites de `name`/`description`: **no se pudo confirmar**.

## 6. MCP

**Estado: confirmado con fuente** (`https://geminicli.com/docs/tools/mcp-server/`; claves en `docs/reference/configuration.md`, sección `mcpServers`, 2026-10-07).

Archivo: `.gemini/settings.json` o `~/.gemini/settings.json`, clave `mcpServers` (objeto por nombre). Claves por servidor (literal de la referencia): `command`, `args`, `env`, `cwd`, `url` (SSE), `httpUrl` (HTTP transmisible), `headers`, `timeout` (ms), `trust` («bypass all tool call confirmations»), `description`, `includeTools`, `excludeTools` («`excludeTools` takes precedence»). «At least one of `command`, `url`, or `httpUrl` must be provided»; precedencia `httpUrl`, `url`, `command`. Cada herramienta se publica como `mcp_<alias>_<herramienta>`. Advertencia oficial: **evitar guiones bajos en el alias del servidor** (el motor de políticas parte el nombre por el primer guion bajo y «can cause security policies to fail silently»). Interpolación (de la referencia, sección de variables de entorno): los valores de texto de `settings.json` admiten `$VAR_NAME`, `${VAR_NAME}` y `${VAR_NAME:-DEFAULT_VALUE}`. Filtros globales: `mcp.allowed`, `mcp.excluded`. Alta por CLI `gemini mcp add`: nombrada en la matriz, no leída aquí (**parcial**).

Ejemplo mínimo copiable: lo leído no trae un bloque completo corto; no se inventa uno. Las claves de arriba son la fuente.

## 7. Permisos, modos, sandbox y aprobaciones

**Estado: confirmado con fuente** (`https://geminicli.com/docs/reference/policy-engine/`, `.../cli/plan-mode/`, `.../cli/sandbox/`, `.../reference/configuration/`, `.../cli/cli-reference/`, 2026-10-07).

- **Modos**: `--approval-mode` con `default`, `auto_edit`, `yolo`, `plan`. En `settings.json`: `general.defaultApprovalMode` con valores `default`, `auto_edit`, `plan`; «YOLO mode [...] can only be enabled via command line». `--yolo` está obsoleto. **Solo lectura**: Plan Mode («A strict, read-only mode»), con `gemini --approval-mode=plan`, `/plan` o `Shift+Tab`. En las reglas TOML el modo se escribe `autoEdit` en la lista `modes`; en la línea de órdenes es `auto_edit`.
- **Motor de políticas** (la lista de comandos permitidos o denegados). Archivos `.toml` en `~/.gemini/policies/` (usuario) y, para administradores, `/etc/gemini-cli/policies` (Linux; con propietario `root` y sin escritura de grupo u otros, si no se ignora). **El nivel de espacio de trabajo `.gemini/policies` está documentado como «currently non-functional»** (issue 18186 del repositorio). Literal:

```toml
[[rule]]
toolName = "run_shell_command"
commandPrefix = "rm -rf"
decision = "deny"
priority = 100
```

Campos: `toolName` (con comodines `*`, `mcp_*`), `mcpName`, `subagent`, `toolAnnotations`, `argsPattern` (expresión regular sobre los argumentos como JSON estable), `commandPrefix`, `commandRegex`, `decision` (`allow`, `deny`, `ask_user`), `priority` (0 a 999), `denyMessage`, `modes`, `interactive`. Gana la prioridad más alta. «`ask_user` [...] (In non-interactive mode, this is treated as `deny`.)». Una regla `deny` sin `argsPattern` retira la herramienta de la vista del modelo. Incoherencia de la documentación: la tabla de niveles numera Default 1, Extension 2, Workspace 3, User 4, Admin 5, pero los ejemplos de la fórmula usan bases hasta 4; no depender de números absolutos entre niveles.
- Lista permitida heredada: `tools.allowed` en `settings.json` (ej. `["run_shell_command(git)", "run_shell_command(npm test)"]`) y `tools.core` (lista blanca de herramientas integradas); `--allowed-tools` está **obsoleto** a favor del motor de políticas.
- **Sandbox**: `-s` / `--sandbox`, `GEMINI_SANDBOX=true|docker|podman|sandbox-exec|runsc|lxc`, o `"tools": {"sandbox": true}` / `"docker"`. Implementaciones: Seatbelt (macOS), contenedor (Docker/Podman), gVisor/`runsc` (Linux), LXC; imagen propia con `GEMINI_SANDBOX_IMAGE` o `.gemini/sandbox.Dockerfile`. (La matriz menciona sandbox nativo de Windows: no se releyó aquí.)

## 8. Ejecución no interactiva para CI

**Estado: confirmado con fuente** (`https://geminicli.com/docs/cli/headless/`; fuentes `docs/cli/headless.md` y `docs/cli/cli-reference.md`, 2026-10-07).

- Se activa con `-p` / `--prompt` («Forces non-interactive mode») o entrada sin TTY. `--output-format` (`-o`) con `text`, `json` (objeto con `response`, `stats`, `error`) o `stream-json` (JSON Lines: `init`, `message`, `tool_use`, `tool_result`, `error`, `result`).
- Códigos de salida (literal): `0` éxito, `1` «General error or API failure», `42` «Input error (invalid prompt or arguments)», `53` «Turn limit exceeded».
- Banderas útiles: `--approval-mode`, `--sandbox`, `--skip-trust` («Trust the current workspace for this session, skipping the folder trust check»), `--allowed-mcp-server-names`; la página de políticas nombra `--admin-policy`.
- Acción de GitHub y variables de autenticación para CI: **no se pudo confirmar** (no se leyó `cli/tutorials/automation.md`).
- Si un hook de proyecto no confiable corre sin diálogo con `-p`: **no se pudo confirmar**.

## 9. Subagentes

**Estado: confirmado con fuente** (`https://geminicli.com/docs/core/subagents/`; fuente `docs/core/subagents.md`, 2026-10-07).

Archivos Markdown con frontmatter YAML en `.gemini/agents/*.md` (proyecto) o `~/.gemini/agents/*.md` (usuario); el cuerpo es el prompt de sistema. Literal:

```markdown
---
name: security-auditor
description: Specialized in finding security vulnerabilities in code.
kind: local
tools:
  - read_file
  - grep_search
model: gemini-3-flash-preview
temperature: 0.2
max_turns: 10
---

You are a ruthless Security Auditor. Your job is to analyze code for potential
vulnerabilities.
```

Campos: `name` (obligatorio; minúsculas, números, guiones y guiones bajos), `description` (obligatorio), `kind` (`local` por defecto o `remote`), `tools` (admite `*`, `mcp_*`, `mcp_server_*`; «If omitted, it inherits all tools from the parent session»), `mcpServers` en línea, `model`, `temperature`, `max_turns` (30 por defecto), `timeout_mins` (10 por defecto). Se invocan con `@nombre` o por delegación automática; integrados `codebase_investigator`, `cli_help`, `generalist`, `browser_agent` (desactivado por defecto). Ajustes globales: `agents.overrides.<nombre>`. «Recursion protection: subagents **cannot** call other subagents.» Ejecución en paralelo de varios subagentes: **no se pudo confirmar** (la página no lo trata).

---

## Lo que un adaptador puede generar con seguridad hoy

Solo lo confirmado arriba:

1. `GEMINI.md` en la raíz, y `context.fileName: ["AGENTS.md", "GEMINI.md"]` en `.gemini/settings.json` si se quiere que lea `AGENTS.md` (nunca asumir que lo lee).
2. Comandos en `.gemini/commands/<ruta>.toml` con `prompt` y `description`, y `{{args}}`.
3. Skills en `.gemini/skills/<nombre>/SKILL.md` o `.agents/skills/<nombre>/SKILL.md` con `name` y `description`.
4. Subagentes en `.gemini/agents/<nombre>.md` con `name`, `description`, `tools`, `max_turns`.
5. MCP en `.gemini/settings.json`, clave `mcpServers`, con `command`/`args`/`env` o `url`/`httpUrl`, alias sin guiones bajos, y `includeTools`/`excludeTools`.
6. Hook `BeforeTool` en `.gemini/settings.json` (objeto `hooks`) con `matcher`, `command`, `timeout`, que conteste JSON `{"decision":"deny","reason":...}` con salida 0, avisando al usuario de la huella de confianza.
7. Reglas de política **en el nivel de usuario** `~/.gemini/policies/*.toml` (o administrador), no en el del proyecto.
8. CI con `gemini -p "..." --approval-mode=plan` (solo lectura) y `-o json` o `stream-json`, interpretando los códigos 0, 1, 42, 53.

## Lo que no debe generarse todavía

- Políticas en `<proyecto>/.gemini/policies/` (documentadas como no funcionales).
- Reglas por ruta/glob (no existe).
- Cualquier confianza en que un hook fallido bloquee: Gemini falla abierto (códigos distintos de 0 y 2, texto en stdout que no es JSON); y la salida 2 solo detiene la herramienta: «The turn continues».
- `--allowed-tools` y `--yolo` (obsoletos).
- Límite de tamaño de `GEMINI.md`; comportamiento del `timeout` de un hook; paralelismo de subagentes; acción de GitHub para CI.
- Alias de servidores MCP con guion bajo.
- Depender de Trusted Folders (desactivado por defecto) para proteger los hooks de proyecto.

### Diseño del hook de bloqueo de datos (Gemini CLI)

Objetivo: impedir que el agente lea, imprima o envíe datos sensibles por sus herramientas.

1. **Cómo recibe la acción.** `BeforeTool` con `matcher` `"run_shell_command|read_file|read_many_files|grep_search|glob|write_file|replace|mcp_.*"`. Por stdin llega JSON con `tool_name` y `tool_input` (argumentos del modelo: `command` en `run_shell_command`, `file_path` en `read_file`/`write_file`/`replace`, `pattern` y `dir_path` en búsqueda; ver `reference/tools.md`). El script normaliza el texto y lo compara con patrones de datos y destinos.
2. **Cómo deniega.** Salida 0 y JSON por stdout: `{"decision":"deny","reason":"<regla y alternativa>","systemMessage":"..."}`; es la forma «idiomática» de la documentación porque el mensaje llega al agente como error de herramienta. Respaldo: salida 2 con la razón en stderr. Nada más en stdout (ni un `echo`).
3. **Fallo cerrado en el propio script.** La plataforma falla abierto (otro código distinto de 0 o 2, o stdout no JSON, equivalen a permitir). El script debe envolver todo en un manejador que ante cualquier excepción o entrada inesperada emita la denegación y salga con 0, e imprimir diagnóstico solo por stderr.
4. **Que no se pueda saltar.** Complementar con reglas `deny` en `~/.gemini/policies/*.toml` (o en la ruta de administrador, de root) con `commandPrefix`/`argsPattern`: una `deny` sin `argsPattern` retira la herramienta del modelo y no depende de que un script termine bien. Mantener `hooksConfig.enabled` en `true` y no confiar en que Trusted Folders esté activo. Sandbox (`-s`) para limitar lo que el comando puede alcanzar.
5. **Pruebas antes de confiar.** Con el agente real: hook con huella cambiada, JSON inválido, `exit 1`, salida 2, tiempo agotado y comando con sustituciones; confirmar caso por caso si la acción se ejecutó. Hasta tener esas pruebas, el hook es una capa de aviso y no la barrera.
