"""
Herramienta de Inventario
"""

from services.inventory import InventoryService
from core.tool_registry import register
from core import responses

inventory = InventoryService()


def search_product(text):

    products = inventory.search(text)

    if not products:
        return f"No encontré productos con '{text}'."

    return responses.products(products)


register(
    "inventory.search",
    search_product
)

def search_barcode(barcode):

    product = inventory.search_barcode(barcode)

    if not product:

        return f"No encontré un producto con el código '{barcode}'."

    return responses.product(product)


register(
    "inventory.barcode",
    search_barcode
)

# ==========================================
# LISTAR PRODUCTOS
# ==========================================

def list_products(_):

    products = inventory.list()

    return responses.products(products)


register(
    "inventory.list",
    list_products
)
import re
from database.nimbo_db import add_stock, remove_stock, get_products, nimbo_connect


def _quitar_articulo(query):
    """Quita el articulo inicial (el/la/los/las) de una busqueda de producto.
    'cambia el precio de la cuchilla a 100' captura 'la cuchilla' como query, y el
    LIKE directo contra Product.Name (sin el fallback fuzzy que si tiene
    get_products()) nunca matcheaba porque el nombre real del producto no trae el
    articulo pegado ('Cuchilla oster original', no 'la Cuchilla oster original')."""
    return re.sub(r"^(el|la|los|las)\s+", "", query.strip(), flags=re.IGNORECASE).strip()


def add_stock_tool(data):
    query = data.get("query", "")
    quantity = data.get("quantity", 0)
    products = get_products(search=query)
    if not products:
        return f"No encontre producto '{query}'."
    p = products[0]
    add_stock(p["Id"], quantity)
    return f"Agregue {quantity} unidades de {p['Name']}. Stock actual: {int(p['Stock']) + quantity}."

register("inventory.add_stock", add_stock_tool)

def remove_stock_tool(data):
    query = data.get("query", "")
    quantity = data.get("quantity", 0)
    products = get_products(search=query)
    if not products:
        return f"No encontre producto '{query}'."
    p = products[0]
    ok = remove_stock(p["Id"], quantity)
    if not ok:
        return f"Stock insuficiente. {p['Name']} solo tiene {int(p['Stock'])} unidades."
    return f"Retire {quantity} unidades de {p['Name']}. Stock actual: {int(p['Stock']) - quantity}."

register("inventory.remove_stock", remove_stock_tool)

def update_price_tool(data):
    query = _quitar_articulo(data.get("query", ""))
    price = data.get("price", 0)
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("UPDATE Producto SET Precio=? WHERE Nombre LIKE ?", (price, f"%{query}%"))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        return f"No encontre producto '{query}'."
    return f"Precio actualizado a Q{price}."

register("inventory.update_price", update_price_tool)

def delete_product_tool(data):
    query = data.get("query", "")
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("UPDATE Producto SET Activo=0 WHERE Nombre LIKE ?", (f"%{query}%",))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        return f"No encontre producto '{query}'."
    return f"Producto '{query}' eliminado."

register("inventory.delete", delete_product_tool)


def _crear_producto_directo(name, price, cost, quantity, codigo=""):
    """Insercion real del producto, ya con precio y costo resueltos (los dos
    obligatorios). Usada tanto por create_product_tool (cuando el mensaje ya
    trae todo) como por el step producto_waiting_costo en core/nimbo.py (cuando
    el flujo conversacional termino de completar los campos que faltaban - ese
    flujo tambien se arranca desde un codigo escaneado sin registrar, ver
    escanear_codigo_tool, en cuyo caso codigo llega prellenado)."""
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Producto (Nombre, Codigo, Precio, Costo, Activo) VALUES (?, ?, ?, ?, 1)",
        (name, codigo or "", price, cost)
    )
    conn.commit()
    product_id = cur.lastrowid
    conn.close()
    if quantity and quantity > 0:
        add_stock(product_id, quantity)
    return f"Producto '{name}' creado. Precio: Q{price}, Costo: Q{cost}, Stock: {int(quantity or 0)}."


def create_product_tool(data):
    query = (data.get("query") or "").strip()
    price = data.get("price")
    cost = data.get("cost")
    quantity = data.get("quantity") or 0

    if price is None or cost is None:
        # Falta precio y/o costo - arranca el flujo conversacional en
        # core/nimbo.py (marcador PRODUCTO_NUEVO_INICIO:) para completarlos uno
        # por uno. El stock nunca se pregunta - si no vino en el mensaje se crea
        # el producto con 0 y se puede agregar despues con "agregar N [producto]".
        precio_str = "" if price is None else str(price)
        costo_str = "" if cost is None else str(cost)
        return f"PRODUCTO_NUEVO_INICIO:{query}|{precio_str}|{costo_str}|{quantity}"

    return _crear_producto_directo(query.title(), price, cost, quantity)

register("inventory.create", create_product_tool)


def escanear_codigo_tool(codigo):
    """Escaneo de codigo de barras directo en el chat (el lector USB/Bluetooth
    escribe el codigo + Enter, ver BARCODE_PATTERNS en
    core/detectors/inventory_detector.py). Recibe el codigo como string plano
    (el detector devuelve solo {"intent","query"}, ver core/action_engine.py).
    Si encuentra el producto arranca BARCODE_INICIO: (pregunta si vender, ver
    step barcode_waiting_accion en core/nimbo.py); si no, arranca
    CODIGO_NO_ENCONTRADO_INICIO: (pregunta si agregarlo como producto nuevo)."""
    from database.nimbo_db import get_product_by_code_ci, get_foto_producto
    codigo = (codigo or "").strip()
    producto = get_product_by_code_ci(codigo)
    if not producto:
        return f"CODIGO_NO_ENCONTRADO_INICIO:{codigo}"

    foto = get_foto_producto(producto["Id"]) or ""
    return (f"BARCODE_INICIO:{producto['Id']}|{producto['Name']}|{producto['Price']}|"
            f"{producto['Stock']}|{producto['Code'] or ''}|{foto}")

register("inventory.scan_barcode", escanear_codigo_tool)


def importar_instrucciones_tool(data):
    return (
        "Para importar productos en lote desde Excel o CSV:\n"
        "1. Ve al Dashboard, seccion 'Inventario' (menu lateral).\n"
        "2. Haz clic en el boton '📦 Importar Excel/CSV'.\n"
        "3. Si no tienes el archivo listo, descarga la plantilla desde ese mismo modal - "
        "trae las columnas correctas y un ejemplo.\n"
        "4. Sube tu archivo (.xlsx o .csv). Solo Nombre y Precio son obligatorios "
        "(Costo, Codigo, Stock, StockMinimo y Categoria son opcionales).\n\n"
        '<a href="/" style="color:var(--accent)">🔗 Ir al Dashboard</a>'
    )

register("inventory.importar_instrucciones", importar_instrucciones_tool)

def set_min_stock_tool(data):
    from database.nimbo_db import set_stock_minimo, get_products
    query = data.get("query", "")
    minimo = data.get("quantity", 5)
    products = get_products(search=query)
    if not products:
        return f"No encontre producto '{query}'."
    p = products[0]
    set_stock_minimo(p["Id"], p["Name"], minimo)
    return f"Stock minimo de {p['Name']} configurado en {minimo} unidades. Te avisare cuando baje de esa cantidad."

register("inventory.set_min_stock", set_min_stock_tool)


def update_cost_tool(data):
    query = _quitar_articulo(data.get("query", ""))
    cost = data.get("cost", 0)
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("UPDATE Producto SET Costo=? WHERE Nombre LIKE ?", (cost, f"%{query}%"))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        return f"No encontre producto '{query}'."
    return f"Costo actualizado a Q{cost}."

register("inventory.update_cost", update_cost_tool)


def alertas_predictivas_tool(data):
    from database.nimbo_db import get_alertas_predictivas
    alertas = get_alertas_predictivas()
    criticos = [a for a in alertas if a["urgencia"] == "CRITICO"]
    advertencias = [a for a in alertas if a["urgencia"] == "ADVERTENCIA"]

    if not criticos and not advertencias:
        return "Todos los productos tienen stock para mas de 21 dias al ritmo actual de ventas."

    resp = "Alertas predictivas de inventario:\n\n"
    if criticos:
        resp += f"CRITICO ({len(criticos)}):\n"
        for a in criticos:
            resp += f"- {a['producto']}: se agota en {a['dias_restantes']} dia(s) (stock {a['stock_actual']:.0f}, vende {a['promedio_diario']:.1f}/dia)\n"
    if advertencias:
        resp += f"\nADVERTENCIA ({len(advertencias)}):\n"
        for a in advertencias:
            resp += f"- {a['producto']}: se agota en {a['dias_restantes']} dia(s) (stock {a['stock_actual']:.0f}, vende {a['promedio_diario']:.1f}/dia)\n"
    return resp.strip()

register("inventory.alertas_predictivas", alertas_predictivas_tool)


def prediccion_producto_tool(query):
    from database.nimbo_db import get_prediccion_producto
    p = get_prediccion_producto(query)
    if not p:
        return f"No encontre productos con '{query}'."

    if p["dias_restantes"] is None:
        return (f"{p['producto']} tiene {p['stock_actual']:.0f} en stock, pero no ha tenido "
                f"salidas en los ultimos 30 dias - no se puede predecir cuando se agota.")

    base = (f"A este ritmo, {p['producto']} se agota en {p['dias_restantes']} dia(s) "
            f"(stock: {p['stock_actual']:.0f}, vende {p['promedio_diario']:.1f}/dia).")
    if p["urgencia"] == "CRITICO":
        return base + " CRITICO - reabastece pronto."
    return base

register("inventory.prediccion_producto", prediccion_producto_tool)


def kardex_tool(data):
    from database.nimbo_db import get_kardex, get_products
    query = data.get("query", "") if isinstance(data, dict) else str(data)

    if query:
        productos = get_products(search=query)
        if not productos:
            return f"No encontre producto '{query}'."
        p = productos[0]
        movimientos = get_kardex(product_id=p["Id"], limit=15)
        titulo = f"Kardex de {p['Name']}"
    else:
        movimientos = get_kardex(limit=15)
        titulo = "Kardex (ultimos movimientos)"

    if not movimientos:
        return f"{titulo}: sin movimientos registrados."

    resp = f"{titulo}:\n"
    for m in movimientos:
        signo = "+" if m["Tipo"] == "ENTRADA" else "-"
        resp += (f"- {m['Fecha'][:16]} | {m['Tipo']} {signo}{m['Cantidad']} {m['ProductName']} "
                 f"({m['StockAntes']}->{m['StockDespues']}) | {m['Razon']}\n")
    return resp.strip()

register("inventory.kardex", kardex_tool)
