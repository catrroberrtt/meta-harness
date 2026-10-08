# Herramientas

<!-- tipo: herramienta · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Scripts parametrizados que miden en vez de recordar: detección de proyecto (modo `adopt`), clasificación de documentos por tipo y especificidad, y a futuro gate, lint y extractor.

- `harness-detectar.py <carpeta> [--json]`: informe de solo lectura «cómo es este proyecto».
- `clasificar-skill.py [--md]`: inventario de tipo, tecnicidad y especificidad; el patrón de lo «propio del proyecto» se fija con `HARNESS_PATRON_PROYECTO` o `patrones-proyecto.txt`.

## Origen

Lo aporta la instancia del proyecto; el mapa de migración vive en la instancia (parametrizacion).

## Patrones de la instancia

Una instancia aporta su propio `patrones-proyecto.txt` (una regex por línea, `#` para comentarios) en la raíz que se analiza.
Alternativamente se define la variable de entorno `HARNESS_PATRON_PROYECTO`; sin ninguno se usa el patrón genérico.
El harness nunca guarda esos patrones: pertenecen a la instancia.
