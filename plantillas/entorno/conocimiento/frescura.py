#!/usr/bin/env python3
"""Lista los documentos cuya marca `<!-- revisado: AAAA-MM-DD · vence: Nd -->` ya venció. Solo lectura.
Un documento sin marca no se juzga. Sale con 1 si hay vencidos (útil en la compuerta)."""
import datetime as dt
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PAT = re.compile(r"revisado:\s*(\d{4}-\d{2}-\d{2})\s*[·\-|]\s*vence:\s*(\d+)d")
hoy = dt.date.today()
vencidos = []
for carpeta in ("docs", "knowledge"):
    for p in sorted((RAIZ / carpeta).rglob("*.md")) if (RAIZ / carpeta).is_dir() else []:
        m = PAT.search(p.read_text(encoding="utf8", errors="replace")[:600])
        if not m:
            continue
        revisado = dt.date.fromisoformat(m.group(1))
        dias = (hoy - revisado).days
        if dias > int(m.group(2)):
            vencidos.append((p.relative_to(RAIZ), dias - int(m.group(2))))
for ruta, exceso in vencidos:
    print(f"VENCIDO hace {exceso} d: {ruta}")
print(f"{len(vencidos)} documento(s) vencido(s)")
sys.exit(1 if vencidos else 0)
