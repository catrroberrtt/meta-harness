#!/usr/bin/env python3
"""Genera, a partir de una politica por proyecto (TOML), el hook de control de acceso a la base.

Uso:
    python3 generar-politicas.py <politicas.toml> --salida <directorio>

- Solo biblioteca estandar (Python >= 3.11, `tomllib`).
- Escribe SOLO dentro del directorio de salida. No instala nada, no registra el hook en ninguna
  configuracion, no toca la red ni ninguna base de datos.
- No asume ambientes, puertos, bases ni cuentas: todo sale de la politica. Una politica sin
  ambientes declarados (o vacia) falla con un mensaje que pide declararlos.

Salida:
    block-db-access.sh              el hook (desde hooks/plantillas/block-db-access.sh.tpl)
    filtrar-tramos-de-lectura.py    filtro auxiliar que el hook invoca (mismo directorio)

El esquema de la politica esta en politicas/ESQUEMA.md.
"""
import argparse
import os
import re
import shlex
import stat
import sys
import tomllib

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANTILLAS = os.path.join(RAIZ, "hooks", "plantillas")
TIPOS = {"local", "pruebas", "produccion"}
PERMISOS = {"permitida", "confirmar", "prohibida"}
CLAVES_PERMISOS = ("lectura", "escritura", "ddl", "migraciones")
PATRON_NOMBRE = re.compile(r"^[A-Za-z0-9_.*?\[\]-]+$")     # patrones de nombre de repo (fnmatch)
PATRON_IDENT = re.compile(r"^[A-Za-z0-9_.:-]+$")           # host, base, variable, archivo
CLIENTES_VALIDOS = re.compile(r"^[a-z0-9_]+$")


class ErrorPolitica(Exception):
    """Politica incompleta o invalida: se informa y no se genera nada."""


# ---------------------------------------------------------------------------------------
# Utilidades de escape (todo lo que viene de la politica se inserta ya escapado)
# ---------------------------------------------------------------------------------------
def sh_dq(texto):
    """Escapa para ir dentro de comillas dobles de bash."""
    return re.sub(r'(["$`\\])', r"\\\1", str(texto))


def sh_q(texto):
    return shlex.quote(str(texto))


def ere(texto):
    """Escapa para una expresion regular extendida (grep -E / re de Python)."""
    return re.sub(r"([.^$*+?()\[\]{}|\\])", r"\\\1", str(texto))


def exigir(cond, mensaje):
    if not cond:
        raise ErrorPolitica(mensaje)


def lista_texto(valor, ruta, patron=None, obligatoria=False):
    if valor is None:
        valor = []
    exigir(isinstance(valor, list) and all(isinstance(v, str) and v for v in valor),
           f"{ruta} debe ser una lista de textos no vacios.")
    exigir(not (obligatoria and not valor), f"{ruta} es obligatoria y esta vacia.")
    if patron:
        for v in valor:
            exigir(patron.match(v), f"{ruta}: valor no permitido {v!r}.")
    return valor


# ---------------------------------------------------------------------------------------
# Lectura y validacion de la politica
# ---------------------------------------------------------------------------------------
def cargar(ruta):
    try:
        with open(ruta, "rb") as f:
            politica = tomllib.load(f)
    except FileNotFoundError:
        raise ErrorPolitica(f"No existe el archivo de politica: {ruta}")
    except tomllib.TOMLDecodeError as e:
        raise ErrorPolitica(f"El archivo de politica no es TOML valido ({ruta}): {e}")
    return politica


def validar(p, ruta):
    datos = p.get("datos")
    ambientes = (datos or {}).get("ambientes") if isinstance(datos, dict) else None
    if not ambientes:
        raise ErrorPolitica(
            f"La politica '{ruta}' no declara ningun ambiente de datos ([[datos.ambientes]]).\n"
            "Este generador nunca asume un ambiente, un puerto ni una cuenta por defecto: "
            "declara al menos un ambiente (nombre, tipo, reconocimiento y permisos) y, en "
            "[datos], los hosts que cuentan como base local (hosts_locales). "
            "Ver politicas/ESQUEMA.md; el adopt del instalador puede proponer los que detecte.")
    exigir(isinstance(ambientes, list), "datos.ambientes debe ser una lista de tablas [[datos.ambientes]].")

    hosts_locales = lista_texto(datos.get("hosts_locales"), "datos.hosts_locales", PATRON_IDENT)
    exigir(hosts_locales,
           "datos.hosts_locales esta vacio: declara que hosts cuentan como base local "
           "(los que no esten ahi se tratan como remotos y se bloquean).")
    clientes = lista_texto(datos.get("clientes_sql"), "datos.clientes_sql", CLIENTES_VALIDOS)
    exigir(clientes, "datos.clientes_sql esta vacio: declara que clientes SQL vigilar (por ejemplo mysql, psql).")

    escribibles = []
    nombres = set()
    for i, a in enumerate(ambientes):
        ref = f"datos.ambientes[{i}]"
        exigir(isinstance(a, dict), f"{ref} debe ser una tabla.")
        nombre = a.get("nombre")
        exigir(isinstance(nombre, str) and nombre, f"{ref}: falta 'nombre'.")
        exigir(nombre not in nombres, f"{ref}: nombre de ambiente repetido ({nombre}).")
        nombres.add(nombre)
        exigir(a.get("tipo") in TIPOS, f"{ref} ({nombre}): 'tipo' debe ser uno de {sorted(TIPOS)}.")
        rec = a.get("reconocimiento")
        exigir(isinstance(rec, dict), f"{ref} ({nombre}): falta [datos.ambientes.reconocimiento].")
        lista_texto(rec.get("hosts"), f"{ref}.reconocimiento.hosts", PATRON_IDENT)
        for pu in rec.get("puertos", []) or []:
            exigir(isinstance(pu, int) and 0 < pu < 65536, f"{ref}.reconocimiento.puertos: {pu!r} no es un puerto.")
        lista_texto(rec.get("bases"), f"{ref}.reconocimiento.bases", PATRON_IDENT)
        lista_texto(rec.get("bases_prefijos"), f"{ref}.reconocimiento.bases_prefijos", PATRON_IDENT)
        exigir(any(rec.get(k) for k in ("hosts", "puertos", "bases", "bases_prefijos")),
               f"{ref} ({nombre}): el ambiente no dice como se reconoce (hosts, puertos o bases).")
        perm = a.get("permisos")
        exigir(isinstance(perm, dict), f"{ref} ({nombre}): falta [datos.ambientes.permisos].")
        for k in CLAVES_PERMISOS:
            exigir(perm.get(k) in PERMISOS,
                   f"{ref} ({nombre}): permisos.{k} debe ser uno de {sorted(PERMISOS)} (no se asume ninguno).")
        if perm["escritura"] == "permitida":
            exigir(a["tipo"] != "produccion",
                   f"{ref} ({nombre}): un ambiente de produccion no puede tener escritura 'permitida' para el agente.")
            escribibles.append(a)
    exigir(len(escribibles) <= 1,
           "Mas de un ambiente con escritura 'permitida': el generador soporta a lo sumo uno (el de pruebas del agente).")

    if escribibles:
        a = escribibles[0]
        rec = a["reconocimiento"]
        exigir(rec.get("hosts") and rec.get("bases"),
               f"El ambiente de escritura '{a['nombre']}' debe declarar reconocimiento.hosts y reconocimiento.bases.")
        exigir(len(rec["bases"]) == 1, "El ambiente de escritura debe tener exactamente una base.")
        exigir(a["permisos"]["ddl"] == "permitida", "El ambiente de escritura debe declarar ddl = 'permitida' (o no ser de escritura).")
        v = a.get("variables")
        exigir(isinstance(v, dict) and all(v.get(k) for k in ("archivo_env", "host", "puerto", "base")),
               f"El ambiente de escritura '{a['nombre']}' debe declarar [datos.ambientes.variables] "
               "(archivo_env, host, puerto, base): no se asumen nombres de variables.")
        for k in ("archivo_env", "host", "puerto", "base", "contrasena"):
            if v.get(k):
                exigir(PATRON_IDENT.match(v[k]), f"variables.{k}: valor no permitido {v[k]!r}.")
    return escribibles[0] if escribibles else None


# ---------------------------------------------------------------------------------------
# Construccion de los fragmentos
# ---------------------------------------------------------------------------------------
def fragmento_remote(p):
    alc = p.get("alcance") or {}
    regex = alc.get("remote_regex", "")
    sin_remote = lista_texto(alc.get("sin_remote_ok"), "alcance.sin_remote_ok", PATRON_NOMBRE)
    cualquiera = lista_texto(alc.get("cualquier_remote"), "alcance.cualquier_remote", PATRON_NOMBRE)
    if not regex:
        return "# La politica no declara remote_regex: no se exige un remote determinado."
    lineas = ["remote=\"$(git -C \"$root\" remote -v 2>/dev/null)\"",
              f"if ! printf '%s' \"$remote\" | grep -qiE {sh_q(regex)}; then",
              "  case \"$name\" in"]
    for pat in sin_remote:
        lineas.append(f"    {pat}) [ -z \"$remote\" ] || exit 0 ;;")
    for pat in cualquiera:
        lineas.append(f"    {pat}) ;;")
    lineas += ["    *) exit 0 ;;", "  esac", "fi"]
    return "\n".join(lineas)


def fragmento_comandos(p, hay_agente, etiqueta_agente):
    bloques = []
    for i, c in enumerate((p["datos"].get("comandos") or [])):
        ref = f"datos.comandos[{i}]"
        exigir(isinstance(c, dict) and c.get("regex") and c.get("motivo"), f"{ref}: faltan 'regex' y/o 'motivo'.")
        exigir(c.get("accion", "prohibida") == "prohibida", f"{ref}: solo se soporta accion = 'prohibida'.")
        lineas = [f"if printf '%s' \"$comando_ejecutable\" | grep -qE {sh_q(c['regex'])}; then"]
        if c.get("permitida_en_ambiente_de_escritura") and hay_agente:
            lineas += ["  if env_es_ambiente_agente; then",
                       f"    allow \"{sh_dq(c.get('nombre', 'comando'))} contra {sh_dq(etiqueta_agente)}\"",
                       "  fi",
                       f"  deny \"{sh_dq(c['motivo'])} (el archivo de entorno del repo no apunta al ambiente de escritura del agente)\""]
        else:
            lineas.append(f"  deny \"{sh_dq(c['motivo'])}\"")
        lineas.append("fi")
        bloques.append("\n".join(lineas))
    return "\n".join(bloques) if bloques else ":"


def fragmento_scripts(p):
    bloques = []
    for i, s in enumerate((p["datos"].get("scripts") or [])):
        ref = f"datos.scripts[{i}]"
        nombres = lista_texto(s.get("nombres"), f"{ref}.nombres", PATRON_IDENT, obligatoria=True)
        exigir(s.get("ruta_regex") and s.get("motivo"), f"{ref}: faltan 'ruta_regex' y/o 'motivo'.")
        exigir(s.get("accion") == "confirmar", f"{ref}: solo se soporta accion = 'confirmar'.")
        cond = " || ".join(f'[ "$nombre" = {sh_q(n)} ]' for n in nombres)
        bloques.append(
            f"  if printf '%s' \"$ruta\" | grep -qE {sh_q(s['ruta_regex'])} \\\n"
            f"     && {{ {cond}; }}; then\n"
            f"    ask \"{sh_dq(s['motivo'])}\"\n"
            f"  fi")
    return "\n".join(bloques) if bloques else "  :"


def construir(p, ruta_politica):
    agente = validar(p, ruta_politica)
    datos = p["datos"]
    proyecto = p.get("proyecto") or {}
    etiqueta = proyecto.get("etiqueta_reglas") or "politica de datos"
    alc = p.get("alcance") or {}
    patrones = lista_texto(alc.get("repos"), "alcance.repos", PATRON_NOMBRE, obligatoria=True)

    hosts_locales = datos["hosts_locales"]
    clientes = datos["clientes_sql"]
    mot = datos.get("motores_solo_lectura") or {}
    motores = lista_texto(mot.get("scripts"), "datos.motores_solo_lectura.scripts", re.compile(r"^[A-Za-z0-9_./-]+$"))
    pin = mot.get("archivo_sha256", "")
    exigir(not pin or re.match(r"^[A-Za-z0-9_./~-]+$", pin), "datos.motores_solo_lectura.archivo_sha256: ruta no permitida.")
    if pin.startswith("~/"):
        pin = "$HOME/" + pin[2:]

    otras_bases, otros_prefijos = [], []
    for a in datos["ambientes"]:
        if a is agente:
            continue
        otras_bases += a["reconocimiento"].get("bases", []) or []
        otros_prefijos += a["reconocimiento"].get("bases_prefijos", []) or []

    sub = {
        "POLITICA_ORIGEN": os.path.basename(ruta_politica),
        "ETIQUETA": sh_dq(etiqueta),
        "ALCANCE_CASE": "|".join(patrones),
        "REMOTE_BLOCK": fragmento_remote(p),
        "CLIENTES_RE": "|".join(clientes),
        "CLIENTES_AWK": "|".join(clientes),
        "HOSTS_LOCALES_CASE": "|".join(hosts_locales),
        "MOTOR_RE": "|".join(ere(m) for m in motores) if motores else "(?!)",
        "PIN_PATH": sh_dq(pin).replace("\\$HOME", "$HOME") if pin else "",
        "SCRIPTS_BLOCK": fragmento_scripts(p),
    }
    if agente:
        rec, v = agente["reconocimiento"], agente["variables"]
        puertos = rec.get("puertos") or []
        etiqueta_ag = f"el ambiente '{agente['nombre']}' (base {rec['bases'][0]}"
        etiqueta_ag += f", {rec['hosts'][0]}:{puertos[0]})" if puertos else ")"
        checks = ["  case \"$h\" in " + "|".join(rec["hosts"]) + ") ;; *) return 1 ;; esac"]
        if puertos:
            checks.append(f"  case \"${{p:-{puertos[0]}}}\" in " + "|".join(str(x) for x in puertos) + ") ;; *) return 1 ;; esac")
        checks.append(f"  [ \"$d\" = {sh_q(rec['bases'][0])} ]")
        base_var = v["base"]
        port_var = v["puerto"]
        pcase = ['""'] + [str(x) for x in puertos[:1]] if puertos else ['""']
        if puertos:
            pcase += [f"'${{{port_var}:-{puertos[0]}}}'", f"'${port_var}'", f"'${{{port_var}}}'"]
        else:
            pcase += [f"'${port_var}'", f"'${{{port_var}}}'"]
        ajenas = []
        if otras_bases or otros_prefijos:
            alt = "|".join([ere(b) for b in otras_bases] + [ere(b) for b in otros_prefijos])
            ajenas.append(f"  printf '%s' \"$comando_ejecutable\" | grep -qiE {sh_q('(' + alt + ')')} && return 1")
        sub.update({
            "AGENTE_HABILITADO": "1",
            "ARCHIVO_ENV": v["archivo_env"],
            "ARCHIVO_ENV_RE": ere(v["archivo_env"]),
            "VAR_HOST": v["host"], "VAR_PUERTO": port_var, "VAR_BASE": base_var,
            "VAR_CONTRASENA": v.get("contrasena", "NO_DECLARADA"),
            "AGENTE_ENV_CHECKS": "\n".join(checks),
            "AGENTE_BASE_REGEX": sh_q("(" + ere(rec["bases"][0]) + "|\\$\\{?" + base_var + "\\}?)"),
            "BASES_AJENAS_CHECK": "\n".join(ajenas) if ajenas else "  :",
            "PUERTO_CMD_CASE": "|".join(pcase),
            "HOSTS_AGENTE_CASE": "|".join(rec["hosts"]),
            "AGENTE_ETIQUETA": sh_dq(etiqueta_ag),
            "LECTURA_RESUMEN": sh_dq("la politica solo permite SELECT, y solo contra un host local; la unica escritura permitida es en " + etiqueta_ag),
        })
    else:
        sub.update({
            "AGENTE_HABILITADO": "0",
            "ARCHIVO_ENV": ".env", "ARCHIVO_ENV_RE": ere(".env"),
            "VAR_HOST": "NO_DECLARADA", "VAR_PUERTO": "NO_DECLARADA", "VAR_BASE": "NO_DECLARADA",
            "VAR_CONTRASENA": "NO_DECLARADA",
            "AGENTE_ENV_CHECKS": "  return 1",
            "AGENTE_BASE_REGEX": "'(?!)'",
            "BASES_AJENAS_CHECK": "  :",
            "PUERTO_CMD_CASE": '""',
            "HOSTS_AGENTE_CASE": "__ningun_host__",
            "AGENTE_ETIQUETA": "ningun ambiente",
            "LECTURA_RESUMEN": "la politica solo permite SELECT, y solo contra un host local; no hay ningun ambiente de escritura para el agente",
        })
    sub["COMANDOS_BLOCK"] = fragmento_comandos(p, bool(agente), sub["AGENTE_ETIQUETA"])
    return sub


def generar(ruta_politica, salida):
    p = cargar(ruta_politica)
    sub = construir(p, ruta_politica)
    with open(os.path.join(PLANTILLAS, "block-db-access.sh.tpl"), encoding="utf-8") as f:
        texto = f.read()
    for clave, valor in sub.items():
        texto = texto.replace(f"@@{clave}@@", valor)
    restantes = sorted(set(re.findall(r"@@[A-Z_]+@@", texto)))
    exigir(not restantes, f"La plantilla quedo con variables sin resolver: {restantes}")

    os.makedirs(salida, exist_ok=True)
    destino = os.path.join(salida, "block-db-access.sh")
    with open(destino, "w", encoding="utf-8") as f:
        f.write(texto)
    os.chmod(destino, 0o755)
    filtro_o = os.path.join(PLANTILLAS, "filtrar-tramos-de-lectura.py")
    filtro_d = os.path.join(salida, "filtrar-tramos-de-lectura.py")
    with open(filtro_o, encoding="utf-8") as fo, open(filtro_d, "w", encoding="utf-8") as fd:
        fd.write(fo.read())
    os.chmod(filtro_d, 0o755)
    return [destino, filtro_d]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Genera el hook de acceso a la base desde una politica por proyecto.")
    ap.add_argument("politica", help="archivo de politicas (TOML)")
    ap.add_argument("--salida", required=True, help="directorio donde se escriben los archivos generados")
    args = ap.parse_args(argv)
    try:
        archivos = generar(args.politica, args.salida)
    except ErrorPolitica as e:
        print(f"ERROR de politica: {e}", file=sys.stderr)
        return 2
    for a in archivos:
        print(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
