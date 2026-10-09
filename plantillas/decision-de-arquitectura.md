<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-08 · vence: 90d · fuente: metodo/terminado-y-trazabilidad.md -->
# Plantilla: decisión de arquitectura (ADR corto)

Para decisiones que sobreviven al cambio (un límite entre módulos, una dependencia, un formato de datos). Las decisiones locales de un cambio van una por línea en su `especificacion.md`. Una decisión no se borra: si cambia, se escribe otra que la sustituye.

## Estructura
```markdown
# DA-{{NNN}} — {{título}}
Estado: {{propuesta | aceptada | sustituida por DA-NNN}} · Fecha: {{AAAA-MM-DD}} · Decide: {{quién}}

## Contexto
{{qué fuerzas empujan: requisitos RQ-NN, restricciones, lo que ya existe}}

## Decisión
{{qué se hace, en una o dos frases}}

## Alternativas descartadas
- {{alternativa}} — {{por qué no}}

## Consecuencias
Buenas: {{...}} · Costos o riesgos: {{...}} · Cómo se sabrá que fue un error: {{señal medible}}
```

## Ejemplo mínimo
```
# DA-001 — Las entregas viven en tabla propia
Estado: aceptada · Fecha: 2026-01-10 · Decide: responsable técnico
Contexto: RQ-01 pide entregas parciales; Pedido ya tiene muchas columnas.
Decisión: tabla entrega (pedido_id, cantidad, fecha); el saldo se calcula, no se guarda.
Alternativas: columna cantidad_entregada en Pedido — no deja historial.
Consecuencias: una consulta más al leer; señal de error: listados lentos con >10 entregas por pedido.
```
