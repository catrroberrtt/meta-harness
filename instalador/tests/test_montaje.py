import os
"""Pruebas de instalador/montaje.py. Instancias sintéticas creadas con `instalar.sh init … --aplicar` en carpetas temporales.
Agentes detectados simulados; sin red, sin git, sin clientes de base de datos."""
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "instalador"))
import montaje as mo  # noqa: E402
import generar_agentes as ga  # noqa: E402

POLITICA_CON_AMBIENTE = """
[[datos.ambientes]]
nombre = "local"
tipo = "local"
[datos.ambientes.reconocimiento]
hosts = ["localhost"]
puertos = [5432]
[datos.ambientes.permisos]
lectura = "permitida"
escritura = "prohibida"
ddl = "prohibida"
migraciones = "prohibida"
"""
MCP_CONFIRMAR = '\n[[mcp.servidores]]\nnombre = "buscador"\nurl = "https://mcp.example.com/mcp"\n'
NADA = ga.SistemaSimulado()
CLAUDE = ga.SistemaSimulado(comandos=["claude"])


def arbol_hash(carpeta):
    h = hashlib.sha256()
    for p in sorted(Path(carpeta).rglob("*")):
        h.update(str(p.relative_to(carpeta)).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def crear_base():
    tmp = Path(tempfile.mkdtemp(prefix="mh-mont-base-"))
    docs = tmp / "docs"
    docs.mkdir()
    (docs / "modelo.md").write_text("# modelo\n", encoding="utf8")
    acc = tmp / "acceso.toml"
    acc.write_text(f'[documentacion]\nmetodo = "carpeta_repo"\ncarpeta = "{docs}"\n', encoding="utf8")
    inst = tmp / "inst"
    r = subprocess.run(["bash", str(RAIZ / "instalador" / "instalar.sh"), "init", str(inst), "--acceso", str(acc), "--aplicar"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    return tmp, inst


BASE_TMP, BASE_INST = crear_base()


def tearDownModule():
    shutil.rmtree(BASE_TMP, True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mh-mont-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.inst = self.tmp / "inst"
        shutil.copytree(BASE_INST, self.inst)
        self.out = []

    def con_ambiente(self):
        p = self.inst / "politicas.toml"
        t = p.read_text(encoding="utf8")
        t = t.replace("repos = []                     # patrones", 'repos = ["servicio-*"]         # patrones', 1)
        t = t.replace("hosts_locales = []", 'hosts_locales = ["localhost"]', 1)
        p.write_text(t + POLITICA_CON_AMBIENTE, encoding="utf8")

    def anexar(self, texto):
        p = self.inst / "politicas.toml"
        p.write_text(p.read_text(encoding="utf8") + "\n" + texto, encoding="utf8")

    def montar(self, agentes=None, aplicar=False, sistema=NADA, **kw):
        kw.setdefault("si", True)
        return mo.montar(self.inst, agentes, aplicar, preguntar=lambda _t: "", salida=self.out.append, sistema=sistema, **kw)

    def informe(self):
        return (self.inst / ".harness" / "montaje.md").read_text(encoding="utf8")

    def archivos(self, res):
        return {f["ruta"] for f in res["plan"]}


class TestPlan(Base):
    def test_plan_no_escribe_nada(self):
        antes = arbol_hash(self.tmp)
        res = self.montar(["claude-code"], aplicar=False)
        self.assertEqual(antes, arbol_hash(self.tmp))
        self.assertFalse(res["aplicado"])
        self.assertIn("AGENTS.md", self.archivos(res) | {r["ruta"] for r in res["plan"]})
        self.assertTrue(any("no se escribió nada" in x for x in self.out))

    def test_aplicar_genera_agents_y_lo_del_agente_solo_dentro(self):
        vecinos = {p.name for p in self.tmp.iterdir()}
        res = self.montar(["claude-code"], aplicar=True)
        self.assertTrue(res["aplicado"] and res["ok"])
        self.assertTrue((self.inst / "AGENTS.md").is_file())
        self.assertTrue((self.inst / "CLAUDE.md").is_file())
        self.assertTrue((self.inst / ".harness" / "montaje.md").is_file())
        self.assertEqual(vecinos, {p.name for p in self.tmp.iterdir()})
        estado = json.loads((self.inst / ".harness" / "estado.json").read_text(encoding="utf8"))
        self.assertEqual(["claude-code"], estado["montaje"]["agentes"])

    def test_idempotente_arbol_identico(self):
        self.montar(["claude-code"], aplicar=True)
        h = arbol_hash(self.inst)
        res = self.montar(["claude-code"], aplicar=True)
        self.assertEqual(h, arbol_hash(self.inst))
        self.assertTrue(res["verificacion"]["idempotente"])

    def test_confirmacion_negada_no_escribe(self):
        antes = arbol_hash(self.inst)
        res = mo.montar(self.inst, ["claude-code"], True, preguntar=lambda _t: "n", salida=self.out.append, sistema=NADA)
        self.assertEqual(antes, arbol_hash(self.inst))
        self.assertFalse(res["aplicado"])


class TestAgentes(Base):
    def test_detectado_se_configura_y_no_detectado_no(self):
        res = self.montar(None, aplicar=True, sistema=CLAUDE)
        self.assertEqual(["claude-code"], res["agentes_configurados"])
        self.assertTrue((self.inst / "CLAUDE.md").exists())
        self.assertFalse((self.inst / ".cursor").exists())
        self.assertFalse((self.inst / "opencode.json").exists())

    def test_ninguno_detectado_solo_agents_md_y_pendiente(self):
        res = self.montar(None, aplicar=True)
        self.assertEqual([], res["agentes_configurados"])
        self.assertTrue((self.inst / "AGENTS.md").exists())
        self.assertFalse((self.inst / "CLAUDE.md").exists())
        self.assertTrue(any("Agentes de IA" in d["que"] for d in res["degradado"]))
        self.assertTrue(any("Configurar un agente" in p["que"] for p in res["pendiente"]))

    def test_elegido_pero_ausente_se_genera_y_se_avisa(self):
        res = self.montar(["claude-code"], aplicar=True, sistema=NADA)
        self.assertTrue((self.inst / "CLAUDE.md").exists())
        self.assertTrue(any("no se detectó" in d["motivo"] for d in res["degradado"]))

    def test_pregunta_de_agentes_respeta_la_eleccion(self):
        respuestas = iter(["ninguno", "s"])
        res = mo.montar(self.inst, None, True, preguntar=lambda _t: next(respuestas), salida=self.out.append, sistema=CLAUDE)
        self.assertEqual([], res["agentes_configurados"])
        self.assertFalse((self.inst / "CLAUDE.md").exists())

    def test_agente_desconocido(self):
        with self.assertRaises(mo.ErrorMontaje):
            self.montar(["no-existe"], aplicar=True)


class TestHooksYMcp(Base):
    def test_sin_ambientes_hooks_degradados_y_no_inventa(self):
        res = self.montar(["claude-code"], aplicar=True)
        self.assertFalse((self.inst / ".claude" / "hooks" / "block-db-access.sh").exists())
        self.assertTrue(any("control por hook" in d["que"] for d in res["degradado"]))
        self.assertTrue(any("Ambientes de datos" in d["que"] for d in res["degradado"]))
        self.assertTrue(any("ambientes" in p["que"].lower() and p["tipo"] == mo.PASO for p in res["pendiente"]))
        self.assertNotIn("[[datos.ambientes]]\nnombre", (self.inst / "politicas.toml").read_text(encoding="utf8"))

    def test_con_ambientes_hooks_generados(self):
        self.con_ambiente()
        res = self.montar(["claude-code"], aplicar=True)
        self.assertTrue((self.inst / ".claude" / "hooks" / "block-db-access.sh").exists())
        self.assertFalse(any("control por hook" in d["que"] for d in res["degradado"]))
        self.assertTrue(any("Ambientes de datos declarados" in h for h in res["hecho"]))

    def test_mcp_confirmar_no_se_escribe_y_es_paso_impreso(self):
        self.anexar(MCP_CONFIRMAR)
        res = self.montar(["claude-code"], aplicar=True)
        self.assertFalse((self.inst / ".mcp.json").exists())
        self.assertTrue(any("buscador" in p["comando"] and ".mcp.json" in p["comando"] for p in res["pendiente"]))


class TestGarantiaYVerificacion(Base):
    def test_gate_por_definir_se_informa(self):
        res = self.montar(["claude-code"], aplicar=True)
        self.assertTrue(any(d["que"] == "Gate de calidad" for d in res["degradado"]))
        self.assertIn("por definir", self.informe())

    def test_gate_declarado_se_informa_como_hecho(self):
        p = self.inst / "convenciones.toml"
        t = p.read_text(encoding="utf8")
        t = t.replace('"gate.comando" = "por definir"', '"gate.comando" = "make verificar"')
        self.assertIn("make verificar", t)
        p.write_text(t, encoding="utf8")
        res = self.montar(["claude-code"], aplicar=True)
        self.assertTrue(any("make verificar" in h for h in res["hecho"]))
        self.assertFalse(any(d["que"] == "Gate de calidad" for d in res["degradado"]))

    def test_lo_que_falta_es_paso_para_la_persona_y_no_se_crea(self):
        proyecto = self.tmp / "proyecto"
        proyecto.mkdir()
        res = self.montar(["claude-code"], aplicar=True, proyecto=proyecto)
        textos = " ".join(p["que"] for p in res["pendiente"])
        for clave in ("Hooks de git", "Integración continua", "Protección de ramas", "Rol de solo lectura"):
            self.assertIn(clave, textos)
        self.assertEqual([], list(proyecto.iterdir()))

    def test_ci_y_hooks_presentes_se_reconocen_sin_tocarlos(self):
        proyecto = self.tmp / "proyecto"
        (proyecto / ".github" / "workflows").mkdir(parents=True)
        (proyecto / ".github" / "workflows" / "ci.yml").write_text("run: make verificar\n", encoding="utf8")
        (proyecto / ".githooks").mkdir()
        (proyecto / ".githooks" / "pre-push").write_text("#!/bin/sh\n", encoding="utf8")
        antes = arbol_hash(proyecto)
        res = self.montar(["claude-code"], aplicar=True, proyecto=proyecto)
        self.assertEqual(antes, arbol_hash(proyecto))
        self.assertTrue(any("Hooks de git presentes" in h for h in res["hecho"]))
        self.assertTrue(any("Integración continua presente" in h for h in res["hecho"]))

    def test_rol_de_solo_lectura_declarado(self):
        p = self.inst / "politicas.toml"
        t = p.read_text(encoding="utf8")
        t = t.replace("hosts_locales = []", 'hosts_locales = []\nrol_solo_lectura = "lector"', 1)
        p.write_text(t, encoding="utf8")
        res = self.montar(["claude-code"], aplicar=True)
        self.assertTrue(any("Rol de solo lectura" in h for h in res["hecho"]))
        self.assertFalse(any("Rol de solo lectura" in x["que"] for x in res["pendiente"]))

    def test_informe_sin_fechas_rutas_ni_empresas(self):
        self.con_ambiente()
        self.anexar(MCP_CONFIRMAR)
        self.montar(["claude-code"], aplicar=True, proyecto=self.tmp)
        t = self.informe()
        self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}", t))
        self.assertIsNone(re.search(r"/(home|tmp|Users|var)/", t))
        self.assertNotIn(str(self.tmp), t)
        # Los nombres de empresa o proyecto salen de un archivo LOCAL (HARNESS_PROHIBIDOS, uno por linea) que no vive en el repositorio.
        ruta = os.environ.get("HARNESS_PROHIBIDOS")
        if ruta and os.path.isfile(ruta):
            for palabra in (l.strip().lower() for l in open(ruta, encoding="utf8") if l.strip() and not l.startswith("#")):
                self.assertNotIn(palabra, t.lower())
        for seccion in ("## Hecho", "## Degradado y por qué", "## Pendiente de la persona"):
            self.assertIn(seccion, t)


class TestAccesoDatos(Base):
    def test_bloque_siempre_en_salida_informe_y_pendiente(self):
        for aplicar in (False, True):
            self.out.clear()
            res = self.montar(["claude-code"], aplicar=aplicar)
            salida = "\n".join(self.out)
            self.assertIn("Acceso a datos (lo das tú)", salida)
            self.assertIn("modo degradado", salida)
            self.assertIn("acceso.local.toml", salida)
            self.assertIn("preflight-accesos.py", salida)
            req = [p for p in res["pendiente"] if p["tipo"] == mo.REQUISITO]
            self.assertEqual(1, len(req))
            self.assertTrue(res["ok"])
        t = self.informe()
        self.assertIn("## Acceso a datos (lo das tú)", t)
        self.assertIn("NO la instala", t)
        self.assertIn("sin comprobar", t)

    def test_bloque_aparece_tambien_cuando_todo_sale_bien(self):
        self.con_ambiente()
        (self.inst / "acceso.local.toml").write_text('[datos.local]\nmetodo = "directo"\nhost = "localhost"\nport = 1\n', encoding="utf8")
        res = self.montar(["claude-code"], aplicar=True)
        self.assertEqual("declarado", res["acceso_datos"]["estado"])
        self.assertIn("método declarado: directo", self.informe())
        self.assertIn("## Acceso a datos (lo das tú)", self.informe())

    def test_sin_acceso_local_queda_sin_comprobar(self):
        self.con_ambiente()
        res = self.montar(["claude-code"], aplicar=False)
        self.assertEqual("sin comprobar", res["acceso_datos"]["estado"])

    def test_ningun_paso_invoca_clientes_de_base_ni_red(self):
        import unittest.mock as m
        llamadas = []
        with m.patch("subprocess.run", side_effect=lambda *a, **k: llamadas.append(a) or (_ for _ in ()).throw(AssertionError("subprocess"))), \
                m.patch("socket.create_connection", side_effect=AssertionError("red")):
            self.con_ambiente()
            self.montar(["claude-code"], aplicar=True)
        self.assertEqual([], llamadas)
        fuente = (RAIZ / "instalador" / "montaje.py").read_text(encoding="utf8")
        for prohibido in ("subprocess", "socket", "docker", "psql", "mysql", "ssh"):
            self.assertNotIn(prohibido + "(", fuente)
            self.assertNotIn(f'"{prohibido}"', fuente)


class TestCli(Base):
    def correr(self, *args):
        out, err = io.StringIO(), io.StringIO()
        import contextlib
        with contextlib.redirect_stderr(err):
            c = mo.main([str(a) for a in args], sistema=NADA, preguntar=lambda _t: "", salida=out)
        return c, out.getvalue(), err.getvalue()

    def test_sin_instancia_valida_exit_2_con_mensaje(self):
        vacia = self.tmp / "vacia"
        vacia.mkdir()
        for destino in (vacia, self.tmp / "no-existe"):
            c, _o, e = self.correr(destino)
            self.assertEqual(2, c)
            self.assertIn("instalar.sh init", e)

    def test_json_y_si(self):
        c, o, _e = self.correr(self.inst, "--agentes", "claude-code", "--aplicar", "--si", "--json")
        self.assertEqual(0, c)
        d = json.loads(o)
        for k in ("hecho", "degradado", "pendiente"):
            self.assertIn(k, d)

    def test_agente_desconocido_exit_2(self):
        c, _o, e = self.correr(self.inst, "--agentes", "zzz")
        self.assertEqual(2, c)
        self.assertIn("zzz", e)


if __name__ == "__main__":
    unittest.main()
