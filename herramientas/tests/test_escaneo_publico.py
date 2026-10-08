import contextlib, importlib.util, io, json, pathlib, subprocess, tempfile, unittest

spec = importlib.util.spec_from_file_location("escaneo", pathlib.Path(__file__).resolve().parent.parent / "harness-escaneo-publico.py")
es = importlib.util.module_from_spec(spec); spec.loader.exec_module(es)

# Valores falsos construidos por partes: este archivo no debe disparar el escaneo.
CLAVE = "AK" + "IA" + "ZZ9QWERTY1234567"
CUENTA = "4827" + "1935" + "0612"
CORREO = "maria.gomez" + "@" + "acme-corp" + ".com"
PASS = "Zq8" + "vK2mP" + "x7Lw"
TERMINO = "zorroazul" + "corp"


def correr(raiz, *extra):
    sal = io.StringIO()
    with contextlib.redirect_stdout(sal):
        code = es.main([str(raiz), *extra])
    return code, sal.getvalue()


def git(raiz, *a):
    subprocess.run(["git", "-C", str(raiz), "-c", "user.email=dev@example.com", "-c", "user.name=dev", *a], check=True, capture_output=True)


class Escaneo(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.raiz = pathlib.Path(self.t.name)
        self.lista = self.raiz.parent / (self.raiz.name + "-prohibidos.txt")
        self.lista.write_text(f"# comentario\n{TERMINO}\n")
    def tearDown(self): self.t.cleanup(); self.lista.unlink(missing_ok=True)
    def w(self, n, txt):
        p = self.raiz / n; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt)

    def test_limpio(self):
        self.w("README.md", "# Proyecto\nContacto: dev@example.com\npassword = <tu-clave>\ntoken: ${TOKEN}\nIP 127.0.0.1 y 192.0.2.10\n")  # escaneo-publico: ignorar
        self.w(".env.example", "API_KEY=changeme\n")  # escaneo-publico: ignorar
        code, out = correr(self.raiz, "--lista-prohibidos", str(self.lista), "--sin-historial")
        self.assertEqual(code, 0, out)

    def test_clase_secreto_y_valor_oculto(self):
        self.w("a.py", f'aws = "{CLAVE}"\ndb = "postgres://app:{PASS}@db.example.com/x"\npassword = "{PASS}"\n')  # escaneo-publico: ignorar
        code, out = correr(self.raiz, "--sin-historial")
        self.assertEqual(code, 1)
        self.assertGreaterEqual(out.count("secreto"), 3)
        for v in (CLAVE, PASS):
            self.assertNotIn(v, out)
        code, js = correr(self.raiz, "--json", "--sin-historial")
        self.assertNotIn(CLAVE, js); self.assertNotIn(PASS, js)

    def test_cuenta_correo_ip(self):
        self.w("i.md", f"cuenta aws {CUENTA}\nescribe a {CORREO}\nhost 10.20.30.40 y 8.8.4.4\n")  # escaneo-publico: ignorar
        code, out = correr(self.raiz, "--sin-historial")
        self.assertEqual(code, 1)
        self.assertIn("cuenta de 12 dígitos", out); self.assertIn("correo", out)
        self.assertIn("IP privada", out); self.assertIn("IP pública", out)
        for v in (CUENTA, CORREO, "10.20.30.40", "8.8.4.4"):  # escaneo-publico: ignorar
            self.assertNotIn(v, out)
        self.assertIn("i.md:1", out)

    def test_numero_largo_sin_contexto_no_es_cuenta(self):
        self.w("n.md", f"id {CUENTA}\n")
        self.assertEqual(correr(self.raiz, "--sin-historial")[0], 0)

    def test_archivo_env(self):
        self.w(".env", "X=1\n"); self.w("volcado.sql", "select 1;")
        code, out = correr(self.raiz, "--sin-historial")
        self.assertEqual(code, 1); self.assertEqual(out.count("archivo que no debe"), 2)

    def test_prohibido_y_aviso_sin_lista(self):
        self.w("d.md", f"hecho para {TERMINO} en 2026\n")
        code, out = correr(self.raiz, "--lista-prohibidos", str(self.lista), "--sin-historial")
        self.assertEqual(code, 1); self.assertIn("prohibido", out); self.assertNotIn(TERMINO, out)
        self.w("d.md", "limpio\n")
        code, out = correr(self.raiz, "--sin-historial")
        self.assertEqual(code, 0); self.assertIn("NO COMPROBADA", out)
        self.assertEqual(correr(self.raiz, "--sin-historial", "--exigir-listas")[0], 2)

    def test_lista_en_raiz_y_nombres(self):
        self.w(".prohibidos.txt", TERMINO + "\n"); self.w(".nombres.txt", "Lucrecia\n")
        self.w("x.md", f"{TERMINO}\nGracias a Lucrecia\n")
        code, out = correr(self.raiz, "--sin-historial")
        self.assertEqual(code, 1); self.assertIn("prohibido", out); self.assertIn("persona", out)
        self.assertNotIn("Lucrecia", out)

    def test_marcador_ignorar(self):
        self.w("e.md", f"clave {CLAVE} escaneo-publico: ignorar\n")
        self.assertEqual(correr(self.raiz, "--sin-historial")[0], 0)

    def test_secreto_solo_en_historial(self):
        git(self.raiz, "init", "-q")
        self.w("config.txt", f"token = {PASS}\n")  # escaneo-publico: ignorar
        git(self.raiz, "add", "."); git(self.raiz, "commit", "-qm", "viejo")
        self.w("config.txt", "token = ${TOKEN}\n")  # escaneo-publico: ignorar
        git(self.raiz, "add", "."); git(self.raiz, "commit", "-qm", "limpio")
        code, out = correr(self.raiz)
        self.assertEqual(code, 1)
        self.assertIn("== ÁRBOL DE TRABAJO: 0", out)
        self.assertIn("HISTORIAL GIT (ya estaría público): 1", out)
        self.assertIn("[commit ", out); self.assertNotIn(PASS, out)
        code, js = correr(self.raiz, "--json"); d = json.loads(js)
        self.assertEqual((len(d["arbol"]), len(d["historial"])), (0, 1)); self.assertNotIn(PASS, js)
        self.assertEqual(correr(self.raiz, "--sin-historial")[0], 0)

    def test_historial_limpio_y_autor_real(self):
        git(self.raiz, "init", "-q"); self.w("a.md", "hola\n"); git(self.raiz, "add", "."); git(self.raiz, "commit", "-qm", "uno")
        self.assertEqual(correr(self.raiz)[0], 0)
        subprocess.run(["git", "-C", str(self.raiz), "-c", f"user.email={CORREO}", "-c", "user.name=x", "commit", "-q", "--allow-empty", "-m", "dos"], check=True, capture_output=True)
        code, out = correr(self.raiz)
        self.assertEqual(code, 1); self.assertIn("autor", out); self.assertNotIn(CORREO, out)

    def test_archivo_borrado_pero_en_historial(self):
        git(self.raiz, "init", "-q"); self.w("llave.pem", "x\n"); git(self.raiz, "add", "."); git(self.raiz, "commit", "-qm", "a")
        (self.raiz / "llave.pem").unlink(); git(self.raiz, "add", "-A"); git(self.raiz, "commit", "-qm", "b")
        code, out = correr(self.raiz)
        self.assertEqual(code, 1); self.assertIn("existió en el historial", out)


class ListaDePermitidos(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        (self.d / "t").mkdir()
        self.f = self.d / "t" / "datos.txt"
        self.f.write_text(f'password = "{PASS}"\n', encoding="utf8")

    def test_sin_lista_hay_hallazgo(self):
        code, _ = correr(self.d, "--sin-historial")
        self.assertEqual(code, 1)

    def test_excepcion_con_motivo_acepta_y_se_ve(self):
        (self.d / ".permitidos.txt").write_text("t/*.txt | secreto | valor falso de una prueba, revisado\n", encoding="utf8")
        code, out = correr(self.d, "--sin-historial")
        self.assertEqual(code, 0)
        self.assertIn("EXCEPCIONES REVISADAS", out)
        self.assertIn("valor falso de una prueba", out)

    def test_sin_motivo_es_error(self):
        (self.d / ".permitidos.txt").write_text("t/*.txt | secreto |\n", encoding="utf8")
        code, _ = correr(self.d, "--sin-historial")
        self.assertEqual(code, 2)

    def test_motivo_corto_es_error(self):
        (self.d / ".permitidos.txt").write_text("t/*.txt | secreto | ok\n", encoding="utf8")
        code, _ = correr(self.d, "--sin-historial")
        self.assertEqual(code, 2)

    def test_prohibido_nunca_se_exceptua(self):
        (self.d / ".permitidos.txt").write_text("* | prohibido | no deberia poder aceptarse esto\n", encoding="utf8")
        code, _ = correr(self.d, "--sin-historial")
        self.assertEqual(code, 2)

    def test_la_excepcion_solo_vale_para_su_ruta_y_clase(self):
        (self.d / ".permitidos.txt").write_text("otra/*.txt | secreto | valor falso de una prueba, revisado\n", encoding="utf8")
        self.assertEqual(correr(self.d, "--sin-historial")[0], 1)
        (self.d / ".permitidos.txt").write_text("t/*.txt | persona | valor falso de una prueba, revisado\n", encoding="utf8")
        self.assertEqual(correr(self.d, "--sin-historial")[0], 1)


if __name__ == "__main__":
    unittest.main()
