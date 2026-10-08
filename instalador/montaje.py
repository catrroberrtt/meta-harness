#!/usr/bin/env python3
"""Montaje completo del entorno de un proyecto sobre una instancia ya creada por `init`, `adopt` o `migrar`.

Uso:
    python3 instalador/montaje.py <instancia> [--agentes a,b | --detectar] [--aplicar] [--json] [--si]
                                  [--proyecto <carpeta>]

Encadena, con UN plan y confirmaciones agrupadas, las piezas que ya existen por separado:
  1. lee la instancia (politicas.toml, convenciones.toml, harness.lock, .harness/estado.json);
  2. detecta los agentes de IA del equipo (`generar_agentes`, sin asumir ninguno) y pregunta cuáles configurar;
  3. genera `AGENTS.md` y lo que cada adaptador confirma (skills, comandos, permisos, MCP solo con
     `registrar = "permitida"`, hooks de datos si la política los permite);
  4. comprueba la garantía real independiente del agente (spec §22) y lista lo que FALTA como pasos para la persona;
  5. verifica: gate declarado, frescura de documentos, idempotencia de lo generado y que nada salió de la instancia;
  6. escribe `.harness/montaje.md` (sin fechas ni rutas absolutas) y actualiza `.harness/estado.json`.

Reglas:
- Sin `--aplicar` solo muestra el plan: no escribe nada. Con `--aplicar` escribe SOLO dentro de la instancia.
- Lo global o pesado (instalar herramientas, registrar un MCP en el agente, crear hooks de git o protección de ramas,
  tocar la integración continua del proyecto, editar la configuración global del agente) se IMPRIME como paso para
  la persona y nunca se ejecuta. Sin red, sin git, sin instalar nada.
- Reanudable e idempotente: la segunda corrida sobre lo mismo no cambia ningún archivo.
- `--si` salta solo las preguntas de bajo riesgo (qué agentes configurar y confirmar la escritura dentro de la instancia).

Como función (para el asistente): `montar(instancia, agentes=None, aplicar=False, preguntar=input, salida=print)`
devuelve un diccionario con `hecho`, `degradado` y `pendiente` (y `plan`, `agentes`, `verificacion`, `ok`).

Salida: 0 hecho o solo plan · 1 una verificación falló (idempotencia o escritura fuera de la instancia) · 2 instancia
inválida o petición inválida. Solo biblioteca estándar.
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import sys
import tomllib
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ_HARNESS = AQUI.parent
NUCLEO = RAIZ_HARNESS / "adaptadores-agente" / "nucleo"
if str(NUCLEO) not in sys.path:
    sys.path.insert(0, str(NUCLEO))
import fuente_neutral as fn  # noqa: E402
import generar_agentes as ga  # noqa: E402

INFORME_REL = ".harness/montaje.md"
ESTADO_REL = ".harness/estado.json"
CMD = "python3 <harness>/instalador/montaje.py <instancia>"
FECHA = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
RUTA_ABS = re.compile(r"(?<![\w.<>~$-])/(?:home|tmp|Users|var|root|opt|mnt|private|srv)/[^\s`'\")>,;]*")
ARCHIVOS_CI = (".gitlab-ci.yml", "Jenkinsfile", ".circleci/config.yml", "azure-pipelines.yml", "bitbucket-pipelines.yml",
               ".travis.yml", ".drone.yml")
AFIRMATIVAS = {"s", "si", "sí", "y", "yes"}


class ErrorMontaje(Exception):
    """La instancia no es válida o la petición no se puede atender (exit 2)."""


# ----------------------------------------------------------------------------- utilidades
def _escribir_si_cambia(instancia, rel, contenido):
    destino = fn._dentro(instancia, rel)
    if destino.exists() and destino.read_text(encoding="utf-8") == contenido:
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(contenido, encoding="utf-8")
    return True


def _limpiador(instancia, harness_raiz, proyecto):
    """Función que quita de un texto fechas y rutas absolutas (el informe viaja con el repositorio)."""
    reemplazos = [(str(Path(instancia)), "<instancia>"), (str(Path(os.path.realpath(instancia))), "<instancia>"),
                  (str(Path(harness_raiz)), "<harness>"), (str(Path(os.path.realpath(harness_raiz))), "<harness>")]
    if proyecto:
        reemplazos.append((str(proyecto), "<proyecto>"))
    reemplazos.append((os.path.expanduser("~"), "~"))
    reemplazos.sort(key=lambda x: -len(x[0]))

    def limpiar(texto):
        t = str(texto)
        for a, b in reemplazos:
            if len(a) > 1:
                t = t.replace(a, b)
        t = FECHA.sub("<fecha>", t)
        return RUTA_ABS.sub("<ruta>", t)
    return limpiar


def _preguntar(preguntar, texto):
    try:
        return (preguntar(texto) or "").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def _toml(ruta):
    try:
        return tomllib.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None


# ----------------------------------------------------------------------------- 1. leer la instancia
def leer_instancia(instancia):
    inst = Path(instancia)
    uso = "Crea o adopta la instancia primero: `instalador/instalar.sh init <instancia> --aplicar` (o adopt / migrar)."
    if not inst.is_dir():
        raise ErrorMontaje(f"La instancia no existe o no es una carpeta. {uso}")
    faltan = [n for n in ("politicas.toml", "convenciones.toml", "harness.lock", ESTADO_REL) if not (inst / n).is_file()]
    if faltan:
        raise ErrorMontaje("La carpeta no es una instancia instalada: falta " + ", ".join(faltan) + ". " + uso)
    pol, conv = _toml(inst / "politicas.toml"), _toml(inst / "convenciones.toml")
    if pol is None or conv is None:
        raise ErrorMontaje("politicas.toml o convenciones.toml no son TOML válido: corrígelos y repite.")
    try:
        estado = json.loads((inst / ESTADO_REL).read_text(encoding="utf-8"))
        if not isinstance(estado, dict):
            raise ValueError
    except ValueError:
        raise ErrorMontaje(f"{ESTADO_REL} es ilegible: revísalo o corre `instalar.sh update` antes del montaje.")
    lock = _toml(inst / "harness.lock") or {}
    return {"politica": pol, "convenciones": conv, "estado": estado, "version": lock.get("version")}


# ----------------------------------------------------------------------------- 4. garantía independiente del agente
def _proyecto_de(instancia, proyecto):
    """Carpeta del proyecto: la indicada, o el primer ancestro de la instancia con `.git` (se mira, no se ejecuta git)."""
    if proyecto:
        return Path(proyecto)
    for p in Path(os.path.realpath(instancia)).parents:
        if (p / ".git").exists():
            return p
    return None


def garantia(inst, proyecto, gate_cmd):
    """(hecho, degradado, pendiente) de las capas que NO dependen del agente. Solo lectura."""
    pol = inst["politica"]
    datos, git = pol.get("datos") or {}, pol.get("git") or {}
    hecho, degradado, pendiente = [], [], []
    ambientes = datos.get("ambientes") or []

    if ambientes:
        hecho.append(f"Ambientes de datos declarados en la política: {len(ambientes)}.")
    else:
        degradado.append({"que": "Ambientes de datos", "motivo": "la política no declara ninguno (`[[datos.ambientes]]`); no se inventa ninguno"})
        pendiente.append({"que": "Declarar los ambientes de datos en `politicas.toml` (esquema: `politicas/ESQUEMA.md` §2)",
                          "comando": f"editar `politicas.toml` y repetir `{CMD} --aplicar`"})

    rol = datos.get("rol_solo_lectura") or any(a.get("rol_lectura") for a in ambientes if isinstance(a, dict))
    if rol:
        hecho.append("Rol de solo lectura para los datos declarado en la política (que exista en el servidor no se verifica sin acceso).")
    else:
        pendiente.append({"que": "Rol de solo lectura en la base de datos para el agente (la garantía real no depende del agente)",
                          "comando": "crearlo en el servidor de datos (lo hace la persona) y declararlo en `politicas.toml` con `datos.rol_solo_lectura = \"<nombre-del-rol>\"`"})

    gate_txt = gate_cmd or "<comando del gate>"
    if proyecto is None:
        pendiente.append({"que": "Comprobar hooks de git, integración continua y protección de ramas: no se indicó la carpeta del proyecto",
                          "comando": f"{CMD} --proyecto <carpeta-del-proyecto>"})
    else:
        hooks_git = [h for h in ("pre-commit", "pre-push", "commit-msg")
                     if (proyecto / ".git" / "hooks" / h).is_file() or (proyecto / ".githooks" / h).is_file()
                     or (proyecto / ".husky" / h).is_file()]
        if hooks_git:
            hecho.append("Hooks de git presentes en el proyecto: " + ", ".join(hooks_git) + " (que corran el gate no se verifica).")
        else:
            pendiente.append({"que": "Hooks de git que corran el gate (pre-commit / pre-push); se pueden saltar con `--no-verify`, por eso no bastan solos",
                              "comando": f"mkdir -p .githooks && printf '#!/bin/sh\\n{gate_txt}\\n' > .githooks/pre-push && chmod +x .githooks/pre-push && git config core.hooksPath .githooks  (en el proyecto, lo corre la persona)"})
        ci = [a for a in ARCHIVOS_CI if (proyecto / a).is_file()]
        wf = proyecto / ".github" / "workflows"
        if wf.is_dir():
            ci += [f".github/workflows/{f.name}" for f in sorted(wf.iterdir()) if f.suffix in (".yml", ".yaml")]
        if ci:
            hecho.append("Integración continua presente en el proyecto (no se modifica).")
            corre_gate = bool(gate_cmd) and any(gate_cmd in (proyecto / c).read_text(encoding="utf-8", errors="replace") for c in ci)
            if gate_cmd and not corre_gate:
                pendiente.append({"que": "Que la integración continua ejecute el mismo gate del harness (no aparece su comando en los flujos)",
                                  "comando": f"agregar un paso que ejecute `{gate_cmd}` al flujo de integración continua (lo hace la persona; el montaje no toca el CI)"})
        else:
            pendiente.append({"que": "Integración continua obligatoria con el mismo gate",
                              "comando": f"crear el flujo de integración continua del proyecto con un paso `{gate_txt}` (lo hace la persona)"})

    ramas = git.get("ramas_protegidas") or []
    if ramas:
        hecho.append(f"Ramas protegidas declaradas en la política: {len(ramas)}.")
    else:
        degradado.append({"que": "Ramas protegidas", "motivo": "la política no declara `git.ramas_protegidas`"})
    pendiente.append({"que": "Protección de ramas en el alojamiento remoto (revisión obligatoria, sin push directo ni force-push, integración continua como estado requerido)"
                             + ("" if ramas else "; antes declara las ramas en `git.ramas_protegidas`"),
                      "comando": "activarla en la configuración del repositorio remoto (lo hace la persona; el montaje no usa la red)"})
    return hecho, degradado, pendiente


# ----------------------------------------------------------------------------- acceso a datos (requisito de la persona)
REQUISITO = "requisito de la persona"
PASO = "paso de la persona"
BLOQUE_DATOS = [
    "La base de datos es la fuente de evidencia más fuerte del sistema y el montaje NO la instala ni la levanta: cada proyecto accede a la suya de forma distinta.",
    "Sin tu acceso, el entorno trabaja en modo degradado y no afirma nada sobre datos.",
    "Para darlo: declara los ambientes en `politicas.toml`, pon tu acceso personal en `acceso.local.toml` (no se versiona) y corre "
    "`python3 <harness>/instalador/preflight-accesos.py --politica politicas.toml --acceso acceso.local.toml` para comprobarlo.",
]


def acceso_datos(instancia, inst):
    """Estado del acceso a datos SIN conectar a nada: solo lee qué métodos declaró la persona (nunca valores de secretos)."""
    ambientes = [a.get("nombre") for a in (inst["politica"].get("datos") or {}).get("ambientes") or [] if isinstance(a, dict) and a.get("nombre")]
    acc = _toml(Path(instancia) / "acceso.local.toml") if (Path(instancia) / "acceso.local.toml").is_file() else None
    if not ambientes:
        return {"estado": "sin comprobar", "detalle": "la política no declara ambientes: no hay nada que comprobar", "ambientes": {}}
    if acc is None:
        return {"estado": "sin comprobar", "detalle": "falta `acceso.local.toml` (o no es TOML válido): el preflight no puede evaluarse", "ambientes": {}}
    datos = acc.get("datos") if isinstance(acc.get("datos"), dict) else {}
    est = {}
    for n in ambientes:
        m = (datos.get(n) or {}).get("metodo") if isinstance(datos.get(n), dict) else None
        est[n] = f"método declarado: {m}" if m and m != "sin_acceso" else ("sin acceso declarado" if m else "sin declarar")
    ok = all(v.startswith("método") for v in est.values())
    return {"estado": "declarado" if ok else "incompleto",
            "detalle": "veredicto estático (solo lo declarado; la conexión real la comprueba el preflight, que corres tú)", "ambientes": est}


# ----------------------------------------------------------------------------- 5. verificación
def _frescura(instancia, harness_raiz):
    f = Path(harness_raiz) / "herramientas" / "harness-frescura.py"
    try:
        spec = importlib.util.spec_from_file_location("harness_frescura", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        r = mod.analizar(Path(instancia), dt.date.today())
        return len(r["vencidos"]), len(r["por_vencer"])
    except Exception:                      # herramienta ausente o rota: se informa, no se inventa
        return None, None


def _foto_vecinos(instancia):
    """Foto superficial de la carpeta que contiene a la instancia (sin ella): detecta escrituras fuera."""
    base = Path(os.path.realpath(instancia))
    padre, foto = base.parent, {}
    try:
        for e in padre.iterdir():
            if e == base:
                continue
            try:
                s = e.lstat()
                foto[e.name] = (s.st_mtime_ns, s.st_size)
            except OSError:
                pass
    except OSError:
        pass
    return foto


def _acciones_no_iguales(informe):
    malas = [a["ruta"] for a in informe["nucleo"] if a["accion"] != "igual"]
    for ag in informe["agentes"].values():
        malas += [f["ruta"] for f in ag.get("archivos", []) if f["accion"] != "igual"]
    return malas


# ----------------------------------------------------------------------------- informe
def informe_md(res, limpiar):
    L = ["# Montaje del entorno", "", f"<!-- {fn.MARCA} -->", "",
         "Informe del último montaje de esta instancia (`instalador/montaje.py`). Sin fechas ni rutas absolutas: regenerarlo sobre lo mismo no lo cambia.", "",
         f"Estado: **{'completo' if not [p for p in res['pendiente'] if p.get('tipo') != REQUISITO] and not res['degradado'] else 'con degradados o pendientes'}**"
         f" · agentes configurados: {', '.join(res['agentes_configurados']) or 'ninguno'}", "", "## Hecho", ""]
    L += [f"- {limpiar(x)}" for x in res["hecho"]] or ["- Nada."]
    L += ["", "## Degradado y por qué", ""]
    L += [f"- {limpiar(d['que'])}: {limpiar(d['motivo'])}" for d in res["degradado"]] or ["- Nada degradado."]
    L += ["", "## Acceso a datos (lo das tú)", ""] + [limpiar(x) + "\n" for x in BLOQUE_DATOS]
    ad = res["acceso_datos"]
    L += [f"Preflight de accesos: {ad['estado']} · {limpiar(ad['detalle'])}"]
    L += [f"- Ambiente «{limpiar(n)}»: {v}" for n, v in ad["ambientes"].items()]
    L += ["", "## Pendiente de la persona", "",
          "El montaje nunca ejecuta esto: es global, pesado o está fuera de la instancia. Cada punto trae su comando o paso exacto. "
          f"Los marcados «{REQUISITO}» no son un fallo del montaje.", ""]
    for i, p in enumerate(res["pendiente"], 1):
        L += [f"{i}. [{p['tipo']}] {limpiar(p['que'])}", f"   - Comando o paso: {limpiar(p['comando'])}"]
    return "\n".join(L).rstrip("\n") + "\n"


def _estado_nuevo(estado, res):
    nuevo = dict(estado)
    nuevo["montaje"] = {"agentes": sorted(res["agentes_configurados"]), "degradados": len(res["degradado"]),
                        "pendientes": len([p for p in res["pendiente"] if p.get("tipo") != REQUISITO]), "idempotente": bool(res["verificacion"].get("idempotente")),
                        "informe": INFORME_REL}
    return json.dumps(nuevo, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# ----------------------------------------------------------------------------- orquestación
def montar(instancia, agentes=None, aplicar=False, preguntar=input, salida=print, sistema=None, si=False,
           proyecto=None, harness_raiz=None):
    """Monta el entorno de la instancia. Devuelve {hecho, degradado, pendiente, ...}. Lanza ErrorMontaje si no hay instancia válida."""
    harness_raiz = Path(harness_raiz or RAIZ_HARNESS)
    instancia = Path(instancia)
    inst = leer_instancia(instancia)
    sistema = sistema or ga.Sistema()
    proyecto_dir = _proyecto_de(instancia, proyecto)
    limpiar = _limpiador(instancia, harness_raiz, proyecto_dir)
    ga.cargar_adaptadores()

    # 2. detectar y elegir agentes
    matriz = ga.Matriz(harness_raiz / "adaptadores-agente" / "MATRIZ.md")
    detectados = sorted(n for n, c in ga.REGISTRO.items() if c(matriz).detectar(sistema)["detectado"])
    degradado, pendiente, hecho = [], [], []
    if agentes:
        elegidos = list(agentes)
        desconocidos = [a for a in elegidos if a not in ga.REGISTRO]
        if desconocidos:
            raise ErrorMontaje(f"Agente desconocido: «{desconocidos[0]}». Con adaptador: {', '.join(sorted(ga.REGISTRO))}.")
    else:
        elegidos = list(detectados)
        if aplicar and not si and detectados:
            r = _preguntar(preguntar, f"Agentes detectados en este equipo: {', '.join(detectados)}. ¿Cuáles configuro? "
                                      "[Enter = todos · «ninguno» · lista separada por comas] ")
            if r.lower() in ("ninguno", "ninguna", "none"):
                elegidos = []
            elif r:
                pedidos = [x.strip() for x in r.split(",") if x.strip()]
                malos = [x for x in pedidos if x not in ga.REGISTRO]
                if malos:
                    raise ErrorMontaje(f"Agente desconocido: «{malos[0]}». Con adaptador: {', '.join(sorted(ga.REGISTRO))}.")
                elegidos = pedidos
    if not elegidos:
        degradado.append({"que": "Agentes de IA", "motivo": "ninguno elegido" + (" ni detectado en este equipo" if not detectados else "")
                          + ": solo se genera `AGENTS.md`, que varios agentes ya leen"})
        pendiente.append({"que": "Configurar un agente cuando exista uno en el equipo",
                          "comando": f"{CMD} --agentes <nombre> --aplicar  (nombres con adaptador: {', '.join(sorted(ga.REGISTRO))})"})

    # 3. plan de lo generado (sin escribir)
    sistema_plan = sistema if elegidos else ga.SistemaSimulado()
    try:
        plan = ga.planificar(instancia, elegidos or None, sistema_plan, False, harness_raiz, matriz)
    except ga.ErrorAgente as e:
        raise ErrorMontaje(str(e))

    def resumen(informe):
        filas = [("AGENTS.md", a["ruta"], a["accion"]) for a in informe["nucleo"]]
        for n in elegidos:
            filas += [(n, f["ruta"], f["accion"]) for f in informe["agentes"][n].get("archivos", [])]
        return filas

    # 4. garantía independiente del agente + piso
    gate_cmd = (fn.construir(instancia, harness_raiz)["gate"] or {}).get("comando")
    h4, d4, p4 = garantia(inst, proyecto_dir, gate_cmd)
    # 5. gate
    if gate_cmd:
        h5 = [f"Gate declarado en `convenciones.toml` (`gate.comando`): `{gate_cmd}` (el montaje no lo ejecuta)."]
    else:
        h5 = []
        degradado.append({"que": "Gate de calidad", "motivo": "`gate.comando` está «por definir» en `convenciones.toml`; AGENTS.md pide a la persona declararlo"})
        pendiente.append({"que": "Declarar el comando del gate", "comando": "editar `convenciones.toml` y poner `gate.comando = \"<comando>\"`, luego repetir "
                                                                            f"`{CMD} --aplicar`"})

    # hooks de datos y pasos por agente (según lo que cada adaptador confirma)
    for n in elegidos:
        a = plan["agentes"][n]
        if not a["detectado"]:
            degradado.append({"que": f"Agente «{n}»", "motivo": "no se detectó en este equipo: se generó igual porque se pidió, sin poder probarlo aquí"})
        if a["control_por_hook"] != "disponible":
            degradado.append({"que": f"Agente «{n}»: control por hook {a['control_por_hook'].replace('_', ' ')}", "motivo": a["control_por_hook_motivo"]})
            if not (inst["politica"].get("datos") or {}).get("ambientes"):
                pass                                    # la causa raíz ya figura en la garantía (ambientes)
        for av in a["avisos"]:
            degradado.append({"que": f"Agente «{n}»", "motivo": av})
        for paso in a["pasos_para_la_persona"]:
            pendiente.append({"que": f"Agente «{n}»: paso global o que requiere decisión de la persona", "comando": paso})
    for av in plan["avisos"]:
        degradado.append({"que": "Aviso del marco de adaptadores", "motivo": av})
    degradado += d4
    pendiente += p4

    # piso (herramientas pesadas que el montaje nunca instala)
    piso = inst["estado"].get("piso") or []
    sin_indexar = True
    try:
        for fila in (instancia / ".harness" / "piso.md").read_text(encoding="utf-8").splitlines():
            if fila.startswith("| Indexacion") and "| instalado |" in fila:
                sin_indexar = False
    except OSError:
        pass
    del piso
    if sin_indexar:
        pendiente.append({"que": "Indexar el código y mantener el índice al día (buscador de archivos y de símbolos)",
                          "comando": "instala la herramienta que elija el equipo siguiendo su documentación oficial (el montaje no instala herramientas ni usa la red)"})

    filas = resumen(plan)
    res = {"instancia": "<instancia>", "aplicado": False, "agentes_detectados": detectados, "agentes_configurados": list(elegidos),
           "plan": [{"origen": o, "ruta": r, "accion": ac} for o, r, ac in filas], "hecho": h4 + h5, "degradado": degradado,
           "pendiente": pendiente, "verificacion": {}, "ok": True, "acceso_datos": acceso_datos(instancia, inst)}
    for p in res["pendiente"]:
        p.setdefault("tipo", PASO)
    res["pendiente"].insert(0, {"tipo": REQUISITO, "que": "Acceso a los datos del proyecto (la base no se instala ni se levanta en el montaje)",
                                "comando": "declarar ambientes en `politicas.toml`, tu acceso en `acceso.local.toml` y correr "
                                           "`python3 <harness>/instalador/preflight-accesos.py --politica politicas.toml --acceso acceso.local.toml`"})

    # 6. mostrar y, si procede, aplicar
    salida(f"Montaje de la instancia · {'APLICAR' if aplicar else 'PLAN (no se escribe nada)'}")
    salida(f"Agentes detectados: {', '.join(detectados) or 'ninguno'} · a configurar: {', '.join(elegidos) or 'ninguno (solo AGENTS.md)'}")
    for o, r, ac in filas:
        salida(f"  {ac:<11} {r}  [{o}]")
    salida(f"  {'escribir' if aplicar else 'escribiría'} además {INFORME_REL} y la clave `montaje` de {ESTADO_REL}")
    if not aplicar:
        _cierre(res, salida, limpiar, plan_solo=True)
        return res
    if not si:
        r = _preguntar(preguntar, "¿Aplico este plan? Escribe solo dentro de la instancia. [s/N] ")
        if r.lower() not in AFIRMATIVAS:
            res["pendiente"].insert(0, {"que": "Confirmar y aplicar el plan", "comando": f"{CMD} --aplicar"})
            res["degradado"].insert(0, {"que": "Montaje", "motivo": "no se confirmó el plan: no se escribió nada"})
            salida("Sin confirmación: no se escribió nada.")
            _cierre(res, salida, limpiar, plan_solo=True)
            return res

    antes = _foto_vecinos(instancia)
    try:
        ga.planificar(instancia, elegidos or None, sistema_plan, True, harness_raiz, matriz)
    except ga.ErrorAgente as e:
        raise ErrorMontaje(str(e))
    res["aplicado"] = True

    verif = res["verificacion"]
    despues = ga.planificar(instancia, elegidos or None, sistema_plan, False, harness_raiz, matriz)
    malas = _acciones_no_iguales(despues)
    verif["idempotente"] = not malas
    verif["fuera_de_la_instancia"] = _foto_vecinos(instancia) != antes
    for _o, r, _a in filas:
        try:
            fn._dentro(instancia, r)
        except fn.ErrorInstancia:
            verif["fuera_de_la_instancia"] = True
    venc, por_venc = _frescura(instancia, harness_raiz)
    verif["documentos_vencidos"], verif["documentos_por_vencer"] = venc, por_venc
    if malas:
        res["degradado"].append({"que": "Idempotencia", "motivo": "una segunda corrida cambiaría: " + ", ".join(malas)})
        res["ok"] = False
    else:
        res["hecho"].append("Verificado: una segunda corrida no cambia ningún archivo generado.")
    if verif["fuera_de_la_instancia"]:
        res["degradado"].append({"que": "Escritura fuera de la instancia", "motivo": "se detectó un cambio fuera de la instancia: revisar antes de seguir"})
        res["ok"] = False
    else:
        res["hecho"].append("Verificado: nada se escribió fuera de la instancia.")
    if venc is None:
        res["degradado"].append({"que": "Frescura de documentos", "motivo": "no se pudo ejecutar `herramientas/harness-frescura.py`"})
    elif venc:
        res["degradado"].append({"que": "Frescura de documentos", "motivo": f"{venc} documento(s) de la instancia con la revisión vencida"})
        res["pendiente"].append({"que": "Revisar los documentos vencidos y actualizar su cabecera de revisión",
                                 "comando": "python3 <harness>/herramientas/harness-frescura.py <instancia>"})
    else:
        res["hecho"].append("Frescura de documentos: ninguno vencido (se miran los que tienen cabecera de revisión).")

    # hecho: lo generado, descrito sin estado (igual en la primera y en la segunda corrida)
    for o, r, ac in filas:
        res["hecho"].append(f"{r} generado" + (f" ({o})" if o != "AGENTS.md" else "") + (" (el original es manual y no se tocó)" if ".generado." in r else ""))
    res["hecho"].append(f"Informe en `{INFORME_REL}`; estado en `{ESTADO_REL}` (clave `montaje`).")

    for p in res["pendiente"]:
        p.setdefault("tipo", PASO)
    _escribir_si_cambia(instancia, INFORME_REL, informe_md(res, limpiar))
    _escribir_si_cambia(instancia, ESTADO_REL, _estado_nuevo(inst["estado"], res))
    _cierre(res, salida, limpiar)
    return res


def _cierre(res, salida, limpiar, plan_solo=False):
    for p in res["pendiente"]:
        p.setdefault("tipo", PASO)
    salida("")
    salida("Hecho:" if res["aplicado"] else "Comprobaciones de solo lectura:")
    for x in res["hecho"] or ["(nada todavía)"]:
        salida(f"  - {limpiar(x)}")
    if res["degradado"]:
        salida("Degradado:")
        for d in res["degradado"]:
            salida(f"  - {limpiar(d['que'])}: {limpiar(d['motivo'])}")
    salida("Acceso a datos (lo das tú):")
    for x in BLOQUE_DATOS:
        salida(f"  {limpiar(x)}")
    ad = res["acceso_datos"]
    salida(f"  Preflight de accesos: {ad['estado']} · {limpiar(ad['detalle'])}")
    for n, v in ad["ambientes"].items():
        salida(f"    - {limpiar(n)}: {v}")
    if res["pendiente"]:
        salida("Pendiente de la persona (el montaje no lo ejecuta):")
        for i, p in enumerate(res["pendiente"], 1):
            salida(f"  {i}. [{p['tipo']}] {limpiar(p['que'])}")
            salida(f"       -> {limpiar(p['comando'])}")
    if plan_solo and not res["aplicado"]:
        salida("\nModo plan: no se escribió nada. Repite con --aplicar para ejecutarlo.")


def main(argv=None, sistema=None, preguntar=input, salida=None):
    ap = argparse.ArgumentParser(description="Montaje completo del entorno de un proyecto sobre una instancia ya creada.")
    ap.add_argument("instancia")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--agentes", help="lista separada por comas (se configuran aunque no se detecten)")
    g.add_argument("--detectar", action="store_true", help="detecta y pregunta cuáles configurar (por defecto)")
    ap.add_argument("--aplicar", action="store_true", help="escribe dentro de la instancia; sin esto solo muestra el plan")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--si", action="store_true", help="salta solo las preguntas de bajo riesgo")
    ap.add_argument("--proyecto", help="carpeta del proyecto para comprobar hooks de git y CI (solo lectura)")
    ap.add_argument("--harness", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    lista = [x.strip() for x in a.agentes.split(",") if x.strip()] if a.agentes else None
    out = salida or sys.stdout
    callado = (lambda *_a, **_k: None) if a.json else (lambda *t: print(*t, file=out))
    try:
        res = montar(a.instancia, lista, a.aplicar, preguntar, callado, sistema, a.si, a.proyecto, a.harness)
    except ErrorMontaje as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2), file=out)
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
