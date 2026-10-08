# Rendimiento · AWS ECS
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (constructos y configuración por ambiente, documentación de costos, escalado y alertas de facturación); ver evidencia.md -->

> Dimensionamiento de tareas, escalado, capacidad de la base, costos y topes. Cada regla lleva un identificador (`REN-n`). Todas están **pendientes de evidencia**; los números son **puntos de partida de una sola instancia**, no estándares, y las cifras de costo son estimaciones, no mediciones.

## 1. Dimensionamiento y escalado

- `REN-1` Se parte de una **tarea pequeña y uniforme** entre ambientes (256 de CPU / 512 MiB en la instancia) y se sube cuando una medición lo pide: un código de salida 137 (falta de memoria) o una utilización de memoria pegada al tope ordenan subir la memoria. El cambio se hace en la configuración, se registra una revisión nueva de la tarea y la actualización es gradual, sin caída.
- `REN-2` **Autoescalado por seguimiento de objetivo de CPU.** Objetivo de 60 a 70 % (60 % donde importa la latencia). Mínimo de 2 tareas en producción (alta disponibilidad) y 1 en no productivos; máximo por ambiente. Enfriamientos: salida (escalar hacia arriba) 60 s; entrada (escalar hacia abajo) 60 a 120 s, nunca menor que la de salida.
- `REN-3` El **periodo de gracia** de la comprobación de salud se ajusta al arranque real (180 s en una aplicación con arranque lento; 60 s en otra más rápida). Retardo de desregistro de 30 s. Una comprobación de salud demasiado estricta con un arranque lento causa un ciclo de reinicios (`ERR-2`).
- `REN-4` Escalar a mano (`update-service --desired-count`) es **temporal**: el autoescalado lo revierte. Para mantener un valor, se sube el mínimo en la configuración.
- `REN-5` **Carga tolerante a interrupciones → capacidad Spot** (ahorro ≈70 %, usado en un servicio de tableros) y **arquitectura ARM64** (≈20 %), siempre con un ejecutor de CI de la misma arquitectura (`COD-19`). No se usa Spot en servicios que atienden al usuario.
- `REN-6` Base serverless: capacidad mínima > 0 en producción (sin arranque en frío); mínima 0 con auto-pausa en no productivos; el máximo se ajusta por medición y puede cambiarse en caliente. Lo que se cambia por línea de comandos es temporal: la IaC lo sobrescribe en el siguiente despliegue.

## 2. Costos

- `REN-7` Se mantiene una **estimación mensual por servicio** en la documentación (rangos, no cifras exactas) y se compara con el costo real por servicio y por etiqueta (`COD-8`). En la instancia, la mayor partida fija de producción es el NAT, seguida por la base y el cómputo.
- `REN-8` Palancas observadas: un NAT en no productivos; auto-pausa de la base; sin lector en no productivos; clase de precio reducida de la distribución en no productivos; retención corta de logs en no productivos (7 días contra 365); flow logs a almacenamiento de objetos y no a logs; claves del cliente solo donde hace falta; sistema de archivos compartido de una sola zona y con paso a acceso infrecuente; ciclo de vida de copias a almacenamiento frío.
- `REN-9` El NAT es la partida que más pesa; los puntos de enlace de VPC para el registro, el gestor de secretos y los logs lo reducirían pero **tienen costo mensual propio**; se decide con números.
- `REN-10` **Tope mensual por cuenta** (presupuesto) con avisos al 80 % del gasto real, al 100 % del real y al 100 % del **proyectado**; el aviso del proyectado es el más temprano (días 5 a 10 del mes) y el más útil. Los topes de cada ambiente se definen en su configuración.
- `REN-11` **Detección de anomalías de costo por servicio**, con umbral en dinero por ambiente. El modelo necesita ≈10 días de historia antes de ser fiable; no es retroactivo.
- `REN-12` Respuesta por tipo de alerta: 80 % real, solo observar y comparar contra el mes previo (un servicio que sube >20 %); 100 % real, identificar el servicio y actuar en ≤24 h (en no productivos, buscar recursos huérfanos: tareas olvidadas, instantáneas, NAT sin uso); 100 % proyectado, decidir en la semana; anomalía, validar en 24 h y marcar los falsos positivos para mejorar el modelo.
- `REN-13` La alarma de facturación estimada **absoluta** de la plataforma de métricas solo existe en la cuenta pagadora de una organización; en las cuentas vinculadas el presupuesto cumple ese papel. Subir un tope temporalmente (×2-3) o desactivar la pila de facturación son las dos formas de silenciar un evento esperado; la primera conserva el tema y las suscripciones.

## Por extraer

- Escalado por memoria, por número de solicitudes o por profundidad de cola (solo hay evidencia de CPU).
- Pruebas de carga y métricas de capacidad reales (los tamaños se eligieron por estimación).
- Costo por inquilino o por funcionalidad dentro de una misma cuenta.
