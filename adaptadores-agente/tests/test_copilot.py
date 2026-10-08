"""Pruebas del adaptador de Copilot (VS Code Local, CLI y Agent Host; contenido exacto según copilot/FORMATO.md) y de los hooks ejecutados de verdad."""
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
HOOKS = ".github/harness-hooks"
VSCODE = ".github/hooks/harness-vscode.json"
CLI = ".github/hooks/harness-cli.json"


def tearDownModule():
    shutil.rmtree(BASE_TMP, True)


class Base(unittest.TestCase):
    agente = "copilot"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mh-cp-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.inst = comun.copiar_instancia(BASE_INST, self.tmp)

    def correr(self, aplicar=False, agente=None):
        agente = agente or self.agente
        return ga.planificar(self.inst, [agente], ga.SistemaSimulado(), aplicar)["agentes"][agente]

    def leer(self, rel):
        return json.loads((self.inst / rel).read_text(encoding="utf8"))


class TestArchivos(Base):
    def test_vscode_local_json_exacto_sin_version_ni_matcher(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr(aplicar=True)
        doc = self.leer(VSCODE)
        self.assertEqual(["hooks"], list(doc))                                  # sin `version` en el arnés Local
        self.assertEqual(["PreToolUse"], list(doc["hooks"]))                    # PascalCase
        (h,) = doc["hooks"]["PreToolUse"]
        self.assertEqual({"type", "command", "timeout"}, set(h))                # `matcher` se ignora en Local: no se escribe
        self.assertEqual(("command", 30), (h["type"], h["timeout"]))
        self.assertIn('"$d/.github/harness-hooks/lanzar-vscode.sh"', h["command"])
        self.assertTrue(h["command"].endswith("# " + fn.MARCA))
        self.assertIn(VSCODE, [a["ruta"] for a in inf["archivos"]])

    def test_cli_json_exacto_con_version_bash_y_timeoutsec(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        doc = self.leer(CLI)
        self.assertEqual(["version", "hooks"], list(doc))
        self.assertEqual(1, doc["version"])
        self.assertEqual(["preToolUse"], list(doc["hooks"]))                    # camelCase
        (h,) = doc["hooks"]["preToolUse"]
        self.assertEqual({"type", "bash", "timeoutSec"}, set(h))
        self.assertEqual(("command", 30), (h["type"], h["timeoutSec"]))
        self.assertIn('"$d/.github/harness-hooks/lanzar-cli.sh"', h["bash"])
        self.assertTrue(h["bash"].endswith("# " + fn.MARCA))
        self.assertNotIn("command", h)

    def test_por_defecto_genera_ambos_y_scripts_fuera_de_hooks(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        for n in ("block-db-access.sh", "guardia-datos.py", "lanzar-vscode.sh", "lanzar-cli.sh"):
            p = self.inst / HOOKS / n
            self.assertTrue(p.stat().st_mode & 0o100, n)
            self.assertTrue(fn.es_generado(p.read_text(encoding="utf8")), n)
        self.assertEqual(["harness-cli.json", "harness-vscode.json"], sorted(p.name for p in (self.inst / ".github" / "hooks").iterdir()))
        self.assertIn("--formato copilot-local", (self.inst / HOOKS / "lanzar-vscode.sh").read_text(encoding="utf8"))
        self.assertIn("--formato copilot-cli", (self.inst / HOOKS / "lanzar-cli.sh").read_text(encoding="utf8"))
        for n in (VSCODE, CLI):
            self.assertTrue(fn.es_generado((self.inst / n).read_text(encoding="utf8")), n)

    def test_variantes_por_superficie(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr(aplicar=True, agente="copilot-vscode")
        self.assertTrue((self.inst / VSCODE).exists())
        self.assertFalse((self.inst / CLI).exists())
        self.assertFalse((self.inst / HOOKS / "lanzar-cli.sh").exists())
        self.assertIn("solo el hook de VS Code", " ".join(inf["pasos_para_la_persona"]))
        shutil.rmtree(self.inst / ".github")
        inf = self.correr(aplicar=True, agente="copilot-cli")
        self.assertTrue((self.inst / CLI).exists())
        self.assertFalse((self.inst / VSCODE).exists())
        self.assertFalse((self.inst / HOOKS / "lanzar-vscode.sh").exists())
        self.assertIn("solo el hook de Copilot CLI", " ".join(inf["pasos_para_la_persona"]))

    def test_dice_que_superficies_son_y_como_elegir(self):
        comun.habilitar_hooks(self.inst)
        pasos = " ".join(self.correr()["pasos_para_la_persona"])
        for clave in ("ELIGE LA SUPERFICIE", "Preview", "Agent Host", "--agentes copilot-vscode", "--agentes copilot-cli", "dos veces"):
            self.assertIn(clave, pasos, clave)

    def test_pasos_deny_tool_y_autoapprove_no_es_control_y_nada_global(self):
        comun.habilitar_hooks(self.inst)
        pasos = " ".join(self.correr(aplicar=True)["pasos_para_la_persona"])
        for clave in ("--deny-tool='shell(", "--allow-all", "autoApprove", "NO bloquea", "no se escribe", "Workspace Trust", "carga útil"):
            self.assertIn(clave, pasos, clave)
        self.assertFalse((self.inst / ".vscode").exists())

    def test_control_por_hook_siempre_degradado_aunque_haya_hook(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr()
        self.assertEqual("degradado", inf["control_por_hook"])
        for clave in ("Preview", "FALLA ABIERTO", "TIEMPO AGOTADO", "capa de aviso"):
            self.assertIn(clave, inf["control_por_hook_motivo"], clave)

    def test_sin_ambientes_hook_degradado_sin_archivos_de_hook(self):
        inf = self.correr(aplicar=True)
        self.assertEqual("degradado", inf["control_por_hook"])
        self.assertIn("ningun ambiente", inf["control_por_hook_motivo"])
        self.assertFalse((self.inst / ".github" / "hooks").exists())
        self.assertFalse((self.inst / ".github" / "harness-hooks").exists())
        self.assertTrue((self.inst / "AGENTS.md").exists())
        self.assertTrue(any("no se generó" in d["que_se_pierde"] for d in inf["degradaciones"]))

    def test_idempotente(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        h = arbol_hash(self.inst)
        inf = self.correr(aplicar=True)
        self.assertEqual(h, arbol_hash(self.inst))
        self.assertTrue(all(a["accion"] == "igual" for a in inf["archivos"]))

    def test_plan_no_escribe(self):
        comun.habilitar_hooks(self.inst)
        antes = arbol_hash(self.tmp)
        inf = self.correr(aplicar=False)
        self.assertEqual(antes, arbol_hash(self.tmp))
        self.assertIn(CLI, [a["ruta"] for a in inf["archivos"]])

    def test_no_pisa_hooks_manuales(self):
        comun.habilitar_hooks(self.inst)
        (self.inst / ".github" / "hooks").mkdir(parents=True)
        (self.inst / VSCODE).write_text('{"hooks": {}}\n', encoding="utf8")
        (self.inst / CLI).write_text('{"version": 1, "hooks": {}}\n', encoding="utf8")
        inf = self.correr(aplicar=True)
        self.assertEqual('{"hooks": {}}\n', (self.inst / VSCODE).read_text(encoding="utf8"))
        self.assertEqual('{"version": 1, "hooks": {}}\n', (self.inst / CLI).read_text(encoding="utf8"))
        self.assertTrue((self.inst / ".github" / "hooks" / "harness-vscode.generado.json").exists())
        self.assertTrue((self.inst / ".github" / "hooks" / "harness-cli.generado.json").exists())
        self.assertEqual(2, sum("escrito a mano" in a for a in inf["avisos"]))

    def test_solo_escribe_dentro_de_la_instancia(self):
        comun.habilitar_hooks(self.inst)
        otros = arbol_hash(comun.RAIZ / "adaptadores-agente")
        inf = self.correr(aplicar=True)
        self.assertEqual(otros, arbol_hash(comun.RAIZ / "adaptadores-agente"))
        self.assertTrue(all(not a["ruta"].startswith(("/", "..", "~")) for a in inf["archivos"]))

    def test_no_duplica_instrucciones_ni_genera_el_resto(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        gh = self.inst / ".github"
        for n in ("copilot-instructions.md", "instructions", "prompts", "agents"):
            self.assertFalse((gh / n).exists(), n)
        for n in (".vscode", ".mcp.json", ".copilot"):
            self.assertFalse((self.inst / n).exists(), n)
        self.assertTrue((self.inst / "AGENTS.md").exists())
        self.assertNotIn("autoApprove", " ".join(p.read_text(encoding="utf8") for p in gh.rglob("*") if p.is_file()))

    def test_deteccion_solo_del_adaptador_principal(self):
        ga.cargar_adaptadores()
        sis = ga.SistemaSimulado(comandos=["copilot"])
        self.assertTrue(ga.REGISTRO["copilot"]().detectar(sis)["detectado"])
        self.assertFalse(ga.REGISTRO["copilot-vscode"]().detectar(sis)["detectado"])
        self.assertFalse(ga.REGISTRO["copilot-cli"]().detectar(sis)["detectado"])
        self.assertEqual(["copilot"], ga.planificar(self.inst, None, sis)["seleccionados"])


class TestCapacidades(Base):
    def test_capacidades_coherentes_con_el_formato(self):
        c = self.correr()["capacidades"]
        self.assertEqual("parcial", c["Hooks que bloquean"]["estado"])          # Preview en VS Code
        self.assertTrue(c["Hooks que bloquean"]["generado_por_este_adaptador"])
        self.assertTrue(c["Instrucciones del proyecto"]["generado_por_este_adaptador"])
        self.assertIn("copilot-instructions.md", c["Instrucciones del proyecto"]["nota"])
        self.assertFalse(c["Reglas por ruta"]["generado_por_este_adaptador"])
        self.assertIn("NO bloquea", c["Permisos / modos / sandbox"]["nota"])
        for cap in ("Skills", "MCP", "Comandos propios"):
            self.assertTrue(c[cap]["generado_por_este_adaptador"], cap)
        for cap in ("Subagentes / paralelo", "Plugins"):
            self.assertFalse(c[cap]["generado_por_este_adaptador"], cap)
        self.assertIn("disable-model-invocation", c["Comandos propios"]["nota"])

    def test_las_variantes_comparten_codigo_de_matriz(self):
        ga.cargar_adaptadores()
        for n in ("copilot", "copilot-vscode", "copilot-cli"):
            self.assertEqual("CP", ga.REGISTRO[n].codigo_matriz)

    def test_degradaciones_dicen_lo_que_el_formato_confirma(self):
        comun.habilitar_hooks(self.inst)
        d = self.correr()["degradaciones"]
        todo = " ".join(x["que_se_pierde"] + " " + x["imposicion_alternativa"] for x in d)
        for clave in ("Preview", "matcher", "ABIERTO", "TIEMPO AGOTADO", "tres superficies", "--deny-tool", "autoApprove", "NO bloquea", "ask",
                      "powershell", "sandbox", "solo lectura", "integración continua", "protección de ramas", "copilot -p", "duplicar"):
            self.assertIn(clave, todo, clave)
        self.assertTrue(all(x["fuente"] and x["imposicion_alternativa"] for x in d))


# ----------------------------------------------------------------------------- skills, comandos, permisos y MCP
import importlib.util

import fixtures_cap as F

_espec = importlib.util.spec_from_file_location("adaptador_copilot", comun.RAIZ / "adaptadores-agente" / "copilot" / "adaptador.py")
adaptador = importlib.util.module_from_spec(_espec)
_espec.loader.exec_module(adaptador)
SKILLS = ".github/skills"
MCP_VS = ".vscode/mcp.json"
MCP_CLI = ".mcp.json"


class TestCapacidadesCopilot(Base):
    def test_skills_en_github_skills_con_marca_y_contenido_neutral(self):
        self.correr(aplicar=True)
        skills = F.fuente_de(self.inst)["skills"]
        self.assertEqual(4, len(skills))
        for s in skills:
            t = F.leer(self.inst, f"{SKILLS}/{s['nombre']}/SKILL.md")
            self.assertTrue(t.startswith("---\nname: " + s["nombre"] + "\n"))
            self.assertTrue(fn.es_generado(t))
            self.assertEqual(s["contenido"], F.sin_marca_html(t).replace(f"# {fn.MARCA}\n", "", 1))
        self.assertFalse((self.inst / ".claude").exists())
        self.assertFalse((self.inst / ".agents").exists())

    def test_comandos_como_skill_de_invocacion_manual(self):
        inf = self.correr(aplicar=True)
        comandos = F.fuente_de(self.inst)["comandos"]
        self.assertEqual({"harness-estado", "harness-gate"}, {c["nombre"] for c in comandos})
        for c in comandos:
            t = F.leer(self.inst, f"{SKILLS}/{c['nombre']}/SKILL.md")
            cab = t.split("---\n")[1]
            self.assertEqual(f"name: {c['nombre']}\ndescription: {json.dumps(c['descripcion'], ensure_ascii=False)}\ndisable-model-invocation: true\n", cab)
            self.assertTrue(fn.es_generado(t))
            self.assertTrue(t.rstrip().endswith(c["contenido"].split("---\n", 2)[2].strip()))
        self.assertFalse((self.inst / ".github" / "prompts").exists())
        self.assertTrue(any("/harness-gate" in p for p in inf["pasos_para_la_persona"]))

    def test_comando_fuera_de_los_limites_de_skill_no_se_genera(self):
        c = {"nombre": "x" * 65, "descripcion": "d", "contenido": "---\ndescription: d\n---\ncuerpo\n"}
        texto, motivo = adaptador.comando_como_skill(c)
        self.assertIsNone(texto)
        self.assertIn("límites", motivo)

    def test_comando_con_el_nombre_de_una_skill_existente_no_se_genera(self):
        sk = F.fuente_de(self.inst)["skills"][0]["nombre"]
        fuente = F.fuente_de(self.inst)
        fuente["comandos"] = [{"nombre": sk, "descripcion": "d", "contenido": "---\ndescription: d\n---\ncuerpo\n"}]
        a = adaptador.Copilot()
        a.generar(fuente, self.inst)
        self.assertEqual([sk], a.comandos_omitidos)

    def test_permisos_solo_paso_deny_tool_literal_y_nada_escrito(self):
        F.anexar(self.inst, F.POL_DENY)
        inf = self.correr(aplicar=True)
        paso = [p for p in inf["pasos_para_la_persona"] if "--deny-tool=" in p]
        self.assertEqual(1, len(paso))
        banderas = [l for l in paso[0].splitlines() if l.startswith("copilot ")][0]
        for esperado in ("--deny-tool='shell(terraform destroy)'", "--deny-tool='shell(kubectl delete)'", "--deny-tool='shell(shred)'"):
            self.assertIn(esperado, banderas)
        for ancho in ("shell(git)'", "shell(terraform)'", "shell(kubectl)'", "shell(*)'"):
            self.assertNotIn(ancho, banderas)
        self.assertNotIn("git commit", banderas)                                    # `ask` es el comportamiento por defecto: sin bandera
        self.assertIn("allow", paso[0])
        deg = " ".join(d["que_se_pierde"] for d in inf["degradaciones"])
        for regla in ("migraciones", "semillas", "CLI del ORM", "comandos.instalar", "push_a_rama_protegida"):
            self.assertIn(regla, deg)
        self.assertFalse((self.inst / ".copilot").exists())

    def test_mcp_permitida_por_superficie_con_type_distinto_y_sin_variables(self):
        F.anexar(self.inst, F.POL_MCP)
        os.environ["DOCS_VAR"] = "valor-secreto-que-no-debe-aparecer"
        self.addCleanup(os.environ.pop, "DOCS_VAR", None)
        inf = self.correr(aplicar=True)
        vs, cli = F.leer(self.inst, MCP_VS), F.leer(self.inst, MCP_CLI)
        self.assertNotIn("valor-secreto", vs + cli)
        self.assertEqual({"_generado_por_el_harness": fn.MARCA, "servers": {"web": {"type": "http", "url": "https://mcp.example.com/web"}}}, json.loads(vs))
        self.assertEqual({"_generado_por_el_harness": fn.MARCA, "mcpServers": {"web": {"type": "http", "url": "https://mcp.example.com/web", "tools": ["*"]}}}, json.loads(cli))
        self.assertTrue(any("docs" in a and "no está confirmada" in a for a in inf["avisos"]))   # lleva `entorno`: no se traduce
        self.assertNotIn("vetado", vs + cli)

    def test_mcp_local_usa_stdio_en_vscode_y_local_en_la_cli(self):
        F.anexar(self.inst, '[[mcp.servidores]]\nnombre = "loc"\ncomando = "npx"\nargs = ["-y", "p"]\nregistrar = "permitida"\n')
        self.correr(aplicar=True)
        self.assertEqual({"loc": {"type": "stdio", "command": "npx", "args": ["-y", "p"]}}, F.leer_json(self.inst, MCP_VS)["servers"])
        self.assertEqual({"loc": {"type": "local", "command": "npx", "args": ["-y", "p"], "tools": ["*"]}}, F.leer_json(self.inst, MCP_CLI)["mcpServers"])

    def test_mcp_variantes_escriben_solo_su_archivo(self):
        F.anexar(self.inst, F.POL_MCP)
        self.correr(aplicar=True, agente="copilot-vscode")
        self.assertTrue((self.inst / MCP_VS).exists())
        self.assertFalse((self.inst / MCP_CLI).exists())
        shutil.rmtree(self.inst / ".vscode")
        self.correr(aplicar=True, agente="copilot-cli")
        self.assertTrue((self.inst / MCP_CLI).exists())
        self.assertFalse((self.inst / MCP_VS).exists())

    def test_mcp_confirmar_no_escribe_e_imprime_el_fragmento(self):
        F.anexar(self.inst, F.POL_MCP_CONFIRMAR)
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / MCP_VS).exists())
        self.assertFalse((self.inst / MCP_CLI).exists())
        pasos = [p for p in inf["pasos_para_la_persona"] if "buscador" in p]
        self.assertEqual(2, len(pasos))
        self.assertTrue(any(json.dumps({"servers": {"buscador": {"type": "http", "url": "https://mcp.example.com/mcp"}}}, ensure_ascii=False, indent=2) in p for p in pasos))
        self.assertTrue(any(json.dumps({"mcpServers": {"buscador": {"type": "http", "url": "https://mcp.example.com/mcp", "tools": ["*"]}}}, ensure_ascii=False, indent=2) in p for p in pasos))

    def test_mcp_prohibida_y_sin_servidores_no_escriben_nada(self):
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / MCP_VS).exists())
        self.assertFalse((self.inst / MCP_CLI).exists())
        self.assertFalse(any("MCP" in p for p in inf["pasos_para_la_persona"]))
        F.anexar(self.inst, '[[mcp.servidores]]\nnombre = "vetado"\ncomando = "otro"\nregistrar = "prohibida"\n')
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / MCP_CLI).exists())
        self.assertTrue(any("vetado" in a for a in inf["avisos"]))

    def test_manual_no_se_pisa_mcp_ni_skill(self):
        F.anexar(self.inst, F.POL_MCP)
        (self.inst / MCP_CLI).write_text('{"mcpServers": {"mio": {"command": "y"}}}\n', encoding="utf8")
        d = self.inst / SKILLS / "sdd-verificar"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: sdd-verificar\ndescription: mía\n---\nmanual\n", encoding="utf8")
        (self.inst / SKILLS / "harness-gate").mkdir()
        (self.inst / SKILLS / "harness-gate" / "SKILL.md").write_text("mío\n", encoding="utf8")
        inf = self.correr(aplicar=True)
        self.assertEqual('{"mcpServers": {"mio": {"command": "y"}}}\n', F.leer(self.inst, MCP_CLI))
        self.assertIn("web", F.leer(self.inst, ".mcp.generado.json"))
        self.assertIn("manual", F.leer(self.inst, f"{SKILLS}/sdd-verificar/SKILL.md"))
        self.assertTrue((d / "SKILL.generado.md").exists())
        self.assertEqual("mío\n", F.leer(self.inst, f"{SKILLS}/harness-gate/SKILL.md"))
        self.assertTrue((self.inst / SKILLS / "harness-gate" / "SKILL.generado.md").exists())

    def test_idempotente_con_todo_y_solo_dentro_de_la_instancia(self):
        comun.habilitar_hooks(self.inst)
        F.anexar(self.inst, F.POL_DENY + F.POL_MCP)
        otros = arbol_hash(comun.RAIZ / "adaptadores-agente")
        self.correr(aplicar=True)
        h = arbol_hash(self.inst)
        inf = self.correr(aplicar=True)
        self.assertEqual(h, arbol_hash(self.inst))
        self.assertTrue(all(a["accion"] == "igual" for a in inf["archivos"]), [a for a in inf["archivos"] if a["accion"] != "igual"])
        self.assertEqual(otros, arbol_hash(comun.RAIZ / "adaptadores-agente"))
        self.assertTrue(all(not a["ruta"].startswith(("/", "..", "~")) for a in inf["archivos"]))

    def test_plan_no_escribe(self):
        F.anexar(self.inst, F.POL_MCP)
        antes = arbol_hash(self.tmp)
        inf = self.correr(aplicar=False)
        self.assertEqual(antes, arbol_hash(self.tmp))
        rutas = [a["ruta"] for a in inf["archivos"]]
        for r in (MCP_VS, MCP_CLI, f"{SKILLS}/harness-gate/SKILL.md"):
            self.assertIn(r, rutas)


@unittest.skipUnless(shutil.which("jq") and shutil.which("git") and shutil.which("bash"), "faltan jq, git o bash")
class TestHookEjecutado(Base):
    """Ejecuta los scripts reales con la entrada documentada de cada superficie."""
    FORMATOS = ("copilot-local", "copilot-cli")

    def preparar(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        repo = self.tmp / "servicio-demo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / ".github").mkdir()
        os.symlink(self.inst / HOOKS, repo / HOOKS)
        return repo

    def entrada(self, formato, repo, comando, otra=False, args_como_texto=False):
        if formato == "copilot-local":
            return json.dumps({"timestamp": "2026-01-01T00:00:00Z", "cwd": str(repo), "session_id": "s", "hook_event_name": "PreToolUse",
                               "transcript_path": "/t", "tool_name": "read_file" if otra else "run_in_terminal",
                               "tool_input": {"filePath": "a.py"} if otra else {"command": comando}, "tool_use_id": "tool-123"})
        args = {"path": "a.py"} if otra else {"command": comando}
        return json.dumps({"sessionId": "s", "timestamp": 1767225600000, "cwd": str(repo), "toolName": "view" if otra else "bash",
                           "toolArgs": json.dumps(args) if args_como_texto else args})

    def puente(self, formato, entrada, repo, env=None):
        return subprocess.run([sys.executable, str(self.inst / HOOKS / "guardia-datos.py"), "--formato", formato], input=entrada,
                              capture_output=True, text=True, cwd=str(repo), env=env)

    def deniega(self, formato, r):
        self.assertEqual(2, r.returncode, r.stdout + r.stderr)
        self.assertTrue(r.stderr.strip())                                   # Local: «stderr como error bloqueante»
        v = json.loads(r.stdout)                                            # y además la decisión en JSON documentada
        if formato == "copilot-local":
            h = v["hookSpecificOutput"]
            self.assertEqual(("PreToolUse", "deny"), (h["hookEventName"], h["permissionDecision"]))
            self.assertTrue(h["permissionDecisionReason"])
        else:
            self.assertEqual("deny", v["permissionDecision"])
            self.assertTrue(v["permissionDecisionReason"])                  # «Required when decision is deny»

    def permite(self, r):
        self.assertEqual((0, "", ""), (r.returncode, r.stdout.strip(), r.stderr.strip()))

    def test_deniega_host_remoto_y_ddl_local_y_permite_ls(self):
        repo = self.preparar()
        for f in self.FORMATOS:
            with self.subTest(f):
                r = self.puente(f, self.entrada(f, repo, "mysql -h db.externo.example -e 'SELECT 1'"), repo)
                self.deniega(f, r)
                self.assertIn("Bloqueado", r.stderr)
                self.deniega(f, self.puente(f, self.entrada(f, repo, "mysql -h localhost -e 'DROP TABLE clientes'"), repo))
                self.permite(self.puente(f, self.entrada(f, repo, "ls -la"), repo))

    def test_cli_acepta_toolargs_como_texto_json(self):
        repo = self.preparar()
        self.deniega("copilot-cli", self.puente("copilot-cli", self.entrada("copilot-cli", repo, "mysql -h db.externo.example -e 'SELECT 1'", args_como_texto=True), repo))
        self.permite(self.puente("copilot-cli", self.entrada("copilot-cli", repo, "ls", args_como_texto=True), repo))

    def test_cli_tambien_juzga_powershell(self):
        repo = self.preparar()
        e = json.loads(self.entrada("copilot-cli", repo, "mysql -h db.externo.example -e 'SELECT 1'"))
        e["toolName"] = "powershell"
        self.deniega("copilot-cli", self.puente("copilot-cli", json.dumps(e), repo))

    def test_otras_herramientas_no_las_juzga(self):
        repo = self.preparar()
        for f in self.FORMATOS:
            with self.subTest(f):
                self.permite(self.puente(f, self.entrada(f, repo, "x", otra=True), repo))

    def test_local_filtra_el_script_porque_matcher_se_ignora(self):
        repo = self.preparar()
        e = json.loads(self.entrada("copilot-local", repo, "x", otra=True))
        e["hook_event_name"] = "PreToolUse"
        self.permite(self.puente("copilot-local", json.dumps(e), repo))        # una herramienta sin comando pasa por el script y se permite
        self.assertNotIn("matcher", self.leer(VSCODE)["hooks"]["PreToolUse"][0])

    def test_entrada_ilegible_o_incompleta_deniega_con_2(self):
        repo = self.preparar()
        malos = {"copilot-local": ["no es json", "", "[]", json.dumps({"tool_name": "run_in_terminal", "tool_input": {}}),
                                   json.dumps({"tool_name": "bash", "tool_input": {"command": ["ls"]}})],
                 "copilot-cli": ["no es json", "", "[]", json.dumps({"toolName": "bash", "toolArgs": {}}),
                                 json.dumps({"toolName": "bash", "toolArgs": "no es json"}),
                                 json.dumps({"toolName": "bash", "toolArgs": {"command": ["ls"]}})]}
        for f, lista in malos.items():
            for malo in lista:
                with self.subTest(f, malo=malo):
                    self.deniega(f, self.puente(f, malo, repo))

    def test_sin_jq_deniega(self):
        repo = self.preparar()
        sin_jq = self.tmp / "bin"
        sin_jq.mkdir()
        for n in ("bash", "git"):
            os.symlink(shutil.which(n), sin_jq / n)
        for f in self.FORMATOS:
            with self.subTest(f):
                r = self.puente(f, self.entrada(f, repo, "ls"), repo, env={"PATH": str(sin_jq)})
                self.deniega(f, r)
                self.assertIn("jq", r.stderr)

    def test_fallo_del_hook_de_politica_deniega(self):
        repo = self.preparar()
        (self.inst / HOOKS / "block-db-access.sh").unlink()
        for f in self.FORMATOS:
            with self.subTest(f):
                self.deniega(f, self.puente(f, self.entrada(f, repo, "ls"), repo))

    def corre_comando_registrado(self, formato, repo, comando):
        if formato == "copilot-local":
            cmd = self.leer(VSCODE)["hooks"]["PreToolUse"][0]["command"]
        else:
            cmd = self.leer(CLI)["hooks"]["preToolUse"][0]["bash"]
        return subprocess.run(["bash", "-c", cmd], input=self.entrada(formato, repo, comando), capture_output=True, text=True, cwd=str(repo))

    def test_el_comando_registrado_funciona_tal_cual(self):
        repo = self.preparar()
        for f in self.FORMATOS:
            with self.subTest(f):
                self.deniega(f, self.corre_comando_registrado(f, repo, "mysql -h db.externo.example -e 'SELECT 1'"))
                self.permite(self.corre_comando_registrado(f, repo, "ls"))

    def test_comando_registrado_sin_el_lanzador_deniega_el_mismo(self):
        repo = self.preparar()
        (self.inst / HOOKS / "lanzar-vscode.sh").unlink()
        (self.inst / HOOKS / "lanzar-cli.sh").unlink()
        for f in self.FORMATOS:
            with self.subTest(f):
                r = self.corre_comando_registrado(f, repo, "ls")
                self.assertEqual(2, r.returncode)
                self.assertIn("lanzador", r.stderr)

    def test_lanzador_sin_python3_deniega_con_2(self):
        repo = self.preparar()
        vacio = self.tmp / "vacio"
        vacio.mkdir()
        for variante, f in (("vscode", "copilot-local"), ("cli", "copilot-cli")):
            with self.subTest(f):
                r = subprocess.run(["/bin/sh", str(self.inst / HOOKS / f"lanzar-{variante}.sh")], input=self.entrada(f, repo, "ls"),
                                   capture_output=True, text=True, cwd=str(repo), env={"PATH": str(vacio)})
                self.assertEqual(2, r.returncode)
                self.assertIn("python3", r.stderr)

    def test_lanzador_sin_el_puente_deniega(self):
        repo = self.preparar()
        (self.inst / HOOKS / "guardia-datos.py").unlink()
        for variante, f in (("vscode", "copilot-local"), ("cli", "copilot-cli")):
            with self.subTest(f):
                r = subprocess.run(["/bin/sh", str(self.inst / HOOKS / f"lanzar-{variante}.sh")], input=self.entrada(f, repo, "ls"),
                                   capture_output=True, text=True, cwd=str(repo))
                self.assertEqual(2, r.returncode)


if __name__ == "__main__":
    unittest.main()
