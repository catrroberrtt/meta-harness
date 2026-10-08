# Patrones · AWS ECS
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (constructos reutilizables, pilas de aplicación, documentación de despliegue y de red); ver evidencia.md -->

> Catálogo de patrones de infraestructura con «cuándo SÍ», «cuándo NO» y un ejemplo mínimo. Cada patrón lleva un identificador (`PAT-n`). Todos están **pendientes de evidencia**.

**Regla de proporcionalidad.** Un patrón se aplica cuando hay hoy un consumidor real; si no, se deja en línea o no se crea (`PAT-10`). (`PAT-0`)

## 1. Servicio HTTP con balanceador (`PAT-1`)

Un solo constructo crea: repositorio de imágenes, clúster, definición de tarea, balanceador con HTTPS y redirección de HTTP, grupo de destino por IP con comprobación de salud, servicio Fargate, autoescalado por CPU y, opcionalmente, una definición de tarea adicional para migraciones y un usuario de CI.

- **Cuándo SÍ:** backend HTTP contenedorizado con 2 o más tareas o con necesidad de escalar.
- **Cuándo NO:** proceso por lotes sin tráfico entrante (usar una tarea programada, `PAT-4`); página estática (`PAT-2`); lógica puntual por evento (otro perfil).
- Parámetros que fija el patrón (puntos de partida de la instancia, no estándares): periodo de gracia de la comprobación de salud ajustado al arranque real de la aplicación (180 s en la instancia de origen); retardo de desregistro de 30 s; tareas sin IP pública; **interruptor de circuito con retroceso** activado, para que un despliegue que falla repetidamente se revierta solo en lugar de reintentar sin fin.
- Los mínimos de despliegue gradual se escriben explícitos (por ejemplo, 100 % saludable y 200 % máximo) para que un despliegue nunca baje por debajo de la capacidad actual.

```ts
new ServicioConBalanceador(this, 'Servicio', {
  vpc, serviceName: `<servicio>-${env}`, certificate,
  ecs: { cpu: 256, memory: 512, desiredCount: 2, containerPort: <puerto> },
  autoScaling: { minCapacity: 2, maxCapacity: 10, cpuTargetUtilization: 60 },
  alb: { healthCheckPath: '/health', healthCheckInterval: 30 },
});
```

## 2. Sitio estático: bucket privado + distribución de contenido (`PAT-2`)

- **Cuándo SÍ:** aplicaciones de una sola página y contenido compilado que no necesita servidor.
- **Cuándo NO:** algo que renderiza en servidor o guarda estado.
- Bucket con bloqueo total de acceso público y política que rechaza transporte no seguro; la distribución lee con **control de acceso de origen** (el bucket nunca es público; se prefiere OAC, el mecanismo vigente; la instancia conserva el legado OAI en su constructo más antiguo); la salida de CI sincroniza el bucket y **invalida** la distribución. En ambientes no productivos, clase de precio reducida de la distribución.

## 3. Tarea única de migración (`PAT-3`)

Una segunda definición de tarea, con su propio secreto de configuración, que se ejecuta una sola vez (`run-task`) y termina con código de salida.

- **Cuándo SÍ:** hay cambios de esquema que deben aplicarse **antes** de que el código nuevo reciba tráfico.
- **Cuándo NO:** la base no tiene esquema que migrar.
- Contrato con el pipeline: se ejecuta antes de actualizar el servicio y, si el código de salida no es cero, el pipeline **aborta antes de tocar el servicio** (ver `datos.md`, `DAT-9`).

## 4. Tarea o función programada (`PAT-4`)

Una regla de calendario (expresión `cron`, siempre en UTC) dispara una tarea Fargate o una función.

- **Cuándo SÍ:** copias de la base, envío de avisos periódicos, reportes periódicos.
- **Cuándo NO:** cualquier cosa que deba reaccionar a un evento; un proceso permanente (servicio).
- Se documenta en cada regla la hora local de negocio equivalente, porque la expresión está en UTC. Las programaciones con efectos reales (envíos a terceros, reportes regulatorios) se habilitan **solo en producción** (`ARQ-11`).

## 5. Cola con consumidor y cola de mensajes fallidos (`PAT-5`)

El productor deja el trabajo en una cola; un consumidor lo procesa a su ritmo; los fallos agotan reintentos y terminan en una cola de mensajes fallidos; una tabla registra el estado de cada envío.

- **Cuándo SÍ:** el efecto es hacia un tercero que puede caer o limitar la tasa (correo, notificaciones) y el resultado no se necesita en la misma respuesta.
- **Cuándo NO:** el cliente necesita el resultado inmediato.
- Costo aceptado: el efecto es asíncrono (segundos a minutos) y hay más piezas que operar y monitorear. La instancia de origen no registra alarmas sobre la cola de fallidos: queda «por extraer» en `observabilidad.md`.

## 6. Bastión de operación sin puertos de entrada (`PAT-6`)

Una instancia pequeña (arquitectura ARM, `requireImdsv2`) en el nivel privado, sin grupo de seguridad de entrada, a la que se llega solo por el gestor de sesiones del proveedor.

- **Cuándo SÍ:** hay personas que deben consultar una base aislada.
- **Cuándo NO:** el trabajo se puede hacer con una tarea o un script del pipeline.
- Sesiones con registro y con tiempo de inactividad y duración máximos (más cortos en producción) y una alarma por cada conexión a la base originada en el bastión (ver `OBS-9`).

## 7. Bucket de copias inmutables (`PAT-7`)

Bucket con cifrado por clave administrada por el cliente, **bloqueo de objetos** (escritura única, lectura múltiple), versionado, políticas de ciclo de vida a almacenamiento frío y expiración, y retención del bucket y de la clave en producción (`COD-12`). Comprobar el modo y el plazo de retención del bloqueo (ver `DAT-4`).

- **Cuándo SÍ:** datos con exigencia regulatoria o riesgo de ransomware.
- **Cuándo NO:** artefactos reproducibles desde el repositorio (frontends, funciones) — el repositorio ya es su copia.

## 8. Filtro WAF en el balanceador o en la distribución (`PAT-8`)

Reglas administradas comunes + límite de peticiones por IP, asociadas al balanceador (regional) o a la distribución (global).

- **Cuándo SÍ:** hay tráfico público real.
- **Cuándo NO:** ambientes sin tráfico real: los registros no tendrían qué analizar.
- Dos variantes observadas: modo de **solo conteo** durante 1-2 semanas para ubicar falsos positivos y luego bloqueo; o **bloqueo desde el primer día** en una plataforma nueva. Un WAF en conteo no sustituye la autenticación de la aplicación (`SEG-12`).

## 9. Arranque con imagen marcadora (`PAT-9`)

La IaC crea el servicio con una imagen pública mínima; el pipeline publica la imagen real y registra una revisión nueva de la definición de tarea.

- **Cuándo SÍ:** el servicio y su pipeline se crean en pasos distintos.
- **Cuándo NO:** si ya hay una imagen real estable: se endurece la comprobación de salud (el marcador responde con un código que la aplicación real no devuelve).
- Una imagen pública no obtiene permiso de lectura del registro privado: ese permiso y el de obtener el token del registro se otorgan **explícitamente** (ver `errores-frecuentes/README.md`, `ERR-4`).

## 10. Qué NO se crea (`PAT-10`)

- Lector de alta disponibilidad, rendimiento avanzado de la base, copias lógicas y monitoreo con almacenamiento persistente en ambientes no productivos.
- Más de un NAT en ambientes no productivos.
- Funciones con efectos reales (cobranza, reportes regulatorios) fuera de producción.
- Usuarios IAM con claves de larga vida en un proyecto nuevo (usar federación; ver `SEG-6`).
- Listas de control de acceso de red propias; puntos de enlace de interfaz sin comparar costo.
- Alarmas sin tema de notificación con suscriptores confirmados.
