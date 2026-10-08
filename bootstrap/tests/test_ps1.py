"""Pruebas estaticas de instalar.ps1 y WINDOWS.md (sin PowerShell: se lee el texto del script)."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parents[1]
PS1 = AQUI / "instalar.ps1"
GUIA = AQUI / "WINDOWS.md"


def _prohibidos():
    """Términos que no pueden aparecer en el script ni en la guía. Salen de un archivo LOCAL (HARNESS_PROHIBIDOS, uno por
    línea) que no vive en el repositorio; sin él solo se comprueban patrones genéricos (puertos de base de datos y rutas de usuario)."""
    import os
    terminos = []
    ruta = os.environ.get("HARNESS_PROHIBIDOS")
    if ruta and os.path.isfile(ruta):
        terminos = [re.escape(l.strip()) for l in open(ruta, encoding="utf8") if l.strip() and not l.startswith("#")]
    terminos += [r"\\b33(?:06|07|08|09)\\b", r"/home/[a-z0-9_.-]+/"]
    return "(?i)" + "|".join(terminos)


PROHIBIDOS = _prohibidos()


def sin_comentarios(texto):
    return "\n".join(l for l in texto.splitlines() if not l.lstrip().startswith("#"))


class Ps1Estatico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.crudo = PS1.read_bytes()
        cls.texto = cls.crudo.decode("ascii")
        cls.codigo = sin_comentarios(cls.texto)

    def test_ascii_puro(self):
        self.assertTrue(all(b < 128 for b in self.crudo))

    def test_sin_sintaxis_de_powershell_7(self):
        for malo in ("&&", "||", "?.", "??", "-Parallel"):
            self.assertNotIn(malo, self.texto, malo)
        self.assertIsNone(re.search(r"\s\?\s", self.texto), "ternario")

    def test_param_con_los_cinco_parametros(self):
        self.assertIn("param(", self.texto)
        bloque = self.texto.split("param(", 1)[1].split(")", 1)[0]
        for p in ("$Instancia", "$Distribucion", "$Version", "$Si", "$SoloPlan"):
            self.assertIn(p, bloque)
        self.assertIn("'Ubuntu-24.04'", bloque)

    def test_ignora_docker_desktop(self):
        self.assertIn("docker-desktop", self.codigo)
        self.assertIn("docker-desktop-data", self.codigo)

    def test_limpia_nul_de_la_salida_de_wsl(self):
        self.assertIn('-replace "`0"', self.codigo)
        self.assertIn('-replace "`r"', self.codigo)

    def test_nunca_usa_rutas_de_windows_montadas(self):
        self.assertNotIn("/mnt/", self.texto)
        self.assertIn("'--cd', '~'", self.codigo)
        self.assertIn("if cd ~;", self.codigo)

    def test_confirma_antes_de_wsl_install(self):
        i_conf = self.codigo.index("Confirmar-Siempre 'Instalar Ubuntu")
        i_inst = self.codigo.index("& wsl.exe --install")
        self.assertLess(i_conf, i_inst)
        self.assertEqual(self.codigo.count("& wsl.exe --install"), 1)

    def test_comprueba_administrador_antes_de_instalar(self):
        self.assertIn("[Security.Principal.WindowsPrincipal]", self.texto.replace("New-Object Security.Principal.WindowsPrincipal", "[Security.Principal.WindowsPrincipal]"))
        self.assertLess(self.codigo.index("if (-not $EsAdmin)"), self.codigo.index("& wsl.exe --install"))

    def test_solo_plan_no_ejecuta(self):
        self.assertIn("if ($SoloPlan) { return $false }", self.codigo)
        self.assertLess(self.codigo.index("if ($SoloPlan)\n") if "if ($SoloPlan)\n" in self.codigo else self.codigo.index("if ($SoloPlan) {\n"),
                        self.codigo.index("& wsl.exe --install"))

    def test_comprobaciones_dentro_de_la_distro(self):
        for c in ("python3 --version", "git --version", "curl --version", "echo", "'ok'"):
            self.assertIn(c, self.codigo)
        self.assertIn("-ge 12", self.codigo)

    def test_comando_linux_y_entrada_no_redirigida(self):
        self.assertIn("curl -fsSL ", self.codigo)
        self.assertIn("| sh -s --", self.codigo)
        self.assertIn("--instancia", self.codigo)
        self.assertIn("--version", self.codigo)
        self.assertIn("'bash', '-lc'", self.codigo)
        self.assertNotIn("Invoke-Expression", self.codigo)
        self.assertNotIn("| iex", self.codigo)

    def test_sin_credenciales_ni_urls_con_usuario(self):
        self.assertIsNone(re.search(r"https?://[^/\s]*@", self.texto))
        self.assertIsNone(re.search(r"(?i)(ghp_|github_pat_|token\s*=|password\s*=|secret)", self.texto))
        self.assertNotIn("Get-Credential", self.texto)
        self.assertNotIn("ConvertTo-SecureString", self.texto)

    def test_sin_nombres_propios(self):
        self.assertIsNone(re.search(PROHIBIDOS, self.texto))

    def test_valida_entradas(self):
        for patron in ("-notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'", "-notmatch '^[0-9]+\\.[0-9]+\\.[0-9]+$'"):
            self.assertIn(patron, self.codigo)


class GuiaCoincideConScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guia = GUIA.read_text(encoding="utf-8")
        cls.ps1 = PS1.read_text(encoding="ascii")

    def test_cabeceras(self):
        lineas = self.guia.splitlines()
        self.assertTrue(lineas[0].startswith("# "))
        self.assertIn("<!-- tipo: guia · capa: 4 -->", self.guia)
        self.assertRegex(self.guia, r"<!-- revisado: \d{4}-\d{2}-\d{2} · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->")

    def test_mensajes_clave_coinciden(self):
        for frase in ("wsl --install -d Ubuntu-24.04", "docker-desktop", "Ejecutar como administrador",
                      "-SoloPlan", "-Instancia", "-Distribucion", "-Version", "-Si", "wsl -d <distro> -- echo ok"):
            self.assertIn(frase, self.guia, frase)
        for frase in ("wsl --install -d", "Ejecutar como administrador", "docker-desktop", "hace falta Python 3.12",
                      "crear un usuario y una contrasena de Linux", "integracion con WSL", "El claude de Windows no es el de Ubuntu",
                      "echo ok", "reiniciar"):
            self.assertIn(frase, self.ps1, frase)
        self.assertIn("integración con WSL", self.guia)
        self.assertIn("El `claude` de Windows no es el de Ubuntu", self.guia)
        self.assertIn("reiniciar", self.guia)

    def test_url_igual_en_guia_y_script(self):
        url = "https://raw.githubusercontent.com/catrroberrtt/meta-harness/main/bootstrap"
        self.assertIn(url + "/instalar.ps1", self.guia)
        self.assertIn(url, self.ps1)

    def test_sin_nombres_propios(self):
        self.assertIsNone(re.search(PROHIBIDOS, self.guia))


@unittest.skipUnless(shutil.which("pwsh"), "pwsh (PowerShell 7) no esta instalado")
class ParseoConPwsh(unittest.TestCase):
    def test_el_script_parsea_sin_errores(self):
        orden = ("$e=$null;$t=$null;[void][System.Management.Automation.Language.Parser]::ParseFile("
                 "'%s',[ref]$t,[ref]$e);if($e.Count -gt 0){$e|ForEach-Object{$_.Message};exit 1}" % PS1)
        r = subprocess.run(["pwsh", "-NoProfile", "-Command", orden], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
