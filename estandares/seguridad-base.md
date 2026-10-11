# Línea base de seguridad: 20 comprobaciones antes de lanzar

<!-- tipo: estándar técnico · capa: 2 -->
<!-- revisado: 2026-10-11 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Veinte cosas que se piden **antes de lanzar** una aplicación. Datos de máquina en `seguridad-base.toml`
(un solo catálogo; este documento lo explica). Herramienta: `herramientas/seguridad_base.py`.

## Dos usos con fuerza distinta

| Situación | Fuerza | Qué pasa |
|---|---|---|
| **Sistema nuevo** (`harness erp`, y `init` cuando exista) | **Se exige** | Las 20 entran como requisitos (`RQ-NN`) de la especificación, con su criterio (`CA-NN.1`) y una fila `pendiente` en la matriz. No se da por terminado un sistema nuevo con filas de seguridad sin evidencia. |
| **Proyecto existente** (`adopt`) | **Se marca, no se impone** | El informe «cómo es este proyecto» trae una sección informativa: qué evidencia hay y qué no se pudo ver. No agrega «Falta» ni «Propuesta» ni cambia el resultado: el equipo decide qué adoptar y cuándo. |

Un proyecto que ya está en marcha puede tener o no tener cada una; imponerlas de golpe lo convertiría en un
informe de deuda. Marcarlas le da el mapa.

## Cómo se lee el estado (análisis estático)

| Estado | Significa | Cómo se actúa |
|---|---|---|
| `evidencia` | Se vio algo concreto (archivo y línea) que la cubre | Revisar que cubra de verdad; enlazarla en la matriz |
| `indicios` | Hay señales, pero solo se confirma en ejecución | Confirmar con una prueba o una revisión de configuración |
| `sin_evidencia` | No se vio al leer los archivos | **No es «no está»**: puede vivir en la infraestructura. Preguntar |
| `confirmar` | No se puede ver leyendo código (p. ej. HTTPS, cabeceras del borde) | Comprobar en el entorno real |
| `alerta` | Apareció algo sospechoso (secreto en código, `.env` versionado, interpolación en consulta) | Revisar primero; puede ser falso positivo |

Los detectores leen archivos de código y configuración, omitiendo pruebas, `.md` y bloqueos de dependencias.
«Versionado» se decide con `git ls-files`, no con lo que haya en disco.

## Las 20

| Id | Comprobación | Se ve leyendo | Qué se exige a un sistema nuevo |
|---|---|---|---|
| SEG-01 | Ocultar API keys | Sí | Claves en el entorno; ejemplo sin valores versionado; real ignorado |
| SEG-02 | Eliminar secretos de Git | Sí | Escáner de secretos al confirmar o en CI; ningún entorno real versionado |
| SEG-03 | Clave pública para la base | Sí | Ninguna cadena de conexión ni clave de servicio en el frontend |
| SEG-04 | Seguridad por fila (RLS o equivalente) | No | Políticas por fila o capa de servicio única que filtra por propietario, con pruebas |
| SEG-05 | Encriptar datos sensibles | No | Cifrado en reposo con clave gestionada fuera de la base |
| SEG-06 | Forzar la autenticación | Sí | Guardia global por defecto; rutas públicas declaradas una a una |
| SEG-07 | Restringir el acceso a registros | No | Permiso por acción y pertenencia verificada en servidor, con pruebas de acceso cruzado |
| SEG-08 | Bloquear manipulación de campos | Sí | Lista blanca de campos y rechazo de los no declarados |
| SEG-09 | Proteger cookies de sesión | No | HttpOnly, Secure y SameSite, o sesión por cabecera con corta vida |
| SEG-10 | Hashear contraseñas | Sí | argon2/bcrypt/scrypt con costo configurable |
| SEG-11 | Límite de intentos | Sí | Tasa global, más estricta en acceso, y bloqueo temporal por fallos |
| SEG-12 | Protección contra bots | No | Verificación en formularios públicos, con alternativa accesible |
| SEG-13 | Parametrizar consultas | Sí | ORM o parámetros; prohibido interpolar entradas en SQL |
| SEG-14 | Validar entradas | Sí | Esquema de validación por entrada, con límites |
| SEG-15 | Sanitizar contenido | Sí | Escape por defecto; HTML solo con lista blanca |
| SEG-16 | Restringir archivos | Sí | Tipos verificados por contenido, tope de tamaño, destino fuera de la raíz pública |
| SEG-17 | Devolver solo lo necesario | No | Modelos de respuesta explícitos; pruebas de que no filtran campos internos |
| SEG-18 | Cabeceras de seguridad | No | CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy activas |
| SEG-19 | Forzar HTTPS | No | Redirección y HSTS en el borde |
| SEG-20 | Escanear dependencias | Sí | Escaneo en CI o bot de actualización con umbral que frene lo crítico |

## Uso

```bash
python3 herramientas/seguridad_base.py <carpeta>          # tabla; 0 siempre (informativo)
python3 herramientas/seguridad_base.py <carpeta> --json
python3 herramientas/harness-detectar.py <carpeta>        # incluye la sección informativa
harness erp --negocio <docs> --erp-base <ruta>            # las 20 entran como requisitos
```

## Cómo se completa en un sistema nuevo

Cada fila de la matriz cierra con **evidencia enlazada**: el archivo y la línea, la prueba que la demuestra
o la configuración del entorno. Las que no se ven leyendo (4, 5, 7, 9, 12, 17, 18, 19) se cierran con una
prueba en ejecución o una captura de configuración, no con una lectura de código. Una fila `alerta` se
resuelve o se justifica por escrito antes de cerrar.
