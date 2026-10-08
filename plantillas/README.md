<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantillas

Una plantilla por formato generalizable. Variables `{{…}}`; los campos marcados `[OBLIGATORIO]` no se omiten; cada archivo trae un ejemplo mínimo con datos inventados (Pedidos, PROJ-123). Los formatos propios de un proyecto no son plantillas distintas: son **un formato base más variantes elegibles por una clave de convención** (`convenciones/estandar.md`); la instancia sobrescribe la clave, no la plantilla.

| Grupo | Plantillas |
|---|---|
| Entrega | `pr.md` · `pr-cuerpo-pase.md` · `checklist-entrega.md` |
| Tickets | `ticket-hallazgo.md` · `ticket-cierre.md` · `ticket-jerarquia.md` · `apertura-de-cambio.md` |
| Documentación | `doc-pagina.md` · `doc-hoja-padre.md` · `doc-modelo-y-migraciones.md` · `doc-contrato-api.md` · `casos-de-prueba.md` · `preguntas-abiertas.md` · `conocimiento-modulo.md` · `convergencia.md` · `descripcion-cambio.md` · `estado-del-tema.md` |
| Planificación | `intake.md` · `mapa-reutilizacion.md` · `plan.md` · `manifiesto.md` |
| Verificación y calidad | `evidencia-datos.md` · `informe-revisor.md` · `hallazgo-validado.md` · `mapeo-diseno.md` · `qa-contexto.md` · `qa-revision.md` · `mapa-cobertura.md` · `patron-calidad.md` · `registro-correcciones.md` |

Cada plantilla lleva en su cabecera `tipo` y `revisado/vence/fuente` (ver `metodo/frescura.md`). La forma de usarlas está en `metodo/forma-de-trabajo.md`.

## Origen

Los formatos salen de una instancia de origen; el mapa formato → plantilla vive en la instancia.
