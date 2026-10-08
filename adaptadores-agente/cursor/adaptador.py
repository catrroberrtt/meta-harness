#!/usr/bin/env python3
"""Adaptador de Cursor: AGENTS.md (ya lo lee) + regla `.mdc` mínima + hook de datos con `failClosed`.

Genera SOLO dentro de la instancia y SOLO lo «confirmado con fuente» en `cursor/FORMATO.md`:
  .cursor/rules/harness.mdc     regla mínima (`alwaysApply: true`) que remite a AGENTS.md
  .cursor/hooks.json            `beforeShellExecution` con `failClosed: true` (la marca va en una clave, JSON no admite comentarios)
  .cursor/hooks/*               hook de datos generado por `instalador/generar-politicas.py` (se reutiliza) + puente (salida 2 = denegar)

Además, desde la fuente neutral y solo con lo confirmado en FORMATO.md:
  .cursor/skills/<n>/SKILL.md   skills neutrales (§5); los comandos neutrales se generan como skills con `disable-model-invocation: true` (§4)
  .cursor/cli.json              `permissions.deny` de la CLI (§7): solo prefijos de UNA palabra como `Shell(cmd)`; `ask` y los de varias palabras se degradan
  .cursor/mcp.json              clave `mcpServers` (§6), SOLO con `registrar = "permitida"`; con "confirmar" se imprime el paso

No genera `.cursor/commands` (no está documentado hoy). El hook existe solo si la política permite generarlo; si no, el control por
hook queda «degradado» con el motivo. Nada global: lo global se imprime como paso.
"""
import copy
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
NUCLEO = AQUI.parent / "nucleo"
if str(NUCLEO) not in sys.path:
    sys.path.insert(0, str(NUCLEO))
import fuente_neutral as fn  # noqa: E402
import generar_agentes as ga  # noqa: E402
import guardia_hook as gh  # noqa: E402

RUTA_REGLA = ".cursor/rules/harness.mdc"
RUTA_HOOKS_JSON = ".cursor/hooks.json"
RUTA_HOOKS = ".cursor/hooks"
FUENTE_CU = "MATRIZ.md y cursor/FORMATO.md"
RUTA_SKILLS = ".cursor/skills"
RUTA_CLI = ".cursor/cli.json"
RUTA_MCP = ".cursor/mcp.json"
RUTA_MANIFIESTO = ".cursor/harness-generado.json"

REGLA_MDC = f"""---
alwaysApply: true
---
<!-- {fn.MARCA} -->
Las reglas duras de este proyecto están en `{{agents}}`, generado desde `politicas.toml`. Léelo antes de ejecutar comandos
que toquen datos, git, despliegue, costos o secretos, y no edites a mano los archivos que llevan la marca del harness.
"""


# ----------------------------------------------------------------------------- archivos propios y fusión de JSON (R53-R55)
# Mismo bloque en los adaptadores que escriben capacidades (Claude Code, OpenCode, Cursor): cada adaptador es autocontenido.
REF_NEUTRAL = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def con_marca_md(contenido):
    """Agrega la marca del harness como comentario HTML justo después del frontmatter (o al inicio si no hay)."""
    comentario = f"<!-- {fn.MARCA} -->"
    m = re.match(r"\A(---\r?\n.*?\r?\n---\r?\n)(.*)\Z", contenido, re.S)
    return f"{m.group(1)}{comentario}\n{m.group(2)}" if m else f"{comentario}\n{contenido}"


def planificar_md(destino, rel, contenido):
    """Como `fn.planificar_archivo`, pero reconoce la marca en cualquier parte (en un SKILL.md va tras el frontmatter)."""
    ruta = fn._dentro(destino, rel)
    propio = ruta.exists() and fn.MARCA.lower() in ruta.read_text(encoding="utf-8", errors="replace").lower()
    return fn.planificar_archivo(destino, rel, contenido, respetar_manual=not propio)


def referencias(texto, plantilla):
    """Cambia cada referencia neutral `${VAR}` por la sintaxis de referencia del agente; nunca resuelve el valor."""
    return REF_NEUTRAL.sub(lambda m: plantilla.format(m.group(1)), texto)


class _Forma(Exception):
    pass


def _json_texto(doc):
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def _obtener(doc, ruta, tipo, crear, comodin=()):
    """Contenedor (lista o tabla) en la ruta punteada; None si no existe (o, si `crear`, lanza _Forma si choca la forma)."""
    *padres, hoja = ruta.split(".")
    cur = doc
    for p in padres:
        if not isinstance(cur, dict):
            raise _Forma(ruta)
        if p not in cur:
            if not crear:
                return None
            cur[p] = {}
        cur = cur[p]
    if not isinstance(cur, dict):
        raise _Forma(ruta)
    if hoja not in cur:
        if not crear:
            return None
        cur[hoja] = tipo()
    if isinstance(cur[hoja], str) and ruta in comodin and tipo is dict:
        cur[hoja] = {"*": cur[hoja]}          # `"bash": "ask"` equivale a `{"*": "ask"}`: se conserva el significado
    if not isinstance(cur[hoja], tipo):
        raise _Forma(ruta)
    return cur[hoja]


def _podar(doc, ruta):
    *padres, hoja = ruta.split(".")
    cur, cadena = doc, []
    for p in padres:
        if not isinstance(cur, dict) or p not in cur:
            return
        cadena.append((cur, p))
        cur = cur[p]
    if isinstance(cur, dict) and hoja in cur and cur[hoja] in ({}, []):
        del cur[hoja]
        for padre, p in reversed(cadena):
            if padre[p] == {}:
                del padre[p]
            else:
                break


def leer_manifiesto(destino, rel):
    ruta = fn._dentro(destino, rel)
    try:
        doc = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    ent = doc.get("entradas") if isinstance(doc, dict) else None
    return ent if isinstance(ent, dict) else {}


def planificar_manifiesto(destino, rel, entradas):
    """Registro de lo que el harness puso en archivos JSON compartidos (sin él no se podría actualizar sin tocar lo manual)."""
    entradas = {k: v for k, v in entradas.items() if v and (v.get("listas") or v.get("claves"))}
    if not entradas and not fn._dentro(destino, rel).exists():
        return None
    return fn.planificar_archivo(destino, rel, _json_texto({"_generado_por_el_harness": fn.MARCA, "entradas": entradas}))


def fusionar_json(destino, rel, listas, claves, inicial, previo, comodin=(), forzar_alterno=None):
    """Fusiona lo que genera el harness en un JSON que puede tener contenido manual. Devuelve (item|None, entrada_manifiesto, avisos).

    `listas`: {"a.b": [elementos]} se agregan sin duplicar. `claves`: {"a.b": {clave: valor}} se agregan solo si la clave no existe.
    Lo manual nunca se pierde ni se pisa: si una clave existe con otro valor, gana lo manual y se avisa. Lo que el harness puso antes
    (según `previo`, el manifiesto) se retira y se vuelve a poner, de modo que un cambio en la política también quita lo que ya no aplica.
    Si el archivo no es JSON estricto, tiene otra forma o hay `forzar_alterno`, se escribe `<nombre>.generado.json` y se explica."""
    previo = previo or {}
    prev_l, prev_c = previo.get("listas") or {}, previo.get("claves") or {}
    if not (any(listas.values()) or any(claves.values()) or prev_l or prev_c):
        return None, {}, []
    ruta = fn._dentro(destino, rel)
    existe = ruta.is_file()
    original, texto_original, motivo = None, None, forzar_alterno
    if existe and motivo is None:
        texto_original = ruta.read_text(encoding="utf-8", errors="replace")
        try:
            original = json.loads(texto_original)
        except ValueError:
            original = None
        if not isinstance(original, dict):
            motivo = "no es JSON estricto (por ejemplo, tiene comentarios) o no es un objeto"

    def aplicar(doc, con_previo):
        avisos, pl, pc = [], {}, {}
        if con_previo:
            for r, items in prev_l.items():
                lst = _obtener(doc, r, list, False)
                if lst is not None:
                    lst[:] = [x for x in lst if x not in items]
            for r, kv in prev_c.items():
                d = _obtener(doc, r, dict, False)
                if d is not None:
                    for k, v in kv.items():
                        if k in d and d[k] == v:
                            del d[k]
        for r, items in listas.items():
            if items:
                lst = _obtener(doc, r, list, True)
                pl[r] = [x for x in items if x not in lst]
                lst.extend(pl[r])
        for r, kv in claves.items():
            if kv:
                d = _obtener(doc, r, dict, True, comodin)
                for k, v in kv.items():
                    if k not in d:
                        d[k] = v
                        pc.setdefault(r, {})[k] = v
                    elif d[k] != v:
                        avisos.append(f"{rel}: `{r}` ya define `{k}` a mano con otro valor; se respeta lo manual y no se escribe el del harness.")
        for r in list(prev_l) + list(prev_c) + list(listas) + list(claves):
            _podar(doc, r)
        return avisos, {"listas": {k: v for k, v in pl.items() if v}, "claves": pc}

    if motivo is None:
        trabajo = copy.deepcopy(original) if existe else copy.deepcopy(inicial)
        try:
            avisos, entrada = aplicar(trabajo, True)
        except _Forma as e:
            motivo = f"la clave `{e}` no tiene la forma esperada"
    if motivo is not None:
        trabajo = copy.deepcopy(inicial)
        avisos, entrada = aplicar(trabajo, False)
        alt = fn.alterno(rel)
        existente = fn._dentro(destino, alt)
        contenido = _json_texto(trabajo)
        accion = "igual" if existente.is_file() and existente.read_text(encoding="utf-8", errors="replace") == contenido else "alterno"
        avisos.append(f"{rel} {motivo if existe or forzar_alterno else 'no se pudo fusionar'}: no se toca; se genera {alt} para que lo revises "
                      "e incorpores lo que quieras.")
        return {"ruta": alt, "accion": accion, "aviso": avisos[-1], "contenido": contenido, "modo": None, "alterno_de": rel}, {}, avisos
    if existe and trabajo == original:
        item = {"ruta": rel, "accion": "igual", "aviso": None, "contenido": texto_original, "modo": None}
    else:
        item = {"ruta": rel, "accion": "actualizar" if existe else "crear", "aviso": None, "contenido": _json_texto(trabajo), "modo": None}
    return item, entrada, avisos


def comando_como_skill(c):
    """Sustituto de comando propio (FORMATO.md §4): skill con `disable-model-invocation: true`, solo se usa si se escribe `/nombre`."""
    m = re.match(r"\A---\r?\n.*?\r?\n---\r?\n?(.*)\Z", c["contenido"], re.S)
    cuerpo = m.group(1) if m else c["contenido"]
    desc = c["descripcion"]
    if re.search(r": |\s#|^[\[\]{}&*!|>'\"%@`-]", desc):
        desc = json.dumps(desc, ensure_ascii=False)
    return f"---\nname: {c['nombre']}\ndescription: {desc}\ndisable-model-invocation: true\n---\n{cuerpo}"


def reglas_shell(permisos):
    """([`Shell(cmd)`], [(prefijo, acción, motivo) sin traducir]). `Shell()` usa el primer token (FORMATO.md §7): un prefijo de varias
    palabras NO se convierte (`git push` -> `Shell(git)` bloquearía todo git) y `ask` no existe en los permisos de la CLI."""
    reglas, sin = [], []
    for p in permisos.get("deny") or []:
        if re.fullmatch(r"[A-Za-z0-9_-]+", p):
            reglas.append(f"Shell({p})")
        else:
            sin.append((p, "deny", "`Shell()` usa solo el primer token y la sintaxis `comando:argumentos` no tiene ejemplo en FORMATO.md; convertirlo ampliaría el bloqueo"))
    for p in permisos.get("ask") or []:
        sin.append((p, "ask", "los permisos de la CLI solo documentan `allow` y `deny`; no hay `ask`"))
    return reglas, sin


def servidor_cu(s):
    """(configuración de `mcpServers.<nombre>`, None) o (None, motivo). Referencias `${env:VAR}`, nunca el valor; sin `type` (FORMATO.md §6)."""
    if s["tipo"] == "local":
        cfg = {"command": referencias(s["comando"], "${{env:{}}}"), "args": [referencias(a, "${{env:{}}}") for a in s["args"]]}
        if s["entorno"]:
            cfg["env"] = {e["clave"]: "${env:" + e["variable"] + "}" for e in s["entorno"]}
        return cfg, None
    if s["entorno"]:
        return None, "un servidor remoto con `entorno` no tiene dónde ponerlo: solo existen `headers` y no hay ejemplo oficial con variables de entorno"
    return {"url": referencias(s["url"], "${{env:{}}}")}, None


def clasificar_mcp(mcp, traducir, archivo, clave):
    """({nombre: cfg} a escribir, pasos, avisos). `permitida` escribe; `confirmar` solo imprime el paso; `prohibida` avisa."""
    escribir, pasos, avisos = {}, [], []
    for s in mcp:
        if s["registrar"] == "prohibida":
            avisos.append(f"Servidor MCP «{s['nombre']}»: la política prohíbe registrarlo; no se genera nada.")
            continue
        cfg, motivo = traducir(s)
        if cfg is None:
            avisos.append(f"Servidor MCP «{s['nombre']}» no se genera: {motivo}.")
        elif s["registrar"] == "permitida":
            escribir[s["nombre"]] = cfg
        else:
            frag = json.dumps({clave: {s["nombre"]: cfg}}, ensure_ascii=False)
            pasos.append(f"Servidor MCP «{s['nombre']}»: la política pide confirmación (`registrar = \"confirmar\"`) y NO se escribió. "
                         f"Si lo quieres, agrega esto a `{archivo}`: {frag}  (las variables son referencias: defínelas en tu entorno, no pegues sus valores).")
    return escribir, pasos, avisos


def hooks_json(ruta_puente):
    """`.cursor/hooks.json` (FORMATO.md §3): `version`, `hooks`, hook de comando con `timeout` y `failClosed`."""
    doc = {"_generado_por_el_harness": fn.MARCA,
           "version": 1,
           "hooks": {"beforeShellExecution": [{"command": ruta_puente, "timeout": 30, "failClosed": True}]}}
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


class Cursor(ga.Adaptador):
    nombre = "cursor"
    codigo_matriz = "CU"
    comandos = ("cursor",)
    carpetas_home = (".cursor",)

    def capacidades(self):
        caps = super().capacidades()
        genera = {"Instrucciones del proyecto": "AGENTS.md lo genera el núcleo; Cursor lo lee sin configuración",
                  "Reglas por ruta": "solo una regla mínima `.cursor/rules/harness.mdc` con `alwaysApply: true`; sin `globs`",
                  "Hooks que bloquean": "`.cursor/hooks.json` con `failClosed: true`, solo si la política lo permite"}
        for k, v in caps.items():
            v["generado_por_este_adaptador"] = k in genera
            v["nota"] = genera.get(k, "no lo genera este adaptador (la fuente neutral aún no lo produce); no se promete")
        caps["Comandos propios"]["nota"] = ("no documentado hoy como ruta independiente: no se genera `.cursor/commands`; "
                                            "sustituto generado: skills `.cursor/skills/<n>/` con `disable-model-invocation: true`")
        caps["Skills"].update(generado_por_este_adaptador=True, nota="`.cursor/skills/<n>/SKILL.md` (FORMATO.md §5)")
        caps["MCP"].update(generado_por_este_adaptador=True, nota="`.cursor/mcp.json` solo con `registrar = \"permitida\"`; con `confirmar` se imprime el paso (FORMATO.md §6)")
        caps["Permisos / modos / sandbox"].update(generado_por_este_adaptador=True,
                                                  nota="`.cursor/cli.json` `permissions.deny` con `Shell(cmd)` de una palabra (FORMATO.md §7); `ask` y varias palabras se degradan; sin modos ni sandbox")
        return caps

    _sin_traducir = []
    _hay_allow = False

    def generar(self, fuente, destino, aplicar=False):
        self.avisos, self.pasos = [], []
        self._sin_traducir = list((fuente.get("permisos") or {}).get("no_traducible") or [])
        self._hay_allow = bool((fuente.get("permisos") or {}).get("allow"))
        self.control_hook_estado = self.control_hook_motivo = None
        plan = []
        agents = fuente.get("archivo_agents", fn.ARCHIVO_AGENTS)
        plan.append(fn.planificar_archivo(destino, RUTA_REGLA, REGLA_MDC.format(agents=agents)))

        if self.estado_hooks() != "si":
            archivos, motivo = [], f"la matriz no confirma hooks que bloquean para Cursor (estado «{self.estado_hooks()}»)"
        else:
            archivos, motivo = gh.archivos_de_hook(fuente)
        if archivos:
            for nombre, contenido, modo in archivos:
                plan.append(fn.planificar_archivo(destino, f"{RUTA_HOOKS}/{nombre}", contenido, modo=modo, respetar_manual=True))
            plan.append(fn.planificar_archivo(destino, RUTA_HOOKS_JSON, hooks_json(f"{RUTA_HOOKS}/{gh.PUENTE}")))
            self.control_hook_estado = "disponible"
            self.control_hook_motivo = ("hook `beforeShellExecution` con `failClosed: true` generado desde la política; Cursor recarga `.cursor/hooks.json` al guardar. "
                                        "Solo vigila los comandos de terminal del agente")
            self.pasos.append("Comprueba en Cursor (ajuste de hooks) que el hook aparece cargado. Requiere `python3`, `bash`, `jq` y `git` en el PATH.")
            self.pasos.append("La marca del harness va en la clave `_generado_por_el_harness` porque JSON no admite comentarios; la documentación no publica un esquema de "
                              "`hooks.json`, así que no está confirmado que Cursor ignore claves desconocidas: si lo rechaza, quita la clave (la instancia dejará de reconocer el archivo como propio).")
        else:
            self.control_hook_estado = "degradado"
            self.control_hook_motivo = motivo
            self.avisos.append(f"Sin hook de datos: {motivo}.")
        plan += self._capacidades(fuente, destino)
        self.pasos.append("Lo global (por ejemplo `~/.cursor/hooks.json` o `~/.cursor/permissions.json`) no se escribe: si lo quieres, hazlo tú.")
        for it in plan:
            if it.get("aviso"):
                self.avisos.append(it["aviso"])
        return fn.escribir_plan(destino, plan, aplicar)

    def _capacidades(self, fuente, destino):
        """Skills, comandos como skills, permisos de la CLI y MCP (R53-R55). Devuelve los ítems del plan."""
        plan = []
        nombres = {s["nombre"] for s in fuente.get("skills") or []}
        for s in fuente.get("skills") or []:
            plan.append(planificar_md(destino, f"{RUTA_SKILLS}/{s['nombre']}/SKILL.md", con_marca_md(s["contenido"])))
        for c in fuente.get("comandos") or []:
            if c["nombre"] in nombres:
                self.avisos.append(f"Comando «{c['nombre']}» no se genera como skill: ya existe una skill con ese nombre.")
                continue
            plan.append(planificar_md(destino, f"{RUTA_SKILLS}/{c['nombre']}/SKILL.md", con_marca_md(comando_como_skill(c))))
        manifiesto = leer_manifiesto(destino, RUTA_MANIFIESTO)
        nuevo = {}
        reglas, sin = reglas_shell(fuente.get("permisos") or {})
        self._permisos_sin_traducir = sin
        item, ent, av = fusionar_json(destino, RUTA_CLI, {"permissions.deny": reglas}, {}, {}, manifiesto.get(RUTA_CLI))
        if item:
            plan.append(item)
            nuevo[RUTA_CLI] = ent
            self.avisos += av
            if reglas:
                self.pasos.append(f"Revisa `{RUTA_CLI}`: el harness agregó `permissions.deny` de la CLI (lo manual se conserva). "
                                  "Aplica a la CLI de Cursor; el IDE no tiene una lista determinista (`permissions.json` es lenguaje natural).")
        escribir, pasos, avisos = clasificar_mcp(fuente.get("mcp") or [], servidor_cu, RUTA_MCP, "mcpServers")
        self.pasos += pasos
        self.avisos += avisos
        item, ent, av = fusionar_json(destino, RUTA_MCP, {}, {"mcpServers": escribir}, {}, manifiesto.get(RUTA_MCP))
        if item:
            plan.append(item)
            nuevo[RUTA_MCP] = ent
            self.avisos += av
            if escribir:
                self.pasos.append("Servidores MCP escritos en `.cursor/mcp.json`: revisa sus variables (referencias `${env:NOMBRE}`, sin valores); la CLI pide `--approve-mcps` o aprobación.")
        man = planificar_manifiesto(destino, RUTA_MANIFIESTO, nuevo)
        if man:
            plan.append(man)
        return plan

    _permisos_sin_traducir = []

    def degradaciones(self):
        base = super().degradaciones()
        f = FUENTE_CU
        base += [
            {"que_se_pierde": "El hook solo vigila `beforeShellExecution` (terminal del agente); no cubre lecturas, MCP ni lo que ocurra fuera del agente. Qué eventos corren en `agent -p` y en agentes en la nube no está confirmado",
             "imposicion_alternativa": "rol de solo lectura en la base de datos, credenciales de producción fuera del alcance del agente e integración continua con el mismo gate", "fuente": f},
            {"que_se_pierde": "`ask` en `preToolUse` no se aplica y en `subagentStart` se trata como `deny`; por eso el hook solo se registra en `beforeShellExecution`, donde `ask` sí es válido",
             "imposicion_alternativa": "lo que la política marca «confirmar» lo decide la persona en el diálogo de Cursor; lo crítico, denegar", "fuente": f},
            {"que_se_pierde": "No existe esquema publicado de `hooks.json`: la clave de marca `_generado_por_el_harness` no está confirmada como admitida",
             "imposicion_alternativa": "probar el archivo en Cursor; si lo rechaza, quitar la clave y mantener el control en la base de datos", "fuente": f},
            {"que_se_pierde": "Comandos propios: `.cursor/commands/` no está documentado hoy (solo `commands/` dentro de un plugin); el comando neutral se genera como skill con `disable-model-invocation: true`, que se invoca con `/nombre` pero no es un comando nativo y su cabecera solo conserva `description`",
             "imposicion_alternativa": "skills con `disable-model-invocation: true` (generadas por este adaptador)", "fuente": f},
            {"que_se_pierde": "`permissions.json` del IDE solo guarda instrucciones en lenguaje natural y Auto-review no es un límite de seguridad; los permisos deterministas (`.cursor/cli.json`) valen para la CLI, no para el IDE",
             "imposicion_alternativa": "permisos de la base de datos e integración continua; el hook `beforeShellExecution` para el IDE", "fuente": f},
            {"que_se_pierde": "Reglas por ruta (`globs`) no se generan: la fuente neutral no las produce y `globs` como lista YAML no tiene ejemplo oficial",
             "imposicion_alternativa": "instrucciones en AGENTS.md (anidados por carpeta) y el gate en integración continua", "fuente": f},
            {"que_se_pierde": "Subagentes y plugins están confirmados en FORMATO.md pero este adaptador no los genera",
             "imposicion_alternativa": "escribirlos a mano siguiendo cursor/FORMATO.md; el control real vive en la base de datos y la integración continua", "fuente": f},
            {"que_se_pierde": "`mcp.json`: la tabla de la documentación exige `type` pero los ejemplos oficiales lo omiten (se genera sin `type`); los remotos con `entorno` no se generan",
             "imposicion_alternativa": "probar el servidor con Cursor; las variables son solo referencias `${env:NOMBRE}`", "fuente": f},
            {"que_se_pierde": "Skills: Cursor también lee `.claude/skills/`, `.codex/skills/` y `.agents/skills/`; si otro adaptador escribe el mismo nombre allí no se confirma cuál prevalece",
             "imposicion_alternativa": "nombres propios del proyecto", "fuente": f},
        ]
        for p, accion, motivo in self._permisos_sin_traducir:
            base.append({"que_se_pierde": f"Regla `{accion}` sobre el prefijo «{p}» no se traduce a `permissions` de la CLI: {motivo}",
                         "imposicion_alternativa": "el hook `beforeShellExecution` (donde `ask` sí es válido) o lo decide la persona en el diálogo de Cursor", "fuente": f})
        for n in self._sin_traducir:
            base.append({"que_se_pierde": f"Regla «{n['regla']}» ({n['origen']}) no se traduce a `permissions` de la CLI: {n['motivo']}",
                         "imposicion_alternativa": "hook de datos o de commit generado desde la política, o rol de solo lectura en la base de datos", "fuente": f})
        if self._hay_allow:
            base.append({"que_se_pierde": "Las reglas `allow` de la política no se escriben en `permissions` (permitir no se amplía por defecto)",
                         "imposicion_alternativa": "ninguna necesaria: lo no listado sigue el modo de ejecución de Cursor", "fuente": f})
        if self.control_hook_estado == "degradado":
            base.append({"que_se_pierde": "El hook de datos no se generó en esta instancia",
                         "imposicion_alternativa": "rol de solo lectura en la base de datos y declarar `[[datos.ambientes]]` y `alcance.repos` en la política para generarlo",
                         "fuente": "instalador/generar-politicas.py"})
        return base


ADAPTADORES = [Cursor]
