# Codificación · NestJS + TypeORM + MySQL
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen (guía de diseño §0.5 y §7, criterios al codificar, convenciones de errores); ver evidencia.md -->

> Paradigmas, código limpio, nombres, manejo de errores, tipos y asincronía. Cada regla lleva un identificador (`COD-n`) que `evidencia.md` traza a su fuente. Se lee **al empezar a escribir**, no al cerrar.

## 1. Paradigma: orientado a objetos en los bordes, funciones puras en el centro

TypeScript no obliga a uno solo. Regla: **núcleo funcional, cascarón imperativo** (`COD-1`).

| Dónde | Paradigma | Por qué |
|---|---|---|
| Reglas de negocio (decidir un pago, cuánto se devuelve, validar un lote, estado visible, transiciones) | **Funciones puras**: entran datos, salen datos; sin E/S, sin `new Date()` interno (la hora se inyecta como `now`), sin mutar parámetros | Se prueban con una tabla de casos, sin Nest ni base; sin estado oculto |
| Orquestación de un flujo (bloquear, leer, aplicar la regla, escribir, auditar) | **Clase con dependencias inyectadas** (use-case o service): el cascarón imperativo | Es el único lugar que conoce el orden de los efectos y la transacción |
| Acceso a datos y servicios externos | **Clases adaptadoras** (detrás de una interfaz solo cuando `PAT-4` lo pide) | Encapsulan SQL, almacenamiento y correo; se sustituyen por dobles |
| Datos (filas, DTO, respuestas) | **Estructuras planas e inmutables**: `interface`/`type`, `readonly` cuando cruzan capas, `as const` para catálogos | Si el repositorio habla SQL y devuelve filas, un modelo de dominio rico con comportamiento sería sobreingeniería |

Reglas que se desprenden:

- `COD-2` El dominio no conoce la infraestructura (ver `ARQ-36`): una regla que necesita un dato lo recibe como argumento.
- `COD-3` Sin estado mutable en singletons (ver `ARQ-38`).
- `COD-4` Inmutabilidad por defecto: no se mutan los parámetros ni las filas recibidas; se devuelve un objeto nuevo. `private readonly` en dependencias y `readonly` en datos que cruzan capas.
- `COD-5` Composición sobre herencia; polimorfismo (Strategy) solo con 3 o más variantes hoy (ver `PAT-7`); con menos, un `if` o un `Record<Tipo, fn>`.
- `COD-6` Una clase con solo métodos estáticos es un módulo de funciones disfrazado: se escribe como funciones exportadas, nombradas por concepto (`money.ts`, no `MoneyUtils`).
- `COD-7` Una clase con comportamiento propio **sí** cuando hay identidad + estado + transiciones validadas **y** varias operaciones comparten esa invariante; aun así, la máquina de estados se modela como tabla de transiciones + función pura (`PAT-17`).
- `COD-8` Encapsulamiento donde importa: el estado de una transacción (`tx`) solo se alcanza por sus repositorios por agregado; nadie fuera del adaptador conoce el `EntityManager`.
- `COD-9` Efectos explícitos: un efecto (correo, almacenamiento, auditoría) se nombra y se ejecuta en un punto conocido (posterior a la confirmación), no escondido dentro de un getter ni de una función «pura».

## 2. Código limpio: el conjunto mínimo exigido

| Principio | Cómo se ve | Verificable |
|---|---|---|
| **Nombres que dicen el propósito** (`COD-10`) | Por concepto de negocio (`reembolsoPendiente`, `ResumenDePedido`); nunca `Manager`, `Helper`, `Utils`, `data`, `tmp`, `handle`, `process` solos | revisión |
| **Funciones pequeñas, una sola cosa** (`COD-11`) | 60 líneas o menos (aviso), 100 o menos (falla); un nivel de abstracción por función; si hace falta un comentario para separar partes, son dos funciones | motor |
| **Poco anidamiento** (`COD-12`) | Cláusulas de guarda y `return` temprano antes que `else` anidados; profundidad máxima de 3 | revisión |
| **Sin números ni textos mágicos** (`COD-13`) | Constantes con nombre (`MAX_BATCH_ROWS`, no `500`); códigos de error del catálogo | motor (parcial) |
| **Sin banderas booleanas posicionales** (`COD-14`) | Dos métodos o un objeto de opciones nombrado | motor |
| **Comandos y consultas separados** (`COD-15`) | Un método o cambia estado o devuelve datos, no ambos a escondidas | revisión |
| **Comentarios solo para el porqué** (`COD-16`) | No narrar el cómo ni la historia de la tarea; un orden de bloqueos o una restricción no obvia sí | revisión |
| **Sin código muerto ni duplicado** (`COD-17`) | Regla de tres; lo exportado que nadie importa se confirma y se borra | motor (parcial) |
| **Pruebas legibles** (`COD-18`) | Preparar-Actuar-Afirmar; un nombre que dice la regla («rechaza si el monto no cabe»); tabla de casos para reglas puras | revisión |
| **Consistencia con el vecino** (`COD-19`) | Si el módulo vecino ya resolvió algo bien, se imita; si lo resolvió mal, se anota, no se copia | revisión |

- `COD-20` Una clase que pasa de ~250 líneas o mezcla dos razones de cambio se parte por razón de cambio antes de seguir.
- `COD-21` Un bloque que ya se escribió dos veces se extrae a la 3.ª copia, aunque cambien los nombres.
- `COD-22` Al editar archivos con un script de reemplazo, cada reemplazo lleva una aserción de que encontró el texto: uno silencioso deja sin insertar el cambio y solo lo delata una prueba.
- `COD-23` Se anota en la deuda técnica, no se arregla de paso, el código que no se está tocando.

## 3. Nombres

- `COD-24` Por concepto de negocio y en el idioma del dominio del proyecto; el nombre dice el propósito, no el mecanismo.
- `COD-25` Un servicio se nombra por **un** concepto (`MoraService`, `CapitalService`); si el nombre necesita una «y» para ser honesto, son dos.
- `COD-26` Los archivos de utilidades se nombran por concepto (`money.ts`, `business-dates.ts`), no `utils.ts`.
- `COD-27` Los dobles de prueba viven en `testing/`, con cualquier nombre (ver `ARQ-35`).

## 4. Manejo de errores

- `COD-28` Los códigos de error están en un único catálogo `as const`; nunca `code: 'TEXTO'` suelto. Un bloque de excepción idéntico en 3 o más sitios pasa a una fábrica (ver `PAT-9`, `PAT-10`).
- `COD-29` Nunca `catch {}` vacío ni tragar un error sin registrarlo; el mensaje para la persona sale del catálogo.
- `COD-30` Una sola familia de excepciones: se lanza `HttpException` y sus derivadas; no se crea una clase de excepción propia que ya existe en el framework.
- `COD-31` Una excepción global da una única forma de respuesta de error (código, motivo, mensaje, ruta, marca de tiempo); el éxito tiene también una forma única por convención.
- `COD-32` Los `message` de los validadores están en el idioma del producto, en **cada** decorador (el valor por defecto en inglés es lo que más devuelve QA). Un `ParseIntPipe` sobre un `@Param()` sin DTO lleva un `exceptionFactory` propio.
- `COD-33` Un enum o valor fuera de lista da un 400 explícito; nunca un valor por defecto silencioso.
- `COD-34` La salida de errores y de registros redacta los campos sensibles (autorización, cookie, claves, `*.password`, `*.token`, `*.secret`).
- `COD-35` Una llamada a otro sistema: se lee **su** validación, no solo el DTO propio (campo vacío se omite, texto largo se recorta, límites de tamaño y cantidad), y se prueba el vacío y el largo.
- `COD-36` Un id elegido de una lista sugerida se revalida en la escritura con la misma condición de negocio: el cliente no es de fiar y nada impide un POST armado a mano.

## 5. Tipos

- `COD-37` Filas de SQL propio con un tipo explícito (`XRow`); no `any`.
- `COD-38` Un puerto que declara devolver la clase de dominio no devuelve una entidad cruda de TypeORM ni `null` (sustitución de Liskov: el adaptador cumple el contrato sin sorpresas).
- `COD-39` Catálogos y estados como `as const` y tipos derivados; los literales de estado dentro de SQL se pasan como parámetro desde la constante (ver `ARQ-41`).
- `COD-40` Una interfaz de puerto con más de 10 métodos está rota (aviso por encima de 10, falla por encima de 15): puertos pequeños y por agregado.
- `COD-41` Una función pura de cálculo (prorrateo, clasificación en tramos o estados) lleva su propio spec aunque el resto de la suite sea liviana.
- `COD-42` Dinero y fechas por la función única (ver `PAT-14`, `PAT-15`); si solo viajan de la base a la respuesta, no se crea una clase para ellos.

## 6. Asincronía

- `COD-43` **Sin promesas flotantes:** toda promesa se espera (`await`), se devuelve o se atrapa (`.catch`) con registro; el efecto posterior a la confirmación usa `.catch` y deja un evento auditable.
- `COD-44` **Sin `await` dentro de un bucle para lecturas independientes** (N+1): `Promise.all`, o por lotes con tope. Excepciones justificadas: dentro de una transacción con bloqueos manda el orden; o cada fila debe ser su propia transacción (lote).
- `COD-45` **Paralelo con tope:** nunca `Promise.all` sobre N filas sin límite; por lotes de 5-10.
- `COD-46` Las lecturas independientes de una respuesta compuesta van con `Promise.all`, salvo transacción con `FOR UPDATE`: dentro de una transacción con bloqueos nunca se paralelizan.
- `COD-47` Tiempo de espera y cancelación en toda llamada a un servicio externo; si falla, no se deja a medias lo ya hecho (compensar: borrar el archivo ya subido).
- `COD-48` Doble envío: unicidad en la base + 409 (ver `PAT-22`).
- `COD-49` Una lectura de archivo o flujo recibe el tope y **corta** al pasarlo; no se mide después de cargar.
- `COD-50` Si hay `FOR UPDATE`, primero el bloqueo y recién después las lecturas comunes.

## 7. Complejidad: decir cuánto vale `n`

- `COD-51` Toda lista que crece lleva su `n` en el plan y en la revisión (filas de un listado, elementos por pedido, destinatarios de un aviso). «Es `O(n)`» sin precisar qué es `n` no informa.
- `COD-52` Una búsqueda (`find`, `filter`, `some`, `includes`, `indexOf`) dentro de un bucle sobre una lista que crece es `O(n²)`: se indexa la lista una vez en un `Map` o `Set`. Una consulta a la base dentro de un bucle se cambia por una sola con `IN (...)` o `JOIN`: en el backend el costo dominante suele ser el número de viajes a la base, no las iteraciones en memoria.
- `COD-53` Un costo que crece con `n` en llamadas a un servicio de pago crece en dinero.
- `COD-54` Se ignora en listas pequeñas y acotadas por diseño: un `O(n²)` simple y legible gana a un `O(n log n)` enredado si `n` es chico. La notación sirve para comparar soluciones; los milisegundos se miden con datos reales.

## Por extraer

- Convención de nombres de archivos y de carpetas del módulo (más allá de `domain/`, `infrastructure/`, `dto/`, `testing/`).
- Reglas de lint y de formato del stack.
- Idioma de los identificadores del código (la convención de nombres en inglés es una advertencia en el material de origen, no una regla).
