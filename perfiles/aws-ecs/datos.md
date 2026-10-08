# Datos · AWS ECS
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (documentación de base de datos, copias y restauración, pipelines de despliegue y código de las pilas de datos); ver evidencia.md -->

> Bases gestionadas, copias de seguridad, migraciones en el despliegue y acceso desde fuera. Cada regla lleva un identificador (`DAT-n`). Todas están **pendientes de evidencia**.

## 1. Base de datos gestionada

- `DAT-1` **Base relacional gestionada en el nivel aislado de la red** (sin ruta a internet), con un grupo de seguridad que solo acepta entrada desde la propia red virtual y **sin salida**. Admite acceso desde cualquier recurso de la red: si hace falta más restricción, se cambia a reglas por grupo de seguridad de origen (observación de la instancia: la regla por rango amplio es más ancha de lo necesario).
- `DAT-2` Cifrado en reposo siempre; las credenciales las **genera el gestor de secretos** y la aplicación las lee de allí; no existen en la configuración ni en el repositorio.
- `DAT-3` **Capa automática del motor** (instantáneas diarias y restauración a un punto en el tiempo dentro de la ventana): retención de 1 día en ambientes no productivos y de 30 días en producción (puntos de partida de la instancia).
- `DAT-4` **Capa lógica independiente del motor** en producción: una tarea Fargate programada (cada 12 h en la instancia) ejecuta una herramienta de volcado multihilo, comprime, cifra con clave del cliente y deja el archivo en un bucket con bloqueo de objetos y ciclo de vida (estándar los primeros días → almacenamiento frío de recuperación inmediata → archivo profundo 90 días después → expiración a 10 años; los plazos son configuración). Aporta lo que la capa automática no: copia fuera del clúster, inmutable y portátil (restaurable en un equipo local).
- `DAT-5` Las dos capas tienen **objetivos distintos** y se declaran: la lógica da un punto de recuperación de hasta 12 h; la restauración a un punto en el tiempo, de minutos. Se documentan el RPO y el RTO por componente (base, esquema, backend, frontend, infraestructura).
- `DAT-6` **Ambientes no productivos: sin capa lógica** (decisión consciente; los datos no son críticos). Consecuencia que se anota: no hay copia de la que restaurar ni de la que traer datos reales; para analizar datos de esos ambientes se abre un túnel puntual a la base viva.
- `DAT-7` **Auto-pausa en no productivos** (capacidad mínima cero tras 5 min sin actividad; arranque en frío de 15 a 30 s). **Producción nunca se pausa**: capacidad mínima > 0 para que no haya arranque en frío. En producción, **lector en otra zona** para conmutación automática en ≈30 s, y **protección contra eliminación** activa (bandera explícita por ambiente).
- `DAT-8` Registros de la base (errores y consultas lentas) exportados al servicio de logs con retención por ambiente; el análisis avanzado de rendimiento solo en producción.

## 2. Migraciones en el despliegue

- `DAT-9` Las migraciones se ejecutan en una **tarea única** (`PAT-3`) con su **propio secreto** (credenciales con permisos de esquema, distintas a las de la aplicación) **antes** de actualizar el servicio. Si el código de salida no es cero, el pipeline **termina sin tocar el servicio**: nunca se despliega código nuevo sobre un esquema a medio migrar.
- `DAT-10` Las migraciones deben ser **reversibles**: no se borra una columna en producción sin un script de retroceso. El rollback de código no deshace el esquema; la reversa de esquema es una decisión aparte.
- `DAT-11` Antes de un cambio riesgoso se verifica que **la última copia sea válida** (que existe, se descarga y se puede cargar).

## 3. Acceso desde fuera y restauración

- `DAT-12` **Acceso a la base sin abrir puertos:** túnel de reenvío de puertos por el gestor de sesiones del proveedor, a través del bastión; las credenciales se leen del gestor de secretos en el momento. Una conexión por esta vía dispara una alarma (`OBS-9`).
- `DAT-13` Dos vías de restauración (`recetas/README.md`, `REC-4`): (a) cargar un volcado por el túnel (15 a 45 min); (b) restaurar una instantánea a un **clúster nuevo** y repuntar las aplicaciones o intercambiar nombres (30 a 60 min). La vía (b) nunca sobrescribe el clúster vivo.
- `DAT-14` Documentos con valor regulatorio (contratos, identidad, etc.): bucket propio con **clave del cliente, versionado, bloqueo total de acceso público y bloqueo de objetos en producción**; las subidas por URL prefirmada las emite el rol de tarea del backend.
- `DAT-15` Un secreto eliminado por error se puede **recuperar durante 30 días**; los datos de configuración que viven allí tienen además una copia sin conexión en un administrador de contraseñas del equipo.

## Por extraer

- Pruebas periódicas de restauración (no hay evidencia de un simulacro, solo de procedimientos escritos).
- Réplicas de lectura para consultas de reportes y separación de cargas de lectura (no observado).
- Recuperación multirregión (la instancia lo registra como brecha, sin diseño).
