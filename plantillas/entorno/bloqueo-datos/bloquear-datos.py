#!/usr/bin/env python3
"""Hook PreToolUse (Bash): el agente no escribe en bases de datos ni se conecta a ambientes que no son locales.

Es una BARRERA, no una garantía: no puede ver SQL que llega por canales que no se leen (una variable, un script remoto). La garantía real es
que el usuario de base de datos del agente sea de SOLO LECTURA. Este hook evita el descuido y deja rastro del intento.

Qué hace, según [datos] de entorno.toml:
  - Un cliente de base de datos (mysql, psql, mongosh, redis-cli...) hacia un host que no está en `hosts_permitidos` -> se rechaza.
  - Con `solo_lectura = true` (por defecto): escribir (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT...) se rechaza, venga la
    consulta en la línea (-e, -c, --eval, heredoc) o de un archivo redirigido (`< archivo.sql`, `source`, `-f`), que se lee y se revisa.
  - Herramientas que escriben por diseño (mysqlimport, pg_restore, mongorestore...) se rechazan con `solo_lectura`.
  - Entiende la línea de comandos (ver _comandos.py): `cd`, `bash -c`, `$(...)`, `docker exec <contenedor> mysql ...`.
Un error interno deja pasar (nunca bloquea por sí mismo). Una línea demasiado larga para analizar con un cliente dentro se rechaza.
"""
import json
import os
import pathlib
import re
import sys
import tomllib

import _comandos as c

CLIENTES = {"mysql", "mariadb", "psql", "mongosh", "mongo", "sqlite3", "redis-cli", "sqlcmd", "cockroach", "clickhouse-client"}
ESCRITORES = {"mysqlimport", "pg_restore", "mongorestore", "mongoimport", "mysqladmin", "dropdb", "createdb", "dropuser", "createuser"}
CONTENEDORES = {"docker", "podman", "kubectl", "nerdctl"}
ESCRITURA = re.compile(r"\b(?:INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|REPLACE|RENAME|MERGE|CALL|LOAD\s+DATA|FLUSHALL|FLUSHDB|"
                       r"SET\s+GLOBAL|SHUTDOWN|CONFIG\s+SET|insertMany|insertOne|updateOne|updateMany|deleteOne|deleteMany|dropDatabase|"
                       r"dropCollection|bulkWrite)\b|\$out\b|\$merge\b|\.remove\(", re.I)
LECTURA_QUE_PARECE_ESCRITURA = re.compile(r"\bSHOW\s+CREATE\s+\w+|\bEXPLAIN\b|\bON\s+UPDATE\b|\bON\s+DELETE\b", re.I)


def escribe(texto):
    """La primera palabra de escritura que quede tras quitar lecturas que la contienen (SHOW CREATE TABLE, EXPLAIN...), o None."""
    m = ESCRITURA.search(LECTURA_QUE_PARECE_ESCRITURA.sub(" ", texto))
    return m.group(0) if m else None


HOST_FLAGS = ("-h", "--host", "--hostname")
LOCALES = ("127.0.0.1", "localhost", "::1")


def denegar(razon):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": razon}}))
    sys.exit(0)


def config(raiz):
    try:
        return tomllib.loads((raiz / "entorno.toml").read_text(encoding="utf8")).get("datos", {})
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def hosts_de(resto):
    """Hosts a los que apunta un cliente: -h X, -hX, --host X, --host=X y URIs (mysql://, postgresql://, mongodb://, redis://)."""
    out = []
    for i, t in enumerate(resto):
        if t in HOST_FLAGS and i + 1 < len(resto):
            out.append(resto[i + 1])
        elif t.startswith("--host=") or t.startswith("--hostname="):
            out.append(t.split("=", 1)[1])
        elif re.fullmatch(r"-h[^\s-].*", t) and not t.startswith("--"):
            out.append(t[2:])
        m = re.match(r"^(?:\w+\+?\w*)://(?:[^/@\s]*@)?(\[[^\]]+\]|[^/:?\s]+)", t)
        if m:
            out.append(m.group(1).strip("[]"))
        for u in re.findall(r"(?:mongodb(?:\+srv)?|postgres(?:ql)?|mysql|redis|rediss)://(?:[^/@\s'\"]*@)?(\[[^\]]+\]|[^/:?\s'\"]+)", t):
            out.append(u.strip("[]"))
    return out


def archivos_de_entrada(sentencia, cwd):
    """Archivos que alimentan al cliente: `< archivo`, `-f archivo`, `--file=archivo`, `source archivo`, `\\i archivo`. Devuelve rutas y si hay una no legible."""
    rutas, ilegible = [], False
    for i, t in enumerate(sentencia):
        sig = sentencia[i + 1] if i + 1 < len(sentencia) else None
        cand = None
        if t == "<" and sig:
            cand = sig
        elif t in ("-f", "--file", "--input") and sig:
            cand = sig
        elif t.startswith(("--file=", "--input=")):
            cand = t.split("=", 1)[1]
        elif t in ("source", "\\i", ".") and sig:
            cand = sig
        if cand:
            p = pathlib.Path(os.path.expanduser(cand))
            p = p if p.is_absolute() else pathlib.Path(cwd) / p
            rutas.append(p)
    return rutas, ilegible


def revisar_cliente(nombre, resto, cfg, cwd, completa):
    hosts = [h for h in hosts_de(resto)] or ["localhost"]
    permitidos = set(cfg.get("hosts_permitidos", LOCALES))
    for h in hosts:
        if h not in permitidos:
            denegar(f"`{nombre}` apunta al host «{h}», que no está en [datos].hosts_permitidos de entorno.toml. El agente no se conecta a ambientes "
                    "remotos: entrégale el comando a la persona para que lo corra ella.")
    if not cfg.get("solo_lectura", True):
        return
    texto = " ".join(resto)
    if escribe(texto):
        denegar(f"`{nombre}` con una instrucción que escribe o cambia el esquema ({escribe(texto)}). El agente solo lee: "
                "entrégale el SQL a la persona. (Para cambiarlo, [datos].solo_lectura en entorno.toml.)")
    archivos, _ = archivos_de_entrada(resto, cwd)
    for p in archivos:
        try:
            if p.stat().st_size > 2_000_000:
                denegar(f"`{nombre}` lee {p.name}, demasiado grande para revisar su contenido: entrégalo a la persona.")
            contenido = p.read_text(encoding="utf8", errors="replace")
        except OSError:
            denegar(f"`{nombre}` lee {p.name} y no se puede leer para comprobar que solo consulta. Entrégalo a la persona.")
        if escribe(contenido):
            denegar(f"`{nombre}` ejecutaría {p.name}, que contiene una instrucción que escribe ({escribe(contenido)}). El agente solo lee.")


def main():
    evento = c.leer_evento()
    cmd = c.comando_de(evento)
    if not cmd or not re.search(r"mysql|maria|psql|mongo|sqlite|redis|sqlcmd|cockroach|clickhouse|pg_|dropdb|createdb|dropuser|createuser|docker|podman|kubectl|nerdctl", cmd):
        return
    raiz = c.raiz_del_entorno()
    cfg = config(raiz)
    cwd = evento.get("cwd") if isinstance(evento.get("cwd"), str) and evento.get("cwd") else os.getcwd()
    if c.demasiado_largo(cmd):
        if re.search(r"\b(mysql|psql|mongosh|redis-cli)\b", cmd):
            denegar("La línea de comandos es demasiado larga para revisarla y menciona un cliente de base de datos. Guarda la consulta en un archivo corto.")
        return
    for sentencia, donde in c.con_directorio(cmd, cwd):
        prog, resto = c.programa(sentencia)
        if prog in CONTENEDORES:  # docker exec <contenedor> mysql ...: el cliente va dentro; el host del contenedor se asume local
            for k, t in enumerate(resto):
                if t.rsplit("/", 1)[-1] in CLIENTES | ESCRITORES:
                    prog, resto = t.rsplit("/", 1)[-1], resto[k + 1:]
                    break
        if prog in ESCRITORES and cfg.get("solo_lectura", True):
            denegar(f"`{prog}` escribe en la base de datos por diseño. El agente solo lee: entrégale el comando a la persona.")
        if prog in CLIENTES:
            revisar_cliente(prog, resto, cfg, donde, cmd)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)  # un error interno nunca bloquea
    sys.exit(0)
