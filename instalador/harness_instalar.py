#!/usr/bin/env python3
"""Instalador del meta harness: adopt | init | update | migrar.

Uso:
    python3 harness_instalar.py <modo> <carpeta-de-la-instancia> [--partida A|B|C]
        [--acceso <acceso.local.toml>] [--politica <politicas.toml>] [--proyecto <carpeta>]
        [--aceptar-degradado] [--aceptar-dentro-de-repo] [--harness <raiz>] [--aplicar]

Reglas:
- Sin --aplicar solo muestra el plan y no escribe nada.
- Solo escribe dentro de la carpeta de la instancia.
- Nunca ejecuta herramientas externas, red ni GitHub: lo que haga falta se imprime como paso para la persona.
- Idempotente: no guarda fechas ni nada que cambie entre corridas iguales.
- Solo biblioteca estandar (Python >= 3.11).
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

MODOS = ("adopt", "init", "update", "migrar")
PARTIDA_DE_MODO = {"adopt": "A", "init": "B", "migrar": "C"}
HARNESS = "harness"        # archivo del harness: update lo actualiza si nadie lo modifico
INSTANCIA = "instancia"    # archivo de la instancia: se crea una vez y update nunca lo toca
ESTADO_REL = ".harness/estado.json"
POR_DECLARAR = "por declarar"


class Detener(Exception):
    """Detiene el instalador con un mensaje y un codigo de salida."""

    def __init__(self, mensaje, codigo=2):
        super().__init__(mensaje)
        self.codigo = codigo


def sha(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def leer(ruta):
    return Path(ruta).read_text(encoding="utf-8")


def version_tupla(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return None


# ------------------------------------------------------------------ contenidos de origen
def convenciones_desde_estandar(raiz, propuesta=None):
    """Genera convenciones.toml a partir de la tabla de convenciones/estandar.md.
    `propuesta` (dict clave -> (valor, nota)) sobrescribe valores detectados por adopt."""
    texto = leer(Path(raiz) / "convenciones" / "estandar.md")
    patron = re.compile(r"^\| `([^`]+)` \| [^|]* \| (.*?) \| [^|]* \|$")
    filas, vistas = [], set()
    for linea in texto.splitlines():
        m = patron.match(linea)
        if m and m.group(1) not in vistas:
            vistas.add(m.group(1))
            filas.append((m.group(1), m.group(2).replace("`", "").strip()))
    propuesta = propuesta or {}
    def esc(v):
        return v.replace("\\", "\\\\").replace('"', '\\"')
    salida = [
        "# Convenciones de esta instancia. Parten del estandar del harness (convenciones/estandar.md).",
        "# Sobrescribe una clave cambiando su valor. Un valor {{...}} o 'por definir' debe resolverse",
        "# antes de cerrar el primer cambio.",
        ""]
    for clave, valor in filas:
        if clave in propuesta:
            v, nota = propuesta[clave]
            salida.append(f"# detectado: {nota}")
            valor = v
        salida.append(f'"{clave}" = "{esc(valor)}"')
    if "gate.comando" not in vistas:
        salida += ["", "# Comando que ejecuta compilacion, pruebas y lint del proyecto (lo declara el equipo).",
                   '"gate.comando" = "por definir"']
    return "\n".join(salida) + "\n"


ENCABEZADO_POLITICA = (
    "# Politicas de esta instancia. Parte de politicas/politicas.defecto.toml del harness.\n"
    "# AMBIENTES DE DATOS: por declarar. El harness no asume ninguno: declara cada uno con\n"
    "# [[datos.ambientes]] (ver politicas/ESQUEMA.md) antes de generar hooks o pedir datos.\n"
    "# Los accesos de cada persona van en acceso.local.toml (no versionado).\n\n")


def politica_inicial(raiz, propuesta_texto=None):
    if propuesta_texto:
        return propuesta_texto
    return ENCABEZADO_POLITICA + leer(Path(raiz) / "politicas" / "politicas.defecto.toml")


def politica_con_motor(raiz, motor):
    """Politica de la partida B/C: el motor propuesto va SOLO como comentario; los ambientes siguen por declarar."""
    if not motor:
        return politica_inicial(raiz)
    ev = "; ".join(motor.get("evidencia") or [])
    lineas = ("# Motor de base de datos: propuesto, por confirmar (no es una decision; no se aplica solo).\n"
              f"#   propuesto: {motor.get('propuesto')} (confianza {motor.get('confianza')}); alternativa: {motor.get('alternativa')}\n"
              f"#   evidencia: {ev}\n"
              "#   Detalle en .harness/entendimiento.md. Confirmarlo antes de declarar ambientes.\n")
    return ENCABEZADO_POLITICA + lineas + "\n" + leer(Path(raiz) / "politicas" / "politicas.defecto.toml")


def lock_texto(version, fuente):
    return f'version = "{version}"\nfuente = "{fuente}"\n'


def archivos_de_instancia(raiz, propuestas):
    """Lista (ruta, tipo, contenido) de lo que el instalador gestiona. harness.lock y estado van aparte."""
    base = Path(raiz) / "plantillas" / "instancia"
    def pl(rel):
        return leer(base / rel)
    return [
        ("README.md", HARNESS, pl("README.md")),
        (".gitignore", HARNESS, pl(".gitignore")),
        ("acceso.local.ejemplo.toml", HARNESS, leer(Path(raiz) / "acceso" / "acceso.local.ejemplo.toml")),
        ("conocimiento/README.md", HARNESS, pl("conocimiento/README.md")),
        ("cambios/README.md", HARNESS, pl("cambios/README.md")),
        ("documentacion/README.md", HARNESS, pl("documentacion/README.md")),
        ("politicas.toml", INSTANCIA, politica_inicial(raiz, propuestas.get("politica"))),
        ("convenciones.toml", INSTANCIA, propuestas.get("convenciones") or convenciones_desde_estandar(raiz)),
        ("mejoras.md", INSTANCIA, pl("mejoras.md")),
    ]


# ------------------------------------------------------------------ comprobaciones previas
def correr(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def comprobar_version(raiz, instancia=None):
    """R26: comprueba la version del harness y la de harness.lock. Devuelve (dict, codigo)."""
    cmd = [sys.executable, str(Path(raiz) / "instalador" / "comprobar-version.py"), "--harness", str(raiz), "--json"]
    if instancia and (Path(instancia) / "harness.lock").exists():
        cmd += ["--instancia", str(instancia)]
    r = correr(cmd)
    try:
        datos = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise Detener("No se pudo comprobar la version del harness: " + (r.stderr.strip() or r.stdout.strip()), 1)
    if r.returncode == 2:
        raise Detener("Version no valida: " + " ".join(datos.get("mensajes", [])), 2)
    return datos, r.returncode


def repo_ancestro(carpeta):
    """Directorio de un repositorio git que contiene ESTRICTAMENTE a la carpeta, o None."""
    p = Path(carpeta).resolve().parent
    while True:
        if (p / ".git").exists():
            return p
        if p.parent == p:
            return None
        p = p.parent


def validar_carpeta(carpeta, raiz, proyecto, modo, dentro_de_repo_ok):
    c = Path(carpeta).resolve()
    r = Path(raiz).resolve()
    if c.is_file():
        raise Detener(f"{carpeta} es un archivo; se espera la carpeta de la instancia.")
    if c == r or r in c.parents:
        raise Detener("La instancia no puede estar dentro del propio harness.")
    if proyecto is not None:
        p = Path(proyecto).resolve()
        if p != c and p in c.parents:
            raise Detener("La instancia no puede estar dentro del proyecto analizado si es otro (el informe nunca se escribe en el proyecto).")
    declarada = (c / "harness.lock").exists() or (c / ESTADO_REL).exists()
    ancestro = repo_ancestro(c)
    if ancestro is not None and not declarada and not dentro_de_repo_ok:
        raise Detener(
            f"{carpeta} esta dentro de otro repositorio ({ancestro}) y no es una instancia declarada "
            "(no tiene harness.lock). Usa una carpeta propia para la instancia o, si es a proposito, "
            "repite con --aceptar-dentro-de-repo.")
    return c


# ------------------------------------------------------------------ puerta de accesos
def correr_preflight(raiz, partida, modo, politica, acceso, degradado):
    cmd = [sys.executable, str(Path(raiz) / "instalador" / "preflight-accesos.py"),
           "--politica", str(politica), "--acceso", str(acceso), "--modo", modo, "--partida", partida, "--json"]
    if degradado:
        cmd += ["--aceptar-degradado", "datos"]
    r = correr(cmd)
    return r.returncode, r.stdout, r.stderr


def puerta_de_accesos(raiz, carpeta, modo, partida, politica, acceso, degradado):
    """Ejecuta el preflight. Devuelve (informe_dict | None). Se detiene si no puede orquestar."""
    carpeta = Path(carpeta)
    pol = Path(politica) if politica else (carpeta / "politicas.toml")
    if not pol.exists():
        pol = Path(raiz) / "politicas" / "politicas.defecto.toml"
    tmp = None
    if acceso:
        acc = Path(acceso)
    elif (carpeta / "acceso.local.toml").exists():
        acc = carpeta / "acceso.local.toml"
    else:
        tmp = tempfile.mkdtemp(prefix="harness-acceso-")
        acc = Path(tmp) / "acceso.local.toml"
        acc.write_text("", encoding="utf-8")
    try:
        codigo, salida, err = correr_preflight(raiz, partida, modo, pol, acc, degradado)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    if codigo == 1:
        raise Detener("Puerta de accesos: error de configuracion.\n" + (err.strip() or salida.strip()), 1)
    try:
        inf = json.loads(salida)
    except json.JSONDecodeError:
        raise Detener("Puerta de accesos: salida ilegible del preflight.\n" + salida + err, 1)
    lineas = [f"Puerta de accesos (partida {inf['partida']}, modo {inf['modo']}):"]
    for f in inf["filas"]:
        pedir = f.get("pedir") or f.get("detalle") or ""
        lineas.append(f"  {f['recurso']:<24}{f['metodo']:<16}{f['estado']:<11}{pedir}")
    if codigo == 2:
        lineas.append("NO PUEDE ORQUESTAR. Falta (requerido): " + ", ".join(inf["faltan"]))
        for f in inf["filas"]:
            if f["estado"] == "FALTA" and f.get("requerido"):
                lineas.append(f"  - {f['recurso']}: {f['pedir']}")
        lineas.append("No se planifica ni se escribe nada. Resuelve lo anterior"
                      + (" o acepta el modo degradado con --aceptar-degradado (solo aplica a datos)." if modo != "migrar" else "."))
        raise Detener("\n".join(lineas), 2)
    if inf["degradados"]:
        lineas.append("MODO DEGRADADO DECLARADO: verificacion con datos NO DISPONIBLE (sin acceso) en: "
                      + ", ".join(inf["degradados"]))
    else:
        lineas.append("PUEDE ORQUESTAR.")
    print("\n".join(lineas))
    return inf


# ------------------------------------------------------------------ lector de entradas (partidas B y C)
def ruta_de_partida(carpeta, acceso, partida):
    """Carpeta con la informacion de partida declarada en el acceso local, o (None, nota)."""
    cand = Path(acceso) if acceso else Path(carpeta) / "acceso.local.toml"
    datos = toml_seguro(cand) if cand.exists() else None
    if not isinstance(datos, dict):
        return None, "no hay acceso local legible: no se pudo localizar la informacion de partida"
    if partida == "B":
        cfg = datos.get("documentacion") or {}
        ruta = cfg.get("carpeta")
        if not isinstance(ruta, str) or not ruta:
            return None, ("la informacion de partida esta en un gestor remoto (sin carpeta local): exportarla a .md, .csv o .xlsx "
                          "en una carpeta y declarar [documentacion] carpeta = \"<ruta>\" para que se lea")
    else:
        cfg = datos.get("origen") or {}
        ruta = cfg.get("ruta")
        if cfg.get("metodo") == "codigo":
            return None, ("el origen es codigo: el lector solo entiende .md, .sql, .csv, .tsv y .xlsx; "
                          "describir el origen en una carpeta con esos formatos (metodo = \"descripcion\")")
        if not isinstance(ruta, str) or not ruta:
            return None, "[origen] no declara ruta"
    return Path(os.path.expanduser(ruta)), None


def correr_lector(raiz, entradas):
    """Ejecuta harness-leer-entradas sobre la carpeta (solo lectura, cwd = la carpeta para rutas relativas).
    Devuelve (informe_json, informe_md). Exit 2 del lector -> Detener con su mensaje."""
    entradas = Path(entradas)
    tmp = None
    if entradas.is_file():
        tmp = tempfile.mkdtemp(prefix="harness-entradas-")
        shutil.copy2(entradas, Path(tmp) / entradas.name)
        entradas = Path(tmp)
    try:
        lector = str(Path(raiz) / "herramientas" / "harness-leer-entradas.py")
        res = {}
        for fmt in ("--json", "--md"):
            r = subprocess.run([sys.executable, lector, ".", fmt], capture_output=True, text=True, cwd=str(entradas))
            if r.returncode == 2:
                raise Detener("Informacion de partida: el lector no pudo entender nada.\n  " + r.stderr.strip().replace(str(entradas), "<carpeta>") +
                              "\n  Poner en la carpeta declarada ([documentacion] carpeta en B, [origen] ruta en C) al menos un .md, .sql, .csv, .tsv o .xlsx "
                              "con el modelo, el diccionario de campos o el esquema. Un pdf, docx o imagen se exporta a .md, .csv o .xlsx (ver docs/ENTRADAS.md).", 2)
            if r.returncode != 0:
                raise Detener("harness-leer-entradas fallo: " + (r.stderr.strip() or r.stdout.strip()), 1)
            res[fmt] = r.stdout
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return json.loads(res["--json"]), res["--md"]


def resumen_entendimiento(inf):
    mo = inf.get("motor")
    motor = f"{mo['propuesto']} (confianza {mo['confianza']}, propuesto, por confirmar)" if mo else "sin propuesta"
    return (f"  Entidades: {len(inf['entidades'])} (tablas SQL: {len(inf['tablas'])}) · relaciones: {len(inf['relaciones'])}\n"
            f"  Motor de base propuesto: {motor}\n"
            f"  Preguntas para quien aporta las entradas: {len(inf['preguntas'])} · abiertas del origen: {len(inf['preguntas_abiertas'])}\n"
            f"  Archivos leidos: {len(inf['leidos'])} · no leidos: {len(inf['no_leidos'])} · secretos enmascarados: {len(inf['secretos'])}")


def preguntas_md(inf):
    L = ["# Preguntas abiertas de la informacion de partida", "",
         "Generado por el instalador desde `.harness/entendimiento.md`. Este archivo es de la instancia: responder aqui; "
         "el instalador no lo reescribe.", "",
         f"## Para quien aporta las entradas ({len(inf['preguntas'])})", ""]
    for q in inf["preguntas"]:
        L += [f"- [ ] {q['pregunta']}", f"  - Se intento: {q['intento']}", "  - Respuesta: "]
    if not inf["preguntas"]:
        L.append("- ninguna")
    L += ["", f"## Abiertas en el origen ({len(inf['preguntas_abiertas'])})", ""]
    for q in inf["preguntas_abiertas"]:
        L += [f"- [ ] {q['texto']} ({q['origen']})", "  - Se intento: leerla tal cual del origen; no la responde el documento", "  - Respuesta: "]
    if not inf["preguntas_abiertas"]:
        L.append("- ninguna")
    return "\n".join(L) + "\n"


def agregar_entendimiento(plan, carpeta, inf, md, partida):
    carpeta = Path(carpeta)
    for ruta, contenido, crea_una_vez in ((".harness/entendimiento.md", md, False),
                                          (".harness/entendimiento.json", json.dumps(inf, ensure_ascii=False, indent=2, sort_keys=True) + "\n", False),
                                          (".harness/preguntas.md", preguntas_md(inf), True)):
        destino = carpeta / ruta
        if not destino.exists():
            plan.add(ruta, "crear", "propuesta para validar, generada por el lector de entradas", contenido)
        elif crea_una_vez:
            plan.add(ruta, "conservar", "es de la instancia: ahi se responden las preguntas")
        elif leer(destino) != contenido:
            plan.add(ruta, "actualizar", "las entradas cambiaron: propuesta regenerada", contenido)
        else:
            plan.add(ruta, "igual", "sin cambios")


def agregar_equivalencia(plan, carpeta, raiz):
    ruta = ".harness/equivalencia/plantilla-casos.md"
    contenido = leer(Path(raiz) / "plantillas" / "equivalencia.md")
    destino = Path(carpeta) / ruta
    if not destino.exists():
        plan.add(ruta, "crear", "plantilla de casos origen <-> nuevo (aqui van los casos de equivalencia)", contenido)
    elif leer(destino) == contenido:
        plan.add(ruta, "igual", "sin cambios")
    else:
        plan.add(ruta, "conservar", "la instancia lo edito: se preserva")


# ------------------------------------------------------------------ plan
class Plan:
    def __init__(self):
        self.acciones = []   # dict(ruta, accion, motivo, contenido?, diff?)
        self.estado_archivos = {}

    def add(self, ruta, accion, motivo, contenido=None, diff=None):
        self.acciones.append({"ruta": ruta, "accion": accion, "motivo": motivo, "contenido": contenido, "diff": diff})

    @property
    def hay_cambios(self):
        return any(a["accion"] in ("crear", "actualizar", "recrear") for a in self.acciones)

    def rutas_finales(self, carpeta):
        """Rutas que existiran al terminar (para el piso)."""
        rutas = {a["ruta"] for a in self.acciones if a["accion"] in ("crear", "actualizar", "recrear")}
        return rutas


def leer_estado(carpeta):
    p = Path(carpeta) / ESTADO_REL
    if not p.exists():
        return None
    try:
        e = json.loads(leer(p))
        if not isinstance(e, dict) or not isinstance(e.get("archivos"), dict):
            raise ValueError
        return e
    except (json.JSONDecodeError, ValueError):
        raise Detener(f"{ESTADO_REL} es ilegible o invalido: no se actualiza a ciegas. Revisalo o borralo.", 1)


def diff_corto(actual, nuevo, ruta, limite=30):
    d = list(difflib.unified_diff(actual.splitlines(), nuevo.splitlines(),
                                  f"{ruta} (en la instancia)", f"{ruta} (harness nuevo)", lineterm="", n=1))
    if len(d) > limite:
        d = d[:limite] + [f"... ({len(d) - limite} lineas mas)"]
    return "\n".join(d)


def planificar_archivos(plan, carpeta, raiz, version, fuente, partida, propuestas, previo):
    carpeta = Path(carpeta)
    prev = (previo or {}).get("archivos", {})
    registro = {}
    for ruta, tipo, nuevo in archivos_de_instancia(raiz, propuestas):
        destino = carpeta / ruta
        existe = destino.exists()
        actual = leer(destino) if existe else None
        p = prev.get(ruta)
        if tipo == INSTANCIA:
            if existe:
                plan.add(ruta, "conservar", "es de la instancia: se preserva")
                if p:
                    registro[ruta] = p
            elif p:
                plan.add(ruta, "falta-preservado", "la instancia lo borro; es suyo, no se recrea")
                registro[ruta] = p
            else:
                plan.add(ruta, "crear", "esqueleto inicial (a partir de la instancia en adelante es suyo)", nuevo)
                registro[ruta] = {"sha256": sha(nuevo), "tipo": INSTANCIA}
            continue
        # tipo HARNESS
        if p is None:
            if not existe:
                plan.add(ruta, "crear", "archivo del harness", nuevo)
                registro[ruta] = {"sha256": sha(nuevo), "tipo": HARNESS}
            elif actual == nuevo:
                plan.add(ruta, "igual", "ya coincide con el harness")
                registro[ruta] = {"sha256": sha(nuevo), "tipo": HARNESS}
            else:
                plan.add(ruta, "ajeno", "existe y no lo instalo el harness: no se pisa",
                         diff=diff_corto(actual, nuevo, ruta))
            continue
        if not existe:
            plan.add(ruta, "recrear", "archivo del harness que faltaba", nuevo)
            registro[ruta] = {"sha256": sha(nuevo), "tipo": HARNESS}
        elif sha(actual) == p["sha256"]:
            if sha(nuevo) == p["sha256"]:
                plan.add(ruta, "igual", "sin cambios")
                registro[ruta] = p
            else:
                plan.add(ruta, "actualizar", "el harness cambio y nadie lo modifico aqui", nuevo,
                         diff_corto(actual, nuevo, ruta))
                registro[ruta] = {"sha256": sha(nuevo), "tipo": HARNESS}
        elif actual == nuevo:
            plan.add(ruta, "igual", "coincide con el harness actual")
            registro[ruta] = {"sha256": sha(nuevo), "tipo": HARNESS}
        else:
            if sha(nuevo) == p["sha256"]:
                plan.add(ruta, "modificado-local", "modificado localmente; el harness no cambio")
            else:
                plan.add(ruta, "modificado-local", "modificado localmente: no se pisa; esto cambiaria",
                         diff=diff_corto(actual, nuevo, ruta))
            registro[ruta] = p
    # harness.lock
    lock = carpeta / "harness.lock"
    if lock.exists():
        try:
            datos = tomllib.loads(leer(lock))
        except tomllib.TOMLDecodeError:
            raise Detener("harness.lock no es TOML valido.", 1)
        fuente_l = datos.get("fuente", fuente)
        nuevo = lock_texto(version, fuente_l)
        if leer(lock) == nuevo:
            plan.add("harness.lock", "igual", f"version {version}")
        else:
            plan.add("harness.lock", "actualizar", f"version {datos.get('version')} -> {version}", nuevo)
    else:
        plan.add("harness.lock", "crear", f"fija la version {version}", lock_texto(version, fuente))
    estado = {"esquema": 1, "partida": (previo or {}).get("partida", partida), "version_harness": version,
              "archivos": dict(sorted(registro.items()))}
    return estado


# ------------------------------------------------------------------ piso (spec 7.2)
def toml_seguro(ruta):
    try:
        return tomllib.loads(leer(ruta))
    except (OSError, tomllib.TOMLDecodeError):
        return None


def piso(carpeta, proyecto, existira, acceso_ruta):
    """Lista de comprobacion del piso: (nombre, estado, detalle)."""
    carpeta = Path(carpeta)
    def hay(rel):
        return rel in existira or (carpeta / rel).exists()
    res = []
    res.append(("Especificacion validada antes de codificar",
                "instalado" if hay("cambios/README.md") else "pendiente",
                "carpeta de control de cambios con la puerta de validacion" if hay("cambios/README.md")
                else "falta cambios/ (se crea con init)"))
    acc = None
    for cand in (acceso_ruta, carpeta / "acceso.local.toml"):
        if cand and Path(cand).exists():
            acc = toml_seguro(cand)
            break
    doc = (acc or {}).get("documentacion", {}) if isinstance(acc, dict) else {}
    declarado = isinstance(doc, dict) and doc.get("metodo") not in (None, "", "sin_acceso")
    if hay("documentacion/README.md") and declarado:
        res.append(("Almacen de documentacion legible en .md", "instalado", f"metodo declarado: {doc['metodo']}"))
    elif hay("documentacion/README.md"):
        res.append(("Almacen de documentacion legible en .md", "requiere confirmacion",
                    "declarar [documentacion] en acceso.local.toml (carpeta del repo, Drive en .md o gestor)"))
    else:
        res.append(("Almacen de documentacion legible en .md", "pendiente", "falta documentacion/"))
    conv = toml_seguro(carpeta / "convenciones.toml") if (carpeta / "convenciones.toml").exists() else None
    pol = toml_seguro(carpeta / "politicas.toml") if (carpeta / "politicas.toml").exists() else None
    pasos = bool(conv and conv.get("gate.pasos")) or ("convenciones.toml" in existira and not conv)
    verif = bool(pol and "verificacion" in pol) or ("politicas.toml" in existira and not pol)
    comando = conv.get("gate.comando") if conv else None
    if pasos and verif and comando and "por definir" not in comando and "{{" not in comando:
        res.append(("Gate de calidad antes de cerrar", "instalado", "reglas y comando declarados"))
    elif pasos and verif:
        res.append(("Gate de calidad antes de cerrar", "requiere confirmacion",
                    "reglas declaradas; falta el comando del proyecto (gate.comando en convenciones.toml)"))
    else:
        res.append(("Gate de calidad antes de cerrar", "pendiente", "faltan convenciones.toml o politicas.toml"))
    base = Path(proyecto) if proyecto else carpeta
    herramienta = any(shutil.which(x) for x in ("codegraph", "fff"))
    indice = (base / ".codegraph").is_dir() or (carpeta / ".codegraph").is_dir()
    if indice:
        res.append(("Indexacion del codigo y actualizacion automatica", "instalado", "indice del codigo presente"))
    elif herramienta:
        res.append(("Indexacion del codigo y actualizacion automatica", "requiere confirmacion",
                    "hay una herramienta en el PATH pero no un indice: la persona lo crea y activa la actualizacion"))
    else:
        res.append(("Indexacion del codigo y actualizacion automatica", "pendiente",
                    "instalar un indexador de codigo y un buscador de archivos (el instalador no lo ejecuta)"))
    res.append(("Estandar unico de arquitectura y estilo",
                "instalado" if hay("convenciones.toml") else "pendiente",
                "convenciones.toml parte del estandar del harness" if hay("convenciones.toml") else "falta convenciones.toml"))
    return res


def piso_md(items):
    filas = ["# Piso del harness (lista de comprobacion)", "",
             "| Punto | Estado | Detalle |", "|---|---|---|"]
    filas += [f"| {n} | {e} | {d} |" for n, e, d in items]
    filas += ["", "Estados: instalado / pendiente / requiere confirmacion. La instalacion de herramientas externas "
              "se muestra, no se ejecuta.", ""]
    return "\n".join(filas)


def pasos_para_la_persona(carpeta, items, existira, acceso_dado):
    pasos = []
    c = Path(carpeta)
    if not (c / "acceso.local.toml").exists() and not acceso_dado:
        pasos.append("Copiar acceso.local.ejemplo.toml a acceso.local.toml y declarar tus metodos de acceso "
                     "(solo metodos, alias, puertos y nombres de perfil; nunca secretos).")
    pasos.append("Declarar los ambientes de datos en politicas.toml ([[datos.ambientes]]): el harness no asume ninguno.")
    pasos.append("Resolver los valores 'por definir' de convenciones.toml (incluido gate.comando).")
    for n, e, d in items:
        if e != "instalado" and n.startswith("Indexacion"):
            pasos.append("Instalar y activar el indexador de codigo y el buscador de archivos que elija el equipo, y "
                         "su actualizacion automatica, siguiendo la documentacion oficial de cada uno. "
                         "El instalador no los ejecuta ni usa la red.")
    if not (c / ".git").exists():
        pasos.append("Si la instancia va a versionarse: crear el repositorio y el primer commit (lo hace la persona).")
    return pasos


# ------------------------------------------------------------------ adopt
def detectar(raiz, proyecto, formato):
    r = correr([sys.executable, str(Path(raiz) / "herramientas" / "harness-detectar.py"), str(proyecto), f"--{formato}"])
    if r.returncode != 0:
        raise Detener("harness-detectar fallo: " + (r.stderr.strip() or r.stdout.strip()), 1)
    return r.stdout


def propuestas_desde_detectado(raiz, det):
    git = det.get("git", {})
    conv = det.get("convenciones", {})
    prop_conv = {}
    ramas = git.get("ramas_base") or []
    if ramas:
        prop_conv["ramas.base"] = (ramas[0], f"rama base {ramas[0]}")
    pct = conv.get("commits_convencionales_pct")
    if isinstance(pct, (int, float)) and pct < 50:
        prop_conv["commits.formato"] = ("texto libre", f"solo {pct}% de commits convencionales")
    if conv.get("claves_de_ticket_en_commits"):
        prop_conv["ramas.clave-de-ticket"] = ("si", "claves de ticket en los commits")
    texto_pol = politica_inicial(raiz)
    nombre = det.get("proyecto", "")
    if nombre:
        texto_pol = texto_pol.replace('nombre = ""', f'nombre = "{nombre}"', 1)
    if ramas:
        lista = ", ".join(f'"{r}"' for r in ramas)
        texto_pol = texto_pol.replace("ramas_protegidas = []", f"ramas_protegidas = [{lista}]  # detectado; confirmar", 1)
    return {"politica": texto_pol, "convenciones": convenciones_desde_estandar(raiz, prop_conv)}


def planificar_adopt(plan, carpeta, raiz, proyecto):
    carpeta = Path(carpeta)
    det = json.loads(detectar(raiz, proyecto, "json"))
    informe = detectar(raiz, proyecto, "md")
    prop = propuestas_desde_detectado(raiz, det)
    cuerpo = (informe.rstrip() + "\n\n## Propuesta del instalador\n\n"
              "Salen de lo detectado; la persona los valida. No se aplican solos.\n\n"
              "- Politica propuesta: `.harness/propuesta/politicas.propuesta.toml` (ambientes: " + POR_DECLARAR + ").\n"
              "- Convenciones propuestas: `.harness/propuesta/convenciones.propuesta.toml`.\n"
              "- Para instalar el esqueleto con esa propuesta: `instalar.sh init <instancia> --partida A --aplicar`.\n")
    for ruta, contenido in ((".harness/informe-adopt.md", cuerpo),
                            (".harness/propuesta/politicas.propuesta.toml", prop["politica"]),
                            (".harness/propuesta/convenciones.propuesta.toml", prop["convenciones"])):
        actual = leer(carpeta / ruta) if (carpeta / ruta).exists() else None
        if actual is None:
            plan.add(ruta, "crear", "informe/propuesta de adopt", contenido)
        elif actual != contenido:
            plan.add(ruta, "actualizar", "informe/propuesta regenerado", contenido)
        else:
            plan.add(ruta, "igual", "sin cambios")
    return det


def leer_propuestas_existentes(carpeta):
    d = Path(carpeta) / ".harness" / "propuesta"
    res = {}
    if (d / "politicas.propuesta.toml").exists():
        res["politica"] = leer(d / "politicas.propuesta.toml")
    if (d / "convenciones.propuesta.toml").exists():
        res["convenciones"] = leer(d / "convenciones.propuesta.toml")
    return res


# ------------------------------------------------------------------ salida y aplicacion
def mostrar_plan(plan, aplicar):
    print("\nPlan:")
    for a in plan.acciones:
        print(f"  [{a['accion']}] {a['ruta']}: {a['motivo']}")
        if a["accion"] in ("modificado-local", "ajeno", "actualizar") and a["diff"]:
            print("      " + a["diff"].replace("\n", "\n      "))
    if not plan.hay_cambios:
        print("  Sin cambios que escribir.")
    ml = [a["ruta"] for a in plan.acciones if a["accion"] == "modificado-local"]
    if ml:
        print("\nModificados localmente (se dejan como estan): " + ", ".join(ml))
    if not aplicar:
        print("\nModo plan: NO se escribio nada. Repite con --aplicar para ejecutarlo.")


def escribir(carpeta, ruta, contenido):
    destino = Path(carpeta) / ruta
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(contenido, encoding="utf-8", newline="\n")


def agregar_informes(plan, carpeta, estado, items, degradado_inf):
    """Estado, piso y limites: archivos generados por el instalador (se comparan para no reescribir)."""
    carpeta = Path(carpeta)
    generados = []
    if estado is not None:
        generados.append((ESTADO_REL, json.dumps(estado, indent=2, sort_keys=True, ensure_ascii=False) + "\n"))
    generados.append((".harness/piso.md", piso_md(items)))
    if degradado_inf and degradado_inf.get("degradados"):
        generados.append((".harness/limites.md",
                          "# Limite registrado: modo degradado de accesos\n\n"
                          "verificacion con datos: NO DISPONIBLE (sin acceso)\n"
                          "ambientes_afectados: " + ", ".join(degradado_inf["degradados"]) + "\n"
                          "efecto: los gates muestran la verificacion con datos como no disponible; "
                          "no se aprueba en silencio.\n"))
    for ruta, contenido in generados:
        destino = carpeta / ruta
        if not destino.exists():
            plan.add(ruta, "crear", "generado por el instalador", contenido)
        elif leer(destino) != contenido:
            plan.add(ruta, "actualizar", "generado por el instalador", contenido)
        else:
            plan.add(ruta, "igual", "sin cambios")


def aplicar_plan(plan, carpeta):
    for a in plan.acciones:
        if a["accion"] in ("crear", "actualizar", "recrear") and a["contenido"] is not None:
            escribir(carpeta, a["ruta"], a["contenido"])


# ------------------------------------------------------------------ principal
def main(argv=None):
    ap = argparse.ArgumentParser(prog="instalar.sh", description="Instalador del meta harness (plan por defecto).")
    ap.add_argument("modo", choices=MODOS)
    ap.add_argument("carpeta")
    ap.add_argument("--partida", choices=("A", "B", "C"))
    ap.add_argument("--acceso")
    ap.add_argument("--politica")
    ap.add_argument("--proyecto", help="adopt: proyecto a analizar si es otro distinto de la instancia")
    ap.add_argument("--aceptar-degradado", action="store_true")
    ap.add_argument("--aceptar-dentro-de-repo", action="store_true")
    ap.add_argument("--harness", help="raiz del harness (por defecto, la de este instalador)")
    ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args(argv)
    raiz = Path(a.harness).resolve() if a.harness else Path(__file__).resolve().parent.parent
    try:
        return ejecutar(a, raiz)
    except Detener as e:
        print(str(e), file=sys.stderr if e.codigo == 1 else sys.stdout)
        return e.codigo


def ejecutar(a, raiz):
    modo = a.modo
    partida = a.partida or PARTIDA_DE_MODO.get(modo)
    if modo == "adopt" and partida != "A":
        raise Detener("adopt es la partida A (proyecto empezado).")
    if modo == "migrar" and partida != "C":
        raise Detener("migrar es la partida C (migracion).")
    if modo == "init" and partida not in ("A", "B"):
        raise Detener("init admite --partida A (esqueleto sobre un proyecto empezado) o B (desde cero).")
    version = leer(raiz / "VERSION").strip()
    carpeta_arg = a.carpeta
    proyecto = a.proyecto if modo == "adopt" else None
    if proyecto is None and modo == "adopt":
        proyecto = carpeta_arg
    if modo == "adopt" and not Path(proyecto).is_dir():
        raise Detener(f"No existe la carpeta del proyecto: {proyecto}")
    if modo == "update" and not Path(carpeta_arg).is_dir():
        raise Detener(f"No existe la instancia: {carpeta_arg}. Usa init.")
    carpeta = validar_carpeta(carpeta_arg, raiz, proyecto if a.proyecto else None, modo, a.aceptar_dentro_de_repo)

    ver, _ = comprobar_version(raiz, carpeta)
    for m in ver.get("mensajes", []):
        print(m)

    previo = leer_estado(carpeta) if carpeta.exists() else None
    degradado_inf = None
    if modo != "update":
        degradado_inf = puerta_de_accesos(raiz, carpeta, modo, partida, a.politica, a.acceso, a.aceptar_degradado)

    entend = None
    if modo != "update" and (modo == "migrar" or (modo == "init" and partida == "B")):
        entradas, nota = ruta_de_partida(carpeta, a.acceso, partida)
        if entradas is None:
            print("\nInformacion de partida: no se leyo (" + nota + ").")
        else:
            er = entradas.resolve()
            if er == carpeta or er in carpeta.parents:
                raise Detener("La instancia no puede estar dentro de la carpeta de entradas: el informe se escribe en la instancia "
                              "y las entradas no se modifican.")
            entend = correr_lector(raiz, entradas)
            print("\nLo que se entendio de la informacion de partida (propuesta para validar, no se aplica sola):")
            print(resumen_entendimiento(entend[0]))

    plan = Plan()
    estado = None
    existira = set()
    if modo == "adopt":
        planificar_adopt(plan, carpeta, raiz, proyecto)
        existira = {x["ruta"] for x in plan.acciones}
    else:
        if modo == "update":
            if previo is None or not (carpeta / "harness.lock").exists():
                raise Detener("No es una instancia instalada (falta harness.lock o .harness/estado.json): usa init.")
            lock = tomllib.loads(leer(carpeta / "harness.lock"))
            vl, vh = version_tupla(str(lock.get("version", ""))), version_tupla(version)
            if vl and vh and vl > vh:
                raise Detener(f"La instancia fija la version {lock['version']}, mas nueva que este harness ({version}): "
                              "no se baja de version.")
            propuestas = {}
            partida = previo.get("partida", partida)
        else:
            propuestas = leer_propuestas_existentes(carpeta) if partida == "A" else {}
            if entend:
                propuestas["politica"] = politica_con_motor(raiz, entend[0].get("motor"))
        if modo != "update" and previo is not None:
            print("La carpeta ya es una instancia: init/migrar equivale a update (no se repite la creacion).")
        estado = planificar_archivos(plan, carpeta, raiz, version, str(raiz), partida, propuestas, previo)
        existira = {x["ruta"] for x in plan.acciones if x["accion"] in ("crear", "actualizar", "recrear", "igual", "conservar")}
    if entend:
        agregar_entendimiento(plan, carpeta, entend[0], entend[1], partida)
        existira |= {x["ruta"] for x in plan.acciones}
    if modo == "migrar":
        agregar_equivalencia(plan, carpeta, raiz)
    items = piso(carpeta, proyecto, existira, a.acceso)
    agregar_informes(plan, carpeta, estado, items, degradado_inf)
    mostrar_plan(plan, a.aplicar)
    print("\nPiso del harness (lista de comprobacion):")
    for n, e, d in items:
        print(f"  [{e}] {n}: {d}")
    pasos = pasos_para_la_persona(carpeta, items, existira, a.acceso)
    if entend:
        pasos.insert(0, "Validar lo entendido: leer .harness/entendimiento.md, responder .harness/preguntas.md y confirmar (o corregir) "
                        "el motor de base propuesto y las entidades antes de generar nada. Nada de eso se aplica solo.")
    if modo == "migrar":
        pasos += ["Replicar primero lo que hace el sistema origen, con sus reglas (tambien las que parecen errores); no aplicar mejoras en la replica.",
                  "Anotar cada mejora detectada: harness-mejoras.py --instancia <instancia> nueva --titulo ... --donde ... --cambio ... "
                  "--motivo ... --riesgo bajo|medio|alto --esfuerzo S|M|L --visible si|no",
                  "Comparar origen y nuevo: guardar los casos (segun .harness/equivalencia/plantilla-casos.md) como JSON o CSV en "
                  ".harness/equivalencia/ y correr harness-equivalencia.py <casos.json|casos.csv>."]
    print("\nPasos para la persona (el instalador no los ejecuta):")
    for i, p in enumerate(pasos, 1):
        print(f"  {i}. {p}")
    if a.aplicar:
        carpeta.mkdir(parents=True, exist_ok=True)
        aplicar_plan(plan, carpeta)
        n = sum(1 for x in plan.acciones if x["accion"] in ("crear", "actualizar", "recrear"))
        print(f"\nAplicado: {n} archivo(s) escritos en {carpeta}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
