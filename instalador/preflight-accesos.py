#!/usr/bin/env python3
"""Preflight de accesos: comprueba, sin guardar credenciales y sin escribir, si esta persona
puede orquestar en el modo elegido.

Uso:
    python3 preflight-accesos.py --politica <politicas.toml> --acceso <acceso.local.toml> \
        --modo adopt|init|update|migrar [--partida A|B|C] [--json] [--aceptar-degradado datos] [--registrar <archivo>] \
        [--proyecto <directorio>] [--tiempo-limite 2]

Punto de partida (--partida): A proyecto empezado (defecto, exige lo de cada modo); B desde cero
(no exige datos ni nube; exige almacen de documentacion con la informacion de partida); C migracion
(exige leer el sistema origen o su descripcion en archivos). Sin informacion de partida en B o C falla
diciendo que falta y donde ponerla.

Salida: tabla Recurso | Metodo | Estado (OK / FALTA / DEGRADADO) | Que pedir.
Codigos de salida:
    0  puede orquestar (todo lo requerido esta OK, o lo que falta fue aceptado como degradado
       y se muestra y registra de forma visible; nunca se aprueba en silencio)
    2  falta algo requerido: se lista exactamente que
    1  error de configuracion (politica sin ambientes, modo invalido, archivo ilegible...)

Reglas:
- Solo biblioteca estandar (Python >= 3.11, `tomllib`).
- No lee valores de secretos, no escribe en ningun recurso, no ejecuta nada que modifique estado.
  De los perfiles de nube solo se leen NOMBRES; de las variables de entorno, solo si EXISTEN.
- Un campo del archivo local con aspecto de secreto (clave, token, contrasena...) se ignora, se
  avisa por NOMBRE de campo y su valor se elimina de cualquier salida.
- Toda comprobacion de red o de comandos pasa por `Sondas`, que se inyecta (pruebas con dobles).
- Nunca asume un ambiente: la lista sale de la politica ([[datos.ambientes]]).
"""
import argparse
import datetime
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tomllib

MODOS = ("adopt", "init", "update", "migrar")
PARTIDAS = ("A", "B", "C")
MODO_DE_PARTIDA = {"A": "adopt", "B": "init", "C": "migrar"}
# Requeridos segun el punto de partida (spec §18). A usa la tabla por modo (§15).
REQUERIDOS_PARTIDA = {
    "B": ("documentacion",),            # sin datos ni nube al inicio; con almacen de documentacion
    "C": ("origen",),                   # lectura del sistema origen o su descripcion en archivos
}
# Recursos requeridos por modo. Los ambientes de datos salen de la politica.
REQUERIDOS = {
    "adopt": ("repositorios", "documentacion", "tickets", "datos", "nube"),
    "init": ("repositorios", "documentacion", "tickets", "datos", "nube", "ci"),
    "update": ("repositorios", "documentacion"),
}
DEGRADABLES = ("datos",)
PATRON_SECRETO = re.compile(r"(clave|secret|contrase|password|passwd|token|credencial|api_?key|private)", re.I)
SUFIJOS_NOMBRE = ("_variable", "_env", "_archivo", "_perfil")
PATRON_HOST = re.compile(r"^[A-Za-z0-9_.-]+$")
PATRON_NOMBRE = re.compile(r"^[A-Za-z0-9_.:@/-]+$")

QUIEN = {
    "datos": "al responsable de bases de datos del proyecto",
    "nube": "al responsable de infraestructura/nube del proyecto",
    "repositorios": "al administrador de los repositorios",
    "documentacion": "al administrador de la documentacion",
    "tickets": "al administrador del gestor de tickets",
    "ci": "al responsable de integracion/despliegue continuo",
    "origen": "al responsable del sistema que se va a migrar o replicar",
}
METODOS = {
    "datos": ("directo", "tunel_ssh", "ssm", "bastion", "vpn", "copia_local", "sin_acceso"),
    "nube": ("perfil_sso", "rol_asumido", "claves_entorno", "sin_acceso"),
    "repositorios": ("ssh", "https", "gh", "sin_acceso"),
    "documentacion": ("confluence", "drive_md", "carpeta_repo", "sin_acceso"),
    "tickets": ("jira", "github_issues", "ninguno", "sin_acceso"),
    "ci": ("github_actions", "otro", "ninguno", "sin_acceso"),
    "origen": ("codigo", "volcado", "descripcion", "sin_acceso"),
}


class ErrorConfig(Exception):
    pass


class Sondas:
    """Comprobaciones reales. Solo lectura. Se reemplaza entera o por metodo en las pruebas."""

    def comando(self, nombre):
        return shutil.which(nombre) is not None

    def tcp(self, host, puerto, tiempo):
        try:
            with socket.create_connection((host, int(puerto)), timeout=tiempo):
                return True
        except (OSError, ValueError):
            return False

    def perfil_nube(self, nombre):
        """True si el NOMBRE del perfil figura en la configuracion de la CLI. No lee valores."""
        ruta = os.path.expanduser(os.environ.get("AWS_CONFIG_FILE", "~/.aws/config"))
        try:
            with open(ruta, encoding="utf-8") as f:
                for linea in f:
                    t = linea.strip()
                    if t in (f"[profile {nombre}]", f"[{nombre}]"):
                        return True
        except OSError:
            return False
        return False

    def sesion_nube(self, perfil, tiempo):
        """Sesion vigente: llamada de solo lectura de identidad; la salida se descarta."""
        try:
            r = subprocess.run(["aws", "sts", "get-caller-identity", "--profile", perfil],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=tiempo * 5)
            return r.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def variable_entorno(self, nombre):
        return bool(os.environ.get(nombre))

    def ruta_existe(self, ruta):
        return os.path.exists(os.path.expanduser(ruta))

    def contenido(self, ruta):
        """True si la ruta es un archivo o una carpeta con al menos un archivo."""
        r = os.path.expanduser(ruta)
        if os.path.isfile(r):
            return True
        for _, _, archivos in os.walk(r):
            if archivos:
                return True
        return False

    def gestor_credenciales_git(self):
        try:
            r = subprocess.run(["git", "config", "--get", "credential.helper"], capture_output=True,
                               text=True, timeout=5)
            return r.returncode == 0 and bool(r.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            return False

    def gh_autenticado(self):
        try:
            r = subprocess.run(["gh", "auth", "status"], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=10)
            return r.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False


# ---------------------------------------------------------------- lectura de entradas
def leer_toml(ruta, que):
    try:
        with open(ruta, "rb") as f:
            return tomllib.load(f)
    except OSError as e:
        raise ErrorConfig(f"No se puede leer {que} '{ruta}': {e.strerror}.")
    except tomllib.TOMLDecodeError as e:
        raise ErrorConfig(f"{que} '{ruta}' no es TOML valido: {e}.")


def ambientes_de_politica(politica, ruta, exigir=True):
    datos = politica.get("datos")
    amb = datos.get("ambientes") if isinstance(datos, dict) else None
    if not amb and not exigir:
        return []
    if not amb or not isinstance(amb, list):
        raise ErrorConfig(
            f"La politica '{ruta}' no declara ningun ambiente de datos ([[datos.ambientes]]). "
            "El preflight nunca asume un ambiente: declara al menos uno (nombre y tipo) en la politica.")
    res = []
    for i, a in enumerate(amb):
        if not isinstance(a, dict) or not a.get("nombre"):
            raise ErrorConfig(f"datos.ambientes[{i}] en '{ruta}' no tiene 'nombre'.")
        res.append((str(a["nombre"]), str(a.get("tipo", ""))))
    return res


def limpiar_secretos(nodo, ruta="", encontrados=None, valores=None):
    """Devuelve copia sin los campos con aspecto de secreto; junto con sus NOMBRES y sus valores
    (estos ultimos solo para redactarlos de cualquier salida, nunca se imprimen)."""
    if encontrados is None:
        encontrados, valores = [], []
    if isinstance(nodo, dict):
        limpio = {}
        for k, v in nodo.items():
            r = f"{ruta}.{k}" if ruta else str(k)
            if (PATRON_SECRETO.search(str(k)) and not str(k).endswith(SUFIJOS_NOMBRE)
                    and isinstance(v, (str, int)) and str(v) != ""):
                encontrados.append(r)
                valores.append(str(v))
                continue
            limpio[k] = limpiar_secretos(v, r, encontrados, valores)[0]
        return limpio, encontrados, valores
    if isinstance(nodo, list):
        return [limpiar_secretos(x, ruta, encontrados, valores)[0] for x in nodo], encontrados, valores
    return nodo, encontrados, valores


# ---------------------------------------------------------------- comprobaciones
def _res(recurso, metodo, estado, pedir="", detalle=""):
    return {"recurso": recurso, "metodo": metodo, "estado": estado, "pedir": pedir, "detalle": detalle}


def _faltan(recurso, metodo, que):
    quien = QUIEN[recurso.split(":")[0]]
    return _res(recurso, metodo, "FALTA", f"Pedir {quien}: {que}")


def _host_ok(v):
    return isinstance(v, str) and PATRON_HOST.match(v) is not None


def _puerto_ok(v):
    return isinstance(v, int) and not isinstance(v, bool) and 0 < v < 65536


def comprobar_datos(nombre, cfg, s, t):
    rec = f"datos:{nombre}"
    if not isinstance(cfg, dict) or not cfg.get("metodo"):
        return _faltan(rec, "(sin declarar)",
                       f"declarar en el acceso local como llegas al ambiente '{nombre}' ([datos.{nombre}] metodo = ...)")
    m = cfg["metodo"]
    if m not in METODOS["datos"]:
        return _faltan(rec, str(m), f"usar un metodo conocido: {', '.join(METODOS['datos'])}")
    if m == "sin_acceso":
        return _faltan(rec, m, f"acceso de solo lectura al ambiente '{nombre}' (conexion directa, tunel, VPN o una copia local/volcado)")
    if m == "copia_local" and cfg.get("archivo"):
        if s.ruta_existe(str(cfg["archivo"])):
            return _res(rec, m, "OK", detalle="volcado presente")
        return _faltan(rec, m, "el volcado o copia local de la base (no existe la ruta declarada)")
    host, puerto = cfg.get("host", ""), cfg.get("puerto")
    if not _host_ok(host) or not _puerto_ok(puerto):
        return _faltan(rec, m, "declarar host (o alias) y puerto validos, sin usuario ni clave dentro")
    if m == "tunel_ssh":
        if not s.comando("ssh"):
            return _faltan(rec, m, "instalar el cliente ssh")
        if not s.tcp(host, puerto, t):
            return _faltan(rec, m, f"abrir el tunel SSH hacia el ambiente '{nombre}' y confirmar que escucha en {host}:{puerto}; "
                                   "si no tienes llave o alias de salto, pedirlos")
    elif m == "ssm":
        for c in ("aws", "session-manager-plugin"):
            if not s.comando(c):
                return _faltan(rec, m, f"instalar '{c}'")
        perfil = cfg.get("perfil")
        if perfil and not s.perfil_nube(str(perfil)):
            return _faltan(rec, m, f"configurar el perfil de nube '{perfil}' (inicio de sesion SSO)")
        if not s.tcp(host, puerto, t):
            return _faltan(rec, m, f"iniciar la sesion SSM de reenvio de puertos y confirmar {host}:{puerto}")
    elif m == "bastion":
        if not s.comando("ssh"):
            return _faltan(rec, m, "instalar el cliente ssh")
        if not s.tcp(host, puerto, t):
            return _faltan(rec, m, f"alcanzabilidad al bastion {host}:{puerto} (red, lista de IP permitidas o llave)")
    else:  # directo, vpn, copia_local con host
        if not s.tcp(host, puerto, t):
            extra = " y conectar la VPN" if m == "vpn" else ""
            return _faltan(rec, m, f"permitir tu acceso de red a {host}:{puerto}{extra}"
                                   if m != "copia_local" else f"levantar la copia local en {host}:{puerto}")
    return _res(rec, m, "OK", detalle=f"{host}:{puerto}")


def comprobar_nube(cfg, s, t):
    rec = "nube"
    if not isinstance(cfg, dict) or not cfg.get("metodo"):
        return _faltan(rec, "(sin declarar)", "declarar en el acceso local como llegas a la nube ([nube] metodo = ...)")
    m = cfg["metodo"]
    if m not in METODOS["nube"]:
        return _faltan(rec, str(m), f"usar un metodo conocido: {', '.join(METODOS['nube'])}")
    if m == "sin_acceso":
        return _faltan(rec, m, "una identidad de nube con permisos de solo lectura (perfil SSO, rol o claves de entorno)")
    if m == "claves_entorno":
        nombres = cfg.get("variables") or []
        if not nombres or not all(isinstance(n, str) and PATRON_NOMBRE.match(n) for n in nombres):
            return _faltan(rec, m, "declarar los NOMBRES de las variables de entorno que se usaran (nunca sus valores)")
        ausentes = [n for n in nombres if not s.variable_entorno(n)]
        if ausentes:
            return _faltan(rec, m, f"definir en tu entorno las variables: {', '.join(ausentes)} (el preflight solo comprueba que existan)")
        return _res(rec, m, "OK", detalle="variables presentes")
    if not s.comando("aws"):
        return _faltan(rec, m, "instalar la CLI de la nube")
    perfil = cfg.get("perfil")
    if not isinstance(perfil, str) or not PATRON_NOMBRE.match(perfil):
        return _faltan(rec, m, "declarar el NOMBRE del perfil de nube")
    if not s.perfil_nube(perfil):
        return _faltan(rec, m, f"configurar el perfil '{perfil}' (SSO o rol asumido) con el alta que te indique el responsable")
    if not s.sesion_nube(perfil, t):
        return _faltan(rec, m, f"iniciar sesion con el perfil '{perfil}' (la sesion no esta vigente)")
    return _res(rec, m, "OK", detalle=f"perfil {perfil}")


def _con_host(rec, m, cfg, s, t, que, comandos=()):
    for c in comandos:
        if not s.comando(c):
            return _faltan(rec, m, f"instalar '{c}'")
    host = cfg.get("host")
    if not _host_ok(host):
        return _faltan(rec, m, "declarar el host (sin usuario ni clave)")
    puerto = cfg.get("puerto", 443)
    if not _puerto_ok(puerto):
        return _faltan(rec, m, "declarar un puerto valido")
    if not s.tcp(host, puerto, t):
        return _faltan(rec, m, f"alcanzabilidad a {host}:{puerto} y {que}")
    return _res(rec, m, "OK", detalle=f"{host}:{puerto}")


def comprobar_simple(recurso, cfg, s, t):
    if not isinstance(cfg, dict) or not cfg.get("metodo"):
        return _faltan(recurso, "(sin declarar)", f"declarar en el acceso local como llegas a '{recurso}' ([{recurso}] metodo = ...)")
    m = cfg["metodo"]
    if m not in METODOS[recurso]:
        return _faltan(recurso, str(m), f"usar un metodo conocido: {', '.join(METODOS[recurso])}")
    if m == "sin_acceso":
        return _faltan(recurso, m, f"acceso de lectura a '{recurso}'")
    if m == "ninguno":
        return _res(recurso, m, "OK", detalle="declarado: el proyecto no lo usa")
    if recurso == "repositorios":
        if not s.comando("git"):
            return _faltan(recurso, m, "instalar git")
        if m == "ssh":
            return _con_host(recurso, m, {"host": cfg.get("host"), "puerto": cfg.get("puerto", 22)}, s, t,
                             "tener tu llave publica registrada en el servicio de repositorios", ("ssh",))
        if m == "https":
            if not s.gestor_credenciales_git():
                return _faltan(recurso, m, "configurar un gestor de credenciales de git (credential.helper); el preflight no guarda credenciales")
            return _res(recurso, m, "OK", detalle="gestor de credenciales presente")
        if not s.comando("gh"):
            return _faltan(recurso, m, "instalar la CLI 'gh'")
        if not s.gh_autenticado():
            return _faltan(recurso, m, "iniciar sesion en 'gh' (gh auth login); la sesion no esta vigente")
        return _res(recurso, m, "OK", detalle="gh autenticado")
    if recurso == "documentacion":
        if m == "confluence":
            return _con_host(recurso, m, cfg, s, t, "tener una cuenta con permiso de lectura al espacio")
        ruta = cfg.get("carpeta")
        if not isinstance(ruta, str) or not ruta or not s.ruta_existe(ruta):
            return _faltan(recurso, m, "la carpeta con la documentacion en .md (copia exportada o carpeta del repo); la ruta declarada no existe")
        return _res(recurso, m, "OK", detalle="carpeta presente")
    if recurso == "tickets":
        if m == "jira":
            return _con_host(recurso, m, cfg, s, t, "tener una cuenta con permiso de lectura al proyecto de tickets")
        if not s.comando("gh") or not s.gh_autenticado():
            return _faltan(recurso, m, "instalar 'gh' e iniciar sesion (gh auth login)")
        return _res(recurso, m, "OK", detalle="gh autenticado")
    if recurso == "ci":
        if m == "github_actions":
            if not s.comando("gh") or not s.gh_autenticado():
                return _faltan(recurso, m, "instalar 'gh' e iniciar sesion (gh auth login)")
            return _res(recurso, m, "OK", detalle="gh autenticado")
        return _con_host(recurso, m, cfg, s, t, "tener permiso de lectura a los pipelines")
    raise ErrorConfig(f"recurso desconocido: {recurso}")


def _tiene_archivos(s, ruta):
    return s.ruta_existe(ruta) and (not hasattr(s, "contenido") or s.contenido(ruta))


def comprobar_partida(recurso, cfg, s, partida):
    """Informacion de partida de B (almacen de documentacion) y C (sistema origen o su descripcion)."""
    donde = ("[documentacion] carpeta = \"<ruta>\" (o espacio de Confluence) en el acceso local, con la "
             "informacion de partida: .md, hojas de calculo (xlsx/csv), esquemas SQL o diagramas exportados"
             if recurso == "documentacion" else
             "[origen] metodo = codigo|volcado|descripcion y ruta = \"<ruta>\" en el acceso local; con "
             "'descripcion' poner esquema, diccionario u hojas de calculo del sistema origen")
    if not isinstance(cfg, dict) or not cfg.get("metodo"):
        return _faltan(recurso, "(sin declarar)", f"la informacion de partida no esta declarada: poner {donde}")
    m = cfg["metodo"]
    if m not in METODOS[recurso]:
        return _faltan(recurso, str(m), f"usar un metodo conocido: {', '.join(METODOS[recurso])}")
    if m == "sin_acceso":
        return _faltan(recurso, m, f"sin informacion de partida no se empieza: poner {donde}")
    if recurso == "documentacion" and m == "confluence":
        if not cfg.get("espacio"):
            return _faltan(recurso, m, "declarar el espacio ([documentacion] espacio = \"<clave>\") donde esta la informacion de partida")
        return _res(recurso, m, "OK", detalle=f"espacio {cfg['espacio']}")
    ruta = cfg.get("carpeta") if recurso == "documentacion" else cfg.get("ruta")
    if not isinstance(ruta, str) or not ruta:
        return _faltan(recurso, m, f"declarar la ruta de la informacion de partida: {donde}")
    if not s.ruta_existe(ruta):
        return _faltan(recurso, m, f"la ruta declarada no existe: poner la informacion de partida en ella ({donde})")
    if hasattr(s, "contenido") and not s.contenido(ruta):
        return _faltan(recurso, m, "la carpeta de partida esta vacia: colocar ahi .md, hojas de calculo (xlsx/csv), esquemas SQL o diagramas")
    return _res(recurso, m, "OK", detalle="informacion de partida presente")


def construir_informe(politica, acceso, modo, sondas, tiempo=2.0, degradado=(), ruta_politica="politica",
                      partida="A"):
    if partida not in PARTIDAS:
        raise ErrorConfig(f"Punto de partida '{partida}' no valido; usa uno de: {', '.join(PARTIDAS)}.")
    if modo is None:
        modo = MODO_DE_PARTIDA[partida]
    if modo not in MODOS:
        raise ErrorConfig(f"Modo '{modo}' no valido; usa uno de: {', '.join(MODOS)}.")
    for d in degradado:
        if d not in DEGRADABLES:
            raise ErrorConfig(f"Solo se puede aceptar degradado para: {', '.join(DEGRADABLES)} (recibido '{d}').")
    ambientes = ambientes_de_politica(politica, ruta_politica, exigir=(partida == "A"))
    limpio, secretos, valores = limpiar_secretos(acceso or {})
    filas = []
    requeridos = REQUERIDOS[modo] if partida == "A" else REQUERIDOS_PARTIDA[partida]
    for recurso in ("repositorios", "documentacion", "tickets", "datos", "nube", "ci", "origen"):
        if partida != "A" and recurso in requeridos:
            f = comprobar_partida(recurso, limpio.get(recurso), sondas, partida)
            f["requerido"] = True
            filas.append(f)
            continue
        if recurso == "origen":
            continue
        if recurso == "datos":
            for nombre, tipo in ambientes:
                cfg = (limpio.get("datos") or {}).get(nombre)
                if recurso not in requeridos or tipo == "produccion":
                    # en B/C se piden cuando el plan los necesite: aqui no son requisito
                    # produccion nunca es requisito: si esta declarado se comprueba solo a titulo informativo
                    if cfg:
                        f = comprobar_datos(nombre, cfg, sondas, tiempo)
                        f["requerido"] = False
                        filas.append(f)
                    continue
                f = comprobar_datos(nombre, cfg, sondas, tiempo)
                f["requerido"] = True
                filas.append(f)
            continue
        cfg = limpio.get(recurso)
        if recurso not in requeridos and not cfg:
            continue
        if partida != "A":
            f = (comprobar_nube(cfg, sondas, tiempo) if recurso == "nube"
                 else comprobar_simple(recurso, cfg, sondas, tiempo))
            f["requerido"] = False
            if f["estado"] == "FALTA":
                f["detalle"] = "se pedira cuando el plan lo necesite"
            filas.append(f)
            continue
        f = comprobar_nube(cfg, sondas, tiempo) if recurso == "nube" else comprobar_simple(recurso, cfg, sondas, tiempo)
        f["requerido"] = recurso in requeridos
        filas.append(f)
    degradados = []
    for f in filas:
        if f["estado"] == "FALTA" and f["requerido"] and f["recurso"].split(":")[0] in degradado:
            f["estado"] = "DEGRADADO"
            f["detalle"] = "verificacion con datos: NO DISPONIBLE (sin acceso)"
            degradados.append(f["recurso"])
        elif f["estado"] == "FALTA" and not f["requerido"] and not f["detalle"]:
            f["detalle"] = "no requerido en este modo"
    faltan = [f["recurso"] for f in filas if f["estado"] == "FALTA" and f["requerido"]]
    return {
        "modo": modo, "partida": partida, "filas": filas, "faltan": faltan, "degradados": degradados,
        "puede_orquestar": not faltan,
        "campos_con_aspecto_de_secreto": secretos,
        "_valores_secretos": valores,
    }


# ---------------------------------------------------------------- salida
def redactar(texto, valores):
    for v in sorted(set(valores), key=len, reverse=True):
        if v:
            texto = texto.replace(v, "[REDACTADO]")
    return texto


def a_texto(inf):
    out = [f"Preflight de accesos - partida {inf['partida']} - modo {inf['modo']}", "",
           f"{'Recurso':<28}{'Metodo':<18}{'Estado':<11}Que pedir", "-" * 100]
    for f in inf["filas"]:
        celda = f['pedir'] or f['detalle']
        if f['estado'] == "FALTA" and not f.get("requerido", True):
            celda = f"(no requerido ahora: {f['detalle']}) {f['pedir']}"
        out.append(f"{f['recurso']:<28}{f['metodo']:<18}{f['estado']:<11}{celda}")
    if inf["campos_con_aspecto_de_secreto"]:
        out += ["", "ADVERTENCIA: el archivo de acceso local contiene campos con aspecto de secreto "
                    "(se ignoran y no se muestran): " + ", ".join(inf["campos_con_aspecto_de_secreto"]),
                "Quitalos del archivo y usa un gestor de secretos, un perfil o variables de entorno."]
    if inf["degradados"]:
        out += ["", "MODO DEGRADADO DECLARADO", "verificacion con datos: NO DISPONIBLE (sin acceso)",
                "Ambientes afectados: " + ", ".join(inf["degradados"]),
                "Cada gate debe mostrar esta verificacion como no disponible, no como aprobada."]
    out.append("")
    if inf["faltan"]:
        out.append("NO PUEDE ORQUESTAR. Falta (requerido): " + ", ".join(inf["faltan"]))
        for f in inf["filas"]:
            if f["estado"] == "FALTA" and f["requerido"]:
                out.append(f"  - {f['recurso']}: {f['pedir']}")
    elif inf["degradados"]:
        out.append("PUEDE ORQUESTAR solo en modo degradado (limites declarados arriba).")
    else:
        out.append("PUEDE ORQUESTAR: todos los accesos requeridos estan en orden.")
    return "\n".join(out)


def a_json(inf):
    pub = {k: v for k, v in inf.items() if not k.startswith("_")}
    return json.dumps(pub, ensure_ascii=False, indent=2)


def texto_registro(inf, fecha):
    return "\n".join([
        "# Limite registrado: modo degradado de accesos",
        f"fecha: {fecha}",
        f"modo: {inf['modo']}",
        "verificacion con datos: NO DISPONIBLE (sin acceso)",
        "ambientes_afectados: " + ", ".join(inf["degradados"]),
        "efecto: los gates muestran la verificacion con datos como no disponible; no se aprueba en silencio.",
        ""])


def dentro_de(ruta, base):
    r, b = os.path.realpath(ruta), os.path.realpath(base)
    return r == b or r.startswith(b + os.sep)


def validar_registro(ruta, proyecto):
    if proyecto and dentro_de(ruta, proyecto):
        raise ErrorConfig("--registrar no puede estar dentro del proyecto analizado.")
    d = os.path.dirname(os.path.realpath(ruta))
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            raise ErrorConfig(f"--registrar no puede estar dentro de un repositorio git ({d}); usa un directorio fuera de los proyectos.")
        padre = os.path.dirname(d)
        if padre == d:
            break
        d = padre


def main(argv=None, sondas=None, salida=None):
    salida = salida or sys.stdout
    ap = argparse.ArgumentParser(description="Preflight de accesos (solo lectura, sin credenciales).")
    ap.add_argument("--politica", required=True)
    ap.add_argument("--acceso", required=True)
    ap.add_argument("--modo", choices=MODOS, help="por defecto segun la partida: A adopt, B init, C migrar")
    ap.add_argument("--partida", choices=PARTIDAS, default="A",
                    help="A proyecto empezado (defecto), B desde cero, C migracion")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--aceptar-degradado", action="append", default=[], metavar="RECURSO")
    ap.add_argument("--registrar")
    ap.add_argument("--proyecto")
    ap.add_argument("--tiempo-limite", type=float, default=2.0)
    a = ap.parse_args(argv)
    sondas = sondas or Sondas()
    try:
        pol = leer_toml(a.politica, "la politica")
        acc = leer_toml(a.acceso, "el acceso local")
        if a.registrar:
            validar_registro(a.registrar, a.proyecto)
        inf = construir_informe(pol, acc, a.modo, sondas, a.tiempo_limite, tuple(a.aceptar_degradado), a.politica,
                              a.partida)
    except ErrorConfig as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    texto = a_json(inf) if a.json else a_texto(inf)
    print(redactar(texto, inf["_valores_secretos"]), file=salida)
    if inf["degradados"] and a.registrar:
        fecha = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
        with open(a.registrar, "w", encoding="utf-8") as f:
            f.write(redactar(texto_registro(inf, fecha), inf["_valores_secretos"]))
    return 0 if inf["puede_orquestar"] else 2


if __name__ == "__main__":
    sys.exit(main())
