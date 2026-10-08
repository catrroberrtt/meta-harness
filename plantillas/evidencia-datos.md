<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: bloque de evidencia de datos

Obligatorio cuando el cambio calcula montos o tasas, clasifica filas, agrega filtros, rangos u orden, muestra el mismo dato en 2+ lugares, toca permisos o migra lógica entre lenguajes. Si no aplica, decir «sin impacto en datos».

```
### Evidencia de datos — {{qué se afirma}}
Consulta:                {{SELECT ...;}}
Resultado real ({{origen}}, {{fecha}}, último registro {{fecha}}):  {{salida pegada tal cual}}
Qué prueba:              {{afirmación concreta}}
Qué NO prueba:           {{el borde que no cubre}}     [OBLIGATORIO]
Veredicto:               {{uno de evidencia.veredictos}}
```
Reglas: la salida va pegada, «dio bien» no es evidencia; dos totales que «coinciden» llevan las dos consultas, comparadas al céntimo; sin credenciales ni datos personales (identificadores anonimizados); lo inferido se marca «inferido»; antes de «no existe», buscar 2-3 sinónimos; «no se reproduce» solo vale probado por el mismo camino que usa la aplicación.

## Veredictos (`evidencia.veredictos`)
| Nivel | Cuándo | Habilita |
|---|---|---|
| verificado-con-datos | se corrió contra datos reales y el resultado está pegado | decir «listo» |
| revisado-codigo | se leyó la lógica, no se corrió nada; no usa la palabra «verificado» | se declara por qué no subió |
| bloqueado-acceso | faltan datos o acceso | no se degrada: se entrega la consulta, qué resultado confirmaría o descartaría, quién puede correrla |

## Ejemplo mínimo
```
### Evidencia de datos — el total de Pedidos suma lo mismo en lista y en detalle
Consulta: SELECT SUM(total) FROM pedido WHERE lote=7;  /  SELECT SUM(d.total) FROM detalle d WHERE d.lote=7;
Resultado real (copia local, 2026-10-07, último registro 2026-10-06): 1 250,40 / 1 250,40
Qué prueba: coinciden al céntimo para el lote 7.
Qué NO prueba: lotes con descuentos por línea.
Veredicto: verificado-con-datos
```
