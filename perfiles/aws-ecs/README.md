# Perfil: AWS ECS
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (documentos de infraestructura y repositorios de infraestructura como código de la instancia, leídos en solo lectura); ver evidencia.md -->

Despliegue en AWS ECS (Fargate) con infraestructura como código.

## Cuándo SÍ

- Hay definición de infraestructura como código (CDK o equivalente) con servicios ECS.
- El backend corre en contenedores con migraciones en el despliegue.

## Cuándo NO

- Funciones sin servidor puras (otro perfil).
- Otro proveedor de nube.

## Comandos

`npm run validate` (tipos + pruebas), `npx cdk synth -c env=<ambiente>`, `npx cdk diff --all -c env=<ambiente>` y `npx cdk deploy <Pila> -c env=<ambiente>`; para un servicio: `aws ecs wait services-stable` y `aws ecs update-service --force-new-deployment`. Los comandos son los de la instancia de origen (CDK); con otra herramienta de IaC se sustituyen por sus equivalentes de síntesis, diferencias y despliegue.

## Archivos del perfil

| Archivo | Estado |
|---|---|
| `arquitectura.md` | con contenido (24 reglas; pendiente de contraste) |
| `patrones.md` | con contenido (10 patrones; pendiente de contraste) |
| `codificacion.md` | con contenido (21 reglas; pendiente de contraste) |
| `datos.md` | con contenido (15 reglas; pendiente de contraste); simulacros y réplicas por extraer |
| `pruebas.md` | con contenido (10 reglas; pendiente de contraste); carga y simulacros por extraer |
| `seguridad.md` | con contenido (19 reglas; pendiente de contraste) |
| `rendimiento.md` | con contenido (13 reglas; pendiente de contraste); mediciones por extraer |
| `observabilidad.md` | con contenido (12 reglas; pendiente de contraste); trazas, SLO y alarmas de colas por extraer |
| `errores-frecuentes/README.md` | con contenido (20 patrones; pendiente de contraste) |
| `recetas/README.md` | con contenido (8 recetas; pendiente de contraste); tres recetas por extraer |
| `evidencia.md` | con contenido (todas las reglas, pendientes de evidencia) |

La estructura es la de `_plantilla/` (R21, R22): backend, frontend e infraestructura llevan los mismos archivos.
