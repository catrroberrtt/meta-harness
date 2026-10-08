<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: ticket de hallazgo (seis secciones fijas)

Secciones por la clave `ticket.cuerpo.secciones`. Todo hallazgo o trabajo planificado usa las seis completas; lo que varía es cuánto detalle vive en el ticket y cuánto en la página de documentación.

```markdown
## Problema                        [OBLIGATORIO]  qué está mal, 1-2 frases
## Qué sucede                      [OBLIGATORIO]  archivo/función/línea (o tabla/columna) y el mecanismo paso a paso
## Qué ocasiona                    [OBLIGATORIO]  impacto real: qué falla, para quién, qué tan visible
## Caso presentado                 [OBLIGATORIO]  caso real (datos, identificadores, montos) o escenario que lo demuestra
## La solución                     [OBLIGATORIO]  cambios concretos; si ya se decidió, la decisión y las alternativas descartadas
## Preguntas abiertas              solo en el tracker, nunca en la wiki; decisiones de negocio que el código no resuelve
## Referencias                     enlace completo a la página de detalle, ticket padre, relacionados
```
Reglas: nunca rutas internas del método ni secretos ni datos personales dentro del ticket.

## Variante `respuesta` (responder a una observación existente)
Se agrega la sección:
```markdown
## Resultados y evidencia de validación   [OBLIGATORIO]
Qué se corrió, contra qué datos, resultado pegado (no adjetivos). Si la validación reveló un matiz, decirlo.
```

## Dónde va un hallazgo
| Qué encontraste | Qué hacer |
|---|---|
| Dentro del alcance del ticket en curso | Se corrige y se cuenta en la descripción del cambio; no es ticket |
| Fuera de alcance, mismo producto y épica | Sub-tarea del padre, con esta plantilla |
| De otro producto o área | Ticket propio |
| Se resuelve cuando avance otro ticket | Sub-tarea que dice qué ticket lo cierra |

Cierre del circuito: cada fila de «Fixes pendientes» de una revisión termina con su clave de ticket o con el motivo de no tenerla.

## Ejemplo mínimo
```markdown
## Problema
El total de un pedido no resta el descuento.
## Qué sucede
`pedidos/total.ts` línea 40 suma `precioLista` en vez de `precioFinal`.
## Qué ocasiona
Los clientes ven un total mayor al pagado en el 8 % de los pedidos.
## Caso presentado
Pedido 1001: lista 100,00; descuento 10,00; mostrado 100,00; esperado 90,00.
## La solución
Usar `precioFinal`. Descartado: recalcular en la vista (duplica la regla).
## Referencias
Detalle: https://wiki.example.com/pages/42 (Total de Pedidos)
```
