---
name: sdd-especificar
description: Especifica un cambio antes de diseñarlo ni programarlo (desarrollo guiado por especificación). Úsala cuando la persona pide algo nuevo, ambiguo o sin criterios de aceptación claros; produce la apertura del cambio con alcance, preguntas abiertas y criterios verificables.
---
<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: método de trabajo del harness (metodo/forma-de-trabajo.md) y plantillas de esta carpeta -->

# sdd-especificar

## Cuándo usarla
- Llega una petición nueva, o una existente cuyos criterios de aceptación no están escritos.
- Antes de proponer un diseño. Si ya hay una especificación aprobada, pasa a `sdd-planificar`.

## Pasos
1. Lee primero lo que ya existe: `conocimiento/`, la documentación del módulo afectado y las convenciones de la instancia (`convenciones.toml`).
2. Haz las preguntas de la plantilla `plantillas/intake.md` del harness, **solo las que falten**, una a una y diciendo qué intentaste antes de preguntar.
3. Abre el cambio en `cambios/<slug>/` con `plantillas/apertura-de-cambio.md`: problema, alcance, fuera de alcance y criterios de aceptación que se puedan comprobar con un resultado observable.
4. Lo que no puedas resolver con los documentos va a `plantillas/preguntas-abiertas.md`, con quién puede responder.
5. Si el origen son archivos de entrada (documentos, SQL, hojas), puedes resumirlos con `herramientas/harness-leer-entradas.py` (solo lectura).
6. Pide la aprobación de la especificación antes de seguir. Sin «ok» explícito no se pasa a planificar.

## Qué NO hacer
- No diseñes ni escribas código en esta etapa.
- No inventes ambientes, nombres, ramas ni reglas de negocio: pregunta.
- No mezcles mejoras ajenas al cambio; regístralas con `herramientas/harness-mejoras.py`.
- No des por entendido un requisito ambiguo: conviértelo en pregunta abierta.
