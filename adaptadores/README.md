# Adaptadores

<!-- tipo: adaptador · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Un adaptador conecta el método con una herramienta externa de **tickets** o de **documentación**. Disponibles: `jira` (tickets), `confluence` (documentación), `drive-md` (documentación en carpeta de Drive legible en `.md`). Sin adaptador de tickets el flujo de especificación, verificación y documentación funciona igual y deja el rastro en `.md`. Cada subcarpeta describe el contrato y lo propio de la herramienta.

## Origen

Lo aporta la instancia del proyecto; el mapa de migración vive en la instancia (parametrizacion).

<!-- open-design:inicio -->
Adaptador adicional: `diseno-web` (sitios web públicos de una empresa; herramienta de generación externa opcional, con modo manual y puntos de control verificables).
<!-- open-design:fin -->
