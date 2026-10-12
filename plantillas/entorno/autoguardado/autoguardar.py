#!/usr/bin/env python3
"""Autoguardado al cerrar la sesión: commit local y, solo si lo activas, subida al remoto.

Orden de seguridad (si algo falla, se detiene y AVISA; nunca sale con error para no romper la sesión):
  1. hay cambios        2. escaneo de secretos limpio        3. commit con mensaje fechado
  4. subida SOLO si [autoguardado].subir = true, estás en la rama configurada y existe remoto. Nunca usa --force.
Lee la configuración de entorno.toml.
"""
import datetime as dt
import pathlib
import subprocess
import sys
import tomllib

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def git(*a):
    return subprocess.run(["git", *a], cwd=RAIZ, capture_output=True, text=True)


def avisa(msg):
    print(f"[autoguardado] {msg}", file=sys.stderr)


def main():
    try:
        cfg = tomllib.loads((RAIZ / "entorno.toml").read_text(encoding="utf8")).get("autoguardado", {})
    except (OSError, tomllib.TOMLDecodeError) as e:
        avisa(f"no pude leer entorno.toml: {e}")
        return 0
    if not cfg.get("commit", True):
        return 0
    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        avisa("esto no es un repositorio git; nada que guardar")
        return 0
    if not git("status", "--porcelain").stdout.strip():
        return 0
    escaneo = RAIZ / "scripts" / "escanear-secretos.py"
    if escaneo.exists():
        r = subprocess.run([sys.executable, str(escaneo)], cwd=RAIZ, capture_output=True, text=True)
        if r.returncode != 0:
            avisa("NO se guardó: el escaneo de secretos encontró algo. Revísalo:\n" + r.stdout.strip())
            return 0
    git("add", "-A")
    c = git("commit", "-q", "-m", f"auto-guardado {dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%MZ}")
    if c.returncode != 0:
        avisa("el commit falló: " + (c.stderr or c.stdout).strip()[:300])
        return 0
    if not cfg.get("subir", False):
        return 0
    rama = cfg.get("rama", "main")
    actual = git("branch", "--show-current").stdout.strip()
    if actual != rama:
        avisa(f"commit hecho pero NO se subió: estás en «{actual}» y la rama configurada es «{rama}»")
        return 0
    if not git("remote").stdout.strip():
        avisa("commit hecho pero no hay remoto configurado")
        return 0
    p = git("push", "-q", "origin", rama)
    if p.returncode != 0:
        avisa("commit hecho pero la subida falló (red o permisos): " + (p.stderr or "").strip()[:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
