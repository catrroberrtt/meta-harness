import contextlib, hashlib, importlib.util, io, json, pathlib, tempfile, unittest, zipfile
from xml.sax.saxutils import escape

spec = importlib.util.spec_from_file_location("leer", pathlib.Path(__file__).resolve().parent.parent / "harness-leer-entradas.py")
le = importlib.util.module_from_spec(spec); spec.loader.exec_module(le)

MD = """# Tienda

## Requisitos
- El sistema debe permitir registrar pedidos.
- El cliente deberá iniciar sesión.
- Nota sin relevancia.

## Entidad: Cliente
| Campo | Tipo |
|---|---|
| nombre | texto |
| correo | texto |

## Catálogo
| Entidad | Descripción |
|---|---|
| Producto | lo que se vende |

## Pendientes
- TODO definir moneda
- ¿Se aceptan devoluciones?
- Plazo de entrega por definir
"""

MYSQL = """-- esquema
CREATE TABLE `clientes` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT, -- identificador
  `nombre` VARCHAR(100) NOT NULL COMMENT 'Nombre completo',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE `pedidos` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `cliente_id` INT NOT NULL,
  `producto_id` INT,
  PRIMARY KEY (`id`),
  KEY `idx_cliente` (`cliente_id`),
  CONSTRAINT `fk_p_c` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`)
) ENGINE=InnoDB;
"""

PG = """CREATE TABLE "usuarios" (
  id SERIAL PRIMARY KEY,
  token uuid NOT NULL,
  datos jsonb
);
CREATE TABLE posts (
  id BIGSERIAL PRIMARY KEY,
  autor_id INTEGER NOT NULL REFERENCES usuarios(id),
  categoria_id INTEGER
);
CREATE INDEX idx_posts_autor ON posts (autor_id);
"""


DICC = [["Tabla", "Campo", "Tipo", "Longitud", "Nulo", "Clave", "Referencia", "Descripción"],
        ["clientes", "id", "INT", "", "No", "PK", "", "Identificador"],
        ["clientes", "nombre", "VARCHAR", "100", "No", "", "", "Nombre completo"],
        ["productos", "id", "INT", "", "No", "PK", "", ""],
        ["productos", "nombre", "VARCHAR", "80", "Sí", "", "", ""],
        ["pedidos", "id", "INT", "", "No", "PK", "", ""],
        ["pedidos", "cliente_id", "INT", "", "No", "FK", "clientes.id", "Quién compra"],
        ["pedidos", "producto_id", "INT", "", "Sí", "", "", "sin referencia declarada"]]
DICC_EN = [["Table", "Field", "Type", "Length", "Nullable", "Key", "Reference", "Description"]] + DICC[1:]


def csv_txt(filas, d):
    return "\n".join(d.join(f) for f in filas) + "\n"


def make_xlsx(path, hojas, inline=None):
    """.xlsx válido mínimo: hojas = {nombre: filas}; texto -> sharedStrings; '=...' -> fórmula; int/float -> número."""
    sst, ids = [], {}
    def cel(r, c, v):
        ref = f"{le.letras(c)}{r}"
        if isinstance(v, (int, float)): return f'<c r="{ref}"><v>{v}</v></c>'
        if isinstance(v, str) and v.startswith("="): return f'<c r="{ref}"><f>{escape(v[1:])}</f><v>2</v></c>'
        if inline and v == inline: return f'<c r="{ref}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'
        if v not in ids: ids[v] = len(sst); sst.append(v)
        return f'<c r="{ref}" t="s"><v>{ids[v]}</v></c>'
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'/>")
        wb = "".join(f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(hojas, 1))
        z.writestr("xl/workbook.xml", f'<workbook {ns} xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{wb}</sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>" +
                   "".join(f'<Relationship Id="rId{i}" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(hojas) + 1)) + "</Relationships>")
        for i, filas in enumerate(hojas.values(), 1):
            rows = "".join(f'<row r="{r}">' + "".join(cel(r, c, v) for c, v in enumerate(f) if v != "") + "</row>" for r, f in enumerate(filas, 1))
            z.writestr(f"xl/worksheets/sheet{i}.xml", f"<worksheet {ns}><sheetData>{rows}</sheetData></worksheet>")
        z.writestr("xl/sharedStrings.xml", f"<sst {ns}>" + "".join(f"<si><t>{escape(t)}</t></si>" for t in sst) + "</sst>")


def snapshot(d):
    return {str(p.relative_to(d)): hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(d.rglob("*")) if p.is_file()}


class LeerEntradas(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = pathlib.Path(self.t.name) / "entradas"; self.d.mkdir()
    def tearDown(self): self.t.cleanup()
    def w(self, n, txt, modo="w"):
        p = self.d / n
        (p.write_bytes if modo == "wb" else p.write_text)(txt); return p

    def test_markdown_requisitos(self):
        self.w("req.md", MD)
        inf = le.analizar(self.d)
        textos = [r["texto"] for r in inf["requisitos"]]
        self.assertEqual(len(textos), 2); self.assertTrue(any("registrar pedidos" in x for x in textos))
        self.assertTrue(all(r["origen"].startswith("req.md:") for r in inf["requisitos"]))
        nombres = {e["nombre"] for e in inf["entidades"]}
        self.assertEqual(nombres, {"Cliente", "Producto"})
        cli = next(e for e in inf["entidades"] if e["nombre"] == "Cliente")
        self.assertEqual([c["nombre"] for c in cli["campos"]], ["nombre", "correo"])
        self.assertEqual(len(inf["preguntas_abiertas"]), 3)
        self.assertEqual(inf["markdown"][0]["titulo"], "Tienda"); self.assertEqual(len(inf["markdown"][0]["tablas"]), 2)
        # sin SQL: motor sin propuesta y pregunta explícita; entidades md sin tabla generan preguntas
        self.assertIsNone(inf["motor"])
        self.assertTrue(any("motor" in q["pregunta"] for q in inf["preguntas"]))
        self.assertTrue(all(q["intento"] for q in inf["preguntas"]))

    def test_sql_mysql(self):
        self.w("a.sql", MYSQL)
        inf = le.analizar(self.d)
        cl = next(t for t in inf["tablas"] if t["nombre"] == "clientes")
        self.assertEqual(cl["pk"], ["id"])
        nom = next(c for c in cl["columnas"] if c["nombre"] == "nombre")
        self.assertEqual((nom["tipo"], nom["not_null"], nom["comentario"]), ("VARCHAR(100)", True, "Nombre completo"))
        idc = next(c for c in cl["columnas"] if c["nombre"] == "id")
        self.assertEqual(idc["tipo"], "INT UNSIGNED"); self.assertEqual(idc["comentario"], "identificador")
        pe = next(t for t in inf["tablas"] if t["nombre"] == "pedidos")
        self.assertEqual(pe["indices"][0]["columnas"], ["cliente_id"])
        alta = [r for r in inf["relaciones"] if r["confianza"] == "alta"]
        self.assertEqual((alta[0]["origen"], alta[0]["columna"], alta[0]["destino"]), ("pedidos", "cliente_id", "clientes"))
        self.assertEqual(inf["motor"]["propuesto"], "MySQL")
        self.assertTrue(any("producto_id" in q["pregunta"] for q in inf["preguntas"]))  # sin tabla destino
        self.assertTrue(any(c["origen"].startswith("a.sql:") for e in inf["entidades"] for c in e["campos"]))

    def test_sql_postgres(self):
        self.w("b.sql", PG)
        inf = le.analizar(self.d)
        self.assertEqual({t["nombre"] for t in inf["tablas"]}, {"usuarios", "posts"})
        us = next(t for t in inf["tablas"] if t["nombre"] == "usuarios")
        self.assertEqual(us["pk"], ["id"]); self.assertEqual(next(c for c in us["columnas"] if c["nombre"] == "datos")["tipo"], "jsonb")
        r = next(r for r in inf["relaciones"] if r["columna"] == "autor_id")
        self.assertEqual((r["destino"], r["confianza"]), ("usuarios", "alta"))
        self.assertEqual(next(t for t in inf["tablas"] if t["nombre"] == "posts")["indices"][0]["nombre"], "idx_posts_autor")
        self.assertEqual(inf["motor"]["propuesto"], "PostgreSQL")

    def test_relacion_por_nombre_confianza_media(self):
        self.w("c.sql", "CREATE TABLE autores (id INT PRIMARY KEY);\nCREATE TABLE libros (id INT PRIMARY KEY, autor_id INT);\n")
        inf = le.analizar(self.d)
        r = inf["relaciones"][0]
        self.assertEqual((r["origen"], r["destino"], r["confianza"]), ("libros", "autores", "media"))

    def test_carpeta_mixta_pdf_no_leido(self):
        self.w("req.md", MD); self.w("a.sql", MYSQL); self.w("doc.pdf", b"%PDF-1.4", "wb"); self.w("datos.xlsx", b"PK", "wb")
        inf = le.analizar(self.d)
        nl = {x["archivo"]: x for x in inf["no_leidos"]}
        self.assertIn("formato no soportado", nl["doc.pdf"]["razon"]); self.assertTrue(nl["doc.pdf"]["pedir"])
        self.assertIn("corrupto", nl["datos.xlsx"]["razon"])  # entrega 2: el .xlsx ya se intenta leer; este es inválido
        self.assertEqual(sorted(inf["leidos"]), ["a.sql", "req.md"])
        out = le.a_md(inf); self.assertIn("doc.pdf", out)

    def test_carpeta_vacia_y_sin_legible(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(le.main([str(self.d)]), 2)
        self.assertIn("vacía", err.getvalue())
        self.w("x.pdf", b"%PDF", "wb")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(le.main([str(self.d)]), 2)
        self.assertIn("x.pdf", err.getvalue())

    def test_salida_dentro_rechazada_y_entradas_intactas(self):
        self.w("req.md", MD); self.w("a.sql", MYSQL); self.w("b.sql", PG)
        antes = snapshot(self.d)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(le.main([str(self.d), "--salida", str(self.d / "informe.md")]), 2)
        fuera = pathlib.Path(self.t.name) / "informe.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(le.main([str(self.d), "--json", "--salida", str(fuera)]), 0)
            self.assertEqual(le.main([str(self.d), "--md"]), 0)
        self.assertEqual(snapshot(self.d), antes)
        datos = json.loads(fuera.read_text())
        self.assertEqual(len(datos["tablas"]), 4)

    # ───────── entrega 2: hojas de cálculo ─────────
    def firma(self, inf):
        ents = {e["nombre"]: sorted(c["nombre"] for c in e["campos"]) for e in inf["entidades"]}
        rels = sorted((r["origen"], r["columna"], r["destino"], r["confianza"]) for r in inf["relaciones"])
        return ents, rels

    ESPERADA = ({"clientes": ["id", "nombre"], "productos": ["id", "nombre"], "pedidos": ["cliente_id", "id", "producto_id"]},
                [("pedidos", "cliente_id", "clientes", "alta"), ("pedidos", "producto_id", "productos", "media")])

    def test_diccionario_xlsx(self):
        filas = [r[:] for r in DICC]; filas[1][7] = "=1+1"  # fórmula
        filas[2][7] = "Nombre «inline»"
        make_xlsx(self.d / "modelo.xlsx", {"Diccionario": filas, "Vacía": []}, inline="Nombre «inline»")
        inf = le.analizar(self.d)
        self.assertEqual(self.firma(inf), self.ESPERADA)
        self.assertEqual(inf["hojas"][0]["clasificacion"], "diccionario")
        cli = next(e for e in inf["entidades"] if e["nombre"] == "clientes")
        idc = next(c for c in cli["campos"] if c["nombre"] == "id"); nom = next(c for c in cli["campos"] if c["nombre"] == "nombre")
        self.assertEqual((idc["pk"], idc["not_null"], idc["origen"]), (True, True, "modelo.xlsx#Diccionario:2"))
        self.assertEqual((nom["tipo"], nom["comentario"]), ("VARCHAR(100)", "Nombre «inline»"))
        self.assertEqual(idc["comentario"], "2")  # fórmula: valor en caché
        self.assertTrue(any("Vacía" in a and "vacía" in a for a in inf["avisos"]))
        self.assertTrue(all(q["intento"] for q in inf["preguntas"]))
        self.assertIn("modelo.xlsx#Diccionario", le.a_md(inf))

    def test_formula_como_texto(self):
        make_xlsx(self.d / "f.xlsx", {"Hoja1": [["Tabla", "Campo", "Descripción"], ["t", "a", "=SUM(A1:A2)"]]})
        hojas, err = le.leer_xlsx(self.d / "f.xlsx")
        self.assertIsNone(err); self.assertEqual(hojas[0]["filas"][1][1][2], "2")  # valor en caché
        make_xlsx(self.d / "g.xlsx", {"Hoja1": [["a"], [3.0]]})
        self.assertEqual(le.leer_xlsx(self.d / "g.xlsx")[0][0]["filas"][1][1], ["3"])

    def test_diccionario_csv_coma_y_punto_y_coma(self):
        (self.d / "coma").mkdir(); (self.d / "pc").mkdir()
        (self.d / "coma" / "d.csv").write_bytes(b"\xef\xbb\xbf" + csv_txt(DICC, ",").encode("utf-8"))
        (self.d / "pc" / "d.csv").write_bytes(csv_txt(DICC_EN, ";").encode("latin-1"))
        for sub in ("coma", "pc"):
            t = pathlib.Path(self.t.name) / sub; t.mkdir()
            (t / "d.csv").write_bytes((self.d / sub / "d.csv").read_bytes())
            inf = le.analizar(t)
            self.assertEqual(self.firma(inf), self.ESPERADA, sub)
            self.assertEqual(inf["hojas"][0]["clasificacion"], "diccionario")
        self.assertIn("coma", inf["hojas"][0]["formato"] + le.analizar(pathlib.Path(self.t.name) / "coma")["hojas"][0]["formato"])
        self.assertIn("latin-1", inf["hojas"][0]["formato"]); self.assertIn("punto y coma", inf["hojas"][0]["formato"])
        self.assertEqual(le.analizar(pathlib.Path(self.t.name) / "coma")["entidades"][0]["campos"][0]["origen"], "d.csv:2")
        self.w("t.tsv", csv_txt(DICC, "\t")); (self.d / "coma").rename(pathlib.Path(self.t.name) / "x1"); (self.d / "pc").rename(pathlib.Path(self.t.name) / "x2")
        self.assertIn("tabulador", le.analizar(self.d)["hojas"][0]["formato"])

    def test_datos_de_ejemplo_csv(self):
        self.w("clientes.csv", "id,nombre,edad,saldo,alta,codigo\n1,Ana,30,10.5,2024-01-02,007\n2,Luis,41,3,2024-02-03,008\n")
        self.w("pedidos.csv", "id,cliente_id,total\n1,1,5.5\n2,2,7\n")
        inf = le.analizar(self.d)
        cli = next(e for e in inf["entidades"] if e["nombre"] == "clientes")
        tipos = {c["nombre"]: c["tipo"] for c in cli["campos"]}
        self.assertEqual(tipos, {"id": "entero", "nombre": "texto", "edad": "entero", "saldo": "decimal", "alta": "fecha", "codigo": "texto"})
        self.assertTrue(all(c["inferido"] for c in cli["campos"]))
        self.assertEqual([h["clasificacion"] for h in inf["hojas"]], ["datos", "datos"])
        r = inf["relaciones"][0]
        self.assertEqual((r["origen"], r["columna"], r["destino"], r["confianza"], r["columna_destino"]), ("pedidos", "cliente_id", "clientes", "media", "id"))
        self.assertIn("(inferido)", le.a_md(inf))

    def test_catalogo(self):
        self.w("paises.csv", "codigo;descripcion\nPE;Perú\nCL;Chile\n")
        inf = le.analizar(self.d)
        self.assertEqual(inf["hojas"][0]["clasificacion"], "catalogo")
        self.assertEqual(inf["entidades"], [])
        c = inf["catalogos"][0]
        self.assertEqual((c["nombre"], c["total"], c["valores"][0]["codigo"], c["valores"][0]["descripcion"]), ("paises", 2, "PE", "Perú"))
        self.assertIn("PE = Perú", le.a_md(inf))

    def test_columna_contrasena_enmascarada(self):
        self.w("usuarios.csv", "id,email,password,notas\n1,a@x.io,S3cr3t!Pass9,hola\n2,b@x.io,Otr4Clave#77,chao\n")
        make_xlsx(self.d / "u.xlsx", {"Datos": [["id", "api_key", "extra"], [1, "k1", "ghp_ABCDEFGHIJKLMNOPQRSTUVWX1234"]]})
        inf = le.analizar(self.d)
        md, js = le.a_md(inf), json.dumps(inf, ensure_ascii=False)
        for v in ("S3cr3t!Pass9", "Otr4Clave#77", "ghp_ABCDEFGHIJKLMNOPQRSTUVWX1234", '"k1"'):
            self.assertNotIn(v, md); self.assertNotIn(v, js)
        self.assertIn("usuarios.csv!C2:C3", md); self.assertIn("u.xlsx#Datos!C2", md); self.assertIn("u.xlsx#Datos!B2:B2", md)
        self.assertEqual({(x["archivo"], x["hoja"]) for x in inf["secretos"]}, {("usuarios.csv", ""), ("u.xlsx", "Datos")})
        self.assertEqual(next(e for e in inf["entidades"] if e["nombre"] == "usuarios")["campos"][2]["nombre"], "password")

    def test_clave_en_diccionario_no_es_secreto(self):
        self.w("d.csv", csv_txt(DICC, ","))
        self.assertEqual(le.analizar(self.d)["secretos"], [])

    def test_xlsx_corrupto_y_no_leidos(self):
        self.w("md.md", MD)
        self.w("roto.xlsx", b"PK\x03\x04basura que no es un zip", "wb")
        self.w("viejo.xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1xx", "wb"); self.w("h.ods", b"PK", "wb"); self.w("n.numbers", b"PK", "wb")
        self.w("clave.xlsx", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1cifrado", "wb")
        inf = le.analizar(self.d)
        nl = {x["archivo"]: x for x in inf["no_leidos"]}
        self.assertIn("corrupto", nl["roto.xlsx"]["razon"]); self.assertIn("xlsx", nl["roto.xlsx"]["pedir"])
        self.assertIn(".xls", nl["viejo.xls"]["razon"]); self.assertIn(".xlsx o .csv", nl["viejo.xls"]["pedir"])
        self.assertIn("contraseña", nl["clave.xlsx"]["razon"])
        self.assertIn("ods", nl["h.ods"]["razon"]); self.assertIn("Numbers", nl["n.numbers"]["razon"])
        self.assertEqual(inf["leidos"], ["md.md"])
        self.assertIn("roto.xlsx", le.a_md(inf))

    def test_xlsx_con_dtd_y_recorte(self):
        with zipfile.ZipFile(self.d / "x.xlsx", "w") as z:
            z.writestr("xl/workbook.xml", '<!DOCTYPE a [<!ENTITY b "c">]><workbook/>')
        self.assertIn("DTD", le.leer_xlsx(self.d / "x.xlsx")[1][0])
        (self.d / "x.xlsx").unlink()
        self.w("g.csv", "a,b\n" + "\n".join(f"{i},x" for i in range(10)) + "\n")
        viejo, le.MAX_FILAS = le.MAX_FILAS, 5
        try: inf = le.analizar(self.d)
        finally: le.MAX_FILAS = viejo
        self.assertTrue(inf["hojas"][0]["recortado"]); self.assertTrue(any("primeras 5 filas" in a for a in inf["avisos"]))

    def test_entradas_intactas_con_hojas(self):
        self.w("d.csv", csv_txt(DICC, ";")); self.w("u.csv", "id,password\n1,Zz9!secretoX\n")
        make_xlsx(self.d / "m.xlsx", {"Diccionario": DICC}); self.w("roto.xlsx", b"PK", "wb"); self.w("v.xls", b"x", "wb")
        antes = snapshot(self.d)
        fuera = pathlib.Path(self.t.name) / "i.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(le.main([str(self.d), "--json", "--salida", str(fuera)]), 0)
            self.assertEqual(le.main([str(self.d)]), 0)
        self.assertEqual(snapshot(self.d), antes)
        self.assertNotIn("Zz9!secretoX", fuera.read_text())


if __name__ == "__main__":
    unittest.main()
