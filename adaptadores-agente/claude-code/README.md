# Adaptador de Claude Code

<!-- tipo: herramienta · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: MATRIZ.md (Claude Code) -->

Genera en la **instancia** (nunca en `~`):

| Archivo | Contenido |
|---|---|
| `CLAUDE.md` | Marca del harness y la línea `@AGENTS.md` (importación). |
| `.claude/hooks/*.sh` y `.py` | Los hooks que produce `instalador/generar-politicas.py` desde `politicas.toml` (se **reutiliza** ese generador; aquí no hay lógica de política). |
| `.claude/settings.ejemplo.json` | Bloque `hooks` de ejemplo (`PreToolUse`, `matcher` `Bash`, tipo `command`) para el `.claude/settings.json` de proyecto. **No** es `settings.json`: la persona lo revisa y copia la clave `hooks`. |

## Cómo se importa AGENTS.md (verificado y no verificado)

- **Verificado en `MATRIZ.md` §1:** Claude Code lee `CLAUDE.md`; solo lee `AGENTS.md` si no hay `CLAUDE.md`; con ambos lee únicamente `CLAUDE.md` y **se puede importar con `@AGENTS.md`** (importaciones `@ruta`, hasta 4 niveles). Por eso el `CLAUDE.md` generado solo contiene esa referencia.
- Si ya existe un `CLAUDE.md` escrito a mano, no se toca: se escribe `CLAUDE.generado.md` y se avisa. Si el `AGENTS.md` es el manual, la importación apunta a `AGENTS.generado.md`.
- **No verificado en la matriz:** la forma exacta de la ruta del comando en el hook (el ejemplo usa una ruta relativa a la raíz del proyecto, `.claude/hooks/block-db-access.sh`). La matriz advierte que nombres y rutas deben contrastarse con la documentación oficial antes de confiar en ellos: hazlo antes de registrar el hook.

## Control por hook (R55)

- **disponible**: la matriz confirma hooks que bloquean (§3: `PreToolUse` con código de salida 2 o `permissionDecision: "deny"`) **y** la política permite generar el hook. Aun así, el hook solo vigila lo que el agente hace por sus herramientas y solo actúa después de que la persona lo registra.
- **degradado**: la política todavía no permite generarlo (por ejemplo, sin `[[datos.ambientes]]` ni `alcance.repos`). El informe dice qué falta y no se escribe nada de `.claude/`.
- Las degradaciones propias de Claude Code (sandbox que no cubre herramientas de archivos, MCP ni hooks; `-p` sin `--bare` ejecuta hooks del repositorio sin diálogo de confianza) salen del informe con su imposición alternativa.

## Qué no hace

No instala nada, no escribe `~/.claude`, no registra hooks, no toca la red. Para lo global imprime el paso para la persona.
