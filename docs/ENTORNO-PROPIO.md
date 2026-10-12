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

## Aprendizaje con evidencia

Una lección no se vuelve regla sin evidencia, y toda regla se puede revertir:
`aprender.py nota "…" --evidencia "…"` → `promover N` (exige evidencia) → `revertir N`. Las reglas viven entre marcadores en
`AGENTS.md`, con el número de la nota, así que revertir es quitar una línea.

## Límites conocidos

- Los hooks se verificaron con Claude Code. Codex usa `AGENTS.md`; sus hooks no se generan todavía.
- La compuerta empieza **sin comandos**: cada equipo declara los suyos (`[gate].comandos`). Sin ellos solo escanea secretos y lo avisa.
- No hay detección automática de que el entorno se desactualizó respecto al harness (por diseño, ver arriba).
