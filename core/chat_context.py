"""
Contexto de conversaciones anteriores (entre sesiones/dias)
Nimbo AI
"""
from database.aronium import get_historial_chat

MAX_MENSAJES = 10
MAX_CHARS = 2000          # ~500 tokens (aprox. 4 caracteres por token)
MAX_CHARS_POR_MENSAJE = 300


def obtener_historial_reciente(limit=MAX_MENSAJES):
    """Ultimos N mensajes guardados en ChatHistorial, en orden cronologico (mas viejo primero)."""
    try:
        return get_historial_chat(limit=limit)
    except Exception:
        return []


def _recortar(texto, max_len=MAX_CHARS_POR_MENSAJE):
    texto = (texto or "").strip()
    if len(texto) > max_len:
        return texto[:max_len].rstrip() + "…"
    return texto


def resumen_texto(mensajes=None, max_chars=MAX_CHARS):
    """Historial reciente como texto plano compacto, listo para insertar en un prompt
    de un solo turno (traduccion, clarificacion, OpenClaw). Vacio si no hay historial."""
    if mensajes is None:
        mensajes = obtener_historial_reciente()
    lineas = []
    total = 0
    for m in mensajes:
        etiqueta = "Usuario" if m.get("Role") == "user" else "Nimbo"
        texto = _recortar(m.get("Content", ""))
        if not texto:
            continue
        linea = f"{etiqueta}: {texto}"
        if total + len(linea) > max_chars:
            break
        lineas.append(linea)
        total += len(linea)
    return "\n".join(lineas)


def resumen_para_gemini(mensajes=None, max_chars=MAX_CHARS):
    """Historial reciente en formato multi-turno para la API de Gemini
    (role 'user'/'model'), respetando el mismo presupuesto de caracteres."""
    if mensajes is None:
        mensajes = obtener_historial_reciente()
    contents = []
    total = 0
    for m in mensajes:
        texto = _recortar(m.get("Content", ""))
        if not texto:
            continue
        if total + len(texto) > max_chars:
            break
        role = "model" if m.get("Role") == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": texto}]})
        total += len(texto)
    return contents
