# Catalogo de recursos y metodos de acceso

<!-- tipo: herramienta · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Para cada metodo: **se comprueba** (solo lectura), **nunca se hace**, y **que pedir y a quien** si falta.
Comunes a todos: nunca se guardan ni se leen valores de secretos; nunca se escribe en el recurso.

## Que exige cada punto de partida
- **A (proyecto empezado):** repositorios, documentacion, tickets, datos y nube (CI ademas en `init`).
- **B (desde cero):** solo un almacen de documentacion con la informacion de partida. Datos y nube, cuando el plan los pida.
- **C (migracion):** el sistema origen (codigo o volcado) o su descripcion en archivos: esquema, diccionario, hojas de calculo.
  Sin esa informacion en B o C: falla diciendo que falta y donde ponerla.

## Datos (un bloque por ambiente de la politica)
| Metodo | Se comprueba | Nunca | Que pedir y a quien |
|---|---|---|---|
| `directo` | alcanzabilidad TCP a host:puerto con tiempo limite corto | abrir sesion SQL, leer usuario o clave | Al responsable de bases de datos: permitir tu red hacia host:puerto |
| `tunel_ssh` | existe `ssh`; el puerto local del tunel escucha | abrir el tunel por ti, leer llaves | Al responsable de bases: alias/llave de salto; abre el tunel y repite |
| `ssm` | existen `aws` y el plugin de sesion; perfil presente por nombre; puerto de reenvio escucha | iniciar la sesion, leer credenciales | Al responsable de nube: permiso de sesion y alta del perfil |
| `bastion` | existe `ssh`; el bastion es alcanzable | conectarse, leer llaves | Al responsable de bases: acceso al bastion (lista de IP, llave) |
| `vpn` | el host:puerto responde (la VPN esta arriba) | conectar la VPN | Al responsable de red: cuenta de VPN; conectala y repite |
| `copia_local` | la ruta del volcado existe, o el host:puerto de la copia responde | leer el volcado | Al responsable de bases: un volcado/copia de solo lectura |
| `sin_acceso` | nada | - | Al responsable de bases: cualquier via de solo lectura; o aceptar el modo degradado (verificacion con datos: NO DISPONIBLE) |
Produccion nunca es requisito; si se declara, se muestra a titulo informativo.

## Nube
| Metodo | Se comprueba | Nunca | Que pedir y a quien |
|---|---|---|---|
| `perfil_sso` | existe la CLI; el NOMBRE del perfil esta configurado; la sesion esta vigente (identidad de solo lectura) | leer tokens o claves | Al responsable de nube: alta SSO del perfil; inicia sesion y repite |
| `rol_asumido` | igual que perfil, con el perfil que asume el rol | leer credenciales | Al responsable de nube: permiso para asumir el rol de lectura |
| `claves_entorno` | las variables declaradas (solo nombres) EXISTEN | leer o imprimir sus valores | Al responsable de nube: claves temporales de solo lectura, cargadas en tu entorno |
| `sin_acceso` | nada | - | Una identidad de nube de solo lectura |

## Repositorios
| Metodo | Se comprueba | Nunca | Que pedir y a quien |
|---|---|---|---|
| `ssh` | `git` y `ssh`; el servicio responde en su puerto | leer llaves | Al administrador de repos: registrar tu llave publica |
| `https` | `git`; existe un `credential.helper` | leer o guardar credenciales | Al administrador de repos: acceso de lectura; configura el gestor de credenciales |
| `gh` | existe `gh` y `gh auth status` es valido | leer el token | Al administrador de repos: acceso; ejecuta `gh auth login` |

## Almacen de documentacion
| Metodo | Se comprueba | Nunca | Que pedir y a quien |
|---|---|---|---|
| `confluence` | host alcanzable (A); espacio declarado (B/C) | iniciar sesion, escribir paginas | Al administrador de la documentacion: lectura del espacio |
| `drive_md` | la carpeta local con la exportacion en `.md` existe (y en B/C tiene archivos) | leer su contenido | Al administrador: la exportacion a `.md` del espacio |
| `carpeta_repo` | la carpeta del repo existe (y en B/C tiene archivos) | escribir en ella | Poner ahi `.md`, xlsx/csv, esquemas SQL o diagramas exportados |

## Tickets
`jira` (host alcanzable), `github_issues` (`gh` autenticado), `ninguno` (declarado: el proyecto no los usa, es valido).
Falta: pedir al administrador del gestor de tickets lectura del proyecto. Nunca se crean ni editan tickets.

## Integracion/despliegue continuo
`github_actions` (`gh` autenticado), `otro` (host alcanzable), `ninguno`. Falta: pedir al responsable de CI
lectura de los pipelines. Nunca se lanza un pipeline.

## Origen (solo partida C)
| Metodo | Se comprueba | Nunca | Que pedir y a quien |
|---|---|---|---|
| `codigo` / `volcado` | la ruta existe y tiene archivos | modificarla | Al responsable del sistema origen: copia del codigo o volcado de solo lectura |
| `descripcion` | la ruta existe y tiene archivos (esquema, diccionario, hojas de calculo) | modificarla | Al responsable del sistema origen: esquema y diccionario de campos exportados |
