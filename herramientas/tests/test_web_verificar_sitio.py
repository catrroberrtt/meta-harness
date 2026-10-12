import importlib.util, pathlib, tempfile, unittest, io, contextlib, json
H = pathlib.Path(__file__).resolve().parent.parent / "web-verificar-sitio.py"
spec = importlib.util.spec_from_file_location("webv", H); V = importlib.util.module_from_spec(spec); spec.loader.exec_module(V)
TOKENS = pathlib.Path(__file__).resolve().parent.parent.parent / "plantillas" / "web" / "tokens.ejemplo.css"

PAGINA = """<!doctype html><html lang="es-PE"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{titulo}</title><link rel="stylesheet" href="tokens.css"><link rel="stylesheet" href="estilo.css"></head>
<body><header><h1>Ejemplo S. A.</h1></header><main><h2 id="funciones">Funciones</h2><p>Control de existencias para comercios.</p>
<h3>Existencias</h3><img src="activos/logo.svg" alt="Logotipo de Ejemplo S. A."><a href="otra.html#funciones">Otra</a> <a href="#funciones">Subir</a>{extra}</main></body></html>"""
ESTILO = "body{font-size:1rem;color:var(--text);background:var(--bg)}h1{font-size:var(--text-4xl)}"
LIC = "| logo.svg | Ejemplo S. A. | propia | licencia propia, uso en el sitio |\n"


def sitio(d, extra="", titulo="Inicio", estilo=ESTILO, lic=LIC, otra=True):
    r = pathlib.Path(d)
    (r / "activos").mkdir(exist_ok=True)
    (r / "index.html").write_text(PAGINA.format(titulo=titulo, extra=extra), encoding="utf8")
    if otra:
        (r / "otra.html").write_text(PAGINA.format(titulo="Otra", extra="").replace('<h2 id="funciones">', '<h2 id="funciones">'), encoding="utf8")
    (r / "estilo.css").write_text(estilo, encoding="utf8")
    (r / "tokens.css").write_text(TOKENS.read_text(encoding="utf8"), encoding="utf8")
    (r / "activos" / "logo.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'></svg>", encoding="utf8")
    if lic is not None:
        (r / "activos" / "LICENCIAS.md").write_text(lic, encoding="utf8")
    return r


def codigos(res, nivel=None):
    return sorted({h["codigo"] for h in res if nivel is None or h["nivel"] == nivel})


class Contraste(unittest.TestCase):
    def test_blanco_sobre_negro(self):
        self.assertAlmostEqual(V.razon_contraste((255, 255, 255), (0, 0, 0)), 21.0, places=2)

    def test_formatos_de_color(self):
        self.assertEqual(V.parsear_color("#fff"), (255, 255, 255))
        self.assertEqual(V.parsear_color("rgb(0 128 255)"), (0, 128, 255))
        self.assertEqual(V.parsear_color("hsl(0 100% 50%)"), (255, 0, 0))
        self.assertIsNone(V.parsear_color("rgba(0,0,0,0.5)"))
        self.assertIsNone(V.parsear_color("#00000080"))
        self.assertIsNone(V.parsear_color("var(--x)"))

    def test_umbral_inclusivo(self):
        # #767676 sobre blanco = 4.54:1 (pasa 4.5); #777777 = 4.48:1 (no pasa)
        self.assertGreaterEqual(V.razon_contraste((0x76, 0x76, 0x76), (255, 255, 255)), 4.5)
        self.assertLess(V.razon_contraste((0x77, 0x77, 0x77), (255, 255, 255)), 4.5)

    def test_tokens_claro_y_oscuro(self):
        t = V.extraer_tokens(":root{--a:#fff}:root[data-theme='dark']{--a:#000}@media (prefers-color-scheme: dark){:root:not([data-theme='light']){--b:#111}}")
        self.assertEqual(t["claro"], {"--a": "#fff"}); self.assertEqual(t["oscuro"], {"--a": "#000", "--b": "#111"})

    def test_par_malo_en_oscuro(self):
        css = ":root{--text:#000;--bg:#fff}:root[data-theme='dark']{--text:#555;--bg:#444}"
        e = V.comprobar_contraste(css, "tokens.css")
        self.assertEqual([h["codigo"] for h in e], ["contraste"]); self.assertIn("oscuro", e[0]["mensaje"])

    def test_par_declarado_y_var(self):
        css = ":root{--text:var(--ink);--ink:#777;--bg:#fff} /* contraste: --ink sobre --bg >= 4.5 */"
        e = V.comprobar_contraste(css, "t.css")
        self.assertEqual(sorted(h["mensaje"].split(":")[1].split("=")[0].strip() for h in e), ["--ink sobre --bg", "--text sobre --bg"])

    def test_sin_tokens(self):
        self.assertEqual(V.comprobar_contraste("body{}", "t.css")[0]["codigo"], "contraste-sin-tokens")


class Sitio(unittest.TestCase):
    def verificar(self, d, **k):
        return V.verificar(d, **k)

    def test_sitio_correcto(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual([h for h in self.verificar(sitio(d)) if h["nivel"] == "error"], [])

    def test_ejemplo_de_tokens_pasa_contraste(self):
        self.assertEqual(V.comprobar_contraste(TOKENS.read_text(encoding="utf8"), "tokens.ejemplo.css"), [])

    def test_lang_y_title(self):
        with tempfile.TemporaryDirectory() as d:
            r = sitio(d, titulo="")
            (r / "index.html").write_text((r / "index.html").read_text().replace('lang="es-PE"', ""), encoding="utf8")
            self.assertTrue({"lang", "title"} <= set(codigos(self.verificar(r), "error")))

    def test_h1_y_saltos(self):
        with tempfile.TemporaryDirectory() as d:
            r = sitio(d, extra="<h1>Otra</h1><h5>Salto</h5>")
            e = self.verificar(r)
            self.assertIn("h1", codigos(e, "error")); self.assertIn("encabezados", codigos(e, "error"))

    def test_alt(self):
        with tempfile.TemporaryDirectory() as d:
            e = self.verificar(sitio(d, extra='<img src="activos/logo.svg"><img src="activos/logo.svg" alt="">'))
            self.assertEqual(sum(h["codigo"] == "alt" for h in e), 1)  # alt="" es decorativa y se acepta

    def test_font_size_px(self):
        with tempfile.TemporaryDirectory() as d:
            e = self.verificar(sitio(d, estilo="p{font-size:14px}.a{border:1px solid var(--border)}"))
            self.assertEqual(sum(h["codigo"] == "fuente-px" for h in e), 1)

    def test_font_size_px_en_linea(self):
        with tempfile.TemporaryDirectory() as d:
            e = self.verificar(sitio(d, extra='<p style="font-size: 12px">x</p><style>.x{font-size:10px}</style>'))
            self.assertEqual(sum(h["codigo"] == "fuente-px" for h in e), 2)

    def test_enlace_roto_y_ancla(self):
        with tempfile.TemporaryDirectory() as d:
            e = self.verificar(sitio(d, extra='<a href="no-existe.html">x</a><a href="#nada">y</a><a href="../fuera.html">z</a><a href="mailto:a@b.c">m</a>'))  # escaneo-publico: ignorar (dato falso de prueba)
            self.assertEqual(sum(h["codigo"] == "enlace-roto" for h in e), 3)

    def test_url_css_rota(self):
        with tempfile.TemporaryDirectory() as d:
            e = self.verificar(sitio(d, estilo=ESTILO + ".h{background:url(img/falta.png)}"))
            self.assertIn("enlace-roto", codigos(e, "error"))

    def test_remoto_no_declarado_y_permitido(self):
        with tempfile.TemporaryDirectory() as d:
            r = sitio(d, extra='<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=X"><a href="https://ejemplo.org/">ok</a>')
            self.assertIn("remoto-no-declarado", codigos(self.verificar(r), "error"))
            (r / "sitio.permitidos.txt").write_text("# motivo\nfonts.googleapis.com  # decidido\n", encoding="utf8")
            self.assertNotIn("remoto-no-declarado", codigos(self.verificar(r)))

    def test_trackers(self):
        with tempfile.TemporaryDirectory() as d:
            r = sitio(d, extra='<script src="https://www.googletagmanager.com/gtag/js?id=G-XXXX"></script><script>gtag("config","G-XXXX")</script>')
            self.assertEqual(sum(h["codigo"] == "tracker" for h in self.verificar(r)), 2)
            (r / "sitio.permitidos.txt").write_text("www.googletagmanager.com\n", encoding="utf8")
            self.assertEqual(sum(h["codigo"] == "tracker" and h["nivel"] == "error" for h in self.verificar(r)), 1)  # el script incrustado sigue sin declarar

    def test_imagen_de_marcador(self):
        with tempfile.TemporaryDirectory() as d:
            e = self.verificar(sitio(d, extra='<img src="https://images.unsplash.com/x.jpg" alt="a">'))
            self.assertIn("imagen-marcador", codigos(e, "error"))

    def test_secretos(self):
        with tempfile.TemporaryDirectory() as d:
            r = sitio(d)
            clave = "AKIA" + "ABCDEFGHIJKLMNOP"
            (r / "app.js").write_text(f"const k = '{clave}';\nconst api_key = \"abcdefgh12345678\";\n", encoding="utf8")
            (r / ".env").write_text("X=1", encoding="utf8")
            e = [h for h in self.verificar(r) if h["codigo"] == "secreto"]
            self.assertEqual(len(e), 3)
            self.assertFalse(any(clave in h["mensaje"] for h in e))  # nunca se imprime el valor

    def test_licencia_de_activos(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("licencia-activo", codigos(self.verificar(sitio(d, lic=None)), "error"))
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("licencia-activo", codigos(self.verificar(sitio(d, lic="otro.png | x | MIT\n")), "error"))
        with tempfile.TemporaryDirectory() as d:
            e = [h for h in self.verificar(sitio(d, lic="logo.svg | Ejemplo | sin datos\n")) if h["codigo"] == "licencia-activo"]
            self.assertEqual(len(e), 1); self.assertIn("no declara licencia", e[0]["mensaje"])

    def test_relleno(self):
        with tempfile.TemporaryDirectory() as d:
            e = self.verificar(sitio(d, extra="<p>Lorem ipsum dolor sit amet</p><p>Hasta 10x más rápido</p><button>🚀 Empezar</button>"))
            self.assertIn("relleno", codigos(e, "error"))
            self.assertTrue({"metrica-inventada", "emoji-icono"} <= set(codigos(e, "aviso")))

    def ficha(self, d, texto):
        r = sitio(d)
        (r / "DISENO.md").write_text(texto, encoding="utf8")
        return self.verificar(r)

    def test_marca_ajena_como_referencia_es_error(self):
        """Decisión 2026-10-09: ni sistemas «inspirados en» marcas reales ni marcas ajenas como referencia a imitar."""
        casos = ["Sistema de diseño inspirado en Stripe, con morado y degradados.", "Tipografía y colores al estilo de Apple.",
                 "Usar el sistema de diseño de BMW como base.", "Inspired by Linear: oscuro y minimalista.",
                 "Queremos una web parecida a la de Nike."]
        for texto in casos:
            with tempfile.TemporaryDirectory() as d:
                e = [h for h in self.ficha(d, "# Ficha\n" + texto + "\n") if h["codigo"] == "marca-ajena"]
                self.assertEqual(len(e), 1, texto)
                self.assertEqual((e[0]["nivel"], e[0]["linea"], e[0]["archivo"]), ("error", 2, "DISENO.md"), texto)

    def test_marca_ajena_negada_o_solo_mencionada(self):
        with tempfile.TemporaryDirectory() as d:
            e = self.ficha(d, "- No hacer: imitar la identidad de otra empresa; prohibido copiar a Stripe.\n- Nunca al estilo de Apple.\n")
            self.assertNotIn("marca-ajena", codigos(e)); self.assertNotIn("marca-ajena-mencion", codigos(e))
        with tempfile.TemporaryDirectory() as d:
            e = self.ficha(d, "Aceptamos pagos con Mastercard y envíos por Uber Eats.\n")
            self.assertIn("marca-ajena-mencion", codigos(e, "aviso")); self.assertNotIn("marca-ajena", codigos(e))

    def test_ficha_propia_no_da_hallazgos_de_marca(self):
        with tempfile.TemporaryDirectory() as d:
            e = self.ficha(d, "# Ficha de Ejemplo S. A.\nColor base #276eb1. Voz sobria y cercana. Sistema de diseño propio de la empresa.\n")
            self.assertEqual([h for h in e if h["codigo"].startswith("marca-ajena")], [])

    def test_solo_se_lee_la_ficha_declarada(self):
        with tempfile.TemporaryDirectory() as d:
            r = sitio(d, extra="<p>Inspirado en Stripe</p>")
            self.assertNotIn("marca-ajena", codigos(self.verificar(r)))

    def test_color_crudo_e_indigo(self):
        with tempfile.TemporaryDirectory() as d:
            e = self.verificar(sitio(d, estilo=ESTILO + ".b{background:#6366f1}"))
            self.assertTrue({"color-crudo", "indigo-defecto"} <= set(codigos(e, "aviso")))

    def test_movimiento(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("movimiento", codigos(self.verificar(sitio(d, estilo=ESTILO + ".a{transition:all .3s}")), "aviso"))
            self.assertNotIn("movimiento", codigos(self.verificar(sitio(d, estilo=ESTILO + ".a{transition:all .3s}@media (prefers-reduced-motion: reduce){.a{transition:none}}"))))

    def test_pesos(self):
        with tempfile.TemporaryDirectory() as d:
            r = sitio(d)
            (r / "activos" / "grande.png").write_bytes(b"0" * 400 * 1024)
            (r / "activos" / "LICENCIAS.md").write_text(LIC + "grande.png | x | CC0\n", encoding="utf8")
            self.assertIn("peso-activo", codigos(self.verificar(r), "error"))
            self.assertIn("peso-html", codigos(self.verificar(r, limites={"html": 100}), "error"))

    def test_peso_pagina_suma_recursos_locales(self):
        with tempfile.TemporaryDirectory() as d:
            r = sitio(d, extra='<img src="activos/foto.jpg" alt="f">')
            (r / "activos" / "foto.jpg").write_bytes(b"0" * 200 * 1024)
            (r / "activos" / "LICENCIAS.md").write_text(LIC + "foto.jpg | x | CC0\n", encoding="utf8")
            self.assertIn("peso-pagina", codigos(self.verificar(r, limites={"pagina": 150 * 1024}), "error"))

    def test_titulo_repetido_y_viewport(self):
        with tempfile.TemporaryDirectory() as d:
            r = sitio(d, titulo="Otra")
            (r / "index.html").write_text((r / "index.html").read_text().replace('<meta name="viewport" content="width=device-width">', ""), encoding="utf8")
            self.assertTrue({"title-repetido", "viewport"} <= set(codigos(self.verificar(r), "aviso")))

    def test_carpeta_sin_paginas(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("sin-paginas", codigos(self.verificar(d), "error"))


class Cli(unittest.TestCase):
    def correr(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            return V.main(list(args)), out.getvalue()

    def test_codigos_de_salida(self):
        with tempfile.TemporaryDirectory() as d:
            r = sitio(d)
            self.assertEqual(self.correr(str(r))[0], 0)
            self.assertEqual(self.correr(str(r), "--json")[0], 0)
            (r / "index.html").write_text("<html><body></body></html>", encoding="utf8")
            self.assertEqual(self.correr(str(r))[0], 1)
            self.assertEqual(self.correr(d + "/no-existe")[0], 2)

    def test_estricto_convierte_avisos(self):
        with tempfile.TemporaryDirectory() as d:
            r = sitio(d, estilo=ESTILO + ".b{background:#6366f1}")
            self.assertEqual(self.correr(str(r))[0], 0)
            self.assertEqual(self.correr(str(r), "--estricto")[0], 1)

    def test_json_valido(self):
        with tempfile.TemporaryDirectory() as d:
            c, out = self.correr(str(sitio(d)), "--json")
            self.assertEqual(json.loads(out)["errores"], 0)


if __name__ == "__main__":
    unittest.main()
