#!/usr/bin/env python3
"""Fuente neutral de instrucciones para agentes (R53) y escritura segura dentro de la instancia.

Construye, desde una INSTANCIA del harness, una estructura independiente del agente:
cómo orientarse, cuándo leer qué, reglas duras (tomadas de `politicas.toml`, no escritas a mano),
comandos del gate, lo que no se debe hacer y qué herramientas del harness existen.
Con ella se renderiza `AGENTS.md` desde `plantillas/AGENTS.md.tpl`.

- Solo biblioteca estándar. No usa red ni git. Escribe SOLO dentro de la instancia y SOLO con `aplicar=True`.
- Idempotente: no incluye fechas ni nada que cambie entre ejecuciones sobre las mismas entradas.
- Un archivo escrito a mano (sin la marca) nunca se pisa: se escribe `<nombre>.generado.<ext>` y se avisa.
"""
import json
import os
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capacidades_comunes as cc  # noqa: E402

RAIZ_HARNESS = Path(__file__).resolve().parents[2]
MARCA = "generado por el harness: no editar a mano; editar la política o las convenciones y regenerar"
MARCAS_DE_GENERADO = (MARCA.lower(), "generado por instalador/generar-politicas.py", "generado por el harness")
ARCHIVO_AGENTS = "AGENTS.md"
PERMISOS = ("permitida", "confirmar", "prohibida")


class ErrorInstancia(Exception):
    """La carpeta no es una instancia utilizable (falta política o convenciones, TOML inválido…)."""


# ----------------------------------------------------------------------------- lectura de la instancia
def _toml(ruta, que):
    try:
        with open(ruta, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        raise ErrorInstancia(f"Falta {que} en la instancia: {ruta}")
    except tomllib.TOMLDecodeError as e:
        raise ErrorInstancia(f"{que} no es TOML válido ({ruta}): {e}")


def _sin_definir(valor):
    """True si el valor está 'por definir' / es un {{marcador}} / está vacío."""
    if valor is None:
        return True
    t = str(valor).strip()
    return t == "" or "por definir" in t.lower() or "por declarar" in t.lower() or bool(re.fullmatch(r"\{\{.*\}\}", t))


def _frase_permiso(valor):
    return {"permitida": "permitido", "confirmar": "solo con confirmación explícita y puntual de la persona",
            "prohibida": "prohibido para el agente (lo corre la persona)"}.get(valor, f"sin declarar ({valor!r})" if valor else "sin declarar")


def _lista(v):
    return [str(x) for x in v] if isinstance(v, list) else []


# ----------------------------------------------------------------------------- reglas desde la política
def reglas_desde_politica(p):
    """Lista de dicts {tema, texto, origen, permiso}; el orden es el de la política, determinista."""
    reglas = []

    def add(tema, texto, origen, permiso=None):
        reglas.append({"tema": tema, "texto": texto, "origen": origen, "permiso": permiso})

    datos = p.get("datos") or {}
    ambientes = datos.get("ambientes") or []
    for a in ambientes:
        perm = a.get("permisos") or {}
        trozos = [f"{k} {_frase_permiso(perm.get(k))}" for k in ("lectura", "escritura", "ddl", "migraciones")]
        add("Datos", f"Ambiente «{a.get('nombre', '?')}» (tipo {a.get('tipo', '?')}): " + "; ".join(trozos) + ".",
            "datos.ambientes")
    if datos.get("hosts_locales"):
        add("Datos", "Solo cuentan como base local estos hosts: " + ", ".join(f"`{h}`" for h in _lista(datos["hosts_locales"]))
            + ". Todo otro host es remoto.", "datos.hosts_locales")
    if datos.get("lectura_host_remoto"):
        add("Datos", f"Leer un host remoto: {_frase_permiso(datos['lectura_host_remoto'])}.", "datos.lectura_host_remoto", datos["lectura_host_remoto"])
    if datos.get("lectura_host_no_resuelto"):
        add("Datos", f"Leer cuando el host no se puede resolver (variable o sin indicar): {_frase_permiso(datos['lectura_host_no_resuelto'])}.",
            "datos.lectura_host_no_resuelto", datos["lectura_host_no_resuelto"])
    if datos.get("escritura_fuera_de_ambiente_de_escritura"):
        add("Datos", f"Escribir fuera del ambiente de escritura declarado: {_frase_permiso(datos['escritura_fuera_de_ambiente_de_escritura'])}.",
            "datos.escritura_fuera_de_ambiente_de_escritura", datos["escritura_fuera_de_ambiente_de_escritura"])
    for c in datos.get("comandos") or []:
        add("Datos", f"Comando vigilado «{c.get('nombre', '?')}»: {c.get('motivo', '')}".rstrip() + ".", "datos.comandos", c.get("accion", "prohibida"))

    git = p.get("git") or {}
    ramas = _lista(git.get("ramas_protegidas"))
    if ramas:
        add("Git", "Ramas protegidas: " + ", ".join(f"`{r}`" for r in ramas) + ".", "git.ramas_protegidas")
    if git.get("aprueba"):
        add("Git", f"Aprueba un merge o despliegue a una rama protegida: {git['aprueba']}.", "git.aprueba")
    if git.get("confirmar"):
        add("Git", "Piden confirmación explícita: " + ", ".join(f"`{x}`" for x in _lista(git["confirmar"])) + ".", "git.confirmar", "confirmar")
    for clave, que in (("push_a_rama_protegida", "Push a una rama protegida"), ("merge_a_rama_de_produccion", "Merge a una rama de producción")):
        if git.get(clave):
            add("Git", f"{que}: {_frase_permiso(git[clave])}.", f"git.{clave}", git[clave])

    cmd = p.get("comandos") or {}
    nombres = {"instalar": "Instalar dependencias o herramientas", "build": "Compilar / empaquetar", "test": "Correr pruebas",
               "servidor_de_desarrollo": "Levantar servidores de desarrollo", "formateo_global": "Formateo global del código"}
    for clave, que in nombres.items():
        t = cmd.get(clave)
        if isinstance(t, dict) and t.get("accion"):
            add("Comandos", f"{que}: {_frase_permiso(t['accion'])}.", f"comandos.{clave}", t["accion"])

    dep = p.get("despliegue") or {}
    if dep.get("accion"):
        add("Despliegue", f"Desplegar: {_frase_permiso(dep['accion'])}.", "despliegue.accion", dep["accion"])
    if dep.get("produccion"):
        add("Despliegue", f"Desplegar a producción: {_frase_permiso(dep['produccion'])}.", "despliegue.produccion", dep["produccion"])

    cos = p.get("costos") or {}
    if cos.get("anunciar_antes"):
        add("Costos", "Antes de cualquier operación que cobre, anuncia: llamadas, ambiente o cuenta, costo por llamada y tope.", "costos.anunciar_antes")
    if cos.get("operaciones_que_cobran"):
        add("Costos", "Operaciones que cobran: " + ", ".join(_lista(cos["operaciones_que_cobran"])) + ".", "costos.operaciones_que_cobran")
    for clave, que in (("produccion_escritura_invocacion_envio", "Escribir, invocar o enviar en producción"),
                       ("lecturas_de_nube", "Leer recursos de la nube (listar, describir, descargar)"),
                       ("bucles_o_paralelismo_sobre_pago", "Bucles o paralelismo sobre un servicio de pago")):
        if cos.get(clave):
            add("Costos", f"{que}: {_frase_permiso(cos[clave])}.", f"costos.{clave}", cos[clave])
    if isinstance(cos.get("tope_de_llamadas_por_pasada"), int) and cos["tope_de_llamadas_por_pasada"] > 0:
        add("Costos", f"Tope de llamadas por pasada: {cos['tope_de_llamadas_por_pasada']}.", "costos.tope_de_llamadas_por_pasada")

    sec = p.get("secretos") or {}
    if sec.get("rutas_prohibidas_en_commit"):
        add("Secretos", "No se confirman (commit) archivos como: " + ", ".join(f"`{r}`" for r in _lista(sec["rutas_prohibidas_en_commit"])) + ".",
            "secretos.rutas_prohibidas_en_commit", "prohibida")
    for clave, que in (("imprimir_secretos", "Imprimir secretos"), ("pii_en_documentacion", "Datos personales en la documentación")):
        if sec.get(clave):
            add("Secretos", f"{que}: {_frase_permiso(sec[clave])}.", f"secretos.{clave}", sec[clave])

    ver = p.get("verificacion") or {}
    textos = {"evidencia_de_datos": "No des un veredicto sobre cifras sin mostrar la consulta real que lo respalda",
              "visual": "Abre y captura las pantallas antes de reportar un cambio de interfaz como listo",
              "estructura_de_modulos": "Mide la estructura del módulo con el motor de auditoría antes de cerrarlo"}
    for clave, texto in textos.items():
        if ver.get(clave):
            add("Verificación", f"{texto} ({ver[clave]}).", f"verificacion.{clave}")
    if ver.get("reporte_sin_prueba"):
        add("Verificación", f"Reportar «listo / correcto / verificado» sin un resultado observable: {_frase_permiso(ver['reporte_sin_prueba'])}.",
            "verificacion.reporte_sin_prueba", ver["reporte_sin_prueba"])
    return reglas


def pendientes_de_declarar(p, conv):
    out = []
    if not (p.get("datos") or {}).get("ambientes"):
        out.append("Ambientes de datos: `politicas.toml` no declara ninguno (`[[datos.ambientes]]`); no se asume ninguno.")
    git = p.get("git") or {}
    if not git.get("ramas_protegidas"):
        out.append("Ramas protegidas: sin declarar (`git.ramas_protegidas`).")
    if not git.get("aprueba"):
        out.append("Quién aprueba un merge o despliegue a rama protegida: sin declarar (`git.aprueba`).")
    cos = p.get("costos") or {}
    if "costos" in p and not cos.get("operaciones_que_cobran"):
        out.append("Servicios de pago: sin declarar (`costos.operaciones_que_cobran`); ante la duda, pregunta.")
    if "costos" in p and not cos.get("cuentas_de_produccion"):
        out.append("Cuentas de producción: sin declarar (`costos.cuentas_de_produccion`).")
    if "costos" in p and cos.get("tope_de_llamadas_por_pasada", 0) == 0:
        out.append("Tope de llamadas por pasada: sin declarar (0); pregunta antes de operaciones que cobran.")
    if not (p.get("alcance") or {}).get("repos"):
        out.append("Repos vigilados por los hooks: sin declarar (`alcance.repos`).")
    sin = [k for k, v in conv.items() if k != "gate.comando" and _sin_definir(v)]
    if sin:
        out.append("Convenciones por resolver antes de cerrar el primer cambio: " + ", ".join(f"`{k}`" for k in sin) + ".")
    if _sin_definir(conv.get("gate.comando")):
        out.append("Comando del gate (`gate.comando` en `convenciones.toml`): por definir.")
    return out


# ----------------------------------------------------------------------------- herramientas del harness
def herramientas_del_harness(harness_raiz):
    """[(ruta relativa a la raíz del harness, descripción)] leyendo la 1.ª línea del docstring de cada herramienta."""
    out = []
    d = Path(harness_raiz) / "herramientas"
    if d.is_dir():
        for f in sorted(d.glob("*.py")):
            desc = ""
            try:
                m = re.search(r'^(?:#![^\n]*\n)?\s*[rR]?"""(.*?)(?:\n|""")', f.read_text(encoding="utf-8"), re.S)
                if m:
                    desc = m.group(1).strip()
            except OSError:
                pass
            out.append((f"herramientas/{f.name}", desc))
    for rel, desc in (("instalador/instalar.sh", "instala, adopta y actualiza instancias (por defecto solo muestra el plan)"),
                      ("adaptadores-agente/nucleo/generar_agentes.py", "regenera este archivo y la configuración de cada agente")):
        if (Path(harness_raiz) / rel).exists():
            out.append((rel, desc))
    return out


# ----------------------------------------------------------------------------- construcción de la fuente
def construir(instancia, harness_raiz=None):
    """Devuelve la fuente neutral (dict) a partir de la instancia. Lee solo; no escribe."""
    inst = Path(instancia)
    harness_raiz = Path(harness_raiz) if harness_raiz else RAIZ_HARNESS
    if not inst.is_dir():
        raise ErrorInstancia(f"La instancia no existe o no es una carpeta: {inst}")
    pol = _toml(inst / "politicas.toml", "politicas.toml")
    conv = _toml(inst / "convenciones.toml", "convenciones.toml")
    version = None
    try:
        version = tomllib.loads((inst / "harness.lock").read_text(encoding="utf-8")).get("version")
    except (OSError, tomllib.TOMLDecodeError):
        pass
    estado = {}
    try:
        estado = json.loads((inst / ".harness" / "estado.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    version = version or estado.get("version_harness") or "sin declarar"

    carpetas = [(n, (inst / n).is_dir()) for n in ("conocimiento", "cambios", "documentacion")]
    existe = {n for n, ok in carpetas if ok}
    nombre = (pol.get("proyecto") or {}).get("nombre") or "este proyecto"

    cuando = [
        ("Antes de tocar código o responder una pregunta de negocio",
         "`conocimiento/` (si existe) y el módulo afectado en `documentacion/`" if existe else "la documentación del proyecto"),
        ("Antes de ejecutar cualquier comando que toque datos, git, despliegue, costos o secretos", "`politicas.toml` (y las reglas duras de abajo)"),
        ("Al nombrar ramas, escribir commits o abrir un PR", "`convenciones.toml`: claves `ramas.*`, `commits.*`, `pr.*`"),
        ("Al crear o cerrar tickets", "`convenciones.toml`: claves `ticket.*`"),
        ("Al abrir un cambio nuevo", "`cambios/` (una carpeta por cambio) y la plantilla de apertura del harness"),
        ("Al escribir documentación", "`convenciones.toml`: claves `documentacion.*` y las plantillas del harness"),
        ("Antes de dar un cambio por terminado", "el gate de calidad (sección siguiente) y `convenciones.toml`: `terminado.criterios`"),
        ("Si descubres una mejora que no corresponde al cambio en curso", "regístrala en `mejoras.md`; no la apliques de paso"),
        ("Si no sabes cómo llega esta persona a un recurso", "`acceso.local.ejemplo.toml` y, si existe, `acceso.local.toml` (no versionado, sin secretos)"),
    ]
    reglas = reglas_desde_politica(pol)
    gate_cmd = conv.get("gate.comando")
    gate = {"comando": None if _sin_definir(gate_cmd) else str(gate_cmd),
            "estado": "declarado" if not _sin_definir(gate_cmd) else "por definir",
            "pasos": None if _sin_definir(conv.get("gate.pasos")) else str(conv.get("gate.pasos"))}
    prohibiciones = [re.sub(r"^(.*?): prohibido para el agente.*$", r"\1: nunca lo hace el agente; si hace falta, se lo pides a la persona.", r["texto"])
                     for r in reglas if r["permiso"] == "prohibida"]
    prohibiciones += [
        "Inventar ambientes, hosts, puertos, cuentas, ramas o nombres que la política o las convenciones no declaran: pregunta.",
        "Dar por verificado algo sin un resultado observable que lo muestre.",
        "Editar `AGENTS.md` a mano: se regenera desde la política y las convenciones.",
        "Versionar credenciales, tokens o `acceso.local.toml`.",
    ]
    orient = [
        f"Estás en la instancia del harness de {nombre} (versión {version}). Aquí vive lo propio del proyecto; el método, los estándares y las plantillas vienen del harness.",
        "Lee primero `README.md` de la instancia, luego lo que indica la tabla siguiente según lo que vayas a hacer.",
        "Las reglas de abajo salen de `politicas.toml`: si necesitas algo distinto, no lo supongas; pregunta a la persona.",
        "Carpetas de la instancia: " + ", ".join(f"`{n}/` ({'existe' if ok else 'no existe'})" for n, ok in carpetas) + ".",
    ]
    capac = cc.capacidades(pol, harness_raiz)
    if capac["errores"]:
        raise ErrorInstancia("Las capacidades neutrales (skills, comandos, MCP) no son válidas:\n- " + "\n- ".join(capac["errores"]))
    return {
        "skills": capac["skills"], "comandos": capac["comandos"], "permisos": capac["permisos"], "mcp": capac["mcp"],
        "proyecto": nombre, "version_harness": version, "orientacion": orient, "cuando_leer": cuando,
        "reglas": reglas, "gate": gate, "prohibiciones": prohibiciones,
        "herramientas": herramientas_del_harness(harness_raiz),
        "pendientes": pendientes_de_declarar(pol, conv),
        "ambientes_datos": [str(a.get("nombre", "?")) for a in ((pol.get("datos") or {}).get("ambientes") or [])],
        "instancia": str(inst), "harness_raiz": str(harness_raiz), "archivo_agents": ARCHIVO_AGENTS,
        "politica_ruta": str(inst / "politicas.toml"),
    }


# ----------------------------------------------------------------------------- render de AGENTS.md
def _md_lista(items, vacio="Nada por ahora."):
    return "\n".join(f"- {x}" for x in items) if items else vacio


def texto_acceso_a_datos(ambientes):
    """Sección fija sobre los datos. La base de datos NO se instala con el harness: cada proyecto accede distinto y el acceso lo da la persona."""
    base = ("La base de datos es la **fuente de evidencia más fuerte** de este proyecto, y el harness **no la instala ni la levanta**: "
            "cada proyecto accede a ella de una forma distinta, así que el acceso lo da la persona. "
            "Sin ese acceso trabajas en **modo degradado**: no afirmes nada sobre datos (cifras, estados, existencia de registros) como verificado; "
            "di «no verificado» y pide el acceso.")
    como = ("Para darlo: la persona declara los ambientes en `politicas.toml` (`[[datos.ambientes]]`), pone su acceso personal en "
            "`acceso.local.toml` (no se versiona ni lleva secretos en el repositorio) y comprueba con `instalador/preflight-accesos.py` del harness. "
            "Nunca pidas ni escribas contraseñas en un archivo versionado, y nunca te conectes a un ambiente que la política no declare.")
    if ambientes:
        estado = "Ambientes declarados en la política: " + ", ".join(f"«{n}»" for n in ambientes) + ". Que estén declarados no significa que haya acceso: el preflight lo comprueba."
    else:
        estado = "La política **no declara ningún ambiente de datos**: no hay acceso configurado y no debes suponer ninguno."
    return base + "\n\n" + como + "\n\n" + estado


def render_agents_md(fuente, harness_raiz=None):
    harness_raiz = Path(harness_raiz) if harness_raiz else Path(fuente.get("harness_raiz") or RAIZ_HARNESS)
    tpl = (harness_raiz / "plantillas" / "AGENTS.md.tpl").read_text(encoding="utf-8")
    cuando = "| Situación | Qué leer |\n|---|---|\n" + "\n".join(f"| {a} | {b} |" for a, b in fuente["cuando_leer"])
    reglas, tema = [], None
    for r in fuente["reglas"]:
        if r["tema"] != tema:
            tema = r["tema"]
            reglas.append(f"\n### {tema}\n")
        reglas.append(f"- {r['texto']} (`{r['origen']}`)")
    g = fuente["gate"]
    if g["comando"]:
        gate = f"Antes de dar un cambio por terminado, ejecuta y muestra el resultado (código de salida incluido):\n\n```\n{g['comando']}\n```"
    else:
        gate = ("El comando del gate **aún no está declarado** (`gate.comando` en `convenciones.toml` está «por definir»). "
                "No lo inventes: pregunta a la persona cuál es y pídele que lo declare.")
    if g["pasos"]:
        gate += f"\n\nPasos del barrido final: {g['pasos']}."
    herr = [f"`{r}`" + (f": {d}" if d else "") for r, d in fuente["herramientas"]]
    valores = {
        "MARCA": MARCA, "PROYECTO": fuente["proyecto"], "VERSION_HARNESS": str(fuente["version_harness"]),
        "ORIENTACION": _md_lista(fuente["orientacion"]), "CUANDO_LEER": cuando,
        "REGLAS": "\n".join(reglas).strip() if reglas else "La política no declara reglas todavía.",
        "DATOS": texto_acceso_a_datos(fuente.get("ambientes_datos") or []),
        "GATE": gate, "PROHIBICIONES": _md_lista(fuente["prohibiciones"]),
        "HERRAMIENTAS": ("Rutas relativas a la raíz del harness (la ruta está en `harness.lock`, clave `fuente`):\n\n" + _md_lista(herr)) if herr else "No se encontraron herramientas.",
        "PENDIENTES": _md_lista(fuente["pendientes"], "Nada pendiente de declarar."),
    }
    texto = tpl
    for k, v in valores.items():
        texto = texto.replace("{{" + k + "}}", v)
    resto = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", texto)))
    if resto:
        raise ErrorInstancia(f"La plantilla AGENTS.md.tpl tiene variables sin resolver: {resto}")
    return texto.rstrip("\n") + "\n" + _seccion_capacidades(fuente)


def _seccion_capacidades(fuente):
    """Sección que solo se AGREGA al final de AGENTS.md: lista skills, comandos, permisos denegados y MCP. Determinista."""
    skills, comandos = fuente.get("skills") or [], fuente.get("comandos") or []
    permisos, mcp = fuente.get("permisos") or {}, fuente.get("mcp") or []
    if not (skills or comandos or permisos.get("deny") or permisos.get("ask") or mcp):
        return ""
    out = ["", "## Capacidades neutrales del harness", "",
           "Lista de lo que el harness ofrece a cualquier agente; cada agente recibe lo que su adaptador soporta."]
    if skills:
        out += ["", "### Skills", ""] + [f"- `{s['nombre']}`: {s['descripcion']}" for s in skills]
    if comandos:
        out += ["", "### Comandos (opcionales por agente)", ""] + [f"- `{c['nombre']}`: {c['descripcion']}" for c in comandos]
    if permisos.get("deny"):
        out += ["", "### Comandos denegados al agente", ""] + [f"- `{x}` (`{permisos['origenes'].get(x, '?')}`)" for x in permisos["deny"]]
    if permisos.get("no_traducible"):
        out += ["", f"Reglas de la política que no se pueden expresar como prefijo de comando ({len(permisos['no_traducible'])}) se hacen cumplir por hooks u otras capas, no por esta lista."]
    if mcp:
        out += ["", "### Servidores MCP declarados", ""] + [f"- `{s['nombre']}` ({s['tipo']}; registrar: {s['registrar']})" for s in mcp]
    return "\n".join(out) + "\n"


# ----------------------------------------------------------------------------- escritura segura
def es_generado(texto):
    cabeza = texto[:800].lower()
    return any(m in cabeza for m in MARCAS_DE_GENERADO)


def _dentro(instancia, rel):
    base = Path(os.path.realpath(instancia))
    destino = Path(os.path.realpath(base / rel))
    if os.path.isabs(rel) or ".." in Path(rel).parts or (destino != base and base not in destino.parents):
        raise ErrorInstancia(f"Ruta fuera de la instancia: {rel}")
    return destino


def alterno(rel):
    p = Path(rel)
    return str(p.with_name(f"{p.stem}.generado{p.suffix}"))


def planificar_archivo(instancia, rel, contenido, modo=None, respetar_manual=True):
    """Decide qué haría con `rel`: crear / actualizar / igual / alterno. No escribe."""
    destino = _dentro(instancia, rel)
    aviso = None
    if destino.exists() and respetar_manual:
        actual = destino.read_text(encoding="utf-8", errors="replace")
        if not es_generado(actual):
            rel_alt = alterno(rel)
            destino_alt = _dentro(instancia, rel_alt)
            aviso = (f"{rel} existe y fue escrito a mano (no tiene la marca del harness): no se toca; "
                     f"se genera {rel_alt} para que lo revises e incorpores lo que quieras.")
            if destino_alt.exists() and destino_alt.read_text(encoding="utf-8", errors="replace") == contenido:
                return {"ruta": rel_alt, "accion": "igual", "aviso": aviso, "contenido": contenido, "modo": modo, "alterno_de": rel}
            return {"ruta": rel_alt, "accion": "alterno", "aviso": aviso, "contenido": contenido, "modo": modo, "alterno_de": rel}
        return {"ruta": rel, "accion": "igual" if actual == contenido else "actualizar", "aviso": None, "contenido": contenido, "modo": modo}
    if destino.exists():
        actual = destino.read_text(encoding="utf-8", errors="replace")
        return {"ruta": rel, "accion": "igual" if actual == contenido else "actualizar", "aviso": None, "contenido": contenido, "modo": modo}
    return {"ruta": rel, "accion": "crear", "aviso": None, "contenido": contenido, "modo": modo}


def escribir_plan(instancia, plan, aplicar=False):
    """Escribe lo planificado (solo con aplicar) y devuelve el plan sin los contenidos."""
    for it in plan:
        if aplicar and it["accion"] in ("crear", "actualizar", "alterno"):
            destino = _dentro(instancia, it["ruta"])
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(it["contenido"], encoding="utf-8")
            if it.get("modo"):
                os.chmod(destino, it["modo"])
    return [{k: v for k, v in it.items() if k != "contenido"} for it in plan]


def plan_agents_md(fuente, instancia, harness_raiz=None):
    """Plan para AGENTS.md; fija `fuente['archivo_agents']` al nombre que realmente quedará (por si hubo uno manual)."""
    it = planificar_archivo(instancia, ARCHIVO_AGENTS, render_agents_md(fuente, harness_raiz))
    fuente["archivo_agents"] = it["ruta"]
    return it
