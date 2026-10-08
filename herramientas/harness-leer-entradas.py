#!/usr/bin/env python3
"""Lector de entradas de partida para los modos `init` (desde cero) y `migrar` (SOLO LECTURA).

Recorre una carpeta con la información de partida y produce un informe de entendimiento: entidades y campos (con su origen
archivo:línea), relaciones (con evidencia y confianza), motor de base de datos propuesto (con evidencia y alternativa),
requisitos, preguntas abiertas del origen y una lista de preguntas donde la información falte o sea ambigua.

Entrega 1: Markdown (.md) y SQL (.sql, MySQL y PostgreSQL). Entrega 2: hojas de cálculo (.csv, .tsv, .xlsx/.xlsm; sin
librerías externas, sin ejecutar nada del archivo) clasificadas por sus encabezados en diccionario/modelo, catálogo o datos de
ejemplo; los valores que parecen secretos se enmascaran. Todo lo demás (.xls, .ods, .numbers, protegidos, corruptos) se lista
como «no leído» con la razón y qué pedir. Nunca inventa un modelo: si no hay nada legible, sale con 2.

Uso: python3 harness-leer-entradas.py <carpeta> [--json|--md] [--salida archivo]
Salida: 0 informe generado · 2 carpeta vacía / sin nada legible / argumentos inválidos (p. ej. --salida dentro de la carpeta).
Solo stdlib. No escribe nada dentro de la carpeta de entradas.
"""
import argparse, csv, io, json, pathlib, posixpath, re, sys, unicodedata, zipfile
import xml.etree.ElementTree as ET
from collections import Counter

MAX_BYTES = 2_000_000
EXCLUIR_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
TABULARES = {".csv", ".tsv", ".xlsx", ".xlsm"}
NO_LEIBLES = {".xls": "formato Excel antiguo (.xls)", ".ods": "hoja OpenDocument (.ods)", ".numbers": "hoja de Apple Numbers (.numbers)"}
MAX_FILAS = 20_000
MAX_PARTE = 30_000_000   # tope por parte descomprimida de un .xlsx (defensa ante zip bombs)
MAX_HOJAS = 50
MAX_COLS = 1000
KW_COL = {"not", "null", "default", "primary", "references", "auto_increment", "unique", "comment", "check",
          "generated", "constraint", "collate", "character", "on", "autoincrement", "identity"}
MODIFICADORES = r"unsigned|zerofill|varying|precision|signed|with(?:out)? time zone"
ENTIDAD_ENCAB = re.compile(r"^(?:entidad|modelo|tabla)\s*[:\-–—]?\s*(.+)$", re.I)
COL_ENTIDAD = {"entidad", "modelo", "tabla"}
COL_CAMPO = {"campo", "atributo", "columna", "field", "propiedad"}
REQ = re.compile(r"\b(debe|deben|deber[aá]|deber[aá]n)\b|\bel sistema\b", re.I)
ABIERTA = re.compile(r"\?|\bTODO\b|\bTBD\b|por definir", re.I)
MOTORES_MD = {"PostgreSQL": r"postgres(?:ql)?", "MySQL": r"mysql|mariadb", "MongoDB": r"mongo(?:db)?", "SQLite": r"sqlite"}


# ───────────────────────── utilidades ─────────────────────────
def linea(texto, pos):
    return texto.count("\n", 0, pos) + 1


def limpiar(texto):
    """Reemplaza comentarios SQL por espacios (conserva posiciones/saltos). Devuelve (limpio, {linea: comentario})."""
    out, coms, i, n, q = [], {}, 0, len(texto), None
    while i < n:
        c = texto[i]
        if q:
            out.append(c)
            if c == q:
                q = None
            i += 1
        elif c in "'\"`":
            q = c; out.append(c); i += 1
        elif texto.startswith("--", i) or c == "#" and False:
            j = texto.find("\n", i); j = n if j < 0 else j
            coms.setdefault(linea(texto, i), texto[i + 2:j].strip())
            out.append(" " * (j - i)); i = j
        elif texto.startswith("/*", i):
            j = texto.find("*/", i + 2); j = n if j < 0 else j + 2
            seg = texto[i:j]
            coms.setdefault(linea(texto, i), seg[2:-2].strip())
            out.append(re.sub(r"[^\n]", " ", seg)); i = j
        else:
            out.append(c); i += 1
    return "".join(out), coms


def partir_comas(cuerpo):
    """Divide por comas de nivel superior. Devuelve [(offset_inicio, offset_fin, texto)]."""
    partes, prof, q, ini = [], 0, None, 0
    for i, c in enumerate(cuerpo):
        if q:
            if c == q: q = None
        elif c in "'\"`": q = c
        elif c == "(": prof += 1
        elif c == ")": prof -= 1
        elif c == "," and prof == 0:
            partes.append((ini, i, cuerpo[ini:i])); ini = i + 1
    partes.append((ini, len(cuerpo), cuerpo[ini:]))
    return [p for p in partes if p[2].strip()]


def ident(s):
    s = s.strip().strip("`\"[]")
    return s.split(".")[-1].strip("`\"[]")


def lista_cols(s):
    return [ident(x) for x in s.split(",") if x.strip()]


def cuerpo_balanceado(texto, ini):
    """texto[ini] == '('. Devuelve índice del ')' que cierra o -1."""
    prof, q = 0, None
    for i in range(ini, len(texto)):
        c = texto[i]
        if q:
            if c == q: q = None
        elif c in "'\"`": q = c
        elif c == "(": prof += 1
        elif c == ")":
            prof -= 1
            if prof == 0: return i
    return -1


# ───────────────────────── SQL ─────────────────────────
RX_CREATE = re.compile(r"CREATE\s+(?:TEMP(?:ORARY)?\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?((?:[`\"\[]?\w+[`\"\]]?\.)?[`\"\[]?\w+[`\"\]]?)\s*\(", re.I)
RX_INDEX = re.compile(r"CREATE\s+(UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\"]?\w+[`\"]?)\s+ON\s+((?:[`\"]?\w+[`\"]?\.)?[`\"]?\w+[`\"]?)[^(;]*\(([^)]*)\)", re.I)
RX_ALTER_FK = re.compile(r"ALTER\s+TABLE\s+(?:ONLY\s+)?((?:[`\"]?\w+[`\"]?\.)?[`\"]?\w+[`\"]?)\s+ADD\s+(?:CONSTRAINT\s+[`\"]?\w+[`\"]?\s+)?FOREIGN\s+KEY\s*\(([^)]*)\)\s*REFERENCES\s+((?:[`\"]?\w+[`\"]?\.)?[`\"]?\w+[`\"]?)\s*(?:\(([^)]*)\))?", re.I)
MARC_MYSQL = {"backticks": r"`", "ENGINE=": r"\bENGINE\s*=", "AUTO_INCREMENT": r"\bAUTO_INCREMENT\b", "UNSIGNED": r"\bUNSIGNED\b",
              "DEFAULT CHARSET": r"\bDEFAULT\s+CHARSET\b", "TINYINT(1)": r"\bTINYINT\s*\(\s*1\s*\)"}
MARC_PG = {"SERIAL": r"\b(?:BIG|SMALL)?SERIAL\b", "uuid": r"\buuid\b", "jsonb": r"\bjsonb\b", "cast ::": r"::\s*\w+",
           "TIMESTAMPTZ": r"\bTIMESTAMPTZ\b|\btimestamp\s+with(?:out)?\s+time\s+zone\b", "CREATE EXTENSION": r"\bCREATE\s+EXTENSION\b",
           "IDENTITY": r"\bGENERATED\s+\w+\s+AS\s+IDENTITY\b", "comillas dobles en identificadores": r'(?<![\w\'])"[A-Za-z_]\w*"'}


def parsear_columna(texto_parte, ln, comentarios_linea):
    t = texto_parte.strip()
    m = re.match(r'([`"\[]?[\w$]+[`"\]]?)\s*(.*)$', t, re.S)
    if not m: return None
    nombre, resto = ident(m.group(1)), m.group(2)
    mt = re.match(r"([A-Za-z_]\w*)", resto)
    tipo, pos = "", 0
    if mt:
        tipo, pos = mt.group(1), mt.end()
        while True:
            mm = re.match(r"\s*(\([^)]*\))", resto[pos:]) or re.match(rf"\s+(?:{MODIFICADORES})\b", resto[pos:], re.I)
            if not mm: break
            tipo += (" " if not mm.group(0).lstrip().startswith("(") else "") + mm.group(0).strip(); pos += mm.end()
        if resto[pos:pos + 2] == "[]": tipo += "[]"
        if mt.group(1).lower() in KW_COL: tipo = ""
    pk = bool(re.search(r"\bPRIMARY\s+KEY\b", resto, re.I))
    nn = bool(re.search(r"\bNOT\s+NULL\b", resto, re.I)) or pk
    fk = None
    mr = re.search(r"\bREFERENCES\s+((?:[`\"]?\w+[`\"]?\.)?[`\"]?\w+[`\"]?)\s*(?:\(([^)]*)\))?", resto, re.I)
    if mr: fk = {"tabla": ident(mr.group(1)), "columnas": lista_cols(mr.group(2) or "")}
    mc = re.search(r"\bCOMMENT\s*'((?:[^']|'')*)'", resto, re.I)
    com = mc.group(1) if mc else comentarios_linea
    return {"nombre": nombre, "tipo": tipo, "not_null": nn, "pk": pk, "unico": bool(re.search(r"\bUNIQUE\b", resto, re.I)),
            "comentario": com or "", "origen": ln, "_fk": fk}


def leer_sql(texto, rel):
    limpio, coms = limpiar(texto)
    tablas, indices, fks_extra = [], [], []
    for m in RX_CREATE.finditer(limpio):
        ap = m.end() - 1
        ci = cuerpo_balanceado(limpio, ap)
        if ci < 0: continue
        cuerpo = limpio[ap + 1:ci]
        fin = limpio.find(";", ci); cola = limpio[ci + 1:(len(limpio) if fin < 0 else fin)]
        mcom = re.search(r"\bCOMMENT\s*=?\s*'((?:[^']|'')*)'", cola, re.I)
        t = {"nombre": ident(m.group(1)), "archivo": rel, "linea": linea(limpio, m.start()), "columnas": [], "pk": [], "fks": [],
             "indices": [], "comentario": mcom.group(1) if mcom else ""}
        for ini, fin_p, parte in partir_comas(cuerpo):
            off = ap + 1 + ini + (len(parte) - len(parte.lstrip()))
            ln = linea(limpio, off); ln_fin = linea(limpio, ap + 1 + fin_p)
            p = parte.strip()
            mpk = re.match(r"(?:CONSTRAINT\s+\S+\s+)?PRIMARY\s+KEY\s*\(([^)]*)\)", p, re.I)
            mfk = re.match(r"(?:CONSTRAINT\s+\S+\s+)?FOREIGN\s+KEY\s*(?:\S+\s*)?\(([^)]*)\)\s*REFERENCES\s+((?:[`\"]?\w+[`\"]?\.)?[`\"]?\w+[`\"]?)\s*(?:\(([^)]*)\))?", p, re.I)
            mix = re.match(r"(?:CONSTRAINT\s+\S+\s+)?(UNIQUE\s+)?(?:KEY|INDEX|FULLTEXT\s+KEY|FULLTEXT\s+INDEX|UNIQUE)\s*([`\"]?\w+[`\"]?)?\s*\(([^)]*)\)", p, re.I)
            if mpk: t["pk"] = lista_cols(mpk.group(1))
            elif mfk:
                for i, c in enumerate(lista_cols(mfk.group(1))):
                    dest = lista_cols(mfk.group(3) or "")
                    t["fks"].append({"columna": c, "tabla": ident(mfk.group(2)), "columna_destino": dest[i] if i < len(dest) else "", "linea": ln})
            elif mix:
                t["indices"].append({"nombre": ident(mix.group(2) or ""), "columnas": lista_cols(mix.group(3)), "unico": bool(mix.group(1)) or p.upper().startswith("UNIQUE"), "linea": ln})
            elif re.match(r"(CONSTRAINT|CHECK|EXCLUDE|LIKE)\b", p, re.I): continue
            else:
                col = parsear_columna(p, ln, " ".join(coms[l] for l in range(ln, ln_fin + 1) if l in coms))
                if col: t["columnas"].append(col)
        for c in t["columnas"]:
            fk = c.pop("_fk")
            if fk: t["fks"].append({"columna": c["nombre"], "tabla": fk["tabla"], "columna_destino": (fk["columnas"] or [""])[0], "linea": c["origen"]})
            if c["pk"] and c["nombre"] not in t["pk"]: t["pk"].append(c["nombre"])
        for c in t["columnas"]:
            if c["nombre"] in t["pk"]: c["pk"] = c["not_null"] = True
        tablas.append(t)
    for m in RX_INDEX.finditer(limpio):
        indices.append({"tabla": ident(m.group(3)), "nombre": ident(m.group(2)), "columnas": lista_cols(m.group(4)), "unico": bool(m.group(1)), "linea": linea(limpio, m.start())})
    for m in RX_ALTER_FK.finditer(limpio):
        dest = lista_cols(m.group(4) or "")
        for i, c in enumerate(lista_cols(m.group(2))):
            fks_extra.append({"tabla_origen": ident(m.group(1)), "columna": c, "tabla": ident(m.group(3)), "columna_destino": dest[i] if i < len(dest) else "", "linea": linea(limpio, m.start())})
    marcas = {"mysql": {}, "postgresql": {}}
    for motor, tabla in (("mysql", MARC_MYSQL), ("postgresql", MARC_PG)):
        for k, rx in tabla.items():
            mm = re.search(rx, limpio, re.I if k != "comillas dobles en identificadores" else 0)
            if mm: marcas[motor][k] = linea(limpio, mm.start())
    return tablas, indices, fks_extra, marcas


# ───────────────────────── Markdown ─────────────────────────
def celdas(l):
    return [c.strip() for c in l.strip().strip("|").split("|")]


def leer_md(texto, rel):
    lineas = texto.splitlines()
    r = {"titulo": "", "secciones": [], "tablas": [], "listas": 0, "requisitos": [], "abiertas": [], "entidades": []}
    en_codigo, entidad, i, n = False, None, 0, len(lineas)
    lista_previa = False
    while i < n:
        l = lineas[i]; ln = i + 1; s = l.strip()
        if s.startswith("```") or s.startswith("~~~"):
            en_codigo = not en_codigo; i += 1; continue
        if en_codigo: i += 1; continue
        mh = re.match(r"(#{1,6})\s+(.+?)\s*#*\s*$", s)
        if mh:
            nivel, tit = len(mh.group(1)), mh.group(2)
            if nivel == 1 and not r["titulo"]: r["titulo"] = tit
            r["secciones"].append({"nivel": nivel, "titulo": tit, "linea": ln})
            me = ENTIDAD_ENCAB.match(re.sub(r"[*_`]", "", tit))
            entidad = me.group(1).strip() if me else None
            if entidad:
                r["entidades"].append({"nombre": entidad, "campos": [], "origen": f"{rel}:{ln}", "via": "encabezado"})
            lista_previa = False
        elif s.startswith("|") and i + 1 < n and re.match(r"^\s*\|?\s*:?-{2,}", lineas[i + 1]):
            cab = celdas(s); filas, j = [], i + 2
            while j < n and lineas[j].strip().startswith("|"):
                filas.append((j + 1, celdas(lineas[j]))); j += 1
            r["tablas"].append({"linea": ln, "columnas": cab, "filas": len(filas)})
            c0 = re.sub(r"[*_`]", "", cab[0]).lower() if cab else ""
            if c0 in COL_ENTIDAD:
                for fl, f in filas:
                    if f and f[0]:
                        r["entidades"].append({"nombre": re.sub(r"[*_`]", "", f[0]), "campos": [], "origen": f"{rel}:{fl}", "via": "tabla de entidades"})
            elif c0 in COL_CAMPO and entidad:
                ent = next((e for e in reversed(r["entidades"]) if e["nombre"] == entidad), None)
                cabl = [re.sub(r"[*_`]", "", c).lower() for c in cab]
                ti = cabl.index("tipo") if "tipo" in cabl else None
                for fl, f in filas:
                    if f and f[0] and ent is not None:
                        ent["campos"].append({"nombre": re.sub(r"[*_`]", "", f[0]), "tipo": f[ti] if ti is not None and ti < len(f) else "", "origen": f"{rel}:{fl}"})
            for fl, f in filas:
                txt = " | ".join(f)
                if REQ.search(txt): r["requisitos"].append({"texto": txt, "origen": f"{rel}:{fl}"})
                if ABIERTA.search(txt): r["abiertas"].append({"texto": txt, "origen": f"{rel}:{fl}"})
            i = j; continue
        else:
            if re.match(r"([-*+]|\d+[.)])\s+", s):
                if not lista_previa: r["listas"] += 1
                lista_previa = True
            elif s: lista_previa = False
            if s and REQ.search(s): r["requisitos"].append({"texto": re.sub(r"^([-*+]|\d+[.)])\s+", "", s), "origen": f"{rel}:{ln}"})
            if s and ABIERTA.search(s): r["abiertas"].append({"texto": re.sub(r"^([-*+]|\d+[.)])\s+", "", s), "origen": f"{rel}:{ln}"})
        i += 1
    menciones = {}
    for k, rx in MOTORES_MD.items():
        mm = re.search(rx, texto, re.I)
        if mm: menciones[k] = f"{rel}:{linea(texto, mm.start())}"
    r["motores_mencionados"] = menciones
    return r


# ───────────────────────── hojas de cálculo (.csv, .tsv, .xlsx) ─────────────────────────
NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def letras(i):
    s, i = "", i + 1
    while i:
        i, r = divmod(i - 1, 26); s = chr(65 + r) + s
    return s


def indice_col(ref):
    m = re.match(r"([A-Za-z]+)", ref or "")
    if not m: return None
    n = 0
    for ch in m.group(1).upper(): n = n * 26 + ord(ch) - 64
    return n - 1


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _parte(zf, nombre):
    info = zf.getinfo(nombre)
    if info.file_size > MAX_PARTE: raise ValueError(f"la parte {nombre} descomprimida supera {MAX_PARTE} bytes")
    data = zf.open(nombre).read(MAX_PARTE + 1)
    if len(data) > MAX_PARTE: raise ValueError(f"la parte {nombre} descomprimida supera {MAX_PARTE} bytes")
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data: raise ValueError(f"{nombre} declara DTD/entidades XML (no se procesa)")
    return data


def _texto_si(el):
    """Texto de un <si> o <is>: <t> directos y <r><t>, sin la fonética (<rPh>)."""
    out = []
    for ch in el:
        ln = _local(ch.tag)
        if ln == "t": out.append(ch.text or "")
        elif ln == "r":
            out += [(t.text or "") for t in ch if _local(t.tag) == "t"]
    return "".join(out)


def _numero(v):
    v = (v or "").strip()
    return re.sub(r"\.0+$", "", v) if re.fullmatch(r"-?\d+\.0+", v) else v


def _hoja_xlsx(data, sst):
    filas, recortado, prev = [], False, 0
    for _ev, el in ET.iterparse(io.BytesIO(data), events=("end",)):
        if _local(el.tag) != "row": continue
        try: nro = int(el.get("r") or prev + 1)
        except ValueError: nro = prev + 1
        prev, cel, sig = nro, {}, 0
        for c in el:
            if _local(c.tag) != "c": continue
            ci = indice_col(c.get("r"))
            ci = sig if ci is None else ci
            sig = ci + 1
            if ci >= MAX_COLS: continue
            t, v, f, ins = c.get("t"), None, None, None
            for ch in c:
                ln = _local(ch.tag)
                if ln == "v": v = ch.text or ""
                elif ln == "f": f = ch.text or ""
                elif ln == "is": ins = ch
            if t == "s":
                try: val = sst[int(v)]
                except (ValueError, IndexError, TypeError): val = ""
            elif t == "inlineStr": val = _texto_si(ins) if ins is not None else ""
            elif t == "b": val = "VERDADERO" if v == "1" else "FALSO"
            elif t in ("str", "e"): val = v or ""
            else: val = _numero(v)
            if val == "" and f: val = "=" + f
            if val != "": cel[ci] = val.strip() if isinstance(val, str) else val
        el.clear()
        if not cel: continue
        if len(filas) >= MAX_FILAS: recortado = True; break
        filas.append((nro, [cel.get(i, "") for i in range(max(cel) + 1)]))
    return filas, recortado


def leer_xlsx(p):
    """Devuelve (hojas, error). Un .xlsx es un zip de XML: se lee sin ejecutar nada (macros, vínculos y fórmulas se ignoran)."""
    try:
        cabeza = p.read_bytes()[:8]
    except OSError as e:
        return None, (f"no se pudo leer ({e.__class__.__name__})", "revisar permisos")
    if cabeza.startswith(OLE):
        return None, ("protegido con contraseña (o es un .xls antiguo con extensión .xlsx)", "quitar la contraseña y exportar a .xlsx sin protección, o a .csv")
    try:
        with zipfile.ZipFile(p) as zf:
            if any(i.flag_bits & 1 for i in zf.infolist()):
                return None, ("zip cifrado con contraseña", "quitar la contraseña y exportar a .xlsx sin protección, o a .csv")
            if "xl/workbook.xml" not in zf.namelist():
                return None, ("zip sin xl/workbook.xml (no es un .xlsx válido)", "volver a exportar desde la hoja de origen a .xlsx o .csv")
            wb = ET.fromstring(_parte(zf, "xl/workbook.xml"))
            rels = {}
            if "xl/_rels/workbook.xml.rels" in zf.namelist():
                for r in ET.fromstring(_parte(zf, "xl/_rels/workbook.xml.rels")):
                    t = r.get("Target") or ""
                    rels[r.get("Id")] = t.lstrip("/") if t.startswith("/") else posixpath.normpath("xl/" + t)
            sst = []
            if "xl/sharedStrings.xml" in zf.namelist():
                sst = [_texto_si(si) for si in ET.fromstring(_parte(zf, "xl/sharedStrings.xml")) if _local(si.tag) == "si"]
            hojas = []
            decl = [e for e in wb.iter() if _local(e.tag) == "sheet"][:MAX_HOJAS]
            for k, e in enumerate(decl, 1):
                ruta = rels.get(e.get(NS_REL)) or f"xl/worksheets/sheet{k}.xml"
                if ruta not in zf.namelist(): continue
                filas, rec = _hoja_xlsx(_parte(zf, ruta), sst)
                hojas.append({"hoja": e.get("name") or f"Hoja{k}", "filas": filas, "recortado": rec, "formato": "xlsx"})
            if not hojas: return None, ("el libro no tiene hojas legibles", "exportar a .csv")
            return hojas, None
    except zipfile.BadZipFile:
        return None, ("zip corrupto (no se pudo abrir el .xlsx)", "volver a exportar el archivo a .xlsx o .csv")
    except (ValueError, ET.ParseError, KeyError, RuntimeError, OSError, zipfile.LargeZipFile) as e:
        return None, (f"contenido ilegible ({e.__class__.__name__}: {str(e)[:80]})", "volver a exportar el archivo a .xlsx o .csv")


def decodificar(b):
    if b.startswith(b"\xef\xbb\xbf"): return b.decode("utf-8-sig"), "utf-8 con BOM"
    if b.startswith((b"\xff\xfe", b"\xfe\xff")): return b.decode("utf-16", errors="replace"), "utf-16"
    try: return b.decode("utf-8"), "utf-8"
    except UnicodeDecodeError: return b.decode("latin-1"), "latin-1"


def detectar_delimitador(texto, ext):
    muestra = [l for l in texto.splitlines()[:30] if l.strip()]
    orden = ["\t", ",", ";"] if ext == ".tsv" else [",", ";", "\t"]
    mejor, puntaje = orden[0], 0.0
    for d in orden:
        try: filas = list(csv.reader(muestra, delimiter=d))
        except csv.Error: continue
        if not filas: continue
        n, c = Counter(len(f) for f in filas).most_common(1)[0]
        pt = (c / len(filas)) * (1 if n > 1 else 0) + (min(n, 10) / 1000 if n > 1 else 0)
        if pt > puntaje + 1e-9: mejor, puntaje = d, pt
    return mejor


def leer_csv(p):
    try:
        texto, cod = decodificar(p.read_bytes())
    except OSError as e:
        return None, (f"no se pudo leer ({e.__class__.__name__})", "revisar permisos")
    delim = detectar_delimitador(texto, p.suffix.lower())
    csv.field_size_limit(10_000_000)
    filas, rec, previa = [], False, 0
    try:
        rd = csv.reader(io.StringIO(texto, newline=""), delimiter=delim)
        for fila in rd:
            ini, previa = previa + 1, rd.line_num
            cel = [c.strip() for c in fila]
            if not any(cel): continue
            if len(filas) >= MAX_FILAS: rec = True; break
            filas.append((ini, cel[:MAX_COLS]))
    except csv.Error as e:
        return None, (f"CSV mal formado ({str(e)[:80]})", "volver a exportar a .csv (UTF-8) o a .xlsx")
    nom = {"\t": "tabulador", ",": "coma", ";": "punto y coma"}[delim]
    return [{"hoja": "", "filas": filas, "recortado": rec, "formato": f"delimitador {nom}, codificación {cod}"}], None


def leer_tabular(p):
    return leer_xlsx(p) if p.suffix.lower() in (".xlsx", ".xlsm") else leer_csv(p)


# ---- clasificación por encabezados ----
ROLES = [(r, re.compile(x)) for r, x in [
    ("tabla", r"(tabla|entidad|table|entity|modelo|nombre (de )?(la )?(tabla|entidad)|(table|entity) name)"),
    ("campo", r"(campo|columna|field|column|atributo|attribute|propiedad|nombre (de(l)? )?(la )?(campo|columna|atributo)|(field|column|attribute) name)"),
    ("tipo", r"(tipo|type|tipo de dato|tipo dato|data type|datatype|tipo de campo)"),
    ("longitud", r"(longitud|largo|length|size|tamano|len|max length|longitud maxima|precision)"),
    ("nulo", r"(nulo|nullable|null|permite nulos?|acepta nulos|admite nulos?|is nullable|permite null|opcional)"),
    ("obligatorio", r"(obligatorio|requerido|required|mandatory|not null|no nulo)"),
    ("clave", r"(clave|key|pk|llave|primary key|clave primaria|pk fk|clave pk|tipo de clave|key type)"),
    ("descripcion", r"(descripcion|description|comentario|comment|comments|detalle|observaciones|observacion|definicion|notes|nota|notas|glosa)"),
    ("referencia", r"(referencia|referencias|reference|references|fk|foreign key|clave foranea|referencia fk|referencia a|ref|relacion|apunta a|tabla referenciada|referenced table)"),
    ("default", r"(default|valor por defecto|por defecto|defecto|valor defecto|ejemplo|example|valor ejemplo)")]]
H_CODIGO = {"codigo", "code", "cod", "valor", "value", "id", "clave", "key", "id codigo"}
H_DESC = {"descripcion", "description", "nombre", "name", "etiqueta", "label", "texto", "detalle", "glosa", "significado"}
H_EXTRA = {"estado", "activo", "orden", "active", "status", "order", "sort"}
RX_NOM_CATALOGO = re.compile(r"catalog|lista|valores|dominio|domain|enum|tipos?_|parametr", re.I)
RX_HOJA_GENERICA = re.compile(r"^(sheet|hoja|page|pagina)\s*\d*$", re.I)
SI = {"si", "s", "yes", "y", "true", "1", "x", "verdadero"}
NO = {"no", "n", "false", "0", "falso"}
SECRETO_H = re.compile(r"\b(password|passwd|pwd|contrasenas?|secret|secreto|token|api key|apikey|credenciales?|credential|private key|llave privada|clave secreta|clave privada|clave de acceso|clave acceso)\b")
SECRETO_GEN = {"clave", "llave", "pass"}
RX_SECRETO_V = [re.compile(x) for x in (
    r"^(sk|pk|rk)[-_](live|test)?[-_]?[A-Za-z0-9]{16,}$", r"^gh[pousr]_[A-Za-z0-9]{20,}", r"^AKIA[0-9A-Z]{16}$", r"^xox[abprs]-",
    r"^eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.", r"-----BEGIN [A-Z ]*PRIVATE KEY", r"^\$2[aby]\$\d\d\$", r"^[0-9a-fA-F]{32,}$")]
RX_SECRETO_KV = re.compile(r"(password|passwd|pwd|contrase\w+|secret|token|api[_-]?key)\s*[:=]\s*\S+", re.I)
RX_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?$|^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}([ T]\d{1,2}:\d{2}(:\d{2})?)?$")


def roles_de(headers):
    r = {}
    for i, h in enumerate(headers):
        n = norm(h)
        for rol, rx in ROLES:
            if rol not in r and rx.fullmatch(n): r[rol] = i; break
    return r


def es_catalogo_h(headers):
    hs = [norm(h) for h in headers if str(h).strip()]
    if not (2 <= len(hs) <= 4): return False
    return (all(h in H_CODIGO | H_DESC | H_EXTRA for h in hs) and any(h in H_CODIGO for h in hs)
            and (any(h in H_DESC for h in hs) or (len(hs) == 2 and all(h in H_CODIGO for h in hs))))


def secreto_valor(v):
    v = v.strip()
    if len(v) < 8 or v == "***": return False
    if RX_SECRETO_KV.search(v): return True
    if any(rx.search(v) for rx in RX_SECRETO_V): return True
    return bool(re.fullmatch(r"[A-Za-z0-9+/_=-]{32,}", v)) and bool(re.search(r"[A-Za-z]", v)) and bool(re.search(r"\d", v))


def clasificar(filas):
    """-> dict(clase, confianza, motivo, enc (índice en filas), headers, roles). clase: diccionario|catalogo|datos|desconocido."""
    cand = [k for k, (_n, c) in enumerate(filas[:10]) if sum(1 for x in c if x.strip()) >= 2]
    for k in cand:
        rl = roles_de(filas[k][1])
        if "campo" in rl and len(rl) >= 2:
            return {"clase": "diccionario", "confianza": "alta", "enc": k, "headers": filas[k][1], "roles": rl,
                    "motivo": "encabezados de diccionario: " + ", ".join(sorted(rl))}
    for k in cand:
        if es_catalogo_h(filas[k][1]):
            return {"clase": "catalogo", "confianza": "media", "enc": k, "headers": filas[k][1], "roles": {},
                    "motivo": "encabezados de código y descripción: " + ", ".join(h for h in filas[k][1] if h.strip())}
    k = cand[0] if cand else 0
    hs = filas[k][1]
    noblank = [h for h in hs if h.strip()]
    if len(filas) - k - 1 < 1 or not noblank or sum(1 for h in noblank if re.fullmatch(r"-?[\d.,]+", h)) * 2 > len(noblank):
        return {"clase": "desconocido", "confianza": "baja", "enc": k, "headers": hs, "roles": {},
                "motivo": "sin filas de datos o la primera fila no parece un encabezado"}
    return {"clase": "datos", "confianza": "media", "enc": k, "headers": hs, "roles": {},
            "motivo": "los encabezados no son de diccionario ni de catálogo: se tratan como los campos de una entidad"}


def ubic(rel, hoja):
    return f"{rel}#{hoja}" if hoja else rel


def enmascarar(cuerpo, cl, rel, hoja, secretos):
    """Enmascara EN SITIO (los valores nunca llegan al informe) y registra solo archivo, hoja y celda."""
    u, hs, rl = ubic(rel, hoja), cl["headers"], cl["roles"]
    cols = {}
    if cl["clase"] != "diccionario":
        for i, h in enumerate(hs):
            n = norm(h)
            if SECRETO_H.search(n) or (cl["clase"] != "catalogo" and n in SECRETO_GEN): cols[i] = h
    for i, h in cols.items():
        celdas_ = [nro for nro, c in cuerpo if i < len(c) and c[i].strip() and c[i] != "***"]
        for nro, c in cuerpo:
            if i < len(c) and c[i].strip(): c[i] = "***"
        if celdas_:
            secretos.append({"archivo": rel, "hoja": hoja, "celda": f"{letras(i)}{min(celdas_)}:{letras(i)}{max(celdas_)} ({len(celdas_)} celdas)",
                             "motivo": f"columna «{h}» con nombre de secreto"})
    libres = {rl.get("campo"), rl.get("tabla")} if cl["clase"] == "diccionario" else set()
    n_ind = 0
    for nro, c in cuerpo:
        if cl["clase"] == "diccionario" and "default" in rl and rl["campo"] < len(c) and rl["default"] < len(c):
            nc = norm(c[rl["campo"]])
            if (SECRETO_H.search(nc) or nc in SECRETO_GEN) and c[rl["default"]].strip():
                c[rl["default"]] = "***"; secretos.append({"archivo": rel, "hoja": hoja, "celda": f"{letras(rl['default'])}{nro}", "motivo": f"valor de ejemplo del campo «{c[rl['campo']]}»"})
        for i, v in enumerate(c):
            if i in cols or i in libres or not secreto_valor(v): continue
            c[i] = "***"; n_ind += 1
            if n_ind <= 10: secretos.append({"archivo": rel, "hoja": hoja, "celda": f"{letras(i)}{nro}", "motivo": "valor con aspecto de secreto (token, clave o hash)"})
    if n_ind > 10: secretos.append({"archivo": rel, "hoja": hoja, "celda": "(otras)", "motivo": f"{n_ind - 10} celdas más con aspecto de secreto"})
    return cols


def tipo_probable(vals):
    vals = [v for v in vals if v.strip()]
    if vals and all(v == "***" for v in vals): return "texto"   # columna enmascarada: no se infiere de valores
    vals = [v for v in vals if v != "***"]
    if not vals: return ""
    if all(re.fullmatch(r"-?(0|[1-9]\d*)", v) for v in vals): return "entero"
    if all(re.fullmatch(r"-?(0|[1-9]\d*)?[.,]\d+|-?(0|[1-9]\d*)", v) for v in vals): return "decimal"
    if all(RX_FECHA.match(v) for v in vals): return "fecha"
    return "texto"


def parsear_ref(txt):
    t = txt.strip()
    while True:
        n = re.sub(r"^(fk|ref\w*|references|a|->|→|=>)\W+", "", t, flags=re.I)
        if n == t: break
        t = n
    m = re.fullmatch(r"([A-Za-z_]\w*)(?:\s*[.(]\s*([A-Za-z_]\w*)\s*\)?)?", t)
    return (m.group(1), m.group(2) or "") if m else None


def agregar_entidad(inf, nombre, campos, origen, fuente):
    e = next((x for x in inf["entidades"] if x["nombre"].lower() == nombre.lower()), None)
    if e is None:
        inf["entidades"].append({"nombre": nombre, "campos": campos, "origenes": [origen], "fuente": fuente}); return
    e["origenes"].append(origen)
    if fuente not in e["fuente"].split("+"): e["fuente"] += "+" + fuente
    for c in campos:
        ya = next((x for x in e["campos"] if x["nombre"].lower() == c["nombre"].lower()), None)
        if ya is None: e["campos"].append(c)
        elif ya.get("inferido") and not c.get("inferido"): e["campos"][e["campos"].index(ya)] = c


def extraer_diccionario(cuerpo, cl, rel, hoja, nombre_base, inf):
    rl, u = cl["roles"], ubic(rel, hoja)
    def g(c, rol):
        i = rl.get(rol); return c[i].strip() if i is not None and i < len(c) else ""
    ncol = norm(cl["headers"][rl["nulo"]]) if "nulo" in rl else ""
    ult, ents, sin_tabla = "", {}, "tabla" not in rl
    for nro, c in cuerpo:
        if g(c, "tabla"): ult = g(c, "tabla")
        campo = g(c, "campo")
        if not campo: continue
        ent = ult or nombre_base
        tipo, lon = g(c, "tipo"), g(c, "longitud")
        if tipo and lon and "(" not in tipo: tipo = f"{tipo}({lon})"
        nn = None
        v = norm(g(c, "nulo"))
        if v:
            if v in SI or v in ("null", "nullable"): nn = False
            elif v in NO or v in ("not null", "no nulo"): nn = True
        v = norm(g(c, "obligatorio"))
        if v and nn is None:
            if v in SI or v in ("not null", "no nulo", "obligatorio", "requerido", "required"): nn = True
            elif v in NO or v in ("null", "opcional"): nn = False
        kv = norm(g(c, "clave"))
        hk = norm(cl["headers"][rl["clave"]]) if "clave" in rl else ""
        pk = bool(re.search(r"\bpk\b|primar|^p$", kv)) or (hk in ("pk", "primary key", "clave primaria") and kv in SI)
        fk = bool(re.search(r"\bfk\b|foran|foreign|externa|^f$", kv))
        ref = None
        rt = g(c, "referencia")
        if rt:
            pr = parsear_ref(rt)
            if pr: ref = {"tabla": pr[0], "columna": pr[1], "texto": rt}
            elif norm(rt) in SI | {"fk"}: fk = True
            else: inf["preguntas"].append({"pregunta": f"No se pudo interpretar la referencia «{rt}» de {ent}.{campo} ({u}:{nro}): ¿a qué tabla y columna apunta?",
                                           "intento": "busqué el patrón «tabla.columna», «tabla(columna)» o «tabla» (con prefijos FK/ref/→); no coincide"})
        if pk: nn = True
        ents.setdefault(ent, []).append({"nombre": campo, "tipo": tipo, "not_null": nn, "pk": pk, "comentario": g(c, "descripcion"), "origen": f"{u}:{nro}",
                                         "origen_tabular": True, "fk": fk or bool(ref), "referencia": ref})
    for ent, campos in ents.items():
        agregar_entidad(inf, ent, campos, campos[0]["origen"], "diccionario")
    if sin_tabla and ents:
        inf["preguntas"].append({"pregunta": f"La hoja {u} no tiene columna de tabla/entidad: ¿«{nombre_base}» es el nombre de la entidad?",
                                 "intento": "busqué una columna Tabla/Entidad/Table/Entity en los encabezados; no hay y se tomó el nombre de la hoja (o del archivo)"})
    return list(ents)


def extraer_catalogo(cuerpo, cl, rel, hoja, nombre_base, inf):
    hs = [norm(h) for h in cl["headers"]]
    ic = next((i for i, h in enumerate(hs) if h in H_CODIGO), 0)
    idc = next((i for i, h in enumerate(hs) if i != ic and (h in H_DESC or h in H_CODIGO)), None)
    u, vals = ubic(rel, hoja), []
    for nro, c in cuerpo:
        cod = c[ic].strip() if ic < len(c) else ""
        ds = c[idc].strip() if idc is not None and idc < len(c) else ""
        if cod or ds: vals.append({"codigo": cod, "descripcion": ds, "origen": f"{u}:{nro}"})
    cat = {"nombre": nombre_base, "archivo": rel, "hoja": hoja, "total": len(vals), "valores": vals[:200], "origen": f"{u}:{cuerpo[0][0]}" if cuerpo else u}
    inf["catalogos"].append(cat)
    return cat


def procesar_tabular(p, rel, inf):
    hojas, err = leer_tabular(p)
    if err:
        inf["no_leidos"].append({"archivo": rel, "razon": err[0], "pedir": err[1]}); return
    if not any(h["filas"] for h in hojas):
        inf["no_leidos"].append({"archivo": rel, "razon": "sin contenido (todas las hojas están vacías)", "pedir": "entregar el archivo con datos o su exportación a .csv"}); return
    inf["leidos"].append(rel)
    stem = pathlib.Path(rel).stem
    for h in hojas:
        hoja, u = h["hoja"], ubic(rel, h["hoja"])
        if not h["filas"]:
            inf["avisos"].append(f"{u}: hoja vacía (se omite)"); continue
        if h["recortado"]:
            inf["avisos"].append(f"{u}: se leyeron solo las primeras {MAX_FILAS} filas; el resto se ignoró")
        cl = clasificar(h["filas"])
        cuerpo = [(n, list(c)) for n, c in h["filas"][cl["enc"] + 1:]]
        enmascarar(cuerpo, cl, rel, hoja, inf["secretos"])
        base = stem if (not hoja or RX_HOJA_GENERICA.match(hoja)) else hoja
        info = {"archivo": rel, "hoja": hoja, "clasificacion": cl["clase"], "confianza": cl["confianza"], "motivo": cl["motivo"],
                "encabezados": [x for x in cl["headers"] if x.strip()], "fila_encabezado": h["filas"][cl["enc"]][0], "filas_datos": len(cuerpo),
                "recortado": h["recortado"], "formato": h["formato"], "entidades": []}
        if cl["clase"] == "catalogo" and cl["confianza"] == "media" and not (RX_NOM_CATALOGO.search(base) or RX_NOM_CATALOGO.search(hoja or "")) \
                and (len([x for x in cl["headers"] if x.strip()]) > 2 or norm(cl["headers"][0]) == "id"):
            inf["preguntas"].append({"pregunta": f"{u} podría ser un catálogo de valores o los datos de una entidad «{base}»: ¿cuál es?",
                                     "intento": "encabezados de código/descripción sin palabra «catálogo/lista/valores» en el nombre del archivo ni de la hoja; se trató como catálogo"})
        if cl["clase"] == "diccionario":
            info["entidades"] = extraer_diccionario(cuerpo, cl, rel, hoja, base, inf)
        elif cl["clase"] == "catalogo":
            extraer_catalogo(cuerpo, cl, rel, hoja, base, inf)
        elif cl["clase"] == "datos":
            campos, vacios = [], []
            for i, hd in enumerate(cl["headers"]):
                if not hd.strip(): continue
                t = tipo_probable([c[i] for _n, c in cuerpo if i < len(c)])
                if not t: vacios.append(hd)
                campos.append({"nombre": hd.strip(), "tipo": t or "texto", "not_null": None, "pk": False, "comentario": "", "inferido": True,
                               "origen": f"{u}:{info['fila_encabezado']}", "origen_tabular": True, "fk": False, "referencia": None})
            agregar_entidad(inf, base, campos, f"{u}:{info['fila_encabezado']}", "datos")
            info["entidades"] = [base]
            if vacios:
                inf["preguntas"].append({"pregunta": f"Los campos {', '.join('«' + v + '»' for v in vacios)} de «{base}» ({u}) no tienen ningún valor de ejemplo: ¿de qué tipo son?",
                                         "intento": f"inferí el tipo (entero, decimal, fecha, texto) de {len(cuerpo)} filas de datos; esas columnas están vacías"})
        else:
            inf["preguntas"].append({"pregunta": f"¿Qué describe {u}? No se pudo clasificar como diccionario, catálogo ni datos de ejemplo.",
                                     "intento": f"revisé los encabezados de las primeras filas ({cl['motivo']}); busqué columnas Tabla/Campo/Tipo, código/descripción y filas de datos"})
        inf["hojas"].append(info)


def resolver_relaciones_tabulares(inf, declaradas):
    ents = inf["entidades"]
    vistas = {(r["origen"].lower(), r["columna"].lower()) for r in inf["relaciones"]}
    for e in ents:
        for c in e["campos"]:
            if not c.get("origen_tabular") or (e["nombre"].lower(), c["nombre"].lower()) in declaradas | vistas: continue
            ref, nm = c.get("referencia"), c["nombre"].lower()
            def pkde(d): return next((x["nombre"] for x in d["campos"] if x.get("pk")), "") or next((x["nombre"] for x in d["campos"] if x["nombre"].lower() == "id"), "")
            if ref:
                dest = [d for d in candidatos_destino(ref["tabla"], ents)]
                if dest:
                    inf["relaciones"].append({"origen": e["nombre"], "columna": c["nombre"], "destino": dest[0]["nombre"], "columna_destino": ref["columna"] or pkde(dest[0]),
                                              "confianza": "alta", "evidencia": f"columna de referencia/FK declarada en {c['origen']}: «{ref['texto']}»"})
                else:
                    inf["preguntas"].append({"pregunta": f"{e['nombre']}.{c['nombre']} referencia «{ref['tabla']}» ({c['origen']}), que no está en las entradas: ¿dónde se define?",
                                             "intento": "busqué una entidad o tabla con ese nombre (y su plural/singular) entre todas las entradas leídas"})
                continue
            base = c["nombre"][:-3] if nm.endswith("_id") and nm != "id" else c["nombre"][3:] if nm.startswith("id_") else None
            if base is None or c.get("pk"):
                if c.get("fk"):
                    inf["preguntas"].append({"pregunta": f"{e['nombre']}.{c['nombre']} está marcado como clave foránea ({c['origen']}) pero no dice a qué apunta: ¿a qué entidad?",
                                             "intento": "busqué una columna de referencia con destino y un nombre terminado en _id o que empiece por id_; no hay"})
                continue
            dest = [d for d in candidatos_destino(base, ents) if d is not e]
            if dest:
                nota = "marcada como FK en la hoja; destino inferido por el nombre" if c.get("fk") else "inferida por el nombre"
                inf["relaciones"].append({"origen": e["nombre"], "columna": c["nombre"], "destino": dest[0]["nombre"], "columna_destino": pkde(dest[0]),
                                          "confianza": "media", "evidencia": f"{nota} «{c['nombre']}» ({c['origen']}) y la entidad «{dest[0]['nombre']}»; sin referencia declarada"})
            else:
                inf["preguntas"].append({"pregunta": f"¿A qué entidad apunta {e['nombre']}.{c['nombre']}? ({c['origen']})",
                                         "intento": f"busqué una entidad llamada «{base}» (o su plural) y una columna de referencia declarada; no hay ninguna"})


# ───────────────────────── recorrido e informe ─────────────────────────
def razon_no_leido(p):
    ext = p.suffix.lower()
    if ext in NO_LEIBLES:
        return f"{NO_LEIBLES[ext]}: no se lee sin librerías externas", "exportar la hoja a .xlsx o .csv (UTF-8)"
    return f"formato no soportado ({ext or 'sin extensión'})", "exportar o transcribir a .md (texto), .sql (esquema), .csv o .xlsx (tablas)"


def candidatos_destino(base, tablas):
    b = base.lower()
    pos = {b, b + "s", b + "es", b[:-1] + "ies" if b.endswith("y") else b, b.rstrip("s"), "tbl_" + b, "tb_" + b}
    return [t for t in tablas if t["nombre"].lower() in pos]


def analizar(carpeta):
    carpeta = pathlib.Path(carpeta)
    inf = {"carpeta": str(carpeta), "leidos": [], "no_leidos": [], "markdown": [], "tablas": [], "entidades": [], "relaciones": [],
           "requisitos": [], "preguntas_abiertas": [], "motor": None, "preguntas": [], "hojas": [], "catalogos": [], "secretos": [], "avisos": []}
    marcas_total, md_motores, fks_extra, indices = {"mysql": {}, "postgresql": {}}, {}, [], []
    archivos = []
    for p in sorted(carpeta.rglob("*")):
        rel = p.relative_to(carpeta)
        if any(x in EXCLUIR_DIRS for x in rel.parts[:-1]) or p.is_dir(): continue
        archivos.append((p, rel.as_posix()))
    for p, rel in archivos:
        ext = p.suffix.lower()
        if p.is_symlink():
            inf["no_leidos"].append({"archivo": rel, "razon": "enlace simbólico (no se sigue)", "pedir": "entregar el archivo real dentro de la carpeta"}); continue
        if ext in TABULARES:
            try:
                if p.stat().st_size > MAX_BYTES:
                    inf["no_leidos"].append({"archivo": rel, "razon": f"supera {MAX_BYTES} bytes", "pedir": "dividir el archivo o exportar solo las hojas relevantes"}); continue
            except OSError as e:
                inf["no_leidos"].append({"archivo": rel, "razon": f"no se pudo leer ({e.__class__.__name__})", "pedir": "revisar permisos"}); continue
            procesar_tabular(p, rel, inf); continue
        if ext not in (".md", ".sql"):
            if rel.split("/")[-1].startswith("."): continue
            rz, pd = razon_no_leido(p)
            inf["no_leidos"].append({"archivo": rel, "razon": rz, "pedir": pd}); continue
        try:
            if p.stat().st_size > MAX_BYTES:
                inf["no_leidos"].append({"archivo": rel, "razon": f"supera {MAX_BYTES} bytes", "pedir": "dividir el archivo"}); continue
            texto = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            inf["no_leidos"].append({"archivo": rel, "razon": f"no se pudo leer ({e.__class__.__name__})", "pedir": "revisar permisos"}); continue
        inf["leidos"].append(rel)
        if ext == ".md":
            md = leer_md(texto, rel)
            inf["markdown"].append({"archivo": rel, "titulo": md["titulo"], "secciones": md["secciones"], "tablas": md["tablas"], "listas": md["listas"]})
            inf["requisitos"] += md["requisitos"]; inf["preguntas_abiertas"] += md["abiertas"]
            for e in md["entidades"]:
                inf["entidades"].append({"nombre": e["nombre"], "campos": e["campos"], "origenes": [e["origen"]], "fuente": "md"})
            for k, v in md["motores_mencionados"].items(): md_motores.setdefault(k, v)
        else:
            tablas, idx, fx, marcas = leer_sql(texto, rel)
            for t in tablas: inf["tablas"].append(t)
            indices += idx; fks_extra += fx
            for mo in marcas:
                for k, ln in marcas[mo].items(): marcas_total[mo].setdefault(k, f"{rel}:{ln}")
            if not tablas: inf["preguntas"].append({"pregunta": f"¿{rel} define el esquema por otro medio? No se encontró ningún CREATE TABLE.", "intento": "búsqueda de CREATE TABLE con paréntesis balanceados, sin comentarios"})
    if not inf["leidos"]:
        return inf
    por_nombre = {t["nombre"].lower(): t for t in inf["tablas"]}
    for ix in indices:
        t = por_nombre.get(ix["tabla"].lower())
        if t: t["indices"].append({k: ix[k] for k in ("nombre", "columnas", "unico", "linea")})
    for fx in fks_extra:
        t = por_nombre.get(fx["tabla_origen"].lower())
        if t: t["fks"].append({k: fx[k] for k in ("columna", "tabla", "columna_destino", "linea")})
    # entidades desde SQL (fusiona con las de md por nombre)
    ents = {}
    for e in inf["entidades"]:
        ents[e["nombre"].lower()] = e
    for t in inf["tablas"]:
        clave = t["nombre"].lower()
        campos = [{"nombre": c["nombre"], "tipo": c["tipo"], "not_null": c["not_null"], "pk": c["pk"], "comentario": c["comentario"], "origen": f'{t["archivo"]}:{c["origen"]}'} for c in t["columnas"]]
        o = f'{t["archivo"]}:{t["linea"]}'
        if clave in ents:
            ents[clave]["origenes"].append(o); ents[clave]["campos"] = ents[clave]["campos"] + campos; ents[clave]["fuente"] += "+sql"
        else:
            ents[clave] = {"nombre": t["nombre"], "campos": campos, "origenes": [o], "fuente": "sql"}
    inf["entidades"] = list(ents.values())
    # relaciones
    declaradas = set()
    for t in inf["tablas"]:
        for fk in t["fks"]:
            declaradas.add((t["nombre"].lower(), fk["columna"].lower()))
            ok = fk["tabla"].lower() in por_nombre
            inf["relaciones"].append({"origen": t["nombre"], "columna": fk["columna"], "destino": fk["tabla"], "columna_destino": fk["columna_destino"],
                                      "confianza": "alta", "evidencia": f'FOREIGN KEY/REFERENCES declarada en {t["archivo"]}:{fk["linea"]}'})
            if not ok:
                inf["preguntas"].append({"pregunta": f'La clave foránea {t["nombre"]}.{fk["columna"]} apunta a «{fk["tabla"]}», que no está en las entradas: ¿dónde se define?',
                                         "intento": "búsqueda de CREATE TABLE con ese nombre en todos los .sql leídos"})
    for t in inf["tablas"]:
        if not t["pk"]:
            inf["preguntas"].append({"pregunta": f'¿Cuál es la clave primaria de {t["nombre"]}? ({t["archivo"]}:{t["linea"]})', "intento": "búsqueda de PRIMARY KEY (columna o restricción) y de columnas SERIAL/AUTO_INCREMENT"})
        for c in t["columnas"]:
            if c["nombre"].lower().endswith("_id") and c["nombre"].lower() != "id" and (t["nombre"].lower(), c["nombre"].lower()) not in declaradas and not (c["pk"] and len(t["pk"]) == 1):
                base = c["nombre"][:-3]
                dest = [d for d in candidatos_destino(base, inf["tablas"]) if d["nombre"] != t["nombre"] or True]
                if dest:
                    d = dest[0]
                    inf["relaciones"].append({"origen": t["nombre"], "columna": c["nombre"], "destino": d["nombre"], "columna_destino": (d["pk"] or [""])[0],
                                              "confianza": "media", "evidencia": f'inferida por el nombre «{c["nombre"]}» ({t["archivo"]}:{c["origen"]}) y la tabla «{d["nombre"]}»; sin FOREIGN KEY declarada'})
                else:
                    inf["preguntas"].append({"pregunta": f'¿A qué tabla apunta {t["nombre"]}.{c["nombre"]}? ({t["archivo"]}:{c["origen"]})',
                                             "intento": f'busqué una tabla llamada «{base}» (o su plural) y una FOREIGN KEY declarada; no hay ninguna'})
    resolver_relaciones_tabulares(inf, declaradas)
    # entidades de md sin esquema
    for e in inf["entidades"]:
        if e["fuente"] == "md":
            inf["preguntas"].append({"pregunta": f'La entidad «{e["nombre"]}» ({e["origenes"][0]}) está en la documentación pero no tiene tabla en los .sql: ¿es nueva o se llama distinto?',
                                     "intento": "comparación por nombre (sin distinguir mayúsculas) contra los CREATE TABLE leídos" if inf["tablas"] else "no hay ningún .sql en las entradas"})
            if not e["campos"]:
                inf["preguntas"].append({"pregunta": f'¿Qué campos tiene «{e["nombre"]}»?', "intento": "busqué una tabla Campo/Atributo/Columna bajo su encabezado; no hay"})
    # motor propuesto
    sm, sp = len(marcas_total["mysql"]), len(marcas_total["postgresql"])
    if sm or sp:
        if sm == sp:
            inf["preguntas"].append({"pregunta": "¿Qué motor de base de datos se usará (MySQL o PostgreSQL)? El SQL aportado tiene indicios de ambos por igual.",
                                     "intento": f"marcas MySQL: {sorted(marcas_total['mysql'])}; marcas PostgreSQL: {sorted(marcas_total['postgresql'])}"})
        else:
            g, o = ("mysql", "postgresql") if sm > sp else ("postgresql", "mysql")
            nom = {"mysql": "MySQL", "postgresql": "PostgreSQL"}
            ev = [f"{k} ({v})" for k, v in marcas_total[g].items()]
            inf["motor"] = {"propuesto": nom[g], "confianza": "alta" if not marcas_total[o] else "media", "evidencia": ev,
                            "alternativa": nom[o] + (f" (indicios contrarios: {', '.join(marcas_total[o])})" if marcas_total[o] else " (sin indicios; solo si se decide migrar de motor)")}
    elif md_motores:
        k, v = next(iter(md_motores.items()))
        inf["motor"] = {"propuesto": k, "confianza": "baja", "evidencia": [f"mencionado en {v}" + (f"; también: {', '.join(x for x in md_motores if x != k)}" if len(md_motores) > 1 else "")],
                        "alternativa": next((x for x in md_motores if x != k), "ninguna indicada")}
    else:
        inf["preguntas"].append({"pregunta": "¿Qué motor de base de datos se usará?", "intento": "busqué marcas de dialecto (backticks, ENGINE=, SERIAL, jsonb, uuid...) en los .sql y menciones de motores en los .md; no hay ninguna"})
    if not inf["requisitos"]:
        inf["preguntas"].append({"pregunta": "¿Dónde están los requisitos funcionales?", "intento": "busqué líneas con «debe», «deberá» o «el sistema» en los .md leídos; no hay ninguna"})
    if inf["no_leidos"]:
        inf["preguntas"].append({"pregunta": f'Hay {len(inf["no_leidos"])} archivo(s) no leídos ({", ".join(x["archivo"] for x in inf["no_leidos"][:5])}): ¿contienen información de partida relevante?',
                                 "intento": "se leen .md, .sql, .csv, .tsv y .xlsx; el resto (o lo que falló al abrirse) se listó con la razón y qué pedir"})
    return inf


def a_md(inf):
    L = [f"# Informe de entradas · {inf['carpeta']}", ""]
    L += ["## Archivos", f"- Leídos ({len(inf['leidos'])}): " + (", ".join(inf["leidos"]) or "ninguno")]
    if inf["no_leidos"]:
        L.append(f"- No leídos ({len(inf['no_leidos'])}):")
        L += [f"  - {x['archivo']}: {x['razon']}. Qué pedir: {x['pedir']}" for x in inf["no_leidos"]]
    if inf["avisos"]:
        L += ["", "## Avisos"] + [f"- {x}" for x in inf["avisos"]]
    if inf["hojas"]:
        L += ["", f"## Hojas de cálculo ({len(inf['hojas'])})"]
        for h in inf["hojas"]:
            L.append(f"- {ubic(h['archivo'], h['hoja'])}: **{h['clasificacion']}** (confianza {h['confianza']}) · {h['formato']} · encabezado en la fila {h['fila_encabezado']} · {h['filas_datos']} filas · {h['motivo']}")
    if inf["catalogos"]:
        L += ["", f"## Catálogos ({len(inf['catalogos'])})"]
        for c in inf["catalogos"]:
            L.append(f"- **{c['nombre']}** — {c['total']} valores · origen: {c['origen']}")
            L += [f"  - {v['codigo']} = {v['descripcion']} ({v['origen']})" for v in c["valores"][:20]]
            if c["total"] > 20: L.append(f"  - … y {c['total'] - 20} más (ver --json)")
    if inf["secretos"]:
        L += ["", f"## Secretos enmascarados ({len(inf['secretos'])})", "- Los valores no se muestran en ninguna salida; solo dónde están."]
        L += [f"- {ubic(x['archivo'], x['hoja'])}!{x['celda']}: {x['motivo']}" for x in inf["secretos"]]
    for m in inf["markdown"]:
        L += ["", f"## Markdown · {m['archivo']}", f"- Título: {m['titulo'] or '(sin título)'}", f"- Secciones: {len(m['secciones'])} · tablas: {len(m['tablas'])} · listas: {m['listas']}"]
        L += [f"  - {'#' * s['nivel']} {s['titulo']} (línea {s['linea']})" for s in m["secciones"]]
    L += ["", f"## Entidades y campos ({len(inf['entidades'])})"]
    for e in inf["entidades"]:
        L.append(f"- **{e['nombre']}** [{e['fuente']}] — origen: {', '.join(e['origenes'])}")
        for c in e["campos"]:
            marcas = " ".join(x for x, v in (("PK", c.get("pk")), ("NOT NULL", c.get("not_null"))) if v)
            L.append(f"  - {c['nombre']}" + (f" `{c['tipo']}`" + (" (inferido)" if c.get("inferido") else "") if c.get("tipo") else "") + (f" {marcas}" if marcas else "") + (f" — «{c['comentario']}»" if c.get("comentario") else "") + f" ({c['origen']})")
    for t in inf["tablas"]:
        if t["indices"]:
            L.append(f"- Índices de {t['nombre']}: " + "; ".join(f"{i['nombre'] or '(sin nombre)'}({', '.join(i['columnas'])}){' único' if i['unico'] else ''} línea {i['linea']}" for i in t["indices"]))
    L += ["", f"## Relaciones ({len(inf['relaciones'])})"]
    L += [f"- {r['origen']}.{r['columna']} -> {r['destino']}.{r['columna_destino'] or '?'} · confianza {r['confianza']} · {r['evidencia']}" for r in inf["relaciones"]] or ["- ninguna"]
    L += ["", "## Motor de base de datos propuesto"]
    mo = inf["motor"]
    L += [f"- {mo['propuesto']} (confianza {mo['confianza']}) · evidencia: {'; '.join(mo['evidencia'])} · alternativa: {mo['alternativa']}"] if mo else ["- sin propuesta (ver preguntas)"]
    L += ["", f"## Requisitos ({len(inf['requisitos'])})"] + [f"- {r['texto']} ({r['origen']})" for r in inf["requisitos"]]
    L += ["", f"## Preguntas abiertas del origen ({len(inf['preguntas_abiertas'])})"] + [f"- {r['texto']} ({r['origen']})" for r in inf["preguntas_abiertas"]]
    L += ["", f"## Preguntas para quien aporta las entradas ({len(inf['preguntas'])})"]
    for q in inf["preguntas"]:
        L += [f"- {q['pregunta']}", f"  - Se intentó: {q['intento']}"]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lee .md, .sql, .csv, .tsv y .xlsx de una carpeta y resume entidades, relaciones y motor (solo lectura).")
    ap.add_argument("carpeta"); g = ap.add_mutually_exclusive_group()
    g.add_argument("--json", action="store_true"); g.add_argument("--md", action="store_true")
    ap.add_argument("--salida")
    a = ap.parse_args(argv)
    c = pathlib.Path(a.carpeta)
    if not c.is_dir():
        print(f"ERROR: {c} no es una carpeta.", file=sys.stderr); return 2
    if a.salida:
        s = pathlib.Path(a.salida).resolve()
        if s == c.resolve() or c.resolve() in s.parents:
            print("ERROR: --salida no puede estar dentro de la carpeta de entradas (se leen sin modificar).", file=sys.stderr); return 2
    inf = analizar(c)
    if not inf["leidos"]:
        print(f"ERROR: {c} no tiene nada legible (se leen .md, .sql, .csv, .tsv y .xlsx)." + (" No leídos: " + "; ".join(f"{x['archivo']} ({x['razon']})" for x in inf["no_leidos"]) if inf["no_leidos"] else " La carpeta está vacía."), file=sys.stderr)
        return 2
    out = json.dumps(inf, ensure_ascii=False, indent=2) if a.json else a_md(inf)
    if a.salida: pathlib.Path(a.salida).write_text(out, encoding="utf-8")
    else: print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
