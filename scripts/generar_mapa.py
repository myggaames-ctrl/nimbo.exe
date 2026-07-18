"""
Genera mapa_nimbo.html a partir del codigo real del proyecto.

Que hace, en orden:
1. Recorre los archivos .py del proyecto y extrae, con el modulo ast (lee el
   codigo real, no busca texto como grep), quien importa a quien.
2. Detecta automaticamente los templates que app.py sirve con render_template().
3. Junta esos imports con una descripcion curada a mano por archivo (que hace,
   funcion principal) - si aparece un archivo nuevo que este script no conoce
   todavia, le arma una entrada generica en vez de fallar.
4. Calcula el estado de cada archivo (activo/huerfano/vacio) de forma
   automatica en vez de tenerlo hardcodeado, para que este script seguido
   reflejando la realidad aunque el proyecto cambie:
   - "vacio": el archivo pesa 0 bytes.
   - "huerfano" (solo aplica a core/detectors/): el detector no esta importado
     en core/intent_detector.py, asi que ningun mensaje del chat lo alcanza.
   - "activo": cualquier otro caso.
   (Para tools/ y services/ no se intenta detectar huerfanos automaticamente:
   eso requeriria rastrear que intent devuelve cada detector y compararlo
   contra los registros de TOOLS{} - demasiado para un script simple. Si en
   el futuro aparece un huerfano ahi, hay que anotarlo a mano en NODOS_EXTRA
   de este archivo, igual que se hizo con los que ya se limpiaron el
   2026-07-18, ver BUGS_Y_FIXES.md.)
5. Escribe mapa_nimbo.html en la raiz del proyecto, con los datos incrustados.

Se puede correr solo (python3 scripts/generar_mapa.py) o via
actualizar_mapa.sh, que ademas copia el resultado al escritorio.
"""
import ast
import json
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # raiz del proyecto (un nivel arriba de scripts/)

PREFIJOS_PROPIOS = ("core", "tools", "services", "database", "openclaw_bridge", "app")

# ── categorías y colores ──────────────────────────────────────────────────
COLORS = {
    "entrada":  "#eab308",  # dorado - punto de entrada (app.py)
    "core":     "#ef4444",  # rojo - orquestacion / cerebro
    "detector": "#22c55e",  # verde - detectores
    "tool":     "#f97316",  # naranja - herramientas
    "service":  "#a855f7",  # morado - servicios
    "database": "#3b82f6",  # azul - base de datos
    "template": "#94a3b8",  # gris - templates / frontend
    "bridge":   "#14b8a6",  # teal - integracion externa
}

CATEGORY_LABEL = {
    "entrada":  "Punto de entrada",
    "core":     "Núcleo / Orquestación",
    "detector": "Detectores",
    "tool":     "Herramientas (Tools)",
    "service":  "Servicios",
    "database": "Base de datos",
    "template": "Templates (Frontend)",
    "bridge":   "Integración externa",
}

# ── descripciones curadas a mano (id de archivo -> name, group, desc, func) ─
# Se guardan sin "status": el estado se calcula solo mas abajo (ver docstring).
NODOS = {}


def curar(fid, name, group, desc, func):
    NODOS[fid] = {"name": name, "group": group, "desc": desc, "func": func}


# ---------- entrada ----------
curar("app.py", "app.py", "entrada",
      "Aplicación Flask principal. Define TODAS las rutas web y de API: login, onboarding "
      "(/setup), dashboard, chat, inventario, caja, servicio técnico, cotizaciones, etc. Es la "
      "puerta de entrada de cualquier request del navegador.",
      "Arrancar el servidor Flask, registrar rutas, e inicializar las tablas de nimbo.db al "
      "arrancar.")

# ---------- core (núcleo) ----------
curar("core/__init__.py", "core/__init__.py", "core",
      "Archivo vacío que marca la carpeta core/ como paquete de Python. No contiene lógica.",
      "Permitir 'import core...' en el resto del proyecto.")

curar("core/nimbo.py", "nimbo.py", "core",
      "El cerebro del chat. NimboCore.send() recibe el mensaje del usuario y lo hace pasar por "
      "todo el pipeline: contexto reciente, ActionEngine/IntentDetector, traducción con Ollama, "
      "clarificación de intención vaga, y por último el fallback directo a Ollama. También "
      "contiene TODOS los flujos conversacionales paso a paso (crear producto, vender, cotizar, "
      "abrir caja, etc).",
      "send(mensaje, usuario) -> siempre devuelve una respuesta de texto para el chat.")

curar("core/action_engine.py", "action_engine.py", "core",
      "Orquestador entre el mensaje ya traducido y la ejecución real. Aplica el control de "
      "acceso por rol (admin/empleado/técnico) según la categoría del intent detectado "
      "(CATEGORIAS_POR_ROL), y si el rol tiene permiso, llama al IntentDetector y ejecuta la "
      "Tool correspondiente desde el TOOL_REGISTRY.",
      "procesar(texto, rol) -> detecta intent, valida permiso, ejecuta la tool y retorna el "
      "resultado.")

curar("core/intent_detector.py", "intent_detector.py", "core",
      "Contiene la lista ordenada de TODOS los detectores activos. Los prueba uno por uno (el "
      "orden importa: los más específicos van primero para evitar choques entre patrones "
      "parecidos) y devuelve el primer intent que matchea.",
      "detect(texto) -> primer {intent, ...datos} que encuentre, o None si ningún detector "
      "matchea.")

curar("core/command_normalizer.py", "command_normalizer.py", "core",
      "Corrector ortográfico simple: antes de que cualquier detector vea el mensaje, corrige "
      "errores tipográficos comunes (diccionario + difflib.get_close_matches contra un "
      "vocabulario del negocio) y quita acentos.",
      "normalizar(texto) -> texto corregido y sin acentos, listo para los detectores.")

curar("core/chat_context.py", "chat_context.py", "core",
      "Carga los últimos mensajes de ChatHistorial (puede incluir días anteriores) y los "
      "recorta a ~500 tokens, para que Ollama pueda resolver referencias como 'cuántas quedan?' "
      "sin repetir el nombre del producto.",
      "resumen_texto(usuario) -> string de contexto reciente para pasarle a Ollama.")

curar("core/auth.py", "auth.py", "core",
      "Todo el sistema de login: modelo Usuario (Flask-Login), roles (admin/empleado/técnico), "
      "hashing de contraseñas, tokens de recuperación de contraseña, y listar_tecnicos() para "
      "asignar órdenes de servicio.",
      "Autenticar usuarios y exponer el modelo Usuario al resto de la app.")

curar("core/configuracion.py", "configuracion.py", "core",
      "Maneja la tabla Configuracion (clave/valor) donde vive toda la info del negocio: nombre, "
      "tipo, país, moneda, IVA, horario, fondo de caja sugerido, etc. Se llena durante el wizard "
      "de /setup.",
      "get_config(clave) / set_config(clave, valor) sobre la tabla Configuracion.")

curar("core/responses.py", "responses.py", "core",
      "Formatea texto de respuesta para el chat en casos concretos (por ejemplo el detalle de "
      "un presupuesto). Depende de database/nimbo_db.py para traer los datos que va a "
      "formatear.",
      "Convertir datos crudos en mensajes de texto legibles para el usuario.")

curar("core/tool_registry.py", "tool_registry.py", "core",
      "El directorio global de herramientas: un diccionario TOOLS{nombre_intent: función}. "
      "Cada archivo de tools/ se registra aquí solo, al cargarse, con "
      "register('categoria.accion', función).",
      "register(nombre, funcion) y list_tools() -> el registro completo que usa ActionEngine.")

curar("core/detectors/__init__.py", "detectors/__init__.py", "core",
      "Archivo vacío. A diferencia de tools/__init__.py, los detectores NO se cargan "
      "automáticamente por convención de carpeta: cada uno se importa a mano, uno por uno, en "
      "core/intent_detector.py - así se evita que un detector nuevo quede huérfano sin que nada "
      "avise (hasta 2026-07-18 hubo 3 así - BudgetDetector/CustomerDetector/WindowsDetector - "
      "se eliminaron en la limpieza de código huérfano, ver BUGS_Y_FIXES.md).",
      "Ninguna, solo marca el paquete.")

curar("core/empresa.py", "empresa.py", "core",
      "Multi-tenant (2026-07-18): el directorio de empresas. Maneja nimbo_master.db (tabla "
      "Empresa: Nombre/Slug/DbPath), separado de los nimbo.db de cada empresa - cada una vive "
      "en data/empresas/<slug>/nimbo.db, aislada del resto. Genera el slug automáticamente a "
      "partir del nombre (sin tildes, espacios a guiones) y, al crear una empresa, llama a las "
      "22 funciones init_* de database/nimbo_db.py más las de core/auth.py y "
      "core/configuracion.py contra el nimbo.db nuevo, para dejarlo con todas las tablas listas "
      "pero vacías.",
      "crear_empresa(nombre) -> crea la carpeta, la fila en el maestro, y todas las tablas; "
      "get_db_path(slug) -> ruta absoluta al nimbo.db de esa empresa.")

# ---------- bridge ----------
curar("openclaw_bridge.py", "openclaw_bridge.py", "bridge",
      "Puente HTTP hacia OpenClaw, un agente que corre en la PC (con Gemini) en el puerto "
      "18789. Ya NO es el fallback automático del chat (eso lo hace Ollama ahora) - se mantiene "
      "solo como opción manual: el botón del dashboard y /api/openclaw/chat en app.py lo siguen "
      "usando.",
      "send_to_openclaw(mensaje) / check_openclaw_status() -> hablar con el agente de PC "
      "externo.")

# ---------- database ----------
curar("database/nimbo_db.py", "nimbo_db.py", "database",
      "El módulo de acceso a datos más grande del proyecto (se llamaba database/aronium.py, de "
      "cuando TODO pasaba por Aronium - se renombró a nimbo_db.py y se actualizaron todos los "
      "imports del proyecto para que el nombre refleje lo que hace hoy). Hoy mezcla dos "
      "fuentes: nimbo.db (Producto, Stock, Kardex, Cotizacion, CajaTurno, Garantias, Combos, "
      "Puntos, CuentaCobrar/Pagar... casi todas las tablas propias del negocio) y pos.db/"
      "Aronium (solo ya para reportes de ventas físicas de caja y el catálogo nativo de "
      "clientes). Es el archivo con más conexiones entrantes de todo el proyecto: casi cada "
      "tool le pide datos directamente.",
      "Decenas de funciones get_*/crear_*/actualizar_* - la capa de persistencia de todo "
      "Nimbo.")

# ---------- detectores (en el orden real de core/intent_detector.py) ----------
DETECTORES_DESC = {
    "caja_detector.py": ("CajaDetector",
        "Reconoce 'abrir caja', 'cerrar caja', 'retirar QN de caja', 'anular turno'."),
    "cliente_detector.py": ("ClienteDetector",
        "Búsqueda/alta de clientes, historial, resumen, y grupos de cliente "
        "(detallista/mayorista/especial/vip). Se revisa temprano porque tiene patrones "
        "catch-all ('cliente ...') que hay que blindar con lookaheads negativos contra otros "
        "detectores."),
    "codigo_barras_detector.py": ("CodigoBarrasDetector",
        "'generar código de X', 'etiqueta de X', 'etiquetas de todos sin código', y el patrón "
        "especial de código de barras 'pelado' (solo dígitos o alfanumérico corto) para el "
        "lector USB/Bluetooth."),
    "combo_detector.py": ("ComboDetector",
        "'crear combo X', 'ver combos', 'vender combo X', 'sugerir combos' (con IA)."),
    "contabilidad_detector.py": ("ContabilidadDetector",
        "Balance, IVA/ISR, margen, punto de equilibrio, declaración de IVA, flujo de caja "
        "proyectado, sugerencias de precios."),
    "contenido_detector.py": ("ContenidoDetector",
        "Generación de posts, guiones y videos para redes sociales."),
    "cotizacion_detector.py": ("CotizacionDetector",
        "'cotización para X', 'ver cotización COT-XXXX', 'aceptaron/rechazaron la cotización'."),
    "cuenta_cobrar_detector.py": ("CuentaCobrarDetector",
        "'X debe QN', 'X pagó QN', 'cuánto debe X' - deudas de clientes con la tienda."),
    "cuenta_pagar_detector.py": ("CuentaPagarDetector",
        "'debo QN a X', 'pagué QN a X' - deudas de la tienda con proveedores (espejo de "
        "cobrar)."),
    "descuento_detector.py": ("DescuentoDetector",
        "'descuento N% para X', 'descuento N% en compras mayores a QN', 'eliminar descuento "
        "X'."),
    "evento_detector.py": ("EventoDetector",
        "Pagos fijos (recordatorios), su monto, y otros recordatorios/eventos del negocio."),
    "garantia_detector.py": ("GarantiaDetector",
        "'garantía de X es N días', 'ver garantía GAR-XXXX', 'garantías de X', 'garantías por "
        "vencer'."),
    "inventory_detector.py": ("InventoryDetector",
        "Se revisa último (catch-all amplio): crear/editar producto, stock, alertas "
        "predictivas, importar, y el patrón especial de escaneo de código de barras directo en "
        "el chat."),
    "proveedor_detector.py": ("ProveedorDetector",
        "'historial de compras a X', 'genera orden para X', contactos de proveedor."),
    "puntos_detector.py": ("PuntosDetector",
        "'puntos de X', 'canjear N puntos de X', 'puntos disponibles' (programa de lealtad)."),
    "reembolso_detector.py": ("ReembolsoDetector",
        "'reembolso de la venta #N', 'cambio de producto de la venta #N', 'crédito de tienda "
        "de X', 'ver reembolso REM-XXXX'."),
    "reporte_detector.py": ("ReporteDetector",
        "Reportes de ventas por período, patrones de venta, mejor hora para vender, próxima "
        "compra estimada de un cliente."),
    "service_detector.py": ("ServiceDetector",
        "Todo el flujo de Servicio Técnico: crear orden, cambiar estado, informes de revisión, "
        "aprobación/rechazo del cliente, fotos, garantía de reparación."),
    "tarifa_detector.py": ("TarifaDetector",
        "'agregar tarifa X QN', 'ver tarifas' (catálogo de mano de obra)."),
    "unidad_medida_detector.py": ("UnidadMedidaDetector",
        "'X se vende por docena/caja/par de N', 'vendí N docenas de X', 'ver unidades de "
        "medida'."),
    "venta_detector.py": ("VentaDetector",
        "El flujo de venta simple por chat: 'vendí N X', selección de cliente, método de "
        "pago."),
}
for _fname, (_cname, _desc) in DETECTORES_DESC.items():
    curar(f"core/detectors/{_fname}", _fname, "detector", f"{_cname}. {_desc}",
          "detect(texto) -> {intent, ...datos} si el mensaje matchea alguno de sus patrones, o "
          "None.")

# ---------- tools ----------
curar("tools/__init__.py", "tools/__init__.py", "tool",
      "Carga automática de TODOS los módulos de tools/ usando pkgutil.iter_modules + "
      "importlib. A diferencia de core/detectors/, aquí basta con crear el archivo para que se "
      "registre solo.",
      "Importar cada archivo de tools/ una sola vez al arrancar la app.")

TOOLS_DESC = {
    "inventory_tool.py": "Inventario: crear/editar/eliminar producto, agregar/quitar stock, "
        "importar Excel/CSV, generar código de barras, resolver el escaneo directo en el chat.",
    "service_tool.py": "Servicio Técnico: crear orden, cambiar estado (7 pasos), informes de "
        "revisión con presupuesto automático, fotos, garantía de reparación.",
    "cliente_tool.py": "Clientes: alta (con selección de grupo), historial completo, resumen, "
        "grupos de cliente.",
    "venta_tool.py": "Registrar una venta simple desde el chat (arranca el flujo conversacional "
        "de venta en core/nimbo.py).",
    "proveedor_tool.py": "Proveedores: contactos, pedidos sugeridos, generar orden de compra.",
    "contenido_tool.py": "Contenido: posts, guiones, videos con Veo 3, publicación en redes.",
    "reporte_tool.py": "Reportes de ventas por período, patrones de venta, predicción de "
        "próxima compra de un cliente.",
    "evento_tool.py": "Recordatorios y pagos fijos (crear, fijar su monto, listar).",
    "contabilidad_tool.py": "Balance, IVA/ISR, margen, sugerencias de precios, declaración de "
        "IVA, flujo de caja proyectado.",
    "cotizacion_tool.py": "Genera cotizaciones (PDF + registro), consulta y cambia su estado.",
    "caja_tool.py": "Solo 'abrir caja' por chat (arranca el flujo conversacional de caja) - el "
        "resto de Caja se opera desde el panel dedicado del dashboard.",
    "descuento_tool.py": "Crear, listar y eliminar descuentos (cliente/temporada/producto/"
        "monto).",
    "garantia_tool.py": "Configurar días de garantía por producto, ver una garantía, listar por "
        "cliente, garantías por vencer.",
    "cuenta_cobrar_tool.py": "Crear deuda de cliente, registrar pagos (FIFO), consultar y "
        "listar cuentas por cobrar/vencidas.",
    "cuenta_pagar_tool.py": "Espejo de cuenta_cobrar_tool pero con proveedores: crear deuda, "
        "pagar, consultar, listar.",
    "combo_tool.py": "Crear combos, listarlos, venderlos de una vez, y sugerir combos nuevos "
        "con IA sobre el inventario real.",
    "unidad_medida_tool.py": "Configurar presentaciones (docena/caja/par) y vender por ellas "
        "reusando el flujo normal de venta.",
    "puntos_tool.py": "Consultar saldo de puntos, canjear manualmente, listar clientes con "
        "saldo.",
    "codigo_barras_tool.py": "Generar un código EAN-13 nuevo y las etiquetas en PDF (con QR).",
    "tarifa_tool.py": "Catálogo de tarifas de mano de obra (agregar y listar).",
    "reembolso_tool.py": "Iniciar reembolso/cambio de producto de una venta, consultar crédito "
        "de tienda de un cliente, buscar un reembolso por número.",
}
for _fname, _desc in TOOLS_DESC.items():
    curar(f"tools/{_fname}", _fname, "tool", _desc,
          "Función registrada en TOOLS{} que ActionEngine ejecuta cuando el intent coincide.")

# ---------- services ----------
SERVICES_DESC = {
    "inventory.py": "InventoryService: search/search_barcode/list - delega en "
        "database/nimbo_db.py para heredar el mismo fallback de búsqueda difusa (fuzzy) con "
        "difflib.",
    "whatsapp.py": "Toda la mensajería de WhatsApp Business API: notificación de orden, "
        "presupuesto, factura, asignación de técnico, aprobación/rechazo de cliente.",
    "social_media.py": "Publicación en Facebook/Instagram (API de Meta).",
    "video_gen.py": "Generación de video con Veo 3 (Google) para contenido de redes.",
    "mail_service.py": "Envío de correo con Flask-Mail (recuperación de contraseña) + logging "
        "detallado de errores SMTP.",
    "pdf_cotizacion.py": "Genera el PDF de una cotización con reportlab; se guarda en "
        "static/cotizaciones/ (público, sin login) para poder compartirse por WhatsApp.",
    "pdf_iva.py": "Genera el PDF de referencia de la declaración mensual de IVA con reportlab.",
    "ticket.py": "Arma el texto plano del ticket de caja en formato térmico de 32 columnas "
        "(58mm).",
    "barcode_service.py": "Genera el PDF de etiquetas de producto: código de barras (EAN-13 o "
        "Code128 según el formato) + un QR que apunta a la página pública del producto.",
    "ollama_service.py": "El único punto de entrada a Ollama local (qwen2.5:7b, un solo modelo "
        "para todo): llamar_ollama/analizar_ollama/ollama_disponible. Nunca lanza excepción: "
        "devuelve None si Ollama no responde, o un MENSAJE_TIMEOUT si tardó demasiado (180s "
        "chat / 300s análisis).",
    "skills_service.py": "Ejecuta un subprocess para chequear el estado de 'skills' externas.",
}
for _fname, _desc in SERVICES_DESC.items():
    curar(f"services/{_fname}", _fname, "service", _desc,
          "Función/clase de servicio que una o varias tools llaman para hablar con el mundo "
          "exterior (APIs, PDFs, IA) o con la base de datos.")

# ---------- templates (descripciones curadas; cuales existen se detecta solo) ----------
TEMPLATES_DESC = {
    "index.html": (
        "El dashboard completo: chat, inventario, caja, servicio técnico, clientes, "
        "contabilidad, reportes, configuración, usuarios - todos los paneles del panel "
        "principal, con el sidebar que se adapta según el rol (admin/empleado/técnico).",
        "render_template('index.html') desde app.py, la vista principal tras iniciar sesión."),
    "login.html": (
        "Pantalla de inicio de sesión, con el botón 'Ver demo del onboarding'.",
        "render_template('login.html') desde app.py en /login."),
    "setup.html": (
        "El wizard de onboarding de 7 pasos (y su modo demo /setup/demo, que reutiliza el "
        "mismo template con demo=True).",
        "render_template('setup.html') desde /setup/<paso> y /setup/demo/<paso>."),
    "forgot_password.html": (
        "Formulario para pedir el correo de recuperación de contraseña.",
        "render_template('forgot_password.html') desde /forgot-password."),
    "reset_password.html": (
        "Formulario para escribir la nueva contraseña usando el token recibido por correo.",
        "render_template('reset_password.html') desde /reset-password?token=."),
    "producto_publico.html": (
        "Página pública de un producto (sin login): foto, nombre, precio y descripción - a "
        "donde apunta el QR de la etiqueta. Nunca muestra stock ni costo.",
        "render_template('producto_publico.html') desde /producto/<codigo>."),
    "pos.html": (
        "Pantalla de punto de venta standalone (tema oscuro), separada del panel 'Caja' del "
        "dashboard principal - un prototipo de checkout simplificado, accesible con sesión "
        "iniciada.",
        "render_template('pos.html') desde /pos (@login_required)."),
    "select_empresa.html": (
        "Multi-tenant (2026-07-18): pantalla para elegir con qué empresa trabajar - lista las "
        "empresas activas (listar_empresas()) con un botón 'Entrar' por fila, más un botón para "
        "ir a registrar una empresa nueva. Es la primera pantalla que ve cualquiera que visite "
        "Nimbo sin una empresa ya elegida en su sesión.",
        "render_template('select_empresa.html') desde /select-empresa (GET/POST)."),
    "register_empresa.html": (
        "Multi-tenant (2026-07-18): wizard de 2 pasos para registrar una empresa nueva (nombre "
        "con vista previa del slug generado en vivo por JavaScript, luego los datos del primer "
        "admin) - termina en un fetch() POST a /api/empresa/crear. Deliberadamente más simple "
        "que el wizard viejo de 7 pasos (setup.html): no pide IVA/horario/fondo de caja, solo lo "
        "mínimo para poder loguearse.",
        "render_template('register_empresa.html') desde /register-empresa."),
}
curar("static/tiktok-verification.html", "tiktok-verification.html", "template",
      "Archivo de una sola línea con el texto literal 'tiktok-verification', usado para la "
      "verificación de dominio de la API de TikTok.",
      "Servido tal cual por /tiktok-verification.html en app.py.")


# ── helpers ──────────────────────────────────────────────────────────────

def listar_archivos_py():
    archivos = []
    for dirpath, dirnames, filenames in os.walk(BASE_DIR):
        dirnames[:] = [
            d for d in dirnames
            if d not in (".git", "__pycache__", "static", "templates", "node_modules", "scripts")
        ]
        for fn in filenames:
            if fn.endswith(".py"):
                archivos.append(os.path.relpath(os.path.join(dirpath, fn), BASE_DIR))
    return sorted(archivos)


def path_a_modulo(path):
    p = path[:-3] if path.endswith(".py") else path
    mod = p.replace(os.sep, ".")
    if mod.endswith(".__init__"):
        mod = mod[: -len(".__init__")]
    return mod


def extraer_edges(archivos):
    """AST real (no grep): para cada archivo, que otros archivos del proyecto importa."""
    mod_a_archivo = {path_a_modulo(f): f for f in archivos}
    edges = []
    for f in archivos:
        ruta_completa = os.path.join(BASE_DIR, f)
        try:
            arbol = ast.parse(open(ruta_completa, encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError):
            continue
        modulos_importados = set()
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.module.startswith(PREFIJOS_PROPIOS):
                modulos_importados.add(nodo.module)
            elif isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    if alias.name.startswith(PREFIJOS_PROPIOS):
                        modulos_importados.add(alias.name)
        for mod in modulos_importados:
            resuelto = mod_a_archivo.get(mod)
            if not resuelto:
                partes = mod.split(".")
                while partes and not resuelto:
                    partes.pop()
                    resuelto = mod_a_archivo.get(".".join(partes))
            if resuelto and resuelto != f:
                edges.append((f, resuelto))
    return sorted(set(edges))


def detectar_templates_usados():
    """Busca render_template('X.html') en app.py - asi un template nuevo se detecta solo,
    sin tener que tocar este script cada vez que se agrega una pagina."""
    ruta_app = os.path.join(BASE_DIR, "app.py")
    codigo = open(ruta_app, encoding="utf-8").read()
    nombres = set(re.findall(r"render_template\(\s*['\"]([^'\"]+\.html)['\"]", codigo))
    edges = []
    for nombre in sorted(nombres):
        ruta_template = os.path.join(BASE_DIR, "templates", nombre)
        if os.path.isfile(ruta_template):
            fid = f"templates/{nombre}"
            if fid not in NODOS:
                desc, func = TEMPLATES_DESC.get(nombre, (
                    "Template detectado automáticamente (render_template en app.py). No tiene "
                    "descripción curada todavía - agrégala en TEMPLATES_DESC de "
                    "scripts/generar_mapa.py.",
                    f"render_template('{nombre}') desde app.py."))
                curar(fid, nombre, "template", desc, func)
            edges.append(("app.py", fid))
    # Caso especial: la ruta /tiktok-verification.html en app.py devuelve el texto
    # hardcodeado directamente (no lee el archivo con render_template ni de otra forma),
    # asi que no hay un import/referencia real que detectar por texto. Se conecta a mano
    # porque conceptualmente sirve el mismo contenido que ese archivo estatico.
    if '"/tiktok-verification.html"' in codigo or "'/tiktok-verification.html'" in codigo:
        ruta = os.path.join(BASE_DIR, "static", "tiktok-verification.html")
        if os.path.isfile(ruta):
            edges.append(("app.py", "static/tiktok-verification.html"))
    return edges


CATEGORIA_POR_CARPETA = {
    "core/detectors": "detector",
    "tools": "tool",
    "services": "service",
    "database": "database",
    "core": "core",
}


def categoria_por_ruta(fid):
    carpeta = os.path.dirname(fid)
    if carpeta in CATEGORIA_POR_CARPETA:
        return CATEGORIA_POR_CARPETA[carpeta]
    return "core"


def calcular_status(fid, group, detectores_importados):
    ruta = os.path.join(BASE_DIR, fid)
    try:
        if os.path.getsize(ruta) == 0:
            return "vacio"
    except OSError:
        return "vacio"
    if group == "detector" and fid not in detectores_importados:
        return "huerfano"
    return "activo"


def main():
    archivos_py = listar_archivos_py()
    edges_py = extraer_edges(archivos_py)
    edges_templates = detectar_templates_usados()
    edges = edges_py + edges_templates

    # que detectores SI estan importados en core/intent_detector.py (para el status huerfano)
    detectores_importados = {
        target for source, target in edges_py
        if source == "core/intent_detector.py" and target.startswith("core/detectors/")
    }

    nodos_finales = {}

    # 1. archivos .py reales encontrados en el proyecto
    for fid in archivos_py:
        if fid in NODOS:
            meta = NODOS[fid]
        else:
            grupo = categoria_por_ruta(fid)
            meta = {
                "name": os.path.basename(fid),
                "group": grupo,
                "desc": "Archivo nuevo detectado automáticamente - todavía no tiene una "
                        "descripción curada. Agrégasela en scripts/generar_mapa.py (función "
                        "curar) para que este mapa la muestre.",
                "func": "(sin documentar todavía)",
            }
        status = calcular_status(fid, meta["group"], detectores_importados)
        nodos_finales[fid] = {
            "id": fid, "name": meta["name"], "group": meta["group"],
            "desc": meta["desc"], "func": meta["func"], "status": status,
        }

    # 2. templates detectados via render_template() (agregados a NODOS por detectar_templates_usados)
    for fid in list(NODOS):
        if fid.startswith("templates/") or fid.startswith("static/"):
            if fid in nodos_finales:
                continue
            ruta_real = os.path.join(BASE_DIR, fid)
            if not os.path.isfile(ruta_real):
                continue  # el template ya no existe en disco - no se incluye
            meta = NODOS[fid]
            status = calcular_status(fid, meta["group"], detectores_importados)
            nodos_finales[fid] = {
                "id": fid, "name": meta["name"], "group": meta["group"],
                "desc": meta["desc"], "func": meta["func"], "status": status,
            }

    edges_out = [{"source": s, "target": t} for s, t in edges if s in nodos_finales and t in nodos_finales]

    graph_data = {
        "colors": COLORS,
        "categoryLabel": CATEGORY_LABEL,
        "nodes": list(nodos_finales.values()),
        "edges": edges_out,
    }

    template_path = os.path.join(SCRIPT_DIR, "mapa_template.html")
    template_html = open(template_path, encoding="utf-8").read()
    html_final = template_html.replace("__GRAPH_DATA__", json.dumps(graph_data, ensure_ascii=False, indent=1))

    salida = os.path.join(BASE_DIR, "mapa_nimbo.html")
    with open(salida, "w", encoding="utf-8") as f:
        f.write(html_final)

    huerfanos = sum(1 for n in nodos_finales.values() if n["status"] == "huerfano")
    vacios = sum(1 for n in nodos_finales.values() if n["status"] == "vacio")

    print(f"NODOS: {len(nodos_finales)}")
    print(f"CONEXIONES: {len(edges_out)}")
    print(f"  activos: {len(nodos_finales) - huerfanos - vacios}")
    print(f"  huerfanos: {huerfanos}")
    print(f"  vacios: {vacios}")
    print(f"Escrito: {salida}")


if __name__ == "__main__":
    main()
