#!/usr/bin/env python3
"""Comprobación de versión del instalador (R26). SOLO LECTURA, SIN RED.

Compara la `VERSION` del harness con la última etiqueta local de git y, con --instancia, con el `harness.lock` de la instancia.
Formato de `harness.lock` (TOML, en la raíz de la instancia):
    version = "X.Y.Z"
    fuente  = "<url-o-ruta del harness>"
Veredictos: al día | la instancia fija una versión anterior (+ commits de por medio si hay git) | harness.lock inválido | sin harness.lock.
Modo con red (consultar la fuente remota por versiones nuevas): PENDIENTE, no implementado.
Uso: python3 comprobar-version.py [--harness RUTA] [--instancia RUTA] [--json]
Salida: 0 al día/informativo, 1 atrasada, 2 lock inválido o VERSION ilegible.
"""
import argparse, json, pathlib, re, subprocess, sys, tomllib

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def git(raiz, *a):
    try:
        p = subprocess.run(["git", "-C", str(raiz), *a], capture_output=True, text=True, timeout=30)
        return p.stdout.strip() if p.returncode == 0 else ""
    except Exception:
        return ""


def ver(s):
    m = SEMVER.match((s or "").strip().lstrip("v"))
    return tuple(int(x) for x in m.groups()) if m else None


def leer_lock(ruta):
    try:
        d = tomllib.loads(ruta.read_text(encoding="utf8"))
    except (tomllib.TOMLDecodeError, OSError) as e:
        return None, f"no se puede leer: {e}"
    if not isinstance(d.get("version"), str) or ver(d["version"]) is None:
        return None, "falta `version = \"X.Y.Z\"` o no es X.Y.Z"
    if not isinstance(d.get("fuente"), str) or not d["fuente"].strip():
        return None, "falta `fuente = \"<url-o-ruta>\"`"
    return d, ""


def comprobar(harness, instancia=None):
    r = {"estado": "al_dia", "mensajes": [], "codigo": 0}
    vf = harness / "VERSION"
    actual = vf.read_text().strip() if vf.is_file() else ""
    if ver(actual) is None:
        r.update(estado="version_ilegible", codigo=2)
        r["mensajes"].append(f"VERSION del harness ausente o ilegible ({actual!r}).")
        return r
    r["version_harness"] = actual
    r["mensajes"].append(f"Harness {actual}.")
    tags = [t for t in git(harness, "tag", "--list", "--sort=-v:refname").splitlines() if ver(t)]
    if tags:
        r["ultima_etiqueta"] = tags[0]
        if ver(tags[0]) > ver(actual):
            r["mensajes"].append(f"Aviso: la última etiqueta local ({tags[0]}) es más nueva que VERSION ({actual}).")
        elif ver(tags[0]) < ver(actual):
            r["mensajes"].append(f"VERSION ({actual}) es posterior a la última etiqueta local ({tags[0]}): versión sin etiquetar.")
        else:
            r["mensajes"].append(f"Coincide con la última etiqueta local ({tags[0]}).")
    else:
        r["mensajes"].append("Sin etiquetas de versión locales en git (se usa solo VERSION).")
    if instancia is None:
        return r
    lock = instancia / "harness.lock"
    if not lock.is_file():
        r["estado"] = "sin_lock"
        r["mensajes"].append(f"La instancia no tiene harness.lock. Para crearlo, escribe en {lock} (esta herramienta no lo crea):\n"
                             f'    version = "{actual}"\n    fuente  = "<url-o-ruta del harness>"')
        return r
    d, err = leer_lock(lock)
    if d is None:
        r.update(estado="lock_invalido", codigo=2)
        r["mensajes"].append(f"harness.lock inválido: {err}.")
        return r
    fijada = d["version"].strip().lstrip("v")
    r["version_instancia"] = fijada
    if ver(fijada) == ver(actual):
        r["mensajes"].append(f"Al día: la instancia fija {fijada}.")
    elif ver(fijada) < ver(actual):
        r.update(estado="atrasada", codigo=1)
        r["mensajes"].append(f"La instancia fija una versión anterior ({fijada}); el harness está en {actual}.")
        for ref in (f"v{fijada}", fijada):
            if git(harness, "rev-parse", "--verify", "-q", ref + "^{commit}"):
                log = git(harness, "log", "--oneline", f"{ref}..HEAD")
                r["cambios"] = log.splitlines()
                r["mensajes"].append("Qué cambió (commits de por medio):\n" + "\n".join("    " + l for l in r["cambios"]) if log else "Sin commits de por medio.")
                break
        else:
            r["mensajes"].append("No hay etiqueta local de esa versión: no se puede listar qué cambió.")
    else:
        r["estado"] = "instancia_adelantada"
        r["mensajes"].append(f"La instancia fija {fijada}, más nueva que este harness ({actual}): actualiza el harness local.")
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--harness", default=str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--instancia")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    inst = pathlib.Path(a.instancia).expanduser().resolve() if a.instancia else None
    if inst and not inst.is_dir():
        sys.exit(f"No existe {inst}")
    r = comprobar(pathlib.Path(a.harness).expanduser().resolve(), inst)
    print(json.dumps(r, ensure_ascii=False, indent=2) if a.json else "\n".join(r["mensajes"]))
    return r["codigo"]


if __name__ == "__main__":
    sys.exit(main())
