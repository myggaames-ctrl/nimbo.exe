"""
Servicio de IA local via Ollama - reemplaza las llamadas directas a Gemini API
para no depender de la nube ni de cuota/costo en cada analisis.
Expone el mismo formato de respuesta que google.genai (objeto con atributo .text)
para que el codigo que ya llamaba a Gemini solo tenga que cambiar de donde
saca el cliente, no como lee la respuesta.
"""
import requests

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
MODELO_CHAT = "qwen2.5:7b"
MODELO_ANALISIS = "gemma2:9b"
TIMEOUT_SEGUNDOS = 120


class OllamaResponse:
    def __init__(self, text):
        self.text = text


def llamar_ollama(prompt, modelo=MODELO_CHAT):
    """Llama al servidor local de Ollama (http://localhost:11434/api/chat).
    Deja que cualquier error (conexion, timeout, HTTP) se propague como excepcion
    para que el caller decida caer a Gemini si Ollama no esta corriendo."""
    r = requests.post(
        OLLAMA_CHAT_URL,
        json={
            "model": modelo,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=TIMEOUT_SEGUNDOS,
    )
    r.raise_for_status()
    data = r.json()
    texto = data["message"]["content"]
    return OllamaResponse(texto)


def analizar_con_ollama(prompt):
    """Igual que llamar_ollama pero con gemma2:9b, el modelo que se usa para
    los analisis financieros/de negocio (mas capaz, se prioriza razonamiento
    sobre velocidad de respuesta)."""
    return llamar_ollama(prompt, modelo=MODELO_ANALISIS)
