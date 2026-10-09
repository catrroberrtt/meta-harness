<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-08 · vence: 90d · fuente: metodo/terminado-y-trazabilidad.md -->
# Plantilla: especificación (`especificacion.md`)

Se copia a `cambios/<fecha>-<slug>/especificacion.md` y se llena antes de diseñar. Los identificadores (`RQ-NN`, `CA-NN.n`, `SU-NN`) son lo que enlaza la matriz de trazabilidad; no se renumeran una vez aprobada la especificación (los nuevos se añaden al final). Reglas en `metodo/terminado-y-trazabilidad.md` §3. La comprueba `herramientas/harness-trazabilidad.py`.

## Estructura
```markdown
# Especificación — {{título}}

## Contexto
Problema: {{qué duele y a quién}} · Alcance: {{qué entra}} · Fuera de alcance: {{qué no, y dónde se atiende}} · Tamaño: {{S/M/L}}

## Suposiciones
- SU-01 · {{establecido | de-trabajo | abierto}} · {{texto}} · origen: {{documento, dato o persona}}

## Requisitos
- RQ-01 · Cuando {{disparador}}, el sistema {{respuesta}}.
  - CA-01.1 · Dado {{estado}}, cuando {{acción}}, entonces {{resultado observable: cifra, estado o código}}.
- RQ-02 · [no funcional] {{requisito con número}}.
  - CA-02.1 · {{cómo se mide}}.

## Desafío previo (M y L)
- Cómo falla esto: {{pre-mortem en una línea}}
- Qué suposición lo rompería: {{SU-NN}}
- Alternativa descartada y por qué: {{...}}

## Decisiones
- {{una por línea; si sobrevive al cambio, usar decision-de-arquitectura.md}}

## Aprobación
- [ ] OK explícito de {{aprobador}} ({{fecha}})
```

## Reglas que el guion comprueba
Todo `RQ` con al menos un `CA`; sin identificadores repetidos; `CA` dentro de su `RQ`; niveles de suposición válidos; sin `{{…}}` sin resolver; sin palabras vagas en criterios (aviso); aprobación marcada antes de delegar; ninguna suposición `abierto` al cerrar.

## Ejemplo mínimo
Ver `plantillas/ejemplos/cambio-ejemplo/especificacion.md`.
