import importlib.util, io, pathlib, subprocess, tempfile, unittest, contextlib, datetime as dt

spec = importlib.util.spec_from_file_location("mejoras", pathlib.Path(__file__).resolve().parent.parent / "harness-mejoras.py")
mj = importlib.util.module_from_spec(spec); spec.loader.exec_module(mj)


def correr(inst, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = mj.main(["--instancia", str(inst), *args])
    return rc, out.getvalue(), err.getvalue()


def nueva(inst, titulo="Algo", riesgo="bajo", esf="S"):
    return correr(inst, "nueva", "--titulo", titulo, "--donde", "función X, caso EQ-1", "--cambio", "cambiar",
                  "--motivo", "mejor", "--riesgo", riesgo, "--esfuerzo", esf, "--visible", "si")


class Mejoras(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.inst = pathlib.Path(self.t.name) / "inst"; self.inst.mkdir()
    def tearDown(self): self.t.cleanup()
    def reg(self): return self.inst / "mejoras.md"

    def test_flujo_completo_e_ids(self):
        rc, out, _ = nueva(self.inst, "Uno"); self.assertEqual((rc, out.strip()), (0, "M-001"))
        self.assertEqual(nueva(self.inst, "Dos", "alto", "L")[1].strip(), "M-002")
        self.assertEqual(nueva(self.inst, "Tres", "medio", "M")[1].strip(), "M-003")
        # aplicar sin aprobar: rechazo
        rc, _, err = correr(self.inst, "aplicada", "M-001", "--especificacion", "SPEC-1")
        self.assertEqual(rc, 2); self.assertIn("aprobada", err)
        rc, rev, _ = correr(self.inst, "revisar")
        self.assertLess(rev.index("Riesgo alto"), rev.index("Riesgo medio")); self.assertLess(rev.index("Riesgo medio"), rev.index("Riesgo bajo"))
        # decidir sin motivo: rechazo
        self.assertEqual(correr(self.inst, "decidir", "M-001", "--estado", "aprobada")[0], 2)
        self.assertEqual(correr(self.inst, "decidir", "M-001", "--estado", "aplicada", "--motivo", "x")[0], 2)
        self.assertEqual(correr(self.inst, "decidir", "M-001", "--estado", "aprobada", "--motivo", "vale la pena")[0], 0)
        self.assertEqual(correr(self.inst, "decidir", "M-002", "--estado", "descartada", "--motivo", "no vale")[0], 0)
        # no se redecide
        self.assertEqual(correr(self.inst, "decidir", "M-001", "--estado", "descartada", "--motivo", "x")[0], 2)
        # descartada no se aplica; aprobada sin especificación tampoco
        self.assertEqual(correr(self.inst, "aplicada", "M-002", "--especificacion", "S")[0], 2)
        self.assertEqual(correr(self.inst, "aplicada", "M-001")[0], 2)
        self.assertEqual(correr(self.inst, "aplicada", "M-001", "--especificacion", "SPEC-1")[0], 0)
        _, lst, _ = correr(self.inst, "listar", "--estado", "aplicada"); self.assertIn("M-001", lst); self.assertNotIn("M-002", lst)
        txt = self.reg().read_text()
        self.assertIn("**fecha de decisión**: " + dt.date.today().isoformat(), txt)
        self.assertIn("**especificación**: SPEC-1", txt)
        _, rev, _ = correr(self.inst, "revisar"); self.assertNotIn("M-001", rev); self.assertIn("M-003", rev)

    def test_edicion_manual_no_rompe(self):
        nueva(self.inst, "Uno"); nueva(self.inst, "Dos")
        txt = self.reg().read_text()
        txt = txt.replace("# Registro de mejoras", "# Registro de mejoras\n\nNota escrita a mano.").replace("**riesgo**: bajo", "**Riesgo**:   alto   # ojo")
        txt += "\n## M-007 · Escrita a mano\n- **Estado**: Propuesta\n- **riesgo**: medio\n- **esfuerzo**: M\nTexto libre suelto\n"
        self.reg().write_text(txt)
        self.assertEqual(nueva(self.inst, "Tras mano")[1].strip(), "M-008")
        self.assertEqual(correr(self.inst, "decidir", "M-007", "--estado", "aprobada", "--motivo", "ok")[0], 0)
        out = self.reg().read_text()
        self.assertIn("Nota escrita a mano.", out); self.assertIn("Texto libre suelto", out)
        self.assertEqual(mj.campos(mj.buscar(mj.leer(self.reg())[1], "M-007"))["estado"], "aprobada")
        self.assertEqual(mj.campos(mj.buscar(mj.leer(self.reg())[1], "M-001"))["riesgo"], "alto")
        self.assertEqual(len(mj.listar(self.reg())), 4)

    def test_rutas_fuera_de_la_instancia(self):
        otro = pathlib.Path(self.t.name) / "otro"; otro.mkdir()
        rc, _, err = correr(self.inst, "listar", "--registro", str(otro / "mejoras.md")); self.assertEqual(rc, 2); self.assertIn("fuera", err)
        rc, *_ = correr(self.inst, "listar", "--registro", str(self.inst / ".." / "otro" / "m.md")); self.assertEqual(rc, 2)
        rc, *_ = correr(self.inst, "listar", "--registro", str(self.inst / "codigo.py")); self.assertEqual(rc, 2)
        self.assertFalse((otro / "mejoras.md").exists())

    def test_repo_distinto(self):
        subprocess.run(["git", "init", "-q", str(self.inst)], check=True)
        (self.inst / "sub").mkdir(); subprocess.run(["git", "init", "-q", str(self.inst / "sub")], check=True)
        rc, _, err = correr(self.inst, "listar", "--registro", str(self.inst / "sub" / "m.md"))
        self.assertEqual(rc, 2); self.assertIn("repositorio", err)
        self.assertEqual(correr(self.inst, "listar")[0], 0)

    def test_origen_sintetico_defecto_replicado_r37(self):
        """R37: la réplica reproduce el defecto del origen; la mejora queda anotada sin cambiar la réplica."""
        origen = "def total(lineas):\n    return sum(int(x) for x in lineas)  # trunca cada línea\n"
        replica = self.inst / "replica.py"; replica.write_text(origen)
        antes = replica.read_bytes()
        ns = {}; exec(origen, ns)
        self.assertEqual(ns["total"]([1.9, 1.9]), 2)  # el defecto existe y se replica
        nueva(self.inst, "Truncado por línea", "medio")
        correr(self.inst, "decidir", "M-001", "--estado", "aprobada", "--motivo", "ok")
        correr(self.inst, "aplicada", "M-001", "--especificacion", "SPEC-9")
        self.assertEqual(replica.read_bytes(), antes)  # la herramienta no tocó la réplica
        self.assertEqual(sorted(p.name for p in self.inst.iterdir()), ["mejoras.md", "replica.py"])


if __name__ == "__main__":
    unittest.main()
