"""Pruebas de instalar-instancia.py con dobles de acceso y un repositorio local como «remoto»."""
import importlib.util
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ii", RAIZ / "instalador" / "instalar-instancia.py")
ii = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ii)


def git(cwd, *a):
    subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *a],
                   check=True, capture_output=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t, True)
        self.remoto = self.t / "remotos" / "instancia-demo"
        self.remoto.mkdir(parents=True)
        git(self.remoto, "init", "-q")
        (self.remoto / "harness.lock").write_text(
            'version = "%s"\nfuente = "x"\n' % (RAIZ / "VERSION").read_text().strip())
        (self.remoto / "restaurar.sh").write_text("echo hola\n")
        git(self.remoto, "add", "-A")
        git(self.remoto, "commit", "-q", "-m", "i")
        self.work = self.t / "trabajo"
        self.work.mkdir()
        self.llamadas = []

    def ejecutar(self, cmd):
        self.llamadas.append(cmd)
        if cmd[0] == "git":
            return subprocess.run(cmd, capture_output=True, text=True)
        return subprocess.CompletedProcess(cmd, 0, "update simulado", "")

    def correr(self, *args, acceso=(True, ""), tty=False, resp="s"):
        buf = io.StringIO()
        cod = ii.main(list(args), comprobar=lambda r: acceso, ejecutar=self.ejecutar, es_terminal=tty,
                      preguntar=lambda p: resp, salida=buf)
        return cod, buf.getvalue()


class TestInstanciaConAcceso(Base):
    def test_acceso_ok_muestra_plan_clona_y_actualiza(self):
        dest = self.work / "inst"
        cod, out = self.correr(str(self.remoto), "--destino", str(dest), "--si")
        self.assertEqual(cod, 0, out)
        self.assertLess(out.index("PLAN"), out.index("Clonado"))
        self.assertIn(str(dest), out)
        self.assertIn("coincide con la instalada", out)
        self.assertTrue((dest / "harness.lock").is_file())
        cmd = self.llamadas[-1]
        self.assertIn("update", cmd)
        self.assertIn("--aplicar", cmd)
        self.assertIn("Pendiente", out)  # restaurar.sh no se ejecuta con --si
        self.assertFalse(any("restaurar.sh" in " ".join(c) for c in self.llamadas))

    def test_lock_con_otra_version_se_informa(self):
        (self.remoto / "harness.lock").write_text('version = "9.9.9"\nfuente = "x"\n')
        git(self.remoto, "commit", "-qam", "v")
        cod, out = self.correr(str(self.remoto), "--destino", str(self.work / "i"), "--si")
        self.assertEqual(cod, 0)
        self.assertIn("DIFIERE", out)

    def test_solo_lectura_no_aplica(self):
        cod, out = self.correr(str(self.remoto), "--destino", str(self.work / "i"), "--si", "--solo-lectura")
        self.assertEqual(cod, 0)
        self.assertNotIn("--aplicar", self.llamadas[-1])

    def test_sin_terminal_y_sin_si_solo_plan(self):
        dest = self.work / "i"
        cod, out = self.correr(str(self.remoto), "--destino", str(dest))
        self.assertEqual(cod, 0)
        self.assertIn("solo se mostro el plan", out)
        self.assertFalse(dest.exists())
        self.assertEqual(self.llamadas, [])

    def test_terminal_respuesta_negativa_cancela(self):
        dest = self.work / "i"
        cod, out = self.correr(str(self.remoto), "--destino", str(dest), tty=True, resp="n")
        self.assertIn("Cancelado", out)
        self.assertFalse(dest.exists())

    def test_restaurar_solo_con_confirmacion_en_terminal(self):
        cod, out = self.correr(str(self.remoto), "--destino", str(self.work / "i"), tty=True, resp="s")
        self.assertEqual(cod, 0)
        self.assertTrue(any("restaurar.sh" in " ".join(c) for c in self.llamadas))


class TestInstanciaRechazos(Base):
    def test_sin_acceso_se_detiene_con_que_pedir_y_no_crea_destino(self):
        dest = self.work / "inst"
        cod, out = self.correr(str(self.remoto), "--destino", str(dest), "--si", acceso=(False, "denegado"))
        self.assertEqual(cod, 3)
        self.assertFalse(dest.exists())
        self.assertEqual(self.llamadas, [])
        for frag in ("instancia-demo", "LECTURA", "responsable del repositorio", "escritura solo si", "init"):
            self.assertIn(frag, out)

    def test_url_con_credenciales_no_aparece_en_ninguna_salida(self):
        url = "https://usuario:SECRETO123@ejemplo.org/org/instancia-demo.git"
        vistos = []
        buf = io.StringIO()
        cod = ii.main([url, "--destino", str(self.work / "i"), "--si"],
                      comprobar=lambda r: vistos.append(r) or (False, "fallo en " + url), ejecutar=self.ejecutar,
                      es_terminal=False, salida=buf)
        self.assertEqual(cod, 3)
        self.assertNotIn("SECRETO123", buf.getvalue())
        self.assertNotIn("usuario", buf.getvalue().replace("Aviso: se descarto el usuario:token", ""))
        self.assertEqual(vistos, ["https://ejemplo.org/org/instancia-demo.git"])  # ni se usa

    def test_credenciales_no_llegan_al_clon_ni_a_la_salida_con_acceso(self):
        url = "https://u:TOKEN9@ejemplo.org/o/r.git"
        buf = io.StringIO()
        ii.main([url, "--destino", str(self.work / "i"), "--si"], comprobar=lambda r: (True, ""),
                ejecutar=self.ejecutar, es_terminal=False, salida=buf)
        self.assertNotIn("TOKEN9", buf.getvalue())
        self.assertNotIn("TOKEN9", " ".join(" ".join(c) for c in self.llamadas))

    def test_destino_dentro_de_otro_repositorio_se_rechaza(self):
        git(self.work, "init", "-q")
        cod, out = self.correr(str(self.remoto), "--destino", str(self.work / "sub" / "i"), "--si")
        self.assertEqual(cod, 2)
        self.assertIn("dentro de otro repositorio", out)
        self.assertFalse((self.work / "sub").exists())
        self.assertEqual(self.llamadas, [])

    def test_destino_no_vacio_se_rechaza(self):
        d = self.work / "ocupado"
        d.mkdir()
        (d / "a").write_text("x")
        cod, _ = self.correr(str(self.remoto), "--destino", str(d), "--si")
        self.assertEqual(cod, 2)


class TestAccesoPorDefecto(Base):
    def test_ls_remote_local_ok_y_repo_inexistente_falla_sin_pedir_clave(self):
        self.assertTrue(ii.acceso_por_defecto(str(self.remoto), 10)[0])
        ok, motivo = ii.acceso_por_defecto(str(self.t / "no-existe"), 10)
        self.assertFalse(ok)

    def test_limpiar(self):
        self.assertEqual(ii.limpiar("https://a:b@h/x y ssh://git@h/z"), "https://h/x y ssh://h/z")
        self.assertEqual(ii.limpiar("git@h:o/r.git"), "git@h:o/r.git")


if __name__ == "__main__":
    unittest.main()
