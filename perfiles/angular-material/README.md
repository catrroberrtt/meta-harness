# Perfil: Angular + Material
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (habilidad y referencias del frontend) contrastada con el código de un frontend real; ver evidencia.md -->

Frontend Angular con Angular Material: panel de administración o aplicación de usuario.

## Cuándo SÍ

- Hay un `angular.json` y dependencia de `@angular/material`.
- La interfaz es una aplicación de una sola página con formularios, tablas y diálogos.

## Cuándo NO

- Sitio de contenido estático o de marketing (otro stack).
- Interfaz sin Angular Material (el perfil de diseño no aplica).

## Comandos

`ng build`, `npx tsc --noEmit -p tsconfig.app.json`, `ng test --include=<ruta>` (Jasmine + Karma, acotado al archivo tocado) y `npx prettier --write "<ruta>"` solo sobre los archivos tocados. Nunca un formato global.

## Archivos del perfil

| Archivo | Estado |
|---|---|
| `arquitectura.md` | con contenido (pendiente de evidencia: una sola instancia) |
| `patrones.md` | con contenido (pendiente de evidencia: una sola instancia) |
| `codificacion.md` | con contenido (pendiente de evidencia); accesibilidad más allá del contraste por extraer (`COD-42`) |
| `datos.md` | con contenido (pendiente de evidencia) |
| `pruebas.md` | con contenido (pendiente de evidencia); pruebas de componentes y sesión vencida por extraer (`PRU-5`, `PRU-22`) |
| `seguridad.md` | con contenido (pendiente de evidencia); `SEG-9` a `SEG-11` son reglas generales sin evidencia de instancia, pendientes de revisión humana |
| `rendimiento.md` | con contenido (pendiente de evidencia) |
| `observabilidad.md` | parcial: 4 reglas con evidencia; captura remota, trazas, métricas y alertas por extraer |
| `errores-frecuentes/README.md` | con contenido (36 filas, pendiente de evidencia) |
| `recetas/README.md` | con contenido (12 recetas, pendiente de evidencia) |
| `evidencia.md` | con contenido (tabla regla → fuente → estado y divergencias) |

La estructura es la de `_plantilla/` (R21, R22): backend, frontend e infraestructura llevan los mismos archivos.
