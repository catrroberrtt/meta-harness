# Codex CLI: formato exacto de configuración (contraste con la fuente)

<!-- tipo: estandar · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: documentación oficial (URLs en el documento) -->

## Fuentes y método

Leídas el 2026-10-07 (fecha de Lima; los servidores respondían ya con fecha UTC del 2026-10-08). Solo lectura: no se ejecutó ni se instaló el agente, no se usaron credenciales.

**Redirección de dominio (destino anotado).** `https://developers.openai.com/codex/<página>` responde `308 Permanent Redirect` hacia `https://learn.chatgpt.com/docs/<página>` (cabecera `location`, comprobada con `curl -I` sobre `/codex/hooks`). Las rutas internas cambiaron: `/codex/hooks` pasa a `/docs/hooks` (comprobado); `/codex/agent-configuration/agents-md` pasa a `/docs/agent-configuration/agents-md` (comprobado con WebFetch). Los `docs/*.md` del repositorio aún enlazan rutas antiguas del tipo `/codex/guides/agents-md` (no se verificó su destino). Cada página publica su versión Markdown añadiendo `.md` a la URL (así lo dice la propia página, y el índice está en `https://developers.openai.com/codex/llms.txt`, que lista las páginas de `learn.chatgpt.com`). Se leyeron en esa versión Markdown:

- `https://learn.chatgpt.com/docs/hooks.md`
- `https://learn.chatgpt.com/docs/agent-configuration/agents-md.md`
- `https://learn.chatgpt.com/docs/agent-configuration/rules.md`
- `https://learn.chatgpt.com/docs/agent-configuration/subagents.md`
- `https://learn.chatgpt.com/docs/build-skills.md`
- `https://learn.chatgpt.com/docs/custom-prompts.md`
- `https://learn.chatgpt.com/docs/extend/mcp.md`
- `https://learn.chatgpt.com/docs/agent-approvals-security.md`
- `https://learn.chatgpt.com/docs/non-interactive-mode.md`
- `https://learn.chatgpt.com/docs/config-file/config-basic.md` y `.../config-file/config-reference.md`
- `https://learn.chatgpt.com/docs/developer-commands.md`

Repositorio oficial `openai/codex`, rama `main`, commit `529cd6b8602f77ce946502d2e67df6b41bc795af` en la fecha de lectura:

- Esquemas JSON generados de los hooks: `codex-rs/hooks/schema/generated/pre-tool-use.command.input.schema.json` y `...output.schema.json` (y los de los demás eventos).
- Código del manejador de `PreToolUse`: `codex-rs/hooks/src/events/pre_tool_use.rs`. Lo que sale de este archivo lleva la etiqueta **[código]**: es comportamiento actual de `main`, no un contrato documentado.
- Los archivos `docs/*.md` del repositorio son solo remisiones a la documentación publicada (p. ej. `docs/agents_md.md` solo enlaza); no contienen el formato.

Limitaciones: (a) la tabla de opciones de `codex exec` y la de `config-reference` se renderizan con componentes JavaScript y en el Markdown solo aparecen parcialmente; lo no visible se marca como no confirmado. (b) Los ejemplos están copiados literalmente de la fuente; solo se quitó texto circundante.

---

## 1. Archivo de instrucciones del proyecto

**Estado: confirmado con fuente** (`https://learn.chatgpt.com/docs/agent-configuration/agents-md.md`, 2026-10-07).

- Nombre: `AGENTS.md` (nombre principal, sin enlazarlo con nada). Variante de sustitución: `AGENTS.override.md`.
- Jerarquía (literal): «1. **Global scope:** In your Codex home directory (defaults to `~/.codex`, unless you set `CODEX_HOME`), Codex reads `AGENTS.override.md` if it exists. Otherwise, Codex reads `AGENTS.md`. Codex uses only the first non-empty file at this level. 2. **Project scope:** Starting at the project root (typically the Git root), Codex walks down to your current working directory. [...] In each directory along the path, it checks for `AGENTS.override.md`, then `AGENTS.md`, then any fallback names in `project_doc_fallback_filenames`. Codex includes at most one file per directory. 3. **Merge order:** Codex concatenates files from the root down, joining them with blank lines. Files closer to your current directory override earlier guidance because they appear later in the combined prompt.»
- Tope: «stops adding files once the combined size reaches the limit defined by `project_doc_max_bytes` (32 KiB by default)». Los archivos vacíos se omiten. Se reconstruye en cada ejecución (sin caché).
- Nombres alternativos y tope (literal, `config.toml`):

```toml
# ~/.codex/config.toml
project_doc_fallback_filenames = ["TEAM_GUIDE.md", ".agents.md"]
project_doc_max_bytes = 65536
```

- Cómo lee `AGENTS.md`: es su nombre nativo. `CLAUDE.md` o `GEMINI.md` **no** se leen salvo que se listen en `project_doc_fallback_filenames`; «Filenames not on this list are ignored for instruction discovery».
- Importaciones `@archivo` dentro de `AGENTS.md`: **no se pudo confirmar** (se buscó en `agents-md.md`; no aparece).
- Ejemplo mínimo (literal):

```md
# AGENTS.md

## Repository expectations

- Run `npm run lint` before opening a pull request.
- Document public utilities in `docs/` when you change behavior.
```

## 2. Reglas por ruta o patrón

**Estado: no se pudo confirmar** que exista activación por glob o por archivo editado.

Se intentó: lectura completa de `agents-md.md` y `rules.md`, y búsqueda de `globs`, `paths` y `applyTo` en las páginas de la lista. Lo que sí existe, confirmado:

- `AGENTS.md` / `AGENTS.override.md` **por directorio, a lo largo de la ruta de la raíz al directorio actual**. «Codex stops searching once it reaches your current directory», es decir, no se cargan los de subdirectorios hermanos ni los de carpetas por debajo del directorio donde se lanza. No es activación por el archivo que se edita.
- Las «Rules» de Codex (`.rules`, ver §7) son reglas de **comandos** (qué puede ejecutarse fuera del sandbox), no de contexto por ruta.
- Alternativa documentada por Codex para trabajo por carpeta: lanzar con `codex --cd services/payments ...` y poner un `AGENTS.override.md` en esa carpeta.

## 3. Hooks que pueden denegar una acción

**Estado: confirmado con fuente** (`https://learn.chatgpt.com/docs/hooks.md`; esquemas y código en `openai/codex@529cd6b8`, 2026-10-07). Los hooks están activos por defecto.

**Archivo de configuración.** Literal: «Codex discovers hooks next to active config layers in either of these forms: `hooks.json`; inline `[hooks]` tables inside `config.toml`». Las cuatro ubicaciones útiles: `~/.codex/hooks.json`, `~/.codex/config.toml`, `<repo>/.codex/hooks.json`, `<repo>/.codex/config.toml`. Los plugins pueden traer `hooks/hooks.json`. «If more than one hook source exists, Codex loads all matching hooks.» Los hooks del proyecto «load only when the project `.codex/` layer is trusted».

**Confianza.** «Before a non-managed hook can run, Codex requires you to review and trust the exact hook definition. Codex records trust against the hook's current hash, so new or changed hooks are marked for review and skipped until trusted.» Se gestiona con `/hooks`. Hooks gestionados (sistema, MDM, nube, `requirements.toml`) van confiados por política. Existe `--dangerously-bypass-hook-trust` («run enabled hooks without requiring persisted hook trust for that invocation»). Desactivar todos: `[features] hooks = false`.

**Eventos** (literal): durante el turno `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStop`, `Stop`; al interrumpir `Interrupt`; al empezar `SessionStart`, `SubagentStart`; al terminar `SessionEnd`.

**Configuración que bloquea (JSON, literal de la página):**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/usr/bin/python3 \"$(git rev-parse --show-toplevel)/.codex/hooks/pre_tool_use_policy.py\"",
            "statusMessage": "Checking Bash command"
          }
        ]
      }
    ]
  }
}
```

Equivalente en TOML (literal):

```toml
[[hooks.PreToolUse]]
matcher = "^Bash$"
[[hooks.PreToolUse.hooks]]
type = "command"
command = '/usr/bin/python3 "$(git rev-parse --show-toplevel)/.codex/hooks/pre_tool_use_policy.py"'
timeout = 30
statusMessage = "Checking Bash command"
```

`timeout` en segundos; sin él, 600. `matcher` es una expresión regular sobre el nombre de herramienta; `"*"`, `""` o ausente la hace coincidir con todo.

**Entrada que recibe (stdin, un objeto JSON).** Esquema oficial `pre-tool-use.command.input` (`additionalProperties: false`), campos obligatorios: `cwd`, `hook_event_name` (`"PreToolUse"`), `model`, `permission_mode` (`default`, `acceptEdits`, `plan`, `dontAsk`, `bypassPermissions`), `session_id`, `tool_input`, `tool_name`, `tool_use_id`, `transcript_path` (texto o `null`), `turn_id`; opcionales `agent_id`, `agent_type`. Según la página: `tool_name` es «Canonical hook tool name, such as `Bash`, `apply_patch`, or an MCP name like `mcp__fs__read`»; «`Bash` and `apply_patch` use `tool_input.command`. MCP and other local function tools send their arguments.»

**Respuesta que bloquea** (literal; salida 0 con JSON en stdout):

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Destructive command blocked by hook."
  }
}
```

Forma antigua aceptada (literal): `{"decision": "block", "reason": "Destructive command blocked by hook."}`. Alternativa: «You can also use exit code `2` and write the blocking reason to `stderr`.» Reescribir sin bloquear: `permissionDecision: "allow"` con `updatedInput` (para `Bash` y `apply_patch` debe llevar un `command` de texto). El texto plano en stdout se ignora en `PreToolUse`.

**Códigos de salida y qué pasa si el hook falla: ABIERTO.** La documentación dice: «`permissionDecision: "ask"`, legacy `decision: "approve"`, `continue: false`, `stopReason`, and `suppressOutput` are parsed but not supported yet. Codex marks the hook run as failed, reports the error, and continues the tool call.» Y, sobre hooks remotos gestionados: «a `PreToolUse` callback error, timeout, or malformed response can fail the hook without blocking the tool». **[código]** `pre_tool_use.rs`, función de análisis del resultado:

- salida 0 y JSON válido con denegación: bloquea (`should_block = true`);
- salida 0 con algo que parece JSON pero no cumple el esquema: estado `Failed`, **no bloquea**;
- salida 2 con texto en stderr: bloquea; **salida 2 sin texto en stderr: `Failed`, no bloquea** (mensaje «exited with code 2 but did not write a blocking reason to stderr»);
- cualquier otro código, error al lanzar o tiempo agotado: `Failed`, **no bloquea**.

Conclusión: el agente falla abierto; el script debe capturar sus propios errores y denegar él mismo.

**Cobertura.** `Bash`, `exec_command` (se empareja como `Bash`), `apply_patch` (también `Edit` o `Write`), herramientas MCP (`mcp__server__tool`) y otras funciones locales (`spawn_agent` empareja también `Agent`). **No** cubre herramientas alojadas como `WebSearch`. `write_stdin` no vuelve a pasar por el hook. Literal: «Some specialized tool paths can opt out of the default hook path. Treat tool hooks as a useful guardrail, not a complete enforcement boundary.»

**Hooks gestionados (para que no dependan del usuario)**, literal: `requirements.toml` con `allow_managed_hooks_only = true`, `[features] hooks = true` y `[hooks] managed_dir = "/enterprise/hooks"` más `[[hooks.PreToolUse]]`. Las rutas gestionadas las instala el administrador, no Codex.

`PermissionRequest` (solo corre cuando Codex iba a pedir aprobación): respuesta literal para denegar `{"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {"behavior": "deny", "message": "Blocked by repository policy."}}}`; «any `deny` wins».

## 4. Comandos personalizados

**Estado: confirmado con fuente, pero obsoleto** (`https://learn.chatgpt.com/docs/custom-prompts.md`, 2026-10-07).

Literal: «Custom prompts are deprecated. Use skills for reusable instructions that Codex can invoke explicitly or implicitly.» Viven solo en el directorio de usuario: `~/.codex/prompts/*.md` (solo archivos de primer nivel, no subcarpetas; no se comparten por el repositorio). Se invocan como `/prompts:<nombre>`.

```markdown
---
description: Prep a branch, commit, and open a draft PR
argument-hint: [FILES=<paths>] [PR_TITLE="<title>"]
---
Create a branch named `dev/<feature_name>` for this work.
If files are specified, stage them first: $FILES.
Commit the staged changes with a clear message.
Open a draft PR on the same branch. Use $PR_TITLE when supplied; otherwise write a concise summary yourself.
```

Marcadores: `$1`..`$9`, `$ARGUMENTS`, nombrados en mayúsculas `$FILE` con `KEY=value`, `$$` para un `$` literal. No hay ruta de proyecto. Sustituto recomendado: skills (§5), que se invocan con `$nombre` o `/skills`.

## 5. Skills

**Estado: confirmado con fuente** (`https://learn.chatgpt.com/docs/build-skills.md`, 2026-10-07).

Formato: directorio con `SKILL.md` («The `SKILL.md` file must include `name` and `description`»), más `scripts/`, `references/`, `assets/` y `agents/openai.yaml` opcionales. Estándar abierto: `https://agentskills.io`.

```md
---
name: skill-name
description: Explain exactly when this skill should and should not trigger.
---

Skill instructions for ChatGPT or Codex to follow.
```

Ubicaciones (tabla oficial): `$CWD/.agents/skills`, `$CWD/../.agents/skills`, `$REPO_ROOT/.agents/skills` (el repositorio se escanea «in every directory from your current working directory up to the repository root»), usuario `$HOME/.agents/skills`, administrador `/etc/codex/skills`, y las del sistema incluidas. Admite carpetas simbólicas. **`.codex/skills` no figura**: la ruta de proyecto es `.agents/skills`. Presupuesto de la lista inicial: «at most 2% of the model's context window, or 8,000 characters when the context window is unknown»; si sobra, acorta las descripciones primero. Invocación explícita: `/skills` o `$nombre`; implícita por la descripción. Límites de `name` y `description`: **no se pudo confirmar** (no aparecen en la página).

## 6. MCP

**Estado: confirmado con fuente** (`https://learn.chatgpt.com/docs/extend/mcp.md`, 2026-10-07).

Archivo: `~/.codex/config.toml` o, en proyectos de confianza, `.codex/config.toml`; tabla `[mcp_servers.<nombre>]` (no `mcpServers`). También `codex mcp add <nombre> --env VAR=VALOR -- <comando>` y `codex mcp add context7 -- npx -y @upstash/context7-mcp`.

- STDIO: `command` (obligatorio), `args`, `env`, `env_vars` (nombres a reenviar), `cwd`.
- HTTP transmisible: `url` (obligatorio), `auth`, `bearer_token_env_var`, `http_headers`, `env_http_headers` (cabecera a nombre de variable), `http_headers_helper`.
- Comunes: `startup_timeout_sec` (10 por defecto), `tool_timeout_sec` (60), `enabled`, `required` (si es `true` y no arranca, `codex exec` termina con error), `enabled_tools`, `disabled_tools` (se aplica después), `default_tools_approval_mode` (`auto`, `prompt`, `writes`, `approve`) y `tools.<tool>.approval_mode`.
- Ejemplo literal con OAuth:

```toml
[mcp_servers.example]
url = "https://mcp.example.com"

[mcp_servers.example.oauth]
client_id = "my-client"
callback_url = "http://127.0.0.1/callback"
```

Interpolación de variables de entorno dentro de valores: **no se pudo confirmar** (se usan los campos `*_env_var` y `env_vars` en su lugar).

## 7. Permisos, modos, sandbox y aprobaciones

**Estado: confirmado con fuente** (`https://learn.chatgpt.com/docs/agent-approvals-security.md`, `https://learn.chatgpt.com/docs/agent-configuration/rules.md`, `https://learn.chatgpt.com/docs/config-file/config-basic.md`, 2026-10-07).

- Claves de `config.toml` (literal): `approval_policy = "on-request"` y `sandbox_mode = "workspace-write"`. Modos de sandbox: `read-only`, `workspace-write`, `danger-full-access`. Para solo lectura interactiva (literal): `sandbox_mode = "read-only"` y `approval_policy = "on-request"`, o `codex --sandbox read-only --ask-for-approval on-request`. `approval_policy = "untrusted"` está **retirado** («no longer support»; puede impedir arrancar). `never` desactiva las preguntas (`-a never`); existe `approval_policy = { granular = { ... } }`.
- Solo lectura para CI: `--sandbox read-only --ask-for-approval never`. Atajo peligroso: `--dangerously-bypass-approvals-and-sandbox` (alias `--yolo`).
- Rutas protegidas en `workspace-write` (literal): `<writable_root>/.git`, `<writable_root>/.agents` y `<writable_root>/.codex` quedan de solo lectura, de forma recursiva. El agente no puede editar sus propios hooks, reglas ni skills de proyecto con esas carpetas.
- Perfiles de permisos con nombre: integrados `:read-only`, `:workspace`, `:danger-full-access`; personalizados `[permissions.<nombre>]` más `default_permissions` (página `permissions`, no leída entera: **parcial**).
- **Lista de comandos permitidos: «Rules»** (experimentales, «may change»). Archivo `.rules` en una carpeta `rules/` junto a una capa de configuración activa (`~/.codex/rules/default.rules`; de proyecto `<repo>/.codex/rules/`, solo si el proyecto es de confianza). Lenguaje Starlark. Literal:

```python
prefix_rule(
    pattern = ["gh", "pr", "view"],
    decision = "prompt",
    justification = "Viewing PRs is allowed with approval",
    match = [
        "gh pr view 7888",
    ],
    not_match = [
        "gh pr --repo openai/codex view 7888",
    ],
)
```

`decision` por defecto `"allow"`; valores `allow`, `prompt`, `forbidden`; con varias reglas gana la más restrictiva (`forbidden` > `prompt` > `allow`). Las cadenas `bash -lc "a && b"` se parten en comandos solo si son lineales y sin expansiones; si no, la regla se aplica al guion completo. Probar: `codex execpolicy check --pretty --rules ~/.codex/rules/default.rules -- gh pr view 7888`. Las reglas son sobre comandos que **salen del sandbox**: no sustituyen al sandbox.
- Configuración, precedencia (mayor a menor): banderas y `--config`, `.codex/config.toml` de proyecto (solo de confianza), perfiles, `~/.codex/config.toml`, configuración gestionada, `/etc/codex/config.toml`, valores por defecto. Un proyecto marcado `untrusted` omite `.codex/` del proyecto (configuración, hooks y reglas).

## 8. Ejecución no interactiva para CI

**Estado: confirmado con fuente** (`https://learn.chatgpt.com/docs/non-interactive-mode.md`, 2026-10-07).

```bash
codex exec "summarize the repository structure and list the top 5 risky areas"
```

- Literal: «By default, `codex exec` runs in a read-only sandbox.» Permitir ediciones: `codex exec --sandbox workspace-write "<task>"`. `--full-auto` está obsoleto.
- Salida: progreso por `stderr`, solo el mensaje final por `stdout`. `--json` convierte `stdout` en JSON Lines (eventos `thread.started`, `turn.started`, `turn.completed`, `turn.failed`, `item.*`, `error`). `-o <ruta>` / `--output-last-message`; `--output-schema ./schema.json` para salida estructurada. `--ephemeral`, `--ignore-user-config`, `--ignore-rules` (omite `.rules` de usuario y de proyecto), `--skip-git-repo-check` (por defecto exige un repositorio Git).
- Autenticación: `CODEX_API_KEY` solo para esa invocación; acción oficial `openai/codex-action@v1` (con el ejemplo de `workflow_run`). La página advierte no poner la clave como variable de entorno del trabajo completo.
- `codex exec resume --last "..."`.
- Códigos de salida de `codex exec`: **no se pudo confirmar** (la página no los lista; solo consta que con un MCP `required` que no arranca «exits with an error»). Qué pasa con una aprobación pendiente con `on-request` en `exec` sin tty: **no se pudo confirmar**.
- Hooks en `exec`: se cargan igual (misma ruta de configuración y confianza); para automatización ya validada existe `--dangerously-bypass-hook-trust`. Que un hook no confiado se **omita** en CI sin error visible es una consecuencia del texto («skipped until trusted»), no un comportamiento probado.

## 9. Subagentes

**Estado: confirmado con fuente** (`https://learn.chatgpt.com/docs/agent-configuration/subagents.md`, 2026-10-07).

Archivos TOML autónomos en `~/.codex/agents/` (personales) o `.codex/agents/` (proyecto). Obligatorios: `name`, `description`, `developer_instructions`; se admiten otras claves de `config.toml` (`model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, `skills.config`), que si faltan se heredan del padre. Literal:

```toml
name = "pr_explorer"
description = "Read-only codebase explorer for gathering evidence before changes are proposed."
model = "gpt-6-luna"
model_reasoning_effort = "high"
sandbox_mode = "read-only"
developer_instructions = """
Stay in exploration mode.
Trace the real execution path, cite files and symbols, and avoid proposing fixes unless the parent agent asks for them.
Prefer fast search and targeted file reads over broad scans.
"""
```

Globales bajo `[agents]`: `enabled` (por defecto `true`), `max_concurrent_threads_per_session` (alias heredado `max_threads`), `default_subagent_model`, `default_subagent_reasoning_effort`, `interrupt_message`. Paralelismo: confirmado («spawning specialized agents in parallel»). Integrados con nombre `explorer` (un agente propio con el mismo nombre tiene prioridad). Los hooks `SubagentStart` y `SubagentStop` existen. Límite de profundidad o de subagentes que lanzan subagentes: **no se pudo confirmar**.

---

## Lo que un adaptador puede generar con seguridad hoy

Solo lo confirmado arriba:

1. `AGENTS.md` en la raíz (Markdown plano) y, si hace falta, `project_doc_fallback_filenames` / `project_doc_max_bytes` en `config.toml`; respetar el tope de 32 KiB combinados.
2. Skills en `.agents/skills/<nombre>/SKILL.md` con `name` y `description` (no `.codex/skills`).
3. MCP en `.codex/config.toml` con `[mcp_servers.<nombre>]` (`command`/`args`/`env` o `url`), sabiendo que solo se lee en proyectos de confianza.
4. Subagentes en `.codex/agents/<nombre>.toml` con `name`, `description`, `developer_instructions` y `sandbox_mode`.
5. Reglas de comandos en `<repo>/.codex/rules/*.rules` con `prefix_rule(pattern, decision, justification, match, not_match)`, validadas con `codex execpolicy check`.
6. Hook `PreToolUse` en `.codex/hooks.json` o `[[hooks.PreToolUse]]` con `matcher` de herramientas, que lea el JSON de stdin y conteste con `hookSpecificOutput.permissionDecision = "deny"` (salida 0), y escribir al usuario que debe revisar y confiar el hook en `/hooks`.
7. CI con `codex exec --sandbox read-only` (o `workspace-write`) y `--json`, `-o`, `--output-schema`, `CODEX_API_KEY` acotada a la invocación.
8. `approval_policy = "on-request"` con `sandbox_mode = "read-only"` o `"workspace-write"`.

## Lo que no debe generarse todavía

- Comandos personalizados en `~/.codex/prompts/` (obsoletos, solo de usuario): usar skills.
- Reglas por ruta/glob (no hay mecanismo documentado).
- Cualquier dependencia de que un hook fallido o ausente bloquee: Codex falla abierto, y un hook cambiado o no confiado se omite hasta que el usuario lo confíe.
- `permissionDecision: "ask"`, `continue: false`, `stopReason`, `updatedInput` en `PermissionRequest`: no soportados (el hook falla y la acción sigue).
- Hooks como única barrera: no cubren herramientas alojadas (`WebSearch`) y «some specialized tool paths can opt out».
- `approval_policy = "untrusted"` (retirado).
- Códigos de salida de `codex exec` y comportamiento ante aprobación pendiente sin tty.
- Interpolación `${VAR}` en `config.toml` y `@archivo` en `AGENTS.md`.
- Límites de `name`/`description` de skills y de profundidad de subagentes.

### Diseño del hook de bloqueo de datos (Codex)

Objetivo: impedir que el agente lea, imprima o envíe datos sensibles (archivos de secretos, volcados de bases de datos, variables de entorno) por sus herramientas.

1. **Cómo recibe la acción.** Registro `PreToolUse` con `matcher` `^Bash$|^apply_patch$|^mcp__.*` (y las funciones locales que interesen). Codex entrega por stdin un objeto con `tool_name` y `tool_input`; para `Bash` el texto a analizar es `tool_input.command`, para `apply_patch` es `tool_input.command` (el parche) y para MCP son los argumentos. El script normaliza el texto (comillas, `bash -lc`, redirecciones, `cat`, `env`, `printenv`, `curl`/`scp`) y compara con una lista de patrones de datos y de destinos.
2. **Cómo deniega.** Salida 0 y JSON `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"<regla y alternativa>"}}`. La forma por salida 2 + stderr sirve de respaldo, **siempre con texto en stderr** (si va vacío, Codex lo trata como fallo y deja pasar).
3. **Fallo cerrado en el propio script.** Envolver todo en un bloque que ante excepción, entrada no analizable o campo desconocido emita la denegación (el agente no lo hace por sí mismo). No usar `continue`, `stopReason`, `ask` ni `suppressOutput`.
4. **Que no se pueda saltar.** Instalar el mismo hook como gestionado (`requirements.toml`, `allow_managed_hooks_only = true`, `[features] hooks = true` y `[hooks] managed_dir`) para que no dependa de la confianza del usuario ni de `[features] hooks = false`; el sandbox `workspace-write` ya deja `.codex` y `.agents` de solo lectura para el agente.
5. **Capas complementarias (no sustituyen).** Reglas `.rules` con `decision = "forbidden"` para los prefijos de comando; sandbox `read-only` sin red; MCP con `disabled_tools`/`enabled_tools`. Documentar que `WebSearch` y rutas especializadas no pasan por el hook.
6. **Pruebas antes de confiar.** Probar con el agente real: hook fuera de confianza, JSON inválido, salida 2 sin stderr, tiempo agotado, comando dentro de `bash -lc` con sustituciones; todo debe terminar en bloqueo antes de dar el adaptador por bueno.
