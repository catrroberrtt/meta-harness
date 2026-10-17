#!/usr/bin/env python3
"""Refresco automático del conocimiento: baja lo nuevo de las fuentes y mide qué parte ya está digerida. Sin IA, solo lectura.

<!-- tipo: herramienta · capa: 4 -->

Qué resuelve: lo nuevo que existe en el código, en la documentación (wiki) y en los tickets no se ve solo. Si nadie lo mira se concluye
«no está documentado» sin haberlo buscado. Esta herramienta lo baja a un espejo local de texto (FUERA de cualquier repositorio), cuenta
cuántas veces nombra la base de conocimiento cada módulo del código y escribe un archivo de novedades con lo que todavía no está digerido.
La digestión (escribir o actualizar la ficha) la hace una persona o una sesión con IA a partir del espejo; leer el espejo es rápido y sin red.

Garantías:
  - Solo lee: git fetch, GET a la wiki y a los tickets. Nunca escribe en una fuente, nunca hace commit ni push.
  - El espejo, la marca de la última corrida y el archivo de novedades viven donde diga la configuración, no en el árbol del harness.
  - Las credenciales se leen de un archivo con permisos del usuario (variables de entorno con nombre configurable); nunca se imprimen.
  - Cada parte es opcional: sin `[wiki]`/`[tickets]` solo mide el código; sin red sigue con lo que hay.

Configuración (archivo del usuario, no se versiona): ~/.config/meta-harness/refresco.toml o la variable HARNESS_REFRESCO. Ejemplo:

  [conocimiento]
  raiz = "~/proyectos/conocimiento"          # carpeta de fichas .md ya digeridas
  salida = "~/proyectos/conocimiento/novedades.md"
  espejo = "~/.local/share/meta-harness/espejo"
  estado = "~/.local/state/meta-harness/refresco.json"

  [codigo]
  raiz = "~/proyectos"                       # se buscan repositorios git hasta `profundidad` niveles
  profundidad = 3
  remoto = "github\\.com[:/]mi-organizacion/" # solo repos cuyo `origin` coincide (regex); vacío = todos
  ramas = ["origin/qas", "origin/main"]      # primera que exista
  [[codigo.reglas]]                          # qué cuenta como «pieza» de cada repo
  repo = "^api-"                             # regex sobre el nombre de la carpeta
  tipo = "módulo"
  modo = "subcarpetas"                       # subcarpetas | archivos | repo
  ruta = "src/modules"
  [[codigo.reglas]]
  repo = "^fn-"
  tipo = "función"
  modo = "repo"

  [wiki]                                     # Confluence Cloud (opcional)
  url = "https://mi-sitio.atlassian.net"
  credenciales = "~/.config/mi-wiki/token.env"
  var_correo = "ATLASSIAN_EMAIL"
  var_token = "<NOMBRE-DE-LA-VARIABLE>"

  [tickets]                                  # Jira Cloud, mismas credenciales que [wiki] si no se indican otras (opcional)
  url = "https://mi-sitio.atlassian.net"

  [sellos]                                   # opcional: comando que imprime JSON {"viejas": [[ficha, [motivos]]], "al_dia": [], "sin_sello": 0}
  comando = ["python3", "scripts/sellos.py", "estado", "--json"]

Uso:
  harness-refrescar.py [--config RUTA]                   corrida normal (incremental; la del temporizador)
  harness-refrescar.py --desde 30                        primera vez o recuperación: últimos 30 días
  harness-refrescar.py --sin-red                         solo la parte de código
  harness-refrescar.py --buscar TEMA                     busca en el espejo local (sin red)
  harness-refrescar.py --simulacro                       calcula y muestra el resumen sin escribir el archivo de novedades
Salida: 0 bien · 2 configuración que falta o inválida.

El archivo de novedades usa secciones `## título` con una viñeta `- ` por pendiente: es el contrato que lee `hooks/plantillas/aviso-novedades.sh.tpl`.
"""
import argparse, base64, html, json, os, pathlib, re, subprocess, sys, time, tomllib, urllib.parse, urllib.request


def _ruta(valor):
    return pathlib.Path(os.path.expanduser(valor)) if valor else None


def cargar_config(arg):
    ruta = _ruta(arg or os.environ.get("HARNESS_REFRESCO") or "~/.config/meta-harness/refresco.toml")
    if not ruta.is_file():
        sys.exit(f"Falta la configuración: {ruta} (ver el ejemplo en la cabecera de este archivo)")
    cfg = tomllib.loads(ruta.read_text(encoding="utf8"))
    c = cfg.get("conocimiento") or {}
    for clave in ("raiz", "salida", "espejo", "estado"):
        if not c.get(clave):
            sys.exit(f"Falta [conocimiento].{clave} en {ruta}")
    return cfg


def leer_json(ruta, defecto):
    try:
        return json.loads(pathlib.Path(ruta).read_text(encoding="utf8"))
    except Exception:
        return defecto


def guardar_json(ruta, obj):
    ruta = pathlib.Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf8")


# ───────────────────────────── conocimiento digerido ─────────────────────────────
def corpus_conocimiento(raiz):
    """Texto en minúsculas de las fichas ya digeridas."""
    partes = []
    for p in pathlib.Path(raiz).rglob("*.md"):
        try:
            partes.append(p.read_text(encoding="utf8", errors="replace").lower())
        except OSError:
            pass
    return "\n".join(partes)


def menciones(corpus, nombre):
    return len(re.findall(r"(?<![a-z0-9-])" + re.escape(nombre.lower()) + r"(?![a-z0-9-])", corpus))


# ───────────────────────────── código ─────────────────────────────
def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True).stdout


def repos(cfg_codigo):
    raiz = _ruta(cfg_codigo["raiz"])
    patron = re.compile(cfg_codigo.get("remoto") or ".", re.I)
    prof = int(cfg_codigo.get("profundidad", 3))
    hallados = []
    for actual, dirs, _ in os.walk(raiz):
        if len(pathlib.Path(actual).relative_to(raiz).parts) > prof:
            dirs[:] = []
            continue
        if ".git" in dirs:
            dirs[:] = []
            url = git(actual, "remote", "get-url", "origin").strip()
            if url and patron.search(url):
                hallados.append(pathlib.Path(actual))
        else:
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git")]
    # un solo clon por nombre de repo: las copias de trabajo (worktrees) repiten el nombre con un sufijo
    vistos, unicos = set(), []
    for r in sorted(hallados, key=lambda p: len(p.name)):
        origen = re.sub(r"[-_.](qas|work|wt|tmp|copia)\w*$", "", r.name)
        if origen not in vistos:
            vistos.add(origen)
            unicos.append(r)
    return unicos


def parte_codigo(cfg_codigo, corpus, traer=True):
    reglas = [(re.compile(r["repo"]), r) for r in cfg_codigo.get("reglas", [])]
    filas = []
    for repo in repos(cfg_codigo):
        regla = next((r for pat, r in reglas if pat.search(repo.name)), None)
        if not regla:
            continue
        if traer:
            subprocess.run(["git", "-C", str(repo), "fetch", "-q", "origin"], capture_output=True, timeout=120)
        rama = next((b for b in cfg_codigo.get("ramas", ["origin/main"]) if git(repo, "rev-parse", "--verify", "-q", b).strip()), None)
        if not rama:
            continue
        modo, ruta, tipo = regla.get("modo", "repo"), regla.get("ruta", "."), regla.get("tipo", "pieza")
        if modo == "repo":
            filas.append((repo.name, tipo, repo.name, menciones(corpus, repo.name)))
        elif modo == "subcarpetas":
            for nombre in git(repo, "ls-tree", "-d", "--name-only", f"{rama}:{ruta}").split():
                filas.append((repo.name, tipo, nombre, menciones(corpus, nombre)))
        elif modo == "archivos":
            patron = re.compile(regla.get("patron", r"([^/]+)\.\w+$"))
            for p in git(repo, "ls-tree", "-r", "--name-only", rama).split("\n"):
                m = patron.search(p)
                if m and (ruta == "." or p.startswith(ruta.rstrip("/") + "/")):
                    filas.append((repo.name, tipo, m.group(1), menciones(corpus, m.group(1))))
    return filas


# ───────────────────────────── wiki y tickets (Atlassian Cloud) ─────────────────────────────
def a_texto(storage):
    t = re.sub(r"<h([1-6])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", storage)
    t = re.sub(r"</(p|tr|h[1-6]|div)>|<br\s*/?>", "\n", t)
    t = re.sub(r"<li[^>]*>", "\n- ", t)
    t = re.sub(r"</t[dh]>", " | ", t)
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\n{3,}", "\n\n", html.unescape(t)).strip()


class Atlassian:
    def __init__(self, url, credenciales, var_correo, var_token):
        env = {}
        for linea in _ruta(credenciales).read_text(encoding="utf8").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                k, v = linea.split("=", 1)
                env[k.strip().removeprefix("export ").strip()] = v.strip().strip("\"'")
        self.url = url.rstrip("/")
        self.auth = "Basic " + base64.b64encode(f"{env[var_correo]}:{env[var_token]}".encode()).decode()

    def get(self, ruta):
        try:
            req = urllib.request.Request(self.url + ruta, headers={"Authorization": self.auth, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            return None


def parte_wiki(api, espejo, ultimo, desde_dias, tope):
    desde = ultimo.get("wiki_desde") or time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() - desde_dias * 86400))
    cql = urllib.parse.quote(f'type=page AND lastmodified >= "{desde}" ORDER BY lastmodified DESC')
    ruta = f"/wiki/rest/api/content/search?limit=50&expand=version,space&cql={cql}"
    indice = leer_json(espejo / "indice.json", {})
    nuevos, total = [], 0
    while ruta and total < tope:
        d = api.get(ruta)
        if not d:
            break
        for r in d.get("results", []):
            total += 1
            pid, ver = r["id"], (r.get("version") or {}).get("number")
            if indice.get(pid, {}).get("version") == ver:
                continue
            p = api.get(f"/wiki/api/v2/pages/{pid}?body-format=storage")
            if not p:
                continue
            esp = (r.get("space") or {}).get("key", "-")
            texto = a_texto(((p.get("body") or {}).get("storage") or {}).get("value", ""))
            (espejo / "wiki").mkdir(parents=True, exist_ok=True)
            (espejo / "wiki" / f"{pid}.md").write_text(f"# {r['title']}\n\n_espacio {esp} · versión {ver} · id {pid}_\n\n{texto}\n", encoding="utf8")
            indice[pid] = {"titulo": r["title"], "espacio": esp, "version": ver, "bajada": time.strftime("%F")}
            nuevos.append(pid)
        sig = (d.get("_links") or {}).get("next")
        # el enlace `next` viene relativo al contexto /wiki; sin ese prefijo la segunda página nunca se pedía
        ruta = ("/wiki" + sig if sig and not sig.startswith("/wiki") else sig) if sig else None
        time.sleep(0.2)
    guardar_json(espejo / "indice.json", indice)
    if total < tope:  # la marca solo avanza si se recorrió todo; si se cortó por el tope, la próxima corrida retoma
        ultimo["wiki_desde"] = time.strftime("%Y-%m-%d %H:%M", time.gmtime())
    return indice, nuevos


def parte_tickets(api, espejo, desde_dias):
    previo = leer_json(espejo / "tickets.json", {})
    cambios, token = [], None
    jql = urllib.parse.quote(f"updated >= -{desde_dias}d ORDER BY updated DESC")
    for _ in range(60):
        ruta = f"/rest/api/3/search/jql?maxResults=100&fields=summary,status,issuetype,updated&jql={jql}"
        if token:
            ruta += "&nextPageToken=" + token
        d = api.get(ruta) or {}
        for i in d.get("issues", []):
            f = i["fields"]
            estado = f["status"]["name"]
            if previo.get(i["key"], {}).get("estado") != estado:
                cambios.append((i["key"], estado, f["summary"][:90]))
            previo[i["key"]] = {"estado": estado, "resumen": f["summary"], "tipo": f["issuetype"]["name"], "actualizado": f["updated"]}
        token = d.get("nextPageToken")
        if not token or d.get("isLast"):
            break
        time.sleep(0.2)
    guardar_json(espejo / "tickets.json", previo)
    return cambios


# ───────────────────────────── informe ─────────────────────────────
def citada(titulo, pid, corpus):
    return pid in corpus or titulo.lower()[:60] in corpus


def buscar(espejo, tema):
    t, hay = tema.lower(), False
    for f in sorted((espejo / "wiki").glob("*.md")) if (espejo / "wiki").is_dir() else []:
        txt = f.read_text(encoding="utf8")
        n = txt.lower().count(t)
        if n:
            hay = True
            print("%3d  %s  %s" % (n, f.stem, txt.split("\n", 1)[0][2:90]))
    if not hay:
        print("(nada en el espejo local; puede no haberse bajado aún: correr sin --buscar o con --desde N)")


def sellos(cfg):
    cmd = (cfg.get("sellos") or {}).get("comando")
    if not cmd:
        return {}
    try:
        return json.loads(subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout or "{}")
    except Exception:
        return {}


def lista(items, formato, vacio="_(ninguno)_", tope=None):
    filas = [formato(i) for i in (items[:tope] if tope else items)]
    return ["- " + f for f in filas] or [vacio]


def construir_informe(sin, poco, sin_citar, cambios, viejas, sel):
    L = ["# Novedades sin digerir", "",
         f"> Generado por `harness-refrescar.py` (sin IA, solo lectura); no se edita a mano. Hecho: {time.strftime('%F %H:%M')}.",
         "> Lo que sigue existe en el código, la wiki o los tickets y la base de conocimiento aún NO lo explica. Digerir = leer el espejo y escribir o actualizar la ficha.", ""]
    if sel:
        L += [f"## Fichas viejas: su fuente cambió desde que se escribieron: {len(viejas)}", ""]
        L += lista(viejas, lambda r: f"`{r[0]}` · {'; '.join(r[1])}", f"_(ninguna; {len(sel.get('al_dia', []))} al día, {sel.get('sin_sello', 0)} sin sello)_") + [""]
    L += ["## Código sin ficha (0 menciones)", ""] + lista(sin, lambda f: f"`{f[0]}` · {f[1]} `{f[2]}`") + [""]
    L += ["## Código casi sin ficha (1 mención)", ""] + lista(poco, lambda f: f"`{f[0]}` · {f[1]} `{f[2]}`") + [""]
    L += [f"## Páginas de la wiki bajadas y sin citar (últimos 30 días): {len(sin_citar)} en total, se listan 60", ""]
    L += lista(sorted(sin_citar, key=lambda x: x[1]["titulo"]), lambda x: f"{x[0]} · {x[1]['espacio']} · {x[1]['titulo'][:100]}", tope=60) + [""]
    L += ["## Tickets con cambio de estado desde la última corrida", ""] + lista(cambios, lambda c: "%s · %s · %s" % c, tope=60) + [""]
    return L


def main(argv=None):
    ap = argparse.ArgumentParser(description="Refresco automático del conocimiento (sin IA, solo lectura)")
    ap.add_argument("--config")
    ap.add_argument("--desde", type=int, default=7)
    ap.add_argument("--buscar")
    ap.add_argument("--sin-red", action="store_true")
    ap.add_argument("--simulacro", action="store_true")
    ap.add_argument("--tope", type=int, default=200)
    a = ap.parse_args(argv)
    cfg = cargar_config(a.config)
    c = cfg["conocimiento"]
    espejo = _ruta(c["espejo"])
    if a.buscar:
        return buscar(espejo, a.buscar) or 0
    estado_ruta = _ruta(c["estado"])
    ultimo = leer_json(estado_ruta, {})
    corpus = corpus_conocimiento(_ruta(c["raiz"]))
    filas = parte_codigo(cfg["codigo"], corpus, traer=not a.sin_red) if cfg.get("codigo") else []
    indice, nuevos, cambios = leer_json(espejo / "indice.json", {}), [], []
    if not a.sin_red:
        w, t = cfg.get("wiki"), cfg.get("tickets")
        try:
            if w:
                api = Atlassian(w["url"], w["credenciales"], w.get("var_correo", "ATLASSIAN_EMAIL"), w.get("var_token", "ATLASSIAN_API_TOKEN"))
                indice, nuevos = parte_wiki(api, espejo, ultimo, a.desde, a.tope)
            if t:
                fuente = w or t
                api = Atlassian(t["url"], t.get("credenciales", fuente.get("credenciales")), t.get("var_correo", fuente.get("var_correo", "ATLASSIAN_EMAIL")),
                                t.get("var_token", fuente.get("var_token", "ATLASSIAN_API_TOKEN")))
                cambios = parte_tickets(api, espejo, a.desde)
        except (KeyError, OSError, TypeError) as e:
            print(f"Aviso: no se pudo leer la wiki o los tickets ({type(e).__name__}); se sigue con el código", file=sys.stderr)
    if not a.simulacro:
        guardar_json(estado_ruta, ultimo)
    sin = [f for f in filas if f[3] == 0]
    poco = [f for f in filas if f[3] == 1]
    hace30 = time.strftime("%F", time.localtime(time.time() - 30 * 86400))
    sin_citar = [(pid, m) for pid, m in indice.items() if not citada(m["titulo"], pid, corpus) and m["bajada"] >= hace30]
    sel = sellos(cfg)
    informe = construir_informe(sin, poco, sin_citar, cambios, sel.get("viejas", []), sel)
    salida = _ruta(c["salida"])
    if not a.simulacro:
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text("\n".join(informe), encoding="utf8")
    print(f"Wiki: {len(nuevos)} páginas nuevas o cambiadas · tickets: {len(cambios)} cambios de estado · código: {len(sin)} sin ficha, "
          f"{len(poco)} con 1 mención · informe: {'(simulacro, no escrito)' if a.simulacro else salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
