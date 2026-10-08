"""Pruebas del adaptador de OpenCode (contenido exacto según opencode/FORMATO.md)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun
from comun import arbol_hash

import fuente_neutral as fn
import generar_agentes as ga

BASE_TMP, BASE_INST = comun.crear_instancia_base()
PLUGIN = ".opencode/plugins/guardia-datos.js"
GUARDIA = ".opencode/guardia"


def tearDownModule():
    shutil.rmtree(BASE_TMP, True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mh-oc-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.inst = comun.copiar_instancia(BASE_INST, self.tmp)

    def correr(self, aplicar=False):
        return ga.planificar(self.inst, ["opencode"], ga.SistemaSimulado(), aplicar)["agentes"]["opencode"]


class TestPlugin(Base):
    def test_contenido_del_plugin_sigue_el_formato_documentado(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr(aplicar=True)
        self.assertEqual("disponible", inf["control_por_hook"])
        js = (self.inst / PLUGIN).read_text(encoding="utf8")
        self.assertIn(fn.MARCA, js.splitlines()[0])
        self.assertTrue(js.startswith("// "))
        self.assertIn("export const GuardiaDatos = async ({ directory })", js)
        self.assertIn('"tool.execute.before": async (input, output) =>', js)
        self.assertIn('input.tool !== "bash"', js)
        self.assertIn("output.args.command", js)
        self.assertIn("throw new Error(", js)
        self.assertIn("guardia-datos.py", js)
        self.assertNotIn("permission.asked", js)

    def test_reutiliza_el_generador_de_politicas(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        import importlib.util
        spec = importlib.util.spec_from_file_location("gp", comun.RAIZ / "instalador" / "generar-politicas.py")
        gp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gp)
        with tempfile.TemporaryDirectory() as d:
            gp.generar(str(self.inst / "politicas.toml"), d)
            self.assertEqual((Path(d) / "block-db-access.sh").read_text(encoding="utf8"),
                             (self.inst / GUARDIA / "block-db-access.sh").read_text(encoding="utf8"))
        self.assertTrue((self.inst / GUARDIA / "block-db-access.sh").stat().st_mode & 0o100)
        self.assertIn(fn.MARCA, (self.inst / GUARDIA / "guardia-datos.py").read_text(encoding="utf8"))

    def test_sin_ambientes_el_hook_queda_degradado_y_sin_archivos(self):
        inf = self.correr(aplicar=True)
        self.assertEqual("degradado", inf["control_por_hook"])
        self.assertIn("ningun ambiente", inf["control_por_hook_motivo"])
        self.assertFalse((self.inst / ".opencode" / "plugins").exists())    # sin plugin (R53 agrega skills y comandos bajo .opencode)
        self.assertFalse((self.inst / ".opencode" / "guardia").exists())
        self.assertTrue(any("Sin hook de datos" in a for a in inf["avisos"]))
        self.assertTrue(any("no se generó" in d["que_se_pierde"] for d in inf["degradaciones"]))

    def test_idempotente(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        h = arbol_hash(self.inst)
        self.correr(aplicar=True)
        self.assertEqual(h, arbol_hash(self.inst))

    def test_plan_no_escribe(self):
        comun.habilitar_hooks(self.inst)
        antes = arbol_hash(self.tmp)
        inf = self.correr(aplicar=False)
        self.assertEqual(antes, arbol_hash(self.tmp))
        self.assertIn(PLUGIN, [a["ruta"] for a in inf["archivos"]])

    def test_no_pisa_un_plugin_escrito_a_mano(self):
        comun.habilitar_hooks(self.inst)
        (self.inst / ".opencode" / "plugins").mkdir(parents=True)
        (self.inst / PLUGIN).write_text("// mío\n", encoding="utf8")
        inf = self.correr(aplicar=True)
        self.assertEqual("// mío\n", (self.inst / PLUGIN).read_text(encoding="utf8"))
        self.assertTrue((self.inst / ".opencode" / "plugins" / "guardia-datos.generado.js").exists())
        self.assertTrue(any("existe y fue escrito a mano" in a for a in inf["avisos"]))

    def test_solo_escribe_dentro_de_la_instancia(self):
        comun.habilitar_hooks(self.inst)
        home = self.tmp / "home"
        home.mkdir()
        antes = arbol_hash(home)
        otros = arbol_hash(comun.RAIZ / "adaptadores-agente")
        self.correr(aplicar=True)
        self.assertEqual(antes, arbol_hash(home))
        self.assertEqual(otros, arbol_hash(comun.RAIZ / "adaptadores-agente"))
        escritos = {p.relative_to(self.inst).parts[0] for p in self.inst.rglob("*") if p.is_file()}
        self.assertIn(".opencode", escritos)
        pasos = " ".join(self.correr()["pasos_para_la_persona"])
        self.assertIn("no se escribe", pasos)


class TestCapacidades(Base):
    def test_capacidades_coherentes_con_la_matriz_corregida(self):
        inf = self.correr()
        c = inf["capacidades"]
        self.assertEqual("si", c["Hooks que bloquean"]["estado"])
        self.assertEqual("no_verificado", c["Reglas por ruta"]["estado"])
        self.assertEqual("no_verificado", c["Memoria entre sesiones"]["estado"])
        self.assertTrue(c["Hooks que bloquean"]["generado_por_este_adaptador"])
        self.assertFalse(c["Reglas por ruta"]["generado_por_este_adaptador"])
        self.assertTrue(c["Skills"]["generado_por_este_adaptador"])           # R53: ahora se generan
        texto = (comun.RAIZ / "adaptadores-agente" / "MATRIZ.md").read_text(encoding="utf8")
        self.assertIn("`throw new Error(...)` en `tool.execute.before`", texto)
        self.assertIn("no están documentados", texto)

    def test_degradaciones_coinciden_con_lo_que_dice_la_matriz(self):
        comun.habilitar_hooks(self.inst)
        d = self.correr()["degradaciones"]
        todo = " ".join(x["que_se_pierde"] for x in d)
        for clave in ("`bash`", "dev", "ask", "no es un contrato documentado", "`--auto`", "Reglas por ruta"):
            self.assertIn(clave, todo)
        self.assertTrue(all(x["fuente"] and x["imposicion_alternativa"] for x in d))
        self.assertIn("solo lectura", " ".join(x["imposicion_alternativa"] for x in d))

    def test_controles_degradados_listan_alternativa(self):
        d = self.correr()["degradaciones"]
        self.assertTrue(any("política" in x["imposicion_alternativa"] or "politica" in x["imposicion_alternativa"] for x in d))


@unittest.skipUnless(shutil.which("jq") and shutil.which("git") and shutil.which("bash"), "faltan jq, git o bash")
class TestHookEjecutado(Base):
    """Ejecuta el puente real con la entrada que usa el plugin: {command, cwd}."""

    def preparar(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        repo = self.tmp / "servicio-demo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        return repo

    def puente(self, repo, comando):
        r = subprocess.run([sys.executable, str(self.inst / GUARDIA / "guardia-datos.py"), "--formato", "opencode"],
                           input=json.dumps({"command": comando, "cwd": str(repo)}), capture_output=True, text=True)
        return r.returncode, json.loads(r.stdout)

    def test_deniega_una_accion_de_datos_prohibida_y_permite_una_inocua(self):
        repo = self.preparar()
        rc, v = self.puente(repo, "mysql -h db.externo.example -e 'SELECT 1'")
        self.assertEqual((0, "deny"), (rc, v["decision"]))
        self.assertIn("Bloqueado", v["reason"])
        rc, v = self.puente(repo, "mysql -h localhost -e 'DROP TABLE clientes'")
        self.assertEqual("deny", v["decision"])
        rc, v = self.puente(repo, "ls -la")
        self.assertEqual((0, "allow"), (rc, v["decision"]))

    def test_falla_cerrado_si_no_puede_decidir(self):
        repo = self.preparar()
        (self.inst / GUARDIA / "block-db-access.sh").unlink()
        rc, v = self.puente(repo, "ls")
        self.assertEqual((1, "deny"), (rc, v["decision"]))

    @unittest.skipUnless(shutil.which("node"), "falta node")
    def test_el_plugin_lanza_la_excepcion_con_el_mensaje_de_la_politica(self):
        repo = self.preparar()
        # el plugin vive en la instancia; para el hook, `directory` es el repo vigilado: se copia la guardia allí
        shutil.copytree(self.inst / ".opencode", repo / ".opencode")
        (repo / "plugin.mjs").write_text(
            "import { GuardiaDatos } from './.opencode/plugins/guardia-datos.js'\n"
            "const h = await GuardiaDatos({ directory: process.cwd() })\n"
            "const llamar = async (tool, command) => { try { await h['tool.execute.before']({ tool, sessionID: 's', callID: 'c' }, { args: { command } }); return 'ok' } catch (e) { return 'ERROR:' + e.message } }\n"
            "console.log(JSON.stringify([await llamar('bash', \"mysql -h db.externo.example -e 'SELECT 1'\"), await llamar('bash', 'ls'), await llamar('read', 'x')]))\n",
            encoding="utf8")
        r = subprocess.run(["node", "plugin.mjs"], cwd=repo, capture_output=True, text=True)
        self.assertEqual(0, r.returncode, r.stderr)
        malo, bueno, otra = json.loads(r.stdout)
        self.assertTrue(malo.startswith("ERROR:Bloqueado"), malo)
        self.assertEqual("ok", bueno)
        self.assertEqual("ok", otra)


# ----------------------------------------------------------------------------- R53-R55: skills, comandos, permisos y MCP
POL_DENY = """
[[datos.comandos]]
nombre = "infra destructiva"
regex = "^terraform destroy|^kubectl delete"
accion = "prohibida"
motivo = "destruye infraestructura"

[[datos.comandos]]
nombre = "borrado seguro"
regex = "^shred"
accion = "prohibida"
motivo = "borra datos"
"""
POL_MCP = """
[[mcp.servidores]]
nombre = "docs"
comando = "npx"
args = ["-y", "paquete-docs"]
entorno = { API_X = "${DOCS_VAR}" }
registrar = "permitida"

[[mcp.servidores]]
nombre = "buscador"
url = "https://mcp.example.com/mcp"

[[mcp.servidores]]
nombre = "vetado"
comando = "otro"
registrar = "prohibida"
"""
POL_MCP_CONFIRMAR = """
[[mcp.servidores]]
nombre = "buscador"
url = "https://mcp.example.com/mcp"
"""


def anexar(inst, texto):
    p = Path(inst) / "politicas.toml"
    p.write_text(p.read_text(encoding="utf8") + "\n" + texto, encoding="utf8")


def sin_marca(texto):
    return texto.replace(f"<!-- {fn.MARCA} -->\n", "", 1)


def fuente_de(inst):
    return fn.construir(inst)


class TestCapacidadesOC(Base):
    def aplicar(self):
        return self.correr(aplicar=True)

    def cfg(self):
        return json.loads((self.inst / "opencode.json").read_text(encoding="utf8"))

    def test_skills_y_comandos_en_las_ubicaciones_confirmadas(self):
        self.aplicar()
        for s in fuente_de(self.inst)["skills"]:
            t = (self.inst / ".opencode" / "skills" / s["nombre"] / "SKILL.md").read_text(encoding="utf8")
            self.assertEqual(s["contenido"], sin_marca(t))
            self.assertIn(fn.MARCA, t)
            self.assertRegex(t, r"(?s)\A---\nname: " + s["nombre"] + r"\n.*?\n---\n<!-- ")
        for c in fuente_de(self.inst)["comandos"]:
            t = (self.inst / ".opencode" / "commands" / (c["nombre"] + ".md")).read_text(encoding="utf8")
            self.assertEqual(c["contenido"], sin_marca(t))
            self.assertTrue(t.startswith("---\ndescription: "))

    def test_permission_bash_exacto_ask_primero_deny_al_final(self):
        anexar(self.inst, POL_DENY)
        self.aplicar()
        cfg = self.cfg()
        self.assertEqual("https://opencode.ai/config.json", cfg["$schema"])
        bash = cfg["permission"]["bash"]
        self.assertEqual(["git commit *", "git commit", "git push *", "git push", "terraform destroy *", "terraform destroy",
                          "kubectl delete *", "kubectl delete", "shred *", "shred"], list(bash))
        self.assertEqual({"ask", "deny"}, set(bash.values()))
        self.assertEqual("ask", bash["git push *"])
        self.assertEqual("deny", bash["terraform destroy"])
        for ancho in ("*", "git *", "git", "terraform *", "kubectl *"):
            self.assertNotIn(ancho, bash)
        self.assertNotIn("mcp", cfg)

    def test_no_traducible_va_a_degradaciones_con_su_motivo(self):
        d = " ".join(x["que_se_pierde"] for x in self.aplicar()["degradaciones"])
        for regla in ("migraciones", "CLI del ORM", "push_a_rama_protegida", "secretos.rutas_prohibidas_en_commit"):
            self.assertIn(regla, d)
        self.assertIn("no se traduce a `permission.bash`", d)

    def test_mcp_permitida_con_las_claves_exactas_y_referencias(self):
        anexar(self.inst, POL_MCP)
        self.aplicar()
        self.assertEqual({"docs": {"type": "local", "command": ["npx", "-y", "paquete-docs"], "enabled": True,
                                   "environment": {"API_X": "{env:DOCS_VAR}"}}}, self.cfg()["mcp"])
        self.assertNotIn("mcpServers", self.cfg())

    def test_mcp_remoto_permitido_usa_type_remote_y_url(self):
        anexar(self.inst, POL_MCP_CONFIRMAR.replace('url = "https://mcp.example.com/mcp"', 'url = "https://mcp.example.com/mcp"\nregistrar = "permitida"'))
        self.aplicar()
        self.assertEqual({"buscador": {"type": "remote", "url": "https://mcp.example.com/mcp", "enabled": True}}, self.cfg()["mcp"])

    def test_mcp_confirmar_no_escribe_e_imprime_el_paso(self):
        anexar(self.inst, POL_MCP_CONFIRMAR)
        inf = self.aplicar()
        self.assertNotIn("mcp", self.cfg())
        paso = [p for p in inf["pasos_para_la_persona"] if "buscador" in p]
        self.assertEqual(1, len(paso))
        self.assertIn(json.dumps({"mcp": {"buscador": {"type": "remote", "url": "https://mcp.example.com/mcp", "enabled": True}}}), paso[0])
        self.assertIn("opencode.json", paso[0])

    def test_mcp_prohibida_no_genera_y_avisa(self):
        anexar(self.inst, POL_MCP)
        inf = self.aplicar()
        self.assertNotIn("vetado", json.dumps(self.cfg()))
        self.assertTrue(any("vetado" in a and "prohíbe" in a for a in inf["avisos"]))

    def test_sin_servidores_ni_permisos_no_hay_mcp(self):
        self.aplicar()
        self.assertNotIn("mcp", self.cfg())

    def test_idempotente_y_plan_no_escribe(self):
        anexar(self.inst, POL_DENY + POL_MCP)
        comun.habilitar_hooks(self.inst)
        antes = arbol_hash(self.tmp)
        plan = self.correr(aplicar=False)
        self.assertEqual(antes, arbol_hash(self.tmp))
        self.assertIn("opencode.json", [a["ruta"] for a in plan["archivos"]])
        self.aplicar()
        h = arbol_hash(self.inst)
        inf = self.aplicar()
        self.assertEqual(h, arbol_hash(self.inst))
        self.assertTrue(all(a["accion"] == "igual" for a in inf["archivos"]), [a for a in inf["archivos"] if a["accion"] != "igual"])

    def test_fusiona_opencode_json_manual_sin_perder_lo_manual(self):
        manual = {"$schema": "https://opencode.ai/config.json", "model": "x", "instructions": ["CONTRIBUTING.md"],
                  "permission": {"edit": "deny", "bash": {"*": "ask", "git status *": "allow", "git push": "allow"}},
                  "mcp": {"mio": {"type": "remote", "url": "http://x.example"}}}
        (self.inst / "opencode.json").write_text(json.dumps(manual), encoding="utf8")
        anexar(self.inst, POL_DENY + POL_MCP)
        inf = self.aplicar()
        cfg = self.cfg()
        self.assertEqual("x", cfg["model"])
        self.assertEqual(["CONTRIBUTING.md"], cfg["instructions"])
        self.assertEqual("deny", cfg["permission"]["edit"])
        self.assertEqual("allow", cfg["permission"]["bash"]["git status *"])
        self.assertEqual("allow", cfg["permission"]["bash"]["git push"])            # lo manual gana ante el mismo patrón
        self.assertTrue(any("git push" in a and "a mano" in a for a in inf["avisos"]))
        self.assertEqual("ask", cfg["permission"]["bash"]["git push *"])
        self.assertEqual("deny", cfg["permission"]["bash"]["shred *"])
        self.assertIn("mio", cfg["mcp"])
        self.assertIn("docs", cfg["mcp"])
        self.assertEqual(list(cfg["permission"]["bash"]).index("*"), 0)           # el comodín manual sigue primero: lo del harness va después
        self.aplicar()
        self.assertEqual(cfg, self.cfg())
        # cambia la política: se retira lo propio y queda lo manual
        p = self.inst / "politicas.toml"
        p.write_text(p.read_text(encoding="utf8").replace("^shred", "^shredx").replace('nombre = "docs"', 'nombre = "docs2"'), encoding="utf8")
        self.aplicar()
        cfg = self.cfg()
        self.assertNotIn("shred *", cfg["permission"]["bash"])
        self.assertIn("shredx *", cfg["permission"]["bash"])
        self.assertNotIn("docs", cfg["mcp"])
        self.assertIn("docs2", cfg["mcp"])
        self.assertIn("mio", cfg["mcp"])

    def test_bash_manual_como_texto_se_conserva_como_comodin(self):
        (self.inst / "opencode.json").write_text(json.dumps({"permission": {"bash": "ask"}}), encoding="utf8")
        self.aplicar()
        self.assertEqual("ask", self.cfg()["permission"]["bash"]["*"])
        self.assertEqual("deny" if False else "ask", self.cfg()["permission"]["bash"]["git push *"])

    def test_opencode_json_con_comentarios_o_jsonc_no_se_tocan(self):
        crudo = '{\n  // mío\n  "model": "x"\n}\n'
        (self.inst / "opencode.json").write_text(crudo, encoding="utf8")
        inf = self.aplicar()
        self.assertEqual(crudo, (self.inst / "opencode.json").read_text(encoding="utf8"))
        alt = json.loads((self.inst / "opencode.generado.json").read_text(encoding="utf8"))
        self.assertIn("git push *", alt["permission"]["bash"])
        self.assertTrue(any("opencode.generado.json" in a for a in inf["avisos"]))
        h = arbol_hash(self.inst)
        self.aplicar()
        self.assertEqual(h, arbol_hash(self.inst))
        (self.inst / "opencode.json").unlink()
        (self.inst / "opencode.jsonc").write_text("{ /* mío */ }\n", encoding="utf8")
        self.aplicar()
        self.assertFalse((self.inst / "opencode.json").exists())
        self.assertEqual("{ /* mío */ }\n", (self.inst / "opencode.jsonc").read_text(encoding="utf8"))

    def test_no_pisa_skill_ni_comando_manuales(self):
        d = self.inst / ".opencode" / "skills" / "sdd-planificar"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("manual\n", encoding="utf8")
        (self.inst / ".opencode" / "commands").mkdir(parents=True)
        (self.inst / ".opencode" / "commands" / "harness-estado.md").write_text("mío\n", encoding="utf8")
        inf = self.aplicar()
        self.assertEqual("manual\n", (d / "SKILL.md").read_text(encoding="utf8"))
        self.assertTrue((d / "SKILL.generado.md").exists())
        self.assertEqual("mío\n", (self.inst / ".opencode" / "commands" / "harness-estado.md").read_text(encoding="utf8"))
        self.assertTrue((self.inst / ".opencode" / "commands" / "harness-estado.generado.md").exists())

    def test_solo_dentro_de_la_instancia(self):
        anexar(self.inst, POL_DENY + POL_MCP)
        home = self.tmp / "home"
        home.mkdir()
        antes, otros = arbol_hash(home), arbol_hash(comun.RAIZ / "adaptadores-agente")
        inf = self.aplicar()
        self.assertEqual(antes, arbol_hash(home))
        self.assertEqual(otros, arbol_hash(comun.RAIZ / "adaptadores-agente"))
        self.assertTrue(all(not a["ruta"].startswith(("/", "..", "~")) for a in inf["archivos"]))

    def test_capacidades_y_degradaciones_honestas(self):
        inf = self.correr()
        c = inf["capacidades"]
        for k in ("Skills", "Comandos propios", "MCP", "Permisos / modos / sandbox"):
            self.assertTrue(c[k]["generado_por_este_adaptador"], k)
        self.assertFalse(c["Subagentes / paralelo"]["generado_por_este_adaptador"])
        d = " ".join(x["que_se_pierde"] for x in inf["degradaciones"])
        for clave in ("{env:VAR}", "`allow`", "Subagentes", ".claude/skills"):
            self.assertIn(clave, d)
        self.assertTrue(all(x["fuente"] and x["imposicion_alternativa"] for x in inf["degradaciones"]))


if __name__ == "__main__":
    unittest.main()
