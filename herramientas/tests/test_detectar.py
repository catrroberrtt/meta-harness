"""Pruebas de harness-detectar.py con proyectos sintéticos (solo stdlib). Ejecutar:
python3 -m unittest herramientas/tests/test_detectar.py
"""
import importlib.util, json, os, pathlib, subprocess, sys, tempfile, unittest

AQUI = pathlib.Path(__file__).resolve().parent
SCRIPT = AQUI.parent / "harness-detectar.py"
spec = importlib.util.spec_from_file_location("harness_detectar", SCRIPT)
hd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hd)

SECRETO = "S3cr3tV4lorUnico987"
CLAVE_FALSA = "AKIA" + "ABCDEFGHIJKLMNOP"   # formato de clave de nube, no real


def w(base, rel, txt=""):
    p = pathlib.Path(base) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf8")


def git(base, *a):
    subprocess.run(["git", "-C", str(base), *a], capture_output=True, check=True)


def arbol(base):
    r = {}
    for dp, dn, fn in os.walk(base):
        for f in fn:
            p = pathlib.Path(dp) / f
            r[str(p.relative_to(base))] = (p.stat().st_size, p.stat().st_mtime_ns, p.read_bytes() if ".git" not in p.parts else b"")
    return r


def dim(R, n):
    return R["dimensiones"][n - 1]


def texto(d):
    return json.dumps(d, ensure_ascii=False)


def nest(base):
    w(base, "package.json", json.dumps({"name": "svc", "engines": {"node": ">=18"}, "scripts": {"test": "jest", "build": "nest build", "test:cov": "jest --coverage"},
        "dependencies": {"@nestjs/core": "^10.0.0", "typeorm": "^0.3.0", "mysql2": "^3.0.0", "@aws-sdk/client-s3": "^3.0.0", "openai": "^4.0.0", "helmet": "^7.0.0"},
        "devDependencies": {"jest": "^29.0.0", "typescript": "^5.0.0"}}))
    w(base, "tsconfig.json", '{"compilerOptions": {"strict": true}}')
    w(base, "jest.config.js", "module.exports = { collectCoverage: true };")
    w(base, "Dockerfile", "FROM node:18\nENV NODE_ENV\n")
    w(base, ".env", f"DB_HOST=localhost\nDB_PASSWORD={SECRETO}\nOPENAI_API_KEY=sk-{SECRETO}\n")
    w(base, ".env.example", "DB_HOST=\nDB_PASSWORD=\n")
    w(base, ".gitignore", "node_modules\n.env\n")
    w(base, "src/modules/users/users.module.ts", "export class UsersModule {}\n")
    w(base, "src/modules/orders/orders.module.ts", "export class OrdersModule {}\n")
    w(base, "src/modules/billing/billing.module.ts", "export class B {}\n")
    w(base, "src/modules/users/users.service.spec.ts", "it('x',()=>{})\n")
    w(base, "src/main.ts", "const h = process.env.DB_HOST;\n" + "// l\n" * 450)
    w(base, "src/migrations/1-init.ts", "export class Init {}\n")
    w(base, "src/migrations/2-more.ts", "export class More {}\n")
    w(base, "src/config.ts", f'export const k = {{ apiKey: "{CLAVE_FALSA}" }};\n')
    w(base, ".github/workflows/deploy.yml", "name: deploy\non:\n  push:\n    branches: [release-x]\njobs:\n  d:\n    environment: stage-a\n    steps:\n      - run: docker push img\n      - run: echo rollback manual\n")
    w(base, "README.md", "# svc\n")
    git(base, "init", "-q"); git(base, "config", "user.email", "t@t"); git(base, "config", "user.name", "t")
    git(base, "add", "-A"); git(base, "commit", "-qm", "feat: inicio")


class Base(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._td.name)
        self.addCleanup(self._td.cleanup)

    def proyecto(self, nombre, fn):
        p = self.tmp / nombre
        p.mkdir()
        fn(p)
        return p


class TestComunes(Base):
    def verifica_estructura(self, R):
        self.assertEqual([d["nombre"] for d in R["dimensiones"]], ["Desarrollo", "QA", "Técnica", "Datos", "Infraestructura y despliegue", "Costos", "Seguridad", "Documentación y gestión"])
        for d in R["dimensiones"]:
            for k in ("detectado", "falta", "propuesta", "pregunta"):
                self.assertIn(k, d)
            for q in d["pregunta"]:
                self.assertTrue(q["intento"].strip(), f"pregunta sin intento en {d['nombre']}")
                self.assertRegex(q["intento"], r"(?i)buscar|revis|intent|sin (éxito|resultado)")
            for x in d["detectado"]:
                self.assertTrue(x["evidencia"])


class TestNest(TestComunes):
    def setUp(self):
        super().setUp()
        self.p = self.proyecto("svc", nest)
        self.antes = arbol(self.p)
        self.R = hd.analizar(self.p)

    def test_estructura_y_no_modifica(self):
        self.verifica_estructura(self.R)
        self.assertEqual(self.antes, arbol(self.p))

    def test_desarrollo_qa_tecnica(self):
        self.assertIn("NestJS", texto(dim(self.R, 1)))
        self.assertIn("jest", texto(dim(self.R, 2)))
        self.assertIn("Cobertura configurada", texto(dim(self.R, 2)))
        t = dim(self.R, 3)
        self.assertIn("pasan de 400", texto(t))
        self.assertIn("estricto", texto(t))
        self.assertIn("3 módulos", texto(t))

    def test_datos_infra_costos(self):
        d = texto(dim(self.R, 4))
        self.assertIn("MySQL", d); self.assertIn("TypeORM", d); self.assertIn("2 archivos de migración", d)
        self.assertIn("DB_HOST", d); self.assertIn("stage-a", d)
        i = texto(dim(self.R, 5))
        self.assertIn("Dockerfile", i); self.assertIn("Workflow de despliegue", i); self.assertIn("reversión", i)
        c = texto(dim(self.R, 6))
        self.assertIn("openai", c); self.assertIn("@aws-sdk/client-s3", c)
        self.assertTrue(any("presupuesto" in x.lower() or "tope" in x.lower() for x in dim(self.R, 6)["falta"] + dim(self.R, 6)["propuesta"]))

    def test_seguridad_no_filtra_valores(self):
        s = dim(self.R, 7)
        self.assertIn("src/config.ts", texto(s))
        self.assertIn("clave-aws", texto(s))
        for malo in (SECRETO, CLAVE_FALSA, "sk-"):
            self.assertNotIn(malo, json.dumps(self.R, ensure_ascii=False))
            self.assertNotIn(malo, hd.md(self.R))

    def test_env_versionado(self):
        git(self.p, "add", "-f", ".env")
        R = hd.analizar(self.p)
        self.assertIn("VERSIONADO", texto(dim(R, 7)))
        self.assertNotIn(SECRETO, hd.md(R))

    def test_no_asume_nada(self):
        # R18: el informe no trae ambientes ni ramas que el proyecto no tiene
        m = hd.md(self.R).lower()
        # términos que el informe no puede traer si el proyecto no los tiene (el nombre de una empresa concreta se
        # comprueba con HARNESS_PROHIBIDOS, un archivo local fuera del repositorio)
        import os
        ajenos = ["jira.", "confluence.", "3307", "qas"]
        ruta = os.environ.get("HARNESS_PROHIBIDOS")
        if ruta and os.path.isfile(ruta):
            ajenos += [l.strip().lower() for l in open(ruta, encoding="utf8") if l.strip() and not l.startswith("#")]
        for ajeno in ajenos:
            self.assertNotIn(ajeno, m)


class TestAngular(TestComunes):
    def test_karma(self):
        def f(b):
            w(b, "package.json", json.dumps({"dependencies": {"@angular/core": "^18.0.0", "@angular/material": "^18.0.0"}, "devDependencies": {"karma": "^6.0.0", "jasmine-core": "^5.0.0"}}))
            w(b, "karma.conf.js", "module.exports = function(c){ c.set({reporters:['progress','coverage']}) }")
            w(b, "src/app/app.component.ts", "export class A {}\n")
            w(b, "src/app/app.component.spec.ts", "it('a',()=>{})\n")
            w(b, "tsconfig.json", '{"compilerOptions": {"strict": false}}')
        p = self.proyecto("web", f)
        R = hd.analizar(p)
        self.verifica_estructura(R)
        self.assertIn("Angular 18", texto(dim(R, 1)))
        self.assertIn("karma", texto(dim(R, 2)))
        self.assertTrue(any("strict" in x for x in dim(R, 3)["falta"]))
        self.assertIn("angular-material", texto(R["propuesta"]))
        self.assertTrue(any("Dockerfile" in x or "infraestructura" in x.lower() for x in dim(R, 5)["falta"]))


class TestPythonERP(TestComunes):
    def test_erp_sin_tickets(self):
        def f(b):
            w(b, "requirements.txt", "django==4.2\npsycopg2-binary\npytest\n")
            w(b, "docker-compose.yml", "services:\n  db:\n    image: postgres:15\n    environment:\n      POSTGRES_PASSWORD: Pg9xK2mQ7vLz\n      POSTGRES_DB: erp\n")
            w(b, "erp/models.py", "def f():\n" + "    x = 1\n" * 70 + "\n")
            w(b, "tests/test_models.py", "def test_a():\n    assert True\n")
            w(b, "pytest.ini", "[pytest]\naddopts = --cov\n")
            w(b, "README.md", "# ERP\n")
        p = self.proyecto("erp", f)
        antes = arbol(p)
        R = hd.analizar(p)
        self.verifica_estructura(R)
        self.assertEqual(antes, arbol(p))
        self.assertIn("pytest", texto(dim(R, 2)))
        self.assertIn("PostgreSQL", texto(dim(R, 4)))
        self.assertIn("funciones Python", texto(dim(R, 3)))
        d8 = dim(R, 8)
        self.assertTrue(any("tareas" in x["pregunta"] for x in d8["pregunta"]))
        self.assertTrue(any("Sin adaptador de tickets" in x for x in d8["propuesta"]))
        self.assertNotIn("Pg9xK2mQ7vLz", hd.md(R))
        self.assertIn("credencial-literal", texto(dim(R, 7)))   # la credencial literal se marca, sin valor
        self.assertEqual(R["propuesta"]["modo"], "init")


class TestVacia(TestComunes):
    def test_carpeta_vacia(self):
        p = self.tmp / "vacia"; p.mkdir()
        R = hd.analizar(p)
        self.verifica_estructura(R)
        for n in range(1, 9):
            d = dim(R, n)
            self.assertTrue(d["falta"] or d["pregunta"], d["nombre"])
        self.assertTrue(dim(R, 6)["pregunta"])           # qué operaciones cobran
        self.assertIn("cobran", dim(R, 6)["pregunta"][0]["pregunta"])
        self.assertIn("documenta", dim(R, 8)["pregunta"][0]["pregunta"])
        self.assertIn("## 8. Documentación y gestión", hd.md(R))


class TestCLI(Base):
    def correr(self, *a):
        return subprocess.run([sys.executable, str(SCRIPT), *a], capture_output=True, text=True)

    def test_salida_y_rechazo(self):
        p = self.proyecto("svc", nest)
        r = self.correr(str(p), "--json")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(len(json.loads(r.stdout)["dimensiones"]), 8)
        fuera = self.tmp / "informe.md"
        r = self.correr(str(p), "--salida", str(fuera))
        self.assertEqual(r.returncode, 0); self.assertEqual(r.stdout, ""); self.assertTrue(fuera.read_text().startswith("# Cómo es"))
        antes = arbol(p)
        r = self.correr(str(p), "--salida", str(p / "docs" / "i.md"))
        self.assertNotEqual(r.returncode, 0); self.assertFalse((p / "docs").exists()); self.assertEqual(antes, arbol(p))


if __name__ == "__main__":
    unittest.main()
