"""
Herramienta de Proveedores
"""
from core.tool_registry import register
from database.aronium import crear_proveedor, buscar_proveedor, get_todos_proveedores, get_historial_proveedor, get_alertas_precios

def nuevo_proveedor_tool(data):
    if isinstance(data, str): return "Error: datos invalidos"
    nombre = data.get("nombre", "")
    whatsapp = data.get("whatsapp", "")
    proveedor_id, creado = crear_proveedor(nombre, whatsapp)
    if not creado:
        return f"El proveedor {nombre} ya existe."
    return f"PROVEEDOR_NUEVO:{proveedor_id}|{nombre}"

register("proveedor.nuevo", nuevo_proveedor_tool)

def buscar_proveedor_tool(data):
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    proveedores = buscar_proveedor(query)
    if not proveedores:
        return f"No encontre proveedor '{query}'."
    resp = ""
    for p in proveedores:
        resp += "Proveedor: " + p["Nombre"] + "\n"
        if p["WhatsApp"]: resp += "WhatsApp: " + p["WhatsApp"] + "\n"
        if p["contactos"]:
            resp += "Contactos:\n"
            for c in p["contactos"]:
                resp += "  - " + c["Nombre"] + " (" + c["Cargo"] + ")"
                if c["WhatsApp"]: resp += " WA: " + c["WhatsApp"]
                resp += "\n"
        resp += "Ordenes: " + str(p["TotalOrdenes"] or 0) + " | Total: Q" + str(p["TotalComprado"] or 0) + "\n---\n"
    return resp.strip()

register("proveedor.buscar", buscar_proveedor_tool)

def listar_proveedores_tool(data):
    proveedores = get_todos_proveedores()
    if not proveedores:
        return "No hay proveedores registrados."
    resp = str(len(proveedores)) + " proveedores:\n"
    for p in proveedores:
        resp += "- " + p["Nombre"]
        if p["WhatsApp"]: resp += " | WA: " + p["WhatsApp"]
        resp += "\n"
    return resp

register("proveedor.listar", listar_proveedores_tool)

def historial_proveedor_tool(data):
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    proveedores = buscar_proveedor(query)
    if not proveedores:
        return f"No encontre proveedor '{query}'."
    p = proveedores[0]
    historial = get_historial_proveedor(p["Id"])
    if not historial:
        return f"Sin historial para {p['Nombre']}."
    resp = "Historial de " + p["Nombre"] + ":\n"
    for o in historial:
        resp += "- " + o["NumeroOrden"] + " | " + o["Fecha"][:10] + " | Q" + str(o["Total"]) + "\n"
        if o["Items"]: resp += "  " + o["Items"] + "\n"
    return resp

register("proveedor.historial", historial_proveedor_tool)

def alertas_precios_tool(data):
    alertas = get_alertas_precios()
    if not alertas:
        return "No hay cambios de precio registrados."
    resp = "Cambios de precio:\n"
    for a in alertas:
        signo = "+" if a["Diferencia"] > 0 else ""
        resp += "- " + a["ProveedorNombre"] + " | " + a["ProductoNombre"] + ": Q" + str(a["PrecioAnterior"]) + " -> Q" + str(a["PrecioNuevo"]) + " (" + signo + str(a["PorcentajeCambio"]) + "%)\n"
    return resp

register("proveedor.alertas", alertas_precios_tool)

def orden_compra_tool(data):
    return "PROVEEDOR_ORDEN_INICIO:" + (data.get("query", "") if isinstance(data, dict) else str(data))

register("proveedor.orden_compra", orden_compra_tool)

def pedidos_sugeridos_tool(data):
    from database.aronium import get_pedidos_sugeridos
    sugeridos = get_pedidos_sugeridos()
    if not sugeridos:
        return "Todo el inventario esta en niveles normales. No hay pedidos urgentes."
    
    # Agrupar por proveedor
    por_proveedor = {}
    sin_proveedor = []
    
    for s in sugeridos:
        if s["proveedores"]:
            for prov in s["proveedores"]:
                key = prov["Nombre"]
                if key not in por_proveedor:
                    por_proveedor[key] = {"proveedor": prov, "items": []}
                por_proveedor[key]["items"].append(s)
        else:
            sin_proveedor.append(s)
    
    resp = "Productos que necesitan reabastecimiento:\n\n"
    
    for nombre_prov, datos in por_proveedor.items():
        resp += "Proveedor: " + nombre_prov + "\n"
        if datos["proveedor"]["WhatsApp"]:
            resp += "WhatsApp: " + datos["proveedor"]["WhatsApp"] + "\n"
        for item in datos["items"]:
            resp += "  - " + item["producto"] + " | Stock: " + str(item["stock_actual"]) + " | Minimo: " + str(item["minimo"]) + " | Pedir: " + str(item["cantidad_sugerida"]) + " unidades\n"
        resp += "\n"
    
    if sin_proveedor:
        resp += "Sin proveedor asignado:\n"
        for item in sin_proveedor:
            resp += "  - " + item["producto"] + " | Stock: " + str(item["stock_actual"]) + " | Pedir: " + str(item["cantidad_sugerida"]) + " unidades\n"
    
    return resp.strip()

register("proveedor.pedidos", pedidos_sugeridos_tool)

def asociar_producto_tool(data):
    if isinstance(data, str): return "Error: datos invalidos"
    from database.aronium import buscar_proveedor, asociar_producto_proveedor, get_products
    proveedor_query = data.get("proveedor", "")
    producto_query = data.get("producto", "")
    proveedores = buscar_proveedor(proveedor_query)
    if not proveedores:
        return f"No encontre proveedor '{proveedor_query}'."
    productos = get_products(search=producto_query)
    if not productos:
        return f"No encontre producto '{producto_query}'."
    p = proveedores[0]
    prod = productos[0]
    asociar_producto_proveedor(p["Id"], prod["Name"], prod["Id"])
    return f"Producto '{prod['Name']}' asociado al proveedor {p['Nombre']}."

register("proveedor.asociar", asociar_producto_tool)

def generar_orden_tool(data):
    from database.aronium import buscar_proveedor, get_pedidos_sugeridos, crear_orden_compra
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    proveedores = buscar_proveedor(query)
    if not proveedores:
        return f"No encontre proveedor '{query}'."
    p = proveedores[0]
    sugeridos = get_pedidos_sugeridos()
    items_proveedor = []
    for s in sugeridos:
        for prov in s["proveedores"]:
            if prov["Id"] == p["Id"]:
                items_proveedor.append({
                    "nombre": s["producto"],
                    "cantidad": s["cantidad_sugerida"],
                    "precio": 0
                })
    if not items_proveedor:
        return f"No hay productos pendientes para {p['Nombre']}."
    numero = crear_orden_compra(p["Id"], items_proveedor)
    resp = f"Orden {numero} creada para {p['Nombre']}:\n"
    for item in items_proveedor:
        resp += f"  - {item['nombre']} x{item['cantidad']}\n"
    resp += f"\nContacta a {p['Nombre']} al WA: {p['WhatsApp'] or 'sin numero'}"
    return resp

register("proveedor.generar_orden", generar_orden_tool)
