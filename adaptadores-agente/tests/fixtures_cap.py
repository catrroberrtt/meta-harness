"""Fragmentos de política y ayudas comunes para las pruebas de skills, comandos, permisos y MCP de los adaptadores."""
import json
import os
from pathlib import Path

import fuente_neutral as fn

POL_DENY = """
[[datos.comandos]]
nombre = "infra destructiva"
regex = "^terraform destroy|^kubectl delete"
accion = "prohibida"
motivo = "destruye infraestructura"

[[datos.comandos]]
nombre = "borrado seguro"
regex = "^shred"
accion = "prohibida"
motivo = "borra datos"
"""
POL_MCP = """
[[mcp.servidores]]
nombre = "docs"
comando = "npx"
args = ["-y", "paquete-docs"]
entorno = { DOCS_VAR = "${DOCS_VAR}" }
registrar = "permitida"

[[mcp.servidores]]
nombre = "web"
url = "https://mcp.example.com/web"
registrar = "permitida"

[[mcp.servidores]]
nombre = "buscador"
url = "https://mcp.example.com/mcp"

[[mcp.servidores]]
nombre = "vetado"
comando = "otro"
registrar = "prohibida"
"""
POL_MCP_CONFIRMAR = """
[[mcp.servidores]]
nombre = "buscador"
url = "https://mcp.example.com/mcp"
"""


def anexar(inst, texto):
    p = Path(inst) / "politicas.toml"
    p.write_text(p.read_text(encoding="utf8") + "\n" + texto, encoding="utf8")


def fuente_de(inst):
    return fn.construir(inst)


def leer(inst, rel):
    return (Path(inst) / rel).read_text(encoding="utf8")


def leer_json(inst, rel):
    return json.loads(leer(inst, rel))


def sin_marca_html(texto):
    return texto.replace(f"<!-- {fn.MARCA} -->\n", "", 1)
