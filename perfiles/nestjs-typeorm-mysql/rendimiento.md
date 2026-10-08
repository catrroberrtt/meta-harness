# Rendimiento · NestJS + TypeORM + MySQL
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: plantilla del harness; contenido por extraer -->

> Cómo se mide, qué se optimiza primero y qué no se cachea.

**Estado: por extraer.** Todavía no tiene contenido verificado; no se rellena a ojo (R24: un estándar entra solo con evidencia registrada).

## Debe cubrir

- Medir antes de optimizar; índice y consulta antes que caché.
- N+1 y consultas dentro de bucles; paralelismo con tope.
- Paginación con límite revisado contra todos los llamadores.

## Cómo se completa

Se extrae de proyectos observados de este stack, se compara entre módulos y entre proyectos, y se registra en `evidencia.md` con su decisión humana antes de dejar de ser «por extraer».
