# Montaje del entorno del proyecto

<!-- tipo: guia · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

`instalador/montaje.py` toma una instancia ya creada y deja el entorno del proyecto coherente con UN plan y confirmaciones agrupadas. Es el paso común de los tres puntos de partida.

## Flujo completo

| Partida | Cómo se crea la instancia | Luego |
|---|---|---|
| A, proyecto en proceso | `instalar.sh adopt` (informe de 8 dimensiones) y `instalar.sh init --partida A` | `montaje.py <instancia>` |
| B, desde cero | `instalar.sh init` (lee la información de partida) | `montaje.py <instancia>` |
| C, migración | `instalar.sh migrar` (lee el origen) | `montaje.py <instancia>` |

```
python3 instalador/montaje.py <instancia> [--agentes a,b | --detectar] [--aplicar] [--json] [--si] [--proyecto <carpeta>]
```

Sin `--aplicar` solo muestra el plan y no escribe nada. Con `--aplicar` escribe solo dentro de la instancia. `--si` salta únicamente las preguntas de bajo riesgo (qué agentes configurar y confirmar la escritura dentro de la instancia). Salida: 0 hecho o solo plan, 1 falló una verificación, 2 instancia o petición inválida.

Pasos: (1) lee `politicas.toml`, `convenciones.toml`, `harness.lock` y `.harness/estado.json`; sin ellos se detiene con un mensaje y exit 2. (2) Detecta los agentes del equipo sin asumir ninguno y pregunta cuáles configurar; `--agentes` genera para los nombrados aunque no se detecten y lo avisa. (3) Genera `AGENTS.md` y lo que cada adaptador confirma: skills, comandos, permisos, MCP solo con `registrar = "permitida"` y hooks de datos si la política los permite. (4) Comprueba la garantía independiente del agente (spec §22). (5) Verifica gate declarado, frescura, idempotencia y que nada salió de la instancia. (6) Escribe `.harness/montaje.md` y la clave `montaje` de `.harness/estado.json`.

## Qué instala

Solo archivos dentro de la instancia: `AGENTS.md`, los archivos de cada agente elegido, `.harness/montaje.md` y la clave `montaje` del estado. Es idempotente: sin cambios en la política, la segunda corrida deja el árbol idéntico (el informe no lleva fechas ni rutas absolutas). `instalar.sh update` regenera `estado.json` sin la clave `montaje`; basta repetir el montaje.

## Qué nunca instala

- Herramientas de búsqueda o indexación, ni cualquier paquete.
- El registro de un MCP en el agente, ni la configuración global del agente.
- Hooks de git, protección de ramas ni integración continua del proyecto: se leen (solo lectura) y lo que falta se imprime como paso con su comando.
- **Bases de datos**: el montaje nunca invoca clientes de base de datos, docker de bases, `aws` ni túneles, y no usa red, git ni `sudo`.

## Garantía real independiente del agente (spec §22)

Informa y lista como pendiente lo que falta: ambientes declarados (nunca se inventan; sin ellos los hooks quedan degradados), rol de solo lectura (`datos.rol_solo_lectura` o `rol_lectura` por ambiente en la política), hooks de git, integración continua (¿el flujo contiene el comando del gate?) y protección de ramas (siempre un paso para la persona, no se verifica sin red). Para mirar hooks y CI se indica `--proyecto`; sin él se busca un `.git` en los ancestros de la instancia.

## Acceso a datos (lo das tú)

La base de datos es la fuente de evidencia más fuerte del sistema y el montaje **no la instala**: cada proyecto accede a la suya de forma distinta. Sin tu acceso el entorno trabaja en modo degradado y no afirma nada sobre datos. Para darlo: declara los ambientes en `politicas.toml`, pon tu acceso personal en `acceso.local.toml` (no se versiona) y corre `python3 instalador/preflight-accesos.py --politica politicas.toml --acceso acceso.local.toml`.

Este bloque aparece SIEMPRE en la salida del plan y en `.harness/montaje.md`, también cuando todo salió bien, y en `pendiente` como entrada de tipo «requisito de la persona», que no cuenta como fallo del montaje. Si la política declara ambientes y existe `acceso.local.toml`, el montaje muestra un veredicto estático (qué método declaraste por ambiente, sin leer secretos y sin conectar a nada); si no, dice «sin comprobar». La conexión real la comprueba el preflight, que corres tú.

## Informe `.harness/montaje.md`

Secciones: Hecho · Degradado y por qué · Acceso a datos (lo das tú) · Pendiente de la persona (cada punto con su comando o paso exacto y su tipo, «paso de la persona» o «requisito de la persona»).

## Conexión con el asistente

Punto de integración: `montar(instancia, agentes=None, aplicar=False, preguntar=input, salida=print, sistema=None, si=False, proyecto=None, harness_raiz=None)`, que devuelve un diccionario con `hecho`, `degradado`, `pendiente` (cada uno con `tipo`), `plan`, `agentes_detectados`, `agentes_configurados`, `acceso_datos`, `verificacion` y `ok`. Lanza `ErrorMontaje` si no hay instancia válida. El asistente debe invocarlo tras `init`, `adopt` o `migrar`: primero sin `aplicar` para mostrar el plan, luego con `aplicar=True` pasando su propio `preguntar` para las confirmaciones agrupadas, y presentar `pendiente` a la persona. Esa conexión (en `cli/`) aún no existe.

## Pruebas

`python3 -B -m unittest instalador/tests/test_montaje.py`
