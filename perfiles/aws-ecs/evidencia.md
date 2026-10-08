# Evidencia · AWS ECS
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (documentos de infraestructura de la skill de la instancia y repositorios de infraestructura como código leídos en solo lectura) -->

> Tabla «regla → fuente: instancia de origen, sección». Toda regla viene de **una sola instancia**: por R24 todas están **pendientes de evidencia** hasta contrastarlas con una segunda instancia independiente y registrar la decisión humana. La evidencia es correlacional: que una práctica se use no la hace «la mejor».

Estados: `pendiente de evidencia` (una sola instancia) · `respaldada` (2 o más instancias independientes y decisión humana).

**Aviso sobre la independencia.** Las fuentes incluyen **varios repositorios de infraestructura de la misma organización** (varios proyectos de infraestructura). Por compartir equipo y herencia de código **no cuentan como instancias independientes**; sirven para registrar **divergencias** (ver más abajo), no para promover reglas.

**Cómo se contrastó.** Las reglas de la documentación se comprobaron contra el código de los repositorios (restricciones de red, circuitos, escalado, retenciones, alarmas, pruebas). Donde no coincidían, se anotó la divergencia y se prefirió el código (`ERR-13`).

Fuentes (se citan por su descripción, sin nombres de archivos ni de proyectos):
- **DA** documentación de arquitectura y ambientes (comparativas de ambientes, dependencias entre pilas, topología de red, orden de despliegue).
- **DD** registro de decisiones de arquitectura.
- **CP** código de los constructos y pilas de la plataforma principal.
- **CN** código, pipelines y pruebas de la plataforma más nueva.
- **CI** documento de CI/CD y de la federación de identidades.
- **DS** documentación de seguridad (secretos, roles, cifrado, red).
- **DR** documentación de recuperación (copias, RPO/RTO, restauración y rollback).
- **DM** documentación de monitoreo, costos y facturación.
- **DO** tutoriales y runbooks de operación.
- **MC** mapa de infraestructura y cuentas por ambiente de la skill.

## Reglas de arquitectura.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| ARQ-1 | DA (alcance de cada pila); DD (consumidores reales); DM (mejoras no implementadas) | pendiente de evidencia |
| ARQ-2, ARQ-3 | DD (separación en cuentas); DA (ambientes); MC (cuentas por ambiente) | pendiente de evidencia |
| ARQ-4 | MC (cuentas por ambiente: caso de pila inexistente en otra cuenta) | pendiente de evidencia |
| ARQ-5 | MC (bases de datos por plataforma); CP (una pila de base por repositorio) | pendiente de evidencia |
| ARQ-6 | DA (ambientes: red y dominios) | pendiente de evidencia |
| ARQ-7, ARQ-8 | DA (estructura del repositorio); CP (nombres de pilas) | pendiente de evidencia |
| ARQ-9, ARQ-10 | DA (dependencias entre pilas; orden de despliegue); CP (punto de entrada) | pendiente de evidencia |
| ARQ-11 | DA (pilas que no se despliegan fuera de producción); CP (punto de entrada) | pendiente de evidencia |
| ARQ-12 a ARQ-14 | DA (topología de red); DS (red y seguridad); CP (red, servicio) | pendiente de evidencia |
| ARQ-15, ARQ-16 | DA (ambientes: red); DM (costos); DS (red: NACL, puntos de enlace); CP (red) | pendiente de evidencia |
| ARQ-17 a ARQ-19 | lectura de tres tamaños observados: CN (alcance mínimo), CP (plataforma completa), DO (servicio nuevo) | pendiente de evidencia |
| ARQ-20 a ARQ-22 | DD (Fargate, sitio estático, CDK) | pendiente de evidencia |
| ARQ-23 | CI (descubrimiento dinámico); CN (parámetros publicados por la IaC) | pendiente de evidencia |
| ARQ-24 | DA (certificados); DO (diagnóstico de certificados) | pendiente de evidencia |

## Reglas de patrones.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| PAT-0, PAT-10 | DA, DM (recursos no creados), DD | pendiente de evidencia |
| PAT-1 | CP (constructo de servicio con balanceador y su documento); CN (servicio); DO (agregar servicio) | pendiente de evidencia |
| PAT-2 | DD (sitio estático); CP (constructo de sitio estático); CI (patrón de frontend) | pendiente de evidencia |
| PAT-3 | CP (tarea de migración del constructo); CI (migraciones antes del servicio); DS (secreto de migración) | pendiente de evidencia |
| PAT-4 | DA (tareas programadas); DR (copias programadas) | pendiente de evidencia |
| PAT-5 | DD (cola de correo y cola de mensajes fallidos) | pendiente de evidencia |
| PAT-6 | MC (bastión); CP (bastión); DA (bastión) | pendiente de evidencia |
| PAT-7 | DR (estrategia de copias); CP (copias); DS (cifrado) | pendiente de evidencia |
| PAT-8 | CP (tipo de configuración del WAF); CN (WAF en bloqueo); MC (WAF en conteo) | pendiente de evidencia |
| PAT-9 | CP (imagen inicial del constructo); CN (comprobación de salud del marcador) | pendiente de evidencia |

## Reglas de codificacion.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| COD-1, COD-5, COD-6 | DA (configuración); DO (leer y modificar configuraciones); CN (tipos de configuración) | pendiente de evidencia |
| COD-2 a COD-4 | CP (punto de entrada: comprobación de seguridad); CN (cargador y prueba de fail-closed) | pendiente de evidencia |
| COD-7 | DA (nombres de pilas); DS (convención de secretos); CP (balanceador) | pendiente de evidencia |
| COD-8, COD-9 | DM (estrategia de etiquetado); CP (etiquetas de gobierno) | pendiente de evidencia |
| COD-10 | DO (diagnóstico de despliegue fallido) | pendiente de evidencia |
| COD-11 | CN (comentario del oyente con identificador lógico fijo) | pendiente de evidencia |
| COD-12 | CP (políticas de eliminación por recurso); DR (retención) | pendiente de evidencia |
| COD-13 | DR (restauración de infraestructura: protección contra terminación); CP | pendiente de evidencia |
| COD-14 | DO (despliegue con CDK) | pendiente de evidencia |
| COD-15 a COD-18 | DA (constructos); DO (crear constructo, agregar servicio); CP; CN | pendiente de evidencia |
| COD-19 | CI (ejecutor de arquitectura nativa); DM (ahorro de ARM) | pendiente de evidencia |
| COD-20, COD-21 | CI (patrón de contenedores); CN (variables de la tarea) | pendiente de evidencia |

## Reglas de datos.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| DAT-1 | DS (red y seguridad: grupo de seguridad de la base); CP (base) | pendiente de evidencia |
| DAT-2 | DS (secretos, cifrado); CP (base) | pendiente de evidencia |
| DAT-3 | DR (copias automáticas); DA (ambientes: retención) | pendiente de evidencia |
| DAT-4, DAT-5 | DR (estrategia de copias, RPO y RTO); CP (copias) | pendiente de evidencia |
| DAT-6 | DA (ambientes: copias); MC (cuentas por ambiente: ausencia de copias) | pendiente de evidencia |
| DAT-7, DAT-8 | DD (base serverless); DA (ambientes: base); CP (base) | pendiente de evidencia |
| DAT-9 | CI (migración antes del servicio y aborto); DS (secreto de migración) | pendiente de evidencia |
| DAT-10, DAT-11 | DR (rollback: prevención) | pendiente de evidencia |
| DAT-12 | DA (bastión); DO (conectar bastión a la base); CP | pendiente de evidencia |
| DAT-13 | DR (restauración); DO (restauración) | pendiente de evidencia |
| DAT-14 | CN (almacenamiento de documentos) | pendiente de evidencia |
| DAT-15 | DR (gestor de secretos) | pendiente de evidencia |

## Reglas de pruebas.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| PRU-1 | DO (scripts de validación y despliegue) | pendiente de evidencia |
| PRU-2, PRU-8 | CN (pipeline de solicitud de integración y de deriva) | pendiente de evidencia |
| PRU-3 a PRU-5 | CN (pruebas de la plantilla) | pendiente de evidencia |
| PRU-6, PRU-7 | DO (despliegue con CDK; primer diff y despliegue); DR (prevención) | pendiente de evidencia |
| PRU-9, PRU-10 | DR (lista de comprobación); CI (espera de estabilidad del servicio) | pendiente de evidencia |

## Reglas de seguridad.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| SEG-1, SEG-2 | DS (roles y permisos de ejecución y de tarea); CP (definición de tarea) | pendiente de evidencia |
| SEG-3 | CN (roles de CI por repositorio, PassRole condicionado) | pendiente de evidencia |
| SEG-4, SEG-5 | DS (inventario y buenas prácticas de secretos); DO (agregar secreto a un servicio); runbook de variables de entorno | pendiente de evidencia |
| SEG-6 | CI (autenticación del pipeline); CN (identidad); DD (migración a OIDC) | pendiente de evidencia |
| SEG-7 | DS (política de rotación); DO (rotar credenciales) | pendiente de evidencia |
| SEG-8, SEG-9 | CI (política de despliegue entre plataformas; protección real de la rama principal) | pendiente de evidencia |
| SEG-10 | CI (pipeline de aplicación móvil; etiquetado de imágenes) | pendiente de evidencia |
| SEG-11 | MC (cuentas por ambiente: perfiles); DS (roles de usuarios) | pendiente de evidencia |
| SEG-12 | MC (WAF en conteo y huecos de autenticación) | pendiente de evidencia |
| SEG-13 | CP (comprobación de seguridad del punto de entrada) | pendiente de evidencia |
| SEG-14 a SEG-16 | DS (red y seguridad); CP (bastión: IMDSv2) | pendiente de evidencia |
| SEG-17 a SEG-19 | DS (cifrado, auditoría, brechas anotadas); CP (registro central y auditoría) | pendiente de evidencia |

## Reglas de rendimiento.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| REN-1 | DA (ambientes: tarea); DO (escalar un servicio); DO (diagnóstico de falta de memoria) | pendiente de evidencia |
| REN-2, REN-3 | CP (autoescalado, periodo de gracia); CN (autoescalado) ; DA | pendiente de evidencia |
| REN-4 | DO (escalar un servicio) | pendiente de evidencia |
| REN-5 | DM (estrategias de costo); CI (ejecutor nativo) | pendiente de evidencia |
| REN-6 | DA (ambientes: base); DO (escalar la base) | pendiente de evidencia |
| REN-7, REN-8, REN-9 | DM (estimación y estrategias de costo) | pendiente de evidencia |
| REN-10 a REN-13 | DM (alertas de facturación: presupuesto, anomalías, respuestas, limitaciones) | pendiente de evidencia |

## Reglas de observabilidad.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| OBS-1, OBS-2 | DM (logs por servicio y retención; Container Insights) | pendiente de evidencia |
| OBS-3 | DM (logs de la base); CP (grupo de parámetros) | pendiente de evidencia |
| OBS-4, OBS-5 | DM (flow logs, accesos); CP (registro central) | pendiente de evidencia |
| OBS-6 | DM (inventario); CP (pila de inventario) | pendiente de evidencia |
| OBS-7, OBS-8 | DM (alertas, alarmas recomendadas); CN (alarmas implementadas) | pendiente de evidencia |
| OBS-9, OBS-10 | DM (alertas del bastión; métricas derivadas); MC (cadena de monitoreo) | pendiente de evidencia |
| OBS-11 | DM (tablero); DR (almacenamiento persistente) | pendiente de evidencia |
| OBS-12 | DO (diagnóstico de un servicio de contenedores) | pendiente de evidencia |

## Reglas de errores-frecuentes/README.md y recetas/README.md

| Regla | Fuente: instancia de origen, sección | Estado |
|---|---|---|
| ERR-1, REC-2 | runbook de variables de entorno; DO (agregar secreto a un servicio) | pendiente de evidencia |
| ERR-2, ERR-3, ERR-14 | DO (diagnóstico de contenedores y escalado) | pendiente de evidencia |
| ERR-4 | CN (concesión explícita de lectura); CP (permiso del token de registro) | pendiente de evidencia |
| ERR-5, ERR-8, ERR-9 | DO (diagnóstico de despliegue fallido); CN (identificador lógico fijo); DR (rollback de pilas) | pendiente de evidencia |
| ERR-6 | MC (cuentas por ambiente: ausencia de copias); DA | pendiente de evidencia |
| ERR-7 | CI (aborto antes de tocar el servicio) | pendiente de evidencia |
| ERR-10 | MC (cuentas por ambiente); CP (comprobación de seguridad) | pendiente de evidencia |
| ERR-11 | DO (solución de problemas de CI) | pendiente de evidencia |
| ERR-12, ERR-19 | DM (alertas de facturación) | pendiente de evidencia |
| ERR-13 | contraste entre DR/DS y CP  | pendiente de evidencia |
| ERR-15 | CP (mapeo de secretos por posición en la definición de tarea) | pendiente de evidencia |
| ERR-16 | CP (balanceador) | pendiente de evidencia |
| ERR-17 | DA (pilas condicionales) | pendiente de evidencia |
| ERR-18 | DS (red y seguridad: grupo de seguridad de la base) | pendiente de evidencia |
| ERR-20 | MC (cuentas por ambiente) | pendiente de evidencia |
| REC-1 | DO (agregar un servicio de contenedores) | pendiente de evidencia |
| REC-3 | DA (orden de despliegue y arranque); DO (agregar un ambiente); CN (puesta en marcha única) | pendiente de evidencia |
| REC-4, REC-5 | DR (restauración y rollback); DO (restaurar copia; rollback de emergencia) | pendiente de evidencia |
| REC-6 | DO (escalar un servicio); DM (escalar la base) | pendiente de evidencia |
| REC-7 | CP (tipo de configuración del WAF: conteo antes de bloqueo) | pendiente de evidencia |
| REC-8 | DM (alertas de facturación: silenciar) | pendiente de evidencia |

## Decisiones humanas y alternativas descartadas

- Aún no hay decisiones registradas para este perfil.
- Descartado en la instancia de origen (se conserva como regla negativa): listas de control de acceso de red propias (`ARQ-16`), puntos de enlace de interfaz sin comparar costo (`ARQ-16`), usuarios IAM con claves de larga vida en la plataforma nueva (`SEG-6`), instancias propias en lugar de Fargate (`ARQ-20`), contenedores para frontends estáticos (`ARQ-21`), copias lógicas en ambientes no productivos (`DAT-6`).

## Divergencias entre fuentes

Las diferencias observadas entre las plataformas de origen y entre la documentación y el código **no se publican aquí**: se registran en la instancia, que es quien debe verificarlas y corregirlas. Aquí solo se conserva la regla general (`ERR-13`: verificar en el código y en la plantilla sintetizada antes de citar un control).

## Pendiente de evidencia: lista completa

Todas las reglas anteriores. Las que dependen además de una decisión puntual de la instancia (puntos de partida, no estándares): los tamaños de tarea (`REN-1`), los objetivos de CPU y los enfriamientos (`REN-2`), el periodo de gracia (`REN-3`), las retenciones de logs y copias (`OBS-1`, `DAT-3`, `DAT-4`), la frecuencia de copia de 12 h (`DAT-4`), los plazos de rotación (`SEG-7`), los umbrales de alarma (`OBS-8`) y los porcentajes del presupuesto (`REN-10`).

## Documentos que siguen «por extraer», con motivo

- **Pruebas** (carga, capacidad, simulacros): sin evidencia de que se hayan ejecutado.
- **Observabilidad**: trazas, métricas de aplicación, SLO, alarmas de colas: sin evidencia.
- **Rendimiento**: escalado por memoria, solicitudes o cola; mediciones reales: sin evidencia.
- **Datos**: simulacros de restauración, réplicas de lectura, multirregión: sin evidencia.
- **Seguridad**: gestión de vulnerabilidades de dependencias y políticas de la organización: sin evidencia.
- **Recetas**: alarma nueva, dominio propio, simulacro de recuperación: solo hay tutoriales no contrastados con el código.
