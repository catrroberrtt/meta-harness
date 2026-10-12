"""La documentación no promete más que el código: rutas, herramientas, subcomandos y módulos que cita deben existir.

<!-- tipo: herramienta · capa: 4 -->
Solo comprueba lo que se puede comprobar sin falsos positivos: rutas con prefijo explícito de este repositorio, nombres `harness-*.py`,
subcomandos `harness <x>` y el catálogo de módulos del generador de entornos. Las líneas de ejemplo o marcadas «(externo)»/«(nuevo)» se
saltan, y los análisis de referencias externas (ANALISIS-*.md) citan archivos de otros proyectos.
"""
import importlib.util, pathlib, re, unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent.parent


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, RAIZ / ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


cli = cargar("harness_cli_docs", "cli/harness_cli.py")
ent = cargar("harness_entorno_docs", "herramientas/harness-entorno.py")
LOCALES = ("herramientas", "plantillas", "estandares", "docs", "hooks", "instalador", "cli", "adaptadores-agente", "perfiles", "bootstrap",
           "metodo", "politicas", "acceso", "convenciones", "adaptadores")
SALTAR_LINEA = re.compile(r"\((nuevo|externo|ejemplo)\)|ejemplo|p\. ?ej|Ejemplo")


def documentos():
    docs = [RAIZ / "README.md", *sorted((RAIZ / "docs").glob("*.md")), *sorted((RAIZ / "estandares").glob("*.md")), *sorted(RAIZ.glob("*/README.md")),
            RAIZ / "adaptadores-agente" / "codex" / "README.md"]
    return [d for d in docs if d.is_file() and not d.name.startswith("ANALISIS-")]


def lineas():
    for d in documentos():
        for i, l in enumerate(d.read_text(encoding="utf8").splitlines(), 1):
            if not SALTAR_LINEA.search(l):
                yield d, i, l


class Documentacion(unittest.TestCase):
    def test_las_rutas_citadas_existen(self):
        faltan = []
        for d, i, l in lineas():
            for t in re.findall(r"`([^`\s]+)`", l):
                if any(c in t for c in "*<>{}$|=(),;:") or t.startswith(("http", "~", "/", "-")):
                    continue
                partes = t.split("/")
                if len(partes) >= 2 and partes[0] in LOCALES and "." in partes[-1]:
                    if not (RAIZ / t).exists() and not (d.parent / t).exists():
                        faltan.append(f"{d.relative_to(RAIZ)}:{i}: `{t}`")
        self.assertEqual(faltan, [], "rutas citadas que no existen")

    def test_las_herramientas_citadas_existen(self):
        faltan = []
        for d, i, l in lineas():
            for t in re.findall(r"`(harness-[a-z-]+\.py)`", l):
                if not (RAIZ / "herramientas" / t).exists():
                    faltan.append(f"{d.relative_to(RAIZ)}:{i}: `{t}`")
        self.assertEqual(faltan, [])

    def test_los_subcomandos_citados_existen(self):
        validos, faltan = set(cli.SUBCOMANDOS), []
        for d, i, l in lineas():
            for m in re.finditer(r"`harness ([a-z]+)\b", l):
                if m.group(1) not in validos:
                    faltan.append(f"{d.relative_to(RAIZ)}:{i}: `harness {m.group(1)}`")
        self.assertEqual(faltan, [])

    def test_todo_modulo_del_catalogo_esta_documentado(self):
        texto = (RAIZ / "docs" / "ENTORNO-PROPIO.md").read_text(encoding="utf8")
        for modulo in ent.MODULOS:
            self.assertIn(f"`{modulo}`", texto, f"docs/ENTORNO-PROPIO.md no documenta el módulo {modulo}")

    def test_todo_modulo_documentado_existe(self):
        texto = (RAIZ / "docs" / "ENTORNO-PROPIO.md").read_text(encoding="utf8")
        tabla = texto.split("## Módulos", 1)[1].split("\n## ", 1)[0]
        for m in re.findall(r"^\| `([\w-]+)` \|", tabla, re.M):
            self.assertIn(m, ent.MODULOS, f"la documentación promete el módulo «{m}» y el generador no lo tiene")

    def test_la_ayuda_de_la_cli_describe_todos_los_subcomandos(self):
        for sub in cli.SUBCOMANDOS:
            if sub != "ayuda":
                self.assertIn(sub, cli.DESCRIPCION, f"falta la descripción de `harness {sub}`")


class NucleoSinDependencias(unittest.TestCase):
    """Frontera del núcleo: lo que se copia a un entorno generado solo puede usar la biblioteca estándar y su propia ayuda (`_comandos`).

    Es la versión ligera de «el núcleo no importa de capas superiores»: un entorno generado funciona solo, así que ningún script suyo puede
    importar el meta-harness ni un paquete que haya que instalar.
    """

    def test_los_scripts_de_los_modulos_solo_importan_biblioteca_estandar(self):
        import ast, sys
        estandar, propios = set(sys.stdlib_module_names), {"_comandos"}
        malos = []
        for f in sorted((RAIZ / "plantillas" / "entorno").rglob("*.py")):
            for nodo in ast.walk(ast.parse(f.read_text(encoding="utf8"))):
                nombres = [a.name.split(".")[0] for a in nodo.names] if isinstance(nodo, ast.Import) else \
                          [nodo.module.split(".")[0]] if isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0 else []
                for n in nombres:
                    if n not in estandar and n not in propios:
                        malos.append(f"{f.relative_to(RAIZ)}: importa «{n}»")
        self.assertEqual(malos, [], "los scripts de un entorno generado no pueden depender de nada que no venga con Python")

    def test_los_scripts_de_shell_no_llaman_al_meta_harness(self):
        for f in sorted((RAIZ / "plantillas" / "entorno").rglob("*.sh")) + sorted((RAIZ / "plantillas" / "entorno").rglob("*.tpl")):
            texto = f.read_text(encoding="utf8")
            for prohibido in ("harness-", "herramientas/harness", "meta-harness/", "adaptadores-agente"):
                self.assertNotIn(prohibido, texto, f"{f.relative_to(RAIZ)} menciona «{prohibido}»")


if __name__ == "__main__":
    unittest.main()
