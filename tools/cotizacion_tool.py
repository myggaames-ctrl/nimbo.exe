"""
Herramienta de Cotizaciones
"""
import json
from core.tool_registry import register
from database.aronium import (
    get_cotizacion, get_cotizaciones, actualizar_estado_cotizacion,
    marcar_cotizacion_enviada, remove_stock, registrar_venta_cliente, get_product_by_id,
    generar_garantia_venta
)

ESTADOS = {
    "PENDIENTE": "Pendiente",
    "ENVIADA": "Enviada",
    "ACEPTADA": "Aceptada",
    "RECHAZADA": "Rechazada",
    "VENCIDA": "Vencida",
}


def _normalizar_numero(numero):
    numero = str(numero).strip().upper()
    numero = numero.replace("COT-", "").replace("COT", "").strip()
    return "COT-" + numero.zfill(4)


def nueva_cotizacion_tool(data):
    cliente = data.get("cliente", "").strip() if isinstance(data, dict) else ""
    return f"COTIZACION_INICIO:{cliente}"

register("cotizacion.nueva", nueva_cotizacion_tool)


def buscar_cotizacion_tool(data):
    numero = _normalizar_numero(data.get("numero", ""))
    c = get_cotizacion(numero)
    if not c:
        return f"No encontre la cotizacion {numero}."
    items = json.loads(c["Items"])
    resp = f"Cotizacion: {c['NumeroC']}\n"
    resp += f"Cliente: {c['ClienteNombre']} - {c.get('ClienteTelefono') or 'sin telefono'}\n"
    resp += "Productos:\n"
    for i in items:
        resp += f"- {i['cantidad']}x {i['nombre']} a Q{i['precio_unit']} = Q{i['subtotal']}\n"
    resp += f"Total: Q{c['Total']}\n"
    resp += f"Estado: {ESTADOS.get(c['Estado'], c['Estado'])}\n"
    resp += f"Creada: {c['FechaCreada'][:10]} | Vence: {c['FechaVencimiento'][:10]}"
    return resp

register("cotizacion.buscar", buscar_cotizacion_tool)


def listar_cotizaciones_tool(data):
    estado = data.get("estado") if isinstance(data, dict) else None
    cotizaciones = get_cotizaciones(estado=estado)
    if not cotizaciones:
        msg = "No hay cotizaciones"
        if estado:
            msg += " " + ESTADOS.get(estado, estado).lower() + "s"
        return msg + "."
    resp = f"{len(cotizaciones)} cotizacion(es):\n"
    for c in cotizaciones:
        resp += f"- {c['NumeroC']} | {c['ClienteNombre']} | Q{c['Total']} | {ESTADOS.get(c['Estado'], c['Estado'])}\n"
    return resp

register("cotizacion.listar", listar_cotizaciones_tool)


def marcar_enviada_tool(data):
    numero = _normalizar_numero(data.get("numero", ""))
    c = get_cotizacion(numero)
    if not c:
        return f"No encontre la cotizacion {numero}."
    if c["Estado"] != "PENDIENTE":
        return f"La cotizacion {numero} ya esta en estado {ESTADOS.get(c['Estado'], c['Estado'])}."
    marcar_cotizacion_enviada(numero)
    return f"Cotizacion {numero} marcada como enviada."

register("cotizacion.marcar_enviada", marcar_enviada_tool)


def aceptar_cotizacion_tool(data):
    numero = _normalizar_numero(data.get("numero", ""))
    c = get_cotizacion(numero)
    if not c:
        return f"No encontre la cotizacion {numero}."
    if c["Estado"] == "ACEPTADA":
        return f"La cotizacion {numero} ya estaba marcada como aceptada."
    if c["Estado"] == "RECHAZADA":
        return f"La cotizacion {numero} esta rechazada. No se puede aceptar."

    items = json.loads(c["Items"])

    # Verificar stock de todos los productos antes de descontar nada
    for item in items:
        producto = get_product_by_id(item["producto_id"])
        stock = producto["Stock"] if producto else 0
        if stock < item["cantidad"]:
            return (f"Stock insuficiente de {item['nombre']} para aceptar la cotizacion "
                     f"({int(stock)} disponibles, se necesitan {item['cantidad']}).")

    for item in items:
        remove_stock(item["producto_id"], item["cantidad"], razon=f"Venta por cotizacion {numero}")

    descripcion = f"Cotizacion {numero}: " + ", ".join([f"{i['cantidad']}x {i['nombre']}" for i in items])
    venta_id = registrar_venta_cliente(c["ClienteId"], descripcion, c["Total"])

    garantias = [
        generar_garantia_venta(
            venta_id, item["producto_id"], item["nombre"],
            cliente_id=c["ClienteId"], cliente_nombre=c["ClienteNombre"],
            cliente_telefono=c.get("ClienteTelefono") or ""
        )
        for item in items
    ]

    actualizar_estado_cotizacion(numero, "ACEPTADA")

    resp = f"Cotizacion {numero} aceptada. Venta registrada por Q{c['Total']} y stock descontado."
    if garantias:
        resp += "\nGarantias generadas: " + ", ".join(
            f"{g['numero']} ({p['nombre']}, hasta {g['vencimiento_propia']})" for g, p in zip(garantias, items)
        )
    return resp

register("cotizacion.aceptar", aceptar_cotizacion_tool)


def rechazar_cotizacion_tool(data):
    numero = _normalizar_numero(data.get("numero", ""))
    c = get_cotizacion(numero)
    if not c:
        return f"No encontre la cotizacion {numero}."
    if c["Estado"] == "ACEPTADA":
        return f"La cotizacion {numero} ya fue aceptada. No se puede rechazar."
    actualizar_estado_cotizacion(numero, "RECHAZADA")
    return f"Cotizacion {numero} marcada como rechazada."

register("cotizacion.rechazar", rechazar_cotizacion_tool)
