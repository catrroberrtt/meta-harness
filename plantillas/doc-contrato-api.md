<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: contrato de API y especificación de pantallas

Forma del sobre de respuesta según `api.sobre-de-respuesta` (ej. `{ message, data }` y `{ data, meta }` con paginación). La forma JSON es **provisional** hasta validar la consulta SQL equivalente contra datos reales.

## Por endpoint [OBLIGATORIO]
- Nombre · método y ruta · autenticación y permiso · auditoría.
- Parámetros:
| Ubicación | Nombre | Tipo | Obligatorio | Por defecto | Ejemplo |
|---|---|---|---|---|---|
- Petición de ejemplo (JSON completo) y respuesta OK (código + JSON real).
- Errores: caso → código → cuerpo.
- Efectos: estado, correo, historial, auditoría.
- Formato por campo (preguntar, no asumir): tipo crudo, qué representa, cómo se muestra (fracción vs porcentaje, moneda, zona horaria).

## Especificación de pantallas
| Pantalla | Endpoint | Estados y validaciones | Ticket |
|---|---|---|---|

## Ejemplo mínimo
```
POST /pedidos/:id/entregas   permiso PEDIDOS_ENTREGAR   auditable
Petición: { "cantidad": 2 }
201: { "message": "ok", "data": { "id": 7, "pendiente": 3 } }
Errores: 404 pedido inexistente · 409 cantidad mayor a lo pendiente
```
