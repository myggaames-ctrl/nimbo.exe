"""
Herramienta de Reembolsos
"""
from core.tool_registry import register
from database.aronium import buscar_cliente_completo, get_credito_cliente, get_reembolso


def _normalizar_numero(numero):
    numero = str(numero).strip().upper()
    numero = numero.replace("REM-", "").replace("REM", "").strip()
    return "REM-" + numero.zfill(4)


def _metodo_pago_de(descripcion):
    """Best-effort: solo el pago mixto deja rastro reconocible en la Descripcion de
    una Venta (ver core/nimbo.py, y la misma logica duplicada en
    tools/cliente_tool.py). Para efectivo/tarjeta/transferencia/credito simple no
    hay metodo de pago guardado en la Venta."""
    if descripcion and "Efectivo: Q" in descripcion and "Tarjeta: Q" in descripcion:
        return "mixto (efectivo + tarjeta)"
    return "no registrado"


def reembolso_iniciar_tool(data):
    venta_id = data.get("venta_id") if isinstance(data, dict) else data
    return f"REEMBOLSO_INICIO:{venta_id}"

register("reembolso.iniciar", reembolso_iniciar_tool)


def cambio_iniciar_tool(data):
    venta_id = data.get("venta_id") if isinstance(data, dict) else data
    return f"CAMBIO_PRODUCTO_INICIO:{venta_id}"

register("reembolso.iniciar_cambio", cambio_iniciar_tool)


def credito_tool(data):
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre cliente con '{query}'."
    c = clientes[0]
    credito = get_credito_cliente(c["Id"])
    if credito <= 0:
        return f"{c['Nombre']} no tiene credito en tienda disponible."
    return f"{c['Nombre']} tiene Q{credito} de credito en tienda disponible."

register("reembolso.credito", credito_tool)


def buscar_reembolso_tool(data):
    numero = _normalizar_numero(data.get("numero", "") if isinstance(data, dict) else data)
    r = get_reembolso(numero)
    if not r:
        return f"No encontre el reembolso {numero}."
    resp = f"Reembolso: {r['NumeroReembolso']}\n"
    resp += f"Venta: #{r['VentaId']}\n"
    resp += f"Cliente: {r['ClienteNombre'] or 'Consumidor Final'}\n"
    resp += f"Tipo: {r['Tipo']}\n"
    resp += f"Monto original de la venta: Q{r['MontoOriginal']}\n"
    resp += f"Monto reembolsado: Q{r['MontoReembolso']}\n"
    resp += f"Metodo de devolucion: {r['MetodoDevolucion']}\n"
    if r["ProductosDevueltos"]:
        resp += "Productos devueltos: " + ", ".join(
            f"{p['cantidad']}x {p['nombre']}" for p in r["ProductosDevueltos"]
        ) + "\n"
    if r["ProductoNuevo"]:
        resp += f"Producto nuevo: {r['ProductoNuevo']['nombre']}\n"
    if r["DiferenciaCobrada"]:
        resp += f"Diferencia cobrada: Q{r['DiferenciaCobrada']}\n"
    if r["DiferenciaDevuelta"]:
        resp += f"Diferencia devuelta: Q{r['DiferenciaDevuelta']}\n"
    if r["Motivo"]:
        resp += f"Motivo: {r['Motivo']}\n"
    resp += f"Estado: {r['Estado']}\n"
    resp += f"Fecha: {r['Fecha'][:16]}"
    return resp

register("reembolso.buscar", buscar_reembolso_tool)
