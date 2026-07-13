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
from database.aronium import add_stock, remove_stock, get_products, connect

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
    query = data.get("query", "")
    price = data.get("price", 0)
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE Product SET Price=? WHERE Name LIKE ?", (price, f"%{query}%"))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        return f"No encontre producto '{query}'."
    return f"Precio actualizado a Q{price}."

register("inventory.update_price", update_price_tool)

def delete_product_tool(data):
    query = data.get("query", "")
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE Product SET IsEnabled=0 WHERE Name LIKE ?", (f"%{query}%",))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        return f"No encontre producto '{query}'."
    return f"Producto '{query}' eliminado."

register("inventory.delete", delete_product_tool)

from database.aronium import add_stock, remove_stock, get_products, connect


def create_product_tool(data):
    from database.aronium import connect, add_stock
    name = data.get("query", "").title()
    price = data.get("price", 0)
    cost = data.get("cost", 0)
    quantity = data.get("quantity", 0)
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Product (Name, Code, Price, Cost, IsEnabled) VALUES (?, ?, ?, ?, 1)",
        (name, "", price, cost)
    )
    conn.commit()
    product_id = cur.lastrowid
    conn.close()
    if quantity > 0:
        add_stock(product_id, quantity)
    return f"Producto '{name}' creado. Precio: Q{price}, Costo: Q{cost}, Stock: {quantity}."

register("inventory.create", create_product_tool)

def set_min_stock_tool(data):
    from database.aronium import set_stock_minimo, get_products
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
    from database.aronium import connect
    query = data.get("query", "")
    cost = data.get("cost", 0)
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE Product SET Cost=? WHERE Name LIKE ?", (cost, f"%{query}%"))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        return f"No encontre producto '{query}'."
    return f"Costo actualizado a Q{cost}."

register("inventory.update_cost", update_cost_tool)
