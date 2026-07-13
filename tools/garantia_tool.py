"""
Herramienta de Garantias
"""
from core.tool_registry import register
from database.aronium import (
    get_products, set_garantia_producto, get_garantia_por_numero,
    get_garantias_cliente, get_garantias_por_vencer
)

ESTADOS = {"VIGENTE": "Vigente", "VENCIDA": "Vencida", "RECLAMADA": "Reclamada"}


def _normalizar_numero(numero):
    numero = str(numero).strip().upper()
    numero = numero.replace("GAR-", "").replace("GAR", "").strip()
    return "GAR-" + numero.zfill(4)


def configurar_garantia_tool(data):
    query = data.get("producto_query", "").strip()
    dias_fabrica = data.get("dias_fabrica")
    dias_propia = data.get("dias_propia")

    productos = get_products(search=query)
    if not productos:
        return f"No encontre ningun producto que coincida con '{query}'."
    producto = productos[0]
    nombre = producto["Name"].strip()
    set_garantia_producto(producto["Id"], nombre, dias_fabrica=dias_fabrica, dias_propia=dias_propia)

    if dias_fabrica is not None:
        return f"Garantia de {nombre} configurada: {dias_fabrica} dias de fabrica y {dias_propia} dias propios (Mi Cocina)."
    return f"Garantia de {nombre} configurada: {dias_propia} dias."

register("garantia.configurar", configurar_garantia_tool)


def ver_garantia_tool(data):
    numero = _normalizar_numero(data.get("numero", ""))
    g = get_garantia_por_numero(numero)
    if not g:
        return f"No encontre la garantia {numero}."
    resp = f"Garantia {g['NumeroGarantia']}\n"
    resp += f"Producto: {g['ProductoNombre']}\n"
    tel = f" ({g['ClienteTelefono']})" if g.get("ClienteTelefono") else ""
    resp += f"Cliente: {g['ClienteNombre']}{tel}\n"
    resp += f"Venta: {str(g['FechaVenta'])[:10]}\n"
    if g.get("FechaVencimientoFabrica"):
        resp += f"Garantia de fabrica hasta: {str(g['FechaVencimientoFabrica'])[:10]}\n"
    resp += f"Garantia propia (Mi Cocina) hasta: {str(g['FechaVencimientoPropias'])[:10]}\n"
    resp += f"Estado: {ESTADOS.get(g['Estado'], g['Estado'])}"
    if g.get("Notas"):
        resp += f"\nNotas: {g['Notas']}"
    return resp

register("garantia.ver", ver_garantia_tool)


def garantias_cliente_tool(data):
    query = data.get("cliente_query", "").strip()
    garantias = get_garantias_cliente(query)
    if not garantias:
        return f"No encontre garantias para '{query}'."
    resp = f"{len(garantias)} garantia(s) de {query}:\n"
    for g in garantias:
        resp += f"- {g['NumeroGarantia']} | {g['ProductoNombre']} | {ESTADOS.get(g['Estado'], g['Estado'])} | vence {str(g['FechaVencimientoPropias'])[:10]}\n"
    return resp

register("garantia.por_cliente", garantias_cliente_tool)


def garantias_por_vencer_tool(data):
    garantias = get_garantias_por_vencer(dias=30)
    if not garantias:
        return "No hay garantias por vencer en los proximos 30 dias."
    resp = f"{len(garantias)} garantia(s) por vencer en los proximos 30 dias:\n"
    for g in garantias:
        vence = str(g.get("VenceEfectivo") or g["FechaVencimientoPropias"])[:10]
        resp += f"- {g['NumeroGarantia']} | {g['ProductoNombre']} | {g['ClienteNombre']} | vence {vence}\n"
    return resp

register("garantia.por_vencer", garantias_por_vencer_tool)
