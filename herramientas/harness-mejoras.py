#!/usr/bin/env python3
"""Registro de mejoras de una migración (`mejoras.md` de la instancia).

Garantía: solo escribe el archivo del registro. Nunca toca el código de la réplica y rechaza un
registro que no esté dentro de la instancia indicada con --instancia (ni en otro repositorio).
Aprobar NO aplica: `decidir` solo registra la decisión; `aplicada` exige estado aprobada + especificación.

Uso: harness-mejoras.py --instancia DIR [--registro RUTA] <subcomando>
  nueva --titulo T --donde D --cambio C --motivo M --riesgo bajo|medio|alto --esfuerzo S|M|L --visible si|no
  listar [--estado X]    revisar    decidir ID --estado aprobada|descartada --motivo "…"
  aplicada ID --especificacion REF
"""
import argparse, datetime as dt, pathlib, re, sys, unicodedata

ESTADOS = ("propuesta", "aprobada", "descartada", "aplicada")
RIESGOS = ("alto", "medio", "bajo")
ESFUERZOS = ("S", "M", "L")
CAMPOS = [("estado", "estado"), ("donde", "dónde se vio"), ("cambio", "qué cambiaría"), ("motivo", "motivo"),
          ("riesgo", "riesgo"), ("esfuerzo", "esfuerzo"), ("visible", "cambia comportamiento visible"),
          ("decision", "decisión"), ("fecha", "fecha de decisión"), ("especificacion", "especificación")]
ETIQ = dict(CAMPOS)
HEAD = re.compile(r"^##\s+(M-\d+)\s*(?:[·:\-—]\s*(.*))?$")
CAMPO = re.compile(r"^\s*-\s+\*\*(.+?)\*\*\s*:\s*(.*?)\s*(?:#.*)?$")
PREAMBULO = ("# Registro de mejoras\n\nMejoras detectadas durante la migración. Anotar no es aplicar: la réplica no cambia "
             "por estar aquí. Se gestiona con `harness-mejoras.py`; también se puede editar a mano respetando "
             "`## M-NNN · título` y las líneas `- **campo**: valor`.\n")


class Error(Exception):
    pass


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip()


CLAVES = {norm(v): k for k, v in CAMPOS}


def raiz_repo(p):
    for d in [p] + list(p.parents):
        if (d / ".git").exists():
            return d
    return None


def resolver_registro(instancia, registro):
    if not instancia:
        raise Error("falta --instancia")
    inst = pathlib.Path(instancia).resolve()
    if not inst.is_dir():
        raise Error(f"la instancia no existe: {inst}")
    reg = pathlib.Path(registro).resolve() if registro else inst / "mejoras.md"
    if reg.suffix != ".md":
        raise Error("el registro debe ser un archivo .md")
    if inst != reg and inst not in reg.parents:
        raise Error(f"el registro {reg} está fuera de la instancia {inst}")
    if raiz_repo(reg.parent) != raiz_repo(inst):
        raise Error("el registro cae en un repositorio distinto al de la instancia")
    return reg


def leer(reg):
    """Devuelve (preambulo_lineas, bloques); bloque = {id, titulo, lineas}. Conserva todo el texto."""
    txt = reg.read_text(encoding="utf8").splitlines() if reg.exists() else PREAMBULO.splitlines()
    pre, bloques, act = [], [], None
    for ln in txt:
        m = HEAD.match(ln.strip())
        if m:
            act = {"id": m.group(1), "titulo": (m.group(2) or "").strip(), "lineas": [ln]}
            bloques.append(act)
        elif act is None:
            pre.append(ln)
        else:
            act["lineas"].append(ln)
    return pre, bloques


def campos(b):
    d = {}
    for ln in b["lineas"][1:]:
        m = CAMPO.match(ln)
        if m and norm(m.group(1)) in CLAVES:
            d.setdefault(CLAVES[norm(m.group(1))], m.group(2).strip())
    return d


def poner(b, clave, valor):
    valor = " ".join(str(valor).split())
    nueva = f"- **{ETIQ[clave]}**: {valor}"
    for i, ln in enumerate(b["lineas"][1:], 1):
        m = CAMPO.match(ln)
        if m and CLAVES.get(norm(m.group(1))) == clave:
            b["lineas"][i] = nueva
            return
    fin = len(b["lineas"])
    while fin > 1 and not b["lineas"][fin - 1].strip():
        fin -= 1
    b["lineas"].insert(fin, nueva)


def escribir(reg, pre, bloques):
    out = list(pre)
    while out and not out[-1].strip():
        out.pop()
    for b in bloques:
        while b["lineas"] and not b["lineas"][-1].strip():
            b["lineas"].pop()
        out += [""] + b["lineas"]
    reg.write_text("\n".join(out) + "\n", encoding="utf8")


def buscar(bloques, ident):
    ident = ident.upper()
    for b in bloques:
        if b["id"] == ident:
            return b
    raise Error(f"no existe {ident}")


def siguiente_id(bloques):
    n = max([int(b["id"][2:]) for b in bloques] or [0]) + 1
    return f"M-{n:03d}"


def nueva(reg, a, hoy=None):
    pre, bloques = leer(reg)
    ident = siguiente_id(bloques)
    b = {"id": ident, "titulo": " ".join(a.titulo.split()), "lineas": []}
    b["lineas"].append(f"## {ident} · {b['titulo']}")
    riesgo, esf, vis = a.riesgo.lower(), a.esfuerzo.upper(), norm(a.visible)
    if riesgo not in RIESGOS or esf not in ESFUERZOS or vis not in ("si", "no"):
        raise Error("riesgo: bajo|medio|alto · esfuerzo: S|M|L · visible: si|no")
    vals = {"estado": "propuesta", "donde": a.donde, "cambio": a.cambio, "motivo": a.motivo, "riesgo": riesgo,
            "esfuerzo": esf, "visible": "sí" if vis == "si" else "no", "decision": "", "fecha": "", "especificacion": ""}
    for k, _ in CAMPOS:
        poner(b, k, vals[k])
    bloques.append(b)
    escribir(reg, pre, bloques)
    return ident


def listar(reg, estado=None):
    _, bloques = leer(reg)
    res = []
    for b in bloques:
        c = campos(b)
        if estado is None or norm(c.get("estado", "")) == estado:
            res.append((b["id"], b["titulo"], c))
    return res


def revisar(reg):
    pend = [(i, t, c) for i, t, c in listar(reg, "propuesta")]
    if not pend:
        return "Sin propuestas pendientes."
    out = [f"Lote de revisión: {len(pend)} propuesta(s) pendiente(s). Decidir con: decidir ID --estado aprobada|descartada --motivo \"…\""]
    for r in RIESGOS:
        grupo = [p for p in pend if norm(p[2].get("riesgo", "")) == r]
        if not grupo:
            continue
        out.append(f"\n== Riesgo {r} ==")
        for e in ESFUERZOS:
            for i, t, c in [g for g in grupo if g[2].get("esfuerzo", "").upper() == e]:
                out.append(f"- {i} · {t} [esfuerzo {e}; visible: {c.get('visible', '?')}]\n    se vio: {c.get('donde', '')}\n    cambiaría: {c.get('cambio', '')}\n    motivo: {c.get('motivo', '')}")
    otros = [p for p in pend if norm(p[2].get("riesgo", "")) not in RIESGOS]
    if otros:
        out.append("\n== Riesgo sin clasificar (completar a mano) ==")
        out += [f"- {i} · {t}" for i, t, _ in otros]
    return "\n".join(out)


def decidir(reg, ident, estado, motivo, hoy=None):
    if estado not in ("aprobada", "descartada"):
        raise Error("el estado de una decisión es aprobada o descartada")
    if not motivo or not motivo.strip():
        raise Error("la decisión exige --motivo")
    pre, bloques = leer(reg)
    b = buscar(bloques, ident)
    actual = norm(campos(b).get("estado", ""))
    if actual != "propuesta":
        raise Error(f"{b['id']} está en estado {actual or 'desconocido'}; solo se decide una propuesta")
    poner(b, "estado", estado)
    poner(b, "decision", motivo)
    poner(b, "fecha", (hoy or dt.date.today()).isoformat())
    escribir(reg, pre, bloques)


def aplicada(reg, ident, especificacion):
    if not especificacion or not especificacion.strip():
        raise Error("marcar aplicada exige --especificacion (referencia a la especificación del cambio)")
    pre, bloques = leer(reg)
    b = buscar(bloques, ident)
    actual = norm(campos(b).get("estado", ""))
    if actual != "aprobada":
        raise Error(f"{b['id']} está en estado {actual or 'desconocido'}; solo una aprobada puede pasar a aplicada")
    poner(b, "estado", "aplicada")
    poner(b, "especificacion", especificacion)
    escribir(reg, pre, bloques)


def main(argv=None):
    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("--instancia", default=argparse.SUPPRESS)
    base.add_argument("--registro", default=argparse.SUPPRESS)
    p = argparse.ArgumentParser(description=__doc__, parents=[base], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("nueva", parents=[base])
    for k in ("titulo", "donde", "cambio", "motivo", "riesgo", "esfuerzo", "visible"):
        n.add_argument("--" + k, required=True)
    l = sub.add_parser("listar", parents=[base]); l.add_argument("--estado", choices=ESTADOS)
    sub.add_parser("revisar", parents=[base])
    d = sub.add_parser("decidir", parents=[base]); d.add_argument("id"); d.add_argument("--estado", required=True); d.add_argument("--motivo", default="")
    ap = sub.add_parser("aplicada", parents=[base]); ap.add_argument("id"); ap.add_argument("--especificacion", default="")
    a = p.parse_args(argv)
    try:
        reg = resolver_registro(getattr(a, "instancia", None), getattr(a, "registro", None))
        if a.cmd == "nueva":
            print(nueva(reg, a))
        elif a.cmd == "listar":
            for i, t, c in listar(reg, a.estado):
                print(f"{i} · {c.get('estado', '?'):10} · riesgo {c.get('riesgo', '?')} · esfuerzo {c.get('esfuerzo', '?')} · {t}")
        elif a.cmd == "revisar":
            print(revisar(reg))
        elif a.cmd == "decidir":
            decidir(reg, a.id, a.estado, a.motivo); print(f"{a.id.upper()} → {a.estado} (el cambio NO se aplicó)")
        elif a.cmd == "aplicada":
            aplicada(reg, a.id, a.especificacion); print(f"{a.id.upper()} → aplicada")
    except Error as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
