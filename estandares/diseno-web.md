# Estándar de diseño web (landing, sitio corporativo, página de producto)

<!-- tipo: estándar técnico · capa: 2 -->
<!-- revisado: 2026-10-08 · vence: 90d · fuente: docs/ANALISIS-OPEN-DESIGN.md y la herramienta herramientas/web-verificar-sitio.py, con sus pruebas -->

Reglas para cualquier web pública de una empresa, sea el sitio de un cliente del ERP o de un proyecto nuevo. Independiente de la herramienta que genere el borrador (ver `adaptadores/diseno-web/`). Lo medible lo mide `herramientas/web-verificar-sitio.py`; lo demás es lectura humana y queda anotado.

## 1. Principios

1. **La marca es de la empresa, no del harness.** Nombre, logotipo, colores, voz y datos de la empresa salen de su **instancia**; en este repositorio solo hay ejemplos inventados.
2. **Una identidad, tres superficies.** El ERP, la web y los documentos de una misma empresa comparten los mismos tokens de marca (sección 3); no se redefinen a ojo en cada superficie.
3. **Contenido real o pendiente.** Nada de texto de relleno, cifras inventadas ni testimonios fabricados: lo que no se sabe se marca «pendiente» en el brief.
4. **Lo prometido existe.** Una web del ERP solo anuncia lo que los módulos instalados hacen hoy (el catálogo y el `erp.lock.json` de la instancia mandan).
5. **Medir antes de afirmar.** «Listo» exige la salida del verificador y la lista manual cerrada; lo no comprobado se dice **no verificado**.

## 2. Qué nunca va en este repositorio

Marcas, logotipos, textos comerciales, datos de personas o clientes, credenciales, claves de proveedores de modelos, ni ningún activo de una empresa real. Las plantillas de `plantillas/web/` usan una empresa inventada («Ejemplo S. A.»).

## 3. Puente de tokens: ERP, web y documentos

El ERP define sus tokens en `frontend/src/styles/_tokens.scss` (escala de marca de seis pasos, superficies, texto, estados, radios, tipografía; tema claro y oscuro) y la instancia sobrescribe la marca en ejecución a partir de **un color base**. La web reutiliza **los mismos nombres y la misma escala**, de modo que cambiar el color base de la empresa cambia las tres superficies a la vez. El mapa campo por campo está en `plantillas/web/mapa-de-tokens.md`; el resumen:

| Papel | Token del ERP | Token de la web | Regla |
|---|---|---|---|
| Escala de marca | `--brand-400` … `--brand-900` | igual | Misma escala generada desde el mismo color base |
| Fondo de la página | `--app-bg` | `--bg` | |
| Superficie de tarjeta | `--app-surface`, `--app-surface-2` | `--surface`, `--surface-2` | |
| Borde | `--app-border` | `--border` | |
| Texto y texto atenuado | `--app-text`, `--app-muted` | `--text`, `--muted` | |
| Foco | `--focus-ring` | igual | ≥ 3:1 contra el fondo |
| Estados | `--tone-ok/warn/danger/info-bg/fg` | igual | El color dice algo solo cuando hay algo que decir |
| Radios | `--radius`, `--radius-control` | igual | |
| Tipografía | `--font-display`, `--font-body` | igual | Ver sección 6 sobre fuentes |
| Solo web | — | `--on-brand`, `--max-w`, `--section-gap`, `--text-sm…--text-4xl` | No existen en el ERP |
| Solo ERP | `--tb-*`, `--sb-*`, `--tile-*`, `--row-h`, `--sb-w` | (no se llevan) | Pertenecen al marco de la aplicación |

Tema oscuro: se declara bajo `:root[data-theme='dark']` **y** bajo `@media (prefers-color-scheme: dark)` para `:root:not([data-theme='light'])`, con los mismos nombres. Los componentes de la web **solo leen variables**: un color escrito fuera de `:root` es un defecto que el verificador avisa (sección 5, «hex crudos fuera de `:root`»).

## 4. Accesibilidad: el piso de trabajo

Objetivo de trabajo: **WCAG 2.2 AA**. Cubre lo que hoy piden las referencias habituales (UE, EN 301 549 sobre WCAG 2.1 AA; EE. UU., WCAG 2.1 AA como criterio de hecho). Vale como piso, no como techo, y no sustituye la asesoría legal de la empresa.

- Contraste: texto normal ≥ 4,5:1; texto grande (≥ 24 px o ≥ 18,5 px en negrita) y componentes de interfaz ≥ 3:1; el foco ≥ 3:1. Los umbrales son inclusivos y no se redondean.
- `lang` en `<html>` y un `<title>` descriptivo y distinto por página.
- Una sola `h1` por página, jerarquía sin saltos (`h2` tras `h1`…).
- Toda imagen con `alt` (o `alt=""` si es decorativa); los iconos que solo decoran no se anuncian.
- Objetivos táctiles ≥ 24×24 px (AA) y, como compromiso, 44×44 px en acciones principales.
- Foco visible, nada atrapa el teclado, el orden de tabulación sigue el orden visual.
- Texto en unidades relativas (`rem`/`em`) para respetar el tamaño de letra de la persona; la página debe poder ampliarse al 200 % sin perder contenido.
- Movimiento respetuoso: toda animación respeta `prefers-reduced-motion`.
- Formularios: cada campo con etiqueta asociada y mensajes de error que dicen qué hacer.

## 5. Qué comprueba el verificador y qué no

`python3 herramientas/web-verificar-sitio.py <carpeta> [--json]` (Python estándar, sin red, sin navegador):

**Sí comprueba:** `lang` y `title`; una `h1` y jerarquía de encabezados; `alt` en imágenes; contraste WCAG de los pares de color de `tokens.css` en tema claro y oscuro (pares por defecto y los declarados con `/* contraste: --a sobre --b >= 4.5 */`); tamaños de fuente en `px`; peso de páginas y activos contra un presupuesto; enlaces y recursos internos rotos; secretos con forma conocida; dominios remotos (scripts, hojas de estilo, fuentes, imágenes, iframes) no declarados en `sitio.permitidos.txt`; trackers conocidos; activos sin línea en `activos/LICENCIAS.md`; relleno (texto de relleno, índigo por defecto, imágenes de marcadores externos, emojis como iconos, métricas del tipo «10× más rápido»); hex crudos fuera de `:root`.

**No comprueba (se hace a mano y se anota):** rendimiento real (LCP, CLS, red lenta); lector de pantalla; navegación con teclado de punta a punta; contraste de texto sobre imágenes o degradados; contraste de pares que no estén en `tokens.css`; calidad y veracidad del texto; que las afirmaciones comerciales correspondan a módulos instalados; textos legales; que la marca no imite otra; compatibilidad de navegadores; validez completa de HTML. El verificador **no es una auditoría de accesibilidad**: un código 0 significa «no se halló lo que sabemos buscar».

Presupuesto por defecto (ajustable con opciones): HTML ≤ 150 KB, CSS ≤ 100 KB, imagen ≤ 300 KB, página con sus recursos locales ≤ 1 MB.

## 6. Sistemas de diseño «inspirados en marcas», activos y licencias

- Herramientas como open-design traen decenas de sistemas «inspirados en» empresas reales. Sirven como **referencia de estructura** (qué campos tiene un buen sistema), **no como diseño a imitar**: usar los colores, tipografías y rasgos distintivos de una marca ajena para la web de otra empresa invita a la confusión y a reclamos de marca registrada. Las tipografías comerciales que esos sistemas nombran no vienen incluidas y requieren licencia propia.
- No se reutiliza el contenido de skills «de catálogo» sin leer la licencia del repositorio de origen (la de la herramienta no la reemplaza).
- Prohibido clonar sitios ajenos o extraer la marca de una URL de terceros.
- Todo activo declara origen, autoría y licencia en `activos/LICENCIAS.md`. Fuentes e imágenes se sirven desde el propio sitio; sin licencia clara no entra.
- Una idea adaptada de un proyecto con licencia Apache-2.0 se registra con atribución en `NOTICE` y en el documento de análisis; no se copian textos ni archivos.

## 7. Privacidad

- Ningún recurso remoto sin declarar: ni fuentes de Google, ni analítica, ni mapas, ni vídeo incrustado que fije cookies. Lo remoto permitido se escribe en `sitio.permitidos.txt` con el motivo.
- Formularios: decir qué datos se piden, para qué y a quién llegan; sin credenciales en el código de la página.
- Antes de usar una herramienta de generación, decir a la persona qué envía y a quién (modelos, telemetría). Sin su confirmación no se usa.

## 8. Contenido

Escribir con contenido real de la empresa; una landing que se parezca a «cualquier landing» (héroe, tres funciones, precios, preguntas, llamada final, sin variación) es señal de que falta conocimiento del negocio. Usar el acento de marca con moderación (acción principal y enlaces), un solo mensaje por sección y una sola acción principal por pantalla.

## Origen

Estructura de «paquete de sistema de diseño» y lista de señales de relleno adaptadas, con redacción propia, de nexu-io/open-design (Apache-2.0); detalle en `docs/ANALISIS-OPEN-DESIGN.md` §8.
