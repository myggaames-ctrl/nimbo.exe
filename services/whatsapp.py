import os
import requests
from dotenv import load_dotenv

load_dotenv('/home/ictor_axtor/micocina-dashboard/.env')

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

def enviar_notificacion_orden(telefono, cliente, numero_orden, equipo, estado):
    mensajes = {
        "LISTO": f"Hola {cliente}, su {equipo} ya esta listo para recoger en Mi Cocina Electrodomesticos. Orden: {numero_orden}. Gracias.",
        "PRESUPUESTO": f"Hola {cliente}, le informamos que ya tenemos el presupuesto de reparacion de su {equipo}. Orden: {numero_orden}. Nos comunicaremos pronto.",
        "ENTREGADO": f"Hola {cliente}, confirmamos la entrega de su {equipo}. Orden: {numero_orden}. Gracias por confiar en Mi Cocina."
    }
    mensaje = mensajes.get(estado, f"Hola {cliente}, actualizacion de su orden {numero_orden}: {estado}")
    return enviar_whatsapp(telefono, mensaje)
