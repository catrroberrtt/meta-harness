#!/usr/bin/env python3
"""Clasifica una lección de una instancia y, si es general y pasa el gate, arma un paquete de aporte para el harness.

<!-- tipo: herramienta · capa: 4 -->

Uso:
  python3 harness-aportar.py <lección.md> --instancia <raíz-de-la-instancia> [--salida <carpeta>]

Sin --salida es SOLO LECTURA: clasifica e imprime el veredicto, la razón y las líneas que la causan.
Con --salida y veredicto «general» que pasa el gate, crea <salida>/<nombre>/ con:
  <nombre>.md   el documento listo (con las referencias al proyecto sustituidas por marcas)
  gate.txt      el resultado del gate de extracción sobre ese documento
  ORIGEN.md     nota de origen ANONIMIZADA (sin proyecto, sin personas, sin tickets, sin rutas)
Nunca modifica la instancia ni el harness, no sobrescribe un paquete existente y NUNCA sube nada por sí mismo:
el paquete se revisa a mano y se incorpora por el camino de metodo/aprendizaje.md.

Veredictos (reglas explícitas; ver «Cómo decide» en metodo/aprendizaje.md):
  general     ninguna línea trae señal de negocio. Si cita al proyecto (ticket, repo, PR, persona, ruta, URL) solo como ejemplo,
              sube con esas referencias sustituidas; el resultado se vuelve a evaluar y debe quedar sin una sola.
  mixta       menos del 40 % de las líneas de contenido son de negocio: se lista línea por línea qué se queda y qué sube.
  de negocio  40 % o más de las líneas de contenido son de negocio: se queda en la instancia.
Señales de negocio (fuertes): términos de `dominio.txt` de la instancia, importes con moneda, porcentajes junto a una palabra de
tarifa o riesgo (tasa, comisión, mora…), frases de decisión del negocio. Señales de referencia (anonimizables): patrón de
`patrones-proyecto.txt` (o la variable HARNESS_PATRON_PROYECTO), nombres de `personas.txt`, rutas locales, URLs, cuentas.
Señales débiles (solo se avisan; exigen criterio humano): nombres propios a mitad de frase, nombres de entorno, cantidades con unidad.
Solo biblioteca estándar.
"""
import argparse, datetime, hashlib, importlib.util, pathlib, re, shutil, sys, tempfile, unicodedata

AQUI = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("harness_extraer", AQUI / "harness-extraer.py")
ext = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ext)

UMBRAL_NEGOCIO = 0.4

MONEDA = re.compile(r"(?:S/\.?|US\$|\$|€|£)\s?\d|\b\d[\d.,]*\s?(?:soles|dólares|dolares|euros|USD|PEN|EUR|MXN|CLP|COP)\b", re.I)
PORCENTAJE = re.compile(r"\d+(?:[.,]\d+)?\s?%")
PALABRA_TARIFA = re.compile(r"\b(?:tasa|inter[eé]s|comisi[oó]n|retenci[oó]n|penalidad|descuento|impuesto|IGV|IVA|rentabilidad|margen|mora|tarifa|recargo)\b", re.I)
DECISION = re.compile(r"\b(?:el negocio (?:decidi[oó]|defini[oó]|pidi[oó]|acord[oó])|decisi[oó]n (?:de|del) negocio|acuerdo comercial|pol[ií]tica comercial|seg[uú]n el cliente|lo pidi[oó] (?:el|la) (?:cliente|gerencia|direcci[oó]n))\b", re.I)
URL = re.compile(r"https?://[^\s)>\]\"'`]+")
URL_PUBLICAS = ("example.com", "example.org", "localhost", "127.0.0.1", "0.0.0.0", "developer.mozilla.org", "www.w3.org", "docs.aws.amazon.com",
                "nodejs.org", "typeorm.io", "angular.dev", "material.angular.io", "stackoverflow.com", "en.wikipedia.org", "datatracker.ietf.org")
RUTA = re.compile(r"/home/[a-z][\w.-]*(?:/[\w.\-]+)*|/Users/[A-Za-z][\w.-]*(?:/[\w.\-]+)*|~/[\w/.\-]+")
CUENTA = re.compile(r"\b\d{12}\b")
ENTORNO_DEBIL = re.compile(r"\b(?:producci[oó]n|prod|qas?|staging|preprod|sandbox)\b", re.I)
CANTIDAD_DEBIL = re.compile(r"\b\d[\d.,]*\s+(?:clientes|usuarios|pedidos|contratos|facturas|pagos|cuentas)\b", re.I)
NOMBRE = re.compile(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}\b")
TECNOLOGIAS = {"TypeScript", "JavaScript", "Angular", "Material", "Node", "NestJS", "TypeORM", "MySQL", "Docker", "Git", "GitHub", "Jest", "Python",
               "Postgres", "Redis", "Linux", "Windows", "Chrome", "Firefox", "Cypress", "Cucumber", "Jira", "Confluence", "Slack", "Excel", "Word",
               "Bearer", "Express", "React", "Vue", "Java", "Spring", "Kotlin", "Terraform", "Kubernetes", "Lambda", "Mandrill", "Swagger"}
MESES_DIAS = {"Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
              "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"}


class Contexto:
    def __init__(self, instancia):
        self.instancia = pathlib.Path(instancia)
        self.patron = ext.cargar_patron(self.instancia)
        f = self.instancia / "dominio.txt"
        self.dominio = ext.leer_lista(f) if f.is_file() else []
        self.dominio_rx = [re.compile(r"(?<!\w)" + re.escape(t) + r"(?!\w)", re.I) for t in self.dominio]
        f = self.instancia / "personas.txt"
        self.personas = ext.leer_lista(f) if f.is_file() else []
        self.personas_rx = [re.compile(r"(?<!\w)" + re.escape(t) + r"(?!\w)") for t in self.personas]


def url_privada(u):
    host = re.sub(r"^https?://", "", u).split("/")[0].split(":")[0].lower()
    return not any(host == p or host.endswith("." + p) for p in URL_PUBLICAS)


def sin_codigo_en_linea(l):
    return re.sub(r"`[^`\n]*`", " ", l)


def analizar(lineas, ctx):
    """Una ficha por línea: {n, texto, rol, cerco, fuertes:[(clase,texto)], debiles:[(clase,texto)]}."""
    fichas, cerco = [], False
    for n, l in enumerate(lineas, 1):
        s = l.strip()
        if s.startswith("```"):
            cerco = not cerco
            fichas.append({"n": n, "texto": l, "rol": "marca", "cerco": True, "fuertes": [], "debiles": []}); continue
        if not s:
            rol = "vacia"
        elif ext.TAG.search(l) and n <= 12 and s.startswith("<!--"):
            rol = "marca"
        elif s.startswith("#") and not cerco:
            rol = "cabecera"
        else:
            rol = "contenido"
        f = {"n": n, "texto": l, "rol": rol, "cerco": cerco, "fuertes": [], "debiles": []}
        fichas.append(f)
        if rol in ("vacia", "marca"):
            continue
        for m in ctx.patron.finditer(l):
            f["fuertes"].append(("proyecto", m.group(0)))
        for rx in ctx.personas_rx:
            for m in rx.finditer(l):
                f["fuertes"].append(("persona", m.group(0)))
        for rx, t in zip(ctx.dominio_rx, ctx.dominio):
            if rx.search(l):
                f["fuertes"].append(("dominio", t))
        for m in MONEDA.finditer(l):
            f["fuertes"].append(("cifra", m.group(0)))
        if PORCENTAJE.search(l) and PALABRA_TARIFA.search(l):
            f["fuertes"].append(("cifra", PORCENTAJE.search(l).group(0) + " junto a «" + PALABRA_TARIFA.search(l).group(0) + "»"))
        for m in DECISION.finditer(l):
            f["fuertes"].append(("decisión", m.group(0)))
        for m in URL.finditer(l):
            if url_privada(m.group(0)):
                f["fuertes"].append(("entorno", m.group(0)))
        for m in RUTA.finditer(l):
            f["fuertes"].append(("entorno", m.group(0)))
        for m in CUENTA.finditer(l):
            f["fuertes"].append(("entorno", m.group(0)))
        for m in ENTORNO_DEBIL.finditer(l):
            f["debiles"].append(("nombre de entorno", m.group(0)))
        for m in CANTIDAD_DEBIL.finditer(l):
            f["debiles"].append(("cantidad con unidad", m.group(0)))
        if not cerco and rol == "contenido":
            for frase in re.split(r"(?<=[.!?:;])\s+", sin_codigo_en_linea(l)):
                ini = len(frase) - len(frase.lstrip(" \t-*>0123456789.)"))
                for m in NOMBRE.finditer(frase):
                    if m.start() <= ini:
                        continue  # primera palabra de la frase: no se distingue de una mayúscula normal
                    if m.group(0) in TECNOLOGIAS or m.group(0) in MESES_DIAS:
                        continue
                    f["debiles"].append(("nombre propio", m.group(0)))
    return fichas


def categoria(f):
    """negocio | referencia | tecnica | (None si no cuenta)."""
    if f["rol"] in ("vacia", "marca"):
        return None
    clases = {c for c, _ in f["fuertes"]}
    if clases & {"dominio", "cifra", "decisión"}:
        return "negocio"
    if clases & {"proyecto", "persona", "entorno"}:
        return "referencia"
    return "tecnica"


def veredicto(fichas):
    contenido = [f for f in fichas if f["rol"] == "contenido"]
    cat = {f["n"]: categoria(f) for f in fichas}
    neg = [f for f in fichas if cat[f["n"]] == "negocio"]
    ref = [f for f in fichas if cat[f["n"]] == "referencia"]
    neg_cont = [f for f in neg if f["rol"] == "contenido"]
    tec = [f for f in contenido if cat[f["n"]] == "tecnica"]
    total = max(len(contenido), 1)
    if not neg:
        if ref:
            razon = (f"{len(ref)} línea(s) citan al proyecto (referencias) pero ninguna trae reglas, cifras ni términos de negocio: "
                     "el contenido es técnico y sube con las referencias sustituidas por marcas.")
            return "general (con referencias a anonimizar)", razon, cat
        return "general", "ninguna línea cita al proyecto ni trae términos de dominio, cifras o decisiones de negocio.", cat
    proporcion = len(neg_cont) / total
    detalle = f"{len(neg_cont)} de {len(contenido)} líneas de contenido son de negocio ({proporcion:.0%}; umbral {UMBRAL_NEGOCIO:.0%})"
    if proporcion >= UMBRAL_NEGOCIO or not tec:
        return "de negocio", detalle + (": domina lo del negocio, se queda." if tec else " y no queda parte técnica separable."), cat
    return "mixta", detalle + f"; hay {len(tec)} línea(s) técnicas sin atadura que podrían subir con un ejemplo anonimizado.", cat


# ---------- anonimización ----------
def marca_para(s):
    if ext.RX_PR.fullmatch(s):
        return "<PR>"
    if ext.RX_TICKET.fullmatch(s):
        return "<TICKET>"
    if re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)+", s):
        return "<repo>"
    return "<proyecto>"


def anonimizar(texto, ctx, cuenta):
    out = []
    for l in texto.splitlines():
        for rx in ctx.personas_rx:
            l = rx.sub(lambda m: (cuenta.__setitem__("persona", cuenta.get("persona", 0) + 1), "<persona>")[1], l)
        l = RUTA.sub(lambda m: (cuenta.__setitem__("ruta", cuenta.get("ruta", 0) + 1), "<ruta-local>")[1], l)
        l = URL.sub(lambda m: (cuenta.__setitem__("url", cuenta.get("url", 0) + 1), "<url>")[1] if url_privada(m.group(0)) else m.group(0), l)
        l = ctx.patron.sustituir(l, lambda s: (cuenta.__setitem__(marca_para(s)[1:-1].lower(), cuenta.get(marca_para(s)[1:-1].lower(), 0) + 1), marca_para(s))[1])
        l = CUENTA.sub(lambda m: (cuenta.__setitem__("cuenta", cuenta.get("cuenta", 0) + 1), "<cuenta>")[1], l)
        out.append(l)
    return "\n".join(out) + ("\n" if texto.endswith("\n") else "")


def slug_de(texto, ctx):
    h1 = next((l[2:].strip() for l in texto.splitlines() if l.startswith("# ")), "")
    s = unicodedata.normalize("NFKD", h1).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > 60:
        s = s[:60].rsplit("-", 1)[0]
    if not s or ctx.patron.search(s) or any(rx.search(s) for rx in ctx.dominio_rx):
        s = "aporte-" + hashlib.sha256(texto.encode()).hexdigest()[:8]
    return s


def residuos(texto, ctx):
    fichas = analizar(texto.splitlines(), ctx)
    return [(f["n"], c, t) for f in fichas for c, t in f["fuertes"]]


def armar_paquete(lec, texto, ctx, salida, razon, veredicto_txt, fichas):
    cuenta = {}
    nuevo = anonimizar(texto, ctx, cuenta)
    sobran = residuos(nuevo, ctx)
    if sobran:
        return False, ["tras anonimizar quedan señales: " + ", ".join(f"L{n} {c}" for n, c, _ in sobran[:8])]
    slug = slug_de(nuevo, ctx)
    destino = pathlib.Path(salida) / slug
    if destino.exists() and any(destino.iterdir()):
        return False, [f"{destino} ya existe: no se sobrescribe"]
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="aporte-"))
    try:
        doc = tmp / (slug + ".md")
        doc.write_text(nuevo, encoding="utf8")
        res = ext.evaluar(doc, ctx.patron)
        gate = [f"{'PASA' if res['pasa'] else 'NO PASA'}  [tipo: {res['tipo'] or '—'}]"]
        for k, fs in res["reglas"].items():
            gate += [f"  · {f}" for f in fs]
        if not res["pasa"]:
            return False, ["el gate de extracción no pasa sobre el documento anonimizado:"] + gate[1:]
        debiles = sorted({(f["n"], c) for f in analizar(nuevo.splitlines(), ctx) for c, _ in f["debiles"]})
        sust = ", ".join(f"{k} ×{v}" for k, v in sorted(cuenta.items())) or "ninguna"
        nota = ["# Nota de origen (anonimizada)", "",
                f"- Fecha del aporte: {datetime.date.today().isoformat()}",
                f"- Clasificación: {veredicto_txt}", f"- Razón: {razon}",
                f"- Documento: `{slug}.md` · sha256 {hashlib.sha256(nuevo.encode()).hexdigest()}",
                f"- Sustituciones automáticas: {sust} (los valores originales no se guardan en el paquete)",
                "- Origen: una instancia sin identificar. No se registran proyecto, personas ni tickets.", "",
                "## Para quien revisa", "",
                "- [ ] El documento se entiende sin conocer el proyecto de origen.",
                "- [ ] Los ejemplos son inventados o genéricos, no datos reales.",
                "- [ ] Las marcas `<...>` leen bien en el texto; si no, reescribir la frase.",
                "- [ ] Tipo y capa de la marca `<!-- tipo: ... -->` son los correctos.",
                f"- [ ] Señales débiles que ninguna regla resuelve (líneas del documento): {', '.join(f'{n} ({c})' for n, c in debiles) or 'ninguna'}."]
        destino.mkdir(parents=True, exist_ok=True)
        shutil.copy2(doc, destino / doc.name)
        (destino / "gate.txt").write_text("\n".join(gate) + "\n", encoding="utf8")
        (destino / "ORIGEN.md").write_text("\n".join(nota) + "\n", encoding="utf8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # defensa final: ni un archivo del paquete debe contener una señal
    for p in destino.iterdir():
        if residuos(p.read_text(encoding="utf8"), ctx):
            shutil.rmtree(destino, ignore_errors=True)
            return False, [f"{p.name} contenía señales del proyecto: paquete descartado"]
    return True, [f"paquete creado en {destino}", "  " + ", ".join(sorted(p.name for p in destino.iterdir())),
                  "  Nada se subió: revisa el paquete y súbelo por el camino de metodo/aprendizaje.md."]


def mostrar(lec, veredicto_txt, razon, fichas, cat, ctx):
    print(f"LECCIÓN: {lec}")
    print(f"PATRÓN DEL PROYECTO: {ctx.patron.origen}; dominio.txt: {len(ctx.dominio)} término(s); personas.txt: {len(ctx.personas)}")
    print(f"VEREDICTO: {veredicto_txt}")
    print(f"RAZÓN: {razon}")
    causas = [f for f in fichas if f["fuertes"]]
    if causas:
        print("LÍNEAS QUE LO CAUSAN:")
        for f in causas:
            det = "; ".join(f"{c}: «{t[:50]}»" for c, t in f["fuertes"][:4])
            print(f"  L{f['n']:<3} [{cat[f['n']]}] {det}\n        {f['texto'].strip()[:110]}")
    deb = [f for f in fichas if f["debiles"]]
    if deb:
        print("SEÑALES DÉBILES (criterio humano; no cambian el veredicto):")
        for f in deb[:12]:
            print(f"  L{f['n']:<3} " + "; ".join(f"{c}: «{t}»" for c, t in f["debiles"][:4]))
        if len(deb) > 12:
            print(f"  … {len(deb) - 12} línea(s) más")


def proponer_corte(fichas, cat):
    print("PROPUESTA DE CORTE (línea por línea):")
    print("  SE QUEDA en la instancia (negocio):")
    for f in fichas:
        if cat[f["n"]] == "negocio":
            print(f"    L{f['n']:<3} {f['texto'].strip()[:100]}")
    print("  SUBE (técnico; las referencias se sustituyen por marcas):")
    for f in fichas:
        if cat[f["n"]] in ("tecnica", "referencia") and f["rol"] in ("contenido", "cabecera"):
            extra = "  (anonimizar)" if cat[f["n"]] == "referencia" else ""
            print(f"    L{f['n']:<3} {f['texto'].strip()[:90]}{extra}")
    print("  Siguiente paso: reescribe la lección en dos documentos (la parte técnica sin negocio, con un ejemplo inventado; la de negocio se queda) y vuelve a correr esta herramienta sobre la técnica.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Clasifica una lección y arma el paquete de aporte (nunca sube nada)")
    ap.add_argument("leccion")
    ap.add_argument("--instancia", required=True, help="raíz de la instancia (patrones-proyecto.txt, dominio.txt, personas.txt)")
    ap.add_argument("--salida", help="carpeta donde crear el paquete (solo si la lección es general y pasa el gate)")
    a = ap.parse_args(argv)
    lec = pathlib.Path(a.leccion)
    inst = pathlib.Path(a.instancia)
    if not lec.is_file():
        print(f"no existe: {lec}", file=sys.stderr); return 2
    if not inst.is_dir():
        print(f"la instancia no es una carpeta: {inst}", file=sys.stderr); return 2
    if a.salida:
        s, i = pathlib.Path(a.salida).resolve(), inst.resolve()
        if s == i or i in s.parents:
            print("--salida no puede estar dentro de la instancia (la instancia no se modifica)", file=sys.stderr); return 2
    ctx = Contexto(inst)
    texto = lec.read_text(encoding="utf8", errors="ignore")
    fichas = analizar(texto.splitlines(), ctx)
    v, razon, cat = veredicto(fichas)
    mostrar(lec, v, razon, fichas, cat, ctx)
    if v == "de negocio":
        print("RESULTADO: se queda en la instancia; no se arma nada."); return 1
    if v == "mixta":
        proponer_corte(fichas, cat)
        print("RESULTADO: no se arma paquete hasta separar la parte técnica."); return 1
    if not a.salida:
        print("RESULTADO: sin --salida no se escribe nada. Con --salida <carpeta> se armaría el paquete."); return 0
    ok, msgs = armar_paquete(lec, texto, ctx, a.salida, razon, v, fichas)
    print("PAQUETE: " + ("\n".join(msgs) if ok else "NO se armó:\n  " + "\n  ".join(msgs)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
