"""Pruebas del instalador (init, update, adopt, migrar). Todo en directorios temporales."""
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "instalador"))
import harness_instalar as hi  # noqa: E402

SH = RAIZ / "instalador" / "instalar.sh"


def arbol_hash(carpeta):
    h = hashlib.sha256()
    for p in sorted(Path(carpeta).rglob("*")):
        h.update(str(p.relative_to(carpeta)).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def correr(*args):
    r = subprocess.run(["bash", str(SH), *map(str, args)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mh-inst-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.docs = self.tmp / "docs"
        self.docs.mkdir()
        (self.docs / "modelo.md").write_text("# modelo\n", encoding="utf8")
        self.acceso = self.tmp / "acceso.toml"
        self.acceso.write_text(f'[documentacion]\nmetodo = "carpeta_repo"\ncarpeta = "{self.docs}"\n', encoding="utf8")
        self.inst = self.tmp / "inst"


class TestInit(Base):
    def test_plan_no_escribe(self):
        antes = arbol_hash(self.tmp)
        c, out = correr("init", self.inst, "--acceso", self.acceso)
        self.assertEqual(c, 0, out)
        self.assertIn("NO se escribio nada", out)
        self.assertFalse(self.inst.exists())
        self.assertEqual(antes, arbol_hash(self.tmp))

    def test_aplicar_crea_esqueleto(self):
        c, out = correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 0, out)
        for r in ("README.md", "harness.lock", "politicas.toml", "convenciones.toml", "acceso.local.ejemplo.toml",
                  ".gitignore", "conocimiento", "cambios", "documentacion", "mejoras.md", ".harness/estado.json"):
            self.assertTrue((self.inst / r).exists(), r)
        self.assertIn("acceso.local.toml", (self.inst / ".gitignore").read_text())
        self.assertFalse((self.inst / "acceso.local.toml").exists())
        pol = (self.inst / "politicas.toml").read_text()
        self.assertIn("por declarar", pol)
        self.assertNotIn("\n[[datos.ambientes]]", pol)       # no se inventan ambientes
        self.assertIsNone(tomllib.loads(pol).get("datos", {}).get("ambientes"))
        conv = tomllib.loads((self.inst / "convenciones.toml").read_text())
        self.assertIn("ramas.base", conv)
        lock = tomllib.loads((self.inst / "harness.lock").read_text())
        self.assertEqual(lock["version"], (RAIZ / "VERSION").read_text().strip())
        estado = json.loads((self.inst / ".harness/estado.json").read_text())
        self.assertEqual(estado["archivos"]["README.md"]["sha256"],
                         hashlib.sha256((self.inst / "README.md").read_bytes()).hexdigest())
        self.assertEqual(estado["archivos"]["politicas.toml"]["tipo"], "instancia")

    def test_segunda_corrida_identica(self):
        correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        h1 = arbol_hash(self.inst)
        c, out = correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 0, out)
        self.assertEqual(h1, arbol_hash(self.inst))
        self.assertIn("Sin cambios que escribir", out)

    def test_sin_almacen_se_detiene(self):
        vacio = self.tmp / "vacio"
        vacio.mkdir()
        self.acceso.write_text(f'[documentacion]\nmetodo = "carpeta_repo"\ncarpeta = "{vacio}"\n', encoding="utf8")
        c, out = correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 2, out)
        self.assertIn("NO PUEDE ORQUESTAR", out)
        self.assertFalse(self.inst.exists())

    def test_sin_acceso_declarado_se_detiene(self):
        c, out = correr("init", self.inst, "--aplicar")
        self.assertEqual(c, 2, out)
        self.assertIn("documentacion", out)
        self.assertFalse(self.inst.exists())

    def test_existente_ajeno_no_se_pisa(self):
        self.inst.mkdir()
        (self.inst / "README.md").write_text("mio\n")
        c, out = correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 0, out)
        self.assertEqual((self.inst / "README.md").read_text(), "mio\n")
        self.assertIn("[ajeno] README.md", out)


class TestMigrar(Base):
    def test_sin_origen_se_detiene(self):
        c, out = correr("migrar", self.inst, "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 2, out)
        self.assertIn("origen", out)
        self.assertIn("NO PUEDE ORQUESTAR", out)
        self.assertFalse(self.inst.exists())

    def test_con_origen_crea(self):
        orig = self.tmp / "origen"
        orig.mkdir()
        (orig / "esquema.sql").write_text("create table t(id int);\n")
        self.acceso.write_text(self.acceso.read_text() + f'[origen]\nmetodo = "descripcion"\nruta = "{orig}"\n')
        c, out = correr("migrar", self.inst, "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 0, out)
        self.assertEqual(json.loads((self.inst / ".harness/estado.json").read_text())["partida"], "C")
        self.assertTrue((self.inst / "mejoras.md").exists())


def version_mas_nueva():
    """Una versión estrictamente mayor que la real de este harness (la prueba no puede depender de un número escrito a mano)."""
    mayor, menor, parche = (int(x) for x in (RAIZ / "VERSION").read_text().strip().split("."))
    return f"{mayor}.{menor}.{parche + 1}"


class TestUpdate(Base):
    def copia_harness(self, version):
        h = self.tmp / "harness2"
        shutil.copytree(RAIZ, h, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        (h / "VERSION").write_text(version + "\n")
        return h

    def test_update_respeta_modificados_y_preservados(self):
        correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        # la instancia modifica un archivo del harness y sus propios archivos
        (self.inst / "cambios" / "README.md").write_text("editado por la instancia\n")
        (self.inst / "politicas.toml").write_text("# mia\n")
        (self.inst / "convenciones.toml").write_text('"ramas.base" = "develop"\n')
        (self.inst / "mejoras.md").write_text("mis mejoras\n")
        (self.inst / "acceso.local.toml").write_text("[documentacion]\nmetodo = \"carpeta_repo\"\n")
        (self.inst / "conocimiento" / "tema.md").write_text("negocio\n")
        # harness nuevo: cambia la plantilla del README y de dos carpetas
        nueva = version_mas_nueva()
        h = self.copia_harness(nueva)
        base = h / "plantillas" / "instancia"
        (base / "README.md").write_text((base / "README.md").read_text() + f"\nNovedad {nueva}\n")
        (base / "cambios" / "README.md").write_text("nuevo del harness\n")
        antes = {r: (self.inst / r).read_text() for r in
                 ("cambios/README.md", "politicas.toml", "convenciones.toml", "mejoras.md", "acceso.local.toml",
                  "conocimiento/tema.md")}
        c, out = correr("update", self.inst, "--harness", h)
        self.assertEqual(c, 0, out)
        self.assertIn("NO se escribio nada", out)
        self.assertNotIn(f"Novedad {nueva}", (self.inst / "README.md").read_text())
        c, out = correr("update", self.inst, "--harness", h, "--aplicar")
        self.assertEqual(c, 0, out)
        self.assertIn(f"Novedad {nueva}", (self.inst / "README.md").read_text())        # lo propio, actualizado
        self.assertIn("[modificado-local] cambios/README.md", out)                    # lo modificado, reportado
        self.assertIn("nuevo del harness", out)                                        # mostrando que cambiaria
        for r, v in antes.items():
            self.assertEqual((self.inst / r).read_text(), v, r)
        self.assertEqual(tomllib.loads((self.inst / "harness.lock").read_text())["version"], nueva)
        h2 = arbol_hash(self.inst)
        c, out = correr("update", self.inst, "--harness", h, "--aplicar")
        self.assertEqual(h2, arbol_hash(self.inst))                                    # idempotente

    def test_update_no_baja_de_version(self):
        correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        h = self.copia_harness("0.0.1")
        c, out = correr("update", self.inst, "--harness", h, "--aplicar")
        self.assertEqual(c, 2, out)
        self.assertIn("no se baja", out)

    def test_update_sin_instancia(self):
        self.inst.mkdir()
        c, out = correr("update", self.inst)
        self.assertEqual(c, 2, out)


class TestAdopt(Base):
    def sintetico(self):
        p = self.tmp / "proyecto"
        (p / "src").mkdir(parents=True)
        (p / "package.json").write_text(json.dumps({
            "name": "x", "dependencies": {"@nestjs/core": "^10", "typeorm": "^0.3", "mysql2": "^3"},
            "scripts": {"build": "nest build", "test": "jest"}}))
        (p / "src" / "main.ts").write_text("// main\n")
        return p

    def adopt_con_puerta(self, *args, aplicar=True):
        """La puerta de A exige datos y nube reales: se sustituye por un doble que la aprueba."""
        def falso(raiz, partida, modo, pol, acc, deg):
            return 0, json.dumps({"modo": "adopt", "partida": "A", "filas": [], "faltan": [], "degradados": [],
                                  "puede_orquestar": True}), ""
        original = hi.correr_preflight
        hi.correr_preflight = falso
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                c = hi.main(["adopt", *map(str, args)] + (["--aplicar"] if aplicar else []))
        finally:
            hi.correr_preflight = original
        return c, buf.getvalue()

    def test_adopt_no_modifica_proyecto_ajeno(self):
        p = self.sintetico()
        antes = arbol_hash(p)
        c, out = self.adopt_con_puerta(self.inst, "--proyecto", p)
        self.assertEqual(c, 0, out)
        self.assertEqual(antes, arbol_hash(p))
        informe = (self.inst / ".harness" / "informe-adopt.md").read_text()
        self.assertIn("NestJS", informe)
        self.assertIn("Propuesta del instalador", informe)
        self.assertTrue((self.inst / ".harness/propuesta/politicas.propuesta.toml").exists())
        self.assertFalse(any((self.inst).glob("src")))

    def test_adopt_sobre_si_mismo_solo_toca_harness(self):
        p = self.sintetico()
        antes = {str(x.relative_to(p)): x.read_bytes() for x in p.rglob("*") if x.is_file()}
        c, out = self.adopt_con_puerta(p)
        self.assertEqual(c, 0, out)
        despues = {str(x.relative_to(p)): x.read_bytes() for x in p.rglob("*") if x.is_file()
                   and not str(x.relative_to(p)).startswith(".harness")}
        self.assertEqual(antes, despues)

    def test_adopt_idempotente(self):
        p = self.sintetico()
        self.adopt_con_puerta(self.inst, "--proyecto", p)
        h1 = arbol_hash(self.inst)
        self.adopt_con_puerta(self.inst, "--proyecto", p)
        self.assertEqual(h1, arbol_hash(self.inst))

    def test_adopt_instancia_dentro_del_proyecto_se_rechaza(self):
        p = self.sintetico()
        c, out = self.adopt_con_puerta(p / "dentro", "--proyecto", p)
        self.assertEqual(c, 2, out)

    def test_adopt_real_sin_ambientes_se_detiene(self):
        p = self.sintetico()
        c, out = correr("adopt", self.inst, "--proyecto", p)
        self.assertNotEqual(c, 0, out)
        self.assertFalse(self.inst.exists())


class TestCarpetaEnRepo(Base):
    def test_dentro_de_otro_repo_se_rechaza(self):
        repo = self.tmp / "repo"
        (repo / ".git").mkdir(parents=True)
        c, out = correr("init", repo / "sub" / "inst", "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 2, out)
        self.assertIn("otro repositorio", out)
        self.assertFalse((repo / "sub").exists())

    def test_raiz_de_un_repo_propio_es_valida(self):
        (self.inst / ".git").mkdir(parents=True)
        c, out = correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 0, out)

    def test_instancia_declarada_dentro_de_repo_se_acepta(self):
        repo = self.tmp / "repo"
        inst = repo / "inst"
        (repo / ".git").mkdir(parents=True)
        c, out = correr("init", inst, "--acceso", self.acceso, "--aplicar", "--aceptar-dentro-de-repo")
        self.assertEqual(c, 0, out)
        c, out = correr("update", inst, "--aplicar")      # ya declarada por harness.lock
        self.assertEqual(c, 0, out)

    def test_dentro_del_harness_se_rechaza(self):
        c, out = correr("init", RAIZ / "zz-prueba", "--acceso", self.acceso)
        self.assertEqual(c, 2, out)
        self.assertFalse((RAIZ / "zz-prueba").exists())


class TestPiso(Base):
    def test_piso_en_init(self):
        c, out = correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        md = (self.inst / ".harness/piso.md").read_text()
        self.assertIn("instalado", md)
        self.assertIn("requiere confirmacion", md)          # gate.comando por definir
        self.assertIn("El instalador no los ejecuta", out)


class TestLectorIntegrado(Base):
    def setUp(self):
        super().setUp()
        (self.docs / "esquema.sql").write_text(
            "CREATE TABLE cliente (id SERIAL PRIMARY KEY, nombre VARCHAR(80) NOT NULL);\n"
            "CREATE TABLE pedido (id SERIAL PRIMARY KEY, cliente_id INT REFERENCES cliente(id));\n", encoding="utf8")
        (self.docs / "campos.csv").write_text(
            "tabla,campo,tipo,longitud,obligatorio,clave,referencia,descripcion\n"
            "producto,id,int,,si,PK,,identificador\nproducto,nombre,texto,80,si,,,nombre\n", encoding="utf8")

    def test_plan_muestra_lo_entendido_y_no_escribe(self):
        antes = arbol_hash(self.tmp)
        c, out = correr("init", self.inst, "--acceso", self.acceso)
        self.assertEqual(c, 0, out)
        self.assertIn("Entidades:", out)
        self.assertIn("Motor de base propuesto: PostgreSQL", out)
        self.assertIn("Preguntas para quien aporta", out)
        self.assertIn("NO se escribio nada", out)
        self.assertEqual(antes, arbol_hash(self.tmp))

    def test_aplicar_deja_informe_sin_tocar_entradas_e_idempotente(self):
        entradas = arbol_hash(self.docs)
        c, out = correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 0, out)
        for r in (".harness/entendimiento.md", ".harness/entendimiento.json", ".harness/preguntas.md"):
            self.assertTrue((self.inst / r).exists(), r)
        self.assertEqual(entradas, arbol_hash(self.docs))
        md = (self.inst / ".harness/entendimiento.md").read_text()
        self.assertIn("cliente", md)
        self.assertNotIn(str(self.tmp), md)
        self.assertNotIn(str(self.tmp), (self.inst / ".harness/entendimiento.json").read_text())
        self.assertIn("Se intento:", (self.inst / ".harness/preguntas.md").read_text())
        h1 = arbol_hash(self.inst)
        c, out = correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 0, out)
        self.assertEqual(h1, arbol_hash(self.inst))
        self.assertEqual(entradas, arbol_hash(self.docs))

    def test_politica_motor_propuesto_y_sin_ambientes(self):
        correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        txt = (self.inst / "politicas.toml").read_text()
        self.assertIn("propuesto, por confirmar", txt)
        datos = tomllib.loads(txt)
        self.assertIsNone(datos.get("datos", {}).get("ambientes"))
        self.assertNotIn("\n[[datos.ambientes]]", txt)
        self.assertIn("por declarar", txt)

    def test_preguntas_respondidas_no_se_pisan(self):
        correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        (self.inst / ".harness/preguntas.md").write_text("respondidas\n")
        c, out = correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 0, out)
        self.assertEqual((self.inst / ".harness/preguntas.md").read_text(), "respondidas\n")

    def test_almacen_solo_pdf_se_detiene(self):
        solo = self.tmp / "solo-pdf"
        solo.mkdir()
        (solo / "modelo.pdf").write_bytes(b"%PDF-1.4\n")
        self.acceso.write_text(f'[documentacion]\nmetodo = "carpeta_repo"\ncarpeta = "{solo}"\n', encoding="utf8")
        c, out = correr("init", self.inst, "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 2, out)
        self.assertIn("nada legible", out)
        self.assertIn("modelo.pdf", out)
        self.assertIn(".md", out)
        self.assertFalse(self.inst.exists())

    def test_instancia_dentro_de_entradas_se_rechaza(self):
        c, out = correr("init", self.docs / "inst", "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 2, out)
        self.assertIn("carpeta de entradas", out)

    def test_migrar_crea_equivalencia_y_pasos(self):
        orig = self.tmp / "origen"
        orig.mkdir()
        (orig / "esquema.sql").write_text("create table t(id int primary key);\n")
        self.acceso.write_text(self.acceso.read_text() + f'[origen]\nmetodo = "descripcion"\nruta = "{orig}"\n')
        c, out = correr("migrar", self.inst, "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 0, out)
        self.assertTrue((self.inst / ".harness/equivalencia/plantilla-casos.md").exists())
        self.assertTrue((self.inst / ".harness/entendimiento.md").exists())
        self.assertIn("mejoras", (self.inst / "mejoras.md").read_text().lower())
        for k in ("harness-mejoras.py", "harness-equivalencia.py", "Replicar primero"):
            self.assertIn(k, out)
        h1 = arbol_hash(self.inst)
        c, out = correr("migrar", self.inst, "--acceso", self.acceso, "--aplicar")
        self.assertEqual(c, 0, out)
        self.assertEqual(h1, arbol_hash(self.inst))


if __name__ == "__main__":
    unittest.main()
