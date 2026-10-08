import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("preflight", os.path.join(AQUI, "..", "preflight-accesos.py"))
pf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pf)

POLITICA = """
[datos]
hosts_locales = ["localhost"]
[[datos.ambientes]]
nombre = "local"
tipo = "local"
[[datos.ambientes]]
nombre = "pruebas"
tipo = "pruebas"
[[datos.ambientes]]
nombre = "prod"
tipo = "produccion"
"""
SECRETO = "valor-super-secreto-123"


class Doble(pf.Sondas):
    """Sondas simuladas: sin red, sin comandos reales, sin archivos de la persona."""
    def __init__(self, tcp=(), comandos=("git", "ssh", "aws", "gh", "session-manager-plugin"),
                 perfiles=(), rutas=(), llenas=None, sesion=True, vars_=(), gh=True, helper=True):
        self.tcp_ok, self.cmds, self.perfiles = set(tcp), set(comandos), set(perfiles)
        self.rutas, self.llenas, self.sesion, self.vars_ = set(rutas), set(rutas if llenas is None else llenas), sesion, set(vars_)
        self.gh, self.helper = gh, helper
        self.llamadas = []

    def comando(self, n): return n in self.cmds
    def tcp(self, h, p, t):
        self.llamadas.append((h, p)); return (h, p) in self.tcp_ok
    def perfil_nube(self, n): return n in self.perfiles
    def sesion_nube(self, p, t): return self.sesion
    def variable_entorno(self, n): return n in self.vars_
    def ruta_existe(self, r): return r in self.rutas
    def contenido(self, r): return r in self.llenas
    def gestor_credenciales_git(self): return self.helper
    def gh_autenticado(self): return self.gh


BASE_A = """
[repositorios]
metodo = "gh"
[documentacion]
metodo = "carpeta_repo"
carpeta = "/docs"
[tickets]
metodo = "ninguno"
[nube]
metodo = "perfil_sso"
perfil = "mi-perfil"
[datos.local]
metodo = "directo"
host = "localhost"
puerto = 5000
[datos.pruebas]
metodo = "directo"
host = "pruebas.ejemplo"
puerto = 5001
"""


def correr(politica, acceso, argv, sondas):
    with tempfile.TemporaryDirectory() as d:
        pp, pa = os.path.join(d, "p.toml"), os.path.join(d, "a.toml")
        for ruta, txt in ((pp, politica), (pa, acceso)):
            with open(ruta, "w") as f:
                f.write(txt)
        out = io.StringIO()
        err = io.StringIO()
        viejo = sys.stderr
        sys.stderr = err
        try:
            rc = pf.main(["--politica", pp, "--acceso", pa] + argv, sondas, out)
        finally:
            sys.stderr = viejo
        return rc, out.getvalue(), err.getvalue()


def sondas_a(**kw):
    base = dict(tcp={("localhost", 5000), ("pruebas.ejemplo", 5001)}, perfiles={"mi-perfil"}, rutas={"/docs"})
    base.update(kw)
    return Doble(**base)


class PartidaA(unittest.TestCase):
    def test_dos_personas_distintos_metodos(self):
        directa = BASE_A
        tunel = BASE_A.replace('metodo = "directo"\nhost = "pruebas.ejemplo"\npuerto = 5001',
                               'metodo = "tunel_ssh"\nhost = "127.0.0.1"\npuerto = 6001')
        r1 = correr(POLITICA, directa, ["--modo", "adopt"], sondas_a())
        r2 = correr(POLITICA, tunel, ["--modo", "adopt"], sondas_a(tcp={("localhost", 5000), ("127.0.0.1", 6001)}))
        self.assertEqual(r1[0], 0, r1[1])
        self.assertEqual(r2[0], 0, r2[1])
        self.assertIn("directo", r1[1])
        self.assertIn("tunel_ssh", r2[1])
        self.assertNotIn("tunel_ssh", r1[1])

    def test_sin_acceso_a_datos_y_luego_degradado(self):
        sin = BASE_A.replace('metodo = "directo"\nhost = "pruebas.ejemplo"\npuerto = 5001', 'metodo = "sin_acceso"')
        rc, out, _ = correr(POLITICA, sin, ["--modo", "adopt"], sondas_a())
        self.assertEqual(rc, 2)
        self.assertIn("datos:pruebas", out)
        self.assertIn("Pedir", out)
        with tempfile.TemporaryDirectory() as d:
            reg = os.path.join(d, "limite.txt")
            rc, out, _ = correr(POLITICA, sin, ["--modo", "adopt", "--aceptar-degradado", "datos", "--registrar", reg], sondas_a())
            self.assertEqual(rc, 0)
            self.assertIn("verificacion con datos: NO DISPONIBLE (sin acceso)", out)
            self.assertIn("DEGRADADO", out)
            with open(reg) as f:
                self.assertIn("NO DISPONIBLE", f.read())

    def test_tunel_cerrado_falta(self):
        t = BASE_A.replace('metodo = "directo"\nhost = "pruebas.ejemplo"\npuerto = 5001',
                           'metodo = "tunel_ssh"\nhost = "127.0.0.1"\npuerto = 6001')
        rc, out, _ = correr(POLITICA, t, ["--modo", "adopt"], sondas_a())
        self.assertEqual(rc, 2)
        self.assertIn("tunel SSH", out)

    def test_secreto_no_se_muestra(self):
        acc = BASE_A + f'\n[datos.local]\n' if False else BASE_A.replace(
            '[datos.local]\n', f'[datos.local]\nclave = "{SECRETO}"\n')
        with tempfile.TemporaryDirectory() as d:
            reg = os.path.join(d, "r.txt")
            sin = acc.replace('metodo = "directo"\nhost = "pruebas.ejemplo"\npuerto = 5001', 'metodo = "sin_acceso"')
            for extra in ([], ["--json"], ["--aceptar-degradado", "datos", "--registrar", reg]):
                rc, out, err = correr(POLITICA, sin, ["--modo", "adopt"] + extra, sondas_a())
                self.assertNotIn(SECRETO, out + err)
            with open(reg) as f:
                self.assertNotIn(SECRETO, f.read())
        rc, out, _ = correr(POLITICA, acc, ["--modo", "adopt"], sondas_a())
        self.assertIn("datos.local.clave", out)
        self.assertEqual(rc, 0)

    def test_politica_sin_ambientes(self):
        rc, out, err = correr("[datos]\nhosts_locales=['x']\n", BASE_A, ["--modo", "adopt"], sondas_a())
        self.assertEqual(rc, 1)
        self.assertIn("ningun ambiente", err)
        rc, _, err = correr("", BASE_A, ["--modo", "adopt"], sondas_a())
        self.assertEqual(rc, 1)

    def test_nube_perfil_ausente_y_sesion_vencida(self):
        rc, out, _ = correr(POLITICA, BASE_A, ["--modo", "adopt"], sondas_a(perfiles=()))
        self.assertEqual(rc, 2)
        self.assertIn("configurar el perfil", out)
        rc, out, _ = correr(POLITICA, BASE_A, ["--modo", "adopt"], sondas_a(sesion=False))
        self.assertEqual(rc, 2)
        self.assertIn("sesion no esta vigente", out)

    def test_update_no_exige_datos(self):
        rc, out, _ = correr(POLITICA, BASE_A.replace("[datos.local]", "[x]"), ["--modo", "update"], sondas_a(tcp=()))
        self.assertEqual(rc, 0, out)


class PartidaB(unittest.TestCase):
    ACC = '[documentacion]\nmetodo = "carpeta_repo"\ncarpeta = "/info"\n'

    def test_b_sin_datos_pero_con_almacen(self):
        rc, out, _ = correr("", self.ACC, ["--partida", "B"], Doble(rutas={"/info"}))
        self.assertEqual(rc, 0, out)
        self.assertIn("partida B", out)
        self.assertNotIn("datos:", out)

    def test_b_sin_almacen(self):
        rc, out, _ = correr("", "", ["--partida", "B"], Doble())
        self.assertEqual(rc, 2)
        self.assertIn("documentacion", out)
        self.assertIn("poner", out)

    def test_b_carpeta_inexistente_o_vacia(self):
        rc, out, _ = correr("", self.ACC, ["--partida", "B"], Doble())
        self.assertEqual(rc, 2)
        self.assertIn("no existe", out)
        rc, out, _ = correr("", self.ACC, ["--partida", "B"], Doble(rutas={"/info"}, llenas=()))
        self.assertEqual(rc, 2)
        self.assertIn("vacia", out)

    def test_b_datos_y_nube_declarados_no_bloquean(self):
        acc = self.ACC + '[nube]\nmetodo = "sin_acceso"\n'
        rc, out, _ = correr(POLITICA, acc, ["--partida", "B"], Doble(rutas={"/info"}))
        self.assertEqual(rc, 0, out)
        self.assertIn("se pedira cuando el plan lo necesite", out)


class PartidaC(unittest.TestCase):
    def test_c_con_origen(self):
        acc = '[origen]\nmetodo = "descripcion"\nruta = "/origen"\n'
        rc, out, _ = correr("", acc, ["--partida", "C"], Doble(rutas={"/origen"}))
        self.assertEqual(rc, 0, out)
        self.assertIn("migrar", out)

    def test_c_sin_origen(self):
        rc, out, _ = correr("", "", ["--partida", "C"], Doble())
        self.assertEqual(rc, 2)
        self.assertIn("origen", out)
        self.assertIn("descripcion", out)

    def test_c_origen_sin_acceso(self):
        rc, out, _ = correr("", '[origen]\nmetodo = "sin_acceso"\n', ["--partida", "C"], Doble())
        self.assertEqual(rc, 2)

    def test_partida_invalida(self):
        with self.assertRaises(SystemExit):
            correr("", "", ["--partida", "Z"], Doble())


class Json(unittest.TestCase):
    def test_json_valido(self):
        rc, out, _ = correr(POLITICA, BASE_A, ["--modo", "adopt", "--json"], sondas_a())
        d = json.loads(out)
        self.assertTrue(d["puede_orquestar"])
        self.assertEqual(d["partida"], "A")

    def test_registro_dentro_de_proyecto_rechazado(self):
        with tempfile.TemporaryDirectory() as d:
            rc, _, err = correr(POLITICA, BASE_A, ["--modo", "adopt", "--aceptar-degradado", "datos",
                                                    "--registrar", os.path.join(d, "x.txt"), "--proyecto", d], sondas_a())
            self.assertEqual(rc, 1)
            self.assertIn("proyecto analizado", err)


if __name__ == "__main__":
    unittest.main()
