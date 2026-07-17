"""
Herramienta de Clientes
"""
import os
import re
from datetime import datetime
from core.tool_registry import register

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from database.aronium import (
    crear_cliente_completo, buscar_cliente_completo,
    get_todos_clientes, get_historial_cliente, get_clientes_inactivos, get_descuentos,
    set_grupo_cliente, get_grupo_descuento, get_clientes_por_grupo, get_credito_cliente
)

ESTADOS_COTIZACION = {
    "PENDIENTE": "Pendiente", "ENVIADA": "Enviada", "ACEPTADA": "Aceptada",
    "RECHAZADA": "Rechazada", "VENCIDA": "Vencida",
}

ESTADOS_GARANTIA = {"VIGENTE": "Vigente", "VENCIDA": "Vencida", "RECLAMADA": "Reclamada"}


def _productos_de_descripcion(descripcion):
    """Extrae pares (cantidad, nombre) de la Descripcion de una Venta de forma
    best-effort (texto libre, no datos estructurados - el detalle real de items
    se borra al cobrar, ver CLAUDE.md). Se usa solo para calcular el producto
    favorito, no para nada financiero."""
    if not descripcion:
        return []
    segmento = descripcion.split("|")[0].strip()
    for prefijo in ("Cotizacion ", "Combo "):
        if segmento.startswith(prefijo) and ":" in segmento:
            segmento = segmento.split(":", 1)[1]
            break
    items = []
    for parte in segmento.split(","):
        m = re.match(r"\s*(\d+(?:\.\d+)?)\s*x\s+(.+?)(?:\s+a\s+Q[\d.]+)?\s*$", parte.strip())
        if m:
            items.append((float(m.group(1)), m.group(2).strip()))
    return items


def _producto_favorito(ventas):
    conteo = {}
    for v in ventas:
        for cantidad, nombre in _productos_de_descripcion(v.get("Descripcion", "")):
            conteo[nombre] = conteo.get(nombre, 0) + cantidad
    if not conteo:
        return None
    return max(conteo.items(), key=lambda kv: kv[1])[0]


def _frecuencia_compra(ventas):
    """Promedio de dias entre compras. None si no hay al menos 2 compras con fecha valida."""
    fechas = []
    for v in ventas:
        if not v.get("Fecha"):
            continue
        try:
            fechas.append(datetime.strptime(v["Fecha"][:19], "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            continue
    if len(fechas) < 2:
        return None
    fechas.sort()
    dias_totales = (fechas[-1] - fechas[0]).days
    intervalos = len(fechas) - 1
    if dias_totales <= 0:
        return None
    return round(dias_totales / intervalos, 1)


def _metodo_pago_de(descripcion):
    """Best-effort: solo el pago mixto deja rastro en la Descripcion (ver
    core/nimbo.py). Para efectivo/tarjeta/transferencia no hay dato guardado."""
    if descripcion and "Efectivo: Q" in descripcion and "Tarjeta: Q" in descripcion:
        return "mixto (efectivo + tarjeta)"
    return "no registrado"


def _descuento_cliente(cliente_id):
    for d in get_descuentos(activo=True, tipo="cliente"):
        if d["ClienteId"] == cliente_id:
            return d
    return None


def _estadisticas_cliente(cliente, historial):
    ventas = historial["ventas"]
    total_gastado = round(sum(v["Total"] for v in ventas), 2)
    descuento = _descuento_cliente(cliente["Id"])
    return {
        "total_gastado": total_gastado,
        "total_compras": len(ventas),
        "producto_favorito": _producto_favorito(ventas),
        "frecuencia_dias": _frecuencia_compra(ventas),
        "ultima_visita": ventas[0]["Fecha"][:10] if ventas else (cliente.get("UltimaCompra") or "").strip()[:10] or None,
        "descuento": descuento,
        "grupo": cliente.get("GrupoCliente") or "detallista",
        "credito_tienda": get_credito_cliente(cliente["Id"]),
    }


def _texto_estadisticas(stats):
    resp = f"Grupo: {stats['grupo'].capitalize()}\n"
    resp += f"Total gastado: Q{stats['total_gastado']} ({stats['total_compras']} compra(s))\n"
    resp += f"Producto favorito: {stats['producto_favorito'] or 'sin datos'}\n"
    if stats["frecuencia_dias"]:
        resp += f"Frecuencia de compra: cada {stats['frecuencia_dias']} dias en promedio\n"
    else:
        resp += "Frecuencia de compra: no hay suficientes compras para calcularla\n"
    resp += f"Ultima visita: {stats['ultima_visita'] or 'sin registro'}\n"
    if stats["credito_tienda"]:
        resp += f"Credito en tienda disponible: Q{stats['credito_tienda']}\n"
    if stats["descuento"]:
        d = stats["descuento"]
        valor = f"{d['Porcentaje']}%" if d.get("Porcentaje") else f"Q{d['MontoFijo']}"
        resp += f"Descuento individual configurado: {valor} ({d['Nombre']})\n"
    else:
        resp += "Descuento individual configurado: ninguno\n"
    return resp

def nuevo_cliente_tool(data):
    """Arranca el flujo conversacional que pregunta el grupo del cliente (detallista/
    mayorista/especial/vip) antes de crearlo - ver step cliente_waiting_grupo en
    core/nimbo.py. No crea el cliente todavia."""
    nombre = data.get("nombre", "") if isinstance(data, dict) else str(data)
    telefono = data.get("telefono", "") if isinstance(data, dict) else ""
    return f"CLIENTE_NUEVO_INICIO:{nombre}|{telefono}"

register("cliente.nuevo", nuevo_cliente_tool)

def buscar_cliente_tool(data):
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre cliente con '{query}'."
    resp = ""
    for c in clientes:
        resp += "Cliente: " + c["Nombre"] + "\n"
        resp += "Grupo: " + (c.get("GrupoCliente") or "detallista").capitalize() + "\n"
        resp += "Telefono: " + (c["Telefono"] or "—") + "\n"
        resp += "Email: " + (c["Email"] or "—") + "\n"
        resp += "NIT: " + (c["Nit"] or "—") + "\n"
        resp += "Ordenes de servicio: " + str(c["TotalOrdenes"]) + "\n"
        resp += "Compras registradas: " + str(c["TotalCompras"]) + "\n"
        total = c["TotalGastado"] or 0
        resp += "Total gastado: Q" + str(total) + "\n"
        if c["UltimaCompra"]:
            resp += "Ultima compra: " + c["UltimaCompra"] + "\n"
        resp += "---\n"
    return resp.strip()

register("cliente.buscar", buscar_cliente_tool)


def _detalle_grupo(grupo_info):
    """Texto corto describiendo el descuento/multiplicador automatico de un grupo."""
    if not grupo_info:
        return ""
    partes = []
    if grupo_info["PorcentajeDescuento"]:
        partes.append(f"{grupo_info['PorcentajeDescuento']}% de descuento automatico")
    mult = float(grupo_info["PuntosMultiplicador"] or 1)
    if mult != 1:
        partes.append(f"puntos x{mult:g}")
    return f" ({', '.join(partes)})" if partes else ""


def cambiar_grupo_cliente_tool(data):
    nombre = data.get("nombre", "").strip()
    grupo = data.get("grupo", "").strip()
    clientes = buscar_cliente_completo(nombre)
    if not clientes:
        return f"No encontre cliente con '{nombre}'."
    c = clientes[0]
    set_grupo_cliente(c["Id"], grupo)
    detalle = _detalle_grupo(get_grupo_descuento(grupo))
    return f"{c['Nombre']} ahora es {grupo}{detalle}."

register("cliente.grupo_set", cambiar_grupo_cliente_tool)


def ver_grupo_cliente_tool(data):
    query = (data.get("query", "") if isinstance(data, dict) else str(data)).strip()
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre cliente con '{query}'."
    c = clientes[0]
    grupo = c.get("GrupoCliente") or "detallista"
    detalle = _detalle_grupo(get_grupo_descuento(grupo))
    resp = f"{c['Nombre']} es {grupo}{detalle}."

    descuento_individual = _descuento_cliente(c["Id"])
    if descuento_individual:
        d = descuento_individual
        valor = f"{d['Porcentaje']}%" if d.get("Porcentaje") else f"Q{d['MontoFijo']}"
        resp += (f" Ademas tiene un descuento individual configurado ({valor}, {d['Nombre']}) "
                 f"que tiene prioridad sobre el del grupo.")
    return resp

register("cliente.grupo_ver", ver_grupo_cliente_tool)


def listar_grupo_cliente_tool(data):
    grupo = data.get("grupo", "").strip() if isinstance(data, dict) else str(data).strip()
    clientes = get_clientes_por_grupo(grupo)
    if not clientes:
        return f"No hay clientes en el grupo {grupo}."
    resp = f"{len(clientes)} cliente(s) en el grupo {grupo}:\n"
    for c in clientes:
        resp += f"- {c['Nombre']} | {c['Telefono'] or 'sin tel'}\n"
    return resp

register("cliente.grupo_listar", listar_grupo_cliente_tool)

def listar_clientes_tool(data):
    clientes = get_todos_clientes()
    if not clientes:
        return "No hay clientes registrados."
    resp = str(len(clientes)) + " clientes:\n"
    for c in clientes:
        resp += "- " + c["Nombre"] + " | " + (c["Telefono"] or "sin tel") 
        if c["TotalCompras"]:
            resp += " | " + str(c["TotalCompras"]) + " compras"
        resp += "\n"
    return resp

register("cliente.listar", listar_clientes_tool)

def historial_cliente_tool(data):
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre cliente con '{query}'."
    c = clientes[0]
    historial = get_historial_cliente(c["Id"])
    stats = _estadisticas_cliente(c, historial)

    resp = f"Historial completo de {c['Nombre']}:\n\n"
    resp += "DATOS DEL CLIENTE\n"
    resp += f"Telefono: {c['Telefono'] or '—'}\n"
    resp += f"Email: {c['Email'] or '—'}\n"
    resp += f"NIT: {c['Nit'] or '—'}\n"
    if c.get("FechaCreado"):
        resp += f"Cliente desde: {str(c['FechaCreado'])[:10]}\n"

    resp += "\nESTADISTICAS\n"
    resp += _texto_estadisticas(stats)

    resp += f"\nCOMPRAS ({len(historial['ventas'])})\n"
    if historial["ventas"]:
        for v in historial["ventas"]:
            metodo = _metodo_pago_de(v["Descripcion"])
            resp += f"- {v['Fecha'][:10]}: {v['Descripcion']} - Q{v['Total']} (Pago: {metodo})\n"
    else:
        resp += "Sin compras registradas.\n"

    resp += f"\nORDENES DE SERVICIO ({len(historial['ordenes'])})\n"
    if historial["ordenes"]:
        for o in historial["ordenes"]:
            resp += f"- {o['NumeroOrden']}: {o['Equipo']} {o['Marca']} | {o['Estado']}\n"
    else:
        resp += "Sin ordenes de servicio.\n"

    resp += f"\nCOTIZACIONES ({len(historial['cotizaciones'])})\n"
    if historial["cotizaciones"]:
        for cot in historial["cotizaciones"]:
            estado = ESTADOS_COTIZACION.get(cot["Estado"], cot["Estado"])
            resp += f"- {cot['NumeroC']} | Q{cot['Total']} | {estado}\n"
    else:
        resp += "Sin cotizaciones.\n"

    resp += f"\nGARANTIAS ACTIVAS ({len(historial['garantias'])})\n"
    if historial["garantias"]:
        for g in historial["garantias"]:
            resp += f"- {g['NumeroGarantia']} | {g['ProductoNombre']} | vence {str(g['FechaVencimientoPropias'])[:10]}\n"
    else:
        resp += "Sin garantias activas.\n"

    return resp

register("cliente.historial", historial_cliente_tool)


def resumen_cliente_tool(data):
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre cliente con '{query}'."
    c = clientes[0]
    historial = get_historial_cliente(c["Id"])
    stats = _estadisticas_cliente(c, historial)

    resp = f"Resumen de {c['Nombre']}:\n"
    resp += _texto_estadisticas(stats)

    garantias = historial["garantias"]
    resp += f"\nGarantias activas ({len(garantias)}):\n"
    if garantias:
        for g in garantias:
            resp += f"- {g['NumeroGarantia']} | {g['ProductoNombre']} | vence {str(g['FechaVencimientoPropias'])[:10]}\n"
    else:
        resp += "Ninguna.\n"

    return resp

register("cliente.resumen", resumen_cliente_tool)

def inactivos_tool(data):
    clientes = get_clientes_inactivos(meses=3)
    if not clientes:
        return "Todos los clientes han comprado en los ultimos 3 meses."
    resp = str(len(clientes)) + " clientes inactivos (sin compras en 3 meses):\n"
    for c in clientes:
        resp += "- " + c["Nombre"] + " | " + (c["Telefono"] or "sin tel")
        if c["UltimaCompra"]:
            resp += " | Ultima compra: " + c["UltimaCompra"][:10]
        else:
            resp += " | Sin compras registradas"
        resp += "\n"
    return resp

register("cliente.inactivos", inactivos_tool)

def excel_clientes_tool(data):
    import openpyxl
    from datetime import datetime
    clientes = get_todos_clientes(limit=1000)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clientes"
    ws.append(["Nombre", "Telefono", "Email", "NIT", "Direccion", "Total Ordenes", "Total Compras", "Total Gastado", "Ultima Compra"])
    for c in clientes:
        ws.append([
            c["Nombre"],
            c["Telefono"] or "",
            c["Email"] or "",
            c["Nit"] or "",
            c["Direccion"] or "",
            c["TotalOrdenes"] or 0,
            c["TotalCompras"] or 0,
            c["TotalGastado"] or 0,
            c["UltimaCompra"] or ""
        ])
    filename = os.path.join(BASE_DIR, "clientes_" + datetime.now().strftime("%Y%m%d") + ".xlsx")
    wb.save(filename)
    basename = "clientes_" + datetime.now().strftime("%Y%m%d") + ".xlsx"
    return f"DOWNLOAD:{basename}"

register("cliente.excel", excel_clientes_tool)
