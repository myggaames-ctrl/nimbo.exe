"""
Herramienta de Servicio Tecnico
"""
from core.tool_registry import register
from database.aronium import (
    crear_cliente, buscar_cliente, crear_orden,
    get_ordenes, get_orden, actualizar_estado_orden,
    set_presupuesto_orden, get_historial_orden
)

ESTADOS = {
    "RECEPCION": "Recepcion",
    "REVISION": "En revision",
    "PRESUPUESTO": "Presupuesto enviado",
    "APROBADO": "Aprobado por cliente",
    "REPARACION": "En reparacion",
    "LISTO": "Listo para recoger",
    "ENTREGADO": "Entregado"
}

def buscar_orden_tool(data):
    numero = data.get("numero", "")
    if not numero.startswith("OS-"):
        numero = "OS-" + numero.zfill(4)
    orden = get_orden(numero)
    if not orden:
        return "No encontre la orden " + numero + "."
    historial = get_historial_orden(numero)
    total = float(orden["Presupuesto"]) + float(orden["ManoObra"])
    resp = "Orden: " + orden["NumeroOrden"] + "\n"
    resp += "Cliente: " + orden["ClienteNombre"] + " - " + orden["ClienteTelefono"] + "\n"
    resp += "Equipo: " + orden["Equipo"] + " " + orden["Marca"] + " " + orden["Modelo"] + "\n"
    resp += "Problema: " + orden["Problema"] + "\n"
    resp += "Estado: " + ESTADOS.get(orden["Estado"], orden["Estado"]) + "\n"
    resp += "Presupuesto: Q" + str(orden["Presupuesto"]) + " + MO Q" + str(orden["ManoObra"]) + " = Q" + str(total) + "\n"
    resp += "Recibido: " + orden["FechaRecepcion"]
    if historial:
        resp += "\nHistorial:"
        for h in historial:
            resp += "\n- " + h["Fecha"] + ": " + h["Estado"] + " - " + h["Nota"]
    return resp

register("service.buscar_orden", buscar_orden_tool)

def listar_ordenes_tool(data):
    estado = data.get("estado")
    ordenes = get_ordenes(estado=estado)
    if not ordenes:
        msg = "No hay ordenes"
        if estado:
            msg += " en estado " + estado
        return msg + "."
    resp = str(len(ordenes)) + " ordenes:\n"
    for o in ordenes:
        total = float(o["Presupuesto"]) + float(o["ManoObra"])
        resp += "- " + o["NumeroOrden"] + " | " + o["ClienteNombre"] + " | " + o["Equipo"] + " " + o["Marca"] + " | " + ESTADOS.get(o["Estado"], o["Estado"])
        if total > 0:
            resp += " | Q" + str(total)
        resp += "\n"
    return resp

register("service.listar", listar_ordenes_tool)

def cambiar_estado_tool(data):
    numero = data.get("numero", "")
    estado = data.get("estado", "")
    if not numero.startswith("OS-"):
        numero = "OS-" + numero.zfill(4)
    orden = get_orden(numero)
    if not orden:
        return "No encontre la orden " + numero + "."
    actualizar_estado_orden(numero, estado)
    estado_texto = ESTADOS.get(estado, estado)
    if estado == "LISTO" and orden.get("ClienteTelefono"):
        from services.whatsapp import enviar_notificacion_orden
        ok, msg = enviar_notificacion_orden(
            orden["ClienteTelefono"],
            orden["ClienteNombre"],
            numero,
            orden["Equipo"] + " " + orden["Marca"],
            estado
        )
        if ok:
            return "Orden " + numero + " lista. Mensaje de WhatsApp enviado a " + orden["ClienteNombre"] + " (" + orden["ClienteTelefono"] + ")."
        else:
            return "Orden " + numero + " lista. No se pudo enviar WhatsApp: " + msg + ". Avisa manualmente al " + orden["ClienteTelefono"] + "."
    if estado == "ENTREGADO":
        return "Orden " + numero + " entregada al cliente."
    return "Orden " + numero + " actualizada a: " + estado_texto + "."

register("service.cambiar_estado", cambiar_estado_tool)

def presupuesto_tool(data):
    numero = data.get("numero", "")
    repuestos = data.get("repuestos", 0)
    mano_obra = data.get("mano_obra", 0)
    if not numero.startswith("OS-"):
        numero = "OS-" + numero.zfill(4)
    orden = get_orden(numero)
    if not orden:
        return "No encontre la orden " + numero + "."
    set_presupuesto_orden(numero, repuestos, mano_obra)
    total = repuestos + mano_obra
    return "Presupuesto de " + numero + " actualizado. Repuestos: Q" + str(repuestos) + ", Mano de obra: Q" + str(mano_obra) + ", Total: Q" + str(total) + ". Avisa al cliente " + orden["ClienteNombre"] + "."

register("service.presupuesto", presupuesto_tool)

def nueva_orden_tool(data):
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    return "NUEVA_ORDEN:" + query

register("service.nueva_orden", nueva_orden_tool)
