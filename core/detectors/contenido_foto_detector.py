import re

# El marcador lo arma app.py en /api/chat/foto (ver ese endpoint): guarda la
# foto subida en static/fotos/chat_temp/ y antepone "[FOTO:ruta]" al mensaje
# de texto que haya escrito el usuario junto con la foto, antes de mandarlo al
# mismo pipeline de core.nimbo.send() que usa el chat normal. Para cuando este
# texto llega aca ya paso por CommandNormalizer.normalize() (lowercase, sin
# acentos, correccion de typos - ver core/intent_detector.py), por eso el
# marcador se busca en minuscula ("[foto:", no "[FOTO:").
PATRON_FOTO = re.compile(r"^\[foto:(.+?)\]\s*(.*)$")

# El "foto" dentro del marcador es texto de chat, NO confiable - aunque en el
# camino normal lo arma app.py con un uuid4 propio (ver /api/chat/foto), nada
# impide que un usuario le escriba a /api/chat directo
# "[foto:../../../etc/passwd] video de esto" sin pasar por el upload real. Se
# exige que matchee EXACTAMENTE el formato que /api/chat/foto genera (mismo
# UPLOAD_FOLDER_CHAT_FOTOS y mismas extensiones permitidas que ese endpoint)
# antes de aceptarlo - cualquier otra cosa (".." incluido) no hace match y el
# detector no dispara, en vez de dejar pasar una ruta arbitraria que
# tools/contenido_tool.py.video_desde_foto_tool despues intentaria abrir
# (Ollama vision) o que services/video_gen.py leeria como bytes para
# mandarselos a Veo 3.
PATRON_RUTA_FOTO_VALIDA = re.compile(r"^/static/fotos/chat_temp/[0-9a-f-]+\.(?:jpg|jpeg|png|webp)$")

# Palabras clave que, junto con una foto adjunta, disparan el flujo de video
# de producto (ver CLAUDE.md, "DETECTOR" del pedido original). Sin acentos
# porque el texto ya paso por el normalizer.
PALABRAS_CLAVE = ("video", "promocion", "promociones", "contenido", "publica", "publicar", "publicalo")


class ContenidoFotoDetector:
    """Detecta una foto subida al chat (marcador [foto:ruta]) acompanada de
    alguna palabra clave de contenido/video. Si la foto viene sin ninguna de
    esas palabras (ej. una foto subida para algo que no sea este flujo), no
    hace match a proposito - el mensaje sigue de largo por el resto del
    pipeline de core.nimbo.send() (traduccion/clarificacion/fallback Ollama),
    igual que cualquier mensaje que ningun detector reconoce. Tampoco hace
    match si la ruta no tiene exactamente la forma que /api/chat/foto genera
    (ver PATRON_RUTA_FOTO_VALIDA) - previene path traversal via el campo
    "foto" del marcador, que es texto de chat no confiable."""

    def detect(self, text: str):
        match = PATRON_FOTO.match(text)
        if not match:
            return None
        foto = match.group(1).strip()
        resto = match.group(2).strip()
        if not PATRON_RUTA_FOTO_VALIDA.match(foto):
            return None
        if not any(palabra in resto for palabra in PALABRAS_CLAVE):
            return None
        return {"intent": "contenido.video_desde_foto", "foto": foto, "texto": resto}
