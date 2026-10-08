"""Pruebas del script de arranque (sin red, HOME falso, descarga simulada con archivos locales)."""
import hashlib
import io
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "instalar.sh"
HERRAMIENTAS = ["sh", "bash", "sed", "awk", "sort", "tail", "basename", "dirname", "mktemp", "rm", "cp", "mkdir",
                "mv", "ln", "tar", "gzip", "sha256sum", "cat", "tr", "head", "env"]


class Base(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.t, True)
        self.home = self.t / "home"
        self.home.mkdir()
        self.paquete = self.crear_paquete("0.2.0")

    def crear_paquete(self, version, suma=None, programa=b"#!/bin/sh\necho harness\n"):
        ruta = self.t / f"meta-harness-{version}.tar.gz"
        with tarfile.open(ruta, "w:gz") as tf:
            datos = programa
            ti = tarfile.TarInfo(f"meta-harness-{version}/cli/harness")
            ti.size, ti.mode = len(datos), 0o755
            tf.addfile(ti, io.BytesIO(datos))
        real = hashlib.sha256(ruta.read_bytes()).hexdigest()
        Path(str(ruta) + ".sha256").write_text(f"{suma or real}  {ruta.name}\n")
        return ruta

    def bin_falso(self, python=None, sin_git=False):
        b = self.t / "bin"
        b.mkdir(exist_ok=True)
        for h in HERRAMIENTAS:
            ruta = shutil.which(h)
            if ruta and not (b / h).exists():
                (b / h).symlink_to(ruta)
        if not sin_git:
            (b / "git").symlink_to(shutil.which("git"))
        if python is None:
            (b / "python3").symlink_to(shutil.which("python3"))
        else:
            (b / "python3").write_text(f"#!/bin/sh\n[ \"$1\" = -V ] && echo 'Python {python}'\nexit 1\n")
            (b / "python3").chmod(0o755)
        return b

    def correr(self, *args, path=None, entrada=None, extra_env=None):
        env = {"HOME": str(self.home), "PATH": path or os.environ["PATH"], "TMPDIR": str(self.t), **(extra_env or {})}
        return subprocess.run(["sh", str(SCRIPT), *args], capture_output=True, text=True, env=env,
                              input=entrada, start_new_session=True)

    def instalado(self):
        return (self.home / ".local").exists()


class TestArranque(Base):
    def test_suma_correcta_instala_en_home_falso(self):
        r = self.correr("--origen", str(self.paquete), "--si")
        self.assertEqual(r.returncode, 0, r.stderr)
        dest = self.home / ".local/share/meta-harness/0.2.0"
        self.assertTrue((dest / "cli/harness").is_file())
        enlace = self.home / ".local/bin/harness"
        self.assertTrue(enlace.is_symlink())
        self.assertEqual(enlace.resolve(), (dest / "cli/harness").resolve())
        self.assertIn("PATH", r.stdout)  # avisa que hay que agregarlo
        self.assertLess(r.stdout.index("PLAN"), r.stdout.index("Instalado"))

    def test_suma_incorrecta_aborta_sin_dejar_nada(self):
        p = self.crear_paquete("0.3.0", suma="0" * 64)
        r = self.correr("--origen", str(p), "--si")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("NO coincide", r.stderr)
        self.assertFalse(self.instalado())
        self.assertEqual([x.name for x in self.t.glob("meta-harness.*")], [])  # sin temporales

    def test_falta_git(self):
        r = self.correr("--origen", str(self.paquete), "--si", path=str(self.bin_falso(sin_git=True)))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("FALTA git", r.stderr)
        self.assertIn("No se instalo nada", r.stderr)
        self.assertFalse(self.instalado())

    def test_python_version_baja(self):
        r = self.correr("--origen", str(self.paquete), "--si", path=str(self.bin_falso(python="3.9.1")))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Python >= 3.12", r.stderr)
        self.assertIn("3.9.1", r.stderr)
        self.assertFalse(self.instalado())

    def test_sin_terminal_y_sin_si_solo_muestra_el_plan(self):
        r = self.correr("--origen", str(self.paquete))
        self.assertEqual(r.returncode, 0)
        self.assertIn("PLAN", r.stdout)
        self.assertIn("0.2.0", r.stdout)
        self.assertIn(str(self.home / ".local/share/meta-harness/0.2.0"), r.stdout)
        self.assertIn("No se instalo nada", r.stdout)
        self.assertFalse(self.instalado())

    def test_version_explicita_y_enlace_ajeno_no_se_pisa(self):
        (self.home / ".local/bin").mkdir(parents=True)
        (self.home / ".local/bin/harness").write_text("mio")
        r = self.correr("--origen", str(self.paquete), "--version", "0.2.0", "--si")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.home / ".local/bin/harness").read_text(), "mio")
        self.assertIn("no lo toco", r.stderr)

    def test_sin_version_ni_origen_pide_version(self):
        r = self.correr("--version", "x", "--si")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(self.instalado())

    def test_marcador_sin_reemplazar_no_descarga(self):
        b = self.bin_falso()
        registro = self.t / "git.log"
        (b / "git").unlink()
        (b / "git").write_text(f"#!/bin/sh\necho \"$@\" >> {registro}\nexit 1\n")
        (b / "git").chmod(0o755)
        (b / "curl").write_text(f"#!/bin/sh\necho \"$@\" >> {registro}\nexit 1\n")
        (b / "curl").chmod(0o755)
        for args in (["--si"], ["--version", "1.2.3", "--si"]):
            r = self.correr(*args, path=str(b), extra_env={"MH_REPO": "https://github.com/ORGANIZACION/meta-harness",
                                                           "MH_URL_BASE": "https://github.com/ORGANIZACION/meta-harness/releases/download"})
            self.assertEqual(r.returncode, 1)
            self.assertIn("aún no está publicado", r.stderr)
            self.assertIn("MH_URL_BASE", r.stderr)
            self.assertIn("--origen", r.stderr)
        self.assertFalse(registro.exists())   # ni git ni curl se invocaron
        self.assertFalse(self.instalado())

    def test_una_sola_variable_define_el_repositorio(self):
        texto = SCRIPT.read_text()
        self.assertEqual(texto.count("github.com/catrroberrtt/meta-harness"), 1)   # un solo lugar donde vive la URL
        r = self.correr("--origen", str(self.paquete), "--si")        # --origen no necesita el repositorio
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_script_corto_sin_sudo_ni_credenciales(self):
        texto = SCRIPT.read_text()
        self.assertLess(len(texto.splitlines()), 120)
        codigo = "\n".join(l for l in texto.splitlines() if not l.lstrip().startswith("#"))
        self.assertNotRegex(codigo, r"\bsudo\b")
        self.assertNotIn("password", codigo.lower())


class TestRelevoAInstancia(Base):
    PROGRAMA = b'#!/bin/sh\necho "ARGS: $*" > "$HOME/args.txt"\ncat > "$HOME/stdin.txt"\n'

    def paquete_con_relevo(self):
        return self.crear_paquete("0.4.0", programa=self.PROGRAMA)

    def test_relevo_reconecta_stdin_a_la_terminal_y_pasa_los_argumentos(self):
        tty = self.t / "tty"
        tty.write_text("respuesta-de-terminal\n")
        r = self.correr("--origen", str(self.paquete_con_relevo()), "--si", "--instancia", "owner/nombre",
                        "--destino", "mi-carpeta", extra_env={"MH_TTY": str(tty)}, entrada="tuberia-curl\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.home / "args.txt").read_text().strip(), "ARGS: instalar owner/nombre --destino mi-carpeta --si")
        self.assertEqual((self.home / "stdin.txt").read_text(), "respuesta-de-terminal\n")   # no la tuberia
        self.assertIn("Despues:     harness instalar owner/nombre", r.stdout)

    def test_sin_terminal_dice_que_ejecutar_y_no_relevea(self):
        r = self.correr("--origen", str(self.paquete_con_relevo()), "--si", "--instancia", "owner/nombre",
                        extra_env={"MH_TTY": str(self.t / "no-existe")})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.home / "args.txt").exists())
        self.assertIn("ejecuta: harness instalar owner/nombre --si", r.stdout)

    def test_el_plan_menciona_el_relevo_y_no_muestra_credenciales(self):
        r = self.correr("--origen", str(self.paquete_con_relevo()), "--instancia", "https://u:ghp_SECRETO@h.invalid/o/n.git")
        self.assertEqual(r.returncode, 0)
        self.assertIn("harness instalar https://h.invalid/o/n.git", r.stdout)
        self.assertNotIn("ghp_SECRETO", r.stdout + r.stderr)

    def test_instancia_con_caracteres_raros_se_rechaza(self):
        r = self.correr("--origen", str(self.paquete), "--si", "--instancia", "a/b;rm -rf x")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(self.instalado())

    def test_sin_instancia_sigue_el_comportamiento_anterior(self):
        r = self.correr("--origen", str(self.paquete), "--si")
        self.assertIn("Siguiente paso: harness (asistente).", r.stdout)


if __name__ == "__main__":
    unittest.main()
