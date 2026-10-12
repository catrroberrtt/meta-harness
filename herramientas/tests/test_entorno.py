"""Pruebas de harness-entorno.py: generación independiente, validación, hooks y mecanismos del entorno generado.

<!-- tipo: herramienta · capa: 4 -->
Todo ocurre en carpetas temporales. El entorno generado se ejercita como lo haría otra persona: ./verificar.sh y cada mecanismo.
"""
import importlib.util, json, os, pathlib, re, subprocess, sys, tempfile, unittest

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
spec = importlib.util.spec_from_file_location("harness_entorno", RAIZ / "herramientas" / "harness-entorno.py")
ent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ent)

TODOS = ",".join(ent.MODULOS)


def generar(destino, modulos=TODOS, agentes="claude,codex", perfiles="", nombre="entorno-prueba", aplicar=True):
    args = ["--nombre", nombre, "--destino", str(destino), "--modulos", modulos, "--agentes", agentes, "--perfiles", perfiles]
    if aplicar:
        args.append("--aplicar")
    return ent.main(args)


def correr(cmd, cwd, entrada=None, env=None):
    e = dict(os.environ, **(env or {}))
    return subprocess.run(cmd, cwd=cwd, input=entrada, capture_output=True, text=True, env=e)


class Validacion(unittest.TestCase):
    def test_sin_aplicar_no_escribe_nada(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "nuevo"
            self.assertEqual(generar(d, aplicar=False), 0)
            self.assertFalse(d.exists())

    def test_rechaza_nombre_modulo_agente_y_perfil_invalidos(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "x"
            self.assertEqual(generar(d, nombre="Mal Nombre"), 2)
            self.assertEqual(generar(d, modulos="inventado"), 2)
            self.assertEqual(generar(d, agentes="otro"), 2)
            self.assertEqual(generar(d, perfiles="_erp"), 2)
            self.assertFalse(d.exists())

    def test_rechaza_destino_con_contenido_y_destino_dentro_del_harness(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t)
            (d / "algo.txt").write_text("x")
            self.assertEqual(generar(d), 2)
        self.assertEqual(generar(RAIZ / "salida-prueba"), 2)
        self.assertFalse((RAIZ / "salida-prueba").exists())

    def test_dependencias_se_agregan(self):
        final, agregados = ent.resolver(["autoguardado"])
        self.assertIn("escaneo-secretos", final)
        self.assertEqual(agregados, ["escaneo-secretos"])


class Independencia(unittest.TestCase):
    def test_el_entorno_no_menciona_el_harness_ni_datos_ajenos(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "e"
            generar(d, perfiles="nestjs-typeorm-mysql")
            prohibido = re.compile(r"/home/|Desktop/Proyectos|harness-sincronizar|harness-aprender|herramientas/harness", re.I)
            for f in d.rglob("*"):
                if f.is_file() and f.suffix not in (".png",):
                    for i, l in enumerate(f.read_text(encoding="utf8").splitlines(), 1):
                        self.assertIsNone(prohibido.search(l), f"{f.relative_to(d)}:{i}: {l[:80]}")

    def test_trae_licencia_y_origen(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "e"
            generar(d, modulos="aprendizaje", agentes="codex")
            self.assertTrue((d / "LICENSE").is_file())
            self.assertIn("meta-harness", (d / "NOTICE").read_text(encoding="utf8"))
            self.assertFalse((d / ".claude").exists())  # sin agente claude no hay hooks

    def test_estandares_de_perfil_se_copian(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "e"
            generar(d, modulos="conocimiento", perfiles="nestjs-typeorm-mysql")
            self.assertTrue(any((d / "estandares" / "nestjs-typeorm-mysql").glob("*.md")))


class EntornoGenerado(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.d = pathlib.Path(cls.tmp.name) / "e"
        generar(cls.d)
        correr(["./instalar.sh", "--aplicar"], cls.d)
        correr(["git", "config", "user.email", "prueba" + "@" + "ejemplo.invalid"], cls.d)
        correr(["git", "config", "user.name", "t"], cls.d)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_verificar_pasa(self):
        r = correr(["./verificar.sh"], self.d)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("TODO OK", r.stdout)

    def test_settings_de_claude_apunta_a_hooks_existentes(self):
        cfg = json.loads((self.d / ".claude" / "settings.json").read_text(encoding="utf8"))
        scripts = re.findall(r"hooks/([\w.-]+\.sh)", json.dumps(cfg))
        self.assertGreaterEqual(len(scripts), 3)
        for s in scripts:
            self.assertTrue((self.d / "hooks" / s).is_file(), s)

    def test_hook_documentacion_primero_avisa_una_vez_y_calla_si_no_aplica(self):
        ev = json.dumps({"prompt": "analicemos los pagos", "session_id": f"prueba-{os.getpid()}"})
        primero = correr(["bash", "hooks/documentacion-primero.sh"], self.d, entrada=ev)
        self.assertIn("ORDEN DE LECTURA", primero.stdout)  # regresión: la lectura del evento llegaba vacía
        self.assertEqual(correr(["bash", "hooks/documentacion-primero.sh"], self.d, entrada=ev).stdout, "")
        otro = json.dumps({"prompt": "hola", "session_id": f"otra-{os.getpid()}"})
        self.assertEqual(correr(["bash", "hooks/documentacion-primero.sh"], self.d, entrada=otro).stdout, "")

    def test_hook_compuerta_avisa_bloquea_y_deja_pasar(self):
        commit = json.dumps({"tool_input": {"command": "git commit -m x"}})
        env = {"CLAUDE_PROJECT_DIR": str(self.d)}
        gate_ok = self.d / ".entorno" / "gate-ok"
        gate_ok.unlink(missing_ok=True)
        r = correr(["bash", "hooks/gate-antes-de-commit.sh"], self.d, entrada=commit, env=env)
        self.assertEqual(r.returncode, 0)
        self.assertIn("compuerta", r.stdout)
        ajeno = json.dumps({"tool_input": {"command": "ls -la"}})
        self.assertEqual(correr(["bash", "hooks/gate-antes-de-commit.sh"], self.d, entrada=ajeno, env=env).stdout, "")
        toml = (self.d / "entorno.toml").read_text(encoding="utf8")
        (self.d / "entorno.toml").write_text(toml.replace("bloquear_commit = false", "bloquear_commit = true"), encoding="utf8")
        try:
            r = correr(["bash", "hooks/gate-antes-de-commit.sh"], self.d, entrada=commit, env=env)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            correr(["bash", "scripts/gate.sh"], self.d)
            r = correr(["bash", "hooks/gate-antes-de-commit.sh"], self.d, entrada=commit, env=env)
            self.assertEqual(r.returncode, 0)
        finally:
            (self.d / "entorno.toml").write_text(toml, encoding="utf8")

    def test_autoguardado_guarda_y_se_niega_con_secreto(self):
        (self.d / "docs").mkdir(exist_ok=True)
        (self.d / "docs" / "a.md").write_text("# a\n", encoding="utf8")
        antes = int(correr(["git", "rev-list", "--count", "HEAD"], self.d).stdout.strip() or 0)
        correr(["bash", "hooks/autoguardado.sh"], self.d)
        despues = int(correr(["git", "rev-list", "--count", "HEAD"], self.d).stdout.strip())
        self.assertEqual(despues, antes + 1)
        clave_falsa = "AK" + "IA" + "ABCDEFGHIJKLMNOP"  # armada en ejecución: el literal dispararía el escaneo del propio repo
        (self.d / "docs" / "malo.md").write_text(f'k = "{clave_falsa}"\n', encoding="utf8")
        r = correr(["bash", "hooks/autoguardado.sh"], self.d)
        self.assertIn("NO se guardó", r.stderr)
        self.assertEqual(int(correr(["git", "rev-list", "--count", "HEAD"], self.d).stdout.strip()), despues)
        (self.d / "docs" / "malo.md").unlink()

    def test_aprendizaje_exige_evidencia_y_revierte(self):
        py = sys.executable
        correr([py, "scripts/aprender.py", "nota", "sin respaldo"], self.d)
        n = len([l for l in (self.d / "knowledge" / "aprendizaje.md").read_text(encoding="utf8").splitlines() if re.match(r"^\d+\. ", l)])
        self.assertEqual(correr([py, "scripts/aprender.py", "promover", str(n)], self.d).returncode, 1)
        correr([py, "scripts/aprender.py", "nota", "con respaldo", "--evidencia", "caso real"], self.d)
        self.assertEqual(correr([py, "scripts/aprender.py", "promover", str(n + 1)], self.d).returncode, 0)
        self.assertIn(f"<!-- regla {n + 1} -->", (self.d / "AGENTS.md").read_text(encoding="utf8"))
        self.assertEqual(correr([py, "scripts/aprender.py", "revertir", str(n + 1)], self.d).returncode, 0)
        self.assertNotIn(f"<!-- regla {n + 1} -->", (self.d / "AGENTS.md").read_text(encoding="utf8"))


class PublicarSoloVerificado(unittest.TestCase):
    """El motor comprueba contra fuentes declaradas; el hook impide publicar sin la marca del texto exacto."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.d = pathlib.Path(cls.tmp.name) / "e"
        generar(cls.d, modulos="publicar-solo-verificado")
        correr(["./instalar.sh", "--aplicar"], cls.d)
        correr(["git", "config", "user.email", "prueba" + "@" + "ejemplo.invalid"], cls.d)
        correr(["git", "config", "user.name", "prueba"], cls.d)
        (cls.d / "docs").mkdir(exist_ok=True)
        (cls.d / "docs" / "real.md").write_text("# real\n", encoding="utf8")
        correr(["git", "add", "-A"], cls.d)
        correr(["git", "commit", "-qm", "base"], cls.d)
        cls.sha = correr(["git", "rev-parse", "--short", "HEAD"], cls.d).stdout.strip()
        estado = cls.d / "scripts" / "estado.sh"
        estado.write_text('#!/usr/bin/env bash\ncase "$1" in T-1) echo CERRADO;; T-2) echo ABIERTO;; *) exit 3;; esac\n', encoding="utf8")
        estado.chmod(0o755)
        toml = (cls.d / "entorno.toml").read_text(encoding="utf8")
        ejemplo = ('# [[publicar.referencias]]\n# nombre = "ticket"\n# patron = "[A-Z]+-[0-9]+"\n'
                   '# comprobar = ["./scripts/estado-ticket.sh", "{id}"]\n# estados_cerrados = ["DONE", "CERRADO"]')
        real = ('[[publicar.referencias]]\nnombre = "ticket"\npatron = "T-[0-9]+"\n'
                'comprobar = ["./scripts/estado.sh", "{id}"]\nestados_cerrados = ["CERRADO"]')
        assert ejemplo in toml, "el ejemplo de referencias cambió: actualizar la prueba"
        (cls.d / "entorno.toml").write_text(toml.replace(ejemplo, real), encoding="utf8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def motor(self, *a):
        return correr([sys.executable, "scripts/verificar-publicacion.py", *a], self.d)

    def texto(self, nombre, contenido):
        (self.d / nombre).write_text(contenido, encoding="utf8")
        return nombre

    def hook(self, comando):
        r = correr([sys.executable, "hooks/publicar-solo-verificado.py"], self.d,
                   entrada=json.dumps({"tool_input": {"command": comando}}), env={"CLAUDE_PROJECT_DIR": str(self.d)})
        return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else "pasa"

    def test_texto_correcto_pasa_y_deja_marca_atada_al_texto(self):
        f = self.texto("ok.md", f"Cambia `docs/real.md` en el commit `{self.sha}`.\nEl ticket T-1 quedó resuelto.\n")
        self.assertEqual(self.motor("revisar", f).returncode, 0)
        self.assertEqual(self.motor("estado", f).returncode, 0)
        (self.d / f).write_text((self.d / f).read_text(encoding="utf8") + "otra línea\n", encoding="utf8")
        self.assertEqual(self.motor("estado", f).returncode, 1)  # editar invalida la marca

    def test_detecta_ruta_commit_relleno_y_secreto(self):
        clave = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
        f = self.texto("mal.md", f"Toca `src/no-existe.ts` y `deadbeefcafe`.\nTODO completar.\nk = \"{clave}\"\n")
        r = self.motor("revisar", f)
        self.assertEqual(r.returncode, 1)
        for esperado in ("no existe en el repo", "el commit", "relleno", "secreto"):
            self.assertIn(esperado, r.stdout)

    def test_nuevo_y_externo_marcados_no_fallan(self):
        f = self.texto("nuevo.md", "Agrega `src/futuro.ts` (nuevo) y usa `lib/ajena.js` (externo).\n")
        self.assertEqual(self.motor("revisar", f).returncode, 0)

    def test_referencia_inexistente_falla_y_estado_distinto_avisa(self):
        f = self.texto("ref.md", "El ticket T-9 también aplica en este cambio.\n")
        self.assertEqual(self.motor("revisar", f).returncode, 1)
        f = self.texto("estado.md", "El ticket T-1 sigue pendiente de cerrar aquí.\nEl ticket T-2 está terminado y resuelto.\n")
        r = self.motor("revisar", f)
        self.assertEqual(r.returncode, 0)  # un aviso no bloquea el nivel 1: lo resuelve la revisión independiente
        self.assertIn("su fuente dice «CERRADO»", r.stdout)
        self.assertIn("su fuente dice «ABIERTO»", r.stdout)
        self.assertIn("AVISOS DEL MOTOR", (self.d / (f + ".afirmaciones.md")).read_text(encoding="utf8"))

    def test_nivel_2_valida_informe(self):
        f = self.texto("n2.md", "Cambia `docs/real.md` y la compuerta siempre pasa en este repo.\n")
        self.motor("revisar", f)
        h = (self.d / (f + ".afirmaciones.md")).read_text(encoding="utf8").splitlines()[0].split()[1]
        (self.d / "inf-mal.md").write_text(f"HASH: {h}\nREFUTADAS: 1\nNO_VERIFICABLES: 0\n| C01 | REFUTADA | x |\n", encoding="utf8")
        self.assertEqual(self.motor("confirmar", f, "inf-mal.md").returncode, 1)
        (self.d / "inf-corto.md").write_text(f"HASH: {h}\nREFUTADAS: 0\nNO_VERIFICABLES: 0\n", encoding="utf8")
        self.assertEqual(self.motor("confirmar", f, "inf-corto.md").returncode, 1)  # no cubre las afirmaciones
        (self.d / "inf-otro.md").write_text("HASH: 000000000000\nREFUTADAS: 0\nNO_VERIFICABLES: 0\n| C01 | CONFIRMADA | x |\n", encoding="utf8")
        self.assertEqual(self.motor("confirmar", f, "inf-otro.md").returncode, 1)  # informe de otro texto
        (self.d / "inf-ok.md").write_text(f"HASH: {h}\nREFUTADAS: 0\nNO_VERIFICABLES: 1\n| C01 | NO VERIFICABLE | x |\n", encoding="utf8")
        self.assertEqual(self.motor("confirmar", f, "inf-ok.md").returncode, 0)

    def test_hook_bloquea_sin_marca_y_deja_pasar_lo_demas(self):
        ok = self.texto("h-ok.md", "Cambia `docs/real.md` hoy.\n")
        self.motor("revisar", ok)
        sin = self.texto("h-sin.md", "Texto sin verificar nunca.\n")
        publicar = "gh pr " + "create --title t --body-file "
        self.assertEqual(self.hook(publicar + ok), "pasa")
        self.assertEqual(self.hook(publicar + sin), "deny")
        self.assertEqual(self.hook("gh pr " + 'create --title t --body "inline"'), "deny")
        self.assertEqual(self.hook("gh pr " + "create --body-file -"), "deny")
        self.assertEqual(self.hook("gh issue " + "comment 4 --body-file no-existe.md"), "deny")
        self.assertEqual(self.hook("echo hola && gh pr " + "comment 3 --body-file " + sin), "deny")
        for lectura in ("gh pr view 12", "gh pr list", "ls -la", "gh pr " + "create --fill"):
            self.assertEqual(self.hook(lectura), "pasa", lectura)

    def test_hook_exige_nivel_2_si_se_configura(self):
        toml = (self.d / "entorno.toml").read_text(encoding="utf8")
        (self.d / "entorno.toml").write_text(toml.replace("exigir_nivel = 1", "exigir_nivel = 2"), encoding="utf8")
        try:
            f = self.texto("h-n1.md", "Cambia `docs/real.md` ahora.\n")
            self.motor("revisar", f)
            self.assertEqual(self.hook("gh pr " + "create --body-file " + f), "deny")
        finally:
            (self.d / "entorno.toml").write_text(toml, encoding="utf8")

    def test_error_interno_del_hook_no_bloquea(self):
        r = correr([sys.executable, "hooks/publicar-solo-verificado.py"], self.d, entrada="esto no es json",
                   env={"CLAUDE_PROJECT_DIR": str(self.d)})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
