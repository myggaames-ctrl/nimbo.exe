"""
Herramienta de Cuentas por Pagar
"""
from core.tool_registry import register
from database.nimbo_db import (
    buscar_proveedor, crear_cuenta_pagar, get_cuenta_pagar_por_id,
    registrar_pago_proveedor, get_cuentas_pagar, get_cuentas_proveedor
)

ESTADOS = {
    "PENDIENTE": "Pendiente", "PAGADO_PARCIAL": "Pago parcial",
    "PAGADO": "Pagado", "VENCIDO": "Vencido"
}


def crear_cuenta_tool(data):
    proveedor_query = data.get("proveedor_query", "").strip()
    monto = data.get("monto")
    descripcion = data.get("descripcion") or "Deuda general"

    proveedores = buscar_proveedor(proveedor_query)
    if not proveedores:
        return f"No encontre ningun proveedor que coincida con '{proveedor_query}'. Registra al proveedor primero."
    proveedor = proveedores[0]

    cuenta_id = crear_cuenta_pagar(
        proveedor["Id"], proveedor["Nombre"], proveedor.get("WhatsApp", ""), descripcion, monto
    )
    cuenta = get_cuenta_pagar_por_id(cuenta_id)
    return (f"Cuenta por pagar creada a {proveedor['Nombre']}: Q{monto} por {descripcion}. "
            f"Vence el {str(cuenta['FechaVencimiento'])[:10]}.")

register("cuentapagar.crear", crear_cuenta_tool)


def pagar_tool(data):
    proveedor_query = data.get("proveedor_query", "").strip()
    monto = data.get("monto")

    proveedores = buscar_proveedor(proveedor_query)
    if not proveedores:
        return f"No encontre ningun proveedor que coincida con '{proveedor_query}'."
    proveedor = proveedores[0]

    resultado = registrar_pago_proveedor(proveedor["Id"], monto)
    if not resultado:
        return f"No tienes cuentas por pagar pendientes con {proveedor['Nombre']}."

    resp = f"Pago de Q{monto} registrado a {proveedor['Nombre']}:\n"
    for a in resultado["aplicados"]:
        resp += f"- {a['descripcion']}: Q{a['monto']} ({ESTADOS.get(a['estado'], a['estado'])})\n"
    if resultado["sobrante"] > 0:
        resp += f"Sobrante sin aplicar: Q{resultado['sobrante']} (no tienes mas cuentas pendientes con este proveedor)."
    return resp.strip()

register("cuentapagar.pagar", pagar_tool)


def consultar_tool(data):
    proveedor_query = data.get("proveedor_query", "").strip()
    cuentas = get_cuentas_proveedor(proveedor_query)
    if not cuentas:
        return f"No le debes nada a '{proveedor_query}'."

    total = round(sum(c["MontoPendiente"] for c in cuentas), 2)
    nombre = cuentas[0]["ProveedorNombre"]
    resp = f"Le debes Q{total} a {nombre} en total:\n"
    for c in cuentas:
        resp += (f"- {c['Descripcion']}: Q{c['MontoPendiente']} pendiente "
                 f"({ESTADOS.get(c['Estado'], c['Estado'])}, vence {str(c['FechaVencimiento'])[:10]})\n")
    return resp.strip()

register("cuentapagar.consultar", consultar_tool)


def listar_tool(data):
    cuentas = get_cuentas_pagar()
    if not cuentas:
        return "No hay cuentas por pagar pendientes."
    total = round(sum(c["MontoPendiente"] for c in cuentas), 2)
    resp = f"{len(cuentas)} cuenta(s) por pagar, total Q{total}:\n"
    for c in cuentas:
        resp += (f"- {c['ProveedorNombre']}: Q{c['MontoPendiente']} ({c['Descripcion']}) | "
                 f"{ESTADOS.get(c['Estado'], c['Estado'])} | vence {str(c['FechaVencimiento'])[:10]}\n")
    return resp.strip()

register("cuentapagar.listar", listar_tool)


def vencidas_tool(data):
    cuentas = get_cuentas_pagar(estado="VENCIDO")
    if not cuentas:
        return "No hay pagos vencidos."
    total = round(sum(c["MontoPendiente"] for c in cuentas), 2)
    resp = f"{len(cuentas)} pago(s) vencido(s), total Q{total}:\n"
    for c in cuentas:
        resp += f"- {c['ProveedorNombre']}: Q{c['MontoPendiente']} ({c['Descripcion']}) | vencio {str(c['FechaVencimiento'])[:10]}\n"
    return resp.strip()

register("cuentapagar.vencidas", vencidas_tool)
