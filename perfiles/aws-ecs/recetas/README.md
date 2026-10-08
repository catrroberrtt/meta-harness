# Recetas · AWS ECS
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (tutoriales y runbooks de operación, procedimientos de restauración y de rollback de los repositorios de infraestructura); ver evidencia.md -->

> Pasos de las tareas típicas del stack. Cada receta lleva un identificador (`REC-n`). Todas están **pendientes de evidencia**. Se usan marcadores (`<servicio>`, `<ambiente>`, `<cuenta>`, `<region>`): se sustituyen al usarlas.

## `REC-1` Servicio nuevo

1. **Tipo de configuración:** añadir la interfaz del servicio (CPU, memoria, número deseado, mínimo, máximo, objetivo de CPU, puerto del contenedor, prefijo DNS, nombre del secreto, retención de logs).
2. **Valores por ambiente:** completarlos en cada archivo (más bajo en no productivos; en producción, deseado 2, retención larga).
3. **Pila delgada:** crear el secreto de la aplicación e instanciar el constructo de servicio con balanceador; añadir el registro DNS del balanceador.
4. **Punto de entrada:** instanciar la pila bajo la bandera de configuración y declarar su dependencia de la red.
5. **Secreto:** poner el JSON con los valores reales en el secreto (`REC-2`).
6. **Comprobar:** tipos y pruebas (`validate`), luego `diff` del ambiente más bajo y despliegue de esa pila (`cdk deploy <Pila> -c env=<ambiente>`).
7. **Verificar:** la ruta de salud responde; ver logs y estado del servicio. La primera imagen es la marcadora: configurar el CI para publicar la real (`PAT-9`).

## `REC-2` Variable de entorno o secreto nuevo en un servicio que ya corre

1. Leer el secreto actual del ambiente (JSON completo).
2. Editar el JSON en local **conservando todo lo demás** y escribirlo como nueva versión del secreto.
3. **Forzar nuevo despliegue** del servicio (`update-service --force-new-deployment`); sin este paso las tareas viejas siguen con el valor anterior.
4. Esperar a que el servicio se estabilice (`wait services-stable`).
5. Volver a leer el secreto y comparar contra lo enviado.
6. Dejar escritas las dos rutas en la ficha del cambio (consola y línea de comandos) para el pase a producción. Un secreto nuevo creado desde la IaC se rellena con el valor real después del primer despliegue.

## `REC-3` Ambiente nuevo

1. Cuenta nueva y acceso de administrador.
2. Archivo de configuración copiado del ambiente más parecido; **CIDR distinto** a los existentes; dominio propio; sin valores de cuenta y región por defecto.
3. Registrar el ambiente en el cargador de configuración (los desconocidos siguen fallando).
4. `bootstrap` de la herramienta de IaC en la cuenta, para la región principal y la región fija de los certificados de la red de distribución.
5. Desplegar *foundation* en el orden de `ARQ-10`; configurar en el registrador los servidores de nombres de la zona; esperar la validación DNS de los certificados.
6. Desplegar los *workloads*; rellenar los secretos reales; lanzar el primer despliegue de cada aplicación por el pipeline; verificar las URL.
7. Crear los **ambientes de despliegue** del CI (con la variable del rol y la región) y protegerlo si es producción.
8. Confirmar las suscripciones del tema de alarmas y activar las etiquetas de asignación de costos.

## `REC-4` Restauración desde copia

- **Desde un volcado lógico:** listar las copias del bucket y elegir la requerida; descargar y descomprimir (o cargar con la herramienta de volcado); leer las credenciales del gestor de secretos; abrir el túnel por el bastión; cargar; cerrar el túnel. (15-45 min).
- **Desde una instantánea:** listar las instantáneas del clúster; restaurar a un **clúster nuevo**; añadir una instancia de escritura; repuntar las aplicaciones al endpoint nuevo o intercambiar los nombres. (30-60 min).
- Después: base accesible con datos correctos, aplicaciones respondiendo, logs sin errores nuevos, métricas en su nivel, equipo avisado, ticket con la causa raíz.

## `REC-5` Rollback de un servicio

1. Listar las revisiones de la definición de tarea de la familia.
2. Elegir la última buena (la anterior a la rota).
3. `update-service` con esa revisión y `--force-new-deployment`.
4. `wait services-stable`. (2-5 min).
5. Comprobar con la lista de `PRU-9` y abrir el ticket de la causa raíz. Si el cambio incluía un cambio de esquema, tratarlo aparte (`DAT-10`).
6. Una infraestructura rota se revierte volviendo al commit anterior y redesplegando (30+ min), salvo que el rollback automático de la pila ya lo haya hecho.

## `REC-6` Escalar un servicio o la base

- **Servicio:** editar CPU, memoria, número deseado, mínimo y máximo, o el objetivo de CPU en la configuración; `diff` y despliegue. El cambio registra una nueva revisión de la tarea y actualiza sin caída.
- **Pico inmediato sin IaC:** subir el número deseado y esperar a que se estabilice; recordar que el autoescalado lo puede bajar (`REN-4`).
- **Base:** cambiar mínimo y máximo de capacidad en la configuración y desplegar esa pila (en caliente). El cambio por línea de comandos es temporal.

## `REC-7` Pasar el WAF de conteo a bloqueo

1. Desplegar en conteo y dejar 1-2 semanas con registros completos.
2. Revisar las peticiones que coinciden con cada grupo de reglas; separar falsos positivos.
3. Cambiar el modo por defecto en la configuración (o anular por grupo de reglas para la granularidad fina) y desplegar.
4. Vigilar el volumen de bloqueos los días siguientes.

## `REC-8` Silenciar una alerta de costo esperada

Subir temporalmente el presupuesto (×2-3) y desplegar la pila de facturación; al terminar el evento, devolverlo. Es más simple que desactivar la pila, porque conserva el tema y las suscripciones.

## Por extraer

- Receta de **alarma nueva** de servicio (existen ejemplos en código, no un procedimiento verificado).
- Receta de **dominio propio** para un servicio ya desplegado (hay un tutorial sin contraste con el código).
- Receta de **simulacro de recuperación**.
