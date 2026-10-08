<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: conocimiento acumulado de un módulo

Carpetas por plataforma según `conocimiento.carpetas`. Un archivo por módulo; el índice general lleva una línea por módulo.

```markdown
# {{modulo}}
> Creado: {{fecha}} · Última actualización: {{fecha}}

## Ubicación en el código        [OBLIGATORIO]
Patrón, módulo, controladores, servicios, repositorios, entidades → tablas.
## Glosario de negocio           términos, estados y campos en lenguaje de negocio, con origen y fecha
## Reglas de negocio             límites, validaciones y excepciones, con origen y fecha
## Mapa de endpoints             | Método y ruta | Manejador | Qué hace | Documento |
## Decisiones de arquitectura    fecha — decisión porque razón; trade-off aceptado
## Correcciones y supuestos fallidos
fecha — Se asumió: A (origen). Es en realidad: B. Lo reveló: X. Impacto: Y. Para no repetir: verificación a hacer.
## Gotchas
fecha — qué pasó → cómo evitarlo
## Relacionados                  [[otro-modulo]] — por qué se tocan; punteros a implementaciones y patrones de calidad
```
Se actualiza sin pedir confirmación cuando aparece información nueva. Si un dato contradice el código actual, se verifica contra el código antes de usarlo. Un hallazgo que debía estar conectado y no lo estaba se enlaza antes de cerrar la tarea.

## Ejemplo mínimo
```
# pedidos
## Reglas de negocio
- Un pedido no puede entregarse por encima de lo pedido. Origen: producto · 2026-10-07
## Relacionados
- [[inventario]] — la entrega descuenta existencias
```
