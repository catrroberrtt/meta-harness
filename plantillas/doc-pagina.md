<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: página de documentación (seis secciones fijas)

Secciones por `documentacion.secciones`. Escrita para quien no estuvo en el trabajo: sin jerga interna, sin rutas internas del método, sin credenciales ni datos personales. Cada afirmación se marca **verificada** (fuente y fecha) o **propuesta**.

Orden de trabajo: buscar primero si el tema ya tiene página (no duplicar); si existe, subpágina; si no, una página del tema. La copia local es la fuente; la wiki es la copia publicada.

| Sección | Qué responde |
|---|---|
| 1. Qué cambia y por qué [OBLIGATORIO] | Dos párrafos, sin nombres de archivo |
| 2. Cómo funciona hoy [OBLIGATORIO] | El comportamiento vigente |
| 3. Qué se decidió [OBLIGATORIO] | Decisión y alternativas descartadas con el motivo |
| 4. Cómo se verificó [OBLIGATORIO] | Con números, no adjetivos |
| 5. Qué quedó afuera y por qué [OBLIGATORIO] | Desviaciones y brechas conocidas |
| 6. Riesgos y decisiones abiertas [OBLIGATORIO] | Con nombre de quién decide |

## Variante `hallazgo-numerado` (proyecto con páginas numeradas)
Cabecera: `Proyecto: {{nombre}} · Página: {{N}} · {{título}} · Fecha: {{fecha}} · Estado: {{estado}}`, y las secciones de `ticket-hallazgo.md` (Problema … La solución), sin «Preguntas abiertas». Las páginas fundacionales (análisis, contrato, modelo) son de diseño libre por sección.

## Ejemplo mínimo
```
# Total de Pedidos con descuento
1. Qué cambia: el total ahora resta el descuento.   [verificado 2026-10-07]
3. Qué se decidió: usar el precio final; descartado recalcular en la vista.
4. Cómo se verificó: 12 casos, 0 diferencias.
6. Riesgos: redondeo en descuentos por línea (decide: producto).
```
