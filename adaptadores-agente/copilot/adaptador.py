#!/usr/bin/env python3
"""Adaptador de GitHub Copilot: AGENTS.md (ya lo lee) + hooks `preToolUse` en `.github/hooks/*.json`, uno por superficie.

Copilot son TRES superficies que comparten archivos pero no comportamiento (copilot/FORMATO.md, «Hallazgo estructural»):
  VS Code, arnés Local (Preview)   `.github/hooks/harness-vscode.json`  `PreToolUse` PascalCase, SIN `version`, `command`/`timeout`;
                                    `matcher` se IGNORA (filtra el script) y falla ABIERTO ante errores
  Copilot CLI y Agent Host de VS Code  `.github/hooks/harness-cli.json`  `version: 1`, `preToolUse`, `bash`/`timeoutSec`; falla CERRADO
                                    ante errores, pero el TIEMPO AGOTADO siempre deja pasar

Cómo se elige (el marco no pasa opciones a `generar`; la superficie es el NOMBRE del adaptador):
  --agentes copilot          (por defecto) genera ambos archivos
  --agentes copilot-vscode   solo el arnés Local de VS Code
  --agentes copilot-cli      solo CLI y Agent Host
Solo `copilot` se detecta solo.

El control por hook queda SIEMPRE «degradado»: Preview en VS Code, falla abierto en Local y tiempo agotado que deja pasar en la CLI; no se
promete barrera. El script deniega él mismo ante cualquier error propio. Si la política no permite generar el hook, no se escribe ningún
archivo de hook.

Genera SOLO dentro de la instancia y SOLO lo «confirmado con fuente»:
  .github/hooks/harness-vscode.json | harness-cli.json   registro del hook (la marca va como comentario de shell dentro del comando: JSON no admite comentarios)
  .github/harness-hooks/*                                hook de datos generado por `instalador/generar-politicas.py` + puente + un lanzador por superficie
                                                         (fuera de `.github/hooks/`, que solo lee `*.json`)
  .github/skills/<n>/SKILL.md                            skills neutrales; los comandos neutrales también van como skill con `disable-model-invocation: true`
                                                         (un skill funciona como comando con `/nombre`; los `.prompt.md` están obsoletos para el Agent Host)
  .vscode/mcp.json | .mcp.json                           `servers` (VS Code, `type: stdio|http`) y/o `mcpServers` (CLI y Agent Host, `type: local|http`), solo
                                                         `registrar = "permitida"` y sin variables de entorno (la referencia a variables no está confirmada)
NO genera `.github/copilot-instructions.md`: Copilot ya lee AGENTS.md y las fuentes de instrucciones se SUMAN (sin precedencia garantizada), así que
repetir el contenido en otro archivo lo duplicaría. Tampoco `chat.tools.terminal.autoApprove: false` (solo exige aprobación, NO bloquea), ni subagentes.
Permisos: `--deny-tool` de la CLI son banderas, no un archivo: se imprimen como paso para la persona (`ask` es el comportamiento por defecto de la CLI,
no hace falta bandera). MCP con `registrar = "confirmar"` (por defecto) no escribe nada y se imprime el fragmento; `"prohibida"` no escribe nada y avisa.
Lo global se imprime como paso para la persona.
"""
import json
import re
import sys
import tomllib
from pathlib import Path

AQUI = Path(__file__).resolve().parent
NUCLEO = AQUI.parent / "nucleo"
if str(NUCLEO) not in sys.path:
    sys.path.insert(0, str(NUCLEO))
import fuente_neutral as fn  # noqa: E402
import generar_agentes as ga  # noqa: E402
import guardia_hook as gh  # noqa: E402

RUTA_HOOKS = ".github/harness-hooks"
RUTA_SKILLS = ".github/skills"
MAX_NOMBRE_SKILL = 64
MAX_DESCRIPCION_SKILL = 1024
FUENTE_CP = "MATRIZ.md y copilot/FORMATO.md"
AVISO_FALTA_LANZADOR = "guardia de datos: no se encontro el lanzador; se bloquea por precaucion"

VARIANTES = {
    "vscode": {"formato": "copilot-local", "json": ".github/hooks/harness-vscode.json", "lanzador": "lanzar-vscode.sh", "superficie": "VS Code (arnés Local)"},
    "cli": {"formato": "copilot-cli", "json": ".github/hooks/harness-cli.json", "lanzador": "lanzar-cli.sh", "superficie": "Copilot CLI y Agent Host"},
}
MCP = {"vscode": {"ruta": ".vscode/mcp.json", "clave": "servers", "local": "stdio", "con_tools": False},
       "cli": {"ruta": ".mcp.json", "clave": "mcpServers", "local": "local", "con_tools": True}}


def comando_hook(lanzador):
    """Una línea de shell: busca la raíz con git (o el directorio actual) y, si falta el lanzador, deniega ELLA MISMA (salida 2).

    Lleva la marca del harness como comentario de shell al final (es lo que reconoce `es_generado`)."""
    ruta = f"{RUTA_HOOKS}/{lanzador}"
    return (f'd=$(git rev-parse --show-toplevel 2>/dev/null) || d=.; l="$d/{ruta}"; '
            f'if [ -f "$l" ]; then exec sh "$l"; fi; echo \'{AVISO_FALTA_LANZADOR}\' >&2; exit 2 # {fn.MARCA}')


def hooks_vscode():
    """`.github/hooks/harness-vscode.json` (FORMATO.md §3A): sin `version`; `PreToolUse[]` con `type`, `command`, `timeout` (segundos). Sin `matcher` (se ignora)."""
    doc = {"hooks": {"PreToolUse": [{"type": "command", "command": comando_hook(VARIANTES["vscode"]["lanzador"]), "timeout": 30}]}}
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def hooks_cli():
    """`.github/hooks/harness-cli.json` (FORMATO.md §3B): `version: 1`; `preToolUse[]` con `type`, `bash`, `timeoutSec`."""
    doc = {"version": 1, "hooks": {"preToolUse": [{"type": "command", "bash": comando_hook(VARIANTES["cli"]["lanzador"]), "timeoutSec": 30}]}}
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def _prefijos_exceptuados(ruta_politica):
    """Prefijos de `datos.comandos` que la política permite en el ambiente de escritura: una denegación fija no admite excepciones, así que no se traducen."""
    try:
        datos = tomllib.loads(Path(ruta_politica).read_text(encoding="utf-8")).get("datos") or {}
    except (OSError, tomllib.TOMLDecodeError):
        return set()
    out = set()
    for c in datos.get("comandos") or []:
        if isinstance(c, dict) and c.get("permitida_en_ambiente_de_escritura"):
            out.update(fn.cc.prefijos_literales(c.get("regex"))[0] or [])
    return out


def permisos_traducibles(fuente):
    """(deny, ask, no_traducible): prefijos literales ya validados por el núcleo; sin los exceptuados por ambiente. `allow` no se traduce."""
    perm = fuente.get("permisos") or {}
    exc = _prefijos_exceptuados(fuente["politica_ruta"])
    deny = [x for x in perm.get("deny") or [] if x not in exc]
    extra = [{"origen": (perm.get("origenes") or {}).get(x, "datos.comandos"), "regla": x,
              "motivo": "la política la permite en el ambiente de escritura y `--deny-tool` no admite excepciones; la juzga el hook de datos"}
             for x in perm.get("deny") or [] if x in exc]
    return deny, list(perm.get("ask") or []), list(perm.get("no_traducible") or []) + extra


def ejemplo_deny_tool(prefijos):
    """Banderas `--deny-tool` de la CLI (FORMATO.md §7): la denegación prevalece incluso con `--allow-all`."""
    partes = [f"--deny-tool='shell({p})'" for p in prefijos] or ["--deny-tool='shell(<prefijo del comando que quieras prohibir>)'"]
    partes += ["--deny-tool='read(.env)'", "--deny-tool='write(.env)'"]
    return "copilot " + " ".join(partes)


def skill_con_marca(texto):
    """SKILL.md con la marca como comentario HTML tras la cabecera; si la cabecera es tan larga que la marca queda fuera de los 800 caracteres
    que mira `es_generado`, va como comentario YAML dentro de ella (la regeneración sigue reconociéndolo)."""
    if fn.MARCA in texto:
        return texto
    m = re.match(r"\A(---\r?\n)(.*?\r?\n---\r?\n)(.*)\Z", texto, re.S)
    if not m:
        return f"<!-- {fn.MARCA} -->\n{texto}"
    r = f"{m.group(1)}{m.group(2)}<!-- {fn.MARCA} -->\n{m.group(3)}"
    if not fn.es_generado(r):
        r = f"{m.group(1)}# {fn.MARCA}\n{m.group(2)}{m.group(3)}"
    return r


def comando_como_skill(c):
    """(SKILL.md, None) o (None, motivo): el comando neutral como skill de invocación manual (`disable-model-invocation: true`, FORMATO.md §5)."""
    if len(c["nombre"]) > MAX_NOMBRE_SKILL or len(c["descripcion"]) > MAX_DESCRIPCION_SKILL:
        return None, f"supera los límites de un skill ({MAX_NOMBRE_SKILL} caracteres de nombre y {MAX_DESCRIPCION_SKILL} de descripción)"
    m = re.match(r"\A---\r?\n.*?\r?\n---\r?\n?(.*)\Z", c["contenido"], re.S)
    cuerpo = (m.group(1) if m else c["contenido"]).replace("\r\n", "\n").lstrip("\n")
    cab = f"---\nname: {c['nombre']}\ndescription: {json.dumps(c['descripcion'], ensure_ascii=False)}\ndisable-model-invocation: true\n---\n"
    return skill_con_marca(cab + cuerpo), None


def entrada_mcp(s, variante):
    """(dict del servidor, None) o (None, motivo). VS Code: `type` `stdio`|`http`. CLI: `type` `local`|`http` y `tools` (FORMATO.md §6).

    Variables de entorno: la única referencia citada es `inputs`/`${input:id}` de VS Code sin la forma de la entrada, y `${env:...}` en la CLI no está
    confirmado: un servidor con `entorno` no se traduce (nunca se escribe un valor). Los remotos con `entorno` tampoco."""
    if s["entorno"]:
        return None, "la referencia a variables de entorno no está confirmada en copilot/FORMATO.md §6 (`${input:id}` sin la forma de `inputs`; `${env:...}` en la CLI «no se pudo confirmar»)"
    cfg = MCP[variante]
    if s["tipo"] == "remoto":
        e = {"type": "http", "url": s["url"]}
    else:
        e = {"type": cfg["local"], "command": s["comando"]}
        if s["args"]:
            e["args"] = list(s["args"])
    if cfg["con_tools"]:
        e["tools"] = ["*"]
    return e, None


def config_mcp(variante, servidores):
    return json.dumps({"_generado_por_el_harness": fn.MARCA, MCP[variante]["clave"]: servidores}, ensure_ascii=False, indent=2) + "\n"


class Copilot(ga.Adaptador):
    nombre = "copilot"
    codigo_matriz = "CP"
    comandos = ("copilot",)
    carpetas_home = (".copilot",)
    variantes = ("vscode", "cli")
    hook_generado = False

    def capacidades(self):
        caps = super().capacidades()
        genera = {"Instrucciones del proyecto": "AGENTS.md lo genera el núcleo; Copilot lo lee sin configuración; no se genera `.github/copilot-instructions.md` (las fuentes se suman y se duplicaría)",
                  "Hooks que bloquean": "`.github/hooks/harness-vscode.json` (Local, Preview) y/o `harness-cli.json` (CLI y Agent Host), solo si la política lo permite; queda «degradado»",
                  "Skills": "`.github/skills/<nombre>/SKILL.md` con las skills neutrales (marca en un comentario HTML tras la cabecera)",
                  "Comandos propios": "los comandos neutrales se generan como skill de invocación manual (`disable-model-invocation: true`), la vía recomendada; no se generan `.prompt.md` (obsoletos para el Agent Host)",
                  "MCP": "`.vscode/mcp.json` (`servers`) y/o `.mcp.json` (`mcpServers`) solo con `registrar = \"permitida\"` y sin variables de entorno; con `confirmar` se imprime el fragmento como paso"}
        for k, v in caps.items():
            v["generado_por_este_adaptador"] = k in genera
            v["nota"] = genera.get(k, "no lo genera este adaptador (la fuente neutral aún no lo produce); no se promete")
        caps["Reglas por ruta"]["nota"] = ("`.github/instructions/*.instructions.md` con `applyTo` está confirmado (FORMATO.md §2), pero la fuente neutral no tiene reglas por ruta: no se genera")
        caps["Permisos / modos / sandbox"]["nota"] = ("`chat.tools.terminal.autoApprove: false` solo exige aprobación y NO bloquea: no se usa como control; "
                                                      "`--deny-tool` de la CLI sí gana siempre (son banderas, no un archivo): los permisos `deny` neutrales se imprimen como paso para la persona")
        return caps

    def generar(self, fuente, destino, aplicar=False):
        self.avisos, self.pasos = [], []
        self.control_hook_estado = self.control_hook_motivo = None
        self.hook_generado = False
        self.no_traducible, self.comandos_omitidos, self.mcp_estado = [], [], {}
        plan = []
        elegidas = [VARIANTES[v] for v in self.variantes]

        if self.estado_hooks() not in ("si", "parcial"):
            archivos, motivo = [], f"la matriz no confirma hooks que bloquean para Copilot (estado «{self.estado_hooks()}»)"
        else:
            archivos, motivo = [], None
            vistos = set()
            for v in elegidas:
                lista, motivo = gh.archivos_de_hook(fuente, lanzador=v["formato"])
                for nombre, contenido, modo in lista:
                    nombre = v["lanzador"] if nombre == gh.LANZADOR else nombre
                    if nombre not in vistos:
                        vistos.add(nombre)
                        archivos.append((nombre, contenido, modo))
        if archivos:
            self.hook_generado = True
            for nombre, contenido, modo in archivos:
                plan.append(fn.planificar_archivo(destino, f"{RUTA_HOOKS}/{nombre}", contenido, modo=modo, respetar_manual=True))
            for v in elegidas:
                plan.append(fn.planificar_archivo(destino, v["json"], hooks_vscode() if v["formato"] == "copilot-local" else hooks_cli()))
            self.control_hook_estado = "degradado"
            self.control_hook_motivo = ("hook `preToolUse` generado desde la política, pero sin barrera: en VS Code Local es Preview, ignora `matcher` y FALLA ABIERTO; en la CLI y el Agent Host "
                                        "cierra ante errores pero el TIEMPO AGOTADO siempre deja pasar; solo vigila el shell: es una capa de aviso, no una barrera")
            if len(elegidas) == 2:
                self.pasos.append("ELIGE LA SUPERFICIE QUE USAS: se generaron `.github/hooks/harness-vscode.json` (arnés Local de VS Code, Preview) y `.github/hooks/harness-cli.json` (Copilot CLI y sesiones Copilot del Agent Host). "
                                  "Comparten carpeta, no comportamiento; una superficie puede leer el archivo de la otra (no confirmado) y entonces el hook corre dos veces, lo que es inocuo (gana la denegación). "
                                  "Si solo usas una, regenera con `--agentes copilot-vscode` o `--agentes copilot-cli`.")
            else:
                self.pasos.append(f"Se generó solo el hook de {elegidas[0]['superficie']}: la otra superficie no está cubierta. Si usas ambas, regenera con `--agentes copilot`.")
            self.pasos.append("Antes de fiarte: registra una carga útil real en cada superficie (en Local, el panel de registros del agente; en la CLI, un hook de bitácora `postToolUse`) y prueba `bash`, "
                              "`view`/`read`, `edit`/`create` y una herramienta MCP. Los hooks de VS Code están sujetos a «Workspace Trust» y a posibles restricciones de la organización. "
                              "Requiere `sh`, `python3`, `bash`, `jq` y `git` en el PATH.")
            self.pasos.append("La marca del harness va como comentario de shell al final del comando (JSON no admite comentarios); si editas ese comando a mano, conserva el comentario o la instancia dejará de reconocer el archivo como propio.")
        else:
            self.control_hook_estado = "degradado"
            self.control_hook_motivo = motivo
            self.avisos.append(f"Sin hook de datos: {motivo}.")
        skills = fuente.get("skills") or []
        for sk in skills:
            plan.append(fn.planificar_archivo(destino, f"{RUTA_SKILLS}/{sk['nombre']}/SKILL.md", skill_con_marca(sk["contenido"])))
        usados = {sk["nombre"] for sk in skills}
        como_skill = []
        for c in fuente.get("comandos") or []:
            texto, motivo_c = (None, "ya existe una skill con el mismo nombre") if c["nombre"] in usados else comando_como_skill(c)
            if texto is None:
                self.comandos_omitidos.append(c["nombre"])
                self.avisos.append(f"Comando `{c['nombre']}` no generado para Copilot: {motivo_c}.")
                continue
            como_skill.append(c["nombre"])
            plan.append(fn.planificar_archivo(destino, f"{RUTA_SKILLS}/{c['nombre']}/SKILL.md", texto))
        if como_skill:
            self.pasos.append("Comandos: se generaron como skills de invocación manual (`disable-model-invocation: true`); se invocan con " + ", ".join(f"`/{n}`" for n in como_skill)
                              + ". Un `name` inválido haría que el skill no cargue sin avisar.")

        self._mcp(fuente, plan, destino)

        deny, ask, self.no_traducible = permisos_traducibles(fuente)
        self.pasos.append("Barrera de la CLI que no depende del script (se pasa en la línea de comandos o en el script de integración continua; no se escribe aquí): "
                          "la denegación gana incluso con `--allow-all`. Los `ask` de la política no necesitan bandera (pedir aprobación es lo que hace la CLI con lo que no está permitido) "
                          "y los `allow` no se traducen. Ejemplo con tu política (ajusta los prefijos):\n" + ejemplo_deny_tool(deny))
        self.pasos.append("Lo global (por ejemplo `~/.copilot/hooks/`, `~/.copilot/copilot-instructions.md`, la política de la organización o los ajustes `chat.*` de VS Code) no se escribe: si lo quieres, hazlo tú. "
                          "`chat.tools.terminal.autoApprove` con `false` NO bloquea (solo pide aprobación): no lo uses como control.")
        for it in plan:
            if it.get("aviso"):
                self.avisos.append(it["aviso"])
        return fn.escribir_plan(destino, plan, aplicar)

    def _mcp(self, fuente, plan, destino):
        """Por superficie: `permitida` escribe su archivo; `confirmar` solo imprime el fragmento; `prohibida` avisa."""
        escribir = {v: {} for v in self.variantes}
        fragmentos = {v: {} for v in self.variantes}
        for sv in fuente.get("mcp") or []:
            nombre = sv["nombre"]
            if sv["registrar"] == "prohibida":
                self.mcp_estado[nombre] = "prohibida"
                self.avisos.append(f"MCP `{nombre}`: la política lo prohíbe (`registrar = \"prohibida\"`); no se escribe nada.")
                continue
            for v in self.variantes:
                entrada, motivo = entrada_mcp(sv, v)
                if entrada is None:
                    self.mcp_estado[nombre] = "no_traducible"
                    self.avisos.append(f"MCP `{nombre}`: no se traduce a `{MCP[v]['ruta']}`: {motivo}. Regístralo a mano.")
                elif sv["registrar"] == "permitida":
                    escribir[v][nombre] = entrada
                    self.mcp_estado[nombre] = "escrito"
                else:
                    fragmentos[v][nombre] = entrada
                    self.mcp_estado[nombre] = "paso_para_la_persona"
        for v in self.variantes:
            if escribir[v]:
                plan.append(fn.planificar_archivo(destino, MCP[v]["ruta"], config_mcp(v, escribir[v])))
                self.pasos.append(f"MCP: se escribió `{MCP[v]['ruta']}` (clave `{MCP[v]['clave']}`, `type: {MCP[v]['local']}|http`) con los servidores `registrar = \"permitida\"`; "
                                  "nunca lleva valores de variables. Exige carpeta de confianza.")
            if fragmentos[v]:
                self.pasos.append(f"MCP (no escrito: `registrar = \"confirmar\"`). Si lo apruebas, añade a `{MCP[v]['ruta']}`:\n"
                                  + json.dumps({MCP[v]["clave"]: fragmentos[v]}, ensure_ascii=False, indent=2))

    def degradaciones(self):
        base = super().degradaciones()
        f = FUENTE_CP
        base += [
            {"que_se_pierde": "VS Code, arnés Local: los hooks están en Preview (pueden cambiar), `matcher` se ignora (filtra el script), cualquier código distinto de 0 y 2 solo avisa (falla ABIERTO) y qué pasa al agotarse `timeout` no está confirmado. "
                              "El script deniega él mismo ante sus errores (salida 2), pero no cubre que `sh`/`git` falten antes de arrancarlo",
             "imposicion_alternativa": "rol de solo lectura en la base de datos, sandbox del Agent Host, `chat.tools.edits.autoApprove` con globos (solo pide aprobación), protección de ramas e integración continua con el mismo gate", "fuente": f},
            {"que_se_pierde": "Copilot CLI y Agent Host: `preToolUse` cierra ante errores y salidas distintas de cero, pero el TIEMPO AGOTADO siempre deja pasar, incluso en hooks de política del administrador; los hooks `http` también fallan abiertos",
             "imposicion_alternativa": "`--deny-tool` / `--allow-tool` con `Kind(argumento)` (la denegación gana incluso con `--allow-all`), sandbox `--sandbox`, hooks de política del administrador, rol de solo lectura en la base de datos e integración continua", "fuente": f},
            {"que_se_pierde": "Son tres superficies con archivos compartidos y comportamiento distinto («file compatibility does not make their behavior identical»): un hook en una no asegura nada en la otra, y no se pudo confirmar que cada superficie ignore el archivo de la otra",
             "imposicion_alternativa": "generar ambos (`--agentes copilot`) o la superficie que usa la persona, y registrar la carga útil de cada una antes de confiar en el hook", "fuente": f},
            {"que_se_pierde": "El hook solo vigila el shell: en Local los nombres de herramienta no están documentados (se juzga cualquier herramienta con `tool_input.command` de texto) y en la CLI solo `bash`/`powershell`; no cubre lectura/escritura de archivos ni MCP (la tabla de nombres de la CLI no los lista)",
             "imposicion_alternativa": "`--deny-tool='read(...)'`/`write(...)` en la CLI, sandbox, servidores MCP con permisos mínimos y rol de solo lectura en la base de datos", "fuente": f},
            {"que_se_pierde": "`chat.tools.terminal.autoApprove` con `false` NO bloquea el comando: solo exige aprobación; no se genera ni se vende como control",
             "imposicion_alternativa": "el hook `PreToolUse` de Local (Preview) y `--deny-tool` en la CLI", "fuente": f},
            {"que_se_pierde": "`ask` no se usa en el hook: lo que la política marca «confirmar» se deniega",
             "imposicion_alternativa": "que la persona corra ella el comando, o declarar el host en la política", "fuente": f},
            {"que_se_pierde": "Solo se genera la variante `bash`/`command` (POSIX): sin `sh`, `git`, `python3`, `bash` y `jq` el hook no funciona (en Local falla abierto); no se genera la variante `powershell`/`windows`",
             "imposicion_alternativa": "usar WSL, o rol de solo lectura en la base de datos e integración continua", "fuente": f},
            {"que_se_pierde": "Instrucciones: Copilot suma `AGENTS.md`, `.github/copilot-instructions.md` y `CLAUDE.md` sin precedencia garantizada y no hay límite de tamaño confirmado; este adaptador no genera otro archivo de instrucciones para no duplicar",
             "imposicion_alternativa": "mantener la política corta y no repetirla a mano en `copilot-instructions.md`; el gate en integración continua", "fuente": f},
            {"que_se_pierde": "Permisos: `--deny-tool` y `--allow-tool` son banderas de la CLI, no un archivo de la instancia: los `deny` neutrales solo se imprimen como paso para la persona (la denegación gana incluso con `--allow-all`); `ask` es el comportamiento por defecto y `allow` no se traduce; en VS Code `autoApprove: false` NO bloquea",
             "imposicion_alternativa": "poner las banderas en el script de integración continua y en el alias de la persona, `permissions.disableBypassPermissionsMode` en la política de la organización y el hook `preToolUse`", "fuente": f},
            {"que_se_pierde": "Comandos propios: los `.prompt.md` están obsoletos para el Agent Host y el Local se retirará; la CLI no tiene archivos de comandos propios. Los comandos neutrales se generan como skills de invocación manual (confirmado), pero un comando con el mismo nombre que una skill, o fuera de los límites de skill, no se genera",
             "imposicion_alternativa": "skills (`.github/skills`) invocadas con `/nombre`", "fuente": f},
            {"que_se_pierde": "Skills: se generan solo en `.github/skills` (los `.claude/skills` y `.agents/skills` no); un `name` inválido hace que el skill no cargue sin avisar (el neutro ya valida el patrón, 64 y 1024 caracteres); `argument-hint`, `user-invocable` y `context` no se generan",
             "imposicion_alternativa": "añadir a mano el frontmatter extra si hace falta", "fuente": f},
            {"que_se_pierde": "MCP: solo se escriben los servidores `registrar = \"permitida\"` y SIN `entorno` (la referencia a variables no está confirmada: `${input:id}` sin la forma de `inputs`, y `${env:...}` en la CLI «no se pudo confirmar»); en la CLI `type` es `local` y en VS Code `stdio` (se respeta por archivo); `tools: [\"*\"]` sigue el ejemplo oficial de la CLI; `sandboxEnabled` no se genera; exige carpeta de confianza",
             "imposicion_alternativa": "paso de la persona con el fragmento exacto, `inputs` a mano en VS Code y credenciales fuera del alcance del agente", "fuente": f},
            {"que_se_pierde": "La marca `_generado_por_el_harness` en `.vscode/mcp.json` y `.mcp.json` no está confirmada como admitida (no se leyó un esquema); un archivo escrito a mano no se fusiona (lo generado va a `mcp.generado.json`)",
             "imposicion_alternativa": "probar el archivo y, si lo rechaza, quitar la clave (la instancia dejará de reconocerlo como propio); incorporar a mano las entradas", "fuente": f},
            {"que_se_pierde": "Reglas por ruta (`.github/instructions`), subagentes (`.github/agents`) y la ejecución no interactiva `copilot -p` (códigos de salida y `preToolUse` en `-p` no confirmados) están en FORMATO.md pero este adaptador no los genera",
             "imposicion_alternativa": "escribirlos a mano siguiendo copilot/FORMATO.md; en `-p` dar permisos mínimos con `--allow-tool`; el control real vive en la base de datos y la integración continua", "fuente": f},
        ]
        if getattr(self, "no_traducible", None):
            detalle = "; ".join(f"{x['origen']} «{x['regla']}»: {x['motivo']}" for x in self.no_traducible)
            base.append({"que_se_pierde": f"Reglas de la política que no se pueden expresar como prefijo literal de comando y por eso NO están en las banderas `--deny-tool` ({len(self.no_traducible)}): {detalle}",
                         "imposicion_alternativa": "el hook de datos y el de commit (donde existan), rol de solo lectura en la base de datos, protección de ramas e integración continua", "fuente": "capacidades_comunes.permisos_desde_politica y copilot/FORMATO.md §7"})
        if not self.hook_generado:
            base.append({"que_se_pierde": "El hook de datos no se generó en esta instancia",
                         "imposicion_alternativa": "rol de solo lectura en la base de datos y declarar `[[datos.ambientes]]` y `alcance.repos` en la política para generarlo",
                         "fuente": "instalador/generar-politicas.py"})
        return base


class CopilotVscode(Copilot):
    nombre = "copilot-vscode"
    comandos = carpetas_home = ()
    variantes = ("vscode",)


class CopilotCli(Copilot):
    nombre = "copilot-cli"
    comandos = carpetas_home = ()
    variantes = ("cli",)


ADAPTADORES = [Copilot, CopilotVscode, CopilotCli]
