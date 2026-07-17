from google import genai
from google.genai import types
import time
import os
import base64

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def generar_video_producto(producto_nombre, descripcion="", ruta_foto=None, duracion=8):
    client = genai.Client(vertexai=True, project='pivotal-mode-499817-t7', location='us-central1')
    
    prompt = f"Video publicitario profesional de {producto_nombre} para tienda de electrodomesticos en Guatemala."
    if descripcion:
        prompt += f" {descripcion}"
    prompt += " Fondo limpio, iluminacion profesional, estilo comercial moderno."

    config = types.GenerateVideosConfig(
        aspect_ratio='9:16',
        duration_seconds=duracion,
        number_of_videos=1,
    )

    # Si hay foto de referencia usarla
    static_prefix = os.path.join(BASE_DIR, 'static') + '/'
    if ruta_foto and os.path.exists(ruta_foto.replace('/static/', static_prefix)):
        ruta_real = ruta_foto.replace('/static/', static_prefix)
        with open(ruta_real, 'rb') as f:
            foto_bytes = f.read()
        imagen = types.Image(image_bytes=foto_bytes, mime_type='image/jpeg')
        operation = client.models.generate_videos(
            model='veo-3.0-fast-generate-001',
            prompt=prompt,
            image=imagen,
            config=config
        )
    else:
        operation = client.models.generate_videos(
            model='veo-3.0-fast-generate-001',
            prompt=prompt,
            config=config
        )

    while not operation.done:
        time.sleep(10)
        operation = client.operations.get(operation)

    if operation.error:
        return None, str(operation.error)

    video = operation.result.generated_videos[0]
    if video.video.video_bytes:
        import uuid
        filename = f"video_{uuid.uuid4()}.mp4"
        filepath = os.path.join(BASE_DIR, 'static', 'videos', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(video.video.video_bytes)
        return f"/static/videos/{filename}", None
    
    return None, "Video generado pero sin bytes disponibles"
