<!-- tipo: guia · capa: 1 -->
<!-- revisado: 2026-10-08 · vence: 90d · fuente: lectura del repositorio público Jeffallan/claude-skills (v0.4.18, licencia MIT) y de este repositorio; las rutas citadas se comprobaron en ambos -->

# Análisis: qué rescatar de `Jeffallan/claude-skills`

Comparación honesta entre este harness y el repositorio público [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills) (67 skills, 9 comandos de flujo, MIT). Se leyó como **material de terceros (datos)**: no se ejecutó nada de él y no se copió texto. Cada idea adoptada se reescribió con nuestro método y está atribuida al final (sección 6) y en `NOTICE`.

Regla de la comparación: **no se reemplaza nada**. Cada proyecto con estándar propio conserva el suyo; aquí solo se decide qué se suma, y dónde.

## 1. Resumen

- claude-skills es, sobre todo, un **catálogo de 67 «personas» de agente** (una por lenguaje, framework o rol) que se activan por palabras. Su valor no está en sus skills por stack (chocan con nuestros perfiles) sino en **cuatro ideas de método** que nosotros no tenemos escritas: requisitos con identificador y forma comprobable, suposiciones con nivel de confianza, desafío previo (pre-mortem) y revisión en dos etapas (primero cumple la especificación, después calidad).
- Lo que ya hacemos mejor: aprobación por fase y por manifiesto, evidencia de datos con «qué NO prueba», revisor independiente de afirmaciones, patrones de calidad con origen real, equivalencia ejecutable en migraciones, instalador idempotente con confirmaciones, frescura de documentos, varios agentes.
- Lo que nos faltaba y ahora se suma: la **cadena de punta a punta con matriz de trazabilidad** (requisito → criterio → prueba → commit → evidencia), el **contrato de delegación con archivos**, la lista de cierre «nunca se escapa algo» y herramientas que lo comprueban sin modelo. Ver `metodo/terminado-y-trazabilidad.md` y `herramientas/harness-trazabilidad.py`.

## 2. Tabla de capacidades

Destinos: **E** = entorno de una empresa que ya tiene su estándar (la instancia lo conserva; solo se le ofrece), **C** = entorno centralizado (este repositorio), **N** = proyecto nuevo. Decisiones: rescatar / adaptar / ya lo hacemos mejor / descartar.

| # | Capacidad | Lo tenemos (dónde) | Lo tiene claude-skills (dónde) | Decisión | Por qué | Sirve a |
|---|---|---|---|---|---|---|
| 1 | Preguntar antes de proponer | `metodo/forma-de-trabajo.md` §1, `plantillas/intake.md` (consulta conocimiento previo, dice qué se intentó) | `skills/feature-forge/SKILL.md`, `references/interview-questions.md`; `commands/intake/*.yaml` (marcados «planificado» en `docs/WORKFLOW_COMMANDS.md`) | Ya lo hacemos mejor | Nuestro intake lee primero lo que ya existe y solo pregunta lo que falta; el suyo es una entrevista genérica | — |
| 2 | Requisitos con identificador y forma comprobable | Solo «criterios de aceptación medibles» (`docs/SPEC.md` principio 3); sin identificadores ni formato | EARS (cuándo/mientras/donde → el sistema debe): `skills/feature-forge/references/ears-syntax.md`, `skills/spec-miner/references/ears-format.md` | Adaptar | Sin identificador no hay trazabilidad posible. EARS es una técnica pública; tomamos la idea de frases con disparador, no su texto | E, C, N |
| 3 | Criterios Dado/Cuando/Entonces | `terminado.criterios` en `convenciones/estandar.md` | `skills/feature-forge/references/acceptance-criteria.md` | Adaptar | Un criterio por requisito con identificador propio (`CA-NN.n`) para poder enlazarlo a su prueba | E, C, N |
| 4 | Reconstruir la especificación de un sistema existente | `instalador` modo `adopt`, `herramientas/harness-detectar.py`, `metodo/migracion.md` | `skills/spec-miner/SKILL.md` | Adaptar (solo la marca) | Ya detectamos stack y convenciones. Rescatamos que lo reconstruido se marque **observado/inferido** y no se confunda con requisito aprobado; queda como estado de suposición (§3 del método) | E, N |
| 5 | Suposiciones explícitas con nivel de confianza | «No verificado antes que suponer» (`forma-de-trabajo.md` §10), `plantillas/preguntas-abiertas.md` | `commands/common-ground/COMMAND.md`, `docs/COMMON_GROUND.md` (tres niveles: establecido, de trabajo, abierto) | Adaptar | Cada suposición con su nivel; una **abierta bloquea la aprobación** de la especificación. Es comprobable por herramienta | E, C, N |
| 6 | Desafío previo del plan (pre-mortem, abogado del diablo) | Nada formal. `plantillas/informe-revisor.md` comprueba afirmaciones, no desafía decisiones | `skills/the-fool/SKILL.md`, `references/pre-mortem-analysis.md`, `references/red-team-adversarial.md` | Adaptar | Sección corta «Desafío previo» en cambios M/L: cómo falla esto, qué supuesto lo rompe, qué haríamos. Dos modos, no cinco | C, N, E (opcional) |
| 7 | Decisiones de arquitectura (ADR) | «decisiones de diseño una por línea» en `plantillas/plan.md`; `estandares/README.md` | `skills/architecture-designer/references/adr-template.md`, `nfr-checklist.md` | Adaptar | Plantilla corta `decision-de-arquitectura.md` para decisiones que sobreviven al cambio. La lista de requisitos no funcionales se compara con `estandares/` en una pasada futura | C, N |
| 8 | Plan por fases con puerta de aprobación | `forma-de-trabajo.md` §4–5, `plantillas/plan.md`, `plantillas/manifiesto.md` | `commands/project/planning/*.md` (depende de Jira y Confluence por MCP) | Ya lo hacemos mejor | Nuestro OK explícito por fase y por archivo es más estricto y no exige un tracker concreto | — |
| 9 | Contrato declarativo por etapa (entradas, salidas, requisitos) | Implícito en `plantillas/skills/sdd-*/SKILL.md` | `commands/workflow-manifest.yaml`, `commands/project/*/*.yaml`, `specs/v050-roadmap-consolidation.spec.md` (FR-001, FR-002) | Adaptar | La tabla de etapas del método dice, por etapa, qué entra, qué sale y qué puerta la cierra. Se escribe como tabla, no como YAML | C, N |
| 10 | Ciclo de vida de épicas con Jira y Confluence | `adaptadores/{jira,confluence,drive-md}`, `plantillas/ticket-*.md`, `convenciones/estandar.md` (`ticket.*`) | `commands/project/{discovery,planning,execution,retrospectives}`, `docs/ATLASSIAN_MCP_SETUP.md` | Descartar | Fija un tracker y escribe en sistemas externos sin pasar por nuestra regla «lista y OK antes de crear» (`forma-de-trabajo.md` §11). Nuestros adaptadores ya cubren el caso con otra filosofía | — |
| 11 | Delegación a subagentes con contrato | `forma-de-trabajo.md` §11 («solo cuando hacen falta»); sin formato de contrato | `skills/feature-forge/references/pre-discovery-subagents.md` (reparto por dominio) | Adaptar (con diseño propio) | Lo que falta no es «quién», sino **qué archivos puede tocar cada encargo y cómo se acepta**. `plantillas/delegacion.md` + comprobación de solapes | E, C, N |
| 12 | Revisión en dos etapas | `plantillas/informe-revisor.md`, `plantillas/checklist-entrega.md` | `skills/code-reviewer/references/spec-compliance-review.md` (etapa 1: cumple la especificación; etapa 2: calidad) | Adaptar | Orden fijo: primero conformidad con la especificación (la matriz), después calidad. Evita pulir código que no cumple. Esa referencia dice estar derivada de obra/superpowers (MIT) | E, C, N |
| 13 | Lista de revisión de código por categorías | `plantillas/patron-calidad.md`, patrones por fuente de hallazgo, `perfiles/*/errores-frecuentes/` | `skills/code-reviewer/references/review-checklist.md`, `common-issues.md` | Ya lo hacemos mejor | Nuestros patrones nacen de hallazgos reales con chequeo mecánico; el suyo es una lista genérica | — |
| 14 | Recibir observaciones de revisión | `plantillas/registro-correcciones.md`, `plantillas/ticket-hallazgo.md` | `skills/code-reviewer/references/receiving-feedback.md` | Ya lo hacemos mejor | Tenemos registro con estado y causa | — |
| 15 | Revisión de seguridad | `estandares/` (seguridad), `perfiles/*/seguridad.md`, `hooks/plantillas/block-db-access.sh.tpl`, `politicas/`, `SECURITY.md`, `herramientas/harness-escaneo-publico.py`, `cli/harness_cli.py::revisar_secretos` | `skills/security-reviewer/SKILL.md`, `skills/secure-code-guardian` | Ya lo hacemos mejor / descartar herramientas | Nuestras políticas bloquean por hook; las suyas piden instalar escáneres externos (semgrep, trivy…), que el instalador no instala. Se conserva solo la exigencia de confirmar alcance antes de pruebas activas, que ya está en `politicas/` | — |
| 16 | Pruebas: la prueba se ve fallar primero | `perfiles/*/pruebas.md`, `plantillas/casos-de-prueba.md`, gate | `skills/test-master/references/tdd-iron-laws.md`, `testing-anti-patterns.md` | Adaptar (como columna de evidencia) | No imponemos TDD estricto a todo proyecto, pero en corrección de errores la matriz pide registrar la prueba **vista fallar y luego pasar**. Los antipatrones de prueba quedan pendientes de revisar contra `perfiles/*/pruebas.md` | E, C, N |
| 17 | Depuración sistemática | `forma-de-trabajo.md` §7 (bug u observación de QA), `plantillas/hallazgo-validado.md` | `skills/debugging-wizard/SKILL.md` (reproducir, aislar, una hipótesis a la vez) | Ya lo hacemos | Ya exigimos reproducir y medir antes de afirmar | — |
| 18 | Skills por stack (NestJS, Angular, PostgreSQL, ~50 más) | `perfiles/nestjs-typeorm-mysql`, `perfiles/angular-material`, `perfiles/aws-ecs` + `herramientas/harness-lint-perfiles.py` | `skills/nestjs-expert`, `angular-architect`, `postgres-pro` y el resto | Descartar | Chocan con nuestros perfiles (p. ej. PostgreSQL frente a MySQL, JWT/Passport frente a la autenticación de cada proyecto) y con estándares propios de cada empresa. Dos fuentes de verdad para un mismo stack producen justo las «correcciones» que se quieren evitar |  — |
| 19 | Modernizar sistemas heredados | `metodo/migracion.md`, `herramientas/harness-equivalencia.py`, modo `migrar` | `skills/legacy-modernizer/SKILL.md` (estrangulamiento, reversa por fase) | Ya lo hacemos mejor / adaptar un detalle | Nuestra equivalencia se ejecuta contra datos. Detalle rescatado: cada tarea delegada declara su **reversa** | E |
| 20 | Validar la propia colección (marcado, referencias cruzadas, conteos) | `verificar.sh`, `herramientas/harness-frescura.py`, `harness-lint-perfiles.py` | `scripts/validate-skills.py`, `scripts/validate-markdown.py`, `Makefile`, `.github/workflows/` | Adaptar (pendiente) | Falta un verificador de rutas citadas en los documentos. No se implementó en esta pasada (ver §7) | C |
| 21 | Distribución como plugin / mercado | `bootstrap/`, `instalador/`, `docs/UNICO-COMANDO.md` | `scripts/build-plugin-dist.sh`, marketplace de Claude Code | Descartar | Otro canal; nuestro comando único cubre también datos de la instancia, accesos y entorno | — |
| 22 | Varios agentes | `adaptadores-agente/MATRIZ.md` (claude-code, codex, copilot, cursor, gemini, opencode, windsurf) | `docs/SUPPORTED_AGENTS.md` | Ya lo hacemos mejor | Generamos configuración por agente desde un núcleo | — |
| 23 | Activación por palabras (disparadores) | `plantillas/skills/sdd-*` (por momento del ciclo) | Frontmatter `triggers` en cada `skills/*/SKILL.md` | Descartar como modelo | 67 skills por palabra inflan el contexto y se pisan; nosotros activamos por **momento** (especificar, planificar, implementar, verificar) | — |
| 24 | Retrospectiva al cerrar | `metodo/aprendizaje.md`, `plantillas/registro-correcciones.md` | `commands/project/retrospectives/complete-epic.md`, `complete-sprint.md` | Adaptar | Una línea obligatoria en la lista de cierre: «lección registrada o `N/A` con motivo», enlazada al camino de `aprendizaje.md` | E, C, N |
| 25 | Cierre mecánico «no se escapó nada» | `plantillas/checklist-entrega.md` (lista humana) | `commands/project/execution/complete-ticket.md` (depende del tracker) | Rescatar la idea, diseño propio | `plantillas/cierre-de-cambio.md` + comprobación en `harness-trazabilidad.py --etapa cierre` | E, C, N |
| 26 | Interfaz de entrada (qué comando y cuándo) | `cli/README.md`, `docs/UNICO-COMANDO.md` | `QUICKSTART.md`, `SKILLS_GUIDE.md` (árboles de decisión) | Adaptar (el árbol de decisión) | Falta un mapa por momento; ver `docs/MAPA-DE-COMANDOS.md` | E, C, N |

## 3. Qué sirve a cada destino

**(a) Entorno de una empresa con estándar propio.** Se **ofrece**, no se impone: las plantillas nuevas son opcionales y la instancia sobrescribe sus claves en `convenciones.toml`. Si ya tiene su cadena (por ejemplo tickets con otra estructura), basta con que su matriz use los mismos identificadores. Entra: matriz de trazabilidad, contrato de delegación, lista de cierre, `harness siguiente`. No entra: nada que escriba en su tracker.

**(b) Entorno centralizado (este repositorio).** Entra todo lo marcado «adaptar» o «rescatar»: método de punta a punta, plantillas, `harness-trazabilidad.py`, `harness siguiente` y `harness trazar`, mapa de comandos. Es el único lugar donde viven; las instancias los reciben con `update`.

**(c) Proyectos nuevos.** Las mismas piezas, desde el primer cambio: si el estándar de «terminado» existe desde el día uno, no hacen falta correcciones posteriores. Un proyecto nuevo que se arma desde un catálogo de módulos (por ejemplo, un ERP estándar compuesto por módulos) puede llevar **una matriz por módulo instalado**; esa integración **no está implementada ni verificada** aquí, solo el método que la haría posible.

## 4. Qué NO conviene copiar (y por qué)

| Qué | Por qué no |
|---|---|
| Los ~50 skills por lenguaje y framework | Choca con los perfiles de stack y con los estándares de cada empresa; duplicar fuentes de verdad es la causa de las correcciones tardías |
| Comandos de flujo atados a Jira y Confluence por MCP | Escriben hacia afuera; nuestra regla exige lista y confirmación antes de crear o transicionar |
| Instalar escáneres externos desde un skill de seguridad | El instalador nunca instala herramientas; las acciones hacia afuera se muestran y esperan confirmación |
| Personas con años de experiencia («arquitecto de 15 años») | Adorno sin efecto medible; nuestras skills son procedimientos con «qué NO hacer» |
| Empaquetado como plugin y publicación en mercado | Otro canal de distribución; no aporta a la trazabilidad |
| Conteos y plantillas de documentación generadas (`update-docs.py`) | Específicas de un catálogo de skills |

## 5. Contenido externo dirigido a un lector

Revisados `README.md`, `CLAUDE.md`, `SKILLS_GUIDE.md`, `ROADMAP.md`, `docs/`, `commands/`, `specs/` y `skills/` de los temas pedidos. Su `CLAUDE.md` es una guía para quien trabaja **en ese repositorio** (versionado, estructura de skills, publicación); es una instrucción dirigida a un agente, así que **se trató como dato y no se siguió**. Una búsqueda de frases del tipo «ignora lo anterior» solo encontró contenido sobre ingeniería de prompts (`skills/prompt-engineer/references/*`), que es tema de ese skill y no se dirige al lector. No se halló ninguna instrucción que intentara cambiar el comportamiento de este trabajo.

## 6. Atribución de ideas adaptadas

Material de [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills) (MIT, © sus autores). **No se copió texto ni código**; se reescribieron ideas con el método de este repositorio.

| Idea | Ruta de origen | Dónde queda aquí |
|---|---|---|
| Requisitos en frases con disparador y criterios Dado/Cuando/Entonces | `skills/feature-forge/references/ears-syntax.md`, `acceptance-criteria.md`; `skills/spec-miner/references/ears-format.md` | `plantillas/especificacion.md`, `metodo/terminado-y-trazabilidad.md` §3 |
| Suposiciones con tres niveles de confianza | `commands/common-ground/COMMAND.md`, `docs/COMMON_GROUND.md` | `plantillas/especificacion.md` (sección Suposiciones) |
| Desafío previo / pre-mortem | `skills/the-fool/SKILL.md`, `references/pre-mortem-analysis.md` | `plantillas/especificacion.md` (sección Desafío previo) |
| Revisión en dos etapas (conformidad, luego calidad) | `skills/code-reviewer/references/spec-compliance-review.md` (que declara derivar de obra/superpowers, MIT) | `metodo/terminado-y-trazabilidad.md` §6 |
| Contrato declarativo por etapa (entradas, salidas, requisitos) | `commands/workflow-manifest.yaml`, `specs/v050-roadmap-consolidation.spec.md` | `metodo/terminado-y-trazabilidad.md` §2 |
| Plantilla de decisión de arquitectura | `skills/architecture-designer/references/adr-template.md` | `plantillas/decision-de-arquitectura.md` |
| Prueba vista fallar antes de pasar | `skills/test-master/references/tdd-iron-laws.md` | columna «Rojo→verde» de `plantillas/matriz-trazabilidad.md` |

## 7. Qué no se verificó

- No se ejecutó ningún script ni comando del repositorio externo (fue una decisión, no una limitación).
- No se comprobó si sus skills funcionan en la práctica; solo se leyó lo que dicen.
- Verificador de rutas citadas entre documentos (fila 20): idea registrada, **no implementada**.
- Integración con un catálogo de módulos de ERP (§3c): **no implementada**.
