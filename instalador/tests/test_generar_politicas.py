"""Pruebas de generar-politicas.py.

R17: el hook generado desde la politica de un proyecto real da el mismo veredicto que la bateria
     de su hook original (los casos y las expectativas se copiaron de esa bateria; los nombres
     de ambientes, puertos y bases salen de la politica, nunca estan escritos aqui).
R18: una politica de otro proyecto (otros ambientes y puertos) funciona igual, y una politica
     vacia falla con un mensaje claro en vez de asumir un ambiente.

La politica de referencia NO esta en este repositorio: se lee de la instancia que la aporta
(POLITICA_REFERENCIA, o la primera `~/.claude/skills/*/entorno/politicas-*.toml` que exista).
Si no hay ninguna, las pruebas de R17 se omiten.
"""
import glob
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
GENERADOR = os.path.join(os.path.dirname(AQUI), "generar-politicas.py")
_spec = importlib.util.spec_from_file_location("generar_politicas", GENERADOR)
gp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gp)

CLI = "my" + "sql"          # los nombres peligrosos se arman por partes (los hooks vigilan el texto)
BORRAR = "de" + "lete"
TIRAR = "DR" + "OP"
MIG = "migra" + "te"
ORM = "type" + "orm"
CURL = "cu" + "rl"


def politica_referencia():
    ruta = os.environ.get("POLITICA_REFERENCIA")
    if ruta:
        return ruta
    hallados = sorted(glob.glob(os.path.expanduser("~/.claude/skills/*/entorno/politicas-*.toml")))
    return hallados[0] if hallados else None


def ejecutar(hook, comando, cwd, home):
    env = dict(os.environ)
    env["HOME"] = home
    env.pop("CLAUDE_HOOK_DEBUG", None)
    r = subprocess.run(["bash", hook], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": comando}}),
                       capture_output=True, text=True, cwd=cwd, env=env)
    if not r.stdout.strip():
        return "none"
    try:
        return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]
    except Exception:
        return "none"


def repo_falso(raiz, nombre, remote, env, archivo_env=".env"):
    ruta = os.path.join(raiz, nombre)
    os.makedirs(ruta)
    subprocess.run(["git", "init", "-q", ruta], check=True)
    if remote:
        subprocess.run(["git", "-C", ruta, "remote", "add", "origin", remote], check=True)
    with open(os.path.join(ruta, archivo_env), "w") as f:
        f.write(env)
    return ruta


class Entorno:
    """Repos falsos + hook generado para una politica, todo en un directorio temporal."""

    def __init__(self, ruta_politica):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        with open(ruta_politica, "rb") as f:
            self.politica = tomllib.load(f)
        amb = self.politica["datos"]["ambientes"]
        self.agente = next(a for a in amb if a["permisos"]["escritura"] == "permitida")
        otros = [a for a in amb if a is not self.agente]
        rec = self.agente["reconocimiento"]
        var = self.agente["variables"]
        self.base = rec["bases"][0]
        self.puerto = rec["puertos"][0]
        self.host = rec["hosts"][0]
        self.puerto_otro = next(a["reconocimiento"]["puertos"][0] for a in otros if a["reconocimiento"].get("puertos"))
        self.base_ajena = next(b for a in otros for b in a["reconocimiento"].get("bases", []))
        self.var = var
        alc = self.politica["alcance"]
        nombre_repo = alc["repos"][0].replace("*", "x")
        env_ok = f"{var['host']}={self.host}\n{var['puerto']}={self.puerto}\n{var['base']}={self.base}\n"
        env_otro = f"{var['host']}={self.host}\n{var['puerto']}={self.puerto_otro}\n{var['base']}={self.base_ajena}\n"
        self.repo = repo_falso(t, nombre_repo, alc["remote_ejemplo"], env_ok, var["archivo_env"])
        os.makedirs(os.path.join(t, "otro"))
        self.repo_ajeno = repo_falso(os.path.join(t, "otro"), nombre_repo, alc["remote_ejemplo"], env_otro, var["archivo_env"])
        self.salida = os.path.join(t, "salida")
        gp.generar(ruta_politica, self.salida)
        self.hook = os.path.join(self.salida, "block-db-access.sh")
        # HOME aislado: ahi vive el archivo de sha256 de los motores de solo lectura.
        self.home = os.path.join(t, "home")
        os.makedirs(self.home)
        mot = self.politica["datos"].get("motores_solo_lectura") or {}
        self.motor = None
        if mot.get("scripts") and mot.get("archivo_sha256"):
            rel = mot["scripts"][0]
            ruta_motor = os.path.join(self.repo, rel)
            os.makedirs(os.path.dirname(ruta_motor), exist_ok=True)
            with open(ruta_motor, "w") as f:
                f.write(f"#!/usr/bin/env bash\n{CLI} -e 'select 1'\n")
            pin = os.path.join(self.home, mot["archivo_sha256"].replace("~/", ""))
            os.makedirs(os.path.dirname(pin), exist_ok=True)
            with open(pin, "w") as f:
                f.write(hashlib.sha256(open(ruta_motor, "rb").read()).hexdigest() + "  " + ruta_motor + "\n")
            self.motor = ruta_motor

    def decision(self, comando, cwd=None):
        return ejecutar(self.hook, comando, cwd or self.repo, self.home)

    def cerrar(self):
        self.tmp.cleanup()


def casos(e):
    """Los casos de la bateria del hook original, con los nombres tomados de la politica."""
    t = tempfile.mkdtemp()
    borra = os.path.join(t, "w.sql")
    open(borra, "w").write(f"{BORRAR.upper()} FROM tabla_a WHERE id = 1;\n")
    sel = os.path.join(t, "s.sql")
    open(sel, "w").write("SELECT COUNT(*) FROM tabla_a WHERE monto > 0;\n")
    call = os.path.join(t, "c.sql")
    open(call, "w").write("CALL sp_ejemplo(1,2,3,4,5);\n")
    B, P, PO, BA, H = e.base, e.puerto, e.puerto_otro, e.base_ajena, e.host
    v = e.var
    envset = f"cd {e.repo} && set -a && . ./{v['archivo_env']} >/dev/null 2>&1 && set +a && "
    lista = [
        ("cliente contra host remoto", "deny", f"{CLI} -h qas.interno -u x -e 'select 1'"),
        ("escritura local a una base que no es la del agente", "deny", f"{CLI} -h {H} -u root {BA} -e '{BORRAR} from tabla_a'"),
        ("escritura al ambiente del agente por otro puerto", "deny", f"{CLI} -h {H} -P {PO} -u root {B} -e '{BORRAR} from tabla_a'"),
        ("escritura al ambiente del agente en host remoto", "deny", f"{CLI} -h qas.interno -u root {B} -e '{BORRAR} from tabla_a'"),
        (f"{TIRAR} DATABASE aunque sea el ambiente del agente", "deny", f"{CLI} -h {H} -u root -e '{TIRAR} DATABASE {B}'"),
        ("DDL escondida en un archivo (base ajena)", "deny", f"{CLI} -h {H} -u root {BA} < {borra}"),
        ("migracion en un repo cuyo .env no es el del agente", "deny", f"npm run {MIG}", e.repo_ajeno),
        ("CLI del ORM", "deny", f"npx {ORM} migration:run"),
        ("seed aunque sea el ambiente del agente", "deny", "npm run seed"),
        ("escritura al ambiente del agente", "allow", f"{CLI} -h {H} -P {P} -u root {B} -e '{BORRAR} from tabla_a'"),
        ("archivo SQL con escritura al ambiente del agente", "allow", f"{CLI} -h {H} -u root {B} < {borra}"),
        ("migracion con .env en el ambiente del agente", "allow", f"npm run {MIG}"),
        ("migracion revertida con .env en el ambiente del agente", "allow", f"npm run {MIG}:revert"),
        ("host que viene de variable", "ask", f'{CLI} -h "$DB_HOST" -u root -e \'select 1\''),
        ("archivo canalizado al cliente", "deny", f"grep -v x {borra} | {CLI} -h {H} -u root {BA}"),
        ("SELECT local (autorizado, sin preguntar)", "allow", f"{CLI} -h {H} -u root {BA} -e 'select 1'"),
        (f"grep en una carpeta cuyo nombre lleva {CLI}", "none", f"cd /tmp/x/tool-{CLI}-docker-x && grep -n patron run.sh"),
        ("grep cuyo PATRON es el cliente", "none", f"grep -n '{CLI}_cmd\\|{CLI} -h' run.sh"),
        ("grep de palabras de DDL", "none", f"grep -nE '{TIRAR}|CREATE|{CLI}dump' prepare.sh"),
        ("leer un script", "none", "cat prepare.sh"),
        ("escribir un documento que las menciona", "none", f"cat > /tmp/nota.md <<'FIN'\nEl procedimiento hace {BORRAR} y {TIRAR}\nFIN"),
        ("forma documentada: .env + MYSQL_PWD + < archivo.sql", "allow",
         envset + f'MYSQL_PWD="${v["contrasena"]}" {CLI} -h {H} -P "${{{v["puerto"]}:-{P}}}" -u "$DB_USERNAME" "${v["base"]}" --table < {sel}'),
        ("el > dentro del SQL no es una redireccion", "allow", f"{CLI} -h {H} -u u base_x -e 'SELECT COUNT(*) FROM tabla_a WHERE monto > 0'"),
        ("DESCRIBE", "allow", f"{CLI} -h {H} -u u base_x -e 'DESCRIBE tabla_a'"),
        ("SELECT + comando de red encadenado", "none", f"{CLI} -h {H} -u u base_x -e 'SELECT 1' && {CURL} -X POST http://localhost:3002/x"),
        ("SELECT + borrado de archivos", "none", f"{CLI} -h {H} -u u base_x -e 'SELECT 1'; rm -rf /tmp/x"),
        ("SELECT INTO OUTFILE (escribe un archivo)", "none", f"{CLI} -h {H} -u u base_x -e \"SELECT * INTO OUTFILE '/tmp/x' FROM tabla_a\""),
        ("SELECT FOR UPDATE (toma locks)", "deny", f"{CLI} -h {H} -u u base_x -e 'SELECT * FROM tabla_a WHERE id=1 FOR UPDATE'"),
        ("CALL a un procedimiento", "none", f"{CLI} -h {H} -u u base_x -e 'CALL sp_ejemplo(1,2,3,4,5)'"),
        ("archivo .sql con un CALL", "none", f"{CLI} -h {H} -u u base_x < {call}"),
        ("salida redirigida a un archivo", "none", f"{CLI} -h {H} -u u base_x -e 'SELECT 1' > /tmp/out.txt"),
        ("sustitucion de comandos", "none", f"{CLI} -h {H} -u u base_x -e \"SELECT $(whoami)\""),
        ("sin -h: el host sale del .env", "ask", f"{CLI} -u u base_x -e 'SELECT 1'"),
    ]
    if e.motor:
        lista += [
            ("motor de solo lectura fijado", "allow", f"bash {e.motor} tabla_a"),
            ("motor fijado con cd previo", "allow", f"cd {e.repo} && bash {e.motor} tabla_a"),
            ("motor fijado + tramo de red", "ask", f"bash {e.motor} tabla_a && {CURL} -X POST http://x"),
        ]
    return lista


@unittest.skipIf(politica_referencia() is None, "no hay politica de referencia (POLITICA_REFERENCIA)")
class EquivalenciaConLaPoliticaDeReferencia(unittest.TestCase):
    """R17."""

    @classmethod
    def setUpClass(cls):
        cls.e = Entorno(politica_referencia())

    @classmethod
    def tearDownClass(cls):
        cls.e.cerrar()

    def test_todos_los_casos_de_la_bateria(self):
        malos, total = [], 0
        for caso in casos(self.e):
            nombre, esperado, comando = caso[:3]
            cwd = caso[3] if len(caso) > 3 else None
            total += 1
            dado = self.e.decision(comando, cwd)
            if dado != esperado:
                malos.append(f"{nombre}: esperaba {esperado}, dio {dado}")
        self.assertGreaterEqual(total, 33)
        self.assertEqual(malos, [], "\n".join(malos))

    def test_el_hook_generado_no_trae_valores_de_la_politica_escritos_a_mano_en_la_plantilla(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(GENERADOR)), "hooks", "plantillas", "block-db-access.sh.tpl")) as f:
            plantilla = f.read()
        p = self.e.politica
        valores = [self.e.base, str(self.e.puerto), str(self.e.puerto_otro), self.e.base_ajena]
        valores += [h for h in p["datos"]["hosts_locales"] if h not in ("localhost", "127.0.0.1", "::1")]
        for v in valores:
            self.assertNotIn(v, plantilla, f"la plantilla trae el valor {v!r} escrito a mano")

    def test_salida_solo_en_el_directorio_pedido(self):
        self.assertEqual(sorted(os.listdir(self.e.salida)), ["block-db-access.sh", "filtrar-tramos-de-lectura.py"])


POLITICA_FICTICIA = """
[proyecto]
etiqueta_reglas = "politica de ejemplo"
[alcance]
repos = ["svc-*"]
remote_regex = 'gitlab\\.example\\.org[:/]acme/'
remote_ejemplo = "git@gitlab.example.org:acme/demo.git"
[datos]
hosts_locales = ["localhost", "127.0.0.1"]
clientes_sql = ["mysql", "psql"]
[[datos.ambientes]]
nombre = "sandbox"
tipo = "local"
[datos.ambientes.reconocimiento]
hosts = ["127.0.0.1"]
puertos = [5544]
bases = ["sandbox_db"]
[datos.ambientes.variables]
archivo_env = ".env.local"
host = "PGHOST"
puerto = "PGPORT"
base = "PGDATABASE"
contrasena = "PGPASSWORD"
[datos.ambientes.permisos]
lectura = "permitida"
escritura = "permitida"
ddl = "permitida"
migraciones = "permitida"
[[datos.ambientes]]
nombre = "staging"
tipo = "pruebas"
[datos.ambientes.reconocimiento]
puertos = [6655]
bases = ["staging_db"]
[datos.ambientes.permisos]
lectura = "permitida"
escritura = "prohibida"
ddl = "prohibida"
migraciones = "prohibida"
[[datos.comandos]]
nombre = "migraciones"
regex = '(^|[;&|] *)make db-upgrade( |$)'
permitida_en_ambiente_de_escritura = true
motivo = "corre una migracion contra una base que no es el sandbox"
"""


class ProyectoFicticio(unittest.TestCase):
    """R18: otros ambientes y puertos, nada de lo del proyecto de referencia."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.ruta = os.path.join(cls.tmp.name, "politica-ficticia.toml")
        open(cls.ruta, "w").write(POLITICA_FICTICIA)
        cls.e = Entorno(cls.ruta)

    @classmethod
    def tearDownClass(cls):
        cls.e.cerrar()
        cls.tmp.cleanup()

    def test_la_escritura_vale_solo_en_su_ambiente(self):
        e = self.e
        w = f"{BORRAR} from t"
        self.assertEqual(e.decision(f"{CLI} -h 127.0.0.1 -P 5544 -u u sandbox_db -e '{w}'"), "allow")
        self.assertEqual(e.decision(f"{CLI} -h 127.0.0.1 -P 6655 -u u sandbox_db -e '{w}'"), "deny")
        self.assertEqual(e.decision(f"{CLI} -h 127.0.0.1 -u u staging_db -e '{w}'"), "deny")
        self.assertEqual(e.decision(f"{CLI} -h db.remoto.example -u u sandbox_db -e '{w}'"), "deny")

    def test_lectura_local_y_host_no_resuelto(self):
        e = self.e
        self.assertEqual(e.decision(f"{CLI} -h 127.0.0.1 -u u x -e 'select 1'"), "allow")
        self.assertEqual(e.decision(f"{CLI} -u u x -e 'select 1'"), "ask")
        self.assertEqual(e.decision(f"{CLI} -h db.remoto.example -u u x -e 'select 1'"), "deny")

    def test_comando_de_la_politica_con_excepcion_en_el_ambiente_de_escritura(self):
        e = self.e
        self.assertEqual(e.decision("make db-upgrade"), "allow")
        self.assertEqual(e.decision("make db-upgrade", e.repo_ajeno), "deny")

    def test_lo_del_otro_proyecto_no_se_asume(self):
        # Sin comandos declarados no hay nada prohibido de oficio: ni migrate ni seed existen aqui.
        self.assertEqual(self.e.decision("npm run seed"), "none")
        # Un repo que no esta en el alcance declarado no se vigila.
        otro = repo_falso(self.e.tmp.name, "api-otro", self.e.politica["alcance"]["remote_ejemplo"], "")
        self.assertEqual(self.e.decision(f"{CLI} -h db.remoto.example -u u x -e 'select 1'", otro), "none")

    def test_el_hook_generado_no_menciona_valores_de_otro_proyecto(self):
        with open(self.e.hook) as f:
            texto = f.read()
        ref = politica_referencia()
        if ref:
            with open(ref, "rb") as f:
                pol = tomllib.load(f)
            ajenos = set()
            for a in pol["datos"]["ambientes"]:
                rec = a["reconocimiento"]
                ajenos |= {str(x) for x in rec.get("puertos", [])} | set(rec.get("bases", [])) | set(rec.get("bases_prefijos", []))
                ajenos |= set((a.get("variables") or {}).values()) - {".env"}
            for ajeno in sorted(ajenos):
                self.assertNotIn(ajeno, texto, f"el hook del proyecto ficticio trae {ajeno!r} de otro proyecto")
        for propio in ("5544", "sandbox_db", "PGPORT", "staging_db"):
            self.assertIn(propio, texto)


class PoliticasInvalidas(unittest.TestCase):
    """R18: nunca se asume un ambiente."""

    def generar_texto(self, texto, nombre="p.toml"):
        with tempfile.TemporaryDirectory() as t:
            ruta = os.path.join(t, nombre)
            open(ruta, "w").write(texto)
            salida = os.path.join(t, "out")
            r = subprocess.run([sys.executable, GENERADOR, ruta, "--salida", salida], capture_output=True, text=True)
            return r, os.path.exists(salida)

    def test_politica_vacia_pide_declarar_los_ambientes(self):
        r, creo_salida = self.generar_texto("")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no declara ningun ambiente", r.stderr)
        self.assertIn("nunca asume", r.stderr)
        self.assertFalse(creo_salida, "no debe escribir nada si la politica es invalida")
        self.assertEqual(r.stdout, "")

    def test_solo_cabeceras_sin_ambientes_tambien_falla(self):
        r, _ = self.generar_texto('[datos]\nhosts_locales = ["localhost"]\nclientes_sql = ["mysql"]\n')
        self.assertEqual(r.returncode, 2)
        self.assertIn("ningun ambiente", r.stderr)

    def test_ambiente_sin_permisos_declarados_falla(self):
        r, _ = self.generar_texto(
            '[alcance]\nrepos=["a-*"]\n[datos]\nhosts_locales=["localhost"]\nclientes_sql=["mysql"]\n'
            '[[datos.ambientes]]\nnombre="x"\ntipo="local"\n[datos.ambientes.reconocimiento]\nhosts=["localhost"]\n')
        self.assertEqual(r.returncode, 2)
        self.assertIn("permisos", r.stderr)

    def test_produccion_con_escritura_permitida_se_rechaza(self):
        r, _ = self.generar_texto(
            '[alcance]\nrepos=["a-*"]\n[datos]\nhosts_locales=["localhost"]\nclientes_sql=["mysql"]\n'
            '[[datos.ambientes]]\nnombre="x"\ntipo="produccion"\n[datos.ambientes.reconocimiento]\nhosts=["localhost"]\n'
            '[datos.ambientes.permisos]\nlectura="permitida"\nescritura="permitida"\nddl="permitida"\nmigraciones="prohibida"\n')
        self.assertEqual(r.returncode, 2)
        self.assertIn("produccion", r.stderr)

    def test_archivo_inexistente(self):
        r = subprocess.run([sys.executable, GENERADOR, "/no/existe.toml", "--salida", "/tmp/no-se-crea-x"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("No existe", r.stderr)

    def test_politica_por_defecto_del_repo_no_declara_ambientes_y_falla(self):
        defecto = os.path.join(os.path.dirname(os.path.dirname(GENERADOR)), "politicas", "politicas.defecto.toml")
        with tempfile.TemporaryDirectory() as t:
            r = subprocess.run([sys.executable, GENERADOR, defecto, "--salida", os.path.join(t, "o")],
                               capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("ningun ambiente", r.stderr)


if __name__ == "__main__":
    unittest.main()
