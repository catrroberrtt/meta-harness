#!/usr/bin/env python3
"""Adaptador de OpenCode: AGENTS.md (ya lo lee) + plugin de bloqueo + skills, comandos, permisos y MCP desde la política.

Genera SOLO dentro de la instancia y SOLO lo «confirmado con fuente» en `opencode/FORMATO.md`:
  .opencode/plugins/guardia-datos.js   plugin con `tool.execute.before` que lanza una excepción para bloquear
  .opencode/guardia/*                  hook de datos generado por `instalador/generar-politicas.py` (se reutiliza) + puente
  .opencode/skills/<n>/SKILL.md        skills neutrales (FORMATO.md §5)
  .opencode/commands/<n>.md            comandos neutrales (FORMATO.md §4)
  opencode.json                        claves `permission.bash` (FORMATO.md §7) y `mcp` (§6, solo `registrar = "permitida"`), fusionadas con lo manual

El plugin no decide nada: ejecuta por subproceso el mismo hook que produce la política. Existe solo si la política permite
generarlo; si no, el control por hook queda «degradado» con el motivo. Nada global: lo global se imprime como paso.
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

RUTA_PLUGIN = ".opencode/plugins/guardia-datos.js"
RUTA_GUARDIA = ".opencode/guardia"
FUENTE_OC = "MATRIZ.md y opencode/FORMATO.md"
RUTA_SKILLS = ".opencode/skills"
RUTA_COMANDOS = ".opencode/commands"
RUTA_CONFIG = "opencode.json"
RUTA_CONFIG_JSONC = "opencode.jsonc"
RUTA_MANIFIESTO = ".opencode/harness-generado.json"
ESQUEMA = "https://opencode.ai/config.json"

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


def permisos_bash(permisos):
    """{patrón: acción} para `permission.bash` (FORMATO.md §7). «El último que coincide gana»: primero `ask`, al final `deny`.
    Cada prefijo literal se escribe como `prefijo *` y como `prefijo` (el comando solo): nunca un patrón más amplio."""
    out = {}
    for accion in ("ask", "deny"):
        for p in permisos.get(accion) or []:
            out[f"{p} *"] = accion
            out[p] = accion
    return out


def servidor_oc(s):
    """(configuración de `mcp.<nombre>`, None) o (None, motivo). Referencias con `{env:VAR}`, nunca el valor."""
    if s["tipo"] == "local":
        cfg = {"type": "local", "command": [referencias(x, "{{env:{}}}") for x in [s["comando"]] + list(s["args"])], "enabled": True}
        if s["entorno"]:
            cfg["environment"] = {e["clave"]: "{env:" + e["variable"] + "}" for e in s["entorno"]}
        return cfg, None
    if s["entorno"]:
        return None, "un servidor remoto con `entorno` no tiene dónde ponerlo: el esquema solo admite `headers`, y la interpolación en ellos no está confirmada"
    return {"type": "remote", "url": referencias(s["url"], "{{env:{}}}"), "enabled": True}, None


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


PLUGIN_JS = '''// __MARCA__
// Plugin de OpenCode (FORMATO.md §3): `tool.execute.before` lanza una excepción para bloquear.
// No decide nada: ejecuta por subproceso el hook de datos generado desde la política (.opencode/guardia/).
import { spawnSync } from "node:child_process"
import path from "node:path"

export const GuardiaDatos = async ({ directory }) => {
  const puente = path.join(directory, ".opencode", "guardia", "guardia-datos.py")
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool !== "bash") return
      const command = output && output.args && output.args.command
      if (typeof command !== "string" || command === "") return
      const r = spawnSync("python3", [puente, "--formato", "opencode"], {
        input: JSON.stringify({ command, cwd: directory }),
        encoding: "utf8",
        timeout: 30000,
      })
      let veredicto = null
      try { veredicto = JSON.parse(r.stdout) } catch (e) { veredicto = null }
      if (r.status === 0 && veredicto && veredicto.decision === "allow") return
      const motivo = (veredicto && veredicto.reason) || (r.error && String(r.error)) || (r.stderr || "sin detalle")
      if (veredicto && veredicto.decision === "ask") {
        throw new Error("Requiere confirmación de la persona (este plugin no puede pedirla): " + motivo)
      }
      throw new Error(motivo)
    },
  }
}
'''


class OpenCode(ga.Adaptador):
    nombre = "opencode"
    codigo_matriz = "OC"
    comandos = ("opencode",)
    carpetas_home = (".config/opencode",)

    _no_traducible = []

    def capacidades(self):
        caps = super().capacidades()
        genera = {"Instrucciones del proyecto": "AGENTS.md lo genera el núcleo; OpenCode lo lee sin configuración",
                  "Hooks que bloquean": "plugin `.opencode/plugins/guardia-datos.js`, solo si la política lo permite",
                  "Comandos propios": "`.opencode/commands/<n>.md` (FORMATO.md §4)",
                  "Skills": "`.opencode/skills/<n>/SKILL.md` (FORMATO.md §5)",
                  "MCP": "clave `mcp` de `opencode.json` solo con `registrar = \"permitida\"`; con `confirmar` se imprime el paso (FORMATO.md §6)",
                  "Permisos / modos / sandbox": "clave `permission.bash` de `opencode.json` con `ask`/`deny` por prefijo literal (FORMATO.md §7); sin modos ni agentes"}
        for k, v in caps.items():
            v["generado_por_este_adaptador"] = k in genera
            v["nota"] = genera.get(k, "no lo genera este adaptador; no se promete")
        return caps

    def generar(self, fuente, destino, aplicar=False):
        self.avisos, self.pasos = [], []
        self.control_hook_estado = self.control_hook_motivo = None
        self._no_traducible = list((fuente.get("permisos") or {}).get("no_traducible") or [])
        plan = []
        if self.estado_hooks() != "si":
            archivos, motivo = [], f"la matriz no confirma hooks que bloquean para OpenCode (estado «{self.estado_hooks()}»)"
        else:
            archivos, motivo = gh.archivos_de_hook(fuente)
        if archivos:
            for nombre, contenido, modo in archivos:
                plan.append(fn.planificar_archivo(destino, f"{RUTA_GUARDIA}/{nombre}", contenido, modo=modo, respetar_manual=True))
            plan.append(fn.planificar_archivo(destino, RUTA_PLUGIN, PLUGIN_JS.replace("__MARCA__", fn.MARCA), respetar_manual=True))
            self.control_hook_estado = "disponible"
            self.control_hook_motivo = ("plugin generado desde la política; bloquea lanzando una excepción en `tool.execute.before` y solo vigila la herramienta `bash`. "
                                        "Que un plugin que falla bloquee está respaldado por el código de la rama `dev`, no por la documentación")
            self.pasos.append("Reinicia OpenCode en esta carpeta: carga `.opencode/plugins/` del proyecto. Requiere `python3`, `bash`, `jq` y `git` en el PATH.")
            self.pasos.append("Antes de depender del plugin, pruébalo con el agente real: la documentación no dice qué pasa si un plugin falla (FORMATO.md §3).")
        else:
            self.control_hook_estado = "degradado"
            self.control_hook_motivo = motivo
            self.avisos.append(f"Sin hook de datos: {motivo}.")
        plan += self._capacidades(fuente, destino)
        self.pasos.append("Lo global (por ejemplo `~/.config/opencode/AGENTS.md` o `~/.config/opencode/plugins/`) no se escribe: si lo quieres, hazlo tú.")
        for it in plan:
            if it.get("aviso"):
                self.avisos.append(it["aviso"])
        return fn.escribir_plan(destino, plan, aplicar)

    def _capacidades(self, fuente, destino):
        """Skills, comandos, permisos y MCP (R53-R55). Devuelve los ítems del plan; avisos y pasos quedan en `self`."""
        plan = []
        for s in fuente.get("skills") or []:
            plan.append(planificar_md(destino, f"{RUTA_SKILLS}/{s['nombre']}/SKILL.md", con_marca_md(s["contenido"])))
        for c in fuente.get("comandos") or []:
            plan.append(planificar_md(destino, f"{RUTA_COMANDOS}/{c['nombre']}.md", con_marca_md(c["contenido"])))
        manifiesto = leer_manifiesto(destino, RUTA_MANIFIESTO)
        escribir, pasos, avisos = clasificar_mcp(fuente.get("mcp") or [], servidor_oc, RUTA_CONFIG, "mcp")
        self.pasos += pasos
        self.avisos += avisos
        claves = {"permission.bash": permisos_bash(fuente.get("permisos") or {}), "mcp": escribir}
        forzar = None
        if fn._dentro(destino, RUTA_CONFIG_JSONC).exists() and not fn._dentro(destino, RUTA_CONFIG).exists():
            forzar = "no existe pero hay un `opencode.jsonc` (admite comentarios y no se reescribe)"
        item, ent, av = fusionar_json(destino, RUTA_CONFIG, {}, claves, {"$schema": ESQUEMA}, manifiesto.get(RUTA_CONFIG),
                                      comodin=("permission.bash",), forzar_alterno=forzar)
        nuevo = {}
        if item:
            plan.append(item)
            nuevo[RUTA_CONFIG] = ent
            self.avisos += av
            if claves["permission.bash"] or escribir:
                self.pasos.append(f"Revisa `{RUTA_CONFIG}`: el harness agregó `permission.bash` y `mcp` (lo manual se conserva; el archivo se reescribe con sangría de 2 espacios). "
                                  "Reinicia OpenCode en esta carpeta.")
        man = planificar_manifiesto(destino, RUTA_MANIFIESTO, nuevo)
        if man:
            plan.append(man)
        return plan

    def degradaciones(self):
        base = super().degradaciones()
        f = FUENTE_OC
        base += [
            {"que_se_pierde": "El plugin solo vigila la herramienta `bash`; no lo que se haga con otras herramientas ni fuera del agente. Que `tool.execute.before` se dispare para MCP, recursos MCP y `task` está confirmado solo en el código de `dev`, no en la documentación",
             "imposicion_alternativa": "rol de solo lectura en la base de datos y credenciales de producción fuera del alcance del agente", "fuente": f},
            {"que_se_pierde": "El plugin no puede pedir confirmación (no hay `ask` en `tool.execute.before`): lo que la política marca «confirmar» se bloquea; `permission.asked` no está documentado como vía para denegar",
             "imposicion_alternativa": "que la persona corra ella el comando, o declarar el host en la política; permisos `ask` en `opencode.json` (no generados por este adaptador)", "fuente": f},
            {"que_se_pierde": "Que un plugin que falla bloquee (cerrado) no es un contrato documentado, solo comportamiento observado en el código",
             "imposicion_alternativa": "probarlo con el agente real y mantener el rol de solo lectura en la base de datos", "fuente": f},
            {"que_se_pierde": "Reglas por ruta: OpenCode no tiene activación según la ruta editada (`instructions` carga siempre; `@archivo` dentro de AGENTS.md no se expande solo)",
             "imposicion_alternativa": "instrucciones en AGENTS.md y el gate en integración continua", "fuente": f},
            {"que_se_pierde": "`opencode run` sin `--auto` ante un permiso `ask` y sus códigos de salida no están documentados",
             "imposicion_alternativa": "integración continua obligatoria con el mismo gate; no depender del código de salida de `opencode run`", "fuente": f},
            {"que_se_pierde": "Subagentes (`.opencode/agents/`) y `permission` de otras herramientas (`edit`, `webfetch`…) están confirmados en FORMATO.md pero este adaptador no los genera",
             "imposicion_alternativa": "escribirlos a mano siguiendo opencode/FORMATO.md", "fuente": f},
            {"que_se_pierde": "`permission.bash` solo traduce `ask` y `deny` por prefijo literal; cada prefijo se escribe como `prefijo *` y como `prefijo` (nunca un patrón más amplio). El comodín exige el espacio; no se confirma que `prefijo *` cubra el comando sin argumentos, por eso va también solo. Las reglas `allow` de la política no se escriben",
             "imposicion_alternativa": "el plugin de bloqueo y la integración continua con el mismo gate", "fuente": f},
            {"que_se_pierde": "MCP: la interpolación `{env:VAR}` está documentada de forma general en `config`, sin ejemplo dentro de `mcp.*`; los remotos con `entorno` no se generan (el esquema solo admite `headers`)",
             "imposicion_alternativa": "probar el servidor con el agente real; las variables son solo referencias", "fuente": f},
            {"que_se_pierde": "Skills: OpenCode también lee `.claude/skills/` y `.agents/skills/`; si otro adaptador escribe el mismo nombre allí no se confirma cuál prevalece. Un comando manual con el mismo nombre deja `<n>.generado.md`, que aparecería como otro comando",
             "imposicion_alternativa": "borrar el `.generado.md` tras revisarlo; nombres propios del proyecto", "fuente": f},
        ]
        for n in self._no_traducible:
            base.append({"que_se_pierde": f"Regla «{n['regla']}» ({n['origen']}) no se traduce a `permission.bash`: {n['motivo']}",
                         "imposicion_alternativa": "plugin de bloqueo o hook de commit generado desde la política, o rol de solo lectura en la base de datos", "fuente": f})
        if self.control_hook_estado == "degradado":
            base.append({"que_se_pierde": "El plugin de bloqueo de datos no se generó en esta instancia",
                         "imposicion_alternativa": "rol de solo lectura en la base de datos y declarar `[[datos.ambientes]]` y `alcance.repos` en la política para generarlo",
                         "fuente": "instalador/generar-politicas.py"})
        return base


ADAPTADORES = [OpenCode]
