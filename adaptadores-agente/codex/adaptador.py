#!/usr/bin/env python3
"""Adaptador de Codex CLI: AGENTS.md (ya lo lee) + hook `PreToolUse` en `.codex/hooks.json` + reglas `forbidden` (si la política las permite).

Genera SOLO dentro de la instancia y SOLO lo «confirmado con fuente» en `codex/FORMATO.md`:
  .codex/hooks.json           `PreToolUse` con `matcher` `^Bash$` (la marca va en una clave: JSON no admite comentarios)
  .codex/hooks/*              hook de datos generado por `instalador/generar-politicas.py` (se reutiliza) + puente + lanzador `lanzar.sh`
  .codex/rules/harness.rules  `prefix_rule(..., decision = "forbidden"|"prompt")`: prefijos literales que la política prohíbe (forbidden) o pide confirmar (prompt)
  .agents/skills/<n>/SKILL.md skills neutrales del harness (la ruta de proyecto es `.agents/skills`, no `.codex/skills`)
  .codex/config.toml          `[mcp_servers.<nombre>]` SOLO de los servidores con `registrar = "permitida"` (variables como `env_vars`, nunca valores)

CODEX FALLA ABIERTO: un hook que falla, se agota o no está confiado deja pasar la acción. Por eso el script deniega él mismo ante
cualquier error y el control por hook queda SIEMPRE «degradado» (capa de aviso, nunca barrera). El hook existe solo si la política
permite generarlo; si no, no se escribe ningún archivo de hook. No genera comandos (los prompts de usuario están obsoletos y son solo de usuario:
el sustituto son las skills) ni subagentes. MCP: `registrar = "confirmar"` (por defecto) no escribe nada y se imprime el fragmento como paso para la
persona; `"prohibida"` no escribe nada y avisa. Nada global: lo global se imprime como paso para la persona.
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

RUTA_HOOKS_JSON = ".codex/hooks.json"
RUTA_HOOKS = ".codex/hooks"
RUTA_REGLAS = ".codex/rules/harness.rules"
RUTA_SKILLS = ".agents/skills"
RUTA_CONFIG = ".codex/config.toml"
TOPE_LISTA_SKILLS = 8000                # caracteres de la lista inicial de skills cuando se desconoce la ventana (FORMATO.md §5)
FUENTE_CX = "MATRIZ.md y codex/FORMATO.md"
TOPE_AGENTS_BYTES = 32 * 1024           # `project_doc_max_bytes` por defecto (FORMATO.md §1)
COMANDO_HOOK = '/bin/sh "$(git rev-parse --show-toplevel)/.codex/hooks/lanzar.sh"'
PALABRAS = "A-Za-z0-9_.-"


def hooks_json():
    """`.codex/hooks.json` (FORMATO.md §3): `hooks.PreToolUse[].matcher` + `hooks[]` con `type`, `command`, `timeout`, `statusMessage`."""
    doc = {"_generado_por_el_harness": fn.MARCA,
           "hooks": {"PreToolUse": [{"matcher": "^Bash$",
                                     "hooks": [{"type": "command", "command": COMANDO_HOOK, "timeout": 30,
                                                "statusMessage": "Comprobando el comando contra la política de datos"}]}]}}
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def _datos_comandos(ruta_politica):
    try:
        datos = tomllib.loads(Path(ruta_politica).read_text(encoding="utf-8")).get("datos") or {}
    except (OSError, tomllib.TOMLDecodeError):
        return []
    return [c for c in datos.get("comandos") or [] if isinstance(c, dict)]


def motivos_y_excepciones(ruta_politica):
    """({prefijo: motivo}, {prefijos exceptuados}) de `datos.comandos`.

    Una regla `forbidden` no admite excepciones: el prefijo que la política permite en el ambiente de escritura
    (`permitida_en_ambiente_de_escritura`) NO se traduce (lo juzga el hook de datos, que sí conoce el ambiente)."""
    motivos, excepciones = {}, set()
    for c in _datos_comandos(ruta_politica):
        prefs, _ = fn.cc.prefijos_literales(c.get("regex"))
        for pref in prefs or []:
            if c.get("permitida_en_ambiente_de_escritura"):
                excepciones.add(pref)
            elif c.get("motivo"):
                motivos[pref] = str(c["motivo"])
    return motivos, excepciones


def reglas_de_permisos(fuente):
    """([(palabras, justificación)] forbidden, [(palabras, justificación)] prompt, [no_traducible extra]) desde los permisos neutrales.

    Solo prefijos literales (los que ya dejó el núcleo): nunca se amplía un prefijo a un patrón más ancho. `allow` no se traduce
    (una regla `allow` ampliaría lo que el agente puede hacer fuera del sandbox). Un prefijo ya listado no se repite."""
    perm = fuente.get("permisos") or {}
    origenes = perm.get("origenes") or {}
    motivos, excepciones = motivos_y_excepciones(fuente["politica_ruta"])
    prohibidas, confirmar, extra, vistos = [], [], [], set()
    for pref in perm.get("deny") or []:
        if pref in vistos:
            continue
        vistos.add(pref)
        if pref in excepciones:
            extra.append({"origen": origenes.get(pref, "datos.comandos"), "regla": pref,
                          "motivo": "la política la permite en el ambiente de escritura y una regla `forbidden` no admite excepciones; la juzga el hook de datos"})
            continue
        prohibidas.append((pref.split(" "), motivos.get(pref) or f"La política del proyecto lo prohíbe ({origenes.get(pref, 'permisos')})."))
    for pref in perm.get("ask") or []:
        if pref in vistos:
            continue
        vistos.add(pref)
        confirmar.append((pref.split(" "), f"La política del proyecto pide confirmación explícita ({origenes.get(pref, 'permisos')})."))
    return prohibidas, confirmar, extra


def reglas_rules(prohibidas, confirmar=()):
    """Archivo `.rules` (Starlark, FORMATO.md §7). `match` repite el propio prefijo: `codex execpolicy check` lo valida."""
    L = [f"# {fn.MARCA}",
         "# Reglas de comandos de Codex (experimentales): solo valen para comandos que SALEN del sandbox y no sustituyen al sandbox ni al hook.",
         "# Probar con: codex execpolicy check --pretty --rules .codex/rules/harness.rules -- <comando>", ""]
    for decision, reglas in (("forbidden", prohibidas), ("prompt", confirmar)):
        for palabras, motivo in reglas:
            L += ["prefix_rule(",
                  f"    pattern = {json.dumps(palabras, ensure_ascii=False)},",
                  f'    decision = "{decision}",',
                  f"    justification = {json.dumps(motivo, ensure_ascii=False)},",
                  f"    match = [{json.dumps(' '.join(palabras), ensure_ascii=False)}],",
                  ")", ""]
    return "\n".join(L)


def skill_con_marca(texto):
    """SKILL.md con la marca como comentario HTML justo tras la cabecera. Si la cabecera es tan larga que la marca queda fuera de los
    800 caracteres que mira `es_generado`, va como comentario YAML dentro de la cabecera (así la regeneración sigue reconociéndolo)."""
    if fn.MARCA in texto:
        return texto
    m = re.match(r"\A(---\r?\n)(.*?\r?\n---\r?\n)(.*)\Z", texto, re.S)
    if not m:
        return f"<!-- {fn.MARCA} -->\n{texto}"
    r = f"{m.group(1)}{m.group(2)}<!-- {fn.MARCA} -->\n{m.group(3)}"
    if not fn.es_generado(r):
        r = f"{m.group(1)}# {fn.MARCA}\n{m.group(2)}{m.group(3)}"
    return r


def _toml_cadena(v):
    return json.dumps(v, ensure_ascii=False)


def bloque_mcp(s):
    """(texto TOML de `[mcp_servers.<nombre>]`, None) o (None, motivo). Solo lo confirmado (FORMATO.md §6): `command`/`args`/`env_vars` o `url`.

    `env_vars` reenvía variables con SU MISMO nombre: una referencia `CLAVE = ${OTRA}` no se puede expresar sin escribir un valor,
    y la interpolación `${VAR}` en `config.toml` no está confirmada: ese servidor no se traduce."""
    L = [f"[mcp_servers.{s['nombre']}]"]
    if s["tipo"] == "remoto":
        if s["entorno"]:
            return None, "un servidor remoto con `entorno` no tiene equivalente confirmado (`env_http_headers` mapea cabeceras, no variables de entorno)"
        L.append(f"url = {_toml_cadena(s['url'])}")
    else:
        L.append(f"command = {_toml_cadena(s['comando'])}")
        if s["args"]:
            L.append("args = [" + ", ".join(_toml_cadena(a) for a in s["args"]) + "]")
        distintas = [e["clave"] for e in s["entorno"] if e["clave"] != e["variable"]]
        if distintas:
            return None, ("`env_vars` solo reenvía variables con el mismo nombre y la interpolación `${VAR}` en `config.toml` no está confirmada; "
                          f"no se puede expresar sin un valor: {', '.join(distintas)}")
        if s["entorno"]:
            L.append("env_vars = [" + ", ".join(_toml_cadena(e["clave"]) for e in s["entorno"]) + "]")
    return "\n".join(L), None


def config_toml(bloques):
    return "\n".join([f"# {fn.MARCA}", "# Servidores MCP de Codex: solo se leen en proyectos de confianza.", ""] + [b + "\n" for b in bloques])


class Codex(ga.Adaptador):
    nombre = "codex"
    codigo_matriz = "CX"
    comandos = ("codex",)
    carpetas_home = (".codex",)
    hook_generado = False

    def capacidades(self):
        caps = super().capacidades()
        genera = {"Instrucciones del proyecto": "AGENTS.md lo genera el núcleo; Codex lo lee sin configuración (tope combinado de 32 KiB)",
                  "Hooks que bloquean": "`.codex/hooks.json` (`PreToolUse`), solo si la política lo permite; Codex falla abierto: queda «degradado»",
                  "Permisos / modos / sandbox": "solo `.codex/rules/harness.rules`: `forbidden` (deny) y `prompt` (ask) con prefijos literales de la política; sin `approval_policy` ni `sandbox_mode`",
                  "Skills": "`.agents/skills/<nombre>/SKILL.md` con las skills neutrales (marca en un comentario HTML tras la cabecera)",
                  "MCP": "`.codex/config.toml` (`[mcp_servers.<nombre>]`) solo con `registrar = \"permitida\"`; con `confirmar` se imprime el fragmento como paso; solo se lee en proyectos de confianza"}
        for k, v in caps.items():
            v["generado_por_este_adaptador"] = k in genera
            v["nota"] = genera.get(k, "no lo genera este adaptador (la fuente neutral aún no lo produce); no se promete")
        caps["Reglas por ruta"]["nota"] = "no hay activación por glob en Codex (FORMATO.md §2): no se genera; alternativa documentada: `AGENTS.override.md` por carpeta"
        caps["Comandos propios"]["nota"] = "`~/.codex/prompts` está obsoleto y es solo de usuario: no se genera; el sustituto son las skills (`.agents/skills`), que sí se generan"
        return caps

    def generar(self, fuente, destino, aplicar=False):
        self.avisos, self.pasos = [], []
        self.control_hook_estado = self.control_hook_motivo = None
        self.hook_generado = False
        self.no_traducible, self.comandos_omitidos, self.mcp_estado = [], [], {}
        plan = []

        tam = len(fn.render_agents_md(fuente, fuente["harness_raiz"]).encode("utf-8"))
        if tam > TOPE_AGENTS_BYTES:
            self.avisos.append(f"El AGENTS.md generado pesa {tam} bytes y supera el tope de Codex de {TOPE_AGENTS_BYTES} bytes combinados "
                               "(`project_doc_max_bytes`): lo que pase del tope no se carga. Reduce la política o sube el tope en `config.toml` (a mano).")

        prohibidas, confirmar, extra = reglas_de_permisos(fuente)
        self.no_traducible = list((fuente.get("permisos") or {}).get("no_traducible") or []) + extra
        if prohibidas or confirmar:
            plan.append(fn.planificar_archivo(destino, RUTA_REGLAS, reglas_rules(prohibidas, confirmar)))
            self.pasos.append("Valida las reglas con `codex execpolicy check --pretty --rules .codex/rules/harness.rules -- <comando>`; "
                              "solo se cargan si el proyecto es de confianza y solo juzgan comandos que salen del sandbox.")

        skills = fuente.get("skills") or []
        for sk in skills:
            plan.append(fn.planificar_archivo(destino, f"{RUTA_SKILLS}/{sk['nombre']}/SKILL.md", skill_con_marca(sk["contenido"])))
        if skills:
            lista = sum(len(sk["nombre"]) + len(sk["descripcion"]) for sk in skills)
            if lista > TOPE_LISTA_SKILLS:
                self.avisos.append(f"Las skills suman {lista} caracteres de nombre y descripción: Codex carga la lista inicial con un tope de {TOPE_LISTA_SKILLS} caracteres "
                                   "(o el 2 % de la ventana de contexto) y acorta primero las descripciones.")
            self.pasos.append("Skills: se invocan con `$nombre` o `/skills`; la carpeta `.agents` queda de solo lectura para el agente bajo el sandbox `workspace-write`.")
        self.comandos_omitidos = [c["nombre"] for c in fuente.get("comandos") or []]
        if self.comandos_omitidos:
            self.avisos.append("Comandos no generados para Codex (los prompts personalizados están obsoletos y son solo de usuario): "
                               + ", ".join(f"`{n}`" for n in self.comandos_omitidos) + ". El sustituto son las skills.")

        self._mcp(fuente, plan, destino)

        if self.estado_hooks() != "si":
            archivos, motivo = [], f"la matriz no confirma hooks que bloquean para Codex (estado «{self.estado_hooks()}»)"
        else:
            archivos, motivo = gh.archivos_de_hook(fuente, lanzador="codex")
        if archivos:
            self.hook_generado = True
            for nombre, contenido, modo in archivos:
                plan.append(fn.planificar_archivo(destino, f"{RUTA_HOOKS}/{nombre}", contenido, modo=modo, respetar_manual=True))
            plan.append(fn.planificar_archivo(destino, RUTA_HOOKS_JSON, hooks_json()))
            self.control_hook_estado = "degradado"
            self.control_hook_motivo = ("hook `PreToolUse` generado desde la política, pero Codex FALLA ABIERTO (hook fuera de confianza, agotado o con otro código de salida deja pasar) "
                                        "y solo vigila la herramienta `Bash`: es una capa de aviso, no una barrera")
            self.pasos.append("OBLIGATORIO: abre Codex en esta carpeta, ejecuta `/hooks`, revisa el hook y confíalo. Un hook nuevo o modificado NO corre hasta que lo confíes "
                              "(se registra por huella, así que cada regeneración con cambios exige confiar de nuevo).")
            self.pasos.append("Comprueba que el proyecto sea de confianza (un proyecto `untrusted` omite `.codex/`: configuración, hooks y reglas). "
                              "Requiere `sh`, `python3`, `bash`, `jq` y `git` en el PATH.")
            self.pasos.append("La marca del harness va en la clave `_generado_por_el_harness` porque JSON no admite comentarios; no está confirmado que Codex ignore claves desconocidas "
                              "en `hooks.json`: si lo rechaza, quita la clave (la instancia dejará de reconocer el archivo como propio).")
        else:
            self.control_hook_estado = "degradado"
            self.control_hook_motivo = motivo
            self.avisos.append(f"Sin hook de datos: {motivo}.")
        self.pasos.append("Para que no dependa de la confianza de cada persona, el administrador puede instalar el mismo hook como gestionado "
                          "(`requirements.toml` con `allow_managed_hooks_only = true`, `[features] hooks = true` y `[hooks] managed_dir`). "
                          "Es de nivel usuario/administrador: este adaptador no escribe `~/.codex` ni `/etc/codex`.")
        self.pasos.append("Lo global (por ejemplo `~/.codex/config.toml` o `~/.codex/hooks.json`) no se escribe: si lo quieres, hazlo tú.")
        for it in plan:
            if it.get("aviso"):
                self.avisos.append(it["aviso"])
        return fn.escribir_plan(destino, plan, aplicar)

    def _mcp(self, fuente, plan, destino):
        """`registrar`: permitida -> escribe `.codex/config.toml`; confirmar -> solo el paso con el fragmento; prohibida -> nada y avisa."""
        escribir, fragmentos = [], []
        for sv in fuente.get("mcp") or []:
            nombre = sv["nombre"]
            if sv["registrar"] == "prohibida":
                self.mcp_estado[nombre] = "prohibida"
                self.avisos.append(f"MCP `{nombre}`: la política lo prohíbe (`registrar = \"prohibida\"`); no se escribe nada.")
                continue
            bloque, motivo = bloque_mcp(sv)
            if bloque is None:
                self.mcp_estado[nombre] = "no_traducible"
                self.avisos.append(f"MCP `{nombre}`: no se traduce a `{RUTA_CONFIG}`: {motivo}. Regístralo a mano.")
                continue
            if sv["registrar"] == "permitida":
                escribir.append(bloque)
                self.mcp_estado[nombre] = "escrito"
            else:
                fragmentos.append(bloque)
                self.mcp_estado[nombre] = "paso_para_la_persona"
        if escribir:
            plan.append(fn.planificar_archivo(destino, RUTA_CONFIG, config_toml(escribir)))
            self.pasos.append(f"MCP: se escribió `{RUTA_CONFIG}` con los servidores `registrar = \"permitida\"`. Codex solo lo lee en proyectos de confianza y las variables "
                              "se reenvían por nombre (`env_vars`): expórtalas en tu entorno; el archivo nunca lleva valores.")
        if fragmentos:
            self.pasos.append(f"MCP (no escrito: `registrar = \"confirmar\"`). Si lo apruebas, añade a `{RUTA_CONFIG}` (o a `~/.codex/config.toml`):\n" + "\n\n".join(fragmentos))

    def degradaciones(self):
        base = super().degradaciones()
        f = FUENTE_CX
        base += [
            {"que_se_pierde": "Codex falla ABIERTO: un hook que falla, se agota, sale con un código distinto de 0 o 2, sale con 2 sin texto en stderr o devuelve algo que no cumple el esquema deja pasar la acción. "
                              "El script solo puede cubrir sus propios errores; no cubre `[features] hooks = false`, que `git` falte (el comando del hook ni arranca) ni un tiempo agotado",
             "imposicion_alternativa": "sandbox `read-only` (o `workspace-write`) sin red, hooks gestionados por el administrador (`requirements.toml`), rol de solo lectura en la base de datos e integración continua con el mismo gate", "fuente": f},
            {"que_se_pierde": "Un hook nuevo o modificado no corre hasta que la persona lo confíe con `/hooks`; en `codex exec` un hook no confiado se omite sin error visible",
             "imposicion_alternativa": "paso de la persona (`/hooks`) tras cada regeneración, `--dangerously-bypass-hook-trust` solo en automatización ya validada, y rol de solo lectura en la base de datos", "fuente": f},
            {"que_se_pierde": "El hook solo vigila `Bash`: no cubre `apply_patch`, herramientas MCP, `write_stdin` ni herramientas alojadas como `WebSearch` («treat tool hooks as a useful guardrail, not a complete enforcement boundary»)",
             "imposicion_alternativa": "sandbox `read-only` sin red, MCP con `enabled_tools`/`disabled_tools` a mano y credenciales de producción fuera del alcance del agente", "fuente": f},
            {"que_se_pierde": "`PreToolUse` no admite `ask` (se parsea pero no se soporta y la acción sigue): lo que la política marca «confirmar» se deniega",
             "imposicion_alternativa": "que la persona corra ella el comando, o declarar el host en la política", "fuente": f},
            {"que_se_pierde": "Las reglas `.rules` son experimentales («may change»), solo valen para comandos que salen del sandbox, se omiten con `--ignore-rules` y solo cargan en proyectos de confianza; solo se traducen los prefijos literales de la política (un regex arbitrario no)",
             "imposicion_alternativa": "reglas `forbidden` o `requirements.toml` de nivel usuario o administrador (a mano), sandbox y rol de solo lectura en la base de datos", "fuente": f},
            {"que_se_pierde": "Con el sandbox `workspace-write` `.codex` queda de solo lectura para el agente, pero sin sandbox o en modo `danger-full-access` el agente podría editar su propio hook",
             "imposicion_alternativa": "no usar `danger-full-access` ni `--dangerously-bypass-approvals-and-sandbox`; protección de ramas e integración continua que verifique `.codex/`", "fuente": f},
            {"que_se_pierde": "AGENTS.md tiene un tope combinado de 32 KiB (`project_doc_max_bytes`): lo que lo pase no se carga; el adaptador solo avisa",
             "imposicion_alternativa": "mantener la política corta o subir el tope en `config.toml` a mano", "fuente": f},
            {"que_se_pierde": "Reglas por ruta: Codex no tiene activación por glob; `@archivo` dentro de AGENTS.md no está confirmado",
             "imposicion_alternativa": "`AGENTS.override.md` por carpeta (`codex --cd <carpeta>`) y el gate en integración continua", "fuente": f},
            {"que_se_pierde": "La clave de marca `_generado_por_el_harness` en `hooks.json` no está confirmada como admitida (no se leyó un esquema de ese archivo)",
             "imposicion_alternativa": "probar el archivo en Codex; si lo rechaza, quitar la clave y mantener el control en la base de datos", "fuente": f},
            {"que_se_pierde": "Comandos propios: `~/.codex/prompts` está obsoleto («Custom prompts are deprecated»), es solo de usuario y no se comparte por el repositorio: no se generan los comandos neutrales",
             "imposicion_alternativa": "skills (`.agents/skills`, ya generadas) que se invocan con `$nombre` o `/skills`", "fuente": f},
            {"que_se_pierde": "Las reglas `prompt` (permisos `ask` de la política) solo juzgan comandos que salen del sandbox: un comando dentro del sandbox no pide confirmación por esa vía; las reglas `allow` no se generan (ampliarían lo permitido)",
             "imposicion_alternativa": "`approval_policy = \"on-request\"` y `sandbox_mode` a mano en `config.toml`, y que la persona confirme lo que la política marca «confirmar»", "fuente": f},
            {"que_se_pierde": "Skills: los límites de `name`/`description` no están confirmados en la fuente; la lista inicial tiene un presupuesto de 2 % del contexto u 8 000 caracteres; solo se generan en `.agents/skills` (no `.codex/skills`)",
             "imposicion_alternativa": "descripciones cortas; el neutro ya valida `name` (64) y `description` (1024)", "fuente": f},
            {"que_se_pierde": "MCP: `.codex/config.toml` solo se lee en proyectos de confianza; la interpolación `${VAR}` no está confirmada, por eso solo se traducen referencias del mismo nombre (`env_vars`) y los servidores remotos sin `entorno`; los de `registrar = \"confirmar\"` no se escriben",
             "imposicion_alternativa": "paso de la persona con el fragmento exacto, `enabled_tools`/`disabled_tools` a mano y credenciales fuera del alcance del agente", "fuente": f},
            {"que_se_pierde": "Subagentes (`.codex/agents`) y `config.toml` (`approval_policy`, `sandbox_mode`) están confirmados en FORMATO.md pero este adaptador no los genera",
             "imposicion_alternativa": "escribirlos a mano siguiendo codex/FORMATO.md; el control real vive en la base de datos y la integración continua", "fuente": f},
        ]
        if getattr(self, "no_traducible", None):
            detalle = "; ".join(f"{x['origen']} «{x['regla']}»: {x['motivo']}" for x in self.no_traducible)
            base.append({"que_se_pierde": f"Reglas de la política que no se pueden expresar como prefijo literal de comando y por eso NO están en `.rules` ({len(self.no_traducible)}): {detalle}",
                         "imposicion_alternativa": "el hook de datos y el de commit (donde existan), rol de solo lectura en la base de datos, protección de ramas e integración continua", "fuente": "capacidades_comunes.permisos_desde_politica y codex/FORMATO.md §7"})
        if not self.hook_generado:
            base.append({"que_se_pierde": "El hook de datos no se generó en esta instancia",
                         "imposicion_alternativa": "rol de solo lectura en la base de datos y declarar `[[datos.ambientes]]` y `alcance.repos` en la política para generarlo",
                         "fuente": "instalador/generar-politicas.py"})
        return base


ADAPTADORES = [Codex]
