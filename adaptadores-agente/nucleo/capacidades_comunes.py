#!/usr/bin/env python3
"""Capacidades neutrales para agentes (R53): skills, comandos, permisos y servidores MCP.

Produce, sin depender de ningún agente, cuatro estructuras que cada adaptador traducirá a su formato:

- `skills`   desde `plantillas/skills/<nombre>/SKILL.md` del harness (formato portable: `name` y `description`).
- `comandos` desde `plantillas/comandos/*.md` del harness (opcionales por agente).
- `permisos` desde `politicas.toml`: `{deny, ask, allow, origenes, no_traducible}` con PREFIJOS LITERALES de comando.
  Un regex que no sea un prefijo literal NUNCA se convierte a mano ni se aproxima: queda en `no_traducible` con el motivo.
- `mcp`      desde `[[mcp.servidores]]` de la política, validada. Sin servidores declarados no hay nada: nunca se asume uno.

Solo biblioteca estándar. No usa red ni git. Solo lectura: no escribe nada.

Uso: python3 capacidades_comunes.py --validar <instancia> [--json]   (salida 0 bien · 1 errores · 2 la instancia no es utilizable)
"""
import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

RAIZ_HARNESS = Path(__file__).resolve().parents[2]
REGEX_NOMBRE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NOMBRE = 64
MAX_DESCRIPCION = 1024
REGISTRAR = ("prohibida", "confirmar", "permitida")
ACCION_A_LISTA = {"prohibida": "deny", "confirmar": "ask", "permitida": "allow"}
CLAVES_SERVIDOR = {"nombre", "comando", "url", "args", "entorno", "registrar"}
REF_VARIABLE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
NOMBRE_ENTORNO = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# patrones con aspecto de secreto (nunca se imprime el valor que los dispara)
SECRETOS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"://[^/\s:@]+:[^/\s@]+@"),
    re.compile(r"(?i)(token|secret|passw(or)?d|passwd|api[_-]?key|apikey)=[^\s$]+"),
]
# solo para valores de `entorno`, donde cualquier cadena larga y opaca es sospechosa (en args/url daría falsos positivos)
SECRETO_OPACO = re.compile(r"^[A-Za-z0-9+/_=-]{24,}$")


class ErrorCapacidades(Exception):
    """Una capacidad (skill, comando, política de MCP…) no es válida; el mensaje dice qué se intentó."""


# ----------------------------------------------------------------------------- skills y comandos
def _frontmatter(texto):
    """Devuelve ({clave: valor}, cuerpo) del bloque `---` inicial; ({}, texto) si no hay."""
    m = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", texto, re.S)
    if not m:
        return {}, texto
    datos = {}
    for linea in m.group(1).splitlines():
        if ":" in linea and not linea.startswith((" ", "\t")):
            k, v = linea.split(":", 1)
            datos[k.strip()] = v.strip()
    return datos, m.group(2)


def skills_neutrales(harness_raiz=None):
    """([{nombre, descripcion, ruta, contenido}], [errores]). `ruta` es relativa a la raíz del harness."""
    base = Path(harness_raiz or RAIZ_HARNESS) / "plantillas" / "skills"
    skills, errores = [], []
    if not base.is_dir():
        return skills, errores
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        rel = f"plantillas/skills/{d.name}/SKILL.md"
        f = d / "SKILL.md"
        if not f.is_file():
            errores.append(f"Skill «{d.name}»: falta {rel}.")
            continue
        texto = f.read_text(encoding="utf-8")
        fm, _ = _frontmatter(texto)
        nombre, desc = fm.get("name", ""), fm.get("description", "")
        previos = len(errores)
        if not nombre:
            errores.append(f"{rel}: falta `name` en la cabecera (---).")
        elif not REGEX_NOMBRE.match(nombre) or len(nombre) > MAX_NOMBRE:
            errores.append(f"{rel}: `name` {nombre!r} no cumple ^[a-z0-9]+(-[a-z0-9]+)*$ (máximo {MAX_NOMBRE} caracteres).")
        elif nombre != d.name:
            errores.append(f"{rel}: `name` ({nombre!r}) debe coincidir con la carpeta ({d.name!r}).")
        if not desc:
            errores.append(f"{rel}: falta `description` en la cabecera.")
        elif len(desc) > MAX_DESCRIPCION:
            errores.append(f"{rel}: `description` pasa de {MAX_DESCRIPCION} caracteres.")
        if len(errores) == previos:
            skills.append({"nombre": nombre, "descripcion": desc, "ruta": rel, "contenido": texto})
    return skills, errores


def comandos_neutrales(harness_raiz=None):
    """([{nombre, descripcion, ruta, contenido}], [errores]) desde `plantillas/comandos/*.md`."""
    base = Path(harness_raiz or RAIZ_HARNESS) / "plantillas" / "comandos"
    comandos, errores = [], []
    if not base.is_dir():
        return comandos, errores
    for f in sorted(base.glob("*.md")):
        rel = f"plantillas/comandos/{f.name}"
        texto = f.read_text(encoding="utf-8")
        fm, _ = _frontmatter(texto)
        if not REGEX_NOMBRE.match(f.stem):
            errores.append(f"{rel}: el nombre del archivo debe cumplir ^[a-z0-9]+(-[a-z0-9]+)*$.")
        elif not fm.get("description"):
            errores.append(f"{rel}: falta `description` en la cabecera.")
        else:
            comandos.append({"nombre": f.stem, "descripcion": fm["description"], "ruta": rel, "contenido": texto})
    return comandos, errores


# ----------------------------------------------------------------------------- permisos
def prefijos_literales(regex):
    """Devuelve (lista_de_prefijos, None) si el regex es un prefijo literal (o alternativas de prefijos literales);
    (None, motivo) si no lo es. Nunca aproxima: ante la duda, no se traduce."""
    if not isinstance(regex, str) or not regex.strip():
        return None, "el regex está vacío"
    partes = regex.split("|")
    if len(partes) > 1 and any(c in regex for c in "()[]"):
        return None, "tiene grupos o clases junto a alternativas: no es un prefijo literal"
    salida = []
    for parte in partes:
        t = parte[1:] if parte.startswith("^") else parte
        if t.endswith("$") and not t.endswith("\\$"):
            return None, "termina en `$` (coincidencia exacta, no un prefijo)"
        lit, i = [], 0
        while i < len(t):
            c = t[i]
            if c == "\\":
                if i + 1 >= len(t):
                    return None, "termina en una barra invertida"
                n = t[i + 1]
                if n.isalnum():
                    return None, f"usa la secuencia especial `\\{n}`"
                lit.append(n)
                i += 2
                continue
            if c in ".*+?()[]{}|^$":
                return None, f"usa el metacarácter `{c}`"
            lit.append(c)
            i += 1
        texto = "".join(lit).strip()
        if not texto or not re.search(r"[A-Za-z0-9]", texto):
            return None, "no contiene un comando literal"
        if not re.fullmatch(r"[A-Za-z0-9_./:=@, -]+", texto):
            return None, "contiene caracteres que no son de un comando literal"
        salida.append(re.sub(r" +", " ", texto))
    return salida, None


def permisos_desde_politica(p):
    """{deny, ask, allow, origenes, no_traducible}: prefijos literales de comando; determinista y sin inventar."""
    listas = {"deny": [], "ask": [], "allow": []}
    origenes, no_trad = {}, []

    def sin(origen, regla, motivo):
        no_trad.append({"origen": origen, "regla": regla, "motivo": motivo})

    def poner(accion, regex, origen, nombre=None):
        lista = ACCION_A_LISTA.get(accion)
        etiqueta = nombre or str(regex)
        if lista is None:
            return sin(origen, etiqueta, f"la acción {accion!r} no es permitida|confirmar|prohibida")
        prefs, motivo = prefijos_literales(regex)
        if prefs is None:
            return sin(origen, etiqueta, f"el regex no es un prefijo literal: {motivo}")
        for pref in prefs:
            if pref not in listas[lista]:
                listas[lista].append(pref)
            origenes.setdefault(pref, origen)

    datos = p.get("datos") or {}
    for i, c in enumerate(datos.get("comandos") or []):
        if isinstance(c, dict):
            poner(c.get("accion", "prohibida"), c.get("regex"), "datos.comandos", c.get("nombre") or f"datos.comandos[{i}]")
    if datos.get("clientes_sql") and (datos.get("lectura_host_remoto") in ("prohibida", "confirmar") or datos.get("lectura_host_no_resuelto")):
        sin("datos.clientes_sql", ", ".join(str(x) for x in datos["clientes_sql"]),
            "leer o no una base depende del host, que un prefijo de comando no expresa; lo cubre el hook de datos")

    git = p.get("git") or {}
    for acc in git.get("confirmar") or []:
        if isinstance(acc, str) and re.fullmatch(r"[a-z][a-z-]*", acc):
            poner("confirmar", "^git " + acc, "git.confirmar", f"git {acc}")
        else:
            sin("git.confirmar", str(acc), "no es un subcomando simple de git")
    for clave in ("push_a_rama_protegida", "merge_a_rama_de_produccion"):
        if git.get(clave) in ("prohibida", "confirmar"):
            sin(f"git.{clave}", clave, "depende de la rama de destino, que un prefijo de comando no expresa")

    cmd = p.get("comandos") or {}
    for clave in ("instalar", "build", "test", "servidor_de_desarrollo", "formateo_global"):
        t = cmd.get(clave)
        if not isinstance(t, dict) or not t.get("accion"):
            continue
        if t.get("regex"):
            poner(t["accion"], t["regex"], f"comandos.{clave}", f"comandos.{clave}")
        elif t["accion"] != "permitida":
            sin(f"comandos.{clave}", clave, f"la política da la acción ({t['accion']}) pero no declara el comando; no se inventa")

    dep = p.get("despliegue") or {}
    regexes = dep.get("regex") if isinstance(dep.get("regex"), list) else ([dep["regex"]] if dep.get("regex") else [])
    for rx in regexes:
        poner(dep.get("accion", "confirmar"), rx, "despliegue.regex", str(rx))
    if not regexes and dep.get("accion") and dep["accion"] != "permitida":
        sin("despliegue.accion", "despliegue", "la política da la acción pero no declara comandos de despliegue (despliegue.regex vacío); no se inventan")

    sec = p.get("secretos") or {}
    if sec.get("rutas_prohibidas_en_commit"):
        sin("secretos.rutas_prohibidas_en_commit", ", ".join(str(x) for x in sec["rutas_prohibidas_en_commit"]),
            "son rutas de archivo, no prefijos de comando; las cubre el hook de commit")

    # lo más estricto gana: lo que está en deny sale de ask/allow, y lo de ask sale de allow
    listas["ask"] = [x for x in listas["ask"] if x not in listas["deny"]]
    listas["allow"] = [x for x in listas["allow"] if x not in listas["deny"] and x not in listas["ask"]]
    return {**listas, "origenes": origenes, "no_traducible": no_trad}


# ----------------------------------------------------------------------------- MCP
def _parece_secreto(valor, opaco=False):
    return isinstance(valor, str) and (any(r.search(valor) for r in SECRETOS) or (opaco and bool(SECRETO_OPACO.match(valor))))


def mcp_desde_politica(p):
    """([servidor_neutral], [errores]). Sin `[[mcp.servidores]]` devuelve ([], []): no se asume ningún servidor.

    Servidor neutral: {nombre, tipo: local|remoto, comando, args, url, entorno: [{clave, variable}], registrar}.
    En `entorno` solo se admite la referencia `${VARIABLE}`: el valor real nunca vive en la política.
    """
    mcp = p.get("mcp")
    if mcp is None:
        return [], []
    errores = []
    if not isinstance(mcp, dict):
        return [], ["`mcp` debe ser una tabla con la lista `[[mcp.servidores]]`."]
    for k in mcp:
        if k != "servidores":
            errores.append(f"mcp.{k}: clave desconocida (solo existe `[[mcp.servidores]]`).")
    lista = mcp.get("servidores")
    if lista is None:
        return [], errores
    if not isinstance(lista, list):
        return [], errores + ["mcp.servidores debe ser una lista de tablas `[[mcp.servidores]]`."]
    servidores, vistos = [], set()
    for i, s in enumerate(lista):
        ref = f"mcp.servidores[{i}]"
        if not isinstance(s, dict):
            errores.append(f"{ref}: debe ser una tabla.")
            continue
        nombre = s.get("nombre")
        if isinstance(nombre, str) and nombre:
            ref = f"mcp.servidores[{i}] ({nombre})"
        for k in sorted(set(s) - CLAVES_SERVIDOR):
            errores.append(f"{ref}: clave desconocida `{k}` (permitidas: {', '.join(sorted(CLAVES_SERVIDOR))}).")
        if not isinstance(nombre, str) or not REGEX_NOMBRE.match(nombre):
            errores.append(f"{ref}: `nombre` debe ser texto en minúsculas, números y guiones (^[a-z0-9]+(-[a-z0-9]+)*$); se recibió {nombre!r}.")
        elif nombre in vistos:
            errores.append(f"{ref}: nombre de servidor repetido.")
        else:
            vistos.add(nombre)
        comando, url = s.get("comando"), s.get("url")
        if bool(comando) == bool(url):
            errores.append(f"{ref}: declara exactamente uno de `comando` (servidor local) o `url` (servidor remoto).")
        if comando is not None and (not isinstance(comando, str) or not comando or re.search(r"\s", comando)):
            errores.append(f"{ref}: `comando` debe ser el ejecutable, sin espacios; los argumentos van en `args`.")
        if url is not None:
            if not isinstance(url, str) or not re.match(r"^https?://[^\s]+$", url):
                errores.append(f"{ref}: `url` debe ser una dirección http(s) sin espacios.")
            elif _parece_secreto(url):
                errores.append(f"{ref}: `url` contiene algo con aspecto de secreto (usuario:clave@ o token); usa una referencia `${{VARIABLE}}` o declara el servidor sin credenciales en la dirección.")
        args = s.get("args", [])
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            errores.append(f"{ref}: `args` debe ser una lista de textos.")
            args = []
        for j, a in enumerate(args):
            if _parece_secreto(a) and not REF_VARIABLE.match(a):
                errores.append(f"{ref}: args[{j}] tiene aspecto de secreto (valor omitido); pásalo por `entorno` como referencia `${{VARIABLE}}`.")
        entorno_neutral = []
        entorno = s.get("entorno", {})
        if not isinstance(entorno, dict):
            errores.append(f"{ref}: `entorno` debe ser una tabla CLAVE = \"${{VARIABLE}}\".")
            entorno = {}
        for clave, valor in entorno.items():
            if not NOMBRE_ENTORNO.match(str(clave)):
                errores.append(f"{ref}: entorno.{clave}: el nombre de la variable no es válido.")
                continue
            m = REF_VARIABLE.match(valor) if isinstance(valor, str) else None
            if m:
                entorno_neutral.append({"clave": clave, "variable": m.group(1)})
            elif _parece_secreto(valor, opaco=True):
                errores.append(f"{ref}: entorno.{clave} tiene un valor con aspecto de secreto (valor omitido). "
                               "Solo se admiten referencias `${VARIABLE}`; nunca el valor.")
            else:
                errores.append(f"{ref}: entorno.{clave} no es una referencia. Se esperaba `${{VARIABLE}}`: "
                               "la política nunca guarda valores, solo el nombre de la variable que los contiene.")
        registrar = s.get("registrar", "confirmar")
        if registrar not in REGISTRAR:
            errores.append(f"{ref}: `registrar` debe ser uno de {', '.join(REGISTRAR)}; se recibió {registrar!r}.")
        servidores.append({"nombre": nombre, "tipo": "local" if comando else "remoto", "comando": comando or None,
                           "args": list(args), "url": url or None, "entorno": entorno_neutral, "registrar": registrar})
    return (servidores if not errores else []), errores


# ----------------------------------------------------------------------------- conjunto
def capacidades(politica, harness_raiz=None):
    """{skills, comandos, permisos, mcp, errores}: todo lo neutral junto. `errores` junta lo que impide usarlo."""
    skills, e1 = skills_neutrales(harness_raiz)
    comandos, e2 = comandos_neutrales(harness_raiz)
    mcp, e3 = mcp_desde_politica(politica)
    return {"skills": skills, "comandos": comandos, "permisos": permisos_desde_politica(politica), "mcp": mcp, "errores": e1 + e2 + e3}


def validar_instancia(instancia, harness_raiz=None):
    """Lista de errores de las capacidades de la instancia (vacía = todo bien). ErrorCapacidades si no hay política legible."""
    ruta = Path(instancia) / "politicas.toml"
    try:
        with open(ruta, "rb") as f:
            pol = tomllib.load(f)
    except FileNotFoundError:
        raise ErrorCapacidades(f"Se intentó leer {ruta} y no existe: la carpeta no es una instancia del harness.")
    except tomllib.TOMLDecodeError as e:
        raise ErrorCapacidades(f"Se intentó leer {ruta} y no es TOML válido: {e}")
    return capacidades(pol, harness_raiz)["errores"]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Valida las capacidades neutrales (skills, comandos, permisos, MCP) de una instancia.")
    ap.add_argument("--validar", metavar="INSTANCIA", required=True)
    ap.add_argument("--harness", default=None, help="raíz del harness (por defecto, la de este archivo)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        errores = validar_instancia(a.validar, a.harness)
    except ErrorCapacidades as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"errores": errores}, ensure_ascii=False, indent=2))
    elif errores:
        print(f"Se encontraron {len(errores)} error(es) en las capacidades de la instancia:")
        for e in errores:
            print(f"- {e}")
    else:
        print("Capacidades válidas: skills, comandos, permisos y MCP sin errores.")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
