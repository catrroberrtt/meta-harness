"""Apoyo de las pruebas de la opción ERP: un catálogo de módulos INVENTADO (misma forma que el del ERP estándar, contenido de prueba)
y negocios ficticios de varios rubros. Sin datos de ninguna empresa."""
import json
import pathlib

# (id, nombre, estado, fase, requiere, núcleo)
MODULOS = [
    ("identidad", "Identidad", "hecho", "ya", [], True),
    ("autenticacion", "Autenticación", "hecho", "ya", ["identidad"], True),
    ("configuracion", "Configuración", "hecho", "ya", ["identidad"], True),
    ("interfaz", "Interfaz", "hecho", "ya", [], True),
    ("notificaciones", "Avisos", "parcial", "ya", ["identidad"], False),
    ("flujo-trabajo", "Flujo de trabajo", "parcial", "ya", ["identidad", "configuracion"], False),
    ("socios-negocio", "Socios de negocio", "planeado", "F2", ["identidad"], False),
    ("almacen", "Almacén", "parcial", "ya", ["configuracion", "identidad"], False),
    ("contabilidad", "Contabilidad", "parcial", "ya", ["configuracion", "identidad"], False),
    ("comprobantes", "Comprobantes", "parcial", "ya", ["configuracion", "identidad"], False),
    ("compras", "Compras", "en_construccion", "F1", ["almacen", "contabilidad", "configuracion"], False),
    ("ventas", "Ventas", "planeado", "F2", ["almacen", "contabilidad", "comprobantes"], False),
    ("cuentas-por-cobrar", "Cuentas por cobrar", "planeado", "F2", ["contabilidad"], False),
    ("cuentas-por-pagar", "Cuentas por pagar", "planeado", "F2", ["contabilidad"], False),
    ("bancos", "Bancos", "planeado", "F2", ["contabilidad"], False),
    ("costos", "Costos", "planeado", "F3", ["contabilidad"], False),
    ("produccion", "Producción", "planeado", "F3", ["almacen", "costos"], False),
    ("calidad", "Calidad", "planeado", "F4", ["almacen"], False),
    ("transporte", "Transporte", "planeado", "F3", ["almacen", "comprobantes"], False),
    ("expedicion", "Expedición", "planeado", "F3", ["ventas", "almacen"], False),
    ("inmuebles", "Inmuebles", "planeado", "F4", ["contabilidad", "cuentas-por-cobrar"], False),
    ("proyectos", "Proyectos", "planeado", "F3", ["costos", "compras"], False),
    ("personal", "Personal", "planeado", "F3", ["identidad", "socios-negocio"], False),
    ("tiempos", "Tiempos", "planeado", "F3", ["personal"], False),
    ("gastos-viaje", "Viajes y gastos", "planeado", "F4", ["personal", "cuentas-por-pagar"], False),
    ("planilla-peru", "Planilla", "planeado", "F4", ["personal", "tiempos", "contabilidad"], False),
    ("integraciones", "Integraciones", "planeado", "F3", ["configuracion"], False),
    ("documentos", "Documentos", "planeado", "F3", ["identidad"], False),
]
PRODUCTOS = [
    ("comercio", ["almacen", "contabilidad", "comprobantes", "compras", "ventas", "bancos", "cuentas-por-pagar", "cuentas-por-cobrar"]),
    ("distribucion", ["almacen", "transporte", "expedicion", "ventas", "contabilidad", "comprobantes"]),
    ("industrial", ["almacen", "produccion", "calidad", "costos", "compras", "ventas", "contabilidad"]),
    ("servicios", ["contabilidad", "proyectos", "costos", "personal", "tiempos", "gastos-viaje"]),
    ("inmobiliario", ["contabilidad", "inmuebles", "cuentas-por-cobrar", "documentos"]),
]


def escribir_catalogo(erp_base):
    base = pathlib.Path(erp_base)
    (base / "modulos").mkdir(parents=True, exist_ok=True)
    mods = []
    for mid, nombre, estado, fase, req, nuc in MODULOS:
        m = {"id": mid, "nombre": nombre, "area": "Prueba", "estado": estado, "fase": fase, "requiere": req}
        if nuc:
            m["nucleo"] = True
        if mid == "notificaciones":
            m["pendiente"] = ["Correo como canal", "Plantillas de aviso editables"]
        mods.append(m)
    cat = {"version": 3, "descripcion": "catálogo ficticio de pruebas", "estados": ["hecho", "parcial", "en_construccion", "diseno", "planeado"],
           "fases": ["ya", "F1", "F2", "F3", "F4"], "modulos": mods,
           "productos": [{"id": pid, "nombre": pid.capitalize(), "modulos": ms} for pid, ms in PRODUCTOS]}
    (base / "modulos" / "catalogo.json").write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")
    return base


NEGOCIOS = {
    "comercio": {"descripcion.md": "# Ferretería Ejemplo\n\nSomos una ferretería minorista y mayorista con tres tiendas.\nLlevamos el inventario y el kardex en Excel.\n"
                                   "Hacemos órdenes de compra a proveedores cada semana.\nLos vendedores arman cotizaciones a clientes y pedidos de venta.\n"
                                   "Emitimos factura electrónica a SUNAT.\n"},
    "distribucion": {"operacion.md": "# Distribuidora Ejemplo\n\nSomos una distribuidora con flota propia y rutas de reparto diarias.\n"
                                     "Cada conductor lleva su guía de transportista y el despacho sale del almacén central.\n"
                                     "Hay un operador logístico que coordina el reparto.\n"},
    "servicios": {"consultora.md": "# Consultora Ejemplo\n\nSomos una consultoría de servicios profesionales; registramos horas facturables por proyecto.\n"
                                   "Cada proyecto tiene hitos y su cronograma de obra. Los consultores reportan viáticos y rendición de gastos de viaje.\n"
                                   "Controlamos las horas con control de asistencia.\n"},
    "industrial": {"planta.md": "# Planta Ejemplo\n\nUna fábrica con línea de producción: materia prima entra, la orden de producción sigue la lista de materiales\n"
                                "y el producto terminado pasa a control de calidad. Registramos no conformidades.\nLlevamos el stock en el almacén.\n"},
    "inmobiliario": {"cartera.md": "# Inmobiliaria Ejemplo\n\nAdministramos una cartera inmobiliaria: cada contrato de alquiler tiene un inquilino.\n"
                                   "El arrendamiento se cobra cada mes y llevamos las cuentas por cobrar de los inquilinos.\nLa contabilidad la lleva un contador.\n"},
}


def escribir_negocio(carpeta, rubro):
    carpeta = pathlib.Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, texto in NEGOCIOS[rubro].items():
        (carpeta / nombre).write_text(texto, encoding="utf-8")
    return carpeta
