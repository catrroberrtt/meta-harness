#!/usr/bin/env python3
"""Opción ERP: del negocio descrito en documentos locales a una propuesta de módulos del ERP estándar (SOLO LECTURA).

Lee una carpeta de documentos del negocio (.md, .txt, .rst, .csv, .tsv, .xlsx; sin red y sin conectores), deduce señales con reglas
simples y explicables (palabras clave ponderadas en `perfiles/_erp/senales.toml`, sin modelo de lenguaje) y las cruza con el catálogo
de módulos del ERP (`<erp-base>/modulos/catalogo.json`, SOLO LECTURA) para proponer: rubro, producto de partida, módulos (núcleo
siempre y cierre de requisitos incluido) con su **estado real** (hecho, parcial, en construcción, diseño, planeado), lo que aún no
existe, los opcionales ligados (sitio web, integraciones, correos) y la entrega al compositor.

NO instala ni copia nada del ERP: la composición real la hará el compositor del ERP (docs/OPCION-ERP.md). Reutiliza el lector de
entradas (herramientas/harness-leer-entradas.py: decodificación, lectura de hojas, topes y detección de secretos).

Uso: python3 harness-erp.py <carpeta-del-negocio> --erp-base <ruta> [--senales archivo.toml] [--json|--md]
Salida: 0 propuesta generada · 2 argumentos o entradas inválidos (carpeta o catálogo inexistente, señales mal formadas).
Mismo contenido y mismas señales => mismo resultado (sin fechas ni rutas absolutas). Solo biblioteca estándar."""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import sys
import tomllib
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SENALES_DEFECTO = RAIZ / "perfiles" / "_erp" / "senales.toml"
ESQUEMA = "meta-harness/propuesta-erp@1"
ESQUEMA_ENTREGA = "meta-harness/entrega-compositor@1"
SLUG_CAMBIO = "erp-composicion"
TEXTO_EXT = {".md", ".markdown", ".txt", ".rst"}
MAX_ARCHIVOS = 2000            # tope de archivos recorridos
MAX_TOTAL_BYTES = 40_000_000   # tope de bytes de texto leídos en total
MAX_LINEA = 5000               # caracteres analizados por línea
ESTADOS_REALES = {"hecho": "Hecho", "parcial": "Parcial", "en_construccion": "En construcción", "diseno": "Solo diseño", "planeado": "Planeado"}
EXISTE = {"hecho": "existe completo", "parcial": "existe en parte", "en_construccion": "en construcción (aún no se puede componer)",
          "diseno": "NO existe: solo hay diseño", "planeado": "NO existe: solo está planeado"}


class ErrorErp(Exception):
    """Entrada inválida: el mensaje dice qué falta y qué hacer."""


# ------------------------------------------------------------------ lector de entradas (reutilizado)
_LECTOR = {}


def cargar_lector(raiz=RAIZ):
    ruta = pathlib.Path(raiz) / "herramientas" / "harness-leer-entradas.py"
    if str(ruta) not in _LECTOR:
        if not ruta.is_file():
            raise ErrorErp(f"No encuentro el lector de entradas en {ruta}. Actualiza el harness (`harness update`) o indica la raíz con --harness.")
        esp = importlib.util.spec_from_file_location("harness_leer_entradas", ruta)
        mod = importlib.util.module_from_spec(esp)
        esp.loader.exec_module(mod)
        _LECTOR[str(ruta)] = mod
    return _LECTOR[str(ruta)]


def sin_tildes(texto):
    """Minúsculas y sin tildes, **conservando la longitud** (cada carácter se reemplaza por uno solo), para ubicar el fragmento original."""
    out = []
    for c in texto.lower():
        d = unicodedata.normalize("NFD", c)
        out.append(d[0] if d and not unicodedata.combining(d[0]) else c)
    return "".join(out)


def leer_documentos(carpeta, raiz=RAIZ):
    """Devuelve (documentos, no_leidos, avisos). documentos = [{archivo, lineas: [(n, texto)]}] ordenados; nunca escribe ni sigue enlaces."""
    lector = cargar_lector(raiz)
    carpeta = pathlib.Path(carpeta)
    docs, no_leidos, avisos = [], [], []
    vistos, total = 0, 0
    for base, dirs, files in os.walk(carpeta, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in lector.EXCLUIR_DIRS and not d.startswith("."))
        for nombre in sorted(files):
            if nombre.startswith("."):
                continue
            p = pathlib.Path(base) / nombre
            rel = p.relative_to(carpeta).as_posix()
            vistos += 1
            if vistos > MAX_ARCHIVOS:
                avisos.append(f"Se alcanzó el tope de {MAX_ARCHIVOS} archivos: el resto no se recorrió. Apunta a una carpeta más acotada.")
                return docs, no_leidos, avisos
            ext = p.suffix.lower()
            if p.is_symlink():
                no_leidos.append({"archivo": rel, "razon": "enlace simbólico (no se sigue)"})
                continue
            if ext not in TEXTO_EXT and ext not in lector.TABULARES:
                razon, _ = lector.razon_no_leido(p)
                no_leidos.append({"archivo": rel, "razon": razon})
                continue
            try:
                tam = p.stat().st_size
            except OSError as e:
                no_leidos.append({"archivo": rel, "razon": f"no se pudo leer ({e.__class__.__name__})"})
                continue
            if tam > lector.MAX_BYTES:
                no_leidos.append({"archivo": rel, "razon": f"supera el tope de lectura de {lector.MAX_BYTES} bytes"})
                continue
            if total + tam > MAX_TOTAL_BYTES:
                no_leidos.append({"archivo": rel, "razon": "se alcanzó el tope total de lectura"})
                continue
            if ext in lector.TABULARES:
                hojas, err = lector.leer_tabular(p)
                if err:
                    no_leidos.append({"archivo": rel, "razon": err[0]})
                    continue
                lineas = []
                for h in hojas:
                    for n, celdas in h["filas"]:
                        fila = " | ".join("[enmascarado]" if lector.secreto_valor(c) else c for c in celdas if c)
                        if fila:
                            lineas.append((n, fila))
                if not lineas:
                    no_leidos.append({"archivo": rel, "razon": "sin contenido"})
                    continue
                total += tam
                docs.append({"archivo": rel, "lineas": lineas})
                continue
            try:
                datos = p.read_bytes()
            except OSError as e:
                no_leidos.append({"archivo": rel, "razon": f"no se pudo leer ({e.__class__.__name__})"})
                continue
            if b"\x00" in datos[:8192] and not datos.startswith((b"\xff\xfe", b"\xfe\xff")):
                no_leidos.append({"archivo": rel, "razon": "contenido binario (no es texto)"})
                continue
            texto, _cod = lector.decodificar(datos)
            lineas = [(n, l) for n, l in enumerate(texto.splitlines(), 1) if l.strip()]
            if not lineas:
                no_leidos.append({"archivo": rel, "razon": "sin contenido"})
                continue
            total += tam
            docs.append({"archivo": rel, "lineas": lineas})
    return docs, no_leidos, avisos


# ------------------------------------------------------------------ señales (datos editables)
def cargar_senales(ruta=SENALES_DEFECTO):
    ruta = pathlib.Path(ruta)
    if not ruta.is_file():
        raise ErrorErp(f"No existe el archivo de señales {ruta}.")
    try:
        cfg = tomllib.loads(ruta.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError) as e:
        raise ErrorErp(f"El archivo de señales {ruta.name} no se pudo leer: {e}")
    um = {"senal": 3, "rubro": 5, "max_por_termino_y_archivo": 3, "evidencia_max": 3, "fragmento_max": 140}
    um.update(cfg.get("umbrales", {}))
    reglas = []
    for clase in ("rubro", "senal"):
        for rid, r in cfg.get(clase, {}).items():
            terminos = []
            for t in r.get("terminos", []):
                if not (isinstance(t, list) and len(t) == 2 and isinstance(t[0], str) and isinstance(t[1], int) and t[1] > 0):
                    raise ErrorErp(f"Señales: en [{clase}.{rid}] cada término debe ser [\"texto\", peso entero > 0]; encontré {t!r}.")
                toks = tokens_de(sin_tildes(t[0]))
                if not toks:
                    raise ErrorErp(f"Señales: el término {t[0]!r} de [{clase}.{rid}] no tiene letras ni números.")
                terminos.append({"texto": t[0], "tokens": tuple(toks), "peso": t[1]})
            if not terminos:
                raise ErrorErp(f"Señales: [{clase}.{rid}] no tiene términos.")
            reglas.append({"clase": clase, "id": rid, "etiqueta": r.get("etiqueta", rid), "modulos": list(r.get("modulos", [])),
                           "producto": r.get("producto"), "perfil": r.get("perfil"), "opcional": r.get("opcional"), "aviso": r.get("aviso"),
                           "umbral": int(r.get("umbral", um["rubro"] if clase == "rubro" else um["senal"])), "terminos": terminos})
    if not reglas:
        raise ErrorErp(f"El archivo de señales {ruta.name} no define ningún rubro ni señal.")
    return {"version": cfg.get("version", 1), "umbrales": um, "reglas": reglas, "archivo": ruta.name}


RX_TOKEN = re.compile(r"[a-z0-9&]+")


def tokens_de(norm):
    return [m.group(0) for m in RX_TOKEN.finditer(norm)]


def _coincide(tok, tt):
    return tok == tt or tok == tt + "s" or tok == tt + "es"


def construir_indice(reglas):
    """{primer token del término: [(tokens, regla, término)]}; el texto se busca por tokens, con plural simple."""
    idx = {}
    for r in reglas:
        for t in r["terminos"]:
            idx.setdefault(t["tokens"][0], []).append((t["tokens"], r, t))
    return idx


def fragmento(linea, ini, fin, maximo, lector):
    marg = max(10, (maximo - (fin - ini)) // 2)
    a, b = max(0, ini - marg), min(len(linea), fin + marg)
    frag = " ".join(linea[a:b].split())
    frag = lector.RX_SECRETO_KV.sub("[enmascarado]", frag)
    if len(frag) > maximo:
        frag = frag[:maximo].rstrip()
    return ("…" if a > 0 else "") + frag + ("…" if b < len(linea) else "")


def evaluar(docs, cfg, raiz=RAIZ):
    """Cuenta coincidencias y suma puntos por regla. Devuelve {(clase, id): {puntos, evidencia[], archivos}}."""
    lector = cargar_lector(raiz)
    um = cfg["umbrales"]
    idx = construir_indice(cfg["reglas"])
    cuentas = {}   # (clase, id, término, archivo) -> [n, [evidencias]]
    for doc in docs:
        for n, linea in doc["lineas"]:
            linea = linea[:MAX_LINEA]
            norm = sin_tildes(linea)
            toks = [(m.group(0), m.start(), m.end()) for m in RX_TOKEN.finditer(norm)]
            for i, (tok, ini, fin) in enumerate(toks):
                bases = {tok}
                if tok.endswith("s"):
                    bases.add(tok[:-1])
                if tok.endswith("es"):
                    bases.add(tok[:-2])
                for base in bases:
                    for tokens, r, t in idx.get(base, ()):
                        if not _coincide(tok, tokens[0]):
                            continue
                        if i + len(tokens) > len(toks):
                            continue
                        ok, fin_t = True, fin
                        for k in range(1, len(tokens)):
                            tk, a2, b2 = toks[i + k]
                            gap = norm[fin_t:a2]
                            if not _coincide(tk, tokens[k]) or not re.fullmatch(r"[\s\-_/]*", gap):
                                ok = False
                                break
                            fin_t = b2
                        if not ok:
                            continue
                        clave = (r["clase"], r["id"], t["texto"], doc["archivo"])
                        c = cuentas.setdefault(clave, [0, []])
                        c[0] += 1
                        if len(c[1]) < 1:
                            c[1].append({"archivo": doc["archivo"], "linea": n, "termino": t["texto"], "peso": t["peso"],
                                         "fragmento": fragmento(linea, ini, fin_t, um["fragmento_max"], lector)})
    res = {}
    pesos = {(r["clase"], r["id"], t["texto"]): t["peso"] for r in cfg["reglas"] for t in r["terminos"]}
    for (clase, rid, termino, archivo), (n, evs) in cuentas.items():
        e = res.setdefault((clase, rid), {"puntos": 0, "candidatas": [], "archivos": set()})
        e["puntos"] += pesos[(clase, rid, termino)] * min(n, um["max_por_termino_y_archivo"])
        e["candidatas"] += evs
        e["archivos"].add(archivo)
    for e in res.values():
        e["candidatas"].sort(key=lambda x: (-x["peso"], x["archivo"], x["linea"], x["termino"]))
        elegidas, usados = [], set()
        for ev in e["candidatas"]:   # primero evidencias de términos y archivos distintos
            if (ev["archivo"], ev["termino"]) not in usados and len(elegidas) < um["evidencia_max"]:
                usados.add((ev["archivo"], ev["termino"]))
                elegidas.append(ev)
        e["evidencia"] = [{k: v for k, v in ev.items() if k != "peso"} for ev in elegidas]
        e["archivos"] = sorted(e["archivos"])
        del e["candidatas"]
    return res


# ------------------------------------------------------------------ catálogo del ERP (SOLO LECTURA)
def cargar_catalogo(erp_base):
    base = pathlib.Path(erp_base)
    ruta = base / "modulos" / "catalogo.json"
    if not ruta.is_file():
        raise ErrorErp(f"No encuentro el catálogo de módulos del ERP en «modulos/catalogo.json» dentro de {base}.\n"
                       "Indica la carpeta del repositorio del ERP estándar con --erp-base <ruta> (se lee, nunca se escribe).")
    datos = ruta.read_bytes()
    try:
        cat = json.loads(datos.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise ErrorErp(f"El catálogo del ERP no es un JSON válido ({e.__class__.__name__}).")
    if not isinstance(cat, dict) or not isinstance(cat.get("modulos"), list) or not cat["modulos"]:
        raise ErrorErp("El catálogo del ERP no tiene la forma esperada: falta la lista «modulos».")
    modulos, orden = {}, []
    for m in cat["modulos"]:
        if not isinstance(m, dict) or "id" not in m or "estado" not in m:
            raise ErrorErp("El catálogo del ERP tiene un módulo sin «id» o sin «estado».")
        modulos[m["id"]] = m
        orden.append(m["id"])
    return {"version": cat.get("version"), "sha256": hashlib.sha256(datos).hexdigest(), "modulos": modulos, "orden": orden,
            "productos": {p["id"]: p for p in cat.get("productos", []) if isinstance(p, dict) and "id" in p}}


def validar_senales(cfg, catalogo):
    """Avisos (no errores) por módulos o productos de las señales que el catálogo leído no tiene (un catálogo más viejo o más corto)."""
    faltan, productos = [], []
    for r in cfg["reglas"]:
        faltan += [m for m in r["modulos"] if m not in catalogo["modulos"] and m not in faltan]
        if r["producto"] and r["producto"] not in catalogo["productos"] and r["producto"] not in productos:
            productos.append(r["producto"])
    av = []
    if faltan:
        av.append(f"{len(faltan)} módulo(s) de las señales no están en este catálogo y se ignoran: " + ", ".join(faltan[:8]) + (" …" if len(faltan) > 8 else "") + ".")
    if productos:
        av.append("Producto(s) de rubro que no están en este catálogo y se ignoran: " + ", ".join(productos) + ".")
    return av


# ------------------------------------------------------------------ composición
def _recorta(textos, n=5, largo=160):
    return [t if len(t) <= largo else t[:largo - 1].rstrip() + "…" for t in textos[:n]]


def proponer(docs, no_leidos, avisos_lectura, cfg, cat, ev, marca_en_instancia=None):
    um = cfg["umbrales"]
    avisos = list(avisos_lectura) + validar_senales(cfg, cat)
    reglas = {(r["clase"], r["id"]): r for r in cfg["reglas"]}
    # rubro
    cand = []
    for r in cfg["reglas"]:
        if r["clase"] == "rubro":
            e = ev.get(("rubro", r["id"]))
            if e:
                cand.append((r, e))
    cand.sort(key=lambda x: -x[1]["puntos"])   # estable: empate => el primero del archivo
    rubro = None
    if cand and cand[0][1]["puntos"] >= cand[0][0]["umbral"]:
        r, e = cand[0]
        rubro = {"id": r["id"], "etiqueta": r["etiqueta"], "puntos": e["puntos"], "evidencia": e["evidencia"],
                 "alternativas": [{"id": r2["id"], "etiqueta": r2["etiqueta"], "puntos": e2["puntos"]} for r2, e2 in cand[1:4]]}
        rubro["_regla"] = r
    # señales
    senales, debiles, opcionales = [], [], []
    seleccion = {}   # módulo -> [ids de señal]
    for r in cfg["reglas"]:
        if r["clase"] != "senal":
            continue
        e = ev.get(("senal", r["id"]))
        if not e:
            continue
        incluida = e["puntos"] >= r["umbral"]
        item = {"id": r["id"], "etiqueta": r["etiqueta"], "puntos": e["puntos"], "umbral": r["umbral"], "incluida": incluida,
                "confianza": "alta" if e["puntos"] >= 2 * r["umbral"] else "media", "modulos": [m for m in r["modulos"] if m in cat["modulos"]],
                "archivos": e["archivos"], "evidencia": e["evidencia"]}
        if incluida:
            senales.append(item)
            for m in item["modulos"]:
                seleccion.setdefault(m, []).append(r["id"])
            if r["opcional"]:
                opcionales.append({"id": r["opcional"], "senal": r["id"], "ofrecido": True, "ejecutado": False,
                                   "motivo": f"Los documentos mencionan «{r['etiqueta']}» ({e['puntos']} puntos).", "evidencia": e["evidencia"]})
            if r["aviso"]:
                avisos.append(r["aviso"])
        else:
            debiles.append({k: item[k] for k in ("id", "etiqueta", "puntos", "umbral", "modulos", "evidencia")})
    # núcleo + señales + cierre de requisitos
    nucleo = [m for m in cat["orden"] if cat["modulos"][m].get("nucleo")]
    requeridos_por = {}
    final = set(nucleo) | set(seleccion)
    cola = sorted(final, key=cat["orden"].index)
    while cola:
        m = cola.pop(0)
        for q in cat["modulos"][m].get("requiere", []):
            if q not in cat["modulos"]:
                avisos.append(f"El módulo «{m}» requiere «{q}», que no está en el catálogo: revisar el catálogo del ERP.")
                continue
            requeridos_por.setdefault(q, [])
            if m not in requeridos_por[q]:
                requeridos_por[q].append(m)
            if q not in final:
                final.add(q)
                cola.append(q)
    producto = cat["productos"].get(rubro["_regla"]["producto"]) if rubro and rubro["_regla"]["producto"] else None
    en_producto = set(producto["modulos"]) if producto else set()
    modulos = []
    for mid in cat["orden"]:
        if mid not in final:
            continue
        m = cat["modulos"][mid]
        origen = "nucleo" if mid in nucleo else ("senal" if mid in seleccion else "requisito")
        item = {"id": mid, "nombre": m.get("nombre", mid), "area": m.get("area", ""), "estado": m["estado"], "fase": m.get("fase", ""),
                "origen": origen, "senales": seleccion.get(mid, []), "requerido_por": sorted(requeridos_por.get(mid, []), key=cat["orden"].index),
                "requiere": list(m.get("requiere", [])), "en_producto_de_partida": mid in en_producto}
        if m.get("pendiente"):
            item["pendiente"] = _recorta(list(m["pendiente"]) if isinstance(m["pendiente"], list) else [str(m["pendiente"])])
        modulos.append(item)
    ids = [m["id"] for m in modulos]
    sin_senal = []
    for mid in (producto["modulos"] if producto else []):
        if mid in cat["modulos"] and mid not in final:
            sin_senal.append({"id": mid, "nombre": cat["modulos"][mid].get("nombre", mid), "estado": cat["modulos"][mid]["estado"]})
    no_existe = [{"id": m["id"], "nombre": m["nombre"], "estado": m["estado"], "fase": m["fase"], "origen": m["origen"],
                  "por_que": ("lo piden tus documentos" if m["origen"] == "senal" else "lo requiere " + ", ".join(m["requerido_por"]) if m["origen"] == "requisito" else "núcleo")}
                 for m in modulos if m["estado"] in ("en_construccion", "diseno", "planeado")]
    parciales = [{"id": m["id"], "nombre": m["nombre"], "fase": m["fase"], "pendiente": m.get("pendiente", [])} for m in modulos if m["estado"] == "parcial"]
    recuento = {e: sum(1 for m in modulos if m["estado"] == e) for e in ESTADOS_REALES}
    if not senales:
        avisos.append("No se encontró ninguna señal con puntos suficientes: la propuesta es solo el núcleo. Revisa que la carpeta tenga los documentos del negocio "
                      "(procesos, áreas, documentos que emiten) o ajusta las palabras en el archivo de señales.")
    if not rubro:
        avisos.append("No se pudo elegir un producto de partida (ningún rubro llega al umbral): la composición sería «a medida», con los módulos de las señales.")
    sin_codigo = [m["id"] for m in modulos if m["estado"] in ("en_construccion", "diseno", "planeado")]
    if sin_codigo:
        avisos.append(f"{len(sin_codigo)} de {len(modulos)} módulos propuestos NO existen aún en el ERP central (planeados, en diseño o en construcción): no se prometen.")
    perfil_id = rubro["_regla"]["perfil"] if rubro and rubro["_regla"]["perfil"] else None
    pc = cat["modulos"].get("perfiles-configuracion")
    perfil = {"id": perfil_id, "origen": "rubro" if perfil_id else "ninguno",
              "nota": ("Nombre del perfil de configuración (qué funciones nacen encendidas o apagadas); su contenido lo define el ERP"
                       + (f" y el módulo «perfiles-configuracion» está {EXISTE.get(pc['estado'], pc['estado'])}." if pc else ".")) if perfil_id
              else "Sin rubro claro: no se sugiere perfil; las funciones nacen con sus valores seguros por defecto."}
    componibles = [m["id"] for m in modulos if m["estado"] in ("hecho", "parcial")]
    pendientes = [m["id"] for m in modulos if m["estado"] not in ("hecho", "parcial")]
    entrega = {
        "esquema": ESQUEMA_ENTREGA,
        "estado_del_compositor": "no existe aún (diseño en docs/COMPOSICION.md del ERP): este objeto es el contrato que recibirá",
        "producto": producto["id"] if producto else "a-medida",
        "modulos": ids,
        "perfil": perfil_id,
        "componibles_hoy": componibles,
        "sin_codigo_aun": pendientes,
        "marca": {"fuente": "sitio/DISENO.md", "en_instancia": marca_en_instancia, "datos_de_marca_en_este_archivo": False},
        "catalogo": {"archivo": "modulos/catalogo.json", "version": cat["version"], "sha256": cat["sha256"]},
        "invocacion_prevista": "scripts/componer-erp.mjs --producto <modulos separados por coma> --destino <carpeta> --perfil <archivo>",
    }
    p = {
        "esquema": ESQUEMA,
        "senales_archivo": {"nombre": cfg["archivo"], "version": cfg["version"]},
        "catalogo": {"archivo": "modulos/catalogo.json", "version": cat["version"], "sha256": cat["sha256"]},
        "documentos": {"leidos": len(docs), "lineas": sum(len(d["lineas"]) for d in docs), "no_leidos": no_leidos},
        "rubro": {k: v for k, v in rubro.items() if k != "_regla"} if rubro else None,
        "producto_partida": ({"id": producto["id"], "nombre": producto.get("nombre", producto["id"]), "modulos_sin_senal": sin_senal} if producto
                             else {"id": "a-medida", "nombre": "A medida", "modulos_sin_senal": []}),
        "perfil_configuracion": perfil,
        "modulos": modulos,
        "resumen": {"modulos": len(modulos), "nucleo": sum(1 for m in modulos if m["origen"] == "nucleo"),
                    "por_senal": sum(1 for m in modulos if m["origen"] == "senal"), "por_requisito": sum(1 for m in modulos if m["origen"] == "requisito"),
                    "por_estado": recuento},
        "no_existe_aun": no_existe,
        "existe_en_parte": parciales,
        "senales": senales,
        "senales_debiles": debiles,
        "opcionales": opcionales,
        "avisos": avisos,
        "entrega_al_compositor": entrega,
    }
    p["trazabilidad"] = trazabilidad(p)
    return p


def trazabilidad(p):
    """Una fila por módulo propuesto: RQ-NN, módulo, señal que lo justifica (con su mejor evidencia) y estado en el catálogo."""
    por_senal = {s["id"]: s for s in p["senales"]}
    filas, n = [], 0
    for m in p["modulos"]:
        n += 1
        if m["origen"] == "nucleo":
            just = "núcleo: siempre"
            ev = None
        elif m["origen"] == "senal":
            s = por_senal[m["senales"][0]]
            ev = s["evidencia"][0] if s["evidencia"] else None
            just = f"señal «{s['etiqueta']}» ({s['puntos']} puntos)"
        else:
            just = "requisito de " + ", ".join(m["requerido_por"])
            ev = None
        filas.append({"requisito": f"RQ-{n:02d}", "modulo": m["id"], "justificacion": just,
                      "evidencia": f"{ev['archivo']}:{ev['linea']}" if ev else None, "estado_catalogo": m["estado"], "fase": m["fase"]})
    return filas


# ------------------------------------------------------------------ salidas legibles
def _c(t):
    return str(t).replace("|", "/").replace("\n", " ")


def a_md(p):
    L = ["# Propuesta de ERP para el negocio", "",
         "<!-- Generado por `harness erp` a partir de los documentos del negocio. Es una propuesta de lectura: no instala ni copia nada del ERP. Para cambiarla, ajusta los documentos o las señales y vuelve a correr el comando. -->", ""]
    r = p["resumen"]
    e = r["por_estado"]
    L += ["## Resumen", "",
          f"- Documentos leídos: {p['documentos']['leidos']} ({p['documentos']['lineas']} líneas); no leídos: {len(p['documentos']['no_leidos'])}.",
          f"- Rubro: " + (f"**{p['rubro']['etiqueta']}** ({p['rubro']['puntos']} puntos)" if p["rubro"] else "no se pudo determinar") + ".",
          f"- Producto de partida: **{p['producto_partida']['nombre']}** (`{p['producto_partida']['id']}`).",
          f"- Módulos propuestos: **{r['modulos']}** (núcleo {r['nucleo']} · por señal {r['por_senal']} · por requisito {r['por_requisito']}).",
          f"- Estado real hoy: {e['hecho']} hechos · {e['parcial']} parciales · {e['en_construccion']} en construcción · {e['diseno']} en diseño · {e['planeado']} planeados.", ""]
    L += ["## Lo que aún NO existe en el ERP central", ""]
    if p["no_existe_aun"]:
        L += ["No se promete lo que solo está planeado o en construcción. Se incluye en la propuesta porque el negocio lo pide o porque otro módulo lo requiere, pero **hoy no hay código** que componer.", "",
              "| Módulo | Estado real | Fase | Por qué aparece |", "|---|---|---|---|"]
        for m in p["no_existe_aun"]:
            L.append(f"| {_c(m['nombre'])} (`{m['id']}`) | {EXISTE.get(m['estado'], m['estado'])} | {m['fase']} | {_c(m['por_que'])} |")
    else:
        L.append("Todos los módulos propuestos existen hoy.")
    if p["existe_en_parte"]:
        L += ["", "## Lo que existe solo en parte", "",
              "Estos módulos tienen código, pero el catálogo del ERP los marca «parcial»: se componen con lo que existe hoy.", ""]
        for m in p["existe_en_parte"]:
            L.append(f"- {m['nombre']} (`{m['id']}`, fase {m['fase']})" + (f" · pendiente: {_c('; '.join(m['pendiente'][:3]))}" if m["pendiente"] else ""))
    L += ["", "## Módulos propuestos", "", "| Módulo | Estado real | Origen | Por qué |", "|---|---|---|---|"]
    por_senal = {s["id"]: s for s in p["senales"]}
    for m in p["modulos"]:
        if m["origen"] == "nucleo":
            por = "Núcleo: va en todas las instalaciones"
        elif m["origen"] == "senal":
            por = "Señal: " + ", ".join(f"«{por_senal[s]['etiqueta']}»" for s in m["senales"])
        else:
            por = "Lo requiere: " + ", ".join(f"`{x}`" for x in m["requerido_por"])
        L.append(f"| {_c(m['nombre'])} (`{m['id']}`) | {ESTADOS_REALES.get(m['estado'], m['estado'])}" + (f" · {m['fase']}" if m['fase'] else "") + f" | {m['origen']} | {_c(por)} |")
    L += ["", "## Señales encontradas (con evidencia)", ""]
    if not p["senales"]:
        L.append("Ninguna llegó al umbral.")
    for s in p["senales"]:
        L.append(f"### {s['etiqueta']} · {s['puntos']} puntos · confianza {s['confianza']}")
        L.append("")
        L.append("Módulos: " + (", ".join(f"`{m}`" for m in s["modulos"]) if s["modulos"] else "ninguno (es un opcional)"))
        L.append("")
        for ev in s["evidencia"]:
            L.append(f"- `{ev['archivo']}:{ev['linea']}` · término «{ev['termino']}» · «{ev['fragmento']}»")
        L.append("")
    if p["rubro"]:
        L += ["### Rubro", ""]
        for ev in p["rubro"]["evidencia"]:
            L.append(f"- `{ev['archivo']}:{ev['linea']}` · término «{ev['termino']}» · «{ev['fragmento']}»")
        if p["rubro"]["alternativas"]:
            L.append("- Otros rubros posibles: " + ", ".join(f"{a['etiqueta']} ({a['puntos']})" for a in p["rubro"]["alternativas"]))
        L.append("")
    if p["senales_debiles"]:
        L += ["## Señales débiles (no incluidas)", "", "Aparecen en los documentos pero sin puntos suficientes. Si el negocio sí lo necesita, confirma y vuelve a correr con más documentos.", ""]
        for s in p["senales_debiles"]:
            ev = s["evidencia"][0] if s["evidencia"] else None
            L.append(f"- {s['etiqueta']}: {s['puntos']} de {s['umbral']} puntos" + (f" · `{ev['archivo']}:{ev['linea']}`" if ev else ""))
        L.append("")
    if p["producto_partida"]["modulos_sin_senal"]:
        L += ["## Del producto de partida, sin señal en los documentos", "",
              "El producto de partida los incluye, pero los documentos no los piden: **no están en la propuesta**. Confirma cuáles necesitas.", ""]
        for m in p["producto_partida"]["modulos_sin_senal"]:
            L.append(f"- {m['nombre']} (`{m['id']}`) · {ESTADOS_REALES.get(m['estado'], m['estado'])}")
        L.append("")
    L += ["## Opcionales ligados (se ofrecen, no se ejecutan)", ""]
    if p["opcionales"]:
        for o in p["opcionales"]:
            L.append(f"- **Adaptador `{o['id']}`**: {o['motivo']} Para sitio web o landing: `python3 herramientas/web-detectar-herramienta.py`, "
                     "luego `plantillas/web/brief-landing.md` y `adaptadores/diseno-web/README.md`. No se ejecutó nada.")
    else:
        L.append("- Sitio web o landing: sin señal en los documentos.")
    por_id = {m["id"] for m in p["modulos"]}
    if "integraciones" in por_id:
        L.append("- **Integraciones**: los documentos las mencionan; el módulo de integraciones aún no existe, así que cada conexión se especifica aparte.")
    if "notificaciones" in por_id:
        L.append("- **Correos y avisos**: los documentos los mencionan; el módulo de notificaciones es parcial (avisos en pantalla hoy).")
    L += ["", "## Avisos", ""]
    L += [f"- {_c(a)}" for a in p["avisos"]] or ["- Ninguno."]
    if p["documentos"]["no_leidos"]:
        L += ["", "## Documentos no leídos", ""]
        L += [f"- `{x['archivo']}`: {x['razon']}" for x in p["documentos"]["no_leidos"][:20]]
        if len(p["documentos"]["no_leidos"]) > 20:
            L.append(f"- … y {len(p['documentos']['no_leidos']) - 20} más.")
    L += ["", "## Trazabilidad: módulo, señal y estado", "",
          f"Cada fila es un requisito de `cambios/{SLUG_CAMBIO}/especificacion.md` y una fila de `cambios/{SLUG_CAMBIO}/matriz.md` (`harness trazar cambios/{SLUG_CAMBIO} --etapa especificacion`).", "",
          "| Requisito | Módulo | Señal que lo justifica | Evidencia | Estado en el catálogo |", "|---|---|---|---|---|"]
    for t in p["trazabilidad"]:
        L.append(f"| {t['requisito']} | `{t['modulo']}` | {_c(t['justificacion'])} | {t['evidencia'] or '—'} | {ESTADOS_REALES.get(t['estado_catalogo'], t['estado_catalogo'])} |")
    L += ["", "## Entrega al compositor (resumen)", "",
          "El detalle y el JSON completo están en `docs/OPCION-ERP.md` y `erp/propuesta-erp.json` (`entrega_al_compositor`).", "",
          f"- Producto: `{p['entrega_al_compositor']['producto']}` · perfil: " + (f"`{p['entrega_al_compositor']['perfil']}`" if p["entrega_al_compositor"]["perfil"] else "ninguno"),
          f"- Módulos ({len(p['entrega_al_compositor']['modulos'])}): " + ", ".join(f"`{m}`" for m in p["entrega_al_compositor"]["modulos"]),
          f"- Sin código aún (el compositor no puede entregarlos): " + (", ".join(f"`{m}`" for m in p["entrega_al_compositor"]["sin_codigo_aun"]) or "ninguno"),
          "- Datos de marca: salen de la ficha `sitio/DISENO.md` de la instancia; este archivo no los lleva.", "",
          "## Lo que esta propuesta no hace", "",
          "- No instala ni copia nada del ERP: el compositor del ERP aún no existe.",
          "- No decide por ti: las señales son palabras de tus documentos; confirma, quita o agrega módulos antes de componer.",
          "- No usa la red ni un modelo de lenguaje: mismas entradas, misma propuesta.", ""]
    return "\n".join(L)


def especificacion_md(p):
    n_mod = len(p["modulos"])
    L = ["# Especificación — Composición del ERP para el negocio", "",
         "<!-- Generada por `harness erp` desde propuesta-erp.json. Es el punto de partida: se edita a mano; el comando no la vuelve a pisar. -->", "",
         "## Contexto", "",
         f"Problema: el negocio necesita un ERP con solo los módulos que usa · Alcance: componer {n_mod} módulos del ERP estándar (producto de partida «{p['producto_partida']['id']}») · "
         "Fuera de alcance: copiar o instalar el ERP (lo hace el compositor del ERP) y construir los módulos que aún no existen · Tamaño: M", "",
         "## Suposiciones", ""]
    sus, rq = [], []
    n_su = 0

    def su(nivel, texto, origen):
        nonlocal n_su
        n_su += 1
        sus.append(f"- SU-{n_su:02d} · {nivel} · {texto} · origen: {origen}")

    if p["rubro"]:
        su("de-trabajo", f"El rubro es «{p['rubro']['etiqueta']}» y el producto de partida es «{p['producto_partida']['id']}»; confirmar con la persona", "propuesta-erp.json (rubro)")
    else:
        su("abierto", "Ningún rubro llegó al umbral: ¿qué producto de partida corresponde, o se compone a medida?", "propuesta-erp.json (rubro)")
    for m in p["modulos"]:
        if m["estado"] in ("planeado", "diseno", "en_construccion"):
            su("abierto", f"El módulo `{m['id']}` está «{m['estado']}» en el catálogo (fase {m['fase']}) y no tiene código: ¿se espera su construcción o se compone sin él?", "modulos/catalogo.json del ERP")
        elif m["estado"] == "parcial":
            su("de-trabajo", f"El módulo `{m['id']}` es parcial en el catálogo: se compone con lo que existe hoy", "modulos/catalogo.json del ERP")
    for s in p["senales"]:
        if s["confianza"] == "media" and s["modulos"]:
            su("de-trabajo", f"La señal «{s['etiqueta']}» tiene {s['puntos']} puntos (cerca del umbral {s['umbral']}); confirmar que el negocio usa " + ", ".join(f"`{x}`" for x in s["modulos"]),
               f"{s['evidencia'][0]['archivo']}:{s['evidencia'][0]['linea']}" if s["evidencia"] else "propuesta-erp.json")
    L += sus or ["- Ninguna."]
    L += ["", "## Requisitos", ""]
    por_senal = {s["id"]: s for s in p["senales"]}
    for i, m in enumerate(p["modulos"], 1):
        t = p["trazabilidad"][i - 1]
        if m["origen"] == "nucleo":
            motivo = "el núcleo va en todas las instalaciones"
        elif m["origen"] == "senal":
            s = por_senal[m["senales"][0]]
            motivo = f"los documentos del negocio piden «{s['etiqueta']}» ({s['puntos']} puntos)"
        else:
            motivo = "lo requiere " + ", ".join(f"`{x}`" for x in m["requerido_por"])
        L.append(f"- {t['requisito']} · Cuando se componga la instalación, el sistema incluirá el módulo «{m['nombre']}» (`{m['id']}`), porque {motivo}.")
        L.append(f"  - CA-{t['requisito'][3:]}.1 · Dado el producto propuesto, cuando el compositor del ERP resuelve la lista de módulos, entonces `erp.lock.json` incluye `{m['id']}` con el estado «{m['estado']}» del catálogo.")
    L += ["", "## Desafío previo (M y L)", "",
          "- Cómo falla esto: se compone un módulo que solo está planeado y la instalación sale sin él, sin que la persona lo note.",
          "- Qué suposición lo rompería: " + (next((f"SU-{k:02d}" for k, l in enumerate(sus, 1) if " abierto " in l), "SU-01")) + ".",
          "- Alternativa descartada y por qué: instalar el ERP completo y apagar módulos; el estándar compone solo lo que el negocio necesita.", "",
          "## Decisiones", "",
          "- La propuesta sale de reglas de palabras (perfiles/_erp/senales.toml), sin modelo de lenguaje; la persona confirma antes de componer.", "",
          "## Aprobación", "",
          "- [ ] OK explícito de la persona dueña del negocio (pendiente)", ""]
    return "\n".join(L)


def matriz_md(p):
    por_senal = {s["id"]: s for s in p["senales"]}
    L = ["# Matriz de trazabilidad — Composición del ERP", "",
         "<!-- Generada por `harness erp`. Una fila por módulo propuesto: requisito, criterio, y en la nota la señal y el estado real en el catálogo. Se completa al componer y verificar. -->", "",
         "| Requisito | Criterio | Prueba | Rojo→verde | Commit | Evidencia | Estado | Nota |", "|---|---|---|---|---|---|---|---|"]
    for t, m in zip(p["trazabilidad"], p["modulos"]):
        num = t["requisito"][3:]
        if m["origen"] == "senal":
            s = por_senal[m["senales"][0]]
            sen = f"señal {s['id']}" + (f" ({s['evidencia'][0]['archivo']}:{s['evidencia'][0]['linea']})" if s["evidencia"] else "")
        elif m["origen"] == "requisito":
            sen = "requisito de " + ", ".join(m["requerido_por"])
        else:
            sen = "núcleo"
        L.append(f"| {t['requisito']} | CA-{num}.1 | erp.lock.json lo lista (lo comprueba el compositor, aún no existe) | n/a | - | - | pendiente | {_c(sen)}; catálogo: {m['estado']} |")
    L.append("")
    return "\n".join(L)


# ------------------------------------------------------------------ escritura (la llama el comando `harness erp` tras confirmar)
def contenidos(p):
    """{ruta relativa a la instancia: (texto, sobrescribir)}. Los archivos generados se actualizan; el cambio editable no se pisa."""
    js = json.dumps(p, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    return {
        "erp/propuesta-erp.md": (a_md(p), True),
        "erp/propuesta-erp.json": (js, True),
        f"cambios/{SLUG_CAMBIO}/especificacion.md": (especificacion_md(p), False),
        f"cambios/{SLUG_CAMBIO}/matriz.md": (matriz_md(p), False),
    }


def estado_escritura(instancia, p):
    """Qué pasaría al escribir, sin escribir: [(ruta, accion)] con accion en crear | actualizar | igual | conservar."""
    instancia = pathlib.Path(instancia)
    out = []
    for rel, (texto, pisa) in contenidos(p).items():
        f = instancia / rel
        if not f.exists():
            out.append((rel, "crear"))
        elif not pisa:
            out.append((rel, "conservar"))
        elif f.read_text(encoding="utf-8", errors="replace") == texto:
            out.append((rel, "igual"))
        else:
            out.append((rel, "actualizar"))
    return out


def escribir(instancia, p):
    instancia = pathlib.Path(instancia)
    if not instancia.is_dir():
        raise ErrorErp(f"No existe la carpeta de la instancia {instancia}.")
    hechas = []
    for rel, accion in estado_escritura(instancia, p):
        f = instancia / rel
        if f.is_symlink():
            raise ErrorErp(f"{rel} es un enlace simbólico: no escribo a través de enlaces.")
        if accion in ("crear", "actualizar"):
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(contenidos(p)[rel][0], encoding="utf-8")
        hechas.append((rel, accion))
    return hechas


# ------------------------------------------------------------------ resumen en pantalla
def resumen_pantalla(p):
    r = p["resumen"]
    e = r["por_estado"]
    L = [f"Documentos leídos: {p['documentos']['leidos']} ({p['documentos']['lineas']} líneas); no leídos: {len(p['documentos']['no_leidos'])}",
         "Rubro: " + (f"{p['rubro']['etiqueta']} ({p['rubro']['puntos']} puntos)" if p["rubro"] else "no determinado"),
         f"Producto de partida: {p['producto_partida']['nombre']} ({p['producto_partida']['id']})",
         f"Módulos propuestos: {r['modulos']} (núcleo {r['nucleo']} · por señal {r['por_senal']} · por requisito {r['por_requisito']})",
         f"Estado real hoy: {e['hecho']} hechos · {e['parcial']} parciales · {e['en_construccion']} en construcción · {e['diseno']} en diseño · {e['planeado']} planeados", ""]
    por_senal = {s["id"]: s for s in p["senales"]}
    L.append("Módulos:")
    for m in p["modulos"]:
        ev = ""
        if m["origen"] == "senal":
            s = por_senal[m["senales"][0]]
            if s["evidencia"]:
                ev = f"  <- {s['evidencia'][0]['archivo']}:{s['evidencia'][0]['linea']} «{s['evidencia'][0]['termino']}»"
        elif m["origen"] == "requisito":
            ev = "  <- lo requiere " + ", ".join(m["requerido_por"])
        marca = {"hecho": "  ", "parcial": "~ ", "en_construccion": "! ", "diseno": "X ", "planeado": "X "}[m["estado"]] if m["estado"] in ESTADOS_REALES else "? "
        L.append(f"  {marca}{m['id']:<26} {ESTADOS_REALES.get(m['estado'], m['estado']):<16}{ev}")
    L.append("  (sin marca = existe · ~ parcial · ! en construcción · X NO existe aún)")
    if p["no_existe_aun"]:
        L += ["", f"NO existe aún en el ERP central ({len(p['no_existe_aun'])}): " + ", ".join(m["id"] for m in p["no_existe_aun"]) + ". No se promete."]
    if p["existe_en_parte"]:
        L += [f"Existe solo en parte ({len(p['existe_en_parte'])}): " + ", ".join(m["id"] for m in p["existe_en_parte"]) + "."]
    if p["opcionales"]:
        L += ["", "Opcional ligado (se ofrece, no se ejecuta): adaptador diseno-web (los documentos mencionan sitio web o landing)."]
    if p["producto_partida"]["modulos_sin_senal"]:
        L += ["", f"Del producto de partida sin señal en los documentos (no incluidos): " + ", ".join(m["id"] for m in p["producto_partida"]["modulos_sin_senal"])]
    for a in p["avisos"]:
        L.append(f"Aviso: {a}")
    return "\n".join(L)


def generar(negocio, erp_base, senales=SENALES_DEFECTO, raiz=RAIZ, marca_en_instancia=None):
    """Lectura completa: documentos + señales + catálogo => propuesta (dict). No escribe."""
    negocio = pathlib.Path(negocio)
    if not negocio.is_dir():
        raise ErrorErp(f"No existe la carpeta del negocio {negocio}.")
    cfg = cargar_senales(senales)
    cat = cargar_catalogo(erp_base)
    docs, no_leidos, avisos = leer_documentos(negocio, raiz)
    ev = evaluar(docs, cfg, raiz)
    return proponer(docs, no_leidos, avisos, cfg, cat, ev, marca_en_instancia)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Propone los módulos del ERP estándar que un negocio necesita, a partir de documentos locales (solo lectura).")
    ap.add_argument("negocio", help="carpeta con los documentos del negocio (.md, .txt, .csv, .xlsx exportados)")
    ap.add_argument("--erp-base", required=True, help="carpeta del repositorio del ERP estándar (se lee modulos/catalogo.json; nunca se escribe)")
    ap.add_argument("--senales", default=str(SENALES_DEFECTO), help="archivo de señales (por defecto perfiles/_erp/senales.toml)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--json", action="store_true")
    g.add_argument("--md", action="store_true")
    a = ap.parse_args(argv)
    try:
        p = generar(a.negocio, a.erp_base, a.senales)
    except ErrorErp as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(json.dumps(p, ensure_ascii=False, indent=2) if a.json else a_md(p) if a.md else resumen_pantalla(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
