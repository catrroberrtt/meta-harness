#!/usr/bin/env python3
"""Trazabilidad de un cambio de punta a punta (SOLO LECTURA, sin red, sin modelo).

Lee la carpeta de un cambio (`cambios/<fecha>-<slug>/`) y comprueba que el rastro es completo y coherente:
  especificacion.md  requisitos `RQ-NN` con criterios `CA-NN.n`, suposiciones `SU-NN` y aprobación
  delegacion.md      tabla de contrato por tarea (encargado, requisitos, archivos que escribe, entrega, aceptación)
  matriz.md          tabla requisito-criterio-prueba-commit-evidencia-estado
  cierre.md          lista de cierre sin casillas vacías
Formatos y reglas: metodo/terminado-y-trazabilidad.md. Plantillas: plantillas/{especificacion,delegacion,matriz-trazabilidad,cierre-de-cambio}.md.

Etapas (cada una incluye las anteriores): especificacion < delegacion < implementacion < cierre. Por defecto, cierre.
Con --repo <carpeta> comprueba además, con `git` local, que los commits existen y que las pruebas y evidencias citadas existen;
sin --repo lo dice como «no comprobado». No escribe nada y no usa la red.
Salida: 0 sin errores · 1 hay errores · 2 uso incorrecto (carpeta inexistente, etapa desconocida).
Uso: python3 harness-trazabilidad.py <carpeta-del-cambio> [--etapa especificacion|delegacion|implementacion|cierre] [--repo <carpeta>] [--json]
"""
import argparse, fnmatch, json, pathlib, re, subprocess, sys, unicodedata

ETAPAS = ("especificacion", "delegacion", "implementacion", "cierre")
NIVELES_SUPOSICION = ("establecido", "de-trabajo", "abierto")
ESTADOS_FILA = ("pendiente", "implementado", "verificado", "no-verificado")
ESTADOS_TAREA = ("pendiente", "en-curso", "entregada", "aceptada", "rechazada")
VACIOS = {"", "-", "—", "–", "n/a", "na", "ninguno", "ninguna"}
VAGAS = ("rápid", "rapid", "fácil", "facil", "adecuad", "apropiad", "óptim", "optim", "intuitiv", "amigable",
         "robust", "escalable", "flexible", "suficiente", "razonable", "lo antes posible", "etc.", "y demás", "y demas")

RE_RQ = re.compile(r"^\s*[-*]\s+(RQ-\d+)\b\s*[·:\-–]?\s*(.*)$")
RE_CA = re.compile(r"^\s*[-*]\s+(CA-(\d+)\.(\d+))\b\s*[·:\-–]?\s*(.*)$")
RE_SU = re.compile(r"^\s*[-*]\s+(SU-\d+)\b\s*[·:\-–]?\s*([A-Za-záéíóúñ-]+)?\s*(.*)$")
RE_CASILLA = re.compile(r"^\s*[-*]\s+\[( |x|X|-)\]\s*(.*)$")
RE_HASH = re.compile(r"^[0-9a-fA-F]{7,40}$")


def sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def clave(t):
    return re.sub(r"[^a-z0-9]+", "_", sin_acentos(t).lower()).strip("_")


def lineas_utiles(texto):
    """(número, línea) fuera de los bloques de código cercados."""
    dentro = False
    for n, l in enumerate(texto.splitlines(), 1):
        if l.strip().startswith("```"):
            dentro = not dentro
            continue
        if not dentro:
            yield n, l


def secciones(texto):
    """{nombre normalizado de la sección '## ...': [(n, línea)]}; lo anterior al primer '##' va en ''."""
    out, actual = {"": []}, ""
    for n, l in lineas_utiles(texto):
        m = re.match(r"^##\s+(.*)$", l)
        if m:
            actual = clave(m.group(1))
            out.setdefault(actual, [])
            continue
        out.setdefault(actual, []).append((n, l))
    return out


def seccion(secs, prefijo):
    for k, v in secs.items():
        if k.startswith(prefijo):
            return v
    return []


def celdas(l):
    t = l.strip()
    if t.startswith("|"):
        t = t[1:]
    if t.endswith("|"):
        t = t[:-1]
    return [c.strip() for c in t.split("|")]


def tabla(texto, obligatorias):
    """Primera tabla cuya cabecera contenga las columnas obligatorias. Devuelve (filas, faltan, encontrada)."""
    ls = list(lineas_utiles(texto))
    for i, (n, l) in enumerate(ls):
        if not l.strip().startswith("|"):
            continue
        cab = [clave(c) for c in celdas(l)]
        if not set(obligatorias) & set(cab):
            continue
        faltan = [c for c in obligatorias if c not in cab]
        if len(faltan) == len(obligatorias):
            continue
        filas = []
        j = i + 1
        if j < len(ls) and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", ls[j][1]) and "-" in ls[j][1]:
            j += 1
        while j < len(ls) and ls[j][1].strip().startswith("|"):
            cs = celdas(ls[j][1])
            fila = {cab[k]: (cs[k] if k < len(cs) else "") for k in range(len(cab))}
            fila["_n"] = ls[j][0]
            filas.append(fila)
            j += 1
        return filas, faltan, True
    return [], list(obligatorias), False


def vacio(v):
    return clave(v) in {clave(x) for x in VACIOS}


def partir(v, seps=r"[,;]"):
    return [x.strip().strip("`").strip() for x in re.split(seps, v) if x.strip() and not vacio(x)]


class Informe:
    def __init__(self):
        self.h = []
        self.no_comprobado = []

    def error(self, cod, donde, msg):
        self.h.append({"nivel": "ERROR", "codigo": cod, "donde": donde, "mensaje": msg})

    def aviso(self, cod, donde, msg):
        self.h.append({"nivel": "AVISO", "codigo": cod, "donde": donde, "mensaje": msg})


def leer(carpeta, nombre):
    p = carpeta / nombre
    if not p.is_file():
        return None
    try:
        return p.read_text(encoding="utf8")
    except (OSError, UnicodeDecodeError):
        return None


def sin_resolver(inf, nombre, texto):
    for n, l in lineas_utiles(texto):
        if "{{" in l:
            inf.error("T09", f"{nombre}:{n}", "marcador «{{…}}» sin resolver")


# ------------------------------------------------------------------ especificación
def analizar_especificacion(inf, carpeta, idx):
    texto = leer(carpeta, "especificacion.md")
    if texto is None:
        inf.error("T01", "especificacion.md", "no existe o no se puede leer (plantilla: plantillas/especificacion.md)")
        return None
    sin_resolver(inf, "especificacion.md", texto)
    secs = secciones(texto)
    reqs, crits, supos, vistos = {}, {}, {}, set()
    actual = None
    for n, l in seccion(secs, "requisitos"):
        m = RE_RQ.match(l)
        if m:
            rid = m.group(1)
            if rid in vistos:
                inf.error("T04", f"especificacion.md:{n}", f"identificador repetido: {rid}")
            vistos.add(rid)
            reqs[rid] = {"n": n, "texto": m.group(2).strip(), "criterios": []}
            actual = rid
            continue
        m = RE_CA.match(l)
        if m:
            cid = m.group(1)
            if cid in vistos:
                inf.error("T04", f"especificacion.md:{n}", f"identificador repetido: {cid}")
            vistos.add(cid)
            crits[cid] = {"n": n, "texto": m.group(4).strip(), "req": actual}
            if actual is None:
                inf.error("T05", f"especificacion.md:{n}", f"{cid} está fuera de un requisito (ponlo bajo su RQ-NN)")
            else:
                reqs[actual]["criterios"].append(cid)
                if int(actual[3:]) != int(m.group(2)):
                    inf.error("T05", f"especificacion.md:{n}", f"{cid} está bajo {actual}: el número no coincide")
            for v in VAGAS:
                if v in sin_acentos(crits[cid]["texto"]).lower() or v in crits[cid]["texto"].lower():
                    inf.aviso("T06", f"especificacion.md:{n}", f"{cid} usa un término no medible («{v.strip()}»): pon una cifra, un estado o un código")
                    break
    if not reqs:
        inf.error("T02", "especificacion.md", "no hay requisitos (lista `- RQ-01 · …` bajo «## Requisitos»)")
    for rid, r in reqs.items():
        if not r["criterios"]:
            inf.error("T03", f"especificacion.md:{r['n']}", f"{rid} no tiene criterio de aceptación (`- CA-NN.n · …`)")
    for n, l in seccion(secs, "suposiciones"):
        m = RE_SU.match(l)
        if not m:
            continue
        sid, nivel = m.group(1), (m.group(2) or "").lower()
        if sid in vistos:
            inf.error("T04", f"especificacion.md:{n}", f"identificador repetido: {sid}")
        vistos.add(sid)
        supos[sid] = {"n": n, "nivel": nivel}
        if nivel not in NIVELES_SUPOSICION:
            inf.error("T07", f"especificacion.md:{n}", f"{sid}: nivel «{nivel or 'vacío'}» no válido (establecido, de-trabajo o abierto)")
        elif nivel == "abierto":
            if idx >= ETAPAS.index("delegacion"):
                inf.error("T07", f"especificacion.md:{n}", f"{sid} sigue abierta: resuélvela (establecido o de-trabajo) antes de delegar y de cerrar")
            else:
                inf.aviso("T07", f"especificacion.md:{n}", f"{sid} está abierta: no se podrá delegar hasta resolverla")
    aprobada = None
    for n, l in seccion(secs, "aprobacion"):
        m = RE_CASILLA.match(l)
        if m:
            aprobada = (m.group(1).lower() == "x") if aprobada is None else (aprobada and m.group(1).lower() == "x")
    if idx >= ETAPAS.index("delegacion") and not aprobada:
        inf.error("T08", "especificacion.md", "sin OK explícito marcado en «## Aprobación» (`- [x] OK explícito de …`): no se delega ni se codifica sin él")
    return {"requisitos": reqs, "criterios": crits, "suposiciones": supos, "aprobada": bool(aprobada)}


# ------------------------------------------------------------------ delegación
def solapan(a, b):
    a, b = a.rstrip("/"), b.rstrip("/")
    if a == b:
        return True
    if fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a):
        return True
    return a.startswith(b + "/") or b.startswith(a + "/")


def analizar_delegacion(inf, carpeta, spec):
    texto = leer(carpeta, "delegacion.md")
    if texto is None:
        inf.aviso("T27", "delegacion.md", "no hay delegación; si el trabajo lo hace una sola persona sin reparto, créala con una tarea cuyo encargado seas tú (plantillas/delegacion.md)")
        return []
    sin_resolver(inf, "delegacion.md", texto)
    oblig = ["tarea", "encargado", "requisitos", "escribe", "entrega", "aceptacion"]
    filas, faltan, hallada = tabla(texto, oblig)
    if faltan:
        inf.error("T20", "delegacion.md", "a la tabla le faltan columnas del contrato: " + ", ".join(faltan))
        if not hallada:
            return []
    tareas = []
    cubiertos = set()
    for f in filas:
        nombre = f.get("tarea", "").strip() or f"fila {f['_n']}"
        donde = f"delegacion.md:{f['_n']}"
        for c in oblig:
            if c in f and vacio(f[c]):
                inf.error("T20", donde, f"la tarea «{nombre}» no tiene «{c}» (sin contrato de archivos no se delega)")
        rqs = re.findall(r"RQ-\d+", f.get("requisitos", ""))
        for r in rqs:
            if spec and r not in spec["requisitos"]:
                inf.error("T21", donde, f"la tarea «{nombre}» cita {r}, que no existe en la especificación")
        cubiertos.update(rqs)
        compartido = "(compartido)" in f.get("escribe", "").lower()
        escribe = [re.sub(r"\s*\(compartido\)\s*", "", p, flags=re.I).strip() for p in partir(f.get("escribe", ""))]
        no_toca = partir(f.get("no_toca", ""))
        for p in escribe + no_toca:
            if p.startswith(("/", "~")) or re.match(r"^[A-Za-z]:[\\/]", p) or ".." in pathlib.PurePosixPath(p).parts:
                inf.error("T23", donde, f"ruta no relativa o que sale de la carpeta del proyecto: «{p}»")
            if p in ("*", "**", "./", ".", "/"):
                inf.error("T23", donde, f"«{p}» abarca todo el proyecto: acota los archivos")
        for p in escribe:
            for q in no_toca:
                if solapan(p, q):
                    inf.error("T22", donde, f"la tarea «{nombre}» escribe «{p}» y a la vez declara no tocar «{q}»")
        est = clave(f.get("estado", "")).replace("_", "-") if "estado" in f else ""
        if "estado" in f and est not in ESTADOS_TAREA:
            inf.error("T26", donde, f"estado «{f.get('estado', '')}» no válido (pendiente, en-curso, entregada, aceptada, rechazada)")
        tareas.append({"nombre": nombre, "n": f["_n"], "escribe": escribe, "compartido": compartido, "estado": est})
    for i, a in enumerate(tareas):
        for b in tareas[i + 1:]:
            for p in a["escribe"]:
                for q in b["escribe"]:
                    if solapan(p, q) and not (a["compartido"] and b["compartido"]):
                        inf.error("T22", f"delegacion.md:{a['n']}", f"«{a['nombre']}» y «{b['nombre']}» escriben el mismo lugar («{p}» / «{q}»): sepáralos o márcalos (compartido) los dos")
    if spec:
        for rid, r in spec["requisitos"].items():
            if rid not in cubiertos:
                inf.error("T24", f"especificacion.md:{r['n']}", f"{rid} no está asignado a ninguna tarea de delegacion.md")
    return tareas


# ------------------------------------------------------------------ matriz
def git_commit_existe(repo, h):
    r = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{h}^{{commit}}"], capture_output=True, text=True)
    return r.returncode == 0


def parece_ruta(t):
    return "/" in t or re.search(r"\.\w{1,6}$", t) is not None


def analizar_matriz(inf, carpeta, spec, idx, repo):
    texto = leer(carpeta, "matriz.md")
    if texto is None:
        inf.error("T40", "matriz.md", "no existe (plantilla: plantillas/matriz-trazabilidad.md)")
        return []
    sin_resolver(inf, "matriz.md", texto)
    oblig = ["requisito", "criterio", "prueba", "commit", "evidencia", "estado"]
    filas, faltan, hallada = tabla(texto, oblig)
    if faltan:
        inf.error("T40", "matriz.md", "a la tabla le faltan columnas: " + ", ".join(faltan))
        if not hallada:
            return []
    git_ok = None
    if repo is not None:
        git_ok = subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-dir"], capture_output=True, text=True).returncode == 0
        if not git_ok:
            inf.aviso("T48", "matriz.md", f"{repo} no es un repositorio git: no se comprobaron los commits")
    cierre = idx >= ETAPAS.index("cierre")
    reqs_con_fila, crits_con_fila = set(), set()
    for f in filas:
        donde = f"matriz.md:{f['_n']}"
        rq, ca = f.get("requisito", "").strip(), f.get("criterio", "").strip()
        estado = clave(f.get("estado", "")).replace("_", "-")
        if vacio(rq) or (spec and rq not in spec["requisitos"]):
            inf.error("T41", donde, f"fila sin requisito válido («{rq or 'vacío'}»): una prueba sin requisito no cuenta")
        else:
            reqs_con_fila.add(rq)
        if vacio(ca) or (spec and ca not in spec["criterios"]):
            inf.error("T41", donde, f"fila sin criterio válido («{ca or 'vacío'}») para {rq or '?'}")
        else:
            crits_con_fila.add(ca)
            if spec and not vacio(rq) and spec["criterios"][ca]["req"] != rq:
                inf.error("T41", donde, f"{ca} pertenece a {spec['criterios'][ca]['req']}, no a {rq}")
        if estado not in ESTADOS_FILA:
            inf.error("T46", donde, f"estado «{f.get('estado', '')}» no válido (pendiente, implementado, verificado, no-verificado)")
        prueba, commit, evid = f.get("prueba", ""), f.get("commit", ""), f.get("evidencia", "")
        if estado == "verificado":
            for campo, v in (("prueba", prueba), ("commit", commit), ("evidencia", evid)):
                if vacio(v):
                    inf.error("T44", donde, f"{ca or rq}: está «verificado» pero no tiene {campo}")
            rv = clave(f.get("rojo_verde", ""))
            if cierre and rv not in ("si", "no", "n_a"):
                inf.aviso("T50", donde, f"{ca or rq}: declara en «Rojo→verde» si se vio fallar la prueba antes (sí / no / n/a)")
        elif estado == "implementado" and vacio(commit):
            inf.error("T44", donde, f"{ca or rq}: está «implementado» pero no tiene commit")
        elif estado == "no-verificado" and vacio(f.get("nota", "")):
            inf.error("T45", donde, f"{ca or rq}: «no-verificado» exige la nota con el motivo y qué lo destrabaría")
        if cierre and estado in ("pendiente", "implementado"):
            inf.error("T47", donde, f"{ca or rq}: sigue «{estado}»; para cerrar debe estar verificado o no-verificado con motivo")
        if repo is not None:
            for h in partir(commit, r"[,;\s]+"):
                if not RE_HASH.match(h):
                    inf.error("T48", donde, f"commit con formato no válido: «{h}»")
                elif git_ok and not git_commit_existe(repo, h):
                    inf.error("T48", donde, f"el commit {h} no existe en {repo}")
            for p in partir(prueba, r";"):
                ruta = p.split("::")[0].strip()
                if parece_ruta(ruta) and not (repo / ruta).exists():
                    inf.error("T49", donde, f"la prueba «{ruta}» no existe en {repo}")
            for e in partir(evid, r";"):
                if re.match(r"^https?://", e):
                    inf.no_comprobado.append(f"{donde}: evidencia por enlace «{e}» (no se abre; sin red)")
                elif parece_ruta(e) and not ((carpeta / e).exists() or (repo / e).exists()):
                    inf.error("T49", donde, f"la evidencia «{e}» no existe (se buscó junto al cambio y en {repo})")
    if spec:
        for rid, r in spec["requisitos"].items():
            if rid not in reqs_con_fila:
                inf.error("T42", f"especificacion.md:{r['n']}", f"{rid} no tiene ninguna fila en la matriz (requisito sin prueba)")
        for cid, c in spec["criterios"].items():
            if cid not in crits_con_fila:
                inf.error("T43", f"especificacion.md:{c['n']}", f"{cid} no tiene fila en la matriz")
    return filas


# ------------------------------------------------------------------ cierre
def analizar_cierre(inf, carpeta, tareas):
    texto = leer(carpeta, "cierre.md")
    if texto is None:
        inf.error("T60", "cierre.md", "no existe (plantilla: plantillas/cierre-de-cambio.md)")
    else:
        sin_resolver(inf, "cierre.md", texto)
        n_cas = 0
        for n, l in lineas_utiles(texto):
            m = RE_CASILLA.match(l)
            if not m:
                continue
            n_cas += 1
            marca, resto = m.group(1), m.group(2)
            if marca == " ":
                inf.error("T61", f"cierre.md:{n}", f"casilla sin marcar: {resto.strip()[:80]}")
            elif marca == "-":
                mo = re.search(r"N/A\s*[:\-–—]\s*(\S.*)$", resto, re.I)
                if not mo:
                    inf.error("T62", f"cierre.md:{n}", f"«no aplica» sin motivo (escribe `N/A: motivo`): {resto.strip()[:60]}")
        if n_cas == 0:
            inf.error("T61", "cierre.md", "no tiene casillas `- [ ]`: usa la lista de plantillas/cierre-de-cambio.md")
    for t in tareas:
        if t["estado"] != "aceptada":
            inf.error("T25", f"delegacion.md:{t['n']}", f"la tarea «{t['nombre']}» está «{t['estado'] or 'sin estado'}»; para cerrar debe estar aceptada")


# ------------------------------------------------------------------ principal
def analizar(carpeta, etapa="cierre", repo=None):
    carpeta = pathlib.Path(carpeta).expanduser().resolve()
    idx = ETAPAS.index(etapa)
    repo = pathlib.Path(repo).expanduser().resolve() if repo else None
    inf = Informe()
    spec = analizar_especificacion(inf, carpeta, idx)
    tareas, filas = [], []
    if idx >= ETAPAS.index("delegacion"):
        tareas = analizar_delegacion(inf, carpeta, spec)
    if idx >= ETAPAS.index("implementacion"):
        filas = analizar_matriz(inf, carpeta, spec, idx, repo)
        if repo is None:
            inf.no_comprobado.append("existencia de commits, pruebas y evidencias (falta --repo <carpeta del repositorio>)")
    if idx >= ETAPAS.index("cierre"):
        analizar_cierre(inf, carpeta, tareas)
        inf.no_comprobado.append("que las pruebas sean buenas y los criterios correctos: eso es la revisión (metodo/terminado-y-trazabilidad.md §8)")
    errores = [h for h in inf.h if h["nivel"] == "ERROR"]
    return {
        "carpeta": str(carpeta), "etapa": etapa,
        "resumen": {"requisitos": len(spec["requisitos"]) if spec else 0, "criterios": len(spec["criterios"]) if spec else 0,
                    "tareas": len(tareas), "filas": len(filas), "errores": len(errores), "avisos": len(inf.h) - len(errores)},
        "hallazgos": inf.h, "no_comprobado": inf.no_comprobado, "ok": not errores,
    }


def estado_del_cambio(carpeta, repo=None):
    """Primera etapa cuya puerta no se cumple (para `harness siguiente`). Devuelve (etapa, informe) o ('cerrable', informe)."""
    for e in ETAPAS:
        r = analizar(carpeta, e, repo)
        if not r["ok"]:
            return e, r
    return "cerrable", r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cambio", help="carpeta del cambio (con especificacion.md, delegacion.md, matriz.md, cierre.md)")
    ap.add_argument("--etapa", choices=ETAPAS, default="cierre", help="hasta qué puerta comprobar (por defecto, cierre)")
    ap.add_argument("--repo", help="repositorio del proyecto: comprueba commits, pruebas y evidencias (git local, sin red)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    carpeta = pathlib.Path(a.cambio).expanduser()
    if not carpeta.is_dir():
        print(f"No existe la carpeta del cambio: {carpeta}\nCrea una desde las plantillas (plantillas/especificacion.md, …) o mira el ejemplo: plantillas/ejemplos/cambio-ejemplo/", file=sys.stderr)
        return 2
    if a.repo and not pathlib.Path(a.repo).expanduser().is_dir():
        print(f"No existe la carpeta del repositorio: {a.repo}", file=sys.stderr)
        return 2
    r = analizar(carpeta, a.etapa, a.repo)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        s = r["resumen"]
        print(f"Trazabilidad de {r['carpeta']} · etapa {r['etapa']}")
        print(f"{s['requisitos']} requisito(s) · {s['criterios']} criterio(s) · {s['tareas']} tarea(s) delegada(s) · {s['filas']} fila(s) de matriz")
        for h in r["hallazgos"]:
            print(f"  [{h['nivel']}] {h['codigo']} {h['donde']}: {h['mensaje']}")
        if r["no_comprobado"]:
            print("No comprobado:")
            for t in r["no_comprobado"]:
                print("  - " + t)
        print(f"\n{s['errores']} error(es), {s['avisos']} aviso(s)")
        print("RESULTADO:", "OK" if r["ok"] else "FALLA")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
