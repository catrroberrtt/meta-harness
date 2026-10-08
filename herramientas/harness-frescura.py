#!/usr/bin/env python3
"""Frescura de los documentos del harness (SOLO LECTURA).

Cada `.md` declara, junto a su línea `<!-- tipo: ... -->`, una cabecera:
    <!-- revisado: AAAA-MM-DD · vence: 90d · fuente: <qué lo respalda> -->
Informa: sin cabecera, vencidos (revisado + vence < hoy), sin fuente y por vencer (próximos 14 días).
Salida 1 si hay vencidos o sin cabecera (con --tolerar-sin-cabecera, los sin cabecera no cuentan).
Uso: python3 harness-frescura.py [raiz] [--hoy AAAA-MM-DD] [--json] [--tolerar-sin-cabecera]
"""
import argparse, datetime as dt, json, pathlib, re, sys

CAB = re.compile(r"<!--\s*revisado:\s*(\S+)\s*[·|;,]\s*vence:\s*(\d+)\s*d\s*(?:[·|;,]\s*fuente:\s*(.*?))?\s*-->", re.S)
VENTANA_POR_VENCER = 14
EXCLUIR = {".git", "node_modules", "__pycache__", ".venv"}
# Las plantillas se copian a cada instancia: la fecha de revisión es del documento ya instanciado, no de la plantilla.
EXCLUIR_PLANTILLAS = {"_plantilla", "plantillas"}


def analizar(raiz, hoy):
    r = {"raiz": str(raiz), "hoy": hoy.isoformat(), "total": 0, "al_dia": [], "sin_cabecera": [], "vencidos": [], "sin_fuente": [], "por_vencer": []}
    for p in sorted(raiz.rglob("*.md")):
        rel = p.relative_to(raiz)
        if set(rel.parts) & (EXCLUIR | EXCLUIR_PLANTILLAS):
            continue
        r["total"] += 1
        m = CAB.search(p.read_text(encoding="utf8", errors="ignore"))
        try:
            rev = dt.date.fromisoformat(m.group(1)) if m else None
        except ValueError:
            rev = None
        if not m or rev is None:
            r["sin_cabecera"].append(str(rel))
            continue
        vence = rev + dt.timedelta(days=int(m.group(2)))
        fuente = (m.group(3) or "").strip()
        dias = (vence - hoy).days
        info = {"doc": str(rel), "revisado": rev.isoformat(), "vence_el": vence.isoformat(), "dias": dias}
        if not fuente:
            r["sin_fuente"].append(str(rel))
        if dias < 0:
            r["vencidos"].append(info)
        elif dias <= VENTANA_POR_VENCER:
            r["por_vencer"].append(info)
        else:
            r["al_dia"].append(str(rel))
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raiz", nargs="?", default=str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--hoy")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tolerar-sin-cabecera", action="store_true")
    a = ap.parse_args(argv)
    raiz = pathlib.Path(a.raiz).expanduser().resolve()
    if not raiz.is_dir():
        sys.exit(f"No existe {raiz}")
    hoy = dt.date.fromisoformat(a.hoy) if a.hoy else dt.date.today()
    r = analizar(raiz, hoy)
    falla = bool(r["vencidos"]) or (bool(r["sin_cabecera"]) and not a.tolerar_sin_cabecera)
    r["falla"] = falla
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"Frescura al {r['hoy']} · {r['total']} documentos · al día {len(r['al_dia'])}")
        for t, k in (("VENCIDOS", "vencidos"), ("POR VENCER (14d)", "por_vencer")):
            if r[k]:
                print(f"\n{t}:")
                for i in r[k]:
                    print(f"  {i['doc']} (revisado {i['revisado']}, vence {i['vence_el']}, {i['dias']} d)")
        for t, k in (("SIN FUENTE", "sin_fuente"), ("SIN CABECERA" + (" (tolerado)" if a.tolerar_sin_cabecera else ""), "sin_cabecera")):
            if r[k]:
                print(f"\n{t} ({len(r[k])}):")
                for d in r[k]:
                    print(f"  {d}")
        print("\nRESULTADO:", "FALLA" if falla else "OK")
    return 1 if falla else 0


if __name__ == "__main__":
    sys.exit(main())
