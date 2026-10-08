# Comando `harness` (asistente de terminal)

<!-- tipo: herramienta · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Un solo comando, con asistente guiado (spec §20). Biblioteca estándar de Python 3.11+, sin red. La lógica está en `harness_cli.py`; el instalador, el preflight, la comprobación de versión, el detector y la frescura **se ejecutan**, no se reimplementan.

| Comando | Qué hace |
|---|---|
| `harness` | Asistente: mira la carpeta, detecta el caso, pregunta lo justo, muestra el plan y pide confirmación |
| `harness instalar <instancia>` | Carpeta local: delega en el instalador (solo plan; `--aplicar` escribe). Repositorio (`https://`, `ssh://`, `git@host:ruta` u `owner/nombre` → `git@github.com:owner/nombre.git`, avisando): usa `instalador/instalar-instancia.py`; comprueba el acceso **antes de clonar**, muestra el plan, pide confirmación (o `--si`), clona (`--destino`) y corre `update`. Sin acceso: exit 3 y qué pedir y a quién, sin crear nada; si falta llave o sesión imprime (sin ejecutarlo) `acceso-github.sh`. Una `usuario:token@` en la URL se descarta y no se muestra. `DESCARGADORES` sigue como punto de extensión para otros orígenes |
| `harness update [instancia]` | Plan de `update` (con `--aplicar`, lo escribe) |
| `harness doctor [instancia]` | Versión del harness y de `harness.lock`, frescura de documentos, herramientas (`git`, `python3` requeridas; `gh`, `ssh`, `node` solo informadas) y accesos locales con aspecto de secreto o versionados. Exit 0 si todo bien, 1 si hay problemas (con la acción sugerida) |
| `harness estado [instancia]` | Modo, versión, qué hay instalado, qué cambió después y qué quedó pendiente del piso |

## El asistente
1. **Qué miré:** cuenta código, manifiestos, SQL, hojas, documentos, `.git` con su historial y un origen declarado (carpeta `origen/` o `[origen] ruta`). Concluye A (hay código, base o historial), B (carpeta vacía o casi vacía, o solo documentos) o C (origen declarado). Si duda (p. ej. solo hay SQL u hojas), **lo pregunta** con su mejor suposición.
2. **Una pregunta por vez**, cada una con «Se intentó: …». Preguntas: caso (si duda), entradas (B/C), carpeta de la instancia, acceso y política (A), notas (opcional).
3. **Qué entendí / qué falta / qué haré**, el **preflight de accesos**, y si no puede orquestar se detiene diciendo qué pedir y a quién (salida 2).
4. El **plan del instalador** (sin escribir) y **«¿Lo aplico? [s/N]»**. Solo «s» (o «si») ejecuta con `--aplicar`.

En A el primer paso es `adopt` (informe «cómo es este proyecto»); al volver a correr `harness` con ese informe presente, instala el esqueleto (`init --partida A`). Si la carpeta ya tiene `harness.lock`, hace `update`.

## Retomar y cortes
El avance (paso y respuestas) se guarda en `<instancia>/.harness/sesion.json` apenas se elige la instancia. Ctrl-C o fin de entrada no instalan nada; al volver ofrece continuar. **Nunca se guardan secretos:** una respuesta que parece secreto (contraseña, token, URL con clave…) se descarta y se avisa. Lo único que se escribe antes de la confirmación es ese archivo; antes de elegir la instancia no se escribe nada. Las carpetas de entradas y el proyecto analizado nunca se tocan.

## Sin interfaz (R45)
`--si` aplica el plan; `--json` imprime un solo JSON; `--no-interactivo` no pregunta. Si la entrada no es una terminal y no hay `--si`, muestra el plan y sale con 0 **sin escribir** (tampoco guarda sesión). Si el caso es dudoso no adivina: exige `--caso A|B|C` (salida 2). Banderas: `--carpeta --caso --instancia --acceso --politica --documentacion --origen --aceptar-degradado --aceptar-dentro-de-repo --harness`.

## Salida
Texto plano. Hay color solo si la salida es una terminal, `TERM` no es `dumb` y no existe `NO_COLOR`. Códigos: 0 bien · 1 problema/error · 2 detenido (falta algo; el mensaje dice qué) · 130 interrumpido.

## Pruebas
`python3 -m unittest cli/tests/test_cli.py` (usa carpetas temporales; el `input()` se inyecta).
