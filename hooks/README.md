# Hooks genéricos

<!-- tipo: herramienta · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: hooks genéricos del propio repositorio -->

Hooks de Claude Code sin datos de empresa (recordatorios antes de cerrar, bloqueo de comandos peligrosos, guardas de consumo y de publicación) y la plantilla de registro. El instalador los copia y los registra; nunca guarda credenciales ni memoria de usuario.

## Origen

Lo aporta la instancia del proyecto; el mapa de migración vive en la instancia (parametrizacion).

## Aprendizaje automático

`plantillas/stop-aprender.sh.tpl`: hook de fin de sesión que (1) corre `harness-aprender.py escanear` en silencio (solo lee las fuentes y escribe en la cola local) y (2) sincroniza el repositorio con `harness-sincronizar.py` solo si pasa la compuerta de publicación. Nunca hace fallar la sesión. Ver `docs/APRENDIZAJE-AUTOMATICO.md`.

## Aviso de novedades sin digerir

`plantillas/aviso-novedades.sh.tpl`: hook de inicio de sesión (SessionStart) que lee un archivo de novedades (secciones `## título` con una viñeta por pendiente, generado por un proceso periódico de la instancia) y, al abrir la sesión, avisa cuántos pendientes hay por sección y si el archivo está desactualizado. Solo imprime texto; sin el archivo no hace nada. Se instala igual que `stop-aprender.sh.tpl`: copiar sin `.tpl`, sustituir `__NOVEDADES__` y registrarlo en SessionStart. Sirve para no concluir «no está documentado» sin haber mirado lo nuevo.
