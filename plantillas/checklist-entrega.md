<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: checklist de entrega y gate de salida

Orden fijo; lo mecánico lo corre un guion, lo que depende de una persona queda listado. Pasos por `gate.pasos`; el agente ejecuta build y pruebas y **pega el resultado y el código de salida**. Base del gate = la rama de la que sale la rama de trabajo.

## Barrido final antes del commit (por defecto)
1. Gate mecánico sin FALLA; los AVISOS leídos uno a uno.
2. Build y pruebas acotados, con código de salida.
3. Patrones de calidad: lista filtrada al ámbito del diff leída entera; patrón nuevo si hubo bug generalizable.
4. Decimales, cálculos y redondeos: mismo total desde una sola fuente; si hay dinero, checklist de riesgo y prueba de dos peticiones en paralelo.
5. Trazabilidad: quién, cuándo y estado anterior quedan registrados.
6. QA previas del módulo y de otros: ninguna observación reaparece.
7. Contrato ↔ documentación ↔ ticket sincronizados; nada se publica sin verificar.
8. Capas completas (servidor, interfaz, infraestructura); si falta una, el ticket no se cierra.
9. Procesos levantados, apagados (comprobar puertos).
10. Datos de prueba limpiados o declarados; ningún secreto copiado al árbol.
11. {{pasos propios de la instancia, p. ej. plantillas de correo publicadas en su repositorio}}.

## Checklist por familia de riesgo (estructura)
| Familia del hallazgo | Ejemplos | Verificación previa |
|---|---|---|
El **contenido** de cada familia (dinero, permisos, formatos, textos) es de la instancia.

## Al reportar
Qué se verificó y qué no (`forma-de-trabajo.md` §8); si se cerró una ronda de QA o de revisión: fila en el registro de correcciones.

## Ejemplo mínimo
```
1. gate: 0 FALLA, 2 AVISOS leídos   2. build/pruebas: código 0 (2026-10-07)
4. decimales: total 90,00 en lista, detalle y exportación   9. puertos libres: sí
No probado: despliegue.
```
