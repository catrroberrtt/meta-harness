<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: patrón de calidad generalizable (y catálogo)

Todo hallazgo generalizable se registra por **fuente** (`qa.destino-patrones`: tracker, repositorio de QA, wiki, revisión de código, diseño), nunca queda solo como nota de sesión. Las familias repetidas pasan a chequeo mecánico.

```markdown
# {{título del patrón}}
**Origen:** {{ronda, fecha, qué pasó}}
## Forma del bug            [OBLIGATORIO]  cómo se reconoce, en general
## Qué hacer antes de cerrar [OBLIGATORIO]  pasos verificables; firma de código a buscar si existe
## Relacionados             enlaces a otros patrones y al flujo de cierre
```
Tras corregir un bug con causa generalizable: escribir el patrón y **barrer el resto del módulo por la misma firma**.

## Variante `catalogo` (observaciones de producto o interfaz)
Entradas con estado: `[completado]` (investigado a fondo, tratamiento validado en 2+ corridas; se toma en cuenta en diseños nuevos) · `[pendiente]` (sin decisión; no se aplica) · `[cerrado, sin corregir]`. El catálogo no es un gestor de errores.

## Ejemplo mínimo
```
# Cambiar el significado de un campo compartido sin listar sus consumidores
Origen: ronda 4 de QA, 2026-10-01.
Forma del bug: se arregla un síntoma tocando el valor de un campo que otros flujos leen.
Qué hacer: listar consumidores; probar la cadena (operación → operación posterior), no solo la tocada.
```
