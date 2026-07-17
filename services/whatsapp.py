import os
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

WA_TOKEN = os.getenv("WA_TOKEN", "")
WA_PHONE_ID = os.getenv("WA_PHONE_ID", "")
WA_API_URL = f"https://graph.facebook.com/v21.0/{WA_PHONE_ID}/messages"

def enviar_whatsapp(telefono, mensaje):
    if not WA_TOKEN or not WA_PHONE_ID:
        return False, "WhatsApp no configurado"
    
    # Asegurar formato de telefono guatemalteco
    tel = telefono.replace("+", "").replace("-", "").replace(" ", "")
    if not tel.startswith("502"):
        tel = "502" + tel
    
    try:
        r = requests.post(
            WA_API_URL,
            headers={
                "Authorization": f"Bearer {WA_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "messaging_product": "whatsapp",
                "to": tel,
                "type": "text",
                "text": {"body": mensaje}
            }
        )
        data = r.json()
        if r.status_code == 200:
            return True, "Mensaje enviado"
        return False, data.get("error", {}).get("message", "Error desconocido")
    except Exception as e:
        return False, str(e)

def enviar_factura_whatsapp(telefono, cliente, items, total, metodo_pago, garantia=None):
    mensaje = f"Hola {cliente}, gracias por su compra en Mi Cocina Electrodomesticos.\n\n"
    mensaje += "Detalle de su compra:\n"
    for item in items:
        mensaje += f"- {item}\n"
    mensaje += f"\nTotal: Q{total}"
    mensaje += f"\nMetodo de pago: {metodo_pago}"
    if garantia:
        mensaje += f"\nGarantia: {garantia['numero']} (valida hasta {garantia['vencimiento_propia']})"
    mensaje += "\n\nGracias por preferirnos. Mi Cocina Electrodomesticos Guatemala."
    return enviar_whatsapp(telefono, mensaje)

def enviar_notificacion_orden(telefono, cliente, numero_orden, equipo, estado, garantia=None):
    mensajes = {
        "LISTO": f"Hola {cliente}, su {equipo} ya esta listo para recoger en Mi Cocina Electrodomesticos. Orden: {numero_orden}. Gracias.",
        "PRESUPUESTO": f"Hola {cliente}, le informamos que ya tenemos el presupuesto de reparacion de su {equipo}. Orden: {numero_orden}. Nos comunicaremos pronto.",
        "ENTREGADO": f"Hola {cliente}, confirmamos la entrega de su {equipo}. Orden: {numero_orden}. Gracias por confiar en Mi Cocina."
    }
    mensaje = mensajes.get(estado, f"Hola {cliente}, actualizacion de su orden {numero_orden}: {estado}")
    if estado == "ENTREGADO" and garantia:
        mensaje += f"\n\nSu reparacion tiene garantia {garantia['numero']} valida hasta {garantia['fecha_vencimiento']}."
    return enviar_whatsapp(telefono, mensaje)


def enviar_asignacion_tecnico_whatsapp(telefono_tecnico, tecnico_nombre, numero_orden, equipo, cliente_nombre, problema):
    """Aviso al tecnico cuando se le asigna una orden nueva (PASO 2 del flujo de
    servicio tecnico) - numero de orden, equipo, cliente y problema descrito."""
    mensaje = (f"Hola {tecnico_nombre}, se te asigno la orden {numero_orden}.\n"
               f"Equipo: {equipo}\nCliente: {cliente_nombre}\nProblema reportado: {problema}\n\n"
               f"Puedes revisar el equipo y registrar tu informe con 'informe {numero_orden}: ...' en Nimbo.")
    return enviar_whatsapp(telefono_tecnico, mensaje)


def enviar_presupuesto_whatsapp(telefono, cliente, numero_orden, equipo, items, mano_obra, total):
    """Presupuesto completo al cliente (PASO 4), con desglose de repuestos + mano de
    obra. items: lista de dicts {nombre, cantidad, costo}."""
    mensaje = f"Hola {cliente}, este es el presupuesto de revision de su {equipo} (orden {numero_orden}):\n\n"
    for item in items:
        subtotal = item["cantidad"] * item["costo"]
        mensaje += f"- {item['nombre']} x{item['cantidad']}: Q{subtotal:.2f}\n"
    mensaje += f"- Mano de obra: Q{mano_obra:.2f}\n\n"
    mensaje += f"Total: Q{total:.2f}\n\n"
    mensaje += "Responda indicando si aprueba o rechaza la reparacion. Gracias por su preferencia."
    return enviar_whatsapp(telefono, mensaje)


def enviar_aprobacion_tecnico_whatsapp(telefono_tecnico, tecnico_nombre, numero_orden, equipo):
    mensaje = (f"Hola {tecnico_nombre}, el cliente APROBO la reparacion de la orden {numero_orden} ({equipo}). "
               f"Puedes proceder con la reparacion.")
    return enviar_whatsapp(telefono_tecnico, mensaje)


def enviar_rechazo_cliente_whatsapp(telefono, cliente, numero_orden, equipo):
    mensaje = (f"Hola {cliente}, entendemos que no desea proceder con la reparacion de su {equipo} "
               f"(orden {numero_orden}). Puede pasar a recoger su equipo sin ningun costo. Gracias por su preferencia.")
    return enviar_whatsapp(telefono, mensaje)
