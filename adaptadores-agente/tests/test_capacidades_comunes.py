"""Pruebas de las capacidades neutrales: skills, comandos, permisos y MCP (instancias sintéticas, sin red ni git)."""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun
from comun import RAIZ

import capacidades_comunes as cc
import fuente_neutral as fn

def _cargar_prohibidos():
    """Términos que ningún texto generado puede contener. Salen de un archivo LOCAL (HARNESS_PROHIBIDOS, uno por línea)
    que no vive en el repositorio; sin él, solo se comprueban patrones genéricos (puertos de base de datos y rutas del usuario)."""
    import os
    ruta = os.environ.get("HARNESS_PROHIBIDOS")
    terminos = []
    if ruta and os.path.isfile(ruta):
        terminos = [l.strip() for l in open(ruta, encoding="utf8") if l.strip() and not l.startswith("#")]
    terminos += [r"\b33(?:06|07|08|09)\b", r"/home/[a-z0-9_.-]+/"]
    return re.compile("|".join(t if t.startswith(("\\b", "/")) else re.escape(t) for t in terminos), re.I)


PROHIBIDOS = _cargar_prohibidos()
BASE_TMP, BASE_INST = comun.crear_instancia_base()
NOMBRE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SDD = ["sdd-especificar", "sdd-implementar", "sdd-planificar", "sdd-verificar"]


def tearDownModule():
    shutil.rmtree(BASE_TMP, True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mh-cap-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.inst = comun.copiar_instancia(BASE_INST, self.tmp)

    def anexar(self, texto):
        p = self.inst / "politicas.toml"
        p.write_text(p.read_text(encoding="utf8") + "\n" + texto, encoding="utf8")

    def validar(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            c = cc.main(["--validar", str(self.inst)])
        return c, out.getvalue()


class TestSkillsYComandos(unittest.TestCase):
    def test_skills_sdd_cumplen_regex_y_coinciden_con_la_carpeta(self):
        skills, errores = cc.skills_neutrales(RAIZ)
        self.assertEqual(errores, [])
        self.assertEqual(sorted(s["nombre"] for s in skills), SDD)
        for s in skills:
            self.assertRegex(s["nombre"], NOMBRE)
            self.assertLessEqual(len(s["nombre"]), 64)
            self.assertTrue((RAIZ / "plantillas" / "skills" / s["nombre"] / "SKILL.md").is_file())
            self.assertTrue(s["descripcion"])
            self.assertLessEqual(len(s["descripcion"]), 1024)
            for h in ("Cuándo usarla", "Pasos", "Qué NO hacer"):
                self.assertIn(h, s["contenido"])

    def test_comandos_neutrales(self):
        comandos, errores = cc.comandos_neutrales(RAIZ)
        self.assertEqual(errores, [])
        self.assertEqual(sorted(c["nombre"] for c in comandos), ["harness-estado", "harness-gate"])
        for c in comandos:
            self.assertRegex(c["nombre"], NOMBRE)
            self.assertTrue(c["descripcion"])

    def test_skill_con_nombre_distinto_a_la_carpeta_se_detecta(self):
        h = Path(tempfile.mkdtemp(prefix="mh-sk-"))
        self.addCleanup(shutil.rmtree, h, True)
        (h / "plantillas" / "skills" / "una-skill").mkdir(parents=True)
        (h / "plantillas" / "skills" / "una-skill" / "SKILL.md").write_text("---\nname: otra-cosa\ndescription: x\n---\n", encoding="utf8")
        (h / "plantillas" / "skills" / "Mala_Carpeta").mkdir()
        (h / "plantillas" / "skills" / "Mala_Carpeta" / "SKILL.md").write_text("---\nname: Mala_Carpeta\ndescription: x\n---\n", encoding="utf8")
        skills, errores = cc.skills_neutrales(h)
        self.assertEqual(skills, [])
        self.assertEqual(len(errores), 2)
        self.assertTrue(any("debe coincidir con la carpeta" in e for e in errores))
        self.assertTrue(any("no cumple" in e for e in errores))

    def test_ningun_texto_contiene_nombres_de_empresa(self):
        archivos = list((RAIZ / "plantillas" / "skills").rglob("*.md")) + list((RAIZ / "plantillas" / "comandos").glob("*.md")) + [
            RAIZ / "adaptadores-agente" / "nucleo" / "capacidades_comunes.py", RAIZ / "adaptadores-agente" / "nucleo" / "fuente_neutral.py",
            RAIZ / "adaptadores-agente" / "nucleo" / "README.md", RAIZ / "politicas" / "ESQUEMA.md", RAIZ / "politicas" / "politicas.defecto.toml"]
        for f in archivos:
            self.assertIsNone(PROHIBIDOS.search(f.read_text(encoding="utf8")), f"{f} contiene un nombre prohibido")


class TestPermisos(unittest.TestCase):
    def test_prefijos_literales(self):
        self.assertEqual(cc.prefijos_literales("^git push"), (["git push"], None))
        self.assertEqual(cc.prefijos_literales("cdk deploy|sam deploy"), (["cdk deploy", "sam deploy"], None))
        self.assertEqual(cc.prefijos_literales(r"^terraform apply\.sh"), (["terraform apply.sh"], None))
        for malo in [r"(^|[;&|] *)npm run migrate(:revert)?( |$)", r"\btypeorm\b", "npm run seed$", "npm .* install", "(a|b) c", "", r"npm \d+"]:
            pref, motivo = cc.prefijos_literales(malo)
            self.assertIsNone(pref, malo)
            self.assertTrue(motivo)

    def test_politica_por_defecto_no_inventa_prefijos(self):
        p = tomllib.loads((RAIZ / "politicas" / "politicas.defecto.toml").read_text(encoding="utf8"))
        perm = cc.permisos_desde_politica(p)
        self.assertEqual(perm["deny"], [])           # los regex por defecto no son prefijos literales
        self.assertEqual(perm["allow"], [])
        self.assertEqual(perm["ask"], ["git commit", "git push"])
        self.assertTrue(any(x["origen"] == "datos.comandos" and "no es un prefijo literal" in x["motivo"] for x in perm["no_traducible"]))
        self.assertTrue(any(x["origen"] == "comandos.instalar" for x in perm["no_traducible"]))

    def test_solo_prefijos_literales_y_lo_demas_se_informa(self):
        p = {"datos": {"comandos": [{"nombre": "literal", "regex": "^make borrar-datos", "accion": "prohibida"},
                                    {"nombre": "complejo", "regex": r"\bdropdb\b.*--force", "accion": "prohibida"}]},
             "comandos": {"instalar": {"accion": "confirmar", "regex": "pip install"}, "build": {"accion": "prohibida"}},
             "despliegue": {"accion": "prohibida", "regex": ["^cdk deploy", "aws .* update-function-code"]},
             "git": {"confirmar": ["commit", "Push!"], "push_a_rama_protegida": "prohibida"}}
        perm = cc.permisos_desde_politica(p)
        self.assertEqual(perm["deny"], ["make borrar-datos", "cdk deploy"])
        self.assertEqual(perm["ask"], ["git commit", "pip install"])
        for lista in ("deny", "ask", "allow"):
            for pref in perm[lista]:
                self.assertRegex(pref, r"^[A-Za-z0-9_./:=@, -]+$")
        nombres = {x["regla"] for x in perm["no_traducible"]}
        self.assertTrue({"complejo", "aws .* update-function-code", "Push!", "build", "push_a_rama_protegida"} <= nombres)
        self.assertTrue(all(x["motivo"] and x["origen"] for x in perm["no_traducible"]))
        self.assertEqual(perm["origenes"]["cdk deploy"], "despliegue.regex")

    def test_deny_gana_sobre_ask_y_es_determinista(self):
        p = {"comandos": {"instalar": {"accion": "confirmar", "regex": "npm ci"}},
             "datos": {"comandos": [{"nombre": "x", "regex": "npm ci", "accion": "prohibida"}]}}
        perm = cc.permisos_desde_politica(p)
        self.assertEqual((perm["deny"], perm["ask"]), (["npm ci"], []))
        self.assertEqual(perm, cc.permisos_desde_politica(p))


class TestMcp(Base):
    def test_sin_servidores_no_se_genera_nada(self):
        self.assertEqual(cc.mcp_desde_politica({}), ([], []))
        fuente = fn.construir(self.inst)
        self.assertEqual(fuente["mcp"], [])
        self.assertNotIn("Servidores MCP", fn.render_agents_md(fuente))
        self.assertEqual(self.validar()[0], 0)

    def test_servidor_valido_local_y_remoto(self):
        self.anexar('[[mcp.servidores]]\nnombre = "docs-locales"\ncomando = "npx"\nargs = ["-y", "paquete-servidor"]\n'
                    'entorno = { TOKEN_DOCS = "${TOKEN_DOCS}" }\n\n'
                    '[[mcp.servidores]]\nnombre = "remoto"\nurl = "https://mcp.ejemplo.test/sse"\nregistrar = "prohibida"\n')
        s = fn.construir(self.inst)["mcp"]
        self.assertEqual([x["nombre"] for x in s], ["docs-locales", "remoto"])
        self.assertEqual(s[0]["registrar"], "confirmar")
        self.assertEqual(s[0]["tipo"], "local")
        self.assertEqual(s[0]["entorno"], [{"clave": "TOKEN_DOCS", "variable": "TOKEN_DOCS"}])
        self.assertEqual((s[1]["tipo"], s[1]["registrar"], s[1]["comando"]), ("remoto", "prohibida", None))
        self.assertIn("`docs-locales` (local; registrar: confirmar)", fn.render_agents_md(fn.construir(self.inst)))

    def test_valor_secreto_en_entorno_es_error_y_no_se_imprime(self):
        secreto = "AKIA" + "ABCDEFGHIJKLMNOP"
        self.anexar(f'[[mcp.servidores]]\nnombre = "s1"\ncomando = "npx"\nentorno = {{ CLAVE = "{secreto}" }}\n')
        c, salida = self.validar()
        self.assertEqual(c, 1)
        self.assertIn("aspecto de secreto", salida)
        self.assertNotIn(secreto, salida)
        with self.assertRaises(fn.ErrorInstancia) as cm:
            fn.construir(self.inst)
        self.assertNotIn(secreto, str(cm.exception))

    def test_valor_literal_que_no_es_referencia_es_error(self):
        self.anexar('[[mcp.servidores]]\nnombre = "s1"\ncomando = "npx"\nentorno = { MODO = "produccion" }\n')
        c, salida = self.validar()
        self.assertEqual(c, 1)
        self.assertIn("no es una referencia", salida)

    def test_registrar_invalido_es_error(self):
        self.anexar('[[mcp.servidores]]\nnombre = "s1"\ncomando = "npx"\nregistrar = "siempre"\n')
        c, salida = self.validar()
        self.assertEqual(c, 1)
        self.assertIn("`registrar` debe ser uno de prohibida, confirmar, permitida", salida)

    def test_otros_errores_se_informan_todos_con_mensaje_claro(self):
        self.anexar('[[mcp.servidores]]\nnombre = "Mal_Nombre"\ncomando = "npx -y algo"\nurl = "https://x.test"\nextra = 1\n\n'
                    '[[mcp.servidores]]\nnombre = "sin-nada"\n')
        c, salida = self.validar()
        self.assertEqual(c, 1)
        for frag in ("clave desconocida `extra`", "^[a-z0-9]+(-[a-z0-9]+)*$", "exactamente uno de `comando`", "sin espacios"):
            self.assertIn(frag, salida)

    def test_url_con_credenciales_es_error(self):
        self.anexar('[[mcp.servidores]]\nnombre = "s1"\nurl = "https://usuario:clave@host.test/mcp"\n')
        self.assertEqual(self.validar()[0], 1)

    def test_validar_instancia_inexistente(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            c = cc.main(["--validar", str(self.tmp / "nada")])
        self.assertEqual(c, 2)
        self.assertIn("Se intentó leer", err.getvalue())


class TestFuenteYAgents(Base):
    def test_claves_nuevas_en_la_fuente(self):
        f = fn.construir(self.inst)
        self.assertEqual(sorted(s["nombre"] for s in f["skills"]), SDD)
        self.assertEqual(sorted(c["nombre"] for c in f["comandos"]), ["harness-estado", "harness-gate"])
        self.assertEqual(set(f["permisos"]), {"deny", "ask", "allow", "origenes", "no_traducible"})
        self.assertEqual(f["mcp"], [])

    def test_agents_md_idempotente_solo_agrega_y_sin_fechas(self):
        a = fn.render_agents_md(fn.construir(self.inst))
        b = fn.render_agents_md(fn.construir(self.inst))
        self.assertEqual(a, b)
        self.assertIn("## Capacidades neutrales del harness", a)
        for s in SDD:
            self.assertIn(f"`{s}`", a)
        self.assertIn("`harness-estado`", a)
        # lo existente sigue idéntico y la sección nueva va al final
        antes, _, _ = a.partition("\n## Capacidades neutrales del harness")
        self.assertTrue(antes.rstrip().endswith("Nada pendiente de declarar.") or "## Pendiente de declarar" in antes)
        self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}", a[a.index("## Capacidades neutrales"):]))
        it = fn.plan_agents_md(fn.construir(self.inst), self.inst)
        fn.escribir_plan(self.inst, [it], True)
        it2 = fn.plan_agents_md(fn.construir(self.inst), self.inst)
        self.assertEqual(it2["accion"], "igual")

    def test_agents_md_lista_denegados_cuando_hay_prefijos(self):
        self.anexar('[[datos.comandos]]\nnombre = "borrado"\nregex = "^make borrar-datos"\nmotivo = "prueba"')
        self.assertIn("`make borrar-datos` (`datos.comandos`)", fn.render_agents_md(fn.construir(self.inst)))

    def test_mcp_invalido_impide_construir(self):
        self.anexar('[[mcp.servidores]]\nnombre = "s1"\ncomando = "npx"\nregistrar = "x"\n')
        with self.assertRaises(fn.ErrorInstancia):
            fn.construir(self.inst)


if __name__ == "__main__":
    unittest.main()
