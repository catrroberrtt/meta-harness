#!/usr/bin/env python3
"""Ayuda común de los adaptadores con hook propio (OpenCode, Cursor, Codex, Gemini, Windsurf, Copilot): produce el hook de datos desde la política.

- NO reimplementa la política: carga `instalador/generar-politicas.py` del harness y usa su `construir` y `generar`
  (los mismos que usa el adaptador de Claude Code). La decisión (allow / ask / deny) la sigue tomando
  `block-db-access.sh`, generado desde `politicas.toml`.
- Añade un script puente, `guardia-datos.py`, que adapta la entrada y la salida de cada agente a esa decisión:
  OpenCode lo invoca desde un plugin (que lanza la excepción); Cursor, Codex y Gemini lo registran en su archivo de hooks.
- Para los agentes que fallan ABIERTOS ante un hook roto (Codex, Gemini, Windsurf, Copilot Local) se añade además un lanzador `lanzar.sh` (POSIX `sh`)
  que deniega él mismo si falta `python3` o el puente: el puente cubre sus propios errores; el lanzador cubre que ni arranque.
- Solo biblioteca estándar. No escribe nada: devuelve (nombre, contenido, modo) para que el adaptador planifique.

Cómo sumar un formato (Windsurf, Copilot...): 1) en `TEXTO_PUENTE`, agregar una entrada a `FORMATOS` con `extraer(datos) ->
(comando, cwd)`, `salida(decision, motivo) -> (stdout, stderr, codigo)` y `error(motivo)`; 2) agregar el nombre a `FORMATOS_PUENTE`
y, si el agente falla abierto, su denegación estática a `DENEGACION_LANZADOR`; 3) en el adaptador, llamar a
`archivos_de_hook(fuente, lanzador="<formato>")`. Los formatos existentes no se tocan: sus pruebas lo vigilan.
"""
import importlib.util
import tempfile
from pathlib import Path

import fuente_neutral as fn

HOOK_DECISION = "block-db-access.sh"
PUENTE = "guardia-datos.py"
LANZADOR = "lanzar.sh"
FORMATOS_PUENTE = ("opencode", "cursor", "codex", "gemini", "windsurf-cascade", "windsurf-devin", "copilot-local", "copilot-cli")

TEXTO_PUENTE = '''#!/usr/bin/env python3
# __MARCA__
"""Puente entre un agente y el hook de datos generado desde la política (`block-db-access.sh`, en esta misma carpeta).

Uso: guardia-datos.py [--formato opencode|cursor|codex|gemini|windsurf-cascade|windsurf-devin|copilot-local|copilot-cli]   (por defecto cursor, porque hooks.json lo registra sin argumentos; la entrada llega por la entrada estándar, como JSON)

- opencode: entrada {"command": ..., "cwd": ...}. Salida: {"decision": "allow|ask|deny", "reason": ...}, código 0.
            Ante cualquier fallo: decision "deny" y código 1 (el plugin bloquea).
- cursor:   entrada de `beforeShellExecution` {"command": ..., "cwd": ...}. Salida: {"permission": ...} y,
            si deniega, código 2. Ante cualquier fallo: deniega con código 2 (falla cerrado).
- codex:    entrada de `PreToolUse` {"tool_name": "Bash", "tool_input": {"command": ...}, "cwd": ...}. Deniega con el JSON
            `hookSpecificOutput.permissionDecision = "deny"` en stdout, la razón en stderr (obligatoria: sin ella Codex deja
            pasar) y código 2; permite sin escribir nada y con código 0. Codex no admite `ask`: se trata como denegar.
- gemini:   entrada de `BeforeTool` {"tool_name": "run_shell_command", "tool_input": {"command": ...}, "cwd": ...}. Deniega con
            {"decision": "deny", "reason": ...} y código 0 (cualquier código distinto de 0 y 2 equivale a permitir); permite con
            {"decision": "allow"}. Nada más en stdout. Gemini no admite `ask` en `BeforeTool`: se trata como denegar.
- windsurf-cascade: entrada de `pre_run_command` {"agent_action_name": ..., "tool_info": {"command_line": ..., "cwd": ...}}. Deniega con el motivo en stderr y
            código 2 (no hay respuesta JSON de decisión); permite sin escribir nada y con código 0.
- windsurf-devin:   entrada de `PreToolUse` de Devin Local {"hook_event_name": ..., "tool_name": "exec", "tool_input": {"command": ...}}. Deniega con
            {"decision": "block", "reason": ...} en stdout, el motivo en stderr y código 2; permite sin escribir nada y con código 0.
- copilot-local:    entrada de `PreToolUse` del arnés Local de VS Code (snake_case; `matcher` se ignora, así que filtra este script: se juzga
            cualquier herramienta cuyo `tool_input.command` sea texto). Deniega con `hookSpecificOutput.permissionDecision = "deny"` en stdout,
            el motivo en stderr y código 2.
- copilot-cli:      entrada de `preToolUse` de la CLI y del Agent Host (camelCase: `toolName`, `toolArgs`). Solo juzga `bash` y `powershell`. Deniega con
            {"permissionDecision": "deny", "permissionDecisionReason": ...} en stdout, el motivo en stderr y código 2 (esa superficie ya
            cierra ante cualquier error, salvo el tiempo agotado, que siempre deja pasar).
Codex, Gemini, Windsurf (ambos) y Copilot Local fallan ABIERTOS ante un hook roto; por eso este script atrapa cualquier error propio y deniega él mismo.
La decisión no se calcula aquí: la toma el hook generado desde la política.

Para sumar un formato: agregar una entrada a FORMATOS con `extraer(datos) -> (comando, cwd)`, `salida(decision, motivo) ->
(stdout, stderr, codigo)` y `error(motivo)`; `estricto` exige una entrada JSON no vacía.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(AQUI, "block-db-access.sh")
SIN_MOTIVO = "bloqueado por la política del proyecto"
PREGUNTAR = "Requiere confirmación de la persona y este agente no la admite en el hook: "


def j(obj):
    return json.dumps(obj, ensure_ascii=False)


def decidir(comando, cwd):
    for herramienta in ("bash", "jq", "git"):
        if shutil.which(herramienta) is None:
            raise RuntimeError(f"falta `{herramienta}` en el PATH: sin él el hook no puede decidir")
    entrada = json.dumps({"tool_input": {"command": comando}})
    r = subprocess.run(["bash", HOOK], input=entrada, capture_output=True, text=True, cwd=cwd, timeout=20)
    if r.returncode != 0:
        raise RuntimeError(f"el hook de datos terminó con código {r.returncode}: {r.stderr.strip()[:300]}")
    salida = r.stdout.strip()
    if not salida:
        return "allow", ""
    h = json.loads(salida)["hookSpecificOutput"]
    decision = h["permissionDecision"]
    if decision not in ("allow", "ask", "deny"):
        raise RuntimeError(f"decisión desconocida del hook: {decision!r}")
    return decision, h.get("permissionDecisionReason", "")


# ---- opencode y cursor: el comando viene en la raíz del objeto
def extraer_plano(datos):
    comando = datos.get("command") or ""
    cwd = datos.get("cwd") or os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd()
    return comando, cwd


def salida_opencode(decision, motivo):
    return j({"decision": decision, "reason": motivo}), "", 0


def error_opencode(motivo):
    return j({"decision": "deny", "reason": motivo}), "", 1


def salida_cursor(decision, motivo):
    if decision == "deny":
        return j({"continue": True, "permission": "deny", "user_message": motivo, "agent_message": motivo}), "", 2
    return j({"permission": decision, "user_message": motivo, "agent_message": motivo}), "", 0


def error_cursor(motivo):
    return salida_cursor("deny", motivo)


# ---- codex y gemini: el comando viene en `tool_input.command` y solo de la herramienta de shell
def extractor_herramienta(nombres, variables_cwd=()):
    def extraer(datos):
        if not isinstance(datos, dict):
            raise ValueError("la entrada no es un objeto JSON")
        cwd = datos.get("cwd") or next((os.environ[v] for v in variables_cwd if os.environ.get(v)), None) or os.getcwd()
        if datos.get("tool_name") not in nombres:
            return "", cwd                                   # otra herramienta: no la juzga este hook
        ti = datos.get("tool_input")
        comando = ti.get("command") if isinstance(ti, dict) else None
        if not isinstance(comando, str) or not comando.strip():
            raise ValueError("la herramienta de shell no trae `tool_input.command`")
        return comando, cwd
    return extraer


def salida_codex(decision, motivo):
    if decision == "allow":
        return "", "", 0
    if decision == "ask":
        motivo = PREGUNTAR + motivo
    motivo = motivo or SIN_MOTIVO
    cuerpo = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": motivo}}
    return j(cuerpo), motivo, 2          # la razón en stderr es obligatoria: salida 2 sin ella no bloquea


def error_codex(motivo):
    return salida_codex("deny", motivo)


def salida_gemini(decision, motivo):
    if decision == "allow":
        return j({"decision": "allow"}), "", 0
    if decision == "ask":
        motivo = PREGUNTAR + motivo
    motivo = motivo or SIN_MOTIVO
    return j({"decision": "deny", "reason": motivo, "systemMessage": motivo}), "", 0


def error_gemini(motivo):
    o, _, c = salida_gemini("deny", motivo)
    return o, motivo, c                  # el diagnóstico va por stderr; stdout solo lleva el JSON


# ---- windsurf (Cascade y Devin Local), copilot (Local de VS Code y CLI / Agent Host): todos deniegan con código 2 (único que bloquea de forma común)
def extraer_cascade(datos):
    if not isinstance(datos, dict):
        raise ValueError("la entrada no es un objeto JSON")
    ti = datos.get("tool_info")
    cwd = (ti.get("cwd") if isinstance(ti, dict) else None) or os.getcwd()
    if datos.get("agent_action_name") != "pre_run_command":
        return "", cwd                                       # otro evento: no lo juzga este hook
    comando = ti.get("command_line") if isinstance(ti, dict) else None
    if not isinstance(comando, str) or not comando.strip():
        raise ValueError("`pre_run_command` no trae `tool_info.command_line`")
    return comando, cwd


NOMBRES_SHELL_LOCAL = ("run_in_terminal", "runinterminal", "bash", "shell", "terminal", "execute", "exec", "run_terminal_command")


def extraer_copilot_local(datos):
    if not isinstance(datos, dict):
        raise ValueError("la entrada no es un objeto JSON")
    cwd = datos.get("cwd") or os.getcwd()
    ti = datos.get("tool_input")
    comando = ti.get("command") if isinstance(ti, dict) else None
    if isinstance(comando, str) and comando.strip():
        return comando, cwd                                  # `matcher` se ignora en Local: filtra el script (por la forma de la entrada)
    if str(datos.get("tool_name", "")).lower() in NOMBRES_SHELL_LOCAL:
        raise ValueError("la herramienta de shell no trae `tool_input.command`")
    return "", cwd


def extraer_copilot_cli(datos):
    if not isinstance(datos, dict):
        raise ValueError("la entrada no es un objeto JSON")
    cwd = datos.get("cwd") or os.getcwd()
    if datos.get("toolName") not in ("bash", "powershell"):
        return "", cwd
    args = datos.get("toolArgs")
    if isinstance(args, str):
        args = json.loads(args)
    comando = args.get("command") if isinstance(args, dict) else None
    if not isinstance(comando, str) or not comando.strip():
        raise ValueError("la herramienta de shell no trae `toolArgs.command`")
    return comando, cwd


def _deniega_con_2(decision, motivo):
    if decision == "ask":
        motivo = PREGUNTAR + motivo
    return (motivo or SIN_MOTIVO)


def salida_cascade(decision, motivo):
    if decision == "allow":
        return "", "", 0
    return "", _deniega_con_2(decision, motivo), 2


def salida_devin(decision, motivo):
    if decision == "allow":
        return "", "", 0
    m = _deniega_con_2(decision, motivo)
    return j({"decision": "block", "reason": m}), m, 2


def salida_copilot_local(decision, motivo):
    if decision == "allow":
        return "", "", 0
    m = _deniega_con_2(decision, motivo)
    return j({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": m}}), m, 2


def salida_copilot_cli(decision, motivo):
    if decision == "allow":
        return "", "", 0
    m = _deniega_con_2(decision, motivo)
    return j({"permissionDecision": "deny", "permissionDecisionReason": m}), m, 2


FORMATOS = {
    "opencode": {"extraer": extraer_plano, "salida": salida_opencode, "error": error_opencode, "estricto": False},
    "cursor": {"extraer": extraer_plano, "salida": salida_cursor, "error": error_cursor, "estricto": False},
    "codex": {"extraer": extractor_herramienta(("Bash", "exec_command"), ("CODEX_PROJECT_DIR",)),
              "salida": salida_codex, "error": error_codex, "estricto": True},
    "gemini": {"extraer": extractor_herramienta(("run_shell_command",), ("GEMINI_CWD", "GEMINI_PROJECT_DIR")),
               "salida": salida_gemini, "error": error_gemini, "estricto": True},
    "windsurf-cascade": {"extraer": extraer_cascade, "salida": salida_cascade, "error": lambda m: salida_cascade("deny", m), "estricto": True},
    "windsurf-devin": {"extraer": extractor_herramienta(("exec",), ("DEVIN_PROJECT_DIR",)), "salida": salida_devin,
                       "error": lambda m: salida_devin("deny", m), "estricto": True},
    "copilot-local": {"extraer": extraer_copilot_local, "salida": salida_copilot_local, "error": lambda m: salida_copilot_local("deny", m), "estricto": True},
    "copilot-cli": {"extraer": extraer_copilot_cli, "salida": salida_copilot_cli, "error": lambda m: salida_copilot_cli("deny", m), "estricto": True},
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--formato", choices=sorted(FORMATOS), default="cursor")
    f = FORMATOS[ap.parse_args(argv).formato]
    try:
        texto = sys.stdin.read()
        datos = json.loads(texto if f["estricto"] else (texto or "{}"))
        comando, cwd = f["extraer"](datos)
        decision, motivo = decidir(comando, cwd) if comando else ("allow", "")
        out, err, codigo = f["salida"](decision, motivo)
    except Exception as e:                                   # falla cerrado: nunca se deja pasar por un error
        out, err, codigo = f["error"](f"guardia de datos: no se pudo decidir ({e}); se bloquea por precaución")
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
'''

AVISO_LANZADOR = "guardia de datos: no se encontró python3 o el puente; se bloquea por precaución"
# Denegación estática del lanzador, por formato (solo los agentes que fallan abiertos la necesitan).
DENEGACION_LANZADOR = {
    "codex": f"echo '{AVISO_LANZADOR}' >&2\nexit 2",
    "gemini": ("printf '%s\\n' '{\"decision\":\"deny\",\"reason\":\"" + AVISO_LANZADOR + "\",\"systemMessage\":\"" + AVISO_LANZADOR + "\"}'\n"
               f"echo '{AVISO_LANZADOR}' >&2\nexit 0"),
    # Windsurf (ambos agentes) y Copilot (ambas superficies): el único bloqueo común es salir con 2 y el motivo en stderr
    "windsurf-cascade": f"echo '{AVISO_LANZADOR}' >&2\nexit 2",
    "windsurf-devin": f"echo '{AVISO_LANZADOR}' >&2\nexit 2",
    "copilot-local": f"echo '{AVISO_LANZADOR}' >&2\nexit 2",
    "copilot-cli": f"echo '{AVISO_LANZADOR}' >&2\nexit 2",
}

TEXTO_LANZADOR = '''#!/bin/sh
# __MARCA__
# Lanzador del hook de datos (formato __FORMATO__). Si falta python3 o el puente, deniega él mismo: el agente fallaría abierto.
aqui=${0%/*}
if [ "$aqui" = "$0" ]; then aqui=.; fi
if command -v python3 >/dev/null 2>&1 && [ -f "$aqui/__PUENTE__" ]; then
  exec python3 "$aqui/__PUENTE__" --formato __FORMATO__
fi
__DENEGAR__
'''


def texto_lanzador(formato):
    if formato not in DENEGACION_LANZADOR:
        raise ValueError(f"el formato «{formato}» no tiene denegación de lanzador definida")
    return (TEXTO_LANZADOR.replace("__MARCA__", fn.MARCA).replace("__FORMATO__", formato)
            .replace("__PUENTE__", PUENTE).replace("__DENEGAR__", DENEGACION_LANZADOR[formato]))


def cargar_generador(harness_raiz):
    ruta = Path(harness_raiz) / "instalador" / "generar-politicas.py"
    spec = importlib.util.spec_from_file_location("generar_politicas", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def con_marca(contenido, comentario="#"):
    if fn.es_generado(contenido):
        return contenido
    primera, _, resto = contenido.partition("\n")
    if primera.startswith("#!"):
        return f"{primera}\n{comentario} {fn.MARCA}\n{resto}"
    return f"{comentario} {fn.MARCA}\n{contenido}"


def archivos_de_hook(fuente, lanzador=None):
    """([(nombre, contenido, modo)], motivo). Sin archivos y con motivo si la política aún no permite generar el hook.

    `lanzador="<formato>"` agrega `lanzar.sh` para ese formato (agentes que fallan abiertos)."""
    gen = cargar_generador(fuente["harness_raiz"])
    try:
        gen.construir(gen.cargar(fuente["politica_ruta"]), fuente["politica_ruta"])        # valida sin escribir
        with tempfile.TemporaryDirectory(prefix="mh-guardia-") as tmp:
            salida = [(Path(r).name, con_marca(Path(r).read_text(encoding="utf-8")), 0o755)
                      for r in gen.generar(fuente["politica_ruta"], tmp)]
    except gen.ErrorPolitica as e:
        return [], f"la política aún no permite generar el hook de datos: {str(e).splitlines()[0].rstrip('.')}"
    except (OSError, KeyError) as e:
        return [], f"no se pudo generar el hook de datos: {e}"
    salida.append((PUENTE, TEXTO_PUENTE.replace("__MARCA__", fn.MARCA), 0o755))
    if lanzador:
        salida.append((LANZADOR, texto_lanzador(lanzador), 0o755))
    return salida, None
