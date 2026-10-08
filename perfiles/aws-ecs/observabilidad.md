# Observabilidad · AWS ECS
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (documentación de monitoreo y alertas, runbooks de diagnóstico y código de alarmas de los repositorios de infraestructura); ver evidencia.md -->

> Logs de contenedor, alarmas, tableros y diagnóstico de un servicio. Cada regla lleva un identificador (`OBS-n`). Todas están **pendientes de evidencia**. La instancia reconoce, además, que casi no hay alarmas de aplicación implementadas: lo que sigue es lo existente y lo que quedó recomendado.

## 1. Registros

- `OBS-1` **Un grupo de logs por servicio** con nombre predecible (`/aws/ecs/<servicio>-<ambiente>`) y retención por ambiente: corta en no productivos (7 días), larga en producción (365). Los logs de un servicio de apoyo con valor menor (tablero) pueden tener una retención intermedia (90 días).
- `OBS-2` **Container Insights** (métricas por tarea: CPU, memoria, red, disco) activado solo en producción, donde la diferencia de costo se justifica.
- `OBS-3` La base exporta **errores y consultas lentas** (y auditoría, en producción) al servicio de logs. El umbral de consulta lenta lo fija un **parámetro del grupo de parámetros**: se lee del código y no de la documentación (ver `ERR-13`).
- `OBS-4` Flow logs de la red completa a almacenamiento central; flow logs de la subred del bastión al servicio de logs, porque alimentan una alarma.
- `OBS-5` Los **registros de acceso** de los balanceadores y de las distribuciones de contenido van a un bucket central, con ciclo de vida y sin acceso público.
- `OBS-6` **Inventario diario** de los recursos de la cuenta, guardado en formato columnar y consultable con SQL, y etiquetas homogéneas: sirve para atribuir costos y detectar recursos huérfanos.

## 2. Alarmas

- `OBS-7` **Un tema de notificación por ambiente** con suscripción por correo a un **alias del equipo** (no a una persona). La suscripción por correo debe **confirmarse** a mano tras el primer despliegue: pendiente de confirmar = las alertas no llegan (`ERR-12`). Todas las alarmas cuelgan de ese tema.
- `OBS-8` Alarmas con **datos faltantes tratados como «no infringe»**, y con acción también al volver a OK. Conjunto mínimo recomendado para un servicio de contenedores, con los umbrales de partida de la instancia (en una de sus plataformas están implementadas las marcadas con *):
  - 5xx del balanceador * (más de 10 en 5 min, 3 periodos seguidos);
  - errores de función * (más de 5 en 5 min, 3 periodos);
  - conexiones de la base * (umbral por capacidad del motor);
  - CPU y memoria del servicio por encima del 85 %, 2 periodos (solo recomendada);
  - CPU de la base por encima del 80 % (solo recomendada).
- `OBS-9` **Alarma de acceso manual a la base:** una métrica derivada con un filtro sobre los flow logs de la subred del bastión (origen = bastión, destino = puerto del motor, acción aceptada) cuenta las conexiones; basta una en 5 minutos. Da visibilidad del acceso manual; no lo impide.
- `OBS-10` Alarmas de bastión por CPU alta (más de 80 %, 2 periodos) para detectar un uso inusual (consultas o scripts pesados).

## 3. Tableros y diagnóstico

- `OBS-11` Tablero de métricas en un servicio de contenedores con almacenamiento persistente (sistema de archivos compartido, `removalPolicy` de retención en producción) y capacidad Spot. Brecha anotada: el almacenamiento persistente **no tiene copia automática**; los tableros pierden con él.
- `OBS-12` **Orden de diagnóstico de un servicio ECS:** (1) estado del servicio y los últimos eventos (corriendo, deseadas, pendientes); (2) tareas **detenidas** y su código de parada (`stopCode`, `stoppedReason`, `exitCode`); (3) los logs del contenedor; (4) la salud de los destinos del balanceador; (5) la política y la actividad de autoescalado. Códigos de salida: 1 = error de la aplicación (mirar el log), 137 = falta de memoria, 143 = señal de terminación sin cierre ordenado.

## Por extraer

- Trazas distribuidas (la instancia solo concede permiso de lectura de trazas al tablero; no hay evidencia de instrumentación).
- Métricas de negocio y de aplicación; objetivos de nivel de servicio (SLO).
- Alarmas de colas y de mensajes fallidos.
