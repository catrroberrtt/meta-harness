#!/usr/bin/env python3
"""Aprendizaje con evidencia y reversible. Una lección NO se vuelve regla sin evidencia, y toda regla se puede revertir.

  aprender.py nota "qué pasó y qué regla sale" [--evidencia "dónde se ve"] [--falla "comando que falló"] [--tipo error|regla|duda]
  aprender.py revisar                  lista las notas (marca las que no tienen evidencia)
  aprender.py promover N               pasa la nota N a «Reglas aprendidas» de AGENTS.md (exige evidencia; si registró una falla, exige que ya no falle)
  aprender.py revertir N               quita esa regla de AGENTS.md y marca la nota como revertida
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import shlex
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
NOTAS = RAIZ / "knowledge" / "aprendizaje.md"
AGENTES = RAIZ / "AGENTS.md"
INI, FIN = "<!-- reglas-aprendidas:inicio -->", "<!-- reglas-aprendidas:fin -->"
CAB = ("# Lecciones aprendidas\n\n<!-- revisado: {f} · vence: 90d -->\n\n"
       "Formato por nota: `N. [estado] [tipo] fecha · texto · evidencia: …`. Estados: nota, regla, revertida.\n\n")


# Mejora medida: `--falla "<comando>"` corre el comando AHORA y exige que falle (si ya pasa, no hay nada que corregir). Al promover se vuelve
# a correr y la regla solo pasa si ahora funciona. El comando se guarda en .entorno/fallas.json (local, fuera de git) y NO se lee del texto de
# la nota: así un archivo de notas manipulado no puede hacer ejecutar nada. Sin ese registro (por ejemplo, en un clon) la nota se promueve solo
# por su evidencia escrita y se dice que no hubo comprobación automática.
FALLAS = RAIZ / ".entorno" / "fallas.json"
TIEMPO_COMANDO = 120


def correr_comando(comando):
    """(código, última línea de salida). Sin shell: el comando se parte con shlex. Un comando que no existe o se agota cuenta como error."""
    try:
        r = subprocess.run(shlex.split(comando), cwd=RAIZ, capture_output=True, text=True, timeout=TIEMPO_COMANDO)
        salida = (r.stdout + r.stderr).strip().splitlines()
        return r.returncode, (salida[-1][:160] if salida else "")
    except FileNotFoundError:
        return 127, "el programa no existe"
    except (subprocess.TimeoutExpired, ValueError, OSError) as e:
        return 124, f"no se pudo ejecutar: {type(e).__name__}"


def leer_fallas():
    try:
        d = json.loads(FALLAS.read_text(encoding="utf8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def guardar_falla(num, comando, codigo, ultima):
    d = leer_fallas()
    d[str(num)] = {"comando": comando, "codigo": codigo, "salida": ultima, "fecha": str(dt.date.today())}
    FALLAS.parent.mkdir(exist_ok=True)
    FALLAS.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf8")


MAX_TEXTO = 300
PROHIBIDO = re.compile(r"[\x00-\x1f\x7f\u2028\u2029]|<!--|-->")


def limpio(campo, nombre):
    """Una nota es UNA línea de texto plano. Un salto de línea o un marcador HTML permitiría forjar otras notas o escribir
    fuera de su sitio en AGENTS.md (que el agente lee como instrucciones), así que se rechaza, no se corrige en silencio."""
    if PROHIBIDO.search(campo):
        sys.exit(f"{nombre} rechazado: no puede tener saltos de línea, caracteres de control ni marcadores «<!--» / «-->».")
    if len(campo) > MAX_TEXTO:
        sys.exit(f"{nombre} rechazado: supera {MAX_TEXTO} caracteres. Resúmelo y guarda el detalle en un documento.")
    return campo.strip()


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
    n = sub.add_parser("nota"); n.add_argument("texto"); n.add_argument("--evidencia", default=""); n.add_argument("--falla", default=""); n.add_argument("--tipo", default="regla", choices=["error", "regla", "duda"])
    sub.add_parser("revisar")
    for c in ("promover", "revertir"):
        s = sub.add_parser(c); s.add_argument("numero", type=int)
    a = ap.parse_args()
    ls = leer()
    if a.cmd == "nota":
        a.texto, a.evidencia = limpio(a.texto, "El texto"), limpio(a.evidencia, "La evidencia")
        if not a.texto:
            sys.exit("El texto no puede estar vacío.")
        num = len(ls) + 1
        if a.falla:
            comando = limpio(a.falla, "El comando")
            codigo, ultima = correr_comando(comando)
            if codigo == 0:
                sys.exit("El comando ya pasa: no hay un fallo que registrar. Anota la lección con --evidencia en texto o usa un comando que hoy falle.")
            guardar_falla(num, comando, codigo, ultima)
            a.evidencia = (a.evidencia + " · " if a.evidencia else "") + f"falla observada: «{comando}» salió {codigo}" + (f" ({ultima})" if ultima else "")
            a.evidencia = limpio(a.evidencia, "La evidencia")
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
    if int(num) != a.numero or PROHIBIDO.search(texto + (ev or "")):
        print(f"La línea {a.numero} del archivo de lecciones no es una nota válida (número distinto o contenido no permitido): "
              "revisa knowledge/aprendizaje.md a mano.", file=sys.stderr)
        return 2
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
        registro = leer_fallas().get(str(a.numero))
        comprobado = ""
        if registro and f"«{registro['comando']}» salió" in (ev or ""):
            codigo, ultima = correr_comando(registro["comando"])
            if codigo != 0:
                print(f"NO se promueve: el comando que falló sigue fallando (salió {codigo}"
                      + (f": {ultima}" if ultima else "") + "). La regla aún no corrige el problema.", file=sys.stderr)
                return 1
            comprobado = f" · comprobado {dt.date.today()}: «{registro['comando']}» ahora pasa"
        elif "falla observada" in (ev or ""):
            print("AVISO: esta nota registró una falla, pero este clon no tiene el registro local (.entorno/fallas.json): "
                  "se promueve por su evidencia escrita, SIN comprobación automática.", file=sys.stderr)
        ag = ag.replace(FIN, f"- {texto} (evidencia: {ev}) {marca}\n{FIN}")
        ls[a.numero - 1] = ls[a.numero - 1].replace("[nota]", "[regla]", 1).replace("[revertida]", "[regla]", 1) + comprobado
    else:
        ag = re.sub(r"^- .*" + re.escape(marca) + r"\n", "", ag, flags=re.M)
        ls[a.numero - 1] = re.sub(r"\[(nota|regla)\]", "[revertida]", ls[a.numero - 1], count=1)
    AGENTES.write_text(ag, encoding="utf8")
    escribir(ls)
    print(f"nota {num}: {'promovida a regla' if a.cmd == 'promover' else 'revertida'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
