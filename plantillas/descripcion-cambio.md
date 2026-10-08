<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: descripción de un cambio, en capas

Ubicación: `{{raiz-documentacion}}/<tema>/<fecha>-<slug>/descripcion.md` (`documentacion.estructura`). Capas por `descripcion.capas`; por defecto cuatro, **siempre todas**, aunque alguna diga «sin cambios» (no omitirla). La QA no va aquí: vive en una carpeta por tema, compartida por todas las fechas.

Cabecera [OBLIGATORIO]: `verificado-contra-git: {{sha}} · {{repo}} · {{fecha}}` (una línea por repo tocado). README corto: qué cambió, por qué (ticket o decisión), estado, enlace al conocimiento.

## Datos
SQL real pegado tal cual, consultas de verificación con el dato real que las confirmó y cómo se llegó al resultado. Sin migración: decirlo y mostrar igual el SQL de lectura.
## Servidor
Qué se implementó **y con qué finalidad** (problema de negocio), funciones nuevas o modificadas con archivo, tipo de respuesta en JSON real, estado verificado contra el historial de git (rama, commit, si llegó a la rama estable).
## Interfaz
Leída del código real: archivos tocados y qué se agregó, con línea o función. Sin cambios: decirlo.
## Diseño
Solo el enlace a la fuente de diseño de la pantalla.

## Documento vivo
Los ajustes posteriores van en el mismo archivo, tras una convergencia: sección `## Ajuste — {{fecha}}` con el mismo nivel de detalle; si vuelven obsoleta una capa, marcarla en vez de borrar. Toda desviación del plan se anota con su motivo.

## Ejemplo mínimo
```
verificado-contra-git: 1a2b3c4 · pedidos-api · 2026-10-07
## Datos   Sin migración. SELECT SUM(precio_final) FROM pedido WHERE id=1001 → 90,00 (2026-10-07)
## Servidor  total.ts usa precioFinal para no mostrar un total mayor al pagado. Respuesta: { "total": 90.00 }
## Interfaz  Sin cambios.
## Diseño   https://design.example.com/p/123
```
