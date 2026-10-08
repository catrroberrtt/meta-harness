#!/usr/bin/env python3
"""Quita de un comando los tramos que solo LEEN texto, para que el hook de RD-1 no confunda el
contenido que se busca o se imprime con una ejecucion contra la base.

Dos reglas, las dos con evidencia del 2026-09-16:

1. Se parte respetando las COMILLAS. La primera version partia por '|' a secas y el patron
   'cliente_cmd\\|cliente -h' de un grep se rompia en dos, dejando un fragmento que arrancaba
   con el nombre del cliente: el hook lo leia como una conexion. Un patron de busqueda no es
   un comando.

2. Si ALGUN tramo de una tuberia invoca al cliente, la tuberia se conserva ENTERA. Asi
   `grep x archivo.sql | cliente base` sigue siendo revisado con el nombre del archivo a la
   vista, en vez de perderlo al descartar el `grep`.
"""
import sys

LECTURA = {
    "grep", "egrep", "fgrep", "rg", "ag", "ack", "sed", "awk", "gawk", "cat", "bat",
    "head", "tail", "less", "more", "wc", "sort", "uniq", "cut", "tr", "nl", "rev",
    "find", "fd", "ls", "tree", "file", "stat", "diff", "cmp", "basename", "dirname",
    "echo", "printf", "cd", "pwd", "which", "git",
}
CLIENTES = {"mysql", "psql", "mysqlsh", "mariadb"}


def partir(texto, separadores):
    """Parte en los separadores dados, ignorando lo que este entre comillas."""
    partes, actual, comilla, i = [], [], None, 0
    while i < len(texto):
        c = texto[i]
        if comilla:
            actual.append(c)
            if c == comilla:
                comilla = None
            elif c == "\\" and i + 1 < len(texto):
                actual.append(texto[i + 1]); i += 1
        elif c in ("'", '"'):
            comilla = c; actual.append(c)
        else:
            for sep in separadores:
                if texto.startswith(sep, i):
                    partes.append("".join(actual)); actual = []
                    i += len(sep) - 1
                    break
            else:
                actual.append(c)
        i += 1
    partes.append("".join(actual))
    return partes


def primer_comando(tramo):
    """Nombre del ejecutable del tramo, salteando 'sudo' y asignaciones VAR=valor."""
    tokens = partir(tramo.strip(), [" ", "\t"])
    tokens = [t for t in tokens if t]
    i = 0
    while i < len(tokens) and (tokens[i] in ("sudo", "time", "nohup") or "=" in tokens[i]):
        i += 1
    return tokens[i].strip("\"'").split("/")[-1] if i < len(tokens) else ""


texto = sys.stdin.read()
conservado = []
for tuberia in partir(texto, ["&&", "||", ";", "\n"]):
    tramos = partir(tuberia, ["|"])
    if any(primer_comando(t) in CLIENTES for t in tramos):
        conservado.append(tuberia)          # regla 2: no se toca
        continue
    utiles = [t for t in tramos if primer_comando(t) not in LECTURA]
    if utiles:
        conservado.append(" | ".join(utiles))
sys.stdout.write(" ; ".join(conservado))
