"""
Herramienta de Eventos y Fidelizacion de Clientes
"""
from core.tool_registry import register
from database.aronium import get_analisis_clientes
from google import genai
import os

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_gemini = None
if GEMINI_API_KEY:
    _gemini = genai.Client(api_key=GEMINI_API_KEY)

def analisis_clientes_tool(data):
    analisis = get_analisis_clientes()
    mejores = analisis["mejores"]
    inactivos = analisis["inactivos"]
    
    if not _gemini:
        return "Gemini no configurado."
    
    prompt = f"""Eres el estratega de clientes de Mi Cocina Electrodomesticos Guatemala.
Tienda de electrodomesticos y repuestos. La mayoria de clientes son mujeres amas de casa.

Datos del trimestre Q{analisis['trimestre']} {analisis['anio']}:
Total clientes: {analisis['total_clientes']}

Mejores clientes:
{chr(10).join([f"- {c['Nombre']}: Q{c['total']} en {c['compras']} compras" for c in mejores]) if mejores else "Sin datos"}

Clientes inactivos (mas de 3 meses):
{chr(10).join([f"- {c['Nombre']}: ultima compra {c['UltimaCompra'] or 'nunca'}" for c in inactivos]) if inactivos else "Ninguno"}

Con base en estos datos:
1. Analiza el comportamiento de los clientes
2. Sugiere UN evento especifico para este trimestre (tipo, fecha sugerida, que ofrecer, costo estimado, potencial de ventas)
3. Lista los 5 mejores clientes que deberian recibir mensaje de agradecimiento
4. Sugiere el mensaje de agradecimiento personalizado para ellos

Responde en espanol, de forma practica y especifica para Guatemala."""

    r = _gemini.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    return r.text

register("evento.analisis", analisis_clientes_tool)

def mensaje_agradecimiento_tool(data):
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    from database.aronium import buscar_cliente_completo, get_historial_cliente
    
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre cliente '{query}'."
    
    c = clientes[0]
    historial = get_historial_cliente(c["Id"])
    total_compras = c.get("TotalCompras", 0) or 0
    total_gastado = c.get("TotalGastado", 0) or 0
    
    if not _gemini:
        return "Gemini no configurado."
    
    prompt = f"""Crea un mensaje de agradecimiento personalizado para WhatsApp para este cliente de Mi Cocina Electrodomesticos Guatemala.

Cliente: {c['Nombre']}
Compras realizadas: {total_compras}
Total gastado: Q{total_gastado}

El mensaje debe ser:
- Caloroso y genuino
- En espanol guatemalteco natural
- Corto (maximo 3 parrafos)
- Mencionar su fidelidad
- Invitarla/o a visitarnos
- Sin ser demasiado comercial
- Firmado como Mi Cocina Electrodomesticos"""

    r = _gemini.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    mensaje = r.text.strip()
    
    if c.get("Telefono"):
        tel = c["Telefono"].replace("+","").replace("-","").replace(" ","")
        if not tel.startswith("502"):
            tel = "502" + tel
        link = f"https://wa.me/{tel}?text={mensaje.replace(' ','%20')[:500]}"
        return f"{mensaje}\n\n<a href='{link}' target='_blank' style='color:var(--accent)'>📱 Enviar por WhatsApp a {c['Nombre']}</a>"
    
    return mensaje

register("evento.agradecimiento", mensaje_agradecimiento_tool)

def sugerir_evento_tool(data):
    analisis = get_analisis_clientes()
    
    if not _gemini:
        return "Gemini no configurado."
    
    prompt = f"""Eres el estratega de marketing de Mi Cocina Electrodomesticos Guatemala.
Tienda de electrodomesticos y repuestos. La mayoria de clientes son mujeres.
Ubicacion: Guatemala City.

Datos actuales:
- Total clientes: {analisis['total_clientes']}
- Mejores clientes este trimestre: {len(analisis['mejores'])}
- Clientes inactivos: {len(analisis['inactivos'])}

Sugiere el evento perfecto para fidelizar clientes considerando:
1. Temporada actual (mes {analisis['anio']})
2. Tipo de negocio (electrodomesticos)
3. Perfil de clientes (principalmente mujeres guatemaltecas)
4. Presupuesto bajo (negocio pequeno)

Para el evento incluye:
- Nombre del evento
- Fecha y hora sugerida
- Actividades concretas (demostraciones, rifas, refaccion, etc.)
- Costo estimado en quetzales
- Potencial de ventas
- Lista de invitados sugeridos de los mejores clientes
- Mensaje de invitacion por WhatsApp listo para enviar

Se creativo pero realista para Guatemala."""

    r = _gemini.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    return r.text

register("evento.sugerir", sugerir_evento_tool)


def agregar_pago_tool(data):
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    return f"PAGO_INICIO:{query}"

register("pago.agregar", agregar_pago_tool)

def listar_pagos_tool(data):
    from database.aronium import get_pagos_fijos
    pagos = get_pagos_fijos()
    if not pagos:
        return "No hay pagos fijos registrados. Di 'agregar pago renta' para agregar uno."
    resp = f"{len(pagos)} pagos fijos registrados:\n"
    for p in pagos:
        monto = f"Q{p['Monto']:.2f}" if p["Monto"] else "sin monto"
        resp += f"- {p['Nombre']} | Dia {p['DiaPago']} | {p['Frecuencia']} | {monto}\n"
    return resp

register("pago.listar", listar_pagos_tool)

def monto_pago_tool(data):
    if isinstance(data, str): return "Error: datos invalidos"
    from database.aronium import set_monto_pago_fijo
    nombre = data.get("query", "")
    monto = data.get("monto", 0)
    coincidencias = set_monto_pago_fijo(nombre, monto)
    if not coincidencias:
        return f"No encontre ningun pago fijo activo llamado '{nombre}'."
    if len(coincidencias) > 1:
        nombres = ", ".join(c["Nombre"] for c in coincidencias)
        return f"'{nombre}' coincide con varios pagos fijos ({nombres}). Se mas especifico."
    return f"Monto de '{coincidencias[0]['Nombre']}' actualizado a Q{monto:.2f}."

register("pago.monto", monto_pago_tool)

def agregar_recordatorio_tool(data):
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    from database.aronium import agregar_recordatorio
    agregar_recordatorio(query)
    return f"Recordatorio agregado: {query}"

register("recordatorio.agregar", agregar_recordatorio_tool)

def agregar_cumpleanos_tool(data):
    if isinstance(data, str): return "Error: datos invalidos"
    from database.aronium import buscar_cliente_completo, set_cumpleanos_cliente
    query = data.get("query", "")
    fecha = data.get("fecha", "")
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre cliente '{query}'."
    c = clientes[0]
    partes = fecha.replace("-", "/").split("/")
    if len(partes) == 2:
        from datetime import datetime
        anio = datetime.now().year
        fecha_completa = f"{anio}-{partes[1].zfill(2)}-{partes[0].zfill(2)}"
    else:
        fecha_completa = fecha
    set_cumpleanos_cliente(c["Id"], fecha_completa)
    return f"Cumpleanos de {c['Nombre']} registrado el {fecha}. Te avisare 3 dias antes."

register("cumpleanos.agregar", agregar_cumpleanos_tool)


def consultar_cumpleanos_tool(data):
    from database.aronium import buscar_cliente_completo
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre cliente '{query}'."
    c = clientes[0]
    if not c.get("FechaCumpleanos"):
        return f"{c['Nombre']} no tiene cumpleanos registrado. Escribe 'cumpleanos de {c['Nombre']} es DD/MM' para registrarlo."
    partes = c["FechaCumpleanos"].split("-")
    fecha_legible = f"{partes[2]}/{partes[1]}" if len(partes) == 3 else c["FechaCumpleanos"]
    return f"El cumpleanos de {c['Nombre']} es el {fecha_legible}."

register("cumpleanos.consultar", consultar_cumpleanos_tool)
