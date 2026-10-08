"""Pruebas del adaptador de Windsurf (Cascade y Devin Local; contenido exacto según windsurf/FORMATO.md) y de los hooks ejecutados de verdad."""
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
HOOKS = ".devin/hooks"
CASCADE = ".devin/hooks.json"
DEVIN = ".devin/hooks.v1.json"


def tearDownModule():
    shutil.rmtree(BASE_TMP, True)


class Base(unittest.TestCase):
    agente = "windsurf"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mh-ws-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.inst = comun.copiar_instancia(BASE_INST, self.tmp)

    def correr(self, aplicar=False, agente=None):
        agente = agente or self.agente
        return ga.planificar(self.inst, [agente], ga.SistemaSimulado(), aplicar)["agentes"][agente]

    def leer(self, rel):
        return json.loads((self.inst / rel).read_text(encoding="utf8"))


class TestArchivos(Base):
    def test_cascade_json_exacto(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr(aplicar=True)
        doc = self.leer(CASCADE)
        self.assertEqual(["hooks"], list(doc))
        self.assertEqual(["pre_run_command"], list(doc["hooks"]))              # solo los `pre_*` bloquean; este es el del shell
        (h,) = doc["hooks"]["pre_run_command"]
        self.assertEqual({"command", "show_output"}, set(h))
        self.assertIs(True, h["show_output"])
        self.assertIn('"$d/.devin/hooks/lanzar-cascade.sh"', h["command"])
        self.assertIn("git rev-parse --show-toplevel", h["command"])
        self.assertTrue(h["command"].endswith("# " + fn.MARCA))
        self.assertIn(CASCADE, [a["ruta"] for a in inf["archivos"]])

    def test_devin_local_json_exacto_sin_clave_envoltorio(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        doc = self.leer(DEVIN)
        self.assertEqual(["PreToolUse"], list(doc))                            # el objeto de hooks ES el archivo entero
        (grupo,) = doc["PreToolUse"]
        self.assertEqual({"matcher", "hooks"}, set(grupo))
        self.assertEqual("^exec$", grupo["matcher"])
        (h,) = grupo["hooks"]
        self.assertEqual({"type", "command", "timeout"}, set(h))
        self.assertEqual(("command", 30), (h["type"], h["timeout"]))
        self.assertIn('"$d/.devin/hooks/lanzar-devin-local.sh"', h["command"])
        self.assertTrue(h["command"].endswith("# " + fn.MARCA))

    def test_por_defecto_genera_ambos_y_scripts_compartidos(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        for n in ("block-db-access.sh", "guardia-datos.py", "lanzar-cascade.sh", "lanzar-devin-local.sh"):
            p = self.inst / HOOKS / n
            self.assertTrue(p.stat().st_mode & 0o100, n)
            self.assertTrue(fn.es_generado(p.read_text(encoding="utf8")), n)
        self.assertFalse((self.inst / HOOKS / "lanzar.sh").exists())
        self.assertIn("--formato windsurf-cascade", (self.inst / HOOKS / "lanzar-cascade.sh").read_text(encoding="utf8"))
        self.assertIn("--formato windsurf-devin", (self.inst / HOOKS / "lanzar-devin-local.sh").read_text(encoding="utf8"))
        for n in (CASCADE, DEVIN):
            self.assertTrue(fn.es_generado((self.inst / n).read_text(encoding="utf8")), n)

    def test_variante_cascade_no_escribe_lo_de_devin_local(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr(aplicar=True, agente="windsurf-cascade")
        self.assertTrue((self.inst / CASCADE).exists())
        self.assertFalse((self.inst / DEVIN).exists())
        self.assertFalse((self.inst / HOOKS / "lanzar-devin-local.sh").exists())
        pasos = " ".join(inf["pasos_para_la_persona"])
        self.assertIn("solo el hook de Cascade", pasos)
        self.assertNotIn("permissions", pasos)                                  # `permissions.deny` es solo de Devin Local

    def test_variante_devin_local_no_escribe_lo_de_cascade(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr(aplicar=True, agente="windsurf-devin-local")
        self.assertTrue((self.inst / DEVIN).exists())
        self.assertFalse((self.inst / CASCADE).exists())
        self.assertFalse((self.inst / HOOKS / "lanzar-cascade.sh").exists())
        self.assertIn("solo el hook de Devin Local", " ".join(inf["pasos_para_la_persona"]))

    def test_dice_cual_usa_la_persona_y_como_elegir(self):
        comun.habilitar_hooks(self.inst)
        pasos = " ".join(self.correr()["pasos_para_la_persona"])
        for clave in ("ELIGE EL AGENTE", "cada agente solo lee el suyo", "Devin Local", "Cascade", "--agentes windsurf-devin-local", "--agentes windsurf-cascade"):
            self.assertIn(clave, pasos, clave)

    def test_pasos_permisos_deny_de_devin_local_y_nada_global(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr(aplicar=True)
        pasos = " ".join(inf["pasos_para_la_persona"])
        for clave in ("permissions", "deny", "Exec(", ".devin/config.json", "no se escribe", "/hooks", "Restricted Mode"):
            self.assertIn(clave, pasos, clave)
        self.assertEqual({"ask": ["Exec(git commit)", "Exec(git push)"]}, self.leer(".devin/config.json")["permissions"])

    def test_control_por_hook_siempre_degradado_aunque_haya_hook(self):
        comun.habilitar_hooks(self.inst)
        inf = self.correr()
        self.assertEqual("degradado", inf["control_por_hook"])
        self.assertIn("FALLA ABIERTO", inf["control_por_hook_motivo"])
        self.assertIn("capa de aviso", inf["control_por_hook_motivo"])
        self.assertNotEqual("disponible", inf["control_por_hook"])

    def test_sin_ambientes_hook_degradado_sin_archivos_de_hook(self):
        inf = self.correr(aplicar=True)
        self.assertEqual("degradado", inf["control_por_hook"])
        self.assertIn("ningun ambiente", inf["control_por_hook_motivo"])
        self.assertFalse((self.inst / HOOKS).exists())
        self.assertFalse((self.inst / CASCADE).exists())
        self.assertFalse((self.inst / DEVIN).exists())
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
        self.assertIn(CASCADE, [a["ruta"] for a in inf["archivos"]])

    def test_no_pisa_hooks_manuales(self):
        comun.habilitar_hooks(self.inst)
        (self.inst / ".devin").mkdir()
        (self.inst / CASCADE).write_text('{"hooks": {}}\n', encoding="utf8")
        (self.inst / DEVIN).write_text('{"Stop": []}\n', encoding="utf8")
        inf = self.correr(aplicar=True)
        self.assertEqual('{"hooks": {}}\n', (self.inst / CASCADE).read_text(encoding="utf8"))
        self.assertEqual('{"Stop": []}\n', (self.inst / DEVIN).read_text(encoding="utf8"))
        self.assertTrue((self.inst / ".devin" / "hooks.generado.json").exists())
        self.assertTrue((self.inst / ".devin" / "hooks.v1.generado.json").exists())
        self.assertEqual(2, sum("escrito a mano" in a for a in inf["avisos"]))

    def test_solo_escribe_dentro_de_la_instancia(self):
        comun.habilitar_hooks(self.inst)
        otros = arbol_hash(comun.RAIZ / "adaptadores-agente")
        inf = self.correr(aplicar=True)
        self.assertEqual(otros, arbol_hash(comun.RAIZ / "adaptadores-agente"))
        self.assertTrue(all(not a["ruta"].startswith(("/", "..", "~")) for a in inf["archivos"]))

    def test_no_duplica_agents_md_ni_genera_reglas_workflows_mcp_sin_servidores_ni_subagentes(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        for n in ("rules", "agents", "workflows", "mcp_config.json"):
            self.assertFalse((self.inst / ".devin" / n).exists(), n)
        self.assertFalse((self.inst / ".windsurf").exists())
        self.assertFalse((self.inst / ".devinignore").exists())
        self.assertTrue((self.inst / "AGENTS.md").exists())

    def test_deteccion_solo_del_adaptador_principal(self):
        ga.cargar_adaptadores()
        sis = ga.SistemaSimulado(comandos=["devin"])
        self.assertTrue(ga.REGISTRO["windsurf"]().detectar(sis)["detectado"])
        self.assertFalse(ga.REGISTRO["windsurf-cascade"]().detectar(sis)["detectado"])
        self.assertFalse(ga.REGISTRO["windsurf-devin-local"]().detectar(sis)["detectado"])
        inf = ga.planificar(self.inst, None, sis)
        self.assertEqual(["windsurf"], inf["seleccionados"])


class TestCapacidades(Base):
    def test_capacidades_coherentes_con_el_formato(self):
        c = self.correr()["capacidades"]
        self.assertEqual("si", c["Hooks que bloquean"]["estado"])
        self.assertTrue(c["Hooks que bloquean"]["generado_por_este_adaptador"])
        self.assertTrue(c["Instrucciones del proyecto"]["generado_por_este_adaptador"])
        self.assertIn("duplic", c["Instrucciones del proyecto"]["nota"] + c["Reglas por ruta"]["nota"])
        self.assertFalse(c["Reglas por ruta"]["generado_por_este_adaptador"])
        self.assertIn("AGENTS.md", c["Reglas por ruta"]["nota"])
        self.assertIn("deny", c["Permisos / modos / sandbox"]["nota"])
        self.assertIn("no bloquea", c["Permisos / modos / sandbox"]["nota"])
        for cap in ("Skills", "MCP", "Permisos / modos / sandbox"):
            self.assertTrue(c[cap]["generado_por_este_adaptador"], cap)
        for cap in ("Subagentes / paralelo", "Comandos propios", "Plugins"):
            self.assertFalse(c[cap]["generado_por_este_adaptador"], cap)
        self.assertIn("Devin Local", c["Comandos propios"]["nota"])

    def test_las_variantes_comparten_codigo_de_matriz(self):
        ga.cargar_adaptadores()
        for n in ("windsurf", "windsurf-cascade", "windsurf-devin-local"):
            self.assertEqual("WS", ga.REGISTRO[n].codigo_matriz)

    def test_degradaciones_dicen_lo_que_el_formato_confirma(self):
        comun.habilitar_hooks(self.inst)
        d = self.correr()["degradaciones"]
        todo = " ".join(x["que_se_pierde"] + " " + x["imposicion_alternativa"] for x in d)
        for clave in ("ABIERTO", "salida 2", "dos agentes", "pre_run_command", "exec", "NO bloquea", "permissions.deny", "Restricted Mode",
                      "ask", "powershell", "sandbox", "solo lectura", "integración continua", "protección de ramas", "devin -p"):
            self.assertIn(clave, todo, clave)
        self.assertTrue(all(x["fuente"] and x["imposicion_alternativa"] for x in d))


# ----------------------------------------------------------------------------- skills, comandos, permisos y MCP
import fixtures_cap as F

SKILLS = ".devin/skills"
CONFIG = ".devin/config.json"
MCP = ".devin/mcp_config.json"
MCP_GLOBAL = "~/.config/devin/mcp_config.json"


class TestCapacidadesWindsurf(Base):
    def test_skills_en_devin_skills_con_marca_para_ambas_variantes(self):
        for agente in ("windsurf", "windsurf-cascade", "windsurf-devin-local"):
            shutil.rmtree(self.inst / ".devin", True)
            self.correr(aplicar=True, agente=agente)
            skills = F.fuente_de(self.inst)["skills"]
            self.assertEqual(4, len(skills))
            for s in skills:
                t = F.leer(self.inst, f"{SKILLS}/{s['nombre']}/SKILL.md")
                self.assertTrue(t.startswith("---\nname: " + s["nombre"] + "\n"), agente)
                self.assertTrue(fn.es_generado(t))
                self.assertEqual(s["contenido"], F.sin_marca_html(t).replace(f"# {fn.MARCA}\n", "", 1))

    def test_comandos_no_se_generan_workflows_ni_nada(self):
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / ".devin" / "workflows").exists())
        self.assertFalse((self.inst / ".windsurf").exists())
        aviso = [a for a in inf["avisos"] if "Comandos no generados" in a]
        self.assertEqual(1, len(aviso))
        self.assertIn("harness-gate", aviso[0])
        self.assertTrue(any("Devin Local no los soporta" in d["que_se_pierde"] for d in inf["degradaciones"]))

    def test_permisos_devin_local_exec_con_prefijos_literales_y_deny_gana(self):
        F.anexar(self.inst, F.POL_DENY)
        inf = self.correr(aplicar=True, agente="windsurf-devin-local")
        doc = self.leer(CONFIG)
        self.assertEqual(fn.MARCA, doc["_generado_por_el_harness"])
        self.assertEqual({"deny": ["Exec(terraform destroy)", "Exec(kubectl delete)", "Exec(shred)"],
                          "ask": ["Exec(git commit)", "Exec(git push)"]}, doc["permissions"])
        todas = doc["permissions"]["deny"] + doc["permissions"]["ask"]
        for ancho in ("Exec(git)", "Exec(terraform)", "Exec(kubectl)", "Exec(*)", "Exec"):
            self.assertNotIn(ancho, todas)
        self.assertNotIn("allow", doc["permissions"])
        deg = " ".join(d["que_se_pierde"] for d in inf["degradaciones"])
        for regla in ("migraciones", "semillas", "CLI del ORM", "comandos.instalar", "push_a_rama_protegida"):
            self.assertIn(regla, deg)
        self.assertTrue(fn.es_generado(F.leer(self.inst, CONFIG)))

    def test_cascade_no_escribe_permisos_ni_los_vende_como_control(self):
        F.anexar(self.inst, F.POL_DENY)
        inf = self.correr(aplicar=True, agente="windsurf-cascade")
        self.assertFalse((self.inst / CONFIG).exists())
        pasos = " ".join(inf["pasos_para_la_persona"])
        self.assertIn("solo exige aprobación (no bloquea)", pasos)
        self.assertIn("no se genera ni se cuenta como control", pasos)

    def test_mcp_permitida_devin_local_con_env_referencia_y_nunca_valores(self):
        F.anexar(self.inst, F.POL_MCP)
        os.environ["DOCS_VAR"] = "valor-secreto-que-no-debe-aparecer"
        self.addCleanup(os.environ.pop, "DOCS_VAR", None)
        inf = self.correr(aplicar=True, agente="windsurf-devin-local")
        texto = F.leer(self.inst, MCP)
        self.assertNotIn("valor-secreto", texto)
        doc = json.loads(texto)
        self.assertEqual({"docs": {"command": "npx", "args": ["-y", "paquete-docs"], "env": {"DOCS_VAR": "${env:DOCS_VAR}"}},
                          "web": {"url": "https://mcp.example.com/web"}}, doc["mcpServers"])
        self.assertEqual(fn.MARCA, doc["_generado_por_el_harness"])
        self.assertNotIn("vetado", texto)
        self.assertTrue(any("vetado" in a and "prohíbe" in a for a in inf["avisos"]))
        paso = [p for p in inf["pasos_para_la_persona"] if "buscador" in p]
        self.assertEqual(1, len(paso))                                              # `confirmar`: solo se imprime
        self.assertNotIn("buscador", texto)

    def test_mcp_confirmar_no_escribe_e_imprime_el_fragmento(self):
        F.anexar(self.inst, F.POL_MCP_CONFIRMAR)
        inf = self.correr(aplicar=True, agente="windsurf-devin-local")
        self.assertFalse((self.inst / MCP).exists())
        paso = [p for p in inf["pasos_para_la_persona"] if "buscador" in p]
        self.assertEqual(1, len(paso))
        self.assertIn(json.dumps({"mcpServers": {"buscador": {"url": "https://mcp.example.com/mcp"}}}, ensure_ascii=False, indent=2), paso[0])
        self.assertIn(MCP, paso[0])

    def test_mcp_cascade_es_global_solo_se_imprime_aunque_sea_permitida(self):
        F.anexar(self.inst, F.POL_MCP)
        inf = self.correr(aplicar=True, agente="windsurf-cascade")
        self.assertFalse((self.inst / MCP).exists())
        pasos = " ".join(inf["pasos_para_la_persona"])
        self.assertIn(MCP_GLOBAL, pasos)
        self.assertIn('"web"', pasos)

    def test_mcp_prohibida_y_sin_servidores_no_escriben_nada(self):
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / MCP).exists())
        self.assertFalse(any("MCP" in p for p in inf["pasos_para_la_persona"]))
        F.anexar(self.inst, '[[mcp.servidores]]\nnombre = "vetado"\ncomando = "otro"\nregistrar = "prohibida"\n')
        inf = self.correr(aplicar=True)
        self.assertFalse((self.inst / MCP).exists())
        self.assertFalse(any("vetado" in p for p in inf["pasos_para_la_persona"]))

    def test_manual_no_se_pisa_config_mcp_y_skill(self):
        F.anexar(self.inst, F.POL_DENY + F.POL_MCP)
        (self.inst / ".devin").mkdir()
        (self.inst / CONFIG).write_text('{"model": "x"}\n', encoding="utf8")
        (self.inst / MCP).write_text('{"mcpServers": {"mio": {"command": "y"}}}\n', encoding="utf8")
        d = self.inst / SKILLS / "sdd-verificar"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: sdd-verificar\ndescription: mía\n---\nmanual\n", encoding="utf8")
        inf = self.correr(aplicar=True, agente="windsurf-devin-local")
        self.assertEqual('{"model": "x"}\n', F.leer(self.inst, CONFIG))
        self.assertEqual('{"mcpServers": {"mio": {"command": "y"}}}\n', F.leer(self.inst, MCP))
        self.assertIn("permissions", F.leer(self.inst, ".devin/config.generado.json"))
        self.assertIn("docs", F.leer(self.inst, ".devin/mcp_config.generado.json"))
        self.assertIn("manual", F.leer(self.inst, f"{SKILLS}/sdd-verificar/SKILL.md"))
        self.assertTrue((d / "SKILL.generado.md").exists())
        self.assertEqual(2, sum("no se fusiona solo" in p for p in inf["pasos_para_la_persona"]))

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
        F.anexar(self.inst, F.POL_DENY + F.POL_MCP)
        antes = arbol_hash(self.tmp)
        inf = self.correr(aplicar=False)
        self.assertEqual(antes, arbol_hash(self.tmp))
        rutas = [a["ruta"] for a in inf["archivos"]]
        for r in (CONFIG, MCP, f"{SKILLS}/sdd-verificar/SKILL.md"):
            self.assertIn(r, rutas)


@unittest.skipUnless(shutil.which("jq") and shutil.which("git") and shutil.which("bash"), "faltan jq, git o bash")
class TestHookEjecutado(Base):
    """Ejecuta los scripts reales con la entrada documentada de cada agente."""

    def preparar(self):
        comun.habilitar_hooks(self.inst)
        self.correr(aplicar=True)
        repo = self.tmp / "servicio-demo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        os.symlink(self.inst / ".devin", repo / ".devin")        # la raíz git de `repo` encuentra `.devin/hooks/...`
        return repo

    def entrada(self, formato, repo, comando, otra=False):
        if formato == "windsurf-cascade":
            if otra:
                return json.dumps({"agent_action_name": "pre_read_code", "tool_info": {"file_path": str(repo / "a.py")}})
            return json.dumps({"agent_action_name": "pre_run_command", "trajectory_id": "t", "execution_id": "e", "timestamp": "2026-01-01T00:00:00Z",
                               "model_name": "m", "tool_info": {"command_line": comando, "cwd": str(repo)}})
        return json.dumps({"hook_event_name": "PreToolUse", "tool_name": "read" if otra else "exec",
                           "tool_input": {"file_path": "a.py"} if otra else {"command": comando}, "session_id": "s", "prompt_id": "p"})

    def puente(self, formato, entrada, repo, env=None):
        env = env if env is not None else dict(os.environ, DEVIN_PROJECT_DIR=str(repo))
        return subprocess.run([sys.executable, str(self.inst / HOOKS / "guardia-datos.py"), "--formato", formato], input=entrada,
                              capture_output=True, text=True, cwd=str(repo), env=env)

    def deniega(self, formato, r):
        self.assertEqual(2, r.returncode, r.stdout + r.stderr)             # solo la salida 2 bloquea
        self.assertTrue(r.stderr.strip())                                  # Cascade: el agente ve stderr
        if formato == "windsurf-devin":
            v = json.loads(r.stdout)
            self.assertEqual("block", v["decision"])
            self.assertTrue(v["reason"])
        else:
            self.assertEqual("", r.stdout.strip())                         # Cascade no tiene respuesta JSON de decisión

    def permite(self, r):
        self.assertEqual((0, "", ""), (r.returncode, r.stdout.strip(), r.stderr.strip()))

    FORMATOS = ("windsurf-cascade", "windsurf-devin")

    def test_deniega_host_remoto_y_ddl_local_y_permite_ls(self):
        repo = self.preparar()
        for f in self.FORMATOS:
            with self.subTest(f):
                r = self.puente(f, self.entrada(f, repo, "mysql -h db.externo.example -e 'SELECT 1'"), repo)
                self.deniega(f, r)
                self.assertIn("Bloqueado", r.stderr)
                self.deniega(f, self.puente(f, self.entrada(f, repo, "mysql -h localhost -e 'DROP TABLE clientes'"), repo))
                self.permite(self.puente(f, self.entrada(f, repo, "ls -la"), repo))

    def test_otros_eventos_y_herramientas_no_los_juzga(self):
        repo = self.preparar()
        for f in self.FORMATOS:
            with self.subTest(f):
                self.permite(self.puente(f, self.entrada(f, repo, "x", otra=True), repo))

    def test_entrada_ilegible_o_incompleta_deniega_con_2(self):
        repo = self.preparar()
        malos = {"windsurf-cascade": ["no es json", "", "[]", json.dumps({"agent_action_name": "pre_run_command", "tool_info": {}}),
                                      json.dumps({"agent_action_name": "pre_run_command", "tool_info": {"command_line": ["ls"]}})],
                 "windsurf-devin": ["no es json", "", "[]", json.dumps({"tool_name": "exec", "tool_input": {}}),
                                    json.dumps({"tool_name": "exec", "tool_input": {"command": ["ls"]}})]}
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
                r = self.puente(f, self.entrada(f, repo, "ls"), repo, env={"PATH": str(sin_jq), "DEVIN_PROJECT_DIR": str(repo)})
                self.deniega(f, r)
                self.assertIn("jq", r.stderr)

    def test_fallo_del_hook_de_politica_deniega(self):
        repo = self.preparar()
        (self.inst / HOOKS / "block-db-access.sh").unlink()
        for f in self.FORMATOS:
            with self.subTest(f):
                self.deniega(f, self.puente(f, self.entrada(f, repo, "ls"), repo))

    def corre_comando_registrado(self, variante, formato, repo, comando):
        if variante == "cascade":
            cmd = self.leer(CASCADE)["hooks"]["pre_run_command"][0]["command"]
        else:
            cmd = self.leer(DEVIN)["PreToolUse"][0]["hooks"][0]["command"]
        env = dict(os.environ, DEVIN_PROJECT_DIR=str(repo))
        return subprocess.run(["bash", "-c", cmd], input=self.entrada(formato, repo, comando), capture_output=True, text=True, cwd=str(repo), env=env)

    def test_el_comando_registrado_funciona_tal_cual(self):
        repo = self.preparar()
        for variante, f in (("cascade", "windsurf-cascade"), ("devin-local", "windsurf-devin")):
            with self.subTest(f):
                self.deniega(f, self.corre_comando_registrado(variante, f, repo, "mysql -h db.externo.example -e 'SELECT 1'"))
                self.permite(self.corre_comando_registrado(variante, f, repo, "ls"))

    def test_comando_registrado_sin_el_lanzador_deniega_el_mismo(self):
        repo = self.preparar()
        (self.inst / HOOKS / "lanzar-cascade.sh").unlink()
        (self.inst / HOOKS / "lanzar-devin-local.sh").unlink()
        for variante, f in (("cascade", "windsurf-cascade"), ("devin-local", "windsurf-devin")):
            with self.subTest(f):
                r = self.corre_comando_registrado(variante, f, repo, "ls")
                self.assertEqual(2, r.returncode)
                self.assertIn("lanzador", r.stderr)

    def test_lanzador_sin_python3_deniega_con_2(self):
        repo = self.preparar()
        vacio = self.tmp / "vacio"
        vacio.mkdir()
        for variante, f in (("cascade", "windsurf-cascade"), ("devin-local", "windsurf-devin")):
            with self.subTest(f):
                r = subprocess.run(["/bin/sh", str(self.inst / HOOKS / f"lanzar-{variante}.sh")], input=self.entrada(f, repo, "ls"),
                                   capture_output=True, text=True, cwd=str(repo), env={"PATH": str(vacio)})
                self.assertEqual(2, r.returncode)
                self.assertIn("python3", r.stderr)

    def test_lanzador_sin_el_puente_deniega(self):
        repo = self.preparar()
        (self.inst / HOOKS / "guardia-datos.py").unlink()
        for variante, f in (("cascade", "windsurf-cascade"), ("devin-local", "windsurf-devin")):
            with self.subTest(f):
                r = subprocess.run(["/bin/sh", str(self.inst / HOOKS / f"lanzar-{variante}.sh")], input=self.entrada(f, repo, "ls"),
                                   capture_output=True, text=True, cwd=str(repo))
                self.assertEqual(2, r.returncode)


if __name__ == "__main__":
    unittest.main()
