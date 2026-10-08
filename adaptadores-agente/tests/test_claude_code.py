"""Pruebas del adaptador de Claude Code."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun
from comun import arbol_hash

import fuente_neutral as fn
import generar_agentes as ga

BASE_TMP, BASE_INST = comun.crear_instancia_base()


def tearDownModule():
    shutil.rmtree(BASE_TMP, True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mh-cc-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.inst = comun.copiar_instancia(BASE_INST, self.tmp)

    def correr(self, aplicar=False, agentes=("claude-code",)):
        return ga.planificar(self.inst, list(agentes), ga.SistemaSimulado(), aplicar)


class TestClaudeMd(Base):
    def test_claude_md_minimo_importa_agents_md(self):
        self.correr(aplicar=True)
        t = (self.inst / "CLAUDE.md").read_text(encoding="utf8")
        self.assertIn(fn.MARCA, t)
        self.assertIn("@AGENTS.md", t)
        self.assertLess(len(t.splitlines()), 5)

    def test_no_pisa_claude_md_manual(self):
        (self.inst / "CLAUDE.md").write_text("# mío\n", encoding="utf8")
        inf = self.correr(aplicar=True)
        self.assertEqual("# mío\n", (self.inst / "CLAUDE.md").read_text(encoding="utf8"))
        self.assertTrue((self.inst / "CLAUDE.generado.md").exists())
        self.assertTrue(any("CLAUDE.md existe" in a for a in inf["agentes"]["claude-code"]["avisos"]))

    def test_si_agents_md_es_manual_claude_md_apunta_al_generado(self):
        (self.inst / "AGENTS.md").write_text("# manual\n", encoding="utf8")
        self.correr(aplicar=True)
        self.assertIn("@AGENTS.generado.md", (self.inst / "CLAUDE.md").read_text(encoding="utf8"))

    def test_plan_no_escribe(self):
        antes = arbol_hash(self.tmp)
        inf = self.correr(aplicar=False)
        self.assertEqual(antes, arbol_hash(self.tmp))
        self.assertIn("CLAUDE.md", [a["ruta"] for a in inf["agentes"]["claude-code"]["archivos"]])

    def test_idempotente(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        h = arbol_hash(self.inst)
        self.correr(aplicar=True)
        self.assertEqual(h, arbol_hash(self.inst))


class TestHooks(Base):
    def test_sin_ambientes_en_la_politica_degrada_y_lo_dice(self):
        inf = self.correr(aplicar=True)["agentes"]["claude-code"]
        self.assertEqual("degradado", inf["control_por_hook"])
        self.assertIn("ningun ambiente", inf["control_por_hook_motivo"])
        self.assertFalse((self.inst / ".claude" / "hooks").exists())      # sin hook de datos (R53 agrega skills y permisos bajo .claude)
        self.assertTrue(any("Sin hook de datos" in a for a in inf["avisos"]))
        self.assertTrue(any("no se generó" in d["que_se_pierde"] for d in inf["degradaciones"]))

    def test_con_politica_valida_genera_hooks_reutilizando_el_generador(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr(aplicar=True)["agentes"]["claude-code"]
        self.assertEqual("disponible", inf["control_por_hook"])
        hook = self.inst / ".claude" / "hooks" / "block-db-access.sh"
        self.assertTrue(hook.exists())
        self.assertTrue(hook.stat().st_mode & 0o100)
        self.assertTrue((self.inst / ".claude" / "hooks" / "filtrar-tramos-de-lectura.py").exists())
        # idéntico a lo que produce directamente instalador/generar-politicas.py
        import importlib.util
        spec = importlib.util.spec_from_file_location("gp", comun.RAIZ / "instalador" / "generar-politicas.py")
        gp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gp)
        with tempfile.TemporaryDirectory() as d:
            gp.generar(str(self.inst / "politicas.toml"), d)
            self.assertEqual((Path(d) / "block-db-access.sh").read_text(encoding="utf8"), hook.read_text(encoding="utf8"))

    def test_ejemplo_de_settings_es_json_con_bloque_hooks_y_no_instala(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        ej = json.loads((self.inst / ".claude" / "settings.ejemplo.json").read_text(encoding="utf8"))
        pre = ej["hooks"]["PreToolUse"][0]
        self.assertEqual("Bash", pre["matcher"])
        self.assertEqual("command", pre["hooks"][0]["type"])
        self.assertTrue(pre["hooks"][0]["command"].endswith("block-db-access.sh"))
        # no registra hooks: settings.json (si existe, por los permisos) no lleva la clave `hooks`
        cfg = self.inst / ".claude" / "settings.json"
        self.assertTrue(not cfg.exists() or "hooks" not in json.loads(cfg.read_text(encoding="utf8")))

    def test_pasos_para_la_persona_cubren_lo_global_y_el_registro(self):
        comun.habilitar_hooks(self.inst)
        pasos = " ".join(self.correr()["agentes"]["claude-code"]["pasos_para_la_persona"])
        self.assertIn("settings.json", pasos)
        self.assertIn("no se escribe", pasos)

    def test_degradaciones_de_claude_code_existen_aun_con_hooks(self):
        comun.habilitar_hooks(self.inst)
        d = self.correr()["agentes"]["claude-code"]["degradaciones"]
        self.assertTrue(d)
        self.assertTrue(all(x["fuente"] and x["imposicion_alternativa"] for x in d))

    def test_hook_manual_existente_no_se_pisa(self):
        comun.habilitar_hooks(self.inst)
        h = self.inst / ".claude" / "hooks"
        h.mkdir(parents=True)
        (h / "block-db-access.sh").write_text("#!/bin/sh\n# mío\n", encoding="utf8")
        self.correr(aplicar=True)
        self.assertEqual("#!/bin/sh\n# mío\n", (h / "block-db-access.sh").read_text(encoding="utf8"))
        self.assertTrue((h / "block-db-access.generado.sh").exists())


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


class TestCapacidadesCC(Base):
    def aplicar(self):
        return self.correr(aplicar=True)["agentes"]["claude-code"]

    def test_skills_en_la_ubicacion_confirmada_con_la_marca_y_el_contenido_neutral(self):
        self.aplicar()
        for s in fuente_de(self.inst)["skills"]:
            t = (self.inst / ".claude" / "skills" / s["nombre"] / "SKILL.md").read_text(encoding="utf8")
            self.assertTrue(t.startswith("---\nname: " + s["nombre"] + "\n"))
            self.assertIn(fn.MARCA, t)
            self.assertEqual(s["contenido"], sin_marca(t))
            self.assertTrue(fn.es_generado(t) or fn.MARCA.lower() in t.lower())
        self.assertEqual(4, len(list((self.inst / ".claude" / "skills").glob("*/SKILL.md"))))

    def test_comandos_en_claude_commands(self):
        self.aplicar()
        for c in fuente_de(self.inst)["comandos"]:
            t = (self.inst / ".claude" / "commands" / (c["nombre"] + ".md")).read_text(encoding="utf8")
            self.assertEqual(c["contenido"], sin_marca(t))
            self.assertIn(fn.MARCA, t)

    def test_permisos_solo_prefijos_literales_y_nunca_mas_amplios(self):
        anexar(self.inst, POL_DENY)
        inf = self.aplicar()
        cfg = json.loads((self.inst / ".claude" / "settings.json").read_text(encoding="utf8"))
        self.assertEqual(["Bash(git commit *)", "Bash(git commit)", "Bash(git push *)", "Bash(git push)"], cfg["permissions"]["ask"])
        self.assertEqual(["Bash(terraform destroy *)", "Bash(terraform destroy)", "Bash(kubectl delete *)", "Bash(kubectl delete)",
                          "Bash(shred *)", "Bash(shred)"], cfg["permissions"]["deny"])
        todas = cfg["permissions"]["deny"] + cfg["permissions"]["ask"]
        for ancho in ("Bash(git *)", "Bash(git)", "Bash(terraform *)", "Bash(kubectl *)", "Bash(*)", "Bash"):
            self.assertNotIn(ancho, todas)
        self.assertNotIn("allow", cfg["permissions"])
        self.assertNotIn("hooks", cfg)
        deg = " ".join(d["que_se_pierde"] for d in inf["degradaciones"])
        for regla in ("migraciones", "semillas", "CLI del ORM", "comandos.instalar", "push_a_rama_protegida"):
            self.assertIn(regla, deg)
        self.assertIn("no es un prefijo literal", deg)

    def test_mcp_permitida_se_escribe_con_referencias_y_nunca_valores(self):
        anexar(self.inst, POL_MCP)
        os.environ["DOCS_VAR"] = "valor-secreto-que-no-debe-aparecer"
        self.addCleanup(os.environ.pop, "DOCS_VAR", None)
        inf = self.aplicar()
        texto = (self.inst / ".mcp.json").read_text(encoding="utf8")
        self.assertNotIn("valor-secreto", texto)
        cfg = json.loads(texto)
        self.assertEqual({"docs": {"type": "stdio", "command": "npx", "args": ["-y", "paquete-docs"], "env": {"API_X": "${DOCS_VAR}"}}}, cfg["mcpServers"])

    def test_mcp_confirmar_no_escribe_e_imprime_el_paso_exacto(self):
        anexar(self.inst, POL_MCP_CONFIRMAR)
        inf = self.aplicar()
        self.assertFalse((self.inst / ".mcp.json").exists())
        paso = [p for p in inf["pasos_para_la_persona"] if "buscador" in p]
        self.assertEqual(1, len(paso))
        self.assertIn(".mcp.json", paso[0])
        self.assertIn(json.dumps({"mcpServers": {"buscador": {"type": "http", "url": "https://mcp.example.com/mcp"}}}), paso[0])
        self.assertIn("NO se escribió", paso[0])

    def test_mcp_prohibida_no_genera_nada_y_avisa(self):
        anexar(self.inst, POL_MCP)
        inf = self.aplicar()
        self.assertNotIn("vetado", (self.inst / ".mcp.json").read_text(encoding="utf8"))
        self.assertTrue(any("vetado" in a and "prohíbe" in a for a in inf["avisos"]))
        self.assertFalse(any("«vetado»" in p and "agrega esto" in p for p in inf["pasos_para_la_persona"]))

    def test_sin_servidores_no_hay_mcp_json(self):
        inf = self.aplicar()
        self.assertFalse((self.inst / ".mcp.json").exists())
        self.assertFalse(any("MCP" in p and "NO se escribió" in p for p in inf["pasos_para_la_persona"]))

    def test_idempotente_con_permisos_y_mcp(self):
        anexar(self.inst, POL_DENY + POL_MCP)
        comun.habilitar_hooks(self.inst)
        self.aplicar()
        h = arbol_hash(self.inst)
        inf = self.aplicar()
        self.assertEqual(h, arbol_hash(self.inst))
        self.assertTrue(all(a["accion"] == "igual" for a in inf["archivos"]), [a for a in inf["archivos"] if a["accion"] != "igual"])

    def test_plan_no_escribe(self):
        anexar(self.inst, POL_DENY + POL_MCP)
        antes = arbol_hash(self.tmp)
        inf = self.correr(aplicar=False)["agentes"]["claude-code"]
        self.assertEqual(antes, arbol_hash(self.tmp))
        rutas = [a["ruta"] for a in inf["archivos"]]
        for r in (".claude/settings.json", ".mcp.json", ".claude/skills/sdd-verificar/SKILL.md", ".claude/commands/harness-gate.md"):
            self.assertIn(r, rutas)

    def test_no_pisa_skill_ni_comando_manuales(self):
        d = self.inst / ".claude" / "skills" / "sdd-verificar"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: sdd-verificar\ndescription: mía\n---\nmanual\n", encoding="utf8")
        (self.inst / ".claude" / "commands").mkdir(parents=True)
        (self.inst / ".claude" / "commands" / "harness-gate.md").write_text("mío\n", encoding="utf8")
        inf = self.aplicar()
        self.assertIn("manual", (d / "SKILL.md").read_text(encoding="utf8"))
        self.assertTrue((d / "SKILL.generado.md").exists())
        self.assertEqual("mío\n", (self.inst / ".claude" / "commands" / "harness-gate.md").read_text(encoding="utf8"))
        self.assertTrue((self.inst / ".claude" / "commands" / "harness-gate.generado.md").exists())
        self.assertEqual(2, sum("escrito a mano" in a for a in inf["avisos"]))

    def test_fusiona_settings_manual_sin_perder_ni_duplicar_y_retira_lo_que_ya_no_aplica(self):
        cfg_ruta = self.inst / ".claude" / "settings.json"
        cfg_ruta.parent.mkdir(parents=True)
        manual = {"model": "x", "permissions": {"deny": ["Bash(rm *)", "Bash(git push)"], "allow": ["Read"]}, "env": {"A": "1"}}
        cfg_ruta.write_text(json.dumps(manual), encoding="utf8")
        anexar(self.inst, POL_DENY)
        self.aplicar()
        cfg = json.loads(cfg_ruta.read_text(encoding="utf8"))
        self.assertEqual("x", cfg["model"])
        self.assertEqual({"A": "1"}, cfg["env"])
        self.assertEqual(["Read"], cfg["permissions"]["allow"])
        self.assertEqual(1, cfg["permissions"]["ask"].count("Bash(git push *)"))
        self.assertEqual(1, cfg["permissions"]["deny"].count("Bash(rm *)"))
        self.assertIn("Bash(shred *)", cfg["permissions"]["deny"])
        self.aplicar()
        self.assertEqual(cfg, json.loads(cfg_ruta.read_text(encoding="utf8")))            # sin duplicados al repetir
        # la política deja de denegar `shred`: se retira lo del harness y se conserva lo manual
        p = self.inst / "politicas.toml"
        p.write_text(p.read_text(encoding="utf8").replace("^shred", "^shredx").replace("^kubectl delete", "^kubectl get"), encoding="utf8")
        self.aplicar()
        cfg = json.loads(cfg_ruta.read_text(encoding="utf8"))
        self.assertNotIn("Bash(shred *)", cfg["permissions"]["deny"])
        self.assertIn("Bash(shredx *)", cfg["permissions"]["deny"])
        self.assertIn("Bash(rm *)", cfg["permissions"]["deny"])
        self.assertIn("Bash(git push)", cfg["permissions"]["deny"])          # lo manual, intacto
        self.assertEqual("x", cfg["model"])

    def test_settings_con_comentarios_no_se_toca_y_se_genera_el_alterno(self):
        cfg_ruta = self.inst / ".claude" / "settings.json"
        cfg_ruta.parent.mkdir(parents=True)
        crudo = '{\n  // mío\n  "model": "x"\n}\n'
        cfg_ruta.write_text(crudo, encoding="utf8")
        inf = self.aplicar()
        self.assertEqual(crudo, cfg_ruta.read_text(encoding="utf8"))
        alt = json.loads((self.inst / ".claude" / "settings.generado.json").read_text(encoding="utf8"))
        self.assertIn("Bash(git push *)", alt["permissions"]["ask"])
        self.assertTrue(any("settings.json" in a and "settings.generado.json" in a for a in inf["avisos"]))
        h = arbol_hash(self.inst)
        self.aplicar()
        self.assertEqual(h, arbol_hash(self.inst))

    def test_mcp_manual_con_otro_valor_gana_lo_manual(self):
        (self.inst / ".mcp.json").write_text(json.dumps({"mcpServers": {"docs": {"command": "mio"}, "otro": {"url": "http://x.example"}}}), encoding="utf8")
        anexar(self.inst, POL_MCP)
        inf = self.aplicar()
        cfg = json.loads((self.inst / ".mcp.json").read_text(encoding="utf8"))
        self.assertEqual({"command": "mio"}, cfg["mcpServers"]["docs"])
        self.assertIn("otro", cfg["mcpServers"])
        self.assertTrue(any("docs" in a and "a mano" in a for a in inf["avisos"]))

    def test_solo_dentro_de_la_instancia_y_nada_global(self):
        anexar(self.inst, POL_DENY + POL_MCP)
        home = self.tmp / "home"
        home.mkdir()
        antes, otros = arbol_hash(home), arbol_hash(comun.RAIZ / "adaptadores-agente")
        inf = self.aplicar()
        self.assertEqual(antes, arbol_hash(home))
        self.assertEqual(otros, arbol_hash(comun.RAIZ / "adaptadores-agente"))
        self.assertTrue(all(not a["ruta"].startswith(("/", "..", "~")) for a in inf["archivos"]))
        self.assertIn("no se escribe", " ".join(inf["pasos_para_la_persona"]))

    def test_capacidades_honestas(self):
        c = self.correr()["agentes"]["claude-code"]["capacidades"]
        for k in ("Skills", "Comandos propios", "MCP", "Permisos / modos / sandbox"):
            self.assertTrue(c[k]["generado_por_este_adaptador"], k)
        self.assertFalse(c["Memoria entre sesiones"]["generado_por_este_adaptador"])
        self.assertFalse(c["Subagentes / paralelo"]["generado_por_este_adaptador"])
        d = " ".join(x["que_se_pierde"] for x in self.correr()["agentes"]["claude-code"]["degradaciones"])
        for clave in ("Bash(git diff *)", "`.mcp.json`", "`.claude/commands/*.md`"):
            self.assertIn(clave, d)
        m = (comun.RAIZ / "adaptadores-agente" / "MATRIZ.md").read_text(encoding="utf8")
        for clave in ("`permissions.allow/deny/ask`", "Bash(git diff *)", "`.claude/commands/*.md`", "`.claude/skills/<n>/", "`.mcp.json`"):
            self.assertIn(clave, m)


if __name__ == "__main__":
    unittest.main()
