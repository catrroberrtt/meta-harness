#!/usr/bin/env python3
"""Gate de extracción del meta harness: decide si un documento de una instancia puede pasar al repositorio genérico.

<!-- tipo: herramienta · capa: 4 -->

Uso:
  python3 harness-extraer.py <doc.md> [<doc2.md> ...]                         evalúa (SOLO LECTURA, modo por defecto)
  python3 harness-extraer.py <doc.md> --destino <carpeta-harness> --aplicar   si PASA, COPIA (no mueve) y registra el sha256
  python3 harness-extraer.py --inventario [--md] <doc.md> ...                 cuenta las referencias al proyecto por clase
Opciones: --instancia <raíz> (por defecto, el directorio actual) · --stack <nombre> (tipo perfil al aplicar)
          --adaptador <nombre> (tipo adaptador al aplicar) · --ejemplos N (con --inventario) · --json

«Lo propio del proyecto» NO está escrito en esta herramienta. Sale, en este orden, de:
  1. el archivo que indique la variable de entorno HARNESS_PATRON_PROYECTO;
  2. `patrones-proyecto.txt` en la raíz de la instancia (una expresión regular por línea; una línea que empieza con `#` es comentario);
  3. un patrón genérico de claves de ticket (ABC-123) y números de PR (PR #12, #123).

Reglas:
  R1  declara `<!-- tipo: X · capa: N -->` (en las primeras 12 líneas), X en {metodo, estandar, perfil, adaptador, herramienta}, capa coherente.
  R2  especificidad = 0: ninguna línea casa con el patrón de lo propio del proyecto.
  R3  sin credenciales ni datos de personas (claves, contraseñas con valor, tokens, correos, teléfonos, rutas /home/<usuario>).
  R4  enlaces relativos a archivos: si no resuelven hoy, falla; si resuelven hoy pero quedarían fuera del destino, se LISTAN.
Las reglas duras de un proyecto (RD-n) son parte del método y no cuentan como atadura: no las pongas en patrones-proyecto.txt.
Garantías: sin --aplicar no escribe nada; con --aplicar solo escribe si TODAS las reglas pasan; nunca borra ni modifica el original;
no sobrescribe un destino distinto. Solo biblioteca estándar.
"""
import re, sys, os, json, hashlib, shutil, argparse, pathlib, datetime, collections

TIPOS = {  # tipo -> (capa, subcarpeta en el harness)
    "metodo": (1, "metodo"), "estandar": (2, "estandares"), "perfil": (3, "perfiles/{stack}"),
    "adaptador": (3, "adaptadores/{adaptador}"), "herramienta": (4, "herramientas"),
}
ADAPTADORES = ("jira", "confluence", "drive-md")
TAG = re.compile(r"<!--\s*tipo:\s*(\w+)(?:\s*[·|]\s*capa:\s*(\d))?[^>]*-->")

# Patrón genérico: clave de ticket (ABC-123) y números de PR. Excluye identificadores públicos, las reglas duras (RD-n) y los
# identificadores de regla de los perfiles (ARQ, PAT, COD, DAT, PRU, SEG, REN, OBS, ERR, REC): son del formato del harness, no de un tracker.
CLAVE_TICKET = r"\b(?!(?:UTF|SHA|ISO|RFC|HTTP|TLS|AES|RS|HS|ES|MD|CVE|RD|WCAG|ECMA|IEEE|ASCII|ARQ|PAT|COD|DAT|PRU|SEG|REN|OBS|ERR|REC)-)[A-Z][A-Z0-9]{1,9}-\d+\b"
NUMERO_PR = r"\bPR\s?#\d+|(?<![\w&])#\d{3,5}\b"
PATRON_GENERICO = [CLAVE_TICKET, NUMERO_PR]
ARCHIVO_PATRONES = "patrones-proyecto.txt"
VARIABLE = "HARNESS_PATRON_PROYECTO"


class Patron:
    """Conjunto de expresiones regulares; cada una se compila por separado (admite banderas propias como (?i))."""
    def __init__(self, regex, origen):
        self.regex = [re.compile(r) for r in regex]
        self.origen = origen

    def finditer(self, s):
        hallados = []
        for rx in self.regex:
            hallados.extend(rx.finditer(s))
        return sorted(hallados, key=lambda m: (m.start(), -(m.end() - m.start())))

    def search(self, s):
        return bool(self.finditer(s))

    def sustituir(self, s, f):
        """Reemplaza cada coincidencia (sin solapar) por f(texto)."""
        out, pos = [], 0
        for m in self.finditer(s):
            if m.start() < pos or m.end() == m.start():
                continue
            out.append(s[pos:m.start()]); out.append(f(m.group(0))); pos = m.end()
        out.append(s[pos:])
        return "".join(out)


def leer_lista(ruta):
    """Una entrada por línea; las que empiezan con `#` son comentario; ignora las vacías."""
    res = []
    for l in pathlib.Path(ruta).read_text(encoding="utf8", errors="ignore").splitlines():
        l = l.strip()
        if l and not l.startswith("#"):
            res.append(l)
    return res


def cargar_patron(instancia=None):
    """Devuelve un Patron según la prioridad: variable de entorno > archivo de la instancia > genérico."""
    env = os.environ.get(VARIABLE)
    if env:
        if not os.path.isfile(env):
            raise SystemExit(f"{VARIABLE} apunta a «{env}», que no es un archivo")
        return Patron(leer_lista(env), f"variable {VARIABLE}")
    if instancia is not None:
        f = pathlib.Path(instancia) / ARCHIVO_PATRONES
        if f.is_file():
            regex = leer_lista(f)
            if regex:
                return Patron(regex, f"{ARCHIVO_PATRONES} de la instancia")
    return Patron(PATRON_GENERICO, "patrón genérico (claves de ticket y PR)")


# R3
PLACEHOLDER = re.compile(r"^(?:x+|\*+|\.+|<.*>|\$\{?\w+\}?|\{\{.*\}\}|\[.*\]|tu[-_]?\w*|xxx\w*|changeme|secret|password|token|valor|\.\.\.)$", re.I)
R3_PATRONES = [
    ("clave AWS", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("clave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("token de GitHub/Slack", re.compile(r"\b(?:ghp_|gho_|github_pat_|xox[abp]-)[A-Za-z0-9_-]{16,}")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}")),
    ("Bearer con valor", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{24,}")),
    ("correo de persona", re.compile(r"\b(?!git@)[\w.+-]+@(?!example\.|noreply|users\.noreply)[A-Za-z][\w-]*\.[A-Za-z][\w.-]*\b")),
    ("teléfono", re.compile(r"(?<![\w.])\+\d{2,3}[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{3}\b")),
    ("documento de identidad", re.compile(r"\b(?:DNI|RUC|CE)\s*[:#]?\s*\d{8,11}\b")),
    ("ruta con usuario del sistema", re.compile(r"/home/[a-z][\w.-]*|/Users/[A-Za-z][\w.-]*|C:\\Users\\\w+")),
]
R3_ASIGNACION = re.compile(r"""(?ix)\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|MYSQL_PWD|DB_PASS\w*)\b["']?\s*[=:]\s*["']?([^\s"'`<>,;)]{6,})""")
ENLACE = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def leer(p):
    return pathlib.Path(p).read_text(encoding="utf8", errors="ignore")


def sin_codigo_cercado(lineas):
    """Devuelve [(nº línea 1-based, texto, dentro_de_cerco)]."""
    cerco, out = False, []
    for i, l in enumerate(lineas, 1):
        if l.strip().startswith("```"):
            cerco = not cerco
            out.append((i, l, True)); continue
        out.append((i, l, cerco))
    return out


def r1(lineas):
    cab = "\n".join(lineas[:12])
    m = TAG.search(cab)
    if not m:
        return None, ["R1 sin «<!-- tipo: … -->» en las primeras 12 líneas"]
    tipo, capa = m.group(1), m.group(2)
    fallas = []
    if tipo not in TIPOS:
        fallas.append(f"R1 tipo «{tipo}» no permitido en el harness (permitidos: {', '.join(TIPOS)})")
    elif capa is not None and int(capa) != TIPOS[tipo][0]:
        fallas.append(f"R1 capa {capa} no corresponde al tipo «{tipo}» (esperada {TIPOS[tipo][0]})")
    return tipo, fallas


def r2(lineas, patron):
    fallas = []
    for i, l in enumerate(lineas, 1):
        hits = [m.group(0) for m in patron.finditer(l)]
        if hits:
            fallas.append(f"R2 línea {i}: {', '.join(sorted(set(hits)))}")
    return fallas


def r3(lineas):
    fallas = []
    for i, l in enumerate(lineas, 1):
        for nombre, rx in R3_PATRONES:
            for m in rx.finditer(l):
                fallas.append(f"R3 línea {i}: {nombre}: «{m.group(0)[:40]}»")
        for m in R3_ASIGNACION.finditer(l):
            val = m.group(1)
            if not PLACEHOLDER.match(val) and not re.fullmatch(r"[A-Z][A-Z0-9_]+", val) and not val.startswith(("$", "{", "<")):
                fallas.append(f"R3 línea {i}: valor asignado a credencial: «{m.group(0)[:50]}»")
    return fallas


def enlaces(doc: pathlib.Path, lineas):
    """(rotos, pendientes): rotos = no resuelven hoy; pendientes = resuelven hoy y saldrían del destino."""
    rotos, pend = [], []
    for i, l, cerco in sin_codigo_cercado(lineas):
        if cerco:
            continue
        for m in ENLACE.finditer(l):
            href = m.group(1).split("#")[0]
            if not href or re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", href, re.I):
                continue
            (pend if (doc.parent / href).resolve().exists() else rotos).append((i, href))
    return rotos, pend


def evaluar(doc: pathlib.Path, patron: Patron):
    lineas = leer(doc).splitlines()
    tipo, f1 = r1(lineas)
    f2, f3 = r2(lineas, patron), r3(lineas)
    rotos, pend = enlaces(doc, lineas)
    f4 = [f"R4 línea {i}: enlace roto: {h}" for i, h in rotos]
    reglas = {"R1": f1, "R2": f2, "R3": f3, "R4": f4}
    return {"doc": doc, "tipo": tipo, "reglas": reglas, "pasa": not any(reglas.values()),
            "enlaces_pendientes": [{"linea": i, "enlace": h} for i, h in pend]}


def subcarpeta(tipo, stack, adaptador):
    plantilla = TIPOS[tipo][1]
    if "{stack}" in plantilla:
        if not stack:
            return None, "tipo perfil: falta --stack <nombre>"
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", stack):
            return None, "stack inválido"
        return plantilla.format(stack=stack), None
    if "{adaptador}" in plantilla:
        if adaptador not in ADAPTADORES:
            return None, f"tipo adaptador: falta --adaptador {{{'|'.join(ADAPTADORES)}}}"
        return plantilla.format(adaptador=adaptador), None
    return plantilla, None


def sha256(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def ahora():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def aplicar(res, destino: pathlib.Path, stack, adaptador, base: pathlib.Path):
    """Copia solo si pasa. Devuelve (ok, mensaje)."""
    if not res["pasa"]:
        return False, "no pasa: no se escribe nada"
    if not destino.is_dir():
        return False, f"el destino {destino} no existe (no se crea el repositorio del harness)"
    sub, err = subcarpeta(res["tipo"], stack, adaptador)
    if err:
        return False, err
    doc = res["doc"]
    final = destino / sub / doc.name
    h = sha256(doc)
    if final.exists() and sha256(final) != h:
        return False, f"{final} ya existe con contenido distinto: no se sobrescribe"
    final.parent.mkdir(parents=True, exist_ok=True)
    if not final.exists():
        shutil.copy2(doc, final)
    if sha256(final) != h:
        return False, "la copia no coincide con el original (sha256)"
    reg = destino / ".harness-extraido.json"
    datos = {"extraidos": []}
    if reg.exists():
        try:
            datos = json.loads(reg.read_text(encoding="utf8"))
        except Exception:
            return False, f"{reg} ilegible: no se toca"
    datos["extraidos"] = [e for e in datos.get("extraidos", []) if e.get("destino") != f"{sub}/{doc.name}"]
    try:
        origen = doc.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        origen = doc.name
    datos["extraidos"].append({"origen": origen, "destino": f"{sub}/{doc.name}", "tipo": res["tipo"], "sha256": h,
                               "fecha": ahora(), "enlaces_que_se_rompen_en_el_destino": res["enlaces_pendientes"]})
    reg.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    return True, f"copiado a {final} (sha256 {h[:12]}…); original intacto; registro en {reg}"


# ---------- inventario por clase ----------
EXTRA = [
    ("ruta", "rutas locales (/home/…, ~/…)", re.compile(r"/home/[a-z]\w*|~/[\w/.-]+")),
    ("puerto", "puertos de BD local (3306-3309)", re.compile(r"\b330[6-9]\b")),
    ("cuenta", "cuentas en la nube (12 dígitos)", re.compile(r"\b\d{12}\b")),
]
RX_TICKET, RX_PR = re.compile(CLAVE_TICKET), re.compile(NUMERO_PR)


def clase(s):
    if RX_PR.fullmatch(s): return "pr"
    if RX_TICKET.fullmatch(s): return "ticket"
    return "otro_del_patron"


def inventario(doc, patron, nej):
    lineas = leer(doc).splitlines()
    cuenta, ej = collections.Counter(), collections.defaultdict(collections.Counter)
    for l in lineas:
        for m in patron.finditer(l):
            c = clase(m.group(0)); cuenta[c] += 1; ej[c][m.group(0)] += 1
        for k, _d, rx in EXTRA:
            for m in rx.finditer(l):
                cuenta[k] += 1; ej[k][m.group(0)] += 1
    return {"lineas": len(lineas), "cuenta": cuenta, "ejemplos": {k: [x for x, _ in v.most_common(nej)] for k, v in ej.items()}}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gate de extracción al meta harness (solo lectura por defecto)")
    ap.add_argument("docs", nargs="+")
    ap.add_argument("--instancia", default=".", help="raíz de la instancia (donde vive patrones-proyecto.txt)")
    ap.add_argument("--destino"); ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--stack"); ap.add_argument("--adaptador")
    ap.add_argument("--inventario", action="store_true"); ap.add_argument("--md", action="store_true")
    ap.add_argument("--ejemplos", type=int, default=2); ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.aplicar and not a.destino:
        ap.error("--aplicar exige --destino <carpeta-del-harness>")
    base = pathlib.Path(a.instancia)
    patron = cargar_patron(base)
    docs = []
    for d in a.docs:
        p = pathlib.Path(d)
        if not p.is_file():
            print(f"no existe: {d}", file=sys.stderr); return 2
        docs.append(p)
    if not a.json:
        print(f"[patrón de lo propio del proyecto: {patron.origen}]")

    if a.inventario:
        cols = ["ticket", "pr", "otro_del_patron"] + [k for k, _d, _r in EXTRA]
        cab = ["documento", "líneas", *cols]
        if a.md:
            print("| " + " | ".join(cab) + " |"); print("|" + "---|" * len(cab))
        else:
            print("\t".join(cab))
        tot, nl = collections.Counter(), 0
        for p in docs:
            r = inventario(p, patron, a.ejemplos)
            tot.update(r["cuenta"]); nl += r["lineas"]
            fila = [p.name, r["lineas"], *[r["cuenta"].get(c, 0) for c in cols]]
            print(("| " + " | ".join(map(str, fila)) + " |") if a.md else "\t".join(map(str, fila)))
        print("TOTAL\t" + "\t".join(map(str, [nl] + [tot.get(c, 0) for c in cols])))
        return 0

    resultados = [evaluar(p, patron) for p in docs]
    salida_json = []
    for r in resultados:
        if a.json:
            salida_json.append({"doc": r["doc"].name, "tipo": r["tipo"], "pasa": r["pasa"],
                                "fallas": {k: v for k, v in r["reglas"].items() if v}, "enlaces_pendientes": r["enlaces_pendientes"]})
        else:
            print(f"{'PASA   ' if r['pasa'] else 'NO PASA'} {r['doc']}  [tipo: {r['tipo'] or '—'}]")
            for k, fs in r["reglas"].items():
                for f in (fs[:8] if len(docs) > 1 else fs):
                    print("   ·", f)
                if len(docs) > 1 and len(fs) > 8:
                    print(f"   · … {k}: {len(fs) - 8} más")
            if r["pasa"] and r["enlaces_pendientes"]:
                print(f"   i {len(r['enlaces_pendientes'])} enlace(s) relativo(s) que saldrían del destino (se listarán en el registro)")
    if a.json:
        print(json.dumps(salida_json, ensure_ascii=False, indent=2))
    if a.aplicar:
        for r in resultados:
            ok, msg = aplicar(r, pathlib.Path(a.destino), a.stack, a.adaptador, base)
            print(("APLICADO: " if ok else "NO APLICADO: ") + str(r["doc"]) + " — " + msg)
    if len(docs) > 1 and not a.json:
        print(f"\nResumen: {sum(1 for r in resultados if r['pasa'])} pasan de {len(resultados)}")
    return 0 if all(r["pasa"] for r in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
