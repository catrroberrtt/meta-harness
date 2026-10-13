# Pautas de UX para pantallas de gestión (listados, detalles, acciones)

<!-- tipo: estándar técnico · capa: 2 -->
<!-- revisado: 2026-10-13 · vence: 90d · fuente: revisión de una pantalla real contra su diseño en un proyecto de back-office financiero; cada pauta salió de una observación concreta y se comprobó en el navegador -->

Pautas que evitan repetir las mismas correcciones al construir pantallas de cero. Son independientes del stack y de la empresa. Se aplican **además** de lo que dicta el diseño del proyecto: **el diseño manda**; si una pauta choca con él, se anota la diferencia y se decide con el dueño, nunca en silencio.

## 0. Cuando existe el HTML del diseño

**Se replica tal cual**: se extrae su plantilla (estructura, medidas, colores, textos) y sus reglas de cálculo, y se arma el dato para que encaje; no se reinterpreta. Solo se corrigen sus errores evidentes (un título duplicado) y se anota. Lo que el dato real no tiene (por ejemplo, una calificación que nadie guarda) se omite y se dice, no se inventa.

## 1. Listados

1. **Acciones de fila = íconos con tooltip** (y `aria-label`), no texto: «Ver», «Retirar», «Aprobar». El texto solo en las acciones principales de un pie de acciones.
2. **El identificador que abre el detalle se ve como acción** (enlace o botón con ícono), no depende de que el usuario sepa que toda la fila es clicable. Si se hace clicable la fila entera, además hay un ícono visible.
3. **Columnas por contenido, sin espacio sobrante.** Ancho fijo para lo corto (número, fecha, estado, acción), flexible solo para los textos largos; la columna de acción no parte su encabezado en dos líneas. Una nota larga se corta a 2 líneas con el texto completo en tooltip. Se prueba con el nombre real más largo.
4. **Alineación coherente:** números a la derecha, estados y textos a la izquierda, y el mismo criterio en todas las tablas del módulo.
5. **Más información útil antes que más blanco:** si la fila tiene datos que el usuario necesita para decidir (contraparte, monto, vencimiento, estado del contrato), se muestran como columnas.

## 2. Pestañas y filtros

1. **Lo exclusivo es pestaña, no chips ni contadores sueltos.** «Por autorizar / Observados / Por vencer» filtran la lista y son pestañas con su contador; los contadores sueltos parecen botones que no hacen nada.
2. **Varias tablas apiladas en una vista = pestañas** con el número de filas de cada una.
3. Las pestañas de segundo nivel son un **panel de pestañas** (barra con pestañas en mayúsculas y subrayado en la activa) **pegado a la tabla**: sin separación y con la tarjeta de la tabla sin esquinas superiores. Se distinguen a propósito de las píldoras del primer nivel.

## 3. Detalles

1. **El detalle se abre a pedido, debajo de la tabla, con una X para cerrar**, y la vista se desplaza hasta él. No se abre solo con la primera fila (llena y sofoca la pantalla). Un detalle de segundo nivel (por ejemplo, una operación dentro de un aviso) reemplaza el contenido del panel con un «Volver».
2. Un resumen de un registro muestra lo que lo define (estado, fechas, montos, contraparte) y enlaza a lo demás; no repite lo que ya está en la fila.
3. **Todo lo que se adjunta se puede ver** desde la pantalla (visor); lo que no se previsualiza se descarga.

## 4. Datos

1. **Montos con 2 decimales, símbolo de moneda** y **separados por moneda** (S/ y US$ en líneas distintas); nunca se suman monedas distintas ni se rotulan con un aviso («puede mezclar…»).
2. **Cada entidad muestra su propio estado** (el de la operación, el del contrato…), no una etiqueta genérica del contenedor.
3. **Aceptaciones y consentimientos:** quién, qué aceptó, cuándo y desde dónde, con «Ver texto». Mientras el texto legal no esté entregado, se muestra con una marca visible de **demostración · pendiente de Legal**.
4. Un texto que afirma lo que el sistema «todavía no hace» caduca cuando se entrega esa función: se busca y se corrige.

## 4 bis. Documentos generados

1. **Un documento generado se parece a los demás documentos de la empresa** (mismos márgenes, bloque de firma, pie). Se genera con el **servicio de documentos que ya existe**, no con uno nuevo.
2. Antes de reutilizar un servicio compartido se evalúa: (a) ¿la rama o plantilla que se usa ya está en producción y la usa otro flujo?; (b) ¿qué hace ante una entrada desconocida? (si devuelve un documento **en blanco** sin error, se valida el tamaño y se trata como falla); (c) ¿hay **fallback** si cae? (mostrar el mismo contenido como texto); (d) ¿se toca algo que usan otros flujos? Si hace falta una plantilla propia, se agrega **una rama nueva** sin modificar las existentes y con regresión de las demás; (e) los datos se **escapan** antes de entrar al HTML; (f) el entorno (URL y clave) viene de configuración, nunca del código.

## 5. Estados de la pantalla

1. Carga, vacío y error se muestran siempre y son distintos (un error no se confunde con «sin datos»; permite reintentar). Un solo indicador de carga por vista.
2. **Una acción que el servidor va a rechazar se apaga en la pantalla y explica por qué.**
3. Un modal con contenido para revisar no se cierra con clic afuera.
4. **Cambiar de función con trabajo a medias** (por ejemplo, de un registro manual a una lista) **pregunta**: seguir editando, guardar el avance o descartar. El cambio es limpio, no deja el formulario «pegado».

## 6. Tema oscuro y contraste

1. El tema oscuro **se mide, no se mira**: contraste ≥ 4,5:1 para texto y ≥ 3:1 para íconos, con un script en el navegador sobre todos los estados (fila alertada, etiquetas, cabeceras, íconos, botón apagado).
2. Las etiquetas (chips) y los íconos tienen **variantes oscuras** propias; no basta con cambiar el fondo.
3. Los grises secundarios en tema claro también cumplen 4,5:1.

## 7. Estilos

1. Los nombres de clase de un módulo no chocan con los de la librería global (`.alert`, `.card`, `.btn`, `.badge` de Bootstrap): se prefijan o se renombran. Se comprueba listando las clases usadas que existen en las hojas globales.
2. Un botón de librería con color propio se fija con las variables de la librería para sus dos estados (activo y apagado).

## 8. Cómo se verifica

Abrir la pantalla real con datos sembrados que cubran **todos los estados** (incluido vacío, alerta, observado, cerrado, dos monedas, nombres largos), en claro y oscuro, a 992 px y 768 px; compararla con el diseño lado a lado y entregar la tabla «diseño vs implementación» (igual · mejor · falta · distinto · descartado, con la razón). Lo que no se vio se dice «no verificado».
