#!/usr/bin/env python3
"""Logica del comando unico `harness` (spec 20): asistente de terminal, instalar, update, doctor y estado.

Solo biblioteca estandar. No usa la red. No reimplementa al instalador: lo ejecuta (instalador/harness_instalar.py),
igual que preflight-accesos.py, comprobar-version.py, harness-detectar.py y harness-frescura.py.

Reglas del asistente:
  - Una pregunta por vez; cada una dice que se intento.
  - Nada se instala sin la confirmacion final («¿Lo aplico? [s/N]»). Lo unico que se guarda antes es el avance
    (`<instancia>/.harness/sesion.json`: paso y respuestas, nunca secretos).
  - Sin terminal interactiva (o con --no-interactivo / --json) no pregunta: muestra el plan y sale con 0 sin escribir;
    con --si aplica el plan.
Codigos de salida: 0 bien; 1 problema (doctor) o error; 2 detenido (faltan accesos, informacion o una decision); 130 interrumpido.
"""
import argparse
import difflib
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SUBCOMANDOS = ("instalar", "update", "montar", "doctor", "estado", "siguiente", "trazar", "erp", "aprender", "entorno", "ayuda")
IGNORAR = {".git", "node_modules", ".venv", "venv", "__pycache__", ".harness", "dist", "build", ".idea", ".vscode"}
CODIGO_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".rb", ".php", ".cs", ".kt", ".swift",
              ".c", ".cpp", ".h", ".scala", ".vue", ".sh", ".dart", ".lua"}
MANIFIESTOS = {"package.json", "pyproject.toml", "requirements.txt", "pom.xml", "build.gradle", "go.mod",
               "Cargo.toml", "Gemfile", "composer.json", "setup.py"}
HOJAS = {".xlsx", ".xls", ".csv", ".tsv"}
DOCS = {".md", ".txt", ".rst"}
ORIGEN_NOMBRES = ("origen", "origin", "sistema-origen", "legacy", "fuente")
LIMITE_ARCHIVOS = 4000
SECRETO = re.compile(
    r"(pass(word|wd)?|contrase[nñ]a|secret|token|api[_-]?key|private[_-]?key|\bpwd\b|credencial)"
    r"|://[^/\s:@]+:[^@\s]+@|\bAKIA[0-9A-Z]{16}\b|\bgh[pousr]_[A-Za-z0-9]{20,}|\bsk-[A-Za-z0-9]{20,}", re.I)
SI = {"s", "si", "sí", "y", "yes"}
NOMBRE_MODO = {"A": "adopt", "B": "init", "C": "migrar"}
NOMBRE_CASO = {"A": "A · proyecto empezado", "B": "B · desde cero", "C": "C · migración o réplica de un sistema existente"}


class Detener(Exception):
    def __init__(self, mensaje, codigo=2):
        super().__init__(mensaje)
        self.codigo = codigo


# ------------------------------------------------------------------ utilidades
def correr(cmd, cwd=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, env=env, cwd=cwd)


def parece_secreto(texto):
    return bool(SECRETO.search(texto or ""))


def sha(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def contar_commits(carpeta):
    """Commits del historial (0 si no hay git o no hay historial). Solo lectura."""
    if not (Path(carpeta) / ".git").exists():
        return 0
    try:
        r = correr(["git", "-C", carpeta, "rev-list", "--count", "HEAD"])
        return int(r.stdout.strip()) if r.returncode == 0 else 0
    except (OSError, ValueError):
        return 0


class Salida:
    """Escritura de texto plano; color solo si es una terminal y sin NO_COLOR."""

    def __init__(self, flujo, callar=False):
        self.flujo, self.callar = flujo, callar
        self.color = (not callar and hasattr(flujo, "isatty") and flujo.isatty()
                      and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb")

    def p(self, texto=""):
        if not self.callar:
            print(texto, file=self.flujo)

    def e(self, texto, codigo):
        if self.color:
            return f"\033[{codigo}m{texto}\033[0m"
        return texto

    def titulo(self, texto):
        self.p("\n" + self.e(texto, "1"))
        self.p("-" * len(texto))


# ------------------------------------------------------------------ detección del caso
def explorar(carpeta):
    """Mira la carpeta (solo lectura) y cuenta lo que hay. No sigue enlaces ni carpetas pesadas."""
    carpeta = Path(carpeta)
    r = {"codigo": [], "manifiestos": [], "sql": [], "hojas": [], "docs": [], "otros": [], "archivos": 0,
         "git": (carpeta / ".git").exists(), "commits": contar_commits(carpeta), "origen": None, "origen_declarado_en": None,
         "truncado": False}
    for nombre in ORIGEN_NOMBRES:
        if (carpeta / nombre).is_dir():
            r["origen"], r["origen_declarado_en"] = str(carpeta / nombre), f"carpeta «{nombre}/»"
    acc = carpeta / "acceso.local.toml"
    if acc.is_file():
        try:
            ruta = (tomllib.loads(acc.read_text(encoding="utf-8")).get("origen") or {}).get("ruta")
            if isinstance(ruta, str) and ruta:
                r["origen"], r["origen_declarado_en"] = os.path.expanduser(ruta), "[origen] ruta de acceso.local.toml"
        except (tomllib.TOMLDecodeError, OSError):
            pass
    for dirpath, dirs, files in os.walk(carpeta):
        dirs[:] = sorted(d for d in dirs if d not in IGNORAR and not os.path.islink(os.path.join(dirpath, d)))
        rel_dir = Path(dirpath).relative_to(carpeta)
        for f in sorted(files):
            if f.startswith(".") or f == "acceso.local.toml":
                continue
            r["archivos"] += 1
            if r["archivos"] > LIMITE_ARCHIVOS:
                r["truncado"] = True
                return r
            rel = str(rel_dir / f) if str(rel_dir) != "." else f
            ext = Path(f).suffix.lower()
            if f in MANIFIESTOS:
                r["manifiestos"].append(rel)
            elif ext in CODIGO_EXT:
                r["codigo"].append(rel)
            elif ext == ".sql":
                r["sql"].append(rel)
            elif ext in HOJAS:
                r["hojas"].append(rel)
            elif ext in DOCS:
                r["docs"].append(rel)
            else:
                r["otros"].append(rel)
    return r


def _ej(lista, n=3):
    return ", ".join(lista[:n]) + (f" (+{len(lista) - n} más)" if len(lista) > n else "")


def detectar_caso(carpeta):
    """Devuelve {caso, confianza: alta|duda, miro: [líneas], porque, alternativas}."""
    x = explorar(carpeta)
    miro = [f"Carpeta: {carpeta}", f"Archivos visibles (sin ocultos ni carpetas de dependencias): {x['archivos']}" + (" (conteo truncado)" if x["truncado"] else "")]
    miro.append("Git: " + (f"sí, {x['commits']} commits de historial" if x["git"] and x["commits"] else "sí, sin historial" if x["git"] else "no hay .git"))
    for clave, etiqueta in (("codigo", "Código fuente"), ("manifiestos", "Manifiestos de proyecto"), ("sql", "Esquemas/volcados SQL"),
                            ("hojas", "Hojas de cálculo (xlsx/csv)"), ("docs", "Documentos de texto (md/txt)"), ("otros", "Otros archivos")):
        if x[clave]:
            miro.append(f"{etiqueta}: {len(x[clave])} ({_ej(x[clave])})")
    miro.append("Origen declarado: " + (f"{x['origen']} (en {x['origen_declarado_en']})" if x["origen"] else "ninguno"))
    hay_codigo = bool(x["codigo"] or x["manifiestos"] or x["commits"])
    if x["origen"]:
        caso, conf, porque = "C", "alta", f"hay un origen declarado ({x['origen_declarado_en']}): se replica un sistema existente"
    elif hay_codigo:
        caso, conf = "A", "alta"
        porque = "hay " + " y ".join(p for p in (f"código ({len(x['codigo'])} archivos)" if x["codigo"] else "",
                                                    "manifiestos de proyecto" if x["manifiestos"] else "",
                                                    f"historial git ({x['commits']} commits)" if x["commits"] else "") if p) + ": el proyecto ya está empezado"
    elif x["sql"]:
        caso, conf = "C", "duda"
        porque = ("no hay código pero sí esquema/volcado SQL: puede ser el volcado de otro sistema (C) o la información de partida "
                  "de un proyecto nuevo (B)")
    elif x["archivos"] <= 3 and not x["hojas"]:
        caso, conf = "B", "alta"
        porque = "la carpeta está vacía o casi vacía (sin código, sin base, sin historial)"
    elif x["hojas"] and not x["docs"]:
        caso, conf = "B", "duda"
        porque = "solo hay hojas de cálculo: pueden ser la información de partida (B) o el diccionario de un sistema a replicar (C)"
    elif x["docs"] and not x["otros"]:
        caso, conf = "B", "alta"
        porque = "solo hay documentos de texto: es información de partida de un proyecto nuevo"
    else:
        caso, conf = "B", "duda"
        porque = "hay archivos que no reconozco como código ni como información de partida"
    return {"caso": caso, "confianza": conf, "miro": miro, "porque": porque, "exploracion": x}


# ------------------------------------------------------------------ sesión (retomar)
class Sesion:
    """Avance guardado en <instancia>/.harness/sesion.json: paso y respuestas, nunca secretos."""

    def __init__(self):
        self.ruta = None
        self.datos = {"version": 1, "estado": "en_curso", "paso": "inicio", "carpeta": None, "respuestas": {}, "omitidas": []}

    @staticmethod
    def leer(ruta):
        try:
            d = json.loads(Path(ruta).read_text(encoding="utf-8"))
            return d if isinstance(d, dict) and isinstance(d.get("respuestas"), dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def fijar_ruta(self, instancia):
        self.ruta = Path(instancia) / ".harness" / "sesion.json"

    def guardar(self):
        if self.ruta is None:
            return
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.datos, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.ruta)

    def responder(self, clave, valor):
        if parece_secreto(str(valor)):
            self.datos["respuestas"].pop(clave, None)
            if clave not in self.datos["omitidas"]:
                self.datos["omitidas"].append(clave)
            return False
        self.datos["respuestas"][clave] = valor
        return True

    def paso(self, nombre):
        self.datos["paso"] = nombre
        self.guardar()


# ------------------------------------------------------------------ asistente
class Asistente:
    def __init__(self, a, entrada, out, interactivo, raiz=RAIZ):
        self.a, self.entrada, self.out, self.interactivo, self.raiz = a, entrada, out, interactivo, Path(raiz)
        self.sesion = Sesion()
        self.n = 0
        self.informe = {"pasos": []}
        self.tmp = []

    # -- preguntas
    def preguntar(self, clave, texto, intento, defecto=None, flag=None, vacio_ok=True):
        """Una pregunta por vez. Orden: bandera > respuesta guardada > pregunta > valor por defecto (sin terminal)."""
        if flag not in (None, ""):
            self.sesion.responder(clave, flag)
            return flag
        previa = self.sesion.datos["respuestas"].get(clave)
        if previa is not None:
            self.out.p(f"(Ya respondido antes: {texto} -> {previa or 'vacío'})")
            return previa
        if not self.interactivo:
            return defecto
        self.n += 1
        self.out.p(f"\nPregunta {self.n}: {texto}")
        self.out.p(f"  Se intentó: {intento}")
        if defecto not in (None, ""):
            self.out.p(f"  (Enter = {defecto})")
        resp = self.entrada("> ").strip()
        if not resp and defecto is not None:
            resp = defecto
        if not self.sesion.responder(clave, resp):
            self.out.p("  Eso parece un secreto: no lo guardo en la sesión ni lo uso. El harness nunca pide ni guarda credenciales; "
                       "usa las que ya tiene tu sistema (perfiles, gh, SSH).")
            return defecto
        self.sesion.guardar()
        return resp

    def confirmar(self, texto):
        self.out.p("\n" + texto)
        return self.entrada("> ").strip().lower() in SI

    # -- ayudantes
    def instancia_por_defecto(self, caso, carpeta, entradas):
        hermana = carpeta.parent / (carpeta.name + "-harness")
        if caso == "A":
            return hermana, ("en un proyecto empezado el informe y la instancia nunca se escriben dentro del proyecto: "
                             "propongo una carpeta hermana")
        if entradas is not None:
            e = Path(entradas).resolve()
            if e == carpeta or e in carpeta.parents:
                return hermana, "las entradas están en la propia carpeta y la instancia no puede quedar dentro de ellas"
        return carpeta, "la propia carpeta"

    def acceso_temporal(self, caso, entradas):
        d = Path(tempfile.mkdtemp(prefix="harness-acceso-"))
        self.tmp.append(d)
        if caso == "B":
            txt = f'[documentacion]\nmetodo = "carpeta_repo"\ncarpeta = "{entradas}"\n'
        else:
            txt = f'[origen]\nmetodo = "descripcion"\nruta = "{entradas}"\n'
        (d / "acceso.local.toml").write_text(txt, encoding="utf-8")
        return str(d / "acceso.local.toml")

    def politica(self, instancia):
        if self.a.politica:
            return self.a.politica
        p = Path(instancia) / "politicas.toml"
        return str(p if p.exists() else self.raiz / "politicas" / "politicas.defecto.toml")

    def preflight(self, partida, modo, instancia, acceso):
        acc = acceso
        if not acc:
            c = Path(instancia) / "acceso.local.toml"
            if c.exists():
                acc = str(c)
            else:
                d = Path(tempfile.mkdtemp(prefix="harness-acceso-"))
                self.tmp.append(d)
                (d / "acceso.local.toml").write_text("", encoding="utf-8")
                acc = str(d / "acceso.local.toml")
        r = correr([sys.executable, self.raiz / "instalador" / "preflight-accesos.py", "--politica", self.politica(instancia),
                    "--acceso", acc, "--modo", modo, "--partida", partida, "--json"])
        if r.returncode == 1 and "ningun ambiente" in (r.stderr + r.stdout):
            raise Detener("No puedo orquestar todavía: la política no declara ningún ambiente de datos y el harness nunca asume uno.\n"
                          "  - Qué hacer: declara al menos uno ([[datos.ambientes]] con nombre y tipo) en tu politicas.toml y pásalo con --politica "
                          "(o ponlo en la instancia), y declara cómo llegas a cada ambiente en tu acceso.local.toml.\n"
                          "No instalo nada. Vuelve a correr `harness`: retomo desde aquí.", 2)
        if r.returncode == 1:
            raise Detener("El preflight de accesos no pudo leer la configuración:\n" + (r.stderr.strip() or r.stdout.strip()), 1)
        try:
            return r.returncode, json.loads(r.stdout)
        except json.JSONDecodeError:
            raise Detener("Salida ilegible del preflight de accesos:\n" + r.stdout + r.stderr, 1)

    def comando_instalador(self, modo, partida, instancia, acceso, proyecto, aplicar):
        cmd = [sys.executable, self.raiz / "instalador" / "harness_instalar.py", modo, instancia, "--harness", self.raiz]
        if modo in ("init", "adopt", "migrar") and partida:
            cmd += ["--partida", partida]
        if acceso:
            cmd += ["--acceso", acceso]
        if self.a.politica:
            cmd += ["--politica", self.a.politica]
        if proyecto:
            cmd += ["--proyecto", proyecto]
        if getattr(self.a, "aceptar_degradado", False):
            cmd += ["--aceptar-degradado"]
        if getattr(self.a, "aceptar_dentro_de_repo", False):
            cmd += ["--aceptar-dentro-de-repo"]
        if aplicar:
            cmd += ["--aplicar"]
        return cmd

    # -- flujo
    def buscar_sesion(self, carpeta):
        cands = []
        if self.a.instancia:
            cands.append(Path(self.a.instancia).expanduser().resolve())
        cands += [carpeta, carpeta.parent / (carpeta.name + "-harness")]
        for c in cands:
            s = Sesion.leer(c / ".harness" / "sesion.json")
            if s and s.get("estado") == "en_curso" and s.get("respuestas"):
                return c, s
        return None, None

    def correr(self):
        try:
            return self._correr()
        finally:
            for d in self.tmp:
                shutil.rmtree(d, ignore_errors=True)

    def _correr(self):
        a, out = self.a, self.out
        carpeta = Path(a.carpeta or os.getcwd()).expanduser().resolve()
        if not carpeta.is_dir():
            raise Detener(f"No existe la carpeta {carpeta}.", 1)
        out.titulo("Asistente del harness")
        out.p("Voy paso a paso y, hasta que digas «s» al final, no instalo nada.")

        # retomar
        donde, previa = self.buscar_sesion(carpeta) if self.interactivo else (None, None)
        if previa is not None:
            self.sesion.datos, self.sesion.ruta = previa, donde / ".harness" / "sesion.json"
            self.out.p(f"\nEncontré una sesión sin terminar en {donde} (paso «{previa.get('paso')}», "
                       f"{len(previa['respuestas'])} respuestas guardadas, sin secretos).")
            if self.entrada("¿Continuar donde quedaste? [S/n] > ").strip().lower() in ("n", "no"):
                self.sesion = Sesion()
                self.sesion.ruta = donde / ".harness" / "sesion.json"
                self.out.p("Empiezo de nuevo (la sesión anterior se reemplaza al guardar).")
        self.sesion.datos["carpeta"] = str(carpeta)

        # 1) detectar el caso
        out.titulo("1. Qué miré")
        det = detectar_caso(carpeta)
        for l in det["miro"]:
            out.p("  " + l)
        out.p(f"\nConclusión: caso {NOMBRE_CASO[det['caso']]}. Porque {det['porque']}.")
        self.informe.update(carpeta=str(carpeta), miro=det["miro"], deteccion={"caso": det["caso"], "confianza": det["confianza"], "porque": det["porque"]})
        caso = a.caso
        if not caso:
            caso = self.sesion.datos["respuestas"].get("caso")
        if not caso:
            if det["confianza"] == "duda":
                if not self.interactivo:
                    raise Detener("No estoy seguro del caso (" + det["porque"] + f"). Mi mejor suposición es {det['caso']}, "
                                  "pero no instalo sobre una suposición: repite con --caso A|B|C.", 2)
                caso = self.preguntar("caso", "¿Qué caso es? A = proyecto empezado, B = desde cero, C = migración/réplica de otro sistema.",
                                      det["porque"] + f". Mi mejor suposición es {det['caso']}.", defecto=det["caso"]).strip().upper()
                if caso not in ("A", "B", "C"):
                    raise Detener("Respuesta no válida: responde A, B o C.", 2)
            else:
                caso = det["caso"]
        caso = caso.upper()
        self.sesion.responder("caso", caso)
        self.informe["caso"] = caso
        x = det["exploracion"]

        # 2) entradas de partida (B y C)
        entradas = None
        if caso in ("B", "C"):
            out.titulo("2. Información de partida")
            if caso == "B":
                cand = a.documentacion or None
                defecto = None
                if (carpeta / "docs").is_dir():
                    defecto = str(carpeta / "docs")
                elif x["docs"] or x["hojas"] or x["sql"]:
                    defecto = str(carpeta)
                intento = (f"busqué una carpeta «docs/» y archivos .md/.csv/.xlsx/.sql en {carpeta}: "
                           + (f"encontré {defecto}" if defecto else "no encontré nada utilizable"))
                entradas = self.preguntar("entradas", "¿En qué carpeta está la información de partida (descripción del producto, "
                                          "modelo de datos, hojas)?", intento, defecto=defecto, flag=cand)
            else:
                cand = a.origen or x["origen"]
                defecto = x["origen"] or (str(carpeta) if (x["sql"] or x["hojas"] or x["docs"]) else None)
                intento = (f"busqué un origen declarado (carpeta origen/ o [origen] ruta) y archivos .sql/.xlsx/.csv/.md en {carpeta}: "
                           + (f"encontré {defecto}" if defecto else "no encontré nada"))
                entradas = self.preguntar("entradas", "¿Dónde está la descripción o el volcado del sistema origen "
                                          "(esquema SQL, diccionario, hojas)?", intento, defecto=defecto, flag=a.origen)
            if not entradas:
                self.informe["falta"] = ["información de partida"]
                raise Detener("Sin la información de partida no empiezo. Falta: una carpeta con "
                              + ("la descripción del producto, el modelo de datos o las hojas (.md, .csv, .xlsx, .sql)"
                                 if caso == "B" else "el esquema, el diccionario o el volcado del sistema origen (.sql, .csv, .xlsx, .md)")
                              + ". Ponla en una carpeta y vuelve a correr `harness` (o pásala con "
                              + ("--documentacion" if caso == "B" else "--origen") + ").", 2)
            entradas = str(Path(entradas).expanduser().resolve())
            if not Path(entradas).is_dir():
                raise Detener(f"La carpeta de entradas {entradas} no existe.", 2)
            out.p(f"Información de partida: {entradas}")

        # 3) dónde va la instancia
        out.titulo("3. Dónde dejo la instancia")
        defecto, motivo = self.instancia_por_defecto(caso, carpeta, entradas)
        inst = self.preguntar("instancia", "¿En qué carpeta dejo la instancia del harness?", f"propongo {defecto} ({motivo})",
                              defecto=str(defecto), flag=a.instancia)
        instancia = Path(inst or str(defecto)).expanduser().resolve()
        if instancia.is_file():
            raise Detener(f"{instancia} es un archivo; se espera una carpeta.", 2)
        if self.interactivo and self.sesion.ruta is None:
            self.sesion.fijar_ruta(instancia)
            self.sesion.guardar()
        self.informe["instancia"] = str(instancia)
        out.p(f"Instancia: {instancia}")

        # 4) accesos declarados (A) / restricciones
        acceso = a.acceso
        if caso == "A":
            out.titulo("4. Accesos")
            defecto_acc = str(instancia / "acceso.local.toml") if (instancia / "acceso.local.toml").exists() else ""
            acceso = self.preguntar("acceso", "¿Dónde está tu acceso.local.toml (cómo llegas a repos, datos y nube)? Enter si todavía no lo tienes.",
                                    "busqué acceso.local.toml en la instancia: " + (defecto_acc or "no está"), defecto=defecto_acc, flag=a.acceso) or None
            pol = self.preguntar("politica", "¿Dónde está tu politicas.toml (qué ambientes existen y qué se permite)? Enter si todavía no la tienes.",
                                 "busqué politicas.toml en la instancia: " + ("encontrada" if (instancia / "politicas.toml").exists() else "no está"),
                                 defecto="", flag=a.politica)
            if pol:
                a.politica = pol
        else:
            acceso = self.acceso_temporal(caso, entradas)
        notas = self.preguntar("notas", "¿Algo que deba saber del proyecto (equipo, restricciones)? Enter para omitir.",
                               "no hay dónde inferirlo; es opcional. Se guarda sin secretos y el instalador todavía no lo usa", defecto="") if self.interactivo else ""

        # 5) resumen
        ya_instalada = (instancia / "harness.lock").exists()
        if ya_instalada:
            modo = "update"
        elif caso == "A":
            modo = "init" if (instancia / ".harness" / "informe-adopt.md").exists() else "adopt"
        else:
            modo = NOMBRE_MODO[caso]
        partida = {"update": None}.get(modo, caso)
        proyecto = str(carpeta) if (caso == "A" and modo == "adopt" and instancia != carpeta) else None
        self.informe.update(modo=modo, partida=caso)
        out.titulo("5. Lo que entendí, lo que falta y lo que haré")
        out.p(f"Entendí: caso {NOMBRE_CASO[caso]}. Instancia en {instancia}." + (f" Entradas en {entradas}." if entradas else ""))
        falta = []
        if caso == "A" and not acceso:
            falta.append("tu acceso.local.toml (cómo llegas a repos, datos y nube)")
        if caso == "A" and modo == "init":
            out.p("Ya existe el informe de adopción: ahora instalo el esqueleto sobre el proyecto empezado.")
        out.p("Haré: modo «" + modo + "» del instalador"
              + (" (analiza el proyecto y deja el informe «cómo es este proyecto»; no cambia código)" if modo == "adopt" else
                 " (actualiza solo lo del harness que nadie modificó)" if modo == "update" else " (crea el esqueleto de la instancia)")
              + f", todo dentro de {instancia}.")

        # 6) preflight de accesos
        if modo != "update":
            out.titulo("6. Preflight de accesos (solo lectura)")
            cod, inf = self.preflight(caso, "init" if modo == "init" else modo, instancia, acceso)
            for f in inf["filas"]:
                out.p(f"  {f['recurso']:<24}{f['metodo']:<16}{f['estado']:<11}{f.get('pedir') or f.get('detalle') or ''}")
            self.informe["accesos"] = {"puede_orquestar": cod == 0, "faltan": inf.get("faltan", []), "degradados": inf.get("degradados", [])}
            if cod == 2:
                faltan = [f for f in inf["filas"] if f["estado"] == "FALTA" and f.get("requerido")]
                self.informe["falta"] = [f["recurso"] for f in faltan]
                self.sesion.paso("accesos")
                msg = ["No puedo orquestar todavía. Falta (requerido): " + ", ".join(inf["faltan"])]
                msg += [f"  - {f['recurso']}: {f.get('pedir', '')}" for f in faltan]
                msg.append("No instalo nada. Resuelve lo anterior y vuelve a correr `harness`: retomo desde aquí.")
                raise Detener("\n".join(msg), 2)
            out.p("Puede orquestar." if not inf["degradados"] else "Modo degradado declarado en: " + ", ".join(inf["degradados"]))
        self.informe["falta"] = falta

        # 7) plan (sin escribir)
        out.titulo("7. Plan del instalador (todavía no escribe nada)")
        self.sesion.paso("plan")
        r = correr(self.comando_instalador(modo, partida, instancia, acceso, proyecto, False))
        plan_txt = (r.stdout + r.stderr).strip()
        out.p(plan_txt)
        self.informe["plan"] = plan_txt
        if r.returncode != 0:
            self.informe["codigo"] = r.returncode
            raise Detener("El instalador se detuvo (arriba está el motivo). No se escribió nada.", r.returncode)

        # 8) confirmación
        if not self.interactivo:
            if a.si:
                aplicar = True
            else:
                out.p("\nSin terminal interactiva y sin --si: muestro el plan y salgo sin escribir. Repite con --si para aplicarlo.")
                self.informe["aplicado"] = False
                return 0
        else:
            self.sesion.paso("confirmacion")
            aplicar = self.confirmar("¿Lo aplico? [s/N]")
        if not aplicar:
            out.p("\nNo apliqué nada. Tu avance quedó guardado; vuelve a correr `harness` para continuar.")
            self.informe["aplicado"] = False
            return 0
        r = correr(self.comando_instalador(modo, partida, instancia, acceso, proyecto, True))
        out.p((r.stdout + r.stderr).strip())
        self.informe["aplicado"] = r.returncode == 0
        self.informe["codigo"] = r.returncode
        if r.returncode == 0:
            if self.sesion.ruta is not None and self.interactivo:
                self.sesion.datos["estado"] = "terminada"
                self.sesion.paso("terminada")
            out.p("\nListo. Siguiente: `harness doctor` y `harness estado` en la instancia."
                  + (" Revisa .harness/informe-adopt.md con tu equipo y vuelve a correr `harness` para instalar el esqueleto." if modo == "adopt" else ""))
            if modo != "adopt" and self.interactivo:
                # Montaje del entorno de los agentes (AGENTS.md, skills, permisos, hooks de datos si la politica lo permite).
                # Si la entrada se agota se toma como «no»: nunca monta sin una respuesta afirmativa.
                try:
                    quiere = self.confirmar("¿Monto ahora el entorno de tus agentes de IA (AGENTS.md, skills, permisos)? [s/N]\n"
                                            "(Las bases de datos no se instalan: el acceso a datos lo das tú; el montaje te lo recordará.)")
                except (EOFError, StopIteration):
                    quiere = False
                if quiere:
                    rc = subprocess.run([sys.executable, str(self.raiz / "instalador" / "montaje.py"), str(instancia), "--aplicar"]).returncode
                    self.informe["montaje"] = rc
                else:
                    out.p("No monté nada. Cuando quieras: `harness montar " + str(instancia) + "` (primero muestra el plan).")
        return r.returncode


# ------------------------------------------------------------------ doctor y estado
def _tracked(carpeta, nombre):
    r = correr(["git", "-C", carpeta, "ls-files", "--", nombre])
    return r.returncode == 0 and bool(r.stdout.strip())


def _ignorado(carpeta, nombre):
    return correr(["git", "-C", carpeta, "check-ignore", "-q", nombre]).returncode == 0


def revisar_secretos(instancia):
    """Accesos locales con aspecto de secreto (solo nombres de campo; nunca valores) o versionados."""
    problemas = []
    instancia = Path(instancia)
    en_git = bool(correr(["git", "-C", instancia, "rev-parse", "--is-inside-work-tree"]).stdout.strip() == "true") if shutil.which("git") else False
    for f in sorted(instancia.glob("*.local.toml")):
        if f.name.endswith("ejemplo.toml"):
            continue
        campos = []
        try:
            datos = tomllib.loads(f.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError):
            datos = {}

        def rec(d, ruta=""):
            for k, v in d.items():
                if isinstance(v, dict):
                    rec(v, ruta + k + ".")
                elif parece_secreto(k) and not str(k).lower().startswith(("variables", "perfil")) or (isinstance(v, str) and parece_secreto(v)):
                    campos.append(ruta + k)
        rec(datos)
        if campos:
            problemas.append((f"{f.name} tiene campos con aspecto de secreto: {', '.join(campos)}",
                              "quita los valores: solo van métodos, hosts y NOMBRES de perfiles o variables; si ya se versionó, rota esa credencial"))
        if en_git:
            if _tracked(instancia, f.name):
                problemas.append((f"{f.name} está versionado en git", f"sácalo del índice (git rm --cached {f.name}) y agrégalo al .gitignore"))
            elif not _ignorado(instancia, f.name):
                problemas.append((f"{f.name} no está en el .gitignore", f"agrega {f.name} al .gitignore antes de versionar la instancia"))
    return problemas


def doctor(instancia, raiz=RAIZ):
    raiz = Path(raiz)
    instancia = Path(instancia).resolve() if instancia else None
    filas = []   # (nivel, texto, accion)  nivel: ok | info | problema

    # versión
    cmd = [sys.executable, raiz / "instalador" / "comprobar-version.py", "--harness", raiz, "--json"]
    es_inst = bool(instancia and (instancia / "harness.lock").exists())
    if es_inst:
        cmd += ["--instancia", instancia]
    r = correr(cmd)
    try:
        v = json.loads(r.stdout)
    except json.JSONDecodeError:
        v = {"estado": "version_ilegible", "mensajes": [r.stderr.strip() or "salida ilegible"], "codigo": 2}
    if v["estado"] == "al_dia":
        filas.append(("ok", f"Versión del harness {v.get('version_harness', '?')}" + (f" y harness.lock al día ({v.get('version_instancia')})" if es_inst else ""), ""))
    elif v["estado"] == "atrasada":
        filas.append(("problema", f"La instancia fija {v.get('version_instancia')} y el harness está en {v.get('version_harness')}", "ejecuta `harness update` en la instancia"))
    elif v["estado"] == "instancia_adelantada":
        filas.append(("problema", f"La instancia fija {v.get('version_instancia')}, más nueva que este harness ({v.get('version_harness')})", "actualiza el harness local"))
    elif v["estado"] in ("lock_invalido", "version_ilegible"):
        filas.append(("problema", "Versión: " + " ".join(v["mensajes"]), "corrige VERSION o harness.lock"))
    else:
        filas.append(("info", f"Versión del harness {v.get('version_harness', '?')}; " + ("la carpeta no tiene harness.lock" if instancia else "sin instancia indicada"), ""))
    if instancia and not es_inst:
        filas.append(("info", f"{instancia} no es una instancia instalada (sin harness.lock)", "corre `harness` para armarla"))

    # frescura
    for etiqueta, base in (("del harness", raiz), ("de la instancia", instancia if es_inst else None)):
        if base is None:
            continue
        r = correr([sys.executable, raiz / "herramientas" / "harness-frescura.py", base, "--json", "--tolerar-sin-cabecera"])
        try:
            f = json.loads(r.stdout)
        except json.JSONDecodeError:
            filas.append(("problema", f"No pude medir la frescura {etiqueta}", "ejecuta harness-frescura.py a mano"))
            continue
        if f["vencidos"]:
            filas.append(("problema", f"Documentos {etiqueta} vencidos: " + ", ".join(i["doc"] for i in f["vencidos"][:5]), "revísalos y actualiza la cabecera «revisado»"))
        else:
            filas.append(("ok", f"Frescura de los documentos {etiqueta}: {f['total']} revisados, ninguno vencido", ""))
        if f["por_vencer"]:
            filas.append(("info", f"Por vencer en 14 días ({etiqueta}): " + ", ".join(i["doc"] for i in f["por_vencer"][:5]), ""))

    # herramientas
    for nombre in ("git", "python3"):
        if shutil.which(nombre):
            filas.append(("ok", f"Herramienta requerida presente: {nombre}", ""))
        else:
            filas.append(("problema", f"Falta la herramienta requerida: {nombre}", f"instala {nombre} y vuelve a correr `harness doctor`"))
    if sys.version_info < (3, 11):
        filas.append(("problema", f"Python {sys.version_info.major}.{sys.version_info.minor} es anterior a 3.11", "usa Python 3.11 o más nuevo"))
    for nombre in ("gh", "ssh", "node"):
        filas.append(("info", f"Herramienta opcional {nombre}: " + ("presente" if shutil.which(nombre) else "no está (solo informado)"), ""))

    # secretos
    if instancia and instancia.is_dir():
        sec = revisar_secretos(instancia)
        for t, ac in sec:
            filas.append(("problema", t, ac))
        if not sec:
            filas.append(("ok", "Ningún acceso local con aspecto de secreto ni versionado", ""))
    return filas


_SECRETOS_BUNDLE = [re.compile(x) for x in (
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----", r"\bAKIA[0-9A-Z]{16}\b", r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b", r"(?i)(passw(or)?d|secret|token|api[_-]?key)(\s*[:=]\s*)\S+",
    r"https?://[^/\s:@]+:[^/\s:@]{3,}@")]


def redactar(valor, casa=None):
    """Quita de un texto o estructura lo que no debe salir en un paquete para pegar: secretos y la ruta personal (se deja «~»)."""
    casa = str(casa if casa is not None else Path.home())
    if isinstance(valor, str):
        if casa and casa != "/":
            valor = valor.replace(casa, "~")
        for pat in _SECRETOS_BUNDLE:
            valor = pat.sub(lambda m: (m.group(1) + (m.group(3) or "") + "«oculto»") if pat.groups >= 3 and m.lastindex and m.lastindex >= 3 else "«oculto»", valor)
        return valor
    if isinstance(valor, dict):
        return {redactar(k, casa): redactar(v, casa) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [redactar(v, casa) for v in valor]
    return valor


def paquete_diagnostico(instancia, raiz=RAIZ):
    """JSON para pegar a quien atiende un problema: versiones, sistema, resultado de `doctor` y estado de la instancia. Sin secretos ni rutas
    personales. No incluye el contenido de ningún archivo del proyecto, solo nombres y estados."""
    import platform
    filas = doctor(instancia, raiz)
    version = (Path(raiz) / "VERSION").read_text(encoding="utf-8").strip() if (Path(raiz) / "VERSION").exists() else "?"
    git = correr(["git", "--version"]) if shutil.which("git") else None
    paquete = {"paquete": "diagnostico-harness", "version_formato": 1, "harness": version,
               "python": platform.python_version(), "sistema": f"{platform.system()} {platform.release()}",
               "git": (git.stdout.strip() if git and git.returncode == 0 else None),
               "herramientas": {n: bool(shutil.which(n)) for n in ("git", "python3", "gh", "ssh", "node", "docker", "jq")},
               "doctor": [{"nivel": n, "texto": t, "accion": ac} for n, t, ac in filas],
               "resumen": {"problemas": sum(1 for f in filas if f[0] == "problema"), "total": len(filas)}}
    if instancia and (Path(instancia) / "harness.lock").exists():
        paquete["instancia"] = estado(instancia, raiz)
    lock = Path(instancia or ".") / "entorno.lock.json"
    if lock.is_file():
        try:
            d = json.loads(lock.read_text(encoding="utf-8"))
            paquete["entorno_propio"] = {"generador": d.get("generador"), "fecha": d.get("fecha"),
                                         "modulos": d.get("opciones", {}).get("modulos"), "archivos": len(d.get("archivos", {}))}
        except (OSError, ValueError):
            paquete["entorno_propio"] = {"error": "entorno.lock.json ilegible"}
    return redactar(paquete)


def mostrar_doctor(filas, out):
    marca = {"ok": "OK       ", "info": "INFO     ", "problema": "PROBLEMA "}
    col = {"ok": "32", "info": "36", "problema": "31"}
    for nivel, texto, accion in filas:
        out.p(out.e(marca[nivel], col[nivel]) + texto)
        if nivel == "problema" and not accion:
            accion = "revisa el detalle de arriba y vuelve a correr `harness doctor`"   # ningún problema se muestra sin siguiente paso
        if accion:
            out.p("          Siguiente: " + accion)
    n = sum(1 for f in filas if f[0] == "problema")
    out.p("\nRESULTADO: " + ("todo bien" if n == 0 else f"{n} problema(s)"))
    return 1 if n else 0


def estado(instancia, raiz=RAIZ):
    instancia = Path(instancia).resolve()
    e = {"instancia": str(instancia), "existe": instancia.is_dir(), "es_instancia": (instancia / "harness.lock").exists()}
    if not e["es_instancia"]:
        return e
    lock = tomllib.loads((instancia / "harness.lock").read_text(encoding="utf-8"))
    e["version_instancia"] = lock.get("version")
    e["fuente"] = lock.get("fuente")
    e["version_harness"] = (Path(raiz) / "VERSION").read_text(encoding="utf-8").strip()
    est = None
    try:
        est = json.loads((instancia / ".harness" / "estado.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    if est:
        e["partida"] = est.get("partida")
        e["modo"] = NOMBRE_MODO.get(est.get("partida"), "?")
        arch = est.get("archivos", {})
        e["instalados"] = sorted(arch)
        mod = []
        for ruta, meta in arch.items():
            p = instancia / ruta
            if not p.exists():
                mod.append(f"{ruta} (borrado)")
            elif sha(p.read_text(encoding="utf-8")) != meta.get("sha256"):
                mod.append(f"{ruta} (modificado localmente)")
        e["modificados"] = mod
    piso = instancia / ".harness" / "piso.md"
    e["piso"] = []
    if piso.exists():
        for linea in piso.read_text(encoding="utf-8").splitlines():
            c = [x.strip() for x in linea.strip().strip("|").split("|")]
            if linea.startswith("|") and len(c) == 3 and c[1] in ("instalado", "pendiente", "requiere confirmacion", "requiere confirmación"):
                e["piso"].append({"punto": c[0], "estado": c[1], "detalle": c[2]})
    e["pendiente"] = [p for p in e["piso"] if p["estado"] != "instalado"]
    s = Sesion.leer(instancia / ".harness" / "sesion.json")
    e["sesion"] = (s or {}).get("estado")
    return e


def mostrar_estado(e, out):
    if not e["es_instancia"]:
        if not e.get("existe", True):
            out.p(f"La carpeta {e['instancia']} no existe. Indica la carpeta de tu instancia (`harness estado <instancia>`) "
                  "o corre `harness` para armar una; `harness siguiente` te dice qué sigue.")
            return 1
        out.p(f"{e['instancia']} no es una instancia instalada (no tiene harness.lock). Corre `harness` para armarla.")
        return 1
    out.p(f"Instancia: {e['instancia']}")
    out.p(f"Modo: {e.get('modo', '?')} (partida {e.get('partida', '?')})")
    out.p(f"Versión: la instancia fija {e['version_instancia']}; harness local {e['version_harness']}")
    out.p(f"Instalado: {len(e.get('instalados', []))} archivo(s) del instalador")
    for m in e.get("modificados", []):
        out.p("  Cambió después de instalar: " + m)
    out.p("Piso (spec 7.2):")
    for p in e["piso"]:
        out.p(f"  [{p['estado']}] {p['punto']}" + ("" if p["estado"] == "instalado" else f": {p['detalle']}"))
    if not e["piso"]:
        out.p("  (sin .harness/piso.md: vuelve a correr el instalador)")
    out.p("Pendiente: " + (f"{len(e['pendiente'])} punto(s) del piso" if e["pendiente"] else "nada del piso"))
    if e.get("sesion") == "en_curso":
        out.p("Hay una sesión del asistente sin terminar: corre `harness` para retomarla.")
    return 0


# ------------------------------------------------------------------ siguiente (dónde estoy y qué sigue)
def cargar_trazabilidad(raiz):
    """Carga herramientas/harness-trazabilidad.py como módulo (solo lectura). None si no está."""
    ruta = Path(raiz) / "herramientas" / "harness-trazabilidad.py"
    if not ruta.is_file():
        return None
    esp = importlib.util.spec_from_file_location("harness_trazabilidad", ruta)
    mod = importlib.util.module_from_spec(esp)
    esp.loader.exec_module(mod)
    return mod


def _version(t):
    try:
        return tuple(int(x) for x in str(t).strip().split("."))
    except ValueError:
        return None


SIGUIENTE_POR_ETAPA = {
    "especificacion": "completa la especificación (plantillas/especificacion.md)",
    "delegacion": "aprueba la especificación y delega con contrato de archivos (plantillas/delegacion.md)",
    "implementacion": "completa la matriz de trazabilidad (plantillas/matriz-trazabilidad.md)",
    "cierre": "completa el cierre (plantillas/cierre-de-cambio.md)",
}


def siguiente(base, raiz=RAIZ):
    """Estado de solo lectura de una carpeta y lista ordenada de pasos sugeridos. No escribe nada."""
    base = Path(base).expanduser().resolve()
    raiz = Path(raiz)
    r = {"carpeta": str(base), "existe": base.is_dir(), "es_instancia": False, "pasos": [], "cambios": [], "cambios_cerrables": 0}
    try:
        r["version_harness"] = (raiz / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        r["version_harness"] = "?"
    if not r["existe"]:
        r["pasos"].append({"que": "La carpeta no existe: indica la de tu instancia o proyecto", "comando": "harness siguiente <carpeta>"})
        return r
    if not (base / "harness.lock").exists():
        if (base / "especificacion.md").is_file():
            r["pasos"].append({"que": "Esta carpeta parece un cambio: comprueba su trazabilidad", "comando": f"harness trazar {base}"})
            return r
        d = detectar_caso(base)
        r["caso"], r["confianza"], r["porque"] = d["caso"], d["confianza"], d["porque"]
        r["pasos"].append({"que": f"No es una instancia del harness. Parece el caso {NOMBRE_CASO[d['caso']]} ({d['porque']})"
                                  + ("; confírmalo con --caso" if d["confianza"] == "duda" else ""),
                           "comando": f"harness --carpeta {base} --no-interactivo" if d["confianza"] == "alta" else f"harness --carpeta {base}"})
        r["pasos"].append({"que": "El asistente muestra el plan y no escribe nada hasta tu «s»", "comando": f"harness --carpeta {base}"})
        return r
    e = estado(base, raiz)
    r["es_instancia"] = True
    r["version_instancia"], r["modo"] = e.get("version_instancia"), e.get("modo")
    vi, vh = _version(e.get("version_instancia")), _version(r["version_harness"])
    if vi and vh and vi < vh:
        r["pasos"].append({"que": f"La instancia fija {e['version_instancia']} y el harness está en {r['version_harness']}: actualiza (muestra el plan)", "comando": f"harness update {base}"})
    elif vi and vh and vi > vh:
        r["pasos"].append({"que": f"La instancia fija {e['version_instancia']}, más nueva que este harness ({r['version_harness']}): actualiza el harness local", "comando": "git -C <harness> pull"})
    for m in e.get("modificados", []):
        r["pasos"].append({"que": "Cambió después de instalar (el update no lo pisa): " + m, "comando": f"harness estado {base}"})
    for p in e.get("pendiente", []):
        r["pasos"].append({"que": f"Piso pendiente — {p['punto']}: {p['detalle']}", "comando": f"harness estado {base}"})
    try:
        est = json.loads((base / ".harness" / "estado.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        est = {}
    if est and "montaje" not in est:
        r["pasos"].append({"que": "Falta montar el entorno de los agentes (AGENTS.md, skills, permisos): muestra el plan primero", "comando": f"harness montar {base}"})
    if e.get("sesion") == "en_curso":
        r["pasos"].append({"que": "Hay una sesión del asistente sin terminar", "comando": "harness"})
    tz = cargar_trazabilidad(raiz)
    carpeta_cambios = base / "cambios"
    if tz and carpeta_cambios.is_dir():
        for c in sorted(p for p in carpeta_cambios.iterdir() if p.is_dir() and not p.name.startswith(".")):
            etapa, inf = tz.estado_del_cambio(c)
            if etapa == "cerrable":
                r["cambios_cerrables"] += 1
                continue
            primero = next((h for h in inf["hallazgos"] if h["nivel"] == "ERROR"), None)
            r["cambios"].append({"cambio": c.name, "etapa": etapa, "errores": inf["resumen"]["errores"],
                                 "primer_error": f"{primero['codigo']} {primero['donde']}: {primero['mensaje']}" if primero else ""})
        for c in r["cambios"][:10]:
            r["pasos"].append({"que": f"Cambio «{c['cambio']}» ({c['errores']} error(es) en la puerta de {c['etapa']}): {SIGUIENTE_POR_ETAPA[c['etapa']]}. Primero: {c['primer_error']}",
                               "comando": f"harness trazar {carpeta_cambios / c['cambio']} --etapa {c['etapa']}"})
    if not r["pasos"]:
        r["pasos"].append({"que": "Nada pendiente. Para empezar un cambio con trazabilidad, copia plantillas/especificacion.md a cambios/<fecha>-<slug>/", "comando": "harness trazar cambios/<fecha>-<slug> --etapa especificacion"})
    return r


def mostrar_siguiente(r, out):
    out.p(f"Dónde estoy: {r['carpeta']}")
    if not r["existe"]:
        pass
    elif r["es_instancia"]:
        out.p(f"  Instancia del harness (modo {r.get('modo', '?')}, fija {r.get('version_instancia')}; harness local {r['version_harness']})")
        if r["cambios_cerrables"]:
            out.p(f"  Cambios sin errores hasta el cierre: {r['cambios_cerrables']}")
    out.p("Qué sigue:")
    for i, p in enumerate(r["pasos"], 1):
        out.p(f"  {i}. {p['que']}")
        if p.get("comando"):
            out.p(f"       {p['comando']}")
    out.p("(Solo lectura: este comando no escribió nada. Mapa completo: docs/MAPA-DE-COMANDOS.md)")
    return 0 if r["existe"] else 1


def cmd_trazar(a, out, raiz):
    herramienta = Path(raiz) / "herramientas" / "harness-trazabilidad.py"
    if not herramienta.is_file():
        raise Detener(f"No encuentro {herramienta}. Actualiza el harness (`harness update`) o indica la raíz con --harness.", 2)
    cambio = Path(a.cambio).expanduser() if a.cambio else Path(os.getcwd())
    if not a.cambio and not (cambio / "especificacion.md").is_file():
        raise Detener("Esta carpeta no parece la de un cambio (falta especificacion.md).\n"
                      "Indica la carpeta: `harness trazar cambios/<fecha>-<slug>`\n"
                      f"Para ver cómo es uno completo: `harness trazar {Path(raiz) / 'plantillas' / 'ejemplos' / 'cambio-ejemplo'}`", 2)
    cmd = [sys.executable, herramienta, cambio, "--etapa", a.etapa]
    if a.repo:
        cmd += ["--repo", a.repo]
    if a.json:
        cmd.append("--json")
    r = correr(cmd)
    out.p((r.stdout + r.stderr).rstrip())
    return r.returncode


def erp_base_registrado(raiz):
    """Ruta del ERP estándar registrado como fuente (herramientas/harness-aprender.py); None si no hay."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("harness_aprender_reg", Path(raiz) / "herramientas" / "harness-aprender.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.erp_base_registrado()
    except Exception:
        return None


def cmd_aprender(a, out, raiz):
    """Delega en herramientas/harness-aprender.py (fuentes, escanear, listar, ver, descartar, promover). No sube nada."""
    herramienta = Path(raiz) / "herramientas" / "harness-aprender.py"
    if not herramienta.is_file():
        raise Detener(f"No encuentro {herramienta}. Actualiza el harness (`harness update`) o indica la raíz con --harness.", 2)
    args = list(a.args or [])
    if args and args[0] == "--":
        args = args[1:]
    if not args:
        args = ["listar"]
    r = correr([sys.executable, herramienta, *args])
    out.p((r.stdout + r.stderr).rstrip())
    return r.returncode


def cmd_entorno(a, out, raiz):
    """Delega en herramientas/harness-entorno.py: genera un entorno INDEPENDIENTE (sin enlace con el harness).
    Sin --aplicar solo muestra el plan."""
    herramienta = Path(raiz) / "herramientas" / "harness-entorno.py"
    if not herramienta.is_file():
        raise Detener(f"No encuentro {herramienta}. Actualiza el harness (`harness update`) o indica la raíz con --harness.", 2)
    if a.comparar:
        args = ["--comparar", a.comparar] + (["--aplicar-seguras"] if a.aplicar_seguras else [])
    else:
        args = ["--listar"] if (a.listar or not (a.nombre or a.destino or a.modulos)) else [
            "--nombre", a.nombre or "", "--destino", a.destino or "", "--modulos", a.modulos or "",
            "--agentes", a.agentes, "--perfiles", a.perfiles] + (["--aplicar"] if a.aplicar else [])
    r = correr([sys.executable, herramienta, *args])
    out.p((r.stdout + r.stderr).rstrip())
    return r.returncode


# ------------------------------------------------------------------ instalar / update
DESCARGADORES = []
"""PUNTO DE EXTENSION de la descarga remota (otro agente). Cada elemento es una funcion `f(origen: str) -> Path | None`
que, si reconoce `origen` (URL, owner/repo, ssh), comprueba el permiso de lectura con las credenciales existentes
(sin pedirlas ni guardarlas, spec 19), descarga la instancia y devuelve la carpeta local; si no lo reconoce devuelve
None; si no hay permiso, lanza `Detener(mensaje_con_que_pedir_y_a_quien, 2)`."""


def parece_remoto(origen):
    return "://" in origen or origen.startswith("git@") or origen.endswith(".git")


def resolver_instancia(origen):
    p = Path(origen).expanduser()
    if p.is_dir() or (not parece_remoto(origen) and not p.exists()):
        return p.resolve()
    for d in DESCARGADORES:
        r = d(origen)
        if r:
            return Path(r).resolve()
    raise Detener(f"«{origen}» no es una carpeta local y la descarga remota todavía no está disponible en esta versión. "
                  "Clona el repositorio con tus propias credenciales y pasa la carpeta: `harness instalar <carpeta>`.", 2)


HOOKS_REMOTO = {}
"""Dobles para pruebas de la descarga remota: claves opcionales `comprobar`, `ejecutar`, `es_terminal`, `preguntar`
(se pasan tal cual a instalar-instancia.py)."""
CRED_URL = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^/\s@]+@")
OWNER_NOMBRE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_.-]+$")
SIN_LLAVE_NI_SESION = re.compile(r"(?i)permission denied|publickey|could not read (username|password)|terminal prompts disabled|"
                                 r"authentication failed|host key verification|denied")


def limpiar_url(t):
    return CRED_URL.sub(r"\1", t or "")


def es_repositorio(origen):
    """True si `origen` parece un repositorio y no una carpeta local existente."""
    if Path(origen).expanduser().is_dir():
        return False
    if origen.startswith(("https://", "ssh://", "http://", "git@")):
        return True
    return bool(OWNER_NOMBRE.fullmatch(origen)) and not origen.startswith(("./", "../", "~"))


def resolver_repositorio(origen, out):
    """owner/nombre -> git@github.com:owner/nombre.git (avisando). Limpia usuario:token@ de las URL."""
    if OWNER_NOMBRE.fullmatch(origen) and "://" not in origen:
        url = f"git@github.com:{origen}.git"
        out.p(f"Aviso: «{origen}» se interpretó como {url} (GitHub por SSH, con tu llave existente). "
              "Si es otro servidor, pasa la URL completa.")
        return url
    limpia = limpiar_url(origen)
    if limpia != origen:
        out.p("Aviso: se descartó el usuario:token de la URL; se usan las credenciales que ya tienes en el sistema.")
    return limpia


def cargar_instalar_instancia(raiz):
    import importlib.util
    ruta = Path(raiz) / "instalador" / "instalar-instancia.py"
    spec = importlib.util.spec_from_file_location("instalar_instancia_mh", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def instalar_remoto(a, out, raiz):
    """Descarga una instancia privada con instalar-instancia.py: acceso ANTES de clonar, plan, confirmación, clon y `update`."""
    url = resolver_repositorio(a.instancia, out)
    mod = cargar_instalar_instancia(raiz)
    hooks = dict(HOOKS_REMOTO)
    comprobar = hooks.pop("comprobar", mod.acceso_por_defecto)
    visto = {}

    def comprobar_anotando(repo):
        ok, motivo = comprobar(repo)
        visto["ok"], visto["motivo"] = ok, motivo or ""
        return ok, motivo

    argv = [url] + (["--destino", a.destino] if a.destino else []) + (["--si"] if a.si else [])
    flujo = out.flujo
    codigo = mod.main(argv, comprobar=comprobar_anotando, raiz=Path(raiz), salida=flujo, **hooks)
    if codigo == 3 and SIN_LLAVE_NI_SESION.search(visto.get("motivo", "")):
        out.p("Si te falta llave o sesión de GitHub, prepara el acceso primero (no lo ejecuto yo; revisa el plan):")
        out.p(f"  bash {Path(raiz) / 'instalador' / 'acceso-github.sh'} --repositorio {limpiar_url(url)}")
        out.p("  (sin --aplicar solo muestra el plan; con --aplicar pide confirmación en cada paso). Después repite este comando.")
    return codigo


HOOKS_ORQ = {}
"""Dobles para pruebas del flujo completo: claves opcionales `sistema`, `preguntar`, `acceso`, `hooks_clonar`, `doctor`
(se pasan tal cual a instalador/orquestador.py)."""


def instalar_completo(a, out, raiz):
    """UN solo comando: paquetes, acceso a GitHub, clon, entorno de la instancia y doctor, con un plan y reanudable."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("orquestador_mh", Path(raiz) / "instalador" / "orquestador.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    argv = [a.instancia] + (["--destino", a.destino] if a.destino else []) + (["--si"] if a.si else []) \
        + (["--plan"] if getattr(a, "plan", False) else [])
    return mod.main(argv, salida=out.flujo, raiz=Path(raiz), **HOOKS_ORQ)


def delegar_instalador(raiz, modo, instancia, extra, out):
    cmd = [sys.executable, Path(raiz) / "instalador" / "harness_instalar.py", modo, instancia, "--harness", raiz] + extra
    r = correr(cmd)
    out.p((r.stdout + r.stderr).rstrip())
    return r.returncode


def cmd_instalar(a, out, raiz):
    if es_repositorio(a.instancia):
        if HOOKS_REMOTO or getattr(a, "solo_clonar", False):   # HOOKS_REMOTO: dobles del flujo corto (solo clonar)
            return instalar_remoto(a, out, raiz)
        return instalar_completo(a, out, raiz)
    instancia = resolver_instancia(a.instancia)
    modo = a.modo or ("update" if (instancia / "harness.lock").exists() else NOMBRE_MODO.get(a.partida or "B", "init"))
    extra = []
    for flag, val in (("--partida", a.partida), ("--acceso", a.acceso), ("--politica", a.politica), ("--proyecto", a.proyecto)):
        if val:
            extra += [flag, val]
    for flag, val in (("--aceptar-degradado", a.aceptar_degradado), ("--aceptar-dentro-de-repo", a.aceptar_dentro_de_repo), ("--aplicar", a.aplicar)):
        if val:
            extra.append(flag)
    if modo == "update":
        extra = [x for x in extra if x not in ("--partida",)]
        if a.partida:
            extra = [x for x in extra if x != a.partida]
    return delegar_instalador(raiz, modo, instancia, extra, out)


def cmd_montar(a, out, raiz):
    """Monta el entorno de los agentes sobre una instancia ya creada. Hereda la terminal: el montaje hace sus propias preguntas."""
    instancia = resolver_instancia(a.instancia or os.getcwd())
    cmd = [sys.executable, str(Path(raiz) / "instalador" / "montaje.py"), str(instancia)]
    if a.agentes:
        cmd += ["--agentes", a.agentes]
    for flag, val in (("--aplicar", a.aplicar), ("--si", a.si), ("--json", a.json)):
        if val:
            cmd.append(flag)
    return subprocess.run(cmd).returncode


def cmd_update(a, out, raiz):
    instancia = Path(a.instancia or os.getcwd()).expanduser().resolve()
    if not instancia.is_dir():
        raise Detener(f"No existe la carpeta {instancia}.\nIndica la carpeta de una instancia ya instalada (`harness update <instancia>`). "
                      "Para crear una: `harness` (asistente) o `harness instalar <instancia> --modo init`.", 2)
    return delegar_instalador(raiz, "update", instancia, ["--aplicar"] if a.aplicar else [], out)


# ------------------------------------------------------------------ erp (opción D: proponer los módulos del ERP estándar)
def cargar_erp(raiz):
    """Carga herramientas/harness-erp.py como módulo. Detiene con el remedio si no está."""
    ruta = Path(raiz) / "herramientas" / "harness-erp.py"
    if not ruta.is_file():
        raise Detener(f"No encuentro {ruta}. Actualiza el harness (`harness update`) o indica la raíz con --harness.", 2)
    esp = importlib.util.spec_from_file_location("harness_erp", ruta)
    mod = importlib.util.module_from_spec(esp)
    esp.loader.exec_module(mod)
    return mod


def _dentro(hijo, padre):
    try:
        Path(hijo).resolve().relative_to(Path(padre).resolve())
        return True
    except ValueError:
        return False


def cmd_erp(a, out, raiz, entrada=None, interactivo=False):
    """`harness erp`: lee los documentos del negocio (solo archivos locales), propone producto y módulos del ERP con su estado real y,
    solo con tu confirmación, deja la propuesta en la instancia. No instala ni copia nada del ERP, no usa la red ni un modelo de lenguaje."""
    erp = cargar_erp(raiz)
    pregunta = entrada or input

    def preguntar(texto):
        r = pregunta(texto + " ").strip()
        if r and parece_secreto(r):
            raise Detener("Lo que escribiste parece un secreto (contraseña, token o clave): no lo uso. Indica una ruta de carpeta.", 2)
        return r

    try:
        negocio = a.negocio
        if not negocio:
            if not interactivo:
                raise Detener("Falta indicar la carpeta con los documentos del negocio: `harness erp --negocio <carpeta> --erp-base <ruta>`.\n"
                              "Es una carpeta local con archivos .md, .txt, .csv o .xlsx (por ejemplo, exportados de Drive u otra fuente); no leo nada más ni uso la red.", 2)
            negocio = preguntar("¿Qué carpeta con documentos del negocio debo leer? (archivos .md, .txt, .csv o .xlsx exportados; solo lectura, sin red):")
        if not negocio:
            raise Detener("Sin carpeta de documentos no puedo proponer nada: no adivino de dónde leer. Repite con `--negocio <carpeta>`.", 2)
        negocio = Path(negocio).expanduser().resolve()
        if not negocio.is_dir():
            raise Detener(f"No existe la carpeta de documentos {negocio}.\nIndica una carpeta local con los documentos del negocio.", 2)
        erp_base = a.erp_base or erp_base_registrado(raiz)
        if erp_base and not a.erp_base:
            out.p(f"Uso el ERP estándar registrado: {erp_base} (se cambia con `harness aprender fuentes`).")
        if not erp_base:
            if not interactivo:
                raise Detener("Falta indicar dónde está el ERP estándar: `--erp-base <ruta>` (la carpeta del repositorio del ERP; solo se lee su `modulos/catalogo.json`).", 2)
            erp_base = preguntar("¿Dónde está la carpeta del ERP estándar (erp-base)? (solo lectura):")
        if not erp_base:
            raise Detener("Sin la ruta del ERP no tengo el catálogo de módulos. Repite con `--erp-base <ruta>`.", 2)
        erp_base = Path(erp_base).expanduser().resolve()
        instancia = a.instancia
        if not instancia and interactivo and not a.json:
            instancia = preguntar("¿En qué carpeta de instancia dejo la propuesta? (Enter = solo mostrarla, sin escribir):")
        instancia = Path(instancia).expanduser().resolve() if instancia else None
        if instancia:
            if _dentro(instancia, negocio):
                raise Detener("La instancia no puede estar dentro de la carpeta de documentos del negocio: esos documentos se leen sin modificarlos "
                              "(y la propuesta escrita ahí se leería como si fuera un documento del negocio).", 2)
            if _dentro(instancia, erp_base):
                raise Detener("La instancia no puede estar dentro del ERP estándar: ese repositorio es de solo lectura para el harness.", 2)
            if not instancia.is_dir():
                raise Detener(f"No existe la carpeta de la instancia {instancia}.\nCrea la instancia primero (`harness` o `harness instalar <instancia> --modo init`) o indica otra.", 2)
        senales = Path(a.senales).expanduser() if a.senales else Path(raiz) / "perfiles" / "_erp" / "senales.toml"
        try:
            p = erp.generar(negocio, erp_base, senales, raiz, marca_en_instancia=((instancia / "sitio" / "DISENO.md").is_file() if instancia else None))
        except erp.ErrorErp as e:
            raise Detener(f"{e}", 2)
        plan = erp.estado_escritura(instancia, p) if instancia else []
        etiqueta = {"crear": "crearía", "actualizar": "actualizaría", "igual": "ya está igual", "conservar": "ya existe; no lo piso"}
        if not a.json:
            out.titulo("Propuesta de ERP (solo lectura: no se instaló ni copió nada)")
            out.p(erp.resumen_pantalla(p))
            if instancia:
                out.p("\nEn la instancia (" + str(instancia) + "):")
                for rel, accion in plan:
                    out.p(f"  - {etiqueta[accion]}: {rel}")
        escribir_ya = bool(instancia) and (a.aplicar or a.si)
        if instancia and not escribir_ya:
            if interactivo and not a.json:
                r = preguntar("\n¿Escribo la propuesta en la instancia? [s/N]")
                escribir_ya = r.strip().lower() in SI
            elif not a.json:
                out.p("\nSin terminal y sin --aplicar: no escribí nada. Repite con --aplicar para dejar la propuesta en la instancia.")
        hechas = []
        if escribir_ya:
            try:
                hechas = erp.escribir(instancia, p)
            except erp.ErrorErp as e:
                raise Detener(f"{e}", 2)
        if a.json:
            print(json.dumps({"propuesta": p, "escritura": {"aplicado": bool(hechas), "archivos": [{"ruta": r, "accion": ac} for r, ac in (hechas or plan)]}},
                             ensure_ascii=False, indent=2), file=out.flujo)
            return 0
        if not instancia:
            out.p("\nNo indicaste instancia, así que no escribí nada. Para dejar la propuesta: `harness erp --negocio ... --erp-base ... --instancia <carpeta>`.")
        elif hechas:
            out.p("\nListo:")
            hecho = {"crear": "creado", "actualizar": "actualizado", "igual": "sin cambios", "conservar": "conservado (ya existía)"}
            for rel, accion in hechas:
                out.p(f"  - {hecho[accion]}: {rel}")
            out.p("Siguiente: revisa erp/propuesta-erp.md, confirma o quita módulos y comprueba el rastro con "
                  f"`harness trazar {instancia / 'cambios' / erp.SLUG_CAMBIO} --etapa especificacion`. El compositor del ERP aún no existe: no se instaló nada.")
        elif interactivo:
            out.p("\nNo escribí nada.")
        return 0
    except (KeyboardInterrupt, EOFError):
        out.p("\nInterrumpido. No se escribió nada.")
        return 130


# ------------------------------------------------------------------ línea de comandos
AYUDA = """Qué comando uso cuándo (mapa completo: docs/MAPA-DE-COMANDOS.md)

  1. INSTALAR en una máquina nueva (replica la instancia de tu equipo)
       harness instalar owner/nombre            plan completo y una sola confirmación
       harness instalar owner/nombre --plan     solo muestra el plan
  2. ADOPTAR un proyecto que ya existe (no toca tu código ni tu estándar)
       harness                                  el asistente detecta el caso A y propone «adopt»
       harness instalar <instancia> --modo adopt --proyecto <carpeta>
  3. EMPEZAR un proyecto nuevo (B), replicar un sistema (C) o usar un ERP estándar (D)
       harness                                  el asistente pregunta lo justo
       harness instalar <instancia> --modo init      (o --modo migrar)
       harness erp --negocio <carpeta> --erp-base <ruta>   propone los módulos del ERP que tu negocio necesita
  4. TRABAJAR una tarea (cada cambio deja su rastro de punta a punta)
       harness siguiente [instancia]            dónde estoy y qué sigue (solo lectura)
       harness trazar <cambio> [--etapa E]      comprueba requisito -> prueba -> commit -> evidencia
  5. VERIFICAR
       harness doctor [instancia]               versión, frescura, herramientas y secretos
       harness estado [instancia]               qué hay instalado y qué falta del piso
  6. ACTUALIZAR
       harness update [instancia]               muestra el plan; con --aplicar escribe
       harness montar [instancia]               entorno de los agentes; con --aplicar escribe
  7. APRENDER (lo que se aprende en un proyecto no se repite en el siguiente)
       harness aprender fuentes agregar <nombre> <ruta> --tipo erp|instancia   registra de dónde aprender (solo lectura)
       harness aprender escanear                separa lo general de lo del negocio y arma la cola
       harness aprender listar | ver <id> | descartar <id> --motivo ... | promover <id> --tipo estandar [--aplicar]
       harness entorno --listar                 módulos que puede llevar un entorno propio e independiente
       harness entorno --nombre N --destino D --modulos a,b [--agentes claude,codex] [--aplicar]
       harness entorno --comparar <carpeta> [--aplicar-seguras]   qué cambió el generador y qué cambiaste tú (nunca pisa lo tuyo)

Nada se escribe sin --aplicar o sin responder «s» a la confirmación. Cada comando acepta -h.
Códigos de salida: 0 bien · 1 problema o error · 2 detenido (falta algo; el mensaje dice qué) · 130 interrumpido."""

EJEMPLOS = {
    "instalar": "harness instalar mi-equipo/mi-instancia --plan\n  harness instalar mi-equipo/mi-instancia\n  harness instalar ./mi-instancia --modo adopt --proyecto ./mi-proyecto",
    "update": "harness update ./mi-instancia            (muestra el plan)\n  harness update ./mi-instancia --aplicar",
    "montar": "harness montar ./mi-instancia --agentes claude-code\n  harness montar ./mi-instancia --aplicar",
    "doctor": "harness doctor\n  harness doctor ./mi-instancia --json\n  harness doctor --bundle    (paquete para pegar a quien te ayuda, sin secretos)",
    "estado": "harness estado ./mi-instancia",
    "siguiente": "harness siguiente\n  harness siguiente ./mi-instancia --json",
    "erp": "harness erp --negocio ./documentos-del-negocio --erp-base ./erp-base              (solo muestra la propuesta)\n  harness erp --negocio ./documentos-del-negocio --erp-base ./erp-base --instancia ./mi-instancia --aplicar",
    "trazar": "harness trazar cambios/2026-01-10-entregas-parciales\n  harness trazar cambios/2026-01-10-entregas-parciales --etapa delegacion\n  harness trazar cambios/2026-01-10-entregas-parciales --repo ./mi-proyecto",
    "entorno": "harness entorno --listar\n  harness entorno --nombre mi-entorno --destino ~/mi-entorno --modulos documentacion-primero,compuerta-calidad,autoguardado\n  (añade --aplicar para escribirlo)",
    "aprender": "harness aprender fuentes agregar erp-base ./erp-base --tipo erp\n  harness aprender escanear\n  harness aprender listar\n  harness aprender promover <id> --tipo estandar --aplicar",
}
DESCRIPCION = {
    "instalar": "Instala una instancia: carpeta local o repositorio (https://, ssh://, git@host:ruta u owner/nombre).",
    "update": "Actualiza lo del harness en una instancia ya instalada (sin --aplicar solo muestra el plan).",
    "montar": "Monta el entorno de los agentes sobre una instancia creada (AGENTS.md, skills, permisos).",
    "doctor": "Comprueba versión, frescura de documentos, herramientas y accesos con aspecto de secreto.",
    "estado": "Muestra modo, versión, qué hay instalado, qué cambió después y qué falta del piso.",
    "siguiente": "Dónde estoy y qué sigue: estado de la carpeta o instancia y pasos sugeridos, en orden. Solo lectura.",
    "trazar": "Comprueba la trazabilidad de un cambio (especificación, delegación, matriz, cierre). Solo lectura.",
    "entorno": "Entorno propio: genera un repositorio independiente (hooks, compuerta, autoguardado, aprendizaje con evidencia) que otra persona usa SIN el meta-harness. Sin --aplicar solo muestra el plan.",
    "aprender": "Aprendizaje: registra fuentes (un ERP central, una instancia), separa lo general de lo del negocio y deja una cola de aportes para revisar. Nunca sube nada.",
    "erp": "Opción ERP: lee los documentos del negocio (archivos locales), propone producto y módulos del ERP estándar con su estado real y, solo si confirmas, deja la propuesta en la instancia. No instala ni copia nada del ERP.",
}
TRADUCCIONES = (("the following arguments are required: ", "falta indicar: "), ("unrecognized arguments: ", "argumentos no reconocidos: "),
                ("expected one argument", "falta el valor de la opción"), ("invalid choice: ", "opción no válida: "))


class Parser(argparse.ArgumentParser):
    """ArgumentParser con errores en español y ejemplos al pie; mismo código de salida (2)."""

    def __init__(self, *args, ejemplos=None, **kw):
        super().__init__(*args, **kw)
        self.ejemplos = ejemplos

    def error(self, mensaje):
        for en, es in TRADUCCIONES:
            mensaje = mensaje.replace(en, es)
        self.print_usage(sys.stderr)
        extra = f"\nEjemplos:\n  {self.ejemplos}\n" if self.ejemplos else ""
        self.exit(2, f"{self.prog}: error: {mensaje}\n{extra}\nQué comando uso cuándo: `harness ayuda`\n")


DESCRIPCION_ASISTENTE = ("Asistente del harness (`harness` sin comando): mira la carpeta, detecta el caso (A/B/C), pregunta lo justo "
                         "y no escribe sin tu confirmación.")


class ParserAsistente(Parser):
    """Ayuda del comando raíz: primero el mapa «qué comando uso cuándo» (por momento) y después las opciones técnicas del asistente.

    Decisión 2026-10-09: quien llega a `harness -h` busca qué comando usar, no la lista de banderas. El significado de los comandos no cambia.
    """

    def format_help(self):
        return AYUDA + "\n\n" + DESCRIPCION_ASISTENTE + "\n\nOpciones técnicas del asistente:\n\n" + super().format_help()


def parser_asistente():
    p = ParserAsistente(prog="harness", formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--carpeta", help="carpeta a mirar (por defecto, la actual)")
    p.add_argument("--si", action="store_true", help="acepta el plan y lo aplica (sin preguntar)")
    p.add_argument("--json", action="store_true", help="salida en JSON (no interactivo)")
    p.add_argument("--no-interactivo", action="store_true", help="no pregunta: muestra el plan y sale sin escribir")
    p.add_argument("--caso", choices=("A", "B", "C", "a", "b", "c"), help="fija el caso sin detectarlo")
    p.add_argument("--instancia", help="carpeta de la instancia")
    p.add_argument("--acceso", help="acceso.local.toml (caso A)")
    p.add_argument("--politica", help="politicas.toml")
    p.add_argument("--documentacion", help="caso B: carpeta con la información de partida")
    p.add_argument("--origen", help="caso C: carpeta con el origen")
    p.add_argument("--aceptar-degradado", action="store_true")
    p.add_argument("--aceptar-dentro-de-repo", action="store_true")
    p.add_argument("--harness", help="raíz del harness (por defecto, este)")
    return p


def main(argv=None, entrada=None, salida=None, interactivo=None, raiz=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    salida = salida or sys.stdout
    raiz = Path(raiz or RAIZ)
    sub = argv[0] if argv and argv[0] in SUBCOMANDOS else None
    if sub is None and argv and not argv[0].startswith("-"):
        # El asistente no recibe palabras sueltas: es un comando mal escrito. Se dice cuál se parece (mismo código de salida: 2).
        cerca = difflib.get_close_matches(argv[0], SUBCOMANDOS, n=1, cutoff=0.5)
        print(f"harness: no existe el comando «{argv[0]}»." + (f" ¿Quisiste decir `harness {cerca[0]}`?" if cerca else "")
              + "\nComandos: " + ", ".join(SUBCOMANDOS) + ".\nQué comando uso cuándo: `harness ayuda` (o `harness -h`).", file=sys.stderr)
        return 2
    try:
        if sub is None:
            a = parser_asistente().parse_args(argv)
            if a.harness:
                raiz = Path(a.harness).expanduser().resolve()
            a.caso = a.caso.upper() if a.caso else None
            sin_terminal = a.no_interactivo or a.json
            if interactivo is None:
                interactivo = sys.stdin.isatty() and sys.stdout.isatty()
            interactivo = bool(interactivo) and not sin_terminal
            out = Salida(salida, callar=a.json)
            asist = Asistente(a, entrada or input, out, interactivo, raiz)
            try:
                codigo = asist.correr()
            except Detener as e:
                asist.informe["detenido"] = str(e)
                asist.informe["codigo"] = e.codigo
                if a.json:
                    asist.informe["aplicado"] = False
                else:
                    print(str(e), file=sys.stderr if e.codigo == 1 else salida)
                codigo = e.codigo
            except (KeyboardInterrupt, EOFError) as e:
                ruta = asist.sesion.ruta
                print("\n\nInterrumpido. No se instaló nada."
                      + (f" Tu avance (sin secretos) quedó en {ruta}; vuelve a correr `harness` para continuar." if ruta and ruta.exists()
                         else " No guardé avance porque todavía no habías elegido la carpeta de la instancia."), file=salida)
                return 130 if isinstance(e, KeyboardInterrupt) else 1
            if a.json:
                inf = {k: v for k, v in asist.informe.items() if k != "pasos"}
                inf.setdefault("aplicado", False)
                print(json.dumps(inf, ensure_ascii=False, indent=2), file=salida)
            return codigo
        p = Parser(prog="harness " + sub, ejemplos=EJEMPLOS.get(sub), description=DESCRIPCION.get(sub, ""),
                   epilog=("Ejemplos:\n  " + EJEMPLOS[sub]) if sub in EJEMPLOS else None, formatter_class=argparse.RawDescriptionHelpFormatter)
        p.add_argument("--harness", help="raíz del harness")
        if sub == "instalar":
            p.add_argument("instancia", help="carpeta local, o repositorio (https://, ssh://, git@host:ruta u owner/nombre)")
            p.add_argument("--destino", help="repositorio remoto: carpeta donde clonar (por defecto, ./<nombre>)")
            p.add_argument("--si", action="store_true", help="repositorio remoto: acepta el plan sin preguntar (sudo, sesion de gh y descargas pesadas SIEMPRE preguntan)")
            p.add_argument("--solo-clonar", action="store_true", help="repositorio remoto: solo comprobar acceso y clonar (sin paquetes, GitHub ni entorno)")
            p.add_argument("--plan", action="store_true", help="repositorio remoto: solo muestra el plan completo")
            p.add_argument("--modo", choices=("adopt", "init", "update", "migrar"))
            p.add_argument("--partida", choices=("A", "B", "C"))
            p.add_argument("--acceso"); p.add_argument("--politica"); p.add_argument("--proyecto")
            p.add_argument("--aceptar-degradado", action="store_true"); p.add_argument("--aceptar-dentro-de-repo", action="store_true")
            p.add_argument("--aplicar", action="store_true", help="escribe; sin esto solo se muestra el plan")
        elif sub == "update":
            p.add_argument("instancia", nargs="?")
            p.add_argument("--aplicar", action="store_true", help="escribe; sin esto solo se muestra el plan")
        elif sub == "montar":
            p.add_argument("instancia", nargs="?", help="carpeta de la instancia (por defecto, la actual)")
            p.add_argument("--agentes", help="lista separada por comas; sin esto detecta los que hay")
            p.add_argument("--aplicar", action="store_true", help="escribe; sin esto solo se muestra el plan")
            p.add_argument("--si", action="store_true", help="salta solo las preguntas de bajo riesgo")
            p.add_argument("--json", action="store_true")
        elif sub == "trazar":
            p.add_argument("cambio", nargs="?", help="carpeta del cambio (por defecto, la actual si tiene especificacion.md)")
            p.add_argument("--etapa", choices=("especificacion", "delegacion", "implementacion", "cierre"), default="cierre",
                           help="hasta qué puerta comprobar (por defecto, cierre)")
            p.add_argument("--repo", help="repositorio del proyecto: comprueba que los commits y archivos citados existen (git local)")
            p.add_argument("--json", action="store_true")
        elif sub == "erp":
            p.add_argument("--negocio", help="carpeta local con los documentos del negocio (.md, .txt, .csv, .xlsx); si falta, la pregunta")
            p.add_argument("--erp-base", dest="erp_base", help="carpeta del repositorio del ERP estándar (se lee modulos/catalogo.json; nunca se escribe)")
            p.add_argument("--instancia", help="carpeta de la instancia donde dejar la propuesta (sin esto, solo se muestra)")
            p.add_argument("--senales", help="archivo de señales alternativo (por defecto perfiles/_erp/senales.toml)")
            p.add_argument("--aplicar", action="store_true", help="escribe la propuesta en la instancia sin preguntar; sin esto pide confirmación")
            p.add_argument("--si", action="store_true", help="igual que --aplicar")
            p.add_argument("--no-interactivo", action="store_true", help="no pregunta: muestra la propuesta y sale sin escribir")
            p.add_argument("--json", action="store_true", help="una sola salida JSON (no interactivo)")
        elif sub == "entorno":
            p.add_argument("--listar", action="store_true", help="muestra módulos, agentes y perfiles disponibles")
            p.add_argument("--nombre", help="nombre del entorno (minúsculas, números y guiones)")
            p.add_argument("--destino", help="carpeta nueva donde se genera (no puede estar dentro del harness)")
            p.add_argument("--modulos", help="módulos separados por coma (mira --listar)")
            p.add_argument("--agentes", default="claude", help="claude, codex (por coma)")
            p.add_argument("--perfiles", default="", help="estándares de stack a copiar (por coma)")
            p.add_argument("--aplicar", action="store_true", help="escribe el entorno; sin esto solo muestra el plan")
            p.add_argument("--comparar", metavar="CARPETA", help="compara un entorno ya generado con lo que generaría hoy el harness (solo lectura)")
            p.add_argument("--aplicar-seguras", action="store_true", help="con --comparar: copia solo lo que no tocaste y el generador mejoró")
        elif sub == "aprender":
            p.add_argument("args", nargs=argparse.REMAINDER, help="acción y argumentos de harness-aprender.py (fuentes, escanear, listar, ver, descartar, promover)")
        elif sub == "ayuda":
            pass
        else:
            p.add_argument("instancia", nargs="?", help="carpeta de la instancia (por defecto, la actual)")
            p.add_argument("--json", action="store_true")
            if sub == "doctor":
                p.add_argument("--bundle", action="store_true", help="paquete de diagnóstico en JSON para pegar a quien atiende un problema (sin secretos ni rutas personales)")
        a = p.parse_args(argv[1:])
        if a.harness:
            raiz = Path(a.harness).expanduser().resolve()
        out = Salida(salida)
        if sub == "instalar":
            return cmd_instalar(a, out, raiz)
        if sub == "update":
            return cmd_update(a, out, raiz)
        if sub == "montar":
            return cmd_montar(a, out, raiz)
        if sub == "trazar":
            return cmd_trazar(a, out, raiz)
        if sub == "entorno":
            return cmd_entorno(a, out, raiz)
        if sub == "aprender":
            return cmd_aprender(a, out, raiz)
        if sub == "erp":
            inter = interactivo if interactivo is not None else (sys.stdin.isatty() and sys.stdout.isatty())
            inter = bool(inter) and not (a.no_interactivo or a.json)
            return cmd_erp(a, out, raiz, entrada or input, inter)
        if sub == "ayuda":
            parser_asistente().print_help(salida)
            return 0
        base = a.instancia or os.getcwd()
        if sub == "siguiente":
            r = siguiente(base, raiz)
            if a.json:
                print(json.dumps(r, ensure_ascii=False, indent=2), file=salida)
                return 0 if r["existe"] else 1
            return mostrar_siguiente(r, out)
        if sub == "doctor" and getattr(a, "bundle", False):
            inst = base if (a.instancia or (Path(base) / "harness.lock").exists() or (Path(base) / "entorno.lock.json").exists()) else None
            print(json.dumps(paquete_diagnostico(inst, raiz), ensure_ascii=False, indent=2), file=salida)
            return 0
        if sub == "doctor":
            filas = doctor(base if (a.instancia or (Path(base) / "harness.lock").exists()) else None, raiz)
            if a.json:
                print(json.dumps([{"nivel": n, "texto": t, "accion": ac} for n, t, ac in filas], ensure_ascii=False, indent=2), file=salida)
                return 1 if any(f[0] == "problema" for f in filas) else 0
            return mostrar_doctor(filas, out)
        e = estado(base, raiz)
        if a.json:
            print(json.dumps(e, ensure_ascii=False, indent=2), file=salida)
            return 0 if e["es_instancia"] else 1
        return mostrar_estado(e, out)
    except Detener as e:
        print(str(e), file=sys.stderr if e.codigo == 1 else salida)
        return e.codigo


if __name__ == "__main__":
    sys.exit(main())
