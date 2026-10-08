# Instancia del meta harness

Esta carpeta es una **instancia**: lo propio de un proyecto (políticas, convenciones, conocimiento de negocio, control de cambios, documentación) apoyado en el meta harness, que aporta el método, los estándares y los perfiles de stack.

## Qué hay aquí
| Ruta | Qué es | Quién la mantiene |
|---|---|---|
| `harness.lock` | versión del harness con la que se instaló esta instancia | el instalador (`update`) |
| `politicas.toml` | qué puede y qué no puede hacer el agente (datos, git, comandos, despliegue, costos, secretos, verificación) | el equipo |
| `convenciones.toml` | formatos de ramas, commits, PR, tickets y QA; parte del estándar del harness | el equipo |
| `acceso.local.ejemplo.toml` | modelo del acceso local de cada persona | el harness |
| `acceso.local.toml` | cómo llega ESTA persona a cada recurso (no se versiona, sin secretos) | cada persona |
| `conocimiento/` | conocimiento de negocio del proyecto | el equipo |
| `cambios/` | control de cambios: una carpeta por cambio, con su especificación y su evidencia | el equipo |
| `documentacion/` | almacén de documentación en `.md` | el equipo |
| `mejoras.md` | registro de mejoras detectadas que no se aplican en el cambio en curso | el equipo |
| `.harness/` | estado del instalador (qué instaló y sus sumas) e informes | el instalador |

## Reglas de esta carpeta
- `acceso.local.toml` nunca se versiona ni lleva contraseñas, claves ni tokens: solo métodos, alias, puertos y nombres de perfiles.
- Los ambientes de datos de `politicas.toml` se **declaran** aquí; el harness no asume ninguno.
- `update` solo cambia los archivos que son del harness y que nadie modificó; lo que cambió la instancia se deja tal cual y se avisa.
- Lo que aprende esta instancia y es general (sin nombrar al proyecto) se aporta al harness; lo de negocio se queda aquí.
