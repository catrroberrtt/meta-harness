# Patrones · NestJS + TypeORM + MySQL
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen (guía de diseño, SOLID y patrones, estructura estándar); ver evidencia.md -->

> Catálogo de patrones con **cuándo SÍ** y **cuándo NO**. Proporcionalidad: una pieza extra se justifica con una frase; si no hay frase, no va. Cada entrada lleva un identificador (`PAT-n`) que `evidencia.md` traza a su fuente. Los ejemplos son mínimos y genéricos («pedido», «cliente»).

## 0. Cómo se decide (árbol A1: ¿creo una abstracción?)

1. ¿Hay hoy 2 o más usos reales (3 si es duplicación)? No → no abstraer, dejar en línea.
2. ¿Cambian por la misma razón? No → no abstraer.
3. ¿Puedo nombrarla por un concepto de negocio (sin «Manager», «Helper», «Utils»)? No → no abstraer.
4. ¿Quita 6 o más líneas o simplifica el spec de un llamador? No → no abstraer.
5. ¿Cuesta como mucho 1 archivo y ninguna capa nueva? Sí → crear. No → llevar la decisión al plan con una frase.

`PAT-0` Cuando la opción limpia cuesta más de 2 archivos o 1 capa sobre la opción simple, se consulta a la persona responsable; si no, se elige y se anota en el plan.

## 1. Catálogo

### Unidad de trabajo (`PAT-1`)
- **Cuándo SÍ:** escritura que toca 2 o más tablas con deshacer conjunto: `IUnidad.runInTransaction(work)` con una `tx` que expone un repositorio **por agregado**, de 10 métodos o menos cada uno, compuestos sobre el mismo `EntityManager`.
- **Cuándo NO:** una sola tabla y un `save()`: `@InjectRepository` y `manager.transaction` en línea en el repository concreto. No se crea `tx.x` con un único método.
- **Ejemplo mínimo:**

```ts
interface IPedidosUnitOfWork { runInTransaction<T>(work: (tx: IPedidosTx) => Promise<T>): Promise<T>; }
interface IPedidosTx { pedidos: IPedidosRepo; pagos: IPagosRepo; }

// en el use-case
await this.uow.runInTransaction(async (tx) => {
  const pedido = await tx.pedidos.lock(id);          // primero el bloqueo
  await tx.pagos.add({ pedidoId: pedido.id, monto });
});
```

### Repository concreto con SQL (`PAT-2`)
- **Cuándo SÍ:** lectura con uniones, agregados o SQL propio: clase **sin interfaz** con un tipo de fila `XRow`; el service la inyecta por clase.
- **Cuándo NO:** si hay un solo implementador, no se le pone interfaz; no se pone `if` de negocio en el SQL (solo filtros).
- **Ejemplo mínimo:**

```ts
interface PedidoRow { id: number; clienteNombre: string; total: string }
@Injectable() export class PedidosReadRepository {
  constructor(private readonly ds: DataSource) {}
  list(clienteId: number): Promise<PedidoRow[]> {
    return this.ds.query('SELECT p.id, c.nombre AS clienteNombre, p.total FROM pedido p JOIN cliente c ON c.id = p.cliente_id WHERE c.id = ?', [clienteId]);
  }
}
```

### Lectura simple con `@InjectRepository` (`PAT-3`)
- **Cuándo SÍ:** lectura de 1-2 tablas, sin cálculo: el service inyecta `@InjectRepository(Entidad)` y devuelve un DTO.
- **Cuándo NO:** con uniones o más de 3 columnas calculadas, pasar a `PAT-2`.
- **Ejemplo mínimo:** `return (await this.repo.findOneByOrFail({ id })).toDto?.() ?? { id: e.id, nombre: e.nombre };` (sin capa extra).

### Puerto y adaptador (`PAT-4`)
- **Cuándo SÍ:** 2 o más implementaciones reales, o transacción compartida (unidad de trabajo), o el spec no se puede escribir con un doble plano. Si el plan declara cuál será la segunda implementación, vale; «por si acaso», no.
- **Cuándo NO:** lecturas. Un implementador + un consumidor + un spec con doble plano → sin interfaz.
- **Ejemplo mínimo:** `{ provide: PEDIDOS_UOW, useExisting: MysqlPedidosUnitOfWork }` y `@Inject(PEDIDOS_UOW)` en el use-case.

### Use-case frente a service (`PAT-5`)
- **Cuándo SÍ (use-case):** flujo de escritura con 3 o más reglas o 2 o más efectos. **Service:** lecturas o un grupo de operaciones de un concern.
- **Cuándo NO:** no un use-case por método; si 2 use-cases tienen las mismas dependencias y se llaman siempre juntos, fusionarlos en un service.
- **Ejemplo mínimo:** `CancelarPedidoUseCase.execute(id)` (bloquea, valida estado, escribe, audita, avisa después de confirmar) frente a `PedidosQueryService.list()`.

### CQRS ligero (`PAT-6`)
- **Cuándo SÍ:** lectura de reporte, listado o exportación muy distinta del modelo de escritura: service de consulta o modelo de lectura con su propio DTO, sin bus, sin eventos, sin tablas espejo.
- **Cuándo NO:** no sirve para validar reglas de escritura (eso va por el use-case); no se crea una tabla de lectura si el SQL corre en menos de 500 ms; una lectura que alimenta una escritura (saldo, bloqueo) va dentro del use-case y de la transacción.
- **Ejemplo mínimo:** `PedidosReportService` con su `ReporteRow` y su DTO, separado de `CancelarPedidoUseCase`.

### Strategy (`PAT-7`)
- **Cuándo SÍ:** 3 o más variantes hoy (o 2 que el plan documenta que cambian por configuración) **y** un `switch` de 3 o más ramas repetido en 2 o más sitios **y** cada variante con dependencias o estado propios.
- **Cuándo NO:** con 1-2 variantes, un `if`; sin estado propio, `Record<Tipo, fn>` (`PAT-8`). No se crea una clase por rama.
- **Ejemplo mínimo:** un token por variante (`ENVIO_ESTANDAR`, `ENVIO_EXPRESS`, `ENVIO_RECOGIDA`) y el use-case elige por clave.

### Mapa de funciones en lugar de Strategy (`PAT-8`)
- **Cuándo SÍ:** variantes sin estado ni dependencias propias.
- **Cuándo NO:** si cada rama necesita estado o dependencias distintas, Strategy con inyección.
- **Ejemplo mínimo:**

```ts
const calculadores: Record<TipoEnvio, (p: Pedido) => number> = {
  estandar: (p) => p.peso * 2, express: (p) => p.peso * 5, recogida: () => 0,
};
// y un test que recorra todas las claves del tipo
```

### Fábrica de errores (`PAT-9`)
- **Cuándo SÍ:** el mismo `throw` en 3 o más sitios (`pedidoNotFound()`); fábrica de dominio solo si construir el objeto tiene 3 o más pasos o reglas.
- **Cuándo NO:** un `new X({...})` simple. `useFactory` de Nest solo en un esquema hexagonal ya existente; en código nuevo, `@Inject(TOKEN)`.
- **Ejemplo mínimo:** `export const pedidoNotFound = () => new NotFoundException({ code: PedidoErrorCode.NOT_FOUND, message: 'El pedido no existe' });`

### Catálogo de errores (`PAT-10`)
- **Cuándo SÍ:** `as const` con códigos de valor estable (contrato con quien los consume).
- **Cuándo NO:** un `NotFoundException('texto')` único en un módulo S sin consumidor que lea el `code`.
- **Ejemplo mínimo:** `export const PedidoErrorCode = { NOT_FOUND: 'PEDIDO_NOT_FOUND' } as const;`

### Mapeador / presentador (`PAT-11`)
- **Cuándo SÍ:** la forma de la respuesta difiere de la de la tabla en 3 o más campos, hay campos sensibles o internos, o se renombran 3 o más columnas.
- **Cuándo NO:** devolver la entidad tal cual sin campos sensibles; no hacer un mapeador bidireccional si solo se lee; si se usa en un solo lugar y tiene menos de 10 líneas, en línea en el service; `toEntity` solo en escritura con un puerto.
- **Ejemplo mínimo:** `const toDto = (r: ClienteRow): ClienteDto => ({ id: r.id, nombre: r.nombre });` (sin exponer `passwordHash`).

### DTO con validación (`PAT-12`)
- **Cuándo SÍ:** siempre para `@Body()` y para una consulta compleja; `message` explícito en cada validador; un enum o valor fuera de lista da 400 explícito, nunca un valor por defecto silencioso. `UpdateXDto extends PartialType(CreateXDto)` para el DTO de actualización.
- **Cuándo NO:** ninguna regla de negocio en el DTO; no se crea un DTO que solo envuelve un `:id` (usar pipe).
- **Ejemplo mínimo:**

```ts
export class CrearPedidoDto {
  @IsInt({ message: 'clienteId debe ser un entero' }) clienteId!: number;
  @IsEnum(TipoEnvio, { message: 'tipoEnvio no es válido' }) tipoEnvio!: TipoEnvio;
}
```

### Guard, pipe, interceptor, filtro (`PAT-13`)
- **Cuándo SÍ:** transversales: permisos, auditoría, forma de error, formato de un identificador de ruta.
- **Cuándo NO:** lógica de negocio (va en el service).
- **Ejemplo mínimo:** `@Get(':id') get(@Param('id', parseIdPipe('pedido')) id: number)`.

### Valor de dinero (`PAT-14`)
- **Cuándo SÍ:** un tipo o ayudante único (`shared/money`) para redondeo, conversión entre unidades y suma; toda la aritmética monetaria pasa por ahí. Obligatorio donde hay prorrateo, retención o comparación de montos. Una clase `Money` completa solo con prorrateo o comparaciones en 3 o más flujos.
- **Cuándo NO:** sin clase `Money` si la base ya trae `DECIMAL` y solo se suma una vez; si el dato solo viaja de la base a la respuesta.
- **Ejemplo mínimo:** `export const toCents = (m: string) => Math.round(Number(m) * 100);`

### Valor de fecha de negocio (`PAT-15`)
- **Cuándo SÍ:** ayudantes únicos (`shared/business-dates`) para parseo, formato y rangos en la zona del negocio; nunca un `new Date()` suelto en un cálculo de negocio (la hora se inyecta como `now`).
- **Cuándo NO:** no se encapsula un `Date` solo para guardar una marca de tiempo.
- **Ejemplo mínimo:** `export const startOfBusinessDay = (d: Date, tz = BUSINESS_TZ) => …;`

### Especificación como función pura (`PAT-16`)
- **Cuándo SÍ:** `puedeCancelar(pedido): Resultado` con spec, cuando la misma regla se evalúa en 2 o más flujos o tiene 4 o más condiciones.
- **Cuándo NO:** una condición de 1-2 comparaciones: en línea en el service. No hay clase `Specification` ni lenguaje propio.
- **Ejemplo mínimo:** `export const puedeCancelar = (p: Pedido): boolean => p.estado === 'PENDIENTE' && !p.enviado;`

### Máquina de estados como tabla y función (`PAT-17`)
- **Cuándo SÍ:** identidad + estado + transiciones validadas compartidas por varias operaciones: tabla de transiciones + función pura `canTransition`.
- **Cuándo NO:** no una jerarquía de clases `State`.
- **Ejemplo mínimo:** `const T: Record<Estado, Estado[]> = { PENDIENTE: ['PAGADO','CANCELADO'], PAGADO: ['ENVIADO'], ENVIADO: [], CANCELADO: [] };`

### Composición frente a herencia (`PAT-18`)
- **Cuándo SÍ:** composición siempre (inyectar colaboradores). Herencia solo para excepciones y DTO.
- **Cuándo NO:** `abstract class` de service o use-case (ver `ARQ-39`). Una clase con solo métodos estáticos es un módulo de funciones: se escribe como funciones exportadas.
- **Ejemplo mínimo:** `export function calcularTotal(lineas: readonly Linea[]): number { … }` en `pedido-total.ts`, no `PedidoUtils.calcularTotal`.

### Efecto posterior a la confirmación (`PAT-19`)
- **Cuándo SÍ:** correo, archivo, auditoría: en el use-case, después de confirmar la transacción, sin lanzar, dejando un evento auditable (un registro con clave única evita repetirlo). Sustituye a los eventos de dominio.
- **Cuándo NO:** no antes de confirmar, no en el controller, no en el retorno idempotente; si hace falta asincronía real, cola y no eventos en el proceso.
- **Ejemplo mínimo:**

```ts
const pedido = await this.uow.runInTransaction((tx) => crear(tx, dto));
await this.notificar(pedido).catch((e) => this.auditoria.registrar('NOTIFY_FAILED', e)); // nunca lanza
return pedido;
```

### Caché (`PAT-20`)
- **Cuándo SÍ:** solo con una consulta medida en más de 500 ms, frecuencia alta y un dato que tolera un TTL de 60 s o más; antes se prueban el índice y la reescritura de la consulta.
- **Cuándo NO:** dinero, saldos, permisos o cualquier lectura que alimente una escritura.
- **Ejemplo mínimo:** `getCatalogo()` con TTL de 5 min sobre una tabla de catálogo; nunca `getSaldo()`.

### Paginación (`PAT-21`)
- **Cuándo SÍ:** listados no acotados: `page/limit` con `@Max` revisado contra **todos** los llamadores, total en `meta`, orden estable (fecha descendente y `id` descendente: lo más reciente primero, salvo catálogos y rankings).
- **Cuándo NO:** catálogos de menos de 100 filas. Cuidado: un `@Max` puede romper a un llamador que pide un límite mayor.
- **Ejemplo mínimo:** `ORDER BY creado_en DESC, id DESC LIMIT ? OFFSET ?`.

### Idempotencia (`PAT-22`)
- **Cuándo SÍ:** todo POST de dinero o de estado: clave natural (identificador de operación) con unicidad en la base y retorno del resultado previo.
- **Cuándo NO:** en GET; en un POST sin efecto sobre dinero y con unicidad natural, basta la restricción de la base.
- **Ejemplo mínimo:** `UNIQUE (pedido_id, numero_operacion)` y, si ya existe, devolver el resultado anterior con 409 o el mismo cuerpo.

### Duplicar o extraer (`PAT-23`)
- **Cuándo SÍ (extraer):** regla de tres: a la 3.ª copia se extrae; a la 2.ª solo si el bloque tiene 6 o más líneas de regla de negocio.
- **Cuándo NO:** si los 2 usos divergen por razones distintas (cambian por separado). Duplicación accidental que **no** se unifica: presentadores de pantallas con contratos distintos, listados con `WHERE` distintos, etiquetas de estado por dominio.
- **Ejemplo mínimo:** tres `startOfDay(...)` copiados → `shared/business-dates`.

### Paridad entre SQL y TypeScript (`PAT-24`)
- **Cuándo SÍ:** una misma regla se necesita en SQL (listados) y en TypeScript (validación): un spec de **paridad** ejecuta ambas con los mismos casos y un comentario cruzado las une.
- **Cuándo NO:** si la regla vive en un solo lugar, no hace falta el spec.
- **Ejemplo mínimo:** `pedido.parity.spec.ts` que compara `clasificarPedido(row)` con el resultado del `CASE` de la consulta.

## 2. Lo que NO se introduce

- `PAT-25` `CommandBus`, `EventBus`, event sourcing y tablas espejo: no se usan aunque estén instalados como dependencia. Si la persona pide CQRS completo, es un proyecto nuevo y se discute aparte.
- `PAT-26` Clases `Manager`, `Helper`, `Utils` o `Context` que solo oculten el número de dependencias (constructor con más de 6 parámetros: partir por concern o agrupar en un colaborador con nombre).
- `PAT-27` Una abstracción exportada que solo importan sus specs: se confirma con el dueño antes de borrarla (puede ser de otro repositorio).

## Por extraer

Catálogo de patrones propios del acceso a datos de TypeORM (hooks de entidad, suscriptores, repositorios personalizados) y su criterio de uso: no hay en el material de origen.
