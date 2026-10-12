"""`harness doctor --bundle`: paquete de diagnóstico para pegar a quien atiende un problema. Nunca debe llevar secretos ni rutas personales.

<!-- tipo: herramienta · capa: 4 -->
Todo en carpetas temporales; los secretos que se usan son inventados y se arman en ejecución para no disparar el escaneo del propio repositorio.
"""
import importlib.util, io, json, pathlib, tempfile, unittest, contextlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent.parent
spec = importlib.util.spec_from_file_location("harness_cli_bundle", RAIZ / "cli" / "harness_cli.py")
hc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hc)

CASA = "/home/alguien"
AKIA = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
GHP = "gh" + "p_" + "a" * 36
# Secretos inventados, armados en ejecución: escritos de corrido dispararían el escaneo de publicación del propio repositorio.
CLAVE_PASS = "pass" + "word = hunter2secreto"
CLAVE_API = "api" + "_key: abcdef123456"
CLAVE_TOKEN = "TOK" + "EN=xyz"
URL_CRED = "https://" + "usuario:clave123" + "@host/repo"
LLAVE = "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIabc\n-----END " + "RSA PRIVATE KEY-----"


class Redaccion(unittest.TestCase):
    def test_oculta_secretos_conocidos(self):
        for texto in (f"clave {AKIA} fin", f"token {GHP} fin", CLAVE_PASS, CLAVE_API, CLAVE_TOKEN, URL_CRED, LLAVE):
            salida = hc.redactar(texto, CASA)
            self.assertIn("«oculto»", salida, texto)
            for secreto in (AKIA, GHP, "hunter2secreto", "abcdef123456", "xyz", "clave123", "MIIabc"):
                self.assertNotIn(secreto, salida)

    def test_la_ruta_personal_se_reemplaza_por_tilde(self):
        self.assertEqual(hc.redactar(f"{CASA}/proyecto/x.py", CASA), "~/proyecto/x.py")

    def test_recorre_estructuras_incluidas_las_claves(self):
        salida = hc.redactar({f"{CASA}/k": [f"password=zzz {AKIA}"], "n": 3, "ok": None}, CASA)
        self.assertEqual(list(salida), ["~/k", "n", "ok"])
        self.assertNotIn("zzz", json.dumps(salida))
        self.assertNotIn(AKIA, json.dumps(salida))
        self.assertEqual((salida["n"], salida["ok"]), (3, None))

    def test_un_texto_normal_no_se_toca(self):
        self.assertEqual(hc.redactar("Versión del harness 0.6.0: todo bien", CASA), "Versión del harness 0.6.0: todo bien")


class Paquete(unittest.TestCase):
    def paquete(self, instancia=None):
        return hc.paquete_diagnostico(instancia, RAIZ)

    def test_trae_lo_necesario_para_atender_un_problema(self):
        p = self.paquete()
        for clave in ("paquete", "harness", "python", "sistema", "herramientas", "doctor", "resumen"):
            self.assertIn(clave, p)
        self.assertEqual(p["paquete"], "diagnostico-harness")
        self.assertEqual(p["resumen"]["total"], len(p["doctor"]))

    def test_no_lleva_la_ruta_personal_de_quien_lo_genera(self):
        casa = str(pathlib.Path.home())
        self.assertNotIn(casa, json.dumps(self.paquete(), ensure_ascii=False))

    def test_instancia_con_secretos_no_los_filtra(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t)
            (d / "acceso.local.toml").write_text("\n".join(["tok" + "en = " + GHP, "cla" + "ve = " + AKIA]) + "\n", encoding="utf8")
            (d / "README.md").write_text(f"mi clave es {AKIA}\n", encoding="utf8")
            texto = json.dumps(self.paquete(d), ensure_ascii=False)
            self.assertNotIn(GHP, texto)
            self.assertNotIn(AKIA, texto)

    def test_incluye_el_entorno_propio_si_hay_lock(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t)
            (d / "entorno.lock.json").write_text(json.dumps({"generador": "meta-harness 0.6.0", "fecha": "2026-10-12",
                                                             "opciones": {"modulos": ["aprendizaje"]}, "archivos": {"a": "1", "b": "2"}}), encoding="utf8")
            p = self.paquete(d)
            self.assertEqual(p["entorno_propio"]["modulos"], ["aprendizaje"])
            self.assertEqual(p["entorno_propio"]["archivos"], 2)

    def test_lock_ilegible_no_rompe_el_paquete(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t)
            (d / "entorno.lock.json").write_text("no es json", encoding="utf8")
            self.assertEqual(self.paquete(d)["entorno_propio"], {"error": "entorno.lock.json ilegible"})

    def test_comando_de_linea_imprime_json_valido(self):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = hc.main(["doctor", "--bundle", "--harness", str(RAIZ)])
        self.assertEqual(codigo, 0)
        self.assertEqual(json.loads(salida.getvalue())["paquete"], "diagnostico-harness")


if __name__ == "__main__":
    unittest.main()
