"""
Herramienta de Clientes
"""
from core.tool_registry import register
from database.aronium import (
    crear_cliente_completo, buscar_cliente_completo,
    get_todos_clientes, get_historial_cliente, get_clientes_inactivos
)

def nuevo_cliente_tool(data):
    nombre = data.get("nombre", "") if isinstance(data, dict) else str(data)
    telefono = data.get("telefono", "") if isinstance(data, dict) else ""
    cliente_id, creado = crear_cliente_completo(nombre, telefono)
    if creado:
        return f"Cliente {nombre} registrado con telefono {telefono}."
    return f"El cliente con telefono {telefono} ya existe."

register("cliente.nuevo", nuevo_cliente_tool)

def buscar_cliente_tool(data):
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre cliente con '{query}'."
    resp = ""
    for c in clientes:
        resp += "Cliente: " + c["Nombre"] + "\n"
        resp += "Telefono: " + (c["Telefono"] or "—") + "\n"
        resp += "Email: " + (c["Email"] or "—") + "\n"
        resp += "NIT: " + (c["Nit"] or "—") + "\n"
        resp += "Ordenes de servicio: " + str(c["TotalOrdenes"]) + "\n"
        resp += "Compras registradas: " + str(c["TotalCompras"]) + "\n"
        total = c["TotalGastado"] or 0
        resp += "Total gastado: Q" + str(total) + "\n"
        if c["UltimaCompra"]:
            resp += "Ultima compra: " + c["UltimaCompra"] + "\n"
        resp += "---\n"
    return resp.strip()

register("cliente.buscar", buscar_cliente_tool)

def listar_clientes_tool(data):
    clientes = get_todos_clientes()
    if not clientes:
        return "No hay clientes registrados."
    resp = str(len(clientes)) + " clientes:\n"
    for c in clientes:
        resp += "- " + c["Nombre"] + " | " + (c["Telefono"] or "sin tel") 
        if c["TotalCompras"]:
            resp += " | " + str(c["TotalCompras"]) + " compras"
        resp += "\n"
    return resp

register("cliente.listar", listar_clientes_tool)

def historial_cliente_tool(data):
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre cliente con '{query}'."
    c = clientes[0]
    historial = get_historial_cliente(c["Id"])
    resp = "Historial de " + c["Nombre"] + ":\n"
    if historial["ventas"]:
        resp += "\nCompras:\n"
        for v in historial["ventas"]:
            resp += "- " + v["Fecha"][:10] + ": " + v["Descripcion"] + " Q" + str(v["Total"]) + "\n"
    else:
        resp += "\nSin compras registradas.\n"
    if historial["ordenes"]:
        resp += "\nOrdenes de servicio:\n"
        for o in historial["ordenes"]:
            resp += "- " + o["NumeroOrden"] + ": " + o["Equipo"] + " " + o["Marca"] + " | " + o["Estado"] + "\n"
    else:
        resp += "Sin ordenes de servicio.\n"
    return resp

register("cliente.historial", historial_cliente_tool)

def inactivos_tool(data):
    clientes = get_clientes_inactivos(meses=3)
    if not clientes:
        return "Todos los clientes han comprado en los ultimos 3 meses."
    resp = str(len(clientes)) + " clientes inactivos (sin compras en 3 meses):\n"
    for c in clientes:
        resp += "- " + c["Nombre"] + " | " + (c["Telefono"] or "sin tel")
        if c["UltimaCompra"]:
            resp += " | Ultima compra: " + c["UltimaCompra"][:10]
        else:
            resp += " | Sin compras registradas"
        resp += "\n"
    return resp

register("cliente.inactivos", inactivos_tool)

def excel_clientes_tool(data):
    import openpyxl
    from datetime import datetime
    clientes = get_todos_clientes(limit=1000)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clientes"
    ws.append(["Nombre", "Telefono", "Email", "NIT", "Direccion", "Total Ordenes", "Total Compras", "Total Gastado", "Ultima Compra"])
    for c in clientes:
        ws.append([
            c["Nombre"],
            c["Telefono"] or "",
            c["Email"] or "",
            c["Nit"] or "",
            c["Direccion"] or "",
            c["TotalOrdenes"] or 0,
            c["TotalCompras"] or 0,
            c["TotalGastado"] or 0,
            c["UltimaCompra"] or ""
        ])
    filename = "/home/ictor_axtor/micocina-dashboard/clientes_" + datetime.now().strftime("%Y%m%d") + ".xlsx"
    wb.save(filename)
    basename = "clientes_" + datetime.now().strftime("%Y%m%d") + ".xlsx"
    return f"DOWNLOAD:{basename}"

register("cliente.excel", excel_clientes_tool)
