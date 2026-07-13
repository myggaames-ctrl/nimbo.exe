"""
Herramienta de Servicio Tecnico
"""
import re
from core.tool_registry import register
from database.aronium import (
    crear_cliente, buscar_cliente, crear_orden,
    get_ordenes, get_orden, actualizar_estado_orden,
    set_presupuesto_orden, get_historial_orden,
    get_garantia_reparacion_por_orden, reclamar_garantia_reparacion,
    get_fotos_orden, get_products, crear_informe_revision
)

ESTADOS_GARANTIA = {"VIGENTE": "Vigente", "VENCIDA": "Vencida", "RECLAMADA": "Reclamada"}

ESTADOS = {
    "RECEPCION": "Recepcion",
    "REVISION": "En revision",
    "PRESUPUESTO": "Presupuesto enviado",
    "APROBADO": "Aprobado por cliente",
    "REPARACION": "En reparacion",
    "LISTO": "Listo para recoger",
    "ENTREGADO": "Entregado",
    "RECHAZADO": "Rechazado por cliente",
}

def _miniaturas_html(fotos, tamano=110):
    imgs = "".join(
        f'<img src="{f["RutaFoto"]}" style="max-width:{tamano}px;max-height:{tamano}px;'
        f'border-radius:6px;margin:4px;object-fit:cover">'
        for f in fotos
    )
    return f'<div style="display:flex;flex-wrap:wrap;margin-top:6px">{imgs}</div>'


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
    fotos = get_fotos_orden(numero)
    if fotos:
        resp += f"\nFotos ({len(fotos)}):"
        resp += _miniaturas_html(fotos)
    return resp

register("service.buscar_orden", buscar_orden_tool)


def fotos_orden_tool(data):
    numero = data.get("numero", "") if isinstance(data, dict) else str(data)
    if not numero.startswith("OS-"):
        numero = "OS-" + numero.zfill(4)
    orden = get_orden(numero)
    if not orden:
        return "No encontre la orden " + numero + "."
    fotos = get_fotos_orden(numero)
    if not fotos:
        return (f"La orden {numero} no tiene fotos todavia. Puedes subirlas en el dashboard, "
                f"seccion Servicio Tecnico, orden {numero}.")
    resp = f"Fotos de la orden {numero} ({orden['Equipo']} {orden['Marca']}), {len(fotos)} foto(s):"
    resp += _miniaturas_html(fotos, tamano=220)
    return resp

register("service.fotos", fotos_orden_tool)

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

    if estado == "ENTREGADO":
        # No se marca ENTREGADO todavia: primero se pregunta cuantos dias de
        # garantia tiene la reparacion (ver step servicio_waiting_dias_garantia
        # en core/nimbo.py, arrancado por este marcador).
        return f"ENTREGA_GARANTIA_INICIO:{numero}"

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


def ver_garantia_reparacion_tool(data):
    numero = data.get("numero", "")
    if not numero.startswith("OS-"):
        numero = "OS-" + numero.zfill(4)
    orden = get_orden(numero)
    if not orden:
        return f"No encontre la orden {numero}."
    garantia = get_garantia_reparacion_por_orden(orden["Id"])
    if not garantia:
        return f"La orden {numero} no tiene una garantia de reparacion registrada (solo se genera al marcarla ENTREGADO)."
    resp = f"Garantia de reparacion {garantia['NumeroGarantia']} (orden {numero})\n"
    resp += f"Equipo: {garantia['ProductoNombre']}\n"
    resp += f"Cliente: {garantia['ClienteNombre']}\n"
    resp += f"Valida hasta: {str(garantia['FechaVencimientoPropias'])[:10]}\n"
    resp += f"Estado: {ESTADOS_GARANTIA.get(garantia['Estado'], garantia['Estado'])}"
    return resp

register("service.ver_garantia_reparacion", ver_garantia_reparacion_tool)


def reclamar_garantia_tool(data):
    numero = data.get("numero", "")
    if not numero.startswith("OS-"):
        numero = "OS-" + numero.zfill(4)
    orden = get_orden(numero)
    if not orden:
        return f"No encontre la orden {numero}."
    resultado = reclamar_garantia_reparacion(orden["Id"], numero)
    if resultado.get("error"):
        return resultado["error"]
    garantia = resultado["garantia"]
    resp = f"Garantia {garantia['NumeroGarantia']} de la orden {numero} reclamada."
    if resultado.get("numero_nueva_orden"):
        resp += f" Se creo la orden {resultado['numero_nueva_orden']} sin costo para la reparacion."
    return resp

register("service.reclamar_garantia", reclamar_garantia_tool)


def _parsear_item_informe(segmento):
    """'cuchilla 1 unidad' -> ('cuchilla', 1.0). Si no trae 'unidad(es)' pero termina en
    un numero ('empaque 2') tambien lo reconoce; si no trae cantidad, asume 1."""
    segmento = segmento.strip()
    m = re.match(r"^(.+?)\s+(\d+(?:\.\d+)?)\s*unidad(?:es)?$", segmento)
    if not m:
        m = re.match(r"^(.+?)\s+(\d+(?:\.\d+)?)$", segmento)
    if m:
        return m.group(1).strip(), float(m.group(2))
    return segmento, 1.0


def informe_tool(data):
    """PASO 3+4: 'informe OS-0001: necesita cuchilla 1 unidad y empaque 2 unidades mano
    de obra 75'. Busca cada producto en el inventario para resolver su precio, calcula
    el total (piezas + mano de obra), guarda el InformeRevision, actualiza la orden a
    PRESUPUESTO (via crear_informe_revision -> set_presupuesto_orden) y envia el
    presupuesto completo al cliente por WhatsApp."""
    from flask_login import current_user

    numero = data.get("numero", "")
    if not numero.startswith("OS-"):
        numero = "OS-" + numero.zfill(4)
    texto = data.get("texto", "").strip()

    orden = get_orden(numero)
    if not orden:
        return f"No encontre la orden {numero}."

    m = re.match(r"^(.*?)\s+mano\s+de\s+obra\s+(\d+(?:\.\d+)?)$", texto, re.IGNORECASE)
    if not m:
        return ("No pude leer el informe. Formato: 'informe " + numero + ": necesita [producto] "
                "[cantidad] unidad(es) y [producto] [cantidad] unidad(es) mano de obra [monto]'.")
    items_texto = re.sub(r"^necesita\s+", "", m.group(1).strip(), flags=re.IGNORECASE)
    mano_obra = float(m.group(2))

    productos_necesarios = []
    no_encontrados = []
    for segmento in re.split(r"\s*,\s*|\s+y\s+", items_texto):
        if not segmento.strip():
            continue
        nombre_buscado, cantidad = _parsear_item_informe(segmento)
        coincidencias = get_products(search=nombre_buscado)
        if coincidencias:
            p = coincidencias[0]
            productos_necesarios.append({"nombre": p["Name"].strip(), "cantidad": cantidad, "costo": p["Price"]})
        else:
            productos_necesarios.append({"nombre": nombre_buscado.strip().capitalize(), "cantidad": cantidad, "costo": 0})
            no_encontrados.append(nombre_buscado.strip())

    tecnico_id = int(current_user.id) if current_user.is_authenticated else None
    tecnico_nombre = (current_user.nombre or current_user.username) if current_user.is_authenticated else "Tecnico"

    resultado = crear_informe_revision(
        orden["Id"], numero, tecnico_id, tecnico_nombre,
        descripcion=texto, productos_necesarios=productos_necesarios, mano_obra=mano_obra
    )

    resp = f"Revision de {orden['Equipo']} {orden['Marca']}:\n"
    for p in productos_necesarios:
        resp += f"- {p['nombre']} x{p['cantidad']:g}: Q{p['costo'] * p['cantidad']:.2f}\n"
    resp += f"- Mano de obra: Q{mano_obra:.2f}\n"
    resp += f"Total: Q{resultado['total']:.2f}\n"
    resp += f"Orden {numero} actualizada a {ESTADOS['PRESUPUESTO']}."

    if no_encontrados:
        resp += (f"\nAviso: no encontre en inventario: {', '.join(no_encontrados)} "
                 f"(se registraron con costo Q0, ajusta el presupuesto si hace falta).")

    if orden.get("ClienteTelefono"):
        from services.whatsapp import enviar_presupuesto_whatsapp
        ok, msg = enviar_presupuesto_whatsapp(
            orden["ClienteTelefono"], orden["ClienteNombre"], numero,
            orden["Equipo"] + " " + orden["Marca"], productos_necesarios, mano_obra, resultado["total"]
        )
        resp += (f"\nPresupuesto enviado por WhatsApp a {orden['ClienteNombre']}." if ok
                  else f"\nNo se pudo enviar el presupuesto por WhatsApp: {msg}.")

    return resp

register("service.informe", informe_tool)


def aprobacion_cliente_tool(data):
    """PASO 5: 'cliente aprobo/rechazo OS-0001'. Aprobado -> estado APROBADO y aviso
    por WhatsApp al tecnico asignado. Rechazado -> estado RECHAZADO y aviso al cliente
    de que puede recoger su equipo sin costo."""
    numero = data.get("numero", "")
    if not numero.startswith("OS-"):
        numero = "OS-" + numero.zfill(4)
    aprobado = data.get("aprobado", False)

    orden = get_orden(numero)
    if not orden:
        return f"No encontre la orden {numero}."

    if aprobado:
        actualizar_estado_orden(numero, "APROBADO")
        resp = f"Orden {numero} marcada como aprobada por el cliente."
        if orden.get("TecnicoId") and orden.get("TecnicoNombre"):
            from database.aronium import nimbo_connect
            conn = nimbo_connect()
            cur = conn.cursor()
            cur.execute("SELECT Telefono FROM Usuario WHERE Id=?", (orden["TecnicoId"],))
            row = cur.fetchone()
            conn.close()
            tel_tecnico = row["Telefono"] if row else ""
            if tel_tecnico:
                from services.whatsapp import enviar_aprobacion_tecnico_whatsapp
                ok, msg = enviar_aprobacion_tecnico_whatsapp(
                    tel_tecnico, orden["TecnicoNombre"], numero, orden["Equipo"] + " " + orden["Marca"])
                resp += (f" Se aviso a {orden['TecnicoNombre']} por WhatsApp." if ok
                          else f" No se pudo avisar a {orden['TecnicoNombre']} por WhatsApp: {msg}.")
        else:
            resp += " La orden no tiene tecnico asignado."
        return resp

    actualizar_estado_orden(numero, "RECHAZADO")
    resp = f"Orden {numero} marcada como rechazada por el cliente."
    if orden.get("ClienteTelefono"):
        from services.whatsapp import enviar_rechazo_cliente_whatsapp
        ok, msg = enviar_rechazo_cliente_whatsapp(
            orden["ClienteTelefono"], orden["ClienteNombre"], numero, orden["Equipo"] + " " + orden["Marca"])
        resp += (f" Se aviso a {orden['ClienteNombre']} que puede recoger su equipo sin costo." if ok
                  else f" No se pudo avisar al cliente por WhatsApp: {msg}.")
    return resp

register("service.aprobacion_cliente", aprobacion_cliente_tool)
