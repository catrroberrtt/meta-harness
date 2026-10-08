#!/usr/bin/env python3
"""Adaptador de Gemini CLI: `GEMINI.md` que importa AGENTS.md + hook `BeforeTool` en `.gemini/settings.json`.

Genera SOLO dentro de la instancia y SOLO lo «confirmado con fuente» en `gemini/FORMATO.md`:
  GEMINI.md                  importa `@./AGENTS.md` (Gemini no lee AGENTS.md salvo que se configure `context.fileName`)
  .gemini/settings.json      objeto `hooks.BeforeTool` y/o `mcpServers` (solo `registrar = "permitida"`); la marca va en una clave: JSON no admite comentarios
  .gemini/skills/<n>/SKILL.md  skills neutrales del harness (marca en un comentario HTML tras la cabecera)
  .gemini/commands/<n>.toml  comandos neutrales traducidos (`description` + `prompt`; marca en un comentario TOML)
  .gemini/hooks/*            hook de datos generado por `instalador/generar-politicas.py` (se reutiliza) + puente + lanzador `lanzar.sh`

GEMINI FALLA ABIERTO: cualquier código de salida distinto de 0 y 2 (o stdout que no sea JSON) deja pasar la acción. Por eso el
script deniega él mismo ante cualquier error (JSON `{"decision":"deny"}` y salida 0) y el control por hook queda SIEMPRE
«degradado» (capa de aviso, nunca barrera). El hook solo vigila `run_shell_command`: la política de datos juzga comandos de
terminal, no rutas de archivo. No escribe `context.fileName` (evita cargar AGENTS.md dos veces), ni políticas `~/.gemini/policies`
(nivel usuario o administrador: los permisos `deny`/`ask` neutrales se imprimen como paso para la persona) ni subagentes. MCP con `registrar =
"confirmar"` (por defecto) no escribe nada y se imprime el fragmento; `"prohibida"` no escribe nada y avisa. Un `settings.json` escrito a mano no se
fusiona: el contenido generado (hook + MCP juntos, sin duplicar) va a `settings.generado.json`.
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

RUTA_GEMINI_MD = "GEMINI.md"
RUTA_SETTINGS = ".gemini/settings.json"
RUTA_HOOKS = ".gemini/hooks"
RUTA_SKILLS = ".gemini/skills"
RUTA_COMANDOS = ".gemini/commands"
FUENTE_GE = "MATRIZ.md y gemini/FORMATO.md"
COMANDO_HOOK = "$GEMINI_PROJECT_DIR/.gemini/hooks/lanzar.sh"
MATCHER = "run_shell_command"

GEMINI_MD = f"""<!-- {fn.MARCA} -->
# Instrucciones del proyecto

Las reglas de este proyecto están en `{{agents}}` (generado desde `politicas.toml`); Gemini CLI no lo lee solo, por eso se importa aquí.
Léelo antes de ejecutar comandos que toquen datos, git, despliegue, costos o secretos, y no edites a mano los archivos que llevan la marca del harness.

@./{{agents}}
"""


def settings_json(hook=True, mcp_servers=None):
    """`.gemini/settings.json` (FORMATO.md §3 y §6): `hooks.BeforeTool[]` (`matcher`, `hooks[]` con `name`, `type`, `command`, `timeout` en ms)
    y `mcpServers` (por alias). Un solo archivo con ambos, sin duplicar."""
    doc = {"_generado_por_el_harness": fn.MARCA}
    if hook:
        doc["hooks"] = {"BeforeTool": [{"matcher": MATCHER,
                                        "hooks": [{"name": "guardia-datos", "type": "command", "command": COMANDO_HOOK, "timeout": 30000,
                                                   "description": "Comprueba el comando contra la política de datos del proyecto"}]}]}
    if mcp_servers:
        doc["mcpServers"] = mcp_servers
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def entrada_mcp(s):
    """(dict del servidor, None) o (None, motivo). Claves de FORMATO.md §6: `command`/`args`/`env` o `httpUrl`.

    El `env` admite `${VAR}` (interpolación confirmada): la referencia neutral se escribe tal cual, nunca un valor. El alias no admite guion bajo
    («can cause security policies to fail silently»). Un remoto se escribe como `httpUrl` (HTTP transmisible); el transporte SSE usa `url` y el neutral no lo distingue."""
    if "_" in s["nombre"]:
        return None, "el alias no puede llevar guion bajo (las políticas de Gemini fallarían sin avisar)"
    if s["tipo"] == "remoto":
        if s["entorno"]:
            return None, "un servidor remoto con `entorno` no tiene equivalente confirmado (`headers` no es una variable de entorno)"
        return {"httpUrl": s["url"]}, None
    e = {"command": s["comando"]}
    if s["args"]:
        e["args"] = list(s["args"])
    if s["entorno"]:
        e["env"] = {x["clave"]: "${" + x["variable"] + "}" for x in s["entorno"]}
    return e, None


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


def comando_toml(c):
    """(texto TOML, None) o (None, motivo). `prompt` y `description` (FORMATO.md §4).

    El cuerpo neutral es el Markdown sin cabecera. Los marcadores propios de Gemini (`{{args}}`, `!{...}`, `@{...}`) NO se traducen ni se dejan pasar:
    `!{...}` ejecutaría un comando y `@{...}` incluiría un archivo; si el neutral los trae, el comando no se genera."""
    m = re.match(r"\A---\r?\n.*?\r?\n---\r?\n?(.*)\Z", c["contenido"], re.S)
    cuerpo = (m.group(1) if m else c["contenido"]).replace("\r\n", "\n").strip("\n")
    for marcador in ("{{", "!{", "@{"):
        if marcador in cuerpo:
            return None, f"el cuerpo contiene `{marcador}`, un marcador propio de Gemini que no se debe colar sin querer"
    comillas = "'" * 3
    if comillas not in cuerpo:
        prompt = f"prompt = {comillas}\n{cuerpo}\n{comillas}"
    else:
        prompt = 'prompt = """\n' + cuerpo.replace("\\", "\\\\").replace('"', '\\"') + '\n"""'
    return f"# {fn.MARCA}\n\ndescription = {json.dumps(c['descripcion'], ensure_ascii=False)}\n{prompt}\n", None


def _prefijos_exceptuados(ruta_politica):
    """Prefijos de `datos.comandos` que la política permite en el ambiente de escritura: una regla `deny` no admite excepciones, así que no se traducen."""
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
              "motivo": "la política la permite en el ambiente de escritura y una regla `deny` no admite excepciones; la juzga el hook de datos"}
             for x in perm.get("deny") or [] if x in exc]
    return deny, list(perm.get("ask") or []), list(perm.get("no_traducible") or []) + extra


def ejemplo_politica(deny, ask=()):
    """Texto TOML de la forma documentada (FORMATO.md §7) para que la PERSONA lo ponga en `~/.gemini/policies/`.

    `deny` con prioridad mayor que `ask_user` (gana la prioridad más alta); en modo no interactivo `ask_user` se trata como `deny`."""
    marcador = ('[[rule]]\ntoolName = "run_shell_command"\ncommandPrefix = "<prefijo del comando que quieras prohibir>"\n'
                'decision = "deny"\npriority = 100\ndenyMessage = "<motivo>"')
    if not deny and not ask:
        return marcador
    trozos = [f'[[rule]]\ntoolName = "run_shell_command"\ncommandPrefix = {json.dumps(p)}\ndecision = "deny"\npriority = 100\n' for p in deny]
    if not deny:
        trozos.append(marcador + "\n")
    trozos += [f'[[rule]]\ntoolName = "run_shell_command"\ncommandPrefix = {json.dumps(p)}\ndecision = "ask_user"\npriority = 50\n' for p in ask]
    return "\n".join(trozos).rstrip()


class Gemini(ga.Adaptador):
    nombre = "gemini"
    codigo_matriz = "GE"
    comandos = ("gemini",)
    carpetas_home = (".gemini",)
    hook_generado = False

    def capacidades(self):
        caps = super().capacidades()
        genera = {"Instrucciones del proyecto": "`GEMINI.md` importa `@./AGENTS.md`; sin `context.fileName`, porque Gemini no lee AGENTS.md por sí mismo",
                  "Hooks que bloquean": "`.gemini/settings.json` (`BeforeTool`), solo si la política lo permite; Gemini falla abierto: queda «degradado»",
                  "Skills": "`.gemini/skills/<nombre>/SKILL.md` con las skills neutrales (marca en un comentario HTML tras la cabecera)",
                  "Comandos propios": "`.gemini/commands/<nombre>.toml` (`description` y `prompt`) traducidos de los comandos neutrales; en una carpeta no confiable (si Trusted Folders está activo) Gemini no los carga",
                  "MCP": "`mcpServers` en `.gemini/settings.json` solo con `registrar = \"permitida\"`; con `confirmar` se imprime el fragmento como paso; alias sin guion bajo"}
        for k, v in caps.items():
            v["generado_por_este_adaptador"] = k in genera
            v["nota"] = genera.get(k, "no lo genera este adaptador (la fuente neutral aún no lo produce); no se promete")
        caps["Reglas por ruta"]["nota"] = "no hay activación por glob en Gemini (FORMATO.md §2); solo carga por directorio tocado: no se genera"
        caps["Permisos / modos / sandbox"]["nota"] = "las políticas `deny`/`ask_user` son de nivel usuario o administrador (`~/.gemini/policies`, `/etc/gemini-cli/policies`); el nivel de proyecto no funciona: los permisos neutrales se imprimen como paso para la persona, no se escriben"
        return caps

    def generar(self, fuente, destino, aplicar=False):
        self.avisos, self.pasos = [], []
        self.control_hook_estado = self.control_hook_motivo = None
        self.hook_generado = False
        self.no_traducible, self.comandos_omitidos, self.mcp_estado = [], [], {}
        plan = []
        agents = fuente.get("archivo_agents", fn.ARCHIVO_AGENTS)
        plan.append(fn.planificar_archivo(destino, RUTA_GEMINI_MD, GEMINI_MD.format(agents=agents)))

        if self.estado_hooks() != "si":
            archivos, motivo = [], f"la matriz no confirma hooks que bloquean para Gemini (estado «{self.estado_hooks()}»)"
        else:
            archivos, motivo = gh.archivos_de_hook(fuente, lanzador="gemini")
        if archivos:
            self.hook_generado = True
            for nombre, contenido, modo in archivos:
                plan.append(fn.planificar_archivo(destino, f"{RUTA_HOOKS}/{nombre}", contenido, modo=modo, respetar_manual=True))
            self.control_hook_estado = "degradado"
            self.control_hook_motivo = ("hook `BeforeTool` generado desde la política, pero Gemini FALLA ABIERTO (un código distinto de 0 y 2 o un stdout que no es JSON deja pasar) "
                                        "y solo vigila `run_shell_command`: es una capa de aviso, no una barrera")
            self.pasos.append("Abre Gemini en esta carpeta y revisa el hook con `/hooks panel`: los hooks de proyecto se registran por huella (nombre y comando); si cambian, se tratan como nuevos y no confiables hasta que los apruebes. "
                              "Requiere `sh`, `python3`, `bash`, `jq` y `git` en el PATH.")
            self.pasos.append("Carpetas de confianza: si las activaste (`security.folderTrust.enabled: true` en `~/.gemini/settings.json`), en una carpeta NO confiable Gemini ignora el `.gemini/settings.json` del proyecto "
                              "y con él el hook, sin avisar. Por defecto están desactivadas; no confíes en ellas para proteger el hook.")
            self.pasos.append("La marca del harness va en la clave `_generado_por_el_harness` porque JSON no admite comentarios; no está confirmado que Gemini ignore claves desconocidas en `settings.json`: "
                              "si lo rechaza, quita la clave (la instancia dejará de reconocer el archivo como propio).")
        else:
            self.control_hook_estado = "degradado"
            self.control_hook_motivo = motivo
            self.avisos.append(f"Sin hook de datos: {motivo}.")

        escribir, fragmentos = self._mcp(fuente)
        if self.hook_generado or escribir:
            plan.append(fn.planificar_archivo(destino, RUTA_SETTINGS, settings_json(self.hook_generado, escribir)))
        if escribir:
            self.pasos.append(f"MCP: se escribió `mcpServers` en `{RUTA_SETTINGS}` con los servidores `registrar = \"permitida\"`. Las variables se escriben como referencias `${{VAR}}` "
                              "(nunca valores): expórtalas en tu entorno. En una carpeta no confiable (Trusted Folders activo) Gemini no conecta los servidores MCP.")
        if fragmentos:
            self.pasos.append(f"MCP (no escrito: `registrar = \"confirmar\"`). Si lo apruebas, añade a `{RUTA_SETTINGS}` (o a `~/.gemini/settings.json`):\n"
                              + json.dumps({"mcpServers": fragmentos}, ensure_ascii=False, indent=2))

        for sk in fuente.get("skills") or []:
            plan.append(fn.planificar_archivo(destino, f"{RUTA_SKILLS}/{sk['nombre']}/SKILL.md", skill_con_marca(sk["contenido"])))
        generados = []
        for c in fuente.get("comandos") or []:
            texto, motivo_c = comando_toml(c)
            if texto is None:
                self.comandos_omitidos.append(c["nombre"])
                self.avisos.append(f"Comando `{c['nombre']}` no generado para Gemini: {motivo_c}.")
                continue
            generados.append(c["nombre"])
            plan.append(fn.planificar_archivo(destino, f"{RUTA_COMANDOS}/{c['nombre']}.toml", texto))
        if generados:
            self.pasos.append("Comandos: se invocan como " + ", ".join(f"`/{n}`" for n in generados) + "; recarga con `/commands reload`. "
                              "Skills: gestión con `/skills list|enable|disable|reload`.")

        deny, ask, self.no_traducible = permisos_traducibles(fuente)
        self.pasos.append("Barrera que no depende del script (nivel usuario o administrador, NO se escribe desde aquí): crea tú `~/.gemini/policies/harness.toml` "
                          "(o `/etc/gemini-cli/policies/`, de root) con reglas `deny` como esta, y ajusta los prefijos a tu política:\n" + ejemplo_politica(deny, ask)
                          + "\n(`deny` gana por prioridad; `ask_user` se trata como `deny` en modo no interactivo; `allow` no se traduce.)")
        self.pasos.append("Lo global (por ejemplo `~/.gemini/GEMINI.md`, `~/.gemini/settings.json` o `~/.gemini/policies/`) no se escribe: si lo quieres, hazlo tú. "
                          "Si prefieres que Gemini lea `AGENTS.md` directamente, añade a mano `context.fileName: [\"AGENTS.md\", \"GEMINI.md\"]` en tu `settings.json` (y quita el import de `GEMINI.md` para no duplicarlo).")
        for it in plan:
            if it.get("aviso"):
                self.avisos.append(it["aviso"])
            if it.get("alterno_de") == RUTA_SETTINGS:
                self.pasos.append(f"`{RUTA_SETTINGS}` es tuyo (escrito a mano) y no se fusiona solo: el hook y los `mcpServers` quedaron en `{it['ruta']}`. "
                                  "Copia a mano las claves `hooks.BeforeTool` y `mcpServers` que quieras, sin duplicar las que ya tengas.")
        return fn.escribir_plan(destino, plan, aplicar)

    def _mcp(self, fuente):
        """({alias: entrada} a escribir, {alias: entrada} para el paso). `permitida` escribe; `confirmar` solo imprime; `prohibida` avisa."""
        escribir, fragmentos = {}, {}
        for sv in fuente.get("mcp") or []:
            nombre = sv["nombre"]
            if sv["registrar"] == "prohibida":
                self.mcp_estado[nombre] = "prohibida"
                self.avisos.append(f"MCP `{nombre}`: la política lo prohíbe (`registrar = \"prohibida\"`); no se escribe nada.")
                continue
            entrada, motivo = entrada_mcp(sv)
            if entrada is None:
                self.mcp_estado[nombre] = "no_traducible"
                self.avisos.append(f"MCP `{nombre}`: no se traduce a `{RUTA_SETTINGS}`: {motivo}. Regístralo a mano.")
            elif sv["registrar"] == "permitida":
                escribir[nombre] = entrada
                self.mcp_estado[nombre] = "escrito"
            else:
                fragmentos[nombre] = entrada
                self.mcp_estado[nombre] = "paso_para_la_persona"
        return escribir, fragmentos

    def degradaciones(self):
        base = super().degradaciones()
        f = FUENTE_GE
        base += [
            {"que_se_pierde": "Gemini falla ABIERTO: cualquier código de salida distinto de 0 y 2 es una advertencia y la acción sigue, y un stdout con texto que no es JSON se trata como «permitir». "
                              "El script solo cubre sus propios errores (deniega con JSON y salida 0); no cubre `hooksConfig.enabled = false`, que `python3` o `sh` falten fuera del lanzador, ni un tiempo agotado (no confirmado qué hace Gemini)",
             "imposicion_alternativa": "reglas `deny` de nivel usuario o administrador en `~/.gemini/policies/` (pasos para la persona), sandbox (`-s`), rol de solo lectura en la base de datos, protección de ramas e integración continua con el mismo gate", "fuente": f},
            {"que_se_pierde": "Un hook de proyecto cuyo nombre o comando cambie se trata como nuevo y no confiable hasta aprobarlo; con Trusted Folders activo, en una carpeta no confiable se ignora todo `.gemini/settings.json` del proyecto",
             "imposicion_alternativa": "revisar con `/hooks panel` tras cada regeneración, no depender de Trusted Folders y mantener la barrera de nivel usuario o administrador", "fuente": f},
            {"que_se_pierde": "El hook solo vigila `run_shell_command`: no cubre herramientas de archivo (`read_file`, `write_file`, `replace`, `grep_search`...) ni MCP, porque la política de datos juzga comandos de terminal",
             "imposicion_alternativa": "reglas `deny` de usuario o administrador por herramienta, `excludeTools` en MCP a mano, sandbox y rol de solo lectura en la base de datos", "fuente": f},
            {"que_se_pierde": "`BeforeTool` no admite `ask`: lo que la política marca «confirmar» se deniega",
             "imposicion_alternativa": "que la persona corra ella el comando, o declarar el host en la política", "fuente": f},
            {"que_se_pierde": "Las políticas del nivel de proyecto (`.gemini/policies`) están documentadas como «currently non-functional»; las de usuario y administrador no se escriben desde la instancia",
             "imposicion_alternativa": "paso de la persona: `~/.gemini/policies/*.toml` o `/etc/gemini-cli/policies` (root) con `deny`; una `deny` sin `argsPattern` retira la herramienta del modelo", "fuente": f},
            {"que_se_pierde": "`AGENTS.md` no es nativo: llega por el import de `GEMINI.md`; el límite de tamaño de `GEMINI.md` no está confirmado",
             "imposicion_alternativa": "mantener la política corta; `context.fileName` a mano si se prefiere", "fuente": f},
            {"que_se_pierde": "Reglas por ruta: no hay activación por glob (solo `GEMINI.md` por directorio tocado)",
             "imposicion_alternativa": "`GEMINI.md` por carpeta (a mano) y el gate en integración continua", "fuente": f},
            {"que_se_pierde": "La clave de marca `_generado_por_el_harness` en `settings.json` no está confirmada como admitida (no se leyó un esquema de ese archivo); un `settings.json` escrito a mano no se pisa y el hook queda en `settings.generado.json` hasta que se incorpore",
             "imposicion_alternativa": "incorporar el objeto `hooks` a mano y, si lo rechaza, quitar la clave; mantener el control en la base de datos", "fuente": f},
            {"que_se_pierde": "Permisos: las políticas `deny`/`ask_user` (`~/.gemini/policies`, `/etc/gemini-cli/policies`) son de nivel usuario o administrador y NO se escriben; el nivel de proyecto está documentado como no funcional. `allow` no se traduce y `ask_user` se trata como `deny` en modo no interactivo",
             "imposicion_alternativa": "paso de la persona con las reglas exactas (`commandPrefix` literal, `deny` con prioridad mayor que `ask_user`), sandbox (`-s`) y rol de solo lectura en la base de datos", "fuente": f},
            {"que_se_pierde": "Comandos: solo se generan los que no traen marcadores propios de Gemini (`{{args}}`, `!{...}`, `@{...}`); en una carpeta no confiable (Trusted Folders activo) no se cargan; `@{archivo}` no está confirmado y no se usa",
             "imposicion_alternativa": "`/commands reload` tras regenerar; los omitidos se escriben a mano siguiendo gemini/FORMATO.md §4", "fuente": f},
            {"que_se_pierde": "Skills: los límites de `name`/`description` no están confirmados en la fuente (el neutro ya valida 64 y 1024); se activan con `activate_skill` y confirmación de la persona",
             "imposicion_alternativa": "descripciones cortas; `/skills list` para comprobar cuáles se cargaron", "fuente": f},
            {"que_se_pierde": "MCP: solo se escriben los servidores `registrar = \"permitida\"`; los remotos van como `httpUrl` (HTTP transmisible; el SSE usa `url` y el neutral no lo distingue) y sin `entorno`; en una carpeta no confiable no se conectan; `trust`, `includeTools` y `excludeTools` no se generan",
             "imposicion_alternativa": "paso de la persona con el fragmento exacto, `excludeTools` a mano y credenciales de producción fuera del alcance del agente", "fuente": f},
            {"que_se_pierde": "Un `settings.json` escrito a mano no se fusiona automáticamente (no se puede distinguir lo manual de lo generado sin perder cambios): el contenido va a `settings.generado.json`; en un archivo ya generado el hook y los `mcpServers` se escriben juntos, sin duplicar, y lo que se añada a mano dentro se pierde al regenerar",
             "imposicion_alternativa": "incorporar a mano las claves `hooks.BeforeTool` y `mcpServers`; poner lo propio en `~/.gemini/settings.json` (usuario)", "fuente": f},
            {"que_se_pierde": "Subagentes (`.gemini/agents`) y `context.fileName` están confirmados en FORMATO.md pero este adaptador no los genera",
             "imposicion_alternativa": "escribirlos a mano siguiendo gemini/FORMATO.md; el control real vive en la base de datos y la integración continua", "fuente": f},
        ]
        if getattr(self, "no_traducible", None):
            detalle = "; ".join(f"{x['origen']} «{x['regla']}»: {x['motivo']}" for x in self.no_traducible)
            base.append({"que_se_pierde": f"Reglas de la política que no se pueden expresar como prefijo literal de comando y por eso NO están en el ejemplo de política ({len(self.no_traducible)}): {detalle}",
                         "imposicion_alternativa": "el hook de datos y el de commit (donde existan), rol de solo lectura en la base de datos, protección de ramas e integración continua", "fuente": "capacidades_comunes.permisos_desde_politica y gemini/FORMATO.md §7"})
        if getattr(self, "comandos_omitidos", None):
            base.append({"que_se_pierde": "Comandos neutrales no generados por traer marcadores propios de Gemini: " + ", ".join(f"`{n}`" for n in self.comandos_omitidos),
                         "imposicion_alternativa": "escribirlos a mano en `.gemini/commands/` sin esos marcadores", "fuente": f})
        if not self.hook_generado:
            base.append({"que_se_pierde": "El hook de datos no se generó en esta instancia",
                         "imposicion_alternativa": "rol de solo lectura en la base de datos y declarar `[[datos.ambientes]]` y `alcance.repos` en la política para generarlo",
                         "fuente": "instalador/generar-politicas.py"})
        return base


ADAPTADORES = [Gemini]
