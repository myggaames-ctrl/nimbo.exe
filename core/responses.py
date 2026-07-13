"""
Response Builder
Nimbo AI
"""


def product(product):

    texto = f"""• {product['Name']}
Código: {product['Code']}
Precio: Q{product['Price']}
Costo: Q{product['Cost']}
Existencias: {product['Stock']}
"""

    if product.get("Id") is not None:
        from database.aronium import get_unidades_medida_producto
        unidades = get_unidades_medida_producto(product["Id"])
        if unidades:
            stock = product.get("Stock") or 0
            equivalentes = [
                f"{stock / u['CantidadPorUnidad']:.1f} {u['UnidadBase']}(s)"
                for u in unidades if u.get("CantidadPorUnidad")
            ]
            if equivalentes:
                texto += f"Equivalente: {', '.join(equivalentes)}\n"

    return texto


def products(items):

    if not items:
        return "No encontré resultados."

    return "\n".join(
        product(item)
        for item in items
    )


def customer(customer):

    return f"""👤 {customer['Name']}
📞 {customer['Phone'] or '-'}
📧 {customer['Email'] or '-'}
🏠 {customer['Address'] or '-'}
"""


def customers(items):

    if not items:
        return "No encontré clientes."

    return "\n".join(
        customer(item)
        for item in items
    )


def success(message):

    return f"✅ {message}"


def error(message):

    return f"❌ {message}"


def info(message):

    return f"ℹ️ {message}"

# ==========================================
# PRESUPUESTO
# ==========================================

def budget_item(item):

    return f"""📦 {item['ProductName']}
Cantidad: {item['Quantity']}
Precio: Q{item['UnitPrice']}
Subtotal: Q{item['Subtotal']}
"""


def budget(budget, customer_name, items):

    message = f"""📄 Presupuesto #{budget['Id']}

👤 Cliente:
{customer_name}

Estado:
🟡 En edición

────────────────────────
"""

    if not items:

        message += "\nSin productos.\n"

    else:

        for item in items:

            message += "\n" + budget_item(item)

    total = sum(
        item["Subtotal"]
        for item in items
    )

    message += f"""

────────────────────────

Productos:
{len(items)}

Total:
Q{total:.2f}
"""

    return message