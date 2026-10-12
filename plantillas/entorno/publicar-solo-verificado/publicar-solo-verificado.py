#!/usr/bin/env python3
"""Hook PreToolUse (Bash): NO se publica un texto que no pasó la verificación.

Cubre los comandos de [publicar].comandos (por defecto gh pr create/edit/comment/review/merge, gh issue create/comment/edit y
gh release create/edit). Exige la marca del texto EXACTO (scripts/verificar-publicacion.py) con el nivel de [publicar].exigir_nivel.

Defensas, cada una nacida de un intento real de saltársela:
  - Entiende la línea de comandos (ver _comandos.py): encadenados, `bash -c "..."`, `$(...)`.
  - Un cuerpo inline (--body) o por entrada estándar no se puede verificar: se rechaza con la instrucción de usar --body-file.
  - Si el archivo del cuerpo aparece en OTRA parte de la misma línea (`echo x > v.md && gh pr create --body-file v.md`), se rechaza:
    el hook ve el archivo antes de que el comando lo cambie, así que la marca no demostraría nada.
Si el propio hook falla por un error interno, DEJA PASAR: solo bloquea un texto sin marca. No toca lecturas (gh pr view, list...).
"""
import importlib.util
import json
import os
import pathlib
import sys
import tomllib

import _comandos as c

POR_DEFECTO = ["gh pr create", "gh pr edit", "gh pr comment", "gh pr review", "gh pr merge", "gh issue create",
               "gh issue comment", "gh issue edit", "gh release create", "gh release edit"]
CUERPO_ARCHIVO = ("--body-file", "-F", "--notes-file")
CUERPO_INLINE = ("--body", "-b", "--notes", "-n")


def denegar(razon):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": razon}}))
    sys.exit(0)


def cuerpo_de(args):
    """(archivo, inline) de los argumentos de un comando de publicación."""
    archivo, inline = None, False
    for k, t in enumerate(args):
        sig = args[k + 1] if k + 1 < len(args) else None
        if t in CUERPO_ARCHIVO and sig is not None:
            archivo = sig
        elif t in CUERPO_INLINE and sig is not None:
            inline = True
        elif t.startswith("--") and "=" in t:
            nombre, valor = t.split("=", 1)
            if nombre in CUERPO_ARCHIVO:
                archivo = valor
            elif nombre in CUERPO_INLINE:
                inline = True
    return archivo, inline


def main():
    evento = c.leer_evento()
    cmd = c.comando_de(evento)
    if "gh" not in cmd:
        return
    if c.demasiado_largo(cmd):
        denegar("La línea de comandos es demasiado larga para verificarla. Escribe el cuerpo en un archivo corto, verifícalo y publica con --body-file.")
    raiz = c.raiz_del_entorno()
    cwd = pathlib.Path(evento.get("cwd") if isinstance(evento.get("cwd"), str) and evento.get("cwd") else os.getcwd())
    try:
        cfg = tomllib.loads((raiz / "entorno.toml").read_text(encoding="utf8")).get("publicar", {})
    except (OSError, tomllib.TOMLDecodeError):
        cfg = {}
    comandos = [x.split() for x in cfg.get("comandos", POR_DEFECTO)]
    sents = c.sentencias(cmd)
    publicaciones = []
    for idx, s in enumerate(sents):
        prog, resto = c.programa(s)
        if prog == "gh" and any(resto[:len(p) - 1] == p[1:] for p in comandos):
            publicaciones.append((idx, resto))
    if not publicaciones:
        return
    spec = importlib.util.spec_from_file_location("verificar_publicacion", raiz / "scripts" / "verificar-publicacion.py")
    motor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(motor)
    exigido = int(cfg.get("exigir_nivel", 1))
    for idx, args in publicaciones:
        archivo, inline = cuerpo_de(args)
        if archivo == "-" or inline:
            denegar("Un cuerpo inline o por entrada estándar no se puede verificar. Escríbelo en un archivo, "
                    "corre `python3 scripts/verificar-publicacion.py revisar <archivo>` y publica con --body-file <archivo>.")
        if archivo is None:
            continue  # sin cuerpo (por ejemplo --fill o --approve): no hay texto que verificar
        for j, otra in enumerate(sents):
            if j != idx and any(archivo in t for t in otra):
                denegar(f"El archivo del cuerpo ({archivo}) aparece en otra parte de la misma línea de comandos. No lo modifiques ni lo "
                        "generes en el mismo comando que publica: la verificación se comprueba antes de ejecutar y no sería válida. "
                        "Prepáralo en un comando aparte, verifícalo y publica después.")
        p = pathlib.Path(archivo)
        p = p if p.is_absolute() else cwd / p  # una ruta relativa es relativa al directorio donde corre el comando
        if not p.is_file():
            denegar(f"El archivo del cuerpo no existe o no es un archivo: {archivo}")
        texto = p.read_text(encoding="utf8", errors="replace")
        m = motor.leer_marca(texto)
        nivel = m["nivel"] if m else 0
        if nivel < exigido:
            paso = "revisar" if nivel < 1 else "confirmar (revisión independiente)"
            denegar(f"El texto de {archivo} no tiene verificación de nivel {exigido} vigente (tiene {nivel}). "
                    f"Corre `python3 scripts/verificar-publicacion.py {paso} {archivo}`. Si editas el texto, la marca se invalida.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)  # un error interno nunca bloquea
    sys.exit(0)
