import tools
from core.action_engine import ActionEngine
from core.chat_context import obtener_historial_reciente, resumen_texto
from openclaw_bridge import send_to_openclaw
from google import genai
import os
import re

_engine = ActionEngine()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_gemini = None
if GEMINI_API_KEY:
    _gemini = genai.Client(api_key=GEMINI_API_KEY)

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
    if not _gemini:
        return None
    try:
        prompt = TRANSLATE_PROMPT.format(message=message)
        if contexto:
            prompt = (
                "Contexto de conversacion reciente (puede ser de dias anteriores):\n"
                f"{contexto}\n\n{prompt}"
            )
        r = _gemini.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        cmd = r.text.strip().lower()
        if cmd == "ninguno" or not cmd:
            return None
        return cmd
    except:
        return None


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
    """Le pregunta a Gemini si el mensaje es una intencion de negocio expresada de forma vaga.
    Retorna la pregunta de clarificacion en espanol, o None si no aplica."""
    if not _gemini:
        return None
    try:
        prompt = CLARIFICACION_PROMPT.format(message=message)
        if contexto:
            prompt = (
                "Contexto de conversacion reciente (puede ser de dias anteriores):\n"
                f"{contexto}\n\n{prompt}"
            )
        r = _gemini.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        texto = r.text.strip()
        if not texto or texto.upper() == "NINGUNO":
            return None
        return texto
    except:
        return None


def _intentar_detectar(message: str, role: str, context: dict, contexto_historial: str = ""):
    """Corre deteccion directa (detectores) y, si falla, traduccion via Gemini.
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
            from database.aronium import DIAS_GARANTIA_REPARACION_DEFAULT
            context = {"step": "servicio_waiting_dias_garantia", "servicio_numero_orden": numero_orden}
            return (f"Cuantos dias de garantia tiene esta reparacion? "
                    f"(por defecto {DIAS_GARANTIA_REPARACION_DEFAULT}, escribe el numero o 'default')"), context

        if str(result).startswith("COTIZACION_INICIO:"):
            cliente_nombre = str(result).replace("COTIZACION_INICIO:", "").strip()
            if cliente_nombre:
                from database.aronium import buscar_cliente_completo
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

        if str(result).startswith("COMBO_INICIO:"):
            nombre_combo = str(result).replace("COMBO_INICIO:", "").strip()
            context = {"step": "combo_crear_waiting_producto", "combo_nombre": nombre_combo, "combo_items": []}
            return f"Creando combo '{nombre_combo}'. Que producto quieres agregar? (o 'listo' para terminar)", context

        if str(result) == "CAJA_ABRIR_INICIO":
            from database.aronium import DENOMINACIONES, get_ultimo_cierre_denominaciones, get_fondo_sugerido
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
            from database.aronium import get_turno_abierto
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
            from database.aronium import get_turno_abierto, anular_turno
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


def _registrar_venta_chat(cliente_id, descripcion, total, producto_id=None, producto_nombre="",
                           cliente_nombre="Consumidor Final", cliente_tel=""):
    """Inserta la Venta del flujo de venta simple del chat (un solo producto),
    actualiza la ultima compra del cliente y genera la garantia del producto
    (ver database.aronium.generar_garantia_venta). Usado tanto por el pago de un
    solo metodo como por el pago mixto (efectivo + tarjeta)."""
    from database.aronium import nimbo_connect, generar_garantia_venta
    from datetime import datetime
    conn = nimbo_connect()
    cur = conn.cursor()
    now = datetime.now()
    mes = now.month
    trimestre = (mes - 1) // 3 + 1
    anio = now.year
    cur.execute(
        "INSERT INTO Venta (ClienteId, Descripcion, Total, Mes, Trimestre, Anio) VALUES (?,?,?,?,?,?)",
        (cliente_id, descripcion, total, mes, trimestre, anio)
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
    from database.aronium import crear_cotizacion, calcular_descuento
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


def send(message: str, context: dict = None, role: str = "admin") -> tuple:
    """
    Retorna (respuesta, context_actualizado)
    context es un dict con el estado de la conversacion
    role controla que categorias de intent puede ejecutar el usuario (admin | empleado)
    """
    if context is None:
        context = {}

    # Contexto de conversaciones anteriores (hasta 10 mensajes / ~500 tokens, ver
    # core/chat_context.py). Se calcula una sola vez por mensaje y se reutiliza en
    # todos los llamados a Gemini/OpenClaw de esta funcion, para que Nimbo entienda
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
        return send_to_openclaw(combinado, contexto_historial), context

    # Flujo de cliente nuevo (arrancado por CLIENTE_NUEVO_INICIO, ver
    # tools/cliente_tool.py nuevo_cliente_tool) - pregunta el grupo antes de crear.
    if step == "cliente_waiting_grupo":
        from database.aronium import crear_cliente_completo, set_grupo_cliente, GRUPOS_CLIENTE
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
        from database.aronium import agregar_pago_fijo
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

    # Flujo de descripcion de producto
    if step == "desc_waiting_descripcion":
        descripcion = message.strip()
        context["step"] = "desc_waiting_corta"
        context["desc_descripcion"] = descripcion
        return f"Descripcion corta (max 100 caracteres, para WhatsApp/redes):", context

    if step == "desc_waiting_corta":
        from database.aronium import set_descripcion_producto
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
        from google import genai as _genai
        import os
        objetivo = message.strip()
        producto = context.get("script_producto", "")
        tono = context.get("script_tono", "profesional")
        duracion = context.get("script_duracion", "30 segundos")
        red = context.get("script_red", "Instagram")
        context = {}
        
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        if not gemini_key:
            return "Gemini no configurado.", context
        
        cliente = _genai.Client(api_key=gemini_key)
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
        
        r = cliente.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
        return r.text, context

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
        from google import genai as _genai
        import os
        tipos = message.strip()
        frecuencia = context.get("prog_frecuencia", "1")
        horas = context.get("prog_horas", "12pm")
        context = {}
        
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        if not gemini_key:
            return "Gemini no configurado.", context
        
        cliente = _genai.Client(api_key=gemini_key)
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
        
        r = cliente.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
        return r.text, context

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
        from database.aronium import agregar_contacto_proveedor
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
        from database.aronium import DIAS_VENCIMIENTO_PAGAR_DEFAULT, crear_cuenta_pagar
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

                from database.aronium import get_product_by_id, remove_stock
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
        from database.aronium import buscar_cliente_completo
        clientes = buscar_cliente_completo(message.strip())
        if clientes:
            context["venta_cliente_id"] = clientes[0]["Id"]
            context["venta_cliente_nombre"] = clientes[0]["Nombre"]
            from database.aronium import get_saldo_puntos, puntos_a_quetzales, PUNTOS_POR_CANJE
            saldo = get_saldo_puntos(clientes[0]["Id"])
            if saldo >= PUNTOS_POR_CANJE:
                context["step"] = "venta_waiting_canjear_puntos"
                valor = puntos_a_quetzales(saldo)
                return (f"Cliente encontrado: {clientes[0]['Nombre']}. Tiene {saldo} puntos disponibles "
                        f"(Q{valor} en descuentos). Quiere canjearlos en esta compra? (si/no)"), context
            context["step"] = "venta_waiting_pago"
            return f"Cliente encontrado: {clientes[0]['Nombre']}. Metodo de pago? (efectivo, tarjeta, transferencia, mixto, credito):", context
        context["venta_cliente_nombre"] = message.strip().title()
        context["step"] = "venta_waiting_telefono"
        return f"Cliente nuevo. Telefono (o 'sin telefono'):", context

    if step == "venta_waiting_canjear_puntos":
        resp_txt = message.strip().lower()
        cliente_id = context.get("venta_cliente_id")
        cliente_nombre = context.get("venta_cliente_nombre", "Consumidor Final")
        aviso = ""
        if resp_txt in ["si", "si.", "sí", "s", "ok", "dale", "yes", "de una"]:
            from database.aronium import get_saldo_puntos, canjear_puntos, PUNTOS_POR_CANJE
            saldo = get_saldo_puntos(cliente_id)
            puntos_a_usar = saldo - (saldo % PUNTOS_POR_CANJE)
            resultado = canjear_puntos(cliente_id, cliente_nombre, puntos_a_usar)
            if resultado.get("error"):
                aviso = f" No se pudo canjear: {resultado['error']}"
            else:
                aviso = f" Canjeaste {puntos_a_usar} puntos por Q{resultado['credito']} de descuento en esta compra."
        context["step"] = "venta_waiting_pago"
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
            from database.aronium import crear_cliente_completo
            cliente_id, _ = crear_cliente_completo(nombre, tel, nit=nit)
            context["venta_cliente_id"] = cliente_id
        context["step"] = "venta_waiting_pago"
        return "Metodo de pago? (efectivo, tarjeta, transferencia, mixto, credito):", context

    if step == "venta_waiting_pago":
        pago = message.strip().lower()
        ctx = context.get("venta_ctx", {})
        cliente_id = context.get("venta_cliente_id")
        cliente_nombre = context.get("venta_cliente_nombre", "Consumidor Final")
        cliente_tel = context.get("venta_cliente_tel", "")

        from database.aronium import calcular_descuento, calcular_ajuste_puntos

        descuento = calcular_descuento(
            cliente_id=cliente_id,
            productos=[{"producto_id": ctx.get("producto_id"), "subtotal": ctx["total"]}],
            total=ctx["total"]
        )
        total_final = round(ctx["total"] - descuento["monto_descuento"], 2) if descuento else ctx["total"]

        ajuste_puntos = calcular_ajuste_puntos(cliente_id, total_final)
        total_final = ajuste_puntos["total_final"]

        if pago in ["mixto", "mixta", "combinado", "los dos", "efectivo y tarjeta"]:
            context = {
                "step": "venta_waiting_pago_mixto_efectivo",
                "venta_ctx": ctx,
                "venta_cliente_id": cliente_id,
                "venta_cliente_nombre": cliente_nombre,
                "venta_cliente_tel": cliente_tel,
                "venta_total_final": total_final,
                "venta_descuento": descuento,
                "venta_ajuste_puntos": ajuste_puntos
            }
            return "Cuanto en efectivo?", context

        if pago in ["credito", "a credito", "fiado", "al fiado"]:
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
                "venta_ajuste_puntos": ajuste_puntos
            }
            return "Cuanto de enganche paga ahora? (puede ser 0)", context

        from database.aronium import formatear_nota_ajuste_puntos, consumir_credito_puntos_pendiente, ganar_puntos

        descripcion = f"{ctx['cantidad']}x {ctx['producto']} a Q{ctx['precio_unit']}"
        if descuento:
            descripcion += f" | Descuento {descuento['nombre']}: -Q{descuento['monto_descuento']}"
        descripcion += formatear_nota_ajuste_puntos(ajuste_puntos)

        venta_id, garantia = _registrar_venta_chat(
            cliente_id, descripcion, total_final,
            producto_id=ctx.get("producto_id"), producto_nombre=ctx.get("producto", ""),
            cliente_nombre=cliente_nombre, cliente_tel=cliente_tel
        )

        puntos_info = None
        if cliente_id:
            consumir_credito_puntos_pendiente(cliente_id, venta_id)
            puntos_info = ganar_puntos(cliente_id, cliente_nombre, total_final, venta_id)

        resumen = f"Venta #{venta_id} registrada. {ctx['cantidad']}x {ctx['producto']} = Q{ctx['total']}."
        if descuento:
            resumen += f" Descuento {descuento['nombre']} ({descuento['tipo']}): -Q{descuento['monto_descuento']}."
        if ajuste_puntos["credito_puntos"] or ajuste_puntos["descuento_oro"]:
            resumen += (f" Ajuste por puntos: -Q{ajuste_puntos['credito_puntos']}"
                        f"{f' + 5% Oro -Q' + str(ajuste_puntos['descuento_oro']) if ajuste_puntos['descuento_oro'] else ''}.")
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

        if round(monto_efectivo + monto_tarjeta, 2) != round(total_final, 2):
            return (f"Los montos no coinciden: Efectivo Q{monto_efectivo} + Tarjeta Q{monto_tarjeta} = "
                    f"Q{round(monto_efectivo + monto_tarjeta, 2)}, pero el total es Q{total_final}. "
                    f"Cuanto en tarjeta?"), context

        comision_pos = round(monto_tarjeta * 0.06, 2)

        from database.aronium import formatear_nota_ajuste_puntos, consumir_credito_puntos_pendiente, ganar_puntos

        descripcion = f"{ctx['cantidad']}x {ctx['producto']} a Q{ctx['precio_unit']}"
        if descuento:
            descripcion += f" | Descuento {descuento['nombre']}: -Q{descuento['monto_descuento']}"
        descripcion += formatear_nota_ajuste_puntos(ajuste_puntos)
        descripcion += f" | Efectivo: Q{monto_efectivo} + Tarjeta: Q{monto_tarjeta}"

        venta_id, garantia = _registrar_venta_chat(
            cliente_id, descripcion, total_final,
            producto_id=ctx.get("producto_id"), producto_nombre=ctx.get("producto", ""),
            cliente_nombre=cliente_nombre, cliente_tel=cliente_tel
        )

        puntos_info = None
        if cliente_id:
            consumir_credito_puntos_pendiente(cliente_id, venta_id)
            puntos_info = ganar_puntos(cliente_id, cliente_nombre, total_final, venta_id)

        resumen = f"Venta #{venta_id} registrada. Efectivo Q{monto_efectivo} + Tarjeta Q{monto_tarjeta}."
        if descuento:
            resumen += f" Descuento {descuento['nombre']} ({descuento['tipo']}): -Q{descuento['monto_descuento']}."
        if ajuste_puntos["credito_puntos"] or ajuste_puntos["descuento_oro"]:
            resumen += (f" Ajuste por puntos: -Q{ajuste_puntos['credito_puntos']}"
                        f"{f' + 5% Oro -Q' + str(ajuste_puntos['descuento_oro']) if ajuste_puntos['descuento_oro'] else ''}.")
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
        from database.aronium import (
            DIAS_VENCIMIENTO_CUENTA_DEFAULT, formatear_nota_ajuste_puntos,
            consumir_credito_puntos_pendiente, ganar_puntos, crear_cuenta_cobrar
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

        descripcion = f"{ctx['cantidad']}x {ctx['producto']} a Q{ctx['precio_unit']}"
        if descuento:
            descripcion += f" | Descuento {descuento['nombre']}: -Q{descuento['monto_descuento']}"
        descripcion += formatear_nota_ajuste_puntos(ajuste_puntos)
        descripcion += f" | Credito: enganche Q{enganche}, resto vence {fecha_vencimiento}"

        venta_id, garantia = _registrar_venta_chat(
            cliente_id, descripcion, total_final,
            producto_id=ctx.get("producto_id"), producto_nombre=ctx.get("producto", ""),
            cliente_nombre=cliente_nombre, cliente_tel=cliente_tel
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

        pendiente = round(total_final - enganche, 2)
        resumen = f"Venta #{venta_id} registrada a credito. {ctx['cantidad']}x {ctx['producto']} = Q{ctx['total']}."
        if descuento:
            resumen += f" Descuento {descuento['nombre']} ({descuento['tipo']}): -Q{descuento['monto_descuento']}."
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
        from database.aronium import crear_cliente, crear_orden
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
        from database.aronium import (
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
        from database.aronium import buscar_cliente_completo
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
        from database.aronium import crear_cliente_completo
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
        from database.aronium import get_products
        productos = get_products(search=message.strip())
        if not productos:
            return f"No encontre '{message.strip()}' en inventario. Intenta con otro nombre, o escribe 'listo' para terminar.", context
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
    # precio con descuento (DESCUENTO_COMBO_SUGERIDO, ver database.aronium) que
    # el admin puede aceptar o reemplazar por un monto propio.
    if step == "combo_crear_waiting_producto":
        msg = message.strip().lower()
        if msg in ["listo", "ya", "no mas", "no más", "terminar", "fin"]:
            items = context.get("combo_items", [])
            if not items:
                return "Agrega al menos un producto antes de terminar.", context
            from database.aronium import DESCUENTO_COMBO_SUGERIDO
            suma = round(sum(i["precio_unit"] * i["cantidad"] for i in items), 2)
            precio_sugerido = round(suma - suma * DESCUENTO_COMBO_SUGERIDO, 2)
            context["combo_suma"] = suma
            context["combo_precio_sugerido"] = precio_sugerido
            context["step"] = "combo_crear_waiting_precio"
            return (f"Precio normal por separado: Q{suma}. Precio sugerido con "
                    f"{int(DESCUENTO_COMBO_SUGERIDO * 100)}% de descuento: Q{precio_sugerido}. "
                    f"Usar este precio? (si, o escribe otro monto)"), context
        from database.aronium import get_products
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
        from database.aronium import crear_combo
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

    # Confirmacion del fondo sugerido (igual al cierre del turno anterior)
    if step == "caja_abrir_confirmar_sugerido":
        resp = message.strip().lower()
        if resp in ["si", "si.", "sí", "s", "ok", "dale", "yes", "de una"]:
            from database.aronium import abrir_turno
            from flask_login import current_user
            fondo = context.get("caja_fondo_sugerido", {})
            context = {}
            turno_id, total = abrir_turno(int(current_user.id), current_user.nombre, fondo)
            detalle = ", ".join([f"{v}xQ{k}" for k, v in fondo.items() if int(v) > 0])
            return f"Turno de caja abierto (#{turno_id}). Fondo inicial: Q{total} ({detalle}).", context
        from database.aronium import DENOMINACIONES
        context = {"step": "caja_abrir_denom", "caja_idx": 0, "caja_fondo": {}}
        return f"Cuantos billetes/monedas de Q{DENOMINACIONES[0]} hay?", context

    # Confirmacion del fondo sugerido como monto total (sin desglose por denominacion)
    if step == "caja_abrir_confirmar_sugerido_total":
        resp = message.strip().lower()
        if resp in ["si", "si.", "sí", "s", "ok", "dale", "yes", "de una"]:
            from database.aronium import abrir_turno_simple
            from flask_login import current_user
            total = context.get("caja_fondo_sugerido_total", 0)
            context = {}
            turno_id, total = abrir_turno_simple(int(current_user.id), current_user.nombre, total)
            return f"Turno de caja abierto (#{turno_id}). Fondo inicial: Q{total}.", context
        from database.aronium import DENOMINACIONES
        context = {"step": "caja_abrir_denom", "caja_idx": 0, "caja_fondo": {}}
        return f"Cuantos billetes/monedas de Q{DENOMINACIONES[0]} hay?", context

    # Flujo de apertura de turno de caja (fondo inicial por denominacion)
    if step == "caja_abrir_denom":
        from database.aronium import DENOMINACIONES, abrir_turno
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
        from database.aronium import get_turno_abierto
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
        from database.aronium import cerrar_turno, get_turno_abierto
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
        from database.aronium import get_turno_abierto, anular_turno
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
            from database.aronium import connect, add_stock
            name = context["product_name"].title()
            price = context["price"]
            qty = context.get("quantity", 0)
            conn = connect()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO Product (Name, Code, Price, Cost, IsEnabled) VALUES (?, ?, ?, ?, 1)",
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

    # Intento 1 y 2: deteccion directa + traduccion Gemini
    detectado = _intentar_detectar(message, role, context, contexto_historial)
    if detectado:
        return detectado

    # Intento 3: el mensaje no coincidio con ningun intent. Antes de mandarlo a
    # OpenClaw, se analiza si es una intencion de negocio expresada de forma vaga
    # (ver CLARIFICACION_PROMPT). Si Gemini genera una pregunta de clarificacion,
    # se guarda el mensaje original en el contexto y se le pregunta al usuario.
    pregunta = _analizar_intencion_vaga(message, contexto_historial)
    if pregunta:
        context = {"step": "clarificando", "original_message": message}
        return pregunta, context

    # Intento 4: OpenClaw
    if role != "admin":
        return ("No entendi esa instruccion. Si necesitas ayuda con algo fuera de "
                "inventario, ventas o clientes, contacta a un administrador."), context
    return send_to_openclaw(message, contexto_historial), context
