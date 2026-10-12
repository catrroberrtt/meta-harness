#!/usr/bin/env python3
"""Genera un ENTORNO independiente a partir de módulos elegidos. <!-- tipo: herramienta · capa: 4 -->

El resultado es un repositorio que funciona solo: sus scripts y hooks son copias, sin enlace con el meta-harness.
Otra persona lo clona y lo usa sin instalar nada de aquí. Solo biblioteca estándar.

  harness-entorno.py --listar
  harness-entorno.py --nombre mi-entorno --destino ~/proyectos/mi-entorno \
      --modulos documentacion-primero,compuerta-calidad,autoguardado --agentes claude,codex [--perfiles a,b] [--aplicar]

Sin --aplicar solo muestra el plan y no escribe nada. Escribe únicamente dentro de --destino, que debe no existir o estar vacío.
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import shutil
import stat
import sys
import tempfile
import tomllib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PLANTILLAS = RAIZ / "plantillas" / "entorno"
VERSION = (RAIZ / "VERSION").read_text(encoding="utf8").strip() if (RAIZ / "VERSION").exists() else "desconocida"

# módulo -> descripción, archivos (plantilla, destino), módulos que arrastra, hooks de Claude Code
MODULOS = {
    "documentacion-primero": {
        "descripcion": "Documentación antes que código y datos; buscador y recordatorio automático",
        "archivos": [("buscar-documentacion.py", "scripts/buscar-documentacion.py"),
                     ("documentacion-primero.py", "hooks/documentacion-primero.py"),
                     ("../nucleo/_comandos.py", "hooks/_comandos.py")],
        "requiere": [],
        "hooks": [("UserPromptSubmit", "", "documentacion-primero.py")],
    },
    "compuerta-calidad": {
        "descripcion": "Compuerta antes de entregar (tus comandos + secretos) y aviso antes de commitear",
        "archivos": [("gate.sh", "scripts/gate.sh"), ("gate-antes-de-commit.py", "hooks/gate-antes-de-commit.py"),
                     ("../nucleo/_comandos.py", "hooks/_comandos.py")],
        "requiere": ["escaneo-secretos"],
        "hooks": [("PreToolUse", "Bash", "gate-antes-de-commit.py")],
    },
    "conocimiento": {
        "descripcion": "Índice del conocimiento y control de frescura de los documentos",
        "archivos": [("INDICE.md.tpl", "knowledge/INDICE.md"), ("frescura.py", "scripts/frescura.py")],
        "requiere": [],
        "hooks": [],
    },
    "escaneo-secretos": {
        "descripcion": "Escaneo de claves, tokens y credenciales en lo versionado",
        "archivos": [("escanear-secretos.py", "scripts/escanear-secretos.py")],
        "requiere": [],
        "hooks": [],
    },
    "autoguardado": {
        "descripcion": "Commit automático al cerrar la sesión (subida opcional y desactivada por defecto)",
        "archivos": [("autoguardar.py", "scripts/autoguardar.py"), ("autoguardado.sh", "hooks/autoguardado.sh")],
        "requiere": ["escaneo-secretos"],
        "hooks": [("Stop", "", "autoguardado.sh")],
    },
    "publicar-solo-verificado": {
        "descripcion": "Nada se publica (PR, comentario, nota de versión) sin verificar el texto contra sus fuentes",
        "archivos": [("verificar-publicacion.py", "scripts/verificar-publicacion.py"),
                     ("revisor-independiente.md", "docs/revisor-independiente.md"),
                     ("publicar-solo-verificado.py", "hooks/publicar-solo-verificado.py"),
                     ("../nucleo/_comandos.py", "hooks/_comandos.py")],
        "requiere": [],
        "hooks": [("PreToolUse", "Bash", "publicar-solo-verificado.py")],
        "toml": """
[publicar]
# Comandos que publican texto hacia otras personas. El hook exige la marca de verificación del texto exacto.
comandos = ["gh pr create", "gh pr edit", "gh pr comment", "gh pr review", "gh pr merge", "gh issue create", "gh issue comment", "gh issue edit", "gh release create", "gh release edit"]
# 1 = comprobación mecánica; 2 = además, revisión independiente (docs/revisor-independiente.md).
exigir_nivel = 1
ttl_horas = 3

# De dónde sale la verdad de cada referencia. Un bloque por tipo; el comando recibe el identificador en {id}, debe
# terminar con 0 si existe e imprimir el estado en la primera línea. Ejemplo (descomenta y adapta):
# [[publicar.referencias]]
# nombre = "ticket"
# patron = "[A-Z]+-[0-9]+"
# comprobar = ["./scripts/estado-ticket.sh", "{id}"]
# estados_cerrados = ["DONE", "CERRADO"]
""",
        "regla": """## Antes de publicar texto

Nada sale hacia otras personas (PR, comentario, nota de versión) sin verificación. Escribe el texto en un archivo,
corre `python3 scripts/verificar-publicacion.py revisar <archivo>` y publica con `--body-file <archivo>`. Editar el texto
invalida la verificación. Lo que no se pudo comprobar se escribe en el texto como pendiente, no como hecho.
""",
    },
    "bloqueo-datos": {
        "descripcion": "El agente no escribe en bases de datos ni se conecta a ambientes que no son locales (barrera, no garantía)",
        "archivos": [("bloquear-datos.py", "hooks/bloquear-datos.py"), ("../nucleo/_comandos.py", "hooks/_comandos.py")],
        "requiere": [],
        "hooks": [("PreToolUse", "Bash", "bloquear-datos.py")],
        "toml": """
[datos]
# Hosts a los que el agente puede conectarse con un cliente de base de datos. Todo lo demás se rechaza.
hosts_permitidos = ["127.0.0.1", "localhost", "::1"]
# true = ni siquiera en un host permitido se escribe (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE...). La garantía real es que el
# usuario de base de datos del agente sea de SOLO LECTURA; este hook evita el descuido y deja rastro.
solo_lectura = true
""",
        "regla": """## Bases de datos

El agente **solo lee** y **solo en ambientes locales**. Una escritura, un cambio de esquema o una conexión a otro ambiente se le entrega a la persona
como comando o SQL. La configuración está en `[datos]` de `entorno.toml`.
""",
    },
    "formato-de-pr": {
        "descripcion": "Un PR no se crea sin las secciones que exige su tipo (pase a producción, observaciones...), según tus tipos declarados",
        "archivos": [("formato-de-pr.py", "hooks/formato-de-pr.py"), ("../nucleo/_comandos.py", "hooks/_comandos.py")],
        "requiere": [],
        "hooks": [("PreToolUse", "Bash", "formato-de-pr.py")],
        "toml": """
# Tipos de PR y las secciones que cada uno exige. Sin tipos declarados, el módulo no hace nada. Ejemplo (descomenta y adapta):
# [[pr.tipos]]
# nombre = "pase a producción"
# cuando_base = "^main$"             # se reconoce por la rama base...
# secciones = ["Resumen del cambio", "Plan de despliegue", "Plan de respaldo"]
#
# [[pr.tipos]]
# nombre = "corrección"
# cuando_titulo = "^fix"             # ...o por el título
# secciones = ["Qué resuelve", "Pruebas"]
""",
        "regla": """## Formato de los PR

El cuerpo de un PR se escribe en un archivo (`--body-file`) con las secciones de su tipo (ver `[[pr.tipos]]` en `entorno.toml`). Cada sección va como
encabezado. Si falta una, el PR no se crea.
""",
    },
    "inventario-de-fuentes": {
        "descripcion": "Foto de los repositorios antes de analizar: contra qué rama de referencia se compara y líneas de sello para pegar",
        "archivos": [("inventario-fuentes.py", "scripts/inventario-fuentes.py")],
        "requiere": [],
        "hooks": [],
        "toml": """
[fuentes]
# Días que un sello `verificado-contra-git` se considera vigente (lo revisa scripts/sellos.py).
vigencia_dias = 7

# Repositorios de los que depende un análisis. «referencia» es contra lo que se compara: la rama validada, no la rama local de turno.
# [[fuentes.repos]]
# nombre = "api"
# ruta = "~/proyectos/api"
# referencia = "origin/main"
""",
        "regla": """## Antes de afirmar qué existe o qué falta

Corre `python3 scripts/inventario-fuentes.py` y pega las líneas `verificado-contra-git` al principio del análisis. Una afirmación sobre «lo que existe» se
contrasta contra la rama de referencia de cada repositorio, no contra la rama local de turno.
""",
    },
    "sello-de-verificacion": {
        "descripcion": "Los sellos `verificado-contra-git` de los documentos caducan: se revisan contra la rama de referencia",
        "archivos": [("sellos.py", "scripts/sellos.py")],
        "requiere": ["inventario-de-fuentes"],
        "hooks": [],
        "regla": """## Sellos de verificación

Un documento de estado lleva `verificado-contra-git: <commit> · <repo> · <fecha>`. Ese sello caduca: `python3 scripts/sellos.py` dice cuáles siguen
vigentes, cuáles están atrasados frente a la referencia y cuáles no existen. Un documento con sello atrasado se relee antes de fiarse de él.
""",
    },
    "aprendizaje": {
        "descripcion": "Lecciones con evidencia: no hay regla sin evidencia y toda regla se revierte",
        "archivos": [("aprender.py", "scripts/aprender.py"), ("aprendizaje.md.tpl", "knowledge/aprendizaje.md")],
        "requiere": [],
        "hooks": [],
    },
}
AGENTES = {"claude": "Claude Code", "codex": "Codex (lee AGENTS.md)"}
NOMBRE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")


def perfiles_disponibles():
    base = RAIZ / "perfiles"
    return sorted(p.name for p in base.iterdir() if p.is_dir() and not p.name.startswith("_")) if base.is_dir() else []


def inspeccionar(archivos):
    """Inspección previa a escribir (el generado no se escribe si no se puede interpretar): entorno.toml y settings.json
    deben parsear y el nombre/módulos/agentes del TOML deben ser exactamente los pedidos. Devuelve lista de problemas."""
    problemas = []
    try:
        cfg = tomllib.loads(archivos["entorno.toml"])
        if set(cfg["entorno"]["modulos"]) - set(MODULOS):
            problemas.append("entorno.toml declara módulos que no existen")
    except (tomllib.TOMLDecodeError, KeyError) as e:
        problemas.append(f"entorno.toml generado no es válido: {e}")
    if ".claude/settings.json" in archivos:
        try:
            json.loads(archivos[".claude/settings.json"])
        except ValueError as e:
            problemas.append(f".claude/settings.json generado no es válido: {e}")
    for ruta in archivos:
        pr = pathlib.PurePosixPath(ruta)
        if pr.is_absolute() or ".." in pr.parts:
            problemas.append(f"ruta de salida fuera del destino: {ruta}")
    return problemas


def huella(texto):
    return hashlib.sha256(texto.encode("utf8")).hexdigest()


LOCK = "entorno.lock.json"
METADATO = {"docs/ORIGEN.md", LOCK}  # cambian con cada versión del generador sin que eso sea una mejora del entorno


def con_lock(archivos, opciones):
    """Agrega entorno.lock.json: con qué opciones se generó y el hash de cada archivo en ese momento (base de la comparación)."""
    lock = {"generador": f"meta-harness {VERSION}", "fecha": dt.date.today().isoformat(), "opciones": opciones,
            "archivos": {r: huella(c) for r, c in sorted(archivos.items())}}
    return {**archivos, LOCK: json.dumps(lock, indent=2, ensure_ascii=False) + "\n"}


def comparar(destino, aplicar_seguras=False):
    """Tres vías por archivo: base (lock) / actual (disco) / nuevo (lo que generaría hoy con las mismas opciones). Solo lectura salvo
    --aplicar-seguras, que copia únicamente archivos que la persona NO tocó y que el generador mejoró."""
    destino = pathlib.Path(destino).expanduser().resolve()
    ruta_lock = destino / LOCK
    if not ruta_lock.is_file():
        print(f"ERROR: {destino} no tiene {LOCK}: no se generó con este harness (o es de una versión anterior).", file=sys.stderr)
        return 2
    try:
        lock = json.loads(ruta_lock.read_text(encoding="utf8"))
        op = lock["opciones"]
        base = lock["archivos"]
        if not isinstance(base, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in base.items()):
            raise ValueError("forma inesperada")
    except (ValueError, KeyError, TypeError):
        print(f"ERROR: {LOCK} no se puede interpretar.", file=sys.stderr)
        return 2
    inseguras = [k for k in base if pathlib.PurePosixPath(k).is_absolute() or ".." in pathlib.PurePosixPath(k).parts]
    if inseguras:  # el lock es un archivo del repo: no se confía en él para leer ni escribir fuera de la carpeta
        print(f"ERROR: {LOCK} contiene rutas fuera de la carpeta ({inseguras[0]}): no se compara.", file=sys.stderr)
        return 2
    args = argparse.Namespace(nombre=op["nombre"], destino=str(destino), modulos=",".join(op["modulos"]), agentes=",".join(op["agentes"]),
                              perfiles=",".join(op["perfiles"]))
    errores, mods, ags, pers = validar_sin_destino(args)
    if errores:
        for e in errores:
            print("ERROR:", e, file=sys.stderr)
        return 2
    nuevo = construir(args, mods, ags, pers, fecha=lock.get("fecha"))
    nuevo_h = {r: huella(c) for r, c in nuevo.items()}
    informe = {"sin_cambios": [], "actualizacion_disponible": [], "editado_por_ti": [], "conflicto": [], "nuevo_en_generador": [],
               "retirado_por_generador": [], "borrado_por_ti": []}
    for r in sorted(set(base) | set(nuevo_h)):
        b, n = base.get(r), nuevo_h.get(r)
        f = destino / r
        c = huella(f.read_text(encoding="utf8", errors="replace")) if f.is_file() else None
        if r in METADATO:
            continue
        if b is None:
            informe["conflicto" if c is not None else "nuevo_en_generador"].append(r)
        elif n is None:
            informe["retirado_por_generador"].append(r)
        elif c is None:
            informe["borrado_por_ti"].append(r)
        elif c == b and n == b:
            informe["sin_cambios"].append(r)
        elif c == b:
            informe["actualizacion_disponible"].append(r)
        elif n == b or c == n:
            informe["editado_por_ti"].append(r)
        else:
            informe["conflicto"].append(r)
    etiquetas = [("actualizacion_disponible", "SEGURO   ", "el generador mejoró un archivo que no tocaste"),
                 ("nuevo_en_generador", "SEGURO   ", "archivo nuevo del generador que no tienes"),
                 ("conflicto", "REVISAR  ", "cambiaste tú y cambió el generador: compáralos a mano"),
                 ("editado_por_ti", "TUYO     ", "lo cambiaste tú; el generador no lo tocó"),
                 ("borrado_por_ti", "INFO     ", "lo borraste tú"),
                 ("retirado_por_generador", "INFO     ", "el generador ya no lo produce")]
    print(f"Comparación de {destino.name}: generado con {lock.get('generador')} el {lock.get('fecha')}; hoy el generador es meta-harness {VERSION}")
    print(f"  sin cambios: {len(informe['sin_cambios'])} archivo(s)")
    for clave, marca, texto in etiquetas:
        for r in informe[clave]:
            print(f"  {marca} {r}  ({texto})")
    seguros = informe["actualizacion_disponible"] + informe["nuevo_en_generador"]
    if not any(informe[k] for k, _, _ in etiquetas):
        print("  Sin diferencias: el entorno coincide con lo que generaría hoy este harness.")
    if not aplicar_seguras:
        if seguros:
            print(f"\nPara copiar solo lo SEGURO ({len(seguros)} archivo(s)): vuelve a correr con --aplicar-seguras. Lo de REVISAR nunca se toca solo.")
        return 1 if informe["conflicto"] else 0
    for r in seguros:
        f = destino / r
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(nuevo[r], encoding="utf8")
        if r.endswith((".sh", ".py")):
            f.chmod(f.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        base[r] = nuevo_h[r]
    lock["archivos"] = base
    lock["generador"] = f"meta-harness {VERSION}"
    ruta_lock.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print(f"\nAplicados {len(seguros)} archivo(s) seguros y actualizado {LOCK}. Lo de REVISAR queda como estaba.")
    return 1 if informe["conflicto"] else 0


# Codex usa el mismo formato de entrada y de respuesta de bloqueo que Claude Code (adaptadores-agente/codex/FORMATO.md §3), pero:
#  - solo se generan los hooks de PreToolUse sobre Bash (matcher «^Bash$»): son los que el adaptador documenta con su esquema;
#  - el autoguardado va en SessionEnd (documentado, NO probado: se avisa en docs/CODEX.md);
#  - UserPromptSubmit no se genera: su formato de salida en Codex no está confirmado con fuente.
CODEX_EVENTOS = {"PreToolUse": "^Bash$", "Stop": None}


def codex_hooks(hooks):
    doc = {"_generado_por": "meta-harness (entorno propio): ver docs/CODEX.md. Un hook nuevo no corre hasta que lo confíes con /hooks en Codex.", "hooks": {}}
    for evento, lst in hooks.items():
        if evento == "PreToolUse":
            destino, matcher = "PreToolUse", CODEX_EVENTOS["PreToolUse"]
        elif evento == "Stop":
            destino, matcher = "SessionEnd", None
        else:
            continue
        grupos = doc["hooks"].setdefault(destino, [])
        for h in lst:
            exe = "python3" if h["script"].endswith(".py") else "bash"
            entrada = {"type": "command", "command": f'{exe} "$(git rev-parse --show-toplevel)/hooks/{h["script"]}"', "timeout": 30,
                       "statusMessage": f"{h['script'].rsplit('.', 1)[0]}"}
            grupos.append({**({"matcher": matcher} if matcher else {}), "hooks": [entrada]})
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def resolver(modulos):
    """Agrega las dependencias y devuelve (lista ordenada, agregados)."""
    final, agregados = [], []
    for m in modulos:
        for dep in MODULOS[m]["requiere"]:
            if dep not in modulos and dep not in agregados:
                agregados.append(dep)
    for m in list(MODULOS):
        if m in modulos or m in agregados:
            final.append(m)
    return final, agregados


def validar(a):
    errores = []
    if not NOMBRE.fullmatch(a.nombre or ""):  # fullmatch: con `$` un salto de línea final pasaba y corrompía entorno.toml
        errores.append("--nombre: minúsculas, números y guiones, de 2 a 41 caracteres, sin empezar por guion")
    mods = [m for m in (a.modulos or "").split(",") if m]
    if not mods:
        errores.append("--modulos: elige al menos uno (mira --listar)")
    for m in mods:
        if m not in MODULOS:
            errores.append(f"módulo desconocido: «{m}» (disponibles: {', '.join(MODULOS)})")
    ags = [x for x in (a.agentes or "").split(",") if x]
    for x in ags:
        if x not in AGENTES:
            errores.append(f"agente desconocido: «{x}» (disponibles: {', '.join(AGENTES)})")
    pers = [p for p in (a.perfiles or "").split(",") if p]
    disponibles = perfiles_disponibles()
    for p in pers:
        if p not in disponibles:  # lista cerrada: un nombre como «../x» nunca se interpreta como ruta
            errores.append(f"perfil desconocido: «{p}» (disponibles: {', '.join(disponibles)})")
    if a.destino:
        d = pathlib.Path(a.destino).expanduser().resolve()
        if d == RAIZ or RAIZ in d.parents:
            errores.append("--destino no puede estar dentro del meta-harness: el entorno debe vivir aparte")
        if d.exists() and any(d.iterdir()):
            errores.append(f"--destino ya existe y no está vacío: {d}")
    else:
        errores.append("--destino es obligatorio")
    return errores, mods, ags, pers


def validar_sin_destino(a):
    """Como validar(), pero sin exigir un destino nuevo y vacío (para comparar un entorno que ya existe)."""
    original = a.destino
    a.destino = str(pathlib.Path(tempfile.gettempdir()) / "entorno-comparar-inexistente")
    try:
        return validar(a)
    finally:
        a.destino = original


def sustituir(texto, v):
    for k, val in v.items():
        texto = texto.replace("{{" + k + "}}", val)
    return texto


def construir(a, mods, ags, pers, fecha=None):
    """Devuelve {ruta_relativa: contenido_texto|bytes} sin escribir nada."""
    final, _ = resolver(mods)
    hoy = fecha or dt.date.today().isoformat()
    v = {
        "nombre": a.nombre, "fecha": hoy, "version_origen": VERSION,
        "lista_modulos": "\n".join(f"- **{m}**: {MODULOS[m]['descripcion']}" for m in final),
        "modulos_texto": ", ".join(final),
        "modulos_toml": ", ".join(f'"{m}"' for m in final),
        "agentes_toml": ", ".join(f'"{x}"' for x in ags),
        "nota_agentes": ("Claude Code carga `.claude/settings.json` y activa los hooks; Codex lee `AGENTS.md`."
                         if ags else "Cualquier agente que lea `AGENTS.md` funciona; los hooks son opcionales."),
    }
    out = {}
    v["reglas_modulos"] = "".join(MODULOS[m].get("regla", "") + "\n" for m in final if MODULOS[m].get("regla")).rstrip("\n")
    nuc = PLANTILLAS / "nucleo"
    for src, dst in [("README.md.tpl", "README.md"), ("AGENTS.md.tpl", "AGENTS.md"), ("entorno.toml.tpl", "entorno.toml"),
                     ("gitignore.tpl", ".gitignore"), ("ORIGEN.md.tpl", "docs/ORIGEN.md"),
                     ("instalar.sh.tpl", "instalar.sh"), ("verificar.sh.tpl", "verificar.sh")]:
        out[dst] = sustituir((nuc / src).read_text(encoding="utf8"), v)
    for m in final:
        if MODULOS[m].get("toml"):
            out["entorno.toml"] += MODULOS[m]["toml"]
    out["LICENSE"] = (RAIZ / "LICENSE").read_text(encoding="utf8")
    out["NOTICE"] = (f"{a.nombre}\n\nEste entorno incluye scripts y plantillas generados con meta-harness {VERSION} "
                     f"(Apache License 2.0, ver LICENSE).\n")
    hooks = {}
    for m in final:
        for src, dst in MODULOS[m]["archivos"]:
            out[dst] = sustituir((PLANTILLAS / m / src).read_text(encoding="utf8"), v)
        for evento, matcher, script in MODULOS[m]["hooks"]:
            hooks.setdefault(evento, []).append({"matcher": matcher, "script": script})
    if "codex" in ags and hooks:
        out[".codex/hooks.json"] = codex_hooks(hooks)
        out["docs/CODEX.md"] = (PLANTILLAS / "nucleo" / "CODEX.md.tpl").read_text(encoding="utf8")
    if "claude" in ags:
        cfg = {"hooks": {}}
        for evento, lst in hooks.items():
            cfg["hooks"][evento] = [{
                **({"matcher": h["matcher"]} if h["matcher"] else {}),
                "hooks": [{"type": "command", "command": (
                    f'{"python3" if h["script"].endswith(".py") else "bash"} "$CLAUDE_PROJECT_DIR/hooks/{h["script"]}"')}],
            } for h in lst]
        out[".claude/settings.json"] = json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"
        out["CLAUDE.md"] = "Lee `AGENTS.md`: ahí están las reglas de este repositorio.\n"
    for p in pers:
        for f in sorted((RAIZ / "perfiles" / p).rglob("*.md")):
            out[f"estandares/{p}/{f.relative_to(RAIZ / 'perfiles' / p)}"] = f.read_text(encoding="utf8")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--listar", action="store_true", help="muestra módulos, agentes y perfiles disponibles")
    ap.add_argument("--nombre")
    ap.add_argument("--destino")
    ap.add_argument("--modulos", help="separados por coma")
    ap.add_argument("--agentes", default="claude", help="claude, codex (por coma)")
    ap.add_argument("--perfiles", default="", help="estándares de stack a copiar (por coma)")
    ap.add_argument("--aplicar", action="store_true", help="escribe el entorno (sin esto solo muestra el plan)")
    ap.add_argument("--comparar", metavar="CARPETA", help="compara un entorno ya generado con lo que generaría hoy este harness (solo lectura)")
    ap.add_argument("--aplicar-seguras", action="store_true", help="con --comparar: copia solo los archivos que no tocaste y el generador mejoró")
    a = ap.parse_args(argv)
    if a.comparar:
        return comparar(a.comparar, a.aplicar_seguras)
    if a.listar:
        print("Módulos:")
        for m, d in MODULOS.items():
            dep = f" (arrastra: {', '.join(d['requiere'])})" if d["requiere"] else ""
            print(f"  {m:<22} {d['descripcion']}{dep}")
        print("Agentes: " + ", ".join(f"{k} ({v})" for k, v in AGENTES.items()))
        print("Perfiles: " + ", ".join(sorted(p.name for p in (RAIZ / 'perfiles').iterdir() if p.is_dir() and not p.name.startswith('_'))))
        return 0
    errores, mods, ags, pers = validar(a)
    if errores:
        for e in errores:
            print("ERROR:", e, file=sys.stderr)
        return 2
    final, agregados = resolver(mods)
    archivos = con_lock(construir(a, mods, ags, pers), {"nombre": a.nombre, "modulos": mods, "agentes": ags, "perfiles": pers})
    problemas = inspeccionar(archivos)
    if problemas:
        for pr in problemas:
            print("ERROR (inspección previa):", pr, file=sys.stderr)
        return 2
    destino = pathlib.Path(a.destino).expanduser().resolve()
    print(f"Entorno «{a.nombre}» → {destino}")
    print(f"  módulos: {', '.join(final)}" + (f"  (agregados por dependencia: {', '.join(agregados)})" if agregados else ""))
    print(f"  agentes: {', '.join(ags) or '(ninguno: solo AGENTS.md)'}   perfiles: {', '.join(pers) or '(ninguno)'}")
    print(f"  archivos: {len(archivos)}")
    for r in sorted(archivos):
        print(f"    {r}")
    if not a.aplicar:
        print("\nSolo se mostró el plan; no se escribió nada. Para generarlo: añade --aplicar")
        return 0
    for r, contenido in archivos.items():
        p = destino / r
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contenido, encoding="utf8")
        if r.endswith((".sh", ".py")):
            p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"\nGenerado. Siguiente: cd {destino} && ./instalar.sh --aplicar && ./verificar.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
