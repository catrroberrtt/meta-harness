# Usar este entorno con Codex

Los hooks de este repositorio están declarados para Codex en `.codex/hooks.json`. Codex usa el mismo formato de entrada y de respuesta de
bloqueo que Claude Code, así que son los mismos scripts de `hooks/`.

## Lo que tienes que hacer una vez

Un hook nuevo o modificado **no corre hasta que lo confíes**: abre Codex en esta carpeta, ejecuta `/hooks`, revisa cada hook y confíalo. Se registra
por huella: después de cada cambio en un hook (o de regenerar el entorno con cambios), hay que confiarlo de nuevo.

## Lo que cubre y lo que no

| Qué | Estado |
|---|---|
| Hooks de `PreToolUse` sobre `Bash` (compuerta, publicación, datos, formato de PR) | Mismo formato que Claude Code; documentado por Codex |
| Autoguardado al cerrar | Declarado en `SessionEnd`; **no probado** contra Codex real |
| Aviso de «documentación primero» | **No se genera**: el formato de salida de `UserPromptSubmit` en Codex no está confirmado |
| `apply_patch`, herramientas MCP y `write_stdin` | **No vigilados** por estos hooks (solo `Bash`) |

## Importante: Codex falla abierto

Si un hook falla, se agota o no está confiado, **la acción pasa**. Cada script de `hooks/` captura sus propios errores y deniega por sí mismo cuando
encuentra algo prohibido, pero un hook sin confiar o un error del lanzador no bloquea nada. Por eso estos hooks son una capa de aviso y de freno, no una
garantía: la garantía real son los permisos (un usuario de base de datos de solo lectura, ramas protegidas, revisión de PR).

Los scripts localizan la raíz del repositorio por su propia ubicación, no por una variable del agente, así que funcionan lanzados desde cualquier carpeta.
