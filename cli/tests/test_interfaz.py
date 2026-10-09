"""Pruebas de la interfaz del comando `harness`: ayuda por momentos, errores accionables y los comandos `siguiente`, `trazar` y `ayuda`.
Todo en carpetas temporales; sin red. Los comandos nuevos son de solo lectura: se comprueba que no cambian el árbol."""
import json
import re
import shutil
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest import mock
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cli import Base, CLI, RAIZ, arbol_hash, hc  # noqa: E402

EJEMPLO = RAIZ / "plantillas" / "ejemplos" / "cambio-ejemplo"


def cli(*args):
    r = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout, r.stderr


class Ayuda(unittest.TestCase):
    def test_h_agrupa_por_momento_y_nombra_todos_los_comandos(self):
        c, out, _ = cli("-h")
        self.assertEqual(c, 0)
        for momento in ("INSTALAR", "ADOPTAR", "EMPEZAR", "TRABAJAR", "VERIFICAR", "ACTUALIZAR"):
            self.assertIn(momento, out)
        for sub in hc.SUBCOMANDOS:
            if sub != "ayuda":
                self.assertRegex(out, rf"harness {sub}\b", sub)
        self.assertIn("docs/MAPA-DE-COMANDOS.md", out)

    def test_orden_de_los_momentos(self):
        _, out, _ = cli("-h")
        pos = [out.index(m) for m in ("1. INSTALAR", "2. ADOPTAR", "3. EMPEZAR", "4. TRABAJAR", "5. VERIFICAR", "6. ACTUALIZAR")]
        self.assertEqual(pos, sorted(pos))

    def test_el_mapa_por_momentos_va_antes_que_las_opciones_tecnicas(self):
        """Decisión 2026-10-09: `harness -h` y `harness ayuda` muestran primero «qué comando uso cuándo»."""
        for args in (("-h",), ("ayuda",)):
            _, out, _ = cli(*args)
            self.assertTrue(out.startswith("Qué comando uso cuándo"), args)
            self.assertLess(out.index("1. INSTALAR"), out.index("usage:"))
            self.assertLess(out.index("6. ACTUALIZAR"), out.index("usage:"))
            self.assertLess(out.index("6. ACTUALIZAR"), out.index("--carpeta CARPETA"))
            self.assertEqual(out.count("Qué comando uso cuándo"), 1)

    def test_ayuda_equivale_a_h(self):
        c1, o1, _ = cli("ayuda")
        c2, o2, _ = cli("-h")
        self.assertEqual((c1, o1), (c2, o2))

    def test_cada_subcomando_acepta_h_con_ejemplos(self):
        for sub in hc.SUBCOMANDOS:
            if sub == "ayuda":
                continue
            c, out, _ = cli(sub, "-h")
            self.assertEqual(c, 0, sub)
            self.assertIn("Ejemplos", out, sub)

    def test_comando_inexistente_sugiere_el_parecido(self):
        c, _, err = cli("estdo")
        self.assertEqual(c, 2)
        self.assertIn("harness estado", err)
        self.assertNotIn("Traceback", err)
        c, _, err = cli("zzzzzz")
        self.assertEqual(c, 2)
        self.assertIn("Comandos:", err)

    def test_falta_un_argumento_da_ejemplos_en_espanol(self):
        c, _, err = cli("instalar")
        self.assertEqual(c, 2)
        self.assertIn("falta indicar: instancia", err)
        self.assertIn("Ejemplos:", err)

    def test_el_asistente_sigue_aceptando_sus_banderas(self):
        c, out, _ = cli("--no-interactivo", "--carpeta", str(RAIZ / "plantillas" / "ejemplos"), "--json")
        self.assertIn(c, (0, 2))


class Errores(Base):
    def test_estado_de_carpeta_inexistente(self):
        buf = StringIO()
        c = hc.main(["estado", str(self.tmp / "no-existe")], salida=buf)
        self.assertEqual(c, 1)
        self.assertIn("no existe", buf.getvalue())
        self.assertIn("harness siguiente", buf.getvalue())

    def test_update_de_carpeta_inexistente(self):
        buf = StringIO()
        c = hc.main(["update", str(self.tmp / "no-existe")], salida=buf)
        self.assertEqual(c, 2)
        self.assertIn("No existe la carpeta", buf.getvalue())
        self.assertIn("harness instalar", buf.getvalue())
        self.assertFalse((self.tmp / "no-existe").exists())


class Siguiente(Base):
    def instalar(self):
        c, out, _ = self.asistente_b([], ["--si"], interactivo=False)
        self.assertEqual(c, 0, out)

    def sig(self, carpeta, *extra):
        buf = StringIO()
        c = hc.main(["siguiente", str(carpeta), *extra], salida=buf)
        return c, buf.getvalue()

    def test_carpeta_inexistente(self):
        c, out = self.sig(self.tmp / "no-existe")
        self.assertEqual(c, 1)
        self.assertIn("no existe", out)

    def test_carpeta_nueva_sugiere_el_asistente_y_no_escribe(self):
        h = arbol_hash(self.vacia)
        c, out = self.sig(self.vacia)
        self.assertEqual(c, 0, out)
        self.assertIn("No es una instancia", out)
        self.assertIn("caso B", out)
        self.assertIn("harness --carpeta", out)
        self.assertEqual(h, arbol_hash(self.vacia))

    def test_instancia_recien_instalada_pide_montar_y_no_escribe(self):
        self.instalar()
        h = arbol_hash(self.inst)
        c, out = self.sig(self.inst)
        self.assertEqual(c, 0, out)
        self.assertIn("Instancia del harness", out)
        self.assertIn("harness montar", out)
        self.assertEqual(h, arbol_hash(self.inst))

    def test_instancia_atrasada_sugiere_update(self):
        self.instalar()
        lock = self.inst / "harness.lock"
        lock.write_text(re.sub(r'version\s*=\s*"[^"]+"', 'version = "0.0.1"', lock.read_text(encoding="utf8")), encoding="utf8")
        _, out = self.sig(self.inst)
        self.assertIn("harness update", out)

    def test_cambio_incompleto_aparece_con_su_siguiente_paso(self):
        self.instalar()
        destino = self.inst / "cambios" / "2026-01-10-ejemplo"
        shutil.copytree(EJEMPLO, destino)
        h = arbol_hash(self.inst)
        _, out = self.sig(self.inst)
        self.assertNotIn("2026-01-10-ejemplo", out)          # el ejemplo completo no estorba
        self.assertIn("Cambios sin errores hasta el cierre: 1", out)
        (destino / "matriz.md").unlink()
        _, out = self.sig(self.inst)
        self.assertIn("2026-01-10-ejemplo", out)
        self.assertIn("puerta de implementacion", out)
        self.assertIn("harness trazar", out)
        self.assertNotEqual(h, arbol_hash(self.inst))        # solo cambió porque el test borró un archivo
        h2 = arbol_hash(self.inst)
        self.sig(self.inst)
        self.assertEqual(h2, arbol_hash(self.inst))

    def test_carpeta_de_un_cambio(self):
        _, out = self.sig(EJEMPLO)
        self.assertIn("harness trazar", out)

    def test_json(self):
        self.instalar()
        c, out = self.sig(self.inst, "--json")
        d = json.loads(out)
        self.assertEqual(c, 0)
        self.assertTrue(d["es_instancia"] and d["pasos"])


class Trazar(Base):
    def correr_trazar(self, *args):
        buf = StringIO()
        c = hc.main(["trazar", *args], salida=buf)
        return c, buf.getvalue()

    def test_ejemplo_completo(self):
        c, out = self.correr_trazar(str(EJEMPLO))
        self.assertEqual(c, 0, out)
        self.assertIn("RESULTADO: OK", out)

    def test_con_errores_sale_1(self):
        cambio = self.tmp / "cambio"
        shutil.copytree(EJEMPLO, cambio)
        (cambio / "matriz.md").unlink()
        c, out = self.correr_trazar(str(cambio))
        self.assertEqual(c, 1)
        self.assertIn("T40", out)
        c, out = self.correr_trazar(str(cambio), "--etapa", "delegacion")
        self.assertEqual(c, 0, out)

    def test_sin_argumento_fuera_de_un_cambio_explica_que_hacer(self):
        with mock.patch.object(hc.os, "getcwd", return_value=str(self.vacia)):
            c, out = self.correr_trazar()
        self.assertEqual(c, 2)
        self.assertIn("falta especificacion.md", out)
        self.assertIn("cambio-ejemplo", out)

    def test_sin_argumento_dentro_de_un_cambio(self):
        with mock.patch.object(hc.os, "getcwd", return_value=str(EJEMPLO)):
            c, out = self.correr_trazar()
        self.assertEqual(c, 0, out)

    def test_carpeta_inexistente(self):
        c, out = self.correr_trazar(str(self.tmp / "nada"))
        self.assertEqual(c, 2)
        self.assertIn("No existe la carpeta del cambio", out)

    def test_json(self):
        c, out = self.correr_trazar(str(EJEMPLO), "--json")
        self.assertEqual(c, 0)
        self.assertTrue(json.loads(out)["ok"])


if __name__ == "__main__":
    unittest.main()
