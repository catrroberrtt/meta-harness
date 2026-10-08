#!/usr/bin/env python3
"""Modo `adopt` del instalador del meta harness (SOLO LECTURA): describe cómo es un proyecto sin tocarlo.

Cubre las ocho dimensiones del análisis completo: Desarrollo, QA, Técnica, Datos, Infraestructura y despliegue, Costos, Seguridad y
Documentación y gestión. Cada una sale con cuatro bloques: Detectado (con su evidencia), Falta, Propuesta (estándar del harness, proporcional
al tamaño) y Pregunta (solo lo que no se pudo detectar, indicando qué se intentó). No asume ambientes, puertos, cuentas ni ramas: los detecta
o los pregunta. De los archivos de entorno (.env*) solo lee NOMBRES de variables; de posibles credenciales solo informa archivo:línea y tipo.
Sin red, solo biblioteca estándar. No escribe nada dentro del proyecto.

Uso: python3 harness-detectar.py <carpeta-del-proyecto> [--md | --json] [--salida <archivo>]
  --salida: escribe el informe en ese archivo (se rechaza una ruta dentro del proyecto analizado); sin ella solo imprime.
"""
import argparse, ast, collections, json, os, pathlib, re, subprocess, sys

IGN = {"node_modules", ".git", "dist", ".angular", ".venv", "venv", "coverage", "__pycache__", ".next", "build", "target", ".terraform",
       "cdk.out", ".tox", ".mypy_cache", ".pytest_cache", ".gradle", "vendor", ".idea", ".nx", ".cache", "site-packages"}
EXT_COD = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".py", ".java", ".go", ".rb", ".php", ".cs", ".vue", ".kt", ".rs", ".swift", ".scala"}
MAX_ARCH, MAX_LEER = 40_000, 400_000


def analizar(root):
    ROOT = pathlib.Path(root).expanduser().resolve()

    def git(*a):
        try:
            return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception:
            return ""
    top = git("rev-parse", "--show-toplevel")
    es_git = bool(top) and pathlib.Path(top).resolve() == ROOT
    gg = git if es_git else (lambda *a: "")

    # ---- inventario (una sola pasada, sin seguir enlaces simbólicos)
    FILES, DIRS = [], []
    for dp, dn, fn in os.walk(ROOT, followlinks=False):
        dn[:] = sorted(d for d in dn if d not in IGN)
        rel = pathlib.Path(dp).relative_to(ROOT)
        for d in dn:
            DIRS.append(rel / d)
        for f in sorted(fn):
            FILES.append(rel / f)
        if len(FILES) > MAX_ARCH:
            break
    FS = {p.as_posix() for p in FILES}
    _c = {}

    def leer(p, n=MAX_LEER):
        k = (str(p), n)
        if k not in _c:
            try:
                _c[k] = (ROOT / p).read_text(encoding="utf8", errors="ignore")[:n]
            except Exception:
                _c[k] = ""
        return _c[k]

    def hay(*nombres):
        return [n for n in nombres if n in FS]

    def glob(rx):
        r = re.compile(rx)
        return [p.as_posix() for p in FILES if r.search(p.as_posix())]

    def en_raiz(rx):
        r = re.compile(rx)
        return [p.name for p in FILES if len(p.parts) == 1 and r.search(p.name)]

    R = {"proyecto": ROOT.name}
    # ---- git (el remoto se limpia de credenciales embebidas)
    remote = re.sub(r"//[^/@\s]+@", "//", gg("remote", "get-url", "origin"))
    ramas = [b.strip() for b in gg("branch", "-r", "--format=%(refname:short)").splitlines() if "HEAD" not in b]
    locales = [b.strip() for b in gg("branch", "--format=%(refname:short)").splitlines()]
    R["git"] = {"es_repositorio": es_git, "remote": remote or None, "ramas_remotas": len(ramas),
                "ramas_base": [b for b in ramas if re.search(r"/(main|master|dev|develop|qas|staging|prod)$", b)],
                "commits": int(gg("rev-list", "--count", "HEAD") or 0), "autores": len(set(gg("log", "--format=%ae", "-n", "500").splitlines())),
                "ultimo_commit": gg("log", "-1", "--format=%cs") or None}
    # ---- dependencias (Node, Python y otros) solo como nombres
    pkgs = [p for p in FILES if p.name == "package.json" and len(p.parts) <= 3]
    pkg, deps = {}, {}
    for p in pkgs:
        try:
            j = json.loads(leer(p))
        except Exception:
            continue
        if not pkg:
            pkg = j
        deps.update(j.get("dependencies", {})); deps.update(j.get("devDependencies", {}))
    py = set()
    reqs = [p for p in FILES if re.match(r"requirements.*\.txt$", p.name) and len(p.parts) <= 3]
    for p in reqs:
        for l in leer(p).splitlines():
            l = l.split("#")[0].strip()
            if l and not l.startswith("-"):
                py.add(re.split(r"[<>=!~\[; ]", l)[0].lower().replace("_", "-"))
    pyproj_txt = " ".join(leer(p) for p in FILES if p.name in ("pyproject.toml", "Pipfile", "setup.py", "setup.cfg") and len(p.parts) <= 2)
    for m in re.finditer(r"""["']([A-Za-z0-9_.-]+)\s*(?:[<>=!~\[;,].*?)?["']""", pyproj_txt):
        py.add(m.group(1).lower().replace("_", "-"))
    otros_txt = " ".join(leer(p) for p in FILES if p.name in ("pom.xml", "build.gradle", "go.mod", "Gemfile", "composer.json", "Cargo.toml") and len(p.parts) <= 2).lower()
    todo_dep = {d.lower() for d in deps} | py

    def tiene(*n):
        return [x for x in n if any(d == x or d.startswith(x) for d in todo_dep)]

    def tiene_txt(*n):
        return [x for x in n if x in otros_txt]
    stack = []
    for cond, nombre in ((tiene("@nestjs/core"), "NestJS"), (tiene("react"), "React"), (tiene("vue"), "Vue"), (tiene("express"), "Express"),
                         (tiene("typeorm"), "TypeORM"), (tiene("prisma", "@prisma/client"), "Prisma"), (tiene("mysql2", "mysql"), "MySQL"),
                         (tiene("pg"), "PostgreSQL"), (tiene("@angular/material"), "Angular Material"), (tiene("aws-cdk-lib"), "AWS CDK"),
                         (tiene("django"), "Django"), (tiene("flask"), "Flask"), (tiene("fastapi"), "FastAPI"), (tiene("odoo", "frappe", "erpnext"), "ERP Python")):
        if cond:
            stack.append(nombre)
    if "@angular/core" in deps:
        stack.insert(0, "Angular " + re.sub(r"^[^\d]*", "", deps["@angular/core"]).split(".")[0])
    for marca, nombre in (("pom.xml", "Java/Maven"), ("go.mod", "Go"), ("pyproject.toml", "Python"), ("requirements.txt", "Python"), ("Gemfile", "Ruby"), ("composer.json", "PHP"), ("Cargo.toml", "Rust")):
        if marca in FS and nombre not in stack:
            stack.append(nombre)
    if "Dockerfile" in FS:
        stack.append("Docker")
    pruebas = tiene("jest", "karma", "cypress", "vitest", "mocha", "playwright", "pytest", "phpunit")
    R["stack"] = {"lenguajes_y_marcos": stack, "node": pkg.get("engines", {}).get("node"), "scripts": sorted(pkg.get("scripts", {}))[:14], "pruebas": pruebas}
    src = ROOT / "src"
    srcdirs = sorted(p.name for p in src.iterdir() if p.is_dir()) if src.is_dir() else []
    migr_dirs = [d.as_posix() for d in DIRS if d.name in ("migrations", "migration", "migrate", "alembic")] + [d.as_posix() for d in DIRS if d.as_posix().endswith("alembic/versions")]
    migr_files = [p for p in FS if any(p.startswith(d + "/") for d in migr_dirs) and not p.endswith(("/__init__.py", ".md"))]
    tests_n = len([p for p in FS if re.search(r"(\.spec\.|\.test\.|(^|/)test_[^/]*\.py$|_test\.(py|go)$|Test\.java$)", p)])
    R["estructura"] = {"raiz": sorted(p.name + ("/" if (ROOT / p.name).is_dir() else "") for p in ROOT.iterdir() if p.name not in IGN and not p.name.startswith("."))[:25],
                       "src": srcdirs[:20], "modulos_por_feature": len(list((src / "modules").glob("*"))) if (src / "modules").is_dir() else 0,
                       "migraciones": len(migr_files), "archivos_de_prueba": tests_n}
    wf = sorted(p.name for p in (ROOT / ".github/workflows").glob("*.y*ml")) if (ROOT / ".github/workflows").is_dir() else []
    ci_otro = [n for n in (".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml", "bitbucket-pipelines.yml", ".circleci/config.yml") if n in FS]
    R["ci"] = {"github_actions": wf, "otro": ci_otro}
    msgs = gg("log", "-n", "200", "--format=%s").splitlines()
    conv = sum(bool(re.match(r"^(feat|fix|chore|docs|refactor|test|perf|build|ci|style)(\([^)]+\))?!?:", m)) for m in msgs)
    claves = collections.Counter(re.findall(r"\b([A-Z][A-Z0-9]{1,6})-\d+\b", " ".join(msgs)))
    plant = [p for p in FS if re.match(r"(\.github/)?(pull_request_template|PULL_REQUEST_TEMPLATE)", p, re.I) or p.lower().startswith(".github/pull_request_template")]
    fmt = [n for n in (".prettierrc", ".prettierrc.json", ".eslintrc.js", ".eslintrc.json", ".eslintrc.cjs", "eslint.config.js", "eslint.config.mjs", ".editorconfig", ".husky",
                       ".flake8", ".pylintrc", "ruff.toml", ".ruff.toml", "mypy.ini", ".pre-commit-config.yaml", ".rubocop.yml", ".golangci.yml", "phpstan.neon", "biome.json") if n in FS or (ROOT / n).exists()]
    R["convenciones"] = {"commits_convencionales_pct": round(100 * conv / len(msgs)) if msgs else None, "claves_de_ticket_en_commits": dict(claves.most_common(4)),
                         "prefijos_de_rama": dict(collections.Counter(re.sub(r"^origin/", "", b).split("/")[0] for b in ramas if "/" in b.replace("origin/", "", 1)).most_common(6)),
                         "plantilla_de_pr": plant or None, "contributing": "CONTRIBUTING.md" in FS, "formato_y_calidad": fmt}
    mds = [p for p in FILES if p.suffix.lower() == ".md"]
    texto_docs = " ".join(leer(p, 30_000) for p in mds[:60]) + leer("package.json")
    R["documentacion"] = {"markdown": len(mds), "readme": "README.md" in FS, "docs_dir": (ROOT / "docs").is_dir(), "adr": len([p for p in mds if re.search(r"adr|decision", p.name, re.I)]),
                          "openapi_swagger": bool(tiene("@nestjs/swagger", "swagger-ui-express", "drf-spectacular", "flasgger")) or bool(glob(r"(^|/)openapi[^/]*\.ya?ml$")),
                          "enlaces_a": sorted({d for d in ("atlassian.net", "confluence", "notion.so", "drive.google.com", "linear.app", "trello.com", "github.com/orgs") if d in texto_docs})}
    R["entorno_ia"] = {"CLAUDE.md": "CLAUDE.md" in FS, ".claude": (ROOT / ".claude").is_dir(), "codegraph": (ROOT / ".codegraph").is_dir(), "plan_files": len([p for p in FS if re.match(r"PLAN-[^/]*\.md$", p)])}
    perfiles = [p for s, p in (("NestJS", "nestjs-typeorm-mysql"), ("Angular", "angular-material"), ("AWS CDK", "aws-ecs")) if any(s in x for x in stack)]
    enl = R["documentacion"]["enlaces_a"]
    R["propuesta"] = {"perfiles": perfiles or ["(ninguno de los tres iniciales: habría que crear uno)"],
                      "tickets": "jira" if any("atlassian" in e for e in enl) or claves else "github-issues o ninguno (preguntar)",
                      "documentacion": "confluence" if any(e in enl for e in ("atlassian.net", "confluence")) else ("drive-md" if "drive.google.com" in enl else ("carpeta docs/ del repositorio" if R["documentacion"]["docs_dir"] else "falta: pedir una carpeta de Drive o el análisis en .md")),
                      "convenciones": ("heredar las vigentes: commits convencionales" + (" y la plantilla de PR" if plant else "; no hay plantilla de PR (se propone la del harness)")) if (msgs and conv / len(msgs) >= 0.6) else "adoptar el estándar del harness y confirmarlo con el equipo",
                      "modo": "adopt" if R["git"]["commits"] > 20 else "init"}

    # ---- tamaño del proyecto (S/M/L), para que las propuestas sean proporcionales
    codigo = [p for p in FILES if p.suffix in EXT_COD and not re.search(r"(\.spec\.|\.test\.|(^|/)tests?/|__tests__)", p.as_posix())]
    escala = "S" if len(codigo) < 60 else ("M" if len(codigo) < 400 else "L")
    R["escala"] = {"nivel": escala, "archivos_de_codigo": len(codigo), "criterio": "S < 60 archivos de código, M < 400, L el resto"}

    # ---- utilidades de las dimensiones
    def nueva(n, nombre):
        return {"n": n, "nombre": nombre, "detectado": [], "falta": [], "propuesta": [], "pregunta": []}

    def det(d, h, ev):
        d["detectado"].append({"hallazgo": h, "evidencia": ev if isinstance(ev, str) else ", ".join(ev)})

    def falta(d, t):
        d["falta"].append(t)

    def prop(d, t):
        d["propuesta"].append(t)

    def preg(d, q, intento):
        assert intento, "toda pregunta debe decir qué se intentó"
        d["pregunta"].append({"pregunta": q, "intento": intento})

    def corto(l, n=4):
        l = list(l)
        return ", ".join(l[:n]) + (f" (+{len(l) - n})" if len(l) > n else "")

    # ---- nombres de variables de entorno (NUNCA valores)
    envfiles = [p.as_posix() for p in FILES if re.match(r"\.env($|\.)", p.name) or p.name.endswith(".env")]
    envfiles_reales = [p for p in envfiles if not re.search(r"(example|sample|template|dist|default)", p, re.I)]
    NOMBRE_VAR = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", re.M)
    var_origen = collections.defaultdict(set)   # NOMBRE -> archivos
    for p in envfiles:
        for m in NOMBRE_VAR.finditer(leer(p, 100_000)):
            var_origen[m.group(1)].add(p)
    composes = [p.as_posix() for p in FILES if re.match(r"(docker-)?compose[^/]*\.ya?ml$", p.name)]
    for p in composes:
        for m in re.finditer(r"^\s*(?:-\s*)?([A-Z][A-Z0-9_]{2,})\s*[:=]", leer(p), re.M):
            var_origen[m.group(1)].add(p)
    wfpaths = [p for p in FS if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml"))]
    for p in wfpaths:
        for m in re.finditer(r"(?:secrets|vars)\.([A-Z][A-Z0-9_]+)", leer(p)):
            var_origen[m.group(1)].add(p)
    for p in [x for x in FILES if x.suffix in EXT_COD][:2500]:
        t = leer(p, 120_000)
        for m in re.finditer(r"process\.env\.([A-Z][A-Z0-9_]+)|os\.environ(?:\.get)?[\[(]\s*['\"]([A-Z][A-Z0-9_]+)|getenv\(\s*['\"]([A-Z][A-Z0-9_]+)|env\(\s*['\"]([A-Z][A-Z0-9_]+)", t):
            var_origen[next(g for g in m.groups() if g)].add(p.as_posix())
    for p in FILES:
        if p.name == "Dockerfile" or p.name.startswith("Dockerfile."):
            for m in re.finditer(r"^\s*(?:ENV|ARG)\s+([A-Z][A-Z0-9_]+)", leer(p), re.M):
                var_origen[m.group(1)].add(p.as_posix())
    VARS = sorted(var_origen)

    def vars_como(rx):
        r = re.compile(rx)
        return [v for v in VARS if r.search(v)]

    def origen(v):
        return sorted(var_origen[v])[0]

    # ---- 1. Desarrollo
    D1 = nueva(1, "Desarrollo")
    if stack:
        det(D1, "Stack: " + ", ".join(stack), [m for m in ("package.json", "requirements.txt", "pyproject.toml", "pom.xml", "go.mod", "Gemfile", "composer.json", "Cargo.toml") if m in FS] or "dependencias")
    else:
        falta(D1, "No se reconoce el stack (sin manifiestos de dependencias)")
        preg(D1, "¿Qué lenguaje y marco usa el proyecto?", "Se buscaron package.json, requirements.txt, pyproject.toml, pom.xml, go.mod, Gemfile, composer.json y Cargo.toml sin éxito")
    if R["estructura"]["raiz"]:
        det(D1, "Estructura raíz: " + corto(R["estructura"]["raiz"], 8) + f" · escala {escala} ({len(codigo)} archivos de código)", "listado de la carpeta")
    if es_git:
        det(D1, f"{R['git']['commits']} commits, {R['git']['autores']} autores, último {R['git']['ultimo_commit']}", "git log")
        if msgs and conv / len(msgs) >= 0.6:
            det(D1, f"Commits convencionales ({R['convenciones']['commits_convencionales_pct']} % de los últimos {len(msgs)})", "git log -n 200")
        elif msgs:
            falta(D1, f"Los commits no siguen un formato uniforme ({R['convenciones']['commits_convencionales_pct']} % convencionales)")
            prop(D1, "Adoptar commits convencionales (feat/fix/docs...) con un chequeo en CI o en el hook de commit")
        pre = R["convenciones"]["prefijos_de_rama"]
        if pre:
            det(D1, "Prefijos de rama en uso: " + ", ".join(f"{k} ({v})" for k, v in pre.items()), "git branch -r")
        merges = len([m for m in gg("log", "-n", "300", "--merges", "--format=%s").splitlines() if re.match(r"Merge (pull request|branch|remote)", m)])
        if merges:
            det(D1, f"Flujo con ramas y fusiones ({merges} fusiones en los últimos 300 commits)", "git log --merges")
    else:
        falta(D1, "La carpeta no es un repositorio git (sin historial: no se pueden inferir commits ni ramas)")
        prop(D1, "Iniciar el control de versiones y adoptar el flujo de ramas del harness (rama base + ramas de trabajo con PR)")
    if wf or ci_otro:
        det(D1, "CI: " + corto(wf + ci_otro), [".github/workflows" if wf else ci_otro[0]])
    else:
        falta(D1, "No hay integración continua (ni GitHub Actions ni otro CI)")
        prop(D1, {"S": "Un workflow único que instale, pruebe y compile", "M": "Workflow de pruebas + lint en cada PR", "L": "Pipeline por etapas (lint, pruebas, compilación, escaneo) con caché"}[escala])
    if plant:
        det(D1, "Plantilla de PR", plant)
    else:
        falta(D1, "No hay plantilla de PR")
        prop(D1, "Usar la plantilla de PR del harness (qué, por qué, cómo se probó)")
    if fmt:
        det(D1, "Formato/calidad de código: " + ", ".join(fmt), fmt)
    else:
        falta(D1, "Sin formateador ni linter configurado")
        prop(D1, "Configurar el formateador y linter estándar del stack y correrlo en CI")
    if "CONTRIBUTING.md" in FS:
        det(D1, "Guía de contribución", "CONTRIBUTING.md")
    cod = [p for p in FS if p.endswith("CODEOWNERS")]
    if not plant and not cod:
        preg(D1, "¿Cómo se revisa el código antes de integrarlo (revisor obligatorio, pareja, ninguno)?",
             "Se buscaron plantilla de PR, CODEOWNERS y fusiones de PR en el historial; la protección real de ramas solo se ve en el servidor de git, que no se consulta")
    elif es_git and not ramas:
        preg(D1, "¿Cuál es la rama base y cómo se protege?", "Hay historial local pero ninguna rama remota registrada; la protección solo se ve en el servidor de git")

    # ---- 2. QA
    D2 = nueva(2, "QA")
    marcos = []
    cfgs = {"cypress": r"(^|/)cypress\.config\.|(^|/)cypress/", "playwright": r"(^|/)playwright\.config\.", "jest": r"(^|/)jest\.config\.",
            "karma": r"(^|/)karma\.conf\.", "vitest": r"(^|/)vitest\.config\.", "pytest": r"(^|/)(pytest\.ini|conftest\.py|tox\.ini)$", "phpunit": r"(^|/)phpunit\.xml"}
    for m, rx in cfgs.items():
        ev = glob(rx)[:2]
        dd = tiene(m)
        if ev or dd:
            marcos.append(m)
            det(D2, f"Marco de pruebas: {m}", ev or [f"dependencia {dd[0]}"])
    if "pytest" not in marcos and any(re.search(r"(^|/)test_[^/]*\.py$", p) for p in FS):
        det(D2, "Pruebas en Python (test_*.py), marco no declarado", glob(r"(^|/)test_[^/]*\.py$")[:2])
    if tests_n:
        det(D2, f"{tests_n} archivos de prueba", "*.spec.* / *.test.* / test_*.py")
    elif not marcos:
        falta(D2, "No hay archivos de prueba")
    carp = sorted({d.as_posix() for d in DIRS if d.name in ("e2e", "qa", "cypress", "integration", "tests", "test", "__tests__", "features")})
    if carp:
        det(D2, "Carpetas de pruebas/QA: " + corto(carp), carp[:3])
    sib = []
    try:
        partes = {t for t in re.split(r"[-_]", ROOT.name.lower()) if t not in ("api", "st", "fn", "infra", "cloud", "app", "web", "qa", "front", "back")}
        sib = sorted(p.name for p in ROOT.parent.iterdir() if p.is_dir() and p.name.lower().startswith("qa-") and p.name != ROOT.name
                     and partes & set(re.split(r"[-_]", p.name.lower()))) if partes else []
    except Exception:
        pass
    if sib:
        det(D2, "Posible repositorio de QA hermano (por nombre): " + corto(sib), "carpetas vecinas qa-*")
    cobertura = [e for e in (glob(r"(^|/)(\.nycrc[^/]*|\.coveragerc|codecov\.ya?ml|\.codecov\.ya?ml)$")[:2]) ]
    cfg_txt = " ".join(leer(p) for p in glob(r"(^|/)(jest\.config\.[^/]+|karma\.conf\.[^/]+|pytest\.ini|tox\.ini|setup\.cfg|pyproject\.toml|package\.json)$")[:12])
    if re.search(r"coverageThreshold|collectCoverage|--cov|coverage\.report|karma-coverage|\"test:cov|\"coverage\"|\bcov-report|fail_under", cfg_txt):
        cobertura.append("configuración de pruebas")
    if cobertura:
        det(D2, "Cobertura configurada", cobertura)
    elif tests_n:
        falta(D2, "Hay pruebas pero no se mide la cobertura")
        prop(D2, "Activar el reporte de cobertura del marco y fijar un umbral mínimo realista (subirlo con el tiempo)")
    feats = glob(r"\.feature$")
    plts = glob(r"(?i)(^|/)(\.github/ISSUE_TEMPLATE/[^/]+|[^/]*(caso|test[-_ ]?case|plantilla)[^/]*(prueba|test|qa|caso)[^/]*\.(md|ya?ml)|[^/]*test[-_ ]?case[^/]*\.md)$")
    if feats:
        det(D2, f"{len(feats)} escenarios Gherkin (.feature)", feats[:2])
    if plts:
        det(D2, "Plantillas de caso de prueba / issue", plts[:3])
    if marcos and not tests_n:
        falta(D2, "Hay marco de pruebas configurado pero ningún archivo de prueba")
        prop(D2, "Escribir primero la prueba de los flujos críticos; sin ellas el marco no protege nada")
    if not (marcos or tests_n):
        falta(D2, "No hay pruebas automáticas de ningún tipo")
        prop(D2, {"S": "Un marco de pruebas unitarias del stack y una prueba por flujo crítico", "M": "Pruebas unitarias por servicio + una E2E de humo", "L": "Pirámide completa: unitarias, integración y E2E en un repositorio o carpeta de QA"}[escala])
    elif not (set(marcos) & {"cypress", "playwright"}) and not carp and not sib and escala != "S":
        falta(D2, "No se ven pruebas E2E ni carpeta/repositorio de QA")
        prop(D2, "Una suite E2E mínima de los flujos críticos (Playwright/Cypress según el stack)")
    if not plts:
        falta(D2, "No hay plantilla de caso de prueba ni de observación de QA")
        prop(D2, "Usar la plantilla de observación de QA del harness (pasos, esperado, obtenido, evidencia)")
    preg(D2, "¿Existe un proceso de QA manual y quién da la aceptación? ¿Dónde se registran las observaciones?",
         "Se buscaron marcos de pruebas, carpetas e2e/qa, repositorios vecinos qa-*, plantillas de caso e issues; el proceso humano no deja rastro en el código")
    if not feats and not re.search(r"(?i)criterios? de aceptaci|acceptance criteria|given .* when", " ".join(leer(p, 20000) for p in mds[:40])):
        preg(D2, "¿Cómo se redactan los criterios de aceptación (Gherkin, lista en el ticket, otro)?", "Se buscaron archivos .feature y la frase «criterios de aceptación» en los .md; no aparecen")

    # ---- 3. Técnica
    D3 = nueva(3, "Técnica")
    grandes, lineas_tot = [], 0
    for p in codigo[:6000]:
        try:
            n = leer(p, 2_000_000).count("\n") + 1
        except Exception:
            n = 0
        lineas_tot += n
        if n > 400:
            grandes.append((n, p.as_posix()))
    grandes.sort(reverse=True)
    if codigo:
        det(D3, f"{len(codigo)} archivos de código, ~{lineas_tot} líneas; {len(grandes)} pasan de 400 líneas", [f"{p} ({n})" for n, p in grandes[:3]] or "recuento de líneas")
        if grandes:
            falta(D3, f"{len(grandes)} archivos superan 400 líneas")
            prop(D3, "Partir los archivos de más de 400 líneas por responsabilidad y fijar el límite en el linter")
    else:
        falta(D3, "No hay archivos de código que medir")
    largas = []
    for p in codigo:
        if p.suffix == ".py":
            try:
                for nd in ast.walk(ast.parse(leer(p, 1_000_000))):
                    if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef)) and (nd.end_lineno - nd.lineno) > 60:
                        largas.append(f"{p.as_posix()}:{nd.lineno}")
            except Exception:
                pass
    if largas:
        det(D3, f"{len(largas)} funciones Python de más de 60 líneas", largas[:3])
        falta(D3, "Funciones largas en Python")
        prop(D3, "Extraer funciones de más de 60 líneas; límite de complejidad en el linter")
    elif any(p.suffix in EXT_COD and p.suffix != ".py" for p in codigo):
        det(D3, "Tamaño de funciones: solo se mide en Python (límite del detector); en los demás lenguajes solo el tamaño de archivo", "análisis estático ligero")
    feat_mod = len(glob(r"\.module\.ts$"))
    capas = sorted({d.name for d in DIRS if d.name in ("controllers", "services", "repositories", "entities", "models", "views", "handlers", "routes", "dto", "dtos")})
    feat_dirs = len(list((src / "modules").glob("*"))) if (src / "modules").is_dir() else 0
    feat_dirs = max(feat_dirs, len([d for d in DIRS if len(d.parts) == 3 and d.parts[:2] == ("src", "app") and d.name not in ("shared", "core", "common", "layout")]) if "@angular/core" in deps else 0)
    if feat_dirs >= 3 or feat_mod >= 3:
        det(D3, f"Organización por feature/módulo ({max(feat_dirs, feat_mod)} módulos)", ["src/modules" if (src / "modules").is_dir() else ("src/app/*" if "@angular/core" in deps else "*.module.ts")])
    if len(capas) >= 3:
        det(D3, "Organización por capas técnicas: " + ", ".join(capas), "carpetas con ese nombre")
    if codigo and not (feat_dirs >= 3 or feat_mod >= 3 or len(capas) >= 3):
        falta(D3, "No se distingue una arquitectura (ni por feature ni por capas)")
        prop(D3, "Adoptar la estructura estándar del perfil del stack (por feature, con controlador → servicio → repositorio)" if escala != "S" else "Mantener una estructura plana por responsabilidad; no introducir capas hasta que haga falta")
    lint = [n for n in fmt if re.search(r"eslint|flake8|pylint|ruff|golangci|rubocop|phpstan|biome|mypy", n)] + [p for p in glob(r"(^|/)(sonar-project\.properties|checkstyle[^/]*\.xml|\.stylelintrc[^/]*)$")[:2]]
    if "tool.ruff" in pyproj_txt or "tool.mypy" in pyproj_txt or "tool.pylint" in pyproj_txt:
        lint.append("pyproject.toml [tool.*]")
    if "eslintConfig" in pkg:
        lint.append("package.json eslintConfig")
    lint_dep = tiene("eslint", "tslint", "@angular-eslint", "@typescript-eslint", "biome", "flake8", "pylint", "ruff", "mypy")
    if lint:
        det(D3, "Linters configurados", lint)
    elif lint_dep:
        det(D3, "Linter en dependencias, sin archivo de configuración visible en la raíz", "dependencia " + lint_dep[0])
    elif codigo:
        falta(D3, "Sin linter estático configurado")
        prop(D3, "Configurar el linter estándar del stack con el mismo conjunto de reglas en local y en CI")
    ts_cfg = [p for p in glob(r"(^|/)tsconfig[^/]*\.json$") if p.count("/") <= 2]
    if ts_cfg:
        estrictos = [p for p in ts_cfg if re.search(r'"strict"\s*:\s*true', leer(p))]
        if estrictos:
            det(D3, "TypeScript en modo estricto", estrictos[:2])
        else:
            falta(D3, "TypeScript sin `strict: true`")
            prop(D3, "Activar `strict` por etapas (primero en archivos nuevos)")
    if "mypy.ini" in FS or "tool.mypy" in pyproj_txt:
        det(D3, "Tipos Python con mypy", "mypy.ini / pyproject.toml")
    tot = len(deps) + len([x for x in py if x])
    if tot:
        malas = [k for k, v in deps.items() if re.match(r"^[\^~]?0\.", str(v))]
        mayores = {k: re.sub(r"^[^\d]*", "", str(deps[k])).split(".")[0] for k in ("@angular/core", "@nestjs/core", "react", "typescript", "typeorm", "jest") if k in deps}
        lockf = hay("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Pipfile.lock", "uv.lock")
        det(D3, f"{tot} dependencias declaradas ({len(deps)} Node, {len(py)} Python); versiones mayores: " + (", ".join(f"{k} {v}" for k, v in mayores.items()) or "n/d") + (f"; {len(malas)} en versión 0.x" if malas else ""), lockf or "manifiestos")
        if not lockf and (deps or py):
            falta(D3, "No hay archivo de bloqueo de versiones (lock)")
            prop(D3, "Versionar el lock para builds reproducibles")
        det(D3, "Cuáles están desactualizadas no se puede saber sin red (límite del detector)", "sin consulta a registros")
        prop(D3, "Programar la revisión de desactualizadas en CI (`npm outdated`/`pip list --outdated`) o con un bot de actualización")
    if not (tiene("k6", "artillery", "locust") or glob(r"(?i)(k6|artillery|locust|jmeter)")):
        preg(D3, "¿Hay requisitos de rendimiento o carga esperada (usuarios, tiempos, volumen)?", "Se buscaron pruebas de carga (k6, artillery, locust, jmeter) en dependencias y archivos; no hay forma de inferirlo del código")

    # ---- 4. Datos
    D4 = nueva(4, "Datos")
    motores = {"MySQL": ("mysql", "mysql2", "pymysql", "mysqlclient", "mysql-connector-python"), "MariaDB": ("mariadb",), "PostgreSQL": ("pg", "postgres", "psycopg2", "psycopg2-binary", "psycopg", "asyncpg", "pg8000"),
               "MongoDB": ("mongodb", "mongoose", "pymongo", "motor"), "Redis": ("redis", "ioredis"), "SQLite": ("sqlite3", "better-sqlite3", "aiosqlite"), "SQL Server": ("mssql", "tedious", "pyodbc"),
               "Oracle": ("oracledb",), "DynamoDB": ("@aws-sdk/client-dynamodb", "boto3-dynamodb", "dynamodb")}
    enc = {}
    for mot, ns in motores.items():
        h = [n for n in ns if n in todo_dep]
        if h:
            enc[mot] = f"dependencia {h[0]}"
    img = {}
    for p in composes:
        for m in re.finditer(r"image:\s*['\"]?([^\s'\"]+)", leer(p)):
            nm = m.group(1).split("/")[-1].split(":")[0].lower()
            for mot, k in (("MySQL", "mysql"), ("MariaDB", "mariadb"), ("PostgreSQL", "postgres"), ("MongoDB", "mongo"), ("Redis", "redis"), ("SQL Server", "mssql"), ("MySQL", "percona")):
                if k in nm:
                    img.setdefault(mot, p)
    for mot, p in img.items():
        enc[mot] = enc.get(mot, "") + ("; " if mot in enc else "") + f"imagen en {p}"
    for mot, ev in enc.items():
        det(D4, f"Motor: {mot}", ev)
    orms = [n for n, ds in (("TypeORM", ("typeorm",)), ("Prisma", ("prisma", "@prisma/client")), ("Sequelize", ("sequelize",)), ("MikroORM", ("@mikro-orm/core",)), ("Knex", ("knex",)), ("Mongoose", ("mongoose",)),
                            ("SQLAlchemy", ("sqlalchemy",)), ("Django ORM", ("django",)), ("Alembic", ("alembic",)), ("Peewee", ("peewee",)), ("Tortoise", ("tortoise-orm",)), ("Eloquent", ("laravel/framework",))) if any(x in todo_dep for x in ds)]
    if "hibernate" in otros_txt or "spring-data" in otros_txt: orms.append("Hibernate/Spring Data")
    if "gorm" in otros_txt: orms.append("GORM")
    if orms:
        det(D4, "ORM/acceso a datos: " + ", ".join(orms), "dependencias")
    elif enc:
        falta(D4, "Hay motor de base de datos pero no se ve ORM ni capa de acceso declarada")
    if migr_dirs or "prisma" in " ".join(FS):
        det(D4, f"{len(migr_files)} archivos de migración", migr_dirs[:2] or "prisma/migrations")
    elif enc or orms:
        falta(D4, "Hay base de datos pero no hay carpeta de migraciones")
        prop(D4, "Versionar cada cambio de esquema como migración (la herramienta del ORM) y revisarla en el PR")
    semillas = [p for p in FS if re.search(r"(?i)(^|/)(seeds?|seeders?|fixtures?)(/|\.)|(^|/)seed[^/]*\.(ts|js|py|sql)$", p)]
    if semillas:
        det(D4, f"Semillas/fixtures ({len(semillas)} archivos)", semillas[:2])
    elif enc:
        falta(D4, "No hay semillas ni datos de prueba reproducibles")
        prop(D4, "Un script de semillas con datos sintéticos para levantar el entorno local desde cero")
    if envfiles:
        nombres_db = sorted(v for v in VARS if re.search(r"(DB|DATABASE|MYSQL|POSTGRES|PG|MONGO|REDIS|SQL)", v))
        if nombres_db:
            det(D4, "Variables de conexión a base de datos (solo nombres): " + corto(nombres_db, 8), sorted({o for v in nombres_db for o in var_origen[v]})[:3])
    nombres_db = sorted(v for v in VARS if re.search(r"(DB|DATABASE|MYSQL|POSTGRES|MONGO|REDIS|SQL)", v))
    if nombres_db and not envfiles:
        det(D4, "Variables de conexión a base de datos (solo nombres): " + corto(nombres_db, 8), origen(nombres_db[0]))
    ENVWORDS = r"(?:^|[/_.-])(dev|develop|development|qa|qas|test|testing|staging|stage|uat|preprod|prod|production|main|master|sandbox|demo|local)(?:$|[/_.-])"
    amb = collections.defaultdict(set)
    for b in set(ramas) | set(locales):
        n = re.sub(r"^origin/", "", b)
        m = re.fullmatch(r"(dev|develop|development|qa|qas|test|testing|staging|stage|uat|preprod|pre-prod|prod|production|main|master|sandbox|demo)", n)
        if m:
            amb[m.group(1)].add(f"rama {n}")
    for p in envfiles + glob(r"(environment|config|settings)[^/]*\.(prod|production|dev|development|staging|qa|qas|test|uat)\.[a-z]+$"):
        m = re.search(r"[._-](prod|production|dev|development|staging|stage|qa|qas|test|uat|local)(?:[._-]|$)", pathlib.PurePosixPath(p).name)
        if m:
            amb[m.group(1)].add(f"archivo {p}")
    wf_info = {}
    for p in wfpaths:
        t = leer(p)
        envs = sorted((set(re.findall(r"^\s*environment:[ \t]*['\"]?([A-Za-z0-9_-]+)['\"]?[ \t]*(?:#.*)?$", t, re.M)) | set(re.findall(r"environment:[ \t]*\n\s+name:[ \t]*['\"]?([A-Za-z0-9_-]+)", t))) - {"description", "type", "required", "default", "options"})
        brs = set(re.findall(r"branches:\s*\[([^\]]*)\]", t))
        brs = {b.strip(" '\"") for x in brs for b in x.split(",") if b.strip()} | set(re.findall(r"^\s*-\s*['\"]?([A-Za-z0-9_./*-]+)['\"]?\s*$", "\n".join(re.findall(r"branches:\s*\n((?:\s+-\s*\S+\n?)+)", t)), re.M))
        wf_info[p] = {"ambientes": envs, "ramas": sorted(brs), "texto": t}
        for e in envs:
            amb[e].add(f"environment en {p}")
    if amb:
        det(D4, "Ambientes inferidos: " + ", ".join(sorted(amb)), sorted({next(iter(v)) for v in amb.values()})[:4])
    else:
        falta(D4, "No se infieren ambientes (sin ramas por ambiente, archivos .env.<ambiente> ni ambientes en workflows)")
    solo_front = bool(tiene("@angular/core", "react", "vue", "svelte")) and not (tiene("@nestjs/core", "express", "fastify", "koa", "next") or py or enc or orms)
    if solo_front:
        det(D4, "Proyecto de interfaz: sin motor ni ORM propios (consume una API)", "dependencias de frontend sin motor ni ORM")
    else:
      preg(D4, "¿Quién puede escribir en qué base de datos y ambiente (permisos, accesos, política de datos productivos)?",
           "Se revisaron .env*, docker-compose, workflows y variables de conexión (solo nombres); los permisos reales viven en el motor y en la nube, que no se consultan")
    if not (enc or orms) and not solo_front:
        preg(D4, "¿El proyecto usa base de datos o almacenamiento persistente? ¿cuál?", "Se buscaron dependencias de motores, imágenes de compose y ORMs; no aparece ninguno")

    # ---- 5. Infraestructura y despliegue
    D5 = nueva(5, "Infraestructura y despliegue")
    dock = [p.as_posix() for p in FILES if p.name == "Dockerfile" or p.name.startswith("Dockerfile.")]
    if dock:
        det(D5, f"Contenedor: {len(dock)} Dockerfile", dock[:3])
    if composes:
        det(D5, "docker-compose", composes[:3])
    iac = []
    for etiqueta, ev in (("Terraform", glob(r"\.tf$")), ("AWS CDK", hay("cdk.json") + (["dependencia aws-cdk-lib"] if "aws-cdk-lib" in deps else [])), ("Pulumi", glob(r"(^|/)Pulumi\.ya?ml$")),
                         ("Serverless Framework", glob(r"(^|/)serverless\.(ya?ml|ts)$")), ("AWS SAM", glob(r"(^|/)(samconfig\.toml|template\.ya?ml)$")),
                         ("Helm", glob(r"(^|/)Chart\.ya?ml$")), ("Kubernetes", [p for p in FS if p.endswith((".yaml", ".yml")) and re.search(r"^kind:\s*(Deployment|StatefulSet|Service|Ingress)\b", leer(p, 20_000), re.M)])):
        if ev:
            iac.append(etiqueta)
            det(D5, f"Infraestructura como código: {etiqueta}", ev[:2])
    cfn = [p for p in FS if p.endswith((".yaml", ".yml", ".json", ".template")) and "AWSTemplateFormatVersion" in leer(p, 5000)]
    if cfn:
        iac.append("CloudFormation"); det(D5, "Infraestructura como código: CloudFormation", cfn[:2])
    DEPLOY = re.compile(r"cdk deploy|terraform apply|serverless deploy|sls deploy|kubectl|helm (upgrade|install)|aws ecs|aws lambda update|docker push|sam deploy|pulumi up|rsync|scp |deploy", re.I)
    desp = {p: i for p, i in wf_info.items() if DEPLOY.search(i["texto"])}
    for p, i in desp.items():
        det(D5, f"Workflow de despliegue (ambientes: {', '.join(i['ambientes']) or 'no declarados'}; ramas: {', '.join(i['ramas']) or 'no declaradas'})", p)
    if not desp and not iac and not dock:
        falta(D5, "No hay rastro de infraestructura ni de despliegue (sin Docker, IaC ni workflows de despliegue)")
        prop(D5, {"S": "Documentar en el README cómo se despliega; automatizar solo si el despliegue es frecuente", "M": "Dockerfile + un workflow de despliegue por ambiente", "L": "Infraestructura como código y pipeline de despliegue por ambiente con aprobación"}[escala])
    else:
        if not iac and (desp or dock):
            falta(D5, "No se ve infraestructura como código")
            prop(D5, "Describir la infraestructura como código (la herramienta que ya use el equipo) antes de añadir ambientes")
        if not desp:
            falta(D5, "No hay workflow de despliegue automatizado")
            prop(D5, "Un workflow de despliegue por ambiente, disparado por la rama o etiqueta de ese ambiente")
    cuentas = vars_como(r"(ACCOUNT|REGION|SUBSCRIPTION|TENANT|PROJECT_ID|CLUSTER)")
    if cuentas:
        det(D5, "Cuentas/regiones como variables (solo nombres): " + corto(cuentas, 6), origen(cuentas[0]))
    rev = [p for p in FS if (p.endswith((".md", ".yml", ".yaml", ".tf", ".sh")) or ("AWS CDK" in iac and p.endswith(".ts") and p.split("/")[0] in ("bin", "lib", "infra"))) and re.search(r"(?i)rollback|revertir|reversi[oó]n|blue[/-]green|canary|previous (task|version|image)", leer(p, 40_000))]
    if rev:
        det(D5, "Estrategia de reversión mencionada", rev[:3])
    elif desp or iac:
        falta(D5, "No se menciona estrategia de reversión")
        prop(D5, "Documentar y probar la reversión (volver a la imagen/versión anterior) antes del primer despliegue serio")
    if (desp or iac) and not cuentas:
        preg(D5, "¿Qué cuentas/proyectos de nube y regiones corresponden a cada ambiente?", "Se buscaron variables con ACCOUNT/REGION/SUBSCRIPTION/PROJECT_ID en .env*, compose, Dockerfile, workflows y código; no aparecen")
    if not desp:
        preg(D5, "¿Cómo se despliega hoy (manual, script, plataforma externa)?", "Se buscaron workflows con comandos de despliegue, Dockerfile, IaC y otros CI; no hay rastro")
    elif not rev:
        preg(D5, "¿Cómo se revierte un despliegue fallido?", "Se buscó «rollback», «revertir», blue/green y canary en docs, workflows e IaC; sin resultados")

    # ---- 6. Costos
    D6 = nueva(6, "Costos")
    PAGO = {"Nube (SDK)": ("aws-sdk", "@aws-sdk/", "boto3", "botocore", "@google-cloud/", "google-cloud-", "@azure/", "azure-"),
            "IA": ("openai", "@anthropic-ai/sdk", "anthropic", "@google/generative-ai", "cohere", "langchain", "replicate", "huggingface"),
            "Pagos": ("stripe", "paypal", "mercadopago", "culqi", "@paypal", "braintree", "adyen", "razorpay"),
            "Correo/SMS": ("@sendgrid/", "sendgrid", "mailgun", "mailchimp", "@mailchimp", "twilio", "nodemailer", "postmark", "resend", "mandrill", "vonage"),
            "Mapas/geo": ("@googlemaps", "googlemaps", "mapbox", "@mapbox", "google-maps"),
            "Búsqueda/datos": ("algolia", "algoliasearch", "elasticsearch", "@elastic/", "pinecone", "@pinecone"),
            "Observabilidad/otros": ("@sentry/", "sentry-sdk", "datadog", "dd-trace", "newrelic", "@vercel/", "firebase", "supabase", "@supabase/")}
    hall = {}
    for cat, ns in PAGO.items():
        h = sorted({d for d in todo_dep for n in ns if d == n or d.startswith(n)})
        if h:
            hall[cat] = h
            det(D6, f"{cat}: " + corto(h), "dependencias")
    VARPAGO = {"Nube": r"^(AWS_|GCP_|GOOGLE_CLOUD|AZURE_)", "IA": r"(OPENAI|ANTHROPIC|GEMINI|COHERE|HUGGINGFACE)", "Pagos": r"(STRIPE|PAYPAL|MERCADOPAGO|CULQI|BRAINTREE|PAYMENT_(API|KEY|SECRET|GATEWAY|PROVIDER))",
               "Correo/SMS": r"(SENDGRID|MAILGUN|MAILCHIMP|TWILIO|SMTP|MANDRILL|SES_|POSTMARK)", "Mapas": r"(MAPBOX|GOOGLE_MAPS|MAPS_API)", "Scoring/riesgo": r"(SCORING|SCORE|BUREAU|CREDIT)"}
    for cat, rx in VARPAGO.items():
        vv = vars_como(rx)
        if vv:
            det(D6, f"{cat} (variables, solo nombres): " + corto(vv, 5), origen(vv[0]))
    iac_txt = " ".join(leer(p, 60_000) for p in FS if p.endswith((".tf", ".yml", ".yaml", ".json", ".ts")) and (p.split("/")[0] in ("infra", "lib", "cdk", "terraform", "stacks", "iac", "deploy", "bin") or any(x in p for x in ("cdk", ".tf", "serverless", "template")))) if iac else ""
    pres = [p for p in FS if p.endswith((".tf", ".ts", ".yml", ".yaml", ".json")) and re.search(r"AWS::Budgets|aws_budgets_budget|CfnBudget|BillingAlarm|EstimatedCharges|aws_cloudwatch_metric_alarm.*[Bb]illing|budget_alert|CostAnomaly|cost_allocation", leer(p, 60_000))]
    if pres:
        det(D6, "Presupuestos/alarmas de costo en la infraestructura", pres[:2])
    etq = [p for p in FS if p.endswith((".tf", ".ts", ".yml", ".yaml")) and re.search(r"Tags\.of\(|^\s*tags\s*[=:]|default_tags", leer(p, 60_000), re.M)] if iac else []
    if etq:
        det(D6, "Etiquetas de asignación de costo/propietario", etq[:2])
    cupo = [p for p in FILES if p.suffix in EXT_COD | {".yml", ".yaml", ".tf", ".json"} and re.search(r"ThrottlerModule|rate-?limit|rateLimit|throttl|UsagePlan|usage_plan|max_tokens|reserved_concurrency|reservedConcurrentExecutions", leer(p, 80_000), re.I)][:40]
    if cupo:
        det(D6, "Cuotas/límites de uso", [p.as_posix() for p in cupo[:2]])
    if hall or any(vars_como(rx) for rx in VARPAGO.values()):
        if iac and not pres:
            falta(D6, "Hay servicios de pago por uso e infraestructura pero ningún presupuesto ni alarma de costo")
            prop(D6, "Un presupuesto mensual con alerta por correo (umbral 80 %) en la cuenta de nube")
        elif not iac:
            falta(D6, "Hay servicios de pago por uso sin tope ni alarma detectables")
            prop(D6, "Fijar un tope mensual en el panel de cada proveedor y registrar cuánto cuesta cada operación")
        if not cupo and any(c in hall for c in ("IA", "Pagos", "Correo/SMS", "Mapas/geo")):
            falta(D6, "No se ven cuotas ni límites de uso hacia los servicios que cobran por llamada")
            prop(D6, "Poner un límite de tasa y un contador de llamadas antes de las operaciones que cobran")
        if iac and not etq:
            falta(D6, "La infraestructura no etiqueta recursos por proyecto/ambiente")
            prop(D6, "Etiquetas mínimas: proyecto, ambiente y responsable")
    else:
        preg(D6, "¿Qué operaciones del proyecto cobran (APIs externas, nube, correos, IA, consultas de pago por uso)?",
             "Se buscaron SDK de nube/IA/pagos/correo/mapas en dependencias y variables de entorno con esos nombres (solo nombres), y presupuestos/alarmas en la infraestructura; no apareció ninguno")
    if hall or iac:
        preg(D6, "¿Cuál es el gasto mensual esperado y quién aprueba superarlo?", "Se buscaron presupuestos y alarmas en la infraestructura y menciones de «costo/presupuesto» en los .md; el gasto real vive en la factura de cada proveedor")

    # ---- 7. Seguridad
    D7 = nueva(7, "Seguridad")
    versionados = [p for p in gg("ls-files").splitlines() if re.search(r"(^|/)\.env(\.|$)|\.env$", p) and not re.search(r"(example|sample|template|dist|default)", p, re.I)] if es_git else []
    if versionados:
        det(D7, "ARCHIVO DE ENTORNO VERSIONADO (riesgo): " + corto(versionados), "git ls-files")
        falta(D7, "Hay archivos .env versionados; sus valores podrían estar en el historial")
        prop(D7, "Sacarlos del índice, rotar lo que contengan y dejar solo un .env.example con nombres")
    elif envfiles_reales:
        det(D7, "Archivos de entorno presentes y no versionados: " + corto(envfiles_reales), "git ls-files" if es_git else "carpeta (sin git: no se puede verificar)")
    gi = leer(".gitignore")
    cubre = bool(re.search(r"^\s*!?/?\*?\.env", gi, re.M)) if gi else False
    if gi and cubre:
        det(D7, ".gitignore cubre archivos .env", ".gitignore")
    elif envfiles_reales or var_origen or iac or deps:
        falta(D7, ".gitignore no cubre `.env`" if gi else "No hay .gitignore")
        prop(D7, "Añadir al .gitignore `.env*` (salvo `.env.example`), llaves (`*.pem`, `*.key`) y volcados de base")
    if cod:
        det(D7, "CODEOWNERS", cod[:1])
    elif es_git:
        falta(D7, "No hay CODEOWNERS")
        prop(D7, "CODEOWNERS mínimo: un responsable por carpeta crítica (infra, datos, autenticación)")
    audit_w = [p for p in wfpaths if re.search(r"npm audit|pip-audit|snyk|trivy|codeql|gitleaks|trufflehog|semgrep|safety check|osv-scanner", leer(p), re.I)]
    bots = hay(".github/dependabot.yml", ".github/dependabot.yaml", "renovate.json", ".renovaterc", ".renovaterc.json")
    if bots or audit_w or "audit" in pkg.get("scripts", {}):
        det(D7, "Control de dependencias vulnerables", bots + audit_w + (["package.json script audit"] if "audit" in pkg.get("scripts", {}) else []))
    elif deps or py:
        falta(D7, "Sin revisión automática de dependencias vulnerables (ni dependabot/renovate ni audit en CI)")
        prop(D7, "Activar dependabot (o renovate) y un `npm audit`/`pip-audit` en CI que solo avise" if escala == "S" else "Dependabot + audit en CI que falle con severidad alta y escaneo de secretos")
    seg = tiene("helmet", "passport", "@nestjs/passport", "jsonwebtoken", "@nestjs/jwt", "bcrypt", "bcryptjs", "argon2", "csurf", "django", "flask-login", "authlib", "pyjwt", "python-jose", "oauthlib")
    if seg:
        det(D7, "Autenticación/protección en dependencias: " + corto(seg), "dependencias")
    audi = [p.as_posix() for p in DIRS + FILES if re.search(r"(?i)(^|/)(audit|auditoria|bitacora)", p.as_posix())][:3]
    if audi:
        det(D7, "Rastro de auditoría", audi)
    brs = sorted({b for i in wf_info.values() for b in i["ramas"]})
    if brs or ramas:
        det(D7, "Política de ramas inferida: " + (f"workflows se disparan en {corto(brs, 5)}; " if brs else "") + f"ramas base remotas: {corto([re.sub('^origin/', '', b) for b in R['git']['ramas_base']]) or 'ninguna reconocible'}", "workflows / git branch -r")
    PAT = [("clave-aws", re.compile(r"AKIA[0-9A-Z]{16}")), ("clave-privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")), ("token-github", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
           ("token-slack", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")), ("clave-stripe-live", re.compile(r"sk_live_[A-Za-z0-9]{16,}")),
           ("credencial-literal", re.compile(r"""(?i)(?:pass(?:word|wd)?|secret|token|api[_-]?key|private[_-]?key)\w*['"]?\s*[:=]\s*['"]([^'"\s]{8,})['"]"""))]
    PAT_YAML = re.compile(r"""(?i)(?:pass(?:word|wd)?|secret|token|api[_-]?key)\w*\s*[:=]\s*([A-Za-z0-9+/_@#%^&*.-]{8,})\s*$""")
    NOVALOR = re.compile(r"(?i)changeme|example|your[-_]|xxx|placeholder|password|secret|token|dummy|\*{3}|process\.|\benv\.|os\.|config\.|this\.|<|\$\{|get\(|test|todo|none|null|false|true|undefined|string|^\.|^/")
    def parece_secreto(v):
        # letras y dígitos mezclados, sin forma de ruta, constante MAYÚSCULAS ni nombre en kebab-case
        return bool(re.search(r"[A-Za-z]", v) and re.search(r"\d", v)) and "/" not in v and not re.fullmatch(r"[A-Z0-9_]+", v) and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)+", v)
    hall_sec = []
    for p in FILES:
        if len(hall_sec) >= 30:
            break
        n = p.as_posix()
        if re.match(r"\.env($|\.)", p.name) or re.search(r"(\.spec\.|\.test\.|lock|\.min\.|\.md$|/__tests__/|(^|/)tests?/|\.map$|\.svg$|(^|/)logs?/)", n) or p.suffix not in EXT_COD | {".yml", ".yaml", ".json", ".tf", ".properties", ".ini", ".toml", ".cfg", ".sh", ".conf", ".xml"}:
            continue
        try:
            if (ROOT / p).stat().st_size > 200_000:
                continue
        except OSError:
            continue
        for i, linea in enumerate(leer(p, 200_000).splitlines(), 1):
            if len(linea) > 400:
                continue
            for tipo, rx in PAT:
                m = rx.search(linea)
                if m and (tipo != "credencial-literal" or (not NOVALOR.search(m.group(1)) and parece_secreto(m.group(1)))):
                    hall_sec.append((f"{n}:{i}", tipo)); break
            else:
                if p.suffix in (".yml", ".yaml", ".properties", ".ini", ".toml", ".cfg", ".conf", ".tf"):
                    m = PAT_YAML.search(linea)
                    if m and not NOVALOR.search(m.group(1)) and parece_secreto(m.group(1)) and not m.group(1).startswith(("!", "-")):
                        hall_sec.append((f"{n}:{i}", "credencial-literal"))
    if hall_sec:
        det(D7, f"{len(hall_sec)} posibles credenciales en el código (solo ubicación y tipo; no se imprime el valor): " + "; ".join(f"{u} [{t}]" for u, t in hall_sec[:8]), [u for u, _ in hall_sec[:3]])
        falta(D7, "Posibles credenciales literales en el código (revisar y, si son reales, rotarlas)")
        prop(D7, "Mover las credenciales a variables de entorno o a un gestor de secretos y añadir un escaneo de secretos en CI")
    preg(D7, "¿Quién tiene acceso a producción, a los secretos y a las ramas protegidas? ¿Cómo se auditan los cambios?",
         "Se buscaron CODEOWNERS, políticas de ramas en workflows, archivos de entorno y rastro de auditoría en el código; los permisos y la protección de ramas viven en el servidor de git y en la nube, que no se consultan")

    # ---- 8. Documentación y gestión
    D8 = nueva(8, "Documentación y gestión")
    d = R["documentacion"]
    if d["readme"]:
        det(D8, f"README ({len(leer('README.md').splitlines())} líneas)", "README.md")
    else:
        falta(D8, "No hay README")
        prop(D8, "README mínimo: qué es, cómo se levanta, cómo se prueba y cómo se despliega")
    if d["docs_dir"]:
        det(D8, "Carpeta docs/ del repositorio", "docs/")
    if d["markdown"]:
        det(D8, f"{d['markdown']} documentos .md; {d['adr']} de decisiones (ADR)", "búsqueda de *.md")
    if d["openapi_swagger"]:
        det(D8, "Contrato de API (OpenAPI/Swagger)", "dependencia o archivo openapi")
    if "CHANGELOG.md" in FS:
        det(D8, "Registro de cambios", "CHANGELOG.md")
    if d["enlaces_a"]:
        det(D8, "Enlaces a herramientas de gestión: " + ", ".join(d["enlaces_a"]), "menciones en los .md y package.json")
    if claves:
        det(D8, "Claves de ticket en los commits: " + ", ".join(f"{k} ({v})" for k, v in claves.most_common(3)), "git log -n 200")
    isu = glob(r"^\.github/ISSUE_TEMPLATE/")
    if isu:
        det(D8, "Plantillas de issue", isu[:2])
    if not d["docs_dir"] and not d["enlaces_a"]:
        falta(D8, "No hay almacén de documentación detectable (ni docs/, ni Confluence, ni Drive, ni Notion)")
        prop(D8, "Almacén mínimo: carpeta docs/ del repositorio en .md (o una carpeta de Drive legible en .md); el instalador la pide si no existe")
        preg(D8, "¿Dónde se documenta hoy (Confluence, Drive, Notion, nada)? Si no hay nada, ¿se puede aportar el análisis previo en .md?",
             "Se buscaron docs/, enlaces a Confluence/Drive/Notion/Linear/Trello en los .md y package.json; no hay ninguno")
    if not claves and not any("atlassian" in e or "linear" in e or "trello" in e for e in d["enlaces_a"]) and not isu:
        falta(D8, "No se detecta gestor de tickets ni trazabilidad commit-ticket")
        prop(D8, "Sin adaptador de tickets: dejar el rastro del cambio en .md (especificación, tareas, verificación); sumar un adaptador cuando exista el gestor")
        preg(D8, "¿Cómo se gestionan las tareas (Jira, GitHub Issues, Linear, otra, ninguna)?", "Se buscaron claves tipo ABC-123 en los últimos 200 commits, enlaces a gestores en los .md y plantillas de issue; no aparece ninguno")
    if not d["adr"] and escala != "S":
        falta(D8, "No se registran decisiones de arquitectura (ADR)")
        prop(D8, "Un ADR corto por decisión relevante en docs/decisiones/")
    R["dimensiones"] = [D1, D2, D3, D4, D5, D6, D7, D8]
    for dim in R["dimensiones"]:
        for q in dim["pregunta"]:
            assert q["intento"]
    return R


def md(R):
    def kv(d):
        return "\n".join(f"- **{k.replace('_', ' ')}:** {', '.join(map(str, v)) if isinstance(v, (list, tuple)) else (json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v)}" for k, v in d.items())
    o = [f"# Cómo es este proyecto: {R['proyecto']}\n", "_Generado por `harness-detectar.py` (solo lectura). Para validar con el equipo antes de instalar. De los archivos de entorno solo se leen nombres; de posibles credenciales solo archivo:línea y tipo._\n"]
    for t in ("git", "stack", "estructura", "ci", "convenciones", "documentacion", "entorno_ia", "escala", "propuesta"):
        o.append(f"## Resumen: {t.replace('_', ' ')}\n{kv(R[t])}\n")
    for dim in R["dimensiones"]:
        o.append(f"## {dim['n']}. {dim['nombre']}\n")
        o.append("**Detectado**\n" + ("\n".join(f"- {x['hallazgo']} (evidencia: `{x['evidencia']}`)" for x in dim["detectado"]) or "- (nada detectado)") + "\n")
        o.append("**Falta**\n" + ("\n".join(f"- {x}" for x in dim["falta"]) or "- (nada que marcar)") + "\n")
        o.append("**Propuesta**\n" + ("\n".join(f"- {x}" for x in dim["propuesta"]) or "- (sin cambios: lo detectado cubre el piso)") + "\n")
        o.append("**Pregunta**\n" + ("\n".join(f"- {x['pregunta']} _Intentado: {x['intento']}._" for x in dim["pregunta"]) or "- (ninguna: todo se pudo detectar)") + "\n")
    return "\n".join(o)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Informe «cómo es este proyecto» (modo adopt, solo lectura).")
    ap.add_argument("carpeta")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--md", action="store_true", help="Markdown (predeterminado)")
    g.add_argument("--json", action="store_true")
    ap.add_argument("--salida", help="escribe el informe en este archivo (fuera del proyecto analizado)")
    a = ap.parse_args(argv)
    root = pathlib.Path(a.carpeta).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"No existe {root}")
    destino = None
    if a.salida:
        destino = pathlib.Path(a.salida).expanduser().resolve()
        if destino == root or root in destino.parents:
            sys.exit(f"Se rechaza --salida dentro del proyecto analizado ({destino}): el detector no escribe en el proyecto")
    R = analizar(root)
    txt = json.dumps(R, ensure_ascii=False, indent=2) if a.json else md(R)
    if destino:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(txt + "\n", encoding="utf8")
        print(f"Informe escrito en {destino}", file=sys.stderr)
    else:
        print(txt)


if __name__ == "__main__":
    main()
