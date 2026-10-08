# Adaptador de Gemini CLI

<!-- tipo: herramienta · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: gemini/FORMATO.md y MATRIZ.md (Gemini) -->

Genera en la **instancia** (nunca en `~`), solo lo «confirmado con fuente» en `FORMATO.md`:

| Archivo | Contenido |
|---|---|
| `GEMINI.md` | Gemini **no** lee `AGENTS.md` salvo que se configure `context.fileName`; este archivo lo importa con `@./AGENTS.md` (sintaxis documentada). Marca como comentario HTML. No se escribe `context.fileName` para no cargarlo dos veces. |
| `.gemini/settings.json` | `{"hooks": {"BeforeTool": [{matcher: "run_shell_command", hooks: [{name, type, command, timeout (ms), description}]}]}}`. JSON no admite comentarios: la marca va en la clave `_generado_por_el_harness`. |
| `.gemini/hooks/` | `block-db-access.sh` y `filtrar-tramos-de-lectura.py` (los produce `instalador/generar-politicas.py`, que se **reutiliza**), `guardia-datos.py` (puente `--formato gemini`) y `lanzar.sh` (lanzador POSIX que deniega si falta `python3` o el puente). |

## Control por hook: siempre «degradado»

**Gemini falla abierto**: cualquier código de salida distinto de 0 y 2, o un stdout con texto que no es JSON, deja pasar la acción. El script deniega él mismo ante cualquier error propio con `{"decision":"deny","reason":...}` y **salida 0** (la forma que prefiere la documentación; nada más en stdout, el diagnóstico va a stderr). Aun así el adaptador informa «degradado» y lo trata como capa de aviso. Si la política no declara ambientes, no se escribe `settings.json` ni hooks y el control queda «degradado» con el motivo (`GEMINI.md` sí se genera).

## Pasos para la persona

- Revisa el hook con `/hooks panel`: los hooks de proyecto se registran por huella (nombre y comando); si cambian, se tratan como nuevos y no confiables hasta aprobarlos.
- **Carpetas de confianza** (desactivadas por defecto): si las activas (`security.folderTrust.enabled`), en una carpeta no confiable Gemini ignora el `.gemini/settings.json` del proyecto y con él el hook, sin avisar. No dependas de ello para proteger nada.
- Barrera que no depende del script: reglas `deny` en `~/.gemini/policies/*.toml` (nivel usuario) o `/etc/gemini-cli/policies` (administrador). El nivel de proyecto está documentado como no funcional. El adaptador **imprime** un ejemplo; no escribe fuera de la instancia.

## Qué no cubre

El hook solo vigila `run_shell_command` (la política de datos juzga comandos de terminal; herramientas de archivo y MCP quedan fuera). `ask` no se admite en `BeforeTool` (se deniega). Qué hace Gemini cuando se agota el `timeout` no está confirmado. No genera comandos, skills, MCP ni subagentes (la fuente neutral aún no los produce). La clave de marca en `settings.json` no está confirmada como admitida: si Gemini la rechaza, quítala. Un `settings.json` escrito a mano no se pisa: el hook queda en `.gemini/settings.generado.json`.

## Reglas

Si ya existe un archivo escrito a mano (sin marca) se escribe `<nombre>.generado.<ext>` al lado y se avisa; es idempotente; todo queda dentro de la instancia. Requiere `sh`, `python3`, `bash`, `jq` y `git` en el PATH.

Pruebas: `python3 -B -m unittest adaptadores-agente/tests/test_gemini.py`.
