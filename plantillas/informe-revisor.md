<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: revisor independiente de afirmaciones

Subagente de solo lectura, sin el contexto de quien redactó el texto. No redacta ni corrige: **comprueba**. Se usa antes de publicar un PR de pase o un texto con datos.

## Archivo de afirmaciones (lo genera el motor)
Cabecera: `HASH: {{hash del texto}}` · `TEXTO: {{ruta}}` · `REPO: {{repo}}` · `RAMA: {{rama}}`; luego `C01 … Cnn`, una afirmación por línea.

## Prompt del revisor (completar `{{…}}`)
> Eres un revisor independiente. Comprueba cada afirmación contra la fuente real, no creas el texto. Solo lectura: no edites (salvo el informe), no hagas commit ni push, no publiques, no escribas en bases de datos.
> Fuentes permitidas: {{politica.fuentes-de-revision}} (control de versiones, repositorio remoto, tracker en solo lectura, consultas SELECT a copias, código y flujos de CI). La referencia de «lo validado» es {{rama-validada}}.
> Para cada afirmación: **CONFIRMADA** (con comando y resultado), **REFUTADA** (qué es lo cierto) o **NO VERIFICABLE** (por qué). Si depende de un dato que no pudiste obtener, es NO VERIFICABLE, nunca CONFIRMADA. Si el texto la marca pendiente y lo está, es CONFIRMADA. Atención a estados, orden y alcance del despliegue, cifras, nombres exactos y omisiones. Presupuesto: ~{{35}} llamadas.

## Formato del informe [OBLIGATORIO]
```
HASH: {{el mismo}}
REFUTADAS: {{n}}
NO_VERIFICABLES: {{n}}

| id | veredicto | evidencia |
|---|---|---|
| C01 | CONFIRMADA | {{comando → resultado}} |
(una fila por afirmación, sin saltar ninguna)

OMISIONES: {{lo que el cambio hace y el texto no dice, o «ninguna»}}
```
Después: el motor valida hash, cobertura y cero refutadas. Con refutadas: se corrige el texto (cambia el hash) y se repite. Las NO VERIFICABLES quedan en el texto como `[ ]` o «sin validar». Editar el texto invalida la marca.

## Ejemplo mínimo
```
HASH: 9f8e7d
REFUTADAS: 1
NO_VERIFICABLES: 0
| C01 | CONFIRMADA | git log origin/main..origin/feat/x → 3 commits |
| C02 | REFUTADA | el flujo de CI despliega también el servicio B |
OMISIONES: la migración elimina una columna.
```
