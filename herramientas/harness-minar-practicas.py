#!/usr/bin/env python3
"""Minero de prácticas del meta harness (SOLO LECTURA): observa lo que cada proyecto hace de verdad (spec §13 pasos 1-3).

Describe, por proyecto: (1) arquitectura real, (2) patrones de diseño con conteo y consistencia, (3) código (tamaños, any, comentarios,
pruebas, controllers con if/throw, literales repetidos) y (4) señales de calidad por módulo (commits de arreglo, churn, tamaño),
SIEMPRE como señal correlacional. Con --comparar cruza proyectos del mismo stack: divergencias y candidatos a estándar (solo propone).
Diseño: registro de detectores por stack (DETECTORES); agregar un stack = escribir un detector y registrarlo con @detector("nombre").
Uso:
  python3 harness-minar-practicas.py <proyecto> [--md|--json] [--salida ARCHIVO]
  python3 harness-minar-practicas.py --comparar <p1> <p2> ... [--md|--json] [--salida ARCHIVO]
No escribe nunca dentro de un proyecto analizado (--salida dentro de uno se rechaza).
"""
import json, os, re, statistics, subprocess, sys, pathlib, collections

LEYENDA = "señal correlacional: no demuestra que una práctica sea mejor"
IGN = {"node_modules", ".git", "dist", ".angular", ".venv", "coverage", "__pycache__", ".next", "build", ".nx", "tmp"}
RUIDO = {"migrations", "migration", "seeds", "seeders", "environments", "assets", "locale", "i18n", "brands"}
MIN_COMMITS = 3  # umbral de commits para que un módulo cuente en las comparaciones de arreglos


# ------------------------------------------------------------------ utilidades
def mediana(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 1) if xs else None


def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def p90(xs):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * 0.9))] if xs else 0


def git(root, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=120, env=env).stdout
    except Exception:
        return ""


class Proyecto:
    """Archivos del proyecto leídos una sola vez (solo lectura)."""

    def __init__(self, ruta):
        self.root = pathlib.Path(ruta).expanduser().resolve()
        if not self.root.is_dir():
            raise SystemExit(f"No existe {self.root}")
        self.pkg = self._pkg()
        self.deps = {**self.pkg.get("dependencies", {}), **self.pkg.get("devDependencies", {})}
        self.src = self.root / "src" if (self.root / "src").is_dir() else self.root
        self.textos = {}
        for dp, dns, fns in os.walk(self.src):
            dns[:] = [d for d in dns if d not in IGN]
            for f in fns:
                if f.endswith((".ts", ".html")) and not f.endswith(".d.ts"):
                    p = pathlib.Path(dp) / f
                    try:
                        self.textos[str(p.relative_to(self.root))] = p.read_text(encoding="utf8", errors="ignore")
                    except Exception:
                        pass

    def _pkg(self):
        for c in [self.root / "package.json", *sorted(self.root.glob("*/package.json"))]:
            try:
                return json.loads(c.read_text(encoding="utf8"))
            except Exception:
                continue
        return {}

    def dep(self, nombre):
        return self.deps.get(nombre)


def es_spec(rel): return bool(re.search(r"\.(spec|e2e-spec|test)\.ts$", rel))
def es_ruido(rel): return bool(set(pathlib.PurePosixPath(rel).parts) & RUIDO)
def fuentes(P): return {r: t for r, t in P.textos.items() if r.endswith(".ts") and not es_spec(r) and not es_ruido(r)}
def specs(P): return {r: t for r, t in P.textos.items() if es_spec(r)}


# ------------------------------------------------------------------ métricas de código (comunes a todos los stacks)
KW = {"if", "for", "while", "switch", "catch", "function", "return", "else", "constructor", "super", "new", "typeof"}
RE_METODO = re.compile(r"^(\s*)(?:(?:public|private|protected|static|async|readonly|override|export|get|set)\s+)*(?:function\s+)?"
                       r"([A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?\([^)]*\)\s*(?::\s*[^{;=]+)?\{\s*$")


def funciones(texto):
    lin = texto.split("\n")
    largos = []
    for i, l in enumerate(lin):
        m = RE_METODO.match(l)
        if not m or m.group(2) in KW:
            continue
        ind = m.group(1)
        for j in range(i + 1, len(lin)):
            if lin[j].startswith(ind + "}") and not lin[j].startswith(ind + "} ") or lin[j] == ind + "}":
                largos.append(j - i + 1)
                break
    return largos


def contar_comentarios(texto):
    com = cod = 0
    en_bloque = False
    for l in texto.split("\n"):
        s = l.strip()
        if not s:
            continue
        if en_bloque:
            com += 1
            if "*/" in s: en_bloque = False
        elif s.startswith("//"):
            com += 1
        elif s.startswith("/*"):
            com += 1
            if "*/" not in s: en_bloque = True
        else:
            cod += 1
    return com, cod


RE_LIT = re.compile(r"""(?:throw\s+new\s+\w+\(\s*|message:\s*)(['"`])([^'"`\n]{8,}?)\1""")
DOBLES = [("jest.fn", r"jest\.fn\("), ("jest.mock", r"jest\.mock\("), ("jest.spyOn", r"jest\.spyOn\("), ("createMock", r"createMock\b"),
          ("useValue", r"useValue\s*:"), ("mockResolvedValue/mockReturnValue", r"mock(?:Resolved|Rejected|Return)Value"), ("sinon", r"\bsinon\."),
          ("TestBed/createTestingModule", r"TestBed\.configureTestingModule|Test\.createTestingModule")]
TESTABLE = re.compile(r"\.(service|controller|repository|guard|interceptor|pipe|mapper|use-?case|handler|component|directive|resolver)\.ts$")


def metricas_codigo(P):
    fu, sp = fuentes(P), specs(P)
    lineas = {r: t.count("\n") + 1 for r, t in fu.items()}
    fn = [n for t in fu.values() for n in funciones(t)]
    com = cod = 0
    for t in fu.values():
        c, d = contar_comentarios(t)
        com += c; cod += d
    n_any = sum(len(re.findall(r":\s*any\b|<any>|\bas any\b|any\[\]", t)) for t in fu.values())
    lits = collections.Counter(m.group(2) for t in fu.values() for m in RE_LIT.finditer(t))
    rep = [(k, v) for k, v in lits.most_common() if v >= 3]
    testables = [r for r in fu if TESTABLE.search(r)]
    con_spec = [r for r in testables if r[:-3] + ".spec.ts" in sp]
    dobles = {n: sum(len(re.findall(rx, t)) for t in sp.values()) for n, rx in DOBLES}
    ctrl = {r: t for r, t in fu.items() if r.endswith(".controller.ts")}
    return {
        "archivos_fuente": len(fu), "lineas_fuente": sum(lineas.values()),
        "lineas_por_archivo": {"mediana": mediana(list(lineas.values())), "p90": p90(list(lineas.values())), "max": max(lineas.values(), default=0),
                               "mayores_a_300": sum(1 for v in lineas.values() if v > 300)},
        "funciones": {"detectadas": len(fn), "mediana": mediana(fn), "p90": p90(fn), "max": max(fn, default=0), "mayores_a_50": sum(1 for v in fn if v > 50),
                      "nota": "aprox. por líneas; firmas multilínea no se detectan"},
        "any": {"usos": n_any, "por_1000_lineas": round(1000 * n_any / max(1, sum(lineas.values())), 2)},
        "comentarios": {"lineas": com, "pct_sobre_codigo": pct(com, cod)},
        "pruebas": {"specs": len(sp), "lineas_spec": sum(t.count("\n") + 1 for t in sp.values()), "specs_por_fuente": round(len(sp) / max(1, len(fu)), 2),
                    "testables": len(testables), "testables_con_spec_hermano": len(con_spec), "pct_testables_con_spec": pct(len(con_spec), len(testables)),
                    "dobles": {k: v for k, v in dobles.items() if v}},
        "controllers": {"archivos": len(ctrl), "con_if_o_throw": sum(1 for t in ctrl.values() if re.search(r"\bif\s*\(|\bthrow\s", t)),
                        "pct_con_if_o_throw": pct(sum(1 for t in ctrl.values() if re.search(r"\bif\s*\(|\bthrow\s", t)), len(ctrl)),
                        "if": sum(len(re.findall(r"\bif\s*\(", t)) for t in ctrl.values()), "throw": sum(len(re.findall(r"\bthrow\s", t)) for t in ctrl.values())},
        "constantes": {"archivos_constants": sum(1 for r in fu if re.search(r"constants?\.ts$|\.consts?\.ts$", r)), "enums": sum(len(re.findall(r"\bexport\s+enum\b", t)) for t in fu.values()),
                       "mensajes_repetidos_3+": len(rep), "ocurrencias_en_repetidos": sum(v for _, v in rep), "top": [{"texto": k[:70], "veces": v} for k, v in rep[:5]]},
    }


# ------------------------------------------------------------------ señales de calidad por módulo (git)
RE_FIX = re.compile(r"^\s*(?:fix|hotfix)(?:\(|:|!|\s|/|$)|corrige", re.I)


def senales_git(P, unidades, archivo_unidad):
    """Una sola corrida de git log (equivale a `git log -- <carpeta>` por módulo); mapea cada archivo a su unidad."""
    salida = git(P.root, "log", "--no-merges", "--no-renames", "--relative", "--numstat", "-n", "6000", "--format=%x01%H%x09%s", "--", ".")
    commits = collections.defaultdict(set); fixes = collections.defaultdict(set); churn = collections.Counter()
    total = 0; es_fix = {}
    for bloque in salida.split("\x01")[1:]:
        lin = bloque.strip("\n").split("\n")
        h, _, asunto = lin[0].partition("\t")
        total += 1
        es_fix[h] = bool(RE_FIX.search(asunto))
        for l in lin[1:]:
            p = l.split("\t")
            if len(p) != 3: continue
            u = archivo_unidad.get(p[2])
            if not u: continue
            commits[u].add(h)
            if es_fix[h]: fixes[u].add(h)
            if p[0].isdigit() and p[1].isdigit(): churn[u] += int(p[0]) + int(p[1])
    for u, d in unidades.items():
        c, f = len(commits[u]), len(fixes[u])
        d["git"] = {"commits": c, "arreglos": f, "pct_arreglos": pct(f, c), "churn": churn[u], "tamano": d["lineas"],
                    "churn_sobre_tamano": round(churn[u] / d["lineas"], 2) if d["lineas"] else None}
    return {"commits_analizados": total, "tope": 6000, "leyenda": LEYENDA}


def evidencia_practicas(unidades):
    """Mediana de % de arreglos con y sin cada práctica (solo módulos con >= MIN_COMMITS). Correlacional."""
    res = {}
    nombres = {k for u in unidades for k, v in u["practicas"].items() if v is not None}
    for k in sorted(nombres):
        con = [u["git"]["pct_arreglos"] for u in unidades if u["practicas"].get(k) is True and u["git"]["commits"] >= MIN_COMMITS]
        sin = [u["git"]["pct_arreglos"] for u in unidades if u["practicas"].get(k) is False and u["git"]["commits"] >= MIN_COMMITS]
        res[k] = {"n_con": len(con), "n_sin": len(sin), "mediana_arreglos_con": mediana(con), "mediana_arreglos_sin": mediana(sin)}
    return res


# ------------------------------------------------------------------ registro de detectores por stack
DETECTORES = {}


def detector(nombre):
    def reg(cls):
        DETECTORES[nombre] = cls
        return cls
    return reg


def construir_unidades(P, fu_rel, resolver):
    """resolver(rel) -> (nombre_unidad, tipo) ; devuelve {unidad: {archivos, tipo,...}}"""
    uni = {}
    for rel in fu_rel:
        nombre, tipo = resolver(rel)
        if nombre is None: continue
        u = uni.setdefault(nombre, {"nombre": nombre, "tipo": tipo, "archivos": [], "specs": []})
        u["archivos"].append(rel)
    return uni


def sub_unidad_specs(P, uni, arch_u):
    for rel in specs(P):
        u = arch_u.get(rel[:-8] + ".ts") or arch_u.get(re.sub(r"\.(spec|e2e-spec|test)\.ts$", ".ts", rel))
        if u: uni[u]["specs"].append(rel)


def finalizar(P, detector_nombre, uni, arquitectura, patrones_globales, extra):
    arch_u = {a: n for n, u in uni.items() for a in u["archivos"]}
    for u in uni.values():
        u["lineas"] = sum(P.textos[a].count("\n") + 1 for a in u["archivos"])
    g = senales_git(P, uni, arch_u)
    unidades = [u for u in uni.values() if u.get("relevante")]
    cod = metricas_codigo(P)
    # consistencia por práctica (a nivel de módulo)
    tabla = {}
    for k in sorted({k for u in unidades for k in u["practicas"]}):
        ap = [u for u in unidades if u["practicas"].get(k) is not None]
        si = [u for u in ap if u["practicas"][k]]
        tabla[k] = {"modulos_aplicables": len(ap), "modulos_con_practica": len(si), "consistencia_pct": pct(len(si), len(ap)),
                    "ejemplos": [u["nombre"] for u in si[:3]], "complejidad": COMPLEJIDAD.get(k, 1)}
    for k, v in patrones_globales.items():
        tabla.setdefault(k, {}).update(v)
    return {"proyecto": P.root.name, "stack": detector_nombre, "arquitectura": arquitectura, "patrones": tabla, "codigo": cod,
            "calidad": {"git": g, "evidencia_por_practica": evidencia_practicas(unidades), "leyenda": LEYENDA,
                        "modulos": [{"modulo": u["nombre"], "tipo": u["tipo"], "estilo": u.get("estilo"), **u["git"]} for u in unidades]},
            "familias": {f: collections.Counter(u["familias"].get(f) for u in unidades if u["familias"].get(f)) for f in sorted({f for u in unidades for f in u["familias"]})},
            "_unidades": [{"nombre": u["nombre"], "practicas": u["practicas"], "familias": u["familias"], "git": u["git"], "estilo": u.get("estilo")} for u in unidades],
            **extra}


COMPLEJIDAD = {  # peso orientativo, declarado: 1 simple · 2 media · 3 alta. Es una convención de la herramienta, no una medición.
    "repositorio propio": 1, "ORM inyectado directo en servicio": 0, "validación en DTO": 1, "guardias/interceptores": 1, "mapeador/presentador": 1,
    "caso de uso/handler": 2, "puerto-adaptador con tokens": 3, "unidad de trabajo/transacciones": 2, "eventos y listeners": 2, "fábricas": 2,
    "estrategias (interfaz con varias implementaciones)": 2, "controller delgado (sin if/throw)": 0, "pruebas junto al fuente": 1, "sin any": 0,
    "componentes standalone": 1, "NgModule": 1, "formularios reactivos": 2, "formularios por plantilla": 1, "estado con signals": 1,
    "estado con RxJS (Subjects)": 1, "estado con NgRx": 3, "servicio HTTP dedicado": 1, "HttpClient directo en componente (anti-patrón)": 0, "OnPush": 1,
    "hexagonal": 3, "funcional (controller+service en el módulo)": 1, "capas planas por tipo": 1,
    "rxjs": 1, "signals": 1, "ngrx": 3, "reactivos": 2, "plantilla": 1, "standalone": 1, "ngmodule": 1, "mixto": 2,
}


# ------------------------------------------------------------------ NestJS
FLAT = {"controllers", "services", "repositories", "dtos", "dto", "entities", "mappers", "interfaces", "guards", "interceptors", "pipes", "providers",
        "middlewares", "listeners", "utils", "models", "enums", "constants", "decorators", "filters", "validators", "helpers"}
VALID = re.compile(r"@(?:Is[A-Z]\w*|Min|Max|Length|MinLength|MaxLength|ValidateNested|Matches|ArrayNotEmpty|ArrayMinSize|Validate|Contains|NotEquals|Equals)\(")
TOKEN = re.compile(r"""@Inject\(\s*(?:['"`]|(?!CACHE_MANAGER|REQUEST|CONTEXT|WINSTON|forwardRef)[A-Z][A-Z0-9_]{2,}\b)|provide:\s*(?:['"`]|(?!APP_|CACHE_MANAGER)[A-Z][A-Z0-9_]{2,}\b)""")
CASOUSO = re.compile(r"(?:\.|/)(?:use-?case|uses?-?cases?|handler|interactor)(?:s)?(?:\.ts$|/)|@(?:Command|Query|Events)Handler\(|/uses?-?cases?/", re.I)


def _rel_unidad_modulo(rel, mod_dirs):
    d = str(pathlib.PurePosixPath(rel).parent)
    while d not in ("", "."):
        if d in mod_dirs: return d
        d = str(pathlib.PurePosixPath(d).parent)
    return None


def _stem(rel):
    return pathlib.PurePosixPath(rel).name.split(".")[0]


@detector("nestjs")
class NestJS:
    nombre = "nestjs"

    @staticmethod
    def detecta(P): return P.dep("@nestjs/core") is not None

    @staticmethod
    def analiza(P):
        fu = fuentes(P)
        srcrel = str(P.src.relative_to(P.root)) if P.src != P.root else "."
        mod_dirs = {str(pathlib.PurePosixPath(r).parent) for r in fu if r.endswith(".module.ts")} - {srcrel}
        flat_rel = lambda r: (pathlib.PurePosixPath(r).relative_to(srcrel).parts[:1] if srcrel != "." else pathlib.PurePosixPath(r).parts[:1])

        def resolver(rel):
            m = _rel_unidad_modulo(rel, mod_dirs)
            if m: return m, "modulo"
            if flat_rel(rel) and flat_rel(rel)[0] in FLAT and len(pathlib.PurePosixPath(rel).parts) > 2:
                if re.search(r"\.(controller|service|repository|mapper|guard|listener|interceptor|factory|strategy|handler)\.ts$", rel):
                    return "plano:" + _stem(rel), "plano"
                return "capa:" + flat_rel(rel)[0], "capa"
            return "raiz", "raiz"
        uni = construir_unidades(P, fu, resolver)
        arch_u = {a: n for n, u in uni.items() for a in u["archivos"]}
        sub_unidad_specs(P, uni, arch_u)
        # interfaces/abstractas con >= 2 implementaciones (estrategia)
        defs = {m.group(1): r for r, t in fu.items() for m in re.finditer(r"export\s+(?:interface|abstract\s+class)\s+(\w+)", t)}
        impl = collections.Counter()
        for t in fu.values():
            for m in re.finditer(r"class\s+\w+(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s<>]+?))?\s*\{", t):
                for n in [m.group(1)] + [x.strip().split("<")[0] for x in (m.group(2) or "").split(",")]:
                    if n in defs: impl[n] += 1
        estrategias = {n for n, c in impl.items() if c >= 2}
        estr_unidad = {arch_u[defs[n]] for n in estrategias if defs[n] in arch_u}
        dto_files = {r: t for r, t in fu.items() if re.search(r"\.dto\.ts$|/dtos?/", r)}
        dto_val = {r for r, t in dto_files.items() if VALID.search(t)}

        for n, u in uni.items():
            txt = {a: fu[a] for a in u["archivos"]}
            names = list(txt)
            def hay(rx, solo=None): return any(re.search(rx, t) for a, t in txt.items() if solo is None or re.search(solo, a))
            ctrl = [a for a in names if a.endswith(".controller.ts")]
            serv = [a for a in names if re.search(r"\.service\.ts$", a)]
            repo = [a for a in names if a.endswith(".repository.ts")]
            cu = [a for a in names if CASOUSO.search(a) or CASOUSO.search(txt[a])]
            u["relevante"] = u["tipo"] in ("modulo", "plano") and bool(ctrl or serv or repo or cu)
            dirs = {p for a in names for p in pathlib.PurePosixPath(a).parts}
            hexa = "domain" in dirs and bool(dirs & {"application", "infrastructure"})
            if u["tipo"] == "plano": u["estilo"] = "capas planas por tipo"
            elif hexa: u["estilo"] = "hexagonal"
            elif ctrl and (serv or cu): u["estilo"] = "funcional (controller+service en el módulo)"
            else: u["estilo"] = "mínimo (sin controller+service)"
            p = {}
            con_logica = bool(serv or cu or repo)
            p["repositorio propio"] = (bool(repo) or hay(r"class\s+\w+Repository\b")) if con_logica else None
            p["ORM inyectado directo en servicio"] = hay(r"@InjectRepository\(") if con_logica else None
            p["caso de uso/handler"] = bool(cu) if (ctrl or cu or serv) else None
            p["puerto-adaptador con tokens"] = (any(a.endswith(".port.ts") for a in names) or hay(TOKEN.pattern)) if con_logica else None
            dts = [a for a in names if a in dto_files]
            p["validación en DTO"] = any(a in dto_val for a in dts) if dts else None
            p["mapeador/presentador"] = (hay(r"\.(mapper|presenter|assembler)\.ts$|class\s+\w*(Mapper|Presenter|Assembler)\b|\btoDto\(|\bfromEntity\(") or any(re.search(r"\.(mapper|presenter|assembler)\.ts$", a) for a in names)) if ctrl else None
            p["guardias/interceptores"] = (hay(r"@UseGuards\(|@UseInterceptors\(") or any(re.search(r"\.(guard|interceptor)\.ts$", a) for a in names)) if ctrl else None
            p["unidad de trabajo/transacciones"] = hay(r"\.transaction\(|QueryRunner|@Transactional|startTransaction|runInTransaction") if con_logica else None
            p["eventos y listeners"] = (hay(r"@OnEvent\(|EventEmitter2?\b|@EventsHandler\(|\.emit\(") or any(a.endswith(".listener.ts") for a in names)) if u["relevante"] else None
            p["fábricas"] = (hay(r"useFactory|class\s+\w+Factory\b") or any(a.endswith(".factory.ts") for a in names)) if u["relevante"] else None
            p["estrategias (interfaz con varias implementaciones)"] = (n in estr_unidad or hay(r"\.strategy\.ts$", ".strategy.ts$")) if u["relevante"] else None
            p["controller delgado (sin if/throw)"] = (not hay(r"\bif\s*\(|\bthrow\s", r"\.controller\.ts$")) if ctrl else None
            testables = [a for a in names if TESTABLE.search(a)]
            p["pruebas junto al fuente"] = (sum(1 for a in testables if a[:-3] + ".spec.ts" in P.textos) * 2 >= len(testables)) if testables else None
            p["sin any"] = (not hay(r":\s*any\b|<any>|\bas any\b")) if u["relevante"] else None
            u["practicas"] = {k: v for k, v in p.items() if v is not None}
            acceso = [x for x, c in (("repositorio propio", p["repositorio propio"]), ("ORM directo", p["ORM inyectado directo en servicio"])) if c]
            u["familias"] = {"arquitectura": u["estilo"].split(" (")[0] if u["relevante"] else None,
                             "acceso a datos": ("+".join(acceso) if acceso else None) if con_logica else None}

        relev = [u for u in uni.values() if u.get("relevante")]
        # arquitectura: estilo por módulos y por archivos
        por_estilo = collections.defaultdict(lambda: {"modulos": 0, "archivos": 0, "ejemplos": []})
        for u in relev:
            e = por_estilo[u["estilo"]]
            e["modulos"] += 1; e["archivos"] += len(u["archivos"]); e["ejemplos"].append(u["nombre"])
        total_m = len(relev) or 1
        capas = {n: len(u["archivos"]) for n, u in uni.items() if u["tipo"] == "capa"}
        total_f = sum(e["archivos"] for e in por_estilo.values()) + sum(capas.values())
        estilos = [{"estilo": k, "modulos": v["modulos"], "pct_modulos": pct(v["modulos"], total_m), "archivos": v["archivos"],
                    "pct_archivos": pct(v["archivos"], total_f), "ejemplos": v["ejemplos"][:3]} for k, v in sorted(por_estilo.items(), key=lambda kv: -kv[1]["modulos"])]
        if capas:
            estilos.append({"estilo": "capas por tipo compartidas (dto/entity/util sin módulo)", "modulos": None, "pct_modulos": None, "archivos": sum(capas.values()),
                            "pct_archivos": pct(sum(capas.values()), total_f), "ejemplos": sorted(capas)[:3]})
        dom = max(estilos, key=lambda e: e["modulos"] or 0, default=None)
        etiqueta = (dom["estilo"] if dom and (dom["pct_modulos"] or 0) >= 70 else "mezcla de estilos")
        arq = {"estilo_dominante": etiqueta, "unidades_analizadas": len(relev), "modulos_nest": len(mod_dirs), "estilos": estilos}
        glob = {"validación en DTO": {"archivos_dto": len(dto_files), "dto_con_validadores": len(dto_val), "consistencia_archivos_pct": pct(len(dto_val), len(dto_files))},
                "estrategias (interfaz con varias implementaciones)": {"interfaces_con_2+_impl": len(estrategias), "nombres": sorted(estrategias)[:5]},
                "guardias/interceptores": {"usos_UseGuards": sum(len(re.findall(r"@UseGuards\(", t)) for t in fu.values()),
                                           "usos_UseInterceptors": sum(len(re.findall(r"@UseInterceptors\(", t)) for t in fu.values()),
                                           "globales_APP_GUARD/INTERCEPTOR": sum(len(re.findall(r"APP_(?:GUARD|INTERCEPTOR)", t)) for t in fu.values())}}
        for k, rx in (("repositorio propio", r"\.repository\.ts$"), ("caso de uso/handler", None), ("eventos y listeners", r"@OnEvent\(|@EventsHandler\("), ("fábricas", r"useFactory|class\s+\w+Factory\b")):
            glob.setdefault(k, {})["conteo_global"] = sum(1 for r, t in fu.items() if (CASOUSO.search(r) or CASOUSO.search(t)) ) if rx is None else \
                (sum(1 for r in fu if re.search(rx, r)) if rx.endswith("$") else sum(len(re.findall(rx, t)) for t in fu.values()))
        glob["unidad de trabajo/transacciones"] = {"conteo_global": sum(len(re.findall(r"\.transaction\(|QueryRunner|@Transactional|startTransaction", t)) for t in fu.values())}
        glob["ORM inyectado directo en servicio"] = {"conteo_global": sum(len(re.findall(r"@InjectRepository\(", t)) for t in fu.values())}
        return finalizar(P, "nestjs", uni, arq, glob, {})


# ------------------------------------------------------------------ Angular
RE_COMP = re.compile(r"@Component\(\s*\{(.*?)\}\s*\)\s*(?:export\s+)?class", re.S)


@detector("angular")
class Angular:
    nombre = "angular"

    @staticmethod
    def detecta(P): return P.dep("@angular/core") is not None

    @staticmethod
    def analiza(P):
        fu = fuentes(P)
        htmls = {r: t for r, t in P.textos.items() if r.endswith(".html")}
        ver = re.sub(r"[^\d.]", "", str(P.dep("@angular/core") or "0")).split(".")
        mayor = int(ver[0] or 0)
        app = pathlib.PurePosixPath(str(P.src.relative_to(P.root))) / "app" if P.src != P.root else pathlib.PurePosixPath("app")
        mod_dirs = {str(pathlib.PurePosixPath(r).parent) for r in fu if r.endswith(".module.ts")} - {str(app)}
        agrupadores = {"pages", "modules", "features", "views", "screens", "routes", "containers"}

        def resolver(rel):
            m = _rel_unidad_modulo(rel, mod_dirs)
            if m: return m, "modulo"
            partes = pathlib.PurePosixPath(rel).parts
            try: i = partes.index("app")
            except ValueError: return "raiz", "raiz"
            resto = partes[i + 1:]
            if len(resto) <= 1: return "raiz", "raiz"
            if resto[0] in agrupadores and len(resto) > 2: return "/".join(resto[:2]), "carpeta"
            return resto[0], "carpeta"
        uni = construir_unidades(P, fu, resolver)
        arch_u = {a: n for n, u in uni.items() for a in u["archivos"]}
        sub_unidad_specs(P, uni, arch_u)
        # HTML asociado a cada unidad (para formularios y flujo de control)
        html_u = collections.defaultdict(dict)
        for r, t in htmls.items():
            c = r[:-5] + ".ts"
            if c in arch_u: html_u[arch_u[c]][r] = t
        comps_tot = std_tot = onpush_tot = 0
        subs = subs_ok = 0
        http_directo_tot = 0
        for n, u in uni.items():
            txt = {a: fu[a] for a in u["archivos"]}
            comps = {a: t for a, t in txt.items() if "@Component(" in t}
            servs = {a: t for a, t in txt.items() if "@Injectable(" in t and not a.endswith(".component.ts")}
            std, onp = 0, 0
            for a, t in comps.items():
                for m in RE_COMP.finditer(t):
                    cuerpo = m.group(1)
                    if re.search(r"standalone\s*:\s*false", cuerpo): pass
                    elif re.search(r"standalone\s*:\s*true", cuerpo) or mayor >= 19: std += 1
                    onp += bool(re.search(r"ChangeDetectionStrategy\.OnPush", cuerpo))
                if ".subscribe(" in t:
                    subs += 1
                    subs_ok += bool(re.search(r"takeUntil|takeUntilDestroyed|unsubscribe|DestroyRef|\.pipe\(\s*first\(|take\(1\)", t))
            comps_tot += len(comps); std_tot += std; onpush_tot += onp
            htm = "\n".join(html_u[n].values())
            alltxt = "\n".join(txt.values())
            reactivo = bool(re.search(r"FormGroup|FormBuilder|FormControl|ReactiveFormsModule|formControlName|\[formGroup\]", alltxt + htm))
            plantilla = bool(re.search(r"ngModel|\bngForm\b|#\w+=\"ngForm\"", alltxt + htm))
            http_d = [a for a, t in comps.items() if re.search(r"\bHttpClient\b", t)]
            http_directo_tot += len(http_d)
            u["relevante"] = bool(comps or servs)
            u["estilo"] = "standalone" if comps and std == len(comps) else ("NgModule" if comps and std == 0 else ("mixto" if comps else "sin componentes"))
            p = {}
            p["componentes standalone"] = (std == len(comps)) if comps else None
            p["NgModule"] = any(a.endswith(".module.ts") for a in txt) if u["relevante"] else None
            p["formularios reactivos"] = reactivo if (reactivo or plantilla) else None
            p["formularios por plantilla"] = plantilla if (reactivo or plantilla) else None
            p["estado con signals"] = bool(re.search(r"\bsignal\(|\bcomputed\(|toSignal\(", alltxt)) if u["relevante"] else None
            p["estado con RxJS (Subjects)"] = bool(re.search(r"BehaviorSubject|ReplaySubject|new Subject\b", alltxt)) if u["relevante"] else None
            p["estado con NgRx"] = bool(re.search(r"@ngrx/|createReducer|createAction|createEffect", alltxt)) if u["relevante"] else None
            p["servicio HTTP dedicado"] = any(re.search(r"\bHttpClient\b", t) for t in servs.values()) if comps else None
            p["HttpClient directo en componente (anti-patrón)"] = bool(http_d) if comps else None
            p["OnPush"] = (onp > 0) if comps else None
            testables = [a for a in txt if TESTABLE.search(a)]
            p["pruebas junto al fuente"] = (sum(1 for a in testables if a[:-3] + ".spec.ts" in P.textos) * 2 >= len(testables)) if testables else None
            u["practicas"] = {k: v for k, v in p.items() if v is not None}
            est = [x for x, c in (("ngrx", p["estado con NgRx"]), ("signals", p["estado con signals"]), ("rxjs", p["estado con RxJS (Subjects)"])) if c]
            u["familias"] = {"componentes": {"standalone": "standalone", "NgModule": "ngmodule", "mixto": "mixto"}.get(u["estilo"]),
                             "formularios": ("mixto" if reactivo and plantilla else "reactivos" if reactivo else "plantilla") if (reactivo or plantilla) else None,
                             "estado": ("+".join(est) if est else None) if u["relevante"] else None}
        relev = [u for u in uni.values() if u.get("relevante")]
        por = collections.defaultdict(lambda: {"modulos": 0, "archivos": 0, "ejemplos": []})
        for u in relev:
            e = por[u["estilo"]]; e["modulos"] += 1; e["archivos"] += len(u["archivos"]); e["ejemplos"].append(u["nombre"])
        tf = sum(e["archivos"] for e in por.values()) or 1
        estilos = [{"estilo": k, "modulos": v["modulos"], "pct_modulos": pct(v["modulos"], len(relev)), "archivos": v["archivos"], "pct_archivos": pct(v["archivos"], tf),
                    "ejemplos": v["ejemplos"][:3]} for k, v in sorted(por.items(), key=lambda kv: -kv[1]["modulos"])]
        dom = estilos[0] if estilos else None
        rutas = [t for r, t in fu.items() if re.search(r"Routes\b|RouterModule\.for", t)]
        lazy = sum(len(re.findall(r"loadChildren|loadComponent", t)) for t in rutas)
        eager = sum(len(re.findall(r"\bcomponent\s*:", t)) for t in rutas)
        ctl_nuevo = sum(len(re.findall(r"@(?:if|for|switch)\b", t)) for t in htmls.values())
        ctl_viejo = sum(len(re.findall(r"\*ng(?:If|For|Switch)", t)) for t in htmls.values())
        arq = {"estilo_dominante": (dom["estilo"] if dom and (dom["pct_modulos"] or 0) >= 70 else "mezcla de estilos"), "version_angular": P.dep("@angular/core"),
               "unidades_analizadas": len(relev), "ngmodules": sum(1 for r in fu if r.endswith(".module.ts")), "estilos": estilos}
        glob = {"componentes standalone": {"componentes": comps_tot, "standalone": std_tot, "consistencia_componentes_pct": pct(std_tot, comps_tot)},
                "OnPush": {"componentes_onpush": onpush_tot, "consistencia_componentes_pct": pct(onpush_tot, comps_tot)},
                "rutas perezosas": {"perezosas": lazy, "directas": eager, "consistencia_pct": pct(lazy, lazy + eager)},
                "desuscripción segura": {"componentes_con_subscribe": subs, "con_takeUntil/unsubscribe": subs_ok, "consistencia_pct": pct(subs_ok, subs)},
                "flujo de control moderno (@if/@for)": {"moderno": ctl_nuevo, "estructural_antiguo": ctl_viejo, "consistencia_pct": pct(ctl_nuevo, ctl_nuevo + ctl_viejo)},
                "estado con signals": {"usos": sum(len(re.findall(r"\bsignal\(|\bcomputed\(", t)) for t in fu.values())},
                "estado con NgRx": {"usos": sum(len(re.findall(r"@ngrx/", t)) for t in fu.values())},
                "estado con RxJS (Subjects)": {"usos": sum(len(re.findall(r"BehaviorSubject|ReplaySubject|new Subject\b", t)) for t in fu.values())},
                "servicio HTTP dedicado": {"servicios_con_HttpClient": sum(1 for r, t in fu.items() if r.endswith(".service.ts") and re.search(r"\bHttpClient\b", t))},
                "interceptores y guards": {"interceptores": sum(1 for t in fu.values() if re.search(r"HttpInterceptor|HttpInterceptorFn", t)),
                                           "guards": sum(1 for r in fu if r.endswith(".guard.ts"))}}
        return finalizar(P, "angular", uni, arq, glob, {"html": {"archivos": len(htmls), "async_pipe": sum(len(re.findall(r"\|\s*async\b", t)) for t in htmls.values())}})


# ------------------------------------------------------------------ comparación
def analizar(ruta):
    P = Proyecto(ruta)
    res = [d.analiza(P) for n, d in DETECTORES.items() if d.detecta(P)]
    if not res:
        raise SystemExit(f"{P.root.name}: ningún detector de stack aplica ({', '.join(DETECTORES)})")
    return res[0] if len(res) == 1 else res[0]


def candidatos(stack, resultados):
    """Propone (no decide): por familia, la alternativa con menor % de arreglos (mediana) y, si empatan (<5 pts), la de menor complejidad."""
    unidades = [u for r in resultados for u in r["_unidades"]]
    out = {"familias": [], "practicas": []}
    for f in sorted({f for u in unidades for f in u["familias"]}):
        grupos = collections.defaultdict(list)
        for u in unidades:
            lab = u["familias"].get(f)
            if lab: grupos[lab].append(u)
        filas = []
        for lab, us in grupos.items():
            vals = [x["git"]["pct_arreglos"] for x in us if x["git"]["commits"] >= MIN_COMMITS]
            filas.append({"alternativa": lab, "modulos": len(us), "modulos_con_commits": len(vals), "mediana_pct_arreglos": mediana(vals),
                          "complejidad": max([COMPLEJIDAD.get(p, 1) for p in lab.split("+")] or [1])})
        ev = [x for x in filas if x["modulos_con_commits"] >= 3 and x["mediana_pct_arreglos"] is not None]
        prop, motivo = None, "evidencia insuficiente (se exigen >= 3 módulos con >= %d commits por alternativa)" % MIN_COMMITS
        if len(ev) >= 2:
            mejor = min(x["mediana_pct_arreglos"] for x in ev)
            empate = [x for x in ev if x["mediana_pct_arreglos"] - mejor < 5]
            prop = min(empate, key=lambda x: (x["complejidad"], x["mediana_pct_arreglos"]))["alternativa"]
            motivo = f"menor % de arreglos (mediana {mejor}) y, entre las que empatan por <5 pts, la de menor complejidad"
        elif len(ev) == 1:
            motivo = "solo una alternativa tiene evidencia suficiente: no hay contra qué comparar"
        out["familias"].append({"familia": f, "filas": sorted(filas, key=lambda x: -x["modulos"]), "propuesta": prop, "motivo": motivo})
    nombres = sorted({k for u in unidades for k in u["practicas"]})
    for k in nombres:
        con = [u["git"]["pct_arreglos"] for u in unidades if u["practicas"].get(k) is True and u["git"]["commits"] >= MIN_COMMITS]
        sin = [u["git"]["pct_arreglos"] for u in unidades if u["practicas"].get(k) is False and u["git"]["commits"] >= MIN_COMMITS]
        ap = [u for u in unidades if k in u["practicas"]]
        cons = pct(sum(1 for u in ap if u["practicas"][k]), len(ap))
        mc, ms = mediana(con), mediana(sin)
        comp = COMPLEJIDAD.get(k, 1)
        if len(con) < 3 or len(sin) < 3: veredicto = "sin evidencia suficiente"
        elif mc <= ms + 0: veredicto = "% de arreglos igual o menor con la práctica (confusores: tamaño, edad, actividad)" + (" · complejidad alta: exigir mejora clara antes de adoptarla" if comp >= 3 and ms - mc < 5 else "")
        else: veredicto = "% de arreglos mayor con la práctica (confusores: tamaño, edad, actividad)"
        out["practicas"].append({"practica": k, "consistencia_pct": cons, "n_con": len(con), "n_sin": len(sin), "mediana_arreglos_con": mc, "mediana_arreglos_sin": ms,
                                 "complejidad": comp, "lectura": veredicto})
    return out


def comparar(rutas):
    res = [analizar(r) for r in rutas]
    por_stack = collections.defaultdict(list)
    for r in res: por_stack[r["stack"]].append(r)
    salida = {"leyenda": LEYENDA, "proyectos": [r["proyecto"] for r in res], "stacks": {}}
    for st, rs in por_stack.items():
        practicas = sorted({k for r in rs for k, v in r["patrones"].items() if v.get("consistencia_pct") is not None or v.get("consistencia_archivos_pct") is not None
                            or v.get("consistencia_componentes_pct") is not None})
        def cons(r, k):
            v = r["patrones"].get(k, {})
            for c in ("consistencia_pct", "consistencia_archivos_pct", "consistencia_componentes_pct"):
                if v.get(c) is not None: return v[c]
            return None
        tabla = {k: {r["proyecto"]: cons(r, k) for r in rs} for k in practicas}
        div = []
        if len(rs) > 1:
            for k, vals in tabla.items():
                v = [x for x in vals.values() if x is not None]
                if len(v) >= 2 and max(v) - min(v) >= 30:
                    div.append({"practica": k, "valores": vals, "brecha_pts": round(max(v) - min(v), 1)})
            est = {r["proyecto"]: r["arquitectura"]["estilo_dominante"] for r in rs}
            if len(set(est.values())) > 1: div.insert(0, {"practica": "estilo de arquitectura dominante", "valores": est, "brecha_pts": None})
            for f in sorted({f for r in rs for f in r["familias"]}):
                dist = {r["proyecto"]: (max(r["familias"].get(f, {}), key=r["familias"][f].get) if r["familias"].get(f) else None) for r in rs}
                if len({v for v in dist.values() if v}) > 1: div.append({"practica": f"alternativa dominante en «{f}»", "valores": dist, "brecha_pts": None})
        salida["stacks"][st] = {"proyectos": [r["proyecto"] for r in rs], "tabla": tabla, "divergencias": sorted(div, key=lambda d: -(d["brecha_pts"] or 0)),
                                "candidatos": candidatos(st, rs), "arquitectura": {r["proyecto"]: r["arquitectura"]["estilo_dominante"] for r in rs},
                                "resultados": [{k: v for k, v in r.items() if k != "_unidades"} for r in rs]}
    return salida


# ------------------------------------------------------------------ salida Markdown
def md_proyecto(r):
    L = [f"# Prácticas observadas: {r['proyecto']} ({r['stack']})", "", f"> {LEYENDA}", ""]
    a = r["arquitectura"]
    L += ["## 1. Arquitectura real", "", f"Estilo dominante: **{a['estilo_dominante']}** · unidades analizadas: {a['unidades_analizadas']}"
          + (f" · NgModules: {a['ngmodules']} · Angular {a['version_angular']}" if r["stack"] == "angular" else f" · módulos Nest: {a['modulos_nest']}"), "",
          "| estilo | módulos | % módulos | archivos | % archivos | ejemplos |", "|---|---|---|---|---|---|"]
    for e in a["estilos"]:
        L.append(f"| {e['estilo']} | {e['modulos'] if e['modulos'] is not None else '-'} | {e['pct_modulos'] if e['pct_modulos'] is not None else '-'} | {e['archivos']} | {e['pct_archivos']} | {', '.join(e['ejemplos'])} |")
    L += ["", "## 2. Patrones de diseño observados", "", "| patrón / práctica | aplicables | con la práctica | consistencia % | otros datos | complejidad |", "|---|---|---|---|---|---|"]
    for k, v in r["patrones"].items():
        otros = ", ".join(f"{c}={d}" for c, d in v.items() if c not in ("modulos_aplicables", "modulos_con_practica", "consistencia_pct", "ejemplos", "complejidad"))
        cons = v.get("consistencia_pct")
        L.append(f"| {k} | {v.get('modulos_aplicables', '-')} | {v.get('modulos_con_practica', '-')} | {cons if cons is not None else '-'} | {otros or '-'} | {v.get('complejidad', COMPLEJIDAD.get(k, '-'))} |")
    c = r["codigo"]
    L += ["", "## 3. Código", "",
          f"- Archivos fuente: {c['archivos_fuente']} · líneas: {c['lineas_fuente']} · por archivo: mediana {c['lineas_por_archivo']['mediana']}, p90 {c['lineas_por_archivo']['p90']}, máx {c['lineas_por_archivo']['max']}, >300 líneas: {c['lineas_por_archivo']['mayores_a_300']}",
          f"- Funciones (aprox.): {c['funciones']['detectadas']} · mediana {c['funciones']['mediana']}, p90 {c['funciones']['p90']}, máx {c['funciones']['max']}, >50 líneas: {c['funciones']['mayores_a_50']}",
          f"- `any`: {c['any']['usos']} usos ({c['any']['por_1000_lineas']} por 1000 líneas) · comentarios: {c['comentarios']['pct_sobre_codigo']} % sobre código",
          f"- Pruebas: {c['pruebas']['specs']} specs ({c['pruebas']['specs_por_fuente']} por archivo fuente) · {c['pruebas']['testables_con_spec_hermano']}/{c['pruebas']['testables']} archivos testables con spec hermano ({c['pruebas']['pct_testables_con_spec']} %) · dobles: {c['pruebas']['dobles']}",
          f"- Controllers: {c['controllers']['archivos']} · con if/throw: {c['controllers']['con_if_o_throw']} ({c['controllers']['pct_con_if_o_throw']} %) · `if`: {c['controllers']['if']}, `throw`: {c['controllers']['throw']}",
          f"- Constantes: {c['constantes']['archivos_constants']} archivos *.constants · enums: {c['constantes']['enums']} · mensajes literales repetidos (>=3 veces): {c['constantes']['mensajes_repetidos_3+']} ({c['constantes']['ocurrencias_en_repetidos']} ocurrencias)"
          + "".join(f"\n  - «{t['texto']}» ×{t['veces']}" for t in c["constantes"]["top"]), ""]
    q = r["calidad"]
    L += ["## 4. Señales de calidad por módulo", "", f"> {LEYENDA}", "",
          f"Commits analizados (sin merges, tope {q['git']['tope']}): {q['git']['commits_analizados']}.", "",
          f"Mediana de %% de commits de arreglo, módulos CON vs SIN la práctica (solo módulos con >= {MIN_COMMITS} commits):".replace("%%", "%"), "",
          "| práctica | n con | n sin | mediana % arreglos con | mediana % arreglos sin |", "|---|---|---|---|---|"]
    for k, e in q["evidencia_por_practica"].items():
        L.append(f"| {k} | {e['n_con']} | {e['n_sin']} | {e['mediana_arreglos_con']} | {e['mediana_arreglos_sin']} |")
    mods = sorted([m for m in q["modulos"] if m["commits"] >= 5], key=lambda m: -(m["pct_arreglos"] or 0))[:10]
    L += ["", "Módulos con mayor % de arreglos (>= 5 commits):", "", "| módulo | estilo | commits | arreglos | % arreglos | churn | tamaño | churn/tamaño |", "|---|---|---|---|---|---|---|---|"]
    for m in mods:
        L.append(f"| {m['modulo']} | {m['estilo']} | {m['commits']} | {m['arreglos']} | {m['pct_arreglos']} | {m['churn']} | {m['tamano']} | {m['churn_sobre_tamano']} |")
    L += ["", f"_{LEYENDA}_", ""]
    return "\n".join(L)


def md_comparar(s):
    L = ["# Comparación de prácticas entre proyectos", "", f"> {LEYENDA}", "", "La herramienta SOLO propone; decide una persona (spec §13 paso 5).", ""]
    for st, d in s["stacks"].items():
        L += [f"## Stack {st}: {', '.join(d['proyectos'])}", "", "### Arquitectura dominante", ""] + [f"- {p}: {e}" for p, e in d["arquitectura"].items()] + [""]
        L += ["### Prácticas × proyectos (consistencia %)", "", "| práctica | " + " | ".join(d["proyectos"]) + " |", "|---|" + "---|" * len(d["proyectos"])]
        for k, vals in d["tabla"].items():
            L.append(f"| {k} | " + " | ".join("-" if vals.get(p) is None else str(vals[p]) for p in d["proyectos"]) + " |")
        L += ["", "### Divergencias (mismo stack, práctica distinta)", ""]
        L += [f"- **{x['practica']}**: " + "; ".join(f"{p}={v}" for p, v in x["valores"].items()) + (f" (brecha {x['brecha_pts']} pts)" if x["brecha_pts"] else "") for x in d["divergencias"]] or ["- ninguna >= 30 pts"]
        c = d["candidatos"]
        L += ["", "### Candidatos a estándar (propuesta; regla: mejor evidencia y menor complejidad)", "", "#### Alternativas por familia", ""]
        for f in c["familias"]:
            L += [f"**{f['familia']}** → propuesta: {f['propuesta'] or 'ninguna'} ({f['motivo']})", "", "| alternativa | módulos | con commits | mediana % arreglos | complejidad |", "|---|---|---|---|---|"]
            L += [f"| {x['alternativa']} | {x['modulos']} | {x['modulos_con_commits']} | {x['mediana_pct_arreglos']} | {x['complejidad']} |" for x in f["filas"]] + [""]
        L += ["#### Prácticas individuales", "", "| práctica | consistencia % | n con | n sin | mediana % arreglos con | sin | complejidad | lectura |", "|---|---|---|---|---|---|---|---|"]
        L += [f"| {x['practica']} | {x['consistencia_pct']} | {x['n_con']} | {x['n_sin']} | {x['mediana_arreglos_con']} | {x['mediana_arreglos_sin']} | {x['complejidad']} | {x['lectura']} |" for x in c["practicas"]]
        L += ["", f"_{LEYENDA}_", ""]
    return "\n".join(L)


# ------------------------------------------------------------------ CLI
def limpiar(o):
    if isinstance(o, dict): return {k: limpiar(v) for k, v in o.items() if k != "_unidades"}
    if isinstance(o, (list, tuple)): return [limpiar(x) for x in o]
    return o


def main(argv):
    if not argv or argv[0] in ("-h", "--help"): sys.exit(__doc__)
    formato = "json" if "--json" in argv else "md"
    salida = None
    if "--salida" in argv:
        i = argv.index("--salida"); salida = pathlib.Path(argv[i + 1]).expanduser().resolve(); del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--") or a == "--comparar"]
    comp = "--comparar" in args
    rutas = [a for a in args if a != "--comparar"]
    if not rutas: sys.exit(__doc__)
    if salida:
        for r in rutas:
            raiz = pathlib.Path(r).expanduser().resolve()
            if salida == raiz or raiz in salida.parents:
                sys.exit(f"Rechazado: no se escribe dentro del proyecto analizado ({raiz})")
    if comp:
        s = comparar(rutas); texto = json.dumps(s, ensure_ascii=False, indent=2, default=dict) if formato == "json" else md_comparar(s)
    else:
        r = analizar(rutas[0]); texto = json.dumps(limpiar(r), ensure_ascii=False, indent=2, default=dict) if formato == "json" else md_proyecto(r)
    if salida: salida.write_text(texto + "\n", encoding="utf8")
    else: print(texto)


if __name__ == "__main__":
    main(sys.argv[1:])
