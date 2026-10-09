import importlib.util, io, json, pathlib, re, shutil, subprocess, tempfile, unittest
from contextlib import redirect_stderr, redirect_stdout

RAIZ = pathlib.Path(__file__).resolve().parent.parent.parent
spec = importlib.util.spec_from_file_location("trazabilidad", RAIZ / "herramientas" / "harness-trazabilidad.py")
tz = importlib.util.module_from_spec(spec); spec.loader.exec_module(tz)
EJEMPLO = RAIZ / "plantillas" / "ejemplos" / "cambio-ejemplo"


def codigos(r, nivel=None):
    return sorted({h["codigo"] for h in r["hallazgos"] if nivel is None or h["nivel"] == nivel})


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.c = pathlib.Path(self.t.name) / "cambio"
        shutil.copytree(EJEMPLO, self.c)

    def tearDown(self):
        self.t.cleanup()

    def leer(self, n): return (self.c / n).read_text(encoding="utf8")
    def poner(self, n, txt): (self.c / n).write_text(txt, encoding="utf8")
    def cambiar(self, n, viejo, nuevo):
        s = self.leer(n); self.assertIn(viejo, s, f"el ejemplo cambió: falta «{viejo}»"); self.poner(n, s.replace(viejo, nuevo, 1))
    def run_(self, etapa="cierre", repo=None): return tz.analizar(self.c, etapa, repo)


class Ejemplo(Base):
    def test_el_ejemplo_del_repositorio_pasa_en_todas_las_etapas(self):
        for e in tz.ETAPAS:
            r = self.run_(e)
            self.assertTrue(r["ok"], (e, r["hallazgos"]))
            self.assertEqual(r["hallazgos"], [], e)

    def test_resumen(self):
        s = self.run_()["resumen"]
        self.assertEqual((s["requisitos"], s["criterios"], s["tareas"], s["filas"]), (3, 4, 2, 4))


class Especificacion(Base):
    def test_requisito_sin_criterio(self):
        self.cambiar("especificacion.md", "  - CA-02.1 ·", "  - texto suelto ·")
        r = self.run_("especificacion")
        self.assertIn("T03", codigos(r, "ERROR")); self.assertFalse(r["ok"])

    def test_sin_requisitos(self):
        self.poner("especificacion.md", "# Especificación\n\n## Requisitos\n\nnada\n")
        self.assertIn("T02", codigos(self.run_("especificacion"), "ERROR"))

    def test_sin_archivo(self):
        (self.c / "especificacion.md").unlink()
        self.assertEqual(codigos(self.run_("especificacion"), "ERROR"), ["T01"])

    def test_identificador_repetido(self):
        self.cambiar("especificacion.md", "- RQ-02 ·", "- RQ-01 ·")
        self.assertIn("T04", codigos(self.run_("especificacion"), "ERROR"))

    def test_criterio_fuera_de_requisito_o_con_numero_ajeno(self):
        self.cambiar("especificacion.md", "  - CA-02.1 ·", "  - CA-09.1 ·")
        self.assertIn("T05", codigos(self.run_("especificacion"), "ERROR"))

    def test_palabra_vaga_es_aviso_y_no_falla(self):
        self.cambiar("especificacion.md", "entonces el saldo es 6 y existe", "entonces responde rápido y existe")
        r = self.run_("especificacion")
        self.assertIn("T06", codigos(r, "AVISO")); self.assertTrue(r["ok"])

    def test_marcador_sin_resolver(self):
        self.cambiar("especificacion.md", "Tamaño: M.", "Tamaño: {{S/M/L}}.")
        self.assertIn("T09", codigos(self.run_("especificacion"), "ERROR"))

    def test_bloque_de_codigo_se_ignora(self):
        s = self.leer("especificacion.md") + "\n```markdown\n- RQ-77 · ejemplo sin criterios\n```\n"
        self.poner("especificacion.md", s)
        self.assertTrue(self.run_("especificacion")["ok"])

    def test_suposicion_abierta_avisa_y_luego_bloquea(self):
        self.cambiar("especificacion.md", "SU-02 · de-trabajo", "SU-02 · abierto")
        self.assertTrue(self.run_("especificacion")["ok"])
        self.assertIn("T07", codigos(self.run_("especificacion"), "AVISO"))
        self.assertIn("T07", codigos(self.run_("delegacion"), "ERROR"))

    def test_nivel_de_suposicion_invalido(self):
        self.cambiar("especificacion.md", "SU-02 · de-trabajo", "SU-02 · quizá")
        self.assertIn("T07", codigos(self.run_("especificacion"), "ERROR"))

    def test_sin_aprobacion_solo_bloquea_desde_delegacion(self):
        self.cambiar("especificacion.md", "- [x] OK explícito", "- [ ] OK explícito")
        self.assertTrue(self.run_("especificacion")["ok"])
        self.assertIn("T08", codigos(self.run_("delegacion"), "ERROR"))


class Delegacion(Base):
    def test_tarea_sin_contrato_de_archivos(self):
        self.cambiar("delegacion.md", "src/web/entregas/", "")
        r = self.run_("delegacion")
        self.assertIn("T20", codigos(r, "ERROR")); self.assertFalse(r["ok"])

    def test_requisito_inexistente(self):
        self.cambiar("delegacion.md", "| RQ-01 | src/web", "| RQ-01, RQ-42 | src/web")
        self.assertIn("T21", codigos(self.run_("delegacion"), "ERROR"))

    def test_solape_de_archivos_y_compartido(self):
        self.cambiar("delegacion.md", "src/web/entregas/", "src/entregas/")
        self.assertIn("T22", codigos(self.run_("delegacion"), "ERROR"))
        self.cambiar("delegacion.md", "src/entregas/, migraciones", "src/entregas/ (compartido), migraciones")
        self.cambiar("delegacion.md", "| src/entregas/ | src/web/pedidos/", "| src/entregas/ (compartido) | src/web/pedidos/")
        self.assertNotIn("T22", codigos(self.run_("delegacion"), "ERROR"))

    def test_escribe_y_no_toca_se_contradicen(self):
        self.cambiar("delegacion.md", "| src/pedidos/ |", "| src/entregas/ |")
        self.assertIn("T22", codigos(self.run_("delegacion"), "ERROR"))

    def test_ruta_insegura(self):
        self.cambiar("delegacion.md", "src/web/entregas/", "../fuera/")
        self.assertIn("T23", codigos(self.run_("delegacion"), "ERROR"))
        self.cambiar("delegacion.md", "../fuera/", "/etc/")
        self.assertIn("T23", codigos(self.run_("delegacion"), "ERROR"))

    def test_requisito_sin_tarea(self):
        self.cambiar("delegacion.md", "RQ-01, RQ-02, RQ-03", "RQ-01, RQ-02")
        self.assertIn("T24", codigos(self.run_("delegacion"), "ERROR"))

    def test_estado_invalido(self):
        self.cambiar("delegacion.md", "| aceptada |\n| Pantalla", "| hecha |\n| Pantalla")
        self.assertIn("T26", codigos(self.run_("delegacion"), "ERROR"))

    def test_sin_delegacion_es_aviso(self):
        (self.c / "delegacion.md").unlink()
        r = self.run_("delegacion")
        self.assertIn("T27", codigos(r, "AVISO")); self.assertTrue(r["ok"])

    def test_columnas_faltantes(self):
        self.poner("delegacion.md", "| Tarea | Encargado |\n|---|---|\n| x | y |\n")
        self.assertIn("T20", codigos(self.run_("delegacion"), "ERROR"))


class Matriz(Base):
    def test_no_se_exige_antes_de_implementacion(self):
        (self.c / "matriz.md").unlink()
        self.assertTrue(self.run_("delegacion")["ok"])
        self.assertIn("T40", codigos(self.run_("implementacion"), "ERROR"))

    def test_requisito_sin_prueba(self):
        s = "\n".join(l for l in self.leer("matriz.md").splitlines() if "RQ-03" not in l) + "\n"
        self.poner("matriz.md", s)
        r = self.run_("implementacion")
        self.assertTrue({"T42", "T43"} <= set(codigos(r, "ERROR")))

    def test_prueba_sin_requisito(self):
        self.cambiar("matriz.md", "| RQ-03 | CA-03.1 |", "| RQ-99 | CA-03.1 |")
        self.assertIn("T41", codigos(self.run_("implementacion"), "ERROR"))

    def test_fila_con_criterio_de_otro_requisito(self):
        self.cambiar("matriz.md", "| RQ-03 | CA-03.1 |", "| RQ-03 | CA-01.1 |")
        self.assertIn("T41", codigos(self.run_("implementacion"), "ERROR"))

    def test_verificado_sin_evidencia(self):
        self.cambiar("matriz.md", "e4f5a6b | evidencia/gate.txt | verificado", "e4f5a6b |  | verificado")
        self.assertIn("T44", codigos(self.run_("implementacion"), "ERROR"))

    def test_no_verificado_pide_motivo(self):
        self.cambiar("matriz.md", "| a1b2c3d | evidencia/gate.txt | verificado | |", "| a1b2c3d | evidencia/gate.txt | no-verificado | |")
        self.assertIn("T45", codigos(self.run_("implementacion"), "ERROR"))
        self.cambiar("matriz.md", "| no-verificado | |", "| no-verificado | sin entorno de carga; lo destraba el área de infraestructura |")
        self.assertNotIn("T45", codigos(self.run_("implementacion"), "ERROR"))

    def test_estado_invalido(self):
        self.cambiar("matriz.md", "verificado | |\n| RQ-01 | CA-01.2", "listo | |\n| RQ-01 | CA-01.2")
        self.assertIn("T46", codigos(self.run_("implementacion"), "ERROR"))

    def test_pendiente_vale_en_implementacion_pero_no_en_cierre(self):
        self.cambiar("matriz.md", "| a1b2c3d | evidencia/gate.txt | verificado | |\n| RQ-01 | CA-01.2",
                     "|  |  | pendiente | |\n| RQ-01 | CA-01.2")
        self.assertTrue(self.run_("implementacion")["ok"])
        self.assertIn("T47", codigos(self.run_("cierre"), "ERROR"))

    def test_rojo_verde_sin_declarar_avisa_en_cierre(self):
        self.cambiar("matriz.md", "| sí | e4f5a6b", "|  | e4f5a6b")
        r = self.run_("cierre")
        self.assertIn("T50", codigos(r, "AVISO")); self.assertTrue(r["ok"])


class Cierre(Base):
    def test_casilla_sin_marcar(self):
        self.cambiar("cierre.md", "- [x] Gate", "- [ ] Gate")
        r = self.run_()
        self.assertIn("T61", codigos(r, "ERROR")); self.assertFalse(r["ok"])
        self.assertTrue(self.run_("implementacion")["ok"])

    def test_no_aplica_sin_motivo(self):
        self.cambiar("cierre.md", "— N/A: el ejemplo no tiene índice de conocimiento", "")
        self.assertIn("T62", codigos(self.run_(), "ERROR"))

    def test_sin_archivo_de_cierre(self):
        (self.c / "cierre.md").unlink()
        self.assertIn("T60", codigos(self.run_(), "ERROR"))

    def test_tarea_no_aceptada(self):
        self.cambiar("delegacion.md", "| aceptada |\n| Pantalla", "| entregada |\n| Pantalla")
        self.assertIn("T25", codigos(self.run_(), "ERROR"))

    def test_suposicion_abierta_impide_cerrar(self):
        self.cambiar("especificacion.md", "SU-01 · establecido", "SU-01 · abierto")
        self.assertIn("T07", codigos(self.run_(), "ERROR"))


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          capture_output=True, text=True, check=True).stdout.strip()


@unittest.skipUnless(shutil.which("git"), "git no está instalado")
class ConRepositorio(Base):
    def setUp(self):
        super().setUp()
        self.repo = pathlib.Path(self.t.name) / "repo"; self.repo.mkdir()
        git(self.repo, "init", "-q")
        (self.repo / "pruebas").mkdir()
        (self.repo / "pruebas" / "entregas.spec.ts").write_text("// prueba de ejemplo\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-q", "-m", "uno")
        self.h1 = git(self.repo, "rev-parse", "--short=7", "HEAD")
        (self.repo / "pruebas" / "otra.txt").write_text("x\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-q", "-m", "dos")
        self.h2 = git(self.repo, "rev-parse", "--short=7", "HEAD")
        s = self.leer("matriz.md").replace("a1b2c3d", self.h1).replace("e4f5a6b", self.h2)
        self.poner("matriz.md", s)

    def test_commits_y_archivos_existentes(self):
        r = self.run_("cierre", self.repo)
        self.assertTrue(r["ok"], r["hallazgos"])
        self.assertFalse(any("falta --repo" in t for t in r["no_comprobado"]))

    def test_commit_inexistente(self):
        self.cambiar("matriz.md", self.h2, "0123abc")
        self.assertIn("T48", codigos(self.run_("cierre", self.repo), "ERROR"))

    def test_commit_con_formato_invalido(self):
        self.cambiar("matriz.md", self.h2, "no-es-hash")
        self.assertIn("T48", codigos(self.run_("cierre", self.repo), "ERROR"))

    def test_prueba_inexistente(self):
        (self.repo / "pruebas" / "entregas.spec.ts").unlink()
        self.assertIn("T49", codigos(self.run_("cierre", self.repo), "ERROR"))

    def test_evidencia_inexistente(self):
        (self.c / "evidencia" / "gate.txt").unlink()
        self.assertIn("T49", codigos(self.run_("cierre", self.repo), "ERROR"))

    def test_sin_repo_lo_declara(self):
        self.assertTrue(any("falta --repo" in t for t in self.run_("cierre")["no_comprobado"]))

    def test_no_escribe_nada(self):
        antes = sorted(str(p.relative_to(self.t.name)) for p in pathlib.Path(self.t.name).rglob("*") if ".git" not in p.parts)
        self.run_("cierre", self.repo)
        despues = sorted(str(p.relative_to(self.t.name)) for p in pathlib.Path(self.t.name).rglob("*") if ".git" not in p.parts)
        self.assertEqual(antes, despues)


class Linea(Base):
    def correr(self, *args):
        o, e = io.StringIO(), io.StringIO()
        with redirect_stdout(o), redirect_stderr(e):
            c = tz.main(list(args))
        return c, o.getvalue(), e.getvalue()

    def test_salida_0_y_texto(self):
        c, o, _ = self.correr(str(self.c))
        self.assertEqual(c, 0); self.assertIn("RESULTADO: OK", o)

    def test_salida_1_con_errores(self):
        self.cambiar("matriz.md", "| RQ-03 | CA-03.1 |", "| RQ-99 | CA-03.1 |")
        c, o, _ = self.correr(str(self.c))
        self.assertEqual(c, 1); self.assertIn("RESULTADO: FALLA", o); self.assertIn("T41", o)

    def test_salida_2_y_mensaje_accionable_sin_carpeta(self):
        c, _, e = self.correr(str(self.c / "no-existe"))
        self.assertEqual(c, 2); self.assertIn("plantillas/ejemplos/cambio-ejemplo", e)

    def test_json(self):
        c, o, _ = self.correr(str(self.c), "--json", "--etapa", "delegacion")
        d = json.loads(o)
        self.assertEqual((c, d["ok"], d["etapa"]), (0, True, "delegacion"))

    def test_estado_del_cambio(self):
        self.assertEqual(tz.estado_del_cambio(self.c)[0], "cerrable")
        self.cambiar("cierre.md", "- [x] Gate", "- [ ] Gate")
        self.assertEqual(tz.estado_del_cambio(self.c)[0], "cierre")
        self.cambiar("especificacion.md", "- [x] OK explícito", "- [ ] OK explícito")
        self.assertEqual(tz.estado_del_cambio(self.c)[0], "delegacion")


class Plantillas(unittest.TestCase):
    def test_las_plantillas_traen_los_nombres_de_columna_que_lee_la_herramienta(self):
        m = (RAIZ / "plantillas" / "matriz-trazabilidad.md").read_text(encoding="utf8")
        filas, faltan, ok = tz.tabla(m.replace("```markdown", "").replace("```", ""), ["requisito", "criterio", "prueba", "commit", "evidencia", "estado"])
        self.assertTrue(ok and not faltan)
        d = (RAIZ / "plantillas" / "delegacion.md").read_text(encoding="utf8")
        filas, faltan, ok = tz.tabla(d.replace("```markdown", "").replace("```", ""), ["tarea", "encargado", "requisitos", "escribe", "entrega", "aceptacion"])
        self.assertTrue(ok and not faltan)


if __name__ == "__main__":
    unittest.main()
