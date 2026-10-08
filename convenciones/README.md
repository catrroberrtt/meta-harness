<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Convenciones

El harness trae valores por defecto (`estandar.md`); cada proyecto tiene **su propio archivo de convenciones** (en su instancia) con las mismas claves. Las plantillas y el método leen las claves, nunca valores fijos.

## Cómo se resuelve un valor
1. Lo **detectado** en el proyecto (plantillas de PR, historial de commits, tickets recientes, vía el detector).
2. Si no hay, el **estándar** del harness.
3. Lo que el **equipo indique** manda sobre ambos.
El valor efectivo se registra en el archivo de convenciones de la instancia.

## Cómo una instancia sobrescribe el estándar
- Copia `estandar.md` a su archivo de convenciones y **repite la clave con su valor**: `pr.variante: pase-a-produccion`. Lo que no repite se hereda.
- Las claves de lista (`ticket.estados.story`, `pr.secciones-pase`, `gate.pasos`, `intake.preguntas`) se reemplazan completas, o se extienden con `+` delante del valor.
- Una clave que la instancia añade y el estándar no conoce es válida; la plantilla que la use la declara.
- Cambiar el formato de un PR, ticket o QA no exige tocar el método ni las plantillas; una prueba lo comprueba.
- Un campo `{{por definir}}` bloquea el primer cierre de cambio.

## Qué claves gobiernan qué
Ver la tabla de `estandar.md` (columna «Gobierna»). Resumen: ramas y commits → `pr`; ticket → `ticket-*`; documentación → `doc-*`, `descripcion-cambio`; QA → `qa-*`, `patron-calidad`; verificación → `evidencia-datos`, `informe-revisor`; terminado → `checklist-entrega`.

## Origen

Lo aporta cada instancia; el mapa de migración vive en la instancia.
