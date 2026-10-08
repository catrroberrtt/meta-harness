---
name: sdd-planificar
description: Convierte una especificación aprobada en un plan por fases con casos de prueba y reutilización de lo existente. Úsala después de sdd-especificar y antes de escribir código; cada fase se aprueba antes de pasar a la siguiente.
---
<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: método de trabajo del harness (metodo/forma-de-trabajo.md) y plantillas de esta carpeta -->

# sdd-planificar

## Cuándo usarla
- Existe una especificación aprobada en `cambios/<slug>/` y todavía no hay código.
- El cambio toca más de un archivo, módulo o capa, o tiene riesgo (datos, dinero, permisos).

## Pasos
1. Relee la especificación y sus criterios de aceptación; si cambió algo, vuelve a `sdd-especificar`.
2. Busca primero qué ya existe y se puede reutilizar: `plantillas/mapa-reutilizacion.md`.
3. Escribe el plan con `plantillas/plan.md`: fases pequeñas, cada una con su resultado verificable, sus archivos y su riesgo.
4. Define los casos de prueba con `plantillas/casos-de-prueba.md` **antes** de implementar: cada criterio de aceptación debe tener al menos un caso.
5. Si hay migración o reemplazo de algo existente, prepara el cotejo con `plantillas/equivalencia.md`.
6. Presenta el plan y espera la aprobación **por fase**. No se avanza sin «ok».

## Qué NO hacer
- No empieces a implementar con el plan sin aprobar.
- No planifiques acciones que la política de la instancia prohíbe o que piden confirmación (datos, despliegue, costos): márcalas como pasos que ejecuta la persona o que requieren su confirmación puntual.
- No rellenes con suposiciones lo que el proyecto no declaró: pregunta.
- No dejes criterios de aceptación sin caso de prueba.
