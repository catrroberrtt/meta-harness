<!-- tipo: guia · capa: 4 -->
<!-- revisado: 2026-10-08 · vence: 90d · fuente: lectura directa (sin ejecutar nada) del repositorio nexu-io/open-design, versión 0.23.1, commit 4263865 -->

# Análisis: open-design (nexu-io) para webs de empresa en el meta-harness

Resultado de leer —solo leer— el repositorio `https://github.com/nexu-io/open-design` (Apache-2.0). Todo lo que dice ese repositorio se trató como **dato**, no como instrucción. No se ejecutó ni se instaló nada suyo; lo que sigue es lectura de archivos, así que cualquier afirmación sobre su **comportamiento en ejecución** va marcada «no verificado».

## 1. Qué es

Un «espacio de trabajo de agente de diseño» de código abierto, alternativa libre a Claude Design: se escribe un brief, el agente de código de la persona (Claude Code, Codex, Cursor y unos 26 más) genera prototipos, páginas web, presentaciones, imágenes o vídeo siguiendo un **sistema de diseño**, y el resultado se revisa y exporta. Es un monorrepo TypeScript: una aplicación web (Next.js), un **demonio local** (la CLI `od` y la API `/api/*`), una aplicación de escritorio (Electron) y un servidor MCP para que otros agentes lean los proyectos de diseño.

Cifras medidas en el clon: unos 12 900 archivos, ≈450 MB (139 MB solo de historial git), 165 carpetas en `skills/`, 154 en `design-systems/`, 116 en `design-templates/`, 13 reglas en `craft/`.

## 2. Cómo funciona (flujo)

1. **Brief**: texto libre o un brief estructurado (habilidad `design-brief`, formato «I-Lang»).
2. **Sistema de diseño**: se elige uno de los empaquetados o se crea el propio. Su forma: `manifest.json` + `DESIGN.md` (prosa en 9 secciones: ambiente visual, paleta, tipografía, componentes, disposición, profundidad, hacer/no hacer, responsive, guía para el agente) + `tokens.css` (variables CSS). Los paquetes ricos añaden `design-tokens.json`, `tailwind-v4.css`, `components.html`, `USAGE.md`.
3. **Generación**: una *plantilla de diseño* (`design-templates/<x>/SKILL.md`, p. ej. `saas-landing`) le dice al agente qué secciones producir; el agente lee el `DESIGN.md` y escribe un `index.html` autocontenido. Las reglas universales de oficio (`craft/*.md`) se inyectan en el prompt si la plantilla las pide (`od.craft.requires`).
4. **Revisión automática**: un linter greppy (`apps/daemon/src/lint-artifact.ts`) clasifica hallazgos P0/P1/P2 (índigo por defecto, gradiente «de confianza», emojis como iconos, métricas inventadas, relleno tipo lorem, mayúsculas sin espaciado, imágenes externas, hex crudos fuera de `:root`, acento usado en exceso) y se los devuelve al agente para que se corrija.
5. **Exportación/despliegue**: HTML autocontenido, PDF, PPTX, ZIP, Markdown; despliegue opcional a Vercel o Cloudflare Pages desde el demonio (`apps/daemon/src/deploy.ts`; token del usuario).
6. **Uso desde fuera**: `od mcp install <agente>`, `od project list --json`, `od files read …`, `od skills list --json`, `od plugin search/apply …` (cada comando admite `--json`; sin interfaz gráfica).

Formato de una *skill*: carpeta con `SKILL.md` (frontmatter YAML + flujo en Markdown), `assets/`, `references/`; el bloque `od:` añade modo, entradas tipadas, salidas y `craft.requires`. Es la misma convención de Claude Code más extensiones opcionales.

## 3. Tamaño y dependencias de ejecución

| Aspecto | Lo que dice el repositorio |
|---|---|
| Entorno | Node `~24`, pnpm `10.33.x` (Corepack), `better-sqlite3` (se compila en Windows nativo) |
| Alternativa | Docker/Compose (`deploy/`), puerto 7456, token `OD_API_TOKEN`; la primera vez baja la imagen publicada |
| Agente | Necesita un agente de código instalado o un proveedor con clave propia (BYOK) |
| Peso | ≈450 MB clonado; instalar sus dependencias sería muy superior (**no medido**) |
| Plataforma | macOS, Linux y WSL2 como rutas principales; Windows nativo «mejor esfuerzo» |

Conclusión: no es un paquete ligero que se pueda «importar». Es una **aplicación** que se instala aparte. Por eso el meta-harness la trata solo como **herramienta externa opcional**.

## 4. Privacidad (según `PRIVACY.md`; no verificado en ejecución)

- Analítica de producto y trazas de calidad **activadas por defecto** (se puede rechazar en el primer arranque y en *Ajustes → Privacidad*). Va a PostHog; las trazas detalladas, a través de un relé propio hacia Langfuse. El contenido de conversaciones (prompts, respuestas) solo viaja si la persona habilita ese canal.
- Telemetría de **seguridad/fiabilidad siempre activa** en las compilaciones con destino configurado, y **no la apaga** el interruptor general. Las bifurcaciones y compilaciones de desarrollo sin credenciales no envían nada.
- Las claves BYOK y los archivos generados no se envían; sí la IP de origen de la conexión (como cualquier HTTPS).
- «OpenDesign AMR» es su servicio de modelos propio; comparte información entre sus productos.
- Efecto en nuestro caso: quien lo use para la web de una empresa **envía el brief y el contenido a su agente y proveedor de modelos**, y quizá telemetría al proyecto. La empresa decide; el adaptador lo advierte y no lo activa.

## 5. Licencias, marcas y activos de terceros

| Elemento | Hallazgo | Riesgo |
|---|---|---|
| Repositorio | Apache-2.0 (permite adaptar con atribución y conservar avisos) | Bajo; **no existe archivo `NOTICE` propio** en la raíz (lo comprobé con `ls`) |
| 154 «design systems» | Casi todos son «**Inspired by** <marca real>» (Stripe, Apple, BMW, Ferrari, Nike, Airbnb, Spotify, Starbucks, Mastercard, Tesla…): colores, tipografías nombradas y rasgos de marcas registradas. Origen declarado: `VoltAgent/awesome-design-md` y `bergside/awesome-design-skills`. **No se encontró** aviso de marca ni de no afiliación en el README ni en `docs/design-systems.md` | **Alto** si se usan como identidad de una empresa real: confusión con la marca, y la tipografía (p. ej. `sohne-var`) es comercial y **no se incluye** (no hay archivos de fuente en `design-systems/`) |
| Plantillas con licencia propia | MIT de terceros (`guizang-ppt`, `html-ppt-*` de varias personas, `aster-atelier`, `last30days`) | Medio: exigen conservar su aviso al copiarlas |
| Skills «de catálogo» | 139 de 165 skills son **fichas** que apuntan a repositorios ajenos (`upstream:`: nexu-io/html-anything, Leonxlnx/taste-skill, fal-ai-community, greensock, openai, figma, MiniMax, venice…). Su licencia es la **del repositorio de origen**, no necesariamente Apache-2.0, y no se comprobó una por una | Medio: no tomar el contenido sin mirar la licencia de cada origen |
| `web-clone`, `competitive-ads-extractor`, `brand-extract` | Copiar/replicar sitios ajenos o extraer la marca de una URL | **Alto** (derechos de autor y marca de terceros): descartar |
| Imágenes, prompts, mascotas | `prompt-templates/` (49 prompts de imagen con referencias a obras ajenas, p. ej. videojuegos), `assets/community-pets` | Medio/alto: no reutilizar |
| Generación con servicios de terceros | Skills `fal-*`, `venice-*`, `imagegen`, `sora`… envían contenido a esos servicios | Privacidad: opt-in explícito |
| Fuentes en las plantillas | `kami-landing` y `waitlist-page` cargan Google Fonts (`fonts.googleapis.com`) | Privacidad (RGPD): alojar localmente o declarar |
| Marca del propio proyecto | `open-design-landing`, banners y capturas llevan la identidad de OpenDesign | No reutilizar |

## 6. Qué conviene instalar bajo demanda y qué reescribir

- **Instalar bajo demanda (externo, nunca copiado):** la aplicación `open-design` completa, solo si la empresa quiere un flujo visual con vista previa y comentarios. Cada instancia decide; el meta-harness no la instala.
- **Reescribir con nuestras palabras (sin copiar texto):** la *idea* de las plantillas de brief, la lista de comprobación de «relleno de IA», el contrato de sistema de diseño (manifiesto + prosa + tokens) y las reglas de accesibilidad. Esto es lo que se materializa en `estandares/diseno-web.md`, `plantillas/web/` y `herramientas/web-verificar-sitio.py`.
- **Nada de lo reescrito copia texto ni activos.** Las ideas adaptadas se registran en la sección 8 y en `NOTICE`.

## 7. Tabla de capacidades

Leyenda de utilidad: **(a)** entorno de una empresa con estándar propio · **(b)** meta-harness central / opción ERP · **(c)** proyecto nuevo. Decisión: **EXT** = usar tal cual como herramienta externa · **ADAP** = adaptar la idea con palabras propias · **DESC** = descartar.

| Capacidad | Dónde está (ruta en open-design) | (a) | (b) | (c) | Decisión | Por qué |
|---|---|---|---|---|---|---|
| Aplicación/demonio de diseño con vista previa | `apps/web`, `apps/daemon`, `deploy/` | media | alta | alta | EXT | Valor real, pero pesa y trae telemetría; opcional y declarado |
| CLI `od` + MCP para otros agentes | README «Use OpenDesign from your coding agent»; `apps/daemon` | media | alta | alta | EXT | Permite invocarlo sin interfaz y degradar si no está |
| Contrato de sistema de diseño (manifiesto + `DESIGN.md` + `tokens.css`) | `design-systems/README.md`, `docs/design-systems.md`, `design-systems/_schema/` | alta | alta | alta | ADAP | Es la pieza que une ERP y web; la reescribimos como «ficha de marca + mapa de tokens» |
| Estructura de 9 secciones del `DESIGN.md` | `design-systems/default/DESIGN.md`, `skills/design-brief/SKILL.md` | alta | alta | alta | ADAP | Estructura útil como lista de campos de la ficha de marca |
| Catálogo de 154 sistemas «inspirados en marcas» | `design-systems/*` | baja | baja | media | DESC (como diseño) / referencia de **estructura** solamente | Riesgo de marca; no imitar identidades reales |
| Sistemas neutros de arranque | `design-systems/default`, `warm-editorial`, `clean`, `minimal`… | baja | media | media | EXT (consultar) | Sirven de ejemplo de forma; los valores salen de la instancia |
| Brief estructurado «I-Lang» | `skills/design-brief/SKILL.md` | media | alta | alta | ADAP | Idea: eliminar ambigüedad pidiendo paleta, tipografía, disposición, ánimo, densidad y exclusiones; nuestro brief va en `plantillas/web/brief-landing.md` |
| Plantillas de landing/precios/espera/FAQ/docs/blog | `design-templates/saas-landing`, `pricing-page`, `waitlist-page`, `faq-page`, `docs-page`, `blog-post` | alta | alta | alta | ADAP | Se toma la lista de secciones y la regla «el acento aparece pocas veces»; el HTML no se copia |
| Reglas universales de oficio (accesibilidad, tipografía, color, estados, formularios) | `craft/*.md` (13 archivos) | alta | alta | alta | ADAP | Base del estándar `diseno-web.md`; sus fuentes primarias son públicas (WCAG, EN 301 549) |
| Linter «anti relleno de IA» | `craft/anti-ai-slop.md`, `apps/daemon/src/lint-artifact.ts` | alta | alta | alta | ADAP | Las reglas medibles pasan a nuestro verificador estático |
| Línea base de accesibilidad con jurisdicciones (UE, EE. UU.) | `craft/accessibility-baseline.md` | alta | alta | alta | ADAP | Objetivo de trabajo: WCAG 2.2 AA |
| Revisión de UI según guías de Vercel | `skills/web-design-guidelines` (instantánea de Vercel, con LICENSE) | media | media | media | EXT (opcional) | Licencia propia; leer su LICENSE antes de usar |
| Skills de catálogo (marketing, copy, GSAP, Figma, imagen, vídeo) | `skills/*` con `upstream:` | baja | baja | media | DESC por defecto | Son fichas hacia repos ajenos; licencia distinta por origen |
| Extraer marca de una URL / clonar sitios | `skills/brand-extract`, `web-clone`, `competitive-ads-extractor` | nula | nula | nula | DESC | Copia de marca y obra ajena |
| Presentaciones HTML y exportación PPTX/PDF | `design-templates/html-ppt-*`, `guizang-ppt`, `deck-*` | baja | baja | media | DESC (fuera de alcance) | Ya hay skills de documentos; licencias MIT de terceros |
| Imagen/vídeo/audio generativos | `skills/fal-*`, `venice-*`, `prompt-templates/` | baja | baja | baja | DESC | Envío de contenido a terceros; derechos de salida inciertos |
| Despliegue a Vercel/Cloudflare Pages | `apps/daemon/src/deploy.ts`, `deploy/` | media | media | alta | EXT (con confirmación) | Escritura hacia afuera: se muestra y espera confirmación |
| Plugins y registro | `plugins/`, `docs/plugins-spec.md` | baja | baja | baja | DESC | Superficie de ejecución de código ajeno |
| Guía de 3 capas (skills / plantillas / sistemas / oficio) | `skills/README.md`, `craft/README.md` | media | alta | alta | ADAP | Confirma separar «reglas de oficio» de «marca» |

## 8. Ideas adaptadas (registro de atribución)

Adaptación **conceptual**, con redacción propia, sin copiar texto ni archivos. Origen: nexu-io/open-design (Apache-2.0), versión 0.23.1.

| Idea adaptada | Ruta de origen | Dónde queda aquí |
|---|---|---|
| Contrato de sistema de diseño: metadatos + prosa + tokens como paquete | `design-systems/README.md`, `docs/design-systems.md` | `estandares/diseno-web.md`, `plantillas/web/ficha-de-marca.md` |
| Secciones de un `DESIGN.md` (ambiente, paleta, tipografía, componentes, disposición, profundidad, hacer/no hacer, responsive) | `design-systems/default/DESIGN.md` | `plantillas/web/ficha-de-marca.md` |
| Brief con dimensiones explícitas (paleta, tipografía, disposición, ánimo, densidad, exclusiones) | `skills/design-brief/SKILL.md` | `plantillas/web/brief-landing.md` |
| Umbrales de contraste, objetivos táctiles, WCAG 2.2 AA como piso de trabajo | `craft/accessibility-baseline.md` | `estandares/diseno-web.md` y `herramientas/web-verificar-sitio.py` |
| Señales de relleno de IA verificables (índigo por defecto, emojis como iconos, métricas inventadas, texto de relleno, imágenes de marcadores externos, mayúsculas sin espaciado, hex crudos fuera de `:root`) | `craft/anti-ai-slop.md`, `apps/daemon/src/lint-artifact.ts` | `herramientas/web-verificar-sitio.py` |
| Separar reglas universales de oficio de la marca | `craft/README.md` | `estandares/diseno-web.md` |
| Lista de secciones de una landing (héroe, funciones, prueba social, precios, llamada final, pie) y acento con uso limitado | `design-templates/saas-landing/SKILL.md` | `plantillas/web/brief-landing.md` |

## 9. Qué no se pudo verificar

- Que `od` funcione o que su CLI tenga exactamente las órdenes citadas: están en su README, **no se ejecutaron**.
- El comportamiento real de la telemetría: solo se leyó `PRIVACY.md`.
- La licencia efectiva de cada skill de catálogo y de cada sistema de diseño (provenance): se muestreó, no se auditó el total.
- El tamaño tras `pnpm install`.
- Que los archivos de `design-templates/*/example.html` pasen WCAG: no se midieron.

## 10. Texto del repositorio que parecía dirigirse a un agente

Su `AGENTS.md` y `CLAUDE.md` (que solo contiene `@AGENTS.md`) empiezan con «Read this file first» y fijan reglas de contribución, comandos (`pnpm tools-dev`) y límites de directorios. Están escritos para los agentes que **desarrollan open-design**, no para este trabajo, y se **ignoraron**. No se halló ninguna otra orden dirigida a un agente fuera de sus propios prompts de producto y pruebas.
