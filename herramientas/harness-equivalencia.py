#!/usr/bin/env python3
"""Equivalencia origen ↔ nuevo (SOLO LECTURA).

Lee casos (JSON: lista o {"casos": [...]}; o CSV) con id, entrada, salida_origen, salida_nuevo y,
opcionales, tolerancia (numérica, por caso) y aceptada_motivo. Veredictos: equivalente,
diferencia aceptada (con motivo) o diferencia. Números con `decimal` exacto, nunca flotantes.
Exit 0 solo si no hay diferencias sin aceptar; 2 si la entrada es inválida o está vacía.
Uso: harness-equivalencia.py casos.json|casos.csv [--json]
"""
import argparse, csv, decimal, json, pathlib, sys
from decimal import Decimal

decimal.getcontext().prec = 60
EQ, ACEPTADA, DIF = "equivalente", "diferencia aceptada", "diferencia"


def a_decimal(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, Decimal):
        d = v
    elif isinstance(v, int):
        d = Decimal(v)
    elif isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            d = Decimal(s)
        except decimal.InvalidOperation:
            return None
    else:
        return None
    return d if d.is_finite() else None


def iguales(a, b, tol):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(iguales(a[k], b[k], tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(iguales(x, y, tol) for x, y in zip(a, b))
    da, db = a_decimal(a), a_decimal(b)
    if da is not None and db is not None:
        return abs(da - db) <= tol
    if isinstance(a, str) and isinstance(b, str):
        return a == b
    return type(a) is type(b) and a == b


def cargar(ruta):
    p = pathlib.Path(ruta)
    txt = p.read_text(encoding="utf8")
    if p.suffix.lower() == ".csv":
        casos = list(csv.DictReader(txt.splitlines()))
    else:
        d = json.loads(txt, parse_float=Decimal)
        casos = d.get("casos") if isinstance(d, dict) else d
    if not isinstance(casos, list) or not casos:
        raise ValueError("no hay casos")
    for i, c in enumerate(casos):
        if not isinstance(c, dict) or not all(k in c for k in ("id", "salida_origen", "salida_nuevo")):
            raise ValueError(f"caso {i + 1}: faltan id, salida_origen o salida_nuevo")
    return casos


def evaluar(casos):
    res = []
    for c in casos:
        t = c.get("tolerancia")
        tol = Decimal(0) if t in (None, "") else a_decimal(t)
        if tol is None or tol < 0:
            raise ValueError(f"{c['id']}: tolerancia inválida")
        motivo = str(c.get("aceptada_motivo") or "").strip()
        if iguales(c["salida_origen"], c["salida_nuevo"], tol):
            v = EQ
        else:
            v = ACEPTADA if motivo else DIF
        res.append({"id": str(c["id"]), "veredicto": v, "motivo": motivo if v == ACEPTADA else "",
                    "entrada": c.get("entrada", ""), "origen": c["salida_origen"], "nuevo": c["salida_nuevo"]})
    return res


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("casos"); p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    try:
        res = evaluar(cargar(a.casos))
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    cuenta = {v: sum(r["veredicto"] == v for r in res) for v in (EQ, ACEPTADA, DIF)}
    if a.json:
        print(json.dumps({"resumen": cuenta, "casos": res}, ensure_ascii=False, default=str, indent=1))
    else:
        for r in res:
            extra = f" — {r['motivo']}" if r["motivo"] else (f" — origen={r['origen']} nuevo={r['nuevo']}" if r["veredicto"] == DIF else "")
            print(f"{r['id']}: {r['veredicto']}{extra}")
        print(f"\nTotal {len(res)}: {cuenta[EQ]} equivalentes, {cuenta[ACEPTADA]} diferencias aceptadas, {cuenta[DIF]} diferencias sin aceptar")
    return 0 if cuenta[DIF] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
