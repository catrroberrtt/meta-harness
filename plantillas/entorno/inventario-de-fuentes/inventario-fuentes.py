#!/usr/bin/env python3
"""Foto de las fuentes ANTES de afirmar qué existe, qué falta o qué está pendiente. Solo lectura (salvo un `git fetch` opcional).

Por cada repositorio de [[fuentes.repos]] en entorno.toml: trae lo remoto (a menos que pidas --sin-red), y dice contra QUÉ rama de referencia se
compara (nunca la rama local de turno), en qué commit está esa referencia, cuánto se adelanta o atrasa la rama actual y si hay cambios sin
commitear. Emite las líneas `verificado-contra-git: <commit> · <repo> · <fecha>` para pegar al principio de un análisis (las revisa sellos.py).

  inventario-fuentes.py [--sin-red] [--repo NOMBRE ...]
Un repositorio que no existe en la ruta declarada se reporta como FALTA: no se inventa su estado.
"""
import argparse
import datetime as dt
import pathlib
import subprocess
import sys
import tomllib

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def git(repo, *a, tiempo=60):
    r = subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, timeout=tiempo)
    return r.returncode, r.stdout.strip()


def repos():
    try:
        cfg = tomllib.loads((RAIZ / "entorno.toml").read_text(encoding="utf8")).get("fuentes", {})
    except (OSError, tomllib.TOMLDecodeError):
        return []
    return cfg.get("repos", [])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sin-red", action="store_true", help="no hace git fetch: usa lo que ya hay descargado (y lo dice)")
    ap.add_argument("--repo", action="append", help="solo este repositorio (por su nombre; se puede repetir)")
    a = ap.parse_args()
    lista = [r for r in repos() if not a.repo or r.get("nombre") in a.repo]
    if not lista:
        print("No hay repositorios en [[fuentes.repos]] de entorno.toml (o ninguno coincide con --repo).")
        print("Siguiente: declara cada repositorio con nombre, ruta y referencia (por ejemplo origin/main).")
        return 0
    hoy = dt.date.today().isoformat()
    print(f"## Fuentes (inventario {hoy}{', SIN RED: lo remoto puede estar desactualizado' if a.sin_red else ''})\n")
    sellos, filas = [], []
    for r in lista:
        nombre, ruta, ref = r.get("nombre", "?"), pathlib.Path(str(r.get("ruta", ""))).expanduser(), r.get("referencia", "origin/main")
        if not (ruta / ".git").exists():
            filas.append(f"| {nombre} | `{ref}` | FALTA | no existe en `{ruta}` | |")
            continue
        if not a.sin_red:
            codigo, _ = git(ruta, "fetch", "--quiet", "--prune", tiempo=120)
            if codigo != 0:
                filas.append(f"| {nombre} | `{ref}` | SIN RED | el fetch falló: se usa lo ya descargado | |")
        c, sha = git(ruta, "rev-parse", "--short", ref)
        if c != 0:
            filas.append(f"| {nombre} | `{ref}` | SIN REFERENCIA | la rama de referencia no existe en este clon | |")
            continue
        actual = git(ruta, "branch", "--show-current")[1] or "(desprendido)"
        _, cuenta = git(ruta, "rev-list", "--left-right", "--count", f"{ref}...HEAD")
        atras, adelante = (cuenta.split() + ["?", "?"])[:2]
        sucios = len([l for l in git(ruta, "status", "--porcelain")[1].splitlines() if l])
        ult = git(ruta, "log", "-1", "--format=%cs", ref)[1]
        sellos.append(f"> verificado-contra-git: {sha} · {nombre} · {hoy}")
        filas.append(f"| {nombre} | `{ref}` ({sha}, {ult}) | {actual} | {adelante} por delante, {atras} por detrás | {sucios} sin commitear |")
    print("\n".join(sellos) + ("\n" if sellos else ""))
    print("| Repo | Referencia | Rama actual | Frente a la referencia | Árbol de trabajo |\n|---|---|---|---|---|")
    print("\n".join(filas))
    print("\nLa referencia manda: una afirmación sobre «lo que existe» se contrasta contra ella, no contra la rama local de turno.")
    print("Siguiente: pega las líneas `verificado-contra-git` al principio del análisis y revísalas después con scripts/sellos.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
