# Evidencia · Angular + Material
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (convenciones de frontend, guía de diseño F1-F8 y A10-A14, reglas aprendidas del frontend, checklist visual, protocolo de verificación visual, catálogo pre-QA de diseño y de frontend, catálogo de hallazgos de interfaz, técnica de pruebas E2E) contrastada con el código de un frontend real de la misma instancia -->

> Tabla «regla → fuente: instancia de origen, sección X». Toda regla viene de **una sola instancia**: por la regla de R24 todas están **pendientes de evidencia** hasta contrastarlas con un segundo proyecto del mismo stack y registrar la decisión humana. El contraste con el código del frontend de la misma instancia valida que la regla **existe y se cumple allí**; no es una segunda instancia y no promueve nada. La evidencia es correlacional: que una práctica se use no la hace «la mejor».

Estados: `pendiente de evidencia` (una sola instancia) · `respaldada` (2 o más instancias independientes y decisión humana).

## Reglas de arquitectura.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| ARQ-1 | guía de diseño §0 (principio rector) | pendiente de evidencia |
| ARQ-2 a ARQ-4 | convenciones de frontend §1 (estructura y enrutador de funcionalidad), §2 (componentes) | pendiente de evidencia |
| ARQ-5 | convenciones de frontend §8 (título por prefijo de ruta) | pendiente de evidencia |
| ARQ-6 a ARQ-15 | guía de diseño F1, F4, F7, F8; reglas aprendidas del frontend 1-3, 6, 7, 11; convenciones de frontend §3.2b, §3.3 | pendiente de evidencia |
| ARQ-16 | derivada de guía de diseño F3, F5, F7, A11, A14 (no es una escala nombrada en el origen) | pendiente de evidencia |
| ARQ-17 | convenciones de frontend §3.2; guía F2, A10 | pendiente de evidencia |
| ARQ-18, ARQ-19 | guía F3, A11; reglas aprendidas del frontend 4, 9 | pendiente de evidencia |
| ARQ-20 a ARQ-22 | guía F5, F6, F7, A13, A14; convenciones de frontend §3.2b (estado) | pendiente de evidencia |
| ARQ-23, ARQ-24 | reglas aprendidas del frontend 5, 10 | pendiente de evidencia |
| ARQ-25 | convenciones de frontend §3.1, §3.2 | pendiente de evidencia |
| ARQ-26 | habilidad del frontend: tabla de decisión («si el patrón ya existe, se usa») | pendiente de evidencia |
| ARQ-27, ARQ-28 | convenciones de frontend §5 (exportación a hoja de cálculo y búsqueda por librería) | pendiente de evidencia |
| ARQ-29 | habilidad del frontend: reglas duras (librería nueva se propone) | pendiente de evidencia |

## Reglas de patrones.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| PAT-0 a PAT-6 | guía de diseño catálogo F1-F8, árboles A10-A14 | pendiente de evidencia |
| PAT-7 | guía F8; convenciones de frontend §3.3; código de los interceptores (contraste) | pendiente de evidencia |
| PAT-8 | guía §7.1 reglas 4 y 5 | pendiente de evidencia |
| PAT-9 | código de interceptores y de su contexto HTTP (contraste); convenciones §3.3 | pendiente de evidencia |
| PAT-10 | convenciones de frontend §7; reglas aprendidas del frontend 11; código de la guarda (contraste) | pendiente de evidencia |
| PAT-11 | catálogo pre-QA de frontend (modal de revisión); catálogo pre-QA de diseño (acción prohibida, confirmación escrita) | pendiente de evidencia |
| PAT-12 | checklist visual §3, §5; catálogo pre-QA de frontend (texto del botón) | pendiente de evidencia |
| PAT-13 | catálogo de hallazgos de interfaz (selector «todos» tras limpiar) | pendiente de evidencia |

## Reglas de codificacion.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| COD-1 a COD-4 | guía §0.5 (paradigma); convenciones de frontend §3.2b | pendiente de evidencia |
| COD-5 a COD-12 | guía §7.1 reglas 1-7; reglas aprendidas del frontend 8 | pendiente de evidencia |
| COD-13 a COD-16 | guía §7.1 reglas 8 y 9 | pendiente de evidencia |
| COD-17, COD-18 | guía §7.1 regla 8, A12; checklist visual §5 | pendiente de evidencia |
| COD-19 | convenciones de frontend §8 (plantillas) | pendiente de evidencia |
| COD-20 | catálogo pre-QA de frontend (enumeración sin traducir); checklist visual §2 | pendiente de evidencia |
| COD-21 a COD-23 | convenciones de frontend §4 y habilidad §5 | pendiente de evidencia |
| COD-24 | reglas aprendidas del frontend 7; código del normalizador de errores (contraste) | pendiente de evidencia |
| COD-25 | habilidad §6 (mejores prácticas); código de configuración de TypeScript (contraste) | pendiente de evidencia |
| COD-26 | reglas aprendidas del frontend 11 | pendiente de evidencia |
| COD-27 a COD-31 | convenciones de frontend §5c; catálogo pre-QA de frontend (recalcular, redondear); checklist visual §8 | pendiente de evidencia |
| COD-32 a COD-36 | convenciones de frontend §6 (checklist de anti-patrones); catálogo pre-QA de frontend (rejilla); checklist visual §7 | pendiente de evidencia |
| COD-37, COD-38 | catálogo pre-QA de diseño (botón de Material, pista de campo) | pendiente de evidencia |
| COD-39 | protocolo de verificación visual (medir en vez de mirar) | pendiente de evidencia |
| COD-40, COD-41 | catálogo pre-QA de diseño (texto de estado); checklist visual §4 | pendiente de evidencia |
| COD-42 | sin fuente: por extraer | por extraer |
| COD-43, COD-44 | convenciones de frontend §8 (comentarios y Prettier) | pendiente de evidencia |
| COD-45 | convenciones de frontend §8 (adaptador de fechas) | pendiente de evidencia |

## Reglas de datos.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| DAT-1 a DAT-4 | convenciones de frontend §3.3, §4; habilidad §8 (contrato campo por campo y mismo cálculo en dos lugares) | pendiente de evidencia |
| DAT-5 | reglas aprendidas del frontend 2; convenciones §3.2b | pendiente de evidencia |
| DAT-6, DAT-7 | catálogo pre-QA de pantallas sin caché; guía A15 | pendiente de evidencia |
| DAT-8, DAT-9 | catálogo pre-QA de frontend (volver al listado); checklist visual §5 | pendiente de evidencia |
| DAT-10, DAT-11 | catálogo de hallazgos de interfaz (cancelación de peticiones); checklist visual §5 | pendiente de evidencia |
| DAT-12 | convenciones de frontend §8; guía de reglas de fechas | pendiente de evidencia |
| DAT-13 a DAT-15 | código de utilidades de fechas (contraste); checklist visual §1 | pendiente de evidencia |
| DAT-16 a DAT-20 | convenciones de frontend §5 (exportación); checklist visual §1 y §6; técnica de pruebas E2E | pendiente de evidencia |

## Reglas de pruebas.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| PRU-1 a PRU-4 | código de pruebas observado (contraste); catálogo pre-QA de diseño (una prueba por regla) | pendiente de evidencia |
| PRU-5 | sin fuente suficiente: por extraer | por extraer |
| PRU-6 | convenciones de frontend §8 (probar en el navegador) | pendiente de evidencia |
| PRU-7 a PRU-15 | protocolo de verificación visual (matriz, evidencia, medir, ventana, datos); mapeo diseño contra implementación | pendiente de evidencia |
| PRU-16 a PRU-21 | técnica de pruebas E2E (catálogo de comportamientos del marco) | pendiente de evidencia |
| PRU-22 | técnica de pruebas E2E (limitación conocida): por extraer | por extraer |

## Reglas de seguridad.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| SEG-1 | convenciones de frontend §3.3; código del interceptor de token y del servicio de token (contraste) | pendiente de evidencia |
| SEG-2, SEG-3 | código del interceptor de errores (contraste) | pendiente de evidencia |
| SEG-4, SEG-5 | catálogo pre-QA de diseño (acción prohibida activa; confirmación escrita) | pendiente de evidencia |
| SEG-6 | código de la reautenticación puntual y sus pruebas (contraste) | pendiente de evidencia |
| SEG-7 | convenciones de frontend §7; checklist visual §9; código de la guarda (contraste) | pendiente de evidencia |
| SEG-8 | reglas aprendidas del frontend 2; código de reglas de archivos (contraste) | pendiente de evidencia |
| SEG-9 a SEG-11 | reglas generales de seguridad de Angular, **sin evidencia de instancia** | pendiente de revisión humana |
| SEG-12 | convenciones de frontend §3.3; habilidad: reglas duras | pendiente de evidencia |
| SEG-13 | habilidad §8 (revisión de seguridad) | pendiente de evidencia |

## Reglas de rendimiento.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| REN-1, REN-8 | catálogo pre-QA de pantallas sin caché | pendiente de evidencia |
| REN-2 a REN-5 | guía §7.1 reglas 2, 4, 8; checklist visual §5 | pendiente de evidencia |
| REN-6 | convenciones de frontend §1 (carga diferida); configuración de compilación (contraste) | pendiente de evidencia |
| REN-7 | guía árbol A15 | pendiente de evidencia |
| REN-9 | checklist visual §10; convenciones de frontend §5 (rejilla) | pendiente de evidencia |
| REN-10 | guía §7.1 regla 5 | pendiente de evidencia |
| REN-11, REN-12 | guía §7.1 regla 8; checklist visual §5 | pendiente de evidencia |

## Reglas de observabilidad.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| OBS-1 | protocolo de verificación visual (consola y red) | pendiente de evidencia |
| OBS-2 a OBS-4 | código del interceptor de errores y del normalizador (contraste) | pendiente de evidencia |
| captura remota, trazas, métricas, alertas | sin fuente | por extraer |

## Reglas de errores-frecuentes y recetas

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| ERR-1 a ERR-36 | catálogos pre-QA de diseño y de frontend, de hallazgos de interfaz, checklist visual, convenciones de frontend (cada fila apunta a su regla) | pendiente de evidencia |
| REC-1 a REC-12 | derivadas de las reglas a las que apuntan; los fragmentos son ejemplos inventados | pendiente de evidencia |

## Decisiones humanas y alternativas descartadas

- Aún no hay decisiones registradas para este perfil.
- Descartado en la instancia de origen (se conserva como regla negativa): un store global (`ARQ-20`); clase base o componente genérico de tabla (`ARQ-23`); unificar diálogos de dominios distintos (`ARQ-24`); `subscriptSizing="dynamic"` en todos los campos de un panel (`COD-38`); normalizar el espacio en blanco al capturar texto en pruebas E2E (`PRU-20`); generalizar a todo el proyecto el ajuste del clic en `mat-select` por la duda de romper casos que ya pasan (`PRU-19`).

## Divergencias observadas (guía contra código)

- **Cierre de suscripciones.** La guía exige `takeUntilDestroyed` en todo flujo de larga vida; el código real lo usa en una fracción pequeña de los componentes (23 de ~300 archivos de componente contienen el operador, 2 usan `OnPush`). La regla es el estándar deseado, no el estado medido. Además hay dos posturas sobre las peticiones de un disparo (`COD-5`).
- **Umbral del subcomponente.** El catálogo (F3) da 2 repeticiones; las reglas aprendidas (4) dan 3 pantallas para el bloque de presentación (`ARQ-19` conserva las dos).
- **Tipado.** El proyecto real tiene `strict` y `strictTemplates` apagados; `COD-25` recomienda evitar `any`, pero eso no se cumple por configuración.
- **Standalone.** El origen es un proyecto por módulos (NgModule) con hojas standalone (~201 de ~299 componentes); no hay evidencia sobre un proyecto 100 % standalone.
- **Pruebas.** Hay unas 138 pruebas, pero las de las funcionalidades recientes son de funciones puras y de servicios; no hay una regla registrada para pruebas de componentes (`PRU-5`).
- Los umbrales numéricos (15 métodos, ~300 líneas, ~150 líneas de plantilla, 500 ms, TTL de 60 s, 5 de concurrencia, 4 MB de presupuesto) se midieron en una sola base de código; falta contrastarlos.

## Pendiente de evidencia: lista completa

Todas las reglas anteriores. Las que dependen además de una decisión puntual de la instancia (puntos de partida, no estándares): los umbrales numéricos citados, `ARQ-17`, `ARQ-18`, `REN-6`, `REN-7` y `REN-9`.

## Por extraer, y por qué (R24)

- Accesibilidad más allá del contraste (ARIA, foco, teclado, lectores de pantalla): el origen no registra reglas (`COD-42`).
- Pruebas de componentes con `TestBed` (`PRU-5`) y simulación de sesión vencida en E2E (`PRU-22`).
- Observabilidad del cliente: captura remota de errores, trazas, métricas, alertas.
- Formularios reactivos con `FormBuilder`: el origen los usa (con una biblioteca de campos compartidos) pero **no registra reglas propias**; no se infieren del código.
- Almacenamiento del token del cliente (`HttpOnly` frente a almacenamiento local, `SEG-11`): decisión de cada proyecto.
