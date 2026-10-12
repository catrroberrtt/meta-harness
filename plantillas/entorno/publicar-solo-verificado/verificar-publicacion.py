#!/usr/bin/env python3
"""Verifica un texto ANTES de publicarlo (cuerpo de PR, comentario, nota de versión). Solo lectura.

La marca de «verificado» queda atada al SHA-256 del texto: cualquier edición la invalida. Dos niveles:
  nivel 1  motor mecánico (este script): rutas y commits que existen, referencias declaradas que existen y en el estado
           que el texto afirma, secretos, marcas de relleno, casillas `[x]` sin evidencia.
  nivel 2  revisión independiente de las afirmaciones que ningún motor comprueba (la hace otra persona o un agente de
           solo lectura con docs/revisor-independiente.md); su informe se valida aquí.

Uso:
  verificar-publicacion.py revisar  <texto.md> [--repo DIR]      # nivel 1; escribe <texto>.afirmaciones.md
  verificar-publicacion.py confirmar <texto.md> <informe.md>     # nivel 2
  verificar-publicacion.py estado   <texto.md>
Salida: 0 pasa · 1 hay fallas · 2 error de uso.

De dónde sale la verdad de cada referencia (un ticket, un incidente, un documento) se declara en entorno.toml, en
[[publicar.referencias]]: un patrón, y un comando que recibe el identificador. Ver docs de entorno.toml.
"""
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time
import tomllib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SECRETOS = [re.compile(p) for p in (
    r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----", r"\bAKIA[0-9A-Z]{16}\b", r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    r"(?i)\b(api[_-]?key|secret|token|passw(or)?d)\b\s*[:=]\s*['\"][A-Za-z0-9/+_\-]{16,}['\"]", r"https?://[^/\s:@]+:[^/\s:@]{3,}@")]
RELLENO = re.compile(r"\bTODO\b|\bXXX\b|\bFIXME\b|<completar[^>]*>|\{\{[^}]*\}\}")


def config():
    try:
        return tomllib.loads((RAIZ / "entorno.toml").read_text(encoding="utf8")).get("publicar", {})
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def sha(texto):
    return hashlib.sha256(texto.encode("utf8")).hexdigest()


def ttl():
    return int(config().get("ttl_horas", 3)) * 3600


def ruta_marca(h):
    return RAIZ / ".entorno" / "verificado" / (h[:16] + ".json")


def leer_marca(texto):
    """Marca vigente del texto exacto (también con o sin salto de línea final: asi lo entrega un archivo)."""
    for t in (texto, texto + "\n", texto.strip(), texto.strip() + "\n"):
        try:
            d = json.loads(ruta_marca(sha(t)).read_text(encoding="utf8"))
            if d["sha"] == sha(t) and time.time() - d["ts"] <= ttl():
                return d
        except (OSError, ValueError, KeyError):
            continue
    return None


def escribir_marca(texto, nivel):
    previo = leer_marca(texto) or {"nivel": 0}
    ruta = ruta_marca(sha(texto))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"sha": sha(texto), "ts": time.time(), "nivel": max(previo["nivel"], nivel)}), encoding="utf8")


def correr(cmd, cwd):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=40)
        return r.returncode, r.stdout.strip()
    except (OSError, subprocess.SubprocessError) as e:
        return 1, str(e)


def revisar(texto, repo):
    fallas, avisos, ok = [], [], []
    lineas = texto.split("\n")
    # 1. relleno sin completar
    for i, l in enumerate(lineas, 1):
        if RELLENO.search(l):
            fallas.append(f"línea {i}: queda relleno sin completar («{RELLENO.search(l).group(0)}»)")
    # 2. rutas citadas existen
    rutas = 0
    for i, l in enumerate(lineas, 1):
        for t in re.findall(r"`([^`\s]+)`", l):
            if t.startswith(("http", "-", "$")) or any(c in t for c in "*<>=(){}|") or not ("/" in t or re.search(r"\.[A-Za-z0-9]{1,5}$", t)):
                continue
            rutas += 1
            if not (pathlib.Path(repo) / t.rstrip("/")).exists() and not re.search(r"\((nuevo|externo)\)", l):
                fallas.append(f"línea {i}: la ruta `{t}` no existe en el repo (si es nueva o externa, márcala con «(nuevo)» o «(externo)»)")
    ok.append(f"{rutas} ruta(s) citada(s) comprobada(s)")
    # 3. commits citados existen
    for i, l in enumerate(lineas, 1):
        for h in re.findall(r"`([0-9a-f]{7,40})`", l):
            if correr(["git", "cat-file", "-e", h + "^{commit}"], repo)[0] != 0:
                fallas.append(f"línea {i}: el commit `{h}` no existe en este repo")
    # 4. referencias declaradas: existen y su estado coincide con lo que el texto afirma
    for ref in config().get("referencias", []):
        patron, cmd = ref.get("patron"), ref.get("comprobar")
        if not patron or not cmd:
            continue
        cerrados = {e.upper() for e in ref.get("estados_cerrados", [])}
        vistos = {}
        for i, l in enumerate(lineas, 1):
            for m in re.finditer(patron, l):
                vistos.setdefault(m.group(0), []).append((i, l))
        for ident, apariciones in vistos.items():
            codigo, salida = correr([c.replace("{id}", ident) for c in cmd], repo)
            estado = (salida.splitlines() or [""])[0].strip()
            if codigo != 0:
                fallas.append(f"{ref.get('nombre', 'referencia')} {ident}: no se pudo comprobar en su fuente (código {codigo})")
                continue
            for i, l in apariciones:
                dice_abierto = re.search(r"(?i)pendiente|abiert|sin empezar|bloquea|por hacer", l)
                dice_cerrado = re.search(r"(?i)cerrad|terminad|resuelt|hech[oa]|listo", l)
                if cerrados and estado.upper() in cerrados and dice_abierto:
                    avisos.append(f"línea {i}: el texto trata {ident} como abierto pero su fuente dice «{estado}»")
                if cerrados and estado.upper() not in cerrados and dice_cerrado:
                    avisos.append(f"línea {i}: el texto trata {ident} como cerrado pero su fuente dice «{estado}»")
        if vistos:
            ok.append(f"{len(vistos)} {ref.get('nombre', 'referencia')}(s) comprobada(s) en su fuente")
    # 5. secretos
    for i, l in enumerate(lineas, 1):
        for p in SECRETOS:
            if p.search(l):
                fallas.append(f"línea {i}: parece un secreto; nunca va en un texto publicado")
    # 6. casillas marcadas sin evidencia
    for i, l in enumerate(lineas, 1):
        if re.match(r"^\s*[-*] \[[xX]\]", l) and not re.search(r"`|evidencia|https?://|#\d+", l):
            avisos.append(f"línea {i}: casilla marcada sin evidencia (comando, ruta, enlace o número)")
    # 7. fechas futuras
    hoy = dt.date.today()
    for i, l in enumerate(lineas, 1):
        for f in re.findall(r"\b(20\d\d-\d\d-\d\d)\b", l):
            try:
                if dt.date.fromisoformat(f) > hoy + dt.timedelta(days=1):
                    avisos.append(f"línea {i}: fecha futura {f}: ¿es un plazo o un error?")
            except ValueError:
                pass
    return fallas, avisos, ok


def afirmaciones(texto):
    """Líneas con datos comprobables que ningún motor verifica: las revisa otra persona o un agente independiente."""
    gat = re.compile(r"\d|ya |existe|coincide|comprob|verific|valid|pasa|probad|cerrad|pendiente|no hay|sin |siempre|nunca", re.I)
    out = []
    for l in texto.split("\n"):
        s = l.strip()
        if len(s) >= 25 and not s.startswith("#") and gat.search(s):
            out.append(re.sub(r"\s+", " ", s)[:400])
    return out[:70]


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("revisar", "confirmar", "estado"):
        print(__doc__)
        return 2
    cmd, ruta = a[0], pathlib.Path(a[1])
    if not ruta.is_file():
        print("No existe", ruta)
        return 2
    texto = ruta.read_text(encoding="utf8")
    h = sha(texto)[:12]
    if cmd == "estado":
        m = leer_marca(texto)
        print(f"sha {h} · " + (f"nivel {m['nivel']} vigente" if m else "SIN marca vigente"))
        return 0 if m else 1
    if cmd == "revisar":
        repo = a[a.index("--repo") + 1] if "--repo" in a else str(RAIZ)
        fallas, avisos, ok = revisar(texto, repo)
        for x in ok:
            print("  OK     " + x)
        for x in avisos:
            print("  AVISO  " + x)
        for x in fallas:
            print("  FALLA  " + x)
        cl = afirmaciones(texto)
        cab = f"HASH: {h}\nTEXTO: {ruta.resolve()}\nREPO: {pathlib.Path(repo).resolve()}\n"
        if avisos:
            cab += "AVISOS DEL MOTOR (el revisor debe resolver cada uno): " + " | ".join(x[:140] for x in avisos) + "\n"
        pathlib.Path(str(ruta) + ".afirmaciones.md").write_text(
            cab + "\n" + "\n".join(f"C{i + 1:02d}. {c}" for i, c in enumerate(cl)) + "\n", encoding="utf8")
        if fallas:
            print(f"\nNIVEL 1: NO PASA ({len(fallas)} fallas). Corrige el texto y vuelve a correr; no se publica.")
            print("Siguiente: una ruta nueva o ajena se marca con «(nuevo)» o «(externo)»; un estado que no coincide se corrige "
                  "en el texto o se confirma con la fuente; un secreto se quita del texto.")
            return 1
        escribir_marca(texto, 1)
        print(f"\nNIVEL 1: pasa (sha {h}). {len(cl)} afirmaciones para revisión independiente en {ruta}.afirmaciones.md "
              f"(guía: docs/revisor-independiente.md).")
        return 0
    if len(a) < 3 or not pathlib.Path(a[2]).is_file():
        print("Falta el informe del revisor independiente")
        return 2
    inf = pathlib.Path(a[2]).read_text(encoding="utf8")
    fallas = []
    if f"HASH: {h}" not in inf:
        fallas.append(f"el informe no corresponde a este texto (falta «HASH: {h}»)")
    ref, nov = re.search(r"REFUTADAS:\s*(\d+)", inf), re.search(r"NO_VERIFICABLES:\s*(\d+)", inf)
    if not ref or not nov:
        fallas.append("el informe no trae «REFUTADAS: n» y «NO_VERIFICABLES: n»")
    elif int(ref.group(1)) > 0:
        fallas.append(f"el revisor refutó {ref.group(1)} afirmación(es): corrige el texto (cambia el hash) y repite")
    esperadas, filas = len(afirmaciones(texto)), len(re.findall(r"^\|?\s*C\d\d\b", inf, re.M))
    if filas < esperadas:
        fallas.append(f"el informe cubre {filas} de {esperadas} afirmaciones")
    if not leer_marca(texto) or leer_marca(texto)["nivel"] < 1:
        fallas.append("falta el nivel 1 vigente: corre «revisar» primero")
    for x in fallas:
        print("  FALLA  " + x)
    if fallas:
        print("\nNIVEL 2: NO PASA.")
        return 1
    escribir_marca(texto, 2)
    print(f"NIVEL 2: pasa (sha {h}); {nov.group(1)} afirmación(es) NO VERIFICABLES: deben figurar en el texto como pendientes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
