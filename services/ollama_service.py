"""
Servicio de IA local via Ollama - Nimbo ya no depende de Gemini API ni de
OpenClaw para generar texto o analizar datos, todo pasa por el servidor local
de Ollama (http://localhost:11434). OpenClaw sigue disponible como opcion
manual desde el dashboard (ver app.py /api/openclaw/chat), solo se le quito
como fallback automatico del chat.
"""
import requests

OLLAMA_URL = "http://localhost:11434"
OLLAMA_CHAT_URL = f"{OLLAMA_URL}/api/chat"
# Un solo modelo para todo (chat, traduccion, contenido y analisis) - antes
# gemma2:9b se usaba solo para analizar_ollama(), pero tener 2 modelos
# distintos hacia que Ollama descargara uno para cargar el otro cada vez que
# se alternaba entre chat y analisis, y esa recarga por si sola podia consumir
# el timeout completo (ademas del riesgo de quedarse sin RAM con los dos
# modelos cargados a la vez, ~11GB combinados). Con un solo modelo siempre
# cargado no hay ese intercambio.
MODELO_CHAT = "qwen2.5:7b"
TIMEOUT_SEGUNDOS = 180
TIMEOUT_ANALISIS_SEGUNDOS = 300  # analizar_ollama() - analisis largos (5 min)

# Se devuelve (en vez de None) cuando la llamada se corto especificamente por
# timeout - Ollama esta corriendo, solo tardo mas de la cuenta (CPU sin GPU en
# este hardware). Distinto de None (Ollama no esta corriendo / error de
# conexion), para que el usuario no piense que Ollama esta caido cuando en
# realidad solo esta tardado. Se devuelve tal cual como el texto de respuesta
# porque todos los callers ya hacen `texto if texto else "<mensaje fijo>"` -
# al ser un string no vacio, este mensaje pasa directo sin que haya que tocar
# ningun caller.
MENSAJE_TIMEOUT = "Ollama esta procesando, esto puede tardar un momento..."


def ollama_disponible():
    """Chequeo rapido de si el servidor de Ollama esta corriendo (GET
    /api/tags, igual que 'curl http://localhost:11434/api/tags'). No es
    obligatorio llamarlo antes de llamar_ollama()/analizar_ollama() - esas ya
    devuelven None solas si Ollama no responde - pero queda disponible para
    quien quiera chequear disponibilidad sin hacer una llamada de chat completa
    (ej. para mostrar un aviso en el dashboard)."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False


def llamar_ollama(prompt, modelo=MODELO_CHAT, sistema=None, timeout=TIMEOUT_SEGUNDOS):
    """Llama al servidor local de Ollama (/api/chat) y devuelve el texto de la
    respuesta (string). sistema, si se da, se manda como mensaje role=system
    (instrucciones de comportamiento separadas del prompt del usuario). Si la
    llamada se corta por timeout devuelve MENSAJE_TIMEOUT (Ollama si esta
    corriendo, solo tardo mas de la cuenta); si Ollama no esta corriendo o
    responde algo invalido devuelve None. Nunca lanza excepcion - quien llama
    decide que hacer con cada caso (los dos son "truthy" salvo None, asi que
    el patron `texto if texto else "<mensaje fijo>"` que ya usan todos los
    callers no necesita cambios)."""
    mensajes = []
    if sistema:
        mensajes.append({"role": "system", "content": sistema})
    mensajes.append({"role": "user", "content": prompt})

    try:
        r = requests.post(
            OLLAMA_CHAT_URL,
            json={
                "model": modelo,
                "messages": mensajes,
                "stream": False,
            },
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
        return data["message"]["content"]
    except requests.exceptions.Timeout:
        return MENSAJE_TIMEOUT
    except (requests.exceptions.RequestException, KeyError, ValueError):
        return None


def analizar_ollama(prompt):
    """Analisis financieros/estrategicos. Usa el mismo (y unico) modelo que
    llamar_ollama() (ver nota en MODELO_CHAT sobre por que ya no hay un
    modelo separado para esto), pero con un timeout mas largo
    (TIMEOUT_ANALISIS_SEGUNDOS) porque estos prompts son mas largos/complejos
    que un mensaje de chat normal."""
    return llamar_ollama(prompt, timeout=TIMEOUT_ANALISIS_SEGUNDOS)
