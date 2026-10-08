#!/usr/bin/env python3
"""Lint de perfiles del meta harness: R21/R22 (estructura de la plantilla) y R25 (cabeceras) en perfiles.
Uso: python3 harness-lint-perfiles.py [carpeta-perfiles] [--hoy AAAA-MM-DD]
Se omiten las carpetas que empiezan por «_» (la plantilla lleva marcadores, no fechas reales).
Sale con código 1 si hay errores."""
import re, sys, pathlib, datetime
REQ = ["README.md","arquitectura.md","patrones.md","codificacion.md","datos.md","pruebas.md","seguridad.md",
       "rendimiento.md","observabilidad.md","errores-frecuentes/README.md","recetas/README.md","evidencia.md"]
TIPO = re.compile(r"^<!-- tipo: perfil · capa: 3 -->\s*$")
REV = re.compile(r"^<!-- revisado: (\d{4}-\d{2}-\d{2}) · vence: (\d+)d · fuente: (.+?) -->\s*$")

def lint_perfil(p, hoy):
    err = []
    for rel in REQ:
        f = p / rel
        if not f.is_file():
            err.append(f"{p.name}/{rel}: falta (R21/R22)"); continue
        l = f.read_text(encoding="utf8").splitlines()
        if len(l) < 3 or not TIPO.match(l[1]):
            err.append(f"{p.name}/{rel}: cabecera `tipo` ausente o mal formada en la línea 2 (R1/R25)")
        m = REV.match(l[2]) if len(l) > 2 else None
        if not m:
            err.append(f"{p.name}/{rel}: cabecera `revisado` ausente o mal formada en la línea 3 (R25)"); continue
        try:
            fecha = datetime.date.fromisoformat(m.group(1))
        except ValueError:
            err.append(f"{p.name}/{rel}: fecha `revisado` inválida"); continue
        if not m.group(3).strip():
            err.append(f"{p.name}/{rel}: `fuente` vacía (R25)")
        if hoy > fecha + datetime.timedelta(days=int(m.group(2))):
            err.append(f"{p.name}/{rel}: vencido (revisado {fecha}, vence {m.group(2)}d) (R25)")
    return err

def main(argv):
    hoy = datetime.date.today(); args = []
    i = 0
    while i < len(argv):
        if argv[i] == "--hoy": hoy = datetime.date.fromisoformat(argv[i+1]); i += 2
        else: args.append(argv[i]); i += 1
    base = pathlib.Path(args[0] if args else pathlib.Path(__file__).resolve().parent.parent / "perfiles")
    perfiles = sorted(d for d in base.iterdir() if d.is_dir() and not d.name.startswith("_"))
    if not perfiles: print("No hay perfiles"); return 1
    total = 0
    for p in perfiles:
        e = lint_perfil(p, hoy); total += len(e)
        print(f"[{'OK' if not e else 'FALLA'}] {p.name}")
        for x in e: print("   - " + x)
    print(f"\n{len(perfiles)} perfiles, {total} errores")
    return 1 if total else 0
if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
