#!/usr/bin/env python3
"""Marco de adaptadores de agente (R52-R57): detecta qué agentes hay, genera AGENTS.md y la configuración de cada uno.

Uso:
    python3 generar_agentes.py <instancia> [--agentes a,b | --detectar] [--aplicar] [--json]

- Sin `--aplicar` solo muestra el plan: no escribe nada.
- `--detectar` (por defecto si no se pasa `--agentes`): informa qué agentes hay rastro en este equipo y
  genera solo para esos; no asume ninguno. `--agentes a,b`: genera para los nombrados aunque no se detecten.
- Todo se escribe DENTRO de la instancia. Lo que sería global (en `~` o en carpetas de configuración del
  agente) nunca se escribe: se imprime el paso para la persona.
- Cada adaptador declara sus capacidades tomadas de `adaptadores-agente/MATRIZ.md` (con su fuente) y sus
  degradaciones (qué no soporta y con qué imposición alternativa). Nunca se promete lo que la matriz marca
  «no» o «no verificado».
- Solo biblioteca estándar. Sin red ni git.

Para agregar un agente: crear `adaptadores-agente/<agente>/adaptador.py` con una lista `ADAPTADORES = [Clase]`
(subclases de `Adaptador`); se descubre solo. También puede usarse `registrar(Clase)`.
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if __name__ == "__main__":                       # que los adaptadores que importan este módulo reciban ESTE objeto
    sys.modules.setdefault("generar_agentes", sys.modules["__main__"])
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))
import fuente_neutral as fn  # noqa: E402

RAIZ_HARNESS = AQUI.parents[1]
DIR_ADAPTADORES = AQUI.parent
CAPACIDADES = {1: "Instrucciones del proyecto", 2: "Reglas por ruta", 3: "Hooks que bloquean", 4: "Subagentes / paralelo",
               5: "Comandos propios", 6: "Skills", 7: "MCP", 8: "Memoria entre sesiones", 9: "Permisos / modos / sandbox",
               10: "No interactivo", 11: "Plugins"}
ESTADOS = {"S": "si", "P": "parcial", "N": "no_verificado", "NO": "no"}
CAP_HOOKS = 3
SIN_HOOKS_ALTERNATIVAS = [
    ("Que el agente no lea ni escriba datos que no debe", "rol de solo lectura en la base de datos (permisos del servidor, credenciales de producción fuera del alcance del agente)"),
    ("Que no se suba código a ramas protegidas ni se reescriba su historia", "protección de ramas en el alojamiento remoto (revisión obligatoria, sin push directo ni force-push)"),
    ("Que no se confirme código que viola el estándar", "hooks de git (pre-commit, pre-push, commit-msg) que corran el gate del harness; se pueden saltar con --no-verify, por eso no bastan solos"),
    ("Que ningún cambio llegue a la rama principal sin verificaciones", "integración continua obligatoria (estado requerido en la protección de ramas) con el mismo gate"),
    ("Que no se filtren secretos", "escaneo de secretos en pre-commit y en integración continua"),
]
FUENTE_SIN_HOOKS = "MATRIZ.md, «Qué se pierde sin hooks»"


class ErrorAgente(Exception):
    """Petición inválida (agente desconocido, instancia inutilizable)."""


# ----------------------------------------------------------------------------- sistema inyectable
class Sistema:
    """Lo que el equipo ofrece: comandos en PATH y rutas. Inyectable para pruebas."""

    def __init__(self, home=None, path=None):
        self.home = Path(home or os.path.expanduser("~"))
        self.path = path

    def existe_comando(self, nombre):
        return shutil.which(nombre, path=self.path) is not None

    def existe_ruta(self, rel_a_home):
        return (self.home / rel_a_home).exists()


class SistemaSimulado(Sistema):
    def __init__(self, comandos=(), rutas=(), home="/nadie"):
        self.home = Path(home)
        self._c, self._r = set(comandos), set(rutas)

    def existe_comando(self, nombre):
        return nombre in self._c

    def existe_ruta(self, rel_a_home):
        return rel_a_home in self._r


# ----------------------------------------------------------------------------- matriz
class Matriz:
    """Lee el «Resumen visual» de MATRIZ.md: estado por agente y capacidad. No inventa nada."""

    def __init__(self, ruta=None):
        self.ruta = Path(ruta) if ruta else DIR_ADAPTADORES / "MATRIZ.md"
        self.estados = {}          # codigo -> {cap: estado}
        self.revisado = self.vence_dias = None
        self._leer()

    def _leer(self):
        try:
            texto = self.ruta.read_text(encoding="utf-8")
        except OSError:
            return
        m = re.search(r"revisado:\s*(\d{4}-\d{2}-\d{2})\s*[·|]\s*vence:\s*(\d+)d", texto)
        if m:
            self.revisado, self.vence_dias = dt.date.fromisoformat(m.group(1)), int(m.group(2))
        sec = re.search(r"^## Resumen visual.*?(?=^## )", texto, re.S | re.M)
        if not sec:
            return
        codigos = None
        for linea in sec.group(0).splitlines():
            if not linea.startswith("|") or set(linea) <= set("|- "):
                continue
            celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
            if celdas[0].lower().startswith("capacidad"):
                codigos = celdas[1:]
                for c in codigos:
                    self.estados.setdefault(c, {})
            elif codigos:
                m2 = re.match(r"(\d+)\s", celdas[0])
                if m2:
                    for c, v in zip(codigos, celdas[1:]):
                        self.estados[c][int(m2.group(1))] = ESTADOS.get(v.upper(), "no_verificado")

    def aviso_vigencia(self, hoy=None):
        if not self.revisado:
            return "MATRIZ.md sin cabecera de vigencia legible: revisarla antes de confiar en las capacidades."
        hoy = hoy or dt.date.today()
        if hoy > self.revisado + dt.timedelta(days=self.vence_dias):
            return f"MATRIZ.md está vencida (revisada {self.revisado}, vigencia {self.vence_dias} días): releer la documentación oficial antes de regenerar adaptadores."
        return None

    def capacidades(self, codigo):
        est = self.estados.get(codigo, {})
        return {CAPACIDADES[n]: {"estado": est.get(n, "no_verificado"),
                                 "fuente": f"MATRIZ.md, «Resumen visual», columna {codigo}; detalle en la sección {n}"}
                for n in CAPACIDADES}


# ----------------------------------------------------------------------------- contrato del adaptador
class Adaptador:
    """Contrato: nombre, detectar(sistema), capacidades(), generar(fuente, destino, aplicar), degradaciones()."""
    nombre = ""
    codigo_matriz = ""
    comandos = ()          # comandos que delatan al agente en PATH
    carpetas_home = ()     # rutas relativas a ~ que delatan al agente (solo se COMPRUEBA que existan)
    pasos_globales = ()    # pasos para la persona (lo que sería global)

    def __init__(self, matriz=None):
        self.matriz = matriz or Matriz()
        self.avisos, self.pasos = [], []
        self.control_hook_estado, self.control_hook_motivo = None, None

    def detectar(self, sistema):
        rastros = [f"comando `{c}` en PATH" for c in self.comandos if sistema.existe_comando(c)]
        rastros += [f"carpeta `~/{r}`" for r in self.carpetas_home if sistema.existe_ruta(r)]
        return {"detectado": bool(rastros), "rastros": rastros}

    def capacidades(self):
        return self.matriz.capacidades(self.codigo_matriz)

    def estado_hooks(self):
        return self.capacidades()["Hooks que bloquean"]["estado"]

    def control_por_hook(self):
        """R55: disponible / degradado / no_disponible. Solo promete lo que la matriz marca «sí»."""
        if self.control_hook_estado:
            return self.control_hook_estado, self.control_hook_motivo
        e = self.estado_hooks()
        if e == "si":
            return "degradado", "el agente soporta hooks que bloquean (MATRIZ.md §3) pero este adaptador no los genera"
        if e == "parcial":
            return "degradado", "la matriz marca los hooks como parcial"
        return "no_disponible", f"la matriz marca los hooks como «{e}»: no se promete control por hook"

    def degradaciones(self):
        """[{que_se_pierde, imposicion_alternativa, fuente}]. No vacía si el agente no tiene hooks confirmados."""
        out = []
        e = self.estado_hooks()
        if e != "si":
            out += [{"que_se_pierde": q, "imposicion_alternativa": a, "fuente": FUENTE_SIN_HOOKS} for q, a in SIN_HOOKS_ALTERNATIVAS]
        return out

    def generar(self, fuente, destino, aplicar=False):
        """Archivos propios del agente (ruta relativa, acción). Solo con `aplicar` escribe, y solo dentro de `destino`."""
        self.avisos, self.pasos = [], list(self.pasos_globales)
        return []


class AdaptadorMinimo(Adaptador):
    """Agente sin archivos propios que generar: solo lee AGENTS.md (o el paso lo indica)."""


class Aider(AdaptadorMinimo):
    nombre, codigo_matriz = "aider", "AI"
    comandos, carpetas_home = ("aider",), (".aider.conf.yml",)
    pasos_globales = ("Aider no descubre archivos de instrucciones solo: arráncalo con `aider --read AGENTS.md` "
                      "(MATRIZ.md §1: cargar con `--read`; que lea AGENTS.md por sí mismo: no verificado). "
                      "El adaptador no escribe `.aider.conf.yml`.",)


class Cline(AdaptadorMinimo):
    nombre, codigo_matriz = "cline", "CL"
    comandos, carpetas_home = (), ("Documents/Cline",)
    pasos_globales = ("Cline detecta `AGENTS.md` en el proyecto (MATRIZ.md §1); no hay nada más que escribir en la instancia.",)


REGISTRO = {}


def registrar(clase):
    if not getattr(clase, "nombre", ""):
        raise ValueError("el adaptador debe tener `nombre`")
    REGISTRO[clase.nombre] = clase
    return clase


def cargar_adaptadores(dir_adaptadores=None):
    """Registra los incluidos y descubre `<agente>/adaptador.py` (lista ADAPTADORES)."""
    for c in (Aider, Cline):
        registrar(c)
    base = Path(dir_adaptadores or DIR_ADAPTADORES)
    for f in sorted(base.glob("*/adaptador.py")):
        spec = importlib.util.spec_from_file_location("adaptador_" + f.parent.name.replace("-", "_"), f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for c in getattr(mod, "ADAPTADORES", []):
            registrar(c)
    return REGISTRO


def agentes_de_la_matriz(matriz):
    return sorted(matriz.estados)


# ----------------------------------------------------------------------------- plan
def planificar(instancia, agentes=None, sistema=None, aplicar=False, harness_raiz=None, matriz=None, hoy=None):
    """Devuelve el informe (dict). `agentes=None` => detectar y generar solo para los detectados."""
    cargar_adaptadores()
    sistema = sistema or Sistema()
    matriz = matriz or Matriz(Path(harness_raiz or RAIZ_HARNESS) / "adaptadores-agente" / "MATRIZ.md")
    try:
        fuente = fn.construir(instancia, harness_raiz)
    except fn.ErrorInstancia as e:
        raise ErrorAgente(str(e))
    if agentes:
        for a in agentes:
            if a not in REGISTRO:
                raise ErrorAgente(f"Agente desconocido: «{a}». Con adaptador: {', '.join(sorted(REGISTRO))}. "
                                  "Para agregar uno, crea adaptadores-agente/<agente>/adaptador.py con ADAPTADORES = [Clase].")
    instancias = {n: c(matriz) for n, c in REGISTRO.items()}
    deteccion = {n: ad.detectar(sistema) for n, ad in instancias.items()}
    elegidos = list(agentes) if agentes else [n for n in sorted(instancias) if deteccion[n]["detectado"]]

    try:
        it = fn.plan_agents_md(fuente, instancia, harness_raiz)
    except (fn.ErrorInstancia, OSError) as e:
        raise ErrorAgente(f"No se pudo preparar AGENTS.md: {e}")
    nucleo = fn.escribir_plan(instancia, [it], aplicar)

    informe_agentes = {}
    for n in sorted(instancias):
        ad = instancias[n]
        entrada = {"nombre": n, "codigo_matriz": ad.codigo_matriz, "detectado": deteccion[n]["detectado"],
                   "rastros": deteccion[n]["rastros"], "seleccionado": n in elegidos,
                   "capacidades": ad.capacidades()}
        if n in elegidos:
            archivos = ad.generar(fuente, instancia, aplicar=aplicar)
            estado, motivo = ad.control_por_hook()
            entrada.update({"archivos": archivos, "pasos_para_la_persona": ad.pasos, "avisos": ad.avisos,
                            "control_por_hook": estado, "control_por_hook_motivo": motivo,
                            "degradaciones": ad.degradaciones()})
        informe_agentes[n] = entrada
    avisos_generales = [x for x in [matriz.aviso_vigencia(hoy)] if x]
    if not matriz.estados:
        avisos_generales.append("No se pudo leer el «Resumen visual» de MATRIZ.md: todas las capacidades figuran «no verificado».")
    return {"instancia": str(instancia), "aplicado": bool(aplicar), "modo": "agentes indicados" if agentes else "detección",
            "nucleo": nucleo, "agentes": informe_agentes, "seleccionados": elegidos,
            "avisos": avisos_generales + [i["aviso"] for i in nucleo if i.get("aviso")],
            "sin_adaptador_en_la_matriz": [c for c in agentes_de_la_matriz(matriz) if c not in {a.codigo_matriz for a in instancias.values()}]}


def texto_informe(inf):
    L = [f"Instancia: {inf['instancia']}", f"Modo: {inf['modo']} · {'APLICADO' if inf['aplicado'] else 'PLAN (no se escribió nada)'}", ""]
    L.append("Núcleo (independiente del agente):")
    for a in inf["nucleo"]:
        L.append(f"  {a['accion']:<11} {a['ruta']}")
    L.append("")
    L.append("Agentes (detectados = hay rastro en este equipo; no se asume ninguno):")
    for n, a in inf["agentes"].items():
        det = "detectado (" + "; ".join(a["rastros"]) + ")" if a["detectado"] else "sin rastro"
        L.append(f"- {n} [{a['codigo_matriz']}]: {det}{' · seleccionado' if a['seleccionado'] else ''}")
        if a["seleccionado"]:
            L.append(f"    control por hook: {a['control_por_hook'].replace('_', ' ')} ({a['control_por_hook_motivo']})")
            for f in a["archivos"]:
                L.append(f"    {f['accion']:<11} {f['ruta']}")
            for p in a["pasos_para_la_persona"]:
                L.append(f"    PASO PARA LA PERSONA: {p}")
            for x in a["avisos"]:
                L.append(f"    AVISO: {x}")
            for d in a["degradaciones"]:
                L.append(f"    DEGRADADO: {d['que_se_pierde']} -> {d['imposicion_alternativa']}")
    if inf["sin_adaptador_en_la_matriz"]:
        L += ["", "En la matriz sin adaptador todavía: " + ", ".join(inf["sin_adaptador_en_la_matriz"])]
    for x in inf["avisos"]:
        L.append(f"AVISO: {x}")
    return "\n".join(L)


def main(argv=None, sistema=None, salida=None):
    ap = argparse.ArgumentParser(description="Genera AGENTS.md y la configuración de cada agente dentro de una instancia.")
    ap.add_argument("instancia")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--agentes", help="lista separada por comas")
    g.add_argument("--detectar", action="store_true", help="detecta y genera solo para los detectados (por defecto)")
    ap.add_argument("--aplicar", action="store_true", help="escribe; sin esto solo muestra el plan")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--harness", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    out = salida or sys.stdout
    lista = [x.strip() for x in a.agentes.split(",") if x.strip()] if a.agentes else None
    try:
        inf = planificar(a.instancia, lista, sistema, a.aplicar, a.harness)
    except ErrorAgente as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(json.dumps(inf, ensure_ascii=False, indent=2) if a.json else texto_informe(inf), file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
