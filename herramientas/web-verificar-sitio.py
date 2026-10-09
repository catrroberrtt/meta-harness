#!/usr/bin/env python3
"""Verificador estático de un sitio web generado (SOLO LECTURA, sin red, sin navegador, solo biblioteca estándar).

Comprueba lo que se puede comprobar leyendo archivos: lang y title, jerarquía de encabezados, alt de imágenes,
contraste WCAG de los pares de color de tokens.css (claro y oscuro), tamaños de fuente en px, peso de páginas y
activos, enlaces y recursos internos rotos, secretos, recursos remotos y trackers no declarados, licencia de los
activos, señales de texto de relleno y referencias a marcas ajenas en la ficha de marca declarada (DISENO.md; decisión
2026-10-09: los sistemas «inspirados en marcas reales» no se usan ni como referencia). NO mide rendimiento real, ni lector de pantalla, ni teclado: ver
estandares/diseno-web.md §5.

Uso: python3 web-verificar-sitio.py <carpeta> [--json] [--estricto] [--permitidos archivo]
        [--max-html-kb N] [--max-css-kb N] [--max-img-kb N] [--max-pagina-kb N]
Salida: 0 sin errores; 1 con errores (con --estricto, también con avisos); 2 uso incorrecto.
Recursos remotos permitidos: <carpeta>/sitio.permitidos.txt (un dominio por línea, «*.dominio» admitido, «#» comenta).
Licencias de activos: <carpeta>/activos/LICENCIAS.md (una línea por activo con origen, autoría y licencia).
Pares extra de contraste, en tokens.css: /* contraste: --a sobre --b >= 4.5 */"""
import argparse, json, pathlib, re, sys
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote

ERROR, AVISO = "error", "aviso"
EXT_PAGINA = {".html", ".htm"}
EXT_MEDIA = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".otf",
             ".eot", ".mp4", ".webm", ".mp3", ".ogg", ".wav", ".pdf"}
EXT_IMAGEN = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico"}
EXT_TEXTO = {".html", ".htm", ".css", ".js", ".mjs", ".json", ".txt", ".md", ".svg", ".xml", ".yml", ".yaml",
             ".toml", ".ini", ".map", ".env"}
REL_NAVEGACION = {"canonical", "alternate", "author", "license", "me", "next", "prev", "help", "search", "bookmark"}
TRACKERS = ("google-analytics.com", "googletagmanager.com", "doubleclick.net", "googlesyndication.com",
            "facebook.net", "facebook.com/tr", "hotjar.com", "clarity.ms", "segment.com", "segment.io", "mixpanel.com",
            "fullstory.com", "amplitude.com", "heap.io", "heapanalytics.com", "hs-scripts.com", "hubspot.com",
            "intercom.io", "crisp.chat", "tiktok.com/i18n", "ads-twitter.com", "linkedin.com/px", "matomo",
            "plausible.io", "posthog.com", "sentry.io", "newrelic.com", "datadoghq.com", "bat.bing.com")
MARCADORES = ("unsplash.com", "placehold.co", "placekitten.com", "picsum.photos", "via.placeholder.com",
              "lorempixel.com", "dummyimage.com", "placeimg.com", "loremflickr.com")
INDIGOS = {"#6366f1", "#4f46e5", "#4338ca", "#3730a3", "#8b5cf6", "#7c3aed", "#a855f7"}
RELLENO = re.compile(r"lorem ipsum|dolor sit amet|feature (one|two|three)\b|placeholder text|sample content|"
                     r"your (text|content|title) here|texto de relleno|texto de ejemplo aqu[ií]|t[ií]tulo aqu[ií]|"
                     r"caracter[ií]stica (uno|dos|tres)\b", re.I)
METRICA = re.compile(r"\b\d+(?:[.,]\d+)?\s?[x×]\s*(?:m[aá]s|more|faster|r[aá]pid|veces)|\b99[.,]9\s?%\s*(?:uptime|de disponibilidad|disponibilidad)", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⚡]")
SECRETOS = [
    ("clave de AWS", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("clave privada", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("token de GitHub", re.compile(r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("token de Slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("clave de API (sk-)", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("clave de Google", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}")),
    ("asignación de secreto", re.compile(r"(?i)\b(?:api[_-]?key|secret|password|passwd|contrase[nñ]a|access[_-]?token)\b['\"]?\s*[:=]\s*['\"][^'\"\s]{8,}['\"]")),
]
# Ficha de marca declarada (DISENO.md): un sistema de diseño «inspirado en» una marca real queda prohibido, incluso como referencia a imitar.
MARCAS_AJENAS = ("Stripe", "Apple", "BMW", "Ferrari", "Nike", "Airbnb", "Spotify", "Starbucks", "Mastercard", "Tesla", "Vercel",
                 "Shopify", "Uber", "Google", "Microsoft", "Amazon", "Netflix", "Adobe", "IBM", "Coinbase", "Revolut", "Porsche",
                 "Lamborghini", "Mercedes", "Audi", "Ikea", "Pinterest", "Supabase", "Framer", "Webflow", "Cloudflare", "Zapier",
                 "Airtable", "Dropbox", "PayPal", "Samsung", "Sony", "Nvidia", "Figma", "Slack", "Intercom", "Mintlify", "Raycast")
RX_MARCA = re.compile(r"(?<![\w-])(" + "|".join(re.escape(m) for m in MARCAS_AJENAS) + r")(?![\w-])")
RX_IMITACION = re.compile(r"inspirad[oa]s?\s+en|inspired\s+by|al\s+estilo\s+de|in\s+the\s+style\s+of|estilo\s+de|style\s+of|"
                          r"similar\s+a|parecid[oa]s?\s+a|como\s+(?:el|la|los|las)\b|clon\s+de|copia\s+de|imitar?|igual\s+que|"
                          r"basad[oa]s?\s+en|like\b|based\s+on|referencia|dise[ñn]o\s+de|design\s+system\s+(?:of|from)|como\s+base", re.I)
RX_INSPIRADO_EN = re.compile(r"(?i:inspirad[oa]s?\s+en|inspired\s+by|al\s+estilo\s+de|in\s+the\s+style\s+of|clon\s+de|copia\s+de)\s+"
                             r"(?i:la\s+marca\s+|el\s+sitio\s+de\s+|la\s+web\s+de\s+)?([A-Z][\w.&-]+)")
RX_NEGACION = re.compile(r"\b(?:no|nunca|sin|jam[aá]s|evitar?|prohibid[oa]s?|never|don'?t|avoid)\b", re.I)
PARES_DEFECTO = [("--text", "--bg", 4.5), ("--text", "--surface", 4.5), ("--muted", "--bg", 4.5),
                 ("--muted", "--surface", 4.5), ("--on-brand", "--brand-600", 4.5), ("--brand-600", "--bg", 4.5),
                 ("--focus-ring", "--bg", 3.0)] + [(f"--tone-{t}-fg", f"--tone-{t}-bg", 4.5) for t in ("ok", "warn", "danger", "info")]
PAR_DECLARADO = re.compile(r"contraste:\s*(--[\w-]+)\s+sobre\s+(--[\w-]+)\s*>=\s*([\d.]+)")
NOMBRES_COLOR = {"white": (255, 255, 255), "black": (0, 0, 0)}


def hallazgo(nivel, codigo, archivo, mensaje, linea=None):
    return {"nivel": nivel, "codigo": codigo, "archivo": str(archivo), "linea": linea, "mensaje": mensaje}


# ---------------------------------------------------------------- color y contraste (WCAG 2.x)
def _canal(v):
    v = v / 255
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def luminancia(rgb):
    r, g, b = (_canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def razon_contraste(a, b):
    la, lb = luminancia(a), luminancia(b)
    claro, oscuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (oscuro + 0.05)


def _num(txt, escala=1.0):
    txt = txt.strip()
    return float(txt[:-1]) * escala / 100 if txt.endswith("%") else float(txt)


def parsear_color(valor):
    """Devuelve (r,g,b) 0-255 o None si no se puede resolver (alfa < 1, formato desconocido, var sin resolver)."""
    v = valor.strip().lower().rstrip(";").replace("!important", "").strip()
    if v in NOMBRES_COLOR:
        return NOMBRES_COLOR[v]
    m = re.fullmatch(r"#([0-9a-f]{3,8})", v)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) == 8:
            if int(h[6:], 16) != 255:
                return None
            h = h[:6]
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) if len(h) == 6 else None
    m = re.fullmatch(r"rgba?\(([^)]*)\)", v)
    if m:
        partes = [p for p in re.split(r"[\s,/]+", m.group(1).strip()) if p]
        if len(partes) == 4 and _num(partes[3]) < 1:
            return None
        try:
            return tuple(max(0, min(255, round(_num(p, 255)))) for p in partes[:3]) if len(partes) >= 3 else None
        except ValueError:
            return None
    m = re.fullmatch(r"hsla?\(([^)]*)\)", v)
    if m:
        partes = [p for p in re.split(r"[\s,/]+", m.group(1).strip()) if p]
        if len(partes) < 3 or (len(partes) == 4 and _num(partes[3]) < 1):
            return None
        try:
            h = float(partes[0].replace("deg", "")) % 360
            s = float(partes[1].rstrip("%")) / 100
            l = float(partes[2].rstrip("%")) / 100
        except ValueError:
            return None
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m0 = l - c / 2
        r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][int(h // 60) % 6]
        return tuple(round((q + m0) * 255) for q in (r, g, b))
    return None


# ---------------------------------------------------------------- CSS
def sin_comentarios(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def iter_reglas(css):
    """Rinde (contextos, selector, declaraciones). Contextos = preludios de at-rules que envuelven la regla."""
    css = sin_comentarios(css)
    pila = [{"pre": "", "decl": "", "pend": ""}]
    comilla = None
    for ch in css:
        top = pila[-1]
        if comilla:
            top["pend"] += ch
            if ch == comilla:
                comilla = None
            continue
        if ch in "\"'":
            comilla = ch
            top["pend"] += ch
        elif ch == "{":
            pre = top["pend"].strip()
            top["pend"] = ""
            pila.append({"pre": pre, "decl": "", "pend": ""})
        elif ch == "}":
            if len(pila) == 1:
                continue
            f = pila.pop()
            f["decl"] += f["pend"]
            ctx = tuple(p["pre"] for p in pila[1:] if p["pre"].startswith("@"))
            if f["decl"].strip() and not f["pre"].startswith(("@media", "@supports", "@layer")):
                yield ctx, f["pre"], f["decl"]
        elif ch == ";":
            top["decl"] += top["pend"] + ";"
            top["pend"] = ""
        else:
            top["pend"] += ch


def declaraciones(cuerpo):
    return [(m.group(1), m.group(2).strip()) for m in re.finditer(r"([\w-]+)\s*:\s*([^;]+)", cuerpo)]


def es_raiz(selector):
    return any(re.match(r"^(:root|html)(\W|$)", s.strip()) for s in selector.split(","))


def extraer_tokens(css):
    """Devuelve {'claro': {...}, 'oscuro': {...}} con las propiedades personalizadas de :root."""
    temas = {"claro": {}, "oscuro": {}}
    for ctx, sel, cuerpo in iter_reglas(css):
        if not es_raiz(sel):
            continue
        oscuro_ctx = any("prefers-color-scheme" in c and "dark" in c for c in ctx)
        otras = [c for c in ctx if "prefers-color-scheme" not in c and c.startswith("@media")]
        if otras:
            continue
        directo = re.sub(r":not\([^)]*\)", "", sel)  # `:not([data-theme='light'])` no declara el tema claro
        marcado_oscuro = bool(re.search(r"data-theme\s*=\s*['\"]?dark", directo))
        marcado_claro = bool(re.search(r"data-theme\s*=\s*['\"]?light", directo))
        if marcado_claro:
            tema = "claro"
        elif marcado_oscuro or oscuro_ctx:
            tema = "oscuro"
        else:
            tema = "claro"
        for nombre, valor in declaraciones(cuerpo):
            if nombre.startswith("--"):
                temas[tema][nombre] = valor
    return temas


def resolver(valor, tokens, vistos=()):
    m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)", valor.strip())
    if not m:
        return valor
    nombre = m.group(1)
    if nombre in vistos:
        return None
    if nombre in tokens:
        return resolver(tokens[nombre], tokens, vistos + (nombre,))
    return resolver(m.group(2), tokens, vistos) if m.group(2) else None


def comprobar_contraste(css, archivo):
    res, temas = [], extraer_tokens(css)
    pares = list(PARES_DEFECTO) + [(a, b, float(n)) for a, b, n in PAR_DECLARADO.findall(css)]
    if not temas["claro"] and not temas["oscuro"]:
        return [hallazgo(AVISO, "contraste-sin-tokens", archivo, "no hay propiedades personalizadas en :root: contraste no comprobado")]
    evaluados = 0
    for nombre_tema in ("claro", "oscuro"):
        tokens = dict(temas["claro"])
        if nombre_tema == "oscuro":
            if not temas["oscuro"]:
                continue
            tokens.update(temas["oscuro"])
        for a, b, minimo in pares:
            if a not in tokens or b not in tokens:
                continue
            ca, cb = (parsear_color(resolver(tokens[x], tokens) or "") for x in (a, b))
            if ca is None or cb is None:
                res.append(hallazgo(AVISO, "contraste-no-evaluable", archivo, f"tema {nombre_tema}: {a}/{b} no se pudo resolver a un color opaco"))
                continue
            evaluados += 1
            r = razon_contraste(ca, cb)
            if r + 1e-9 < minimo:
                res.append(hallazgo(ERROR, "contraste", archivo, f"tema {nombre_tema}: {a} sobre {b} = {r:.2f}:1 (mínimo {minimo}:1)"))
    if evaluados == 0:
        res.append(hallazgo(AVISO, "contraste-sin-pares", archivo, "ningún par por defecto o declarado tiene ambos tokens: contraste no comprobado"))
    return res


def comprobar_css_texto(css, archivo, es_tokens=False):
    """Fuentes en px, hex crudos fuera de :root, índigos por defecto, movimiento."""
    res, crudos = [], []
    limpio = sin_comentarios(css)
    for ctx, sel, cuerpo in iter_reglas(css):
        for nombre, valor in declaraciones(cuerpo):
            if nombre == "font-size" and re.search(r"\d(?:\.\d+)?px\b", valor):
                res.append(hallazgo(ERROR, "fuente-px", archivo, f"font-size en px en «{sel[:40]}»: usar rem o em"))
            elif nombre == "font" and re.search(r"\d(?:\.\d+)?px\b", valor):
                res.append(hallazgo(ERROR, "fuente-px", archivo, f"font en px en «{sel[:40]}»: usar rem o em"))
            elif nombre.startswith(("--text-", "--font-size")) and re.fullmatch(r"[\d.]+px", valor.strip()):
                res.append(hallazgo(ERROR, "fuente-px", archivo, f"token {nombre} en px: usar rem"))
            if not es_raiz(sel) and not nombre.startswith("--"):
                crudos += re.findall(r"#[0-9a-fA-F]{3,8}\b|\brgba?\([^)]*\)|\bhsla?\([^)]*\)", valor)
    if crudos:
        res.append(hallazgo(AVISO, "color-crudo", archivo, f"{len(crudos)} color(es) escrito(s) fuera de :root (ej.: {crudos[0]}): leer variables de tokens.css"))
    for h in {x.lower() for x in re.findall(r"#[0-9a-fA-F]{6}\b", limpio)} & INDIGOS:
        res.append(hallazgo(AVISO, "indigo-defecto", archivo, f"{h} es el índigo por defecto de las plantillas genéricas: usar el color de la marca"))
    if re.search(r"@keyframes|\banimation\s*:|\btransition\s*:", limpio) and "prefers-reduced-motion" not in limpio:
        res.append(hallazgo(AVISO, "movimiento", archivo, "hay animaciones o transiciones sin prefers-reduced-motion"))
    return res


def urls_css(css):
    css = sin_comentarios(css)
    urls = [m.group(2) for m in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", css)]
    urls += [m.group(1) for m in re.finditer(r"@import\s+['\"]([^'\"]+)['\"]", css)]
    return [u.strip() for u in urls if u.strip()]


# ---------------------------------------------------------------- HTML
class Pagina(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None; self.title = ""; self.encabezados = []; self.imgs = []; self.recursos = []; self.enlaces = []
        self.ids = set(); self.estilos = []; self.estilos_attr = []; self.scripts = []; self.texto = []
        self.viewport = False; self._en = []; self._buf = {}; self.emojis = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        l = self.getpos()[0]
        self._en.append(tag)
        if tag == "html":
            self.lang = a.get("lang")
        if "id" in a: self.ids.add(a["id"])
        if tag == "a" and "name" in a: self.ids.add(a["name"])
        if "style" in a: self.estilos_attr.append((a["style"], l))
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.encabezados.append((int(tag[1]), l)); self._buf[tag] = ""
        if tag == "button": self._buf[tag] = ""
        if tag == "img":
            self.imgs.append(("alt" in a, a.get("alt", ""), a.get("src", ""), l))
            if a.get("src"): self.recursos.append((a["src"], l))
            for parte in a.get("srcset", "").split(","):
                if parte.strip(): self.recursos.append((parte.strip().split()[0], l))
        elif tag in ("script", "source", "iframe", "video", "audio", "embed", "track", "input") and a.get("src"):
            if not (tag == "input" and a.get("type") != "image"): self.recursos.append((a["src"], l))
        elif tag == "object" and a.get("data"): self.recursos.append((a["data"], l))
        elif tag == "video" and a.get("poster"): self.recursos.append((a["poster"], l))
        elif tag == "form" and a.get("action"): self.recursos.append((a["action"], l))
        elif tag == "link" and a.get("href"):
            rel = set(a.get("rel", "").lower().split())
            if rel & REL_NAVEGACION and not rel & {"stylesheet", "icon", "preload", "preconnect", "dns-prefetch", "manifest"}:
                self.enlaces.append((a["href"], l))
            else:
                self.recursos.append((a["href"], l))
        elif tag == "a" and a.get("href"): self.enlaces.append((a["href"], l))
        if tag == "meta" and a.get("name", "").lower() == "viewport": self.viewport = True
        if tag == "script": self.scripts.append(["", l, bool(a.get("src"))])
        if tag == "style": self.estilos.append(["", l])

    def handle_endtag(self, tag):
        if tag in self._buf:
            texto = self._buf.pop(tag)
            if EMOJI.search(texto): self.emojis.append((tag, texto.strip()[:30]))
        while self._en and self._en[-1] != tag:
            self._en.pop()
        if self._en: self._en.pop()

    def handle_data(self, d):
        actual = self._en[-1] if self._en else ""
        if actual == "title": self.title += d
        elif actual == "style" and self.estilos: self.estilos[-1][0] += d
        elif actual == "script" and self.scripts: self.scripts[-1][0] += d
        else:
            self.texto.append(d)
            for k in self._buf: self._buf[k] += d


def cargar_permitidos(ruta):
    permitidos = []
    if ruta and ruta.is_file():
        for linea in ruta.read_text(encoding="utf8", errors="ignore").splitlines():
            linea = linea.split("#")[0].strip().lower()
            if linea: permitidos.append(linea)
    return permitidos


def host_permitido(host, permitidos):
    return any(host == p or (p.startswith("*.") and host.endswith(p[1:])) for p in permitidos)


def clasificar_ref(ref):
    """('local', ruta_sin_query, fragmento) | ('remoto', host, '') | ('omitir', '', '')."""
    ref = ref.strip()
    if not ref or ref.startswith(("data:", "mailto:", "tel:", "sms:", "about:", "blob:")):
        return "omitir", "", ""
    if ref.lower().startswith("javascript:"):
        return "js", "", ""
    partes = urlsplit(ref)
    if partes.scheme in ("http", "https") or ref.startswith("//"):
        return "remoto", (partes.hostname or "").lower(), ""
    if partes.scheme:
        return "omitir", "", ""
    return "local", unquote(partes.path), partes.fragment


def resolver_local(raiz, pagina, ruta):
    base = raiz if ruta.startswith("/") else pagina.parent
    destino = (base / ruta.lstrip("/")).resolve()
    try:
        destino.relative_to(raiz.resolve())
    except ValueError:
        return None
    if destino.is_dir(): destino = destino / "index.html"
    return destino


def comprobar_pagina(raiz, ruta, permitidos, lim, titulos):
    rel = ruta.relative_to(raiz)
    res = []
    texto_html = ruta.read_text(encoding="utf8", errors="replace")
    p = Pagina(); p.feed(texto_html); p.close()
    if not p.lang or not re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*", p.lang.strip()):
        res.append(hallazgo(ERROR, "lang", rel, "falta <html lang> o no es un código BCP 47 válido"))
    t = " ".join(p.title.split())
    if not t: res.append(hallazgo(ERROR, "title", rel, "falta <title> o está vacío"))
    elif t in titulos: res.append(hallazgo(AVISO, "title-repetido", rel, f"el título «{t}» se repite en {titulos[t]}"))
    else: titulos[t] = str(rel)
    if not p.viewport: res.append(hallazgo(AVISO, "viewport", rel, "falta <meta name=\"viewport\">: la página no se adaptará a móviles"))
    h1 = [l for n, l in p.encabezados if n == 1]
    if len(h1) != 1: res.append(hallazgo(ERROR, "h1", rel, f"debe haber exactamente una h1 (hay {len(h1)})"))
    previo = 0
    for n, l in p.encabezados:
        if previo and n > previo + 1:
            res.append(hallazgo(ERROR, "encabezados", rel, f"salto de h{previo} a h{n}", l))
        elif not previo and n != 1:
            res.append(hallazgo(AVISO, "encabezados", rel, f"el primer encabezado es h{n}, no h1", l))
        previo = n
    for hay_alt, alt, src, l in p.imgs:
        if not hay_alt: res.append(hallazgo(ERROR, "alt", rel, f"imagen sin atributo alt: {src[:50]}", l))
    for tag, txt in p.emojis:
        res.append(hallazgo(AVISO, "emoji-icono", rel, f"emoji dentro de <{tag}> («{txt}»): usar iconos SVG"))
    texto = " ".join(" ".join(p.texto).split())
    m = RELLENO.search(texto)
    if m: res.append(hallazgo(ERROR, "relleno", rel, f"texto de relleno: «{m.group(0)}»"))
    m = METRICA.search(texto)
    if m: res.append(hallazgo(AVISO, "metrica-inventada", rel, f"cifra tipo marketing sin fuente a revisar: «{m.group(0)}»"))
    # estilos incrustados
    for css, l in [(s[0], s[1]) for s in p.estilos] + [("x{" + s + "}", l) for s, l in p.estilos_attr]:
        res += [dict(h, archivo=f"{rel}", linea=l) for h in comprobar_css_texto(css, rel)]
    # scripts incrustados: trackers
    for cuerpo, l, ext in p.scripts:
        for tr in TRACKERS:
            if tr in cuerpo.lower() or re.search(r"\b(gtag|fbq|_paq)\s*\(", cuerpo):
                dom = tr if tr in cuerpo.lower() else "llamada de analítica"
                res.append(hallazgo(AVISO if host_permitido(tr, permitidos) else ERROR, "tracker", rel, f"script incrustado de seguimiento ({dom}) no declarado", l)); break
    # referencias
    peso = len(texto_html.encode("utf8")); vistos = set()
    if peso > lim["html"]: res.append(hallazgo(ERROR, "peso-html", rel, f"{peso // 1024} KB supera {lim['html'] // 1024} KB"))
    cola = [(r, l, "recurso") for r, l in p.recursos] + [(r, l, "enlace") for r, l in p.enlaces]
    css_pendientes = []
    for ref, l, clase in cola:
        tipo, valor, frag = clasificar_ref(ref)
        if tipo == "js": res.append(hallazgo(AVISO, "javascript-url", rel, "enlace javascript: (no accesible)", l)); continue
        if tipo == "remoto":
            if clase == "recurso":
                trk = next((tr for tr in TRACKERS if tr in (valor + urlsplit(ref).path)), None)
                if trk and not host_permitido(valor, permitidos): res.append(hallazgo(ERROR, "tracker", rel, f"recurso de seguimiento no declarado: {valor}", l))
                elif any(valor.endswith(mk) for mk in MARCADORES): res.append(hallazgo(ERROR, "imagen-marcador", rel, f"imagen de marcador externo: {valor}", l))
                elif not host_permitido(valor, permitidos): res.append(hallazgo(ERROR, "remoto-no-declarado", rel, f"recurso remoto no declarado en sitio.permitidos.txt: {valor}", l))
            continue
        if tipo != "local": continue
        if not valor:
            if frag and frag not in p.ids and frag != "top": res.append(hallazgo(ERROR, "enlace-roto", rel, f"ancla #{frag} no existe en la página", l))
            continue
        destino = resolver_local(raiz, ruta, valor)
        if destino is None: res.append(hallazgo(ERROR, "enlace-roto", rel, f"{ref} sale de la carpeta del sitio", l)); continue
        if not destino.is_file(): res.append(hallazgo(ERROR, "enlace-roto", rel, f"{ref} no existe", l)); continue
        if clase == "recurso" and destino not in vistos:
            vistos.add(destino); peso += destino.stat().st_size
            if destino.suffix.lower() == ".css": css_pendientes.append(destino)
    for css in css_pendientes:
        for u in urls_css(css.read_text(encoding="utf8", errors="replace")):
            tipo, valor, _ = clasificar_ref(u)
            if tipo == "local" and valor:
                d = resolver_local(raiz, css, valor)
                if d and d.is_file() and d not in vistos: vistos.add(d); peso += d.stat().st_size
    if peso > lim["pagina"]: res.append(hallazgo(ERROR, "peso-pagina", rel, f"página con sus recursos locales: {peso // 1024} KB supera {lim['pagina'] // 1024} KB"))
    return res


def comprobar_css_archivo(raiz, ruta, permitidos, lim):
    rel = ruta.relative_to(raiz); css = ruta.read_text(encoding="utf8", errors="replace"); res = []
    if len(css.encode("utf8")) > lim["css"]: res.append(hallazgo(ERROR, "peso-css", rel, f"{len(css.encode('utf8')) // 1024} KB supera {lim['css'] // 1024} KB"))
    res += comprobar_css_texto(css, rel)
    for u in urls_css(css):
        tipo, valor, _ = clasificar_ref(u)
        if tipo == "remoto":
            if any(valor.endswith(mk) for mk in MARCADORES): res.append(hallazgo(ERROR, "imagen-marcador", rel, f"marcador externo: {valor}"))
            elif not host_permitido(valor, permitidos):
                res.append(hallazgo(ERROR, "tracker" if any(t in valor for t in TRACKERS) else "remoto-no-declarado", rel, f"recurso remoto no declarado: {valor}"))
        elif tipo == "local" and valor:
            d = resolver_local(raiz, ruta, valor)
            if d is None or not d.is_file(): res.append(hallazgo(ERROR, "enlace-roto", rel, f"url({u}) no existe"))
    return res


def comprobar_secretos(raiz):
    res = []
    for f in sorted(raiz.rglob("*")):
        if not f.is_file(): continue
        rel = f.relative_to(raiz)
        if f.name == ".env" or f.name.startswith(".env."):
            res.append(hallazgo(ERROR, "secreto", rel, "archivo de entorno dentro del sitio")); continue
        if f.suffix.lower() not in EXT_TEXTO: continue
        for n, linea in enumerate(f.read_text(encoding="utf8", errors="ignore").splitlines(), 1):
            for nombre, rx in SECRETOS:
                if rx.search(linea): res.append(hallazgo(ERROR, "secreto", rel, f"posible {nombre} (valor no mostrado)", n)); break
    return res


def comprobar_marca_ajena(raiz):
    """En la ficha de marca declarada (DISENO.md): marcas reales usadas como referencia a imitar (error) o solo mencionadas (aviso).
    Las líneas que lo niegan («no imitar a …», «prohibido …») no cuentan. Es una búsqueda de texto: no sustituye la revisión humana (punto 16)."""
    res = []
    for f in sorted(raiz.rglob("*")):
        if not f.is_file() or f.name.lower() != "diseno.md": continue
        rel = f.relative_to(raiz)
        for n, linea in enumerate(f.read_text(encoding="utf8", errors="ignore").splitlines(), 1):
            inspirada = RX_INSPIRADO_EN.search(linea)
            marcas = list(RX_MARCA.finditer(linea))
            pos = inspirada.start() if inspirada else (marcas[0].start() if marcas else None)
            if pos is None: continue
            if RX_NEGACION.search(linea[:pos]): continue   # «no imitar a …», «prohibido …»: la línea lo niega
            nombres = ", ".join(sorted({m.group(1) for m in marcas}))
            if inspirada:
                res.append(hallazgo(ERROR, "marca-ajena", rel, f"sistema de diseño «inspirado en» otra marca ({inspirada.group(1)}): prohibido, ni como referencia (ficha propia o genérica sin marca)", n))
            elif RX_IMITACION.search(linea):
                res.append(hallazgo(ERROR, "marca-ajena", rel, f"marca ajena como referencia a imitar ({nombres}): prohibido, ni como referencia (ficha propia o genérica sin marca)", n))
            else:
                res.append(hallazgo(AVISO, "marca-ajena-mencion", rel, f"menciona marca(s) ajena(s) ({nombres}): confirmar que no son referencia de diseño", n))
    return res


def comprobar_licencias(raiz):
    res, lic = [], raiz / "activos" / "LICENCIAS.md"
    activos = [f for f in sorted(raiz.rglob("*")) if f.is_file() and f.suffix.lower() in EXT_MEDIA]
    if not activos: return res
    if not lic.is_file():
        return [hallazgo(ERROR, "licencia-activo", f.relative_to(raiz), "no existe activos/LICENCIAS.md") for f in activos]
    lineas = lic.read_text(encoding="utf8", errors="ignore").splitlines()
    for f in activos:
        propias = [l for l in lineas if f.name.lower() in l.lower()]
        if not propias: res.append(hallazgo(ERROR, "licencia-activo", f.relative_to(raiz), "activo sin línea en activos/LICENCIAS.md"))
        elif not any(re.search(r"licen|cc0|cc-by|\bmit\b|apache|\bofl\b|\bsil\b|propia|dominio p", l, re.I) for l in propias):
            res.append(hallazgo(ERROR, "licencia-activo", f.relative_to(raiz), "la línea del activo no declara licencia"))
    return res


def comprobar_pesos_activos(raiz, lim):
    return [hallazgo(ERROR, "peso-activo", f.relative_to(raiz), f"{f.stat().st_size // 1024} KB supera {lim['img'] // 1024} KB")
            for f in sorted(raiz.rglob("*")) if f.is_file() and f.suffix.lower() in EXT_IMAGEN and f.stat().st_size > lim["img"]]


def verificar(raiz, permitidos_ruta=None, limites=None):
    raiz = pathlib.Path(raiz)
    lim = {"html": 150 * 1024, "css": 100 * 1024, "img": 300 * 1024, "pagina": 1024 * 1024}
    lim.update(limites or {})
    permitidos = cargar_permitidos(permitidos_ruta or raiz / "sitio.permitidos.txt")
    paginas = [f for f in sorted(raiz.rglob("*")) if f.is_file() and f.suffix.lower() in EXT_PAGINA]
    res, titulos = [], {}
    if not paginas: res.append(hallazgo(ERROR, "sin-paginas", ".", "no hay ninguna página .html en la carpeta"))
    for p in paginas: res += comprobar_pagina(raiz, p, permitidos, lim, titulos)
    css_files = [f for f in sorted(raiz.rglob("*.css"))]
    for c in css_files: res += comprobar_css_archivo(raiz, c, permitidos, lim)
    tokens = [c for c in css_files if c.name == "tokens.css"]
    if tokens:
        for t in tokens: res += comprobar_contraste(t.read_text(encoding="utf8", errors="replace"), t.relative_to(raiz))
    else:
        res.append(hallazgo(AVISO, "contraste-sin-tokens", ".", "no hay tokens.css: contraste de color no comprobado"))
    res += comprobar_secretos(raiz) + comprobar_licencias(raiz) + comprobar_pesos_activos(raiz, lim) + comprobar_marca_ajena(raiz)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta"); ap.add_argument("--json", action="store_true"); ap.add_argument("--estricto", action="store_true")
    ap.add_argument("--permitidos"); ap.add_argument("--max-html-kb", type=int); ap.add_argument("--max-css-kb", type=int)
    ap.add_argument("--max-img-kb", type=int); ap.add_argument("--max-pagina-kb", type=int)
    a = ap.parse_args(argv)
    raiz = pathlib.Path(a.carpeta)
    if not raiz.is_dir():
        print(f"No existe la carpeta: {raiz}", file=sys.stderr); return 2
    lim = {k: v * 1024 for k, v in (("html", a.max_html_kb), ("css", a.max_css_kb), ("img", a.max_img_kb), ("pagina", a.max_pagina_kb)) if v}
    res = verificar(raiz, pathlib.Path(a.permitidos) if a.permitidos else None, lim)
    errores = [h for h in res if h["nivel"] == ERROR]; avisos = [h for h in res if h["nivel"] == AVISO]
    if a.json:
        print(json.dumps({"carpeta": str(raiz), "errores": len(errores), "avisos": len(avisos), "hallazgos": res}, ensure_ascii=False, indent=2))
    else:
        for h in res:
            donde = f"{h['archivo']}" + (f":{h['linea']}" if h["linea"] else "")
            print(f"[{h['nivel'].upper()}] {h['codigo']} · {donde} · {h['mensaje']}")
        print(f"\n{len(errores)} errores, {len(avisos)} avisos. Lo que NO comprueba (rendimiento real, lector de pantalla, teclado, texto, legales): ver estandares/diseno-web.md §5.")
    return 1 if errores or (a.estricto and avisos) else 0


if __name__ == "__main__":
    sys.exit(main())
