import re

# El marcador lo arma app.py en /api/chat/foto (ver ese endpoint): guarda la
# foto subida en static/fotos/chat_temp/ y antepone "[FOTO:ruta]" al mensaje
# de texto que haya escrito el usuario junto con la foto, antes de mandarlo al
# mismo pipeline de core.nimbo.send() que usa el chat normal. Para cuando este
# texto llega aca ya paso por CommandNormalizer.normalize() (lowercase, sin
# acentos, correccion de typos - ver core/intent_detector.py), por eso el
# marcador se busca en minuscula ("[foto:", no "[FOTO:").
PATRON_FOTO = re.compile(r"^\[foto:(.+?)\]\s*(.*)$")

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
    igual que cualquier mensaje que ningun detector reconoce."""

    def detect(self, text: str):
        match = PATRON_FOTO.match(text)
        if not match:
            return None
        foto = match.group(1).strip()
        resto = match.group(2).strip()
        if not any(palabra in resto for palabra in PALABRAS_CLAVE):
            return None
        return {"intent": "contenido.video_desde_foto", "foto": foto, "texto": resto}
