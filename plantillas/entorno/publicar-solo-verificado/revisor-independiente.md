# Revisor independiente de afirmaciones (nivel 2)

Lo hace **otra persona o un agente de solo lectura sin el contexto de quien escribió el texto**. No redacta ni corrige:
comprueba. Su valor es no compartir las suposiciones del autor.

## Qué recibe
El archivo `<texto>.afirmaciones.md` que deja `scripts/verificar-publicacion.py revisar`: una cabecera (HASH, TEXTO, REPO) y
afirmaciones numeradas `C01`, `C02`… Si hay avisos del motor, cada uno debe resolverse.

## Fuentes permitidas (solo lectura)
Las que declare este repo: su historial git y sus archivos, y las fuentes de `[[publicar.referencias]]` en `entorno.toml`.
Nada de escribir, commitear, subir ni publicar. Lo que la fuente dice manda sobre lo que el texto cree.

## Veredicto por afirmación
- **CONFIRMADA** con la evidencia (comando y resultado resumido).
- **REFUTADA** y qué es lo cierto.
- **NO VERIFICABLE** y por qué. Una afirmación que depende de un dato que no se pudo obtener **nunca** es CONFIRMADA.
  Si el texto la marca como pendiente y lo está, cuenta como CONFIRMADA: el texto es honesto.

Presta atención a estados («cerrado», «pendiente»), cifras, nombres exactos y a **omisiones**: algo que el cambio hace y el
texto no dice.

## Formato del informe (exacto)
```
HASH: <el mismo HASH de la cabecera>
REFUTADAS: <n>
NO_VERIFICABLES: <n>

| id | veredicto | evidencia |
|---|---|---|
| C01 | CONFIRMADA | <comando → resultado> |
(una fila por afirmación, sin saltar ninguna)

OMISIONES: <lo que falta decir, o «ninguna»>
```
Luego: `python3 scripts/verificar-publicacion.py confirmar <texto> <informe>`.
