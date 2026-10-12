#!/usr/bin/env python3
"""Hook PreToolUse (Bash): NO se publica un texto que no pasó la verificación.

Cubre los comandos de [publicar].comandos (por defecto gh pr create/edit/comment, gh issue create/comment y gh release create).
Exige la marca del texto EXACTO (scripts/verificar-publicacion.py) con el nivel de [publicar].exigir_nivel.
Un cuerpo inline (--body) o por entrada estándar no se puede verificar: se rechaza con la instrucción de usar --body-file.
Si el propio hook falla por un error interno, DEJA PASAR: solo bloquea un texto sin marca. No toca lecturas (gh pr view, list...).
"""
import importlib.util
import json
import os
import pathlib
import shlex
import sys
import tomllib

POR_DEFECTO = ["gh pr create", "gh pr edit", "gh pr comment", "gh issue create", "gh issue comment", "gh release create"]
CUERPO_ARCHIVO = ("--body-file", "-F", "--notes-file")
CUERPO_INLINE = ("--body", "-b", "--notes", "-n")


def denegar(razon):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": razon}}))
    sys.exit(0)


def tramos(cmd, comandos):
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        toks = cmd.split()
    out = []
    for c in comandos:
        pal = c.split()
        for i in range(len(toks) - len(pal) + 1):
            if toks[i:i + len(pal)] == pal:
                j = i + len(pal)
                while j < len(toks) and toks[j] not in ("&&", ";", "||", "|", "&", ";;"):
                    j += 1
                out.append(toks[i:j])
    return out


def main():
    d = json.load(sys.stdin)
    cmd = (d.get("tool_input") or {}).get("command", "") or ""
    raiz = pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or d.get("cwd") or os.getcwd())
    try:
        cfg = tomllib.loads((raiz / "entorno.toml").read_text(encoding="utf8")).get("publicar", {})
    except (OSError, tomllib.TOMLDecodeError):
        cfg = {}
    spec = importlib.util.spec_from_file_location("verificar_publicacion", raiz / "scripts" / "verificar-publicacion.py")
    motor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(motor)
    exigido = int(cfg.get("exigir_nivel", 1))
    for tr in tramos(cmd, cfg.get("comandos", POR_DEFECTO)):
        archivo, inline = None, False
        for k, t in enumerate(tr):
            sig = tr[k + 1] if k + 1 < len(tr) else None
            if t in CUERPO_ARCHIVO and sig:
                archivo = sig
            elif t in CUERPO_INLINE and sig:
                inline = True
            elif any(t.startswith(p + "=") for p in CUERPO_ARCHIVO if p.startswith("--")):
                archivo = t.split("=", 1)[1]
            elif any(t.startswith(p + "=") for p in CUERPO_INLINE if p.startswith("--")):
                inline = True
        if archivo == "-" or inline:
            denegar("Un cuerpo inline o por entrada estándar no se puede verificar. Escríbelo en un archivo, "
                    "corre `python3 scripts/verificar-publicacion.py revisar <archivo>` y publica con --body-file <archivo>.")
        if archivo:
            p = pathlib.Path(archivo)
            p = p if p.is_absolute() else raiz / p
            if not p.is_file():
                denegar(f"El archivo del cuerpo no existe: {archivo}")
            texto = p.read_text(encoding="utf8")
            m = motor.leer_marca(texto)
            nivel = m["nivel"] if m else 0
            if nivel < exigido:
                paso = "revisar" if nivel < 1 else "confirmar (revisión independiente)"
                denegar(f"El texto de {archivo} no tiene verificación de nivel {exigido} vigente (tiene {nivel}). "
                        f"Corre `python3 scripts/verificar-publicacion.py {paso} {archivo}`. Si editas el texto, la marca se invalida.")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)  # un error interno nunca bloquea
