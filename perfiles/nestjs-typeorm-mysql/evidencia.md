# Evidencia · NestJS + TypeORM + MySQL
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (estándares de estructura, SOLID y patrones, guía de diseño, criterios al codificar, convenciones de seguridad) -->

> Tabla «regla → fuente: instancia de origen, sección X». Toda regla viene de **una sola instancia**: por la regla de R24 todas están **pendientes de evidencia** hasta contrastarlas con un segundo proyecto del mismo stack y registrar la decisión humana. La evidencia es correlacional: que una práctica se use no la hace «la mejor».

Estados: `pendiente de evidencia` (una sola instancia) · `respaldada` (2 o más instancias independientes y decisión humana).

## Reglas de arquitectura.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| ARQ-1 | guía de diseño §0 (principio rector) | pendiente de evidencia |
| ARQ-2, ARQ-3 | estructura estándar §1 | pendiente de evidencia |
| ARQ-4, ARQ-5 a ARQ-11 | estructura estándar §2 | pendiente de evidencia |
| ARQ-12 a ARQ-14 | estructura estándar §3 (escala), §3.9 (números) | pendiente de evidencia |
| ARQ-15 a ARQ-19 | estructura estándar §3.1; SOLID (DIP); guía §0 | pendiente de evidencia |
| ARQ-20 a ARQ-23 | estructura estándar §3.2; SOLID (cohesión de servicios) | pendiente de evidencia |
| ARQ-24 a ARQ-27 | estructura estándar §3.3; guía §0 | pendiente de evidencia |
| ARQ-28 | estructura estándar §3.4 | pendiente de evidencia |
| ARQ-29 | estructura estándar §3.5 | pendiente de evidencia |
| ARQ-30, ARQ-31 | estructura estándar §3.6; guía catálogo B25 | pendiente de evidencia |
| ARQ-32, ARQ-33 | estructura estándar §3.7 | pendiente de evidencia |
| ARQ-34, ARQ-35 | estructura estándar §3.8 | pendiente de evidencia |
| ARQ-36 a ARQ-39 | guía §0.5 reglas 1, 2, 4; catálogo B19 | pendiente de evidencia |
| ARQ-40 | guía §0; SOLID (CQRS ligero) | pendiente de evidencia |
| ARQ-41 | convenciones de seguridad §7.1; guía §3 regla 1 | pendiente de evidencia |
| ARQ-42, ARQ-43 | guía §5 (umbrales medidos en una sola base de código), B7 | pendiente de evidencia |
| ARQ-44, ARQ-45 | estructura estándar §4 | pendiente de evidencia |

## Reglas de patrones.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| PAT-0, PAT-1 a PAT-5 | guía de diseño §0, catálogo B1, B2, B4, B6, B9 y árbol A1; estructura estándar §3.1-§3.2 | pendiente de evidencia |
| PAT-6 | guía catálogo B5, árbol A4; SOLID (CQRS ligero) | pendiente de evidencia |
| PAT-7, PAT-8 | guía catálogo B10, B11, árbol A7 | pendiente de evidencia |
| PAT-9, PAT-10 | guía catálogo B12, B16; estructura estándar §3.7 | pendiente de evidencia |
| PAT-11 | guía catálogo B13, árbol A9; SOLID (tabla de patrones, Mapper) | pendiente de evidencia |
| PAT-12, PAT-13 | SOLID (tabla de patrones: DTO, Guard/Interceptor/Filter, PartialType); convenciones de seguridad §7 | pendiente de evidencia |
| PAT-14, PAT-15 | guía catálogo B14, B15, árbol A8 | pendiente de evidencia |
| PAT-16, PAT-17 | guía catálogo B18; §0.5 regla 6 | pendiente de evidencia |
| PAT-18 | guía catálogo B19; §0.5 reglas 4 y 5 | pendiente de evidencia |
| PAT-19 | estructura estándar §3.3; criterios al codificar (primera fila); guía catálogo B20 | pendiente de evidencia |
| PAT-20 | guía catálogo B21, árbol A15 | pendiente de evidencia |
| PAT-21, PAT-22 | guía catálogo B22, B23; criterios al codificar (listas paginadas) | pendiente de evidencia |
| PAT-23 | guía catálogo B24, árbol A6; §3 regla 12 | pendiente de evidencia |
| PAT-24 | guía §3 regla 1; convenciones de seguridad §7.1 | pendiente de evidencia |
| PAT-25 a PAT-27 | SOLID (No introducir); guía catálogo B8, §3 regla 11 | pendiente de evidencia |

## Reglas de codificacion.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| COD-1 a COD-9 | guía de diseño §0.5 (paradigma) | pendiente de evidencia |
| COD-10 a COD-19 | guía §7.3 (código limpio) | pendiente de evidencia |
| COD-20, COD-21, COD-22 | criterios al codificar (filas de clase grande, bloque duplicado, script de reemplazo) | pendiente de evidencia |
| COD-23 | guía §6 | pendiente de evidencia |
| COD-24 a COD-27 | guía §7.3 (nombres); SOLID (cohesión); estructura estándar §3.8 | pendiente de evidencia |
| COD-28 a COD-31 | estructura estándar §3.7; guía §7.3 (errores explícitos); convenciones de seguridad §3 | pendiente de evidencia |
| COD-32, COD-33 | convenciones de seguridad §7 (al escribir código) | pendiente de evidencia |
| COD-34 | convenciones de seguridad §3 (registro con redacción) | pendiente de evidencia |
| COD-35 | criterios al codificar (llamada a otro sistema) | pendiente de evidencia |
| COD-36 | convenciones de seguridad §7.2.4 | pendiente de evidencia |
| COD-37 a COD-42 | guía catálogo B4, B14, B15; SOLID (LSP, ISP); convenciones de seguridad §7 | pendiente de evidencia |
| COD-43 a COD-50 | guía §7.2 (asincronía), §3 reglas 6-7; criterios al codificar (lectura de archivo) | pendiente de evidencia |
| COD-51 a COD-54 | guía §7.5 (complejidad) | pendiente de evidencia |

## Decisiones humanas y alternativas descartadas

- Aún no hay decisiones registradas para este perfil.
- Descartado en la instancia de origen (se conserva como regla negativa): bus de comandos, bus de eventos, event sourcing y tablas espejo (`PAT-25`); puerto de lectura simétrico al de escritura (`ARQ-18`).

## Divergencias observadas

Los umbrales de `ARQ-42` se midieron sobre una sola base de código; falta contrastarlos con otro proyecto del mismo stack.

## Pendiente de evidencia: lista completa

Todas las reglas anteriores. Las que dependen además de una decisión puntual de la instancia (puntos de partida, no estándares): umbrales numéricos de `ARQ-42`/`ARQ-43`, `COD-11`, `COD-20`, `COD-45` (lotes de 5-10) y `PAT-20` (500 ms, TTL de 60 s).
