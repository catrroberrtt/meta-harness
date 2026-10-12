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

## Límites conocidos

- Los hooks se verificaron con Claude Code. Codex usa `AGENTS.md`; sus hooks no se generan todavía.
- La compuerta empieza **sin comandos**: cada equipo declara los suyos (`[gate].comandos`). Sin ellos solo escanea secretos y lo avisa.
- No hay detección automática de que el entorno se desactualizó respecto al harness (por diseño, ver arriba).
