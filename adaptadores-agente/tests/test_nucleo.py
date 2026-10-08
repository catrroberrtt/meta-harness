"""Pruebas del núcleo: fuente neutral, AGENTS.md, marco de adaptadores y CLI."""
import contextlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun
from comun import RAIZ, arbol_hash

import fuente_neutral as fn
import generar_agentes as ga

# la lista se arma por trozos para que este archivo tampoco contenga los nombres que vigila
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


def tearDownModule():
    shutil.rmtree(BASE_TMP, True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mh-nuc-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.inst = comun.copiar_instancia(BASE_INST, self.tmp)

    def cli(self, *args, sistema=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err):
            c = ga.main([str(a) for a in args], sistema=sistema, salida=out)
        return c, out.getvalue(), err.getvalue()

    def politica(self, reemplazos):
        p = self.inst / "politicas.toml"
        t = p.read_text(encoding="utf8")
        for a, b in reemplazos:
            self.assertIn(a, t)
            t = t.replace(a, b, 1)
        p.write_text(t, encoding="utf8")


class TestFuente(Base):
    def test_reglas_salen_de_la_politica_y_cambian_con_ella(self):
        antes = fn.render_agents_md(fn.construir(self.inst))
        self.assertIn("Push a una rama protegida: prohibido para el agente", antes)
        self.politica([('push_a_rama_protegida = "prohibida"', 'push_a_rama_protegida = "confirmar"'),
                       ("ramas_protegidas = []", 'ramas_protegidas = ["principal", "estable"]')])
        despues = fn.render_agents_md(fn.construir(self.inst))
        self.assertNotEqual(antes, despues)
        self.assertIn("Push a una rama protegida: solo con confirmación explícita", despues)
        self.assertIn("`principal`, `estable`", despues)
        self.assertNotIn("Ramas protegidas: sin declarar", despues)

    def test_gate_por_definir_lo_dice_y_declarado_lo_muestra(self):
        t = fn.render_agents_md(fn.construir(self.inst))
        self.assertIn("aún no está declarado", t)
        self.assertIn("por definir", t)
        c = self.inst / "convenciones.toml"
        c.write_text(c.read_text(encoding="utf8").replace('"gate.comando" = "por definir"', '"gate.comando" = "make verificar"'), encoding="utf8")
        t2 = fn.render_agents_md(fn.construir(self.inst))
        self.assertIn("make verificar", t2)
        self.assertNotIn("aún no está declarado", t2)

    def test_secciones_obligatorias_y_marca(self):
        t = fn.render_agents_md(fn.construir(self.inst))
        for s in ("## Cómo orientarte", "## Cuándo leer qué", "## Reglas duras", "## Gate de calidad",
                  "## Lo que no debes hacer", "## Herramientas del harness", "## Pendiente de declarar"):
            self.assertIn(s, t)
        self.assertTrue(t.startswith("<!-- generado por el harness: no editar a mano; editar la política o las convenciones y regenerar -->"))
        self.assertNotRegex(t, r"\{\{[A-Z_]+\}\}")

    def test_falta_politica_error_claro(self):
        (self.inst / "politicas.toml").unlink()
        with self.assertRaises(fn.ErrorInstancia) as cm:
            fn.construir(self.inst)
        self.assertIn("politicas.toml", str(cm.exception))

    def test_sin_nombres_de_empresa_ni_rutas_personales(self):
        t = fn.render_agents_md(fn.construir(self.inst))
        self.assertIsNone(PROHIBIDOS.search(t), PROHIBIDOS.search(t))
        self.assertNotIn(str(self.tmp), t)       # no copia rutas absolutas de la instancia


class TestAgentsMd(Base):
    def aplicar(self, *extra):
        return self.cli(self.inst, "--agentes", "aider", "--aplicar", *extra)

    def test_el_plan_no_escribe(self):
        antes = arbol_hash(self.tmp)
        c, out, _ = self.cli(self.inst)
        self.assertEqual(c, 0, out)
        self.assertIn("PLAN (no se escribió nada)", out)
        self.assertIn("crear", out)
        self.assertEqual(antes, arbol_hash(self.tmp))
        self.assertFalse((self.inst / "AGENTS.md").exists())

    def test_agents_md_siempre_dice_que_los_datos_los_da_la_persona(self):
        # Decisión del dueño: la base de datos NO se instala; es la evidencia más fuerte y el acceso lo da la persona.
        self.assertEqual(self.aplicar()[0], 0)
        texto = (self.inst / "AGENTS.md").read_text(encoding="utf8")
        self.assertIn("## Acceso a datos (lo da la persona)", texto)
        for frase in ("fuente de evidencia más fuerte", "no la instala ni la levanta", "modo degradado", "acceso.local.toml",
                      "preflight-accesos.py", "no verificado"):
            self.assertIn(frase, texto)
        self.assertLess(texto.index("## Acceso a datos"), texto.index("## Gate de calidad"))

    def test_sin_ambientes_declarados_dice_que_no_hay_acceso(self):
        self.assertEqual(self.aplicar()[0], 0)
        base = (self.inst / "AGENTS.md").read_text(encoding="utf8")
        sec = base.split("## Acceso a datos (lo da la persona)")[1].split("## Gate de calidad")[0]
        if "no declara ningún ambiente de datos" in sec:
            self.assertIn("no debes suponer ninguno", sec)
        else:
            self.assertIn("Ambientes declarados en la política", sec)
            self.assertIn("no significa que haya acceso", sec)

    def test_con_ambientes_los_nombra_sin_afirmar_acceso(self):
        fuente = fn.construir(self.inst)
        fuente = dict(fuente, ambientes_datos=["ambiente-uno", "ambiente-dos"])
        texto = fn.render_agents_md(fuente)
        sec = texto.split("## Acceso a datos (lo da la persona)")[1].split("## Gate de calidad")[0]
        self.assertIn("«ambiente-uno», «ambiente-dos»", sec)
        self.assertIn("no significa que haya acceso", sec)
        sin = fn.render_agents_md(dict(fuente, ambientes_datos=[]))
        self.assertIn("no declara ningún ambiente de datos", sin)
        self.assertIn("no debes suponer ninguno", sin)

    def test_regenerar_dos_veces_es_identico(self):
        self.assertEqual(self.aplicar()[0], 0)
        h1 = arbol_hash(self.inst)
        c, out, _ = self.aplicar()
        self.assertEqual(c, 0)
        self.assertEqual(h1, arbol_hash(self.inst))
        self.assertIn("igual", out)

    def test_no_pisa_agents_md_escrito_a_mano(self):
        manual = "# Mis reglas\nEscritas a mano.\n"
        (self.inst / "AGENTS.md").write_text(manual, encoding="utf8")
        c, out, _ = self.aplicar()
        self.assertEqual(c, 0)
        self.assertEqual((self.inst / "AGENTS.md").read_text(encoding="utf8"), manual)
        gen = (self.inst / "AGENTS.generado.md").read_text(encoding="utf8")
        self.assertIn(fn.MARCA, gen)
        self.assertIn("fue escrito a mano", out)
        h = arbol_hash(self.inst)
        self.aplicar()
        self.assertEqual(h, arbol_hash(self.inst))       # idempotente también en este caso

    def test_regenera_un_agents_md_generado_viejo(self):
        self.aplicar()
        p = self.inst / "AGENTS.md"
        p.write_text(p.read_text(encoding="utf8") + "\nresto viejo\n", encoding="utf8")
        self.aplicar()
        self.assertNotIn("resto viejo", p.read_text(encoding="utf8"))
        self.assertFalse((self.inst / "AGENTS.generado.md").exists())

    def test_solo_escribe_dentro_de_la_instancia(self):
        fuera_antes = {p for p in self.tmp.rglob("*") if self.inst not in p.parents and p != self.inst}
        hash_fuera = {p: p.read_bytes() for p in fuera_antes if p.is_file()}
        home = Path(tempfile.mkdtemp(prefix="mh-home-"))
        self.addCleanup(shutil.rmtree, home, True)
        import os
        viejo = os.environ.get("HOME")
        os.environ["HOME"] = str(home)
        try:
            self.cli(self.inst, "--agentes", "claude-code,aider,cline", "--aplicar")
        finally:
            os.environ["HOME"] = viejo
        self.assertEqual([], list(home.iterdir()))
        fuera_despues = {p for p in self.tmp.rglob("*") if self.inst not in p.parents and p != self.inst}
        self.assertEqual(fuera_antes, fuera_despues)
        for p, b in hash_fuera.items():
            self.assertEqual(b, p.read_bytes())

    def test_ruta_fuera_de_la_instancia_se_rechaza(self):
        for rel in ("../escape.md", "/tmp/escape.md", "a/../../escape.md"):
            with self.assertRaises(fn.ErrorInstancia):
                fn.planificar_archivo(self.inst, rel, "x")

    def test_archivos_generados_sin_nombres_de_empresa(self):
        habilitar = comun.habilitar_hooks
        habilitar(self.inst)
        self.cli(self.inst, "--agentes", "claude-code,aider,cline", "--aplicar")
        n = 0
        for p in self.inst.rglob("*"):
            if p.is_file() and p.name in ("AGENTS.md", "CLAUDE.md") or ".claude" in p.parts and p.is_file():
                n += 1
                self.assertIsNone(PROHIBIDOS.search(p.read_text(encoding="utf8")), p)
        self.assertGreaterEqual(n, 4)


class TestMarco(Base):
    def test_deteccion_con_sistemas_simulados(self):
        ga.cargar_adaptadores()
        nada = ga.SistemaSimulado()
        cc = ga.SistemaSimulado(comandos={"claude"})
        carp = ga.SistemaSimulado(rutas={".claude"})
        ai = ga.SistemaSimulado(comandos={"aider"})
        self.assertFalse(ga.REGISTRO["claude-code"]().detectar(nada)["detectado"])
        self.assertTrue(ga.REGISTRO["claude-code"]().detectar(cc)["detectado"])
        self.assertEqual(["comando `claude` en PATH"], ga.REGISTRO["claude-code"]().detectar(cc)["rastros"])
        self.assertTrue(ga.REGISTRO["claude-code"]().detectar(carp)["detectado"])
        self.assertFalse(ga.REGISTRO["claude-code"]().detectar(ai)["detectado"])
        self.assertTrue(ga.REGISTRO["aider"]().detectar(ai)["detectado"])

    def test_detectar_informa_y_solo_genera_para_los_detectados(self):
        c, out, _ = self.cli(self.inst, "--detectar", "--json", sistema=ga.SistemaSimulado(comandos={"aider"}))
        inf = json.loads(out)
        self.assertEqual(["aider"], inf["seleccionados"])
        self.assertTrue(inf["agentes"]["aider"]["detectado"])
        self.assertFalse(inf["agentes"]["claude-code"]["detectado"])
        self.assertNotIn("archivos", inf["agentes"]["claude-code"])        # no asume: no se planifica lo no detectado
        self.assertTrue(inf["agentes"]["claude-code"]["rastros"] == [])

    def test_sin_agentes_detectados_solo_el_nucleo(self):
        c, out, _ = self.cli(self.inst, "--json", sistema=ga.SistemaSimulado())
        inf = json.loads(out)
        self.assertEqual([], inf["seleccionados"])
        self.assertEqual("AGENTS.md", inf["nucleo"][0]["ruta"])

    def test_agente_desconocido_falla_con_mensaje_claro(self):
        antes = arbol_hash(self.tmp)
        c, out, err = self.cli(self.inst, "--agentes", "inexistente", "--aplicar")
        self.assertEqual(2, c)
        self.assertIn("Agente desconocido: «inexistente»", err)
        self.assertIn("claude-code", err)
        self.assertEqual(antes, arbol_hash(self.tmp))

    def test_instancia_invalida_falla(self):
        c, _, err = self.cli(self.tmp / "no-existe")
        self.assertEqual(2, c)
        self.assertIn("instancia", err.lower())

    def test_capacidades_vienen_de_la_matriz_con_fuente(self):
        m = ga.Matriz()
        self.assertEqual("si", m.capacidades("CC")["Hooks que bloquean"]["estado"])
        self.assertEqual("no_verificado", m.capacidades("AI")["Hooks que bloquean"]["estado"])
        self.assertEqual("parcial", m.capacidades("CP")["Hooks que bloquean"]["estado"])
        for cap in m.capacidades("AI").values():
            self.assertIn("MATRIZ.md", cap["fuente"])
        self.assertEqual(11, len(m.capacidades("CC")))

    def test_degradaciones_no_vacias_sin_hooks_y_nombran_la_alternativa(self):
        d = ga.REGISTRO["aider"]().degradaciones() if ga.REGISTRO else None
        ga.cargar_adaptadores()
        d = ga.REGISTRO["aider"]().degradaciones()
        self.assertTrue(d)
        texto = " ".join(x["imposicion_alternativa"] for x in d).lower()
        for clave in ("solo lectura", "hooks de git", "integración continua", "protección de ramas"):
            self.assertIn(clave, texto)

    def test_control_por_hook_nunca_promete_lo_no_verificado(self):
        ga.cargar_adaptadores()
        for n in ("aider", "cline"):
            ad = ga.REGISTRO[n]()
            self.assertEqual("no_disponible", ad.control_por_hook()[0])
        c, out, _ = self.cli(self.inst, "--agentes", "aider")
        self.assertIn("control por hook: no disponible", out)
        self.assertNotIn("control por hook: disponible", out)

    def test_registro_por_nombre_acepta_nuevos_agentes(self):
        class Nuevo(ga.AdaptadorMinimo):
            nombre, codigo_matriz, comandos = "agente-nuevo", "XX", ("nuevo",)
        ga.registrar(Nuevo)
        self.addCleanup(ga.REGISTRO.pop, "agente-nuevo", None)
        c, out, _ = self.cli(self.inst, "--agentes", "agente-nuevo", "--json")
        inf = json.loads(out)
        self.assertEqual("no_disponible", inf["agentes"]["agente-nuevo"]["control_por_hook"])    # XX no está en la matriz: no verificado
        self.assertTrue(inf["agentes"]["agente-nuevo"]["degradaciones"])

    def test_matriz_vencida_avisa(self):
        import datetime as dt
        m = ga.Matriz()
        self.assertIsNone(m.aviso_vigencia(m.revisado))
        self.assertIn("vencida", m.aviso_vigencia(m.revisado + dt.timedelta(days=m.vence_dias + 1)))

    def test_json_valido(self):
        c, out, _ = self.cli(self.inst, "--agentes", "claude-code,aider", "--json")
        self.assertEqual(0, c)
        inf = json.loads(out)
        self.assertFalse(inf["aplicado"])
        self.assertIn("control_por_hook", inf["agentes"]["claude-code"])


if __name__ == "__main__":
    unittest.main()
