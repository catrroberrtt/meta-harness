# Datos · NestJS + TypeORM + MySQL
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: plantilla del harness; contenido por extraer -->

> Acceso a datos, migraciones, transacciones y concurrencia (si aplica al stack).

**Estado: por extraer.** Todavía no tiene contenido verificado; no se rellena a ojo (R24: un estándar entra solo con evidencia registrada).

## Debe cubrir

- Repositorio concreto con SQL y tipo de fila; consultas en un solo lugar.
- Migraciones: escritura, prueba fuera de la carpeta de migraciones, largo de literales contra la columna.
- Transacciones y bloqueos: bloquear primero, leer después; nunca paralelizar dentro de una transacción con bloqueos.
- Tipos del motor con TypeORM (valores devueltos como texto, decimales) y fechas de negocio.
- Unicidad e idempotencia en la base.

## Cómo se completa

Se extrae de proyectos observados de este stack, se compara entre módulos y entre proyectos, y se registra en `evidencia.md` con su decisión humana antes de dejar de ser «por extraer».
