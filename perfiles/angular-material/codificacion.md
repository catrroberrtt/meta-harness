# Codificación · Angular + Material
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (guía de diseño §0.5 y §7.1, reglas aprendidas del frontend, convenciones de frontend §5-§8, checklist visual, catálogo de hallazgos de interfaz); ver evidencia.md -->

> Paradigma reactivo, ciclo de vida, plantillas, nombres, errores de API, tipos, formato de valores, estilos SCSS y accesibilidad medible. Cada regla lleva un identificador (`COD-n`). Se lee **al empezar a escribir**.

## 1. Paradigma: el componente es vista; las reglas son funciones puras

- `COD-1` El componente guarda estado de interfaz y plantilla. Las reglas (estados, etiquetas, cálculos, formato) son **funciones puras** del mapeador: entran datos, salen datos, sin E/S ni `new Date()` interno si la hora importa (se pasa como argumento).
- `COD-2` Lo asíncrono es **declarativo**: RxJS con `switchMap`/`concatMap`/`exhaustMap`, `catchError` y `async` pipe; sin `subscribe` anidados.
- `COD-3` Composición sobre herencia: no hay clase base de componentes de lista.
- `COD-4` Datos como estructuras planas: `interface`/`type`, `readonly` cuando cruzan capas, `as const` para catálogos (códigos de error, tipos de archivo).

## 2. Programación reactiva: toda suscripción termina de forma explícita

- `COD-5` Una suscripción manual tiene final explícito: `takeUntilDestroyed(destroyRef)` (Angular 16 o más), `take(1)`/`first()` para un valor, o no suscribirse (`async`, `toSignal`). Los flujos de larga vida (`valueChanges`, `statusChanges`, `paramMap`, `queryParams`, `router.events`, `fromEvent`, `interval`, `Subject`) sin final son una **falla** (fuga y llamadas sobre un componente destruido). Una llamada HTTP de un disparo completa sola, pero lleva el operador también si su callback toca el estado del componente (diálogos incluidos); cuesta una línea. La instancia de origen deja sin cancelar las peticiones de un solo disparo cuyo callback no toca estado; **las dos posturas coexisten** (ver `evidencia.md`, divergencias).
- `COD-6` Preferir no suscribirse: `@if (datos$ | async; as datos)` una sola vez por observable (dos `| async` son dos peticiones) o `toSignal(datos$)`. Se suscribe a mano solo para efectos (aviso, navegación, escritura).
- `COD-7` **Nunca `subscribe` dentro de `subscribe`**: se encadena con `switchMap`, `concatMap`, `exhaustMap` o `mergeMap`.
- `COD-8` Filtros, búsqueda y paginación que disparan la misma lectura son **un solo flujo de parámetros**, no un `load()` llamado desde cinco sitios:
  - `debounceTime` + `distinctUntilChanged` sobre el texto;
  - `switchMap` en lecturas (cancela la anterior; evita que una respuesta lenta pise a una nueva);
  - `catchError` **dentro** del `switchMap` (fuera, el primer error mata el flujo de filtros);
  - cambiar un filtro **reinicia la página a 1** dentro del mismo flujo;
  - cargando, vacío y error salen del flujo (`startWith`, `finalize`), no de banderas sueltas.
- `COD-9` Operador por intención: `switchMap` = importa solo la última (búsquedas, detalle); `exhaustMap` = ignora lo nuevo mientras hay uno en curso (**guardar, validar, pagar: previene el doble clic**); `concatMap` = en orden, uno a uno; `mergeMap(fn, concurrencia)` = paralelo con tope (5 o menos), nunca sin tope sobre N elementos; `forkJoin` = varias llamadas independientes que completan (cargas iniciales); `combineLatest` = varias fuentes vivas; `merge` = eventos de varias fuentes.
- `COD-10` Errores: `catchError` en el borde de cada llamada (devuelve un valor por defecto o relanza con el mensaje normalizado, `COD-24`). `retry` solo en lecturas idempotentes; **nunca en un POST que mueve dinero o estado**.
- `COD-11` Subjects privados, expuestos con `asObservable()`, completados en `ngOnDestroy` si el componente los posee. `shareReplay({ bufferSize: 1, refCount: true })` (sin `refCount: true` la suscripción interna nunca se cierra).
- `COD-12` Una escritura que depende de varias llamadas lleva su orden y su manejo de error en el **servicio**, no en el componente (`ARQ-8`).

## 3. Ciclo de vida, señales y detección de cambios

- `COD-13` El constructor solo inyecta; la inicialización va en `ngOnInit`; se reacciona a un `@Input` con `ngOnChanges`, setters o signals; la lógica de negocio no vive en los hooks.
- `COD-14` `ngOnDestroy` solo si hay recursos manuales: URL de objeto (`revokeObjectURL`), escuchas del DOM, temporizadores.
- `COD-15` Los componentes de presentación (`@Input` + eventos) usan `ChangeDetectionStrategy.OnPush`.
- `COD-16` Estado local de vista con `signal()` y `computed()`; el puente con RxJS es `toSignal`/`toObservable`. No se mezclan dos formas de estado para el mismo dato.

## 4. Plantillas

- `COD-17` **Nada que calcule o recorra en la plantilla**: sin llamadas de método con `filter`/`map`/arreglos nuevos (congelan la pantalla al renderizar). El valor llega calculado desde el mapeador (o memoizado, o con `OnPush`).
- `COD-18` En `@for`, siempre `track` por identidad estable (id); nunca por índice si la lista cambia.
- `COD-19` Control de flujo nuevo: `@else if (x; as o)` no es válido; se anidan los `@if`.
- `COD-20` Ningún valor de una enumeración interna (estado, tipo, código técnico) se interpola directo: toda enumeración que llega a pantalla tiene un mapeo a etiqueta en el idioma del usuario, y si ya existe en otro punto de la funcionalidad se **reutiliza**, no se vuelve a inventar.

## 5. Nombres, errores de API y tipos

- `COD-21` Archivos en kebab-case: `<nombre>.component.{ts,html,scss}`, `<nombre>.service.ts`, `<nombre>.interface.ts`, `<nombre>.mapper.ts`. Los selectores llevan el prefijo de la aplicación.
- `COD-22` Las interfaces de API viven en una carpeta de interfaces, con prefijo `I`; `import type` cuando solo se necesita el tipo. Se confirma la forma real de cada respuesta (paginada con elementos y metadatos, objeto con mensaje y datos, arreglo plano) en lugar de suponerla.
- `COD-23` Se importa con alias de ruta (`@/…`) en vez de rutas relativas largas.
- `COD-24` **Un normalizador de errores** (`apiError(err) -> { code, message }`) saca el código y el mensaje del cuerpo del error y da un texto por defecto cuando falta; los códigos que el cliente compara están en una constante exportada. El componente no abre el cuerpo del error a mano.
- `COD-25` Evitar `any` y escribir interfaces reales; `@Input({ required: true })` para entradas obligatorias. El proyecto de origen trabaja con `strict` apagado y `strictTemplates` apagado; **no es un modelo a imitar** (ver `evidencia.md`).
- `COD-26` Los permisos se escriben con la enumeración de permisos y los estados con funciones del mapeador; no hay cadenas sueltas en los componentes.

## 6. Formato de valores

- `COD-27` **Preguntar, no asumir**: un `0.42` puede ser 42 % o 0,42 %. El formato de cada campo (fracción o porcentaje, moneda, decimales, zona horaria) se define campo por campo antes de pintar.
- `COD-28` Si el servidor ya devuelve un monto con sus decimales reales, la pantalla lo muestra **tal cual**; no se redondea ni se trunca al formatear (`toFixed`, `Math.round`, un pipe con 0 decimales). Se prueba con un monto con centavos distintos de cero, porque uno redondo no revela el defecto.
- `COD-29` Si el servidor devuelve el resultado final de una operación (saldo nuevo, total), el cliente lo **muestra**; no lo recalcula sumando el cambio al estado anterior (doble conteo).
- `COD-30` La misma cifra en tarjeta, tabla, barra y exportación sale de **una** fuente. Una sola forma de formatear dinero en todo el proyecto: no conviven el pipe `number`, `toFixed` y `toLocaleString`.
- `COD-31` Símbolo de moneda y no código en pantalla; un porcentaje no lleva símbolo de moneda; un ratio en fracción se multiplica por 100 una sola vez.

## 7. Estilos SCSS por componente y accesibilidad medible

- `COD-32` Los estilos van en el SCSS del propio componente (`styleUrl`); nada global ni CSS suelto. **Cada clase usada en la plantilla está definida en el SCSS de ese componente**: los estilos están encapsulados y una clase que solo existe en un componente hermano o en el padre no aplica y no da error de compilación.
- `COD-33` Nada de `width` fijo en píxeles en un contenedor que debería fluir (`max-width: 100%` no lo salva); un ancho fijo del diseño se traduce a proporciones, `fr` o `%`. Se prueba con el ancho del diseño, ~992, ~768 y ~400 px.
- `COD-34` Columnas numéricas en un bloque angosto: `white-space: nowrap` y `font-variant-numeric: tabular-nums` en **todas** las columnas de monto, con su propio contenedor de desplazamiento horizontal.
- `COD-35` No se duplica el espaciado de un contenedor compartido: si un padre común ya da relleno a varias vistas, la vista propia no agrega otro margen sin revisar lo que aporta el padre.
- `COD-36` Filas de rejilla con columnas de texto variable: `min-width: 0` en los hijos, `overflow: hidden` + `text-overflow: ellipsis` + `white-space: nowrap` en el texto, y el dato completo en un `title`. Las proporciones reflejan el contenido real (se prueba con el nombre más largo real).
- `COD-37` El color de un botón de Material se fija con las **variables del propio Material** (`--mdc-filled-button-container-color`, `…-label-text-color` y las variantes `disabled`), no con `background:` en la clase: un fondo fijo pisa los estados y el botón sale del color equivocado o se ve activo estando apagado. El estado apagado se distingue a simple vista.
- `COD-38` Pistas de campo (`mat-hint`) en columnas de media anchura: se acortan (~35 caracteres por 250 px) o se aplica `subscriptSizing="dynamic"` **solo** a ese campo; nunca a todos (los campos quedan pegados). La fila lleva `align-items: start`.
- `COD-39` El contraste del texto es de al menos **4.5:1**, también en el tema oscuro; se mide, no se juzga a ojo (ver `pruebas.md`, `PRU-12`). Los botones deshabilitados están exentos.
- `COD-40` Todo lo que la interfaz muestra y no cabe se prueba con el dato más largo real. Los textos que describen el estado del sistema («aún no se envía», «pendiente») se revisan cada vez que esa funcionalidad cambia de estado.
- `COD-41` Un ícono con tooltip y los botones con el estilo de Material (módulos importados), no nativos.
- `COD-42` **Por extraer:** ARIA, foco, navegación por teclado y lectores de pantalla. La instancia de origen no los registra; no se rellenan a ojo.

## 8. Comentarios y formato de código

- `COD-43` Un comentario no narra la implementación puntual (qué defecto arregla, qué investigación lo originó); eso va al mensaje del commit. Se justifica solo para una restricción no obvia que seguirá cierta (un comportamiento de una librería, una invariante), en una línea.
- `COD-44` Prettier acotado a los archivos tocados (`npx prettier --write "<ruta>"`). **Nunca** un script global con `src/**/*` en un repositorio que no está limpio: reescribe cientos de archivos ajenos al cambio.
- `COD-45` `matDatepicker` necesita su adaptador de fechas y su configuración regional en el **propio componente** (`provideNativeDateAdapter()`, `MAT_DATE_LOCALE`); si falta, la pantalla da `No provider found for DateAdapter` al abrirla, y la prueba unitaria no lo detecta.
