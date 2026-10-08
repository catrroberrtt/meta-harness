"""Pruebas del minero de prácticas con proyectos sintéticos en /tmp (git real, commits de arreglo)."""
import hashlib, json, os, pathlib, subprocess, sys, tempfile, unittest

HERR = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = HERR / "harness-minar-practicas.py"
LEY = "señal correlacional: no demuestra que una práctica sea mejor"


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def w(root, rel, txt):
    p = pathlib.Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf8")


def git(root, *a):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    subprocess.run(["git", "-C", str(root), *a], capture_output=True, check=True, env=env)


def commit(root, msg):
    git(root, "add", "-A"); git(root, "commit", "-q", "-m", msg)


def huella(root):
    h = hashlib.sha256()
    for p in sorted(pathlib.Path(root).rglob("*")):
        if ".git" in p.parts and p.name != "HEAD": 
            continue
        h.update(str(p.relative_to(root)).encode())
        if p.is_file(): h.update(p.read_bytes())
    return h.hexdigest(), subprocess.run(["git", "-C", str(root), "status", "--porcelain"], capture_output=True, text=True).stdout


def nest_pkg(root):
    w(root, "package.json", json.dumps({"dependencies": {"@nestjs/core": "10.0.0"}}))
    git(root, "init", "-q")


def plano(root):
    nest_pkg(root)
    for n in ("a", "b", "c"):
        w(root, f"src/controllers/{n}.controller.ts", f"@Controller('{n}')\nexport class {n.upper()}Controller {{\n  constructor(private s: {n.upper()}Service) {{}}\n  @Get()\n  get(x: any) {{\n    if (!x) {{\n      throw new BadRequestException('dato invalido de entrada');\n    }}\n    return this.s.get();\n  }}\n}}\n")
        w(root, f"src/services/{n}.service.ts", f"@Injectable()\nexport class {n.upper()}Service {{\n  constructor(@InjectRepository(E) private r: Repository<E>) {{}}\n  get() {{ return this.r.find(); }}\n}}\n")
    commit(root, "feat: base")
    w(root, "src/services/a.service.ts", "@Injectable()\nexport class AService {\n  constructor(@InjectRepository(E) private r: Repository<E>) {}\n  get() { return this.r.find({ take: 1 }); }\n}\n")
    commit(root, "fix: corrige a")
    w(root, "src/controllers/a.controller.ts", "// cambio\n@Controller('a')\nexport class AController {}\n")
    commit(root, "hotfix: otra")


def modular(root):
    nest_pkg(root)
    for n in ("pagos", "ofertas", "cuentas"):
        w(root, f"src/{n}/{n}.module.ts", "@Module({})\nexport class M {}\n")
        w(root, f"src/{n}/{n}.controller.ts", "@Controller()\nexport class C {\n  @Post()\n  crear(@Body() d: CrearDto) { return this.uc.ejecutar(d); }\n}\n")
        w(root, f"src/{n}/application/crear.use-case.ts", "@Injectable()\nexport class CrearUseCase {\n  constructor(@Inject(REPO_PORT) private r: Port) {}\n  ejecutar(d) { return this.r.guardar(d); }\n}\n")
        w(root, f"src/{n}/domain/entidad.ts", "export class Entidad {}\n")
        w(root, f"src/{n}/infrastructure/repo.adapter.ts", "@Injectable()\nexport class RepoAdapter {}\n")
        w(root, f"src/{n}/dto/crear.dto.ts", "export class CrearDto {\n  @IsString()\n  nombre: string;\n}\n")
        w(root, f"src/{n}/crear.use-case.spec.ts", "describe('x', () => { it('y', () => { const m = jest.fn(); }); });\n")
    commit(root, "feat: base")
    w(root, "src/pagos/application/crear.use-case.ts", "@Injectable()\nexport class CrearUseCase {\n  constructor(@Inject(REPO_PORT) private r: Port) {}\n  ejecutar(d) { return 1; }\n}\n")
    commit(root, "fix: pagos")


def angular(root):
    w(root, "package.json", json.dumps({"dependencies": {"@angular/core": "^18.0.0"}}))
    git(root, "init", "-q")
    w(root, "src/app/app.routes.ts", "export const routes: Routes = [{ path: 'a', loadComponent: () => import('./a/a.component') }];\n")
    for n in ("a", "b"):
        w(root, f"src/app/{n}/{n}.component.ts", "@Component({ selector: 'x', standalone: true, changeDetection: ChangeDetectionStrategy.OnPush, templateUrl: './x.html' })\nexport class XComponent {\n  s = signal(0);\n  f = new FormGroup({});\n}\n")
        w(root, f"src/app/{n}/{n}.component.html", "@if (x) { <p></p> }\n")
        w(root, f"src/app/{n}/{n}.service.ts", "@Injectable()\nexport class XService { constructor(private h: HttpClient) {} }\n")
        w(root, f"src/app/{n}/{n}.component.spec.ts", "describe('c', () => {});\n")
    commit(root, "feat: base")
    w(root, "src/app/a/a.component.html", "@if (y) { <p></p> }\n")
    commit(root, "fix: a")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="minar_")
        cls.P = {}
        for nombre, f in (("plano", plano), ("modular", modular), ("ng", angular)):
            d = pathlib.Path(cls.tmp) / nombre; d.mkdir(); f(d); cls.P[nombre] = str(d)

    def j(self, p):
        r = run(self.P[p], "--json"); self.assertEqual(r.returncode, 0, r.stderr); return json.loads(r.stdout)


class Pruebas(Base):
    def test_estilo_capas_planas(self):
        r = self.j("plano")
        self.assertEqual(r["arquitectura"]["estilo_dominante"], "capas planas por tipo")
        e = r["arquitectura"]["estilos"][0]
        self.assertEqual(e["pct_modulos"], 100.0)

    def test_estilo_hexagonal_y_patrones(self):
        r = self.j("modular")
        self.assertEqual(r["arquitectura"]["estilo_dominante"], "hexagonal")
        self.assertEqual(r["patrones"]["caso de uso/handler"]["consistencia_pct"], 100.0)
        self.assertEqual(r["patrones"]["puerto-adaptador con tokens"]["consistencia_pct"], 100.0)
        self.assertEqual(r["patrones"]["validación en DTO"]["consistencia_pct"], 100.0)

    def test_plano_con_orm_directo_y_controllers_con_if(self):
        r = self.j("plano")
        self.assertEqual(r["patrones"]["ORM inyectado directo en servicio"]["consistencia_pct"], 100.0)
        self.assertEqual(r["codigo"]["controllers"]["pct_con_if_o_throw"], 66.7)  # a.controller fue reescrito sin if
        self.assertGreaterEqual(r["codigo"]["any"]["usos"], 2)
        self.assertEqual(r["codigo"]["constantes"]["mensajes_repetidos_3+"], 0)

    def test_dobles_y_specs(self):
        r = self.j("modular")
        self.assertEqual(r["codigo"]["pruebas"]["specs"], 3)
        self.assertEqual(r["codigo"]["pruebas"]["dobles"].get("jest.fn"), 3)

    def test_arreglos_por_modulo(self):
        r = self.j("modular")
        pagos = [m for m in r["calidad"]["modulos"] if m["modulo"].endswith("pagos")][0]
        self.assertEqual(pagos["commits"], 2); self.assertEqual(pagos["arreglos"], 1); self.assertEqual(pagos["pct_arreglos"], 50.0)

    def test_angular(self):
        r = self.j("ng")
        self.assertEqual(r["stack"], "angular")
        self.assertEqual(r["arquitectura"]["estilo_dominante"], "standalone")
        self.assertEqual(r["patrones"]["componentes standalone"]["consistencia_componentes_pct"], 100.0)
        self.assertEqual(r["patrones"]["rutas perezosas"]["consistencia_pct"], 100.0)
        self.assertEqual(r["patrones"]["formularios reactivos"]["consistencia_pct"], 100.0)

    def test_comparar_marca_divergencia(self):
        r = run("--comparar", self.P["plano"], self.P["modular"], "--md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Divergencias", r.stdout)
        self.assertIn("estilo de arquitectura dominante", r.stdout)
        self.assertIn("caso de uso/handler", r.stdout)
        self.assertIn("Candidatos a estándar", r.stdout)
        self.assertIn("SOLO propone", r.stdout)
        s = json.loads(run("--comparar", self.P["plano"], self.P["modular"], "--json").stdout)
        prac = {d["practica"] for d in s["stacks"]["nestjs"]["divergencias"]}
        self.assertIn("estilo de arquitectura dominante", prac)

    def test_solo_lectura(self):
        antes = {k: huella(v) for k, v in self.P.items()}
        for k, v in self.P.items(): run(v, "--md"); run(v, "--json")
        run("--comparar", *self.P.values())
        self.assertEqual(antes, {k: huella(v) for k, v in self.P.items()})
        self.assertEqual(huella(self.P["plano"])[1], "")  # git status limpio

    def test_rechaza_escribir_en_proyecto(self):
        r = run(self.P["plano"], "--salida", str(pathlib.Path(self.P["plano"]) / "x.md"))
        self.assertNotEqual(r.returncode, 0); self.assertIn("Rechazado", r.stdout + r.stderr)
        self.assertFalse((pathlib.Path(self.P["plano"]) / "x.md").exists())

    def test_leyenda_siempre(self):
        for p in self.P:
            self.assertIn(LEY, run(self.P[p], "--md").stdout)
            self.assertIn(LEY, run(self.P[p], "--json").stdout)
        self.assertIn(LEY, run("--comparar", self.P["plano"], self.P["modular"], "--md").stdout)
        self.assertIn(LEY, run("--comparar", self.P["plano"], self.P["modular"], "--json").stdout)

    def test_registro_extensible(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("minar", SCRIPT); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        self.assertTrue({"nestjs", "angular"} <= set(m.DETECTORES))


if __name__ == "__main__":
    unittest.main()
