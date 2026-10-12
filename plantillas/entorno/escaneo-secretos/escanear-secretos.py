#!/usr/bin/env python3
"""Busca secretos en los archivos versionados (o en todos si no hay git). Solo lectura; sale con 1 si encuentra.
Un falso positivo se silencia agregando `# entorno:permitir` en esa línea."""
import pathlib
import re
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PATRONES = {
    "clave privada": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    "clave de acceso AWS": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "token de GitHub": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "token de API genérico": re.compile(r"(?i)\b(api[_-]?key|secret|token|passw(or)?d)\b\s*[:=]\s*['\"][A-Za-z0-9/+_\-]{16,}['\"]"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"),
    "URL con credenciales": re.compile(r"https?://[^/\s:@]+:[^/\s:@]{3,}@"),
}
IGNORAR_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".ico", ".woff", ".woff2", ".lock"}


def archivos():
    try:
        out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=RAIZ,
                             capture_output=True, text=True, check=True).stdout.split("\n")
        return [RAIZ / f for f in out if f]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in RAIZ.rglob("*") if p.is_file() and ".git" not in p.parts]


def main():
    hallazgos = []
    for p in archivos():
        if p.suffix.lower() in IGNORAR_EXT or not p.is_file() or p.name == pathlib.Path(__file__).name:
            continue
        try:
            for i, linea in enumerate(p.read_text(encoding="utf8").splitlines(), 1):
                if "entorno:permitir" in linea:
                    continue
                for nombre, pat in PATRONES.items():
                    if pat.search(linea):
                        hallazgos.append(f"{p.relative_to(RAIZ)}:{i}: {nombre}")
        except (OSError, UnicodeDecodeError):
            continue
    for h in hallazgos:
        print("SECRETO?", h)
    print(f"escaneo de secretos: {len(hallazgos)} hallazgo(s)")
    return 1 if hallazgos else 0


if __name__ == "__main__":
    sys.exit(main())
