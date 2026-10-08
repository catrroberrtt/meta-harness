<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: cierre técnico de un ticket y bloque de PR en el padre

Se completa antes de sincronizar el tracker y armar el PR (`ticket.cierre-tecnico`). No basta transicionar el estado.

## Cierre técnico (comentario o actualización de «La solución»)
- **Qué se implementó al final** [OBLIGATORIO] — puede diferir del plan original; explicar por qué.
- **Alternativas evaluadas y por qué se descartaron** [OBLIGATORIO]
- **Evidencia de que funciona** [OBLIGATORIO] — usa `evidencia-datos.md`; números, no adjetivos.
- **Enlace a la documentación detallada** (URL completa).
- **Lo no probado**, dicho explícito.

## Bloque de PR en el ticket padre
Va en el padre, no en cada sub-tarea; se actualiza en el momento en que un PR se abre, se reemplaza o se integra.
```
**Pull requests ({{destino}}):**
* [{{repo}} #{{n}}]({{url}}) — {{estado: vigente | cerrado, reemplazado por X | integrado}} · rama `{{rama}}`
```
Un PR viejo reemplazado se deja en la lista con la nota, no se borra.

## Sincronización de estados
Al cerrar el PR, cada ticket que resuelve pasa por los estados intermedios hasta el que corresponda (`ticket-jerarquia.md`). Si necesita revisión detallada, se detiene en el intermedio. Se muestra la lista (ticket → estado actual → destino → por qué) antes de ejecutar.

## Ejemplo mínimo
```
Implementado: reintento local con 3 intentos (nivel 1).
Descartado: cola persistente propia, porque el servicio de correo ya reintenta y guarda.
Evidencia: 20 envíos simulados con fallo, 20 reintentados (2026-10-07).
**Pull requests (integración):**
* [pedidos-api #45](https://git.example.com/pedidos-api/pull/45) — vigente · rama feat/reintento
```
