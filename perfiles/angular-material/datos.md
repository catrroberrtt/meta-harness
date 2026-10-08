# Datos · Angular + Material
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (convenciones de frontend §3-§5, guía de diseño reglas del frontend, catálogo pre-QA de frontend y de pruebas contra el entorno, técnica de pruebas de extremo a extremo, código de utilidades de fechas); ver evidencia.md -->

> Contratos de API, estado y caché del cliente, fechas, descargas y exportaciones. Cada regla lleva un identificador (`DAT-n`).

## 1. Contratos de API

- `DAT-1` Se confirma la **forma real** de cada respuesta (paginada con elementos y metadatos, objeto con mensaje y datos, arreglo plano) antes de tiparla, y el tipo del cliente se contrasta **campo por campo** con el DTO del servidor usando el compilador de TypeScript (no memoria ni expresiones regulares).
- `DAT-2` Los métodos del servicio devuelven `Observable<ITipo>` tipado; la URL base sale de la configuración del entorno (con campos para cada API), nunca de un literal.
- `DAT-3` Un dato que el servidor ya calculó se muestra tal cual (`COD-28`, `COD-29`). Si el mismo dato o regla se calcula en 2 lugares (cliente y servidor, o 2 componentes), se extrae una función compartida o se **verifica el mismo caso límite en los dos lados**: clasificaciones y umbrales divergen en silencio.
- `DAT-4` Una enumeración del servidor llega como código técnico; el cliente la traduce con un mapeo a etiqueta (`COD-20`), no la muestra cruda.
- `DAT-5` Las reglas de archivos que el servidor valida (tipos y tope de tamaño, filas máximas de un lote) viven una vez en la carpeta compartida como constantes y una función de validación; **el servidor vuelve a validarlas** (`SEG-8`). Copiar el tope por pantalla da una copia por componente.

## 2. Estado y caché del cliente

- `DAT-6` Una pantalla que combina 2 o más llamadas para pintar un mismo bloque (`forkJoin`) no pinta hasta que **todas** resuelven. Antes de entregarla se **mide** la latencia real contra un entorno real (no con datos locales pequeños). Si es lenta, la primera pregunta es si el dato se puede cachear o materializar en el servidor; si el diseño lo permite, se pinta parcialmente lo que ya llegó.
- `DAT-7` No se cachea sin medir (ver `REN-7`). Un servicio de raíz con caché corta solo para datos compartidos entre pantallas sin relación (`ARQ-20`).
- `DAT-8` Cuando una pestaña o ruta **reutiliza la instancia** del componente, volver a ella no dispara `ngOnInit` de nuevo: completar una acción en otro componente y regresar al listado no lo refresca solo. Hay que forzar el refresco (`@ViewChild` + método público invocado al volver, o navegación con recarga real) y verificar cuál aplica.
- `DAT-9` Volver a un listado después de una acción refresca la tabla **y** sus indicadores (KPI); un asistente terminado vuelve al paso 1.
- `DAT-10` Un cambio de moneda, rango o filtro que dispara varias lecturas espera a las que correspondan (`forkJoin`) y **cancela** las obsoletas; un `unsubscribe` sobre la suscripción anterior o un `switchMap` evita que una respuesta vieja pise a una nueva.
- `DAT-11` Un rango con una sola fecha (solo «desde» o solo «hasta») no manda una petición a medias ni cae a un valor por defecto oculto; se prueba vacío, con una fecha y con las dos. Un valor por defecto de rango que esconde la mayoría de los datos es un defecto de datos, no de estilo.

## 3. Fechas

- `DAT-12` Toda fecha elegible en pantalla va con **selector de calendario en modo de solo lectura**, nunca como texto libre. El año de inicio se elige con una lista.
- `DAT-13` El intercambio con el servidor usa `AAAA-MM-DD` (día de negocio). Se convierte a `Date` local y de vuelta con dos funciones puras (`fromYmd`, `toYmd`) **sin saltos por zona horaria**; no se pasa por `toISOString()` para fechas sin hora.
- `DAT-14` «Hoy» y los cierres de fecha usan el día de la **zona horaria del negocio**, no la conversión del navegador: una función pura `todayInZone(now)` con la hora inyectada, probada con instantes cercanos a la medianoche.
- `DAT-15` En una exportación, las fechas son de tipo fecha de la hoja de cálculo, en la misma zona y el mismo día que en pantalla.

## 4. Descargas y exportaciones

- `DAT-16` Una descarga usa `responseType: 'blob'` y `observe: 'response'` para leer el nombre y el tipo; el archivo a revisar se abre en un visor modal con cierre explícito (`PAT-11`). Un tipo que no se previsualiza (hoja de cálculo) se **descarga**, no falla en el visor. Si se abre una pestaña nueva, se abre **antes** de la petición asíncrona.
- `DAT-17` La exportación a hoja de cálculo la hace **un solo servicio** del proyecto (`ARQ-28`): recibe filas ya resueltas con `{ encabezado, campo, tipo }`, con `tipo` limitado a fecha, número o texto. Para un porcentaje o una moneda se formatea el valor **antes** de mapear la fila.
- `DAT-18` La exportación mantiene las mismas columnas y los mismos textos que la pantalla (incluida la nomenclatura de estados), con montos como **número** con 2 decimales, enteros como enteros, fila de totales si la pantalla los muestra, anchos ajustados al contenido real también con mayúsculas, y un nombre de archivo identificable sin códigos que la pantalla no muestra.
- `DAT-19` Para exportar todo sin paginar, la pantalla pide al servidor sin el parámetro que activa la paginación (según el convenio del servidor), no con un valor «todos» inventado.
- `DAT-20` Un archivo subido con nombre con tildes o eñe se guarda y se muestra igual; se prueba con uno (`Comprobante ñandú.pdf`).
