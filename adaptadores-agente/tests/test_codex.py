"""Pruebas del adaptador de Codex (contenido exacto según codex/FORMATO.md) y del hook ejecutado de verdad."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun
from comun import arbol_hash

import fuente_neutral as fn
import generar_agentes as ga

BASE_TMP, BASE_INST = comun.crear_instancia_base()
HOOKS_JSON = ".codex/hooks.json"
HOOKS = ".codex/hooks"
REGLAS = ".codex/rules/harness.rules"
COMANDOS_POLITICA = """
[[datos.comandos]]
nombre = "volcado"
regex = "^mysqldump"
motivo = "No se hacen volcados desde el agente"

[[datos.comandos]]
nombre = "complejo"
regex = "(drop|truncate)\\\\s+table"
motivo = "Regex arbitrario: no se traduce a prefijo"
"""


def tearDownModule():
    shutil.rmtree(BASE_TMP, True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mh-cx-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.inst = comun.copiar_instancia(BASE_INST, self.tmp)

    def correr(self, aplicar=False):
        return ga.planificar(self.inst, ["codex"], ga.SistemaSimulado(), aplicar)["agentes"]["codex"]


class TestArchivos(Base):
    def test_hooks_json_exacto(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr(aplicar=True)
        doc = json.loads((self.inst / HOOKS_JSON).read_text(encoding="utf8"))
        self.assertEqual(fn.MARCA, doc["_generado_por_el_harness"])
        self.assertEqual(["_generado_por_el_harness", "hooks"], list(doc))
        self.assertEqual(["PreToolUse"], list(doc["hooks"]))
        (grupo,) = doc["hooks"]["PreToolUse"]
        self.assertEqual("^Bash$", grupo["matcher"])
        (h,) = grupo["hooks"]
        self.assertEqual({"type", "command", "timeout", "statusMessage"}, set(h))
        self.assertEqual("command", h["type"])
        self.assertEqual(30, h["timeout"])
        self.assertEqual('/bin/sh "$(git rev-parse --show-toplevel)/.codex/hooks/lanzar.sh"', h["command"])
        for n in ("block-db-access.sh", "guardia-datos.py", "lanzar.sh"):
            self.assertTrue((self.inst / HOOKS / n).stat().st_mode & 0o100, n)
            self.assertTrue(fn.es_generado((self.inst / HOOKS / n).read_text(encoding="utf8")), n)
        self.assertIn("--formato codex", (self.inst / HOOKS / "lanzar.sh").read_text(encoding="utf8"))
        self.assertIn(HOOKS_JSON, [a["ruta"] for a in inf["archivos"]])

    def test_control_por_hook_siempre_degradado_aunque_haya_hook(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr()
        self.assertEqual("degradado", inf["control_por_hook"])
        self.assertIn("FALLA ABIERTO", inf["control_por_hook_motivo"])
        self.assertIn("capa de aviso", inf["control_por_hook_motivo"])
        self.assertNotEqual("disponible", inf["control_por_hook"])

    def test_pasos_incluyen_confiar_en_el_hook_y_lo_global_no_se_escribe(self):
        comun.habilitar_hooks(self.inst)
        pasos = " ".join(self.correr()["pasos_para_la_persona"])
        self.assertIn("/hooks", pasos)
        self.assertIn("NO corre hasta que lo confíes", pasos)
        self.assertIn("requirements.toml", pasos)
        self.assertIn("no se escribe", pasos)

    def test_sin_ambientes_hook_degradado_y_sin_archivos_de_hook(self):
        inf = self.correr(aplicar=True)
        self.assertEqual("degradado", inf["control_por_hook"])
        self.assertIn("ningun ambiente", inf["control_por_hook_motivo"])
        self.assertFalse((self.inst / ".codex" / "hooks").exists())
        self.assertFalse((self.inst / HOOKS_JSON).exists())
        self.assertTrue(any("no se generó" in d["que_se_pierde"] for d in inf["degradaciones"]))

    def test_rules_solo_con_prefijos_literales_de_la_politica(self):
        comun.habilitar_hooks(self.inst)
        p = self.inst / "politicas.toml"
        p.write_text(p.read_text(encoding="utf8") + COMANDOS_POLITICA, encoding="utf8")
        inf = self.correr(aplicar=True)
        t = (self.inst / REGLAS).read_text(encoding="utf8")
        self.assertTrue(t.startswith(f"# {fn.MARCA}"))
        self.assertEqual(1, t.count('decision = "forbidden"'))
        self.assertIn('pattern = ["mysqldump"],', t)
        self.assertIn('decision = "forbidden",', t)
        self.assertIn('justification = "No se hacen volcados desde el agente",', t)
        self.assertIn('match = ["mysqldump"],', t)
        self.assertNotIn("drop", t)
        self.assertIn("codex execpolicy check", " ".join(inf["pasos_para_la_persona"]))

    def test_sin_comandos_prohibidos_solo_hay_reglas_prompt_de_la_politica(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        t = (self.inst / REGLAS).read_text(encoding="utf8")
        self.assertNotIn("forbidden", t)
        self.assertEqual(['pattern = ["git", "commit"],', 'pattern = ["git", "push"],'], [l.strip() for l in t.splitlines() if "pattern" in l])

    def test_idempotente(self):
        comun.habilitar_hooks(self.inst)
        p = self.inst / "politicas.toml"
        p.write_text(p.read_text(encoding="utf8") + COMANDOS_POLITICA, encoding="utf8")
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

    def test_no_pisa_hooks_json_manual(self):
        comun.habilitar_hooks(self.inst)
        (self.inst / ".codex").mkdir()
        (self.inst / HOOKS_JSON).write_text('{"hooks": {}}\n', encoding="utf8")
        inf = self.correr(aplicar=True)
        self.assertEqual('{"hooks": {}}\n', (self.inst / HOOKS_JSON).read_text(encoding="utf8"))
        self.assertTrue((self.inst / ".codex" / "hooks.generado.json").exists())
        self.assertEqual(1, sum("escrito a mano" in a for a in inf["avisos"]))

    def test_no_pisa_rules_manual(self):
        comun.habilitar_hooks(self.inst)
        p = self.inst / "politicas.toml"
        p.write_text(p.read_text(encoding="utf8") + COMANDOS_POLITICA, encoding="utf8")
        (self.inst / ".codex" / "rules").mkdir(parents=True)
        (self.inst / REGLAS).write_text("# mía\n", encoding="utf8")
        self.correr(aplicar=True)
        self.assertEqual("# mía\n", (self.inst / REGLAS).read_text(encoding="utf8"))
        self.assertTrue((self.inst / ".codex" / "rules" / "harness.generado.rules").exists())

    def test_solo_escribe_dentro_de_la_instancia(self):
        comun.habilitar_hooks(self.inst)
        otros = arbol_hash(comun.RAIZ / "adaptadores-agente")
        inf = self.correr(aplicar=True)
        self.assertEqual(otros, arbol_hash(comun.RAIZ / "adaptadores-agente"))
        self.assertTrue(all(not a["ruta"].startswith(("/", "..", "~")) for a in inf["archivos"]))

    def test_no_genera_mcp_ni_subagentes_ni_prompts_sin_servidores(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        self.assertFalse((self.inst / ".codex" / "config.toml").exists())
        self.assertFalse((self.inst / ".codex" / "agents").exists())
        self.assertFalse((self.inst / ".codex" / "prompts").exists())

    def test_aviso_si_agents_md_supera_32_kib(self):
        with mock.patch.object(fn, "render_agents_md", return_value="x" * (32 * 1024 + 1)):
            inf = self.correr()
        self.assertTrue(any("32768" in a and "project_doc_max_bytes" in a for a in inf["avisos"]))

    def test_sin_aviso_de_tamano_normalmente(self):
        self.assertFalse(any("project_doc_max_bytes" in a for a in self.correr()["avisos"]))


class TestCapacidades(Base):
    def test_capacidades_coherentes_con_el_formato(self):
        c = self.correr()["capacidades"]
        self.assertEqual("si", c["Hooks que bloquean"]["estado"])
        self.assertTrue(c["Hooks que bloquean"]["generado_por_este_adaptador"])
        self.assertTrue(c["Instrucciones del proyecto"]["generado_por_este_adaptador"])
        self.assertIn("32 KiB", c["Instrucciones del proyecto"]["nota"])
        self.assertIn("glob", c["Reglas por ruta"]["nota"])
        for cap in ("Skills", "MCP"):
            self.assertTrue(c[cap]["generado_por_este_adaptador"], cap)
        self.assertFalse(c["Subagentes / paralelo"]["generado_por_este_adaptador"])
        self.assertFalse(c["Comandos propios"]["generado_por_este_adaptador"])
        self.assertIn("obsoleto", c["Comandos propios"]["nota"])

    def test_degradaciones_dicen_lo_que_el_formato_confirma(self):
        comun.habilitar_hooks(self.inst)
        d = self.correr()["degradaciones"]
        todo = " ".join(x["que_se_pierde"] + " " + x["imposicion_alternativa"] for x in d)
        for clave in ("ABIERTO", "/hooks", "apply_patch", "WebSearch", "ask", ".rules", "forbidden", "sandbox", "solo lectura",
                      "integración continua", "requirements.toml", "32 KiB", "glob", "danger-full-access"):
            self.assertIn(clave, todo, clave)
        self.assertTrue(all(x["fuente"] and x["imposicion_alternativa"] for x in d))
        self.assertTrue(any("protección de ramas" in x["imposicion_alternativa"] for x in d))


# ----------------------------------------------------------------------------- skills, comandos, permisos y MCP
import tomllib

import fixtures_cap as F

CONFIG = ".codex/config.toml"
SKILLS = ".agents/skills"


def reglas_de(texto):
    """[(pattern, decision, justification)] leídos del Starlark generado (formato fijo de `prefix_rule`)."""
    out, cur = [], {}
    for l in texto.splitlines():
        l = l.strip()
        for k in ("pattern", "decision", "justification"):
            if l.startswith(k + " = "):
                cur[k] = json.loads(l[len(k) + 3:].rstrip(","))
        if l == ")":
            out.append((cur["pattern"], cur["decision"], cur["justification"]))
            cur = {}
    return out


class TestCapacidadesCodex(Base):
    def test_skills_en_agents_skills_con_marca_y_contenido_neutral(self):
        self.correr(aplicar=True)
        skills = F.fuente_de(self.inst)["skills"]
        self.assertEqual(4, len(skills))
        for s in skills:
            t = F.leer(self.inst, f"{SKILLS}/{s['nombre']}/SKILL.md")
            self.assertTrue(t.startswith("---\nname: " + s["nombre"] + "\n"))
            self.assertTrue(fn.es_generado(t))
            self.assertEqual(s["contenido"], F.sin_marca_html(t).replace(f"# {fn.MARCA}\n", "", 1))
        self.assertFalse((self.inst / ".codex" / "skills").exists())

    def test_comandos_no_se_generan_y_se_avisa_con_el_sustituto(self):
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / ".codex" / "prompts").exists())
        aviso = [a for a in inf["avisos"] if "Comandos no generados" in a]
        self.assertEqual(1, len(aviso))
        self.assertIn("harness-gate", aviso[0])
        self.assertIn("skills", aviso[0])
        self.assertTrue(any("prompts" in d["que_se_pierde"] and "obsoleto" in d["que_se_pierde"] for d in inf["degradaciones"]))

    def test_permisos_forbidden_y_prompt_con_prefijos_literales(self):
        F.anexar(self.inst, F.POL_DENY)
        inf = self.correr(aplicar=True)
        reglas = reglas_de(F.leer(self.inst, REGLAS))
        self.assertEqual([(["terraform", "destroy"], "forbidden", "destruye infraestructura"), (["kubectl", "delete"], "forbidden", "destruye infraestructura"),
                          (["shred"], "forbidden", "borra datos")],
                         [r for r in reglas if r[1] == "forbidden"])
        self.assertEqual([["git", "commit"], ["git", "push"]], [r[0] for r in reglas if r[1] == "prompt"])
        for ancho in (["git"], ["terraform"], ["kubectl"]):
            self.assertNotIn(ancho, [r[0] for r in reglas])
        self.assertFalse(any(r[1] == "allow" for r in reglas))
        t = F.leer(self.inst, REGLAS)
        self.assertTrue(t.startswith(f"# {fn.MARCA}"))
        deg = " ".join(d["que_se_pierde"] for d in inf["degradaciones"])
        for regla in ("migraciones", "semillas", "CLI del ORM", "comandos.instalar", "push_a_rama_protegida"):
            self.assertIn(regla, deg)
        self.assertIn("no es un prefijo literal", deg)

    def test_regla_exceptuada_por_ambiente_no_se_traduce_y_se_informa(self):
        F.anexar(self.inst, '[[datos.comandos]]\nnombre = "x"\nregex = "^rm -rf"\naccion = "prohibida"\nmotivo = "m"\npermitida_en_ambiente_de_escritura = true\n')
        inf = self.correr(aplicar=True)
        self.assertNotIn("rm", " ".join(" ".join(r[0]) for r in reglas_de(F.leer(self.inst, REGLAS))))
        self.assertTrue(any("rm -rf" in d["que_se_pierde"] and "forbidden" in d["que_se_pierde"] for d in inf["degradaciones"]))

    def test_rules_no_duplica_prefijos(self):
        F.anexar(self.inst, '[[datos.comandos]]\nnombre = "p"\nregex = "^git push"\naccion = "prohibida"\nmotivo = "no pushear"\n')
        reglas = reglas_de(F.leer(self.inst, REGLAS)) if self.correr(aplicar=True) else []
        self.assertEqual(1, [r[0] for r in reglas].count(["git", "push"]))

    def test_mcp_permitida_escribe_config_toml_con_env_vars_y_nunca_valores(self):
        F.anexar(self.inst, F.POL_MCP)
        os.environ["DOCS_VAR"] = "valor-secreto-que-no-debe-aparecer"
        self.addCleanup(os.environ.pop, "DOCS_VAR", None)
        inf = self.correr(aplicar=True)
        texto = F.leer(self.inst, CONFIG)
        self.assertNotIn("valor-secreto", texto)
        self.assertTrue(texto.startswith(f"# {fn.MARCA}"))
        self.assertTrue(fn.es_generado(texto))
        doc = tomllib.loads(texto)
        self.assertEqual({"docs": {"command": "npx", "args": ["-y", "paquete-docs"], "env_vars": ["DOCS_VAR"]},
                          "web": {"url": "https://mcp.example.com/web"}}, doc["mcp_servers"])
        self.assertNotIn("buscador", texto)
        self.assertNotIn("vetado", texto)
        self.assertTrue(any("vetado" in a and "prohíbe" in a for a in inf["avisos"]))

    def test_mcp_con_variable_de_otro_nombre_no_se_traduce(self):
        F.anexar(self.inst, '[[mcp.servidores]]\nnombre = "docs"\ncomando = "npx"\nentorno = { API_X = "${OTRA}" }\nregistrar = "permitida"\n')
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / CONFIG).exists())
        self.assertTrue(any("docs" in a and "API_X" in a for a in inf["avisos"]))

    def test_mcp_confirmar_no_escribe_e_imprime_el_fragmento(self):
        F.anexar(self.inst, F.POL_MCP_CONFIRMAR)
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / CONFIG).exists())
        paso = [p for p in inf["pasos_para_la_persona"] if "buscador" in p]
        self.assertEqual(1, len(paso))
        self.assertIn('[mcp_servers.buscador]\nurl = "https://mcp.example.com/mcp"', paso[0])
        self.assertIn("confirmar", paso[0])

    def test_mcp_prohibida_y_sin_servidores_no_escriben_nada(self):
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / CONFIG).exists())
        self.assertFalse(any("MCP" in p for p in inf["pasos_para_la_persona"]))
        F.anexar(self.inst, '[[mcp.servidores]]\nnombre = "vetado"\ncomando = "otro"\nregistrar = "prohibida"\n')
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / CONFIG).exists())
        self.assertFalse(any("vetado" in p for p in inf["pasos_para_la_persona"]))
        self.assertTrue(any("vetado" in a for a in inf["avisos"]))

    def test_manual_no_se_pisa_config_skill_y_rules(self):
        F.anexar(self.inst, F.POL_DENY + F.POL_MCP)
        (self.inst / ".codex").mkdir()
        (self.inst / CONFIG).write_text("model = \"x\"\n", encoding="utf8")
        d = self.inst / SKILLS / "sdd-verificar"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: sdd-verificar\ndescription: mía\n---\nmanual\n", encoding="utf8")
        self.correr(aplicar=True)
        self.assertEqual("model = \"x\"\n", F.leer(self.inst, CONFIG))
        self.assertTrue((self.inst / ".codex" / "config.generado.toml").exists())
        self.assertIn("manual", F.leer(self.inst, f"{SKILLS}/sdd-verificar/SKILL.md"))
        self.assertTrue((d / "SKILL.generado.md").exists())

    def test_idempotente_con_todo_y_solo_dentro_de_la_instancia(self):
        comun.habilitar_hooks(self.inst)
        F.anexar(self.inst, F.POL_DENY + F.POL_MCP)
        otros = arbol_hash(comun.RAIZ / "adaptadores-agente")
        inf = self.correr(aplicar=True)
        h = arbol_hash(self.inst)
        inf = self.correr(aplicar=True)
        self.assertEqual(h, arbol_hash(self.inst))
        self.assertTrue(all(a["accion"] == "igual" for a in inf["archivos"]), [a for a in inf["archivos"] if a["accion"] != "igual"])
        self.assertEqual(otros, arbol_hash(comun.RAIZ / "adaptadores-agente"))
        self.assertTrue(all(not a["ruta"].startswith(("/", "..", "~")) for a in inf["archivos"]))

    def test_plan_no_escribe(self):
        F.anexar(self.inst, F.POL_DENY + F.POL_MCP)
        antes = arbol_hash(self.tmp)
        inf = self.correr(aplicar=False)
        self.assertEqual(antes, arbol_hash(self.tmp))
        rutas = [a["ruta"] for a in inf["archivos"]]
        for r in (REGLAS, CONFIG, f"{SKILLS}/sdd-verificar/SKILL.md"):
            self.assertIn(r, rutas)


@unittest.skipUnless(shutil.which("jq") and shutil.which("git") and shutil.which("bash"), "faltan jq, git o bash")
class TestHookEjecutado(Base):
    """Ejecuta los scripts reales con la entrada documentada de `PreToolUse`."""

    def preparar(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        repo = self.tmp / "servicio-demo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        return repo

    def entrada(self, repo, comando, herramienta="Bash"):
        return json.dumps({"session_id": "s", "cwd": str(repo), "hook_event_name": "PreToolUse", "model": "m", "permission_mode": "default",
                           "tool_name": herramienta, "tool_input": {"command": comando}, "tool_use_id": "t", "transcript_path": None, "turn_id": "1"})

    def correr_puente(self, entrada, repo, env=None):
        return subprocess.run([sys.executable, str(self.inst / HOOKS / "guardia-datos.py"), "--formato", "codex"], input=entrada,
                              capture_output=True, text=True, cwd=str(repo), env=env)

    def verifica_denegacion(self, r):
        self.assertEqual(2, r.returncode, r.stdout + r.stderr)
        self.assertTrue(r.stderr.strip(), "salida 2 sin texto en stderr: Codex la trataría como fallo y dejaría pasar")
        h = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual("PreToolUse", h["hookEventName"])
        self.assertEqual("deny", h["permissionDecision"])
        self.assertTrue(h["permissionDecisionReason"])

    def test_deniega_host_remoto_y_ddl_local_y_permite_ls(self):
        repo = self.preparar()
        self.verifica_denegacion(self.correr_puente(self.entrada(repo, "mysql -h db.externo.example -e 'SELECT 1'"), repo))
        self.verifica_denegacion(self.correr_puente(self.entrada(repo, "mysql -h localhost -e 'DROP TABLE clientes'"), repo))
        r = self.correr_puente(self.entrada(repo, "ls -la"), repo)
        self.assertEqual((0, ""), (r.returncode, r.stdout.strip()))

    def test_otras_herramientas_no_las_juzga(self):
        repo = self.preparar()
        r = self.correr_puente(self.entrada(repo, "*** Begin Patch", herramienta="apply_patch"), repo)
        self.assertEqual(0, r.returncode)

    def test_entrada_ilegible_o_incompleta_deniega(self):
        repo = self.preparar()
        for malo in ("no es json", "", "[]", json.dumps({"tool_name": "Bash", "tool_input": {}}),
                     json.dumps({"tool_name": "Bash", "tool_input": {"command": 5}})):
            self.verifica_denegacion(self.correr_puente(malo, repo))

    def test_sin_jq_deniega(self):
        repo = self.preparar()
        sin_jq = self.tmp / "bin"
        sin_jq.mkdir()
        for n in ("bash", "git"):
            os.symlink(shutil.which(n), sin_jq / n)
        r = self.correr_puente(self.entrada(repo, "ls"), repo, env={"PATH": str(sin_jq)})
        self.verifica_denegacion(r)
        self.assertIn("jq", r.stderr)

    def test_fallo_del_hook_de_politica_deniega(self):
        repo = self.preparar()
        (self.inst / HOOKS / "block-db-access.sh").unlink()
        self.verifica_denegacion(self.correr_puente(self.entrada(repo, "ls"), repo))

    def test_el_comando_registrado_en_hooks_json_funciona_tal_cual(self):
        repo = self.preparar()
        subprocess.run(["git", "init", "-q", str(self.inst)], check=True)
        comando = json.loads((self.inst / HOOKS_JSON).read_text(encoding="utf8"))["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        corre = lambda cmd: subprocess.run(["sh", "-c", comando], input=self.entrada(repo, cmd), capture_output=True, text=True, cwd=str(self.inst))
        self.verifica_denegacion(corre("mysql -h db.externo.example -e 'SELECT 1'"))
        self.assertEqual(0, corre("ls").returncode)

    def test_lanzador_sin_python3_deniega_con_texto_en_stderr(self):
        repo = self.preparar()
        vacio = self.tmp / "vacio"
        vacio.mkdir()
        r = subprocess.run(["/bin/sh", str(self.inst / HOOKS / "lanzar.sh")], input=self.entrada(repo, "ls"), capture_output=True,
                           text=True, cwd=str(repo), env={"PATH": str(vacio)})
        self.assertEqual(2, r.returncode)
        self.assertIn("python3", r.stderr)

    def test_lanzador_sin_el_puente_deniega(self):
        repo = self.preparar()
        (self.inst / HOOKS / "guardia-datos.py").unlink()
        r = subprocess.run(["/bin/sh", str(self.inst / HOOKS / "lanzar.sh")], input=self.entrada(repo, "ls"), capture_output=True, text=True, cwd=str(repo))
        self.assertEqual(2, r.returncode)
        self.assertTrue(r.stderr.strip())


if __name__ == "__main__":
    unittest.main()
