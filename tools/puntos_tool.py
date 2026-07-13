"""
Herramienta de Programa de Lealtad (Puntos)
"""
from core.tool_registry import register
from database.aronium import (
    buscar_cliente_completo, get_puntos_cliente, get_saldo_puntos, get_nivel_lealtad,
    puntos_a_quetzales, canjear_puntos, get_clientes_con_puntos
)


def ver_puntos_tool(data):
    query = data.get("cliente_query", "").strip()
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre cliente con '{query}'."
    c = clientes[0]
    p = get_puntos_cliente(c["Id"])
    saldo = get_saldo_puntos(c["Id"])
    valor = puntos_a_quetzales(saldo)
    nivel = get_nivel_lealtad(p["PuntosAcumulados"]) if p else "Bronce"

    resp = f"{c['Nombre']} tiene {saldo} puntos disponibles (Q{valor} en descuentos). Nivel: {nivel}."
    if nivel == "Oro":
        resp += " Tiene 5% de descuento extra en todas sus compras."
    if p:
        resp += f" (Acumulados historicos: {int(p['PuntosAcumulados'])}, usados: {int(p['PuntosUsados'])}.)"
    return resp

register("puntos.ver", ver_puntos_tool)


def canjear_puntos_tool(data):
    puntos = data.get("puntos", 0)
    query = data.get("cliente_query", "").strip()
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre cliente con '{query}'."
    c = clientes[0]

    resultado = canjear_puntos(c["Id"], c["Nombre"], puntos)
    if resultado.get("error"):
        return resultado["error"]

    return (f"Canjeados {resultado['puntos']} puntos de {c['Nombre']} por Q{resultado['credito']} "
            f"de descuento. Se aplicara automaticamente en su siguiente compra. "
            f"Puntos restantes: {resultado['saldo_restante']}.")

register("puntos.canjear", canjear_puntos_tool)


def puntos_disponibles_tool(data):
    clientes = get_clientes_con_puntos()
    if not clientes:
        return "Ningun cliente tiene puntos acumulados todavia."
    resp = f"{len(clientes)} cliente(s) con puntos disponibles:\n"
    for c in clientes:
        saldo = int(c["Saldo"])
        valor = puntos_a_quetzales(saldo)
        nivel = get_nivel_lealtad(c["PuntosAcumulados"])
        resp += f"- {c['ClienteNombre']}: {saldo} puntos (Q{valor}) | Nivel {nivel}\n"
    return resp

register("puntos.disponibles", puntos_disponibles_tool)
