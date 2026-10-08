<!-- tipo: guia -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: spec §14 y requisitos R20, R25, R26 -->
# Frescura: nada desactualizado en ninguna parte

Cada parte del harness tiene un mecanismo que la mantiene al día y una comprobación que lo demuestra.

| Parte | Cómo se mantiene al día | Comprobación |
|---|---|---|
| Documentos del harness | cada documento declara `revisado` (fecha) y `fuente` (qué lo respalda) y vence a los N días | `harness-frescura` lo marca; la integración continua no libera una versión con vencidos |
| Estándares frente a la realidad | el minero vuelve a medir los proyectos observados y marca divergencias o prácticas nuevas | informe periódico |
| Instancia frente al harness | `harness.lock` + `update` avisa de versiones nuevas y qué cambió; cada instancia decide cuándo subir | prueba de `update` |
| Documentos de la instancia frente al código | sellos `verificado-contra-git` | lint de la instancia |
| El propio instalador | comprueba su versión y la de `harness.lock` al arrancar; sus autopruebas corren en la integración continua | `instalador/comprobar-version.py` |
| Hooks y políticas | se regeneran desde la política cuando cambia el harness o la política | baterías de pruebas |
| Conocimiento aprendido | el flujo de aportes sigue entrando; un aporte sin revisar vence | cola de aportes |

## Cabecera de frescura de un documento
Junto a la línea `<!-- tipo: … -->`:

    <!-- revisado: AAAA-MM-DD · vence: 90d · fuente: <qué lo respalda> -->

- `revisado`: la última vez que alguien comprobó que el contenido sigue siendo cierto (no la última edición).
- `vence`: días de validez desde `revisado` (`90d` por defecto).
- `fuente`: lo que lo respalda (otro documento, un código, una medición, una decisión). Sin fuente, el aviso es «sin fuente».

`python3 herramientas/harness-frescura.py [raiz] [--hoy AAAA-MM-DD] [--json] [--tolerar-sin-cabecera]` es de solo lectura y reporta sin cabecera, vencidos, sin fuente y por vencer (14 días). Sale con 1 si hay vencidos o sin cabecera; `--tolerar-sin-cabecera` es solo para la transición mientras se añaden las cabeceras. Para renovar un documento: releerlo contra su fuente, corregir lo que cambió y actualizar `revisado`.

## Cabecera de versión de la instancia: `harness.lock`
Archivo TOML en la raíz de la instancia:

    version = "X.Y.Z"
    fuente  = "<url-o-ruta del harness>"

`python3 instalador/comprobar-version.py [--harness RUTA] [--instancia RUTA] [--json]` compara `VERSION` con la última etiqueta local de git y con el `harness.lock`, e informa: al día; la instancia fija una versión anterior (con los commits de por medio si hay git); `harness.lock` inválido; o instancia sin `harness.lock` (indica cómo crearlo, sin crearlo). No usa la red; consultar la fuente remota queda pendiente.

## Verificación completa
`./verificar.sh` encadena sintaxis de shell, compilación de Python, pruebas, frescura y el escaneo de referencias prohibidas (lista opcional en `.prohibidos.txt`). La integración continua lo ejecuta en cada push y pull request.
