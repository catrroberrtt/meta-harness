# Seguridad · AWS ECS
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (documentación de seguridad, inventario de roles y secretos, pipelines de despliegue y código de identidades, red y datos de los repositorios de infraestructura); ver evidencia.md -->

> Permisos mínimos, secretos, red privada, cifrado, cuentas y aprobación de producción. Cada regla lleva un identificador (`SEG-n`). Todas están **pendientes de evidencia**.

## 1. Permisos

- `SEG-1` **Dos roles por servicio.** *Ejecución* (lo que necesita el agente para arrancar: descargar la imagen, escribir logs, leer los secretos que inyecta) y *tarea* (lo que usa el código en ejecución: su bucket, su secreto, su tabla). Cada rol tiene solo lo suyo; un servicio no lee el secreto de otro.
- `SEG-2` Los permisos se acotan a recursos concretos. La única excepción habitual es obtener el token del registro de imágenes, que exige recurso comodín. Los secretos de la aplicación se conceden por identificador, no con comodín sobre todo el gestor.
- `SEG-3` Los roles de CI de despliegue se acotan **por repositorio y por tipo**: un backend puede publicar en su registro y actualizar su servicio y su tarea de migración; un frontend solo sincroniza su bucket e invalida su distribución; una función solo actualiza su código. Pasar un rol a un servicio (`iam:PassRole`) se **condiciona al servicio destino**.

## 2. Secretos

- `SEG-4` Un **secreto por servicio y ambiente** en el gestor de secretos, con convención de nombres (`<ambiente>/<servicio>/<nombre>`); la definición de tarea los inyecta por referencia y nunca por valor. Nunca se versionan en el repositorio (los archivos `.env` y las carpetas de secretos van en el archivo de ignorados).
- `SEG-5` **Cambiar un secreto no actualiza las tareas que ya corren.** Hace falta un nuevo despliegue forzado del servicio (`update-service --force-new-deployment`) y verificar luego el valor. Sin ese paso el cambio «no hace nada» (ver `ERR-1`).
- `SEG-6` **El CI no usa credenciales de larga vida.** Federación OIDC desde el proveedor de CI: roles por ambiente (y por repositorio) cuya confianza exige la audiencia esperada y un sujeto que incluye repositorio y ambiente; el identificador del rol se guarda como variable, no como secreto. Los usuarios IAM con claves, con permisos de administrador y rotación manual, son el patrón **anterior** que se migra.
- `SEG-7` Rotación (puntos de partida de la instancia): claves de acceso y claves de API, cada 90 días; contraseñas de base de datos, cada 180 días, o ante sospecha. Procedimiento invariable: crear nueva → actualizar el secreto → actualizar los consumidores → verificar → **borrar** la anterior después de ≥24 h (no solo desactivarla). Tras rotar una contraseña de base, forzar nuevo despliegue de los servicios que la usan. Si una clave de API vive también en el servicio que la valida, se actualiza en **ambos** lados.

## 3. Aprobación de producción

- `SEG-8` **Producción no se despliega por accidente.** Dos variantes habituales: (a) la rama principal despliega a producción directamente en cada push, sin compuerta en el pipeline; (b) la rama principal despliega solo a pruebas y producción exige un disparo manual sobre un **ambiente protegido con revisores**. (b) es la postura endurecida; (a) depende solo de que nadie fusione sin querer.
- `SEG-9` Una regla de rama que exige solicitud de integración pero **cero aprobaciones y cero comprobaciones obligatorias** no es un control: cualquiera con permiso de escritura puede fusionar. La protección real es revisión obligatoria + comprobaciones en verde + ambiente protegido de despliegue; son tres mecanismos independientes (quién fusiona, qué pasa antes, quién autoriza el despliegue).
- `SEG-10` **Trazabilidad de lo que corre.** La imagen se etiqueta con el hash del commit (`COD-20`) y producción sale de la rama de producción, de modo que se pueda afirmar qué código generó lo desplegado. La instancia lo aplica de forma explícita en un pipeline de aplicación móvil («auditoría regulatoria») y lo comparte con los pipelines de contenedores por el etiquetado.

## 4. Cuentas

- `SEG-11` Un perfil de **solo lectura** para inspeccionar producción; administración solo en ambientes no productivos. Brecha observada: el despliegue manual de la IaC usa un usuario con permisos de administrador por ambiente; el pipeline de la plataforma más nueva lo evita (`SEG-6`).
- `SEG-12` **Un WAF en modo de solo conteo no es autenticación.** Si la aplicación tiene un hueco de autenticación, el filtro no lo compensa; se corrige en la aplicación.
- `SEG-13` **Verificación de cuenta destino.** El despliegue de IaC falla si falta la bandera de ambiente o si la cuenta y la región no están definidas; se eliminan los valores por defecto que pudieran apuntar a otra cuenta (`COD-3`).

## 5. Red

- `SEG-14` Tareas en nivel privado sin IP pública; el grupo de seguridad de las tareas acepta entrada **solo del grupo de seguridad del balanceador**; el balanceador acepta HTTPS (y HTTP solo para redirigir). Base aislada (`DAT-1`). Bastión **sin ninguna entrada** (acceso por el gestor de sesiones, nunca por SSH) y con `requireImdsv2`.
- `SEG-15` La salida se limita lo que se pueda: la observada es HTTPS abierto hacia internet (APIs externas, registro de imágenes, gestor de secretos) y el puerto del motor hacia la red virtual. Reducirla con puntos de enlace de VPC es una mejora registrada, pendiente de comparar el costo.
- `SEG-16` Los registros de red (flow logs) de toda la red van a almacenamiento central con retención larga en producción; el de la subred del bastión alimenta una alarma (`OBS-9`).

## 6. Cifrado y datos

- `SEG-17` Cifrado en reposo en todo; claves **gestionadas por el cliente** solo donde hace falta auditoría de uso o rotación (copias de la base, documentos regulatorios), con rotación anual y retención de la clave en producción. El resto usa claves del proveedor. Con claves del cliente, activar la «clave de bucket» reduce las llamadas de cifrado en ~99 %.
- `SEG-18` En tránsito: HTTPS en el borde y redirección permanente de HTTP; los buckets **rechazan el transporte no seguro** por política. Brecha anotada: balanceador → contenedor y contenedor → base viajan sin TLS por quedar dentro de la red; para exigencias formales (PCI, SOC2, ISO) se exige TLS hacia la base y cifrado de los logs.
- `SEG-19` Auditoría: registro de las llamadas a la API de la cuenta, **multirregión y con validación de archivos**; sesiones del bastión registradas; flow logs. Para exigencias formales se suma el escaneo de vulnerabilidades de las imágenes (el escaneo al subir está activado) y servicios de detección de amenazas.

## Por extraer

- Política de acceso al registro entre cuentas, y revisión de permisos por rol (solo hay un inventario escrito).
- Gestión de vulnerabilidades de dependencias dentro de la imagen.
- Controles de la cuenta pagadora de la organización (políticas de control de servicio).
