# meta-harness

<!-- tipo: guia · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Entorno de trabajo dirigido por especificaciones (SDD), reutilizable e **independiente de cualquier empresa**: método, estándares de ingeniería, perfiles de stack, adaptadores, herramientas, hooks y un instalador. Empezar o entrar a un proyecto es **instanciar**, no rehacer. Este repositorio no contiene datos de ningún proyecto; el conocimiento propio de cada uno vive en su **instancia**, que fija la versión del harness en un archivo `harness.lock`. Versión actual: ver `VERSION`.

## Capas

| Capa | Carpeta | Contenido |
|---|---|---|
| 1 · Método | `metodo/`, `plantillas/`, `convenciones/` | Ciclo SDD, plantillas, definición de «terminado» |
| 2 · Estándares | `estandares/` | Arquitectura, paradigmas, seguridad, datos, frontend, patrones de calidad |
| 3 · Perfiles y adaptadores | `perfiles/`, `adaptadores/` | Stack (`nestjs-typeorm-mysql`, `angular-material`, `aws-ecs`) y herramientas externas (`jira`, `confluence`, `drive-md`) |
| 4 · Herramientas | `herramientas/`, `hooks/`, `instalador/` | Detección, clasificación, gate, lint, hooks, instalador |
| 5 · Proyecto | (fuera de este repo) | Negocio, control de cambios, entorno, memoria: la instancia |

Todo documento declara su tipo: `<!-- tipo: … · capa: N -->`.

## Ejes de adaptación

El stack es solo uno de los ejes. Lo que cambia entre proyectos: **stack** (perfil), **gestión de trabajo** (Jira, GitHub Issues o ninguna), **almacén de documentación** (Confluence, carpeta de Drive legible en `.md` o `docs/` del repositorio) y **convenciones** (PR, QA, tickets, ramas y commits, definición de «terminado»).

## Los tres modos del instalador

| Modo | Cuándo | Qué hace |
|---|---|---|
| `adopt <carpeta>` | Proyecto existente | Analiza stack, convenciones vigentes, documentación, pruebas y CI; emite el informe «cómo es este proyecto» para validar. **No modifica el código.** |
| `init` | Proyecto nuevo o vacío | Entrevista corta y estructura mínima con la escala S/M/L que corresponda. *(pendiente, fase 7)* |
| `update` | Ya instalado | Sincroniza la versión, vuelve a medir y avisa de la deriva. *(pendiente, fase 7)* |

El instalador es idempotente: correrlo otra vez equivale a `update`.

## El piso (no un techo)

En los tres modos se instala como mínimo: (a) toda especificación se valida **antes** de escribir código; (b) un almacén de documentación legible en `.md`; (c) el gate de calidad corre antes de cerrar; (d) indexación del código (CodeGraph, fff, búsqueda semántica) y actualización automática; (e) un único estándar de arquitectura y estilo. Todo lo demás depende del proyecto.

## Cómo se instala una instancia

1. Clonar este repositorio en una versión etiquetada.
2. `bash instalador/instalar.sh adopt <carpeta-del-proyecto>` para obtener el informe y validarlo con el equipo (o `init` en un proyecto nuevo).
3. La instancia fija la versión en `harness.lock`, guarda sus convenciones (partiendo de `convenciones/estandar.md`) y su conocimiento propio.
4. Las acciones hacia afuera (crear repositorios, pedir permisos, publicar) se muestran y esperan confirmación; nunca se guardan credenciales.

## Estado

Esqueleto (0.1.x): estructura, contratos de adaptadores, plantilla de convenciones, `adopt` funcional y dos herramientas genéricas. El resto de documentos llega a cada carpeta solo cuando supera la medición (tipo declarado y especificidad 0).
