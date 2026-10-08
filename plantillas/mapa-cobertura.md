<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: comentario de QA troceado y mapa de cobertura

Para un comentario con muchos puntos numerados. Se trocea **una vez**; luego se consulta el mapa, no el original.

1. Fuentes: `qa/fuentes/{{autor}}-comentario-{{id}}-{{sistema}}.md`, un punto por sección.
2. Mapa: `qa/mapa-{{asunto}}.md`, leyendo las descripciones completas (no el título) de los tickets candidatos.

| Punto | Resumen | Ticket que lo cubre | Certeza (confirmada / probable / sin ticket) | Notas |
|---|---|---|---|---|

Artefacto interno de análisis: no se publica tal cual en el tracker ni en la wiki.

## Ejemplo mínimo
| Punto | Resumen | Ticket | Certeza |
|---|---|---|---|
| 7 | El Excel muestra montos como texto | PROJ-141 | confirmada |
