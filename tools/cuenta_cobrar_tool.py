"""
Herramienta de Cuentas por Cobrar
"""
from core.tool_registry import register
from database.nimbo_db import (
    buscar_cliente_completo, crear_cuenta_cobrar, get_cuenta_por_id,
    registrar_pago_cliente, get_cuentas_cobrar, get_cuentas_cliente
)

ESTADOS = {
    "PENDIENTE": "Pendiente", "PAGADO_PARCIAL": "Pago parcial",
    "PAGADO": "Pagado", "VENCIDO": "Vencido"
}


def crear_cuenta_tool(data):
    cliente_query = data.get("cliente_query", "").strip()
    monto = data.get("monto")
    descripcion = data.get("descripcion") or "Deuda general"

    clientes = buscar_cliente_completo(cliente_query)
    if not clientes:
        return f"No encontre ningun cliente que coincida con '{cliente_query}'. Registra al cliente primero."
    cliente = clientes[0]

    cuenta_id = crear_cuenta_cobrar(
        cliente["Id"], cliente["Nombre"], cliente.get("Telefono", ""), descripcion, monto
    )
    cuenta = get_cuenta_por_id(cuenta_id)
    return (f"Cuenta por cobrar creada para {cliente['Nombre']}: Q{monto} por {descripcion}. "
            f"Vence el {str(cuenta['FechaVencimiento'])[:10]}.")

register("cuentacobrar.crear", crear_cuenta_tool)


def pagar_tool(data):
    cliente_query = data.get("cliente_query", "").strip()
    monto = data.get("monto")

    clientes = buscar_cliente_completo(cliente_query)
    if not clientes:
        return f"No encontre ningun cliente que coincida con '{cliente_query}'."
    cliente = clientes[0]

    resultado = registrar_pago_cliente(cliente["Id"], monto)
    if not resultado:
        return f"{cliente['Nombre']} no tiene cuentas por cobrar pendientes."

    resp = f"Abono de Q{monto} registrado para {cliente['Nombre']}:\n"
    for a in resultado["aplicados"]:
        resp += f"- {a['descripcion']}: Q{a['monto']} ({ESTADOS.get(a['estado'], a['estado'])})\n"
    if resultado["sobrante"] > 0:
        resp += f"Sobrante sin aplicar: Q{resultado['sobrante']} (no tiene mas cuentas pendientes)."
    return resp.strip()

register("cuentacobrar.pagar", pagar_tool)


def consultar_tool(data):
    cliente_query = data.get("cliente_query", "").strip()
    cuentas = get_cuentas_cliente(cliente_query)
    if not cuentas:
        return f"'{cliente_query}' no tiene deudas pendientes."

    total = round(sum(c["MontoPendiente"] for c in cuentas), 2)
    nombre = cuentas[0]["ClienteNombre"]
    resp = f"{nombre} debe Q{total} en total:\n"
    for c in cuentas:
        resp += (f"- {c['Descripcion']}: Q{c['MontoPendiente']} pendiente "
                 f"({ESTADOS.get(c['Estado'], c['Estado'])}, vence {str(c['FechaVencimiento'])[:10]})\n")
    return resp.strip()

register("cuentacobrar.consultar", consultar_tool)


def listar_tool(data):
    cuentas = get_cuentas_cobrar()
    if not cuentas:
        return "No hay cuentas por cobrar pendientes."
    total = round(sum(c["MontoPendiente"] for c in cuentas), 2)
    resp = f"{len(cuentas)} cuenta(s) por cobrar, total Q{total}:\n"
    for c in cuentas:
        resp += (f"- {c['ClienteNombre']}: Q{c['MontoPendiente']} ({c['Descripcion']}) | "
                 f"{ESTADOS.get(c['Estado'], c['Estado'])} | vence {str(c['FechaVencimiento'])[:10]}\n")
    return resp.strip()

register("cuentacobrar.listar", listar_tool)


def vencidas_tool(data):
    cuentas = get_cuentas_cobrar(estado="VENCIDO")
    if not cuentas:
        return "No hay cuentas vencidas."
    total = round(sum(c["MontoPendiente"] for c in cuentas), 2)
    resp = f"{len(cuentas)} cuenta(s) vencida(s), total Q{total}:\n"
    for c in cuentas:
        resp += f"- {c['ClienteNombre']}: Q{c['MontoPendiente']} ({c['Descripcion']}) | vencio {str(c['FechaVencimiento'])[:10]}\n"
    return resp.strip()

register("cuentacobrar.vencidas", vencidas_tool)
