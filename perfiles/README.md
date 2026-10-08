# Perfiles de stack
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: especificación del harness §12 y §14 -->

Un perfil por stack; se elige por proyecto según la necesidad, sin sobreingeniería. Backend, frontend e infraestructura son perfiles con **la misma estructura**, la de `_plantilla/` (la comprueba `herramientas/harness-lint-perfiles.py`).

| Perfil | Rol | Estado |
|---|---|---|
| `nestjs-typeorm-mysql` | backend | arquitectura, patrones y codificación con contenido; resto por extraer |
| `angular-material` | frontend | por extraer |
| `aws-ecs` | infraestructura | por extraer |

## Estructura obligatoria de un perfil

`README.md`, `arquitectura.md`, `patrones.md`, `codificacion.md`, `datos.md`, `pruebas.md`, `seguridad.md`, `rendimiento.md`, `observabilidad.md`, `errores-frecuentes/README.md`, `recetas/README.md`, `evidencia.md`.

## Cabecera de todo documento

Línea 2 `<!-- tipo: perfil · capa: 3 -->`; línea 3 `<!-- revisado: AAAA-MM-DD · vence: 90d · fuente: <qué lo respalda> -->`. Un documento vencido bloquea la liberación (R25).

## Origen

Lo aporta la instancia del proyecto; solo se promueve con evidencia registrada y decisión humana (R24).
