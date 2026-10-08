<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: mapa de reutilización

Lo primero que se aprueba del plan. Reutilizar = usar el componente existente, no copiar su lógica ni volver a consultar la tabla.

| Concepto de dominio | Qué ya existe (ruta verificada en la rama de referencia) | Reutiliza / extiende / crea | Por qué |
|---|---|---|---|

## Reglas del flujo análogo (cuando el cambio es una variante de un flujo existente)
Listar cada validación, tope o permiso del flujo existente, aunque parezca no aplicar.
| Regla del flujo análogo | ¿Aplica a este flujo? | Decisión (aplica / no aplica, porque… / pendiente de negocio) |
|---|---|---|
Ninguna fila queda en blanco.

## Impacto cruzado
¿Esto existe también en otro repo o plataforma? No darlo por pendiente ni por inexistente sin comprobar en ese repo; si no está disponible, decirlo.

## Ejemplo mínimo
| Concepto | Qué existe | Decisión | Por qué |
|---|---|---|---|
| Descuento | pedidos/descuento.ts | Reutiliza | ya calcula el precio final |
| Entrega | — | Crea | no existe |
