# Núcleo de adaptadores de agente

<!-- tipo: herramienta · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: spec §22 (R52-R57) y MATRIZ.md -->

Lo que no depende de ningún agente: la **fuente neutral** de instrucciones, el `AGENTS.md` que se genera de ella y el marco que detecta agentes y llama a un adaptador por agente.

| Archivo | Qué hace |
|---|---|
| `fuente_neutral.py` | Lee la instancia (`politicas.toml`, `convenciones.toml`, `harness.lock`, `.harness/estado.json`, sus carpetas) y arma la estructura neutral: cómo orientarse, cuándo leer qué, reglas duras **tomadas de la política**, comando del gate (o «por definir»), lo que no se debe hacer, herramientas del harness y lo pendiente de declarar. Renderiza `plantillas/AGENTS.md.tpl`. También trae la escritura segura (nunca fuera de la instancia, nunca sobre un archivo escrito a mano). |
| `guardia_hook.py` | Ayuda común de OpenCode y Cursor: reutiliza `instalador/generar-politicas.py` para producir el hook de datos y el puente `guardia-datos.py` (falla cerrado). |
| `capacidades_comunes.py` | Capacidades neutrales (entrega 1 de R53): skills (`plantillas/skills/<nombre>/SKILL.md`), comandos (`plantillas/comandos/*.md`), permisos con **prefijos literales** derivados de la política y servidores MCP declarados en `[[mcp.servidores]]`. Valida y entrega; **no escribe nada**. Los adaptadores aún no las usan (entrega 2). |
| `generar_agentes.py` | CLI y marco: contrato `Adaptador`, registro por nombre, detección, lectura de capacidades desde `MATRIZ.md` e informe. |

## Uso

```
python3 generar_agentes.py <instancia> [--agentes a,b | --detectar] [--aplicar] [--json]
```

- Sin `--aplicar` solo se muestra el plan; no se escribe nada.
- Sin `--agentes` se **detecta** (comando en PATH o carpeta de configuración en `~`, solo se comprueba que existan) y se genera únicamente para los detectados. Con `--agentes` se genera para los nombrados aunque no se detecten. `AGENTS.md` se genera siempre.
- Agente desconocido: error claro (código 2) con la lista de los que tienen adaptador.
- Todo se escribe **dentro de la instancia**. Lo que sería global (`~`, carpetas del agente) se imprime como paso para la persona.

## AGENTS.md generado

- Lleva la marca «generado por el harness: no editar a mano; editar la política o las convenciones y regenerar» y se **regenera**: es idempotente (sin fechas ni datos cambiantes).
- Si ya existe un `AGENTS.md` sin la marca (escrito a mano) **no se toca**: se escribe `AGENTS.generado.md` y se avisa. Lo mismo vale para cualquier otro archivo que genere un adaptador.
- Las reglas duras no se escriben a mano: cambian al cambiar `politicas.toml`. Lo que la política no declara sale en «Pendiente de declarar»; no se completa con suposiciones.

## Contrato de un adaptador

`nombre` · `detectar(sistema)` (inyectable: `SistemaSimulado` para pruebas) · `capacidades()` (sí / parcial / no / no_verificado con su fuente, leídas del «Resumen visual» de `MATRIZ.md`) · `generar(fuente, destino, aplicar=False)` (lista de archivos con acción crear / actualizar / igual / alterno) · `degradaciones()` (qué no soporta y con qué imposición alternativa: rol de solo lectura en la base, hooks de git, integración continua, protección de ramas) · `control_por_hook()` (R55: disponible / degradado / no_disponible).

Para agregar un agente: `adaptadores-agente/<agente>/adaptador.py` con `ADAPTADORES = [Clase]` (subclase de `Adaptador`); el marco lo descubre. Incluidos sin carpeta propia: `aider` y `cline` (solo leen `AGENTS.md`; sin hooks confirmados en la matriz, así que todo su control va por las capas de la degradación).

## Límites

- Las capacidades son las de la matriz del día de su revisión; el informe avisa si la matriz venció. Lo «no verificado» no se promete.
- El control por hook nunca sustituye al permiso en la base de datos (ver «Qué se pierde sin hooks» en `MATRIZ.md`).
- Hay adaptador para Claude Code, OpenCode y Cursor (más Aider y Cline, mínimos); el resto de agentes de la matriz figura como «sin adaptador todavía».
- `fuente_neutral.py` guarda en `AGENTS.md` rutas relativas a la raíz del harness, no absolutas.

Pruebas: `python3 -B -m unittest adaptadores-agente/tests/test_nucleo.py adaptadores-agente/tests/test_claude_code.py adaptadores-agente/tests/test_opencode.py adaptadores-agente/tests/test_cursor.py` (desde la raíz del harness).

## Capacidades neutrales (contrato para los adaptadores)

`fuente_neutral.construir(...)` agrega cuatro claves (las existentes no cambian; si las capacidades no son válidas lanza `ErrorInstancia` con la lista de errores):

| Clave | Forma |
|---|---|
| `skills` | `[{nombre, descripcion, ruta, contenido}]`; `ruta` relativa a la raíz del harness; `nombre` = carpeta y cumple `^[a-z0-9]+(-[a-z0-9]+)*$` |
| `comandos` | `[{nombre, descripcion, ruta, contenido}]` (opcionales por agente) |
| `permisos` | `{deny: [prefijo], ask: [prefijo], allow: [prefijo], origenes: {prefijo: clave_de_politica}, no_traducible: [{origen, regla, motivo}]}` |
| `mcp` | `[{nombre, tipo: "local"\|"remoto", comando, args, url, entorno: [{clave, variable}], registrar}]`; lista vacía si la política no declara servidores |

- Los prefijos son texto literal de comando (`git push`); un regex que no lo sea nunca se aproxima: va a `no_traducible` y lo cubren los hooks u otras capas. `allow` solo se llena con lo que la política permite de forma explícita; nunca se inventa. Si un prefijo está en `deny` y en `ask`, gana `deny`.
- `entorno` guarda solo el **nombre de la variable** (`${VARIABLE}` en la política); un valor con aspecto de secreto es un error y nunca se imprime.
- `AGENTS.md` agrega al final la sección «Capacidades neutrales del harness» (lista skills, comandos, comandos denegados y servidores MCP); lo anterior no cambia y sigue idempotente.
- Validar: `python3 capacidades_comunes.py --validar <instancia> [--json]` (0 bien · 1 errores · 2 instancia no utilizable).
- Límites: la traducción a regex→prefijo cubre solo lo que empieza por el comando (un regex sin ancla que casaba en medio de una línea no se aproxima); el prefijo `ask` de `git commit`/`git push` sale de `git.confirmar`.

Pruebas de esta parte: `python3 -B -m unittest adaptadores-agente/tests/test_capacidades_comunes.py`.
