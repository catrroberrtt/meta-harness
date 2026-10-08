<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: registro de correcciones y rondas (tablero)

Mide si el entorno logra que se pueda delegar y confiar. Solo números contados, nunca estimados. Estructura vacía; los datos son de la instancia.

## Rondas de QA o revisión (una fila al cerrar la ronda)
| Fecha | Tema | Tipo (QA externa / revisión / plan / propia) | Devueltas | Reales | De dato | De código | Reabiertas | Gate aplicado (sí/no/parcial/sin registro) |
|---|---|---|---|---|---|---|---|---|

## Correcciones de la persona (una fila en el momento, no después)
| Fecha | Qué se corrigió | Momento en que falló (entender / hacer / demostrar) | Regla o mecanismo añadido |
|---|---|---|---|

## Afirmaciones falsas detectadas
| Fecha | Afirmación | Fuente que la refutó | Causa |
|---|---|---|---|

Si una métrica no baja: preguntar en qué momento falla y cambiar o **quitar** piezas de ese momento, no agregar otra.

## Ejemplo mínimo
| 2026-10-07 | Pedidos | QA externa | 10 | 8 | 3 | 5 | 1 | sí |
