---
name: sdd-implementar
description: Implementa una fase aprobada del plan, con cambios pequeños y trazables a los criterios de aceptación. Úsala solo cuando hay plan aprobado; respeta las reglas duras de AGENTS.md y registra las mejoras ajenas sin aplicarlas.
---
<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: método de trabajo del harness (metodo/forma-de-trabajo.md) y plantillas de esta carpeta -->

# sdd-implementar

## Cuándo usarla
- Hay una fase del plan aprobada por la persona. Una fase a la vez.

## Pasos
1. Relee `AGENTS.md` (reglas duras y pendiente de declarar) y las convenciones de ramas, commits y pull requests de `convenciones.toml`.
2. Implementa solo lo que la fase pide. Cada cambio debe poder enlazarse a un criterio de aceptación.
3. Escribe o ajusta las pruebas de los casos definidos en la planificación.
4. Si descubres una mejora que no corresponde al cambio, regístrala con `herramientas/harness-mejoras.py` (subcomando `nueva`) y sigue; no la apliques de paso.
5. Si el código y lo documentado dejan de coincidir, corre el chequeo de `plantillas/convergencia.md` antes de añadir ajustes.
6. Al terminar la fase, resume qué cambió y pasa a `sdd-verificar`; no declares «listo».

## Qué NO hacer
- No hagas commit, push, despliegue ni acciones sobre datos si la política exige confirmación o las prohíbe: pídelo a la persona.
- No instales dependencias ni herramientas globales sin aprobación.
- No amplíes el alcance ni toques archivos fuera del plan.
- No versiones credenciales ni `acceso.local.toml`.
