# Adaptador: Jira

<!-- tipo: adaptador · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

## Específico de `jira`

Adaptador de **tickets** (crear y leer; también transiciones de estado y subtareas). Se pide al usuario: sitio y proyecto, tipos de ticket y su jerarquía, secuencia de estados y regla de estimación. Acceso por el conector del cliente o por token de usuario guardado fuera del repositorio. Proceso: mostrar la lista de tickets a crear y esperar confirmación antes de escribir.

## Contrato de un adaptador

Todo adaptador es intercambiable: el método solo conoce estas operaciones, no la herramienta concreta.

| Operación | Obligatoria | Descripción |
|---|---|---|
| `crear-documento(titulo, contenido, padre?)` | sí | Crea un documento en el almacén y devuelve su identificador y enlace |
| `leer-documento(id o ruta)` | sí | Devuelve el contenido (en `.md` o convertido a `.md`) |
| `actualizar-documento(id, contenido)` | sí | Reemplaza o modifica; conserva el historial si la herramienta lo ofrece |
| `crear-ticket(titulo, tipo, cuerpo, padre?)` | solo adaptadores de tickets | Devuelve clave y enlace |
| `leer-ticket(clave)` | solo adaptadores de tickets | Devuelve título, estado, cuerpo y enlaces |

**Autenticación:** nunca se guardan credenciales en el repositorio ni en la instancia. El adaptador lee el acceso del entorno del usuario (sesión del cliente, variable de entorno o archivo fuera del repositorio con permisos restringidos) y, si falta, lo pide y se detiene.

**Cuando no existe:** el adaptador declara `disponible: no`; el flujo no falla, deja el rastro en `.md` dentro del almacén por defecto (`docs/` del repositorio) y lo informa. Las escrituras hacia afuera se muestran y esperan confirmación.

## Origen

Lo aporta la instancia del proyecto; el mapa de migración vive en la instancia (parametrizacion).
