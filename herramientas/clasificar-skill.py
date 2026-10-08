#!/usr/bin/env python3
"""Inventario del meta harness: de qué tipo es cada documento de la skill y cuánto se mezclan lo técnico, lo de negocio y lo de este proyecto.

SOLO LECTURA. Existe porque el entorno (skill, hooks, memoria, scripts) ya sirve más allá de un solo proyecto y se quiere poder empezar otro proyecto
sin rehacerlo: para eso hay que saber qué es reutilizable (técnico, de método) y qué es del proyecto (negocio, control de cambios, entorno), y
dónde están anidados. Mide dos cosas por archivo, con reglas simples y reproducibles:
  · tecnicidad  = % de líneas que son código o comandos (cercos ```, SQL, rutas src/, nombres de clase/función con backticks).
  · especificidad = nº de referencias al proyecto por cada 100 líneas (repos, claves de ticket, PR #, nombres de módulos, productos y personas del proyecto; configurables).
Uso: python3 clasificar-skill.py [--md]   (--md imprime el informe en Markdown; sin él, un resumen corto)
"""
import re, sys, pathlib, collections
ROOT = pathlib.Path(__file__).resolve().parent.parent
# Patrón de "lo propio del proyecto": se lee de la variable HARNESS_PATRON_PROYECTO o del archivo patrones-proyecto.txt (una regex por línea)
# junto a la raíz analizada. Sin ninguno, se usa un predeterminado genérico (claves de ticket y números de PR).
def _patron():
    import os
    lineas = []
    if os.environ.get("HARNESS_PATRON_PROYECTO"): lineas.append(os.environ["HARNESS_PATRON_PROYECTO"])
    f = ROOT / "patrones-proyecto.txt"
    if f.exists(): lineas += [l.strip() for l in f.read_text(encoding="utf8").splitlines() if l.strip() and not l.startswith("#")]
    return re.compile("|".join(lineas) if lineas else r"\b[A-Z]{2,}-\d+\b|PR\s?#\d+")
PROY = _patron()
TEC = re.compile(r"`[^`\n]*(?:[/_.()]|[A-Z][a-z]+[A-Z])[^`\n]*`|\b(?:SELECT|INSERT|UPDATE|DELETE|ORDER BY|JOIN|WHERE|npm|npx|git|jest|tsc|curl|mysql)\b|\.(?:ts|sql|sh|py|json)\b|\bsrc/")
def kind(rel: str) -> str:
    p = rel.split("/")
    if rel == "SKILL.md": return "router"
    if p[0] == "references": return "técnico (método y estándares)"
    if p[0] == "frontend": return "técnico (frontend)"
    if p[0] == "knowledge":
        if len(p) > 2 and p[1] == "grupo" and p[2] == "calidad": return "técnico (calidad)"
        return "negocio"
    if p[0] == "_kb":
        if "implementaciones" in p: return "control de cambios"
        if "memory-backup" in p: return "memoria"
        return "datos y publicados"
    if p[0] == "entorno": return "entorno"
    return "otro"
def medir(path: pathlib.Path):
    text = path.read_text(encoding="utf8", errors="ignore").splitlines()
    n = max(len(text), 1); fence = False; code = 0
    for l in text:
        if l.strip().startswith("```"): fence = not fence; code += 1; continue
        code += 1 if fence else (1 if TEC.search(l) else 0)
    espec = len(PROY.findall("\n".join(text)))
    return n, round(100 * code / n), round(100 * espec / n, 1)
filas = []
for f in sorted(ROOT.rglob("*.md")):
    rel = f.relative_to(ROOT).as_posix()
    if any(x in rel for x in (".venv", "node_modules", "_kb/semantic-index", "_kb/memory-backup", "_kb/artifacts/publicados")): continue
    n, tec, esp = medir(f); filas.append((kind(rel), rel, n, tec, esp))
por = collections.defaultdict(list)
for k, rel, n, tec, esp in filas: por[k].append((rel, n, tec, esp))
md = "--md" in sys.argv
out = []
out.append("| Tipo | Archivos | Líneas | Tecnicidad media | Especificidad media (refs al proyecto / 100 líneas) |\n|---|---|---|---|---|" if md else "tipo · archivos · líneas · tecnicidad% · especificidad")
for k, v in sorted(por.items(), key=lambda kv: -sum(x[1] for x in kv[1])):
    lin = sum(x[1] for x in v); tec = round(sum(x[2] * x[1] for x in v) / lin); esp = round(sum(x[3] * x[1] for x in v) / lin, 1)
    out.append(f"| {k} | {len(v)} | {lin} | {tec} % | {esp} |" if md else f"{k:34} {len(v):4} {lin:7} {tec:4}% {esp:6}")
def top(titulo, tipo, clave, rev=True, nmin=40, n=12):
    cand = [(rel, nn, tec, esp) for rel, nn, tec, esp in por.get(tipo, []) if nn >= nmin]
    cand.sort(key=clave, reverse=rev)
    out.append(f"\n### {titulo}\n" if md else f"\n== {titulo}")
    if md: out.append("| Archivo | Líneas | Tecnicidad | Especificidad |\n|---|---|---|---|")
    for rel, nn, tec, esp in cand[:n]:
        out.append(f"| `{rel}` | {nn} | {tec} % | {esp} |" if md else f"{rel:78} {nn:5} {tec:4}% {esp:5}")
top("Documentos técnicos MUY atados a este proyecto (hay que parametrizarlos para reutilizarlos)", "técnico (método y estándares)", lambda x: x[3])
top("Documentos de negocio con mucho contenido técnico (hay que separar lo técnico a su propio documento)", "negocio", lambda x: x[2])
top("Control de cambios con mucho contenido técnico general (candidatos a subir a estándares)", "control de cambios", lambda x: x[2], nmin=60)
print("\n".join(out))
