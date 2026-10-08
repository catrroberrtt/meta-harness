# Meta harness: especificación (resumen genérico)

<!-- tipo: método · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

La especificación completa contiene datos de la instancia de origen, por lo que aquí solo se resume lo genérico.

## Principios
1. Un documento, un tipo (método, estándar, perfil, negocio, control de cambios, entorno); se enlaza, no se anida.
2. Lo técnico no conoce el proyecto; el negocio no lleva recetas; el control de cambios cuenta lo ocurrido.
3. Especificación primero con criterios de aceptación medibles.
4. Medir, no recordar: lo comprobable se comprueba con un script.

## Capas
1 Método (SDD) · 2 Estándares de ingeniería · 3 Perfiles de stack y adaptadores · 4 Herramientas · 5 Proyecto (instancia, fuera de este repo).

## Modos
`adopt` (proyecto existente, solo lectura, informe para validar), `init` (proyecto nuevo, entrevista y estructura mínima S/M/L), `update` (sincroniza versión, mide, avisa deriva). Idempotente.

## Piso
Validación de la especificación antes de codificar; almacén de documentación en `.md`; gate antes de cerrar; indexación y actualización automática; estándar único de arquitectura y estilo.

## Orquestador SDD
Especificar → validar información → planificar → tareas → implementar → verificar → documentar → crear tickets (si hay adaptador) → actualizar conocimiento.

## Topología
`meta-harness` (capas 1–4, versionado por etiquetas) + una instancia por proyecto (capa 5, con `harness.lock`). Un documento pasa al harness solo si supera la medición (tipo declarado, especificidad 0, sin datos de empresa).

## Origen

Lo aporta la instancia del proyecto; el mapa de migración vive en la instancia (parametrizacion).
