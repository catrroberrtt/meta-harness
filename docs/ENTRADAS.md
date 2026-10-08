# Entradas de partida: qué se lee y cómo prepararlas

<!-- tipo: guia · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

En las partidas **B** (`init`, desde cero) y **C** (`migrar`) el instalador lee la carpeta con la información de partida antes de generar nada. Este documento explica qué formatos entiende, cómo preparar una hoja de cálculo, qué pasa con los secretos y cómo se valida lo entendido.

Dónde se declara la carpeta (en `acceso.local.toml`): partida B, `[documentacion] carpeta = "<ruta>"`; partida C, `[origen] metodo = "descripcion"|"volcado"` y `ruta = "<ruta>"` (carpeta o archivo). Si el origen es `codigo`, el lector no lo analiza (solo entiende los formatos de abajo): describirlo en una carpeta.

## Formatos que se leen
| Formato | Qué se saca |
|---|---|
| `.md` | Secciones, tablas, listas, entidades descritas, requisitos («debe», «el sistema»), preguntas abiertas (`?`, TODO, TBD), motores mencionados |
| `.sql` | `CREATE TABLE` (MySQL y PostgreSQL): columnas, tipos, claves, índices, claves foráneas, comentarios; pistas del motor |
| `.csv`, `.tsv` | Se clasifican por sus encabezados: diccionario/modelo, catálogo o datos de ejemplo |
| `.xlsx`, `.xlsm` | Igual que csv, hoja por hoja (sin librerías externas; no se ejecuta nada del archivo, macros incluidas) |

## Cómo preparar una hoja de cálculo
Una fila por campo, con estas columnas (los nombres exactos no importan tanto como que existan; en español o inglés):

| tabla / entidad | campo | tipo | longitud | obligatorio | clave | referencia | descripción |
|---|---|---|---|---|---|---|---|
| cliente | id | entero | | sí | PK | | identificador |
| pedido | cliente_id | entero | | sí | FK | cliente.id | quién compra |

Recomendaciones:
- **Una fila por campo**, repitiendo el nombre de la tabla/entidad en cada fila.
- **Sin celdas combinadas** ni cabeceras partidas en dos filas; el encabezado en una sola fila (puede haber título encima).
- Una hoja por tema (modelo, catálogos, ejemplos); catálogos como pares código/descripción.
- La columna `referencia` con `tabla.campo` permite deducir relaciones con evidencia.
- Un `.csv` va en UTF-8.

## Secretos
Si una celda o campo parece un secreto (contraseña, token, clave), **se enmascara**: no aparece en ninguna salida y el informe avisa por archivo y celda dónde estaba. **No pongas contraseñas reales en las entradas**: si ya las pusiste, quítalas del origen y rótalas.

## Lo que no se puede leer
`.pdf`, `.docx`, imágenes (diagramas), `.xls` antiguo, `.ods`, `.numbers`, archivos protegidos o corruptos, o demasiado grandes: se listan en el informe como «no leídos» con la razón y qué pedir. Se exportan a `.md` (texto), `.csv` o `.xlsx` (tablas) o `.sql` (esquema). Si la carpeta no tiene **nada** legible (por ejemplo, solo un pdf), el instalador se detiene con el mensaje del lector y no escribe nada.

## Cómo se valida lo entendido
El lector **propone**, no decide. El instalador deja, dentro de la instancia (nunca en la carpeta de entradas, que no se modifica):
- `.harness/entendimiento.md` y `.harness/entendimiento.json`: entidades, campos y relaciones con su origen (archivo:línea), motor propuesto con evidencia, requisitos y preguntas. Sin fechas ni rutas absolutas: correr dos veces con las mismas entradas da el mismo resultado.
- `.harness/preguntas.md`: las preguntas abiertas con «Se intentó»; se responden ahí y el instalador no lo reescribe.
- `politicas.toml`: el motor propuesto va solo como comentario «propuesto, por confirmar»; los ambientes de datos quedan «por declarar» (nunca se inventan).

Antes de generar nada una persona lee el informe, responde las preguntas y confirma o corrige el motor y las entidades. Sin `--aplicar` el plan muestra qué entendió (entidades, motor, nº de preguntas) y no escribe.

En `migrar` además se crea `.harness/equivalencia/plantilla-casos.md` y se muestran los pasos: replicar primero, anotar mejoras con `harness-mejoras.py nueva`, comparar con `harness-equivalencia.py`.
