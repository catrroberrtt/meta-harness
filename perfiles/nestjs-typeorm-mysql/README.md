# Perfil: NestJS + TypeORM + MySQL
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: plantilla del harness y descripción del stack; contenido por extraer salvo lo indicado -->

Backend NestJS con TypeORM y MySQL: API HTTP con capas, transacciones y migraciones.

## Cuándo SÍ

- Hay dependencias `@nestjs/*` y `typeorm` con el controlador de MySQL.
- El servicio expone una API y escribe en una base relacional.

## Cuándo NO

- Función puntual sin servidor (otro perfil).
- Backend sin base relacional o sin NestJS.

## Comandos

`npm run build`, `npx tsc --noEmit`, `npx jest` (acotados al archivo tocado).

## Archivos del perfil

| Archivo | Estado |
|---|---|
| `arquitectura.md` | con contenido (parte de la evidencia, pendiente de contraste) |
| `patrones.md` | con contenido (parte de la evidencia, pendiente de contraste) |
| `codificacion.md` | con contenido (parte de la evidencia, pendiente de contraste) |
| `datos.md` | por extraer |
| `pruebas.md` | por extraer |
| `seguridad.md` | por extraer |
| `rendimiento.md` | por extraer |
| `observabilidad.md` | por extraer |
| `errores-frecuentes/README.md` | por extraer |
| `recetas/README.md` | por extraer |
| `evidencia.md` | con contenido (parte de la evidencia, pendiente de contraste) |

La estructura es la de `_plantilla/` (R21, R22): backend, frontend e infraestructura llevan los mismos archivos.
