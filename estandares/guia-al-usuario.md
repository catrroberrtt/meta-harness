# Guía al usuario: textos, estados vacíos, primer uso y gráficos

<!-- tipo: estándar técnico · capa: 2 -->
<!-- revisado: 2026-10-11 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Reglas de experiencia de uso para toda interfaz que el harness ayude a construir. Independientes del stack.
Se **exigen** en sistemas nuevos (entran como criterios de la especificación) y, en un proyecto existente, solo
se **marcan** en el análisis (misma lógica que `seguridad-base.md`).

## 1. Textos
1. Todo campo lleva **placeholder con un ejemplo real**, no el nombre del campo repetido.
2. Los botones **nombran la acción y su objeto** («Guardar artículo»); nunca «Aceptar», «OK» o «Enviar» a secas.
3. Texto claro: frases cortas, voz activa, sin siglas internas.
4. **Texto largo → «Leer más / Leer menos»** (más de ~3 líneas): accesible, sin muros de texto.

## 2. Estados vacíos: orientan, no informan
Cada uno lleva **título que nombra el estado**, **una línea que explica por qué está vacío**, **un CTA** con la
acción que sigue y, cuando aplica, **alternativas**. Un vacío sin acción deja a la persona decidiendo sola.

- **Cero resultados no es cero intención.** Quien buscó ya dijo qué quiere: devolver **lo más cercano que exista**
  antes de que se vaya (sin tildes ni mayúsculas, por prefijo, términos sueltos, mismo grupo), más «Quitar filtros»
  y «Crear “lo buscado”».
- Tipos: primer uso · búsqueda sin resultados · trabajo hecho · permiso o función apagada · error de carga (esto es
  un error, no un vacío).
- **El tono acompaña al momento.** Bandeja al día, carrito, bienvenida: amable, admite humor. Búsqueda sin
  resultados, recepción pendiente: neutro. **Cobro o pago fallido, historial médico o contable, auditoría,
  seguridad, accesos bloqueados: serio y preciso, sin humor ni exclamaciones.**

## 3. Primer uso
El primer uso es el momento de mayor abandono: nadie debe enfrentar una pantalla en blanco.
**Datos de muestra** cargables y quitables (marcados «Ejemplo», nunca mezclados con los reales), **plantillas**
de arranque, **importación** con plantilla descargable, una **lista de arranque** con pasos enlazados y un tablero
con contenido desde el minuto uno. Que la persona vea el producto funcionando antes de invertir tiempo en llenarlo.

## 4. Gráficos
Primera carga profesional: **esqueleto** con las proporciones del gráfico y alto reservado (sin saltos), carga
diferida de la librería sin recuadros en blanco, **entrada animada una sola vez** y transiciones suaves después
(respetando `prefers-reduced-motion`), cifras que cuentan hasta su valor, un resalte con valor flotante, estado
vacío con rango sugerido, y accesibilidad (resumen textual, tabla alternativa, contraste AA).

## 5. Cómo se verifica
Auditor de la interfaz con reglas `campo-sin-ejemplo`, `boton-generico`, `vacio-sin-accion` y
`texto-largo-sin-recorte`; lista de entrega del módulo con los cuatro puntos; capturas reales de un vacío por
búsqueda, un vacío de primer uso y la primera carga de un gráfico. «Sin evidencia» significa que no se vio al leer
el código, no que falte.
