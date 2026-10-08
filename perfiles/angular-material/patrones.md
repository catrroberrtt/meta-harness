# Patrones · Angular + Material
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (guía de diseño catálogo F1-F8 y árboles A10-A14, reglas aprendidas del frontend, convenciones de frontend, código de interceptores y guardas); ver evidencia.md -->

> Catálogo de patrones con «cuándo SÍ», «cuándo NO» (proporcionalidad) y un ejemplo mínimo inventado. Cada regla lleva un identificador (`PAT-n`).

**Regla de entrada.** `PAT-0`: ningún patrón se aplica por costumbre; se aplica cuando su «cuándo SÍ» se cumple hoy. Se mide con la frase de justificación del plan, no con la opinión.

## 1. Servicio de funcionalidad (`PAT-1`)

- **Cuándo SÍ:** hay llamadas HTTP de una pantalla o de un recurso. El servicio concentra todos los usos del cliente HTTP.
- **Cuándo NO:** un servicio por endpoint; un servicio vacío que solo reexporta; llamar al endpoint desde el componente «porque es una sola vez».
- **Ejemplo mínimo:**

```ts
@Injectable()                                   // se provee en el módulo o componente
export class ReportService {
  constructor(private readonly http: HttpClient) {}
  list(page = 1, limit = 10): Observable<IReportPage> {
    return this.http.get<IReportPage>(`${environment.apiServer}/reports`, { params: { page, limit } });
  }
}
```

## 2. Mapeador de vista (`PAT-2`)

- **Cuándo SÍ:** se transforman 4 o más campos, o hay cálculo y formato, y el resultado se usa en 2 o más sitios o se prueba aparte. Reglas de estado («editable», «bloqueado») como funciones puras.
- **Cuándo NO:** la respuesta se pinta tal cual.
- **Ejemplo mínimo:** `export const isEditable = (s: Status) => s === 'draft' || s === 'rejected';` y `toViewModel(resp): RowView` en `report.mapper.ts`, con una prueba por tabla de casos.

## 3. Pipe puro frente a función (`PAT-3`)

- **Cuándo SÍ (pipe):** formato visual puro usado en 3 o más plantillas. Si también se usa en TypeScript (avisos, mensajes), el pipe y el código comparten **la misma función**.
- **Cuándo NO:** un solo uso (el valor llega calculado desde el mapeador); lógica de negocio (va a servicio o mapeador, nunca a un pipe); una llamada de método en la plantilla que calcula o recorre.
- **Ejemplo mínimo:** una función `formatMoney(n)` y un pipe `MoneyPipe` que la invoca; ningún sitio formatea con otra forma.

## 4. Subcomponente de presentación (`PAT-4`)

- **Cuándo SÍ:** bloque con `@Input` propios repetido 2 o más veces, plantilla de más de ~150 líneas o estado propio; bloque idéntico en 3 o más pantallas.
- **Cuándo NO:** 30 líneas o menos usadas una vez; dos usos con campos distintos; fragmentar por estética.
- **Ejemplo mínimo:** `<app-status-history [items]="history" />` con `ChangeDetectionStrategy.OnPush` y solo `@Input`.

## 5. Estado local, servicio con alcance o global (`PAT-5`)

- **Cuándo SÍ (local):** lo usa un solo componente. **(Servicio con alcance):** lo comparten padre e hijos; se provee en el `providers` del padre. **(Servicio de raíz con caché corta):** lo comparten pantallas sin relación.
- **Cuándo NO:** un store global. La instancia de origen decidió no tener uno; no se agrega por moda. Si alguien lo pide, se discute aparte con datos.
- **Ejemplo mínimo:** `@Injectable() class WizardState { private readonly _step = signal(1); readonly step = this._step.asReadonly(); }` provisto en el componente padre.

## 6. Facade (`PAT-6`)

- **Cuándo SÍ:** una pantalla coordina 3 o más servicios con pasos fijos y 2 o más hijos comparten ese estado.
- **Cuándo NO:** 1 o 2 servicios; para esconder el cliente HTTP.

## 7. Interceptor (`PAT-7`)

- **Cuándo SÍ:** solo preocupaciones transversales de **todas** las llamadas: token, indicador de carga, errores y sesión. El proyecto de origen tiene cuatro.
- **Cuándo NO:** una necesidad de una sola pantalla; poner el token, el indicador de carga o el aviso de error genérico a mano en un servicio (ya lo hace el interceptor y se duplicaría).
- **Ejemplo mínimo:** `intercept(req, next) { return next.handle(req.clone({ setHeaders: { Authorization: token } })); }`.

## 8. Un solo flujo de parámetros para filtros (`PAT-8`)

- **Cuándo SÍ:** búsqueda, filtros y paginación que disparan la misma lectura. Se detalla en `COD-8` y se da la receta en `recetas/README.md`.
- **Cuándo NO:** una lectura única al abrir la pantalla.

## 9. Contexto HTTP para la excepción por petición (`PAT-9`)

- **Cuándo SÍ:** una petición debe saltarse una preocupación transversal (no mostrar el indicador de carga, o no mostrar el aviso genérico porque el módulo cuenta el error con sus palabras). Se marca con un `HttpContextToken` leído por el interceptor. El contexto vive en Angular, no viaja como cabecera.
- **Cuándo NO:** cuando un solo aviso basta; entonces no se duplica el aviso del interceptor y el del módulo (dos avisos por el mismo fallo).
- **Ejemplo mínimo:** `export const OWN_ERRORS = new HttpContextToken<boolean>(() => false);` y `http.get(url, { context: new HttpContext().set(OWN_ERRORS, true) })`.

## 10. Guarda de ruta + directiva de permiso (`PAT-10`)

- **Cuándo SÍ:** la ruta exige un permiso (guarda funcional con `inject()`), y los elementos sueltos (un botón) se muestran por una directiva que consulta el mismo servicio de permisos. Los permisos se escriben con una **enumeración**, nunca con cadenas sueltas.
- **Cuándo NO:** tratar el permiso de la interfaz como autoridad (ver `SEG-4`).

## 11. Diálogo de revisión frente a confirmación liviana (`PAT-11`)

- **Cuándo SÍ (bloquea el cierre por clic afuera):** el diálogo muestra contenido para **revisar o leer** (detalle, documentos, un formulario con datos cargados). Se abre con `disableClose: true`.
- **Cuándo NO:** una confirmación de una línea puede cerrarse con clic afuera, porque no hay nada que perder.
- **Confirmación escrita:** una acción irreversible o que mueve dinero pide una **palabra escrita** además del botón (ver `SEG-5`).

## 12. Estados de la pantalla como patrón de plantilla (`PAT-12`)

- **Cuándo SÍ:** toda vista de datos declara cuatro estados: cargando, vacío, error y con datos. Un indicador de carga **por vista** (local o global, nunca los dos superpuestos). Lo que no aplica a un botón se **deshabilita** y el motivo se escribe.
- **Cuándo NO:** mostrar una pestaña sin filas; dejar que el usuario haga clic en una acción que el servidor va a rechazar.

## 13. Selector de lista con opción «todos» (`PAT-13`)

- **Cuándo SÍ:** un `mat-select` necesita mostrar una opción que representa «sin filtro». Material nunca selecciona una opción cuyo valor es `null` o `undefined` y cae al marcador de posición. Se usa un **valor centinela** (cadena vacía) solo para el enlace y se traduce a `undefined` antes de emitir el filtro.
- **Cuándo NO:** cambiar el contrato hacia el padre o hacia el servidor por esto; el centinela vive dentro del componente.
