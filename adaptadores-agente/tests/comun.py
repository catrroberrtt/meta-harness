"""Ayudas de prueba: instancias sintéticas en carpetas temporales (sin red, sin git)."""
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "adaptadores-agente" / "nucleo"))
sys.path.insert(0, str(RAIZ / "adaptadores-agente" / "claude-code"))

POLITICA_CON_AMBIENTE = """
[[datos.ambientes]]
nombre = "local"
tipo = "local"
[datos.ambientes.reconocimiento]
hosts = ["localhost"]
puertos = [5432]
[datos.ambientes.permisos]
lectura = "permitida"
escritura = "prohibida"
ddl = "prohibida"
migraciones = "prohibida"
"""


def arbol_hash(carpeta):
    h = hashlib.sha256()
    for p in sorted(Path(carpeta).rglob("*")):
        h.update(str(p.relative_to(carpeta)).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def crear_instancia_base():
    """Instancia mínima creada con el instalador real (`instalar.sh init … --aplicar`). Devuelve (tmp, instancia)."""
    tmp = Path(tempfile.mkdtemp(prefix="mh-adap-"))
    docs = tmp / "docs"
    docs.mkdir()
    (docs / "modelo.md").write_text("# modelo\n", encoding="utf8")
    acc = tmp / "acceso.toml"
    acc.write_text(f'[documentacion]\nmetodo = "carpeta_repo"\ncarpeta = "{docs}"\n', encoding="utf8")
    inst = tmp / "inst"
    r = subprocess.run(["bash", str(RAIZ / "instalador" / "instalar.sh"), "init", str(inst), "--acceso", str(acc), "--aplicar"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    return tmp, inst


def copiar_instancia(base, destino_padre, nombre="inst"):
    destino = Path(destino_padre) / nombre
    shutil.copytree(base, destino)
    return destino


def habilitar_hooks(inst):
    """Completa la política de la instancia para que el generador de hooks pueda producir el hook de datos."""
    p = Path(inst) / "politicas.toml"
    t = p.read_text(encoding="utf8")
    t = t.replace("repos = []                     # patrones", 'repos = ["servicio-*"]         # patrones', 1)
    t = t.replace("hosts_locales = []", 'hosts_locales = ["localhost"]', 1)
    p.write_text(t + POLITICA_CON_AMBIENTE, encoding="utf8")
