<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-08 · vence: 90d · fuente: metodo/terminado-y-trazabilidad.md -->
# Plantilla: contrato de delegación (`delegacion.md`)

Una fila por tarea encargada (a una persona, a un subagente o a uno mismo en otra fase). Sin contrato de archivos no se delega. Reglas en `metodo/terminado-y-trazabilidad.md` §4.

## Estructura
```markdown
| Tarea | Encargado | Requisitos | Escribe | No toca | Entrega | Aceptación | Reversa | Estado |
|---|---|---|---|---|---|---|---|---|
| {{qué se encarga}} | {{quién}} | RQ-01, RQ-02 | {{src/entregas/, pruebas/entregas.spec}} | {{src/pedidos/}} | {{rama o carpeta + resumen}} | {{CA-01.1 y comando}} | {{cómo se deshace}} | {{pendiente / en-curso / entregada / aceptada / rechazada}} |
```

- `Escribe`: rutas relativas, separadas por coma; una carpeta termina en `/`. Si dos tareas comparten un archivo, ambas lo marcan `(compartido)`.
- `Estado` final: `aceptada`, solo después de que quien coordina verificó por su cuenta.
- El contrato no entrega datos reales ni credenciales; si hacen falta, se nombran aparte y los da una persona.

## Ejemplo mínimo
Ver `plantillas/ejemplos/cambio-ejemplo/delegacion.md`.
