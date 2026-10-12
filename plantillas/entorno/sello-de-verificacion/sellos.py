#!/usr/bin/env python3
"""Revisa los sellos `verificado-contra-git: <commit> · <repo> · <fecha>` de los documentos. Solo lectura.

Un documento de estado dice «verificado contra tal commit»: ese sello caduca. Para cada sello se comprueba, contra el repositorio declarado en
[[fuentes.repos]]:
  INEXISTENTE  el commit no existe en ese repo (sello inventado o de otro repo)       -> falla
  ATRASADO     la referencia ya avanzó N commits desde el sello                       -> avisa (falla con --estricto)
  VENCIDO      el sello tiene más de [fuentes].vigencia_dias días (7 por defecto)     -> avisa (falla con --estricto)
  VIGENTE      la referencia sigue en ese commit y el sello es reciente
  SIN REPO     el repo del sello no está declarado ni existe: no se puede comprobar   -> avisa
Uso: sellos.py [--estricto] [archivo ...]   (sin archivos: docs/ y knowledge/)
"""
import argparse
import datetime as dt
import pathlib
import re
import subprocess
import sys
import tomllib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SELLO = re.compile(r"verificado-contra-git:\s*([0-9a-f]{7,40})\s*[·|\-]\s*([\w.\-]+)\s*[·|\-]\s*(\d{4}-\d{2}-\d{2})")


def cfg():
    try:
        return tomllib.loads((RAIZ / "entorno.toml").read_text(encoding="utf8")).get("fuentes", {})
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def git(repo, *a):
    r = subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout.strip()


def estado(sha, nombre, fecha, repos, vigencia_dias, hoy):
    r = repos.get(nombre)
    ruta = pathlib.Path(str(r.get("ruta", ""))).expanduser() if r else None
    if not r or not (ruta / ".git").exists():
        return "SIN REPO", f"el repositorio «{nombre}» no está declarado en [[fuentes.repos]] o no existe en esa ruta"
    if git(ruta, "cat-file", "-e", f"{sha}^{{commit}}")[0] != 0:
        return "INEXISTENTE", f"el commit {sha} no existe en «{nombre}»"
    ref = r.get("referencia", "origin/main")
    c, n = git(ruta, "rev-list", "--count", f"{sha}..{ref}")
    edad = (hoy - dt.date.fromisoformat(fecha)).days
    if c == 0 and n.isdigit() and int(n) > 0:
        return "ATRASADO", f"la referencia {ref} avanzó {n} commit(s) desde el sello"
    if edad > vigencia_dias:
        return "VENCIDO", f"el sello tiene {edad} días (vigencia {vigencia_dias})"
    return "VIGENTE", f"la referencia {ref} sigue en ese commit" if c == 0 else "vigente"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("archivos", nargs="*")
    ap.add_argument("--estricto", action="store_true", help="ATRASADO y VENCIDO también hacen fallar")
    a = ap.parse_args()
    conf = cfg()
    repos = {r.get("nombre"): r for r in conf.get("repos", []) if r.get("nombre")}
    vigencia = int(conf.get("vigencia_dias", 7))
    hoy = dt.date.today()
    archivos = [pathlib.Path(x) for x in a.archivos] or [p for d in ("docs", "knowledge") if (RAIZ / d).is_dir() for p in sorted((RAIZ / d).rglob("*.md"))]
    total, malos, avisos = 0, 0, 0
    for p in archivos:
        try:
            lineas = p.read_text(encoding="utf8", errors="replace").splitlines()
        except OSError:
            continue
        for i, l in enumerate(lineas, 1):
            for m in SELLO.finditer(l):
                total += 1
                try:
                    est, motivo = estado(m.group(1), m.group(2), m.group(3), repos, vigencia, hoy)
                except (ValueError, subprocess.SubprocessError) as e:
                    est, motivo = "SIN REPO", f"no se pudo comprobar ({type(e).__name__})"
                destino = p.relative_to(RAIZ) if p.is_absolute() and RAIZ in p.parents else p
                print(f"  {est:<11} {destino}:{i}  {m.group(2)}@{m.group(1)} ({m.group(3)}): {motivo}")
                malos += est == "INEXISTENTE"
                avisos += est in ("ATRASADO", "VENCIDO", "SIN REPO")
    print(f"{total} sello(s): {malos} inexistente(s), {avisos} con aviso.")
    if malos or (a.estricto and avisos):
        print("Siguiente: un sello INEXISTENTE no demuestra nada: vuelve a verificar el documento y re-sella con scripts/inventario-fuentes.py. "
              "Uno ATRASADO o VENCIDO pide releer el documento contra la referencia actual antes de fiarte de él.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
