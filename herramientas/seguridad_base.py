#!/usr/bin/env python3
"""Línea base de seguridad (20 comprobaciones previas al lanzamiento). Solo lectura, sin red, solo biblioteca estándar.

Dos usos con fuerza distinta (ver estandares/seguridad-base.md):
  · sistema NUEVO: se exige (`requisitos()` produce los requisitos con su criterio);
  · proyecto EXISTENTE: se marca sin imponer (`evaluar()` dice qué evidencia hay y qué no se pudo ver).

«sin_evidencia» no es «no está»: es «no lo vi leyendo archivos». Lo que solo se confirma en ejecución sale como «confirmar».

Uso: python3 seguridad_base.py <carpeta> [--json]
Salida: 0 siempre que la carpeta exista (es informativo); 2 argumentos inválidos."""
import json
import os
import pathlib
import re
import subprocess
import sys
import tomllib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "estandares" / "seguridad-base.toml"
IGNORADOS = {".git", "node_modules", "dist", "build", "target", "vendor", ".venv", "venv", "__pycache__", ".angular", "coverage", ".next"}
EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".java", ".kt", ".cs", ".go", ".rb", ".php", ".rs", ".sql", ".yml", ".yaml",
       ".toml", ".json", ".tf", ".conf", ".ini", ".sh", ".html", ".gradle", ".xml", ".properties", ".env", ".example"}
OMITIR = re.compile(r"(\.spec\.|\.test\.|__tests__|(^|/)tests?/|(^|/)fixtures?/|\.min\.|package-lock\.json$|pnpm-lock|yarn\.lock|\.lock$|\.md$|\.d\.ts$)")
MAX_ARCHIVOS = 4000
MAX_BYTES = 300_000
ESTADOS = ("evidencia", "indicios", "sin_evidencia", "confirmar", "alerta")


def cargar(ruta=CATALOGO):
    with open(ruta, "rb") as f:
        datos = tomllib.load(f)
    items = datos.get("item", [])
    if len({i["id"] for i in items}) != len(items) or not items:
        raise ValueError("seguridad-base.toml: ids repetidos o catálogo vacío")
    return items


def inventario(carpeta):
    """Lista de rutas relativas (posix) de la carpeta, sin seguir enlaces simbólicos."""
    raiz = pathlib.Path(carpeta).resolve()
    out = []
    for dp, dn, fn in os.walk(raiz, followlinks=False):
        dn[:] = sorted(d for d in dn if d not in IGNORADOS)
        for f in sorted(fn):
            out.append((pathlib.Path(dp) / f).relative_to(raiz).as_posix())
            if len(out) >= MAX_ARCHIVOS * 3:
                return out
    return out


def _lector(carpeta):
    raiz = pathlib.Path(carpeta).resolve()

    def leer(rel):
        try:
            with open(raiz / rel, "rb") as f:
                return f.read(MAX_BYTES).decode("utf-8", errors="ignore")
        except OSError:
            return ""
    return leer


def _revisables(archivos):
    out = []
    for r in archivos:
        if OMITIR.search(r):
            continue
        base = r.rsplit("/", 1)[-1]
        ext = "." + base.rsplit(".", 1)[-1] if "." in base else ""
        if ext in EXT or base.startswith(".env") or base in ("Dockerfile", "docker-compose.yml"):
            out.append(r)
        if len(out) >= MAX_ARCHIVOS:
            break
    return out


def _lineas(texto, rx):
    for n, linea in enumerate(texto.splitlines(), 1):
        if rx.search(linea):
            yield n


def versionados_git(carpeta):
    """Conjunto de rutas que git versiona en la carpeta, o None si no es un repositorio (entonces no se puede afirmar)."""
    try:
        top = subprocess.run(["git", "-C", str(carpeta), "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=20).stdout.strip()
        if not top or pathlib.Path(top).resolve() != pathlib.Path(carpeta).resolve():
            return None
        out = subprocess.run(["git", "-C", str(carpeta), "ls-files"], capture_output=True, text=True, timeout=60).stdout
        return set(out.splitlines())
    except Exception:
        return None


def evaluar(archivos, leer, items=None, versionados=None):
    """archivos: rutas relativas; leer(rel) -> texto; versionados: rutas que git versiona (None si no se sabe).
    Devuelve {"items": [...], "resumen": {estado: n}, "aviso": str}."""
    items = items or cargar()
    revisables = _revisables(archivos)
    textos = {}

    def texto(r):
        if r not in textos:
            textos[r] = leer(r)
        return textos[r]

    # .gitignore y flujos de CI cuentan como evidencia de proceso aunque su extensión no sea de código
    extra = [r for r in archivos if r in (".gitignore", ".pre-commit-config.yaml") or r.startswith(".github/")]
    universo = sorted(set(revisables) | set(extra))
    resultado = []
    for it in items:
        evidencias, alertas = [], []
        for rx in it.get("archivo", []):
            c = re.compile(rx)
            evidencias += [r for r in archivos if c.search(r)][:3]
        if it.get("ignorado"):
            gi = texto(".gitignore") if ".gitignore" in archivos else ""
            if gi and any(re.search(rx, gi, re.M) for rx in it["ignorado"]):
                evidencias.append(".gitignore")
        cont = [re.compile(rx) for rx in it.get("contenido", [])]
        ale = [re.compile(rx) for rx in it.get("alerta", [])]
        solo = [re.compile(rx) for rx in it.get("alerta_en", [])]
        fuera = [re.compile(rx) for rx in it.get("alerta_excluye", [])]
        for r in universo:
            t = texto(r)
            if not t:
                continue
            if cont and len(evidencias) < 3:
                for c in cont:
                    n = next(_lineas(t, c), None)
                    if n:
                        evidencias.append(f"{r}:{n}")
                        break
            if ale and (not solo or any(s.search(r) for s in solo)) and not any(f.search(r) for f in fuera):
                for c in ale:
                    n = next(_lineas(t, c), None)
                    if n:
                        alertas.append(f"{r}:{n}")
                        break
            if len(alertas) >= 5:
                break
        for rx in it.get("versionados", []):
            c = re.compile(rx)
            for r in archivos:
                if c.search(r) and not r.endswith((".example", ".sample", ".template")):
                    if versionados is None:
                        evidencias.append(f"{r} (existe en disco; no se pudo comprobar con git si se versiona)")
                    elif r in versionados:
                        alertas.append(f"{r} (archivo de entorno versionado)")
        evidencias = list(dict.fromkeys(evidencias))[:3]
        alertas = list(dict.fromkeys(alertas))[:5]
        if alertas:
            estado = "alerta"
        elif evidencias:
            estado = "evidencia" if it.get("verificable", True) else "indicios"
        else:
            estado = "sin_evidencia" if it.get("verificable", True) else "confirmar"
        resultado.append({"id": it["id"], "titulo": it["titulo"], "estado": estado, "evidencia": evidencias, "alertas": alertas,
                          "verificable_leyendo": bool(it.get("verificable", True)),
                          "nota": it.get("nota_alerta", "") if alertas else ""})
    resumen = {e: sum(1 for r in resultado if r["estado"] == e) for e in ESTADOS}
    return {"items": resultado, "resumen": resumen,
            "aviso": "Informativo: «sin evidencia» significa que no se vio al leer los archivos, no que falte; «confirmar» solo se comprueba en ejecución."}


def requisitos(items=None):
    """Para sistemas NUEVOS: una entrada por comprobación, con su criterio de aceptación verificable."""
    items = items or cargar()
    return [{"id": i["id"], "titulo": i["titulo"], "que": i["que"], "exigencia": i["exigencia"],
             "verificable_leyendo": bool(i.get("verificable", True))} for i in items]


def a_md(res):
    L = ["| Id | Comprobación | Estado | Evidencia o alerta |", "|---|---|---|---|"]
    marca = {"evidencia": "evidencia", "indicios": "indicios (confirmar)", "sin_evidencia": "sin evidencia", "confirmar": "confirmar", "alerta": "ALERTA"}
    for r in res["items"]:
        det = "; ".join((r["alertas"] or r["evidencia"])) or "—"
        L.append(f"| {r['id']} | {r['titulo']} | {marca[r['estado']]} | {det.replace('|', '/')} |")
    return "\n".join(L)


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    if not a or a[0].startswith("-") or not pathlib.Path(a[0]).is_dir():
        print("Uso: seguridad_base.py <carpeta> [--json]", file=sys.stderr)
        return 2
    archivos = inventario(a[0])
    res = evaluar(archivos, _lector(a[0]), versionados=versionados_git(a[0]))
    print(json.dumps(res, ensure_ascii=False, indent=2) if "--json" in a else a_md(res) + "\n\n" + res["aviso"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
