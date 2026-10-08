# Datos
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: AAAA-MM-DD · vence: 90d · fuente: <qué lo respalda> -->

> **Qué es:** Acceso a datos, migraciones, transacciones y concurrencia (si aplica al stack).

## Qué debe contener

- Cómo se accede a los datos (ORM, SQL propio) y dónde vive cada consulta.
- Migraciones: cómo se escriben, se prueban y se aplican por ambiente.
- Transacciones y bloqueos: orden, alcance y trampas conocidas.
- Particularidades de tipos del motor (decimales, fechas, booleanos) y de la librería.
- Si el stack no tiene datos propios: decirlo y enlazar al perfil que sí los tiene.

## Cabecera obligatoria

La línea 2 es `<!-- tipo: perfil · capa: 3 -->` y la línea 3 `<!-- revisado: AAAA-MM-DD · vence: 90d · fuente: <qué lo respalda> -->` (la fecha real de la última revisión; «fuente» dice qué respalda el contenido: proyecto observado, estándar, medición).

## Estado

Si todavía no hay contenido: escribir **«por extraer»** y dejar arriba la lista de lo que debe cubrir.
