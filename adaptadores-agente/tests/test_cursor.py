"""Pruebas del adaptador de Cursor (contenido exacto según cursor/FORMATO.md)."""
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
HOOKS_JSON = ".cursor/hooks.json"
REGLA = ".cursor/rules/harness.mdc"
HOOKS = ".cursor/hooks"


def tearDownModule():
    shutil.rmtree(BASE_TMP, True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mh-cu-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.inst = comun.copiar_instancia(BASE_INST, self.tmp)

    def correr(self, aplicar=False):
        return ga.planificar(self.inst, ["cursor"], ga.SistemaSimulado(), aplicar)["agentes"]["cursor"]


class TestArchivos(Base):
    def test_hooks_json_exacto(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr(aplicar=True)
        self.assertEqual("disponible", inf["control_por_hook"])
        doc = json.loads((self.inst / HOOKS_JSON).read_text(encoding="utf8"))
        self.assertEqual(fn.MARCA, doc["_generado_por_el_harness"])
        self.assertEqual(1, doc["version"])
        self.assertEqual(["beforeShellExecution"], list(doc["hooks"]))
        h = doc["hooks"]["beforeShellExecution"]
        self.assertEqual([{"command": ".cursor/hooks/guardia-datos.py", "timeout": 30, "failClosed": True}], h)
        self.assertTrue((self.inst / HOOKS / "guardia-datos.py").stat().st_mode & 0o100)

    def test_regla_mdc_minima_con_el_frontmatter_documentado(self):
        self.correr(aplicar=True)
        t = (self.inst / REGLA).read_text(encoding="utf8")
        self.assertTrue(t.startswith("---\nalwaysApply: true\n---\n"))
        self.assertIn(fn.MARCA, t)
        self.assertIn("AGENTS.md", t)
        self.assertLess(len(t.splitlines()), 10)
        self.assertEqual([REGLA], [p.relative_to(self.inst).as_posix() for p in (self.inst / ".cursor" / "rules").iterdir()])

    def test_no_genera_comandos_ni_reglas_md(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        self.assertFalse((self.inst / ".cursor" / "commands").exists())
        self.assertEqual([], list((self.inst / ".cursor" / "rules").glob("*.md")))

    def test_sin_ambientes_hook_degradado_y_sin_archivos_de_hook(self):
        inf = self.correr(aplicar=True)
        self.assertEqual("degradado", inf["control_por_hook"])
        self.assertIn("ningun ambiente", inf["control_por_hook_motivo"])
        self.assertFalse((self.inst / HOOKS_JSON).exists())
        self.assertFalse((self.inst / HOOKS).exists())
        self.assertTrue((self.inst / REGLA).exists())
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
        self.assertIn(HOOKS_JSON, [a["ruta"] for a in inf["archivos"]])

    def test_no_pisa_hooks_json_ni_regla_manuales(self):
        comun.habilitar_hooks(self.inst)
        (self.inst / ".cursor" / "rules").mkdir(parents=True)
        (self.inst / HOOKS_JSON).write_text('{"version": 1, "hooks": {}}\n', encoding="utf8")
        (self.inst / REGLA).write_text("---\nalwaysApply: true\n---\nmía\n", encoding="utf8")
        inf = self.correr(aplicar=True)
        self.assertEqual('{"version": 1, "hooks": {}}\n', (self.inst / HOOKS_JSON).read_text(encoding="utf8"))
        self.assertEqual("---\nalwaysApply: true\n---\nmía\n", (self.inst / REGLA).read_text(encoding="utf8"))
        self.assertTrue((self.inst / ".cursor" / "hooks.generado.json").exists())
        self.assertTrue((self.inst / ".cursor" / "rules" / "harness.generado.mdc").exists())
        self.assertEqual(2, sum("escrito a mano" in a for a in inf["avisos"]))

    def test_solo_escribe_dentro_de_la_instancia(self):
        comun.habilitar_hooks(self.inst)
        otros = arbol_hash(comun.RAIZ / "adaptadores-agente")
        inf = self.correr(aplicar=True)
        self.assertEqual(otros, arbol_hash(comun.RAIZ / "adaptadores-agente"))
        self.assertTrue(all(not a["ruta"].startswith(("/", "..", "~")) for a in inf["archivos"]))
        self.assertIn("no se escribe", " ".join(inf["pasos_para_la_persona"]))


class TestCapacidades(Base):
    def test_capacidades_coherentes_con_la_matriz_corregida(self):
        c = self.correr()["capacidades"]
        self.assertEqual("si", c["Hooks que bloquean"]["estado"])
        self.assertEqual("parcial", c["Comandos propios"]["estado"])
        self.assertIn("no documentado", c["Comandos propios"]["nota"])
        self.assertFalse(c["Comandos propios"]["generado_por_este_adaptador"])
        self.assertTrue(c["Reglas por ruta"]["generado_por_este_adaptador"])
        self.assertEqual("no_verificado", c["Memoria entre sesiones"]["estado"])
        texto = (comun.RAIZ / "adaptadores-agente" / "MATRIZ.md").read_text(encoding="utf8")
        for clave in ("`failClosed: true` bloquea además fallo", "generar sin `type`", "solo `.mdc`", "/docs/rules"):
            self.assertIn(clave.lower(), texto.lower())

    def test_degradaciones_coinciden_con_lo_que_dice_la_matriz(self):
        comun.habilitar_hooks(self.inst)
        d = self.correr()["degradaciones"]
        todo = " ".join(x["que_se_pierde"] for x in d)
        for clave in ("beforeShellExecution", "preToolUse", "subagentStart", "hooks.json", "`.cursor/commands/`", "permissions.json", "globs"):
            self.assertIn(clave, todo)
        self.assertTrue(all(x["fuente"] and x["imposicion_alternativa"] for x in d))


@unittest.skipUnless(shutil.which("jq") and shutil.which("git") and shutil.which("bash"), "faltan jq, git o bash")
class TestHookEjecutado(Base):
    """Ejecuta el script real con la entrada documentada de `beforeShellExecution`."""

    def preparar(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        repo = self.tmp / "servicio-demo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        return repo

    def hook(self, repo, comando):
        entrada = {"command": comando, "cwd": str(repo), "sandbox": False}
        r = subprocess.run([str(self.inst / HOOKS / "guardia-datos.py"), "--formato", "cursor"], input=json.dumps(entrada),
                           capture_output=True, text=True, cwd=str(repo))
        return r.returncode, json.loads(r.stdout)

    def test_el_comando_registrado_en_hooks_json_funciona_tal_cual_desde_la_raiz_del_proyecto(self):
        repo = self.preparar()
        doc = json.loads((self.inst / HOOKS_JSON).read_text(encoding="utf8"))
        comando = doc["hooks"]["beforeShellExecution"][0]["command"]
        for cmd, esperado in (("mysql -h db.externo.example -e 'SELECT 1'", 2), ("ls", 0)):
            r = subprocess.run([comando], input=json.dumps({"command": cmd, "cwd": str(repo)}), capture_output=True, text=True,
                               cwd=str(self.inst))
            self.assertEqual(esperado, r.returncode, r.stdout + r.stderr)

    def test_deniega_con_salida_2_y_permite_con_salida_0(self):
        repo = self.preparar()
        rc, v = self.hook(repo, "mysql -h db.externo.example -e 'SELECT 1'")
        self.assertEqual((2, "deny"), (rc, v["permission"]))
        self.assertIn("Bloqueado", v["user_message"])
        self.assertIn("Bloqueado", v["agent_message"])
        rc, v = self.hook(repo, "mysql -h localhost -e 'DROP TABLE clientes'")
        self.assertEqual((2, "deny"), (rc, v["permission"]))
        rc, v = self.hook(repo, "ls -la")
        self.assertEqual((0, "allow"), (rc, v["permission"]))

    def test_falla_cerrado_si_no_puede_decidir(self):
        repo = self.preparar()
        (self.inst / HOOKS / "block-db-access.sh").unlink()
        rc, v = self.hook(repo, "ls")
        self.assertEqual((2, "deny"), (rc, v["permission"]))

    def test_entrada_invalida_deniega(self):
        repo = self.preparar()
        r = subprocess.run([str(self.inst / HOOKS / "guardia-datos.py"), "--formato", "cursor"], input="no es json",
                           capture_output=True, text=True, cwd=str(repo))
        self.assertEqual(2, r.returncode)
        self.assertEqual("deny", json.loads(r.stdout)["permission"])


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


POL_DENY_UNA_PALABRA = """
[[datos.comandos]]
nombre = "borrado seguro"
regex = "^shred"
accion = "prohibida"
motivo = "borra datos"

[[datos.comandos]]
nombre = "destructiva"
regex = "^terraform destroy"
accion = "prohibida"
motivo = "destruye infraestructura"
"""


class TestCapacidadesCU(Base):
    def aplicar(self):
        return self.correr(aplicar=True)

    def test_skills_en_cursor_skills_con_la_marca_y_el_contenido_neutral(self):
        self.aplicar()
        for s in fuente_de(self.inst)["skills"]:
            t = (self.inst / ".cursor" / "skills" / s["nombre"] / "SKILL.md").read_text(encoding="utf8")
            self.assertEqual(s["contenido"], sin_marca(t))
            self.assertIn(fn.MARCA, t)

    def test_comandos_se_generan_como_skills_con_disable_model_invocation(self):
        self.aplicar()
        self.assertFalse((self.inst / ".cursor" / "commands").exists())
        for c in fuente_de(self.inst)["comandos"]:
            t = (self.inst / ".cursor" / "skills" / c["nombre"] / "SKILL.md").read_text(encoding="utf8")
            self.assertTrue(t.startswith(f"---\nname: {c['nombre']}\ndescription: "), t[:120])
            cab = t.split("---\n")[1]
            self.assertIn("disable-model-invocation: true\n", cab)
            self.assertIn(fn.MARCA, t)
            cuerpo = c["contenido"].split("---\n", 2)[2].strip()
            self.assertIn(cuerpo, t)
            self.assertNotIn("description: " + c["descripcion"] + "\ndescription", t)

    def test_comando_con_el_nombre_de_una_skill_no_se_genera_y_avisa(self):
        d = self.inst / "plantillas-no-usadas"
        d.mkdir()
        f = fuente_de(self.inst)
        f["comandos"] = [{"nombre": "sdd-verificar", "descripcion": "x", "ruta": "r", "contenido": "---\ndescription: x\n---\ncuerpo\n"}]
        import importlib.util
        spec = importlib.util.spec_from_file_location("ad_cu", comun.RAIZ / "adaptadores-agente" / "cursor" / "adaptador.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ad = mod.Cursor()
        ad.generar(f, self.inst, aplicar=True)
        self.assertTrue(any("sdd-verificar" in a and "ya existe una skill" in a for a in ad.avisos))
        self.assertNotIn("cuerpo", (self.inst / ".cursor" / "skills" / "sdd-verificar" / "SKILL.md").read_text(encoding="utf8"))

    def test_permisos_cli_solo_una_palabra_nunca_se_amplia(self):
        anexar(self.inst, POL_DENY_UNA_PALABRA)
        inf = self.aplicar()
        cfg = json.loads((self.inst / ".cursor" / "cli.json").read_text(encoding="utf8"))
        self.assertEqual({"permissions": {"deny": ["Shell(shred)"]}}, cfg)
        self.assertNotIn("Shell(git)", cfg["permissions"]["deny"])
        self.assertNotIn("Shell(terraform)", cfg["permissions"]["deny"])
        d = " ".join(x["que_se_pierde"] for x in inf["degradaciones"])
        self.assertIn("«terraform destroy»", d)
        self.assertIn("`ask` sobre el prefijo «git push»", d)
        self.assertIn("no hay `ask`", d)
        self.assertIn("migraciones", d)                      # lo no traducible del núcleo, con su motivo
        self.assertIn("no es un prefijo literal", d)

    def test_sin_denegaciones_de_una_palabra_no_hay_cli_json(self):
        inf = self.aplicar()
        self.assertFalse((self.inst / ".cursor" / "cli.json").exists())
        self.assertTrue(any("«git push»" in x["que_se_pierde"] for x in inf["degradaciones"]))

    def test_mcp_permitida_con_las_claves_exactas_y_referencias_env(self):
        anexar(self.inst, POL_MCP)
        self.aplicar()
        cfg = json.loads((self.inst / ".cursor" / "mcp.json").read_text(encoding="utf8"))
        self.assertEqual({"mcpServers": {"docs": {"command": "npx", "args": ["-y", "paquete-docs"], "env": {"API_X": "${env:DOCS_VAR}"}}}}, cfg)
        self.assertNotIn("type", cfg["mcpServers"]["docs"])

    def test_mcp_confirmar_no_escribe_e_imprime_el_paso(self):
        anexar(self.inst, POL_MCP_CONFIRMAR)
        inf = self.aplicar()
        self.assertFalse((self.inst / ".cursor" / "mcp.json").exists())
        paso = [p for p in inf["pasos_para_la_persona"] if "buscador" in p]
        self.assertEqual(1, len(paso))
        self.assertIn(json.dumps({"mcpServers": {"buscador": {"url": "https://mcp.example.com/mcp"}}}), paso[0])
        self.assertIn(".cursor/mcp.json", paso[0])

    def test_mcp_prohibida_no_genera_y_avisa(self):
        anexar(self.inst, POL_MCP)
        inf = self.aplicar()
        self.assertNotIn("vetado", (self.inst / ".cursor" / "mcp.json").read_text(encoding="utf8"))
        self.assertTrue(any("vetado" in a and "prohíbe" in a for a in inf["avisos"]))

    def test_sin_servidores_no_hay_mcp_json(self):
        self.aplicar()
        self.assertFalse((self.inst / ".cursor" / "mcp.json").exists())

    def test_idempotente_y_plan_no_escribe(self):
        anexar(self.inst, POL_DENY_UNA_PALABRA + POL_MCP)
        comun.habilitar_hooks(self.inst)
        antes = arbol_hash(self.tmp)
        plan = self.correr(aplicar=False)
        self.assertEqual(antes, arbol_hash(self.tmp))
        self.assertIn(".cursor/cli.json", [a["ruta"] for a in plan["archivos"]])
        self.aplicar()
        h = arbol_hash(self.inst)
        inf = self.aplicar()
        self.assertEqual(h, arbol_hash(self.inst))
        self.assertTrue(all(a["accion"] == "igual" for a in inf["archivos"]), [a for a in inf["archivos"] if a["accion"] != "igual"])

    def test_fusiona_cli_json_y_mcp_json_manuales(self):
        (self.inst / ".cursor").mkdir()
        (self.inst / ".cursor" / "cli.json").write_text(json.dumps({"permissions": {"allow": ["Shell(ls)"], "deny": ["Read(.env*)"]}}), encoding="utf8")
        (self.inst / ".cursor" / "mcp.json").write_text(json.dumps({"mcpServers": {"mio": {"url": "http://x.example"}}}), encoding="utf8")
        anexar(self.inst, POL_DENY_UNA_PALABRA + POL_MCP)
        self.aplicar()
        cli = json.loads((self.inst / ".cursor" / "cli.json").read_text(encoding="utf8"))
        self.assertEqual(["Shell(ls)"], cli["permissions"]["allow"])
        self.assertEqual(["Read(.env*)", "Shell(shred)"], cli["permissions"]["deny"])
        mcp = json.loads((self.inst / ".cursor" / "mcp.json").read_text(encoding="utf8"))
        self.assertEqual({"mio", "docs"}, set(mcp["mcpServers"]))
        self.aplicar()
        self.assertEqual(cli, json.loads((self.inst / ".cursor" / "cli.json").read_text(encoding="utf8")))
        p = self.inst / "politicas.toml"
        p.write_text(p.read_text(encoding="utf8").replace("^shred", "^shredx"), encoding="utf8")
        self.aplicar()
        cli = json.loads((self.inst / ".cursor" / "cli.json").read_text(encoding="utf8"))
        self.assertEqual(["Read(.env*)", "Shell(shredx)"], cli["permissions"]["deny"])

    def test_json_manual_invalido_no_se_toca_y_va_al_alterno(self):
        (self.inst / ".cursor").mkdir()
        (self.inst / ".cursor" / "mcp.json").write_text("{ no es json", encoding="utf8")
        anexar(self.inst, POL_MCP)
        inf = self.aplicar()
        self.assertEqual("{ no es json", (self.inst / ".cursor" / "mcp.json").read_text(encoding="utf8"))
        self.assertIn("docs", json.loads((self.inst / ".cursor" / "mcp.generado.json").read_text(encoding="utf8"))["mcpServers"])
        self.assertTrue(any("mcp.generado.json" in a for a in inf["avisos"]))

    def test_no_pisa_una_skill_manual(self):
        d = self.inst / ".cursor" / "skills" / "harness-gate"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("mía\n", encoding="utf8")
        self.aplicar()
        self.assertEqual("mía\n", (d / "SKILL.md").read_text(encoding="utf8"))
        self.assertTrue((d / "SKILL.generado.md").exists())

    def test_solo_dentro_de_la_instancia(self):
        anexar(self.inst, POL_DENY_UNA_PALABRA + POL_MCP)
        home = self.tmp / "home"
        home.mkdir()
        antes, otros = arbol_hash(home), arbol_hash(comun.RAIZ / "adaptadores-agente")
        inf = self.aplicar()
        self.assertEqual(antes, arbol_hash(home))
        self.assertEqual(otros, arbol_hash(comun.RAIZ / "adaptadores-agente"))
        self.assertTrue(all(not a["ruta"].startswith(("/", "..", "~")) for a in inf["archivos"]))

    def test_capacidades_honestas(self):
        inf = self.correr()
        c = inf["capacidades"]
        for k in ("Skills", "MCP", "Permisos / modos / sandbox"):
            self.assertTrue(c[k]["generado_por_este_adaptador"], k)
        self.assertFalse(c["Comandos propios"]["generado_por_este_adaptador"])
        self.assertIn("disable-model-invocation: true", c["Comandos propios"]["nota"])
        self.assertFalse(c["Subagentes / paralelo"]["generado_por_este_adaptador"])
        d = " ".join(x["que_se_pierde"] for x in inf["degradaciones"])
        for clave in ("`type`", ".claude/skills", "no es un comando nativo"):
            self.assertIn(clave, d)
        self.assertTrue(all(x["fuente"] and x["imposicion_alternativa"] for x in inf["degradaciones"]))


if __name__ == "__main__":
    unittest.main()
