<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: pull request (formato base + variantes)

Clave `pr.variante` elige una de: `primera-entrega` · `pase-a-produccion` · `correcciones` · `correcciones-corta`. Título según `pr.titulo` (por defecto `<tipo>({{TICKET}}): <resumen>`; en `pase-a-produccion` se añade el sufijo `{{sufijo-de-pase}}`).

## Reglas comunes (obligatorias)
- [OBLIGATORIO] Origen y destino dichos en la primera línea. Un pase a la rama estable sale de la rama limpia, nunca de la rama de integración.
- [OBLIGATORIO] Lo no verificado va como `[ ]`, nunca `[x]`. Cifras y estados con su fuente y fecha.
- [OBLIGATORIO] Cuerpo escrito en un archivo y revisado antes de publicar (ver `metodo/forma-de-trabajo.md` §8).
- Si la rama absorbió un merge de conflicto: decir qué archivos son del cambio y cuáles llegaron de la brecha entre ramas.

## Variante `primera-entrega` (hacia {{rama-de-integracion}})
Cuerpo = las secciones de `pr-cuerpo-pase.md` (8 secciones).

## Variante `pase-a-produccion` (hacia {{rama-estable}})
- Rama construida desde `{{rama-estable}}` actualizada, con exactamente los commits ya validados en `{{rama-de-integracion}}`.
- [OBLIGATORIO] Línea de trazabilidad: «Mismo contenido ya integrado en {{rama-de-integracion}} ({{PR-previo}})».
- Cuerpo = `pr-cuerpo-pase.md`, con el detalle completo; modelo: `{{pr.modelo-de-referencia}}`.

## Variante `correcciones` (segundo PR sobre una feature ya integrada)
```
## Qué resuelve
{{contexto: ambiente donde se vio, ticket}}
**Causa** {{por qué pasaba}}
**Cambios** {{qué se tocó}}
## Pruebas
{{resultados ya corridos, con números reales}}
```
Si mezcla dos controles de cambio: dos secciones separadas.
El título no repite el de la feature original.

## Variante `correcciones-corta`
```
## Resumen
- {{ticket}}: {{una línea}}
## Plan de pruebas
- [ ] {{lo que falta verificar}}
```

## Ejemplo mínimo (datos inventados)
```
fix(PROJ-123): el total de Pedidos ignoraba los descuentos
## Qué resuelve
En el ambiente de pruebas, el total no restaba el descuento (PROJ-123).
**Causa** el cálculo leía el precio de lista.
**Cambios** `pedidos/total.ts` usa el precio con descuento.
## Pruebas
12 casos corridos, 0 diferencias; build y pruebas con código de salida 0 (2026-10-07).
```
