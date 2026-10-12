#!/usr/bin/env python3
"""Aprendizaje automático del meta harness: lee las fuentes registradas, separa lo general de lo del negocio y deja una cola de aportes.

<!-- tipo: herramienta · capa: 4 -->

Qué resuelve: lo que se aprende en un proyecto (un ERP central, la instancia de una empresa) no debe repetirse en el siguiente. Esta
herramienta mira esas fuentes SIN modificarlas, parte cada documento en secciones, clasifica cada sección con la misma regla de
`harness-aportar.py` (general / mixta / de negocio) y deja las generales, ya anonimizadas, en una cola local para revisión.

Garantías:
  - Nunca escribe en una fuente ni en el árbol del harness al escanear; la cola vive FUERA del repositorio
    (por defecto ~/.local/share/meta-harness/aportes, o HARNESS_COLA, o `cola` del registro).
  - Nunca sube nada (ni commit ni push). Promover copia un documento al árbol del harness solo con --aplicar, tras el gate de
    extracción, la lista de términos prohibidos y el escaneo de publicación; el commit lo hace una persona.
  - Idempotente: un ledger por sección (sha256) evita reprocesar lo que no cambió y respeta lo descartado.
  - Falla abierta en modo --silencioso: pensada para colgarse de un hook de fin de sesión sin romper nada.

Registro de fuentes (archivo del usuario, no se versiona): ~/.config/meta-harness/fuentes.toml o HARNESS_FUENTES.

Uso:
  harness-aprender.py fuentes listar
  harness-aprender.py fuentes agregar <nombre> <ruta> [--tipo erp|instancia|carpeta] [--incluir GLOB ...] [--excluir GLOB ...]
  harness-aprender.py fuentes quitar <nombre>
  harness-aprender.py escanear [--fuente NOMBRE] [--max-frecuencia SEGUNDOS] [--silencioso] [--json]
  harness-aprender.py listar [--todo]            la cola (pendientes; con --todo, también lo ya resuelto)
  harness-aprender.py ver <id>                   muestra el documento de un aporte pendiente
  harness-aprender.py descartar <id> --motivo T
  harness-aprender.py promover <id> --tipo estandar|metodo|perfil|adaptador|herramienta [--stack S] [--adaptador A] [--aplicar]
Salida: 0 bien · 1 problema · 2 uso incorrecto o algo falta.
"""
import argparse, datetime, hashlib, importlib.util, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time, tomllib

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent


def _cargar(nombre, archivo):
    spec = importlib.util.spec_from_file_location(nombre, AQUI / archivo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ext = _cargar("harness_extraer", "harness-extraer.py")
apo = _cargar("harness_aportar", "harness-aportar.py")

TIPOS_FUENTE = ("erp", "instancia", "carpeta")
INCLUIR_POR_TIPO = {
    # Solo lo que es método o estándar del producto; la descripción de cada módulo es del ERP, no del harness.
    # Para otro conjunto: `fuentes agregar … --incluir GLOB`.
    "erp": ["docs/ESTANDAR*.md", "docs/CRITERIOS.md", "docs/DECISIONES.md", "docs/ESTRUCTURA-DE-MODULO.md", "docs/FLUJO-TRABAJO.md"],
    "instancia": ["references/**/*.md", "docs/**/*.md", "metodo/**/*.md", "convenciones/**/*.md",
                  "_kb/memory-backup/feedback_*.md"],  # las reglas que la persona fue dictando
    "carpeta": [],
}
IGNORAR = {"node_modules", ".git", "dist", "build", "__pycache__", ".venv", "venv", "coverage"}
MIN_LINEAS_CONTENIDO = 4
MIN_MARCADORES_NORMATIVOS = 2
RX_NORMATIVO = re.compile(r"\b(?:nunca|siempre|jam[aá]s|debe|deben|obligatori[oa]s?|prohib\w+|evit[ae]\w*|regla|reglas|criterio|"
                          r"exige|exigid[oa]|hay que|se debe|no se)\b", re.I)
RX_H2 = re.compile(r"^##\s+(.+?)\s*$")
RX_FRONT = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)
RX_ETIQUETA = re.compile(r"^\s*<!--\s*(tipo|revisado)\s*:.*-->\s*$")
RX_FICHA = re.compile(r"<!--\s*ficha:auto\s*-->.*?<!--\s*/ficha:auto\s*-->\n?", re.S)
ETIQUETA_PROVISIONAL = "<!-- tipo: estandar · capa: 2 -->"
FRESCURA = "<!-- revisado: {fecha} · vence: 90d · fuente: aporte de una instancia, revisado por una persona antes de promoverse -->"
ESTADOS_CERRADOS = {"descartada", "promovida"}


class Fallo(Exception):
    def __init__(self, msg, codigo=2):
        super().__init__(msg)
        self.codigo = codigo


# ------------------------------------------------------------------ registro de fuentes
def ruta_registro():
    return pathlib.Path(os.environ.get("HARNESS_FUENTES") or "~/.config/meta-harness/fuentes.toml").expanduser()


def leer_registro():
    f = ruta_registro()
    if not f.is_file():
        return {"cola": None, "fuentes": []}
    try:
        d = tomllib.loads(f.read_text(encoding="utf8"))
    except tomllib.TOMLDecodeError as e:
        raise Fallo(f"El registro de fuentes {f} no es TOML válido: {e}", 1)
    return {"cola": d.get("cola"), "fuentes": list(d.get("fuente", []))}


def escribir_registro(reg):
    f = ruta_registro()
    f.parent.mkdir(parents=True, exist_ok=True)
    out = ["# Fuentes que el harness lee para aprender (solo lectura). Archivo del usuario: no se versiona.", ""]
    if reg.get("cola"):
        out += [f"cola = {json.dumps(reg['cola'], ensure_ascii=False)}", ""]
    for x in reg["fuentes"]:
        out += ["[[fuente]]",
                f"nombre = {json.dumps(x['nombre'], ensure_ascii=False)}",
                f"tipo = {json.dumps(x['tipo'])}",
                f"ruta = {json.dumps(x['ruta'], ensure_ascii=False)}",
                f"incluir = {json.dumps(x.get('incluir', []), ensure_ascii=False)}",
                f"excluir = {json.dumps(x.get('excluir', []), ensure_ascii=False)}", ""]
    f.write_text("\n".join(out), encoding="utf8")


def erp_base_registrado():
    """Ruta de la fuente de tipo `erp` si está registrada y existe; si no, None. Lo usa `harness erp` por defecto."""
    try:
        for x in leer_registro()["fuentes"]:
            if x.get("tipo") == "erp" and pathlib.Path(x["ruta"]).expanduser().is_dir():
                return str(pathlib.Path(x["ruta"]).expanduser())
    except Fallo:
        return None
    return None


def ruta_cola(reg):
    base = os.environ.get("HARNESS_COLA") or reg.get("cola") or "~/.local/share/meta-harness/aportes"
    return pathlib.Path(base).expanduser().resolve()


def cmd_fuentes(a):
    reg = leer_registro()
    if a.accion == "listar":
        print(f"Registro: {ruta_registro()}" + ("" if ruta_registro().is_file() else "  (no existe todavía)"))
        print(f"Cola: {ruta_cola(reg)}")
        if not reg["fuentes"]:
            print("Sin fuentes. Registra una: harness aprender fuentes agregar erp-base <ruta> --tipo erp")
        for x in reg["fuentes"]:
            ok = "existe" if pathlib.Path(x["ruta"]).expanduser().is_dir() else "NO EXISTE"
            print(f"  - {x['nombre']} [{x['tipo']}] {x['ruta']} ({ok}); incluye {', '.join(x.get('incluir', [])) or '—'}")
        return 0
    if a.accion == "agregar":
        if not a.nombre or not a.ruta:
            raise Fallo("Uso: fuentes agregar <nombre> <ruta> [--tipo erp|instancia|carpeta]")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", a.nombre):
            raise Fallo("El nombre solo admite letras, números, punto, guion y guion bajo.")
        ruta = pathlib.Path(a.ruta).expanduser().resolve()
        if not ruta.is_dir():
            raise Fallo(f"No existe la carpeta {ruta}.")
        incluir = a.incluir or INCLUIR_POR_TIPO[a.tipo]
        if not incluir:
            raise Fallo("Una fuente de tipo `carpeta` necesita --incluir (por ejemplo docs/*.md).")
        reg["fuentes"] = [x for x in reg["fuentes"] if x["nombre"] != a.nombre]
        reg["fuentes"].append({"nombre": a.nombre, "tipo": a.tipo, "ruta": str(ruta), "incluir": incluir, "excluir": a.excluir or []})
        escribir_registro(reg)
        print(f"Fuente «{a.nombre}» registrada ({a.tipo}). Solo se lee; nunca se escribe en ella.")
        if a.tipo == "instancia" and not (ruta / "dominio.txt").is_file():
            print("  Aviso: la fuente no tiene dominio.txt; sin los términos del negocio la clasificación es débil y "
                  "lo que parezca técnico exige más revisión humana.")
        return 0
    if a.accion == "quitar":
        antes = len(reg["fuentes"])
        reg["fuentes"] = [x for x in reg["fuentes"] if x["nombre"] != a.nombre]
        if len(reg["fuentes"]) == antes:
            raise Fallo(f"No hay una fuente llamada «{a.nombre}».", 1)
        escribir_registro(reg)
        print(f"Fuente «{a.nombre}» quitada del registro (no se borra nada de la carpeta).")
        return 0
    raise Fallo("Acción de fuentes desconocida.")


# ------------------------------------------------------------------ unidades
def archivos_de(fuente):
    raiz = pathlib.Path(fuente["ruta"]).expanduser().resolve()
    vistos, res = set(), []
    for patron in fuente.get("incluir", []):
        for p in sorted(raiz.glob(patron)):
            if not p.is_file() or p.suffix.lower() != ".md":
                continue
            rel = p.relative_to(raiz)
            if any(parte in IGNORAR for parte in rel.parts):
                continue
            if any(rel.match(x) or rel.as_posix() == x for x in fuente.get("excluir", [])):
                continue
            if rel not in vistos:
                vistos.add(rel)
                res.append((rel, p))
    return raiz, res


def quitar_frontmatter(texto):
    """Quita el encabezado YAML de una memoria; devuelve (texto, título legible o None)."""
    m = RX_FRONT.match(texto)
    if not m:
        return texto, None
    nombre = re.search(r"^name:\s*(.+)$", m.group(1), re.M)
    titulo = re.sub(r"[-_]+", " ", nombre.group(1).strip().strip("\"'")) if nombre else None
    return texto[m.end():], titulo


def partir_unidades(texto, titulo_intro="introducción"):
    """Secciones `##` (fuera de cercos de código); lo anterior al primer `##` es la introducción."""
    lineas = texto.splitlines()
    cortes, cerco = [(0, titulo_intro)], False
    for i, l in enumerate(lineas):
        if l.lstrip().startswith("```"):
            cerco = not cerco
            continue
        if not cerco:
            m = RX_H2.match(l)
            if m:
                cortes.append((i, m.group(1)))
    out = []
    for k, (ini, titulo) in enumerate(cortes):
        fin = cortes[k + 1][0] if k + 1 < len(cortes) else len(lineas)
        out.append((titulo, "\n".join(lineas[ini:fin]).strip("\n") + "\n"))
    return out


def documento_provisional(titulo, cuerpo):
    cuerpo = RX_FICHA.sub("", cuerpo)
    lineas = [l for l in cuerpo.splitlines() if not RX_ETIQUETA.match(l)]
    if lineas and RX_H2.match(lineas[0]):
        lineas = lineas[1:]
    if lineas and lineas[0].startswith("# "):
        titulo, lineas = lineas[0][2:].strip(), lineas[1:]
    limpio = [l for l in lineas]
    while limpio and not limpio[0].strip():
        limpio.pop(0)
    return f"{ETIQUETA_PROVISIONAL}\n# {titulo}\n\n" + "\n".join(limpio).rstrip("\n") + "\n"


def lineas_de_contenido(texto):
    n, cerco = 0, False
    for l in texto.splitlines():
        s = l.strip()
        if s.startswith("```"):
            cerco = not cerco
            continue
        if not s or s.startswith("#") or s.startswith("<!--"):
            continue
        n += 1
    return n


# ------------------------------------------------------------------ cola y ledger
def sha(txt):
    return hashlib.sha256(txt.encode("utf8")).hexdigest()


def ahora():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


class Cola:
    def __init__(self, base):
        self.base = pathlib.Path(base)
        self.pendientes = self.base / "pendientes"
        self.ledger_ruta = self.base / "ledger.json"
        self.ledger = {}
        if self.ledger_ruta.is_file():
            try:
                self.ledger = json.loads(self.ledger_ruta.read_text(encoding="utf8"))
            except json.JSONDecodeError:
                raise Fallo(f"El ledger {self.ledger_ruta} está dañado: no se toca. Revísalo o bórralo a propósito.", 1)

    def guardar(self):
        self.base.mkdir(parents=True, exist_ok=True)
        tmp = self.ledger_ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf8")
        os.replace(tmp, self.ledger_ruta)

    def por_slug(self, slug):
        for uid, r in self.ledger.items():
            if r.get("paquete") == slug:
                return uid, r
        return None, None


def adquirir_cierre(base):
    base.mkdir(parents=True, exist_ok=True)
    cierre = base / ".escaneo.lock"
    try:
        fd = os.open(cierre, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return cierre
    except FileExistsError:
        if time.time() - cierre.stat().st_mtime > 600:
            cierre.unlink(missing_ok=True)
            return adquirir_cierre(base)
        return None


def archivos_prohibidos(raiz):
    """Listas de términos que no pueden salir: la del repositorio (.prohibidos.txt), la de la variable HARNESS_PROHIBIDOS y,
    si la variable no está definida, la del usuario (~/.config/meta-harness/prohibidos.txt). Todas son locales y no se versionan."""
    rutas = [pathlib.Path(raiz) / ".prohibidos.txt"]
    env = os.environ.get("HARNESS_PROHIBIDOS")
    rutas.append(pathlib.Path(env).expanduser() if env else pathlib.Path("~/.config/meta-harness/prohibidos.txt").expanduser())
    return [r for r in rutas if r.is_file()]


def lista_prohibidos(raiz):
    res = []
    for f in archivos_prohibidos(raiz):
        res += [t for t in ext.leer_lista(f) if t not in res]
    return res


def escanear_fuente(fuente, cola, prohibidos, resumen):
    raiz, archivos = archivos_de(fuente)
    ctx = apo.Contexto(raiz)
    if fuente["tipo"] == "instancia" and not ctx.dominio:
        resumen["avisos"].append(f"{fuente['nombre']}: sin dominio.txt (clasificación débil)")
    for rel, p in archivos:
        texto = p.read_text(encoding="utf8", errors="ignore")
        texto, nombre_memoria = quitar_frontmatter(texto)
        for titulo, cuerpo in partir_unidades(texto, nombre_memoria or "introducción"):
            uid = f"{fuente['nombre']}:{rel.as_posix()}#{titulo}"
            resumen["unidades"] += 1
            if lineas_de_contenido(cuerpo) < MIN_LINEAS_CONTENIDO:
                resumen["cortas"] += 1
                continue
            h = sha(cuerpo)
            previo = cola.ledger.get(uid)
            if previo and previo.get("sha") == h:
                resumen["sin_cambio"] += 1
                continue
            if previo and previo.get("paquete") and previo.get("estado") == "pendiente":
                shutil.rmtree(cola.pendientes / previo["paquete"], ignore_errors=True)
            doc = documento_provisional(titulo, cuerpo)
            fichas = apo.analizar(doc.splitlines(), ctx)
            veredicto, razon, _ = apo.veredicto(fichas)
            reg = {"sha": h, "fecha": ahora(), "veredicto": veredicto, "estado": "", "paquete": None, "motivo": razon}
            if veredicto == "de negocio":
                reg["estado"] = "negocio"
                resumen["negocio"] += 1
            elif veredicto == "mixta":
                reg["estado"] = "mixta"
                resumen["mixta"] += 1
            elif len(RX_NORMATIVO.findall(doc)) < MIN_MARCADORES_NORMATIVOS:
                # Es general pero describe, no prescribe: un estándar dice qué se debe o no se debe hacer.
                reg["estado"], reg["motivo"] = "descriptiva", "describe cómo es algo; no fija una regla"
                resumen["descriptivas"] += 1
            else:
                low = doc.lower()
                hit = next((t for t in prohibidos if t.lower() in low), None)
                if hit:
                    reg["estado"], reg["motivo"] = "bloqueada", "contiene un término de la lista de prohibidos"
                    resumen["bloqueadas"] += 1
                else:
                    cuenta = {}
                    nuevo = apo.anonimizar(doc, ctx, cuenta)
                    slug = apo.slug_de(nuevo, ctx)
                    if any(t.lower() in nuevo.lower() for t in prohibidos):
                        reg["estado"], reg["motivo"] = "bloqueada", "tras anonimizar sigue habiendo un término prohibido"
                        resumen["bloqueadas"] += 1
                    else:
                        ya = cola.pendientes / slug
                        if ya.exists():
                            shutil.rmtree(ya, ignore_errors=True)
                        ok, msgs = apo.armar_paquete(uid, doc, ctx, cola.pendientes, razon, veredicto, fichas)
                        if ok:
                            nota = ya / "ORIGEN.md"
                            if nota.is_file():
                                nota.write_text(nota.read_text(encoding="utf8") +
                                                f"- Tipo de fuente: {fuente['tipo']}. La etiqueta `tipo/capa` es PROVISIONAL: se fija al promover.\n",
                                                encoding="utf8")
                            reg["estado"], reg["paquete"] = "pendiente", slug
                            resumen["nuevos"].append(slug)
                        else:
                            reg["estado"], reg["motivo"] = "bloqueada", "; ".join(msgs)[:300]
                            resumen["bloqueadas"] += 1
            cola.ledger[uid] = reg


def cmd_escanear(a):
    reg = leer_registro()
    fuentes = [x for x in reg["fuentes"] if not a.fuente or x["nombre"] == a.fuente]
    if a.fuente and not fuentes:
        raise Fallo(f"No hay una fuente llamada «{a.fuente}».", 1)
    if not fuentes:
        if not a.silencioso:
            print("No hay fuentes registradas: nada que escanear. `harness aprender fuentes agregar <nombre> <ruta> --tipo erp`")
        return 0
    cola_dir = ruta_cola(reg)
    for x in fuentes:
        raiz = pathlib.Path(x["ruta"]).expanduser().resolve()
        if cola_dir == raiz or raiz in cola_dir.parents:
            raise Fallo(f"La cola ({cola_dir}) no puede estar dentro de la fuente «{x['nombre']}»: las fuentes no se modifican.", 2)
    marca = cola_dir / "ultimo-escaneo"
    if a.max_frecuencia and marca.is_file() and time.time() - marca.stat().st_mtime < a.max_frecuencia:
        if not a.silencioso:
            print("Escaneo reciente: se omite (--max-frecuencia).")
        return 0
    cierre = adquirir_cierre(cola_dir)
    if cierre is None:
        if not a.silencioso:
            print("Ya hay un escaneo en curso: se omite.")
        return 0
    try:
        cola = Cola(cola_dir)
        resumen = {"unidades": 0, "cortas": 0, "sin_cambio": 0, "negocio": 0, "mixta": 0, "bloqueadas": 0, "descriptivas": 0,
                   "nuevos": [], "avisos": [], "fuentes": [x["nombre"] for x in fuentes]}
        prohibidos = lista_prohibidos(RAIZ)
        for x in fuentes:
            if not pathlib.Path(x["ruta"]).expanduser().is_dir():
                resumen["avisos"].append(f"{x['nombre']}: la carpeta no existe, se omite")
                continue
            escanear_fuente(x, cola, prohibidos, resumen)
        cola.guardar()
        escribir_informe(cola, resumen)
        marca.write_text(ahora() + "\n", encoding="utf8")
    finally:
        cierre.unlink(missing_ok=True)
    if a.json:
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
    elif a.silencioso:
        if resumen["nuevos"]:
            print(f"harness aprender: {len(resumen['nuevos'])} aporte(s) nuevo(s) en la cola ({cola_dir}). `harness aprender listar`")
    else:
        print(f"Fuentes: {', '.join(resumen['fuentes'])} · secciones vistas: {resumen['unidades']} "
              f"(cortas {resumen['cortas']}, sin cambio {resumen['sin_cambio']})")
        print(f"Nuevos aportes generales: {len(resumen['nuevos'])} · se quedan por ser de negocio: {resumen['negocio']} · "
              f"mixtos: {resumen['mixta']} · descriptivos: {resumen['descriptivas']} · bloqueados: {resumen['bloqueadas']}")
        for s in resumen["nuevos"]:
            print(f"  + {s}")
        for av in resumen["avisos"]:
            print(f"  ! {av}")
        print(f"Cola: {cola_dir}   (informe: INFORME.md)")
    return 0


def escribir_informe(cola, resumen):
    pend = [(u, r) for u, r in cola.ledger.items() if r.get("estado") == "pendiente"]
    cuenta = {}
    for r in cola.ledger.values():
        cuenta[r.get("estado", "?")] = cuenta.get(r.get("estado", "?"), 0) + 1
    lineas = ["# Informe de aprendizaje", "", f"- Generado: {ahora()}",
              "- Estados: " + ", ".join(f"{k} {v}" for k, v in sorted(cuenta.items())), "",
              "## Pendientes de revisión", ""]
    if not pend:
        lineas.append("(ninguno)")
    for u, r in sorted(pend):
        lineas.append(f"- `{r['paquete']}` ← {u.split('#')[0].split(':', 1)[-1]}")
    lineas += ["", "Revisar: `harness aprender ver <id>` · promover: `harness aprender promover <id> --tipo estandar --aplicar` "
               "· descartar: `harness aprender descartar <id> --motivo ...`", ""]
    (cola.base / "INFORME.md").write_text("\n".join(lineas), encoding="utf8")


# ------------------------------------------------------------------ listar / ver / descartar / promover
def cmd_listar(a):
    cola = Cola(ruta_cola(leer_registro()))
    filas = [(u, r) for u, r in cola.ledger.items() if a.todo or r.get("estado") == "pendiente"]
    if not filas:
        print("La cola está vacía." if not a.todo else "El ledger está vacío.")
        return 0
    for u, r in sorted(filas, key=lambda x: x[1].get("fecha", "")):
        ident = r.get("paquete") or "—"
        print(f"{ident:<48} {r.get('estado'):<10} {u.split('#')[0].split(':', 1)[-1]}")
    return 0


def paquete(cola, ident):
    uid, r = cola.por_slug(ident)
    d = cola.pendientes / ident
    if not r or not d.is_dir():
        raise Fallo(f"No hay un aporte pendiente «{ident}». Mira `harness aprender listar`.", 1)
    return uid, r, d


def cmd_ver(a):
    cola = Cola(ruta_cola(leer_registro()))
    _, r, d = paquete(cola, a.id)
    print((d / f"{a.id}.md").read_text(encoding="utf8"))
    print("— Nota de origen —")
    print((d / "ORIGEN.md").read_text(encoding="utf8"))
    return 0


def cmd_descartar(a):
    if not a.motivo:
        raise Fallo("Descartar exige --motivo (queda en el ledger para no volver a proponerlo).")
    cola = Cola(ruta_cola(leer_registro()))
    uid, r, d = paquete(cola, a.id)
    r["estado"], r["motivo"], r["fecha_decision"] = "descartada", a.motivo, ahora()
    shutil.rmtree(d, ignore_errors=True)
    cola.guardar()
    print(f"Descartado «{a.id}»: no se volverá a proponer mientras la sección no cambie.")
    return 0


def escaneo_publico(doc_dir, raiz):
    herr = AQUI / "harness-escaneo-publico.py"
    cmd = [sys.executable, str(herr), str(doc_dir), "--sin-historial"]
    terminos = lista_prohibidos(raiz)
    with tempfile.TemporaryDirectory(prefix="prohibidos-") as t:
        if terminos:
            lista = pathlib.Path(t) / "lista.txt"
            lista.write_text("\n".join(terminos) + "\n", encoding="utf8")
            cmd += ["--lista-prohibidos", str(lista)]
        r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def cmd_promover(a):
    if a.tipo not in ext.TIPOS:
        raise Fallo(f"--tipo debe ser uno de: {', '.join(sorted(ext.TIPOS))}.")
    raiz = pathlib.Path(a.harness).expanduser().resolve() if a.harness else RAIZ
    cola = Cola(ruta_cola(leer_registro()))
    uid, r, d = paquete(cola, a.id)
    capa = ext.TIPOS[a.tipo][0]
    cuerpo = (d / f"{a.id}.md").read_text(encoding="utf8").splitlines()
    cuerpo = [l for l in cuerpo if l.strip() != ETIQUETA_PROVISIONAL]
    final = [f"<!-- tipo: {a.tipo} · capa: {capa} -->", FRESCURA.format(fecha=datetime.date.today().isoformat())] + cuerpo
    texto = "\n".join(final).rstrip("\n") + "\n"
    with tempfile.TemporaryDirectory(prefix="promover-") as t:
        doc = pathlib.Path(t) / f"{a.id}.md"
        doc.write_text(texto, encoding="utf8")
        res = ext.evaluar(doc, ext.cargar_patron(None))
        print(f"Aporte «{a.id}» como {a.tipo} (capa {capa}).")
        print(f"Gate de extracción: {'PASA' if res['pasa'] else 'NO PASA'}")
        for regla, fs in res["reglas"].items():
            for f in fs:
                print(f"  · {f}")
        prohibidos = lista_prohibidos(raiz)
        golpe = next((p for p in prohibidos if p.lower() in texto.lower()), None)
        if golpe:
            print("  · contiene un término de la lista de prohibidos: no se promueve.")
        codigo, salida = escaneo_publico(t, raiz)
        if codigo != 0:
            print("Escaneo de publicación: HALLAZGOS")
            print("\n".join("  " + x for x in salida.splitlines()[:12]))
        if not res["pasa"] or golpe or codigo != 0:
            print("RESULTADO: no se promueve. Corrige el documento de la cola o descártalo.")
            return 1
        sub, err = ext.subcarpeta(res["tipo"], a.stack, a.adaptador)
        if err:
            raise Fallo(err)
        if not a.aplicar:
            print(f"RESULTADO: pasaría a {raiz / sub / doc.name}. Sin --aplicar no se escribe nada.")
            return 0
        ok, msg = ext.aplicar(res, raiz, a.stack, a.adaptador, cola.base)
        if not ok:
            print(f"RESULTADO: no se aplicó: {msg}")
            return 1
    r["estado"], r["fecha_decision"], r["destino"] = "promovida", ahora(), f"{sub}/{a.id}.md"
    shutil.rmtree(d, ignore_errors=True)
    cola.guardar()
    print(f"RESULTADO: {msg}")
    print("No se hizo commit ni push. Revisa `git diff`, haz el commit local y sube la versión (menor) cuando corresponda.")
    return 0


# ------------------------------------------------------------------ main
def parser():
    p = argparse.ArgumentParser(description="Aprendizaje automático del meta harness (no sube nada por sí mismo)")
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fuentes")
    f.add_argument("accion", choices=("listar", "agregar", "quitar"))
    f.add_argument("nombre", nargs="?")
    f.add_argument("ruta", nargs="?")
    f.add_argument("--tipo", choices=TIPOS_FUENTE, default="carpeta")
    f.add_argument("--incluir", action="append")
    f.add_argument("--excluir", action="append")
    e = sub.add_parser("escanear")
    e.add_argument("--fuente")
    e.add_argument("--max-frecuencia", type=int, default=0, dest="max_frecuencia", help="no escanear si el último fue hace menos de N segundos")
    e.add_argument("--silencioso", action="store_true")
    e.add_argument("--json", action="store_true")
    l = sub.add_parser("listar")
    l.add_argument("--todo", action="store_true")
    v = sub.add_parser("ver")
    v.add_argument("id")
    d = sub.add_parser("descartar")
    d.add_argument("id")
    d.add_argument("--motivo")
    pr = sub.add_parser("promover")
    pr.add_argument("id")
    pr.add_argument("--tipo", required=True)
    pr.add_argument("--stack")
    pr.add_argument("--adaptador")
    pr.add_argument("--aplicar", action="store_true")
    pr.add_argument("--harness", help="raíz del harness donde promover (por defecto, el repositorio de esta herramienta)")
    return p


def main(argv=None):
    try:
        return _main(argv)
    except BrokenPipeError:  # `... | head`
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0


def _main(argv=None):
    a = parser().parse_args(argv)
    silencioso = getattr(a, "silencioso", False)
    try:
        return {"fuentes": cmd_fuentes, "escanear": cmd_escanear, "listar": cmd_listar, "ver": cmd_ver,
                "descartar": cmd_descartar, "promover": cmd_promover}[a.cmd](a)
    except Fallo as e:
        if not silencioso:
            print(str(e), file=sys.stderr)
        return e.codigo
    except Exception as e:  # el hook de fin de sesión nunca debe romper la sesión
        if silencioso:
            return 0
        raise


if __name__ == "__main__":
    sys.exit(main())
