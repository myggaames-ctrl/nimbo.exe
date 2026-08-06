"""
Herramienta de Generacion de Contenido
"""
from core.tool_registry import register
from services.ollama_service import llamar_ollama
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NEGOCIO = "Mi Cocina Electrodomesticos Guatemala - tienda de electrodomesticos y repuestos"

def post_tool(data):
    if isinstance(data, str): return "Error: datos invalidos"
    red = data.get("red", "general")
    producto = data.get("query", "")

    estilos = {
        "instagram": "Instagram: usa emojis, maximo 2200 caracteres, 5-10 hashtags relevantes, llamada a la accion",
        "tiktok": "TikTok: muy corto, energico, trending, 3-5 hashtags virales, gancho en primeras palabras",
        "facebook": "Facebook: mas informativo, puede ser mas largo, link amigable, pregunta para engagement",
        "whatsapp": "WhatsApp: mensaje directo, personal, sin hashtags, con precio si aplica",
        "general": "redes sociales en general: profesional y atractivo"
    }

    estilo = estilos.get(red.lower(), estilos["general"])
    for key in estilos:
        if key in red.lower():
            estilo = estilos[key]
            break

    prompt = f"""Eres experto en marketing digital para {NEGOCIO}.
Crea un post para {estilo}.
Producto/tema: {producto}
Tono: profesional pero cercano, en español guatemalteco
Incluye precio si es relevante con Q (quetzales)
No inventes precios especificos si no los sabes."""

    texto = llamar_ollama(prompt)
    return texto if texto else "Ollama no esta disponible ahora mismo."

register("contenido.post", post_tool)

def script_tool(data):
    return "SCRIPT_INICIO:" + (data.get("query", "") if isinstance(data, dict) else str(data))

register("contenido.script", script_tool)

def catalogo_tool(data):
    if isinstance(data, str): producto = data
    else: producto = data.get("query", "")

    prompt = f"""Eres experto en catalogo de productos para {NEGOCIO}.
Crea una descripcion de catalogo para: {producto}
Incluye:
- Nombre del producto
- Descripcion atractiva (2-3 oraciones)
- Caracteristicas principales (3-5 puntos)
- Para que sirve / beneficios
- Nota sobre garantia y servicio
Formato limpio y profesional en espanol."""

    texto = llamar_ollama(prompt)
    return texto if texto else "Ollama no esta disponible ahora mismo."

register("contenido.catalogo", catalogo_tool)

def ideas_tool(data):
    from database.nimbo_db import get_products
    productos = get_products()
    lista_productos = ", ".join([p["Name"].strip() for p in productos[:10]]) if productos else "electrodomesticos en general"
    
    prompt = f"""Eres experto en marketing digital para {NEGOCIO}.
Productos disponibles en inventario: {lista_productos}

Genera 7 ideas de contenido para esta semana para redes sociales.
Basa las ideas en los productos reales del inventario.
Mezcla: productos especificos, tips de uso, promociones, contenido educativo, testimonios, detras de escena.
Para cada idea indica: tipo de red, formato (foto/video/carrusel), tema, objetivo.
En espanol, enfocado en Guatemala."""

    texto = llamar_ollama(prompt)
    return texto if texto else "Ollama no esta disponible ahora mismo."

register("contenido.ideas", ideas_tool)

def programacion_tool(data):
    return "PROGRAMACION_INICIO"

register("contenido.programacion", programacion_tool)


def foto_producto_tool(data):
    from database.nimbo_db import get_products, get_foto_producto, get_descripcion_producto
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    modo = data.get("modo", "tienda") if isinstance(data, dict) else "tienda"
    productos = get_products(search=query)
    if not productos:
        return f"No encontre producto '{query}'."
    p = productos[0]
    foto = get_foto_producto(p["Id"])
    info = get_descripcion_producto(p["Id"])
    
    descripcion = info["Descripcion"] if info and info["Descripcion"] else ""
    descripcion_corta = info["DescripcionCorta"] if info and info["DescripcionCorta"] else descripcion
    
    if not foto:
        if modo == "cliente":
            resp = f"<b>{p['Name'].strip()}</b> - Q{p['Price']}"
            if descripcion_corta:
                resp += f"<br>{descripcion_corta}"
            return resp
        return f"No hay foto para {p['Name']}. Sube una con el boton 📷 en inventario."
    
    if modo == "cliente":
        resp = f'<img src="{foto}" style="max-width:300px;border-radius:8px;margin:8px 0"><br>'
        resp += f"<b>{p['Name'].strip()}</b><br>"
        resp += f"Precio: Q{p['Price']}<br>"
        if descripcion_corta:
            resp += f"{descripcion_corta}<br>"
        resp += "¿Te interesa? Escribenos para apartar uno."
        return resp
    else:
        disponible = int(p["Stock"]) > 0
        resp = f'<img src="{foto}" style="max-width:300px;border-radius:8px;margin:8px 0"><br>'
        resp += f"<b>{p['Name'].strip()}</b><br>"
        resp += f"Precio: Q{p['Price']} | Costo: Q{p['Cost']}<br>"
        if disponible:
            resp += f'<span style="color:var(--green)">✓ Disponible - {int(p["Stock"])} en stock</span><br>'
        else:
            resp += '<span style="color:var(--red)">✗ Sin stock</span><br>'
        if descripcion:
            resp += f"{descripcion}<br>"
        if disponible:
            resp += '<br>¿Registrar venta? Escribe "vendi 1 ' + p['Name'].strip() + '"'
        return resp

register("contenido.foto", foto_producto_tool)


def set_descripcion_tool(data):
    if isinstance(data, str): return "Error: datos invalidos"
    from database.nimbo_db import get_products, set_descripcion_producto
    query = data.get("query", "")
    descripcion = data.get("descripcion", "")
    productos = get_products(search=query)
    if not productos:
        return f"No encontre producto '{query}'."
    p = productos[0]
    if not descripcion:
        return f"SET_DESC_INICIO:{p['Id']}|{p['Name'].strip()}"
    set_descripcion_producto(p["Id"], p["Name"].strip(), descripcion, descripcion[:100])
    return f"Descripcion de {p['Name'].strip()} actualizada."

register("contenido.set_descripcion", set_descripcion_tool)


def video_producto_tool(data):
    from database.nimbo_db import get_products, get_foto_producto, get_descripcion_producto
    query = data.get("query", "") if isinstance(data, dict) else str(data)
    productos = get_products(search=query)
    if not productos:
        return f"No encontre producto '{query}'."
    p = productos[0]
    foto = get_foto_producto(p["Id"])
    info = get_descripcion_producto(p["Id"])
    descripcion = info["DescripcionCorta"] if info and info["DescripcionCorta"] else ""
    return f"VIDEO_INICIO:{p['Id']}|{p['Name'].strip()}|{foto or ''}|{descripcion}"

register("contenido.video", video_producto_tool)


def video_desde_foto_tool(data):
    """Punto de entrada del flujo de "video de producto desde una foto subida
    al chat" (ver core/detectors/contenido_foto_detector.py, app.py
    /api/chat/foto, core/nimbo.py steps videofoto_*). Intenta identificar el
    producto en la foto con Ollama vision si el modelo pulled lo soporta (ver
    services/ollama_service.modelo_soporta_vision) - si no lo soporta, o si no
    logra identificar nada util, cae al texto que el usuario escribio junto a
    la foto (data['texto']) como busqueda; si esa busqueda tampoco encuentra
    nada (o no hay texto), arranca el flujo de "no reconoci el producto" para
    pedirlo a mano en vez de fallar. La busqueda en si (con vision o con
    texto) usa get_products(), el mismo fuzzy match que el resto del
    inventario - no es una busqueda nueva ni distinta."""
    from database.nimbo_db import get_products
    from services.ollama_service import modelo_soporta_vision, analizar_imagen_ollama, MENSAJE_TIMEOUT

    foto = data.get("foto", "") if isinstance(data, dict) else ""
    texto = data.get("texto", "") if isinstance(data, dict) else ""
    if not foto:
        return "No recibí ninguna foto."

    # "foto" ya paso el patron estricto de core/detectors/contenido_foto_detector.py
    # (solo rutas con la forma exacta que /api/chat/foto genera), pero se
    # revalida aca tambien (defensa en profundidad - "foto" sigue siendo texto
    # de chat, no un valor interno) antes de tocar el disco: se resuelve la
    # ruta real (os.path.realpath, sigue symlinks y colapsa "..") y se exige
    # que quede DENTRO de la carpeta de fotos temporales del chat. Sin esto,
    # un "foto" con path traversal (ej. "../../../etc/passwd") terminaria
    # leyendose como bytes de imagen mas abajo (via Ollama vision o, si el
    # marcador llega a services/video_gen.py, mandado como referencia a Veo 3).
    carpeta_fotos_chat = os.path.realpath(os.path.join(BASE_DIR, "static", "fotos", "chat_temp"))
    ruta_disco = os.path.realpath(os.path.join(BASE_DIR, foto.lstrip("/")))
    if not ruta_disco.startswith(carpeta_fotos_chat + os.sep):
        return "Foto inválida."

    query_busqueda = ""
    if modelo_soporta_vision():
        prompt_vision = (
            "Identifica en pocas palabras que producto de una tienda de "
            "electrodomesticos y repuestos aparece en esta foto (ej: "
            "'licuadora', 'plancha', 'cuchilla de licuadora'). Responde "
            "SOLO el nombre del producto, sin explicaciones ni puntuacion."
        )
        descripcion_ia = analizar_imagen_ollama(ruta_disco, prompt_vision)
        if descripcion_ia and descripcion_ia != MENSAJE_TIMEOUT:
            query_busqueda = descripcion_ia.strip()

    if not query_busqueda:
        query_busqueda = texto

    productos = get_products(search=query_busqueda) if query_busqueda else []
    if productos:
        p = productos[0]
        return f"VIDEOFOTO_ENCONTRADO_INICIO:{p['Id']}|{p['Name'].strip()}|{p['Price']}|{foto}"

    return f"VIDEOFOTO_NUEVO_INICIO:{foto}"

register("contenido.video_desde_foto", video_desde_foto_tool)


def publicar_tool(data):
    if isinstance(data, str): return "Error: datos invalidos"
    from database.nimbo_db import get_products, get_foto_producto, nimbo_connect
    from services.social_media import publicar_facebook
    
    query = data.get("query", "")
    red = data.get("red", "facebook")
    
    # Quitar articulos del query
    for art in ["el ", "la ", "los ", "las ", "un ", "una "]:
        if query.startswith(art):
            query = query[len(art):]
            break
    
    # Buscar el video mas reciente del producto
    productos = get_products(search=query)
    if not productos:
        return f"No encontre producto '{query}'."
    
    p = productos[0]
    
    # Buscar video generado
    import os
    video_dir = os.path.join(BASE_DIR, "static", "videos")
    video_path = None
    if os.path.exists(video_dir):
        videos = sorted([f for f in os.listdir(video_dir) if f.endswith('.mp4')], reverse=True)
        if videos:
            video_path = f"/static/videos/{videos[0]}"
    
    # Buscar foto si no hay video
    foto_path = get_foto_producto(p["Id"])
    
    # Obtener descripcion
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT DescripcionCorta FROM ProductoInfo WHERE ProductoId=?", (p["Id"],))
    row = cur.fetchone()
    conn.close()
    descripcion = row["DescripcionCorta"] if row else p["Name"].strip()
    
    caption = f"{p['Name'].strip()} - Q{p['Price']}\n{descripcion}\n\n#MiCocina #Electrodomesticos #Guatemala #Oster"
    
    if video_path and red == "facebook":
        ok, result = publicar_facebook(caption, ruta_video=video_path)
    elif foto_path and red == "facebook":
        ok, result = publicar_facebook(caption, ruta_foto=foto_path)
    else:
        ok, result = publicar_facebook(caption)
    
    if ok:
        return f"Publicado en {red.title()} exitosamente. ID: {result}"
    return f"Error publicando en {red.title()}: {result}"

register("contenido.publicar", publicar_tool)
