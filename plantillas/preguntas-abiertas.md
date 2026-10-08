<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: página viva de preguntas abiertas

Se actualiza con estado y respuesta (con fecha) a medida que se contestan.

| Id | Pregunta | Origen | Cómo lo resuelve hoy el sistema | Propuesta | Valor por defecto con el que se avanza | Qué falta confirmar | Estado | Área que responde |
|---|---|---|---|---|---|---|---|---|

## Sección «¿Alguna pregunta frena el desarrollo?» [OBLIGATORIO]
- Frena la salida a producción: {{lista}}
- Frena una sub-tarea acotada: {{lista}}
- Avanza con un valor por defecto reversible: {{lista}}

## Ficha de bloqueante
Un bloqueante nunca se entrega solo como «espera respuesta». Cada uno lleva:
1. Qué bloquea de verdad (capa).
2. Evidencia que ya existe o se consiguió.
3. Ángulos de cobertura (datos, código, diseño con valor por defecto reversible, proceso, riesgo legal).
4. Qué puede avanzar ya sin la respuesta.
5. La pregunta exacta, con opciones, recomendación y quién decide.

## Ejemplo mínimo
| Id | Pregunta | Valor por defecto | Estado | Área |
|---|---|---|---|---|
| P1 | ¿Se permite entregar más de lo pedido? | No | Abierta | Producto |
