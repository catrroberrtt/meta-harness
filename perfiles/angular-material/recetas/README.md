# Recetas · Angular + Material
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (guía de diseño §7.1, convenciones de frontend §3 y §5, protocolo de verificación visual, catálogo pre-QA); ejemplos inventados; ver evidencia.md -->

> Pasos de las tareas típicas del stack. Cada receta lleva un identificador (`REC-n`) y apunta a la regla que aplica. Los fragmentos son ejemplos mínimos inventados, no código de ningún proyecto.

## REC-1 Listado con filtros, búsqueda y paginación (`COD-8`, `COD-5`)

1. Servicio de la funcionalidad con `list(params)` tipado (`PAT-1`).
2. En el componente, un flujo de parámetros y un solo `switchMap`:

```ts
readonly text$ = new Subject<string>();
readonly filter$ = new BehaviorSubject<string | undefined>(undefined);
readonly page$ = new BehaviorSubject(1);

readonly vm$ = combineLatest([
  this.text$.pipe(debounceTime(300), distinctUntilChanged(), startWith('')),
  this.filter$,
  this.page$,
]).pipe(
  switchMap(([text, filter, page]) =>
    this.api.list({ text, filter, page }).pipe(
      map(toViewModel),
      startWith(LOADING),
      catchError(err => of(errorState(apiError(err).message)))   // dentro del switchMap
    )
  )
);
```

3. Cambiar un filtro reinicia `page$` a 1 en el mismo flujo; la plantilla usa `@if (vm$ | async; as vm)` una sola vez.
4. Estados cargando, vacío y error salen de `vm`; 10 filas por página por defecto.

## REC-2 Guardar sin doble clic (`COD-9`, `REN-10`)

```ts
readonly save$ = new Subject<void>();
constructor() {
  this.save$.pipe(
    exhaustMap(() => this.api.save(this.form.getRawValue()).pipe(catchError(e => { this.notify(apiError(e).message); return EMPTY; }))),
    takeUntilDestroyed()
  ).subscribe(() => this.notifyOk());
}
```

El botón llama `save$.next()`, queda apagado mientras hay una en curso y la acción irreversible pide la palabra de confirmación (`SEG-5`). Prueba: pedidos en paralelo, no uno solo.

## REC-3 Servicio que encadena llamadas, con su prueba (`ARQ-8`, `PRU-2`)

1. El servicio expone un solo método (`createFull(input)`) que ordena las llamadas con `switchMap` y devuelve un resultado que dice qué pasos fallaron.
2. La prueba arma un doble plano de `HttpClient` que registra `MÉTODO ruta` y permite fallar una firma concreta, y aserta la secuencia y el resultado para cada rama.

## REC-4 Mapeador puro con tabla de casos (`PAT-2`, `PRU-1`)

```ts
export const statusLabel = (s: string) => LABELS[s] ?? s;
export const isEditable = (s: Status) => s === 'draft';
// spec
[['draft', true], ['sent', false]].forEach(([s, ok]) =>
  it(`isEditable(${s}) = ${ok}`, () => expect(isEditable(s as Status)).toBe(ok)));
```

## REC-5 Botón de Material con color propio (`COD-37`)

```scss
.btn-danger {
  --mdc-filled-button-container-color: #c62828;
  --mdc-filled-button-label-text-color: #fff;
  --mdc-filled-button-disabled-container-color: #f2b8b5;
  --mdc-filled-button-disabled-label-text-color: #fff;
}
```

Verificar con `getComputedStyle(boton).backgroundColor` y `disabled`, activo y apagado.

## REC-6 Selector de fecha (`COD-45`, `DAT-12`, `DAT-13`)

1. En el componente: `providers: [provideNativeDateAdapter(), { provide: MAT_DATE_LOCALE, useValue: 'es-ES' }]`.
2. `<input matInput [matDatepicker]="p" readonly>` y `<mat-datepicker #p>`; el valor sale con `toYmd` y entra con `fromYmd`.
3. Abrir la pantalla en el navegador y mirar la consola: la prueba unitaria no detecta el proveedor que falta.

## REC-7 Opción «todos» en un `mat-select` (`PAT-13`)

El enlace usa `''`; el getter traduce `null → ''` al mostrar y `onChange` traduce `'' → undefined` antes de emitir al padre. La opción de la plantilla pasa de `[value]="null"` a `[value]="''"`.

## REC-8 Excepción por petición con contexto HTTP (`PAT-9`)

1. `export const SILENCE = new HttpContextToken<boolean>(() => false);`
2. El interceptor lee `req.context.get(SILENCE)` y se salta el indicador de carga (o el aviso de error).
3. El servicio lo marca: `http.get(url, { context: new HttpContext().set(SILENCE, true) })`.

## REC-9 Diálogo de revisión (`PAT-11`)

`dialog.open(Detail, { disableClose: true, autoFocus: false, data })`; el pie lleva un botón explícito de cerrar. Una acción irreversible agrega un campo de palabra de confirmación y mantiene el botón apagado hasta que coincide.

## REC-10 Medir contraste en el navegador (`PRU-12`)

Con la consola o una herramienta de ejecución de JavaScript sobre el componente abierto:

```js
const lum = ([r,g,b]) => { const f = v => (v/=255) <= .03928 ? v/12.92 : ((v+.055)/1.055)**2.4; return .2126*f(r)+.7152*f(g)+.0722*f(b); };
const bg = el => { for (let e = el; e; e = e.parentElement) { const c = getComputedStyle(e).backgroundColor; if (!/rgba\(.*, 0\)|transparent/.test(c)) return c.match(/\d+/g).slice(0,3).map(Number); } return [255,255,255]; };
[...document.querySelectorAll('*')].filter(e => e.childNodes.length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
  .map(e => { const fg = getComputedStyle(e).color.match(/\d+/g).slice(0,3).map(Number), a = lum(fg), b = lum(bg(e)); return { e, r: (Math.max(a,b)+.05)/(Math.min(a,b)+.05) }; })
  .filter(x => x.r < 4.5).sort((a,b) => a.r - b.r).slice(0, 10);
```

Se revisan los menores de 4.5 (los botones deshabilitados están exentos), en claro y oscuro.

## REC-11 Prueba E2E que espera la carga inicial y el clic (`PRU-17`)

```js
cy.intercept('GET', '**/resource*').as('load');   // antes de navegar
cy.visit('/ruta'); cy.wait('@load');              // carga inicial terminada
cy.intercept('GET', '**/resource*').as('reload'); // antes del clic
cy.get('.range button').contains('90').click(); cy.wait('@reload');
```

## REC-12 Antes de entregar una pantalla (`PRU-7` a `PRU-15`)

1. Compilar y tipar acotado; reportar la salida real.
2. Abrir cada pantalla y recorrer la matriz; consola y red al final de cada flujo.
3. Medir contraste, recortes, peticiones por escritura y colores del botón.
4. Tabla diseño-contra-implementación con veredicto por pieza.
5. Restaurar los datos de prueba y declarar lo que no se pudo ver.
