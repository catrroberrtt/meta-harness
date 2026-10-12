#!/usr/bin/env python3
"""Aprendizaje con evidencia y reversible. Una lección NO se vuelve regla sin evidencia, y toda regla se puede revertir.

  aprender.py nota "qué pasó y qué regla sale" [--evidencia "dónde se ve"] [--tipo error|regla|duda]
  aprender.py revisar                  lista las notas (marca las que no tienen evidencia)
  aprender.py promover N               pasa la nota N a «Reglas aprendidas» de AGENTS.md (exige evidencia)
  aprender.py revertir N               quita esa regla de AGENTS.md y marca la nota como revertida
"""
import argparse
import datetime as dt
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
NOTAS = RAIZ / "knowledge" / "aprendizaje.md"
AGENTES = RAIZ / "AGENTS.md"
INI, FIN = "<!-- reglas-aprendidas:inicio -->", "<!-- reglas-aprendidas:fin -->"
CAB = ("# Lecciones aprendidas\n\n<!-- revisado: {f} · vence: 90d -->\n\n"
       "Formato por nota: `N. [estado] [tipo] fecha · texto · evidencia: …`. Estados: nota, regla, revertida.\n\n")


def leer():
    if not NOTAS.exists():
        return []
    return [l for l in NOTAS.read_text(encoding="utf8").splitlines() if re.match(r"^\d+\. \[", l)]


def escribir(lineas):
    NOTAS.parent.mkdir(exist_ok=True)
    NOTAS.write_text(CAB.format(f=dt.date.today()) + "\n".join(lineas) + "\n", encoding="utf8")


def partes(l):
    m = re.match(r"^(\d+)\. \[(\w+)\] \[(\w+)\] (\S+) · (.*?)(?: · evidencia: (.*))?$", l)
    return m.groups() if m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("nota"); n.add_argument("texto"); n.add_argument("--evidencia", default=""); n.add_argument("--tipo", default="regla", choices=["error", "regla", "duda"])
    sub.add_parser("revisar")
    for c in ("promover", "revertir"):
        s = sub.add_parser(c); s.add_argument("numero", type=int)
    a = ap.parse_args()
    ls = leer()
    if a.cmd == "nota":
        num = len(ls) + 1
        ev = f" · evidencia: {a.evidencia}" if a.evidencia else ""
        ls.append(f"{num}. [nota] [{a.tipo}] {dt.date.today()} · {a.texto}{ev}")
        escribir(ls)
        print(f"nota {num} guardada" + ("" if a.evidencia else " (sin evidencia: aún no se puede promover)"))
        return 0
    if a.cmd == "revisar":
        for l in ls:
            p = partes(l)
            print(l + ("" if p and p[5] else "   <-- sin evidencia"))
        print(f"{len(ls)} nota(s)")
        return 0
    if not 1 <= a.numero <= len(ls):
        print("número fuera de rango", file=sys.stderr)
        return 2
    p = partes(ls[a.numero - 1])
    if not p:
        print("la nota no se pudo interpretar", file=sys.stderr)
        return 2
    num, estado, tipo, fecha, texto, ev = p
    marca = f"<!-- regla {num} -->"
    ag = AGENTES.read_text(encoding="utf8")
    if INI not in ag or FIN not in ag:
        print("AGENTS.md no tiene la sección de reglas aprendidas", file=sys.stderr)
        return 2
    if a.cmd == "promover":
        if not ev:
            print("NO se promueve: la nota no tiene evidencia. Agrégala y vuelve a intentar.", file=sys.stderr)
            return 1
        if marca in ag:
            print("ya estaba promovida")
            return 0
        ag = ag.replace(FIN, f"- {texto} (evidencia: {ev}) {marca}\n{FIN}")
        ls[a.numero - 1] = ls[a.numero - 1].replace("[nota]", "[regla]", 1).replace("[revertida]", "[regla]", 1)
    else:
        ag = re.sub(r"^- .*" + re.escape(marca) + r"\n", "", ag, flags=re.M)
        ls[a.numero - 1] = re.sub(r"\[(nota|regla)\]", "[revertida]", ls[a.numero - 1], count=1)
    AGENTES.write_text(ag, encoding="utf8")
    escribir(ls)
    print(f"nota {num}: {'promovida a regla' if a.cmd == 'promover' else 'revertida'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
