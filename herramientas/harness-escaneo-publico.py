#!/usr/bin/env python3
"""Escaneo de publicación del harness (SOLO LECTURA, solo biblioteca estándar).

Busca, antes de hacer público un repositorio, lo que no debe salir:
  secreto          claves y tokens (patrones conocidos, claves privadas, JWT, conexiones con contraseña, asignaciones)
  infraestructura  cuentas de 12 dígitos con contexto, ARNs, IP privadas/públicas, hosts internos
  persona          correos con dominio real; nombres de una lista opcional (--lista-nombres / .nombres.txt)
  prohibido        términos de empresa/proyecto de la lista (--lista-prohibidos / .prohibidos.txt)
  archivo          archivos que no deben publicarse (.env*, *.pem, *.sql, *.tfstate, ...)
Revisa todo el árbol (sin .git) y, aparte, el historial (`git log -p --all`, solo líneas añadidas,
limitado por --max-commits y --max-bytes), porque lo que está en el historial también se publicaría.
NUNCA imprime el valor completo: solo una pista enmascarada. Una línea con `escaneo-publico: ignorar` se omite.
Uso: harness-escaneo-publico.py [raiz] [--json] [--lista-prohibidos F] [--lista-nombres F] [--max-commits N] [--max-bytes N] [--sin-historial]
Salida: 0 sin hallazgos; 1 con hallazgos; 2 si --exigir-listas y falta la lista de prohibidos.
"""
import argparse, fnmatch, json, pathlib, re, subprocess, sys

EXCLUIR_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
MAX_ARCHIVO = 2_000_000
IGNORAR = "escaneo-publico: ignorar"
PLACEHOLDER = re.compile(r"^(<.*>|\$\{.*\}|\$[A-Za-z_].*|%.*%|\{\{.*\}\}|x+|\*+|\.+|-+|_+|n/?a|none|null|nil|true|false|"
                         r"changeme|change-me|example.*|ejemplo.*|dummy.*|sample.*|placeholder.*|your[-_ ].*|tu[-_ ].*|"
                         r"mi[-_ ]?(clave|secreto|token).*|secret|password|token|contrase.a|clave|valor|value|test|"
                         r"process\.env.*|os\.environ.*|env\..*|getenv.*|redacted|oculto|enmascarado)$", re.I)
NOMBRES_ARCHIVO = [".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks", "id_rsa", "id_ed25519", "*.sql", "*.dump",
                   "*.tfstate", "*.tfstate.*", "*.sqlite", "*.sqlite3", "*.kdbx", "credentials", ".netrc", ".npmrc", ".pypirc"]
PERMITIDOS_ARCHIVO = [".env.example", ".env.sample", ".env.template", ".env.dist", "*.example", "*.sample", "*.template"]
DOMINIOS_FICTICIOS = re.compile(r"(^|\.)(example\.(com|org|net)|example|test|invalid|localhost|local|localdomain)$|noreply|no-reply|"
                                r"users\.noreply\.github\.com$", re.I)
RE_EMAIL = re.compile(r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)\b")
RE_IP = re.compile(r"(?<![\d.])((?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})(?![\d.]|\.\d)")
RE_CTX_CUENTA = re.compile(r"(account|cuenta|aws|acct|iam|arn|profile|perfil)", re.I)
RE_DOCE = re.compile(r"(?<![\d.])(\d{12})(?![\d.])")

# (clase, subtipo, regex, grupo del valor)
PATRONES = [
    ("secreto", "aws-access-key", re.compile(r"\b((?:AKIA|ASIA)[0-9A-Z]{16})\b"), 1),
    ("secreto", "github-token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b"), 1),
    ("secreto", "slack-token", re.compile(r"\b(xox[abprs]-[A-Za-z0-9-]{10,})\b"), 1),
    ("secreto", "api-key-sk", re.compile(r"\b(sk-[A-Za-z0-9_-]{20,})\b"), 1),
    ("secreto", "google-api-key", re.compile(r"\b(AIza[0-9A-Za-z_-]{35})\b"), 1),
    ("secreto", "clave-privada", re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----)"), 1),
    ("secreto", "jwt", re.compile(r"\b(eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})\b"), 1),
    ("secreto", "conexion-con-contraseña", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@'\"<>]+:([^\s@/'\"<>]{3,})@[^\s'\"<>]+", re.I), 1),
    ("secreto", "asignacion-secreta", re.compile(
        r"(?i)\b[\w.-]*(?:password|passwd|pwd|secret|token|api[_-]?key|private[_-]?key|contrase[nñ]a|clave)[\w.-]*"
        r"[\"']?\s*(?:=|:|=>)\s*[\"']?([^\s\"',;`)]{6,})"), 1),
    ("infraestructura", "arn", re.compile(r"\b(arn:aws[a-z-]*:[a-z0-9-]+:[a-z0-9-]*:\d{12}:[^\s\"'<>]+)"), 1),
    ("infraestructura", "host-aws", re.compile(r"\b([a-z0-9.-]+\.(?:rds|elb|compute|execute-api)\.[a-z0-9.-]*amazonaws\.com)\b", re.I), 1),
    ("infraestructura", "host-interno", re.compile(r"\b([a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:internal|corp|intranet|lan|home\.arpa))\b", re.I), 1),
]


def enmascarar(v):
    v = str(v)
    return "***" if len(v) <= 4 else f"{v[:2]}***({len(v)} car.)"


def enmascarar_correo(local, dom):
    return f"{local[:1]}***@{dom}"


def es_trivial(v):
    v = v.strip("\"'`")
    if PLACEHOLDER.match(v) or "(" in v or ")" in v or v.startswith(("http", "/", "./")):
        return True
    if len(set(v)) <= 2:
        return True
    return False


def clase_ip(ip):
    o = [int(x) for x in ip.split(".")]
    if o[0] in (0, 127, 255) or o[0] >= 224 or o[:3] in ([192, 0, 2], [198, 51, 100], [203, 0, 113]):
        return None  # loopback, difusión, rangos reservados para documentación
    if o[0] == 10 or (o[0] == 172 and 16 <= o[1] <= 31) or (o[0] == 192 and o[1] == 168) or (o[0] == 169 and o[1] == 254):
        return "IP privada"
    return "IP pública"


def escanear_linea(texto, nombres=(), prohibidos=()):
    """Devuelve [(clase, pista)] para una línea. Nunca incluye el valor completo."""
    if IGNORAR in texto:
        return []
    r = []
    for clase, sub, rx, g in PATRONES:
        for m in rx.finditer(texto):
            v = m.group(g)
            if sub == "asignacion-secreta" and es_trivial(v):
                continue
            if sub == "conexion-con-contraseña" and es_trivial(v):
                continue
            r.append((clase, f"{sub}: {enmascarar(v)}"))
    for m in RE_IP.finditer(texto):
        c = clase_ip(m.group(1))
        if c:
            r.append(("infraestructura", f"{c}: {enmascarar(m.group(1))}"))
    if RE_CTX_CUENTA.search(texto):
        for m in RE_DOCE.finditer(texto):
            r.append(("infraestructura", f"cuenta de 12 dígitos: {enmascarar(m.group(1))}"))
    for m in RE_EMAIL.finditer(texto):
        if not DOMINIOS_FICTICIOS.search(m.group(2)):
            r.append(("persona", f"correo: {enmascarar_correo(m.group(1), m.group(2))}"))
    bajo = texto.lower()
    for i, n in enumerate(nombres):
        if re.search(r"\b" + re.escape(n.lower()) + r"\b", bajo):
            r.append(("persona", f"nombre #{i + 1} de la lista: {enmascarar(n)}"))
    for i, t in enumerate(prohibidos):
        if t.lower() in bajo:
            r.append(("prohibido", f"término #{i + 1} de la lista: {enmascarar(t)}"))
    return r


def archivo_prohibido(nombre):
    n = nombre.lower()
    if any(fnmatch.fnmatch(n, p) for p in PERMITIDOS_ARCHIVO):
        return False
    return any(fnmatch.fnmatch(n, p) for p in NOMBRES_ARCHIVO)


def leer_lista(ruta):
    if not ruta or not ruta.is_file():
        return None
    out = []
    for l in ruta.read_text(encoding="utf8", errors="ignore").splitlines():
        l = l.strip()
        if l and not l.startswith("#"):
            out.append(l)
    return out


CLASES_EXCEPTUABLES = {"secreto", "persona", "cuenta", "ip", "archivo"}


def leer_excepciones(ruta):
    """`.permitidos.txt`: una excepción por línea, `glob-de-ruta | clase | motivo`. Devuelve (lista, errores).
    El motivo es obligatorio (mín. 10 caracteres) y la clase `prohibido` (empresa/proyecto) nunca se puede exceptuar."""
    if not ruta or not ruta.is_file():
        return [], []
    out, err = [], []
    for n, l in enumerate(ruta.read_text(encoding="utf8", errors="ignore").splitlines(), 1):
        l = l.strip()
        if not l or l.startswith("#"):
            continue
        partes = [x.strip() for x in l.split("|", 2)]
        if len(partes) != 3 or not all(partes):
            err.append(f"{ruta.name}:{n}: formato `glob | clase | motivo` (los tres son obligatorios)")
        elif partes[1] == "prohibido":
            err.append(f"{ruta.name}:{n}: la clase `prohibido` (empresa/proyecto) no se puede exceptuar")
        elif partes[1] not in CLASES_EXCEPTUABLES:
            err.append(f"{ruta.name}:{n}: clase `{partes[1]}` desconocida (válidas: {', '.join(sorted(CLASES_EXCEPTUABLES))})")
        elif len(partes[2]) < 10:
            err.append(f"{ruta.name}:{n}: el motivo es demasiado corto para justificar la excepción")
        else:
            out.append({"glob": partes[0], "clase": partes[1], "motivo": partes[2], "usos": 0})
    return out, err


def aplicar_excepciones(hallazgos, excepciones):
    """Separa (vigentes, aceptados). Un hallazgo se acepta si coincide ruta y clase con una excepción."""
    vigentes, aceptados = [], []
    for h in hallazgos:
        e = next((x for x in excepciones if x["clase"] == h["clase"] and fnmatch.fnmatch(h["archivo"], x["glob"])), None)
        if e:
            e["usos"] += 1
            aceptados.append(h)
        else:
            vigentes.append(h)
    return vigentes, aceptados


def hallazgo(ambito, clase, archivo, linea, pista, commit=None):
    return {"ambito": ambito, "clase": clase, "archivo": archivo, "linea": linea, "commit": commit, "pista": pista}


def escanear_arbol(raiz, nombres, prohibidos):
    hs = []
    for p in sorted(raiz.rglob("*")):
        rel = p.relative_to(raiz)
        if set(rel.parts) & EXCLUIR_DIRS or not p.is_file() or p.is_symlink():
            continue
        if archivo_prohibido(p.name):
            hs.append(hallazgo("arbol", "archivo", str(rel), 0, f"archivo que no debe publicarse ({p.name.split('.')[-1] if '.' in p.name else p.name})"))
            continue
        try:
            if p.stat().st_size > MAX_ARCHIVO:
                continue
            datos = p.read_bytes()
        except OSError:
            continue
        if b"\0" in datos[:4096]:
            continue
        for n, linea in enumerate(datos.decode("utf8", errors="ignore").splitlines(), 1):
            for clase, pista in escanear_linea(linea, nombres, prohibidos):
                hs.append(hallazgo("arbol", clase, str(rel), n, pista))
    return hs


def git(raiz, *args, limite=None):
    try:
        p = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    return p.stdout[:limite] if limite else p.stdout


def escanear_historial(raiz, nombres, prohibidos, max_commits, max_bytes):
    """Devuelve (hallazgos, info). Solo líneas añadidas; deduplica por (clase, archivo, pista)."""
    info = {"disponible": False, "commits": 0, "truncado": False}
    if git(raiz, "rev-parse", "--git-dir") is None:
        return [], info
    info["disponible"] = True
    hs, vistos = [], set()

    def agregar(h):
        k = (h["clase"], h["archivo"], h["pista"])
        if k not in vistos:
            vistos.add(k); hs.append(h)

    meta = git(raiz, "log", "--all", f"--max-count={max_commits}", "--format=%h%x09%ae%x09%ce")
    for l in (meta or b"").decode("utf8", errors="ignore").splitlines():
        sha, *mails = l.split("\t")
        for mail in set(mails):
            m = RE_EMAIL.fullmatch(mail)
            if m and not DOMINIOS_FICTICIOS.search(m.group(2)):
                agregar(hallazgo("historial", "persona", "(metadatos del commit)", 0, f"correo de autor/committer: {enmascarar_correo(m.group(1), m.group(2))}", sha))
    out = git(raiz, "log", "-p", "--all", "--no-color", "--no-ext-diff", f"--max-count={max_commits}", "--format=@@COMMIT %h", limite=max_bytes + 1)
    if out is None:
        return hs, info
    if len(out) > max_bytes:
        info["truncado"] = True; out = out[:max_bytes]
    commit, archivo, n = None, None, 0
    for raw in out.decode("utf8", errors="ignore").splitlines():
        if raw.startswith("@@COMMIT "):
            commit = raw.split()[1]; info["commits"] += 1; archivo = None; continue
        if raw.startswith("+++ "):
            archivo = raw[6:] if raw.startswith("+++ b/") else None
            if archivo and archivo_prohibido(pathlib.PurePosixPath(archivo).name):
                agregar(hallazgo("historial", "archivo", archivo, 0, "archivo que no debe publicarse (existió en el historial)", commit))
            continue
        if raw.startswith("@@ "):
            m = re.search(r"\+(\d+)", raw); n = int(m.group(1)) - 1 if m else 0; continue
        if raw.startswith("+") and not raw.startswith("+++") and archivo:
            n += 1
            for clase, pista in escanear_linea(raw[1:], nombres, prohibidos):
                agregar(hallazgo("historial", clase, archivo, n, pista, commit))
        elif raw.startswith(" "):
            n += 1
    return hs, info


def main(argv=None):
    ap = argparse.ArgumentParser(description="Escaneo de publicación (solo lectura)")
    ap.add_argument("raiz", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--lista-prohibidos")
    ap.add_argument("--lista-nombres")
    ap.add_argument("--max-commits", type=int, default=2000)
    ap.add_argument("--max-bytes", type=int, default=50_000_000)
    ap.add_argument("--sin-historial", action="store_true")
    ap.add_argument("--lista-permitidos", help="excepciones revisadas por una persona: `glob | clase | motivo` por línea (por defecto .permitidos.txt)")
    ap.add_argument("--exigir-listas", action="store_true", help="sale con 2 si no hay lista de prohibidos")
    a = ap.parse_args(argv)
    raiz = pathlib.Path(a.raiz).resolve()
    prohibidos = leer_lista(pathlib.Path(a.lista_prohibidos) if a.lista_prohibidos else raiz / ".prohibidos.txt")
    nombres = leer_lista(pathlib.Path(a.lista_nombres) if a.lista_nombres else raiz / ".nombres.txt")
    avisos = []
    if prohibidos is None:
        avisos.append("NO COMPROBADA la clase 'prohibido' (referencias a empresa/proyecto): falta --lista-prohibidos o .prohibidos.txt")
    if nombres is None:
        avisos.append("sin lista de nombres (--lista-nombres / .nombres.txt): solo se detectan correos, no nombres propios")
    hs = escanear_arbol(raiz, nombres or [], prohibidos or [])
    hh, info = ([], {"disponible": False, "commits": 0, "truncado": False}) if a.sin_historial else \
        escanear_historial(raiz, nombres or [], prohibidos or [], a.max_commits, a.max_bytes)
    if a.sin_historial:
        avisos.append("historial NO escaneado (--sin-historial)")
    elif not info["disponible"]:
        avisos.append("no es un repositorio git: historial no escaneado")
    if info["truncado"]:
        avisos.append(f"historial truncado a {a.max_bytes} bytes / {a.max_commits} commits: el escaneo es parcial")
    excepciones, errores = leer_excepciones(pathlib.Path(a.lista_permitidos) if a.lista_permitidos else raiz / ".permitidos.txt")
    if errores:
        print("LISTA DE PERMITIDOS INVÁLIDA:", *errores, sep="\n  ", file=sys.stderr)
        return 2
    hs, acep_a = aplicar_excepciones(hs, excepciones)
    hh, acep_h = aplicar_excepciones(hh, excepciones)
    todos = hs + hh
    res = {"raiz": str(raiz), "arbol": hs, "historial": hh, "historial_info": info, "avisos": avisos, "total": len(todos),
           "excepciones_aceptadas": [{k: e[k] for k in ("glob", "clase", "motivo", "usos")} for e in excepciones]}
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for titulo, lista in (("ÁRBOL DE TRABAJO", hs), ("HISTORIAL GIT (ya estaría público)", hh)):
            print(f"== {titulo}: {len(lista)} hallazgo(s)")
            for h in lista:
                donde = f"{h['archivo']}:{h['linea']}" if h["linea"] else h["archivo"]
                c = f" [commit {h['commit']}]" if h["commit"] else ""
                print(f"  {donde}{c}  {h['clase']}  {h['pista']}")
        if excepciones:
            print(f"== EXCEPCIONES REVISADAS POR UNA PERSONA: {len(acep_a) + len(acep_h)} hallazgo(s) aceptado(s)")
            for e in excepciones:
                print(f"  {e['glob']} | {e['clase']} | {e['usos']} uso(s) | {e['motivo']}")
                if not e["usos"]:
                    avisos.append(f"excepción sin uso (¿sobra?): {e['glob']} | {e['clase']}")
        for av in avisos:
            print(f"AVISO: {av}")
        print("RESULTADO:", "LIMPIO" if not todos else f"{len(todos)} hallazgo(s): NO publicar")
    if todos:
        return 1
    return 2 if (a.exigir_listas and prohibidos is None) else 0


if __name__ == "__main__":
    sys.exit(main())
