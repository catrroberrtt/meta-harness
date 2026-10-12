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
import json
import pathlib
import re
import shutil
import stat
import sys
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


def sustituir(texto, v):
    for k, val in v.items():
        texto = texto.replace("{{" + k + "}}", val)
    return texto


def construir(a, mods, ags, pers):
    """Devuelve {ruta_relativa: contenido_texto|bytes} sin escribir nada."""
    final, _ = resolver(mods)
    hoy = dt.date.today().isoformat()
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
    a = ap.parse_args(argv)
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
    archivos = construir(a, mods, ags, pers)
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
