<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: intake (preguntas antes de proponer)

No se propone ni se diseña hasta haber consultado el conocimiento previo y preguntado **solo lo que falte**. La lista es `intake.preguntas` (extensible por la instancia).

Antes de preguntar: leer el índice de conocimiento, el módulo afectado y sus relacionados, la entrada más reciente de implementaciones del tema y sus revisiones de QA, y los patrones de calidad que citen el módulo. Si no se sabe una ruta: búsqueda dirigida, nunca rastreo general.

| # | Pregunta | Respuesta | Origen |
|---|---|---|---|
| 1 | Objetivo funcional: qué problema resuelve, quién lo consume [OBLIGATORIO] | | |
| 2 | Módulo o recurso afectado y ruta exacta | | |
| 3 | Proveedores existentes a reutilizar (ruta directa) | | |
| 4 | Datos y tablas involucradas | | |
| 5 | Reglas de negocio, validaciones, volumen, paginación | | |
| 6 | Lectura o escritura; ¿cambia el esquema? | | |
| 7 | Quién puede llamarlo (usuario, permiso, llamada entre sistemas) | | |

Si la persona dice «no sé»: búsqueda dirigida y confirmar lo encontrado antes de seguir. Si el cambio itera un tema que ya tuvo QA: revisar sus checklists, incluidos los ítems abiertos.

## Ejemplo mínimo
| # | Pregunta | Respuesta |
|---|---|---|
| 1 | Objetivo | Entregar pedidos en partes; lo usa el área de despacho |
| 6 | Lectura/escritura | Escritura; añade tabla |
