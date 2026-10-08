# Pruebas · Angular + Material
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (protocolo de verificación visual con capturas, checklist visual, técnica de pruebas de extremo a extremo, código de pruebas observado); ver evidencia.md -->

> Qué se prueba y cómo, dobles y datos de prueba, prueba en navegador y pruebas de extremo a extremo. Cada regla lleva un identificador (`PRU-n`). Marco observado: Jasmine + Karma para pruebas unitarias; Cypress + Cucumber para extremo a extremo.

## 1. Unidades

- `PRU-1` Los **mapeadores y funciones puras** se prueban con una tabla de casos, sin `TestBed`: etiquetas de estado, reglas de «editable», cálculos, validación de archivos, normalizador de errores, conversión de fechas.
- `PRU-2` Un **servicio** que encadena llamadas se prueba con un **doble plano de `HttpClient`** (`useValue` con `get`/`post`/`put`/`patch`/`delete` que registran la firma `MÉTODO ruta` en una lista y devuelven `of(...)` o `throwError(...)`). Se aserta la **secuencia** de llamadas y qué pasa cuando un paso falla (`ARQ-8`).
- `PRU-3` Las funciones que dependen de la hora reciben el instante como argumento y se prueban con instantes de borde (cerca de la medianoche, cambio de mes).
- `PRU-4` Una regla de autorización o de estado que el servidor aplica y que la pantalla anticipa (`SEG-4`) tiene **una prueba por regla**: «quien lo registró ve los botones apagados».
- `PRU-5` **Por extraer:** pruebas de componentes con `TestBed`. El origen las tiene (hay pruebas de guarda y del componente raíz) pero no registra una regla de qué cubrir; las pruebas de las funcionalidades recientes son de funciones puras y de servicios.
- `PRU-6` Un `ng test` verde **no** prueba que la pantalla abre: no detecta proveedores de Material que faltan (`COD-45`). La compilación y el tipado acotados al archivo tocado se reportan con su salida real, pero no sustituyen la prueba en navegador.

## 2. Prueba en navegador antes de entregar

Se aplica al terminar toda tarea de pantalla, **antes de decir «listo»**.

- `PRU-7` Se abre cada pantalla tocada en el navegador y se recorre una **matriz mínima**: estados (cargando, vacío, con datos, paginado, error del servidor forzado), cada **rama de negocio** (el camino feliz y cada rama de la regla, con su resultado y su mensaje), perfiles (con y sin el permiso: botón oculto o apagado, ruta bloqueada, solo lectura), entradas (inválida, vacía, límite, texto largo, caracteres especiales), acciones (doble clic, cancelar, cerrar con clic afuera o Esc, repetir tras un error, volver atrás), tema claro y oscuro, tamaños (ancho del diseño, ~992 y ~400 px a 100 % de zoom), textos y datos (todo en el idioma del usuario, el mismo dato igual en pantalla, diálogo y exportación) y archivos (descarga y exportación abiertas de verdad).
- `PRU-8` Un caso que no aplica se anota como «no aplica» con la razón; no se omite en silencio. Lo que no se pudo verificar se declara («no verificado visualmente: X, motivo»); nunca se resume como «listo».
- `PRU-9` Al final de cada flujo se leen los **mensajes de la consola** y las **peticiones de red**: sin errores nuevos ni 4xx/5xx inesperados. Un defecto visto se corrige y **se captura de nuevo**.
- `PRU-10` La evidencia queda como una tabla en la documentación del cambio: pantalla, caso, perfil, tema/ancho, **qué se vio** (texto, estado, color observados; no «se ve bien») y resultado.
- `PRU-11` Se **mide la ventana** antes de juzgar anchos: una pestaña nueva puede abrir a 615 px y el cambio de tamaño responde «ok» sin cambiar nada. Una captura «a 420 px» puede ser la página completa; se verifica el ancho real (por ejemplo con un `iframe` del mismo origen).
- `PRU-12` Lo que se **mide**, no se mira: el **contraste** del texto (recorrer los nodos de texto visibles, calcular la luminancia relativa del color propio y del primer fondo no transparente, `ratio = (max + 0.05) / (min + 0.05)`; revisar los menores de 4.5), los **mensajes recortados** (`scrollWidth > clientWidth` con `text-overflow: ellipsis`), las **peticiones por escritura rápida** (con la red limpia, escribir de corrido: debe salir una sola) y los **estados del botón** (`getComputedStyle(boton).backgroundColor` y `disabled`, con el botón activo y apagado).
- `PRU-13` Las animaciones de entrada de paneles y diálogos tardan 2-3 s: un clic durante la entrada se pierde y una captura temprana muestra el contenido translúcido. Se espera, se mide y luego se hace clic. El primer clic tras cargar la página a veces no hace nada; se confirma con una consulta al DOM que el panel abrió antes de seguir.
- `PRU-14` Datos de prueba: si falta una fila en el estado que hay que ver, se crea en la **base de pruebas** con una marca identificable, se anota y se **restaura** al terminar. Solo se abren y se cancelan los diálogos de acciones con efectos externos (correo, dinero); no se confirman.
- `PRU-15` Una prueba **diseño contra implementación** se hace con la tabla de piezas (igual, mejora, falta, distinto, descartado con razón), mirando la pantalla real y no de memoria; sin ella no se cierra una pantalla.

## 3. Extremo a extremo (Cypress + Cucumber)

- `PRU-16` Un elemento que existe pero queda **fuera del alto del viewport** no pasa `be.visible` ni `filter(':visible')`: se hace `scrollIntoView()` antes de leer o interactuar. Después de bajar, un elemento de «arriba» necesita su propio `scrollIntoView()`.
- `PRU-17` **Registrar el `intercept` antes del clic** que dispara la carga, y también envolver la **carga inicial**: si el intercept se registra después de navegar, el `wait` se resuelve contra la petición inicial vieja y el test sigue con el DOM sin actualizar (parece un defecto del producto y es una carrera). Esperar **todas** las peticiones de las que depende el pintado (`forkJoin`).
- `PRU-18` Un `cy.wait(N)` fijo es frágil o desperdicia tiempo; se espera el alias de la petición real.
- `PRU-19` Un `mat-select` no siempre abre con un clic en el elemento anfitrión: se hace clic en `.mat-mdc-select-trigger` interno antes de asumir un problema de datos.
- `PRU-20` Al capturar texto para compararlo después con `contain.text`, **no se normaliza** el espacio en blanco (la comparación es una subcadena contra el DOM crudo); la normalización queda para comparaciones manuales con `expect`.
- `PRU-21` **Limitación conocida:** una descarga real se guarda, y se puede esperar la petición que la generó y verificar sus parámetros, pero no se puede leer el contenido de un binario con los comandos base; hace falta una `cy.task()` del lado Node con una librería de hoja de cálculo. Evaluar la inversión antes de prometerlo.
- `PRU-22` **Por extraer:** un patrón probado para simular una sesión vencida (corromper el token o forzar un 401). Mockear mal (interceptar un solo endpoint sin que reaccione el interceptor global) da un falso positivo; se revisa primero cómo está armado el interceptor real.
