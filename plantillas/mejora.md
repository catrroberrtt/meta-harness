<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: especificación del harness §18 -->
# Plantilla: una entrada del registro de mejoras

Una por mejora detectada durante una migración; vive en `mejoras.md` de la instancia (la gestiona `herramientas/harness-mejoras.py`). **Anotar no es aplicar**: la réplica no cambia por estar anotada. Campos [OBLIGATORIO] salvo decisión, fecha y especificación, que se llenan al decidir/aplicar.

```
## {{id}} · {{título corto}}
- **estado**: propuesta            # propuesta | aprobada | descartada | aplicada
- **dónde se vio**: {{lugar del origen + evidencia: archivo/línea, consulta, caso de equivalencia}}
- **qué cambiaría**: {{cambio concreto respecto a lo que el origen hace hoy}}
- **motivo**: {{por qué conviene}}
- **riesgo**: {{bajo | medio | alto}}
- **esfuerzo**: {{S | M | L}}
- **cambia comportamiento visible**: {{sí | no}}
- **decisión**: {{motivo de la decisión}}
- **fecha de decisión**: {{AAAA-MM-DD}}
- **especificación**: {{referencia a la especificación del cambio, solo al aplicar}}
```

Estados: `propuesta` → `aprobada` o `descartada` (decide una persona) → `aplicada` (solo desde `aprobada`, con su especificación y después de cerrar la equivalencia).

## Ejemplo mínimo
```
## M-001 · Redondeo del total de un pedido
- **estado**: propuesta
- **dónde se vio**: función de totales del origen, redondea hacia abajo cada línea; caso EQ-004
- **qué cambiaría**: redondear una sola vez al final
- **motivo**: evita diferencias de centavos acumuladas en pedidos grandes
- **riesgo**: medio
- **esfuerzo**: S
- **cambia comportamiento visible**: sí
- **decisión**:
- **fecha de decisión**:
- **especificación**:
```
