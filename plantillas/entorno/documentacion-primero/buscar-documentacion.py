#!/usr/bin/env python3
"""Busca términos en la documentación del repo ANTES de leer código o datos. Solo lectura.

Uso: buscar-documentacion.py "término" ["otro término" ...] [--max N]
Dónde busca: las rutas de [documentacion].rutas en entorno.toml (por defecto docs/ y knowledge/).
"""
import argparse
import pathlib
import sys
import tomllib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
EXT = {".md", ".txt", ".toml", ".rst", ".adoc"}


def rutas():
    try:
        cfg = tomllib.loads((RAIZ / "entorno.toml").read_text(encoding="utf8"))
        return cfg.get("documentacion", {}).get("rutas", ["docs", "knowledge"])
    except (OSError, tomllib.TOMLDecodeError):
        return ["docs", "knowledge"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("terminos", nargs="+")
    ap.add_argument("--max", type=int, default=8, help="coincidencias por término")
    a = ap.parse_args()
    archivos = []
    for r in rutas():
        base = (RAIZ / r)
        if base.is_file():
            archivos.append(base)
        elif base.is_dir():
            archivos += [p for p in sorted(base.rglob("*")) if p.is_file() and p.suffix in EXT]
    if not archivos:
        print("No hay documentación en las rutas configuradas: eso también es un dato. Pregunta a la persona.")
        print("Siguiente: si la documentación vive en otra carpeta, agrégala en [documentacion].rutas de entorno.toml.")
        return 0
    for t in a.terminos:
        print(f"### {t}")
        n = 0
        for p in archivos:
            try:
                lineas = p.read_text(encoding="utf8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for i, l in enumerate(lineas, 1):
                if t.lower() in l.lower():
                    print(f"  {p.relative_to(RAIZ)}:{i}: {l.strip()[:150]}")
                    n += 1
                    if n >= a.max:
                        break
            if n >= a.max:
                break
        if n == 0:
            print("  (sin coincidencias: prueba sinónimos antes de concluir que no está documentado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
