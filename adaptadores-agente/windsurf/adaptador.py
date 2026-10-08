#!/usr/bin/env python3
"""Adaptador de Windsurf (Devin Desktop): AGENTS.md (ya lo leen ambos agentes) + hook de bloqueo para Cascade y/o Devin Local.

Windsurf son DOS agentes con archivos distintos; los de uno no los lee el otro (windsurf/FORMATO.md, «Hallazgo estructural»):
  Cascade (agente histórico)       `.devin/hooks.json`     eventos `snake_case`; solo los `pre_*` bloquean, con salida 2
  Devin Local (agente por defecto) `.devin/hooks.v1.json`  `PreToolUse`; bloquea con salida 2 o `{"decision":"block"}`

Cómo se elige (el marco no pasa opciones a `generar`, así que la variante es el NOMBRE del adaptador):
  --agentes windsurf               (por defecto) genera AMBOS, cada uno por separado, y dice cuál tocar según lo que use la persona
  --agentes windsurf-devin-local   solo Devin Local
  --agentes windsurf-cascade       solo Cascade
Solo `windsurf` se detecta solo; las variantes se piden por nombre. Qué agente usa la persona: las pestañas nuevas arrancan en Devin Local
salvo que haya elegido otro; Cascade queda para conversaciones antiguas (FORMATO.md §«Hallazgo estructural»).

AMBOS FALLAN ABIERTOS: cualquier salida distinta de 2 deja pasar la acción. Por eso el script deniega él mismo ante cualquier error
(entrada ilegible, falta de `jq`/`bash`/`git`/`python3`, fallo de la política) y el control por hook queda SIEMPRE «degradado»
(capa de aviso, nunca barrera). Si la política no permite generar el hook, no se escribe ningún archivo de hook.

Genera SOLO dentro de la instancia y SOLO lo «confirmado con fuente»:
  .devin/hooks.json | .devin/hooks.v1.json   registro del hook (la marca va como comentario de shell dentro de `command`: JSON no admite
                                             comentarios y en Devin Local el objeto de hooks es el archivo ENTERO, sin sitio para una clave extra)
  .devin/hooks/*                             hook de datos generado por `instalador/generar-politicas.py` + puente + un lanzador por variante
  .devin/skills/<n>/SKILL.md                 skills neutrales (las leen Cascade y Devin Local; marca en un comentario HTML tras la cabecera)
  .devin/config.json                         SOLO Devin Local: `permissions.deny`/`ask` con `Exec(<prefijo literal>)` (deny gana siempre)
  .devin/mcp_config.json                     SOLO Devin Local: `mcpServers` de los servidores con `registrar = "permitida"` (variables `${env:VAR}`)
No genera reglas `.devin/rules` (el contenido iría duplicado con AGENTS.md, que ambos leen), subagentes ni `.devinignore`; tampoco comandos:
los workflows son solo de Cascade y sus claves de cabecera no están confirmadas, y Devin Local no los soporta (el sustituto son las skills).
Cascade no tiene `permissions` (su lista de denegados SOLO exige aprobación: no se vende como control) y su MCP es global del usuario: ambos
se imprimen como pasos para la persona. MCP con `registrar = "confirmar"` (por defecto) no escribe nada y se imprime el fragmento; `"prohibida"`
no escribe nada y avisa. Lo global se imprime como paso para la persona.
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

RUTA_HOOKS = ".devin/hooks"
RUTA_SKILLS = ".devin/skills"
RUTA_CONFIG = ".devin/config.json"
RUTA_MCP = ".devin/mcp_config.json"
RUTA_MCP_GLOBAL = "~/.config/devin/mcp_config.json"
FUENTE_WS = "MATRIZ.md y windsurf/FORMATO.md"
AVISO_FALTA_LANZADOR = "guardia de datos: no se encontro el lanzador; se bloquea por precaucion"

VARIANTES = {
    "cascade": {"formato": "windsurf-cascade", "json": ".devin/hooks.json", "lanzador": "lanzar-cascade.sh", "agente": "Cascade"},
    "devin-local": {"formato": "windsurf-devin", "json": ".devin/hooks.v1.json", "lanzador": "lanzar-devin-local.sh", "agente": "Devin Local"},
}


def comando_hook(lanzador):
    """Una línea para `bash -c`: busca la raíz con git (o el directorio actual) y, si falta el lanzador, deniega ELLA MISMA (salida 2).

    Lleva la marca del harness como comentario de shell al final (es lo que reconoce `es_generado`)."""
    ruta = f"{RUTA_HOOKS}/{lanzador}"
    return (f'd=$(git rev-parse --show-toplevel 2>/dev/null) || d=.; l="$d/{ruta}"; '
            f'if [ -f "$l" ]; then exec sh "$l"; fi; echo \'{AVISO_FALTA_LANZADOR}\' >&2; exit 2 # {fn.MARCA}')


def hooks_cascade():
    """`.devin/hooks.json` (FORMATO.md §3A): `hooks.pre_run_command[]` con `command` y `show_output`."""
    doc = {"hooks": {"pre_run_command": [{"command": comando_hook(VARIANTES["cascade"]["lanzador"]), "show_output": True}]}}
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def hooks_devin_local():
    """`.devin/hooks.v1.json` (FORMATO.md §3B): el objeto de hooks es el archivo entero; `PreToolUse[].matcher` (regex) + `hooks[]`."""
    doc = {"PreToolUse": [{"matcher": "^exec$",
                           "hooks": [{"type": "command", "command": comando_hook(VARIANTES["devin-local"]["lanzador"]), "timeout": 30}]}]}
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


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


def config_permisos(deny, ask):
    """`.devin/config.json` (FORMATO.md §7): `permissions.deny`/`ask` con `Exec(<prefijo>)`. Orden de evaluación: denegar > preguntar > permitir."""
    perm = {}
    if deny:
        perm["deny"] = [f"Exec({p})" for p in deny]
    if ask:
        perm["ask"] = [f"Exec({p})" for p in ask]
    return json.dumps({"_generado_por_el_harness": fn.MARCA, "permissions": perm}, ensure_ascii=False, indent=2) + "\n"


def entrada_mcp(s):
    """(dict del servidor, None) o (None, motivo). Devin Local (FORMATO.md §6): `command`/`args`/`env` o `url`; variables como `${env:VAR}`."""
    if s["tipo"] == "remoto":
        if s["entorno"]:
            return None, "un servidor remoto con `entorno` no tiene equivalente confirmado (`headers` no es una variable de entorno)"
        return {"url": s["url"]}, None
    e = {"command": s["comando"]}
    if s["args"]:
        e["args"] = list(s["args"])
    if s["entorno"]:
        e["env"] = {x["clave"]: "${env:" + x["variable"] + "}" for x in s["entorno"]}
    return e, None


def config_mcp(servidores):
    return json.dumps({"_generado_por_el_harness": fn.MARCA, "mcpServers": servidores}, ensure_ascii=False, indent=2) + "\n"


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


class Windsurf(ga.Adaptador):
    nombre = "windsurf"
    codigo_matriz = "WS"
    comandos = ("windsurf", "devin")
    carpetas_home = (".codeium/windsurf", ".config/devin")
    variantes = ("cascade", "devin-local")
    hook_generado = False

    def capacidades(self):
        caps = super().capacidades()
        genera = {"Instrucciones del proyecto": "AGENTS.md lo genera el núcleo; Cascade y Devin Local lo leen sin configuración; no se genera otro archivo de instrucciones (se duplicaría)",
                  "Hooks que bloquean": "`.devin/hooks.json` (Cascade) y/o `.devin/hooks.v1.json` (Devin Local), solo si la política lo permite; ambos fallan abiertos: queda «degradado»",
                  "Skills": "`.devin/skills/<nombre>/SKILL.md` con las skills neutrales (las leen Cascade y Devin Local; marca en un comentario HTML tras la cabecera)",
                  "MCP": "Devin Local: `.devin/mcp_config.json` solo con `registrar = \"permitida\"`; con `confirmar` se imprime el fragmento; el MCP de Cascade es global del usuario y solo se imprime"}
        for k, v in caps.items():
            v["generado_por_este_adaptador"] = k in genera
            v["nota"] = genera.get(k, "no lo genera este adaptador (la fuente neutral aún no lo produce); no se promete")
        caps["Reglas por ruta"]["nota"] = ("el formato `.devin/rules/*.md` con `trigger` está confirmado (FORMATO.md §2), pero la fuente neutral no tiene reglas por ruta y "
                                           "una regla `always_on` repetiría AGENTS.md (que ambos agentes ya leen): no se genera")
        caps["Comandos propios"]["nota"] = "los workflows son solo de Cascade y sus claves de cabecera no están confirmadas; Devin Local no los soporta y los sustituye por skills (generadas): no se generan comandos"
        caps["Permisos / modos / sandbox"]["generado_por_este_adaptador"] = "devin-local" in self.variantes
        caps["Permisos / modos / sandbox"]["nota"] = ("Devin Local: `.devin/config.json` con `permissions.deny`/`ask` (`Exec(<prefijo literal>)`; deny gana siempre); "
                                                      "Cascade: una entrada denegada solo exige aprobación, no bloquea: no se genera ni se vende como control")
        return caps

    def generar(self, fuente, destino, aplicar=False):
        self.avisos, self.pasos = [], []
        self.control_hook_estado = self.control_hook_motivo = None
        self.hook_generado = False
        self.no_traducible, self.comandos_omitidos, self.mcp_estado = [], [], {}
        plan = []
        elegidas = [VARIANTES[v] for v in self.variantes]

        if self.estado_hooks() != "si":
            archivos, motivo = [], f"la matriz no confirma hooks que bloquean para Windsurf (estado «{self.estado_hooks()}»)"
        else:
            archivos, motivo = [], None
            vistos = {}
            for v in elegidas:
                lista, motivo = gh.archivos_de_hook(fuente, lanzador=v["formato"])
                for nombre, contenido, modo in lista:
                    nombre = v["lanzador"] if nombre == gh.LANZADOR else nombre
                    if nombre not in vistos:
                        vistos[nombre] = True
                        archivos.append((nombre, contenido, modo))
        if archivos:
            self.hook_generado = True
            for nombre, contenido, modo in archivos:
                plan.append(fn.planificar_archivo(destino, f"{RUTA_HOOKS}/{nombre}", contenido, modo=modo, respetar_manual=True))
            for v in elegidas:
                texto = hooks_cascade() if v["formato"] == "windsurf-cascade" else hooks_devin_local()
                plan.append(fn.planificar_archivo(destino, v["json"], texto))
            self.control_hook_estado = "degradado"
            self.control_hook_motivo = ("hook de bloqueo generado desde la política, pero Windsurf FALLA ABIERTO (solo la salida 2 bloquea; un guion que falla, no arranca o se agota deja pasar) "
                                        "y solo vigila el shell (`pre_run_command` en Cascade, `exec` en Devin Local): es una capa de aviso, no una barrera")
            nombres = " y ".join(v["agente"] for v in elegidas)
            if len(elegidas) == 2:
                self.pasos.append("ELIGE EL AGENTE QUE USAS: se generaron los archivos de Cascade (`.devin/hooks.json`) y de Devin Local (`.devin/hooks.v1.json`); cada agente solo lee el suyo. "
                                  "Las pestañas nuevas arrancan en Devin Local (Cascade queda para conversaciones antiguas). Si solo usas uno, regenera con `--agentes windsurf-devin-local` "
                                  "o `--agentes windsurf-cascade` y borra el archivo del otro.")
            else:
                self.pasos.append(f"Se generó solo el hook de {nombres}: el otro agente de Windsurf no lo lee. Si usas ambos, regenera con `--agentes windsurf`.")
            self.pasos.append("Comprueba el hook antes de fiarte: en Devin Local ejecuta `/hooks`; registra la carga útil real con un hook de bitácora y prueba `exec` (los nombres de herramienta "
                              "«can vary by CLI mode, model, and enabled integrations»). Los hooks no cargan con el espacio de trabajo en «Restricted Mode». "
                              "Requiere `sh`, `python3`, `bash`, `jq` y `git` en el PATH.")
            self.pasos.append("La marca del harness va como comentario de shell al final de `command` (JSON no admite comentarios); si editas ese `command` a mano, conserva el comentario o la instancia dejará de reconocer el archivo como propio.")
        else:
            self.control_hook_estado = "degradado"
            self.control_hook_motivo = motivo
            self.avisos.append(f"Sin hook de datos: {motivo}.")
        for sk in fuente.get("skills") or []:
            plan.append(fn.planificar_archivo(destino, f"{RUTA_SKILLS}/{sk['nombre']}/SKILL.md", skill_con_marca(sk["contenido"])))
        self.comandos_omitidos = [c["nombre"] for c in fuente.get("comandos") or []]
        if self.comandos_omitidos:
            self.avisos.append("Comandos no generados para Windsurf (los workflows son solo de Cascade y sus claves no están confirmadas; Devin Local los sustituye por skills): "
                               + ", ".join(f"`{n}`" for n in self.comandos_omitidos) + ".")

        deny, ask, self.no_traducible = permisos_traducibles(fuente)
        if "devin-local" in self.variantes:
            if deny or ask:
                plan.append(fn.planificar_archivo(destino, RUTA_CONFIG, config_permisos(deny, ask)))
            self.pasos.append("Barrera declarativa de Devin Local, que no depende del script: `permissions.deny` gana siempre (denegar > preguntar > permitir). "
                              f"Se escribe en `{RUTA_CONFIG}` con los prefijos literales de la política (`Exec(<prefijo>)`); complétalo a mano si quieres, por ejemplo con `Read(**/.env*)` y `Write(**/.env*)`. "
                              "Las reglas `allow` no se traducen.")
        if "cascade" in self.variantes and "devin-local" not in self.variantes:
            self.pasos.append("Cascade no tiene permisos de proyecto por archivo: su lista de comandos denegados solo exige aprobación (no bloquea) y se configura en el IDE, no en la instancia; no se genera ni se cuenta como control.")

        self._mcp(fuente, plan, destino)
        self.pasos.append("Lo global (por ejemplo `~/.codeium/windsurf/hooks.json`, `~/.config/devin/AGENTS.md` o `/etc/devin/`) no se escribe: si lo quieres, hazlo tú.")
        for it in plan:
            if it.get("aviso"):
                self.avisos.append(it["aviso"])
            if it.get("alterno_de") in (RUTA_CONFIG, RUTA_MCP):
                self.pasos.append(f"`{it['alterno_de']}` es tuyo (escrito a mano) y no se fusiona solo: lo generado quedó en `{it['ruta']}`; copia a mano las entradas que quieras, sin duplicar las que ya tengas.")
        return fn.escribir_plan(destino, plan, aplicar)

    def _mcp(self, fuente, plan, destino):
        """Devin Local: `permitida` escribe `.devin/mcp_config.json`; `confirmar` solo imprime. Cascade: el archivo es global (`~/.config/devin`): solo se imprime."""
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
                self.avisos.append(f"MCP `{nombre}`: no se traduce a Windsurf: {motivo}. Regístralo a mano.")
            elif sv["registrar"] == "permitida" and "devin-local" in self.variantes:
                escribir[nombre] = entrada
                self.mcp_estado[nombre] = "escrito"
            else:
                fragmentos[nombre] = entrada
                self.mcp_estado[nombre] = "paso_para_la_persona"
        if escribir:
            plan.append(fn.planificar_archivo(destino, RUTA_MCP, config_mcp(escribir)))
            self.pasos.append(f"MCP: se escribió `{RUTA_MCP}` (Devin Local) con los servidores `registrar = \"permitida\"`; las variables van como `${{env:VAR}}` (nunca valores): "
                              "expórtalas en tu entorno. Por defecto Devin Local pide aprobación antes de usar cualquier herramienta MCP.")
        if fragmentos:
            donde = RUTA_MCP if "devin-local" in self.variantes else RUTA_MCP_GLOBAL
            self.pasos.append(f"MCP (no escrito: `registrar = \"confirmar\"` o el agente no tiene archivo de proyecto). Si lo apruebas, añade a `{donde}`:\n"
                              + json.dumps({"mcpServers": fragmentos}, ensure_ascii=False, indent=2))
        if (escribir or fragmentos) and "cascade" in self.variantes:
            self.pasos.append(f"Cascade solo lee el MCP de `{RUTA_MCP_GLOBAL}` (global del usuario, no se escribe): copia ahí el mismo bloque `mcpServers` si usas Cascade.")

    def degradaciones(self):
        base = super().degradaciones()
        f = FUENTE_WS
        base += [
            {"que_se_pierde": "Windsurf falla ABIERTO en sus dos agentes: solo la salida 2 bloquea; un guion que se cae, sale con 1 o con otro código, o devuelve JSON ilegible deja pasar la acción. "
                              "El script cubre sus propios errores (deniega con salida 2); no cubre que `bash`/`git` falten antes de arrancarlo ni un tiempo agotado (qué hace Windsurf al expirar: no confirmado)",
             "imposicion_alternativa": "rol de solo lectura en la base de datos, `permissions.deny` de Devin Local (paso para la persona), sandbox de Devin Local (`--sandbox`: no cubre `edit`/`write` y no existe en Windows), protección de ramas e integración continua con el mismo gate", "fuente": f},
            {"que_se_pierde": "Windsurf son dos agentes y cada uno lee solo su archivo (`.devin/hooks.json` Cascade, `.devin/hooks.v1.json` Devin Local): quien use el agente cuyo archivo no se generó queda sin hook",
             "imposicion_alternativa": "generar ambos (`--agentes windsurf`) o la variante que usa la persona, y declarar el agente en uso en el README de la instancia", "fuente": f},
            {"que_se_pierde": "El hook solo vigila el shell (`pre_run_command` en Cascade; `exec` en Devin Local): no cubre lectura/escritura de archivos, MCP ni `apply_patch`, y no está confirmado que toda vía de edición de Cascade pase por `pre_write_code`",
             "imposicion_alternativa": "`permissions.deny` con `Read(...)`/`Write(...)` en Devin Local, `.devinignore` (a mano), servidores MCP con permisos mínimos y rol de solo lectura en la base de datos", "fuente": f},
            {"que_se_pierde": "Cascade: la lista de comandos denegados NO bloquea (siempre pide permiso) y no tiene `permissions`; solo `.devinignore` y el hook (que falla abierto) lo limitan",
             "imposicion_alternativa": "usar Devin Local para trabajo con datos, o rol de solo lectura en la base de datos, integración continua y protección de ramas", "fuente": f},
            {"que_se_pierde": "Los hooks no cargan en «Restricted Mode»; los nombres de herramienta de Devin Local pueden variar por modo y modelo, así que `matcher: ^exec$` podría no coincidir con la herramienta de shell",
             "imposicion_alternativa": "confiar el espacio de trabajo y registrar la carga útil real antes de fijar el filtro; mantener la barrera `permissions.deny`", "fuente": f},
            {"que_se_pierde": "`ask` no existe en estos hooks: lo que la política marca «confirmar» se deniega",
             "imposicion_alternativa": "que la persona corra ella el comando, o declarar el host en la política", "fuente": f},
            {"que_se_pierde": "El lanzador es POSIX (`sh`, `git`, `python3`, `bash`, `jq`); no se genera la variante `powershell` de Cascade: en Windows sin esas herramientas el hook no funciona (y falla abierto)",
             "imposicion_alternativa": "usar WSL, o rol de solo lectura en la base de datos e integración continua", "fuente": f},
            {"que_se_pierde": "Comandos propios: los workflows son solo de Cascade y las claves de su cabecera no están confirmadas; Devin Local no los soporta. No se generan los comandos neutrales",
             "imposicion_alternativa": "skills (`.devin/skills`, ya generadas), que se invocan con `/nombre` en Devin Local o `@nombre` en Cascade", "fuente": f},
            {"que_se_pierde": "Permisos: `.devin/config.json` solo lo usa Devin Local (deny gana siempre); en Cascade la lista de denegados solo exige aprobación. `ask` y `allow` neutrales: `ask` se escribe, `allow` no se traduce. Un `config.json` escrito a mano no se fusiona (el contenido va a `config.generado.json`)",
             "imposicion_alternativa": "usar Devin Local para trabajo con datos, incorporar a mano `permissions` si ya tienes un `config.json`, y rol de solo lectura en la base de datos", "fuente": f},
            {"que_se_pierde": "Skills: los límites de `name`/`description` en Devin no están confirmados (el neutro ya valida 64 y 1024); `allowed-tools`, `permissions` y `triggers` (solo Devin Local) no se generan",
             "imposicion_alternativa": "descripciones cortas; añadir a mano el frontmatter de Devin Local si hace falta", "fuente": f},
            {"que_se_pierde": "MCP: solo Devin Local tiene archivo de proyecto (`.devin/mcp_config.json`); el de Cascade es global del usuario y no se escribe. Solo se escriben los `registrar = \"permitida\"`, los remotos sin `entorno` y con `${env:VAR}` (la interpolación consta en la página de Cascade; para Devin Local la fuente solo muestra un ejemplo con valor literal)",
             "imposicion_alternativa": "paso de la persona con el fragmento exacto, `disabledTools`/`disabled` a mano, credenciales fuera del alcance del agente y el archivo `.devin/mcp_config.local.json` (ignorado) para valores propios", "fuente": f},
            {"que_se_pierde": "La marca `_generado_por_el_harness` en `config.json` y `mcp_config.json` no está confirmada como admitida (no se leyó un esquema de esos archivos)",
             "imposicion_alternativa": "probar los archivos en Devin Local; si los rechaza, quitar la clave (la instancia dejará de reconocerlos como propios)", "fuente": f},
            {"que_se_pierde": "Reglas por ruta (`.devin/rules/*.md` con `trigger`), subagentes de Devin Local y `.devinignore` están confirmados en FORMATO.md pero este adaptador no los genera; AGENTS.md ya lo leen ambos",
             "imposicion_alternativa": "escribirlos a mano siguiendo windsurf/FORMATO.md; el control real vive en la base de datos y la integración continua", "fuente": f},
            {"que_se_pierde": "Ejecución no interactiva: el IDE no la tiene; para la CLI (`devin -p`) no está confirmado que se ejecuten los hooks ni qué código de salida devuelve",
             "imposicion_alternativa": "no depender del hook en automatización: sandbox, rol de solo lectura en la base de datos e integración continua", "fuente": f},
        ]
        if getattr(self, "no_traducible", None):
            detalle = "; ".join(f"{x['origen']} «{x['regla']}»: {x['motivo']}" for x in self.no_traducible)
            base.append({"que_se_pierde": f"Reglas de la política que no se pueden expresar como prefijo literal de comando y por eso NO están en `permissions` ({len(self.no_traducible)}): {detalle}",
                         "imposicion_alternativa": "el hook de datos y el de commit (donde existan), rol de solo lectura en la base de datos, protección de ramas e integración continua", "fuente": "capacidades_comunes.permisos_desde_politica y windsurf/FORMATO.md §7"})
        if not self.hook_generado:
            base.append({"que_se_pierde": "El hook de datos no se generó en esta instancia",
                         "imposicion_alternativa": "rol de solo lectura en la base de datos y declarar `[[datos.ambientes]]` y `alcance.repos` en la política para generarlo",
                         "fuente": "instalador/generar-politicas.py"})
        return base


class WindsurfCascade(Windsurf):
    nombre = "windsurf-cascade"
    comandos = carpetas_home = ()
    variantes = ("cascade",)


class WindsurfDevinLocal(Windsurf):
    nombre = "windsurf-devin-local"
    comandos = carpetas_home = ()
    variantes = ("devin-local",)


ADAPTADORES = [Windsurf, WindsurfCascade, WindsurfDevinLocal]
