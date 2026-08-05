import os
import requests

TOKEN = os.getenv("OPENCLAW_TOKEN", "")
URL = "http://127.0.0.1:18789/v1/chat/completions"

SYSTEM_PROMPT = """Eres Nimbo, el asistente inteligente de Mi Cocina Electrodomesticos en Guatemala.

Puedes controlar el inventario usando estos comandos exactos:
- busca [producto]
- agrega [cantidad] [producto]
- quita [cantidad] [producto]
- cambia precio de [producto] a [precio]
- elimina [producto]
- inventario

Cuando el usuario te pida algo relacionado con inventario, responde ejecutando el comando correspondiente.
Responde siempre en español."""

def send_to_openclaw(message: str, contexto: str = "") -> str:
    system_prompt = SYSTEM_PROMPT
    if contexto:
        system_prompt += (
            "\n\nResumen de la conversacion reciente (puede ser de dias anteriores, "
            "usalo para entender referencias como 'eso', 'ese producto' o preguntas de seguimiento):\n"
            f"{contexto}"
        )
    try:
        r = requests.post(URL,
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
            json={
                "model": "openclaw/main",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
            },
            timeout=120)
        if r.status_code != 200:
            return r.text
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {e}"

def check_openclaw_status() -> bool:
    try:
        r = requests.get("http://127.0.0.1:18789/v1/models",
            headers={"Authorization": f"Bearer {TOKEN}"}, timeout=3)
        return r.status_code == 200
    except:
        return False
