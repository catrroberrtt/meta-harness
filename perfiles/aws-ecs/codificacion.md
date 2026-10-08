# Codificación · AWS ECS
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (código de los repositorios de infraestructura, su documentación de configuración, etiquetado y depuración de despliegues); ver evidencia.md -->

> Configuración por ambiente, nombres, etiquetas, tipos y cambios que reemplazan recursos. Cada regla lleva un identificador (`COD-n`). Se lee **al empezar a escribir** una pila. Todas están **pendientes de evidencia**.

## 1. Configuración por ambiente

- `COD-1` **Todo valor que cambia entre ambientes** (tamaños, números de tareas, retenciones, dominios, banderas) vive en un archivo de configuración por ambiente, con un tipo/interfaz compartido. Una pila nunca contiene un valor literal que dependa del ambiente.
- `COD-2` **Cargador de configuración «fail-closed».** Un ambiente ausente o desconocido (incluida una variación de mayúsculas) lanza un error; no hay ambiente por defecto.
- `COD-3` **Cuenta y región vienen de variables de entorno y no tienen valor por defecto.** El punto de entrada se detiene si faltan o no coinciden con las credenciales activas. Se eliminan los respaldos silenciosos (`CDK_DEFAULT_ACCOUNT`) en cualquier ambiente, no solo en producción: son la vía por la que se despliega a la cuenta equivocada.
- `COD-4` El ambiente se elige con **una bandera de contexto obligatoria** (`-c env=<ambiente>`); sin ella, el punto de entrada falla con un mensaje de uso.
- `COD-5` Parámetros que mejor se definen como **configuración y no como constante**: tamaño de tarea, número mínimo/máximo de tareas, objetivo de CPU del autoescalado, retención de logs, límites de la base, presupuesto, modo del WAF, banderas `enabled`, protección contra borrado y política de retención de datos.
- `COD-6` Las opciones de postura (WAF, protección contra borrado, retención, bloqueo de objetos) son **explícitas por ambiente**, no deducidas de un nombre de ambiente dentro del código.

## 2. Nombres y etiquetas

- `COD-7` Recursos: `<proyecto>-<ambiente>-<Pila>` para pilas; `<ambiente>/<servicio>/<nombre>` para secretos y parámetros; los nombres de recursos con tope de longitud (por ejemplo, el balanceador admite 32 caracteres) se truncan de forma determinista.
- `COD-8` Etiquetas de gobierno aplicadas **a nivel de aplicación**, no recurso por recurso: proyecto, ambiente, responsable, centro de costo y «gestionado por IaC». Si un recurso ya tiene la misma clave, gana la más cercana al recurso. Activar las etiquetas para asignación de costos es un paso manual por cuenta, que tarda en surtir efecto (≈24 h).
- `COD-9` Recursos creados fuera de la IaC (por ejemplo, un secreto creado a mano) se etiquetan con las mismas claves y con «gestionado: manual».

## 3. Cambios que reemplazan o destruyen

- `COD-10` **Antes de cambiar un nombre físico o el identificador lógico de un recurso**, leer el `diff` y buscar *replacement* o *requires recreation*: la plantilla destruirá el recurso viejo y creará otro. En producción, evaluar el tiempo de indisponibilidad.
- `COD-11` Para **convertir un recurso existente sin recrearlo** (por ejemplo, un oyente de HTTP que pasa de reenviar a redirigir), se conserva el **mismo identificador lógico**; con uno nuevo la creación choca con el original («ya existe»).
- `COD-12` Políticas de eliminación explícitas: **retener** en producción los datos y secretos (buckets de documentos y de copias, repositorios de imágenes, secretos de aplicación, clave de cifrado de copias); **destruir** solo en ambientes no productivos y para recursos derivados (logs de contenedor, buckets de compilados). El valor por defecto «destruir» de la herramienta no se acepta sin leerlo.
- `COD-13` La **protección contra terminación** de las pilas de producción se declara en el código y se afirma con una prueba. (ver `ERR-13`).
- `COD-14` Los despliegues rápidos en caliente (`hotswap`, `watch`) son solo para el ambiente más bajo: se saltan el modelo de la plantilla.

## 4. Constructos y pilas delgadas

- `COD-15` Lo que se repite entre servicios es un **constructo** con propiedades tipadas (servicio con balanceador, sitio estático, función con puerta HTTP); la pila de cada aplicación solo lo instancia con sus valores y crea lo propio (secreto, registro DNS, permisos).
- `COD-16` Los constructos exponen como propiedades públicas lo que otras pilas necesitan (repositorio, clúster, servicio, balanceador, rol de tarea) y como **salidas/parámetros** lo que necesita el pipeline (nombre del servicio, familia de la tarea, repositorio de imágenes, bucket, identificador de distribución).
- `COD-17` Un constructo acepta ARN completos o parciales de secretos; el nombre/identificador completo es preferible porque un ARN parcial exige conceder permisos con comodín.
- `COD-18` Un comentario junto a un valor no obvio dice **el porqué** (periodo de gracia por arranque lento, rango de códigos del marcador de salud, la razón de un identificador lógico fijo); no narra lo que hace la línea.

## 5. Contenedores y arquitectura

- `COD-19` La arquitectura de CPU de la tarea se declara (ARM64 o x86_64); el ejecutor de CI que construye la imagen usa **la misma arquitectura nativa** para evitar emulación lenta.
- `COD-20` La imagen se publica con dos etiquetas: el **hash del commit** (inmutable, sirve para volver atrás) y `latest`.
- `COD-21` La aplicación lee su configuración por **nombre del secreto** (variable de entorno con el nombre) y las variables que el entorno de contenedores no inyecta (región) se definen explícitas en la tarea.
