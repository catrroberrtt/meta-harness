<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Convenciones: estándar del harness

Valores por defecto. La instancia copia este archivo a su propio archivo de convenciones y **sobrescribe una clave repitiéndola con otro valor**. Un valor `{{por definir}}` debe resolverse antes de cerrar el primer cambio. Las plantillas leen las claves; cambiar un formato no exige tocar el método ni la plantilla.

## Claves por área
| Clave | Gobierna (plantilla) | Valor por defecto | Alternativas |
|---|---|---|---|
| `ramas.base` | pr, plan | `{{main}}` | cualquier rama |
| `ramas.integracion` | pr | `{{ninguna}}` | rama de pruebas del equipo |
| `ramas.estrategia` | pr | `una-rama` | `limpia-y-puente`, `trunk` |
| `ramas.nombre` | pr | `<tipo>/<tema-corto>` (tipo: feat, fix, chore, docs, refactor) | con clave de ticket |
| `ramas.clave-de-ticket` | pr | `no` | `si` (formato `{{CLAVE-123}}`) |
| `commits.formato` | pr | `<tipo>(<alcance>): <resumen en imperativo, ≤72>` | texto libre |
| `commits.pie` | pr | `{{lo fija el entorno}}` | — |
| `pr.variante` | pr | `correcciones-corta` para cambios chicos; `primera-entrega` y `pase-a-produccion` si hay rama de integración | `primera-entrega`, `pase-a-produccion`, `correcciones`, `correcciones-corta` |
| `pr.titulo` | pr | igual que el commit principal | con sufijo de pase |
| `pr.secciones-pase` | pr-cuerpo-pase | las 8 de la plantilla | lista propia |
| `pr.modelo-de-referencia` | pr | `{{ninguno}}` | un ticket o PR modelo |
| `pr.destino-pase` | pr | `{{ramas.base}}` | — |
| `pr.revisores` | pr | `{{por definir}}` | — |
| `ticket.cuerpo.secciones` | ticket-hallazgo | Problema · Qué sucede · Qué ocasiona · Caso presentado · La solución · Preguntas abiertas · Referencias | lista propia |
| `ticket.jerarquia` | ticket-jerarquia | `una-historia-con-subtareas` | `plano`, `por-persona` |
| `ticket.nombre` | ticket-jerarquia | `[Marca] Título` (si `ticket.marcas` no está vacío) | `Título` |
| `ticket.tipos` | ticket-jerarquia | historia (visible, pasa por QA) · tarea (sin QA) | — |
| `ticket.peso` | ticket-jerarquia | entero 1-10 solo en historia o tarea | sin peso |
| `ticket.estados.story` / `.task` | ticket-jerarquia | `{{Por hacer → En desarrollo → En revisión → Terminado}}` | el workflow real del tracker |
| `ticket.aprobacion-previa` | ticket-jerarquia | `si` (lista y OK antes de crear o transicionar) | — |
| `ticket.cierre-tecnico` | ticket-cierre | `si` | — |
| `ticket.subtarea.prefijo-bloque` | ticket-jerarquia | `si` | `no` |
| `ticket.subtarea.diccionario` | ticket-jerarquia | `si, cuando hay cambio de base` | `no` |
| `documentacion.destino` | doc-* | `{{adaptador de documentación}}` | carpeta local |
| `documentacion.secciones` | doc-pagina | las seis de la plantilla | lista propia |
| `documentacion.completa-antes-de-codificar` | doc-hoja-padre | `M y L` | `siempre`, `nunca` |
| `documentacion.paginas` | doc-hoja-padre | lista de la plantilla | lista propia |
| `documentacion.estructura` | descripcion-cambio | `<tema>/<fecha>-<slug>/` + `qa/` por tema | plana |
| `documentacion.sello` | descripcion-cambio, estado-del-tema | `verificado-contra-git: <sha> · <repo> · <fecha>` | — |
| `descripcion.capas` | descripcion-cambio | Datos · Servidor · Interfaz · Diseño | lista propia |
| `api.sobre-de-respuesta` | doc-contrato-api | `{{por definir}}` | p. ej. `{ data, meta }` |
| `conocimiento.carpetas` | conocimiento-modulo | `{{una carpeta por plataforma o dominio}}` | — |
| `qa.revisiones` | qa-revision | `interfaz` + `servicio` | una sola |
| `qa.fixes-pendientes` | qa-revision | sección obligatoria con tabla | — |
| `qa.auditoria-independiente` | qa-revision | lista mínima de la plantilla | ampliada por perfil |
| `qa.destino-patrones` | patron-calidad | por fuente del hallazgo | por ámbito |
| `plan.ubicacion` | plan | `raiz-del-repo/PLAN-<slug>.md` | carpeta de la implementación |
| `plan.fases` | plan | por variante | lista propia |
| `intake.preguntas` | intake | las siete de la plantilla | ampliadas |
| `evidencia.veredictos` | evidencia-datos | verificado-con-datos · revisado-codigo · bloqueado-acceso | nombres propios |
| `verificacion.topes` | forma-de-trabajo §7 | `{{por definir, medidos}}` | — |
| `gate.pasos` | checklist-entrega | los once del barrido | ampliados |
| `diseno.prioridad` | mapeo-diseno | QA > estilo del producto > diseño | otra |
| `hallazgo.etiquetas` | hallazgo-validado | alarma · observación · histórico | — |
| `terminado.criterios` | (abajo) | seis criterios | ampliados |
| `idioma` | todas | `{{idioma de la persona}}`, también en notas intermedias | — |
| `respuesta.estilo` | forma-de-trabajo §9 | conclusión primero, tablas, evidencia corta | — |
| `politica.fuentes-de-revision` | informe-revisor | `{{por definir}}` | — |

## Definición de «terminado» (`terminado.criterios`)
1. La especificación tiene criterios de aceptación medibles y se cumplen.
2. El gate de calidad pasa (compilación, pruebas, lint), ejecutado y con código de salida.
3. Verificado con datos o ejecución real, no solo por lectura; lo no verificado se declara.
4. Todas las capas completas (servidor, interfaz, infraestructura si aplica).
5. Documentación y tickets al día, con enlaces completos.
6. Conocimiento e índices actualizados; procesos de prueba apagados y datos de prueba limpios.

## QA (valores por defecto)
Informe: alcance, casos (entrada y resultado observado), hallazgos con severidad, evidencia, veredicto. Un hallazgo sin evidencia observable no se da por resuelto.
