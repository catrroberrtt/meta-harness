#!/usr/bin/env python3
"""Adaptador de Claude Code: CLAUDE.md mínimo, hooks de ejemplo, skills, comandos, permisos y MCP generados desde la política.

Genera SOLO dentro de la instancia y SOLO lo confirmado en MATRIZ.md (Claude Code):
  CLAUDE.md                          marca + `@AGENTS.md` (importación; MATRIZ.md §1)
  .claude/hooks/<hook>.sh            hooks que produce `instalador/generar-politicas.py` (se reutiliza, no se reescribe)
  .claude/settings.ejemplo.json      bloque `hooks` de ejemplo para el `.claude/settings.json` de proyecto
  .claude/skills/<n>/SKILL.md        skills neutrales (MATRIZ.md §6)
  .claude/commands/<n>.md            comandos neutrales (MATRIZ.md §5: `.claude/commands/*.md`, heredado)
  .claude/settings.json              clave `permissions` (`deny`/`ask`, reglas `Bash(prefijo *)`; MATRIZ.md §9), fusionada con lo manual
  .mcp.json                          clave `mcpServers`, SOLO con `registrar = "permitida"` (MATRIZ.md §7); con "confirmar" se imprime el paso

Los hooks no se registran: `settings.ejemplo.json` NO es `settings.json`; la persona lo revisa y lo copia. Nada global.
"""
import copy
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
NUCLEO = AQUI.parent / "nucleo"
if str(NUCLEO) not in sys.path:
    sys.path.insert(0, str(NUCLEO))
import fuente_neutral as fn  # noqa: E402
import generar_agentes as ga  # noqa: E402

RUTA_HOOKS = ".claude/hooks"
RUTA_EJEMPLO = ".claude/settings.ejemplo.json"
HOOK_PRINCIPAL = "block-db-access.sh"
CLAUDE_MD = f"<!-- {fn.MARCA} -->\n@{{agents}}\n"
RUTA_SKILLS = ".claude/skills"
RUTA_COMANDOS = ".claude/commands"
RUTA_SETTINGS = ".claude/settings.json"
RUTA_MCP = ".mcp.json"
RUTA_MANIFIESTO = ".claude/harness-generado.json"


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


def reglas_bash(prefijos):
    """`Bash(prefijo *)` (forma de MATRIZ.md §9) y `Bash(prefijo)` (el comando solo): ambas igual o más estrechas que el prefijo; nunca más amplias."""
    out = []
    for p in prefijos:
        out += [f"Bash({p} *)", f"Bash({p})"]
    return out


def servidor_cc(s):
    """(configuración de `.mcp.json`, None) o (None, motivo). Las variables van como referencia `${VAR}`, jamás su valor."""
    if s["tipo"] == "local":
        cfg = {"type": "stdio", "command": s["comando"], "args": list(s["args"])}
        if s["entorno"]:
            cfg["env"] = {e["clave"]: "${" + e["variable"] + "}" for e in s["entorno"]}
        return cfg, None
    if s["entorno"]:
        return None, "un servidor remoto con `entorno` no tiene dónde ponerlo en `.mcp.json` según MATRIZ.md (no se confirma `headers` ni su interpolación)"
    return {"type": "http", "url": s["url"]}, None


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


def _cargar_generador(harness_raiz):
    ruta = Path(harness_raiz) / "instalador" / "generar-politicas.py"
    spec = importlib.util.spec_from_file_location("generar_politicas", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def con_marca(contenido):
    """Los archivos que produce el generador de políticas pueden no traer la marca: se la agrega tras el shebang."""
    if fn.es_generado(contenido):
        return contenido
    primera, _, resto = contenido.partition("\n")
    if primera.startswith("#!"):
        return f"{primera}\n# {fn.MARCA}\n{resto}"
    return f"# {fn.MARCA}\n{contenido}"


def bloque_hooks(ruta_hook):
    """Bloque `hooks` de Claude Code (MATRIZ.md §3): PreToolUse con `command`; el hook decide deny/ask/allow."""
    return {"_generado_por_el_harness": fn.MARCA + ". Copia solo la clave `hooks` a .claude/settings.json",
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": ruta_hook}]}]}}


class ClaudeCode(ga.Adaptador):
    nombre = "claude-code"
    codigo_matriz = "CC"
    comandos = ("claude",)
    carpetas_home = (".claude",)

    _no_traducible, _hay_allow = [], False

    def capacidades(self):
        caps = super().capacidades()
        genera = {"Instrucciones del proyecto": "CLAUDE.md mínimo con `@AGENTS.md` (MATRIZ.md §1)",
                  "Hooks que bloquean": "bloque de ejemplo + hooks generados; no se registran solos",
                  "Comandos propios": "`.claude/commands/<n>.md` (ubicación confirmada en MATRIZ.md §5; solo se usa `description`, el resto de la cabecera no está en la matriz)",
                  "Skills": "`.claude/skills/<n>/SKILL.md` (MATRIZ.md §6)",
                  "MCP": "`.mcp.json` solo con `registrar = \"permitida\"`; con `confirmar` se imprime el paso",
                  "Permisos / modos / sandbox": "`permissions.deny`/`ask` en `.claude/settings.json` (reglas `Bash(prefijo *)`, MATRIZ.md §9); sin modos ni sandbox"}
        for k, v in caps.items():
            v["generado_por_este_adaptador"] = k in genera
            v["nota"] = genera.get(k, "no lo genera este adaptador; no se promete")
        return caps

    def generar(self, fuente, destino, aplicar=False):
        self.avisos, self.pasos = [], []
        self.control_hook_estado = self.control_hook_motivo = None
        permisos = fuente.get("permisos") or {}
        self._no_traducible = list(permisos.get("no_traducible") or [])
        self._hay_allow = bool(permisos.get("allow"))
        plan = []
        agents = fuente.get("archivo_agents", fn.ARCHIVO_AGENTS)
        plan.append(fn.planificar_archivo(destino, "CLAUDE.md", CLAUDE_MD.format(agents=agents)))

        hooks_ok, motivo = False, None
        if self.estado_hooks() != "si":
            motivo = f"la matriz no confirma hooks que bloquean para Claude Code (estado «{self.estado_hooks()}»)"
        else:
            gen = _cargar_generador(fuente["harness_raiz"])
            try:
                politica = gen.cargar(fuente["politica_ruta"])
                gen.construir(politica, fuente["politica_ruta"])          # valida sin escribir
                with tempfile.TemporaryDirectory(prefix="mh-hooks-") as tmp:
                    for ruta in gen.generar(fuente["politica_ruta"], tmp):
                        contenido = con_marca(Path(ruta).read_text(encoding="utf-8"))
                        plan.append(fn.planificar_archivo(destino, f"{RUTA_HOOKS}/{Path(ruta).name}", contenido,
                                                          modo=0o755, respetar_manual=True))
                hooks_ok = True
            except gen.ErrorPolitica as e:
                motivo = f"la política aún no permite generar el hook de datos: {str(e).splitlines()[0].rstrip(".")}"
            except (OSError, KeyError) as e:
                motivo = f"no se pudo generar el hook de datos: {e}"
        if hooks_ok:
            ejemplo = json.dumps(bloque_hooks(f"{RUTA_HOOKS}/{HOOK_PRINCIPAL}"), ensure_ascii=False, indent=2) + "\n"
            plan.append(fn.planificar_archivo(destino, RUTA_EJEMPLO, ejemplo))
            self.control_hook_estado = "disponible"
            self.control_hook_motivo = ("hook generado desde la política; actúa solo después de que la persona lo registre en "
                                        ".claude/settings.json, y solo vigila acciones hechas por las herramientas del agente")
            self.pasos.append(f"Revisa `{RUTA_EJEMPLO}` y copia su clave `hooks` al `.claude/settings.json` de proyecto (el adaptador no lo escribe). "
                              "La forma de la ruta del comando (relativa) no está verificada en MATRIZ.md: contrástala con la documentación de hooks.")
        else:
            self.control_hook_estado = "degradado"
            self.control_hook_motivo = motivo
            self.avisos.append(f"Sin hook de datos: {motivo}.")
        plan += self._capacidades(fuente, destino)
        self.pasos.append("Lo global (por ejemplo `~/.claude/CLAUDE.md` o `~/.claude/settings.json`) no se escribe: si lo quieres, hazlo tú.")
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
        nuevo = {}
        perm = fuente.get("permisos") or {}
        listas = {"permissions.deny": reglas_bash(perm.get("deny") or []), "permissions.ask": reglas_bash(perm.get("ask") or [])}
        item, ent, av = fusionar_json(destino, RUTA_SETTINGS, listas, {}, {}, manifiesto.get(RUTA_SETTINGS))
        if item:
            plan.append(item)
            nuevo[RUTA_SETTINGS] = ent
            self.avisos += av
            if any(listas.values()):
                self.pasos.append(f"Revisa `{RUTA_SETTINGS}`: el harness agregó `permissions.deny`/`ask` (lo manual se conserva). "
                                  "Es el control del propio agente; confirma con la documentación de permisos que el prefijo cubre las variantes que te importan.")
        escribir, pasos, avisos = clasificar_mcp(fuente.get("mcp") or [], servidor_cc, RUTA_MCP, "mcpServers")
        self.pasos += pasos
        self.avisos += avisos
        item, ent, av = fusionar_json(destino, RUTA_MCP, {}, {"mcpServers": escribir}, {}, manifiesto.get(RUTA_MCP))
        if item:
            plan.append(item)
            nuevo[RUTA_MCP] = ent
            self.avisos += av
            if escribir:
                self.pasos.append("Servidores MCP escritos en `.mcp.json`: Claude Code te pedirá aprobarlos al abrir el proyecto; revisa sus variables de entorno (referencias, sin valores).")
        man = planificar_manifiesto(destino, RUTA_MANIFIESTO, nuevo)
        if man:
            plan.append(man)
        return plan

    def degradaciones(self):
        base = super().degradaciones()
        base += [
            {"que_se_pierde": "Un hook solo vigila lo que el agente hace con sus herramientas; no lo que ocurre fuera de él, ni el sandbox cubre herramientas de archivos, MCP ni hooks",
             "imposicion_alternativa": "rol de solo lectura en la base de datos y credenciales de producción fuera del alcance del agente", "fuente": FUENTE_CC},
            {"que_se_pierde": "Con `-p` sin `--bare` se ejecutan los hooks del repositorio sin diálogo de confianza",
             "imposicion_alternativa": "protección de ramas, hooks de git e integración continua con el mismo gate", "fuente": FUENTE_CC},
        ]
        for n in self._no_traducible:
            base.append({"que_se_pierde": f"Regla «{n['regla']}» ({n['origen']}) no se traduce a `permissions`: {n['motivo']}",
                         "imposicion_alternativa": "hook de datos o de commit generado desde la política, o rol de solo lectura en la base de datos", "fuente": FUENTE_PERMISOS})
        base += [
            {"que_se_pierde": "Solo se traducen `deny` y `ask` a `permissions`; las reglas `allow` de la política no se escriben (permitir no se amplía por defecto)" if self._hay_allow else
                              "Sintaxis de `Bash(prefijo *)`: MATRIZ.md confirma el ejemplo `Bash(git diff *)`, pero no si el prefijo cubre rutas absolutas, envoltorios (`sh -c`), `env VAR=…` ni comandos encadenados; por eso se escriben las dos formas (`prefijo *` y `prefijo`) y nunca un patrón más amplio",
             "imposicion_alternativa": "el hook de datos y la integración continua con el mismo gate", "fuente": FUENTE_PERMISOS},
            {"que_se_pierde": "`.mcp.json`: MATRIZ.md confirma el archivo, la clave `mcpServers` y los transportes http y stdio, pero no la expansión `${VAR}` en `env`, el valor `type` de cada transporte ni que un remoto sea http y no sse",
             "imposicion_alternativa": "contrastar con la documentación de MCP de Claude Code antes de registrar; las variables son solo referencias", "fuente": FUENTE_MCP},
            {"que_se_pierde": "Comandos: de `.claude/commands/*.md` MATRIZ.md confirma la ruta, no los campos de la cabecera (solo se usa `description`); si existe un comando escrito a mano con el mismo nombre se genera `<n>.generado.md` y aparecería como otro comando",
             "imposicion_alternativa": "borrar el `.generado.md` tras revisarlo", "fuente": FUENTE_CC_CAP},
            {"que_se_pierde": "Skills y comandos del mismo nombre en otras ubicaciones (por ejemplo `~/.claude/skills`) no se revisan; la precedencia entre alcances no está en la matriz",
             "imposicion_alternativa": "usar nombres propios del proyecto", "fuente": FUENTE_CC_CAP},
        ]
        if self.control_hook_estado == "degradado":
            base.append({"que_se_pierde": "El hook de datos no se generó en esta instancia",
                         "imposicion_alternativa": "rol de solo lectura en la base de datos y declarar `[[datos.ambientes]]` y `alcance.repos` en la política para generarlo",
                         "fuente": "instalador/generar-politicas.py"})
        return base


FUENTE_CC = "MATRIZ.md, «Qué se pierde sin hooks» (Claude Code)"
FUENTE_PERMISOS = "MATRIZ.md §9 (Claude Code)"
FUENTE_MCP = "MATRIZ.md §7 (Claude Code)"
FUENTE_CC_CAP = "MATRIZ.md §5 y §6 (Claude Code)"
ADAPTADORES = [ClaudeCode]
