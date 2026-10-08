<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: casos de prueba «dado / cuando / entonces»

Agrupados por flujo y ligados a la sub-tarea que los habilita.

| Id | Flujo | Dado | Cuando | Entonces | Sub-tarea |
|---|---|---|---|---|---|

Incluir [OBLIGATORIO]: caso normal, borde (límites exactos), error y permiso (sin sesión vs sin permiso son distintos), concurrencia (dos peticiones a la vez) si hay escritura.

## Ejemplo mínimo
| Id | Flujo | Dado | Cuando | Entonces | Sub-tarea |
|---|---|---|---|---|---|
| C1 | Entrega | pedido con 5 pendientes | entrego 2 | quedan 3 | Servidor · S1 |
| C2 | Entrega | pedido con 3 pendientes | entrego 4 | error 409 | Servidor · S1 |
