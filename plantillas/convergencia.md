<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: convergencia (¿el código sigue coincidiendo con lo documentado?)

Se corre antes de añadir un ajuste a una descripción existente y a pedido; no en cada tarea chica.

Pasos: identificar el tema → releer la descripción más reciente (con sus ajustes) → releer el código que cita → comparar.

| Sección | Lo documentado dice | El código real dice | ¿Coincide? |
|---|---|---|---|

- Si todo coincide: decirlo y parar; opcional una línea «Convergencia {{fecha}}: verificado, sin deriva».
- Si hay deriva: no corregir en silencio ni elegir versión; presentarla como hallazgo y preguntar cuál es la correcta.

## Ejemplo mínimo
| Sección | Documentado | Código | ¿Coincide? |
|---|---|---|---|
| Servidor | límite de 100 por página | límite de 50 | No |
