"""
Motor determinista de prompts de video para Veo 3.

Reemplaza el uso de Ollama para CONSTRUIR el prompt del flujo de "video de
producto desde una foto" (ver core/nimbo.py, steps videofoto_*) por reglas
fijas basadas en conocimiento experto de videografia publicitaria,
hardcodeado en este archivo: clasificacion del producto por categoria,
biblioteca visual (fondos/props/iluminacion/camara) por categoria,
inferencia de la accion correcta a partir del nombre, reglas de contraste
segun el color real extraido de la foto (ver llava en
tools/contenido_tool.py) y ensamblado de 3 prompts listos para Veo 3
(TikTok/Instagram/Facebook).

Sin llamadas a Ollama en ningun punto de este archivo - dado el mismo
nombre/precio/descripcion visual/oferta/mostrar/texto en pantalla, siempre
produce exactamente el mismo resultado (reproducible, sin variacion entre
corridas). El flujo de ajuste POST-entrega (core/nimbo.py
videofoto_waiting_ajuste, PROMPT_AJUSTAR_VIDEO) sigue usando Ollama a
proposito - no fue parte de este pedido y necesita interpretar texto libre
arbitrario del usuario ("quiero el teflon amarillo dorado"), algo que un
motor de reglas fijas no puede cubrir de forma general.
"""
import unicodedata


def _normalizar(texto: str) -> str:
    return unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode("utf-8").lower()


# ── 1. CLASIFICADOR DE PRODUCTOS ──
# Orden del dict = prioridad si un nombre matchea palabras de mas de una
# categoria (deterministico: siempre gana la primera categoria en este
# orden, nunca al azar).
CATEGORIAS_PALABRAS_CLAVE = {
    "cocina": ["sarten", "olla", "comal", "wok", "cazuela", "cacerola"],
    "electrodomestico_calor": ["plancha", "tostadora", "horno", "microondas", "freidora", "cafetera"],
    "electrodomestico_frio": ["refrigerador", "nevera", "congelador"],
    "electrodomestico_motor": ["licuadora", "batidora", "procesador", "extractor", "juguera"],
    "limpieza": ["aspiradora", "lavadora", "secadora", "trapero"],
    "almacenamiento": ["tupperware", "recipiente", "contenedor"],
}


def clasificar_producto(nombre: str) -> str:
    """Clasifica el producto por palabras clave de su nombre. 'general' si
    no matchea ninguna categoria conocida."""
    nombre_norm = _normalizar(nombre)
    for categoria, palabras in CATEGORIAS_PALABRAS_CLAVE.items():
        if any(palabra in nombre_norm for palabra in palabras):
            return categoria
    return "general"


# ── 2. BIBLIOTECA VISUAL POR CATEGORIA ──
# Cada fondo va etiquetado (texto, tono) - el tono ("claro"/"oscuro"/
# "neutro") es un juicio editorial propio sobre cada fondo especifico dado
# en el pedido (el pedido dio los textos de los fondos, no su clasificacion
# de tono) para poder aplicar las reglas de contraste del punto 4 de forma
# precisa, en vez de adivinar el tono de cada fondo con deteccion de
# palabras clave sobre su propio texto (fragil - ej. "granito gris
# antracita" no contiene la palabra "oscuro" en absoluto).
#
# electrodomestico_frio, limpieza y almacenamiento NO tienen biblioteca
# propia en el pedido original - caen a la de "general" (ver
# _biblioteca_de(categoria) mas abajo). Se documenta como limitacion
# conocida en vez de inventar una biblioteca no pedida.
BIBLIOTECA_VISUAL = {
    "cocina": {
        "fondos": [
            ("encimera de pizarra negra", "oscuro"),
            ("marmol blanco con vetas doradas", "claro"),
            ("madera oscura tipo nogal", "oscuro"),
            ("granito gris antracita", "oscuro"),
        ],
        "props": ["aceite de oliva dorado siendo vertido", "hierbas frescas (romero, tomillo)", "tomates cherry", "ajo fresco", "vapor sutil"],
        "iluminacion": "luz calida dorada desde arriba-izquierda, efecto halo en la superficie",
        "camara": "macro close-up con transicion a toma general, camara lenta",
    },
    "electrodomestico_motor": {
        "fondos": [
            ("encimera blanca minimalista", "claro"),
            ("marmol claro", "claro"),
            ("superficie de madera clara", "claro"),
        ],
        "props": ["frutas frescas cortadas", "ingredientes coloridos alrededor", "vaso transparente mostrando resultado"],
        "iluminacion": "luz de estudio blanca fria desde arriba, sombras suaves",
        "camara": "toma lateral con zoom in al vaso, luego toma frontal del aparato",
    },
    "electrodomestico_calor": {
        "fondos": [
            ("encimera de cocina moderna", "neutro"),
            ("superficie blanca limpia", "claro"),
            ("mesa de desayuno con mantel", "neutro"),
        ],
        "props": ["alimento siendo procesado (pan tostandose, cafe preparandose)", "vapor visible", "plato listo al lado"],
        "iluminacion": "luz calida matutina desde ventana lateral",
        "camara": "toma frontal, zoom in al alimento, toma cenital del resultado",
    },
    "general": {
        "fondos": [
            ("fondo blanco limpio", "claro"),
            ("superficie de madera natural", "neutro"),
            ("fondo degradado gris suave", "neutro"),
        ],
        "props": ["manos elegantes sosteniendo el producto", "contexto de uso natural"],
        "iluminacion": "luz de estudio profesional, sombras suaves",
        "camara": "toma frontal lenta, rotacion 360 grados del producto",
    },
}


def _biblioteca_de(categoria: str) -> dict:
    return BIBLIOTECA_VISUAL.get(categoria, BIBLIOTECA_VISUAL["general"])


# ── 3. INFERENCIA DE ACCION CORRECTA ──
# Lista (no dict) para que el orden decida el desempate cuando el nombre
# matchea mas de una palabra clave - "huevo" va primero a proposito: un
# "sarten para 4 huevos" tiene que mostrar huevos, no un salteado generico
# de verduras solo porque tambien contiene la palabra "sarten" (bug real de
# uso incorrecto que motivo este cambio, ver BUGS_Y_FIXES.md).
ACCION_POR_PALABRA_CLAVE = [
    ("huevo", "huevos estrellados fritos deslizandose sin pegarse, yemas intactas"),
    ("sarten", "salteado de verduras con llama visible"),
    ("comal", "salteado de verduras con llama visible"),
    ("olla", "caldo hirviendo con vapor ascendente"),
    ("cazuela", "caldo hirviendo con vapor ascendente"),
    ("licuadora", "frutas siendo licuadas, liquido colorido girando"),
    ("batidora", "frutas siendo licuadas, liquido colorido girando"),
    ("tostadora", "pan dorandose, saltando al terminar"),
    ("cafetera", "cafe negro siendo vertido en taza blanca con vapor"),
    ("freidora", "papas doradas crujientes saliendo"),
    ("plancha", "ropa quedando perfectamente lisa con vapor"),
]
ACCION_DEFAULT = "producto siendo usado de forma natural y elegante"


def inferir_accion(nombre: str) -> str:
    """Accion logica y correcta a mostrar en el video, inferida por palabra
    clave del NOMBRE del producto (no de la foto). Determinista: mismo
    nombre, siempre la misma accion."""
    nombre_norm = _normalizar(nombre)
    for palabra, accion in ACCION_POR_PALABRA_CLAVE:
        if palabra in nombre_norm:
            return accion
    return ACCION_DEFAULT


# ── 4. REGLAS DE CONTRASTE INTELIGENTE ──
PALABRAS_COLOR_METALICO = ["metalico", "acero inoxidable", "cromado", "brillante", "aluminio"]
PALABRAS_COLOR_OSCURO = ["negro", "gris oscuro", "azul marino", "cafe oscuro", "marron oscuro"]
PALABRAS_COLOR_CLARO = ["blanco", "crema", "plateado", "plata", "beige"]
PALABRAS_COLOR_VIVO = ["rojo", "verde", "amarillo", "azul", "naranja", "rosado", "morado", "dorado"]


def _tono_del_producto(descripcion_visual: str) -> str:
    """'metalico'/'oscuro'/'claro'/'color'/'' segun palabras de color
    encontradas en la descripcion visual real (de llava, ver
    tools/contenido_tool.py). '' si no hay descripcion o no matchea
    ninguna palabra conocida - quien llama cae a un fondo neutro."""
    texto = _normalizar(descripcion_visual)
    if not texto:
        return ""
    if any(p in texto for p in PALABRAS_COLOR_METALICO):
        return "metalico"
    if any(p in texto for p in PALABRAS_COLOR_OSCURO):
        return "oscuro"
    if any(p in texto for p in PALABRAS_COLOR_CLARO):
        return "claro"
    if any(p in texto for p in PALABRAS_COLOR_VIVO):
        return "color"
    return ""


def elegir_fondo_y_iluminacion(categoria: str, descripcion_visual: str, color_corregido: str = ""):
    """(fondo, iluminacion) elegidos de la biblioteca de la categoria segun
    el contraste con el color real del producto: producto oscuro -> fondo
    claro, producto claro -> fondo oscuro, producto de color -> fondo
    neutro, producto metalico/brillante -> iluminacion lateral para
    reflejos (ademas de la regla de fondo que le corresponda por su color
    base). Si la categoria no tiene un fondo del tono buscado (ver huecos
    reales en BIBLIOTECA_VISUAL, ej. electrodomestico_motor no tiene ningun
    fondo oscuro), cae al primer fondo neutro disponible, y si tampoco hay
    ninguno neutro, al primero de la lista - nunca revienta por falta de
    opciones.

    Si el usuario corrigio el color (color_corregido), la deteccion de tono
    se basa SOLO en esa correccion, no en descripcion_visual - que puede
    seguir mencionando el color VIEJO que llava identifico mal (bug real:
    antes se usaba siempre descripcion_visual, y si el color corregido no
    coincidia por casualidad con el orden de busqueda de
    _tono_del_producto(), la eleccion de fondo terminaba basada en el color
    equivocado)."""
    fondos = _biblioteca_de(categoria)["fondos"]
    texto_para_tono = color_corregido if color_corregido else descripcion_visual
    tono_producto = _tono_del_producto(texto_para_tono)

    def _primero(tono_buscado):
        return next((f for f, t in fondos if t == tono_buscado), None)

    if tono_producto == "oscuro":
        fondo = _primero("claro") or _primero("neutro") or fondos[0][0]
    elif tono_producto == "claro":
        fondo = _primero("oscuro") or _primero("neutro") or fondos[0][0]
    elif tono_producto == "color":
        fondo = _primero("neutro") or fondos[0][0]
    else:
        fondo = fondos[0][0]

    iluminacion = _biblioteca_de(categoria)["iluminacion"]
    if tono_producto == "metalico":
        iluminacion = "iluminacion lateral direccional para resaltar reflejos metalicos, " + iluminacion

    return fondo, iluminacion


# ── 6. FRASE DE IMPACTO POR CATEGORIA ──
# electrodomestico_frio, limpieza y almacenamiento tampoco tienen frase
# propia en el pedido - caen a la de "general", mismo criterio que la
# biblioteca visual (ver nota arriba).
FRASE_IMPACTO_POR_CATEGORIA = {
    "cocina": "La cocina que siempre quisiste.",
    "electrodomestico_motor": "Potencia que se nota.",
    "electrodomestico_calor": "El sabor perfecto, cada vez.",
    "general": "Calidad que se ve.",
}


def frase_impacto(categoria: str) -> str:
    return FRASE_IMPACTO_POR_CATEGORIA.get(categoria, FRASE_IMPACTO_POR_CATEGORIA["general"])


# ── 5. ENSAMBLADO DEL PROMPT FINAL ──
# aspect_ratio real que se le pasa a Veo 3 (services/video_gen.py) segun la
# plataforma elegida. Facebook pasa de 1:1 (mapeo anterior, ver entrada de
# BUGS_Y_FIXES.md de la foto/video con Ollama) a 16:9 - este pedido lo
# especifica explicitamente ("Toma amplia 16:9"), asi que se sigue esta
# version mas reciente. No se pudo verificar contra documentacion real de
# Vertex AI que Veo 3 image_to_video acepte 16:9 (mismo tipo de limitacion
# ya documentada para 1:1 antes) - si lo rechaza, operation.error lo
# reporta igual que cualquier otro error, no revienta en silencio.
ASPECT_RATIO_POR_PLATAFORMA = {
    "tiktok": "9:16",
    "instagram": "1:1",
    "facebook": "16:9",
}


def _declaracion_color(descripcion_visual: str, color_corregido: str = "") -> str:
    """Oracion standalone (no un fragmento que dependa de encajar
    gramaticalmente dentro de otra frase) que declara el color/material real
    del producto. color_corregido - la correccion que el usuario escribio en
    core/nimbo.py videofoto_waiting_descripcion_visual (ej. "interior
    amarillo dorado casi color gold", o "es negro mate por dentro") cuando
    el analisis de llava se equivoco - tiene PRIORIDAD ABSOLUTA sobre
    descripcion_visual: se declara primero y explicito, y se le pide al
    lector del prompt que ignore cualquier color que aparezca en
    descripcion_visual si contradice.

    Se devuelve como oracion propia (no insertada a la fuerza dentro de un
    molde tipo "mostrando su interior de X") porque el texto que escribe el
    usuario puede venir en cualquier forma gramatical - "amarillo dorado" es
    un fragmento, pero "es negro mate por dentro" ya es una oracion
    completa; forzarla dentro de otro molde ("mostrando su interior de es
    negro mate por dentro") quedaba gramaticalmente roto.

    Bug real que motivo el diseño de esta funcion: una version anterior
    concatenaba la correccion directo con el texto de llava (que podia
    seguir mencionando el color VIEJO, ej. "Teflon negro mate"), y ese texto
    viejo terminaba compitiendo/ganando tanto en el prompt como en la
    deteccion de contraste (ver elegir_fondo_y_iluminacion) porque seguia
    presente palabra por palabra, sin ninguna indicacion de que estaba
    superado."""
    if color_corregido:
        declaracion = (f"Color/material real del producto, confirmado por el cliente y con "
                        f"prioridad sobre cualquier otro color mencionado a continuacion: {color_corregido}.")
        if descripcion_visual:
            declaracion += f" Otros detalles visuales observados (forma, condicion, fondo original): {descripcion_visual}."
        return declaracion
    if descripcion_visual:
        return f"Color y material reales del producto: {descripcion_visual}."
    return ""


def _apertura(nombre: str) -> str:
    return f"Primer plano macro de {nombre}"


def _clausula_texto_pantalla(texto_pantalla: str) -> str:
    if texto_pantalla:
        return f', excepto este texto pedido por el cliente: "{texto_pantalla}"'
    return ""


def _formatear_precio(precio) -> str:
    """Precio con 2 decimales fijos (Q168.00, no Q168.0 ni Q168) - precio
    puede llegar como float o como string (ver construir_prompts_video,
    core/nimbo.py guarda vf_precio como string en el camino de producto ya
    existente en el inventario, y como float en el camino de producto
    descrito a mano)."""
    try:
        return f"{float(precio):.2f}"
    except (TypeError, ValueError):
        return str(precio)


def _clausula_mostrar(mostrar: str) -> str:
    return f" Enfoque narrativo: {mostrar}." if mostrar else ""


def _construir_prompt_tiktok(datos: dict) -> str:
    props_texto = ", ".join(datos["props"])
    partes = [f"{datos['apertura']}."]
    if datos["declaracion_color"]:
        partes.append(datos["declaracion_color"])
    partes += [
        f"{datos['accion']}.{datos['clausula_mostrar']}",
        f"Elementos visuales: {props_texto}.",
        f"Ambiente: {datos['fondo']}.",
        f"Iluminacion: {datos['iluminacion']}.",
        f"Camara: {datos['camara']}.",
        f"Vertical 9:16. Energetico y dinamico. Camara lenta en momentos clave. 4K. "
        f"Sin personas visibles. Sin texto en pantalla{datos['clausula_texto_pantalla']}.",
        f"Audio: sonido del producto en uso, musica urbana de fondo. Voz en off: '{datos['frase']}'.",
    ]
    return " ".join(partes)


def _construir_prompt_instagram(datos: dict) -> str:
    # "Misma base pero..." (pedido original) - mismo contenido central
    # (apertura/accion/props/ambiente/iluminacion/camara) que TikTok, con un
    # bloque de cierre distinto (cuadrado 1:1, estilo editorial de revista,
    # musica mas suave en vez de "urbana") en vez del bloque vertical
    # energetico de TikTok.
    props_texto = ", ".join(datos["props"])
    partes = [f"{datos['apertura']}."]
    if datos["declaracion_color"]:
        partes.append(datos["declaracion_color"])
    partes += [
        f"{datos['accion']}.{datos['clausula_mostrar']}",
        f"Elementos visuales: {props_texto}.",
        f"Ambiente: {datos['fondo']}.",
        f"Iluminacion: {datos['iluminacion']}.",
        f"Camara: {datos['camara']}.",
        f"Composicion cuadrada 1:1. Estilo aspiracional y limpio. Paleta de colores cohesiva. "
        f"Lighting de editorial de revista. 4K. Sin personas visibles. Sin texto en pantalla"
        f"{datos['clausula_texto_pantalla']}.",
        f"Audio: sonido del producto en uso, musica suave de fondo. Voz en off: '{datos['frase']}'.",
    ]
    return " ".join(partes)


def _construir_prompt_facebook(datos: dict) -> str:
    # Facebook cambia mas que solo el cierre: toma amplia (no macro) desde
    # el arranque, y SI lleva texto en pantalla (el precio) - al reves de
    # TikTok/Instagram, que lo evitan por defecto.
    props_texto = ", ".join(datos["props"])
    clausula_oferta = f" - {datos['oferta']}" if datos["oferta"] else ""
    partes = [f"Toma amplia 16:9 mostrando {datos['nombre']} en contexto completo de cocina/hogar."]
    if datos["declaracion_color"]:
        partes.append(datos["declaracion_color"])
    partes += [
        f"{datos['accion']}.{datos['clausula_mostrar']}",
        f"Elementos visuales: {props_texto}.",
        f"Ambiente: {datos['fondo']}.",
        f"Iluminacion: {datos['iluminacion']}.",
        f"Camara: {datos['camara']}, informativo y claro.",
        f"Texto grande visible en pantalla: 'Q{_formatear_precio(datos['precio'])}'{clausula_oferta}.",
        "Estilo: publicidad familiar y calida. 4K.",
        f"Audio: musica calida de fondo. Voz en off: '{datos['frase']}'.",
    ]
    return " ".join(partes)


def construir_prompts_video(nombre: str, precio, descripcion_visual: str = "", oferta: str = "", mostrar: str = "", texto_pantalla: str = "", color_corregido: str = "") -> dict:
    """Punto de entrada del motor: arma los 3 prompts (TikTok/Instagram/
    Facebook) listos para Veo 3, deterministas (sin Ollama en ningun punto
    de esta funcion ni de las que llama). precio puede venir como str o
    numero (ver core/nimbo.py, vf_precio se guarda como string en algunos
    caminos del flujo) - se formatea siempre a 2 decimales fijos donde se
    muestra (ver _formatear_precio()). color_corregido es la correccion de
    color que el usuario escribio en core/nimbo.py cuando el analisis de
    llava se equivoco - tiene prioridad absoluta sobre descripcion_visual
    tanto en el texto del prompt (como oracion propia, ver
    _declaracion_color()) como en la eleccion de fondo por contraste (ver
    elegir_fondo_y_iluminacion()).

    Retorna {"tiktok": texto, "instagram": texto, "facebook": texto}."""
    categoria = clasificar_producto(nombre)
    lib = _biblioteca_de(categoria)
    fondo, iluminacion = elegir_fondo_y_iluminacion(categoria, descripcion_visual, color_corregido)

    datos = {
        "nombre": nombre,
        "precio": precio,
        "oferta": oferta,
        "descripcion_visual": descripcion_visual,
        "color_corregido": color_corregido,
        "apertura": _apertura(nombre),
        "declaracion_color": _declaracion_color(descripcion_visual, color_corregido),
        "accion": inferir_accion(nombre),
        "clausula_mostrar": _clausula_mostrar(mostrar),
        "clausula_texto_pantalla": _clausula_texto_pantalla(texto_pantalla),
        "props": lib["props"][:2],
        "fondo": fondo,
        "iluminacion": iluminacion,
        "camara": lib["camara"],
        "frase": frase_impacto(categoria),
    }

    return {
        "tiktok": _construir_prompt_tiktok(datos),
        "instagram": _construir_prompt_instagram(datos),
        "facebook": _construir_prompt_facebook(datos),
    }
