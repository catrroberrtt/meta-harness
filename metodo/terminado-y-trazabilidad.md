<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-08 · vence: 90d · fuente: método del repositorio (forma-de-trabajo.md) y comprobado con herramientas/harness-trazabilidad.py y su ejemplo -->

# «Terminado» y trazabilidad de punta a punta

Para que al crear algo nuevo no haya «correcciones» posteriores, el estándar existe **antes** de escribir código: cada cambio recorre la misma cadena, deja un rastro que se puede comprobar con un guion y no se cierra mientras quede un hueco. Este documento **suma** a `forma-de-trabajo.md` (no lo reemplaza) y a la definición de `terminado.criterios` de `convenciones/estandar.md`.

Quién lo usa: una empresa con estándar propio lo adopta pieza a pieza (cada plantilla es opcional y se puede mapear a sus formatos con tal de conservar los identificadores); el entorno centralizado lo trae completo; un proyecto nuevo lo usa desde el primer cambio.

## 1. Regla única

> **Nada se da por terminado sin que cada requisito tenga un criterio comprobable, una prueba, un commit y una evidencia; y lo que no se pudo verificar queda dicho como «no verificado», con el motivo.**

Un cambio vive en una carpeta de la instancia (`cambios/<fecha>-<slug>/`) con archivos de nombre fijo. Las plantillas están en `plantillas/`; un ejemplo completo y ejecutable, en `plantillas/ejemplos/cambio-ejemplo/`.

## 2. La cadena

| # | Etapa | Entra | Sale (archivo del cambio) | Quién | Puerta para pasar a la siguiente | Cómo se comprueba |
|---|---|---|---|---|---|---|
| 1 | Propuesta | Petición de una persona | `apertura.md` (`plantillas/apertura-de-cambio.md`) | Quien propone | Los cuatro puntos completos; fuera de alcance escrito | Lectura (humana) |
| 2 | Análisis | Apertura, conocimiento previo | `intake.md`, `reutilizacion.md` (`plantillas/intake.md`, `mapa-reutilizacion.md`); suposiciones y desafío en la especificación | Quien analiza | Ninguna suposición **abierta** sin dueño; mapa de reutilización aprobado | `harness trazar --etapa especificacion` (suposiciones) |
| 3 | Especificación (SDD) | Análisis | `especificacion.md` (`plantillas/especificacion.md`) | Quien especifica | Cada requisito (`RQ-NN`) con ≥1 criterio (`CA-NN.n`); cero palabras vagas sin resolver; **OK explícito** marcado | `harness trazar --etapa especificacion` |
| 4 | Delegación | Especificación aprobada | `delegacion.md` (`plantillas/delegacion.md`), `plan.md`, `manifiesto.md` | Quien coordina | Cada tarea con encargado, requisitos, archivos que escribe, entrega y aceptación; ningún solape de archivos; todo requisito asignado | `harness trazar --etapa delegacion` |
| 5 | Implementación | Tarea delegada | Código, pruebas, filas de la matriz en `pendiente`/`implementado` | Encargado | Cada fila de la matriz apunta a su prueba y su commit | `harness trazar --etapa implementacion` |
| 6 | Revisión | Entrega | Informe en dos etapas (§6) | Alguien **distinto** del implementador | Etapa 1 sin refutaciones; etapa 2 sin bloqueantes | Revisión (humana o `plantillas/informe-revisor.md`) |
| 7 | Verificación | Código revisado | Evidencia (gate con código de salida, consultas con datos) enlazada en la matriz | Quien verifica | Toda fila `verificado` o `no-verificado` con motivo | `harness trazar --etapa cierre` |
| 8 | Cierre | Matriz completa | `cierre.md` (`plantillas/cierre-de-cambio.md`) | Quien cierra | Cero casillas sin marcar; cada N/A con motivo | `harness trazar --etapa cierre` |

Cada etapa corresponde a una skill del ciclo (`plantillas/skills/sdd-*`): 1–3 a `sdd-especificar`, 4 a `sdd-planificar`, 5 a `sdd-implementar`, 6–8 a `sdd-verificar`. Las puertas no se saltan; las aprobaciones por fase de `forma-de-trabajo.md` §4–5 siguen en pie.

## 3. Especificación con identificadores

- **Requisito** `RQ-NN`: una frase con disparador y respuesta («Cuando … el sistema …», «Mientras … el sistema …», «Si … el sistema …»). Los no funcionales también son `RQ` y empiezan por `[no funcional]`.
- **Criterio de aceptación** `CA-NN.n`: pertenece a su requisito y se escribe en forma Dado / Cuando / Entonces con un **resultado observable** (una cifra, un estado, un código). Palabras como «rápido», «fácil», «adecuado» o «etc.» se resuelven con un número o se convierten en pregunta abierta.
- **Suposición** `SU-NN` con nivel: `establecido` (verificado, se trata como premisa), `de-trabajo` (se usa como valor por defecto y se avisa al desviarse) o `abierto` (se pregunta antes de decidir). Lo **reconstruido** de un sistema existente (modo `adopt`) entra como `de-trabajo` hasta que una persona lo confirme. Una suposición `abierta` no puede acompañar un cierre.
- **Desafío previo** (cambios M y L): tres líneas — cómo falla esto, qué suposición lo rompería, qué se haría entonces. Dos modos bastan: *pre-mortem* (imaginar que ya falló) y *contraargumento* (la mejor alternativa descartada y por qué).
- **Aprobación**: una casilla `- [x] OK explícito de <persona> (<fecha>)`. Sin ella, la delegación no puede empezar.

## 4. Delegación con contrato de archivos

Delegar (a una persona, a un subagente o a uno mismo en otra fase) exige un contrato, no una frase:

| Campo | Qué dice |
|---|---|
| Tarea | Qué se encarga, en una línea |
| Encargado | Quién o qué lo hace |
| Requisitos | Los `RQ-NN` que cumple |
| Escribe | Archivos o carpetas que **puede** crear o modificar (rutas relativas; sin `..` ni rutas absolutas) |
| No toca | Lo que no debe modificar aunque lo vea |
| Entrega | Qué devuelve y dónde |
| Aceptación | Cómo se sabe que está bien (el `CA-NN.n` o el comando) |
| Reversa | Cómo se deshace (opcional si no hay datos ni despliegue) |
| Estado | `pendiente` · `en-curso` · `entregada` · `aceptada` · `rechazada` |

Reglas: dos tareas no escriben el mismo archivo salvo que ambas lo marquen `(compartido)` y se diga quién integra; el encargado no recibe datos reales ni credenciales que el contrato no nombre; las tareas mecánicas ya identificadas pueden ir a un modelo menor (`forma-de-trabajo.md` §11); tras la entrega, quien coordina **verifica por su cuenta** antes de pasar a `aceptada`.

## 5. Matriz de trazabilidad

Tabla en `matriz.md` con una fila por par requisito–criterio:

| Requisito | Criterio | Prueba | Rojo→verde | Commit | Evidencia | Estado | Nota |
|---|---|---|---|---|---|---|---|

- **Prueba**: ruta del archivo de prueba, opcionalmente `::nombre del caso`.
- **Rojo→verde**: `sí` si se vio fallar la prueba antes del cambio y pasar después (obligatorio declararlo en correcciones de errores), `no` o `n/a`.
- **Commit**: uno o varios hashes del repositorio.
- **Evidencia**: archivo (salida del gate con código de salida, consulta con su resultado, captura) o enlace completo.
- **Estado**: `pendiente`, `implementado`, `verificado` o `no-verificado` (esta última exige la **Nota** con el motivo y qué lo destrabaría).

Se leen cuatro preguntas de la matriz, y la herramienta responde las cuatro: ¿hay un requisito **sin prueba**? ¿hay una prueba **sin requisito**? ¿hay una especificación **sin criterios**? ¿hay una tarea delegada **sin contrato de archivos**?

## 6. Revisión en dos etapas

1. **Conformidad con la especificación.** Quien revisa recorre la matriz: ¿el código hace lo que dice cada criterio, ni más ni menos? Se contrasta con el diff, no con el relato de quien implementó. Si hay incumplimientos, vuelve a implementación y **no se pasa a la etapa 2**.
2. **Calidad.** Patrones de calidad del ámbito del diff, seguridad (permisos, datos personales, secretos), rendimiento, legibilidad, pruebas que fallarían si el código se rompiera.

Para texto que se publica (PR, ticket, página) sigue vigente el revisor independiente de `plantillas/informe-revisor.md`.

## 7. Lista de cierre «nunca se escapa algo»

`cierre.md` trae la lista completa (`plantillas/cierre-de-cambio.md`). Qué comprueba el guion y qué queda a una persona:

| Punto | Lo comprueba |
|---|---|
| Especificación aprobada antes de codificar | Guion (casilla de OK) |
| Cada requisito con criterio, prueba, commit y evidencia | Guion |
| Los commits y archivos citados existen | Guion con `--repo` (local, sin red) |
| Suposiciones abiertas | Guion |
| Tareas delegadas aceptadas | Guion |
| Cero casillas sin marcar, cada N/A con motivo | Guion |
| Gate ejecutado, con código de salida pegado | Persona (el guion exige el archivo de evidencia) |
| Revisión de dos etapas hecha por otra persona | Persona |
| Capas completas, documentación y tickets al día con enlaces completos | Persona |
| Cifras verificadas con datos o declaradas no verificadas | Persona |
| Lección registrada (`aprendizaje.md`) o N/A con motivo | Persona |
| Procesos apagados y datos de prueba limpiados | Persona |

## 8. Límites

La herramienta comprueba que el rastro **existe y es coherente**; no que la prueba sea buena ni que el criterio sea correcto: eso es la revisión. Lo que el guion no pudo comprobar lo dice («no comprobado: falta `--repo`»). Una matriz completa con pruebas malas sigue siendo un cierre malo; por eso la etapa 1 de revisión la hace otra persona.
