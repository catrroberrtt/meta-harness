# Instalador

<!-- tipo: herramienta · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instalador y sus pruebas -->

`instalar.sh <adopt|init|update|migrar> <carpeta-de-la-instancia> [opciones]`. La lógica está en `harness_instalar.py` (biblioteca estándar, sin red). **Sin `--aplicar` solo muestra el plan y no escribe nada.**

## Uso
```
instalar.sh <modo> <carpeta-de-la-instancia> [--partida A|B|C] [--acceso <acceso.local.toml>]
            [--politica <politicas.toml>] [--proyecto <carpeta>] [--aceptar-degradado]
            [--aceptar-dentro-de-repo] [--harness <raiz>] [--aplicar]
```
`--acceso` y `--politica` toman por defecto los de la instancia (`acceso.local.toml`, `politicas.toml`); sin política, la del harness. `--proyecto` (solo `adopt`) es el proyecto analizado cuando es distinto de la instancia.

## Modos
| Modo | Partida | Qué hace |
|---|---|---|
| `adopt` | A, proyecto empezado | Puerta de accesos; ejecuta `harness-detectar` y deja `.harness/informe-adopt.md` y la propuesta de política y convenciones en `.harness/propuesta/`. No cambia código. Con otro proyecto, el informe va a la instancia, nunca al proyecto. |
| `init` | B, desde cero (o `--partida A` para instalar el esqueleto sobre un proyecto empezado, usando la propuesta de `adopt` si existe) | Puerta de accesos; en B **lee** la carpeta de información de partida con `harness-leer-entradas` y deja `.harness/entendimiento.md`/`.json` y `.harness/preguntas.md`; crea el esqueleto. |
| `migrar` | C, migración | Igual que `init` con la puerta de la partida C: lee el origen (`[origen] ruta`), deja el informe de entendimiento, `mejoras.md` (mejoras que no se aplican en la réplica) y `.harness/equivalencia/plantilla-casos.md`; imprime los pasos: replicar primero, `harness-mejoras.py nueva`, `harness-equivalencia.py`. |
| `update` | instancia instalada | Lee `harness.lock` y `.harness/estado.json` y actualiza lo del harness. Sin puerta de accesos (solo lectura local). |

Correr `init` o `migrar` sobre una instancia ya instalada equivale a `update`.

## Lectura de la información de partida (B y C)
Tras la puerta de accesos, `init --partida B` y `migrar` ejecutan el lector sobre la carpeta declarada (`[documentacion] carpeta` en B, `[origen] ruta` en C). **No escribe nada en esa carpeta** y rechaza una instancia que esté dentro de ella. Sin `--aplicar` el plan muestra qué entendió (entidades, motor propuesto, nº de preguntas). Si no hay nada legible (exit 2 del lector) se detiene con su mensaje y qué poner dónde. El informe es una **propuesta para validar**: el motor propuesto queda en `politicas.toml` solo como comentario «propuesto, por confirmar» y los ambientes siguen «por declarar». `preguntas.md` se crea una vez y no se reescribe; el informe se regenera si cambian las entradas y no lleva fechas ni rutas absolutas. Formatos y cómo preparar las hojas: `docs/ENTRADAS.md`.

## Puerta de accesos
Antes de planificar `adopt`, `init` y `migrar` se ejecuta `preflight-accesos.py` con la partida del modo. Si dice «no puede orquestar», el instalador se detiene, reproduce lo que falta y no escribe nada. El modo degradado (solo datos) exige `--aceptar-degradado` y deja `.harness/limites.md`. En partida A la política debe declarar ambientes: el harness no asume ninguno.

## Qué escribe (solo dentro de la carpeta de la instancia)
- Del harness, actualizables: `README.md`, `.gitignore`, `acceso.local.ejemplo.toml`, `README.md` de `conocimiento/`, `cambios/` y `documentacion/`.
- De la instancia, creados una vez y nunca tocados por `update`: `politicas.toml` (ambientes «por declarar»), `convenciones.toml` (valores del estándar), `mejoras.md`.
- Control: `harness.lock` (versión), `.harness/estado.json` (qué se instaló y su suma sha256), `.harness/piso.md` (lista de comprobación del piso, §7.2).

## `update`
Compara el hash del archivo en la instancia con el instalado. Si coincide, lo actualiza; si difiere, lo deja, lo reporta como `modificado-local` y muestra qué cambiaría. Un archivo del harness borrado se recrea; uno de la instancia borrado se reporta y no se recrea. No baja de versión.

## Piso (§7.2)
Cada corrida lista: especificación validada antes de codificar, almacén de documentación en `.md`, gate de calidad, indexación del código con actualización automática y estándar único; cada punto es «instalado», «pendiente» o «requiere confirmación». Las herramientas externas se muestran como pasos para la persona y **nunca se ejecutan**.

## Qué nunca hace
- No escribe sin `--aplicar`, ni fuera de la instancia, ni dentro del proyecto analizado si es otro.
- No usa la red, GitHub, `git` ni instala paquetes o herramientas.
- No guarda credenciales ni crea `acceso.local.toml`; no inventa ambientes.
- No pisa lo que la instancia modificó.
- Rechaza una instancia dentro de otro repositorio si no está declarada (sin `harness.lock`) y no se pasó `--aceptar-dentro-de-repo`; rechaza una dentro del propio harness.
- No guarda fechas: dos corridas iguales con `--aplicar` no cambian nada la segunda vez.

## Pruebas
`python3 -m unittest instalador/tests/test_instalar.py herramientas/tests/test_leer_entradas.py` y `bash -n instalador/instalar.sh`.

## Origen
Lo aporta la instancia del proyecto; el mapa de migración vive en la instancia (parametrizacion).
