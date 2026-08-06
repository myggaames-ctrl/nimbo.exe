import tools
from core.action_engine import ActionEngine
from core.chat_context import obtener_historial_reciente, resumen_texto
from services.ollama_service import llamar_ollama, MENSAJE_TIMEOUT
import re
import unicodedata

_engine = ActionEngine()


SISTEMA_FALLBACK = """Eres Nimbo, el asistente de gestion de "Mi Cocina Electrodomesticos",
una tienda de electrodomesticos y repuestos en Guatemala. Respondes en espanol guatemalteco,
de forma breve y directa. El sistema puede: buscar y gestionar inventario/productos, registrar
ventas, buscar y gestionar clientes, crear y dar seguimiento a ordenes de servicio tecnico
(reparaciones), gestionar proveedores, ver contabilidad/gastos/balance, y generar contenido
para redes sociales - si el usuario pregunta algo del negocio que no reconociste como comando,
ayudalo sugiriendo como pedirlo. Si pregunta algo sin relacion con el negocio (cultura general,
charla casual), respondes normalmente como un asistente util, sin forzar el tema del negocio."""


def _fallback_ollama(message: str, contexto: str = "") -> str:
    """Ultimo recurso del chat: cuando ningun detector matcheo y la aclaracion
    de intencion vaga tampoco aplico (ver _analizar_intencion_vaga), en vez de
    mandar el mensaje a OpenClaw (que ahora solo queda como opcion manual, ver
    boton en el dashboard / app.py /api/openclaw/chat) se le pasa directo a
    Ollama con un system prompt que lo situa como Nimbo."""
    prompt = message
    if contexto:
        prompt = (
            "Contexto de conversacion reciente (puede ser de dias anteriores):\n"
            f"{contexto}\n\nMensaje del usuario: {message}"
        )
    texto = llamar_ollama(prompt, sistema=SISTEMA_FALLBACK)
    if texto:
        return texto
    return "No pude conectarme con el modelo de IA local (Ollama). Verifica que este corriendo (ollama serve)."


TRANSLATE_PROMPT = """Eres un traductor de comandos para un sistema de inventario.
Convierte el mensaje del usuario a uno de estos comandos exactos:
- busca [producto]
- agrega [cantidad] [producto]
- quita [cantidad] [producto]
- cambia precio de [producto] a [precio]
- elimina [producto]
- inventario

Si el mensaje usa una referencia ambigua (ej: "eso", "ese producto", "cuantos quedan?", "y ese otro")
y hay contexto de conversacion reciente disponible, usalo para identificar a que producto se
refiere y arma el comando con el nombre de producto correcto.

Si el mensaje no es sobre inventario, responde: NINGUNO

Mensaje: {message}
Comando:"""

def _translate(message: str, contexto: str = "") -> str:
    prompt = TRANSLATE_PROMPT.format(message=message)
    if contexto:
        prompt = (
            "Contexto de conversacion reciente (puede ser de dias anteriores):\n"
            f"{contexto}\n\n{prompt}"
        )
    texto = llamar_ollama(prompt)
    # MENSAJE_TIMEOUT no es un comando traducido valido - se trata igual que
    # None (cae al siguiente paso del pipeline) en vez de intentar ejecutarlo
    # como si fuera un comando real. A diferencia de _fallback_ollama() o las
    # tools de contabilidad/evento/contenido, aqui "texto" es un valor
    # intermedio, no la respuesta final que ve el usuario.
    if not texto or texto == MENSAJE_TIMEOUT:
        return None
    cmd = texto.strip().lower()
    if cmd == "ninguno" or not cmd:
        return None
    return cmd


CLARIFICACION_PROMPT = """Eres Nimbo, el asistente de un sistema de gestion para "Mi Cocina Electrodomesticos", una tienda de electrodomesticos y repuestos en Guatemala.

El sistema puede: buscar y gestionar inventario/productos, registrar ventas, buscar y gestionar clientes, crear y dar seguimiento a ordenes de servicio tecnico (reparaciones), gestionar proveedores, ver contabilidad/gastos/balance, y generar contenido para redes sociales.

El usuario escribio un mensaje que el sistema NO logro entender como una accion concreta. Tu trabajo es decidir si el usuario esta tratando de pedir algo relacionado al negocio pero lo expreso de forma vaga, confusa o incompleta.

Si es asi, responde UNICAMENTE con una pregunta corta en espanol guatemalteco que ayude a aclarar que necesita, ofreciendo entre 2 y 4 opciones concretas. No agregues saludos ni explicaciones, solo la pregunta.

Ejemplos:
Mensaje: "no encuentro la cosa esa de la licuadora"
Respuesta: ¿Buscas el repuesto de la licuadora o una orden de servicio?

Mensaje: "cuanto tengo"
Respuesta: ¿Quieres saber el inventario, el saldo del dia o el valor del inventario?

Mensaje: "el cliente ese"
Respuesta: ¿Cual cliente buscas? Puedo buscar por nombre o telefono

Mensaje: "no se"
Respuesta: ¿En que te puedo ayudar? Puedo gestionar inventario, ventas, clientes, reparaciones o generar contenido

Si hay contexto de conversacion reciente disponible (puede ser de dias anteriores), usalo para hacer
la pregunta de clarificacion mas especifica en vez de una generica (ej: si ayer se hablo de licuadoras
y hoy el usuario escribe "y esa otra", pregunta directamente si se refiere a las licuadoras).

Si el mensaje es claramente una pregunta de cultura general, un saludo, charla casual, o algo sin ninguna relacion con el negocio, responde exactamente: NINGUNO

Mensaje del usuario: {message}
Respuesta:"""

def _analizar_intencion_vaga(message: str, contexto: str = "") -> str:
    """Le pregunta a Ollama si el mensaje es una intencion de negocio
    expresada de forma vaga. Retorna la pregunta de clarificacion en espanol,
    o None si no aplica (o si Ollama no esta disponible)."""
    prompt = CLARIFICACION_PROMPT.format(message=message)
    if contexto:
        prompt = (
            "Contexto de conversacion reciente (puede ser de dias anteriores):\n"
            f"{contexto}\n\n{prompt}"
        )
    texto = llamar_ollama(prompt)
    # Mismo criterio que en _translate(): MENSAJE_TIMEOUT no es una pregunta
    # de clarificacion valida, se trata como "no aplico".
    if not texto or texto == MENSAJE_TIMEOUT:
        return None
    texto = texto.strip()
    if not texto or texto.upper() == "NINGUNO":
        return None
    return texto


def _iniciar_flujo_barcode(resultado):
    """Parsea el resultado de tools/inventory_tool.py escanear_codigo_tool()
    (marcador BARCODE_INICIO: si encontro el producto, o
    CODIGO_NO_ENCONTRADO_INICIO: si no) y arma el texto + contexto para
    arrancar el flujo de escaneo. Se llama tanto desde _intentar_detectar()
    (escaneo nuevo, sin flujo previo) como directo desde los steps
    barcode_waiting_accion/barcode_waiting_crear (escaneo que interrumpe la
    pregunta pendiente de un escaneo anterior). Retorna None si `resultado` no
    es ninguno de los dos marcadores."""
    resultado = str(resultado)

    if resultado.startswith("BARCODE_INICIO:"):
        partes = resultado.replace("BARCODE_INICIO:", "").split("|", 5)
        producto_id, nombre, precio, stock, codigo, foto = partes
        context = {
            "step": "barcode_waiting_accion",
            "barcode_producto_id": int(producto_id),
            "barcode_nombre": nombre,
            "barcode_precio": float(precio),
            "barcode_stock": float(stock),
        }
        texto = ""
        if foto:
            ruta = foto if foto.startswith(("http://", "https://", "/")) else f"/{foto}"
            texto += f'<img src="{ruta}" style="max-width:220px;border-radius:8px;margin-bottom:6px"><br>'
        texto += (f"<b>{nombre}</b><br>"
                  f"Código: {codigo or '—'}<br>"
                  f"Precio: Q{precio}<br>"
                  f"Existencias: {int(float(stock))}<br><br>"
                  f"¿Quieres vender este producto? (si/no) o escribe la cantidad")
        return texto, context

    if resultado.startswith("CODIGO_NO_ENCONTRADO_INICIO:"):
        codigo = resultado.replace("CODIGO_NO_ENCONTRADO_INICIO:", "").strip()
        context = {"step": "barcode_waiting_crear", "barcode_codigo_nuevo": codigo}
        return f"Código '{codigo}' no registrado. ¿Quieres agregarlo como producto nuevo? (si/no)", context

    return None


# Frases que, escritas a mitad de cualquier flujo conversacional, cancelan ese flujo
# en vez de interpretarse como el dato que el step actual esperaba (ver salida
# universal en send()).
_PALABRAS_CANCELACION = ["cancelar", "cancela", "salir", "olvida", "olvidalo", "mejor no", "stop"]


def _es_cancelacion(message: str) -> bool:
    texto = unicodedata.normalize("NFD", message or "").encode("ascii", "ignore").decode("utf-8").lower().strip()
    texto = texto.rstrip(".!?")
    for palabra in _PALABRAS_CANCELACION:
        if texto == palabra or texto.startswith(palabra + " ") or texto.startswith(palabra + ","):
            return True
    return False


# Frases que, a mitad de un step que espera un dato puntual, indican que el
# usuario esta cambiando de decision en vez de responder tal cual lo que se le
# pregunto (ej. "mejor tarjeta" en vez de "tarjeta" a secas). "mejor no" y
# "olvida" NO estan aqui a proposito: esas dos ya cancelan el flujo completo mas
# arriba (ver _PALABRAS_CANCELACION / _es_cancelacion, que corre ANTES que
# cualquier step) - agregarlas aqui nunca se alcanzaria a ejecutar.
_FRASES_CAMBIO_DECISION = ["no mejor", "mejor", "cambio a", "cambiar a", "en realidad"]


def _detectar_cambio_decision(message: str, step: str):
    """Si el mensaje trae una de las frases de _FRASES_CAMBIO_DECISION seguida de
    un valor reconocible para el step actual, retorna ese valor ya limpio (ej.
    "mejor tarjeta" en el step venta_waiting_pago -> "tarjeta") para que el
    parseo normal de ese step lo use en vez del mensaje completo, sin tener que
    duplicar esa logica de parseo aqui. Retorna None si el mensaje no trae
    ninguna de esas frases, o si las trae pero no reconoce un valor valido para
    el step actual - en ambos casos el step sigue su parseo normal tal cual
    (que dara su propio mensaje de error si corresponde)."""
    texto = unicodedata.normalize("NFD", message or "").encode("ascii", "ignore").decode("utf-8").lower().strip()
    texto = texto.rstrip(".!?").replace(",", " ")
    texto = " ".join(texto.split())

    resto = None
    for frase in _FRASES_CAMBIO_DECISION:
        if texto.startswith(frase + " "):
            resto = texto[len(frase):].strip()
            break
    if not resto:
        return None

    if step == "reembolso_waiting_monto":
        # "mejor total": ya no quiere que le pregunten un monto parcial, quiere
        # el reembolso completo - mismo valor que reembolso_waiting_tipo acepta.
        return resto if resto in ("total", "todo", "completo") else None

    if step == "venta_waiting_pago":
        metodos = ("efectivo", "tarjeta", "transferencia", "mixto", "credito", "fiado")
        return resto if resto in metodos else None

    if step in ("reembolso_waiting_metodo", "cambio_waiting_metodo_diferencia"):
        metodos = ("efectivo", "tarjeta", "credito tienda", "credito de tienda", "credito")
        return resto if resto in metodos else None

    if step == "cotizacion_waiting_producto":
        # Cualquier texto despues de la frase de cambio se reinterpreta como el
        # nombre del producto correcto (ej. "mejor licuadora" -> "licuadora").
        return resto

    return None


def _intentar_detectar(message: str, role: str, context: dict, contexto_historial: str = ""):
    """Corre deteccion directa (detectores) y, si falla, traduccion via Ollama.
    Retorna (respuesta, context) si algo se detecto, o None si nada aplico."""
    result = _engine.execute(message, role)
    if result:
        if str(result).startswith("PAGO_INICIO:"):
            nombre = str(result).replace("PAGO_INICIO:", "").strip()
            context = {"step": "pago_waiting_dia", "pago_nombre": nombre}
            return f"¿Que dia del mes se paga {nombre}?", context

        if str(result).startswith("VIDEO_INICIO:"):
            partes = str(result).replace("VIDEO_INICIO:", "").split("|")
            producto_id = partes[0]
            nombre = partes[1]
            foto = partes[2] if len(partes) > 2 else ""
            descripcion = partes[3] if len(partes) > 3 else ""
            context = {
                "step": "video_waiting_estilo",
                "video_producto_id": producto_id,
                "video_nombre": nombre,
                "video_foto": foto,
                "video_descripcion": descripcion
            }
            tiene_foto = "Con foto del producto" if foto else "Sin foto (solo texto)"
            return f"Video de {nombre}. {tiene_foto}.\nEstilo del video? (producto, promocional, tutorial, reel viral):", context

        if str(result).startswith("VIDEOFOTO_ENCONTRADO_INICIO:"):
            # Arrancado por tools/contenido_tool.py video_desde_foto_tool cuando
            # identifico (con Ollama vision o con el texto que acompanaba la foto)
            # un producto que ya existe en el inventario. Flujo separado del de
            # VIDEO_INICIO: arriba (ese es "video de [producto ya escrito]" por
            # texto; este es "aqui esta la foto de un producto" - preguntas y
            # steps distintos, ver videofoto_waiting_* mas abajo en send()).
            # split("|", 4): el 5to campo (descripcion_visual, texto libre
            # armado por un modelo de IA) puede traer sus propios "|" - se le
            # deja el resto del string entero sin volver a partirlo.
            partes = str(result).replace("VIDEOFOTO_ENCONTRADO_INICIO:", "").split("|", 4)
            producto_id, nombre, precio = partes[0], partes[1], partes[2]
            foto = partes[3] if len(partes) > 3 else ""
            descripcion_visual = partes[4] if len(partes) > 4 else ""
            context = {
                "step": "videofoto_waiting_confirmar",
                "vf_producto_id": producto_id,
                "vf_nombre": nombre,
                "vf_precio": precio,
                "vf_foto": foto,
                "vf_descripcion_visual": descripcion_visual,
            }
            return f"Encontré {nombre}, precio Q{precio}. ¿Quieres que genere un video? (si/no)", context

        if str(result).startswith("VIDEOFOTO_NUEVO_INICIO:"):
            # No se pudo identificar el producto (sin vision disponible, o vision/
            # texto sin match en el inventario) - se pide nombre y precio a mano en
            # vez de crear el producto solo (ver nota de diseno en BUGS_Y_FIXES.md:
            # a proposito NO se crea un Producto nuevo en la base de datos como
            # efecto secundario de este flujo, solo se usan para armar el video).
            # split("|", 1): igual que arriba, descripcion_visual puede traer
            # sus propios "|".
            partes = str(result).replace("VIDEOFOTO_NUEVO_INICIO:", "").split("|", 1)
            foto = partes[0].strip()
            descripcion_visual = partes[1].strip() if len(partes) > 1 else ""
            context = {"step": "videofoto_waiting_datos_nuevo", "vf_foto": foto, "vf_descripcion_visual": descripcion_visual}
            return "No reconocí el producto. ¿Cómo se llama y cuál es el precio? (ej: licuadora oster 350)", context

        if str(result).startswith("SET_DESC_INICIO:"):
            partes = str(result).replace("SET_DESC_INICIO:", "").split("|")
            producto_id, nombre = partes[0], partes[1]
            context = {"step": "desc_waiting_descripcion", "desc_producto_id": int(producto_id), "desc_nombre": nombre}
            return f"Escribe la descripcion completa de {nombre}:", context

        if str(result).startswith("SCRIPT_INICIO:"):
            producto = str(result).replace("SCRIPT_INICIO:", "").strip()
            context = {"step": "script_waiting_tono", "script_producto": producto}
            return f"Script para video de '{producto}'. Que tono quieres? (energico, profesional, divertido, informativo, emotivo):", context

        if str(result) == "PROGRAMACION_INICIO":
            context = {"step": "prog_waiting_frecuencia"}
            return "Cuantas veces al dia quieres publicar? (1, 2 o 3):", context

        if str(result).startswith("PROVEEDOR_NUEVO:"):
            partes = str(result).replace("PROVEEDOR_NUEVO:", "").split("|")
            proveedor_id, nombre = partes[0], partes[1]
            context = {"step": "proveedor_waiting_contacto", "proveedor_id": int(proveedor_id), "proveedor_nombre": nombre}
            return f"Proveedor {nombre} registrado. Nombre del vendedor/contacto (o 'listo' para terminar):", context

        if str(result).startswith("ORDEN_COMPRA_PAGO_INICIO:"):
            partes = str(result).replace("ORDEN_COMPRA_PAGO_INICIO:", "").split("|", 6)
            orden_id, numero, proveedor_id, proveedor_nombre, proveedor_wa, total, resp = partes
            context = {
                "step": "ordencompra_waiting_pago",
                "oc_orden_id": int(orden_id),
                "oc_numero": numero,
                "oc_proveedor_id": int(proveedor_id),
                "oc_proveedor_nombre": proveedor_nombre,
                "oc_proveedor_tel": proveedor_wa,
                "oc_total": float(total)
            }
            return f"{resp}\n\nSe pago de una vez o queda pendiente? (pagado/pendiente)", context

        if str(result).startswith("VENTA_INICIO:"):
            partes = str(result).replace("VENTA_INICIO:", "").split("|")
            # Puede venir con multiples productos separados por ;
            if ";" in partes[0]:
                # Multiples productos encontrados
                opciones = partes[0].split(";")
                context = {
                    "step": "venta_waiting_seleccion",
                    "venta_cantidad": int(partes[1]) if len(partes) > 1 else 1,
                    "venta_opciones": opciones
                }
                lista = "\n".join([f"{i+1}. {op.split(':')[0]} - Q{op.split(':')[1]}" for i, op in enumerate(opciones)])
                return f"Hay varios productos similares:\n{lista}\n\nEscribe el numero del producto:", context
            else:
                cantidad, producto, precio_unit, total, producto_id = partes
                context = {
                    "step": "venta_waiting_nombre",
                    "venta_ctx": {
                        "cantidad": int(cantidad),
                        "producto": producto,
                        "precio_unit": float(precio_unit),
                        "total": float(total),
                        "producto_id": int(producto_id)
                    }
                }
                return f"Venta: {cantidad}x {producto} = Q{total}. Nombre del cliente (o 'sin nombre'):", context

        if str(result).startswith("DOWNLOAD:"):
            filename = str(result).replace("DOWNLOAD:", "").strip()
            return f'Excel listo. <a href="/api/download/{filename}" download style="color:var(--accent)">⬇️ Descargar {filename}</a>', context

        if str(result).startswith("NUEVA_ORDEN:"):
            context = {"step": "service_waiting_cliente"}
            return "Nombre del cliente:", context

        if str(result).startswith("ENTREGA_GARANTIA_INICIO:"):
            numero_orden = str(result).replace("ENTREGA_GARANTIA_INICIO:", "").strip()
            from database.nimbo_db import DIAS_GARANTIA_REPARACION_DEFAULT
            context = {"step": "servicio_waiting_dias_garantia", "servicio_numero_orden": numero_orden}
            return (f"Cuantos dias de garantia tiene esta reparacion? "
                    f"(por defecto {DIAS_GARANTIA_REPARACION_DEFAULT}, escribe el numero o 'default')"), context

        if str(result).startswith("COTIZACION_INICIO:"):
            cliente_nombre = str(result).replace("COTIZACION_INICIO:", "").strip()
            if cliente_nombre:
                from database.nimbo_db import buscar_cliente_completo
                clientes = buscar_cliente_completo(cliente_nombre)
                if clientes:
                    c = clientes[0]
                    context = {
                        "step": "cotizacion_waiting_producto",
                        "cot_cliente_id": c["Id"],
                        "cot_cliente_nombre": c["Nombre"],
                        "cot_cliente_tel": c.get("Telefono", ""),
                        "cot_items": []
                    }
                    return f"Cotizacion para {c['Nombre']}. Que producto quieres agregar? (o 'listo' para terminar)", context
                context = {"step": "cotizacion_waiting_telefono", "cot_cliente_nombre": cliente_nombre.title(), "cot_items": []}
                return f"Cliente nuevo: {cliente_nombre.title()}. Telefono (o 'sin telefono'):", context
            context = {"step": "cotizacion_waiting_cliente", "cot_items": []}
            return "Para que cliente es la cotizacion?", context

        if str(result).startswith("CLIENTE_NUEVO_INICIO:"):
            partes = str(result).replace("CLIENTE_NUEVO_INICIO:", "").split("|")
            nombre = partes[0]
            telefono = partes[1] if len(partes) > 1 else ""
            context = {"step": "cliente_waiting_grupo", "cliente_nombre": nombre, "cliente_telefono": telefono}
            return (f"Cliente {nombre}. Que tipo de cliente es? "
                    f"(detallista, mayorista, especial o vip - por defecto detallista):"), context

        if str(result).startswith("PRODUCTO_NUEVO_INICIO:"):
            # Arrancado por tools/inventory_tool.py create_product_tool cuando el
            # mensaje ("agregar/nuevo/crear producto X precio N [costo N] [stock N]")
            # no traia precio y/o costo. El stock nunca se pregunta aqui (si no vino
            # en el mensaje se crea con 0, ver producto_waiting_costo mas abajo).
            partes = str(result).replace("PRODUCTO_NUEVO_INICIO:", "").split("|")
            nombre = partes[0]
            precio = partes[1] if len(partes) > 1 else ""
            costo = partes[2] if len(partes) > 2 else ""
            cantidad = float(partes[3]) if len(partes) > 3 and partes[3] else 0
            context = {"step": "producto_waiting_precio", "prod_nombre": nombre, "prod_cantidad": cantidad}
            if precio:
                context["prod_precio"] = float(precio)
                context["step"] = "producto_waiting_costo"
                return f"¿Cuál es el costo de {nombre}?", context
            return f"¿A qué precio se vende {nombre}?", context

        if str(result).startswith("BARCODE_INICIO:") or str(result).startswith("CODIGO_NO_ENCONTRADO_INICIO:"):
            # Arrancado por tools/inventory_tool.py escanear_codigo_tool. Factorizado
            # en _iniciar_flujo_barcode() porque los steps barcode_waiting_accion y
            # barcode_waiting_crear tambien lo llaman directo, cuando el mensaje que
            # llega a mitad de esos steps resulta ser un escaneo NUEVO (no la
            # respuesta si/no/cantidad que se estaba esperando) - ver esos steps.
            return _iniciar_flujo_barcode(result)

        if str(result).startswith("COMBO_INICIO:"):
            nombre_combo = str(result).replace("COMBO_INICIO:", "").strip()
            context = {"step": "combo_crear_waiting_producto", "combo_nombre": nombre_combo, "combo_items": []}
            return f"Creando combo '{nombre_combo}'. Que producto quieres agregar? (o 'listo' para terminar)", context

        if str(result).startswith("REEMBOLSO_INICIO:"):
            venta_id = int(str(result).replace("REEMBOLSO_INICIO:", "").strip())
            from database.nimbo_db import get_venta_por_id, get_cliente_por_id, get_total_reembolsado_venta
            venta = get_venta_por_id(venta_id)
            if not venta:
                return f"No encontre la venta #{venta_id}.", context
            cliente_nombre = "Consumidor Final"
            if venta["ClienteId"]:
                cliente = get_cliente_por_id(venta["ClienteId"])
                if cliente:
                    cliente_nombre = cliente["Nombre"]
            ya_reembolsado = get_total_reembolsado_venta(venta_id)
            disponible = round(venta["Total"] - ya_reembolsado, 2)
            if disponible <= 0:
                return (f"La venta #{venta_id} ya fue reembolsada por completo "
                        f"(Q{ya_reembolsado} de Q{venta['Total']})."), context
            aviso_previo = f" (ya se habian reembolsado Q{ya_reembolsado} antes)" if ya_reembolsado else ""
            context = {"step": "reembolso_waiting_tipo", "reembolso_venta_id": venta_id, "reembolso_disponible": disponible}
            return (f"Venta #{venta_id}: {venta['Descripcion']}\n"
                    f"Total: Q{venta['Total']}{aviso_previo}. Cliente: {cliente_nombre}. "
                    f"Metodo de pago: {_metodo_pago_de(venta['Descripcion'])}.\n"
                    f"Quieres un reembolso total o parcial?"), context

        if str(result).startswith("CAMBIO_PRODUCTO_INICIO:"):
            venta_id = int(str(result).replace("CAMBIO_PRODUCTO_INICIO:", "").strip())
            from database.nimbo_db import get_venta_por_id, get_items_venta
            venta = get_venta_por_id(venta_id)
            if not venta:
                return f"No encontre la venta #{venta_id}.", context
            items = get_items_venta(venta_id)
            if not items:
                return (f"No pude identificar los productos de la venta #{venta_id} "
                        f"(descripcion: '{venta['Descripcion']}'). No se puede hacer el cambio."), context
            if len(items) > 1:
                context = {
                    "step": "cambio_waiting_seleccion_viejo",
                    "cambio_venta_id": venta_id,
                    "cambio_opciones_viejo": [{"nombre": nombre, "cantidad": cantidad} for cantidad, nombre in items]
                }
                lista = "\n".join(f"{i+1}. {cantidad}x {nombre}" for i, (cantidad, nombre) in enumerate(items))
                return f"Venta #{venta_id}. Que producto de esta venta estas cambiando?\n{lista}\n\nEscribe el numero:", context
            cantidad, nombre = items[0]
            context = {
                "step": "cambio_waiting_producto_nuevo",
                "cambio_venta_id": venta_id,
                "cambio_producto_viejo_nombre": nombre,
                "cambio_producto_viejo_cantidad": cantidad
            }
            return f"Venta #{venta_id}. Cambiando {cantidad}x {nombre}. Que producto nuevo se lleva?", context

        if str(result) == "CAJA_ABRIR_INICIO":
            from database.nimbo_db import DENOMINACIONES, get_ultimo_cierre_denominaciones, get_fondo_sugerido
            sugerido = get_ultimo_cierre_denominaciones()
            if sugerido:
                total = sum(int(k) * int(v) for k, v in sugerido.items())
                detalle = ", ".join([f"{v}xQ{k}" for k, v in sugerido.items() if int(v) > 0])
                context = {"step": "caja_abrir_confirmar_sugerido", "caja_fondo_sugerido": sugerido}
                return (f"El cierre anterior quedo en Q{total} ({detalle}). "
                        f"Abrir el turno con este mismo fondo? (si / no, quiero contar de nuevo)"), context
            total_sugerido = get_fondo_sugerido()
            if total_sugerido is not None:
                context = {"step": "caja_abrir_confirmar_sugerido_total", "caja_fondo_sugerido_total": total_sugerido}
                return (f"El cierre anterior dejo Q{total_sugerido} como fondo para hoy. "
                        f"Abrir el turno con Q{total_sugerido}? (si / no, quiero contar por denominacion)"), context
            context = {"step": "caja_abrir_denom", "caja_idx": 0, "caja_fondo": {}}
            return f"Abriendo turno de caja. Fondo inicial: cuantos billetes/monedas de Q{DENOMINACIONES[0]} hay?", context

        if str(result) == "CAJA_CERRAR_INICIO":
            from database.nimbo_db import get_turno_abierto
            turno = get_turno_abierto()
            esperado = turno["EfectivoEsperado"] if turno else 0
            context = {"step": "caja_cerrar_total"}
            return (f"Cerrando turno de caja. Segun mis registros deberia haber Q{esperado} en caja. "
                     "Cuanto hay realmente? (el total nada mas, no hace falta contar billete por billete)"), context

        if str(result) == "CAJA_ANULAR_INICIO":
            context = {"step": "caja_anular_waiting_motivo"}
            return "Cual es el motivo de la anulacion? (esta accion no se puede deshacer)", context

        if str(result).startswith("CAJA_ANULAR_CONFIRMAR:"):
            motivo = str(result).replace("CAJA_ANULAR_CONFIRMAR:", "").strip()
            from database.nimbo_db import get_turno_abierto, anular_turno
            from flask_login import current_user
            turno = get_turno_abierto()
            if not turno:
                return "No hay ningun turno de caja abierto para anular.", context
            resultado = anular_turno(turno["Id"], motivo, current_user.nombre)
            aviso = ""
            if resultado.get("ventas_no_revertidas"):
                aviso = (f" Atencion: este turno ya tenia Q{resultado['ventas_no_revertidas']} en ventas "
                         f"registradas; esas ventas y el stock descontado NO se revierten automaticamente.")
            return f"Turno #{turno['Id']} anulado. Motivo: {motivo}.{aviso}", context

        if "No encontre producto" in str(result):
            m = re.search(r"agrega[r]?\s+(\d+)\s+(.+)", message.lower())
            if not m:
                translated = _translate(message, contexto_historial)
                if translated:
                    m = re.search(r"agrega[r]?\s+(\d+)\s+(.+)", translated.lower())
            if m:
                qty = int(m.group(1))
                product_name = m.group(2).strip()
                context = {"step": "waiting_price", "product_name": product_name, "quantity": qty}
                return f"El producto '{product_name}' no existe. ¿A qué precio se vende? (en quetzales)", context
        return result, context

    translated = _translate(message, contexto_historial)
    if translated:
        result = _engine.execute(translated, role)
        if result:
            if "No encontre producto" in str(result):
                m = re.search(r"agrega[r]?\s+(\d+)\s+(.+)", translated.lower())
                if m:
                    qty = int(m.group(1))
                    product_name = m.group(2).strip()
                    context = {"step": "waiting_price", "product_name": product_name, "quantity": qty}
                    return f"El producto '{product_name}' no existe. ¿A qué precio se vende? (en quetzales)", context
            return result, context

    return None


def _metodo_pago_de(descripcion):
    """Best-effort: solo el pago mixto deja rastro reconocible en la Descripcion de
    una Venta (misma logica duplicada en tools/cliente_tool.py y
    tools/reembolso_tool.py - ver CLAUDE.md seccion Clientes). Para efectivo/
    tarjeta/transferencia/credito simple no hay metodo de pago guardado en la Venta."""
    if descripcion and "Efectivo: Q" in descripcion and "Tarjeta: Q" in descripcion:
        return "mixto (efectivo + tarjeta)"
    return "no registrado"


def _siguiente_paso_venta_credito(context: dict, prefijo: str = "", aviso: str = ""):
    """Despues de resolver el canje de puntos de lealtad (si aplicaba), revisa si el
    cliente tiene credito de tienda disponible (de un reembolso anterior, ver
    tools/reembolso_tool.py) antes de pedir el metodo de pago - mismo criterio
    interactivo que el canje de puntos, implementado solo en la venta simple del
    chat (no en Caja/Cotizaciones, mismo alcance que puntos de lealtad)."""
    from database.nimbo_db import get_credito_cliente
    cliente_id = context.get("venta_cliente_id")
    credito = get_credito_cliente(cliente_id) if cliente_id else 0
    if credito > 0:
        context["step"] = "venta_waiting_usar_credito"
        return f"{prefijo}Tiene Q{credito} de credito en tienda disponible. Quiere usarlo en esta compra? (si/no){aviso}", context
    context["step"] = "venta_waiting_pago"
    return f"{prefijo}Metodo de pago? (efectivo, tarjeta, transferencia, mixto, credito):{aviso}", context


def _registrar_venta_chat(cliente_id, descripcion, total, producto_id=None, producto_nombre="",
                           cliente_nombre="Consumidor Final", cliente_tel="",
                           metodo_pago="", monto_tarjeta=0):
    """Inserta la Venta del flujo de venta simple del chat (un solo producto),
    actualiza la ultima compra del cliente y genera la garantia del producto
    (ver database.nimbo_db.generar_garantia_venta). Usado tanto por el pago de un
    solo metodo como por el pago mixto (efectivo + tarjeta) y la venta a credito.
    monto_tarjeta es el monto REAL cobrado con tarjeta (todo el total si
    metodo_pago='tarjeta', la porcion de tarjeta si fue mixto, 0 en cualquier
    otro caso) - se usa para el cuadre de POS, ver get_cuadre_pos_dia."""
    from database.nimbo_db import nimbo_connect, generar_garantia_venta
    from datetime import datetime
    conn = nimbo_connect()
    cur = conn.cursor()
    now = datetime.now()
    mes = now.month
    trimestre = (mes - 1) // 3 + 1
    anio = now.year
    cur.execute(
        "INSERT INTO Venta (ClienteId, Descripcion, Total, Mes, Trimestre, Anio, MetodoPago, MontoTarjeta) VALUES (?,?,?,?,?,?,?,?)",
        (cliente_id, descripcion, total, mes, trimestre, anio, metodo_pago, monto_tarjeta)
    )
    venta_id = cur.lastrowid
    if cliente_id:
        cur.execute("UPDATE Cliente SET UltimaCompra=? WHERE Id=?", (now.isoformat(), cliente_id))
    conn.commit()
    conn.close()

    garantia = None
    if producto_id is not None:
        garantia = generar_garantia_venta(
            venta_id, producto_id, producto_nombre,
            cliente_id=cliente_id, cliente_nombre=cliente_nombre,
            cliente_telefono=cliente_tel, fecha_venta=now
        )
    return venta_id, garantia


def _finalizar_cotizacion(context: dict):
    """Registra la cotizacion, genera el PDF y arma los links de descarga/WhatsApp."""
    import urllib.parse
    from datetime import datetime
    from database.nimbo_db import crear_cotizacion, calcular_descuento
    from services.pdf_cotizacion import generar_pdf_cotizacion

    items = context.get("cot_items", [])
    subtotal = round(sum(i["subtotal"] for i in items), 2)
    cliente_id = context.get("cot_cliente_id")
    cliente_nombre = context.get("cot_cliente_nombre", "")
    cliente_tel = context.get("cot_cliente_tel", "")

    descuento = calcular_descuento(
        cliente_id=cliente_id,
        productos=[{"producto_id": i["producto_id"], "subtotal": i["subtotal"]} for i in items],
        total=subtotal
    )
    total = round(subtotal - descuento["monto_descuento"], 2) if descuento else subtotal

    notas = f"Descuento {descuento['nombre']}: -Q{descuento['monto_descuento']}" if descuento else ""
    numero, fecha_vencimiento = crear_cotizacion(cliente_id, cliente_nombre, cliente_tel, items, total, notas=notas)

    generar_pdf_cotizacion({
        "numero": numero,
        "cliente_nombre": cliente_nombre,
        "cliente_tel": cliente_tel,
        "items": items,
        "subtotal": subtotal,
        "descuento": descuento,
        "total": total,
        "fecha_creada": datetime.now().strftime("%Y-%m-%d"),
        "fecha_vencimiento": fecha_vencimiento
    })

    resp = f"Cotizacion {numero} generada para {cliente_nombre} por Q{total}"
    if descuento:
        resp += f" (subtotal Q{subtotal}, descuento {descuento['nombre']} -Q{descuento['monto_descuento']})"
    resp += f", valida hasta {fecha_vencimiento[:10]}.\n"
    resp += f'<a href="/static/cotizaciones/{numero}.pdf" target="_blank" style="color:var(--accent)">📄 Descargar PDF</a>'

    if cliente_tel:
        detalle = "\n".join([f"- {i['cantidad']}x {i['nombre']} a Q{i['precio_unit']}" for i in items])
        mensaje_wa = (f"Hola {cliente_nombre}, aqui tiene su cotizacion {numero} de Mi Cocina Electrodomesticos:\n\n"
                      f"{detalle}\n\nTotal: Q{total}\nValida hasta: {fecha_vencimiento[:10]}\n\nGracias por su preferencia.")
        tel = cliente_tel.replace("+", "").replace("-", "").replace(" ", "")
        if not tel.startswith("502"):
            tel = "502" + tel
        link = f"https://wa.me/{tel}?text={urllib.parse.quote(mensaje_wa)}"
        resp += f'<br><a href="{link}" target="_blank" style="color:var(--accent)">📱 Enviar por WhatsApp</a>'

    return resp, {}


def _procesar_cambio_confirmar(context: dict, producto_nuevo_id, producto_nuevo_nombre, producto_nuevo_precio):
    """Calcula la diferencia de precio (con el precio ACTUAL de inventario de ambos
    productos - la venta original no guarda precio por item, ver CLAUDE.md seccion
    Caja) y decide el siguiente paso: confirmar directo si no hay diferencia, o
    preguntar el metodo si hay que cobrar/devolver algo."""
    from database.nimbo_db import get_products
    nombre_viejo = context.get("cambio_producto_viejo_nombre", "")
    cantidad_viejo = context.get("cambio_producto_viejo_cantidad", 1)
    productos_viejo = get_products(search=nombre_viejo)
    precio_viejo_unit = productos_viejo[0]["Price"] if productos_viejo else 0
    precio_viejo = round(precio_viejo_unit * cantidad_viejo, 2)
    diferencia = round(producto_nuevo_precio - precio_viejo, 2)

    context["cambio_producto_nuevo_id"] = producto_nuevo_id
    context["cambio_producto_nuevo_nombre"] = producto_nuevo_nombre
    context["cambio_diferencia"] = diferencia
    resumen = f"Cambio: {cantidad_viejo}x {nombre_viejo} (Q{precio_viejo}) por {producto_nuevo_nombre} (Q{producto_nuevo_precio})."

    if diferencia == 0:
        context["step"] = "cambio_waiting_confirmar"
        return f"{resumen} Sin diferencia que cobrar ni devolver. Confirmas? (si/no)", context

    context["step"] = "cambio_waiting_metodo_diferencia"
    if diferencia > 0:
        return f"{resumen} El cliente debe pagar una diferencia de Q{diferencia}. Como paga la diferencia? (efectivo/tarjeta/credito tienda)", context
    return f"{resumen} Se le debe devolver una diferencia de Q{-diferencia}. Como se la devuelves? (efectivo/tarjeta/credito tienda)", context


def _finalizar_cambio(context: dict, metodo: str):
    from database.nimbo_db import procesar_cambio_producto, get_turno_abierto
    venta_id = context.get("cambio_venta_id")
    nombre_viejo = context.get("cambio_producto_viejo_nombre", "")
    cantidad_viejo = context.get("cambio_producto_viejo_cantidad", 1)
    producto_nuevo_id = context.get("cambio_producto_nuevo_id")

    turno = get_turno_abierto()
    turno_id = turno["Id"] if turno else None

    resultado = procesar_cambio_producto(venta_id, nombre_viejo, cantidad_viejo, producto_nuevo_id, metodo, turno_id=turno_id)
    if resultado.get("error"):
        return resultado["error"], {}

    resp = f"Cambio {resultado['numero']} procesado: {resultado['producto_viejo']} por {resultado['producto_nuevo']}."
    if resultado["diferencia_cobrada"]:
        resp += f" Diferencia cobrada: Q{resultado['diferencia_cobrada']} ({metodo})."
    if resultado["diferencia_devuelta"]:
        resp += f" Diferencia devuelta: Q{resultado['diferencia_devuelta']} ({metodo})."
    if metodo == "tarjeta" and (resultado["diferencia_cobrada"] or resultado["diferencia_devuelta"]):
        resp += " Recuerda procesar la diferencia con el POS fisico."
    if not turno_id and metodo == "efectivo" and (resultado["diferencia_cobrada"] or resultado["diferencia_devuelta"]):
        resp += " Aviso: no hay ningun turno de caja abierto, la diferencia en efectivo no se registro contra ninguna caja."
    return resp, {}


# ── Helpers del flujo de video desde foto (ver steps videofoto_waiting_* en
# send() mas abajo) ──

# Veo 3 image_to_video (el modo que se usa cuando hay foto de referencia, ver
# services/video_gen.py) solo soporta estas 3 duraciones - a diferencia de
# aspect_ratio (que se documenta como no verificado en services/video_gen.py),
# esto SI esta confirmado. Ver videofoto_waiting_duracion en send().
DURACIONES_VEO3_VALIDAS = (4, 6, 8)

# Numero que sigue explicitamente a la palabra "precio" (ej. "precio 168",
# "precio: Q168", "precio de 168") - se busca ESTO primero, antes de caer a
# "el ultimo numero del mensaje", porque el nombre del producto puede traer
# numeros propios que no son el precio (ej. "sarten para 4 huevos, precio
# 168" - el "4" es parte del nombre, no del precio).
_PATRON_PRECIO_EXPLICITO = re.compile(r"precio\s*(?:es|de)?\s*:?\s*q?\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)

# El mensaje ENTERO es solo un numero (con o sin "Q" adelante) - ej. "168",
# "Q168.50" - usado en videofoto_waiting_oferta para reconocer una
# correccion de precio de una sola palabra sin confundirla con una respuesta
# de oferta que tambien traiga numeros (ej. "2x1", "10% de descuento"), que
# NO son solo un numero.
_PATRON_PRECIO_BARE = re.compile(r"^q?\s*(\d+(?:[.,]\d+)?)\.?$", re.IGNORECASE)


def _extraer_precio_producto(mensaje: str):
    """Busca un precio en el mensaje: primero el numero que sigue a la
    palabra "precio" (ver _PATRON_PRECIO_EXPLICITO); si no aparece esa
    palabra, cae al ULTIMO numero del mensaje (el precio normalmente se dice
    al final, ej. "licuadora oster 350" - y asi tampoco se confunde con un
    numero que sea parte del nombre, ej. "sarten para 4 huevos 168" -> toma
    168, no el 4). Retorna (precio, indice donde empieza el match) o
    (None, None) si no encontro ningun numero."""
    m = _PATRON_PRECIO_EXPLICITO.search(mensaje)
    if m:
        return float(m.group(1).replace(",", ".")), m.start()
    matches = list(re.finditer(r"(\d+(?:[.,]\d+)?)", mensaje))
    if matches:
        m = matches[-1]
        return float(m.group(1).replace(",", ".")), m.start()
    return None, None


def _preguntar_descripcion_visual_o_oferta(context: dict, prefijo: str = ""):
    """Se llama justo despues de confirmar el producto que SI viene de un
    analisis real de una foto (tools/contenido_tool.py video_desde_foto_tool
    con llava) - nunca para un producto descrito a mano por el usuario (ver
    videofoto_waiting_datos_nuevo, que llena vf_descripcion_visual el mismo
    con el texto que el usuario ya escribio, y salta esta pregunta a
    proposito: no tiene sentido pedirle que "confirme" algo que el mismo
    acaba de escribir). Si hay descripcion visual, se le pregunta puntualmente
    por el color interior (el dato que mas suele fallar/importar en
    electrodomesticos de cocina - teflon, esmalte, etc.) ANTES de seguir
    (step videofoto_waiting_descripcion_visual), para que un color mal
    identificado no llegue arrastrado hasta el prompt final de Veo 3. Si no
    hay descripcion visual (llava no esta pulled, o no se pudo analizar), se
    salta esa pregunta de una vez y sigue directo con oferta."""
    descripcion_visual = context.get("vf_descripcion_visual", "")
    if descripcion_visual:
        context["step"] = "videofoto_waiting_descripcion_visual"
        return (f"{prefijo}Vi en la foto: {descripcion_visual}\n"
                f"¿El color interior del producto es correcto? Si no, descríbelo "
                f"(ej: 'el interior es amarillo dorado', 'es negro mate por dentro')."), context
    context["step"] = "videofoto_waiting_oferta"
    return f"{prefijo}¿Hay oferta o promoción? (precio especial, descuento, 2x1, etc. o escribe 'no')", context


NOMBRE_PLATAFORMA = {"tiktok": "TikTok", "instagram": "Instagram", "facebook": "Facebook"}


def _resolver_plataforma_motor(texto_plataforma: str) -> str:
    """Interpreta la respuesta libre del usuario en
    videofoto_waiting_plataforma_unica a una de las 3 claves que espera el
    motor determinista (core/video_prompt_engine.py): 'tiktok', 'instagram'
    o 'facebook'. Default 'tiktok' si no reconoce nada."""
    texto_norm = unicodedata.normalize("NFD", texto_plataforma or "").encode("ascii", "ignore").decode("utf-8").lower()
    if "tiktok" in texto_norm:
        return "tiktok"
    if "insta" in texto_norm or "reel" in texto_norm:
        return "instagram"
    if "facebook" in texto_norm or texto_norm.strip() == "fb":
        return "facebook"
    return "tiktok"


def _armar_datos_motor(context: dict) -> dict:
    """Junta los datos ya recolectados en el context (nombre/precio/
    descripcion visual/oferta/mostrar/texto en pantalla/color corregido) en
    los kwargs que espera core.video_prompt_engine.construir_prompts_video().
    vf_plataforma y vf_tono NO se incluyen a proposito: el motor determinista
    asigna un tono y estilo fijo y curado por plataforma (ver
    core/video_prompt_engine.py) que reemplaza la seleccion de tono libre
    del usuario - esas 2 preguntas siguen en el flujo (no se removieron, no
    era parte de este pedido) pero su respuesta ya no se usa para armar el
    prompt. vf_color_corregido se pasa SEPARADO de vf_descripcion_visual (no
    mezclado) para que el motor pueda darle prioridad absoluta sobre el
    color que detecto llava - ver videofoto_waiting_descripcion_visual."""
    return {
        "nombre": context.get("vf_nombre", ""),
        "precio": context.get("vf_precio", ""),
        "descripcion_visual": context.get("vf_descripcion_visual", ""),
        "oferta": context.get("vf_oferta", ""),
        "mostrar": context.get("vf_mostrar", ""),
        "texto_pantalla": context.get("vf_texto_pantalla", ""),
        "color_corregido": context.get("vf_color_corregido", ""),
    }


# Meta-prompt para videofoto_waiting_ajuste: le pide a Ollama que reescriba el
# prompt ANTERIOR (el que ya se uso para generar un video) aplicando el
# cambio puntual que pide el usuario ("quiero el teflon amarillo dorado",
# "cambia la iluminacion"), en vez de arrancar un prompt nuevo desde cero -
# asi el resto del video (producto, tono, composicion) no cambia sin que se
# haya pedido.
PROMPT_AJUSTAR_VIDEO = """Eres un director de videografia publicitaria experto en prompts para Veo 3, el generador de video de Google.

Este es el prompt que se uso para generar un video:
{prompt_anterior}

El cliente pidio este ajuste puntual: "{ajuste}"

Reescribe el prompt COMPLETO aplicando ese ajuste, manteniendo todo lo demas igual (mismo producto, mismo tono, misma estructura: escena principal, sujeto, accion, ambiente, iluminacion, camara, composicion visual, paleta de colores, estilo, texto en pantalla si aplica). Responde SOLO con el prompt final ajustado, en espanol, sin explicaciones ni comillas."""


def _generar_video_final(nombre, prompt, foto, aspect_ratio, duracion):
    """Ultimo paso de generacion real: llama a Veo 3 con el prompt ya decidido
    (basico, optimizado por Ollama, editado a mano, o ajustado post-entrega -
    ver videofoto_waiting_ajuste) y arma la respuesta con el video reproducible
    inline (tag <video> con controles nativos, no solo un link de descarga) +
    un boton de descarga debajo.

    Al terminar, en vez de vaciar el contexto por completo (como hacia antes),
    deja el flujo en el step videofoto_waiting_ajuste con el prompt/datos
    usados guardados - asi el siguiente mensaje del usuario se puede
    interpretar como un pedido de ajuste sobre ESTE mismo video ("cambia la
    iluminacion") sin repetir todas las preguntas desde cero, Y ademas evita
    que un "no" o cualquier respuesta sin sentido despues del video se cuele
    al detector de clarificacion de intenciones vagas y deje al usuario en un
    loop de preguntas sin salida (ver BUGS_Y_FIXES.md) - videofoto_waiting_ajuste
    reconoce esas respuestas de cierre y termina el flujo limpio."""
    from services.video_gen import generar_video_producto
    ruta, error = generar_video_producto(nombre, prompt, foto if foto else None, duracion=duracion, aspect_ratio=aspect_ratio)
    if error:
        return f"Error generando el video: {error}", {}
    context = {
        "step": "videofoto_waiting_ajuste",
        "vf_nombre": nombre,
        "vf_foto": foto,
        "vf_aspect_ratio": aspect_ratio,
        "vf_duracion": duracion,
        "vf_prompt_final": prompt,
    }
    video_html = (
        f'Video de {nombre} generado.<br>'
        f'<video controls preload="metadata" playsinline style="max-width:320px;width:100%;border-radius:8px;display:block;margin-top:6px">'
        f'<source src="{ruta}" type="video/mp4"></video>'
        f'<div style="margin-top:8px"><a href="{ruta}" download style="display:inline-block;padding:6px 14px;'
        f'background:var(--accent);color:white;border-radius:8px;text-decoration:none;font-size:13px">'
        f'⬇️ Descargar video</a></div>'
        f'<div style="margin-top:10px">¡Listo! ¿Quieres generar otro video o necesitas algo más?</div>'
    )
    return video_html, context


def send(message: str, context: dict = None, role: str = "admin") -> tuple:
    """
    Retorna (respuesta, context_actualizado)
    context es un dict con el estado de la conversacion
    role controla que categorias de intent puede ejecutar el usuario (admin | empleado)
    """
    # Salida universal de cualquier flujo conversacional activo: se revisa ANTES que
    # cualquier otra cosa (incluso antes de normalizar context/cargar el historial),
    # para que ningun detector de intents pueda interceptar "cancelar" como si fuera
    # parte de un comando de negocio (ver auditoria: varios steps de texto libre
    # absorbian cualquier mensaje, incluida una cancelacion, como si fuera la
    # respuesta esperada). Solo aplica si hay un step activo - sin flujo en curso,
    # "cancelar" sigue el camino normal (detectores -> Ollama -> fallback final).
    if context and context.get("step") and _es_cancelacion(message):
        # Si el flujo llego a arrancar con VENTA_INICIO, registrar_venta_tool (y el
        # resto de caminos que reusan el mismo marcador: seleccion entre varios
        # productos, venta por unidad de medida) ya le hicieron remove_stock() al
        # producto ANTES de esta conversacion multi-paso (venta_waiting_nombre en
        # adelante) - si se cancela a mitad de camino, ese stock nunca se revertia,
        # dejando el inventario descontado sin ninguna Venta real detras.
        venta_ctx = context.get("venta_ctx")
        aviso_stock = ""
        if venta_ctx and venta_ctx.get("producto_id"):
            from database.nimbo_db import add_stock
            add_stock(venta_ctx["producto_id"], venta_ctx["cantidad"])
            aviso_stock = f" Se repuso el stock de {venta_ctx['producto']} ({venta_ctx['cantidad']} unidad(es))."
        return f"De acuerdo, empecemos de nuevo. ¿En que te puedo ayudar?{aviso_stock}", {}

    # Segunda salida universal, mismo criterio que la de arriba (se revisa
    # ANTES de entrar a cualquier step especifico): una foto NUEVA subida
    # mientras un flujo de video-desde-foto ya esta en curso (steps
    # "videofoto_*") se trata como reinicio del flujo, no como la respuesta de
    # texto libre que el step actual estaba esperando. Sin este chequeo, el
    # marcador crudo "[foto:ruta] texto" se guardaba tal cual en el campo que
    # el step de turno estuviera llenando (vf_mostrar, vf_oferta,
    # vf_texto_pantalla, o incluso vf_nombre via videofoto_waiting_datos_nuevo,
    # que busca numeros en el mensaje y el nombre de archivo del uuid puede
    # traer digitos) - y esa ruta terminaba filtrandose, literal, hasta el
    # prompt final que arma core/video_prompt_engine.py (ver BUGS_Y_FIXES.md).
    # El detector real de este marcador (core/detectors/contenido_foto_detector.py)
    # trabaja sobre texto YA normalizado a minusculas (ver
    # CommandNormalizer.normalize(), que corre recien dentro de
    # _intentar_detectar() mas abajo) - aca el mensaje todavia esta crudo, por
    # eso el chequeo es case-insensitive en vez de buscar "[foto:" literal.
    if (context and str(context.get("step", "")).startswith("videofoto_")
            and re.match(r"^\[foto:", message.strip(), re.IGNORECASE)):
        context = {}

    if context is None:
        context = {}

    # Contexto de conversaciones anteriores (hasta 10 mensajes / ~500 tokens, ver
    # core/chat_context.py). Se calcula una sola vez por mensaje y se reutiliza en
    # todos los llamados a Ollama de esta funcion, para que Nimbo entienda
    # referencias como "cuantas quedan?" aunque el tema se haya hablado dias antes.
    contexto_historial = resumen_texto(obtener_historial_reciente())

    step = context.get("step")

    # Flujo de aclaracion de intencion vaga (ver _analizar_intencion_vaga)
    if step == "clarificando":
        original = context.get("original_message", "")
        context = {}  # se limpia de inmediato: si esto tampoco se detecta, no se vuelve a preguntar

        detectado = _intentar_detectar(message, role, context, contexto_historial)
        if not detectado:
            combinado = f"{original} {message}".strip()
            detectado = _intentar_detectar(combinado, role, context, contexto_historial)
        if detectado:
            return detectado

        # Ni la respuesta sola ni combinada con el mensaje original se detectaron:
        # se responde directo (sin volver a preguntar) para evitar un loop de aclaraciones.
        if role != "admin":
            return ("No entendi esa instruccion. Si necesitas ayuda con algo fuera de "
                    "inventario, ventas o clientes, contacta a un administrador."), context
        return _fallback_ollama(combinado, contexto_historial), context

    # Flujo de cliente nuevo (arrancado por CLIENTE_NUEVO_INICIO, ver
    # tools/cliente_tool.py nuevo_cliente_tool) - pregunta el grupo antes de crear.
    if step == "cliente_waiting_grupo":
        from database.nimbo_db import crear_cliente_completo, set_grupo_cliente, GRUPOS_CLIENTE
        nombre = context.get("cliente_nombre", "")
        telefono = context.get("cliente_telefono", "")
        txt = message.strip().lower()
        if txt in ("", "no", "ninguno", "default", "normal"):
            grupo = "detallista"
        elif txt in GRUPOS_CLIENTE:
            grupo = txt
        elif txt.rstrip("s") in GRUPOS_CLIENTE:
            grupo = txt.rstrip("s")
        else:
            return ("Tipo de cliente no reconocido. Escribe: detallista, mayorista, "
                     "especial o vip (o 'no' para dejarlo como detallista)."), context

        cliente_id, creado = crear_cliente_completo(nombre, telefono)
        context = {}
        if not creado:
            return f"El cliente con telefono {telefono} ya existe.", context
        if grupo != "detallista":
            set_grupo_cliente(cliente_id, grupo)
        return f"Cliente {nombre} registrado con telefono {telefono}. Grupo: {grupo.capitalize()}.", context

    # Flujo de agregar pago fijo
    if step == "pago_waiting_dia":
        try:
            dia = int(message.strip())
            context["pago_dia"] = dia
            context["step"] = "pago_waiting_frecuencia"
            return f"¿Con que frecuencia? (mensual, quincenal, anual):", context
        except:
            return "Escribe solo el numero del dia. Ejemplo: 5", context

    if step == "pago_waiting_frecuencia":
        frecuencia = message.strip().lower()
        context["pago_frecuencia"] = frecuencia
        context["step"] = "pago_waiting_monto"
        return "¿De cuanto es el pago (en quetzales)?", context

    if step == "pago_waiting_monto":
        from database.nimbo_db import agregar_pago_fijo
        nombre = context.get("pago_nombre", "")
        dia = context.get("pago_dia", 1)
        frecuencia = context.get("pago_frecuencia", "mensual")
        try:
            monto = float(message.strip().replace("Q", "").replace("q", ""))
        except ValueError:
            return "Escribe solo el monto en quetzales. Ejemplo: 1500", context
        agregar_pago_fijo(nombre, frecuencia, dia, monto=monto)
        context = {}
        return f"Pago '{nombre}' registrado: Q{monto:.2f} el dia {dia} de cada {frecuencia}.", context

    # Flujo de generacion de video
    if step == "video_waiting_estilo":
        estilo = message.strip()
        context["video_estilo"] = estilo
        context["step"] = "video_waiting_texto"
        return f"Texto o mensaje principal para el video (o 'automatico' para que Nimbo lo genere):", context

    if step == "video_waiting_texto":
        texto = message.strip()
        nombre = context.get("video_nombre", "")
        descripcion = context.get("video_descripcion", "")
        estilo = context.get("video_estilo", "promocional")
        foto = context.get("video_foto", "")
        context = {}

        if texto.lower() == "automatico":
            texto = descripcion or nombre

        prompt_final = f"Video {estilo} de {nombre} para Mi Cocina Electrodomesticos Guatemala. {texto}"

        from services.video_gen import generar_video_producto
        return f"Generando video de {nombre}, esto puede tardar 1-2 minutos...", {"step": "video_generando", "video_prompt": prompt_final, "video_foto": foto, "video_nombre": nombre}

    if step == "video_generando":
        from services.video_gen import generar_video_producto
        prompt = context.get("video_prompt", "")
        foto = context.get("video_foto", "")
        nombre = context.get("video_nombre", "")
        context = {}
        ruta, error = generar_video_producto(nombre, prompt, foto if foto else None)
        if error:
            return f"Error generando video: {error}", context
        return f'<video controls style="max-width:300px;border-radius:8px"><source src="{ruta}" type="video/mp4"></video><br>Video de {nombre} generado. <a href="{ruta}" download style="color:var(--accent)">⬇️ Descargar</a>', context

    # Flujo de video de producto generado desde una foto subida al chat (ver
    # core/detectors/contenido_foto_detector.py, app.py /api/chat/foto,
    # tools/contenido_tool.py video_desde_foto_tool). Arrancado por
    # VIDEOFOTO_ENCONTRADO_INICIO:/VIDEOFOTO_NUEVO_INICIO: mas arriba en
    # _intentar_detectar(). Flujo separado del de video_waiting_estilo/
    # video_waiting_texto de arriba (ese arranca escribiendo "video de X" por
    # texto; este arranca subiendo una foto) - preguntas y datos distintos,
    # aunque ambos terminan llamando a generar_video_producto().
    #
    # Despues de tono, el flujo sigue con mostrar/texto en pantalla/duracion/
    # optimizar-con-IA (ver videofoto_waiting_mostrar en adelante) y termina
    # SIEMPRE con una previsualizacion del prompt final (basico o el que arme
    # Ollama) antes de generar el video - "confirmar" genera de una vez,
    # "editar" pide un prompt de reemplazo completo y genera con ese.
    if step == "videofoto_waiting_confirmar":
        resp = message.strip().lower()
        if resp not in ["si", "si.", "sí", "s", "ok", "dale", "yes", "de una"]:
            return "Entendido, no genero el video.", {}
        return _preguntar_descripcion_visual_o_oferta(context)

    if step == "videofoto_waiting_datos_nuevo":
        # "No reconoci el producto. Como se llama y cual es el precio?" -
        # se piden ambos datos en una sola respuesta (ej. "licuadora oster
        # 350", o "sarten para 4 huevos aldura, precio 168"). El precio se
        # busca con _extraer_precio_producto() - prioriza el numero que sigue
        # a la palabra "precio" para no confundirlo con un numero que sea
        # parte del nombre (el "4" de "4 huevos" en el ejemplo de arriba); el
        # resto del mensaje (sin palabras de relleno como "precio"/"cuesta")
        # es el nombre. A proposito NO se crea un Producto nuevo en la base
        # de datos con estos datos - solo se usan para armar el prompt del
        # video (ver nota en BUGS_Y_FIXES.md).
        precio, idx = _extraer_precio_producto(message)
        if precio is None:
            return "No pude identificar el precio. Escribe el nombre del producto y el precio (ej: licuadora oster 350).", context
        nombre = message[:idx].strip()
        nombre = re.sub(r"\b(precio|cuesta|vale|a|q|quetzales|es|de|por)\b\s*:?\s*$", "", nombre, flags=re.IGNORECASE).strip(" ,.-")
        if not nombre:
            nombre = message[idx:].strip(" ,.-Q")
        if not nombre:
            return "No pude identificar el nombre del producto. Escribe el nombre y el precio (ej: licuadora oster 350).", context
        context["vf_nombre"] = nombre.title()
        context["vf_precio"] = precio
        if not context.get("vf_descripcion_visual"):
            # Sin analisis de llava (no esta pulled, o no ayudo a encontrar
            # el producto): se usa el texto completo que el usuario escribio
            # como descripcion visual tambien - asi detalles como "teflon
            # amarillo" no quedan atrapados solo dentro del nombre, sino que
            # tambien alimentan el prompt visual (_apertura() en
            # core/video_prompt_engine.py) y las reglas de contraste de color
            # (elegir_fondo_y_iluminacion()). NO se dispara la pregunta de
            # confirmacion de color de mas abajo en este caso a proposito -
            # ese texto lo acaba de escribir el usuario, no lo "vio" ningun
            # analisis de llava; pedirle que confirme sus propias palabras
            # seria confuso.
            context["vf_descripcion_visual"] = nombre
            context["step"] = "videofoto_waiting_oferta"
            return f"Producto: {nombre.title()}, precio Q{precio:g}.\n¿Hay oferta o promoción? (precio especial, descuento, 2x1, etc. o escribe 'no')", context
        return _preguntar_descripcion_visual_o_oferta(context, prefijo=f"Producto: {nombre.title()}, precio Q{precio:g}.\n")

    if step == "videofoto_waiting_descripcion_visual":
        # Confirmacion/correccion del color interior real (ver
        # tools/contenido_tool.py video_desde_foto_tool, analisis con llava)
        # antes de seguir con el resto de preguntas - permite corregir un
        # color mal identificado en vez de arrastrarlo hasta el prompt final
        # de Veo 3.
        resp_norm = unicodedata.normalize("NFD", message.strip()).encode("ascii", "ignore").decode("utf-8").lower().rstrip(".!?")
        if resp_norm in ("si", "s", "ok", "correcto", "esta bien", "de una", "dale", "yes"):
            pass  # descripcion (incluido el color) se queda igual, sigue con oferta mas abajo
        elif resp_norm in ("no", "no gracias", "nel", "para nada"):
            # Un "no" a secas dice que el color NO es correcto pero todavia
            # no trae la correccion en si - hay que pedirla, no guardar el
            # literal "no" como si fuera la descripcion nueva (bug real
            # encontrado al probar este mismo step en una version anterior:
            # un "no" bare se colaba al else de abajo y pisaba la descripcion
            # real).
            return ("¿Cuál es el color correcto? Escribe algo como 'el interior es "
                    "amarillo dorado' o 'es negro mate por dentro'."), context
        else:
            # El usuario corrigio el color: se guarda APARTE
            # (vf_color_corregido), sin tocar vf_descripcion_visual. Una
            # version anterior lo anteponia concatenado directo al texto de
            # llava (que podia seguir mencionando el color VIEJO, ej.
            # "Teflon negro mate") - eso dejaba ambas afirmaciones de color
            # compitiendo en el mismo bloque de texto, y tanto el prompt
            # final como la eleccion de fondo por contraste (ver
            # core/video_prompt_engine.py elegir_fondo_y_iluminacion) podian
            # terminar basandose en el color equivocado, que seguia presente
            # palabra por palabra. Guardandolo separado,
            # core.video_prompt_engine.construir_prompts_video() le da
            # prioridad absoluta al color corregido en ambos lugares (ver
            # _clausula_color_material()).
            context["vf_color_corregido"] = message.strip()
        context["step"] = "videofoto_waiting_oferta"
        return "¿Hay oferta o promoción? (precio especial, descuento, 2x1, etc. o escribe 'no')", context

    if step == "videofoto_waiting_oferta":
        texto = message.strip()
        # Correccion de precio a mitad de flujo: si el usuario escribe
        # "precio 168" o directamente "168" (mensaje entero = solo un
        # numero) en vez de responder la pregunta de oferta, se interpreta
        # como una correccion del precio detectado antes, no como respuesta
        # de oferta - se actualiza y se vuelve a preguntar oferta (el step no
        # cambia). Se exige la palabra "precio" O que el mensaje sea SOLO un
        # numero (no "contiene un numero en cualquier lado") para no
        # confundir una oferta real que tambien trae numeros (ej. "2x1",
        # "10% de descuento") con una correccion de precio.
        es_correccion_precio = bool(_PATRON_PRECIO_EXPLICITO.search(texto)) or bool(_PATRON_PRECIO_BARE.match(texto))
        if es_correccion_precio:
            precio_nuevo, _ = _extraer_precio_producto(texto)
            if precio_nuevo is not None:
                context["vf_precio"] = precio_nuevo
                return (f"Precio actualizado a Q{precio_nuevo:g}.\n"
                        f"¿Hay oferta o promoción? (precio especial, descuento, 2x1, etc. o escribe 'no')"), context
        context["vf_oferta"] = "" if texto.lower() in ("no", "no.", "ninguna", "no hay") else texto
        context["step"] = "videofoto_waiting_plataforma"
        return "¿Para qué plataforma? (TikTok / Instagram Reels / Facebook / General)", context

    if step == "videofoto_waiting_plataforma":
        context["vf_plataforma"] = message.strip()
        context["step"] = "videofoto_waiting_tono"
        return "¿Qué tono quieres? (Urgente y llamativo / Informativo / Divertido y casual / Elegante)", context

    if step == "videofoto_waiting_tono":
        context["vf_tono"] = message.strip()
        context["step"] = "videofoto_waiting_mostrar"
        return "¿Qué quieres mostrar en el video? (uso del producto / características / demostración / unboxing)", context

    if step == "videofoto_waiting_mostrar":
        context["vf_mostrar"] = message.strip()
        context["step"] = "videofoto_waiting_texto_pantalla"
        return "¿Algún texto o frase que quieras que aparezca en el video? (escríbelo, o 'no')", context

    if step == "videofoto_waiting_texto_pantalla":
        texto = message.strip()
        context["vf_texto_pantalla"] = "" if texto.lower() in ("no", "no.", "ninguno", "ninguna") else texto
        context["step"] = "videofoto_waiting_duracion"
        return "¿Duración aproximada? (4 segundos / 6 segundos / 8 segundos)", context

    if step == "videofoto_waiting_duracion":
        # Veo 3 image_to_video (el modo que usa este flujo cuando hay foto de
        # referencia, ver services/video_gen.py) solo soporta 4, 6 u 8 segundos
        # - a diferencia de aspect_ratio/duracion en otros lugares de este
        # archivo, esto SI esta confirmado (no es una suposicion sin
        # verificar), asi que ademas de ofrecer solo esas 3 opciones en la
        # pregunta, cualquier numero que el usuario escriba se ajusta al valor
        # valido mas cercano en vez de pasarlo tal cual - para no mandarle a
        # Veo 3 un duration_seconds que sabemos que va a rechazar.
        m = re.search(r"(\d+)", message)
        if m:
            context["vf_duracion"] = min(DURACIONES_VEO3_VALIDAS, key=lambda d: abs(d - int(m.group(1))))
        else:
            context["vf_duracion"] = 8
        context["step"] = "videofoto_waiting_cuantos_prompts"
        return "¿Quieres los 3 prompts (TikTok/Instagram/Facebook) o solo uno? (3 / uno)", context

    if step == "videofoto_waiting_cuantos_prompts":
        # Ultimo paso de preguntas: con todo lo recolectado, el motor
        # determinista (core/video_prompt_engine.py - sin Ollama, ver ese
        # archivo) arma los 3 prompts listos para Veo 3. "3" los muestra
        # todos numerados para elegir uno (videofoto_waiting_elegir_prompt_
        # multiple); "uno" pregunta la plataforma primero
        # (videofoto_waiting_plataforma_unica) y muestra solo ese.
        from core.video_prompt_engine import construir_prompts_video

        resp = unicodedata.normalize("NFD", message.strip()).encode("ascii", "ignore").decode("utf-8").lower()
        quiere_los_3 = resp in ("3", "los 3", "las 3", "tres", "todos", "todas", "los tres")

        if quiere_los_3:
            prompts = construir_prompts_video(**_armar_datos_motor(context))
            context["vf_prompt_1"] = prompts["tiktok"]
            context["vf_prompt_1_plataforma"] = "tiktok"
            context["vf_prompt_2"] = prompts["instagram"]
            context["vf_prompt_2_plataforma"] = "instagram"
            context["vf_prompt_3"] = prompts["facebook"]
            context["vf_prompt_3_plataforma"] = "facebook"
            context["step"] = "videofoto_waiting_elegir_prompt_multiple"
            return (f"Aquí tienes los 3 prompts:\n\n"
                    f"1) TikTok:\n{prompts['tiktok']}\n\n"
                    f"2) Instagram:\n{prompts['instagram']}\n\n"
                    f"3) Facebook:\n{prompts['facebook']}\n\n"
                    f"¿Cuál confirmas? Escribe 1, 2 o 3 - o 'editar 1'/'editar 2'/'editar 3' si quieres cambiar alguno."), context

        context["step"] = "videofoto_waiting_plataforma_unica"
        return "¿Para cuál plataforma? (TikTok / Instagram / Facebook)", context

    if step == "videofoto_waiting_plataforma_unica":
        from core.video_prompt_engine import construir_prompts_video, ASPECT_RATIO_POR_PLATAFORMA

        plataforma = _resolver_plataforma_motor(message)
        prompts = construir_prompts_video(**_armar_datos_motor(context))
        prompt_elegido = prompts[plataforma]

        context["step"] = "videofoto_waiting_prompt_decision"
        context["vf_prompt_final"] = prompt_elegido
        context["vf_aspect_ratio"] = ASPECT_RATIO_POR_PLATAFORMA[plataforma]
        return (f"Este es el prompt para {NOMBRE_PLATAFORMA.get(plataforma, plataforma.title())} que se usará para generar el video:\n\n{prompt_elegido}\n\n"
                f"¿Confirmar y generar video, o prefieres editarlo? (escribe 'confirmar' o 'editar')"), context

    if step == "videofoto_waiting_elegir_prompt_multiple":
        from core.video_prompt_engine import ASPECT_RATIO_POR_PLATAFORMA

        texto_norm = unicodedata.normalize("NFD", message.strip()).encode("ascii", "ignore").decode("utf-8").lower()
        m_editar = re.match(r"editar\s*(\d)$", texto_norm)
        m_num = re.match(r"^(\d)$", texto_norm)

        if m_editar and context.get(f"vf_prompt_{m_editar.group(1)}"):
            idx = m_editar.group(1)
            plataforma = context.get(f"vf_prompt_{idx}_plataforma", "tiktok")
            context["step"] = "videofoto_waiting_prompt_editado"
            context["vf_aspect_ratio"] = ASPECT_RATIO_POR_PLATAFORMA.get(plataforma, "9:16")
            return f"Escribe el prompt que quieras usar para {NOMBRE_PLATAFORMA.get(plataforma, plataforma.title())} en su lugar (reemplaza el anterior por completo):", context

        if m_num and context.get(f"vf_prompt_{m_num.group(1)}"):
            idx = m_num.group(1)
            plataforma = context.get(f"vf_prompt_{idx}_plataforma", "tiktok")
            prompt_elegido = context[f"vf_prompt_{idx}"]
            return _generar_video_final(
                context.get("vf_nombre", ""), prompt_elegido,
                context.get("vf_foto", ""), ASPECT_RATIO_POR_PLATAFORMA.get(plataforma, "9:16"),
                context.get("vf_duracion", 8),
            )

        return "No reconozco esa opción. Escribe 1, 2 o 3 - o 'editar 1'/'editar 2'/'editar 3'.", context

    if step == "videofoto_waiting_prompt_decision":
        resp = unicodedata.normalize("NFD", message.strip()).encode("ascii", "ignore").decode("utf-8").lower()
        if resp in ("editar", "edita", "editar prompt", "cambiar", "modificar"):
            context["step"] = "videofoto_waiting_prompt_editado"
            return "Escribe el prompt que quieras usar en su lugar (reemplaza el anterior por completo):", context
        if resp in ("confirmar", "confirma", "confirmar y generar video", "si", "si.", "sí", "s", "ok", "dale", "generar", "genera", "de una"):
            return _generar_video_final(
                context.get("vf_nombre", ""), context.get("vf_prompt_final", ""),
                context.get("vf_foto", ""), context.get("vf_aspect_ratio", "9:16"),
                context.get("vf_duracion", 8),
            )
        return "No entendí. Escribe 'confirmar' para generar el video con este prompt, o 'editar' para cambiarlo.", context

    if step == "videofoto_waiting_prompt_editado":
        prompt_editado = message.strip()
        if not prompt_editado:
            return "El prompt no puede quedar vacío. Escribe el prompt que quieras usar:", context
        return _generar_video_final(
            context.get("vf_nombre", ""), prompt_editado,
            context.get("vf_foto", ""), context.get("vf_aspect_ratio", "9:16"),
            context.get("vf_duracion", 8),
        )

    if step == "videofoto_waiting_ajuste":
        # Arrancado por _generar_video_final() apenas se entrega un video -
        # en vez de vaciar el contexto (lo que hacia que un "no" o cualquier
        # respuesta ambigua se colara al detector de clarificacion de
        # intenciones vagas y dejara al usuario en un loop de preguntas sin
        # salida, ver BUGS_Y_FIXES.md), este step decide entre dos caminos:
        # una frase de cierre (termina el flujo limpio) o un pedido de ajuste
        # sobre el video recien generado (le pide a Ollama que reescriba el
        # prompt anterior aplicando ese cambio puntual, y lo muestra para
        # confirmar/editar igual que un prompt nuevo).
        texto = message.strip()
        texto_norm = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode("utf-8").lower().rstrip(".!?")
        FRASES_CIERRE_AJUSTE = (
            "no", "no gracias", "no, gracias", "nada", "nada mas", "listo",
            "gracias", "ya esta", "eso es todo", "asi esta bien", "esta bien",
            "por ahora no", "no por ahora",
        )
        if texto_norm in FRASES_CIERRE_AJUSTE:
            return "Perfecto, aquí estoy si necesitas algo más.", {}

        from services.ollama_service import llamar_ollama, MENSAJE_TIMEOUT
        prompt_anterior = context.get("vf_prompt_final", "")
        prompt_ia = llamar_ollama(PROMPT_AJUSTAR_VIDEO.format(prompt_anterior=prompt_anterior, ajuste=texto))
        if prompt_ia and prompt_ia != MENSAJE_TIMEOUT:
            prompt_ajustado = prompt_ia.strip()
            aviso = ""
        else:
            prompt_ajustado = f"{prompt_anterior} Ajuste pedido: {texto}."
            aviso = "\n\n(No pude aplicar el ajuste con IA en este momento - lo agregué directo al prompt anterior.)"

        context["step"] = "videofoto_waiting_prompt_decision"
        context["vf_prompt_final"] = prompt_ajustado
        return (f"Este es el prompt ajustado que se usará para el nuevo video:\n\n{prompt_ajustado}{aviso}\n\n"
                f"¿Confirmar y generar video, o prefieres editarlo? (escribe 'confirmar' o 'editar')"), context

    # Flujo de descripcion de producto
    if step == "desc_waiting_descripcion":
        descripcion = message.strip()
        context["step"] = "desc_waiting_corta"
        context["desc_descripcion"] = descripcion
        return f"Descripcion corta (max 100 caracteres, para WhatsApp/redes):", context

    if step == "desc_waiting_corta":
        from database.nimbo_db import set_descripcion_producto
        corta = message.strip()[:100]
        set_descripcion_producto(context["desc_producto_id"], context["desc_nombre"], context["desc_descripcion"], corta)
        nombre = context["desc_nombre"]
        context = {}
        return f"Descripcion de {nombre} guardada correctamente.", context

    # Flujo de script de video
    if step == "script_waiting_tono":
        context["script_tono"] = message.strip()
        context["step"] = "script_waiting_duracion"
        return "Duracion del video? (15, 30, 60 segundos o 1 minuto):", context

    if step == "script_waiting_duracion":
        context["script_duracion"] = message.strip()
        context["step"] = "script_waiting_red"
        return "Para que red social? (TikTok, Instagram, Facebook, todas):", context

    if step == "script_waiting_red":
        context["script_red"] = message.strip()
        context["step"] = "script_waiting_objetivo"
        return "Cual es el objetivo? (vender, informar, entretener, generar engagement):", context

    if step == "script_waiting_objetivo":
        objetivo = message.strip()
        producto = context.get("script_producto", "")
        tono = context.get("script_tono", "profesional")
        duracion = context.get("script_duracion", "30 segundos")
        red = context.get("script_red", "Instagram")
        context = {}

        prompt = f"""Eres experto en contenido viral para redes sociales en Guatemala.
Crea un script completo para video de {duracion} para {red}.
Producto: {producto}
Tono: {tono}
Objetivo: {objetivo}
Negocio: Mi Cocina Electrodomesticos Guatemala

El script debe incluir:
- Gancho inicial (primeros 3 segundos)
- Desarrollo del mensaje
- Llamada a la accion final
- Indicaciones de camara/escena entre parentesis
- Texto en pantalla sugerido entre corchetes

En espanol guatemalteco natural."""

        texto = llamar_ollama(prompt)
        return (texto if texto else "Ollama no esta disponible ahora mismo."), context

    # Flujo de programacion de contenido
    if step == "prog_waiting_frecuencia":
        context["prog_frecuencia"] = message.strip()
        context["step"] = "prog_waiting_horas"
        frecuencia = message.strip()
        if frecuencia == "1":
            return "A que hora quieres publicar? (ej: 12pm):", context
        elif frecuencia == "2":
            return "A que horas? (ej: 9am y 6pm):", context
        else:
            return "A que horas? (ej: 9am, 1pm y 7pm):", context

    if step == "prog_waiting_horas":
        context["prog_horas"] = message.strip()
        context["step"] = "prog_waiting_tipos"
        return "Que tipos de contenido quieres alternar? (ej: productos, tips, promociones, testimonios):", context

    if step == "prog_waiting_tipos":
        tipos = message.strip()
        frecuencia = context.get("prog_frecuencia", "1")
        horas = context.get("prog_horas", "12pm")
        context = {}

        prompt = f"""Eres experto en marketing digital para Mi Cocina Electrodomesticos Guatemala.
Crea un plan de publicacion semanal con estas especificaciones:
- Frecuencia: {frecuencia} publicacion(es) por dia
- Horarios: {horas}
- Tipos de contenido: {tipos}

Genera un calendario para 7 dias con:
- Dia y hora
- Red social sugerida
- Tipo de contenido
- Tema especifico sugerido
- Formato (foto, video, carrusel, historia)

En espanol, practico y realista para una tienda de electrodomesticos en Guatemala."""

        texto = llamar_ollama(prompt)
        return (texto if texto else "Ollama no esta disponible ahora mismo."), context

    # Flujo de nuevo proveedor
    if step == "proveedor_waiting_contacto":
        if message.strip().lower() in ["listo", "no", "ninguno", "skip"]:
            context = {}
            return f"Proveedor guardado sin contacto.", context
        context["contacto_nombre"] = message.strip().title()
        context["step"] = "proveedor_waiting_contacto_wa"
        return f"WhatsApp de {message.strip().title()} (o 'skip'):", context

    if step == "proveedor_waiting_contacto_wa":
        wa = message.strip()
        if wa.lower() == "skip": wa = ""
        context["step"] = "proveedor_waiting_contacto_cargo"
        context["contacto_wa"] = wa
        return "Cargo del contacto? (ej: Vendedor, Gerente, Representante):", context

    if step == "proveedor_waiting_contacto_cargo":
        from database.nimbo_db import agregar_contacto_proveedor
        cargo = message.strip().title()
        agregar_contacto_proveedor(
            context["proveedor_id"],
            context["contacto_nombre"],
            context.get("contacto_wa", ""),
            cargo
        )
        nombre_prov = context["proveedor_nombre"]
        context = {}
        return f"Contacto registrado. Proveedor listo. Para agregar una orden de compra di: pedido a {nombre_prov}", context

    # Flujo de pago de una orden de compra recien creada (arrancado por
    # ORDEN_COMPRA_PAGO_INICIO, ver tools/proveedor_tool.py generar_orden_tool)
    if step == "ordencompra_waiting_pago":
        txt = message.strip().lower()
        numero = context.get("oc_numero", "")
        if txt in ["pagado", "pago", "ya pague", "de contado", "contado", "si"]:
            context = {}
            return f"Orden {numero} marcada como pagada. No se creo ninguna cuenta por pagar.", context
        if txt in ["pendiente", "no", "queda pendiente", "fiado", "credito"]:
            context["step"] = "ordencompra_waiting_fecha"
            return "Para cuando queda de pagar? (fecha dd/mm/aaaa o los dias, ej: 30)", context
        return "Responde 'pagado' o 'pendiente'.", context

    if step == "ordencompra_waiting_fecha":
        from datetime import datetime, timedelta
        from database.nimbo_db import DIAS_VENCIMIENTO_PAGAR_DEFAULT, crear_cuenta_pagar
        txt = message.strip()
        fecha_vencimiento = None
        if txt.isdigit():
            fecha_vencimiento = (datetime.now() + timedelta(days=int(txt))).strftime("%Y-%m-%d")
        else:
            for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
                try:
                    fecha_vencimiento = datetime.strptime(txt, fmt).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
        aviso_fecha = ""
        if not fecha_vencimiento:
            fecha_vencimiento = (datetime.now() + timedelta(days=DIAS_VENCIMIENTO_PAGAR_DEFAULT)).strftime("%Y-%m-%d")
            aviso_fecha = f" No entendi la fecha, se dejo por defecto a {DIAS_VENCIMIENTO_PAGAR_DEFAULT} dias ({fecha_vencimiento})."

        numero = context.get("oc_numero", "")
        proveedor_id = context.get("oc_proveedor_id")
        proveedor_nombre = context.get("oc_proveedor_nombre", "")
        proveedor_tel = context.get("oc_proveedor_tel", "")
        total = context.get("oc_total", 0)
        orden_id = context.get("oc_orden_id")
        context = {}

        crear_cuenta_pagar(
            proveedor_id, proveedor_nombre, proveedor_tel,
            f"Orden {numero}", total, fecha_vencimiento=fecha_vencimiento, orden_compra_id=orden_id
        )
        return (f"Cuenta por pagar creada para {proveedor_nombre}: Q{total} (orden {numero}), "
                f"vence {fecha_vencimiento}.{aviso_fecha}"), context

    # Flujo de venta con cliente
    if step == "venta_waiting_seleccion":
        try:
            idx = int(message.strip()) - 1
            opciones = context.get("venta_opciones", [])
            if 0 <= idx < len(opciones):
                op = opciones[idx].split(":")
                nombre_prod = op[0].strip()
                precio = float(op[1].strip()) if len(op) > 1 else 0
                producto_id = int(op[2].strip()) if len(op) > 2 else 0
                # 4to campo opcional: cuantas unidades base representa cada unidad de
                # medida (ej. 12 si es una docena). Ausente = 1 (venta por unidad simple).
                cantidad_por_unidad = float(op[3].strip()) if len(op) > 3 else 1
                cantidad = context.get("venta_cantidad", 1)
                cantidad_base = cantidad * cantidad_por_unidad

                from database.nimbo_db import get_product_by_id, remove_stock
                producto = get_product_by_id(producto_id)
                stock = producto["Stock"] if producto else 0
                if stock < cantidad_base:
                    return f"Stock insuficiente. {nombre_prod} solo tiene {int(stock)} unidades disponibles. Escribe el numero de otro producto:", context
                remove_stock(producto_id, cantidad_base, razon="Venta")

                total = precio * cantidad
                context["venta_ctx"] = {"cantidad": cantidad, "producto": nombre_prod, "precio_unit": precio, "total": total, "producto_id": producto_id}
                context["step"] = "venta_waiting_nombre"
                return f"Venta: {cantidad}x {nombre_prod} = Q{total}. Nombre del cliente (o 'sin nombre'):", context
        except:
            pass
        return "Por favor escribe el numero del producto:", context

    if step == "venta_waiting_nombre":
        msg = message.strip().lower()
        if msg in ["sin nombre", "sin cliente", "contado", "cf", "consumidor final"]:
            context["venta_cliente_nombre"] = "Consumidor Final"
            context["venta_cliente_id"] = None
            context["step"] = "venta_waiting_telefono"
            return "Telefono del cliente (o 'sin telefono'):", context
        from database.nimbo_db import buscar_cliente_completo
        clientes = buscar_cliente_completo(message.strip())
        if clientes:
            context["venta_cliente_id"] = clientes[0]["Id"]
            context["venta_cliente_nombre"] = clientes[0]["Nombre"]
            from database.nimbo_db import get_saldo_puntos, puntos_a_quetzales, PUNTOS_POR_CANJE
            saldo = get_saldo_puntos(clientes[0]["Id"])
            if saldo >= PUNTOS_POR_CANJE:
                context["step"] = "venta_waiting_canjear_puntos"
                valor = puntos_a_quetzales(saldo)
                return (f"Cliente encontrado: {clientes[0]['Nombre']}. Tiene {saldo} puntos disponibles "
                        f"(Q{valor} en descuentos). Quiere canjearlos en esta compra? (si/no)"), context
            return _siguiente_paso_venta_credito(context, prefijo=f"Cliente encontrado: {clientes[0]['Nombre']}. ")
        context["venta_cliente_nombre"] = message.strip().title()
        context["step"] = "venta_waiting_telefono"
        return f"Cliente nuevo. Telefono (o 'sin telefono'):", context

    if step == "venta_waiting_canjear_puntos":
        resp_txt = message.strip().lower()
        cliente_id = context.get("venta_cliente_id")
        cliente_nombre = context.get("venta_cliente_nombre", "Consumidor Final")
        aviso = ""
        if resp_txt in ["si", "si.", "sí", "s", "ok", "dale", "yes", "de una"]:
            from database.nimbo_db import get_saldo_puntos, canjear_puntos, PUNTOS_POR_CANJE
            saldo = get_saldo_puntos(cliente_id)
            puntos_a_usar = saldo - (saldo % PUNTOS_POR_CANJE)
            resultado = canjear_puntos(cliente_id, cliente_nombre, puntos_a_usar)
            if resultado.get("error"):
                aviso = f" No se pudo canjear: {resultado['error']}"
            else:
                aviso = f" Canjeaste {puntos_a_usar} puntos por Q{resultado['credito']} de descuento en esta compra."
        return _siguiente_paso_venta_credito(context, aviso=aviso)

    if step == "venta_waiting_usar_credito":
        resp_txt = message.strip().lower()
        context["venta_usar_credito_tienda"] = resp_txt in ["si", "si.", "sí", "s", "ok", "dale", "yes", "de una"]
        context["step"] = "venta_waiting_pago"
        aviso = " Se aplicara tu credito de tienda en el pago." if context["venta_usar_credito_tienda"] else ""
        return f"Metodo de pago? (efectivo, tarjeta, transferencia, mixto, credito):{aviso}", context

    if step == "venta_waiting_telefono":
        tel = message.strip()
        if tel.lower() in ["sin telefono", "no", "-"]:
            tel = ""
        context["venta_cliente_tel"] = tel
        context["step"] = "venta_waiting_nit"
        return "NIT del cliente (o 'CF' para consumidor final):", context

    if step == "venta_waiting_nit":
        nit = message.strip().upper()
        if nit in ["CF", "C/F", "CONSUMIDOR FINAL", "NO", "-"]:
            nit = "CF"
        context["venta_cliente_nit"] = nit
        nombre = context.get("venta_cliente_nombre", "")
        tel = context.get("venta_cliente_tel", "")
        if nombre != "Consumidor Final" and not context.get("venta_cliente_id"):
            from database.nimbo_db import crear_cliente_completo
            cliente_id, _ = crear_cliente_completo(nombre, tel, nit=nit)
            context["venta_cliente_id"] = cliente_id
        context["step"] = "venta_waiting_pago"
        return "Metodo de pago? (efectivo, tarjeta, transferencia, mixto, credito):", context

    if step == "venta_waiting_pago":
        pago = _detectar_cambio_decision(message, step) or message.strip().lower()

        _PAGO_MIXTO = ["mixto", "mixta", "combinado", "los dos", "efectivo y tarjeta"]
        _PAGO_CREDITO = ["credito", "a credito", "fiado", "al fiado"]
        _PAGO_DIRECTO = ["efectivo", "tarjeta", "transferencia"]

        # Validacion del metodo de pago: cualquier texto que no sea uno de los
        # reconocidos (o una pregunta ajena a mitad del flujo) se rechaza sin cerrar
        # la venta, en vez de registrarse tal cual como "metodo de pago" (ver
        # auditoria - este step no validaba nada antes).
        if pago not in _PAGO_MIXTO and pago not in _PAGO_CREDITO and pago not in _PAGO_DIRECTO:
            return "Por favor escribe: efectivo, tarjeta, transferencia, mixto o credito", context

        ctx = context.get("venta_ctx", {})
        cliente_id = context.get("venta_cliente_id")
        cliente_nombre = context.get("venta_cliente_nombre", "Consumidor Final")
        cliente_tel = context.get("venta_cliente_tel", "")

        from database.nimbo_db import calcular_descuento, calcular_ajuste_puntos

        descuento = calcular_descuento(
            cliente_id=cliente_id,
            productos=[{"producto_id": ctx.get("producto_id"), "subtotal": ctx["total"]}],
            total=ctx["total"]
        )
        total_final = round(ctx["total"] - descuento["monto_descuento"], 2) if descuento else ctx["total"]

        ajuste_puntos = calcular_ajuste_puntos(cliente_id, total_final)
        total_final = ajuste_puntos["total_final"]

        credito_tienda_usado = 0
        if cliente_id and context.get("venta_usar_credito_tienda"):
            from database.nimbo_db import get_credito_cliente
            credito_tienda_usado = min(get_credito_cliente(cliente_id), total_final)
            total_final = round(total_final - credito_tienda_usado, 2)

        if pago in _PAGO_MIXTO:
            context = {
                "step": "venta_waiting_pago_mixto_efectivo",
                "venta_ctx": ctx,
                "venta_cliente_id": cliente_id,
                "venta_cliente_nombre": cliente_nombre,
                "venta_cliente_tel": cliente_tel,
                "venta_total_final": total_final,
                "venta_descuento": descuento,
                "venta_ajuste_puntos": ajuste_puntos,
                "venta_credito_tienda_usado": credito_tienda_usado
            }
            return "Cuanto en efectivo?", context

        if pago in _PAGO_CREDITO:
            if not cliente_id:
                return ("Para vender a credito necesito un cliente registrado (no puede ser "
                        "'Consumidor Final'). Escribe el metodo de pago (efectivo, tarjeta, "
                        "transferencia, mixto) o vuelve a iniciar la venta con el nombre del cliente."), context
            context = {
                "step": "venta_waiting_credito_enganche",
                "venta_ctx": ctx,
                "venta_cliente_id": cliente_id,
                "venta_cliente_nombre": cliente_nombre,
                "venta_cliente_tel": cliente_tel,
                "venta_total_final": total_final,
                "venta_descuento": descuento,
                "venta_ajuste_puntos": ajuste_puntos,
                "venta_credito_tienda_usado": credito_tienda_usado
            }
            return "Cuanto de enganche paga ahora? (puede ser 0)", context

        from database.nimbo_db import formatear_nota_ajuste_puntos, consumir_credito_puntos_pendiente, ganar_puntos, usar_credito_cliente

        descripcion = f"{ctx['cantidad']}x {ctx['producto']} a Q{ctx['precio_unit']}"
        if descuento:
            descripcion += f" | Descuento {descuento['nombre']}: -Q{descuento['monto_descuento']}"
        descripcion += formatear_nota_ajuste_puntos(ajuste_puntos)

        venta_id, garantia = _registrar_venta_chat(
            cliente_id, descripcion, total_final,
            producto_id=ctx.get("producto_id"), producto_nombre=ctx.get("producto", ""),
            cliente_nombre=cliente_nombre, cliente_tel=cliente_tel,
            metodo_pago=pago, monto_tarjeta=total_final if pago == "tarjeta" else 0
        )

        puntos_info = None
        if cliente_id:
            consumir_credito_puntos_pendiente(cliente_id, venta_id)
            puntos_info = ganar_puntos(cliente_id, cliente_nombre, total_final, venta_id)
            if credito_tienda_usado:
                usar_credito_cliente(cliente_id, credito_tienda_usado)

        resumen = f"Venta #{venta_id} registrada. {ctx['cantidad']}x {ctx['producto']} = Q{ctx['total']}."
        if descuento:
            resumen += f" Descuento {descuento['nombre']} ({descuento['tipo']}): -Q{descuento['monto_descuento']}."
        if ajuste_puntos["credito_puntos"] or ajuste_puntos["descuento_oro"]:
            resumen += (f" Ajuste por puntos: -Q{ajuste_puntos['credito_puntos']}"
                        f"{f' + 5% Oro -Q' + str(ajuste_puntos['descuento_oro']) if ajuste_puntos['descuento_oro'] else ''}.")
        if credito_tienda_usado:
            resumen += f" Credito de tienda usado: -Q{credito_tienda_usado}."
        resumen += f" Total: Q{total_final}. Pago: {pago}. Cliente: {cliente_nombre}."
        if garantia:
            resumen += f" Garantia {garantia['numero']} hasta {garantia['vencimiento_propia']}."
        if puntos_info:
            resumen += (f" {cliente_nombre} gano {puntos_info['puntos_ganados']} puntos. "
                        f"Total acumulado: {puntos_info['saldo_disponible']} puntos "
                        f"(Q{puntos_info['valor_disponible']} en descuentos).")

        factura_opts = ""
        if cliente_tel:
            factura_opts = f"\nFactura para {cliente_nombre}. Como enviarla? (whatsapp, imprimir, ninguna)"
            context = {"step": "venta_waiting_factura", "venta_id": venta_id, "cliente_tel": cliente_tel, "cliente_nombre": cliente_nombre, "venta_ctx": ctx, "pago": pago, "venta_garantia": garantia}
            return resumen + factura_opts, context

        context = {}
        return resumen, context

    # Flujo de pago mixto (efectivo + tarjeta) para la venta simple del chat
    if step == "venta_waiting_pago_mixto_efectivo":
        try:
            monto_efectivo = round(float(message.strip().replace(",", "").replace("Q", "").replace("q", "").strip()), 2)
            if monto_efectivo < 0:
                raise ValueError()
        except (TypeError, ValueError):
            return "Escribe solo el monto en efectivo. Ejemplo: 50", context

        total_final = context.get("venta_total_final", 0)
        if monto_efectivo > total_final:
            return f"El monto en efectivo (Q{monto_efectivo}) no puede ser mayor al total (Q{total_final}). Cuanto en efectivo?", context

        restante = round(total_final - monto_efectivo, 2)
        context["venta_pago_efectivo"] = monto_efectivo
        context["step"] = "venta_waiting_pago_mixto_tarjeta"
        return f"Cuanto en tarjeta? (resta Q{restante})", context

    if step == "venta_waiting_pago_mixto_tarjeta":
        try:
            monto_tarjeta = round(float(message.strip().replace(",", "").replace("Q", "").replace("q", "").strip()), 2)
            if monto_tarjeta < 0:
                raise ValueError()
        except (TypeError, ValueError):
            return "Escribe solo el monto en tarjeta. Ejemplo: 45.50", context

        ctx = context.get("venta_ctx", {})
        cliente_id = context.get("venta_cliente_id")
        cliente_nombre = context.get("venta_cliente_nombre", "Consumidor Final")
        cliente_tel = context.get("venta_cliente_tel", "")
        total_final = context.get("venta_total_final", 0)
        descuento = context.get("venta_descuento")
        ajuste_puntos = context.get("venta_ajuste_puntos", {"credito_puntos": 0, "descuento_oro": 0})
        monto_efectivo = context.get("venta_pago_efectivo", 0)
        credito_tienda_usado = context.get("venta_credito_tienda_usado", 0)

        if round(monto_efectivo + monto_tarjeta, 2) != round(total_final, 2):
            return (f"Los montos no coinciden: Efectivo Q{monto_efectivo} + Tarjeta Q{monto_tarjeta} = "
                    f"Q{round(monto_efectivo + monto_tarjeta, 2)}, pero el total es Q{total_final}. "
                    f"Cuanto en tarjeta?"), context

        comision_pos = round(monto_tarjeta * 0.06, 2)

        from database.nimbo_db import formatear_nota_ajuste_puntos, consumir_credito_puntos_pendiente, ganar_puntos, usar_credito_cliente

        descripcion = f"{ctx['cantidad']}x {ctx['producto']} a Q{ctx['precio_unit']}"
        if descuento:
            descripcion += f" | Descuento {descuento['nombre']}: -Q{descuento['monto_descuento']}"
        descripcion += formatear_nota_ajuste_puntos(ajuste_puntos)
        descripcion += f" | Efectivo: Q{monto_efectivo} + Tarjeta: Q{monto_tarjeta}"

        venta_id, garantia = _registrar_venta_chat(
            cliente_id, descripcion, total_final,
            producto_id=ctx.get("producto_id"), producto_nombre=ctx.get("producto", ""),
            cliente_nombre=cliente_nombre, cliente_tel=cliente_tel,
            metodo_pago="mixto", monto_tarjeta=monto_tarjeta
        )

        puntos_info = None
        if cliente_id:
            consumir_credito_puntos_pendiente(cliente_id, venta_id)
            puntos_info = ganar_puntos(cliente_id, cliente_nombre, total_final, venta_id)
            if credito_tienda_usado:
                usar_credito_cliente(cliente_id, credito_tienda_usado)

        resumen = f"Venta #{venta_id} registrada. Efectivo Q{monto_efectivo} + Tarjeta Q{monto_tarjeta}."
        if descuento:
            resumen += f" Descuento {descuento['nombre']} ({descuento['tipo']}): -Q{descuento['monto_descuento']}."
        if ajuste_puntos["credito_puntos"] or ajuste_puntos["descuento_oro"]:
            resumen += (f" Ajuste por puntos: -Q{ajuste_puntos['credito_puntos']}"
                        f"{f' + 5% Oro -Q' + str(ajuste_puntos['descuento_oro']) if ajuste_puntos['descuento_oro'] else ''}.")
        if credito_tienda_usado:
            resumen += f" Credito de tienda usado: -Q{credito_tienda_usado}."
        resumen += f" Comision POS: Q{comision_pos} (solo sobre tarjeta). Cliente: {cliente_nombre}."
        if garantia:
            resumen += f" Garantia {garantia['numero']} hasta {garantia['vencimiento_propia']}."
        if puntos_info:
            resumen += (f" {cliente_nombre} gano {puntos_info['puntos_ganados']} puntos. "
                        f"Total acumulado: {puntos_info['saldo_disponible']} puntos "
                        f"(Q{puntos_info['valor_disponible']} en descuentos).")

        factura_opts = ""
        if cliente_tel:
            factura_opts = f"\nFactura para {cliente_nombre}. Como enviarla? (whatsapp, imprimir, ninguna)"
            context = {"step": "venta_waiting_factura", "venta_id": venta_id, "cliente_tel": cliente_tel, "cliente_nombre": cliente_nombre, "venta_ctx": ctx, "pago": "mixto", "venta_garantia": garantia}
            return resumen + factura_opts, context

        context = {}
        return resumen, context

    # Flujo de venta a credito (enganche + fecha de pago) para la venta simple del chat
    if step == "venta_waiting_credito_enganche":
        try:
            enganche = round(float(message.strip().replace(",", "").replace("Q", "").replace("q", "").strip()), 2)
            if enganche < 0:
                raise ValueError()
        except (TypeError, ValueError):
            return "Escribe solo el monto del enganche (0 si no da nada ahorita). Ejemplo: 50", context

        total_final = context.get("venta_total_final", 0)
        if enganche > total_final:
            return f"El enganche (Q{enganche}) no puede ser mayor al total (Q{total_final}). Cuanto de enganche?", context

        context["venta_credito_enganche"] = enganche
        context["step"] = "venta_waiting_credito_fecha"
        return "Para cuando queda de pagar el resto? (escribe una fecha dd/mm/aaaa o los dias, ej: 30)", context

    if step == "venta_waiting_credito_fecha":
        from datetime import datetime, timedelta
        from database.nimbo_db import (
            DIAS_VENCIMIENTO_CUENTA_DEFAULT, formatear_nota_ajuste_puntos,
            consumir_credito_puntos_pendiente, ganar_puntos, crear_cuenta_cobrar, usar_credito_cliente
        )
        txt = message.strip()
        fecha_vencimiento = None
        if txt.isdigit():
            fecha_vencimiento = (datetime.now() + timedelta(days=int(txt))).strftime("%Y-%m-%d")
        else:
            for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
                try:
                    fecha_vencimiento = datetime.strptime(txt, fmt).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
        aviso_fecha = ""
        if not fecha_vencimiento:
            fecha_vencimiento = (datetime.now() + timedelta(days=DIAS_VENCIMIENTO_CUENTA_DEFAULT)).strftime("%Y-%m-%d")
            aviso_fecha = f" No entendi la fecha, se dejo por defecto a {DIAS_VENCIMIENTO_CUENTA_DEFAULT} dias ({fecha_vencimiento})."

        ctx = context.get("venta_ctx", {})
        cliente_id = context.get("venta_cliente_id")
        cliente_nombre = context.get("venta_cliente_nombre", "Consumidor Final")
        cliente_tel = context.get("venta_cliente_tel", "")
        total_final = context.get("venta_total_final", 0)
        descuento = context.get("venta_descuento")
        ajuste_puntos = context.get("venta_ajuste_puntos", {"credito_puntos": 0, "descuento_oro": 0})
        enganche = context.get("venta_credito_enganche", 0)
        credito_tienda_usado = context.get("venta_credito_tienda_usado", 0)

        descripcion = f"{ctx['cantidad']}x {ctx['producto']} a Q{ctx['precio_unit']}"
        if descuento:
            descripcion += f" | Descuento {descuento['nombre']}: -Q{descuento['monto_descuento']}"
        descripcion += formatear_nota_ajuste_puntos(ajuste_puntos)
        descripcion += f" | Credito: enganche Q{enganche}, resto vence {fecha_vencimiento}"

        venta_id, garantia = _registrar_venta_chat(
            cliente_id, descripcion, total_final,
            producto_id=ctx.get("producto_id"), producto_nombre=ctx.get("producto", ""),
            cliente_nombre=cliente_nombre, cliente_tel=cliente_tel,
            metodo_pago="credito"
        )

        crear_cuenta_cobrar(
            cliente_id, cliente_nombre, cliente_tel,
            f"Venta #{venta_id}: {ctx['cantidad']}x {ctx['producto']}",
            total_final, monto_pagado=enganche, fecha_vencimiento=fecha_vencimiento, venta_id=venta_id
        )

        puntos_info = None
        if cliente_id:
            consumir_credito_puntos_pendiente(cliente_id, venta_id)
            puntos_info = ganar_puntos(cliente_id, cliente_nombre, total_final, venta_id)
            if credito_tienda_usado:
                usar_credito_cliente(cliente_id, credito_tienda_usado)

        pendiente = round(total_final - enganche, 2)
        resumen = f"Venta #{venta_id} registrada a credito. {ctx['cantidad']}x {ctx['producto']} = Q{ctx['total']}."
        if descuento:
            resumen += f" Descuento {descuento['nombre']} ({descuento['tipo']}): -Q{descuento['monto_descuento']}."
        if credito_tienda_usado:
            resumen += f" Credito de tienda usado: -Q{credito_tienda_usado}."
        resumen += f" Total: Q{total_final}. Enganche: Q{enganche}. Pendiente: Q{pendiente}, vence {fecha_vencimiento}."
        resumen += f" Cuenta por cobrar creada para {cliente_nombre}."
        if garantia:
            resumen += f" Garantia {garantia['numero']} hasta {garantia['vencimiento_propia']}."
        if puntos_info:
            resumen += (f" {cliente_nombre} gano {puntos_info['puntos_ganados']} puntos. "
                        f"Total acumulado: {puntos_info['saldo_disponible']} puntos "
                        f"(Q{puntos_info['valor_disponible']} en descuentos).")
        resumen += aviso_fecha

        factura_opts = ""
        if cliente_tel:
            factura_opts = f"\nFactura para {cliente_nombre}. Como enviarla? (whatsapp, imprimir, ninguna)"
            context = {"step": "venta_waiting_factura", "venta_id": venta_id, "cliente_tel": cliente_tel, "cliente_nombre": cliente_nombre, "venta_ctx": ctx, "pago": "credito", "venta_garantia": garantia}
            return resumen + factura_opts, context

        context = {}
        return resumen, context

    if step == "venta_waiting_factura":
        opcion = message.strip().lower()
        cliente_tel = context.get("cliente_tel", "")
        cliente_nombre = context.get("cliente_nombre", "")
        ctx = context.get("venta_ctx", {})
        venta_id = context.get("venta_id", "")
        pago = context.get("pago", "efectivo")
        garantia = context.get("venta_garantia")
        context = {}
        if opcion in ["whatsapp", "wa", "wapp"]:
            from services.whatsapp import enviar_factura_whatsapp
            items = [f"{ctx['cantidad']}x {ctx['producto']} a Q{ctx['precio_unit']}"]
            ok, msg = enviar_factura_whatsapp(cliente_tel, cliente_nombre, items, ctx['total'], pago, garantia=garantia)
            if ok:
                return f"Factura enviada por WhatsApp a {cliente_nombre} ({cliente_tel}).", context
            else:
                return f"No se pudo enviar por WhatsApp: {msg}. Intenta manualmente.", context
        elif opcion in ["imprimir", "print", "impresora"]:
            return "Funcion de impresion proximamente disponible.", context
        else:
            return "Listo. Venta completada sin enviar factura.", context

    # Flujo de nueva orden de servicio
    if step == "service_waiting_cliente":
        context["cliente_nombre"] = message.strip()
        context["step"] = "service_waiting_telefono"
        return "Telefono del cliente:", context

    if step == "service_waiting_telefono":
        context["cliente_telefono"] = message.strip()
        context["step"] = "service_waiting_equipo"
        return "Que equipo trajo? (ej: Licuadora, Cafetera, Olla):", context

    if step == "service_waiting_equipo":
        context["equipo"] = message.strip()
        context["step"] = "service_waiting_marca"
        return "Marca y modelo:", context

    if step == "service_waiting_marca":
        context["marca"] = message.strip()
        context["step"] = "service_waiting_problema"
        return "Cual es el problema o falla que reporta el cliente?:", context

    if step == "service_waiting_problema":
        from core.auth import listar_tecnicos
        context["problema"] = message.strip()
        tecnicos = listar_tecnicos()
        context["step"] = "service_waiting_tecnico"
        context["tecnicos_opciones"] = [
            {"id": t["Id"], "nombre": t["Nombre"] or t["Username"], "telefono": t.get("Telefono", "")}
            for t in tecnicos
        ]
        if not context["tecnicos_opciones"]:
            return "No hay tecnicos registrados todavia. Escribe 'ninguno' para crear la orden sin asignar.", context
        lista = "\n".join(f"{i+1}. {t['nombre']}" for i, t in enumerate(context["tecnicos_opciones"]))
        return f"A que tecnico se asigna esta orden?\n{lista}\n\nEscribe el numero o 'ninguno' para no asignar todavia.", context

    if step == "service_waiting_tecnico":
        from database.nimbo_db import crear_cliente, crear_orden
        from services.whatsapp import enviar_asignacion_tecnico_whatsapp
        txt = message.strip().lower()
        opciones = context.get("tecnicos_opciones", [])
        tecnico_id, tecnico_nombre, tecnico_telefono = None, "", ""
        if txt not in ("ninguno", "no", "sin asignar", "ninguna", ""):
            try:
                idx = int(txt) - 1
            except ValueError:
                return "Escribe el numero del tecnico de la lista, o 'ninguno'.", context
            if not (0 <= idx < len(opciones)):
                return "Numero invalido. Escribe el numero del tecnico de la lista, o 'ninguno'.", context
            elegido = opciones[idx]
            tecnico_id, tecnico_nombre, tecnico_telefono = elegido["id"], elegido["nombre"], elegido["telefono"]

        problema = context.get("problema", "")
        cliente_id = crear_cliente(context["cliente_nombre"], context.get("cliente_telefono", ""))
        marca_modelo = context["marca"].split(" ", 1)
        marca = marca_modelo[0]
        modelo = marca_modelo[1] if len(marca_modelo) > 1 else ""
        numero = crear_orden(cliente_id, context["equipo"], marca, modelo, problema,
                              tecnico_id=tecnico_id, tecnico_nombre=tecnico_nombre)
        ctx = {}
        resp = ("Orden " + numero + " creada. Cliente: " + context["cliente_nombre"] + ". Equipo: "
                + context["equipo"] + " " + context["marca"] + ". Problema: " + problema)
        if tecnico_nombre:
            resp += f"\nAsignada a: {tecnico_nombre}."
            if tecnico_telefono:
                ok, msg = enviar_asignacion_tecnico_whatsapp(
                    tecnico_telefono, tecnico_nombre, numero,
                    context["equipo"] + " " + context["marca"], context["cliente_nombre"], problema)
                resp += " Se le aviso por WhatsApp." if ok else f" No se pudo avisar por WhatsApp ({msg})."
            else:
                resp += " No tiene telefono registrado, no se le pudo avisar por WhatsApp."
        else:
            resp += "\nSin tecnico asignado todavia."
        resp += f"\nPuedes subir fotos del equipo en el dashboard, seccion Servicio Tecnico, orden {numero}."
        return resp, ctx

    # Flujo de entrega con garantia de reparacion (arrancado por
    # ENTREGA_GARANTIA_INICIO, ver tools/service_tool.py cambiar_estado_tool)
    if step == "servicio_waiting_dias_garantia":
        from database.nimbo_db import (
            get_orden, actualizar_estado_orden, generar_garantia_reparacion,
            DIAS_GARANTIA_REPARACION_DEFAULT
        )
        numero = context.get("servicio_numero_orden", "")
        txt = message.strip().lower()
        if txt in ["", "default", "predeterminado", "normal", "estandar", "estándar"]:
            dias = DIAS_GARANTIA_REPARACION_DEFAULT
        else:
            try:
                dias = int(txt)
                if dias < 0:
                    raise ValueError()
            except ValueError:
                return (f"Escribe solo el numero de dias de garantia, o 'default' para usar "
                        f"{DIAS_GARANTIA_REPARACION_DEFAULT} dias."), context

        orden = get_orden(numero)
        context = {}
        if not orden:
            return f"No encontre la orden {numero}.", context

        actualizar_estado_orden(numero, "ENTREGADO")
        garantia = generar_garantia_reparacion(orden, dias)

        resp = (f"Orden {numero} entregada al cliente. Garantia de reparacion {garantia['numero']} "
                f"valida hasta {garantia['fecha_vencimiento']} ({dias} dias).")

        if orden.get("ClienteTelefono"):
            from services.whatsapp import enviar_notificacion_orden
            ok, msg = enviar_notificacion_orden(
                orden["ClienteTelefono"], orden["ClienteNombre"], numero,
                orden["Equipo"] + " " + orden["Marca"], "ENTREGADO", garantia=garantia
            )
            if ok:
                resp += f" Mensaje de WhatsApp enviado a {orden['ClienteNombre']} ({orden['ClienteTelefono']})."
            else:
                resp += f" No se pudo enviar WhatsApp: {msg}. Avisa manualmente al {orden['ClienteTelefono']}."

        return resp, context

    # Flujo de nueva cotizacion
    if step == "cotizacion_waiting_cliente":
        from database.nimbo_db import buscar_cliente_completo
        nombre = message.strip()
        clientes = buscar_cliente_completo(nombre)
        if clientes:
            c = clientes[0]
            context["cot_cliente_id"] = c["Id"]
            context["cot_cliente_nombre"] = c["Nombre"]
            context["cot_cliente_tel"] = c.get("Telefono", "")
            context["step"] = "cotizacion_waiting_producto"
            return f"Cliente encontrado: {c['Nombre']}. Que producto quieres agregar? (o 'listo' para terminar)", context
        context["cot_cliente_nombre"] = nombre.title()
        context["step"] = "cotizacion_waiting_telefono"
        return f"Cliente nuevo. Telefono de {nombre.title()} (o 'sin telefono'):", context

    if step == "cotizacion_waiting_telefono":
        from database.nimbo_db import crear_cliente_completo
        tel = message.strip()
        if tel.lower() in ["sin telefono", "no", "-"]:
            tel = ""
        cliente_id, _ = crear_cliente_completo(context["cot_cliente_nombre"], tel)
        context["cot_cliente_id"] = cliente_id
        context["cot_cliente_tel"] = tel
        context["step"] = "cotizacion_waiting_producto"
        return "Que producto quieres agregar? (o 'listo' para terminar)", context

    if step == "cotizacion_waiting_producto":
        msg = message.strip().lower()
        if msg in ["listo", "ya", "no mas", "no más", "terminar", "fin"]:
            items = context.get("cot_items", [])
            if not items:
                return "Agrega al menos un producto antes de terminar.", context
            return _finalizar_cotizacion(context)
        # "mejor licuadora": el producto que iba a escribir no era el que queria,
        # se busca directo lo que dijo despues de la frase de cambio.
        busqueda = _detectar_cambio_decision(message, step) or message.strip()
        from database.nimbo_db import get_products
        productos = get_products(search=busqueda)
        if not productos:
            return f"No encontre '{busqueda}' en inventario. Intenta con otro nombre, o escribe 'listo' para terminar.", context
        if len(productos) > 1:
            context["cot_opciones"] = [{"id": p["Id"], "nombre": p["Name"], "precio": p["Price"]} for p in productos[:5]]
            context["step"] = "cotizacion_waiting_seleccion"
            lista = "\n".join([f"{i+1}. {p['nombre']} - Q{p['precio']}" for i, p in enumerate(context["cot_opciones"])])
            return f"Varios productos similares:\n{lista}\n\nEscribe el numero:", context
        p = productos[0]
        context["cot_pendiente"] = {"id": p["Id"], "nombre": p["Name"], "precio": p["Price"]}
        context["step"] = "cotizacion_waiting_cantidad"
        return f"Cuantas unidades de {p['Name']}?", context

    if step == "cotizacion_waiting_seleccion":
        try:
            idx = int(message.strip()) - 1
            opciones = context.get("cot_opciones", [])
            if 0 <= idx < len(opciones):
                context["cot_pendiente"] = opciones[idx]
                context["step"] = "cotizacion_waiting_cantidad"
                return f"Cuantas unidades de {opciones[idx]['nombre']}?", context
        except:
            pass
        return "Por favor escribe el numero del producto:", context

    if step == "cotizacion_waiting_cantidad":
        try:
            cantidad = float(message.strip())
            if cantidad <= 0:
                raise ValueError()
        except:
            return "Escribe solo la cantidad en numeros. Ejemplo: 2", context
        p = context.get("cot_pendiente", {})
        subtotal = round(p["precio"] * cantidad, 2)
        items = context.get("cot_items", [])
        items.append({
            "producto_id": p["id"], "nombre": p["nombre"],
            "cantidad": cantidad, "precio_unit": p["precio"], "subtotal": subtotal
        })
        context["cot_items"] = items
        context.pop("cot_pendiente", None)
        context["step"] = "cotizacion_waiting_producto"
        return f"Agregado: {cantidad}x {p['nombre']} = Q{subtotal}. Otro producto? (nombre o 'listo' para terminar)", context

    # Flujo de creacion manual de un combo (crear combo X). Igual que las
    # cotizaciones: agrega productos en loop hasta 'listo', luego sugiere un
    # precio con descuento (DESCUENTO_COMBO_SUGERIDO, ver database.nimbo_db) que
    # el admin puede aceptar o reemplazar por un monto propio.
    if step == "combo_crear_waiting_producto":
        msg = message.strip().lower()
        if msg in ["listo", "ya", "no mas", "no más", "terminar", "fin"]:
            items = context.get("combo_items", [])
            if not items:
                return "Agrega al menos un producto antes de terminar.", context
            from database.nimbo_db import DESCUENTO_COMBO_SUGERIDO
            suma = round(sum(i["precio_unit"] * i["cantidad"] for i in items), 2)
            precio_sugerido = round(suma - suma * DESCUENTO_COMBO_SUGERIDO, 2)
            context["combo_suma"] = suma
            context["combo_precio_sugerido"] = precio_sugerido
            context["step"] = "combo_crear_waiting_precio"
            return (f"Precio normal por separado: Q{suma}. Precio sugerido con "
                    f"{int(DESCUENTO_COMBO_SUGERIDO * 100)}% de descuento: Q{precio_sugerido}. "
                    f"Usar este precio? (si, o escribe otro monto)"), context
        from database.nimbo_db import get_products
        productos = get_products(search=message.strip())
        if not productos:
            return f"No encontre '{message.strip()}' en inventario. Intenta con otro nombre, o escribe 'listo' para terminar.", context
        if len(productos) > 1:
            context["combo_opciones"] = [{"id": p["Id"], "nombre": p["Name"], "precio": p["Price"]} for p in productos[:5]]
            context["step"] = "combo_crear_waiting_seleccion"
            lista = "\n".join([f"{i+1}. {p['nombre']} - Q{p['precio']}" for i, p in enumerate(context["combo_opciones"])])
            return f"Varios productos similares:\n{lista}\n\nEscribe el numero:", context
        p = productos[0]
        context["combo_pendiente"] = {"id": p["Id"], "nombre": p["Name"], "precio": p["Price"]}
        context["step"] = "combo_crear_waiting_cantidad"
        return f"Cuantas unidades de {p['Name']}?", context

    if step == "combo_crear_waiting_seleccion":
        try:
            idx = int(message.strip()) - 1
            opciones = context.get("combo_opciones", [])
            if 0 <= idx < len(opciones):
                context["combo_pendiente"] = opciones[idx]
                context["step"] = "combo_crear_waiting_cantidad"
                return f"Cuantas unidades de {opciones[idx]['nombre']}?", context
        except:
            pass
        return "Por favor escribe el numero del producto:", context

    if step == "combo_crear_waiting_cantidad":
        try:
            cantidad = float(message.strip())
            if cantidad <= 0:
                raise ValueError()
        except:
            return "Escribe solo la cantidad en numeros. Ejemplo: 1", context
        p = context.get("combo_pendiente", {})
        items = context.get("combo_items", [])
        items.append({"producto_id": p["id"], "nombre": p["nombre"], "cantidad": cantidad, "precio_unit": p["precio"]})
        context["combo_items"] = items
        context.pop("combo_pendiente", None)
        context["step"] = "combo_crear_waiting_producto"
        return f"Agregado: {cantidad}x {p['nombre']}. Otro producto? (nombre o 'listo' para terminar)", context

    if step == "combo_crear_waiting_precio":
        from database.nimbo_db import crear_combo
        respuesta = message.strip().lower()
        precio_sugerido = context.get("combo_precio_sugerido", 0)
        if respuesta in ["si", "si.", "sí", "s", "ok", "dale", "yes", "de una"]:
            precio_final = precio_sugerido
        else:
            try:
                precio_final = round(float(respuesta.replace("q", "").replace(",", "").strip()), 2)
                if precio_final <= 0:
                    raise ValueError()
            except:
                return "Escribe 'si' para usar el precio sugerido, o el monto que quieras usar. Ejemplo: 150", context

        nombre = context.get("combo_nombre", "Combo")
        items = context.get("combo_items", [])
        descripcion = "Incluye: " + ", ".join(f"{i['cantidad']}x {i['nombre']}" for i in items)
        combo_id = crear_combo(nombre, descripcion, precio_final, [
            {"producto_id": i["producto_id"], "producto_nombre": i["nombre"], "cantidad": i["cantidad"]}
            for i in items
        ])
        suma = context.get("combo_suma", 0)
        context = {}
        resp = f"Combo '{nombre}' creado (#{combo_id}). {descripcion}. Precio: Q{precio_final}"
        ahorro = round(suma - precio_final, 2)
        if ahorro > 0:
            resp += f" (ahorro de Q{ahorro} vs Q{suma} por separado)"
        resp += f". Para venderlo: 'vender combo {nombre}'"
        return resp, context

    # Flujo de reembolso (arrancado por REEMBOLSO_INICIO, ver tools/reembolso_tool.py
    # y el marcador manejado en _intentar_detectar). Solo admin (categoria
    # "reembolso" no esta en CATEGORIAS_EMPLEADO/CATEGORIAS_TECNICO de
    # core/action_engine.py).
    if step == "reembolso_waiting_tipo":
        tipo_txt = message.strip().lower()
        disponible = context.get("reembolso_disponible", 0)
        if tipo_txt in ["total", "todo", "completo"]:
            context["reembolso_tipo"] = "TOTAL"
            context["reembolso_monto"] = disponible
            context["step"] = "reembolso_waiting_metodo"
            return f"Reembolso total: Q{disponible}. Como se devuelve? (efectivo/tarjeta/credito tienda)", context
        if tipo_txt in ["parcial", "parte"]:
            context["reembolso_tipo"] = "PARCIAL"
            context["step"] = "reembolso_waiting_monto"
            return f"Cuanto quieres devolver? (maximo Q{disponible})", context
        return "Por favor escribe: total o parcial", context

    if step == "reembolso_waiting_monto":
        if _detectar_cambio_decision(message, step):
            # "mejor total": se salta la pregunta del monto parcial (mismo efecto
            # que responder "total" en reembolso_waiting_tipo, ver esa rama arriba).
            disponible = context.get("reembolso_disponible", 0)
            context["reembolso_tipo"] = "TOTAL"
            context["reembolso_monto"] = disponible
            context["step"] = "reembolso_waiting_metodo"
            return f"Entendido, reembolso total: Q{disponible}. Como se devuelve? (efectivo/tarjeta/credito tienda)", context
        try:
            monto = round(float(message.strip().replace(",", "").replace("Q", "").replace("q", "").strip()), 2)
            if monto <= 0:
                raise ValueError()
        except (TypeError, ValueError):
            return "Escribe solo el monto a devolver. Ejemplo: 50", context
        disponible = context.get("reembolso_disponible", 0)
        if monto > disponible:
            return f"El monto (Q{monto}) no puede ser mayor a lo disponible para reembolsar (Q{disponible}). Cuanto quieres devolver?", context
        context["reembolso_monto"] = monto
        context["step"] = "reembolso_waiting_metodo"
        return f"Reembolso parcial: Q{monto}. Como se devuelve? (efectivo/tarjeta/credito tienda)", context

    if step == "reembolso_waiting_metodo":
        metodo_map = {"efectivo": "efectivo", "tarjeta": "tarjeta", "credito tienda": "credito_tienda",
                      "credito de tienda": "credito_tienda", "credito": "credito_tienda"}
        respuesta = _detectar_cambio_decision(message, step) or message.strip().lower()
        metodo = metodo_map.get(respuesta)
        if not metodo:
            return "Por favor escribe: efectivo, tarjeta o credito tienda", context

        from database.nimbo_db import procesar_reembolso, get_turno_abierto
        venta_id = context.get("reembolso_venta_id")
        tipo = context.get("reembolso_tipo", "TOTAL")
        monto = context.get("reembolso_monto", 0)

        turno = get_turno_abierto()
        turno_id = turno["Id"] if turno else None

        resultado = procesar_reembolso(venta_id, tipo, monto, metodo, turno_id=turno_id)
        if resultado.get("error"):
            return resultado["error"], {}

        resp = f"Reembolso {resultado['numero']} procesado ({tipo.lower()}): Q{resultado['monto']} via {metodo}."
        if resultado["revertidos"]:
            resp += "\nStock repuesto: " + ", ".join(f"{it['cantidad']}x {it['nombre']}" for it in resultado["revertidos"])
        if resultado["no_encontrados"]:
            resp += "\nNo se pudo identificar en inventario (revisa el stock manualmente): " + ", ".join(resultado["no_encontrados"])
        if metodo == "tarjeta":
            resp += "\nEstado: PENDIENTE - procesa la devolucion con el POS fisico."
        elif metodo == "credito_tienda":
            resp += "\nEl monto se sumo como credito en tienda para el cliente."
        elif turno_id:
            resp += "\nSe descuenta de la caja del turno activo."
        else:
            resp += "\nAviso: no hay ningun turno de caja abierto, el efectivo no se registro contra ninguna caja."
        return resp, {}

    # Flujo de cambio de producto (arrancado por CAMBIO_PRODUCTO_INICIO)
    if step == "cambio_waiting_seleccion_viejo":
        try:
            idx = int(message.strip()) - 1
            opciones = context.get("cambio_opciones_viejo", [])
            if 0 <= idx < len(opciones):
                op = opciones[idx]
                context["cambio_producto_viejo_nombre"] = op["nombre"]
                context["cambio_producto_viejo_cantidad"] = op["cantidad"]
                context["step"] = "cambio_waiting_producto_nuevo"
                return f"Cambiando {op['cantidad']}x {op['nombre']}. Que producto nuevo se lleva?", context
        except:
            pass
        return "Por favor escribe el numero del producto:", context

    if step == "cambio_waiting_producto_nuevo":
        from database.nimbo_db import get_products
        productos = get_products(search=message.strip())
        if not productos:
            return f"No encontre '{message.strip()}' en inventario. Intenta con otro nombre:", context
        if len(productos) > 1:
            context["cambio_opciones_nuevo"] = [{"id": p["Id"], "nombre": p["Name"], "precio": p["Price"]} for p in productos[:5]]
            context["step"] = "cambio_waiting_seleccion_nuevo"
            lista = "\n".join(f"{i+1}. {p['nombre']} - Q{p['precio']}" for i, p in enumerate(context["cambio_opciones_nuevo"]))
            return f"Varios productos similares:\n{lista}\n\nEscribe el numero:", context
        p = productos[0]
        return _procesar_cambio_confirmar(context, p["Id"], p["Name"], p["Price"])

    if step == "cambio_waiting_seleccion_nuevo":
        try:
            idx = int(message.strip()) - 1
            opciones = context.get("cambio_opciones_nuevo", [])
            if 0 <= idx < len(opciones):
                op = opciones[idx]
                return _procesar_cambio_confirmar(context, op["id"], op["nombre"], op["precio"])
        except:
            pass
        return "Por favor escribe el numero del producto:", context

    if step == "cambio_waiting_confirmar":
        if message.strip().lower() not in ["si", "si.", "sí", "s", "ok", "dale", "yes", "de una"]:
            return "Cambio cancelado.", {}
        return _finalizar_cambio(context, "efectivo")

    if step == "cambio_waiting_metodo_diferencia":
        metodo_map = {"efectivo": "efectivo", "tarjeta": "tarjeta", "credito tienda": "credito_tienda",
                      "credito de tienda": "credito_tienda", "credito": "credito_tienda"}
        respuesta = _detectar_cambio_decision(message, step) or message.strip().lower()
        metodo = metodo_map.get(respuesta)
        if not metodo:
            return "Por favor escribe: efectivo, tarjeta o credito tienda", context
        return _finalizar_cambio(context, metodo)

    # Confirmacion del fondo sugerido (igual al cierre del turno anterior)
    if step == "caja_abrir_confirmar_sugerido":
        resp = message.strip().lower()
        if resp in ["si", "si.", "sí", "s", "ok", "dale", "yes", "de una"]:
            from database.nimbo_db import abrir_turno
            from flask_login import current_user
            fondo = context.get("caja_fondo_sugerido", {})
            context = {}
            turno_id, total = abrir_turno(int(current_user.id), current_user.nombre, fondo)
            detalle = ", ".join([f"{v}xQ{k}" for k, v in fondo.items() if int(v) > 0])
            return f"Turno de caja abierto (#{turno_id}). Fondo inicial: Q{total} ({detalle}).", context
        from database.nimbo_db import DENOMINACIONES
        context = {"step": "caja_abrir_denom", "caja_idx": 0, "caja_fondo": {}}
        return f"Cuantos billetes/monedas de Q{DENOMINACIONES[0]} hay?", context

    # Confirmacion del fondo sugerido como monto total (sin desglose por denominacion)
    if step == "caja_abrir_confirmar_sugerido_total":
        resp = message.strip().lower()
        if resp in ["si", "si.", "sí", "s", "ok", "dale", "yes", "de una"]:
            from database.nimbo_db import abrir_turno_simple
            from flask_login import current_user
            total = context.get("caja_fondo_sugerido_total", 0)
            context = {}
            turno_id, total = abrir_turno_simple(int(current_user.id), current_user.nombre, total)
            return f"Turno de caja abierto (#{turno_id}). Fondo inicial: Q{total}.", context
        from database.nimbo_db import DENOMINACIONES
        context = {"step": "caja_abrir_denom", "caja_idx": 0, "caja_fondo": {}}
        return f"Cuantos billetes/monedas de Q{DENOMINACIONES[0]} hay?", context

    # Flujo de apertura de turno de caja (fondo inicial por denominacion)
    if step == "caja_abrir_denom":
        from database.nimbo_db import DENOMINACIONES, abrir_turno
        try:
            cantidad = int(message.strip())
            if cantidad < 0:
                raise ValueError()
        except:
            return "Escribe solo un numero (puede ser 0). Ejemplo: 5", context
        idx = context.get("caja_idx", 0)
        denom = DENOMINACIONES[idx]
        fondo = context.get("caja_fondo", {})
        fondo[str(denom)] = cantidad
        context["caja_fondo"] = fondo
        idx += 1
        if idx < len(DENOMINACIONES):
            context["caja_idx"] = idx
            return f"Cuantos billetes/monedas de Q{DENOMINACIONES[idx]} hay?", context
        from flask_login import current_user
        turno_id, total = abrir_turno(int(current_user.id), current_user.nombre, fondo)
        context = {}
        detalle = ", ".join([f"{v}xQ{k}" for k, v in fondo.items() if int(v) > 0])
        return f"Turno de caja abierto (#{turno_id}). Fondo inicial: Q{total} ({detalle}).", context

    # Flujo de cierre de turno de caja: 1) cuanto hay realmente (total, sin desglose
    # obligatorio) 2) cuanto se retira para la caja fuerte. El resto queda como fondo
    # sugerido para el turno de manana (ver cerrar_turno/get_fondo_sugerido).
    if step == "caja_cerrar_total":
        from database.nimbo_db import get_turno_abierto
        try:
            contado = round(float(message.strip().replace(",", "")), 2)
            if contado < 0:
                raise ValueError()
        except:
            return "Escribe solo el monto total que hay en caja. Ejemplo: 850", context
        turno = get_turno_abierto()
        if not turno:
            context = {}
            return "No encontre el turno abierto.", context
        diferencia = round(contado - turno["EfectivoEsperado"], 2)
        if diferencia == 0:
            msg_dif = "Cuadra exacto, sin diferencias."
        elif diferencia > 0:
            msg_dif = f"Sobran Q{diferencia} respecto a lo esperado."
        else:
            msg_dif = f"ALERTA: faltan Q{abs(diferencia)} respecto a lo esperado."
        context = {"step": "caja_cerrar_retiro", "caja_contado": contado}
        return f"{msg_dif}\nCuanto vas a retirar para la caja fuerte? (escribe 0 si no vas a retirar nada)", context

    if step == "caja_cerrar_retiro":
        from database.nimbo_db import cerrar_turno, get_turno_abierto
        try:
            retiro = round(float(message.strip().replace(",", "")), 2)
            if retiro < 0:
                raise ValueError()
        except:
            return "Escribe solo el monto a retirar para la caja fuerte. Ejemplo: 500 (o 0 si no retiras nada)", context
        contado = context.get("caja_contado", 0)
        if retiro > contado:
            return f"El retiro (Q{retiro}) no puede ser mayor a lo contado en caja (Q{contado}). Cuanto vas a retirar?", context
        turno = get_turno_abierto()
        if not turno:
            context = {}
            return "No encontre el turno abierto.", context
        resultado = cerrar_turno(turno["Id"], contado, retiro)
        context = {}
        diferencia = resultado["Diferencia"]
        if diferencia == 0:
            msg_dif = "Cuadra exacto, sin diferencias."
        elif diferencia > 0:
            msg_dif = f"Sobran Q{diferencia} respecto a lo esperado."
        else:
            msg_dif = f"Faltan Q{abs(diferencia)} respecto a lo esperado."
        resp = f"Turno #{turno['Id']} cerrado.\n"
        resp += f"Esperado: Q{resultado['EfectivoEsperado']} | Contado: Q{resultado['EfectivoContado']}\n"
        resp += f"{msg_dif}\n"
        resp += f"Ventas del turno: Q{resultado['TotalVentas']} (Efectivo Q{resultado['TotalEfectivo']}, Tarjeta Q{resultado['TotalTarjeta']}, Mixto Q{resultado['TotalMixto']})\n"
        if retiro > 0:
            resp += f"Retiro a caja fuerte: Q{retiro} (acumulado en caja fuerte: Q{resultado['CajaFuerteAcumulada']})\n"
        resp += f"Fondo para manana: Q{resultado['FondoSugerido']}"
        return resp, context

    # Flujo de anulacion de turno (admin-only, ver INTENTS_SOLO_ADMIN en action_engine.py)
    if step == "caja_anular_waiting_motivo":
        from database.nimbo_db import get_turno_abierto, anular_turno
        from flask_login import current_user
        motivo = message.strip()
        if not motivo:
            return "Escribe el motivo de la anulacion.", context
        turno = get_turno_abierto()
        context = {}
        if not turno:
            return "No hay ningun turno de caja abierto para anular.", context
        resultado = anular_turno(turno["Id"], motivo, current_user.nombre)
        aviso = ""
        if resultado.get("ventas_no_revertidas"):
            aviso = (f" Atencion: este turno ya tenia Q{resultado['ventas_no_revertidas']} en ventas "
                     f"registradas; esas ventas y el stock descontado NO se revierten automaticamente.")
        return f"Turno #{turno['Id']} anulado. Motivo: {motivo}.{aviso}", context

    # Si hay un flujo activo de creacion de producto
    if step == "waiting_price":
        try:
            price = float(message.strip().replace("Q","").replace("q","").strip())
            context["price"] = price
            context["step"] = "waiting_cost"
            return f"¿Cuál es el costo de {context['product_name']}?", context
        except:
            return "Por favor escribe solo el precio en números. Ej: 25", context

    if step == "waiting_cost":
        try:
            cost = float(message.strip().replace("Q","").replace("q","").strip())
            from database.nimbo_db import nimbo_connect, add_stock
            name = context["product_name"].title()
            price = context["price"]
            qty = context.get("quantity", 0)
            conn = nimbo_connect()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Producto (Nombre, Codigo, Precio, Costo, Activo) VALUES (?, ?, ?, ?, 1)",
                (name, "", price, cost)
            )
            conn.commit()
            product_id = cur.lastrowid
            conn.close()
            if qty > 0:
                add_stock(product_id, qty)
            context = {}
            return f"Producto '{name}' creado con {qty} unidades. Precio: Q{price}, Costo: Q{cost}.", context
        except Exception as e:
            context = {}
            return f"Error al crear producto: {e}", context

    # Flujo de creacion de producto explicita por chat ("agregar/nuevo/crear
    # producto X precio N ..."), arrancado por PRODUCTO_NUEVO_INICIO: mas arriba.
    # Distinto del flujo waiting_price/waiting_cost de arriba (ese es un fallback
    # de "agregar N [producto]" cuando el producto no existe, no un comando de
    # creacion explicita) - se mantienen separados para no mezclar los dos gatillos.
    if step == "producto_waiting_precio":
        try:
            precio = float(message.strip().replace("Q","").replace("q","").strip())
        except:
            return "Por favor escribe solo el precio en números. Ej: 95", context
        context["prod_precio"] = precio
        context["step"] = "producto_waiting_costo"
        return f"¿Cuál es el costo de {context['prod_nombre']}?", context

    if step == "producto_waiting_costo":
        try:
            costo = float(message.strip().replace("Q","").replace("q","").strip())
        except:
            return "Por favor escribe solo el costo en números. Ej: 40", context
        from tools.inventory_tool import _crear_producto_directo
        nombre = context["prod_nombre"].title()
        precio = context["prod_precio"]
        cantidad = context.get("prod_cantidad", 0)
        codigo = context.get("prod_codigo", "")
        context = {}
        return _crear_producto_directo(nombre, precio, costo, cantidad, codigo=codigo), context

    # Flujo de escaneo de codigo de barras en el chat (arrancado por
    # BARCODE_INICIO:/CODIGO_NO_ENCONTRADO_INICIO: mas arriba, ver
    # tools/inventory_tool.py escanear_codigo_tool).
    if step == "barcode_waiting_accion":
        # Si el mensaje que llega ahora es EN SI MISMO un codigo de barras (el
        # cajero escaneo otro producto antes de contestar la pregunta anterior -
        # muy comun escaneando varios articulos seguidos), se trata como un
        # escaneo nuevo en vez de intentar interpretarlo como la cantidad a
        # vender del producto anterior (un codigo numerico de 13 digitos, leido
        # como cantidad, siempre da "stock insuficiente" - ese era el bug).
        from core.detectors.inventory_detector import es_codigo_barras, normalize as _normalize_barcode
        if es_codigo_barras(message):
            from tools.inventory_tool import escanear_codigo_tool
            nuevo = _iniciar_flujo_barcode(escanear_codigo_tool(_normalize_barcode(message)))
            if nuevo:
                return nuevo

        resp = message.strip().lower()
        nombre = context["barcode_nombre"]
        producto_id = context["barcode_producto_id"]
        precio = context["barcode_precio"]
        stock = context["barcode_stock"]

        if resp in ("no", "n"):
            return f"De acuerdo, no se vendio nada de {nombre}.", {}

        if resp in ("si", "sí", "s"):
            cantidad = 1
        else:
            try:
                cantidad = int(float(resp.replace(",", ".")))
            except ValueError:
                return "Responde 'si', 'no', o escribe la cantidad a vender.", context
            if cantidad <= 0:
                return "La cantidad debe ser mayor a 0.", context

        if stock < cantidad:
            return f"Stock insuficiente. {nombre} solo tiene {int(stock)} unidades.", {}

        from database.nimbo_db import remove_stock
        remove_stock(producto_id, cantidad, razon="Venta")
        total = precio * cantidad
        context = {
            "step": "venta_waiting_nombre",
            "venta_ctx": {
                "cantidad": cantidad,
                "producto": nombre,
                "precio_unit": precio,
                "total": total,
                "producto_id": producto_id
            }
        }
        return f"Venta: {cantidad}x {nombre} = Q{total}. Nombre del cliente (o 'sin nombre'):", context

    if step == "barcode_waiting_crear":
        # Mismo caso que en barcode_waiting_accion: si en vez de responder
        # si/no el usuario escanea otro codigo, se arranca el escaneo nuevo.
        from core.detectors.inventory_detector import es_codigo_barras, normalize as _normalize_barcode
        if es_codigo_barras(message):
            from tools.inventory_tool import escanear_codigo_tool
            nuevo = _iniciar_flujo_barcode(escanear_codigo_tool(_normalize_barcode(message)))
            if nuevo:
                return nuevo

        resp = message.strip().lower()
        codigo = context.get("barcode_codigo_nuevo", "")
        if resp in ("no", "n"):
            return "De acuerdo, no se agrego nada.", {}
        if resp in ("si", "sí", "s"):
            context = {"step": "barcode_waiting_nombre_nuevo", "barcode_codigo_nuevo": codigo}
            return "¿Cómo se llama el producto?", context
        return "Responde 'si' o 'no'.", context

    if step == "barcode_waiting_nombre_nuevo":
        nombre = message.strip()
        if not nombre:
            return "Escribe el nombre del producto.", context
        codigo = context.get("barcode_codigo_nuevo", "")
        context = {"step": "producto_waiting_precio", "prod_nombre": nombre, "prod_cantidad": 0, "prod_codigo": codigo}
        return f"¿A qué precio se vende {nombre}?", context

    # Red de seguridad: un step "videofoto_*" que llego hasta aca (sin matchear
    # NINGUNO de los bloques `if step == "videofoto_..."` de arriba) es un step
    # viejo/desconocido - tipicamente un context.session con un nombre de step
    # que ya no existe (ej. esto paso literalmente al renombrar
    # videofoto_waiting_optimizar a videofoto_waiting_cuantos_prompts: una
    # sesion de chat que ya estaba a mitad de ese step se quedaba con ese
    # nombre viejo en su cookie de sesion). Sin este chequeo, el mensaje caia
    # en silencio al pipeline generico de abajo (deteccion de intents ->
    # Ollama) CON el context viejo intacto - el usuario nunca volvia a ver el
    # step nuevo ("¿quieres los 3 prompts o solo uno?"), el motor determinista
    # de core/video_prompt_engine.py nunca se llegaba a invocar, y las
    # respuestas se sentian "genericas" porque en realidad NO eran parte del
    # flujo de video en absoluto. Se limpia el context en vez de intentar
    # adivinar a que step nuevo deberia mapear el viejo.
    if step and step.startswith("videofoto_"):
        return "Parece que la sesión del video quedó en un estado anterior. Empecemos de nuevo - sube la foto otra vez.", {}

    # Intento 1 y 2: deteccion directa + traduccion via Ollama
    detectado = _intentar_detectar(message, role, context, contexto_historial)
    if detectado:
        return detectado

    # Intento 3: el mensaje no coincidio con ningun intent. Antes de caer al
    # fallback final, se analiza si es una intencion de negocio expresada de
    # forma vaga (ver CLARIFICACION_PROMPT). Si Ollama genera una pregunta de
    # clarificacion, se guarda el mensaje original en el contexto y se le
    # pregunta al usuario.
    pregunta = _analizar_intencion_vaga(message, contexto_historial)
    if pregunta:
        context = {"step": "clarificando", "original_message": message}
        return pregunta, context

    # Intento 4: fallback final - Ollama directo (OpenClaw ya no es automatico,
    # queda solo como opcion manual en el dashboard, ver app.py /api/openclaw/chat).
    if role != "admin":
        return ("No entendi esa instruccion. Si necesitas ayuda con algo fuera de "
                "inventario, ventas o clientes, contacta a un administrador."), context
    return _fallback_ollama(message, contexto_historial), context
