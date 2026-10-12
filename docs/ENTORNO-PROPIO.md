# Entorno propio: un repositorio independiente generado por el harness

<!-- tipo: guia · capa: 4 -->
<!-- revisado: 2026-10-12 · vence: 90d · fuente: herramientas/harness-entorno.py y sus pruebas (herramientas/tests/test_entorno.py); cada mecanismo se ejecutó -->

El harness central guarda el método. Un **entorno propio** es lo que una persona o un equipo usa cada día: reglas para el
agente, hooks, compuerta, autoguardado y aprendizaje. Se genera **una vez** y desde ese momento **vive solo**: quien lo
clona no instala ni necesita el meta-harness.

```
harness entorno --listar
harness entorno --nombre mi-entorno --destino ~/mi-entorno \
        --modulos documentacion-primero,compuerta-calidad,autoguardado,aprendizaje \
        --agentes claude,codex [--perfiles nestjs-typeorm-mysql] [--aplicar]
```

Sin `--aplicar` solo muestra el plan. Escribe únicamente en `--destino`, que debe no existir o estar vacío y no puede estar
dentro del harness.

## Módulos

| Módulo | Qué deja en el entorno | Cómo se activa |
|---|---|---|
| `documentacion-primero` | Buscador `scripts/buscar-documentacion.py` y un aviso cuando se pide analizar o evaluar | Hook `UserPromptSubmit` |
| `compuerta-calidad` | `scripts/gate.sh` (tus comandos + secretos) y aviso, o bloqueo opcional, antes de `git commit` | Hook `PreToolUse` |
| `conocimiento` | `knowledge/INDICE.md` y `scripts/frescura.py` (documentos vencidos) | A demanda |
| `escaneo-secretos` | `scripts/escanear-secretos.py` (claves, tokens, credenciales en lo versionado) | A demanda y desde la compuerta |
| `autoguardado` | Commit al cerrar la sesión; la **subida está apagada por defecto** | Hook `Stop` |
| `publicar-solo-verificado` | Motor que comprueba un texto contra sus fuentes y deja una marca atada a su contenido; el hook impide publicarlo sin ella | Hook `PreToolUse` |
| `bloqueo-datos` | Impide que el agente escriba en bases de datos o se conecte a ambientes no locales (barrera; la garantía real es un usuario de solo lectura) | Hook `PreToolUse` |
| `formato-de-pr` | Un PR no se crea sin las secciones que exige su tipo, según los tipos que declares | Hook `PreToolUse` |
| `inventario-de-fuentes` | Foto de tus repositorios contra su rama de referencia, con líneas de sello para pegar en un análisis | A demanda |
| `sello-de-verificacion` | Revisa que los sellos `verificado-contra-git` de los documentos sigan vigentes | A demanda |
| `aprendizaje` | `scripts/aprender.py`: lección con evidencia, promoción a regla y reversión | A demanda |

Un módulo puede arrastrar a otro (autoguardado y compuerta traen el escaneo de secretos).

## Qué garantiza lo que se genera

- **Independencia:** los archivos son copias; no hay rutas al harness ni comando de actualización. Para recibir mejoras se
  vuelve a generar y se compara. Es deliberado: un entorno que se reescribe solo deja de ser de quien lo usa.
- **Un solo archivo de ajuste:** `entorno.toml` (módulos, comandos de la compuerta, rutas de documentación, autoguardado).
- **Seguro por defecto:** el autoguardado no sube, no usa `--force`, y no guarda si el escaneo de secretos encuentra algo.
  Ningún hook modifica la configuración global del agente: la de Claude Code va en `.claude/settings.json` del propio repo.
- **Sin dependencias:** solo `bash`, `git` y `python3 >= 3.11` (biblioteca estándar).
- **Verificable:** `./verificar.sh` comprueba sintaxis, configuración, que cada módulo tenga sus archivos y el escaneo.

## Ejemplo ya generado

Un entorno de ejemplo (para Claude Code y Codex) está publicado como ejemplo en
<https://github.com/catrroberrtt/entorno-ejemplo>. Se puede clonar y probar sin instalar el harness.

## Cómo lo usa otra persona

1. Clona el repositorio del entorno.
2. `./instalar.sh` (muestra qué falta, no cambia nada) y `./instalar.sh --aplicar`.
3. `./verificar.sh`.
4. Abre la carpeta con su agente.

## Publicar solo lo verificado

El módulo `publicar-solo-verificado` separa el mecanismo de cualquier herramienta concreta: **de dónde sale la verdad de cada
referencia se declara en `entorno.toml`**, no está escrito en el código.

```toml
[publicar]
exigir_nivel = 1              # 2 = además, revisión independiente (docs/revisor-independiente.md)

[[publicar.referencias]]
nombre = "ticket"
patron = "[A-Z]+-[0-9]+"
comprobar = ["./scripts/estado-ticket.sh", "{id}"]   # termina en 0 si existe e imprime el estado
estados_cerrados = ["DONE", "CERRADO"]
```

- **Nivel 1 (mecánico):** las rutas y los commits citados existen, cada referencia existe en su fuente y su estado coincide
  con lo que el texto afirma (un aviso si dice «pendiente» y la fuente dice «cerrado»), sin secretos ni relleno sin completar.
- **Nivel 2 (independiente):** otra persona o un agente de solo lectura comprueba las afirmaciones que ningún motor puede
  (datos, estados, «ya existe en producción») y deja un informe que el motor valida.
- **La marca está atada al contenido:** editar el texto la invalida. El hook rechaza además un cuerpo inline o por entrada
  estándar, porque no se puede verificar; un error interno del hook **nunca** bloquea.

## Aprendizaje con evidencia

Una lección no se vuelve regla sin evidencia, y toda regla se puede revertir:
`aprender.py nota "…" --evidencia "…"` → `promover N` (exige evidencia) → `revertir N`. Las reglas viven entre marcadores en
`AGENTS.md`, con el número de la nota, así que revertir es quitar una línea.

**Mejora medida.** `aprender.py nota "…" --falla "<comando>"` corre el comando **ahora** y exige que falle (si ya pasa, no hay nada que corregir).
Al promover se vuelve a correr y la regla solo pasa si ahora funciona: queda anotado «comprobado: el comando ahora pasa». El comando se guarda en
`.entorno/fallas.json` (local, fuera de git) y **no se lee del texto de la nota**: un archivo de notas manipulado no puede hacer ejecutar nada.
Una nota es una sola línea de texto plano (máximo 300 caracteres, sin saltos de línea ni marcadores `<!--`/`-->`): lo promovido termina en
`AGENTS.md`, que el agente lee como instrucciones, así que no se acepta nada que pueda forjar otras notas o salirse de su sitio.

## Mantener el entorno al día sin perder lo tuyo

`harness entorno --comparar <carpeta>` compara tres cosas por archivo: lo que se generó (guardado en `entorno.lock.json`), lo que hay ahora y lo que
generaría hoy el harness con las mismas opciones. Nunca escribe, salvo con `--aplicar-seguras`, que copia **solo** archivos que no tocaste y que el
generador mejoró.

| Resultado | Significa | Qué se hace |
|---|---|---|
| `SEGURO` | El generador mejoró un archivo que no tocaste, o trae uno nuevo | Se puede copiar (`--aplicar-seguras`) |
| `TUYO` | Lo cambiaste tú; el generador no lo tocó | Nada |
| `REVISAR` | Cambiaste tú **y** cambió el generador | Se compara a mano; no se toca solo |
| `INFO` | Lo borraste tú, o el generador ya no lo produce | Nada |

El `entorno.lock.json` es un archivo del repositorio y, por tanto, **no es de confianza**: si lleva rutas fuera de la carpeta, opciones inválidas o no se
puede interpretar, la comparación se detiene.

## Más módulos

- **`bloqueo-datos`**: el agente no se conecta con un cliente de base de datos a un host que no esté en `[datos].hosts_permitidos` y, con `solo_lectura`
  (por defecto), no escribe ni cambia el esquema, venga la consulta en la línea, en un heredoc o en un archivo (que se lee y se revisa). Es una **barrera, no
  una garantía**: no ve SQL que llega por canales que no se leen. La garantía real es que el usuario de base de datos del agente sea de **solo lectura**.
- **`formato-de-pr`**: declaras tus tipos de PR (cómo se reconocen y qué secciones llevan) en `[[pr.tipos]]` y el PR no se crea sin ellas. Sin tipos
  declarados no hace nada.
- **`inventario-de-fuentes`** y **`sello-de-verificacion`**: `scripts/inventario-fuentes.py` da la foto de tus repositorios contra su rama de **referencia**
  (no la rama local de turno) y las líneas `verificado-contra-git: <commit> · <repo> · <fecha>`; `scripts/sellos.py` revisa que esos sellos sigan
  vigentes: `INEXISTENTE` (commit inventado), `ATRASADO` (la referencia avanzó), `VENCIDO` (más de `vigencia_dias`).

## Codex

Con `--agentes codex` se genera `.codex/hooks.json` con los mismos hooks (formato documentado por Codex, que coincide con el de Claude Code) y
`docs/CODEX.md` (externo), un archivo que se crea dentro del entorno generado, con lo que hay que saber. Resumen: hay que **confiar** cada hook una vez con `/hooks`; solo se vigila `Bash`; Codex **falla abierto**
(un hook sin confiar o con error no bloquea), así que es una capa de freno y no una garantía; el autoguardado va en `SessionEnd` y **no se probó contra
Codex real**; el aviso de «documentación primero» no se genera porque el formato de salida de `UserPromptSubmit` en Codex no está confirmado.

## Defensas que se probaron (y por qué existen)

Cada una nació de un intento real de saltarse el mecanismo, y tiene su prueba:

- Los hooks **entienden la línea de comandos** en lugar de buscar texto: `git -C . commit`, `bash -c "…"`, `$(…)` y `cd` cuentan; `echo git commit` no.
- Los hooks encuentran la raíz del entorno **por su propia ubicación**, no por una variable del agente: lanzados desde una subcarpeta o por otro agente
  siguen funcionando (antes fallaban abiertos).
- Publicar rechaza modificar el archivo del cuerpo **en la misma línea** que publica (el hook lo ve antes de que el comando lo cambie) y las líneas
  demasiado largas para analizar. Una línea enorme no cuelga la sesión.
- El nombre del entorno y los perfiles se validan con coincidencia **completa** y contra una lista cerrada: un salto de línea final o una ruta como
  perfil no se aceptan.
- Lo generado se **inspecciona antes de escribir**: si `entorno.toml` o `settings.json` no se pueden interpretar, no se escribe nada.
- Los scripts de un entorno **solo usan la biblioteca estándar** (lo vigila una prueba): ningún script generado importa el harness.

## Límites conocidos

- Los hooks se probaron con Claude Code y con eventos construidos según el esquema documentado de Codex; **no se probaron contra Codex real** (no estaba instalado).
- La compuerta empieza **sin comandos**: cada equipo declara los suyos (`[gate].comandos`). Sin ellos solo escanea secretos y lo avisa.
- No hay actualización automática del entorno (por diseño): `--comparar` dice qué cambió y `--aplicar-seguras` copia solo lo que no tocaste.
- Los hooks vigilan `Bash`. `apply_patch`, herramientas MCP y SQL que llega por canales no leídos quedan fuera.
