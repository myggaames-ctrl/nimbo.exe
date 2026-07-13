"""
Herramienta de Ventas
"""
from core.tool_registry import register
from database.aronium import get_products, remove_stock, registrar_venta_cliente, buscar_cliente_completo
from datetime import datetime

def registrar_venta_tool(data):
    if isinstance(data, str):
        return "Error: datos invalidos"
    
    cantidad = data.get("cantidad", 1)
    query = data.get("query", "")
    precio_manual = data.get("precio")

    productos = get_products(search=query)
    if not productos:
        return f"No encontre producto '{query}' en inventario."
    
    # Si hay varios productos mostrar opciones
    if len(productos) > 1:
        opciones = ";".join([f"{p['Name']}:{p['Price']}:{p['Id']}" for p in productos[:5]])
        return f"VENTA_INICIO:{opciones}|{cantidad}"

    p = productos[0]
    precio_unit = precio_manual if precio_manual else p["Price"]
    total = precio_unit * cantidad

    if p["Stock"] < cantidad:
        return f"Stock insuficiente. {p['Name']} solo tiene {int(p['Stock'])} unidades."

    remove_stock(p["Id"], cantidad, razon="Venta")

    return f"VENTA_INICIO:{cantidad}|{p['Name']}|{precio_unit}|{total}|{p['Id']}"

register("venta.registrar", registrar_venta_tool)

def resumen_dia_tool(data):
    from database.aronium import nimbo_connect
    from datetime import datetime
    hoy = datetime.now().strftime("%Y-%m-%d")
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as Cantidad, SUM(Total) as Total, GROUP_CONCAT(Descripcion, ' | ') as Detalle
        FROM Venta WHERE Mes=? AND Anio=? AND DATE(Fecha) >= DATE('now', '-1 day')
    """, (datetime.now().month, datetime.now().year))
    row = dict(cur.fetchone())
    conn.close()
    if not row["Cantidad"] or row["Total"] is None:
        return "No hay ventas registradas hoy."
    return f"Ventas de hoy:\n- Transacciones: {row['Cantidad']}\n- Total: Q{row['Total']:.2f}\n- Detalle: {row['Detalle']}"

register("venta.resumen_dia", resumen_dia_tool)

def resumen_mes_tool(data):
    from database.aronium import nimbo_connect
    from datetime import datetime
    mes = datetime.now().month
    anio = datetime.now().year
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as Cantidad, SUM(Total) as Total
        FROM Venta WHERE Mes=? AND Anio=?
    """, (mes, anio))
    row = dict(cur.fetchone())
    conn.close()
    if not row["Cantidad"] or row["Total"] is None:
        return "No hay ventas registradas este mes."
    return f"Ventas del mes:\n- Transacciones: {row['Cantidad']}\n- Total: Q{row['Total']:.2f}"

register("venta.resumen_mes", resumen_mes_tool)
