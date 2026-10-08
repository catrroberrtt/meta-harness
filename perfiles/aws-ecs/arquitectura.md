# Arquitectura · AWS ECS
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (documentación de arquitectura, decisiones de diseño y código de los repositorios de infraestructura como código de la instancia); ver evidencia.md -->

> Estructura de pilas, ambientes y cuentas, red por niveles, escala S/M/L y reglas de dependencia. Cada regla lleva un identificador (`ARQ-n`) que `evidencia.md` traza a su fuente. Todas están **pendientes de evidencia** (una sola instancia).

**Principio rector.** La infraestructura se define como código, se parametriza por ambiente y se arma con piezas reutilizables; lo que se crea tiene un consumidor real hoy. Un recurso sin consumidor (alarma sin suscriptor, réplica en un ambiente de pruebas, punto de enlace de interfaz sin ahorro que lo justifique) se deja fuera y se documenta como mejora futura. (`ARQ-1`)

## 1. Ambientes y cuentas

- `ARQ-2` **Un ambiente = una cuenta de nube.** Desarrollo, pruebas de calidad y producción viven en cuentas distintas, no en la misma cuenta con roles distintos. Razones registradas: radio de daño limitado, facturación separada, credenciales de un ambiente que no sirven en otro y aislamiento de datos entre ambientes.
- `ARQ-3` El costo aceptado de `ARQ-2` es multiplicar por el número de ambientes las cuentas, los perfiles de línea de comandos, los despliegues y la preparación inicial de la herramienta de IaC (`bootstrap`) en cada cuenta y región.
- `ARQ-4` Una cuenta de un ambiente no se infiere de otra: el identificador de cuenta de producción no sirve para localizar pilas de pruebas. Se lee de la configuración del ambiente o del portal de acceso.
- `ARQ-5` **Una plataforma (una línea de producto con su propia base de datos) = su propio repositorio de infraestructura y sus propias cuentas.** Las bases no se comparten entre plataformas; lo que cruza de una a otra es un canal de API puntual, nunca una consulta directa a la base de otra.
- `ARQ-6` Cada ambiente usa un bloque de direcciones de red (CIDR) distinto, para no chocar si algún día se conectan redes. Cada ambiente usa también su propio dominio o subdominio.

## 2. Estructura del repositorio de infraestructura

```
lib/
├── foundation/   # compartido por el ambiente: red, base de datos, DNS, certificados,
│                 #   registro central de logs, bastión, copias, identidades de CI, facturación
├── workloads/    # una aplicación o servicio por pila (backend, frontend, funciones)
├── constructs/   # patrones reutilizables de alto nivel (servicio con balanceador, sitio estático)
└── config/       # un archivo tipado por ambiente + el tipo de configuración
bin/              # punto de entrada: elige ambiente, valida cuenta, instancia las pilas y sus dependencias
```

- `ARQ-7` Cuatro capas con sentido único: **foundation** (lo compartido por todas las aplicaciones del ambiente), **workloads** (una aplicación por pila), **constructs** (el patrón que se repite) y **config** (los valores). Los valores nunca se escriben dentro de las pilas.
- `ARQ-8` Nombre de pila: `<proyecto>-<ambiente>-<Pila>`, derivado de **un solo** campo de nombre de proyecto que se propaga a pilas, recursos, etiquetas y exportaciones.
- `ARQ-9` Dependencias permitidas: *foundation* no depende de *workloads*; un *workload* depende de la red, del certificado y de la zona DNS de *foundation*; entre *workloads* solo se admite una dependencia explícita y de una sola propiedad (por ejemplo, la tarea de reportes recibe el rol de ejecución de la API que consulta). Toda dependencia se declara en el punto de entrada; no se infiere.
- `ARQ-10` Orden de despliegue por fases: (0) lo independiente (registro central, zona DNS, identidades de CI), (1) red y analítica, (2) base de datos y copias, (3) bastión y certificados, (4) servicios de apoyo, (5) backends, (6) frontends y funciones en paralelo, (7) lo que depende de otro *workload*. El orden lo impone la declaración de dependencias; conocerlo sirve para el arranque de un ambiente y para diagnosticar.
- `ARQ-11` Una pila opcional (servicio de monitoreo, copias, tareas con efectos reales) lleva una bandera `enabled` por ambiente; deshabilitada, **no se instancia**. Se comprueba sintetizando el ambiente y mirando que no aparezca en la salida, no confiando en el listado.

## 3. Red por niveles

| Nivel | Qué vive aquí | Salida a internet |
|---|---|---|
| **Público** | Balanceadores de carga, puerta de salida, NAT | Sí (entrada y salida) |
| **Privado con salida** | Tareas de contenedores, bastión, funciones dentro de la red | Solo saliente, por NAT |
| **Aislado** | Base de datos | Ninguna: sin ruta ni NAT |

- `ARQ-12` Las tareas de contenedores van **siempre** en el nivel privado con salida y sin IP pública; el único punto público de un backend es su balanceador (`ARQ-14`).
- `ARQ-13` La base de datos va en el nivel aislado: aunque una regla de seguridad se abriera por error, no hay ruta desde internet ni hacia internet.
- `ARQ-14` Backend HTTP: DNS → (filtro WAF si aplica) → balanceador público → tareas privadas. Frontend estático: DNS → (filtro WAF) → red de distribución de contenido → bucket **privado** de objetos.
- `ARQ-15` NAT: uno en ambientes no productivos; uno por zona de disponibilidad activa en producción (si una cae, la otra zona conserva su salida). Zonas: dos en no productivos, tres en producción. El NAT es una de las partidas fijas de costo más altas (ver `REN-9`).
- `ARQ-16` Gateways de punto de enlace gratuitos (almacenamiento de objetos, tabla clave-valor) sí; puntos de enlace de interfaz para registro de imágenes o gestor de secretos, solo tras comparar su costo mensual con el NAT que sustituirían. No se declaran listas de control de acceso de red (NACL) propias: los grupos de seguridad bastan y las NACL, al no tener estado, solo añaden complejidad.

## 4. Cuánta estructura: escala S/M/L

La escala es una **lectura de los tres tamaños observados**, no un umbral medido. Se elige el tamaño antes de escribir pilas y cada pieza extra lleva una frase de justificación. (`ARQ-17`)

| Tamaño | Cuándo | Contiene |
|---|---|---|
| **S** | Un servicio HTTP sobre una red y un certificado que ya existen | Config del ambiente · pila delgada · constructo de servicio con balanceador (clúster, tarea, servicio, repositorio de imágenes, autoescalado) · secreto de la aplicación · registro DNS |
| **M** | Un producto con base de datos, frontend y pocas funciones, en 2 ambientes | S + red por niveles · base gestionada · tarea de migración · frontend estático · tema de alarmas · identidades de CI federadas |
| **L** | Plataforma completa con varios servicios y requisitos regulatorios | M + varios backends y frontends · funciones con cola · copias lógicas inmutables · filtro WAF · presupuestos y detección de anomalías · inventario de recursos · registro central y auditoría · bastión de operación |

- `ARQ-18` Lo que distingue L de M no es el número de servicios sino el conjunto de **controles de plataforma** (copias inmutables, auditoría, presupuestos, WAF). Se agregan por riesgo, no por tamaño.
- `ARQ-19` Un cambio que añade un servicio recorre siempre el mismo camino (ver `recetas/README.md`): tipo de configuración → valores por ambiente → pila delgada → instancia en el punto de entrada con su dependencia → secreto → despliegue → verificación.

## 5. Cómputo y entrega

- `ARQ-20` Contenedores en **Fargate** y no en instancias propias: sin administrar sistema operativo ni parches, pago por tarea, escalado por número de tareas y aislamiento por interfaz de red y grupo de seguridad propios. Costos aceptados: arranque de una tarea nueva de 10 a 30 s y un tope por tarea (16 vCPU, 120 GB al momento de la decisión). Instancias propias solo para un sistema legado que ya las usa.
- `ARQ-21` Frontends de una sola página como sitio estático (bucket privado + distribución de contenido con control de origen), no en contenedores: es más barato, escala sin ajustes y no hay servidores que mantener.
- `ARQ-22` La IaC sin lenguaje de plantillas propio (CDK en el mismo lenguaje que los backends): constructos de alto nivel que encapsulan patrones completos, tipado fuerte y plantilla sintetizada revisable. Costo aceptado: el estado es el de la herramienta de plantillas de la nube, menos portable, y las plantillas generadas incluyen muchos recursos automáticos.
- `ARQ-23` El pipeline de despliegue **descubre** dónde desplegar (nombre de repositorio de imágenes, clúster, servicio, contenedor) leyendo las salidas de las pilas o parámetros publicados por la infraestructura, no nombres fijos; así sobrevive a un cambio de nombre de proyecto.
- `ARQ-24` Los certificados son dos por ambiente: uno regional para los balanceadores y otro en la región fija que exige la red de distribución; se validan por DNS contra la zona gestionada por la propia IaC.

## 6. Qué NO entra en este perfil

Funciones puramente sin servidor con su puerta HTTP propia tienen un perfil distinto; aquí solo se citan donde comparten red, secretos o pipeline con un servicio de contenedores.
