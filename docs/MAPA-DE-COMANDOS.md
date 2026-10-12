<!-- tipo: guia · capa: 4 -->
<!-- revisado: 2026-10-09 · vence: 90d · fuente: cli/harness_cli.py y sus pruebas (cli/tests/test_interfaz.py); cada comando se ejecutó -->

# Qué comando uso cuándo

Una sola entrada, `harness`. La misma ayuda sale con `harness -h` o `harness ayuda` (el mapa por momentos va primero y las opciones técnicas del asistente, después). Regla común: **nada se escribe sin `--aplicar` o sin que respondas «s»**; los comandos de lectura (`estado`, `doctor`, `siguiente`, `trazar`) nunca escriben.

## 1. Por momento

| Momento | Quiero… | Comando | ¿Escribe? |
|---|---|---|---|
| 1 · Instalar | Replicar en una máquina nueva la instancia de mi equipo | `harness instalar owner/nombre` (primero `--plan` si quiero solo mirar) | Sí, tras confirmar |
| 2 · Adoptar | Entrar a un proyecto que ya existe **sin tocar su código ni su estándar** | `harness` (el asistente detecta el caso A) o `harness instalar <instancia> --modo adopt --proyecto <carpeta>` | `adopt` deja el informe en la instancia, nunca en el proyecto |
| 3 · Empezar | Arrancar un proyecto nuevo (caso B) o replicar un sistema (caso C) | `harness` o `harness instalar <instancia> --modo init` / `--modo migrar` | Sí, tras confirmar |
| 3c · Usar un ERP estándar (estado D) | Saber qué módulos del ERP necesita mi negocio, a partir de mis documentos | `harness erp --negocio <carpeta> --erp-base <ruta> [--instancia <carpeta>]` (`docs/OPCION-ERP.md`) | Solo con tu «s» o `--aplicar`, y solo en la instancia; no instala nada del ERP |
| 3b · Preparar agentes | Dejar listos `AGENTS.md`, skills y permisos de mi agente | `harness montar <instancia>` (plan) y luego `--aplicar` | Solo con `--aplicar`, solo dentro de la instancia |
| 4 · Trabajar | Saber **dónde estoy y qué sigue** | `harness siguiente [instancia]` | No |
| 4 · Trabajar | Comprobar que un cambio no dejó huecos (requisito sin prueba, tarea sin contrato…) | `harness trazar <cambio> [--etapa E] [--repo <proyecto>]` | No |
| 5 · Verificar | Ver si el entorno está sano (versión, frescura, herramientas, secretos) | `harness doctor [instancia]` | No |
| 5 · Verificar | Ver qué hay instalado y qué falta del piso | `harness estado [instancia]` | No |
| 6 · Actualizar | Traer la versión nueva del harness a mi instancia | `harness update [instancia]` (plan) y luego `--aplicar` | Solo con `--aplicar`; no pisa lo que cambiaste |
| 7 · Aprender | Que lo aprendido en un proyecto (por ejemplo, el ERP central) llegue a los siguientes | `harness aprender fuentes agregar erp-base <ruta> --tipo erp` y luego `harness aprender escanear` | Solo la cola local; promover escribe con `--aplicar` y nunca sube |

## 2. Según dónde estás

El orden importa: cada paso deja listo el siguiente, y `harness siguiente` te dice cuál toca.

### A. Entorno de una empresa que ya tiene su estándar (proyecto existente)
Tu estándar manda: el harness lo **lee y lo respeta**; lo nuevo se ofrece, no se impone.
1. `harness instalar owner/instancia` (máquina nueva) o `harness` en la carpeta del proyecto.
2. `harness instalar <instancia> --modo adopt --proyecto <carpeta>`: lee stack, convenciones, pruebas y CI y escribe el informe «cómo es este proyecto» en la **instancia**. Validarlo con el equipo.
3. Tus convenciones viven en `convenciones.toml` de la instancia (se parte de `convenciones/estandar.md` y se sobrescribe clave por clave).
4. `harness montar <instancia>` → `--aplicar`.
5. Por cada tarea: `plantillas/especificacion.md` → `harness trazar … --etapa especificacion` … → `--etapa cierre`. Si ya numeras requisitos con otra clave (por ejemplo la de tu tracker), déjala como alias dentro del texto del requisito (`RQ-01 · [CLAVE-123] …`): la herramienta exige el patrón `RQ-NN` / `CA-NN.n`, no admite otro.
6. `harness doctor` y `harness update` cuando salga una versión.

### D. Negocio que usará un ERP estándar (opción ERP)
1. `harness erp --negocio <carpeta-de-documentos> --erp-base <ruta-del-erp>`: lee los documentos (archivos locales), muestra la propuesta con el **estado real** de cada módulo y lo que aún no existe. No escribe.
2. Con `--instancia <carpeta>` te pregunta y deja `erp/propuesta-erp.md` y `.json` y el cambio `cambios/erp-composicion/` (especificación y matriz).
3. Revisa la propuesta, confirma o quita módulos, resuelve las suposiciones abiertas y comprueba con `harness trazar cambios/erp-composicion --etapa especificacion`. La composición real la hará el compositor del ERP (aún sin código): contrato en `docs/OPCION-ERP.md`.
4. Si habla de sitio web: el adaptador `diseno-web` (se ofrece, no se ejecuta).

### B. Entorno centralizado (este repositorio)
1. `bash verificar.sh` antes de cada commit: sintaxis, pruebas de herramientas, instalador, CLI y adaptadores, frescura y referencias prohibidas.
2. `harness doctor` (sin instancia): versión y frescura del propio harness.
3. Una lección de una instancia sube con `python3 herramientas/harness-aportar.py` (ver `metodo/aprendizaje.md`); un documento nuevo entra solo si pasa la medición.
4. Cambio de capacidad: sube `VERSION` (menor) y actualiza la documentación enlazada desde `README.md`.

### C. Proyecto nuevo
1. `harness` (el asistente detecta B o C y pregunta lo justo) o `harness instalar <instancia> --modo init`.
2. `harness montar <instancia>` → `--aplicar`.
3. **Desde el primer cambio**: especificación con identificadores → delegación con contrato → matriz → cierre (`metodo/terminado-y-trazabilidad.md`). Si el estándar existe desde el día uno, no hay correcciones posteriores que hacer.
4. `harness siguiente` cuando dudes del paso.

## 3. Fuera de `harness`: herramientas sueltas

Se ejecutan con `python3 herramientas/<nombre>.py -h`. Las que más se usan:

| Quiero… | Herramienta |
|---|---|
| Comprobar la trazabilidad de un cambio (lo mismo que `harness trazar`) | `harness-trazabilidad.py` |
| Ver cómo es un proyecto existente | `harness-detectar.py` |
| Ver qué documentos vencieron | `harness-frescura.py` |
| Cotejar una réplica o migración contra el origen | `harness-equivalencia.py` |
| Registrar una mejora que no se aplica ahora | `harness-mejoras.py` |
| Decidir si una lección sube al harness | `harness-aportar.py` |

## 4. Códigos de salida

`0` bien · `1` problema o error (doctor, estado de algo que no es instancia, trazabilidad con errores) · `2` detenido: falta algo y el mensaje dice qué (accesos, argumentos, carpeta inexistente) · `130` interrumpido con Ctrl-C.

## 5. Si algo no sale

| Síntoma | Qué hacer |
|---|---|
| `no existe el comando «x»` | El mensaje propone el más parecido; la lista completa está en `harness ayuda` |
| `falta indicar: instancia` | Cada comando trae ejemplos en `harness <comando> -h` |
| `no es una instancia instalada` | Estás fuera de la instancia: pasa su carpeta, o corre `harness` para armarla |
| `NO PUEDE ORQUESTAR` | Falta un acceso declarado; el mensaje dice qué pedir y a quién. Nada se escribió |
| `harness trazar` falla con `T0x` / `T4x` | Cada código tiene su causa en el mensaje y su regla en `metodo/terminado-y-trazabilidad.md` |
