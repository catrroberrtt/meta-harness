#!/usr/bin/env python3
"""Hook PreToolUse (Bash): un PR no se crea con un cuerpo que no tiene las secciones que su TIPO exige.

Cada equipo declara sus tipos en entorno.toml: qué es un «pase a producción», una «corrección de observaciones» o un «primer PR», cómo se
reconoce (por la rama base o por el título) y qué secciones lleva. Así el formato deja de depender de que alguien se acuerde de releer la guía:
[[pr.tipos]]
nombre = "pase a producción"
cuando_base = "^main$"
secciones = ["Resumen del cambio", "Plan de despliegue", "Plan de respaldo"]

Reconoce el tipo por --base o --title (el primero que coincide), lee el cuerpo de --body-file y exige un encabezado por sección (se ignora la
numeración «2. » y las mayúsculas). Si ningún tipo coincide, deja pasar: sin tipos configurados el hook no hace nada. Entiende la línea de
comandos (ver _comandos.py). Un error interno deja pasar. Un cuerpo inline no se puede revisar: se rechaza (igual que el módulo de publicación).
"""
import json
import os
import pathlib
import re
import sys
import tomllib

import _comandos as c


def denegar(razon):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": razon}}))
    sys.exit(0)


def valor(args, cortas, larga):
    for i, t in enumerate(args):
        if t in cortas + (larga,) and i + 1 < len(args):
            return args[i + 1]
        if t.startswith(larga + "="):
            return t.split("=", 1)[1]
    return None


def encabezados(texto):
    """Encabezados del documento sin la numeración ni el formato: «## 2. Plan de despliegue (opcional)» -> «plan de despliegue»."""
    out = set()
    for l in texto.splitlines():
        m = re.match(r"^\s{0,3}#{1,6}\s*(?:\d+[\.\)]\s*)?(.+?)\s*#*\s*$", l)
        if m:
            out.add(re.sub(r"\s*\(.*\)\s*$", "", re.sub(r"[*_`]", "", m.group(1))).strip().rstrip(":").lower())
    return out


def tipo_de(tipos, base, titulo):
    for t in tipos:
        try:
            if t.get("cuando_base") and base is not None and re.search(t["cuando_base"], base):
                return t
            if t.get("cuando_titulo") and titulo is not None and re.search(t["cuando_titulo"], titulo):
                return t
        except re.error:
            continue
    return None


def main():
    evento = c.leer_evento()
    cmd = c.comando_de(evento)
    if "gh" not in cmd or c.demasiado_largo(cmd):
        return
    raiz = c.raiz_del_entorno()
    cwd = pathlib.Path(evento.get("cwd") if isinstance(evento.get("cwd"), str) and evento.get("cwd") else os.getcwd())
    try:
        tipos = tomllib.loads((raiz / "entorno.toml").read_text(encoding="utf8")).get("pr", {}).get("tipos", [])
    except (OSError, tomllib.TOMLDecodeError):
        return
    if not tipos:
        return
    for sentencia in c.sentencias(cmd):
        prog, resto = c.programa(sentencia)
        if prog != "gh" or resto[:2] != ["pr", "create"]:
            continue
        args = resto[2:]
        tipo = tipo_de(tipos, valor(args, ("-B",), "--base"), valor(args, ("-t",), "--title"))
        if not tipo:
            continue
        archivo = valor(args, ("-F",), "--body-file")
        if archivo is None:
            denegar(f"Este PR es de tipo «{tipo.get('nombre', '?')}» y exige un cuerpo con secciones: escríbelo en un archivo y usa --body-file.")
        p = pathlib.Path(archivo)
        p = p if p.is_absolute() else cwd / p
        try:
            presentes = encabezados(p.read_text(encoding="utf8", errors="replace"))
        except OSError:
            denegar(f"No se puede leer el cuerpo del PR ({archivo}).")
        faltan = [s for s in tipo.get("secciones", []) if s.lower() not in presentes]
        if faltan:
            denegar(f"Un PR de tipo «{tipo.get('nombre', '?')}» exige estas secciones y faltan en {archivo}: " + ", ".join(faltan)
                    + ". Cada una va como encabezado (por ejemplo «## " + faltan[0] + "»).")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
    sys.exit(0)
