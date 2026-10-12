#!/usr/bin/env python3
"""Sincronización automática del repositorio del harness: commit, traer, subir; con compuerta de publicación.

<!-- tipo: herramienta · capa: 4 -->

Es el mismo mecanismo que el repositorio privado de una instancia (commit automático al cerrar la sesión, fetch + merge antes de
subir, conflicto = abortar y avisar), con UNA diferencia que lo hace seguro para un remoto PÚBLICO: antes de commitear se pasa la
compuerta de publicación y, si falla, no se commitea ni se sube nada.

Compuerta (todas deben pasar; se guarda el resultado por contenido para no repetirla si nada cambió):
  1. `verificar.sh` del repositorio (sintaxis, pruebas, frescura y referencias prohibidas).
  2. `harness-escaneo-publico.py --sin-historial --exigir-listas` sobre todo el árbol: secretos, infraestructura, personas,
     términos prohibidos y archivos que no deben publicarse. Sin lista de términos prohibidos NO se publica (la protección estaría inactiva).

Garantías:
  - Solo sube la rama indicada (por defecto `main`) con refspec explícito: nunca `--all`, nunca etiquetas, nunca `--force`.
    Las ramas locales de trabajo (por ejemplo, historiales anteriores a una limpieza) no salen.
  - Si la rama actual no es la indicada, no hace nada.
  - Un conflicto al traer lo remoto aborta el merge y deja el commit local sin subir; nunca resuelve a ciegas.
  - Sale siempre con 0 en modo --silencioso y avisa con un mensaje JSON `systemMessage` (formato de los hooks de fin de sesión).
  - Las versiones y etiquetas (release con su suma) siguen siendo un acto deliberado: esto solo sincroniza `main`.

Uso:
  harness-sincronizar.py [--raiz CARPETA] [--rama main] [--simulacro] [--silencioso] [--sin-subir] [--solo-compuerta]
Salida: 0 bien o nada que hacer · 1 compuerta, conflicto o subida fallida (con --silencioso, siempre 0).
"""
import argparse, datetime, hashlib, json, os, pathlib, subprocess, sys, tempfile

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent
CACHE = pathlib.Path(os.environ.get("HARNESS_CACHE") or "~/.cache/meta-harness").expanduser() / "sync-gate.json"


class Alto(Exception):
    """La compuerta o git dijo que no: se avisa y no se toca nada más."""


def git(raiz, *args, check=True, entrada=None):
    r = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True, input=entrada,
                       env=dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0"))
    if check and r.returncode != 0:
        raise Alto(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()[:300]}")
    return r


def listas_prohibidas(raiz):
    rutas = [pathlib.Path(raiz) / ".prohibidos.txt"]
    env = os.environ.get("HARNESS_PROHIBIDOS")
    rutas.append(pathlib.Path(env).expanduser() if env else pathlib.Path("~/.config/meta-harness/prohibidos.txt").expanduser())
    terminos = []
    for f in rutas:
        if f.is_file():
            for l in f.read_text(encoding="utf8", errors="ignore").splitlines():
                l = l.strip()
                if l and not l.startswith("#") and l not in terminos:
                    terminos.append(l)
    return terminos


def huella(raiz):
    """Hash del contenido que se publicaría (archivos versionables modificados o nuevos + HEAD)."""
    h = hashlib.sha256()
    h.update(git(raiz, "rev-parse", "HEAD").stdout.encode())
    nombres = git(raiz, "ls-files", "-m", "-o", "--exclude-standard").stdout.split("\n")
    for n in sorted(x for x in nombres if x):
        p = pathlib.Path(raiz) / n
        h.update(n.encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def cache_ok(clave):
    try:
        return json.loads(CACHE.read_text(encoding="utf8")).get("ok") == clave
    except Exception:
        return False


def cache_guardar(clave):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({"ok": clave, "fecha": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}), encoding="utf8")


def compuerta(raiz, verificador, terminos):
    if not terminos:
        raise Alto("no hay lista de términos prohibidos (.prohibidos.txt, HARNESS_PROHIBIDOS o ~/.config/meta-harness/prohibidos.txt): "
                   "sin ella la protección de un repositorio público está inactiva, así que no se publica")
    if verificador:
        r = subprocess.run(["bash", str(verificador)], cwd=str(raiz), capture_output=True, text=True, timeout=900,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        if r.returncode != 0:
            cola = "\n".join((r.stdout + r.stderr).strip().splitlines()[-6:])
            raise Alto("verificar.sh falló, no se publica:\n" + cola)
    with tempfile.TemporaryDirectory(prefix="sync-") as t:
        lista = pathlib.Path(t) / "prohibidos.txt"
        lista.write_text("\n".join(terminos) + "\n", encoding="utf8")
        r = subprocess.run([sys.executable, str(AQUI / "harness-escaneo-publico.py"), str(raiz), "--sin-historial",
                            "--lista-prohibidos", str(lista), "--exigir-listas"], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        # nunca se reimprime el valor completo (el escáner ya lo enmascara); solo las primeras líneas
        cola = "\n".join((r.stdout + r.stderr).strip().splitlines()[:8])
        raise Alto("el escaneo de publicación encontró hallazgos, no se publica:\n" + cola)


def sincronizar(raiz, rama="main", simulacro=False, sin_subir=False, verificador="auto", solo_compuerta=False):
    raiz = pathlib.Path(raiz).resolve()
    if not (raiz / ".git").exists():
        return "no es un repositorio git", 0
    actual = git(raiz, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if actual != rama:
        return f"la rama actual es «{actual}», no «{rama}»: no se sincroniza", 0
    sucio = bool(git(raiz, "status", "--porcelain").stdout.strip())
    git(raiz, "fetch", "-q", "origin", rama, check=False)
    adelante = int(git(raiz, "rev-list", "--count", f"origin/{rama}..{rama}", check=False).stdout.strip() or 0)
    if not sucio and adelante == 0:
        # todavía puede haber algo remoto que traer
        atras = int(git(raiz, "rev-list", "--count", f"{rama}..origin/{rama}", check=False).stdout.strip() or 0)
        if atras == 0:
            return "nada que sincronizar", 0
    if solo_compuerta:
        v = (raiz / "verificar.sh") if verificador == "auto" else (pathlib.Path(verificador) if verificador else None)
        compuerta(raiz, v if (v and v.is_file()) else None, listas_prohibidas(raiz))
        return "la compuerta de publicación pasa; no se commiteó ni se subió nada (--solo-compuerta)", 0
    if simulacro:
        return f"simulacro: habría pasado la compuerta y sincronizado (cambios locales: {sucio}, commits sin subir: {adelante})", 0
    if sucio or adelante:
        clave = huella(raiz)
        if not cache_ok(clave):
            v = (raiz / "verificar.sh") if verificador == "auto" else (pathlib.Path(verificador) if verificador else None)
            compuerta(raiz, v if (v and v.is_file()) else None, listas_prohibidas(raiz))
            cache_guardar(clave)
    if sucio:
        git(raiz, "add", "-A")
        n = len([l for l in git(raiz, "diff", "--cached", "--name-only").stdout.splitlines() if l])
        git(raiz, "commit", "-q", "-m", f"chore(auto-sync): {n} archivo(s) · {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%dT%H:%MZ}")
        cache_guardar(huella(raiz))  # el mismo contenido, ya commiteado, sigue contando como verificado
    git(raiz, "fetch", "-q", "origin", rama)
    atras = int(git(raiz, "rev-list", "--count", f"{rama}..origin/{rama}").stdout.strip() or 0)
    if atras:
        m = git(raiz, "merge", "-q", "--no-edit", f"origin/{rama}", check=False)
        if m.returncode != 0:
            git(raiz, "merge", "--abort", check=False)
            raise Alto("conflicto al traer lo remoto: el commit local quedó SIN subir; revisar con git status / git log")
    if sin_subir:
        return "commit local hecho; --sin-subir: no se sube", 0
    git(raiz, "push", "-q", "origin", f"{rama}:{rama}")
    return "sincronizado", 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Commit + traer + subir con compuerta de publicación (solo la rama indicada)")
    ap.add_argument("--raiz", default=str(RAIZ))
    ap.add_argument("--rama", default="main")
    ap.add_argument("--simulacro", action="store_true")
    ap.add_argument("--sin-subir", action="store_true")
    ap.add_argument("--solo-compuerta", action="store_true", help="corre la compuerta de publicación y sale: no commitea ni sube")
    ap.add_argument("--silencioso", action="store_true")
    ap.add_argument("--verificador", default="auto", help="ruta del script de verificación; vacío para omitirlo (solo pruebas)")
    a = ap.parse_args(argv)
    try:
        msg, cod = sincronizar(a.raiz, a.rama, a.simulacro, a.sin_subir, a.verificador, a.solo_compuerta)
    except Alto as e:
        texto = f"⚠ auto-sync del harness: {e}"
        if a.silencioso:
            print(json.dumps({"systemMessage": texto}, ensure_ascii=False))
            return 0
        print(texto, file=sys.stderr)
        return 1
    except Exception as e:  # el hook de fin de sesión nunca debe romper la sesión
        if a.silencioso:
            return 0
        raise
    if not a.silencioso:
        print(msg)
    return cod


if __name__ == "__main__":
    sys.exit(main())
