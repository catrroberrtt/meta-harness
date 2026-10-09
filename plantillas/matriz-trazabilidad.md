<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-08 · vence: 90d · fuente: metodo/terminado-y-trazabilidad.md -->
# Plantilla: matriz de trazabilidad (`matriz.md`)

Una fila por par requisito–criterio. Es lo que responde, sin leer el código, «¿qué prueba cubre este requisito, en qué commit quedó y dónde está la evidencia?». Reglas en `metodo/terminado-y-trazabilidad.md` §5.

## Estructura
```markdown
| Requisito | Criterio | Prueba | Rojo→verde | Commit | Evidencia | Estado | Nota |
|---|---|---|---|---|---|---|---|
| RQ-01 | CA-01.1 | {{ruta/de/prueba.ext::caso}} | {{sí / no / n/a}} | {{hash}} | {{evidencia/gate.txt}} | {{pendiente / implementado / verificado / no-verificado}} | {{motivo si no-verificado}} |
```

- Sin `|` dentro de las celdas. Varios commits: separados por coma.
- `verificado` exige prueba, commit y evidencia. `no-verificado` exige la nota (motivo y qué lo destrabaría).
- `Rojo→verde`: `sí` si la prueba se vio fallar antes del cambio y pasar después; obligatorio declararlo (sí, no o n/a) en el cierre.

## Ejemplo mínimo
Ver `plantillas/ejemplos/cambio-ejemplo/matriz.md`.
