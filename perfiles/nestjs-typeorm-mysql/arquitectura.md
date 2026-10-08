# Arquitectura · NestJS + TypeORM + MySQL
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen (estándares de estructura, SOLID y guía de diseño); ver evidencia.md -->

> Capas, escalas S/M/L, dónde va cada cosa y reglas de dependencia. Cada regla lleva un identificador (`ARQ-n`) que `evidencia.md` traza a su fuente.

**Principio rector.** Una abstracción se gana con evidencia, no con previsión: se crea cuando hay hoy 2 o más usos reales (3 si es duplicación), con la misma razón de cambio y se puede nombrar por un concepto de negocio. Si no, se deja en línea. Lo contrario también es un defecto: no abstraer cuando ya hay 3 copias. (`ARQ-1`)

## 1. La cadena de capas es fija

```
HTTP ─▶ controller ─▶ service / use-case ─▶ repository ─▶ BD
        (traduce)      (decide)              (habla SQL)
```

- `ARQ-2` El controller **nunca** toca un repository, ni en el módulo más pequeño. La variante mínima es `controller + service + @InjectRepository`, no `controller + repository`.
- `ARQ-3` Un service que solo delega sigue siendo la capa correcta: es la costura donde entra la regla el día que aparece. Lo sobrante es la *indirección* extra (interfaz, token, mapeador), no la capa.
- `ARQ-4` El controller no tiene lógica: cero `if` y cero `throw`. Solo `@Body/@Param/@Query`, delegar y devolver. Se audita con una línea antes de cerrar el módulo:

```bash
grep -nE '\b(if|throw|new [A-Za-z]+Exception)\b' src/modules/<modulo>/*.controller.ts   # debe dar 0
```

## 2. Dónde va cada cosa

| Qué se resuelve | Dónde | Regla |
|---|---|---|
| Forma y tipos del cuerpo o de la consulta | **DTO** con validadores, `message` en el idioma del producto en **cada** decorador | `ARQ-5` |
| Formato de un `:id` de la ruta | **Pipe** (una constante por parámetro) | `ARQ-6` |
| Quién puede llamar | **Guard** propio del módulo | `ARQ-7` |
| Contenido real de un archivo, estados, reglas de negocio | **Service / use-case** | `ARQ-8` |
| «Existe / no existe» (`NotFoundException`) | **Service** | `ARQ-8` |
| Bloqueos, transacción, unicidad, SQL | **Repository** | `ARQ-9` |
| Ninguna regla de negocio en el DTO ni en el pipe | — | `ARQ-10` |

`ARQ-11` Validar el contenido de un archivo (por ejemplo, sus bytes) es una razón real para mirar más allá de lo que declara el cliente, pero **no** para hacerlo en el controller: el buffer completo pasa al service, que decide.

## 3. Cuánta estructura: la escala S/M/L

Se elige el tamaño **antes** del estilo. Cada pieza extra lleva **una frase** de justificación en el plan; sin frase, no va. (`ARQ-12`)

| Tamaño | Cuándo | Archivos |
|---|---|---|
| **S** | 1-2 lecturas sobre una tabla, sin cálculo | `controller` · `service` (con `@InjectRepository(Entidad)`) · `dto/` de respuesta · `module` · spec del service |
| **M** | lectura con uniones o SQL propio, o escritura con pocas reglas | S + `repository` **concreto** (query builder o SQL) que el service inyecta por clase, sin interfaz ni token · DTO validado para el `@Body()` |
| **L** | escritura **transaccional** con varias reglas y efectos | M + `use-case` por *flujo* + **puerto de escritura** (interfaz + token) + adaptador MySQL con `runInTransaction` · `domain/` para ayudantes puros con su spec · `guard` propio si hay permiso propio |

- `ARQ-13` Controller y `module` van en la **raíz** del módulo, más `dto/`. Las carpetas `domain/` e `infrastructure/` aparecen recién en **L**, o en M si el repository concreto se separa del service. No se crea una carpeta vacía «por si crece».
- `ARQ-14` «Varias reglas» (tamaño L) se lee con números: **use-case = flujo de escritura con 3 o más reglas o 2 o más efectos** (correo, almacenamiento, auditoría).

### 3.1 Puerto: solo del lado que lo gana

Un puerto (interfaz + token) se justifica por **una** de tres razones, escrita en el plan: (a) persistencia no trivial con transacción compartida entre operaciones, (b) el service o use-case no se puede probar sin él, (c) hay 2 o más implementaciones reales. (`ARQ-15`)

- `ARQ-16` **Escritura transaccional → puerto sí.** Expone `runInTransaction(work)`; `work` recibe una `tx` con las operaciones que comparten la transacción. Habilita probar el use-case con un doble plano.
- `ARQ-17` **Lectura → sin puerto.** Cada consulta es independiente, no comparte transacción y el service se prueba con **un** doble plano. El service inyecta la clase concreta.
- `ARQ-18` No se hace simétrico «por consistencia»: que la escritura tenga puerto no obliga a la lectura. Se decide lado por lado.
- `ARQ-19` DIP estricto (depender de la interfaz y nunca de la clase concreta) rige en la **escritura transaccional**. En lecturas simples el service puede inyectar `@InjectRepository(Entidad)` o el repository concreto; no es una ruptura.

### 3.2 Use-case frente a service

- `ARQ-20` **Use-case** = un flujo de escritura con varias reglas y efectos. Pertenece al dominio; no sabe de HTTP ni de SQL.
- `ARQ-21` **Service** = agrupa operaciones cohesivas de un mismo concern (lecturas, documentos). Un service por concern, no un use-case por método.
- `ARQ-22` Si varias clases comparten las mismas dependencias y nunca se llaman por separado, son un solo service.
- `ARQ-23` Un service se nombra por **un** concepto de dominio y solo tiene lógica de ese concepto. Un flujo que necesita varios concerns lo compone un orquestador que no contiene cálculo propio. Señales de que hay que partir: el nombre necesita una «y»; un método mezcla E/S + cálculo + efecto externo; el spec necesita mockear varios colaboradores para probar un cálculo; dos motivos de cambio tocan la misma clase.

### 3.3 Efectos posteriores a la confirmación

- `ARQ-24` Correo, almacenamiento y auditoría se disparan **después** de `runInTransaction`, dentro del use-case, nunca antes ni en el controller.
- `ARQ-25` **Nunca lanzan**: cada uno atrapa su error y lo deja como evento auditable, porque un correo caído no puede convertir en 500 un registro que ya existe.
- `ARQ-26` No se disparan en el retorno idempotente ni en el camino de quien perdió la carrera de idempotencia.
- `ARQ-27` Los efectos viven en el use-case que posee la transacción, no en el service: así los cubre cualquier camino, incluido el procesamiento por lotes.

### 3.4 Archivo propio o en línea

| Sí, archivo propio | No, en línea o consolidar |
|---|---|
| función pura con reglas y **spec** | ayudante de 3 líneas usado en un solo lugar |
| clase con 2 o más consumidores | DTO que solo envuelve un `:id` de la ruta → usar **pipe** |
| guard o pipe reutilizable | `try/catch` anidado que otro ya cubre |

`ARQ-28` aplica la tabla anterior.

### 3.5 Escritura que toca varios agregados: unidad de trabajo

`ARQ-29` Si la escritura transaccional toca **varios agregados**, el puerto no es una interfaz plana con todos los métodos (un puerto de 36 métodos y 15 use-cases dependiendo de todo hubo que rehacerlo). La forma correcta desde el primer commit:

- `IXUnitOfWork { runInTransaction(work); …lecturas que deben ir FUERA de la transacción }` y `IXTransaction { pedidos: IPedidosTx; pagos: IPagosTx; … }`: **un repositorio por agregado**, cada uno con 10 métodos o menos. El use-case lee solo lo que usa (`tx.pagos.bloquear(id)`).
- Una clase MySQL por agregado (de 20 a 120 líneas) y una clase que las compone sobre el **mismo** `EntityManager`: se conserva la transacción compartida y el orden de bloqueos, que era la razón del puerto.
- El doble en memoria sigue la misma forma y conserva las etiquetas que los specs comprueban.

### 3.6 Núcleo compartido: `shared/`

- `ARQ-30` Lo que usan **3 o más subáreas** (conversión de dinero, fechas de negocio, normalización de identificadores, el almacén de archivos, el propio puerto) vive en `shared/`, no dentro de la carpeta de la subárea que lo escribió primero; si no, las subáreas se importan entre sí (acoplamiento por carpetas aunque no haya ciclos de archivos). Una constante exportada desde un **service** para que otros la importen es la señal.
- `ARQ-31` Si lo usan 2, vive en el módulo del dueño. Nada de un `utils.ts` genérico: el nombre es por concepto (`money.ts`, `business-dates.ts`).

### 3.7 Errores: catálogo y fábricas

- `ARQ-32` Los códigos de error viven en un solo `as const` (`PedidoErrorCode.NOT_FOUND`); nunca `code: 'TEXTO'` suelto. Los valores son contrato con el consumidor: no se renombran sin avisar.
- `ARQ-33` Un bloque `throw new NotFoundException({ code, message })` idéntico en 3 o más sitios pasa a una fábrica (`pedidoNotFound()`).

### 3.8 Archivos subidos y dobles de prueba

- `ARQ-34` Validar un archivo es mirar sus bytes, no el `Content-Type` que declara el cliente. Un único almacén con `assertValid(archivo, reglas)`, `upload`, `discard` y `serve`; las reglas de cada uso se declaran una sola vez.
- `ARQ-35` Los dobles en memoria van en una carpeta `testing/` y la configuración de compilación la excluye: un archivo `*-test-doubles.ts` suelto se compila y viaja a producción (vale para `test-kit`, `test-utils`, `stub`, `mock`, `fake`).

## 4. Reglas de dependencia

- `ARQ-36` El dominio no conoce la infraestructura: un archivo de `domain/` no importa `typeorm`, `EntityManager` ni `DataSource`. Si una regla necesita un dato, lo recibe como argumento.
- `ARQ-37` Los puertos de lectura no se crean por simetría (ver `ARQ-18`); un puerto con un implementador, un consumidor y un spec con doble plano no se ganó su lugar.
- `ARQ-38` Sin estado mutable en singletons: todo provider de Nest es singleton; un campo mutable (`private cache = new Map()`) se comparte entre peticiones. Las cachés legítimas se justifican en el plan.
- `ARQ-39` Composición sobre herencia: herencia solo para excepciones y DTO (`PartialType`). Una `abstract class` de service o use-case se justifica en el plan (solo con 2 o más clases que comparten 30 o más líneas de esqueleto).
- `ARQ-40` **CQRS ligero permitido, CQRS completo no:** el camino de lectura (service + repository concreto, DTO propio) separado del de escritura (use-case + unidad de trabajo), sin bus de comandos, bus de eventos, event sourcing ni tablas espejo. Si hace falta asincronía real, va por cola, no por eventos dentro del proceso.
- `ARQ-41` Una regla de negocio escrita en dos lenguajes o lugares (SQL agregado + TypeScript, backend + frontend) siempre termina divergiendo: se define **una sola fuente** y el otro lado se genera de ella; si duplicar es inevitable, el plan lo declara y un test de **paridad** ejecuta ambas con los mismos casos. Un literal de estado dentro de `IN (...)` se pasa como parámetro desde la constante del dominio.

## 5. Umbrales medibles

Valores iniciales medidos sobre una sola base de código (percentiles 90-98); se recalibran cuando el código cambie de forma (`ARQ-42`). En archivos nuevos o modificados el umbral de FALLA es bloqueante; en código heredado es aviso.

| Medida | AVISO | FALLA |
|---|---|---|
| Dependencias por constructor | más de 6 | más de 10 |
| Métodos públicos por clase | más de 12 | más de 20 |
| Métodos por interfaz de puerto | más de 10 | más de 15 |
| Líneas por archivo (sin DTO ni entidades) | más de 300 | más de 600 |
| Líneas por método | más de 60 | más de 100 |

`ARQ-43` Un service se parte con más de 10 dependencias, más de 300 líneas o 2 o más razones de cambio; no se parte por estética (un service de 450 líneas con 3 dependencias y un solo concern puede quedarse).

## 6. Auditoría antes de cerrar un módulo (5 preguntas)

Para cada archivo nuevo de `domain/` e `infrastructure/` (`ARQ-44`):

1. ¿Tiene una frase de justificación? Si no, ¿es una interfaz, token o mapeador que quedó «por si acaso»?
2. ¿Tiene **un solo implementador** y **un solo consumidor**? Entonces el puerto no se ganó su lugar.
3. ¿El spec del service se escribe con **un** doble plano? Entonces no hace falta puerto.
4. ¿Es un pass-through sin regla ni `NotFoundException`? Se queda solo si es la capa del service; no se le agrega otra encima.
5. ¿El controller da 0 en el `grep` de `ARQ-4`?

`ARQ-45` Si una respuesta obliga a desviarse del plan, la desviación se anota con su motivo (incluso «aceptado por costo de cambio»): una desviación sin nota es un descuido; con nota es una decisión.

## 7. Antipatrones

| Antipatrón | Cómo se evita |
|---|---|
| Validación de negocio o de archivo en el controller | `ARQ-4`, `ARQ-11` |
| Puerto de lectura «por simetría» con el de escritura | `ARQ-18` |
| Un use-case por método de un mismo concern | `ARQ-21`, `ARQ-22` |
| DTO para un `:id`, archivo para un ayudante de 3 líneas | `ARQ-28` |
| Controller que llama directo al repository «para simplificar» | `ARQ-2` |
| Puerto de escritura plano con todos los métodos del módulo | `ARQ-29` |
| Utilidades de una subárea usadas por otras | `ARQ-30` |
| `code: 'TEXTO'` suelto repetido | `ARQ-32` |
| Validación de archivo solo por tipo declarado, copiada varias veces | `ARQ-34` |
| Dobles de prueba en el árbol de producción | `ARQ-35` |
| Efecto posterior a la confirmación disparado desde el service y repetido | `ARQ-24`, `ARQ-27` |
| Una definición de «quién recibe» con regla propia distinta de la definición única | reusar la definición única y probar con datos sembrados (caso con devolución parcial y caso con devolución total) |

## Por extraer

Estilos de organización del proyecto (módulo por funcionalidad, plano, hexagonal) y su criterio de elección: el material de origen los remite a un documento que este perfil aún no ha leído; no se inventa.
