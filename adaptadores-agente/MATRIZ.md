# Matriz de capacidades de agentes de programación con IA

<!-- tipo: estandar · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: documentación oficial de cada agente (ver MATRIZ.md); celdas de Cursor, OpenCode, Codex, Gemini, Windsurf y Copilot corregidas contra su `FORMATO.md` -->

Todas las celdas se leyeron el **2026-10-07** en la documentación oficial de cada agente. Estados: **sí** (soportado), **parcial**, **no** (la documentación dice que no), **no verificado** (no se encontró en la fuente oficial leída; no significa que no exista). Nada se rellenó por suposición.

**Correcciones del 2026-10-07:** las celdas de Cursor y OpenCode que discrepaban de la fuente se corrigieron contra `cursor/FORMATO.md` y `opencode/FORMATO.md` (cada celda corregida cita ese archivo). Los estados del «Resumen visual» que cambiaron se indican abajo.

**Segunda ronda de correcciones (2026-10-07):** se corrigieron las celdas de **Codex, Gemini, Windsurf y Copilot** contra `codex/FORMATO.md`, `gemini/FORMATO.md`, `windsurf/FORMATO.md` y `copilot/FORMATO.md` (cada celda cambiada cita su archivo y la fecha). Gemini: la fila de instrucciones resultó correcta y no cambió. Estados del «Resumen visual» que cambiaron: Codex «5 Comandos propios» N a P; Windsurf «5 Comandos propios» S a P (workflows solo en Cascade), «10 No interactivo» N a P (solo la CLI). «9 Permisos / modos / sandbox» de Windsurf se **mantiene en P**: en Cascade una entrada denegada solo exige aprobación y no bloquea; solo Devin Local tiene un deny que gana siempre. Windsurf se documenta como **dos agentes** (Cascade y Devin Local) y Copilot como **tres superficies** (VS Code Local, Agent Host y CLI): una celda que dice «sí» puede valer solo para una de ellas.

## Límites de esta lectura (leer antes de usar la matriz)

- Las páginas se leyeron con una herramienta que resume cada página con un modelo pequeño; los **nombres de archivo y rutas** deben revisarse contra la fuente antes de generar un adaptador (criterio de aceptación del adaptador, no de la matriz).
- Claude Code: las páginas de hooks, skills, subagentes y MCP superan 100 000 caracteres y se leyó solo el primer tramo; lo no visto queda «no verificado».
- Codex: `developers.openai.com/codex/*` redirige (308) a `learn.chatgpt.com/docs/*`; se leyó el destino de la redirección. Windsurf: `docs.windsurf.com` redirige (307) a `docs.devin.ai/desktop/*` y la documentación habla de «Devin Desktop»; se leyó el destino. Ambos dominios llegan por redirección del dominio original, no por enlace verificado aparte.
- Cursor: las URLs `context/*` ya no sirven (devuelven «Page not found»); las canónicas actuales son `/docs/rules`, `/docs/hooks`, `/docs/skills`, `/docs/subagents`, `/docs/mcp` y `/docs/plugins` (con sufijo `.md` se lee el Markdown oficial) [FORMATO.md de Cursor, «Fuentes y método», 2026-10-07]. Los comandos propios no están documentados hoy como ruta independiente (ver §5).
- Los productos cambian rápido (hooks de Copilot en VS Code están en *Preview*); por eso la matriz vence a los 60 días.

## Agentes y fuentes

Todas las fuentes se leyeron el 2026-10-07. Clave `Agente:página` usada en las tablas.

| Agente | Páginas oficiales leídas (URL) |
|---|---|
| **Claude Code** (CC) | `https://code.claude.com/docs/en/` + `memory`, `hooks`, `sub-agents`, `skills`, `permissions`, `sandboxing`, `mcp`, `plugins`, `headless` |
| **OpenCode** (OC) | `https://opencode.ai/docs/` + `rules/`, `plugins/`, `agents/`, `commands/`, `skills/`, `mcp-servers/`, `permissions/`, `cli/` |
| **Cursor** (CU) | `https://cursor.com/docs/` + `rules`, `hooks`, `reference/third-party-hooks`, `skills`, `subagents`, `mcp`, `plugins`, `reference/plugins`, `agent/security/run-modes`, `agent/plan-mode`, `cli/using`, `cli/headless`, `cli/reference/parameters`, `cli/reference/permissions`, `cli/reference/configuration`, `cli/reference/output-format` (las rutas `context/*` ya no sirven; fuente: FORMATO.md de Cursor) |
| **OpenAI Codex CLI** (CX) | `https://developers.openai.com/codex/...` redirigido a `https://learn.chatgpt.com/docs/` + `agent-configuration/agents-md`, `config-file/config-basic`, `hooks`, `non-interactive-mode`, `build-skills`, `agent-configuration/subagents`, `extend/mcp`, `developer-commands` |
| **Gemini CLI** (GE) | `https://geminicli.com/docs/` + `cli/gemini-md/`, `hooks/`, `cli/headless/`, `cli/custom-commands/`, `core/subagents/`, `cli/skills/`, `tools/mcp-server/`, `cli/sandbox/`, `cli/plan-mode/`, `extensions/`, `cli/tutorials/memory-management/`, `reference/policy-engine/` |
| **Windsurf / Devin Desktop** (WS) | `https://docs.windsurf.com/windsurf/cascade/*` redirigido a `https://docs.devin.ai/desktop/cascade/` + `memories`, `hooks`, `workflows`, `skills`, `mcp`, `cascade` |
| **Aider** (AI) | `https://aider.chat/docs/` + `usage/conventions.html`, `scripting.html`, `config/options.html`, `usage/commands.html` (búsqueda de «MCP» en aider.chat sin resultados) |
| **GitHub Copilot, modo agente en VS Code** (CP) | `https://code.visualstudio.com/docs/copilot/customization/` + `custom-instructions`, `hooks`, `custom-agents`, `prompt-files`, `agent-skills`, `mcp-servers`, `agent-plugins`; `.../copilot/agents/agent-tools`; Copilot CLI: `https://docs.github.com/en/copilot/concepts/agents/about-copilot-cli` |
| **Cline** (CL, agregado) | `https://docs.cline.bot/customization/cline-rules`, `.../hooks` |

**Por qué se agrega Cline:** extensión de VS Code de código abierto con adopción amplia; se incluye solo con lo que la documentación confirmó (reglas) y el resto queda «no verificado». No se agregó ningún otro agente.

## 1. Archivo de instrucciones del proyecto

| Agente | Nombre y ubicación | ¿Lee `AGENTS.md`? | Jerarquía / límites | Estado |
|---|---|---|---|---|
| CC | `./CLAUDE.md` o `./.claude/CLAUDE.md`; personal `./CLAUDE.local.md`; usuario `~/.claude/CLAUDE.md`; gestionado `/etc/claude-code/CLAUDE.md` (Linux) [CC:memory] | Sí, **solo si no hay** `CLAUDE.md`/`CLAUDE.local.md` en el directorio de trabajo o encima; con ambos lee solo `CLAUDE.md` (se puede importar con `@AGENTS.md`) [CC:memory] | Se concatenan de la raíz hacia el directorio actual; subdirectorios se cargan al leer archivos de ahí; importaciones `@ruta` hasta 4 niveles. Guía: menos de 200 líneas por archivo (recomendación, no tope) [CC:memory] | sí |
| OC | `AGENTS.md` en la raíz; global `~/.config/opencode/AGENTS.md`; alternativa `CLAUDE.md` / `~/.claude/CLAUDE.md` [OC:rules] | Sí (nombre principal) | Gana el primer archivo coincidente por categoría; `instructions` en `opencode.json` admite globos y URLs. Límite de tamaño: no documentado (no aparece en `rules` ni en `config`); `@archivo` dentro de `AGENTS.md` no se expande solo; `instructions` carga los archivos siempre, no según la ruta editada; las URLs remotas se descargan con tiempo límite de 5 s [OC:rules; FORMATO.md de OpenCode §1, 2026-10-07] | sí |
| CU | Reglas de proyecto `.cursor/rules/*.mdc`; reglas de usuario y de equipo; `AGENTS.md` en raíz o subdirectorios [CU:rules] | Sí (raíz y anidados; el más específico prevalece); la CLI lee además `CLAUDE.md` de la raíz [CU:rules, CU:cli/using; FORMATO.md de Cursor §1, 2026-10-07] | Recomendación «menos de 500 líneas» confirmada con fuente; tope duro: no se pudo confirmar | sí |
| CX | `AGENTS.md`; global `~/.codex/AGENTS.md`; sobrescritura `AGENTS.override.md`; nombres alternativos configurables [CX:agents-md] | Sí (nombre principal) | De la raíz de git al directorio actual, un archivo por directorio; **tope combinado 32 KiB** por defecto (`project_doc_max_bytes`); `CLAUDE.md` o `GEMINI.md` **no** se leen salvo que se listen en `project_doc_fallback_filenames` [CX:agents-md; FORMATO.md de Codex §1, 2026-10-07] | sí |
| GE | `GEMINI.md` (global `~/.gemini/GEMINI.md`, proyecto, subdirectorios); el nombre se cambia con `context.fileName` en `settings.json` [GE:gemini-md] | Parcial: solo si se configura `context.fileName: ["AGENTS.md", ...]` [GE:gemini-md] | Global, espacio de trabajo y carga bajo demanda al tocar archivos; importaciones `@archivo.md`. Límite de tamaño: no verificado | parcial |
| WS | Reglas `.devin/rules/*.md` (preferida) o `.windsurf/rules/*.md` (heredada) o `.windsurfrules`; global `~/.codeium/windsurf/memories/global_rules.md`; empresa `/etc/devin/rules/*.md` [WS:memories] | Sí: la documentación recomienda escribir el conocimiento como regla o en `AGENTS.md` del repo [WS:memories]; lectura de anidados confirmada: la raíz siempre está activa; un `AGENTS.md` de subdirectorio es una regla con patrón `<dir>/**` en Cascade, y Devin Local los carga de forma perezosa al acceder a archivos de ese directorio [FORMATO.md de Windsurf §1, 2026-10-07] | **Tope: 6 000 caracteres (global) y 12 000 por regla** [WS:memories] | sí |
| AI | No hay archivo propio autodescubierto; se cargan archivos de convenciones (`CONVENTIONS.md`) con `--read` o `read:` en `.aider.conf.yml` [AI:conventions] | No verificado (la página de convenciones no lo menciona) | Configuración: `.aider.conf.yml` en raíz de git, directorio actual o `~` [AI:options] | parcial |
| CP | `.github/copilot-instructions.md`; `AGENTS.md` (raíz y anidados); `CLAUDE.md` (raíz o `.claude`) [CP:custom-instructions] | Sí | Las fuentes se **suman** (no se sobrescriben); no se usan en sugerencias en línea. Límite: no verificado | sí |
| CL | `.clinerules/` o `.cline/rules/`; global `~/Documents/Cline/Rules`; detecta `.cursorrules`, `.windsurfrules` y `AGENTS.md` [CL:cline-rules] | Sí | Las reglas del proyecto prevalecen sobre las globales. Límite: no verificado | sí |

## 2. Reglas por archivo o por patrón de ruta

| Agente | Mecanismo | Estado |
|---|---|---|
| CC | `.claude/rules/*.md` (recursivo) con frontmatter `paths:`; se cargan al trabajar con archivos coincidentes; `~/.claude/rules/` para usuario [CC:memory] | sí |
| OC | `instructions` en `opencode.json` carga archivos por globo, pero no se documenta activación según la ruta editada (carga los archivos siempre) [FORMATO.md de OpenCode §2] | no verificado |
| CU | `.cursor/rules/**/*.mdc` con `globs`, `alwaysApply`, `description` [CU:rules]. **Solo `.mdc`: un `.md` en `.cursor/rules` se ignora**; la regla con `globs` se adjunta cuando un archivo coincidente está en el contexto [FORMATO.md de Cursor §2, 2026-10-07] | sí |
| CX | Solo `AGENTS.md` anidados por directorio [CX:agents-md]; reglas por globo: no verificado | parcial |
| GE | `GEMINI.md` de subdirectorio cargado al acceder a archivos [GE:gemini-md]; globos: no verificado | parcial |
| WS | Frontmatter `trigger: always_on / model_decision / glob / manual` [WS:memories] | sí |
| AI | No aparece en las páginas leídas | no verificado |
| CP | `.github/instructions/*.instructions.md` (o `.claude/rules`) con `applyTo` (globo) [CP:custom-instructions] | sí |
| CL | Frontmatter `paths:` en las reglas [CL:cline-rules] | sí |

## 3. Hooks o eventos que permiten bloquear o validar antes de actuar

| Agente | Dónde se configura | Eventos relevantes | ¿Puede denegar? | Estado |
|---|---|---|---|---|
| CC | `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`, política gestionada, `hooks/hooks.json` de plugin, frontmatter de skill/subagente; JSON `{"hooks":{"Evento":[{"matcher":..,"hooks":[{"type":"command",..}]}]}}` [CC:hooks] | SessionStart/End, UserPromptSubmit, **PreToolUse**, PostToolUse, PermissionRequest, Stop, SubagentStop, ConfigChange y otros (lista completa no leída) | **Sí**: código de salida 2 o JSON `permissionDecision: "deny"` en PreToolUse. Tipos: command, http, mcp_tool, prompt, agent | sí |
| OC | Plugins JS/TS en `.opencode/plugins/` o `~/.config/opencode/plugins/`, o npm en `"plugin"` [OC:plugins]. No son eventos con códigos de salida: son funciones `(input, output)`; en `tool.execute.before` la entrada es `input {tool, sessionID, callID}` y `output {args}` [FORMATO.md de OpenCode §3, 2026-10-07] | `tool.execute.before/after`, `file.edited`, `session.*`, `permission.asked` | **Sí**: se bloquea con `throw new Error(...)` en `tool.execute.before` (patrón documentado). Que el hook se dispare para MCP, recursos MCP y `task`: confirmado en el código de la rama `dev`, no en la documentación. `permission.asked` existe pero no está documentado como vía para denegar [FORMATO.md de OpenCode §3] | sí |
| CU | `.cursor/hooks.json` (proyecto) o `~/.cursor/hooks.json`; `{"version":1,"hooks":{..}}`; Cursor también lee hooks de `.claude/settings.json`, `.claude/settings.local.json` y `~/.claude/settings.json` [CU:hooks, CU:reference/third-party-hooks; FORMATO.md de Cursor §3, 2026-10-07] | `beforeShellExecution`, `beforeMCPExecution`, `beforeReadFile`, `preToolUse`, `beforeSubmitPrompt`, `afterFileEdit`, `stop`, subagentes, etc. | **Sí**: salida 2 deniega; JSON `permission`. Con salida 0, en un hook de permiso, un JSON inválido o fuera de esquema **bloquea**. «Otros códigos de salida permiten» vale solo para fallos del script; `failClosed: true` bloquea además fallo, tiempo agotado, código ≠ 0 y ausencia de salida. `preToolUse` solo acepta `allow`/`deny` (`ask` no se aplica); en `subagentStart` `ask` se trata como `deny` [FORMATO.md de Cursor §3] | sí |
| CX | `~/.codex/hooks.json` o `config.toml`, `<repo>/.codex/hooks.json` o `config.toml`, plugins; los hooks no gestionados exigen revisión de confianza [CX:hooks]. **Un hook nuevo o modificado no corre hasta confiar en él con `/hooks`** (la confianza se liga al hash). Vía gestionada: `requirements.toml` con `allow_managed_hooks_only = true` [FORMATO.md de Codex §3, 2026-10-07] | 12 eventos: SessionStart, **PreToolUse**, PostToolUse, PermissionRequest, UserPromptSubmit, Stop, y además SessionEnd, Interrupt, PreCompact, PostCompact, SubagentStart, SubagentStop [FORMATO.md de Codex §3, 2026-10-07] | **Sí, pero falla abierto**: PreToolUse puede denegar (JSON `permissionDecision: "deny"` con salida 0, o salida 2 **con texto en stderr**) o reescribir; PermissionRequest permite/deniega. **No bloquean**: salida 2 sin stderr, otro código, JSON inválido o tiempo agotado. No cubre herramientas alojadas como `WebSearch`: es «guardrail, no barrera» [FORMATO.md de Codex §3, 2026-10-07] | sí |
| GE | Sección de hooks de `settings.json` (`.gemini/settings.json`, `~/.gemini/settings.json`, `/etc/gemini-cli/settings.json`, extensiones) [GE:hooks]. `matcher` de herramientas MCP: `mcp_<servidor>_<herramienta>`. «Trusted Folders» está **desactivado por defecto**; si se activa, en una carpeta no confiable se ignora el `.gemini/settings.json` del proyecto, incluidos sus hooks [FORMATO.md de Gemini §3, 2026-10-07] | 11 eventos: SessionStart/End, BeforeAgent, AfterAgent, BeforeModel, AfterModel, BeforeToolSelection, **BeforeTool**, AfterTool, PreCompress, Notification | **Sí, pero falla abierto**: salida 2 o JSON `{"decision":"deny"}` en BeforeTool; la salida 2 detiene **solo la herramienta y el turno continúa**; salida 2 y JSON `deny` conviven (la documentación prefiere JSON con salida 0). Otro código o texto no JSON en stdout equivale a permitir [FORMATO.md de Gemini §3, 2026-10-07] | sí |
| WS | **Dos agentes con archivos distintos; los de uno no los lee el otro.** Cascade: `.devin/hooks.json` (proyecto), `~/.codeium/windsurf/hooks.json` (usuario), `/etc/devin/hooks.json` (sistema) [WS:hooks]. Devin Local: `.devin/hooks.v1.json`, o la clave `hooks` en `.devin/config.json` y `~/.config/devin/config.json`; migración con `devin migrate hooks` [FORMATO.md de Windsurf §3, 2026-10-07] | Cascade (12 eventos): previos `pre_read_code`, `pre_write_code`, `pre_run_command`, `pre_mcp_tool_use`, `pre_user_prompt`; posteriores informativos. Devin Local: `PreToolUse`, `PostToolUse`, `PermissionRequest`, `UserPromptSubmit`, `Stop`, `PostCompaction`, `SessionStart`, `SessionEnd` [FORMATO.md de Windsurf §3, 2026-10-07] | **Sí, pero ambos fallan abiertos** (solo la salida 2 bloquea). Cascade: solo los `pre_*` bloquean, con salida 2. Devin Local: salida 2 o JSON `{"decision":"block"}` [FORMATO.md de Windsurf §3, 2026-10-07] | sí |
| AI | No aparecen hooks del agente. Existen `--lint-cmd`, `--test-cmd` y `--git-commit-verify` (ejecuta los hooks de **git** al confirmar; desactivado por defecto) [AI:options] | n/a | No verificado como mecanismo de bloqueo previo a una acción | no verificado |
| CP | **Tres superficies que comparten archivos pero no comportamiento.** (a) VS Code, agente Local (Preview): `.github/hooks/*.json`, `~/.copilot/hooks/*.json`, `hooks` en `.agent.md`, PascalCase, sin `version`. (b) Agent Host y (c) CLI: `version: 1`, `bash`/`powershell`/`timeoutSec`, nombres camelCase; políticas, `.github/hooks/*.json`, `~/.copilot/hooks/*.json`, plugins [CP:hooks; FORMATO.md de Copilot §3, 2026-10-07] | Local: SessionStart, UserPromptSubmit, **PreToolUse**, PostToolUse, PreCompact, SubagentStart/Stop, Stop. CLI/Agent Host: `sessionStart`, `preToolUse`, `postToolUse`, `permissionRequest`, `subagentStart/Stop`, `preCompact` y otros [FORMATO.md de Copilot §3, 2026-10-07] | **Sí, con comportamiento distinto por superficie.** Local (Preview): `permissionDecision: "deny"` o salida 2; **`matcher` se ignora** y falla abierto (otro código solo avisa). CLI/Agent Host: `preToolUse` **falla cerrado** ante errores (incluso salida distinta de cero), pero **el tiempo agotado siempre deja pasar** [FORMATO.md de Copilot §3, 2026-10-07] | parcial (Preview) |
| CL | La página de hooks solo remite a «SDK Plugins» | no verificado | no verificado | no verificado |

## 4. Subagentes o agentes en paralelo

| Agente | Definición | Paralelo | Estado |
|---|---|---|---|
| CC | `.claude/agents/*.md` (frontmatter: name, description, tools, model, permissionMode, hooks, mcpServers, isolation: worktree...), `~/.claude/agents/`, `--agents` JSON, plugins [CC:sub-agents] | Sí; 20 simultáneos por defecto, 3 niveles de anidación | sí |
| OC | `.opencode/agents/*.md` o `~/.config/opencode/agents/`, o clave `agent` en `opencode.json`; `mode: primary/subagent` [OC:agents] | Parcialmente confirmado: el agente integrado `general` es para «run multiple units of work in parallel»; tope de concurrencia: sin confirmar [FORMATO.md de OpenCode §9, 2026-10-07] | sí (paralelo: parcial) |
| CU | `.cursor/agents/`, `.claude/agents/`, `.codex/agents/` (y de usuario) [CU:subagents] | Sí (varias llamadas Task a la vez); `is_background` | sí |
| CX | `.codex/agents/*.toml` o `~/.codex/agents/` (name, description, developer_instructions) [CX:subagents] | Sí; `max_concurrent_threads_per_session` | sí |
| GE | `.gemini/agents/*.md` o `~/.gemini/agents/` [GE:subagents] | La documentación no lo aclara; los subagentes **no pueden llamar a otros** | parcial |
| WS | **Cascade: no tiene subagentes**; solo varias conversaciones en paralelo (conflictos si editan el mismo archivo) [WS:cascade]. **Devin Local sí**: `.devin/agents/<n>.md` (o `<n>/AGENT.md`) con `allowed-tools`; sin anidamiento salvo `max-nesting`; concurrencia: sin confirmar [FORMATO.md de Windsurf §9, 2026-10-07] | parcial | parcial |
| AI | Modo `/architect` (modelo arquitecto + editor) [AI:commands]; subagentes: no verificado | no verificado | no verificado |
| CP | **VS Code**: `.github/agents/*.agent.md` o `.claude/agents`, `~/.copilot/agents`; `agents:` en la cabecera, herramienta `runSubagent`, sin anidamiento por defecto (profundidad máxima 5). **CLI**: `.github/agents/`, `~/.copilot/agents/`, agentes integrados y `--fleet` para subagentes en paralelo [CP:custom-agents; FORMATO.md de Copilot §9, 2026-10-07] | Confirmado en la CLI (`--fleet`, `explore` es seguro en paralelo); en VS Code el paralelismo sigue sin confirmar | sí (paralelo en VS Code: no verificado) |
| CL | no verificado | no verificado | no verificado |

## 5. Comandos personalizados, slash commands, plantillas de prompt

| Agente | Mecanismo | Estado |
|---|---|---|
| CC | `.claude/commands/*.md` (heredado) o skills (`/nombre`); ambos crean `/nombre` [CC:skills] | sí |
| OC | `.opencode/commands/*.md` o `~/.config/opencode/commands/`, o `command` en `opencode.json`; frontmatter description, agent, model, subtask [OC:commands] | sí |
| CU | **No documentado hoy como ruta independiente** (`.cursor/commands/` no aparece en la documentación actual). Solo `commands/` dentro de un plugin (`.md`, `.mdc`, `.markdown`, `.txt`; frontmatter `name` y `description`). Sustituto: skills con `disable-model-invocation: true`, que se invocan con `/nombre` [CU:plugins, CU:skills; FORMATO.md de Cursor §4, 2026-10-07] | parcial |
| CX | Comandos `/` integrados; custom prompts `~/.codex/prompts/*.md` invocados como `/prompts:<nombre>`, **obsoletos** y solo de usuario (no hay ruta de proyecto): usar skills (`$nombre`) [CX:developer-commands; FORMATO.md de Codex §4, 2026-10-07] | parcial (custom prompts obsoletos; usar skills) |
| GE | `.gemini/commands/**/*.toml` o `~/.gemini/commands/`; `prompt` obligatorio, `{{args}}`, `!{shell}`, `@{archivo}`; espacio de nombres por subcarpeta (`/git:commit`) [GE:custom-commands] | sí |
| WS | **Solo Cascade**: workflows `.devin/workflows/*.md` (o `.windsurf/workflows/`), global `~/.codeium/windsurf/global_workflows/`; solo manuales; 12 000 caracteres [WS:workflows]. **Devin Local no soporta workflows**: se migran a skills (`devin migrate workflows`) [FORMATO.md de Windsurf §4, 2026-10-07] | parcial (solo en Cascade) |
| AI | Solo comandos `/` integrados (`/add`, `/ask`, `/run`, `/test`...) [AI:commands]; personalizados: no verificado | no verificado |
| CP | `.github/prompts/*.prompt.md` (workspace o perfil), se invocan con `/nombre`; **deprecados** para sesiones de «Agent Host» (no los carga): migrar a skills. Los `.prompt.md` solo siguen funcionando en el agente Local, que se retirará [CP:prompt-files; FORMATO.md de Copilot §4, 2026-10-07] | sí (con aviso) |
| CL | no verificado | no verificado |

## 6. Skills (paquetes de conocimiento bajo demanda, `SKILL.md`)

| Agente | Ubicaciones | Carga | Estado |
|---|---|---|---|
| CC | `~/.claude/skills/<n>/SKILL.md`, `.claude/skills/<n>/`, plugins, gestionadas; frontmatter `name`, `description`, `disable-model-invocation`, `allowed-tools`, `context: fork`... [CC:skills] | Descripción siempre en contexto; contenido al usarla; SKILL.md recomendado menos de 500 líneas | sí |
| OC | `.opencode/skills/`, `~/.config/opencode/skills/`, también `.claude/skills/` y `.agents/skills/` (y equivalentes en `~`) [OC:skills] | Bajo demanda mediante una herramienta nativa. Campos reconocidos: `name`, `description`, `license`, `compatibility`, `metadata`; `name` 1-64 caracteres con regex `^[a-z0-9]+(-[a-z0-9]+)*$` y debe coincidir con el directorio; `description` hasta 1024 [FORMATO.md de OpenCode §5, 2026-10-07] | sí |
| CU | `.cursor/skills/`, `.agents/skills/`, `~/.cursor/skills/`, `~/.agents/skills/`; `paths` opcional [CU:skills] | Carga progresiva | sí |
| CX | `.agents/skills` (se escanea en cada directorio desde el actual hasta la raíz del repositorio), `~/.agents/skills`, `/etc/codex/skills` [CX:build-skills] | Solo nombre y descripción hasta elegirla; tope de la lista: hasta el 2 % de la ventana de contexto, u 8 000 caracteres si la ventana es desconocida; `$nombre` o implícito [FORMATO.md de Codex §5, 2026-10-07] | sí |
| GE | `.gemini/skills/` o `.agents/skills/`, `~/.gemini/skills/` o `~/.agents/skills/`, extensiones [GE:skills] | Herramienta `activate_skill` con aprobación | sí |
| WS | `.devin/skills/<n>/`, `~/.codeium/windsurf/skills/` o `~/.config/devin/skills/` [WS:skills] | Carga progresiva; `@nombre` | sí |
| AI | No aparece | | no verificado |
| CP | `.github/skills/`, `.claude/skills/`, `.agents/skills/`, `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/` [CP:agent-skills] | Carga progresiva; el nombre debe igualar la carpeta | sí |
| CL | no verificado | | no verificado |

Observación: el formato `SKILL.md` con frontmatter `name` y `description` aparece en 7 de 8 agentes principales y varios leen `.claude/skills/` o `.agents/skills/`.

## 7. MCP

| Agente | Dónde y cómo se registra | Estado |
|---|---|---|
| CC | `claude mcp add` (alcances local/proyecto/usuario), `.mcp.json` en la raíz (`mcpServers`), `~/.claude.json`; transportes http, stdio, sse (obsoleto) [CC:mcp] | sí |
| OC | Clave `mcp` en `opencode.json`; `type: local` (`command` como arreglo) o `remote` (`url`, `headers`, `oauth`) [OC:mcp-servers] | sí |
| CU | `.cursor/mcp.json` o `~/.cursor/mcp.json` (`mcpServers`; `${env:NAME}`) [CU:mcp]. La tabla de la página marca `type: "stdio"` como obligatorio pero los ejemplos oficiales lo omiten: **generar sin `type`** [FORMATO.md de Cursor §6, 2026-10-07] | sí |
| CX | `[mcp_servers.<nombre>]` en `~/.codex/config.toml` o `.codex/config.toml` (proyectos de confianza); `codex mcp add` [CX:mcp] | sí |
| GE | `mcpServers` en `.gemini/settings.json` o `~/.gemini/settings.json`; `gemini mcp add` [GE:mcp-server] | sí |
| WS | Cascade: `~/.config/devin/mcp_config.json` (`mcpServers`; `${env:VAR}`) [WS:mcp]. Devin Local: además `.devin/mcp_config.json` (proyecto) y `.devin/mcp_config.local.json` (local, ignorado) [FORMATO.md de Windsurf §6, 2026-10-07]. La ruta antigua de Windsurf sigue sin confirmar | sí |
| AI | No se encontró en la documentación oficial leída ni en la búsqueda dentro de aider.chat | no verificado |
| CP | `.vscode/mcp.json` (objeto `servers`), `.mcp.json`, `~/.copilot/mcp-config.json`, perfil de usuario [CP:mcp-servers]. Diferencia de esquema: el tipo local es `stdio` en VS Code y `local` en la CLI [FORMATO.md de Copilot §6, 2026-10-07] | sí |
| CL | no verificado | no verificado |

## 8. Memoria entre sesiones

| Agente | Mecanismo | Estado |
|---|---|---|
| CC | Memoria automática que Claude escribe (primeras 200 líneas o 25 KB al iniciar), por repositorio; `memory:` en subagentes [CC:memory, CC:sub-agents] | sí |
| OC | Las sesiones se continúan (`--continue`, `--session`); memoria entre sesiones: no se menciona [OC:cli] | no verificado |
| CU | No verificado (la página de reglas indica que el modelo no retiene memoria entre completados y ofrece reglas como contexto persistente) | no verificado |
| CX | Bandera experimental `[features] memories = true` en `config.toml`; su funcionamiento no se leyó [CX:config-basic] | parcial |
| GE | El agente guarda hechos en archivos Markdown de memoria; `/memory show`, `/memory reload` [GE:memory-management] | sí |
| WS | «Memories» generadas automáticamente; la documentación recomienda reglas o `AGENTS.md` para lo importante [WS:memories] | sí |
| AI | No verificado | no verificado |
| CP | No verificado | no verificado |
| CL | No verificado | no verificado |

## 9. Permisos y modos (lista de comandos, solo lectura/plan, sandbox)

| Agente | Permisos | Modo solo lectura / plan | Sandbox | Estado |
|---|---|---|---|---|
| CC | `permissions.allow/deny/ask` en settings con reglas como `Bash(git diff *)` [CC:permissions] | Modos: manual, `acceptEdits`, `plan`, `auto`, `dontAsk` (`plan` confirmado en subagentes; lista completa en la página de modos, no leída) | Sandbox de Bash por el sistema operativo en macOS, Linux y WSL2 (no en Windows nativo); **no cubre** herramientas de archivos, MCP ni hooks [CC:sandboxing] | sí |
| OC | `permission` con `allow/ask/deny` por herramienta y patrón; gana la última regla coincidente; `.env` denegado por defecto [OC:permissions] | Agente primario `Plan` (editar y bash en «ask») [OC:agents] | No mencionado | parcial |
| CU | CLI: `allow`/`deny` con `Shell()`, `Read()`, `Write()`, `WebFetch()`, `Mcp()` en `~/.cursor/cli-config.json` o `.cursor/cli.json`; denegar prevalece; en el JSON de la CLI `approvalMode` acepta `allowlist`, `auto-review` o `unrestricted`. El `permissions.json` del IDE solo tiene instrucciones en lenguaje natural (`autoRun.allow_instructions` / `block_instructions`), no una lista determinista, y Auto-review no es un límite de seguridad [CU:cli/reference/permissions; FORMATO.md de Cursor §7, 2026-10-07] | Modo Plan (Shift+Tab); modo solo lectura de subagentes `readonly` | `sandbox.json` en el terminal del agente [CU:agent/terminal] | sí |
| CX | `approval_policy` (p. ej. `on-request`, `never`) en `config.toml`; `approval_policy = "untrusted"` está **retirado**. Reglas de ejecución en archivos `.rules` (Starlark) con decisiones `allow`, `prompt`, `forbidden` (`--ignore-rules` las omite) [CX:config-basic, CX:non-interactive-mode; FORMATO.md de Codex §7, 2026-10-07] | Sandbox `read-only` es el predeterminado de `codex exec` | `read-only`, `workspace-write`, `danger-full-access`; en `workspace-write`, `.codex` y `.agents` (y `.git`) son de solo lectura [FORMATO.md de Codex §7, 2026-10-07] | sí |
| GE | Motor de políticas: `~/.gemini/policies/*.toml` y administrador; decisiones `allow/deny/ask_user` con `commandPrefix`/`commandRegex`. **El nivel de espacio de trabajo sigue figurando como no funcional en `main`**; `ask_user` en modo no interactivo equivale a `deny`; la tabla de niveles 1–5 no coincide con los ejemplos de la fórmula (no depender de números absolutos); en reglas `modes` se escribe `autoEdit`, en la línea de órdenes `auto_edit` [GE:policy-engine; FORMATO.md de Gemini §7, 2026-10-07] | `--approval-mode=plan`, `/plan` [GE:plan-mode] | Seatbelt (macOS), sandbox nativo (Windows), gVisor/LXC/Docker/Podman (Linux), `-s` o `tools.sandbox` [GE:sandbox] | sí |
| WS | **Cascade**: niveles `Disabled`, `Allowlist Only`, `Auto`, `Turbo` y listas con comodín; **una entrada denegada solo exige aprobación, no bloquea**. **Devin Local**: clave `permissions` (`allow`/`ask`/`deny`) donde **deny gana siempre**. `.devinignore` es el nombre vigente (`.windsurfignore` y `.codeiumignore` son heredados) [FORMATO.md de Windsurf §7, 2026-10-07] | Modo Chat/Ask (solo lectura) frente a Code; Plan | Devin Local: `--sandbox` (bubblewrap en Linux, seatbelt en macOS, **no soportado en Windows**); Cascade: no documentado [FORMATO.md de Windsurf §7, 2026-10-07] | sí |
| AI | `--yes-always` (confirma todo); sin lista de comandos | Modo `/ask` consulta sin editar [AI:commands]; `--dry-run` [AI:scripting] | No verificado | parcial |
| CP | **VS Code**: `chat.tools.terminal.autoApprove` y aprobaciones por herramienta; una regla `false` **exige aprobación y no bloquea** (la fuente indica usar un hook). **CLI**: `--allow-tool` / `--deny-tool` con patrón `Kind(arg)`; **deny gana incluso con `--allow-all`**; `--allow-all-tools` es peligroso [CP:agent-tools, CP:about-copilot-cli; FORMATO.md de Copilot §7, 2026-10-07] | Sección «Plan» en el agente; CLI `--plan` | Sandbox de Agent Host con **red abierta por defecto** (`allowNetwork = true`); sandbox de servidores MCP en macOS/Linux [FORMATO.md de Copilot §7, 2026-10-07] | parcial |
| CL | No verificado | No verificado | No verificado | no verificado |

## 10. Ejecución no interactiva (CI)

| Agente | Comando | Salida estructurada | Estado |
|---|---|---|---|
| CC | `claude -p "..."`; `--bare` omite hooks/skills/MCP/CLAUDE.md descubiertos (recomendado en CI); `--allowedTools`, `--permission-mode`; **sin `--bare`, `-p` ejecuta los hooks y MCP del `.claude/settings.json` y `.mcp.json` del repositorio sin diálogo de confianza** [CC:headless] | `--output-format json / stream-json`, `--json-schema` | sí |
| OC | `opencode run "..."`; `--auto` y `--format json` confirmados; `opencode serve` + `--attach` [OC:cli]. Códigos de salida y comportamiento ante `ask` sin `--auto`: no documentados [FORMATO.md de OpenCode §8, 2026-10-07] | JSON de eventos | sí |
| CU | `agent -p` / `--print`; `--force` para editar; `CURSOR_API_KEY` [CU:cli/headless] | `text`, `stream-json` | sí |
| CX | `codex exec "..."`; `--sandbox`, `--json`, `--output-schema`, `-o`; `CODEX_API_KEY`; acción `openai/codex-action` [CX:non-interactive-mode] | JSON Lines | sí |
| GE | `gemini -p` o entrada sin TTY; códigos de salida 0, 1, 42, 53 [GE:headless] | `--output-format json / stream-json` | sí |
| WS | **El IDE no tiene modo no interactivo documentado.** La CLI sí: `devin -p` / `--print`, con `--respect-workspace-trust false` para CI en un directorio que no lo pide; códigos de salida y ejecución de hooks en `-p`: no confirmados [FORMATO.md de Windsurf §8, 2026-10-07] | no verificado | parcial (solo la CLI) |
| AI | `aider --message "..."` (`-m`), `--message-file`, `--yes`; API de Python sin documentación oficial estable [AI:scripting] | no verificado | sí |
| CP | Copilot CLI: `copilot -p "..." -s --allow-tool=... --no-ask-user` (patrón confirmado; producto distinto de la extensión de VS Code, que no tiene modo no interactivo documentado). Códigos de salida de `-p`: no confirmados [CP:about-copilot-cli; FORMATO.md de Copilot §8, 2026-10-07] | `--output-format json` (JSONL) | parcial |
| CL | No verificado | no verificado | no verificado |

## 11. Plugins o empaquetado de configuración

| Agente | Mecanismo | Estado |
|---|---|---|
| CC | Plugin = directorio con `.claude-plugin/plugin.json` + skills, agentes, hooks (`hooks/hooks.json`), `.mcp.json`; mercados (`marketplace.json`), alcances usuario/proyecto/local [CC:plugins] | sí |
| OC | Plugins JS/TS locales o npm (`"plugin"` en config, `opencode plugin <módulo>`) [OC:plugins, OC:cli]; empaquetan código de hooks; el empaquetado de skills/comandos: no verificado | parcial |
| CU | Dos formatos: `plugin.json` en la raíz (estándar «Agent Plugins») y `.cursor-plugin/plugin.json`; contienen reglas, skills, agentes, comandos, MCP, hooks; mercado propio [CU:plugins] | sí |
| CX | Existe el comando `codex plugin` y plugins con `hooks/hooks.json`; la documentación recomienda empaquetar skills como plugins [CX:developer-commands, CX:hooks, CX:build-skills]; estructura exacta no leída | parcial |
| GE | Extensiones (`gemini extensions install <repo>`): prompts, MCP, comandos, temas, hooks, subagentes y skills; manifiesto `gemini-extension.json` (en otra página, no leída) [GE:extensions] | sí |
| WS | No verificado | no verificado |
| AI | No verificado | no verificado |
| CP | Agent plugins con `plugin.json` (esquema `agent-plugins.org`): skills, MCP, agentes, hooks, comandos; mercados `chat.plugins.marketplaces` [CP:agent-plugins] | sí |
| CL | No verificado | no verificado |

## Resumen visual (estado por capacidad)

Leyenda: S sí, P parcial, N no verificado.

| Capacidad | CC | OC | CU | CX | GE | WS | AI | CP | CL |
|---|---|---|---|---|---|---|---|---|---|
| 1 Instrucciones del proyecto | S | S | S | S | P | S | P | S | S |
| 2 Reglas por ruta | S | N | S | P | P | S | N | S | S |
| 3 Hooks que bloquean | S | S | S | S | S | S | N | P | N |
| 4 Subagentes / paralelo | S | S | S | S | P | P | N | S | N |
| 5 Comandos propios | S | S | P | P | S | P | N | S | N |
| 6 Skills | S | S | S | S | S | S | N | S | N |
| 7 MCP | S | S | S | S | S | S | N | S | N |
| 8 Memoria entre sesiones | S | N | N | P | S | S | N | N | N |
| 9 Permisos / modos / sandbox | S | P | S | S | S | P | P | P | N |
| 10 No interactivo | S | S | S | S | S | P | S | P | N |
| 11 Plugins | S | P | S | P | S | N | N | S | N |

## Mínimo común

Capacidades confirmadas en **todos** los agentes principales de la lista (CC, OC, CU, CX, GE, WS, AI, CP):

1. **Un archivo de instrucciones en Markdown que el agente lee** (nombre y descubrimiento distintos; en Aider hay que pasarlo explícitamente con `--read`). El punto de encuentro es **`AGENTS.md`**: lo leen sin configuración OC, CU, CX, WS, CP (y CL); CX no lee `CLAUDE.md` ni `GEMINI.md` salvo que se listen en `project_doc_fallback_filenames`; CC lo lee solo si no existe `CLAUDE.md` (o se importa); GE solo si se configura `context.fileName`; Aider: no verificado.
2. **Ejecución de comandos en la terminal** (herramientas de shell del agente; en Aider mediante `/run` y `/test`).

Confirmadas en **todos menos Aider** (y Cline, mayormente «no verificado»): hooks previos que pueden denegar (CP en Preview; en Codex, Gemini y Windsurf el hook **falla abierto** y en Copilot depende de la superficie, ver abajo), skills con `SKILL.md`, MCP, subagentes o variantes. Los formatos de hooks, reglas y comandos **no son intercambiables** (cada agente usa su propio archivo y esquema JSON o TOML), y lo único portable de verdad es: texto Markdown, `AGENTS.md` y el formato `SKILL.md`.

Consecuencia para los adaptadores: un adaptador mínimo solo puede suponer «archivo de instrucciones + terminal». Todo lo demás se declara por agente y, si falta, el estado es «degradado».

## Qué se pierde sin hooks

Agentes sin hook bloqueante confirmado: **Aider** (no verificado en la documentación leída) y **Cline** (no verificado). Además, donde sí hay hooks conviene no depender solo de ellos:

- Copilot: los hooks están en **Preview** en VS Code. Local ignora `matcher` y falla abierto; CLI y Agent Host fallan cerrados ante errores pero **el tiempo agotado siempre deja pasar**; una regla `autoApprove: false` solo exige aprobación [FORMATO.md de Copilot §3, §7, 2026-10-07].
- Codex: `PreToolUse` falla abierto (salida 2 sin stderr, otro código, JSON inválido o tiempo agotado no bloquean), no cubre herramientas alojadas como `WebSearch` y es «guardrail, no barrera»; un hook nuevo o modificado no corre hasta confiar en él con `/hooks`; la vía `requirements.toml` con `allow_managed_hooks_only` lo vuelve obligatorio [FORMATO.md de Codex §3, 2026-10-07].
- Cursor: ante un fallo del script (código distinto de 0 y 2, tiempo agotado, sin salida) la acción **pasa** salvo `failClosed: true`; con salida 0 y JSON inválido o fuera de esquema un hook de permiso **bloquea**. `preToolUse` no aplica `ask` y `subagentStart` lo trata como `deny`. Qué eventos corren en `agent -p` y en agentes en la nube no está confirmado [FORMATO.md de Cursor §3].
- Gemini: el hook falla abierto (otro código distinto de 0 y 2, o texto no JSON en stdout, permite); la salida 2 detiene solo la herramienta y el turno continúa. El nivel de políticas de espacio de trabajo figura como no funcional en `main`. «Trusted Folders» está desactivado por defecto; si se activa, una carpeta no confiable ignora el `.gemini/settings.json` del proyecto y con él sus hooks [FORMATO.md de Gemini §3, §7, 2026-10-07].
- Claude Code: el sandbox no cubre herramientas de archivos, MCP ni hooks; con `-p` sin `--bare` se ejecutan los hooks del repositorio sin diálogo de confianza. Un hook solo vigila las acciones que el agente hace por sus herramientas, no lo que ocurra fuera del agente.
- OpenCode: el hook es un plugin que bloquea lanzando una excepción (no hay códigos de salida ni `ask`); su cobertura de MCP, recursos MCP y `task` está confirmada solo en el código de `dev`, y que un plugin que falla bloquee también (no está en la documentación); `permission.asked` no está documentado como vía para denegar [FORMATO.md de OpenCode §3].
- Windsurf: son dos agentes con hooks distintos (Cascade y Devin Local) y **ambos fallan abiertos** (solo la salida 2 bloquea); en Cascade, la lista de comandos denegados solo exige aprobación; qué vías de edición pasan por el hook no está confirmado [FORMATO.md de Windsurf §3, §7, 2026-10-07].

Capas independientes del agente recomendadas, de la más fuerte a la más débil, y por qué:

| Restricción que se quería imponer | Capa independiente del agente | Por qué sirve |
|---|---|---|
| Que el agente no lea ni escriba datos que no debe | **Permisos de la base de datos**: un usuario/rol de solo lectura (o sin acceso a las tablas sensibles) por persona o ambiente, y credenciales de producción fuera del alcance del agente | La imposición ocurre en el servidor de datos: da igual qué agente, qué comando o qué script use la credencial. Es la única capa que sigue en pie si el agente ignora una instrucción |
| Que no se suba código a ramas protegidas ni se reescriba su historia | **Protección de ramas** en el alojamiento remoto (revisión obligatoria, sin push directo, sin force-push) | La plataforma rechaza la operación sin importar quién la ejecute; un agente sin hooks no puede saltarla |
| Que no se confirme código que viola el estándar | **Hooks de git** (`pre-commit`, `pre-push`, `commit-msg`) que corran el gate del harness | Funcionan igual con cualquier agente y con personas. Limitación: se pueden saltar con `--no-verify`, y en Aider los hooks de git solo corren con `--git-commit-verify`; por eso no bastan solos |
| Que ningún cambio llegue a la rama principal sin pasar las verificaciones | **Integración continua** obligatoria (estado requerido en la protección de ramas) ejecutando el mismo gate | Es la verificación que no se puede omitir desde el equipo local; da el mismo resultado sin agente |
| Que el agente no ejecute comandos destructivos o salga del proyecto | **Aislamiento del entorno**: contenedor o máquina virtual de desarrollo, usuario del sistema sin privilegios, credenciales de nube de solo lectura | El límite lo aplica el sistema operativo, no el agente |
| Que no se filtren secretos | **Escaneo de secretos** en pre-commit y en integración continua | Detecta el resultado, sea cual sea el agente que lo produjo |
| Que el agente respete reglas de estilo y de flujo | Instrucciones en `AGENTS.md` más el gate en integración continua | Las instrucciones guían, no obligan; el gate convierte la instrucción en una verificación |

Principio: el hook del agente es una **capa adicional** de conveniencia (feedback inmediato antes de actuar); la **garantía** debe vivir en capas que el agente no controla (base de datos, plataforma de alojamiento, integración continua, sistema operativo). Ningún hook de ningún agente sustituye al permiso en la base de datos.

## Pendientes de verificación (candidatos a la próxima revisión)

Hooks de Aider y de Cline; MCP y subagentes de Aider; límites de tamaño de instrucciones en OpenCode (no documentado), Cursor (solo recomendación de 500 líneas), Gemini, Windsurf, Copilot y Cline; qué hooks de Cursor corren en `agent -p`; memoria de OpenCode, Cursor, Copilot y Cline; comportamiento de un hook al agotar el tiempo en Gemini, Windsurf y Copilot Local; códigos de salida y hooks en `devin -p` y códigos de salida de `copilot -p`; paralelismo de subagentes de Copilot en VS Code y concurrencia de los de Devin Local; ruta antigua de MCP de Windsurf; plugins de Windsurf, Aider y Cline; páginas de Claude Code más allá de los primeros 100 000 caracteres (hooks, skills, subagentes, MCP) y la página de modos de permiso. Resueltos en la segunda ronda: comandos propios de Codex (obsoletos), lectura de `AGENTS.md` anidados en Windsurf, listas de comandos y sandbox de Windsurf, modo no interactivo de Windsurf (solo CLI).
