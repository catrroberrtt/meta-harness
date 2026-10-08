"""Pruebas del adaptador de Gemini CLI (contenido exacto según gemini/FORMATO.md) y del hook ejecutado de verdad."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun
from comun import arbol_hash

import fuente_neutral as fn
import generar_agentes as ga

BASE_TMP, BASE_INST = comun.crear_instancia_base()
SETTINGS = ".gemini/settings.json"
HOOKS = ".gemini/hooks"
GEMINI_MD = "GEMINI.md"


def tearDownModule():
    shutil.rmtree(BASE_TMP, True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mh-ge-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.inst = comun.copiar_instancia(BASE_INST, self.tmp)

    def correr(self, aplicar=False):
        return ga.planificar(self.inst, ["gemini"], ga.SistemaSimulado(), aplicar)["agentes"]["gemini"]


class TestArchivos(Base):
    def test_settings_json_exacto(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr(aplicar=True)
        doc = json.loads((self.inst / SETTINGS).read_text(encoding="utf8"))
        self.assertEqual(fn.MARCA, doc["_generado_por_el_harness"])
        self.assertEqual(["_generado_por_el_harness", "hooks"], list(doc))
        self.assertEqual(["BeforeTool"], list(doc["hooks"]))
        (grupo,) = doc["hooks"]["BeforeTool"]
        self.assertEqual("run_shell_command", grupo["matcher"])
        (h,) = grupo["hooks"]
        self.assertEqual({"name", "type", "command", "timeout", "description"}, set(h))
        self.assertEqual(("guardia-datos", "command", 30000), (h["name"], h["type"], h["timeout"]))
        self.assertEqual("$GEMINI_PROJECT_DIR/.gemini/hooks/lanzar.sh", h["command"])
        for n in ("block-db-access.sh", "guardia-datos.py", "lanzar.sh"):
            self.assertTrue((self.inst / HOOKS / n).stat().st_mode & 0o100, n)
            self.assertTrue(fn.es_generado((self.inst / HOOKS / n).read_text(encoding="utf8")), n)
        self.assertIn("--formato gemini", (self.inst / HOOKS / "lanzar.sh").read_text(encoding="utf8"))
        self.assertIn(SETTINGS, [a["ruta"] for a in inf["archivos"]])

    def test_gemini_md_importa_agents_md_con_la_sintaxis_documentada(self):
        self.correr(aplicar=True)
        t = (self.inst / GEMINI_MD).read_text(encoding="utf8")
        self.assertTrue(t.startswith(f"<!-- {fn.MARCA} -->"))
        self.assertIn("\n@./AGENTS.md\n", t)
        self.assertLess(len(t.splitlines()), 12)
        self.assertTrue(fn.es_generado(t))

    def test_no_escribe_context_filename(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        self.assertNotIn("context", json.loads((self.inst / SETTINGS).read_text(encoding="utf8")))

    def test_control_por_hook_siempre_degradado_aunque_haya_hook(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr()
        self.assertEqual("degradado", inf["control_por_hook"])
        self.assertIn("FALLA ABIERTO", inf["control_por_hook_motivo"])
        self.assertIn("capa de aviso", inf["control_por_hook_motivo"])

    def test_pasos_carpetas_de_confianza_huella_y_politica_de_usuario(self):
        comun.habilitar_hooks(self.inst)
        pasos = " ".join(self.correr()["pasos_para_la_persona"])
        for clave in ("folderTrust", "ignora", "/hooks panel", "huella", "~/.gemini/policies", 'decision = "deny"', "no se escribe"):
            self.assertIn(clave, pasos, clave)

    def test_sin_ambientes_hook_degradado_sin_archivos_de_hook_pero_con_gemini_md(self):
        inf = self.correr(aplicar=True)
        self.assertEqual("degradado", inf["control_por_hook"])
        self.assertIn("ningun ambiente", inf["control_por_hook_motivo"])
        self.assertFalse((self.inst / SETTINGS).exists())          # sin hook ni MCP permitido no hay settings.json
        self.assertFalse((self.inst / HOOKS).exists())
        self.assertTrue((self.inst / GEMINI_MD).exists())
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
        self.assertIn(SETTINGS, [a["ruta"] for a in inf["archivos"]])

    def test_no_pisa_settings_ni_gemini_md_manuales(self):
        comun.habilitar_hooks(self.inst)
        (self.inst / ".gemini").mkdir()
        (self.inst / SETTINGS).write_text('{"theme": "x"}\n', encoding="utf8")
        (self.inst / GEMINI_MD).write_text("# mío\n", encoding="utf8")
        inf = self.correr(aplicar=True)
        self.assertEqual('{"theme": "x"}\n', (self.inst / SETTINGS).read_text(encoding="utf8"))
        self.assertEqual("# mío\n", (self.inst / GEMINI_MD).read_text(encoding="utf8"))
        self.assertTrue((self.inst / ".gemini" / "settings.generado.json").exists())
        self.assertTrue((self.inst / "GEMINI.generado.md").exists())
        self.assertEqual(2, sum("escrito a mano" in a for a in inf["avisos"]))

    def test_agents_md_manual_se_importa_por_su_nombre_alterno(self):
        (self.inst / "AGENTS.md").write_text("# a mano\n", encoding="utf8")
        self.correr(aplicar=True)
        self.assertIn("@./AGENTS.generado.md", (self.inst / GEMINI_MD).read_text(encoding="utf8"))

    def test_solo_escribe_dentro_de_la_instancia(self):
        comun.habilitar_hooks(self.inst)
        otros = arbol_hash(comun.RAIZ / "adaptadores-agente")
        inf = self.correr(aplicar=True)
        self.assertEqual(otros, arbol_hash(comun.RAIZ / "adaptadores-agente"))
        self.assertTrue(all(not a["ruta"].startswith(("/", "..", "~")) for a in inf["archivos"]))
        self.assertFalse((self.inst / ".gemini" / "policies").exists())

    def test_no_genera_subagentes_ni_mcp_sin_servidores(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        self.assertFalse((self.inst / ".gemini" / "agents").exists())
        self.assertNotIn("mcpServers", (self.inst / SETTINGS).read_text(encoding="utf8"))


class TestCapacidades(Base):
    def test_capacidades_coherentes_con_el_formato(self):
        c = self.correr()["capacidades"]
        self.assertEqual("si", c["Hooks que bloquean"]["estado"])
        self.assertTrue(c["Hooks que bloquean"]["generado_por_este_adaptador"])
        self.assertTrue(c["Instrucciones del proyecto"]["generado_por_este_adaptador"])
        self.assertIn("context.fileName", c["Instrucciones del proyecto"]["nota"])
        self.assertIn("no funciona", c["Permisos / modos / sandbox"]["nota"])
        for cap in ("Skills", "MCP", "Comandos propios"):
            self.assertTrue(c[cap]["generado_por_este_adaptador"], cap)
        self.assertIn("permitida", c["MCP"]["nota"])
        self.assertIn("paso para la persona", c["Permisos / modos / sandbox"]["nota"])
        self.assertFalse(c["Subagentes / paralelo"]["generado_por_este_adaptador"])

    def test_degradaciones_dicen_lo_que_el_formato_confirma(self):
        comun.habilitar_hooks(self.inst)
        d = self.correr()["degradaciones"]
        todo = " ".join(x["que_se_pierde"] + " " + x["imposicion_alternativa"] for x in d)
        for clave in ("ABIERTO", "distinto de 0 y 2", "nombre o comando", "Trusted Folders", "run_shell_command", "ask", "non-functional",
                      "~/.gemini/policies", "sandbox", "solo lectura", "integración continua", "glob"):
            self.assertIn(clave, todo, clave)
        self.assertTrue(all(x["fuente"] and x["imposicion_alternativa"] for x in d))
        self.assertTrue(any("protección de ramas" in x["imposicion_alternativa"] for x in d))


@unittest.skipUnless(shutil.which("jq") and shutil.which("git") and shutil.which("bash"), "faltan jq, git o bash")
class TestHookEjecutado(Base):
    """Ejecuta los scripts reales con la entrada documentada de `BeforeTool`."""

    def preparar(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        repo = self.tmp / "servicio-demo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        return repo

    def entrada(self, repo, comando, herramienta="run_shell_command"):
        return json.dumps({"session_id": "s", "transcript_path": "/t", "cwd": str(repo), "hook_event_name": "BeforeTool", "timestamp": "2026-01-01T00:00:00Z",
                           "tool_name": herramienta, "tool_input": {"command": comando}, "original_request_name": herramienta})

    def correr_puente(self, entrada, repo, env=None):
        return subprocess.run([sys.executable, str(self.inst / HOOKS / "guardia-datos.py"), "--formato", "gemini"], input=entrada,
                              capture_output=True, text=True, cwd=str(repo), env=env)

    def verifica_denegacion(self, r):
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)            # JSON + salida 0 (la documentación lo prefiere)
        v = json.loads(r.stdout)                                           # stdout solo lleva el JSON
        self.assertEqual("deny", v["decision"])
        self.assertTrue(v["reason"])
        return v

    def test_deniega_host_remoto_y_ddl_local_y_permite_ls(self):
        repo = self.preparar()
        v = self.verifica_denegacion(self.correr_puente(self.entrada(repo, "mysql -h db.externo.example -e 'SELECT 1'"), repo))
        self.assertIn("Bloqueado", v["reason"])
        self.verifica_denegacion(self.correr_puente(self.entrada(repo, "mysql -h localhost -e 'DROP TABLE clientes'"), repo))
        r = self.correr_puente(self.entrada(repo, "ls -la"), repo)
        self.assertEqual((0, {"decision": "allow"}), (r.returncode, json.loads(r.stdout)))

    def test_otras_herramientas_no_las_juzga(self):
        repo = self.preparar()
        r = self.correr_puente(self.entrada(repo, "x", herramienta="read_file"), repo)
        self.assertEqual((0, "allow"), (r.returncode, json.loads(r.stdout)["decision"]))

    def test_entrada_ilegible_o_incompleta_deniega(self):
        repo = self.preparar()
        for malo in ("no es json", "", "[]", json.dumps({"tool_name": "run_shell_command", "tool_input": {}}),
                     json.dumps({"tool_name": "run_shell_command", "tool_input": {"command": ["ls"]}})):
            r = self.correr_puente(malo, repo)
            self.verifica_denegacion(r)
            self.assertTrue(r.stderr.strip())

    def test_sin_jq_deniega(self):
        repo = self.preparar()
        sin_jq = self.tmp / "bin"
        sin_jq.mkdir()
        for n in ("bash", "git"):
            os.symlink(shutil.which(n), sin_jq / n)
        r = self.correr_puente(self.entrada(repo, "ls"), repo, env={"PATH": str(sin_jq)})
        self.verifica_denegacion(r)
        self.assertIn("jq", json.loads(r.stdout)["reason"])

    def test_fallo_del_hook_de_politica_deniega(self):
        repo = self.preparar()
        (self.inst / HOOKS / "block-db-access.sh").unlink()
        self.verifica_denegacion(self.correr_puente(self.entrada(repo, "ls"), repo))

    def test_el_comando_registrado_en_settings_funciona_tal_cual(self):
        repo = self.preparar()
        comando = json.loads((self.inst / SETTINGS).read_text(encoding="utf8"))["hooks"]["BeforeTool"][0]["hooks"][0]["command"]
        env = dict(os.environ, GEMINI_PROJECT_DIR=str(self.inst))
        corre = lambda cmd: subprocess.run(["sh", "-c", comando], input=self.entrada(repo, cmd), capture_output=True, text=True, cwd=str(repo), env=env)
        self.verifica_denegacion(corre("mysql -h db.externo.example -e 'SELECT 1'"))
        self.assertEqual("allow", json.loads(corre("ls").stdout)["decision"])

    def test_lanzador_sin_python3_deniega_con_json_y_salida_0(self):
        repo = self.preparar()
        vacio = self.tmp / "vacio"
        vacio.mkdir()
        r = subprocess.run(["/bin/sh", str(self.inst / HOOKS / "lanzar.sh")], input=self.entrada(repo, "ls"), capture_output=True,
                           text=True, cwd=str(repo), env={"PATH": str(vacio)})
        self.verifica_denegacion(r)
        self.assertIn("python3", r.stderr)

    def test_lanzador_sin_el_puente_deniega(self):
        repo = self.preparar()
        (self.inst / HOOKS / "guardia-datos.py").unlink()
        r = subprocess.run(["/bin/sh", str(self.inst / HOOKS / "lanzar.sh")], input=self.entrada(repo, "ls"), capture_output=True, text=True, cwd=str(repo))
        self.verifica_denegacion(r)


# ----------------------------------------------------------------------------- skills, comandos, permisos y MCP
import importlib.util

import fixtures_cap as F

_espec = importlib.util.spec_from_file_location("adaptador_gemini", comun.RAIZ / "adaptadores-agente" / "gemini" / "adaptador.py")
adaptador = importlib.util.module_from_spec(_espec)
_espec.loader.exec_module(adaptador)
SKILLS = ".gemini/skills"
COMANDOS = ".gemini/commands"


class TestCapacidadesGemini(Base):
    def test_skills_en_gemini_skills_con_marca_y_contenido_neutral(self):
        self.correr(aplicar=True)
        skills = F.fuente_de(self.inst)["skills"]
        self.assertEqual(4, len(skills))
        for s in skills:
            t = F.leer(self.inst, f"{SKILLS}/{s['nombre']}/SKILL.md")
            self.assertTrue(t.startswith("---\nname: " + s["nombre"] + "\n"))
            self.assertIn(fn.MARCA, t)
            self.assertTrue(fn.es_generado(t))
            self.assertEqual(s["contenido"], F.sin_marca_html(t).replace(f"# {fn.MARCA}\n", "", 1))
        self.assertEqual(4, len(list((self.inst / SKILLS).glob("*/SKILL.md"))))
        self.assertFalse((self.inst / ".agents").exists())

    def test_comandos_toml_con_description_y_prompt(self):
        inf = self.correr(aplicar=True)
        comandos = F.fuente_de(self.inst)["comandos"]
        self.assertEqual({"harness-estado", "harness-gate"}, {c["nombre"] for c in comandos})
        for c in comandos:
            t = F.leer(self.inst, f"{COMANDOS}/{c['nombre']}.toml")
            doc = tomllib.loads(t)
            self.assertEqual({"description", "prompt"}, set(doc))
            self.assertEqual(c["descripcion"], doc["description"])
            cuerpo = c["contenido"].split("---\n", 2)[2].strip("\n")
            self.assertEqual(cuerpo, doc["prompt"].strip("\n"))
            self.assertTrue(t.startswith("# " + fn.MARCA))
            self.assertTrue(fn.es_generado(t))
        self.assertTrue(any("/commands reload" in p for p in inf["pasos_para_la_persona"]))

    def test_comando_con_marcadores_de_gemini_no_se_genera(self):
        c = {"nombre": "peligro", "descripcion": "d", "contenido": "---\ndescription: d\n---\nejecuta !{ls}\n"}
        texto, motivo = adaptador.comando_toml(c)
        self.assertIsNone(texto)
        self.assertIn("!{", motivo)

    def test_permisos_solo_paso_para_la_persona_con_prefijos_literales(self):
        F.anexar(self.inst, F.POL_DENY)
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / ".gemini" / "policies").exists())
        paso = [p for p in inf["pasos_para_la_persona"] if "~/.gemini/policies/harness.toml" in p]
        self.assertEqual(1, len(paso))
        doc = tomllib.loads(paso[0].split(":\n", 1)[1].split("\n(`deny`", 1)[0])
        reglas = [(r["commandPrefix"], r["decision"], r["priority"]) for r in doc["rule"]]
        self.assertEqual([("terraform destroy", "deny", 100), ("kubectl delete", "deny", 100), ("shred", "deny", 100),
                          ("git commit", "ask_user", 50), ("git push", "ask_user", 50)], reglas)
        for r in doc["rule"]:
            self.assertEqual("run_shell_command", r["toolName"])
        for ancho in ("git", "terraform", "kubectl"):
            self.assertNotIn(ancho, [x[0] for x in reglas])
        deg = " ".join(d["que_se_pierde"] for d in inf["degradaciones"])
        for regla in ("migraciones", "semillas", "CLI del ORM", "comandos.instalar", "push_a_rama_protegida"):
            self.assertIn(regla, deg)

    def test_regla_exceptuada_por_ambiente_va_a_no_traducible(self):
        F.anexar(self.inst, '[[datos.comandos]]\nnombre = "x"\nregex = "^rm -rf"\naccion = "prohibida"\nmotivo = "m"\npermitida_en_ambiente_de_escritura = true\n')
        deny, ask, nt = adaptador.permisos_traducibles(F.fuente_de(self.inst))
        self.assertNotIn("rm -rf", deny)
        self.assertIn("rm -rf", [x["regla"] for x in nt])

    def test_mcp_permitida_escribe_en_settings_con_referencias_y_nunca_valores(self):
        F.anexar(self.inst, F.POL_MCP)
        os.environ["DOCS_VAR"] = "valor-secreto-que-no-debe-aparecer"
        self.addCleanup(os.environ.pop, "DOCS_VAR", None)
        inf = self.correr(aplicar=True)
        texto = F.leer(self.inst, SETTINGS)
        self.assertNotIn("valor-secreto", texto)
        doc = json.loads(texto)
        self.assertEqual({"docs": {"command": "npx", "args": ["-y", "paquete-docs"], "env": {"DOCS_VAR": "${DOCS_VAR}"}},
                          "web": {"httpUrl": "https://mcp.example.com/web"}}, doc["mcpServers"])
        self.assertNotIn("hooks", doc)
        self.assertNotIn("buscador", texto)
        self.assertNotIn("vetado", texto)
        self.assertTrue(any("vetado" in a and "prohíbe" in a for a in inf["avisos"]))

    def test_mcp_confirmar_no_escribe_e_imprime_el_fragmento(self):
        F.anexar(self.inst, F.POL_MCP_CONFIRMAR)
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / SETTINGS).exists())
        paso = [p for p in inf["pasos_para_la_persona"] if "buscador" in p]
        self.assertEqual(1, len(paso))
        self.assertIn(json.dumps({"mcpServers": {"buscador": {"httpUrl": "https://mcp.example.com/mcp"}}}, ensure_ascii=False, indent=2), paso[0])
        self.assertIn("registrar = \"confirmar\"", paso[0])

    def test_mcp_prohibida_no_escribe_nada(self):
        F.anexar(self.inst, '[[mcp.servidores]]\nnombre = "vetado"\ncomando = "otro"\nregistrar = "prohibida"\n')
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / SETTINGS).exists())
        self.assertFalse(any("vetado" in p for p in inf["pasos_para_la_persona"]))
        self.assertTrue(any("vetado" in a for a in inf["avisos"]))

    def test_sin_servidores_no_hay_mcp(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr(aplicar=True)
        self.assertNotIn("mcpServers", F.leer(self.inst, SETTINGS))
        self.assertFalse(any("MCP" in p for p in inf["pasos_para_la_persona"]))

    def test_alias_con_guion_bajo_no_se_traduce(self):
        e, motivo = adaptador.entrada_mcp({"nombre": "mi_srv", "tipo": "local", "comando": "x", "args": [], "entorno": []})
        self.assertIsNone(e)
        self.assertIn("guion bajo", motivo)

    def test_hook_y_mcp_van_juntos_en_un_solo_settings_sin_duplicar(self):
        comun.habilitar_hooks(self.inst)
        F.anexar(self.inst, F.POL_MCP)
        self.correr(aplicar=True)
        doc = F.leer_json(self.inst, SETTINGS)
        self.assertEqual({"_generado_por_el_harness", "hooks", "mcpServers"}, set(doc))
        self.assertEqual(1, len(doc["hooks"]["BeforeTool"]))
        self.assertEqual(1, F.leer(self.inst, SETTINGS).count('"BeforeTool"'))

    def test_settings_manual_no_se_pisa_y_lo_generado_va_al_lado(self):
        F.anexar(self.inst, F.POL_MCP)
        (self.inst / ".gemini").mkdir()
        (self.inst / SETTINGS).write_text('{"theme": "x"}\n', encoding="utf8")
        inf = self.correr(aplicar=True)
        self.assertEqual('{"theme": "x"}\n', F.leer(self.inst, SETTINGS))
        self.assertIn("mcpServers", F.leer(self.inst, ".gemini/settings.generado.json"))
        self.assertTrue(any("no se fusiona" in p for p in inf["pasos_para_la_persona"]))

    def test_skill_y_comando_manuales_no_se_pisan(self):
        d = self.inst / SKILLS / "sdd-verificar"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: sdd-verificar\ndescription: mía\n---\nmanual\n", encoding="utf8")
        (self.inst / COMANDOS).mkdir(parents=True)
        (self.inst / COMANDOS / "harness-gate.toml").write_text('prompt = "mío"\n', encoding="utf8")
        self.correr(aplicar=True)
        self.assertIn("manual", F.leer(self.inst, f"{SKILLS}/sdd-verificar/SKILL.md"))
        self.assertTrue((d / "SKILL.generado.md").exists())
        self.assertEqual('prompt = "mío"\n', F.leer(self.inst, f"{COMANDOS}/harness-gate.toml"))
        self.assertTrue((self.inst / COMANDOS / "harness-gate.generado.toml").exists())

    def test_idempotente_con_todo(self):
        comun.habilitar_hooks(self.inst)
        F.anexar(self.inst, F.POL_DENY + F.POL_MCP)
        self.correr(aplicar=True)
        h = arbol_hash(self.inst)
        inf = self.correr(aplicar=True)
        self.assertEqual(h, arbol_hash(self.inst))
        self.assertTrue(all(a["accion"] == "igual" for a in inf["archivos"]), [a for a in inf["archivos"] if a["accion"] != "igual"])

    def test_solo_dentro_de_la_instancia_y_plan_no_escribe(self):
        F.anexar(self.inst, F.POL_DENY + F.POL_MCP)
        antes = arbol_hash(self.tmp)
        inf = self.correr(aplicar=False)
        self.assertEqual(antes, arbol_hash(self.tmp))
        self.assertIn(f"{COMANDOS}/harness-gate.toml", [a["ruta"] for a in inf["archivos"]])
        inf = self.correr(aplicar=True)
        self.assertTrue(all(not a["ruta"].startswith(("/", "..", "~")) for a in inf["archivos"]))

    def test_degradaciones_honestas_sobre_mcp_permisos_y_comandos(self):
        F.anexar(self.inst, F.POL_DENY)
        d = " ".join(x["que_se_pierde"] + " " + x["imposicion_alternativa"] for x in self.correr()["degradaciones"])
        for clave in ("registrar = \"permitida\"", "httpUrl", "Trusted Folders", "NO se escriben", "ask_user", "marcadores propios"):
            self.assertIn(clave, d, clave)


if __name__ == "__main__":
    unittest.main()
