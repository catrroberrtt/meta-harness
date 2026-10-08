# Esquema de la política por proyecto

<!-- tipo: estándar · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: esquema de politicas.toml y su generador -->

Cada proyecto que usa el harness tiene **un archivo de políticas** (TOML) que dice qué se puede y qué no: sobre los datos, el git, los comandos, el despliegue, los costos, los secretos y la verificación. El harness trae un conjunto **por defecto, conservador y sin datos de ningún proyecto** (`politicas.defecto.toml`); el proyecto lo copia, declara lo suyo y lo ajusta. Los hooks y los gates **se generan desde ese archivo** (`instalador/generar-politicas.py`): ningún ambiente, puerto, base, cuenta ni rama está escrito a mano en una plantilla.

**Principio rector: no se asume.** Lo que el instalador no puede detectar, se pregunta. Lo que sigue sin declarar, el generador lo trata como falta y se niega a producir el hook (ver «Qué pasa si falta algo»).

Valores de permiso (en todo el archivo): `"permitida"` · `"confirmar"` (pide confirmación explícita y puntual) · `"prohibida"` (el agente nunca; lo corre el usuario).

## 1. `[proyecto]` y `[alcance]`

| Clave | Tipo | Qué dice |
|---|---|---|
| `proyecto.nombre` | texto | libre, solo informativo |
| `proyecto.etiqueta_reglas` | texto | prefijo de los mensajes de los hooks generados |
| `alcance.repos` | lista de patrones | repos que vigila el hook de datos (nombre del repo, estilo `fnmatch`: `api-*`) |
| `alcance.remote_regex` | regex | remoto que identifica al grupo; vacío = no se exige un remoto |
| `alcance.sin_remote_ok` | lista de patrones | repos locales que pueden no tener remoto |
| `alcance.cualquier_remote` | lista de patrones | repos vigilados con cualquier remoto |
| `alcance.remote_ejemplo` | URL | una URL que debe satisfacer `remote_regex` (solo para la autoprueba) |

## 2. `[datos]`: ambientes y qué se permite en cada uno

Claves generales:

| Clave | Tipo | Qué dice |
|---|---|---|
| `datos.hosts_locales` | lista | hosts que cuentan como «base local»; **todo otro host es remoto** (obligatoria) |
| `datos.clientes_sql` | lista | clientes SQL que se vigilan (`mysql`, `psql`…) (obligatoria) |
| `datos.lectura_host_no_resuelto` | permiso | host que viene de una variable o no se indica: `confirmar` |
| `datos.lectura_host_remoto` | permiso | `prohibida` |
| `datos.escritura_fuera_de_ambiente_de_escritura` | permiso | `prohibida` |
| `datos.motores_solo_lectura.scripts` | lista de rutas | scripts de solo lectura que pueden autorizarse sin preguntar |
| `datos.motores_solo_lectura.archivo_sha256` | ruta | archivo donde **el usuario** fija el hash de cada motor; editar un motor vuelve a preguntar |

### `[[datos.ambientes]]` (uno por ambiente, **sin defecto**)

| Clave | Tipo | Qué dice |
|---|---|---|
| `nombre` | texto | nombre libre y único |
| `tipo` | `local` · `pruebas` · `produccion` | un ambiente `produccion` nunca puede tener `escritura = "permitida"` (el generador lo rechaza) |
| `reconocimiento.hosts` | lista | cómo se reconoce por host |
| `reconocimiento.puertos` | lista de enteros | …por puerto |
| `reconocimiento.bases` | lista | …por nombre de base |
| `reconocimiento.bases_prefijos` | lista | …por prefijo de nombre de base (esquemas desechables) |
| `variables.archivo_env`, `.host`, `.puerto`, `.base`, `.contrasena` | texto | **solo para el ambiente donde el agente escribe**: archivo de entorno del repo y nombres de las variables que lo identifican. El hook solo habilita la escritura si el archivo de entorno apunta a ese ambiente |
| `permisos.lectura` / `.escritura` / `.ddl` / `.migraciones` | permiso | los cuatro son obligatorios; no se asume ninguno |

Reglas que el generador hace cumplir: a lo sumo **un** ambiente con `escritura = "permitida"`; ese ambiente declara `hosts`, una `bases`, `variables` y `ddl = "permitida"` (el `DROP/CREATE DATABASE` siguen prohibidos siempre); las bases y prefijos de **los demás** ambientes no pueden nombrarse en un comando de escritura del agente.

Granularidad del hook generado: la **lectura** se decide por host (`hosts_locales`); la **escritura** exige host + puerto + base del ambiente de escritura. Si un proyecto quiere que leer otro ambiente local (por puerto) pida confirmación, es una decisión nueva que se declara y se pregunta.

### `[[datos.comandos]]` (comandos que tocan la base)

| Clave | Qué dice |
|---|---|
| `nombre`, `regex`, `motivo` | comando prohibido (regex sobre el comando ya filtrado) y el mensaje |
| `accion` | solo `"prohibida"` |
| `permitida_en_ambiente_de_escritura` | `true` = se permite si el archivo de entorno apunta al ambiente de escritura del agente |

### `[[datos.scripts]]` (scripts que mencionan un cliente SQL y exigen confirmación)

`nombres` (lista), `ruta_regex`, `accion = "confirmar"`, `motivo`. Cualquier otro script que mencione un cliente SQL ya cae en confirmación.

## 3. `[git]`

| Clave | Tipo | Qué dice |
|---|---|---|
| `ramas_protegidas` | lista | **sin defecto**: se detectan del remoto o se preguntan |
| `aprueba` | texto | quién aprueba un merge/despliegue a una rama protegida: se pregunta |
| `confirmar` | lista | acciones que piden confirmación explícita (`commit`, `push`) |
| `remote_regex`, `repos_exentos` | regex, lista | a qué repos aplica y cuáles quedan fuera |
| `push_a_rama_protegida`, `merge_a_rama_de_produccion` | permiso | `prohibida` por defecto |

## 4. `[comandos]`

Tablas `[comandos.instalar]`, `[comandos.build]`, `[comandos.test]`, `[comandos.servidor_de_desarrollo]`, `[comandos.formateo_global]`, cada una con `accion` (permiso). `instalar` además lleva `regex`, `repos`, `repos_exentos` (a qué repos se aplica y cuáles quedan fuera). Instalar dependencias o herramientas globales es `prohibida` por defecto.

## 5. `[despliegue]`

`accion` (permiso, `confirmar` por defecto), `repos`, `regex` (lista de comandos de despliegue a vigilar), `produccion` (`prohibida`: el agente nunca despliega a producción).

## 6. `[costos]`

| Clave | Qué dice |
|---|---|
| `anunciar_antes` | `true`: llamadas, ambiente/cuenta, costo por llamada y tope, **antes** de ejecutar |
| `operaciones_que_cobran` | servicios de pago del proyecto (sin defecto: se preguntan) |
| `cuentas_de_produccion` | identificadores de cuenta/proyecto de producción (sin defecto) |
| `produccion_escritura_invocacion_envio` | `prohibida` |
| `lecturas_de_nube` | `permitida` (listar, describir, descargar) |
| `bucles_o_paralelismo_sobre_pago` | `prohibida` |
| `tope_de_llamadas_por_pasada` | `0` = sin tope declarado, el agente pregunta |

## 7. `[secretos]`

`rutas_prohibidas_en_commit` (patrones de archivo), `patrones_prohibidos` (regex de contenido), `imprimir_secretos`, `pii_en_documentacion` (`prohibida`), `excepciones` (rutas versionadas a propósito aunque parezcan secretas).

## 8. `[verificacion]`

`evidencia_de_datos` (no hay veredicto sobre cifras sin una consulta real mostrada), `visual` (pantallas abiertas y capturadas antes de reportar listo), `estructura_de_modulos` (medir con el motor de auditoría antes de cerrar), `reporte_sin_prueba` (`prohibida`). Valores: `obligatoria` / `recomendada` / `no_aplica`.

## 9. `[[mcp.servidores]]` (opcional: servidores MCP declarados)

**Sin defecto y sin servidores no se genera nada**: el harness nunca asume que existe un servidor MCP. Cada servidor declarado se valida (`adaptadores-agente/nucleo/capacidades_comunes.py --validar <instancia>`) y se entrega en forma neutral para que cada adaptador lo traduzca a su formato.

| Clave | Tipo | Qué dice |
|---|---|---|
| `nombre` | texto | `^[a-z0-9]+(-[a-z0-9]+)*$`, único |
| `comando` / `url` | texto | **exactamente uno**: `comando` (servidor local; solo el ejecutable, sin espacios) o `url` (servidor remoto `http(s)://`, sin credenciales dentro) |
| `args` | lista de textos | argumentos del comando; sin secretos |
| `entorno` | tabla `CLAVE = "${VARIABLE}"` | **solo referencias a variables, jamás valores**: un valor con aspecto de secreto, o cualquier texto que no sea `${VARIABLE}`, se rechaza |
| `registrar` | `"prohibida"` · `"confirmar"` · `"permitida"` | si el agente puede registrar el servidor por su cuenta; por defecto `"confirmar"` |

```toml
# [[mcp.servidores]]
# nombre = "docs-internas"
# comando = "npx"
# args = ["-y", "paquete-del-servidor"]
# entorno = { TOKEN_DOCS = "${TOKEN_DOCS}" }   # la variable la define la persona en su entorno
# registrar = "confirmar"
```

## 10. Permisos neutrales derivados de la política

No es una sección nueva: `capacidades_comunes.permisos_desde_politica` lee las secciones anteriores y produce `{deny, ask, allow, origenes, no_traducible}` con **prefijos literales de comando** únicamente. Un `regex` de la política se traduce solo si es un prefijo literal (por ejemplo `^git push` o `cdk deploy|sam deploy`); si usa metacaracteres, grupos, secuencias como `\b` o termina en `$`, **no se aproxima**: queda en `no_traducible` con el motivo. Lo que depende del host, de la rama o de rutas de archivo (leer una base, `push` a una rama protegida, archivos que no se confirman) tampoco se traduce; lo cubren los hooks. Si un prefijo está en `deny` y en `ask`, gana `deny`. `allow` solo se llena con lo que la política permite de forma explícita con un comando literal; nunca se inventa.

## Qué pasa si falta algo

El generador **no completa con valores por defecto** lo que identifica a un proyecto. Falla (código 2, nada se escribe) con un mensaje que dice qué declarar cuando:

- el archivo está vacío o no declara ningún `[[datos.ambientes]]`;
- falta `datos.hosts_locales` o `datos.clientes_sql`;
- un ambiente no dice cómo se reconoce o no declara sus cuatro permisos;
- hay un ambiente de producción con escritura permitida, o más de un ambiente de escritura;
- el ambiente de escritura no declara sus variables de entorno.

## Mapa de las reglas duras de la instancia de origen

Las reglas duras de la instancia de origen (RD-1 a RD-10) son el conjunto de políticas que sirvió de punto de partida; en un proyecto nuevo son **el valor por defecto de estas claves**, no sus valores. Esta tabla dice dónde vive cada una.

| Regla | Qué cubre | Sección y claves de la política |
|---|---|---|
| RD-1 | acceso a la base: lectura solo local, escritura/DDL/migraciones prohibidas salvo la base de pruebas del agente, conexiones remotas prohibidas, scripts que hablan con la base | `datos.hosts_locales`, `datos.ambientes[*].reconocimiento` y `.permisos`, `datos.ambientes[*].variables`, `datos.comandos`, `datos.scripts`, `datos.motores_solo_lectura`, `datos.lectura_host_*` |
| RD-2 | git y despliegue: `main` nunca, ramas de integración solo con aprobación puntual, commits/PR solo si se piden, nada real contra qas/prod sin aprobación | `git.ramas_protegidas`, `git.aprueba`, `git.confirmar`, `git.push_a_rama_protegida`, `git.merge_a_rama_de_produccion`, `despliegue.accion`, `despliegue.regex`, `despliegue.produccion` |
| RD-3 | build, tests y servidores: el agente valida; servidor de desarrollo, formateo global y DDL no | `comandos.build`, `comandos.test`, `comandos.servidor_de_desarrollo`, `comandos.formateo_global`, `datos.ambientes[*].permisos.ddl` |
| RD-4 | dependencias y herramientas globales: nada de instalar sin aprobación | `comandos.instalar` |
| RD-5 | nada de la sesión sale al repo (apodos, rutas internas del harness en archivos que viajan al equipo) | `verificacion.reporte_sin_prueba` (parcial) y la lista de patrones de `secretos.patrones_prohibidos`; es una regla de redacción: se hace cumplir con un chequeo propio, no con una clave de permiso. **Sin clave dedicada hoy** |
| RD-6 | secretos y PII: archivos que no se commitean, nada de secretos en documentación | `secretos.rutas_prohibidas_en_commit`, `secretos.patrones_prohibidos`, `secretos.imprimir_secretos`, `secretos.pii_en_documentacion`, `secretos.excepciones` |
| RD-7 | ningún veredicto de negocio sin evidencia de datos | `verificacion.evidencia_de_datos`, `verificacion.reporte_sin_prueba` |
| RD-8 | frontend: ninguna pantalla se entrega sin verificarla en el navegador con capturas | `verificacion.visual` |
| RD-9 | backend: la estructura de un módulo se mide antes de cerrarlo | `verificacion.estructura_de_modulos` |
| RD-10 | consumo y costo: anunciar antes, lo masivo ni se intenta, producción y servicios de pago prohibidos al agente | `costos.anunciar_antes`, `costos.operaciones_que_cobran`, `costos.cuentas_de_produccion`, `costos.produccion_escritura_invocacion_envio`, `costos.lecturas_de_nube`, `costos.bucles_o_paralelismo_sobre_pago`, `costos.tope_de_llamadas_por_pasada` |

Qué genera hoy el instalador desde la política: el hook de acceso a la base (`hooks/plantillas/block-db-access.sh.tpl`). Las demás secciones están definidas y validan, y sus plantillas de hook (git, instalación, despliegue, costos) se añaden con el mismo mecanismo.
