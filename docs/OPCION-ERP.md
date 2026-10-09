# Opción ERP: proponer los módulos del ERP estándar que un negocio necesita

<!-- tipo: guia · capa: 4 -->
<!-- revisado: 2026-10-09 · vence: 90d · fuente: herramientas/harness-erp.py, cli/harness_cli.py (cmd_erp) y sus pruebas (herramientas/tests/test_erp.py, cli/tests/test_erp.py); cada comando se ejecutó -->

Cuarto estado del comando único (**D**): el negocio no tiene sistema o quiere uno estándar, y existe un ERP estándar en **otro repositorio** que se compone **solo con los módulos que el negocio necesita**. `harness erp` es el primer tramo de ese camino: **lee los documentos del negocio y propone** producto de partida y módulos, con el estado real de cada uno. No instala ni copia nada del ERP.

```sh
harness erp --negocio <carpeta> --erp-base <ruta> [--instancia <carpeta>] [--aplicar]
```

## Qué hace, paso a paso

1. **Entrada.** `--negocio` es una carpeta **local** de documentos (`.md`, `.txt`, `.rst`, `.csv`, `.tsv`, `.xlsx`; por ejemplo, exportados de Drive u otra fuente). Si falta, **la pregunta**: nunca asume de dónde leer. `--erp-base` es la carpeta del repositorio del ERP estándar: solo se lee su `modulos/catalogo.json`, y la ruta **siempre** se pasa por parámetro (no está escrita en ningún archivo). Sin conectores y sin red.
2. **Lectura** (solo lectura). Reutiliza el lector de entradas (`herramientas/harness-leer-entradas.py`, ver `ENTRADAS.md`): decodificación, hojas de cálculo, tope de 2 MB por archivo y detección de secretos (los valores con forma de secreto se enmascaran). Además: tope de 2000 archivos y 40 MB en total, no sigue enlaces simbólicos y lista como «no leído» (con la razón) lo binario, `.pdf`, `.docx`, imágenes, `.xls`, archivos rotos o enormes. Una carpeta vacía no rompe: la propuesta es solo el núcleo y lo dice.
3. **Descubrimiento.** Reglas de palabras ponderadas, sin modelo de lenguaje (sección siguiente). Cada señal guarda su evidencia: archivo, línea, término y un fragmento corto.
4. **Propuesta.** Con el catálogo: rubro, **producto de partida**, módulos (**núcleo siempre** y **cierre de requisitos**) y, por módulo, su **estado real** (hecho, parcial, en construcción, diseño, planeado). Lo que **aún no existe** va en su propia sección y se avisa; no se promete.
5. **Confirmación.** Nada se escribe sin tu «s» (o `--aplicar`). Sin terminal y sin `--aplicar` muestra el plan y sale con 0 sin escribir. Sin `--instancia` solo muestra la propuesta.
6. **Escritura** (solo dentro de la instancia): `erp/propuesta-erp.md` (legible), `erp/propuesta-erp.json` (máquina) y, enlazado a la trazabilidad del método, `cambios/erp-composicion/especificacion.md` y `matriz.md`. La propuesta se actualiza cada vez; la especificación y la matriz, una vez editadas por ti, **no se pisan**.
7. **Opcionales ligados** (se ofrecen, no se ejecutan): si hablan de sitio web o landing, el adaptador `diseno-web`; si hablan de integraciones o correos, se señalan (y se avisa que `integraciones` no existe y `notificaciones` es parcial).

Códigos de salida: 0 bien (incluye «solo mostré») · 2 detenido (falta carpeta o catálogo, instancia mal ubicada, señales mal formadas) · 130 interrumpido. La instancia no puede estar dentro de la carpeta de documentos (se leen sin modificarlos) ni dentro del ERP (solo lectura).

## Cómo se descubren las señales

Datos editables, sin código: `perfiles/_erp/senales.toml` (o el archivo que pases con `--senales`).

- Cada **señal** (`[senal.<id>]`) lista los módulos del catálogo que justifica y sus términos con peso: `["orden de compra", 3]`. Cada **rubro** (`[rubro.<id>]`) apunta a un producto del catálogo y a un perfil de configuración.
- Los términos van en minúsculas y **sin tildes** (el texto también se normaliza), se buscan como palabra completa y aceptan plural simple («proveedor» encuentra «proveedores»; «restock» no encuentra «stock»).
- **Puntos**: cada término suma `peso` por archivo, con tope de 3 coincidencias del mismo término en el mismo archivo (repetir una palabra no infla la señal); los archivos suman entre sí. Si llega al umbral (por defecto 3 para una señal, 5 para un rubro), los módulos entran. Por debajo del umbral aparece como **señal débil**, no incluida.
- Del **producto de partida** solo entra lo que tiene señal: el resto se lista como «sin señal en tus documentos» para que confirmes.
- Un módulo del archivo de señales que el catálogo leído no tiene se ignora con **un** aviso (útil con un catálogo más viejo). `suministros` no tiene señal a propósito (demasiado ambiguo).
- Misma carpeta, mismas señales y mismo catálogo dan **exactamente** la misma propuesta (sin fechas ni rutas absolutas; el JSON guarda la huella `sha256` del catálogo leído).

## Qué NO hace aún

- **No compone ni copia nada del ERP**: el compositor (`componer-erp`) está en diseño en el ERP (su `docs/COMPOSICION.md`) y no tiene código. *No verificado* contra un compositor real: solo contra el catálogo.
- No construye módulos que están planeados; no decide por ti (las señales son palabras de tus documentos: confirma, quita o agrega).
- No lee `.pdf`, `.docx` ni imágenes (se exportan a `.md`/`.csv`/`.xlsx`); no lee Drive ni ningún conector.
- No genera el contenido del perfil de configuración (solo sugiere su nombre; el módulo `perfiles-configuracion` del ERP está planeado).
- No sabe de multiempresa ni de datos reales del negocio (cifras, clientes): solo de qué procesos habla.

## Contrato con el compositor

`erp/propuesta-erp.json` trae, además de todo lo explicado para la persona, el objeto **`entrega_al_compositor`** (esquema `meta-harness/entrega-compositor@1`): es lo que se le entregará.

| Campo | Contenido |
|---|---|
| `producto` | id del producto de partida del catálogo, o `a-medida` si ningún rubro llegó al umbral |
| `modulos` | lista **ya cerrada** (núcleo + señales + requisitos), en el orden del catálogo |
| `perfil` | nombre del perfil de configuración sugerido por el rubro (o `null`); solo el nombre |
| `componibles_hoy` | módulos con estado `hecho` o `parcial` |
| `sin_codigo_aun` | módulos `en_construccion`, `diseno` o `planeado`: **no tienen código** |
| `marca` | `{fuente: "sitio/DISENO.md", en_instancia: true/false, datos_de_marca_en_este_archivo: false}`: **puntero**, nunca los datos |
| `catalogo` | `{archivo, version, sha256}` del catálogo con el que se calculó |
| `invocacion_prevista` | forma prevista del compositor según el diseño del ERP (`scripts/componer-erp.mjs --producto … --destino … --perfil …`); no existe aún |

Obligaciones que asume el compositor (por escribir en el ERP, no en este repositorio):

1. Validar `esquema` y rechazar una versión que no conozca.
2. **Volver a resolver** el cierre de requisitos con su propio catálogo: la lista de la propuesta es la entrada deseada, no la autoridad. Si difiere, falla con el mensaje de la diferencia (si el `sha256` no coincide, avisa que la propuesta es de otro catálogo).
3. Detenerse con un mensaje claro si algún módulo de `sin_codigo_aun` está en la lista; solo con confirmación explícita sigue **sin** ellos. Nunca genera carcasas vacías.
4. Leer los datos de marca de la **instancia** (`sitio/DISENO.md` y los tokens), nunca de este repositorio ni del ERP.
5. Escribir `erp.lock.json` en el proyecto generado; ese archivo es la prueba del criterio `CA-NN.1` de cada módulo en la matriz.

Sin datos de empresa en estos repositorios: la propuesta, la marca y los documentos viven en la instancia; en el harness y en el ERP solo hay ejemplos inventados.

## Trazabilidad

Cada módulo propuesto es un **requisito** (`RQ-NN`) de `cambios/erp-composicion/especificacion.md`, con su criterio (`CA-NN.1`: «`erp.lock.json` incluye el módulo con el estado del catálogo»), y una fila de `matriz.md` con la señal que lo justifica (archivo y línea) y su estado en el catálogo. También sale en `propuesta-erp.md`, sección «Trazabilidad».

- Los módulos planeados o en construcción generan una suposición **abierta**: `harness trazar … --etapa especificacion` pasa (con avisos), pero `--etapa delegacion` **falla** hasta que decidas si se espera su construcción o se compone sin ellos, y marques el OK. Es el comportamiento buscado: no se delega lo que no existe.
- Los módulos parciales y las señales cercanas al umbral generan suposiciones `de-trabajo` para confirmar.

## Ejemplo completo (datos inventados)

Documentos del negocio (`docs-negocio/descripcion.md`):

```markdown
# Ferretería Ejemplo
Somos una ferretería con tres tiendas y venta mayorista. Llevamos el inventario en Excel y el kardex a mano.
Los proveedores nos envían facturas y emitimos factura electrónica a SUNAT. Hacemos órdenes de compra cada semana.
Queremos una página web con catálogo de productos y un sitio web corporativo.
Los vendedores arman cotizaciones a clientes y pedidos de venta. La cobranza se hace por transferencias.
Necesitamos integración con el banco y enviar correos automáticos a los clientes.
```

```sh
harness erp --negocio ./docs-negocio --erp-base ./erp-base --instancia ./mi-instancia
```

Salida (estado del catálogo del ERP al 2026-10-09; cambia con el catálogo):

```text
Documentos leídos: 1 (6 líneas); no leídos: 0
Rubro: Comercio (tiendas, mayoristas, minoristas) (13 puntos)
Producto de partida: Comercio (comercio)
Módulos propuestos: 11 (núcleo 4 · por señal 6 · por requisito 1)
Estado real hoy: 4 hechos · 4 parciales · 1 en construcción · 0 en diseño · 2 planeados

Módulos:
    identidad                  Hecho
    ...
  ~ notificaciones             Parcial           <- descripcion.md:7 «correos automaticos»
  ~ contabilidad               Parcial           <- lo requiere compras, ventas
  ~ comprobantes               Parcial           <- descripcion.md:4 «factura electronica»
  ! compras                    En construcción   <- descripcion.md:4 «orden de compra»
  X ventas                     Planeado          <- descripcion.md:6 «cotizacion a cliente»
  ~ almacen                    Parcial           <- descripcion.md:3 «kardex»
  X integraciones              Planeado          <- descripcion.md:7 «integracion con»
  (sin marca = existe · ~ parcial · ! en construcción · X NO existe aún)

NO existe aún en el ERP central (3): compras, ventas, integraciones. No se promete.
Opcional ligado (se ofrece, no se ejecuta): adaptador diseno-web (los documentos mencionan sitio web o landing).
Del producto de partida sin señal en los documentos (no incluidos): acceso, impuestos-peru, ...

¿Escribo la propuesta en la instancia? [s/N]
```

Con «s» deja `erp/propuesta-erp.md`, `erp/propuesta-erp.json`, `cambios/erp-composicion/especificacion.md` y `matriz.md`. La entrega al compositor de este ejemplo:

```json
{
  "esquema": "meta-harness/entrega-compositor@1",
  "producto": "comercio",
  "modulos": ["identidad", "autenticacion", "configuracion", "interfaz", "notificaciones", "contabilidad",
              "comprobantes", "compras", "ventas", "almacen", "integraciones"],
  "perfil": "comercio",
  "componibles_hoy": ["identidad", "autenticacion", "configuracion", "interfaz", "notificaciones", "contabilidad", "comprobantes", "almacen"],
  "sin_codigo_aun": ["compras", "ventas", "integraciones"],
  "marca": {"fuente": "sitio/DISENO.md", "en_instancia": false, "datos_de_marca_en_este_archivo": false},
  "catalogo": {"archivo": "modulos/catalogo.json", "version": 3, "sha256": "<huella del catálogo leído>"}
}
```

Una fila de la matriz del mismo ejemplo: `| RQ-08 | CA-08.1 | erp.lock.json lo lista (lo comprueba el compositor, aún no existe) | n/a | - | - | pendiente | señal compras (descripcion.md:4); catálogo: en_construccion |`.

## Pruebas

`python3 -m unittest herramientas/tests/test_erp.py cli/tests/test_erp.py` (catálogo y negocios inventados de comercio, distribución, servicios, industrial e inmobiliario; carpeta vacía, binarios, archivo enorme, tope de archivos, enlaces, secretos, determinismo, no escribir sin confirmación, trazabilidad). Con `HARNESS_ERP_BASE_PRUEBA=<ruta del ERP estándar>` se comprueba además que el archivo de señales no tiene ids huérfanos contra el catálogo real.

## Decisiones registradas (2026-10-09)

1. Sistemas de diseño «inspirados en marcas reales»: prohibidos en el flujo de `diseno-web`, ni como referencia. Solo propios o genéricos sin marca (`adaptadores/diseno-web/README.md`, `estandares/diseno-web.md` §6, `ANALISIS-OPEN-DESIGN.md` §11; el verificador marca `marca-ajena`).
2. Telemetría de herramientas externas de diseño: solo dentro de un contenedor sin telemetría y con confirmación explícita; si no, modo manual (adaptador, «Invocación»; estándar §7).
3. Fuentes tipográficas remotas: se alojan en local (adaptador, «Activos»; estándar §7).
4. `harness ayuda` / `harness -h`: primero el mapa «qué comando uso cuándo», después las opciones técnicas (`cli/README.md`, `MAPA-DE-COMANDOS.md`).
