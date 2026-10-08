# Seguridad · Angular + Material
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (convenciones de frontend §3.3 y §7, catálogo pre-QA de diseño y de frontend, código de interceptores y guardas observado como contraste); ver evidencia.md -->

> Autenticación del lado del cliente, autorización en la interfaz, validación de entrada, secretos y revisión. Cada regla lleva un identificador (`SEG-n`). Las reglas `SEG-9` a `SEG-11` son reglas generales de seguridad de Angular **sin evidencia de instancia**: quedan pendientes de revisión humana.

## 1. Autenticación y sesión

- `SEG-1` **El token lo pone un interceptor** (cabecera de autorización) en todas las llamadas; los servicios no lo agregan. Un solo servicio de token (leer, guardar, borrar, decodificar, comprobar vencimiento) es el único que toca el almacenamiento.
- `SEG-2` Una sesión desplazada o invalidada (otro dispositivo, cambio de contraseña, inactividad) llega como un 401 **con código**. El interceptor de errores limpia la sesión, muestra un **diálogo bloqueante** con el motivo y, al cerrarlo, lleva al inicio de sesión, **antes** del aviso genérico. Es idempotente: varios 401 simultáneos abren un solo diálogo.
- `SEG-3` Los códigos de sesión que el cliente comprueba **coinciden** con los del servidor y están en una constante; se documenta en ambos lados.

## 2. Autorización en la interfaz

- `SEG-4` Los permisos de la interfaz son **ayuda, no autoridad**: el servidor sigue decidiendo. Cada regla de autorización o de estado que el servidor aplica y que depende de datos que la pantalla ya tiene (quién lo registró, el estado actual) **se refleja en la pantalla**: el botón se apaga y el motivo se escribe en el idioma del usuario. Se listan las excepciones de prohibición y conflicto del caso de uso y se comprueba que la pantalla anticipa cada una.
- `SEG-5` Toda acción **irreversible o que mueve dinero** pide una **palabra de confirmación escrita**, no solo un botón de aceptar. Un diálogo con contenido para revisar no se cierra con clic afuera (`PAT-11`).
- `SEG-6` Una operación sensible puede exigir **reautenticación puntual** (volver a pedir la contraseña): el servidor responde 401 con un código «falta la credencial» y una razón; el cliente reconoce ese código con una función pura (y la distingue de «credencial inválida» y de otros errores), pide la credencial en un diálogo y reintenta.
- `SEG-7` La ruta lleva su guarda (`canActivate`) con permiso; los elementos, la directiva de permiso; los permisos con enumeración. Un perfil sin el permiso: el endpoint responde 403 y el botón no aparece; con solo lectura no se puede ejecutar. El permiso nuevo se asigna en el origen de datos, no solo en el código.

## 3. Entrada y archivos

- `SEG-8` La validación de archivos del cliente (tipo declarado, tope de tamaño, filas de un lote) es **comodidad**; el servidor las repite sobre el contenido real (`DAT-5`). Los tipos y el tope viven una vez en la carpeta compartida.

## 4. Hallazgos del contraste con el código (requieren decisión)

- `SEG-9` **Texto del servidor como HTML.** Armar un aviso con `enableHtml` interpolando el mensaje del servidor en una cadena HTML convierte en HTML cualquier mensaje controlable por un usuario (un nombre, un valor rechazado). Regla: el texto que viene del servidor se trata como **texto**, nunca como HTML; si hace falta una lista, se construye con elementos y no con cadenas.
- `SEG-10` **Omisión de la sanitización.** Llamar a `bypassSecurityTrustResourceUrl` sobre un valor de entrada deja pasar cualquier URL. Regla: `bypassSecurityTrust*` solo sobre valores que el propio código construyó o que provienen de una lista cerrada, y con el pipe limitado a un caso de uso nombrado.
- `SEG-11` **Dónde se guarda el token.** Guardar el token en el almacenamiento local del navegador lo deja legible por cualquier script de la página. Las alternativas son una cookie `HttpOnly` con protección contra falsificación de petición, o mantenerlo en almacenamiento local con una política de contenido estricta. **Decisión de cada proyecto; no se promueve ninguna**: queda como pregunta abierta.

## 5. Secretos y configuración

- `SEG-12` Las URL base y los datos de entorno salen de la configuración del entorno; **no se hardcodean** y los archivos de entorno reales no se tocan (solo el ejemplo, si se pide).
- `SEG-13` Un cambio que toca inicio de sesión, tokens, permisos, guardas o el interceptor de autenticación pasa por una **revisión de seguridad** además de la de código.
