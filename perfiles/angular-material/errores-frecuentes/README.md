# Errores frecuentes · Angular + Material
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (catálogo pre-QA de diseño y de frontend, catálogo de hallazgos de interfaz, checklist visual, convenciones de frontend); ver evidencia.md -->

> Patrones de calidad de este stack, con su síntoma, su causa y la regla o receta que lo evita. Cada fila lleva un identificador (`ERR-n`). Todos vienen de incidentes reales de **una sola instancia**; los que se repitieron 2 o más veces ahí van primero.

| ID | Error | Síntoma | Causa y receta | Regla |
|---|---|---|---|---|
| `ERR-1` | Suscripción sin final | Callbacks sobre componentes destruidos, memoria que crece | `valueChanges`, `paramMap`, `Subject`, `interval` sin `takeUntilDestroyed` → cerrar con el operador o no suscribirse | `COD-5` |
| `ERR-2` | `subscribe` anidado | Orden impredecible, errores no propagados | Encadenar con `switchMap`/`concatMap`/`exhaustMap` | `COD-7` |
| `ERR-3` | `catchError` fuera del `switchMap` | El primer error deja los filtros muertos | Mover `catchError` dentro del `switchMap` | `COD-8` |
| `ERR-4` | Doble clic en una acción de dinero o estado | Dos peticiones; el segundo falla con 500 o duplica | `exhaustMap` + botón apagado mientras hay una en curso | `COD-9`, `REN-10` |
| `ERR-5` | Botón de Material con `background` fijo | El botón activo sale del color equivocado y el apagado parece activo | Variables `--mdc-filled-button-*` en lugar de `background:`; verificar con `getComputedStyle` | `COD-37` |
| `ERR-6` | Estilos de botones de Material en estado apagado sin diseñar | Un botón deshabilitado se ve igual que uno activo | Estilo propio para `:disabled` (p. ej. un rojo claro) | `COD-37` |
| `ERR-7` | `mat-select` con opción de valor `null` | Vuelve al marcador de posición en vez de «Todas» | Valor centinela (cadena vacía) solo para el enlace | `PAT-13` |
| `ERR-8` | `No provider found for DateAdapter` | La pantalla da error al abrirse; las pruebas unitarias pasan | `provideNativeDateAdapter()` y `MAT_DATE_LOCALE` en el propio componente; probar en navegador | `COD-45`, `PRU-6` |
| `ERR-9` | Clase CSS definida en otro componente | El estilo no aplica y nadie avisa (no hay error de compilación) | Definirla en el SCSS del componente que la usa | `COD-32` |
| `ERR-10` | `width` fijo en px copiado del diseño | El contenedor no fluye; el diseño «justo» se rompe con la barra lateral | Proporciones, `fr` o `%`; probar 4 anchos | `COD-33` |
| `ERR-11` | Cifras numéricas partidas en un bloque angosto | Montos que se parten a media línea o «chocan» | `nowrap` + `tabular-nums` en todas las columnas de monto, con desplazamiento propio | `COD-34` |
| `ERR-12` | Rejilla de ratio fijo sin `min-width: 0` | Nombres largos cortados, columna con la mitad de ancho que su contenido | `min-width: 0`, elipsis y `title`; ratio según contenido real | `COD-36` |
| `ERR-13` | Pista de campo que se parte en dos líneas | La pista pisa la etiqueta del campo de abajo | Acortar o `subscriptSizing="dynamic"` solo en ese campo | `COD-38` |
| `ERR-14` | Espaciado duplicado con el contenedor padre | Una pantalla con el doble de espacio que sus hermanas | Revisar el relleno del contenedor compartido antes de agregar margen | `COD-35` |
| `ERR-15` | Diálogo de revisión que se cierra con clic afuera | Se pierde el contexto que costó abrir | `disableClose: true` | `PAT-11` |
| `ERR-16` | Volver a un listado no lo refresca | La acción parece no haberse registrado | Refresco explícito (`@ViewChild` + método público) o recarga real | `DAT-8`, `DAT-9` |
| `ERR-17` | El cliente recalcula lo que el servidor ya calculó | El valor se aplica dos veces (saldo nuevo = anterior + cambio) | Mostrar el valor de la respuesta | `COD-29` |
| `ERR-18` | Monto redondeado al pintarlo | `1` en lugar de `1.40`; un monto redondo oculta el defecto | Sin `toFixed`/`Math.round`/`0 decimales` sobre campos monetarios; probar con centavos | `COD-28` |
| `ERR-19` | Tres formas de formatear dinero | Mismo monto con distinto resultado en tarjeta, tabla y exportación | Una función y un pipe; una sola fuente | `COD-30` |
| `ERR-20` | Código de moneda en lugar del símbolo, y un componente hijo que no lo recibe | Un monto sale con el código de moneda y el resto con el símbolo | Resolver el símbolo en el padre y pasarlo; revisar la cadena padre-hijo | `COD-31` |
| `ERR-21` | Enumeración interna visible | `CONTRACT`, `TRANSFER_IN` en pantalla | Mapeo a etiqueta, reutilizando el existente | `COD-20` |
| `ERR-22` | Texto de estado desactualizado | «aún no se envía» cuando ya se envía | Buscar `aún no`, `todavía no`, `próximamente` cada vez que algo pasa de pendiente a existe | `COD-40` |
| `ERR-23` | Acción que el servidor prohíbe, activa en pantalla | El usuario hace clic y recibe un error | Apagar el botón y escribir el motivo | `SEG-4` |
| `ERR-24` | Texto del botón que promete menos de lo que hace | «Ver» que además cambia una selección o avanza un asistente | El verbo refleja el efecto real: «Elegir», «Seleccionar» | `PAT-12` |
| `ERR-25` | Título del encabezado de la ruta equivocado | Dos rutas con prefijo común muestran el título de la primera | Nombrarlas sin prefijo común (cliente y servidor) | `ARQ-5` |
| `ERR-26` | Sintaxis `@else if (x; as o)` | Error de compilación | Anidar los `@if` | `COD-19` |
| `ERR-27` | Función que recorre un arreglo dentro de la plantilla | La pantalla se congela | Calcular antes (mapeador, `computed`) | `COD-17` |
| `ERR-28` | Dos indicadores de carga superpuestos | Spinner doble | Uno por vista | `PAT-12`, `REN-12` |
| `ERR-29` | Rango con una sola fecha | Petición a medias o valor por defecto oculto | Probar vacío, una fecha y dos | `DAT-11` |
| `ERR-30` | Duplicar un servicio por buscar mal | Servicio de utilidad nuevo cuando ya existía | Buscar por la librería importada | `ARQ-27` |
| `ERR-31` | Constante o validación copiada por pantalla | El mismo tope en 6 componentes | Carpeta compartida | `ARQ-10`, `DAT-5` |
| `ERR-32` | Un código de error como literal en el componente | No se puede rastrear ni refactorizar | Constante exportada | `ARQ-15` |
| `ERR-33` | Formato global del repositorio | Cientos de archivos ajenos reescritos | Prettier acotado a los archivos tocados | `COD-44` |
| `ERR-34` | Esperar solo una de dos peticiones en una prueba E2E | Prueba intermitente, aparente defecto del producto | Esperar todos los alias y envolver la carga inicial | `PRU-17` |
| `ERR-35` | «Compila» tomado por «funciona» | Pantalla rota que pasa las pruebas | Prueba en navegador con capturas y consola | `PRU-6`, `PRU-7` |
| `ERR-36` | Regla de autorización sin prueba | Un perfil sin permiso ve el botón o el 403 llega sin avisar | Una prueba por regla de autorización | `PRU-4`, `SEG-7` |

## Cómo se usa

Antes de pedir una revisión se recorre esta tabla contra el diff. Una clase de error que aparece **2 o más veces** debe volverse un chequeo mecánico, no un recordatorio. `ERR-n` apunta a la regla (donde está el porqué) y la receta (`recetas/README.md`) cuando existe.
