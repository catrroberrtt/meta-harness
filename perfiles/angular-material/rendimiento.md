# Rendimiento · Angular + Material
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (guía de diseño §7.1 y árbol A15, checklist visual §5 y §10, catálogo pre-QA de pantallas sin caché, convenciones de frontend §5, configuración de compilación observada); ver evidencia.md -->

> Cómo se mide, qué se optimiza primero y qué no se cachea. Cada regla lleva un identificador (`REN-n`).

- `REN-1` **Se mide antes de optimizar**, contra un entorno real; no se afirma una mejora sin cifra. Una latencia lenta percibida se atribuye con datos (qué llamada, cuánto tarda) antes de tocar el cliente: la causa real suele estar en el servidor.
- `REN-2` **Detección de cambios `OnPush`** en los componentes de presentación (`@Input` + eventos), con signals para el estado local (`COD-15`, `COD-16`).
- `REN-3` `track` por identidad estable en `@for` (`COD-18`); una lista que cambia y se rastrea por índice rehace el DOM.
- `REN-4` **Nada que calcule en la plantilla** (`COD-17`): una llamada de método con `filter`/`map` en la plantilla se ejecuta en cada ciclo y congela la pantalla. Se calcula una vez (mapeador, `computed`, memoización) y se abre cada pestaña al probar: un bloqueo en una bloquea todo.
- `REN-5` Un observable se suscribe **una sola vez** en la plantilla (`async` una vez; dos son dos peticiones). `switchMap` cancela la lectura anterior; la escritura rápida lleva `debounceTime` + `distinctUntilChanged` (una petición por pausa, no por tecla); `mergeMap` con tope de concurrencia (`COD-9`).
- `REN-6` **Carga diferida** de cada funcionalidad desde el enrutador raíz (`ARQ-2`); el compilador lleva **presupuestos de tamaño** (inicial y por componente) con advertencia y error. Las cifras del origen (advertencia a 4 MB, error a 5 MB) son un punto de partida, no un estándar.
- `REN-7` **Qué no se cachea.** Árbol del origen: ¿hay una consulta **medida** de más de ~500 ms? Si no, no se cachea. ¿Alimenta dinero, saldos o permisos? Entonces no se cachea. ¿Tolera un TTL de ≥ 60 s? Si no, no se cachea. ¿Se probó antes el índice y reescribir la consulta? Hacerlo primero. (Son puntos de partida de una sola instancia.)
- `REN-8` Una pantalla que espera a 2 o más llamadas en paralelo no pinta nada hasta que todas llegan: se mide, se pregunta si el servidor puede materializar el dato y se considera pintar parcialmente (`DAT-6`). Un `cy.wait` largo no es una solución.
- `REN-9` **Listas largas:** paginación del servidor con 10 registros por página por defecto y sin desplazamiento interno con la opción más pequeña; para rejillas pesadas se usa el componente de rejilla ya instalado en lugar de una tabla de Material con miles de filas. Se prueba con un volumen real.
- `REN-10` Una escritura repetida (doble clic, doble envío) se evita con `exhaustMap` y el botón apagado mientras hay una en curso (`COD-9`).
- `REN-11` Los recursos manuales se liberan (URL de objeto, escuchas, temporizadores) en `ngOnDestroy` (`COD-14`); una fuga de suscripción acumula callbacks (`COD-5`).
- `REN-12` Un solo indicador de carga por vista (local o global, no ambos superpuestos). Los indicadores globales que lleva el interceptor se silencian por petición con un contexto (`PAT-9`), no se duplican a mano.
