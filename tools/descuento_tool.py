"""
Herramienta de Descuentos
"""
from datetime import datetime, date
from core.tool_registry import register
from database.nimbo_db import (
    crear_descuento, get_descuentos, get_descuento_por_id, buscar_descuentos,
    desactivar_descuento, get_product_by_id, get_products
)
from database.nimbo_db import buscar_cliente_completo

MESES_NOMBRE = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def crear_cliente_tool(data):
    porcentaje = data.get("porcentaje")
    query = data.get("cliente_query", "").strip()
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre ningun cliente que coincida con '{query}'. Registra al cliente primero."
    cliente = clientes[0]
    nombre = f"Descuento cliente: {cliente['Nombre']}"
    crear_descuento(nombre, "cliente", porcentaje=porcentaje, cliente_id=cliente["Id"])
    return f"Descuento del {porcentaje}% creado para {cliente['Nombre']}. Se aplicara automaticamente en sus compras."

register("descuento.crear_cliente", crear_cliente_tool)


def crear_temporada_tool(data):
    porcentaje = data.get("porcentaje")
    dia_inicio = data.get("dia_inicio")
    dia_fin = data.get("dia_fin")
    mes = data.get("mes")
    anio = data.get("anio")

    hoy = date.today()
    if anio is None:
        anio = hoy.year
        try:
            if date(anio, mes, dia_fin) < hoy:
                anio += 1
        except ValueError:
            return "La fecha de temporada no es valida."

    try:
        fecha_inicio = date(anio, mes, dia_inicio).strftime("%Y-%m-%d")
        fecha_fin = date(anio, mes, dia_fin).strftime("%Y-%m-%d")
    except ValueError:
        return "La fecha de temporada no es valida."

    mes_nombre = MESES_NOMBRE.get(mes, "")
    nombre = f"Descuento temporada: {dia_inicio}-{dia_fin} {mes_nombre} {anio}"
    crear_descuento(nombre, "temporada", porcentaje=porcentaje, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
    return (f"Descuento del {porcentaje}% creado del {dia_inicio} al {dia_fin} de {mes_nombre} de {anio}. "
            f"Se aplicara automaticamente a las ventas en ese rango de fechas.")

register("descuento.crear_temporada", crear_temporada_tool)


def crear_producto_tool(data):
    porcentaje = data.get("porcentaje")
    query = data.get("producto_query", "").strip()
    productos = get_products(search=query)
    if not productos:
        return f"No encontre ningun producto que coincida con '{query}'."
    producto = productos[0]
    nombre = f"Descuento producto: {producto['Name'].strip()}"
    crear_descuento(nombre, "producto", porcentaje=porcentaje, producto_id=producto["Id"])
    return f"Descuento del {porcentaje}% creado en {producto['Name'].strip()}. Se aplicara automaticamente al venderlo."

register("descuento.crear_producto", crear_producto_tool)


def crear_monto_tool(data):
    porcentaje = data.get("porcentaje")
    monto_minimo = data.get("monto_minimo")
    nombre = f"Descuento por monto: compras mayores a Q{monto_minimo:.2f}"
    crear_descuento(nombre, "monto", porcentaje=porcentaje, monto_minimo=monto_minimo)
    return f"Descuento del {porcentaje}% creado para compras mayores a Q{monto_minimo:.2f}."

register("descuento.crear_monto", crear_monto_tool)


def _describir_descuento(d):
    valor = f"{d['Porcentaje']}%" if d.get("Porcentaje") else f"Q{d['MontoFijo']}"
    if d["Tipo"] == "cliente":
        detalle = f"Cliente Id {d['ClienteId']}"
    elif d["Tipo"] == "temporada":
        detalle = f"del {str(d['FechaInicio'])[:10]} al {str(d['FechaFin'])[:10]}"
    elif d["Tipo"] == "producto":
        producto = get_product_by_id(d["ProductoId"])
        detalle = producto["Name"].strip() if producto else f"Producto Id {d['ProductoId']}"
    elif d["Tipo"] == "monto":
        detalle = f"compras mayores a Q{d['MontoMinimo']}"
    else:
        detalle = ""
    return f"- #{d['Id']} {d['Nombre']} ({valor}) - {detalle}"


def listar_tool(data):
    descuentos = get_descuentos(activo=True)
    if not descuentos:
        return "No hay descuentos activos."
    resp = f"{len(descuentos)} descuento(s) activo(s):\n"
    resp += "\n".join(_describir_descuento(d) for d in descuentos)
    return resp

register("descuento.listar", listar_tool)


def eliminar_tool(data):
    query = data.get("descuento_query", "").strip()

    descuento = None
    if query.isdigit():
        descuento = get_descuento_por_id(int(query))
        if descuento and not descuento["Activo"]:
            descuento = None

    if descuento:
        desactivar_descuento(descuento["Id"])
        return f"Descuento '{descuento['Nombre']}' desactivado."

    coincidencias = buscar_descuentos(query)
    if not coincidencias:
        return f"No encontre ningun descuento activo que coincida con '{query}'."
    if len(coincidencias) > 1:
        lista = "\n".join(_describir_descuento(d) for d in coincidencias)
        return f"Hay varios descuentos que coinciden:\n{lista}\n\nEspecifica el numero (#Id) que quieres eliminar."
    d = coincidencias[0]
    desactivar_descuento(d["Id"])
    return f"Descuento '{d['Nombre']}' desactivado."

register("descuento.eliminar", eliminar_tool)
