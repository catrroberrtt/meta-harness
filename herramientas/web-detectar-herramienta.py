#!/usr/bin/env python3
"""Detecta si hay una herramienta externa de generación de webs (hoy: open-design, orden `od`) SIN ejecutarla ni usar la red.
Solo mira variables de entorno, el PATH y los primeros bytes del archivo encontrado. Sale siempre con 0:
«no disponible» no es un error, el adaptador `diseno-web` pasa al modo manual.
Aviso: en casi todos los sistemas `od` es el volcado octal de coreutils; por eso no basta con que exista en el PATH.
Uso: python3 web-detectar-herramienta.py [--json]
Variable opcional: HARNESS_WEB_HERRAMIENTA=<ruta o nombre> para fijar la herramienta que decide la instancia."""
import json, os, shutil, sys

HUELLAS = (b"open-design", b"od.mjs", b"@open-design")


def inspeccionar(ruta):
    """Devuelve ('si'|'no'|'incierto', motivo) para un ejecutable, sin ejecutarlo."""
    real = os.path.realpath(ruta)
    try:
        with open(real, "rb") as f:
            cab = f.read(4096)
    except OSError as e:
        return "incierto", f"no se pudo leer {real}: {e.strerror}"
    if cab.startswith(b"\x7fELF") or cab.startswith(b"MZ") or cab[:4] in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"):
        return "no", f"{real} es un programa nativo (en un sistema normal, el volcado octal `od` de coreutils)"
    if any(h in cab for h in HUELLAS) or any(h.decode() in real for h in HUELLAS):
        return "si", f"{real} parece la CLI de open-design (no ejecutada, no verificado)"
    return "incierto", f"{real} es un script sin huella reconocible: confirmar con la persona"


def detectar(entorno=None, buscar=shutil.which):
    entorno = os.environ if entorno is None else entorno
    candidatos = []
    fijada = entorno.get("HARNESS_WEB_HERRAMIENTA", "").strip()
    if fijada:
        ruta = fijada if os.path.sep in fijada else buscar(fijada)
        candidatos.append(("variable HARNESS_WEB_HERRAMIENTA", ruta, fijada))
    ruta_od = buscar("od")
    candidatos.append(("orden `od` en el PATH", ruta_od, "od"))
    for origen, ruta, nombre in candidatos:
        if not ruta or not os.path.exists(ruta):
            continue
        estado, motivo = inspeccionar(ruta)
        if estado == "si" or (estado == "incierto" and origen.startswith("variable")):
            return {"disponible": "sí", "herramienta": "open-design", "ruta": ruta, "motivo": f"{origen}: {motivo}", "modo": "externo"}
        if estado == "incierto":
            return {"disponible": "no", "herramienta": None, "ruta": ruta, "motivo": f"{origen}: {motivo}", "modo": "manual"}
    return {"disponible": "no", "herramienta": None, "ruta": None, "modo": "manual",
            "motivo": "no se encontró la herramienta: se usa el modo manual con plantillas/web/"}


def main(argv=None):
    r = detectar()
    if "--json" in (argv if argv is not None else sys.argv[1:]):
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"disponible: {r['disponible']} · modo: {r['modo']} · {r['motivo']}")
        if r["disponible"] == "sí":
            print("Antes de usarla: mostrar a la persona qué datos envía y esperar su confirmación (adaptadores/diseno-web/README.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
