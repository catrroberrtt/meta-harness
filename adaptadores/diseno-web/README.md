# Adaptador: Diseño web

<!-- tipo: adaptador · capa: 3 -->
<!-- revisado: 2026-10-09 · vence: 90d · fuente: contrato de adaptadores del repositorio y docs/ANALISIS-OPEN-DESIGN.md -->

## Específico de `diseno-web`

Adaptador de **sitios web públicos** de una empresa: landing, sitio corporativo, página de producto, precios, lista de espera, preguntas frecuentes y documentación pública. Sirve a dos entradas del meta-harness: la **opción ERP** («quiero mi landing» sobre un ERP ya compuesto) y el **proyecto nuevo**. No ofrece tickets ni almacén de documentos: entrega una **carpeta de sitio estático** y su informe de verificación.

La herramienta de generación es **opcional y externa**. Hoy se conoce una (open-design, `nexu-io/open-design`, Apache-2.0; análisis en `docs/ANALISIS-OPEN-DESIGN.md`), pero el método solo conoce las operaciones de abajo: cualquier otra herramienta, o ninguna, las cumple igual. El adaptador **nunca** la instala, **nunca** copia su código dentro de un repositorio nuestro y **nunca** depende de ella para dar por terminada una web.

## Qué pide al usuario (entradas)

| Entrada | Obligatoria | De dónde sale | Notas |
|---|---|---|---|
| `brief` | sí | la persona, con `plantillas/web/brief-landing.md` | objetivo, acción principal, secciones, qué se excluye |
| `marca` | sí | la **instancia** (`plantillas/web/ficha-de-marca.md` rellena) | nombre, voz, logotipo (archivo de la empresa), colores base. **Nunca** vive en este repositorio |
| `tokens` | sí | derivados con `plantillas/web/mapa-de-tokens.md` desde el tema del ERP (`_tokens.scss`) o desde la ficha de marca | escala de marca, claro/oscuro, radios, tipografía |
| `modulos_erp` | solo opción ERP | el catálogo y el `erp.lock.json` de la instancia | decide qué se puede prometer en la web (p. ej. solo hablar de facturación si ese módulo está instalado) |
| `publico` | sí | la persona | quién llega a la web y desde dónde |
| `idioma` | sí | la persona | código BCP 47 (`es`, `es-PE`, `en`…); se escribe en `<html lang>` |
| `contenido_real` | sí | la persona | textos, cifras y testimonios **reales**; si falta algo se marca como pendiente, no se inventa |
| `permiso_red` | no (`no`) | la persona | si la herramienta puede usar la red o servicios de terceros (modelos, imágenes, fuentes remotas, telemetría) |

## Qué entrega (salidas) y dónde

Todo cae en la **carpeta del sitio de la instancia** (por defecto `sitio/` en el repositorio de la instancia; el meta-harness no la crea fuera de ella).

| Salida | Ruta | Descripción |
|---|---|---|
| Páginas estáticas | `sitio/*.html` | HTML con CSS propio; JavaScript solo si el brief lo justifica |
| Activos | `sitio/activos/` | imágenes, iconos y fuentes **con su licencia declarada** (ver «Activos») |
| Tokens web | `sitio/tokens.css` | variables CSS generadas desde el mapa de tokens |
| Ficha de marca | `sitio/DISENO.md` | ficha de marca rellena (la que usa la herramienta como contexto) |
| Registro de activos | `sitio/activos/LICENCIAS.md` | un renglón por activo: origen, autoría, licencia, uso permitido |
| Informe | `sitio/INFORME-VERIFICACION.md` | resultado del verificador estático + lista manual firmada |

## Operaciones

El método solo conoce estas operaciones.

| Operación | Obligatoria | Descripción |
|---|---|---|
| `detectar-herramienta()` | sí | Devuelve `disponible: sí/no` y cuál. Se hace con `python3 herramientas/web-detectar-herramienta.py`; solo mira el PATH, **no ejecuta** la herramienta ni usa la red |
| `preparar-brief(brief, marca, tokens, modulos_erp, publico, idioma)` | sí | Rellena las plantillas de `plantillas/web/` y deja el brief completo en `sitio/DISENO.md`; sin campos `[OBLIGATORIO]` vacíos |
| `generar-sitio(brief_completo)` | sí | Con herramienta: se le pasa el brief y los tokens (ver «Invocación»). Sin herramienta: **modo manual** |
| `verificar-sitio(carpeta)` | sí | Corre `python3 herramientas/web-verificar-sitio.py <carpeta>` y cierra los puntos de control de abajo |
| `publicar-sitio(carpeta, destino)` | no | Escritura hacia afuera: se muestra qué se publicará y dónde y **espera confirmación**; sin credenciales en el repositorio |

## Invocación de la herramienta externa (sin depender de ella)

1. `detectar-herramienta()`. Si dice `no`, ir al **modo manual**; no es un error.
2. Si dice `sí`, mostrar a la persona **antes de ejecutar**: qué herramienta es, que puede enviar el brief y el contenido a su proveedor de modelos y, según su configuración, telemetría al proyecto (ver `docs/ANALISIS-OPEN-DESIGN.md` §4), y pedir confirmación. **Regla de telemetría (decisión 2026-10-09):** una herramienta externa de diseño se ejecuta **solo dentro de un contenedor sin telemetría** (sin salida de red hacia el proyecto de la herramienta ni hacia analítica) **y con la confirmación explícita de la persona**, dada para esa ejecución. Si falta cualquiera de las dos cosas, **modo manual**. Sin `permiso_red: sí` tampoco se sigue por esta vía.
3. Pasar a la herramienta **solo** el brief completo, `sitio/tokens.css` y `sitio/DISENO.md`; nunca credenciales, datos de clientes ni contenido del ERP. Usar el sistema de diseño **de la empresa** (la ficha de marca) o uno **genérico sin marca**; los sistemas «inspirados en marcas reales» (Stripe, Apple, BMW…) que la herramienta trae de fábrica están **prohibidos** en este flujo, ni siquiera como referencia a imitar (decisión 2026-10-09; `estandares/diseno-web.md` §6).
4. Traer el resultado a `sitio/`, **revisarlo línea a línea** (es contenido generado), completar `activos/LICENCIAS.md` y seguir con `verificar-sitio`.

Las órdenes concretas de cada herramienta (p. ej. `od …`) son de la herramienta, cambian entre versiones y **no** se fijan aquí; se leen de su documentación el día que se usa y se declaran «no verificado» hasta ejecutarlas.

## Modo manual (sin herramienta)

1. Rellenar `plantillas/web/brief-landing.md`, `ficha-de-marca.md` y `mapa-de-tokens.md`.
2. Generar `sitio/tokens.css` a mano o con el agente de código habitual, a partir del mapa de tokens.
3. Escribir las páginas con HTML semántico (`header`, `nav`, `main`, `section`, `footer`), una sola `h1`, estilos que lean **solo** las variables de `tokens.css`.
4. Seguir con `verificar-sitio`.

El modo manual produce el mismo resultado exigible; la herramienta externa solo acelera el borrador.

## Puntos de control (se cierran antes de dar por terminada una web)

Automáticos: `python3 herramientas/web-verificar-sitio.py sitio/` debe salir con código 0 (ver lo que comprueba y lo que **no** en `estandares/diseno-web.md` §5).

| # | Punto | Cómo se comprueba |
|---|---|---|
| 1 | `lang` y `title` en cada página | automático |
| 2 | Una `h1` por página y jerarquía sin saltos | automático |
| 3 | Texto alternativo en toda imagen (o `alt=""` si es decorativa) | automático |
| 4 | Contraste de los pares de color de `tokens.css` (claro y oscuro) ≥ WCAG AA | automático |
| 5 | Texto en unidades relativas (`rem`/`em`/`%`), sin `px` en tamaños de fuente | automático |
| 6 | Peso de cada página y de cada activo bajo el presupuesto | automático |
| 7 | Enlaces y recursos internos que existen | automático |
| 8 | Sin secretos y sin dominios de seguimiento o recursos remotos no declarados | automático |
| 9 | Cada activo tiene su línea en `LICENCIAS.md` | automático |
| 10 | Sin señales de relleno (texto de relleno, métricas inventadas, imágenes de marcadores externos) | automático |
| 11 | Navegación por teclado completa y foco visible | **a mano** |
| 12 | Lector de pantalla recorre la página con sentido | **a mano** |
| 13 | Rendimiento real (carga en red móvil lenta) | **a mano** con la herramienta de la instancia |
| 14 | Cada afirmación comercial corresponde a un módulo realmente instalado o a un hecho real de la empresa | **a mano**, contra `modulos_erp` |
| 15 | Textos legales (privacidad, cookies, términos) revisados por la empresa | **a mano** |
| 16 | Marca: ningún elemento imita la identidad de otra empresa | **a mano**; el verificador ayuda: marca como error `marca-ajena` una ficha `DISENO.md` «inspirada en» o «al estilo de» una marca real |

Lo marcado «a mano» queda anotado con fecha y autor en `INFORME-VERIFICACION.md`. Lo que no se comprobó se escribe **no verificado**.

## Activos

Todo activo (imagen, icono, fuente, ilustración) entra con origen, autoría y licencia en `activos/LICENCIAS.md`. Las fuentes tipográficas se **alojan en local**, dentro del propio sitio: nunca desde Google Fonts ni otro servicio remoto (decisión 2026-10-09; el verificador ya lo exige con `recurso-remoto`). Sin licencia clara no entra.

## Autenticación y cuando no existe

Como en todo adaptador: nunca se guardan credenciales en el repositorio ni en la instancia. Las claves de la herramienta o del proveedor de modelos las guarda la persona en su entorno, fuera de los repositorios. Si la herramienta no existe, el adaptador declara `disponible: no`, **no falla**, usa el modo manual y lo informa. Las publicaciones se muestran y esperan confirmación.

## Decisiones registradas (2026-10-09)

| # | Decisión | Dónde se aplica |
|---|---|---|
| 1 | Los sistemas de diseño «inspirados en marcas reales» quedan **prohibidos** en este flujo, ni como referencia a imitar. Solo sistemas propios de la empresa o genéricos sin marca | «Invocación» paso 3, punto 16, `estandares/diseno-web.md` §6, verificador (`marca-ajena`) |
| 2 | Telemetría de herramientas externas de diseño: solo dentro de un contenedor sin telemetría **y** con confirmación explícita; si no, modo manual | «Invocación» paso 2, `estandares/diseno-web.md` §7 |
| 3 | Fuentes tipográficas remotas: se alojan en local | «Activos», `estandares/diseno-web.md` §7 |

## Origen

Contrato derivado de los adaptadores existentes; la idea de generación asistida con sistema de diseño se adapta de nexu-io/open-design (Apache-2.0), registro en `docs/ANALISIS-OPEN-DESIGN.md` §8.
