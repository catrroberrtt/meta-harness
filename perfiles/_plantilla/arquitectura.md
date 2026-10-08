# Arquitectura
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: AAAA-MM-DD · vence: 90d · fuente: <qué lo respalda> -->

> **Qué es:** Capas, escalas S/M/L, dónde va cada cosa y reglas de dependencia.

## Qué debe contener

- Las capas y la dirección permitida de las dependencias (quién puede importar a quién).
- La escala S/M/L: qué archivos lleva cada tamaño y cuándo se pasa de uno a otro.
- Una tabla «qué va dónde» (validación de forma, permisos, reglas de negocio, acceso a datos, efectos externos).
- Reglas de dependencia verificables (qué se puede medir con un script y con qué umbral).
- Antipatrones frecuentes con su remedio.

## Cabecera obligatoria

La línea 2 es `<!-- tipo: perfil · capa: 3 -->` y la línea 3 `<!-- revisado: AAAA-MM-DD · vence: 90d · fuente: <qué lo respalda> -->` (la fecha real de la última revisión; «fuente» dice qué respalda el contenido: proyecto observado, estándar, medición).

## Estado

Si todavía no hay contenido: escribir **«por extraer»** y dejar arriba la lista de lo que debe cubrir.
