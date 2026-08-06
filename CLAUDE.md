# Nimbo AI Dashboard - Mi Cocina Electrodomesticos Guatemala

## Descripcion
Sistema de gestion empresarial con IA para tienda de electrodomesticos y repuestos en Guatemala.
Chat en lenguaje natural en espanol que controla todo el negocio.

## Stack
- Backend: Flask (Python 3.10) en WSL2, puerto 5000
- IA Principal: Ollama local (http://localhost:11434) - un unico modelo, qwen2.5:7b, para
  todo (chat, traduccion, contenido y analisis financieros/estrategicos - ver
  services/ollama_service.py y seccion "Arquitectura del chat" mas abajo). Se probo primero
  con gemma2:9b aparte para los analisis, pero se descarto: alternar entre 2 modelos hacia
  que Ollama descargara uno para cargar el otro en cada llamada (penalidad de recarga que por
  si sola podia agotar el timeout) y arriesgaba quedarse sin RAM con ambos cargados a la vez
  (~11GB combinados, causo que el servidor de Nimbo se cayera por presion de memoria durante
  las pruebas). Gemini API (GEMINI_API_KEY, libreria google-genai) ya NO se usa en NINGUN
  punto del proyecto - la migracion se hizo en 2 pasos: primero el pipeline conversacional
  del chat (core/nimbo.py) y las tools de contabilidad/evento/contenido que ese pipeline
  invoca; despues, el 2026-08-05, los 5 usos que quedaban fuera de ese pipeline (encontrados
  con un escaneo completo del repo - un CLAUDE.md anterior a esa fecha decia
  "reemplazado por completo" y esa afirmacion era incorrecta, no cubria estos 5):
  - /api/inventory/analyze (app.py) - panel "Analisis de Datos" del dashboard (acceso propio
    en el sidebar, no pasa por el chat) - ahora usa analizar_ollama().
  - /api/content/generate (app.py) - panel "Generar Contenido" del dashboard - genera posts,
    scripts de video, descripciones y hashtags con llamar_ollama(). Es DISTINTO de
    tools/contenido_tool.py (el comando de chat "genera un post de X"), que ya estaba en
    Ollama desde el primer paso de la migracion.
  - /api/status (app.py) - health check del dashboard, ahora usa
    services.ollama_service.ollama_disponible() (GET /api/tags) en vez de pingear Gemini.
    La UI (templates/index.html) tambien se renombro de "Gemini API"/"Estado Gemini" a
    "Ollama"/"Estado Ollama" (ids dot-ollama/txt-ollama/stat-ollama, antes -gemini).
  - tools/combo_tool.py sugerir_combos_tool() - comando de chat "sugerir combos", ahora con
    analizar_ollama() (sigue pidiendole un JSON estricto al modelo, igual que antes).
  - tools/reporte_tool.py patrones_ventas_tool() - comando de chat "analiza mis patrones de
    venta", ahora con analizar_ollama() (el unico de los 5 con fallback: si Ollama no
    responde cae a un resumen sin IA, _resumen_patrones_sin_ia(), renombrada de
    _resumen_patrones_sin_gemini()).
  De paso se borro codigo muerto que solo existia para la integracion vieja con Gemini: el
  bloque "Paso 2" de la ruta /api/chat en app.py (fallback a Gemini que nunca se alcanzaba,
  ver mas abajo por que) y core/chat_context.py.resumen_para_gemini() (formato "contents" de
  la API de Gemini, sin ningun caller). GEMINI_API_KEY se removio de .env y del codigo. La
  libreria google-genai se mantiene instalada solo porque services/video_gen.py (Veo 3) la
  sigue usando, pero via Vertex AI (vertexai=True, project/location - ver seccion Google
  Cloud), sin relacion con GEMINI_API_KEY ni con este cambio.
- Agente PC: OpenClaw con Gemini (puerto 18789) - ya NO es el fallback automatico del chat
  (ver Arquitectura del chat), pero se mantiene como opcion manual: boton en el dashboard y
  la ruta /api/openclaw/chat en app.py siguen intactos, sin cambios.
- Base de datos: Nimbo SQLite /home/ictor_axtor/micocina-dashboard/nimbo.db - unica fuente de
  datos del negocio (productos, stock, kardex, ventas, clientes). Aronium (el POS externo que
  se uso durante la migracion inicial - Aronium SQLite, pos.db) ya NO se usa en ningun punto
  del proyecto: la integracion completa (ARONIUM_DB_PATH, database.nimbo_db.connect(),
  get_sales_today/get_sales_month/get_top_products/get_customers leyendo Document/
  DocumentItem/Product/Customer de Aronium, la seccion "INVENTARIO ARONIUM" de app.py, y
  migrar_productos_desde_aronium()) se removio por completo (ver BUGS_Y_FIXES.md). Ver
  "Catalogo propio (Producto/Stock)" mas abajo para el historial de esa migracion.

## Arranque diario
- Terminal 1: ~/nimbo-start.sh
- Terminal 2: openclaw
- Navegador: http://localhost:5000
- Primera vez (nimbo.db sin usuarios): el navegador redirige automaticamente a /setup

## Arquitectura del chat
Usuario escribe mensaje
-> nimbo.py send()
-> 0. Carga los ultimos 10 mensajes de ChatHistorial (core/chat_context.py,
     resumen_texto()), recortados a ~500 tokens. Puede incluir dias anteriores,
     no solo la sesion actual. Se calcula una vez por mensaje y se pasa a todos
     los pasos que llaman a Ollama abajo, para resolver referencias
     como "cuantas quedan?" sin repetir el nombre del producto.
-> 1. Verifica contexto activo (flujos conversacionales)
-> 2. ActionEngine -> IntentDetector -> Detectores -> Tool
-> 3. Si no detecta -> Ollama traduce (con el contexto reciente, _translate() en
     core/nimbo.py, modelo qwen2.5:7b via services.ollama_service.llamar_ollama) ->
     intenta de nuevo
-> 3.5. Si sigue sin detectar -> Ollama analiza si es una intencion de negocio vaga
        (tambien con contexto, _analizar_intencion_vaga()) y genera una pregunta de
        clarificacion (context.step = "clarificando")
-> 4. Si nada -> fallback final directo a Ollama (_fallback_ollama(), con
     SISTEMA_FALLBACK como system prompt situandolo como Nimbo) - ya NO cae a
     OpenClaw automaticamente. Si Ollama no esta corriendo se muestra un aviso
     pidiendo verificarlo, en vez de fallar en silencio; si esta corriendo pero
     tarda mas del timeout (ver services/ollama_service.py mas abajo) se avisa que
     esta procesando, sin decir que esta caido (son dos mensajes distintos, ver
     MENSAJE_TIMEOUT abajo). OpenClaw sigue existiendo como opcion MANUAL (boton en
     el dashboard, /api/openclaw/chat en app.py) - ver Stack arriba. Este mismo
     _fallback_ollama() tambien se usa cuando la clarificacion del paso 3.5 tampoco
     logra detectar nada en la respuesta del usuario (step "clarificando", ver mas
     abajo en send()).
- services/ollama_service.py: llamar_ollama(prompt, modelo="qwen2.5:7b", sistema=None,
  timeout=TIMEOUT_SEGUNDOS) y analizar_ollama(prompt) son las unicas dos funciones de
  entrada a Ollama en todo el codebase. analizar_ollama(prompt) es solo
  llamar_ollama(prompt, timeout=TIMEOUT_ANALISIS_SEGUNDOS) - mismo (y unico) modelo
  que el resto (ver Stack arriba, se probo con gemma2:9b aparte y se descarto por
  RAM/latencia), pero con mas tiempo porque sus prompts son mas largos/complejos.
  TIMEOUT_SEGUNDOS = 180 (chat/traduccion/contenido), TIMEOUT_ANALISIS_SEGUNDOS = 300
  (analisis financieros/estrategicos) - subidos desde 60s despues de que las pruebas
  mostraran que este hardware (CPU sin GPU) supera 60s facilmente con prompts largos
  o al recargar un modelo distinto en memoria.
  - Nunca lanzan excepcion: si Ollama no esta corriendo (o responde algo invalido)
    devuelven None; si la llamada se corta especificamente por timeout devuelven
    MENSAJE_TIMEOUT ("Ollama esta procesando, esto puede tardar un momento...") en
    vez de None - Ollama SI esta corriendo, solo tardo mas de la cuenta, y antes ese
    caso se mostraba con el mismo texto engañoso que "Ollama no esta corriendo"
    (confundio a mas de un chequeo manual). Como MENSAJE_TIMEOUT es un string no
    vacio, el patron `texto if texto else "<mensaje fijo>"` que ya usaban todos los
    callers (core/nimbo.py, tools/contabilidad_tool.py, tools/evento_tool.py,
    tools/contenido_tool.py) lo deja pasar tal cual sin que haya hecho falta tocar
    ninguno de esos call sites - excepto _translate() y _analizar_intencion_vaga()
    en core/nimbo.py, que SI se les agrego un chequeo explicito
    `if not texto or texto == MENSAJE_TIMEOUT: return None` porque ahi "texto" es un
    valor intermedio (se reinterpreta como comando traducido o pregunta de
    clarificacion), no la respuesta final que ve el usuario - sin ese chequeo,
    MENSAJE_TIMEOUT se hubiera colado como si fuera un comando real o una pregunta
    real en vez de caer al siguiente paso del pipeline como corresponde.
  - ollama_disponible() hace un chequeo rapido con GET /api/tags (igual que
    `curl http://localhost:11434/api/tags`) para quien quiera verificar
    disponibilidad sin hacer una llamada de chat completa - no la usa ningun caller
    todavia (ver mas abajo el aviso sobre confundirla con MENSAJE_TIMEOUT).
  - Con un solo modelo siempre cargado no hay penalidad de recarga entre llamadas
    (antes, alternar entre 2 modelos distintos podia consumir el timeout completo
    solo en la recarga). Los analisis largos (sugerencias_precios_tool,
    analisis_completo_tool) igual pueden superar TIMEOUT_ANALISIS_SEGUNDOS por lo
    largo del prompt en si - en ese caso sugerencias_precios_tool cae a su resumen
    determinista sin IA (_resumen_sin_ia(), ya existia antes de este cambio) y
    analisis_completo_tool muestra MENSAJE_TIMEOUT tal cual ("Ollama esta
    procesando, esto puede tardar un momento...", sin el prefijo "No pude generar
    el analisis:" - ese prefijo solo se antepone cuando texto es None/vacio, no
    cuando ya trae MENSAJE_TIMEOUT, que es un string no vacio y se devuelve directo).

Auto-focus permanente en #chat-input (templates/index.html, funcion
refocusInputActivo() + listener global `document.addEventListener('click', ...)`):
al entrar al panel Chat (showPanel), despues de mandar un mensaje (sendChat, tanto
si la respuesta llega bien como si falla), y al hacer click en cualquier parte de
la pantalla que no sea un boton/link/input/textarea/select ni dentro de un modal
abierto - asi el lector de codigo de barras (que escribe como si fuera un teclado)
siempre le llega al chat sin que el usuario tenga que hacer click primero en el
campo. Mismo mecanismo se reusa para el buscador de Caja, ver seccion Caja
Registradora mas abajo - refocusInputActivo() decide a cual de los dos enfocar
segun cual panel este activo (`panel-chat`/`panel-caja`), o no hace nada si hay un
modal abierto encima (para no robarle el foco a un campo como la contraseña de
identificacion de cobro).

## Login y roles
- Flask-Login. Roles: admin (acceso total), empleado (solo inventario, ventas y clientes;
  el resto de categorias de intent quedan bloqueadas tanto en las rutas API como dentro
  del chat, ver core/action_engine.py) y tecnico (solo Servicio Tecnico - ver mas abajo).
  core/action_engine.py.CATEGORIAS_POR_ROL mapea cada rol no-admin a su propio set de
  categorias permitidas (CATEGORIAS_EMPLEADO / CATEGORIAS_TECNICO = {"service"}); un rol
  que no aparece en ese dict no tiene ninguna categoria permitida por defecto (deny-by-default).
- Usuario.Telefono (ALTER TABLE, migracion en core/auth.py init_usuarios()) - necesario para
  que Nimbo pueda avisar a un tecnico por WhatsApp cuando se le asigna una orden. Se pide en
  el formulario "Nuevo usuario" del dashboard (obligatorio en el frontend si el rol es
  tecnico, no hay validacion equivalente en el backend). core.auth.listar_tecnicos() trae
  los tecnicos activos (Id, Nombre, Username, Telefono) para ofrecerlos al crear una orden.
- El dashboard oculta del sidebar todo lo que no sea Dashboard/Chat IA/Servicio Tecnico para
  rol tecnico (templates/index.html, bloques `{% if rol != 'tecnico' %}` / `{% if rol ==
  'admin' or rol == 'tecnico' %}`) - incluye tambien los accesos rapidos del panel Dashboard
  (antes tenian botones sueltos a Inventario/Analisis/Contenido sin gate de rol, lo que le
  hubiera permitido a un tecnico saltarse el sidebar oculto con esos atajos; ahora tecnico ve
  en su lugar un acceso directo a Servicio Tecnico). Los endpoints /api/servicio/* usan un
  decorador nuevo admin_o_tecnico_required (ademas de admin_required) para que la
  restriccion no dependa solo de ocultar botones en el HTML. Los widgets del Dashboard que
  siguen siendo @admin_required (recordatorios, alertas de precio, punto de equilibrio,
  cotizaciones) no se ocultaron especificamente para tecnico - su API ya rechaza el rol, asi
  que el tecnico solo veria esas tarjetas vacias/con error si entrara al Dashboard, no datos
  reales; no se considero necesario ocultar tambien esas tarjetas.
- Primera instalacion: mientras Configuracion.onboarding_completado != "1", cualquier
  ruta redirige a /setup, que a su vez redirige a /setup/<paso> (wizard de 7 pasos,
  progreso guardado en Configuracion.onboarding_step, templates/setup.html):
  1. Bienvenida (nombre del negocio*, tipo*, pais* -default Guatemala-, NIT, telefono,
     correo, direccion - solo nombre/tipo/pais son obligatorios). Guarda negocio_nombre/
     negocio_tipo/negocio_pais/negocio_nit/negocio_telefono/negocio_correo/
     negocio_direccion.
  2. Cuenta admin (nombre, usuario, contrasena, correo) -> crea el usuario admin
     (crear_usuario(..., "admin")). El correo se guarda como admin_email (antes se
     guardaba como "negocio_email" - se renombro porque paso 1 ahora tiene su propio
     correo de negocio separado; admin_email es solo informativo/para el resumen, la
     recuperacion de contrasena real sigue usando la env var ADMIN_EMAIL, sin relacion
     con este campo).
  3. Configuracion financiera: moneda (default Q), cobra_iva si/no (si -> iva_porcentaje
     fijo en "12"), usa_pos si/no (si -> muestra el campo comision_pos, default 6%,
     oculto con JS si no), isr_trimestral si/no (si -> isr_porcentaje fijo en "5"). Estos
     valores quedan en Configuracion solo como referencia/resumen - el 12%/6%/5% que ya
     usa el resto del sistema (declaracion de IVA, sugerencias de precio, punto de
     equilibrio, balance mensual - ver esas secciones) sigue hardcodeado en Python en
     vez de leer estas claves nuevas, no se rewireo ese calculo como parte de este
     feature.
  4. Horario del negocio: dias laborales (lunes a sabado por defecto), hora apertura
     (08:00 default), hora cierre (18:00 default).
  5. Configuracion de caja (opcional, se puede saltar): fondo inicial de caja en Q. Si
     se da un monto, ademas de guardarlo en caja_fondo_inicial se escribe tambien en
     Configuracion.caja_fondo_sugerido - la misma clave que database.nimbo_db.
     cerrar_turno() usa para sugerir el fondo del turno siguiente (ver seccion Caja
     Registradora) - asi el primer "abrir caja" del negocio (por chat o desde la UI) ya
     llega con este monto sugerido en vez de pedir contar denominacion por denominacion.
  6. Primer empleado (opcional, se puede saltar): nombre, usuario, contrasena, rol
     (empleado/tecnico), telefono -> crea el usuario con crear_usuario(). El telefono es
     obligatorio en el frontend si el rol es tecnico (mismo criterio que el panel
     "Usuarios" del dashboard, sin validacion equivalente en el backend).
  7. Resumen (incluye NIT/telefono/correo/direccion del negocio, IVA/POS/ISR, fondo de
     caja y primer empleado solo si se llenaron) + boton "Comenzar a usar Nimbo" ->
     marca onboarding_completado="1" y redirige a /login.
  No se puede saltar a un paso mas adelante del progreso guardado (antes-request
  rebota al paso actual); si se completa, /setup redirige directo a /login.
  Instalaciones que ya tenian usuarios antes de que existiera el wizard se marcan
  como completas automaticamente al arrancar (ver app.py, justo despues de
  init_usuarios()/init_configuracion()).
  Cada campo no obvio tiene un icono ℹ️ con un tooltip en espanol (CSS puro, sin
  librerias - macro Jinja `tip()` en templates/setup.html) explicando que es y por que
  se pide (ej. NIT, comision POS, ISR, fondo de caja).
- Demo del onboarding: boton "🔍 Ver demo del onboarding" en /login (templates/login.html,
  dentro de `{% if not current_user.is_authenticated %}` - aunque en la practica login.html
  nunca se renderiza para un usuario ya autenticado, la ruta /login redirige a / de una vez,
  ver app.py login()) -> /setup/demo -> /setup/demo/<paso> (app.py setup_demo/
  setup_demo_paso). Reutiliza el mismo template setup.html con `demo=True`: cada form pasa de
  POST a GET y su action apunta directo al siguiente paso (`next_action()`, macro Jinja) en
  vez de a la ruta real de /setup/<paso> - por eso nada de lo que se escribe en la demo llega
  a set_config()/crear_usuario(), ni pasa por ninguna validacion de backend. El resumen del
  paso 7 usa un diccionario fijo de ejemplo (DEMO_RESUMEN_EJEMPLO en app.py) en vez de leer
  Configuracion - /setup/demo no requiere login, asi que jamas debe mostrar datos reales del
  negocio. Un banner "Modo demo - nada se guarda" con link "Salir" (a /login) se muestra en
  todos los pasos. El boton final del paso 7 tambien cambia: en modo real hace POST y marca
  onboarding_completado, en demo es un boton que solo redirige a /login sin tocar nada.
  setup_demo/setup_demo_paso estan exentos del before_request require_setup (igual que
  setup/setup_paso) para que la demo funcione incluso en una instalacion que todavia no
  completo el onboarding real.
- Gestion de usuarios: panel "Usuarios" en el dashboard (solo admin) -> listar, crear,
  activar/desactivar, y cambiar contrasena de cualquier usuario sin pedir la actual.
  Backend: /api/usuarios (GET/POST), /api/usuarios/<id>/toggle, /api/usuarios/<id>/password.
- Configuracion del negocio: panel "Configuración" en el dashboard (solo admin, sidebar
  seccion Sistema junto a Usuarios) -> edita despues, sin resetear onboarding_completado, la
  misma info que se recopila en los pasos 1 (datos del negocio), 3 (financiera), 4 (horario)
  y 5 (fondo de caja) del wizard de /setup. No incluye la cuenta admin (paso 2) ni el primer
  empleado (paso 6) - esos se gestionan desde el panel "Usuarios" ya existente, no desde aqui.
  Backend: GET/PUT /api/configuracion/negocio (CONFIG_NEGOCIO_KEYS en app.py), misma
  validacion que /setup/3 (nombre/tipo/pais obligatorios, comision_pos solo se guarda si
  usa_pos='si', etc.) y el mismo efecto secundario que el paso 5 del onboarding: si se guarda
  un fondo de caja, tambien actualiza Configuracion.caja_fondo_sugerido (ver seccion Caja
  Registradora - "Fondo inicial automatico"). El nombre del negocio en el sidebar
  (#sidebar-negocio-nombre) se actualiza en el momento al guardar, sin recargar la pagina.
- Recuperacion de contrasena (solo admin): /forgot-password pide el correo, si coincide
  con ADMIN_EMAIL genera un token (tabla PasswordResetToken, expira en 1 hora) y envia un
  link por correo (Flask-Mail) a /reset-password?token=. Logging detallado de errores SMTP
  en services/mail_service.py.
- core/auth.py - Usuario, PasswordResetToken, hashing (werkzeug), tokens de reset
- core/configuracion.py - tabla Configuracion (clave/valor) para datos del negocio

## Estructura de archivos
- app.py - Flask principal, rutas de auth/setup y todas las rutas API
- core/nimbo.py - NimboCore con flujos conversacionales + clarificacion de intenciones vagas
- core/chat_context.py - Carga y recorta el historial reciente de ChatHistorial (entre dias)
  para pasarlo como contexto a Ollama (ver "Arquitectura del chat" mas abajo)
- core/intent_detector.py - Carga todos los detectores
- core/command_normalizer.py - Corrige errores tipograficos comunes (ej. "cuchila"->"cuchilla")
  palabra por palabra (diccionario + difflib.get_close_matches contra un vocabulario de
  verbos/sustantivos del negocio) y quita acentos, antes de que el mensaje llegue a los
  detectores. Corre una sola vez, al inicio de IntentDetector.detect().
- core/action_engine.py - Orquestador, aplica el gate de roles admin/empleado por categoria de intent
- core/auth.py - Login, usuarios, roles, recuperacion de contrasena
- core/configuracion.py - Configuracion del negocio (clave/valor)
- core/detectors/ - inventory, service, cliente, venta, proveedor, contenido, reporte, evento, contabilidad, cotizacion, caja
- tools/ - mismo set de modulos, carga automatica via __init__.py
- database/nimbo_db.py - Todas las funciones de BD (se llamaba database/aronium.py, de
  cuando todo el acceso a datos pasaba por Aronium - ya no es el caso, ver "Catalogo propio
  (Producto/Stock)" mas abajo; se renombro a nimbo_db.py y se actualizaron todos los imports
  del proyecto para que el nombre del archivo refleje lo que hace hoy). get_products(search)
  intenta busqueda fuzzy con
  difflib.SequenceMatcher (contra el nombre completo y cada palabra del nombre) si la
  busqueda exacta (LIKE) no encuentra nada. services/inventory.py delega su search()
  aqui para heredar el mismo fallback. get_product_by_id(id)/get_product_by_code(code) para
  lookup exacto (usado por Caja y por cotizacion.aceptar en vez de la busqueda fuzzy).
- services/whatsapp.py - WhatsApp Business API
- services/social_media.py - Facebook/Instagram API
- services/video_gen.py - Veo 3 video generation
- services/mail_service.py - Envio de correo (Flask-Mail) + logging de errores SMTP
- services/pdf_cotizacion.py - Genera el PDF de cotizaciones (reportlab), logo static/icon.png,
  guardado en static/cotizaciones/COT-XXXX.pdf (publico, sin login, para poder compartirse por WhatsApp)
- services/ticket.py - Genera el texto plano del ticket de caja (32 columnas, formato thermal 58mm)
- static/fotos/ - Fotos de productos
- static/videos/ - Videos generados
- templates/index.html - Frontend completo (dashboard, panel Usuarios solo admin)
- templates/login.html, setup.html, forgot_password.html, reset_password.html

## Modulos completados
- Catalogo propio (Producto/Stock): hasta esta migracion, el catalogo de productos y las
  cantidades en stock vivian unicamente en pos.db (Aronium) - Nimbo dependia de que Aronium
  estuviera instalado y accesible (via ARONIUM_DB_PATH) para casi cualquier operacion de
  inventario/ventas. Ahora viven en 2 tablas propias de nimbo.db:
  - Producto (Id, Codigo, Nombre, Precio, Costo, Categoria, Descripcion, Unidad, Activo,
    FechaCreado). Categoria y Unidad existen en el esquema pero ningun flujo las llena
    todavia (quedan para una integracion futura, ej. Unidad con las presentaciones de
    "Unidades de medida" mas abajo, que hoy vive en su propia tabla UnidadMedida sin
    relacion con esta columna). Descripcion tampoco se usa activamente - la descripcion
    "real" de un producto para el chat/pagina publica sigue siendo ProductoInfo
    (set_descripcion_producto/get_descripcion_producto, ver seccion Contenido), Producto.
    Descripcion solo se lee como fallback en get_product_by_code() si ProductoInfo no
    tiene nada, igual que antes se leia Product.Description de Aronium.
  - Stock (Id, ProductoId UNIQUE, Cantidad, StockMinimo, UltimaActualizacion). Aronium
    soportaba multiples almacenes (WarehouseId); como nada en el codebase pasaba nunca un
    warehouse_id distinto de 1, la tabla propia es 1 fila por producto y ese concepto se
    dejo fuera. StockMinimo es un campo nuevo en el esquema pero NO esta conectado a nada
    todavia (queda en 0) - el stock minimo por producto que de verdad usan get_alertas_stock/
    get_pedidos_sugeridos/set_stock_minimo sigue siendo la tabla StockMinimo ya existente
    (ProductId/ProductName/Minimo), que no se toco; son dos campos con el mismo proposito
    sin consolidar, pendiente para una limpieza futura.
  - database.nimbo_db.init_productos() crea ambas tablas (se llama en app.py junto al resto
    de init_*). En su momento, database.nimbo_db.migrar_productos_desde_aronium() se corria
    una sola vez despues (tambien en app.py) para copiar el catalogo Product/Stock de pos.db
    (Aronium) preservando EXACTAMENTE el mismo Id que tenian los productos en Aronium -
    critico porque Kardex, GarantiaProducto, ItemCombo, UnidadMedida, StockMinimo, Descuento
    (tipo producto), CodigoBarrasGenerado y ProductoProveedor ya tenian filas en nimbo.db con
    un ProductId/ProductoId suelto (sin FK real) apuntando a ese Id - si la migracion hubiera
    reasignado Ids nuevos esas referencias habrian quedado huerfanas. Esa migracion ya se
    hizo (los Ids preservados siguen siendo la base de todas esas referencias hoy) y la
    funcion se elimino del codebase al remover por completo la integracion con Aronium (ver
    mas abajo y BUGS_Y_FIXES.md) - no queda ninguna dependencia de pos.db para crear una
    empresa nueva, que arranca directo con Producto/Stock vacios.
  - Funciones migradas en database/nimbo_db.py (mismos nombres, parametros y claves de
    retorno que antes - Id/Name/Code/Price/Cost/Stock/Description en ingles, aunque las
    columnas fisicas de Producto/Stock esten en espanol; nada que consuma estas funciones
    en el resto del codebase cambio): get_products(), get_product_by_code(),
    get_product_by_id(), get_low_stock(), add_stock(), remove_stock(), get_stock(),
    _buscar_productos_similares() (fallback fuzzy), get_valor_inventario(),
    get_margen_productos(), get_productos_sin_codigo(), asignar_codigo_barras(),
    _codigo_ean_existe(). add_stock()/remove_stock() conservan el parametro warehouse_id
    por compatibilidad de firma pero ya no lo usan. services/inventory.py (search,
    search_barcode, list) y las herramientas de creacion/edicion/eliminacion de producto
    (tools/inventory_tool.py, el flujo de creacion de producto por chat en core/nimbo.py,
    y /api/db/products en app.py) tambien se migraron a la tabla Producto propia.
    get_reporte_dia() tambien se migro en la parte que busca el costo de los productos
    vendidos por Nimbo (Venta.Descripcion) - antes ese lookup de costo iba, por error de
    diseno original, contra el Product de Aronium.
  - Remocion completa de Aronium (2026-08-06, ver BUGS_Y_FIXES.md): hasta esta limpieza,
    4 funciones seguian dependiendo de Aronium via database.nimbo_db.connect()/DB_PATH
    (ARONIUM_DB_PATH) - get_sales_today()/get_sales_month()/get_top_products() (leian
    Document/DocumentItem/Product, el historial de ventas nativo de la caja fisica de
    Aronium) y get_customers() (leia el catalogo nativo Customer de Aronium, sin relacion
    con la tabla Cliente de Nimbo) - ademas del calculo de costos_productos dentro de
    get_balance_mes() (mezclaba ingresos de Nimbo, tabla Venta, con costos de Document/
    DocumentItem de Aronium). Las 4 se reescribieron para leer solo tablas propias de
    Nimbo (Venta, Cliente, Producto): get_sales_today/month ahora agregan Venta.Total por
    fecha; get_top_products y el costos_productos de get_balance_mes extraen items de
    Venta.Descripcion con _extraer_items_venta() (best-effort, mismo criterio que
    get_patrones_ventas() - Venta no guarda un detalle estructurado de items, asi que
    get_top_products() ya no puede devolver un Total en quetzales por producto como antes,
    solo unidades vendidas); get_customers() ahora lee Cliente. connect()/DB_PATH
    (ARONIUM_DB_PATH) se eliminaron del codigo, junto con la seccion "INVENTARIO ARONIUM"
    de app.py (4 rutas que tambien leian pos.db directo adivinando nombres de tabla
    genericos - se reescribieron sobre las mismas tablas propias, ver seccion "Inventario"
    mas abajo) y el ping a Aronium de /api/status. Cambiar la metodologia de
    costos_productos puede mover los numeros de contabilidad que ya estaban en uso
    respecto a como se calculaban antes (ya no mezcla los dos sistemas de ventas).
- Inventario: CRUD, kardex, alertas stock, fotos, descripcion
  - Alertas predictivas: database.nimbo_db.get_alertas_predictivas() calcula, para cada
    producto, el promedio de unidades de SALIDA por dia en el Kardex de los ultimos 30 dias
    (DIAS_HISTORIAL_CONSUMO - incluye ventas y salidas manuales, cualquier egreso real de
    stock, no solo Razon='Venta') y proyecta dias_restantes = stock_actual / promedio_diario.
    Clasifica en CRITICO (<7 dias, DIAS_CRITICO_STOCK), ADVERTENCIA (7-21 dias,
    DIAS_ADVERTENCIA_STOCK) u OK (>21 dias); un producto sin ninguna salida en el periodo
    queda en SIN_DATOS (dias_restantes=None, no hay tasa de consumo con la que proyectar) en
    vez de asumir que nunca se agota. Lista ordenada de mas a menos urgente.
    database.nimbo_db.get_prediccion_producto(query) hace lo mismo para un solo producto
    (busqueda fuzzy con get_products(), mismo criterio que el resto del sistema).
  - Desde el chat: "alertas de inventario" / "alertas predictivas" (inventory.
    alertas_predictivas) lista los productos CRITICO/ADVERTENCIA agrupados; "cuando se acaban
    las cuchillas" / "en cuantos dias se acaban los empaques" (inventory.prediccion_producto,
    core/detectors/inventory_detector.py) da la prediccion de un producto especifico ("A este
    ritmo, [producto] se agota en N dia(s)..."). Los patrones con articulo (el/la/los/las) se
    revisan antes que los patrones sin articulo, y exigen `\s+` (no `\s*`) despues del
    articulo - con `?` opcional y `\s*` la alternancia "la" matcheaba como prefijo de "las" y
    dejaba una "s" suelta pegada al nombre del producto buscado.
  - Categoria "inventory" ya era de empleado (CATEGORIAS_EMPLEADO en core/action_engine.py),
    asi que estos comandos nuevos tambien quedan disponibles para el rol empleado sin cambios
    adicionales.
  - Recordatorios: get_recordatorios() agrega un recordatorio tipo "stock_predictivo" (urgencia
    alta) por cada producto CRITICO.
  - Widget en el dashboard (/api/inventario/alertas-predictivas, @login_required igual que
    /api/db/alertas - visible para empleado y admin): muestra solo los productos CRITICO con
    sus dias estimados; si no hay ninguno muestra "Sin productos criticos".
  - Importacion masiva de productos (Excel/CSV): boton "📦 Importar desde Excel" fijo en el
    panel Inventario del dashboard (templates/index.html, junto a "+ Agregar" y a
    "📄 Descargar template" - ambos siempre visibles para el admin, no solo dentro de un
    flujo especial), abre el modal modal-importar-productos. Columnas reconocidas (con o
    sin acentos/mayusculas/espacios, app.py _normalizar_header): Nombre y Precio
    obligatorias; Costo, Codigo, Stock, StockMinimo, Categoria, Descripcion, Unidad
    opcionales (Descripcion/Unidad agregadas 2026-07-19 - antes se leian del archivo pero
    database.nimbo_db.crear_producto_importado() nunca las guardaba: Unidad quedaba
    siempre en el literal fijo "unidad" sin importar lo que trajera la fila, y Descripcion
    ni se intentaba leer; ahora ambas se guardan igual que el resto de columnas opcionales).
    - Preview + mapeo manual de columnas (2026-07-19, antes de esto la deteccion de
      columnas era 100% automatica y sin forma de corregirla): al elegir un archivo en el
      modal, POST /api/db/products/import/preview (multipart, sin importar nada todavia)
      devuelve los encabezados crudos, el mapeo automatico sugerido
      (app.py._mapeo_automatico(), mismo diccionario COLUMNAS_IMPORTACION_PRODUCTOS que ya
      usaba la importacion real) y las primeras 5 filas de datos. El modal muestra un
      <select> por columna (pre-seleccionado segun la sugerencia, con las opciones de
      CAMPOS_IMPORTACION_LABELS) para que el admin corrija el mapeo si sus encabezados no
      coinciden con ningun sinonimo conocido (ej. "Nombre Producto", "Precio Venta"). Al
      confirmar, POST /api/db/products/import (el mismo endpoint de siempre) recibe ademas
      un campo de formulario opcional "mapeo" (JSON, {indice_columna: campo_interno}) que
      reemplaza por completo la deteccion automatica cuando viene presente -
      app.py._leer_archivo_productos(archivo, mapeo_manual=None) - si no se manda mapeo
      (ej. una integracion externa que llame al endpoint directo) el comportamiento es
      exactamente el de antes.
    - Boton "Descargar template" (GET /api/db/products/plantilla, mismo endpoint de
      siempre, contenido reescrito 2026-07-19) genera un .xlsx en memoria (openpyxl,
      nombre de descarga template_inventario_nimbo.xlsx) con columnas Nombre, Codigo,
      Precio, Costo, Stock, Descripcion, Unidad - una fila de ejemplo ya llena, una fila en
      blanco lista para escribir, y una segunda hoja "Instrucciones" explicando que va en
      cada columna. Mismo boton usado desde el modal de Inventario, el boton fijo del panel
      Inventario, y el mensaje del chat cuando la empresa no tiene productos (ver
      "Chat inteligente segun estado del inventario" mas abajo).
    - POST /api/db/products/import (multipart, campo "archivo", @login_required):
      app.py._leer_archivo_productos() detecta .csv (modulo csv, decodifica utf-8-sig para
      tolerar el BOM que agrega Excel) o .xlsx/.xls (openpyxl, data_only=True). Cada fila se
      normaliza a un dict (nombre, precio, costo, codigo, stock, stock_minimo, categoria,
      descripcion, unidad) - los opcionales quedan en None si la celda vino vacia, SIN
      aplicarles todavia ningun default (el default se aplica recien al crear, ver mas
      abajo) para poder distinguir "no vino en el archivo" de "vino en 0" cuando se trata de
      una actualizacion. Filas sin Nombre se ignoran en silencio (fila vacia); filas con
      Precio faltante o <= 0 se reportan en "errores" (fila, motivo) sin bloquear el resto
      del archivo.
    - Deteccion de duplicados: database.nimbo_db.buscar_producto_duplicado(nombre, codigo)
      busca primero por Codigo exacto (si la fila trae uno) y si no por similitud de Nombre
      (mismo difflib.SequenceMatcher y UMBRAL_SIMILITUD_PRODUCTO que usa la busqueda fuzzy de
      get_products()). Las filas sin duplicado se crean de inmediato
      (database.nimbo_db.crear_producto_importado - aqui si se aplican los defaults: Costo 0,
      Stock 0, StockMinimo 5; si la fila no trae Codigo se le genera un EAN-13 automatico via
      asignar_codigo_barras(), igual que "generar codigo" del chat). Las filas con duplicado
      NO se crean todavia - la respuesta del endpoint las devuelve en "duplicados" (la fila
      entrante + el producto existente que matcheo) para que el dashboard le pregunte al
      usuario que hacer con cada una, en vez de decidir solo.
    - El modal muestra cada duplicado con 3 botones - Actualizar existente / Crear como nuevo
      / Saltar (un boton mas que lo pedido originalmente: "crear como nuevo" cubre el caso de
      un falso positivo de la busqueda fuzzy, ej. "Licuadora Oster" vs "Licuadora Oster Mini"
      son productos distintos aunque el nombre se parezca) - mas botones "Actualizar todos" /
      "Saltar todos" para no tener que decidir fila por fila si el usuario ya sabe que quiere
      para todo el lote. Al confirmar, el frontend manda TODAS las filas+decisiones juntas
      (sin volver a subir el archivo) a POST /api/db/products/import/resolver (JSON, no
      multipart): "actualizar" llama a database.nimbo_db.actualizar_producto_importado(), que
      solo pisa los campos que la fila trae (Costo/Stock/StockMinimo/Categoria/Descripcion/
      Unidad en None no se tocan) - para que reimportar un archivo que solo trae precios
      actualizados no vacie el stock existente por accidente; el Codigo del producto
      existente tampoco se pisa si ya tenia uno (evita choques de codigos). "crear" llama a
      crear_producto_importado() igual que una fila sin duplicado. "saltar" no hace nada.
  - Chat inteligente segun estado del inventario (2026-07-19): index() en app.py calcula
    sin_inventario = database.nimbo_db.contar_productos() == 0 y lo pasa al template junto
    a chat_tutorial_pendiente (ver seccion "Diagnostico de negocio + tour del dashboard +
    tutorial del chat" mas abajo). La primera vez que se abre el chat
    (mostrarTutorialChatSiCorresponde() en templates/index.html), si sin_inventario es
    true muestra un mensaje distinto al tutorial normal: explica que hace falta cargar
    productos antes de poder ayudar con ventas/reportes, con 2 botones funcionales (no
    decorativos) - "📥 Subir mi Excel" (llama a abrirImportarProductos(), el mismo modal de
    Inventario) y "📋 Descargar template" (llama a descargarPlantillaProductos()) - y
    menciona la alternativa de agregar productos uno por uno por chat. Si la empresa ya
    tiene productos, se muestra el tutorial normal sin cambios; si el tutorial ya se
    mostro antes (Configuracion.chat_tutorial_mostrado="1"), no se muestra nada, sin
    importar el estado del inventario - la clave se marca una sola vez, no se re-evalua
    despues de la primera vez que se abre el chat.
  - Etiquetas desde el dashboard: boton 🏷 por fila en la tabla de Inventario
    (GET /api/db/products/<id>/etiqueta, @login_required) - si el producto no tiene Codigo se
    lo genera de una vez (asignar_codigo_barras) y genera su PDF de etiqueta con
    services/barcode_service.generar_etiqueta_producto_pdf() (la misma funcion que ya usaba
    el comando de chat "etiqueta de X"), devuelve la ruta y el frontend la abre en pestana
    nueva. Antes de esto la unica forma de generar una etiqueta era escribiendole al chat.
  - El escaneo de codigo de barras (el lector USB/Bluetooth actua como teclado, escribe el
    codigo + Enter en el campo que este enfocado) ya funciona sin cambios adicionales en
    #inv-search: get_products() ya busca por Nombre O Codigo, asi que enfocar el buscador de
    Inventario y escanear encuentra el producto igual que escribir su nombre.
  - Importar productos y crear producto desde el chat (complementa la importacion masiva
    del dashboard, ver arriba):
    - "importar productos" / "cargar productos" (y variantes: "importar/cargar producto",
      "importar productos desde excel/csv", "importar excel", "importar inventario" -
      IMPORTAR_EXACT en core/detectors/inventory_detector.py) no sube ningun archivo por
      chat (no es posible) - tools/inventory_tool.py importar_instrucciones_tool() responde
      con los pasos para usar el boton "📦 Importar Excel/CSV" del dashboard (Inventario) y
      un link `<a href="/">` para llegar ahi.
    - "agregar producto X precio N costo N stock N" / "nuevo producto X precio N ..." /
      "crear producto X precio N ..." (CREATE_NATURAL_PATTERNS en inventory_detector.py,
      distinto del patron rigido preexistente "crear NOMBRE / precio: N / costo: N") crea el
      producto de una sola vez si el mensaje ya trae Precio y Costo (Stock es siempre
      opcional, si no viene se crea con 0 - nunca se pregunta). Costo y Stock se buscan en
      cualquier orden despues de "precio N", asi que "... precio 95 stock 10 costo 28"
      tambien funciona igual que "... precio 95 costo 28 stock 10".
    - Si falta Precio y/o Costo, create_product_tool (tools/inventory_tool.py) retorna el
      marcador PRODUCTO_NUEVO_INICIO:nombre|precio|costo|cantidad (los que faltan van vacios)
      que arranca el step producto_waiting_precio (si falta precio) o directo
      producto_waiting_costo (si el precio ya vino) en core/nimbo.py, preguntando solo lo que
      falta uno por uno. Al completarse llama a tools/inventory_tool._crear_producto_directo()
      (extraida como funcion compartida - antes esta insercion estaba duplicada entre
      create_product_tool y el step waiting_cost de un flujo distinto, ver mas abajo).
    - Este flujo es DISTINTO del ya existente waiting_price/waiting_cost (arrancado cuando
      "agregar N [producto]" no encuentra el producto - ver seccion Kardex/Stock mas abajo si
      aplica): ese es un fallback de "agregar stock a un producto que no existe todavia", no
      un comando explicito de creacion, y nunca parsea precio/costo/stock que ya vengan en el
      mensaje original (siempre pregunta ambos desde cero). Se dejaron ambos flujos separados
      a proposito para no mezclar sus dos disparadores distintos, aunque los dos terminan
      llamando a la misma _crear_producto_directo().
    - Se encontro y corrigio un choque real entre detectores al implementar esto:
      core/detectors/contabilidad_detector.py.PATTERNS_GASTO tiene un patron generico
      `"(.+) costo N"` (para "la reparacion costo 200" = gasto), y ContabilidadDetector se
      revisa antes que InventoryDetector en core/intent_detector.py - por eso "nuevo producto
      X precio N costo N" (sin Stock al final, asi que "costo N" queda literal al final del
      mensaje) se interpretaba como un gasto en vez de una creacion de producto. Se le agrego
      un lookahead negativo a ese patron para excluir mensajes que empiecen con
      "agregar/agrega/nuevo/crear producto " - mismo tipo de fix que ya existia para
      "cliente aprobo/rechazo" (cliente_detector.py) y "garantia de reparacion"
      (garantia_detector.py).
    - Categoria "inventory" ya era de empleado, asi que estos comandos tambien quedan
      disponibles para el rol empleado sin cambios adicionales.
  - Escaneo de codigo de barras directo en el chat: el lector USB/Bluetooth escribe el
    codigo + Enter como si fuera un mensaje normal - sin ningun verbo alrededor, a
    diferencia del resto de comandos de inventario. BARCODE_PATTERNS en
    core/detectors/inventory_detector.py detecta esto revisando si el mensaje COMPLETO
    es un codigo "pelado": solo digitos (6-13, cubre desde codigos cortos legados hasta
    el EAN-13 completo de generar_ean13()) o alfanumerico corto tipo "LIC001" (4-12
    caracteres, exige al menos una letra y un digito para no chocar con una busqueda de
    producto por nombre normal). Tiene un lookahead negativo para excluir los numeros de
    referencia propios de la app que tambien son alfanumericos cortos - OS-XXXX
    (Servicio Tecnico), GAR-XXXX/GARR-XXXX (garantias), COT-XXXX (cotizaciones) - y
    "QNNN" (mencion de precio, no codigo). Produce intent "inventory.scan_barcode".
    - tools/inventory_tool.py escanear_codigo_tool(codigo) busca con
      database.nimbo_db.get_product_by_code_ci() (case-insensitive - el mensaje ya paso
      por CommandNormalizer, todo en minusculas, y algunos codigos legados como "LIC001"
      se guardaron con mayusculas).
    - Si encuentra el producto: arranca BARCODE_INICIO: (core/nimbo.py) que muestra foto
      (si tiene, get_foto_producto), nombre, codigo, precio y existencias, y pregunta
      "Quieres vender este producto? (si/no) o escribe la cantidad" (step
      barcode_waiting_accion). "si" o cualquier numero > 0 descuenta el stock
      (remove_stock, razon="Venta") y arranca el MISMO flujo de venta simple del chat
      (step venta_waiting_nombre, ver seccion Ventas) con venta_ctx ya armado - se
      reutiliza tal cual la maquina de estados existente (cliente, puntos, credito,
      metodo de pago, factura) en vez de duplicarla, asi que hereda gratis la
      cancelacion universal (revierte el stock si se cancela a medio camino) y todo lo
      demas. "no" solo muestra la info sin vender ni tocar stock.
    - Si NO encuentra el producto: arranca CODIGO_NO_ENCONTRADO_INICIO: - "Codigo 'X' no
      registrado. Quieres agregarlo como producto nuevo? (si/no)" (step
      barcode_waiting_crear). "si" pide el nombre (step barcode_waiting_nombre_nuevo) y
      de ahi entra al mismo flujo producto_waiting_precio/producto_waiting_costo de
      "agregar producto" (ver arriba) con el codigo escaneado ya prellenado -
      _crear_producto_directo() ahora acepta un parametro codigo opcional para esto.
- Ventas: flujo completo, WhatsApp, descuento stock automatico
- Clientes: historial completo, Excel, cumpleanos. "historial de Juan Perez" (cliente.historial,
  tools/cliente_tool.py) muestra todo desde el primer dia: datos (telefono/email/NIT/fecha de
  alta), estadisticas (total gastado, producto favorito, frecuencia de compra en dias promedio,
  ultima visita, descuento tipo cliente si tiene uno configurado - ver database.nimbo_db.
  get_descuentos), compras (Descripcion + Total + metodo de pago), ordenes de servicio,
  cotizaciones y garantias activas. database.nimbo_db.get_historial_cliente(cliente_id,
  meses=None) trae ventas/ordenes/cotizaciones/garantias vigentes (meses=None = sin limite de
  tiempo; si se pasa un numero, acota las ventas a esos ultimos meses). "resumen de Juan Perez"
  (cliente.resumen) es la version corta: solo estadisticas + garantias activas, sin la lista
  completa de compras/ordenes/cotizaciones. El "producto favorito" y el "metodo de pago" se
  extraen por texto de Venta.Descripcion de forma best-effort (no hay detalle estructurado de
  items por venta, ver seccion Caja arriba) - el metodo de pago solo se detecta cuando fue un
  pago mixto (unico caso que deja un rastro reconocible en la Descripcion, ver core/nimbo.py);
  para efectivo/tarjeta/transferencia simple se muestra "no registrado".
- Servicio Tecnico: OS-XXXX, flujo 7 estados, WhatsApp automatico. Garantia de reparacion:
  al marcar una orden como ENTREGADO (tools/service_tool.py cambiar_estado_tool), en vez de
  actualizar el estado de una vez, retorna el marcador ENTREGA_GARANTIA_INICIO:OS-XXXX que
  arranca el step servicio_waiting_dias_garantia en core/nimbo.py (pregunta "Cuantos dias de
  garantia tiene esta reparacion?", default database.nimbo_db.DIAS_GARANTIA_REPARACION_DEFAULT
  = 30, acepta 'default' o un numero). Con la respuesta ya se marca ENTREGADO
  (actualizar_estado_orden) y se genera la garantia (database.nimbo_db.
  generar_garantia_reparacion) - reutiliza la MISMA tabla GarantiaVenta de las garantias de
  producto, distinguida por la columna Tipo ('producto' default o 'reparacion', agregada con
  ALTER TABLE en init_garantias() porque la tabla ya existia de antes) y OrdenServicioId (para
  vincularla a la orden; no tiene VentaId porque no es una venta de producto). Numeracion
  aparte: GARR-XXXX en vez de GAR-XXXX (secuencia propia, WHERE Tipo='reparacion'). El mensaje
  de WhatsApp de entrega (antes solo se enviaba para LISTO, nunca para ENTREGADO) ahora si se
  manda en ENTREGADO e incluye "Su reparacion tiene garantia GARR-XXXX valida hasta [fecha]"
  (services/whatsapp.py enviar_notificacion_orden, parametro garantia).
  - "garantia de reparacion OS-0001" (service.ver_garantia_reparacion) muestra el estado y
    vencimiento de la garantia de esa orden (database.nimbo_db.get_garantia_reparacion_por_orden).
  - "reclamacion garantia OS-0001" / "reclamar garantia OS-0001" (service.reclamar_garantia,
    database.nimbo_db.reclamar_garantia_reparacion): verifica que la garantia siga VIGENTE (si
    esta VENCIDA o ya fue RECLAMADA antes, rechaza con el motivo), la marca RECLAMADA (unico
    lugar del codebase que usa ese estado - antes quedaba sin comando de chat, ver seccion
    Garantias) y crea una OrdenServicio nueva sin costo para el mismo cliente/equipo,
    anotando en Observaciones la garantia y orden originales.
  - Se aprovecho para cerrar una ambiguedad preexistente entre detectores: "garantia de
    reparacion X" coincidia tambien con el catch-all "garantias de X" (busqueda de garantias
    de un cliente) de core/detectors/garantia_detector.py, que se revisa antes que
    ServiceDetector - se le agrego un lookahead negativo para excluir "reparacion".
  - Fotos del equipo al recibirlo: tabla FotoOrdenServicio en nimbo.db (Id, OrdenId,
    NumeroOrden, RutaFoto, Descripcion, Fecha - database.nimbo_db.init_fotos_servicio/
    agregar_foto_orden/get_fotos_orden). Se suben desde el dashboard, no desde el chat (subir
    un archivo por chat no es posible) - panel "Servicio Tecnico" en el menu lateral
    (admin y tecnico - categoria "service" en core/action_engine.py, ver seccion "Flujo de
    tecnicos" mas abajo), templates/index.html panel-servicio: tabla simple de ordenes con
    boton 📷 "Subir foto" por fila (subirFotoServicio(), mismo patron que subirFoto() de
    productos: input file oculto -> FormData -> POST) y, si ya tiene fotos, un boton 🖼 con el
    conteo que abre un modal con las miniaturas (verFotosServicio()). Los 3 endpoints usan
    @admin_o_tecnico_required (no solo @login_required) para que un empleado no pueda llegar
    a ellos directo por URL aunque el boton/panel este oculto para su rol. Endpoints: POST
    /api/servicio/fotos (foto + numero_orden + descripcion opcional, guarda en
    static/fotos_servicio/OS-XXXX/uuid.ext, valida que la orden exista) y GET
    /api/servicio/fotos/<numero_orden>; GET /api/servicio/ordenes lista las ordenes para la
    tabla del panel (separado del tools/service_tool.py.listar_ordenes_tool, que devuelve
    texto para el chat, no JSON).
  - Desde el chat: "fotos de OS-0001" / "fotos OS-0001" (service.fotos,
    core/detectors/service_detector.py + tools/service_tool.py fotos_orden_tool) muestra las
    fotos como imagenes HTML inline (`<img>`, mismo patron que tools/contenido_tool.py para
    fotos de producto); si la orden no tiene fotos avisa que se suben desde el dashboard. "ver
    orden OS-0001" (service.buscar_orden) tambien agrega las miniaturas al final si la orden
    tiene fotos. Al crear una orden nueva (step service_waiting_problema en core/nimbo.py) el
    mensaje final ahora incluye "Puedes subir fotos del equipo en el dashboard, seccion
    Servicio Tecnico, orden OS-XXXX".
  - Flujo de tecnicos (rol "tecnico", ver seccion "Login y roles"): asignacion de tecnico,
    informe de revision con presupuesto automatico, aprobacion/rechazo del cliente y tarifas
    de mano de obra configurables.
    - Asignar tecnico: OrdenServicio.TecnicoId/TecnicoNombre (ALTER TABLE, migracion en
      database.nimbo_db.init_servicio_tecnico_ext() - reemplazan a la columna vieja "Tecnico",
      texto libre que nunca se conecto a ningun flujo). Al crear una orden, despues de
      "problema" el step service_waiting_tecnico (core/nimbo.py) lista los tecnicos activos
      (core.auth.listar_tecnicos()) y pide un numero, o "ninguno" para no asignar todavia (o
      si no hay ningun tecnico registrado). crear_orden() ahora acepta tecnico_id/
      tecnico_nombre. Si el tecnico elegido tiene Telefono, Nimbo le manda un WhatsApp
      (services/whatsapp.py enviar_asignacion_tecnico_whatsapp) con el numero de orden,
      equipo, cliente y problema descrito.
    - Informe de revision: tabla InformeRevision en nimbo.db (Id, OrdenId, NumeroOrden,
      TecnicoId, TecnicoNombre, Descripcion, ProductosNecesarios [JSON: [{nombre, cantidad,
      costo}]], ManoObra, Total, Fecha - database.nimbo_db.init_informes_revision/
      crear_informe_revision/get_informes_orden). "informe OS-0001: necesita cuchilla 1
      unidad y empaque 2 unidades mano de obra 75" (service.informe,
      core/detectors/service_detector.py + tools/service_tool.py informe_tool): separa el
      texto por " mano de obra N" al final, parte el resto por "," o " y " en items
      individuales ("cuchilla 1 unidad"), y por cada uno busca el producto en el inventario
      (database.nimbo_db.get_products(), mismo fuzzy fallback que el resto del sistema) para
      resolver el precio (Price, no Cost - es lo que se le cobra al cliente) automaticamente;
      si un producto no matchea nada se registra con costo Q0 y se avisa en la respuesta ("no
      encontre en inventario: X"). El TecnicoId/TecnicoNombre del informe se toma de
      flask_login.current_user (quien esta escribiendo el informe en ese momento, no
      necesariamente el mismo tecnico que quedo asignado en la orden - mismo criterio que
      anular_turno en core/nimbo.py, que tambien usa current_user.nombre directamente) - por
      eso informe_tool solo funciona dentro de una request real de Flask (no se puede probar
      llamando core.nimbo.send() en un script suelto sin app context, hay que usar
      app.test_client() con una sesion logueada).
    - Presupuesto automatico: crear_informe_revision() calcula presupuesto_repuestos = suma
      de costo*cantidad, total = presupuesto_repuestos + mano_obra, y llama a la funcion ya
      existente set_presupuesto_orden() (que ya actualizaba Presupuesto/ManoObra y ponia
      Estado='PRESUPUESTO' con su nota en HistorialOrden desde antes de este feature - nunca
      se habia conectado a nada que la disparara automaticamente). informe_tool arma el
      desglose completo ("Revision de X:\n- producto xN: QN\n...\n- Mano de obra: QN\nTotal:
      QN") y lo manda por WhatsApp al cliente completo (services/whatsapp.py
      enviar_presupuesto_whatsapp), ademas de mostrarlo en el chat.
    - Aprobacion/rechazo del cliente: "cliente aprobo OS-0001" / "cliente rechazo OS-0001"
      (service.aprobacion_cliente, core/detectors/service_detector.py + tools/service_tool.py
      aprobacion_cliente_tool). Aprobado -> actualizar_estado_orden a APROBADO + WhatsApp al
      tecnico asignado (busca su Telefono en Usuario por OrdenServicio.TecnicoId,
      enviar_aprobacion_tecnico_whatsapp). Rechazado -> nuevo estado RECHAZADO (no forma
      parte de la secuencia normal de 7 estados, es un estado terminal aparte) + WhatsApp al
      cliente avisando que puede recoger su equipo sin costo (enviar_rechazo_cliente_whatsapp).
      Se agrego un lookahead negativo en core/detectors/cliente_detector.py PATTERNS_BUSCAR
      (`r"^cliente\s+(?!aprobo\b|rechazo\b)(.+)$"`) porque ClienteDetector se revisa antes que
      ServiceDetector en core/intent_detector.py y su catch-all "cliente (.+)" interceptaba
      "cliente aprobo/rechazo OS-XXXX" como si fuera una busqueda de cliente por nombre
      (mismo tipo de ambiguedad que ya existia entre GarantiaDetector/ServiceDetector, ver
      mas arriba).
    - Tarifas de mano de obra: tabla TarifaManoObra en nimbo.db (Id, Descripcion, Precio,
      Activo - database.nimbo_db.init_tarifas_mano_obra/crear_tarifa/get_tarifas). "agregar
      tarifa revision basica Q50" (tarifa.agregar) / "ver tarifas" (tarifa.listar) - detector
      nuevo core/detectors/tarifa_detector.py + tools/tarifa_tool.py. Es solo un catalogo de
      referencia (no hay ningun lugar del codigo que lo consulte automaticamente): el tecnico
      sigue escribiendo el monto de mano de obra directo en el comando "informe": ("mano de
      obra 75"), las tarifas no se aplican solas. Categoria "tarifa" no esta en
      CATEGORIAS_EMPLEADO ni CATEGORIAS_TECNICO (admin-only, como el resto de configuracion
      de precios: descuento, garantia, combo).
    - Vocabulario del CommandNormalizer (core/command_normalizer.py): "mano" y "obra" no
      estaban en la lista y "obra" se corregia sola a "cobrar" (el par mas cercano en
      similitud de cadenas, cutoff 0.8) ANTES de que cualquier detector viera el mensaje -
      esto rompia silenciosamente tanto "informe OS-XXXX: ... mano de obra N" como el
      "presupuesto OS-XXXX es N mano de obra N" que ya existia desde antes. Se agregaron
      "mano", "obra", "presupuesto", "tecnico(s)", "informe(s)", "tarifa(s)", "aprobo",
      "rechazo", "asigna(da/do)", "necesita", "revision" al VOCABULARIO.
    - Widget de pipeline: GET /api/servicio/pipeline (@admin_o_tecnico_required,
      database.nimbo_db.get_pipeline_servicio() - COUNT(*) por Estado) alimenta una fila de
      tarjetas en panel-servicio (RECEPCION | REVISION | PRESUPUESTO | APROBADO | REPARACION
      | LISTO | ENTREGADO, mismo estilo .stat-card del Dashboard) mas una tarjeta aparte para
      RECHAZADO (solo se muestra si hay al menos una) porque no es parte de la secuencia del
      pipeline. loadPipelineServicio() en templates/index.html, se llama junto con
      loadOrdenesServicio() al entrar al panel.
- Proveedores: contactos, pedidos sugeridos, ordenes compra, alertas precio. El historial de
  proveedor requiere la palabra "compras" ("historial de compras a/de X", "compras a X", "cuanto
  le compre a X") - antes ese calificador era opcional en core/detectors/proveedor_detector.py y
  "historial de X" (sin "compras") interceptaba tambien el historial de clientes, porque
  ProveedorDetector se revisa antes que ClienteDetector en core/intent_detector.py. Sigue
  existiendo una ambiguedad menor sin resolver con "compras de X" (sin la palabra "historial"):
  matchea primero como proveedor.historial antes de llegar a ClienteDetector.
- Contabilidad: balance, IVA/ISR, margen, inventario valor, equilibrio, analisis Gemini, Excel, comparacion 6 meses,
  sugerencias de precios ("analiza mis precios" / "sugerencias de precios") -> contabilidad.sugerencias_precios
  en tools/contabilidad_tool.py. Calcula el margen real (Precio-Costo)/Precio por producto usando
  get_margen_productos(); si es menor a 30% calcula un precio sugerido deterministico en Python
  (costo / (1 - 6% comision POS - 30% margen objetivo)) y le pasa a Gemini los productos ya separados
  en dos grupos (saludable / necesita ajuste) para que solo narre el analisis sin recalcular ni inventar
  precios. Usa tambien get_balance_mes() (gastos operativos, ingresos) como contexto. Admin-only.
  - Declaracion mensual de IVA (SAT-2046, declaraguate.com): database.nimbo_db.
    get_declaracion_iva(mes=None, anio=None) - si no se especifica periodo, usa el mes recien
    cerrado (mes actual - 1), no el mes en curso todavia incompleto, porque ese es el periodo
    que efectivamente toca declarar dentro de los primeros 10 dias habiles del mes actual.
    Debito fiscal = ventas del periodo x 12/112 (se asume que el precio de venta YA incluye
    IVA, practica estandar en Guatemala para consumidor final - distinto del campo
    "iva_estimado" de get_balance_mes(), que es solo un estimado informativo separado y usa
    ingresos x 12% sin dividir, no se toco). Credito fiscal = 12% sobre el total de
    OrdenCompra del periodo con Total > 0 (las ordenes creadas por "genera orden para X" hoy
    siempre quedan en Q0 porque ese flujo no captura precio de compra - ver Pendiente #9 -
    por eso se filtra Total > 0 y la respuesta avisa explicitamente cuando el credito fiscal
    da Q0, para no confundirlo con "no compraste nada"). IVA a pagar = debito - credito; si
    sale negativo se reporta como credito fiscal a favor (remanente, no se implementa arrastre
    entre meses, solo se informa).
    - "declaracion de iva" / "iva del mes" / "resumen de iva" (contabilidad.declaracion_iva)
      da el resumen completo y genera un PDF de referencia (services/pdf_iva.py,
      generar_pdf_declaracion_iva() - mismo patron reportlab que services/pdf_cotizacion.py)
      guardado en la raiz del proyecto (NO en static/, a diferencia de las cotizaciones - es
      informacion financiera interna, se sirve solo logueado via /api/download/<filename>,
      mismo endpoint que ya usaba el Excel de contabilidad). "cuanto iva debo"
      (contabilidad.iva_rapido) da solo el monto a pagar, sin generar PDF.
    - Recordatorio automatico: get_recordatorios() agrega un aviso de urgencia alta del dia 1
      al 10 de cada mes ("Recuerda declarar el IVA del mes pasado") - el plazo real de la SAT
      es en dias habiles, aqui se aproxima como dias de calendario 1-10.
- Reportes: dia/mes/trimestre/semestre/anual, Excel, automatico 5:30pm, limpieza anual
  - Patrones de venta: database.nimbo_db.get_patrones_ventas(dias_historial=90) analiza el
    historial de Venta de los ultimos 90 dias y detecta: dia de la semana con mas/menos
    ventas (y el ratio entre ambos), mejor hora del dia, productos que se venden juntos
    frecuentemente, tendencia (ultimas 4 semanas vs las 4 anteriores) y clientes con un ciclo
    de compra regular (con su proxima compra estimada). "Productos juntos" se calcula
    agrupando por Venta.Id y extrayendo los nombres de producto de Venta.Descripcion de forma
    best-effort (_extraer_items_venta - misma logica que _productos_de_descripcion en
    tools/cliente_tool.py, duplicada en database/nimbo_db.py en vez de importada porque
    database/ no debe depender de tools/; solo las ventas multi-producto de Caja generan mas
    de un item por venta, ver seccion Caja). database.nimbo_db.get_prediccion_compra_cliente
    (query) hace la prediccion de ciclo para UN cliente especifico (busqueda fuzzy con
    buscar_cliente_completo): requiere minimo 3 compras con fecha valida, calcula el promedio
    y la desviacion estandar de los dias entre compras consecutivas, y marca "regular": True
    solo si la desviacion es <= 60% del promedio (heuristica simple para no reportar como
    "ciclico" a un cliente con compras muy irregulares) - igual devuelve la prediccion aunque
    no sea regular, marcandola como menos confiable en la respuesta del chat.
    - "analiza mis patrones de venta" / "patrones de venta" (reporte.patrones_ventas,
      tools/reporte_tool.py) le pasa los datos ya calculados a Ollama (analizar_ollama(),
      mismo patron que contabilidad.sugerencias_precios) para que narre recomendaciones sin
      inventar numeros; si Ollama no responde cae a un resumen de texto plano con los mismos
      datos (_resumen_patrones_sin_ia()). "cuando vendo mas" / "mejor hora para vender"
      (reporte.cuando_vendo_mas) da solo el dia/hora pico sin pasar por ningun modelo.
      "proxima compra de Juan Perez" / "cuando vuelve a comprar Juan Perez"
      (reporte.proxima_compra, core/detectors/reporte_detector.py) da la prediccion de un
      cliente especifico.
    - Categoria "reporte" ya era admin-only (no esta en CATEGORIAS_EMPLEADO en
      core/action_engine.py), asi que estos comandos tambien quedan restringidos a admin sin
      cambios adicionales.
    - Bug preexistente encontrado y corregido de paso en core/command_normalizer.py: "para"
      no estaba en VOCABULARIO, asi que el corrector de errores tipograficos lo autocorregia
      a "par" (la unidad de medida, muy similar en distancia de edicion, cutoff 0.8) ANTES de
      que cualquier detector viera el mensaje - esto rompia en silencio "cotizacion para X",
      "genera orden para X" y cualquier otro comando que dependiera de la palabra "para"
      literal (incluyendo el nuevo "mejor hora para vender" de este feature). Se agrego
      "para" (y "vendo", que se autocorregia a "vendio" y rompia "cuando vendo mas") al
      VOCABULARIO.
- Contenido: posts, scripts, video Veo3, publicacion Facebook
  - Video de producto desde una foto subida al chat: boton 📷 junto al campo de texto
    del chat (templates/index.html) - `sendChat()` manda la foto por
    `POST /api/chat/foto` (multipart, app.py) en vez del `POST /api/chat` con JSON de
    siempre. Esa ruta guarda la foto en `static/fotos/chat_temp/<uuid>.<ext>`
    (temporal, no queda asociada a ningun producto en la base de datos) y arma un
    mensaje sintetico `[FOTO:ruta] mensaje` que pasa por el mismo `core.nimbo.send()`
    de siempre - mismo patron que ya usa el escaneo de codigo de barras (texto
    sintetico como puente hacia el pipeline de detectores).
    `core/detectors/contenido_foto_detector.py` reconoce ese marcador (ya en
    minuscula, el texto pasa antes por `CommandNormalizer.normalize()`) solo si
    ademas trae una palabra clave (video/promocion/contenido/publicar) - una foto sin
    esas palabras no dispara el flujo, sigue de largo por el resto del pipeline. El
    valor de `ruta` dentro del marcador tambien se valida contra
    `PATRON_RUTA_FOTO_VALIDA` (exige la forma exacta `/static/fotos/chat_temp/
    <uuid>.<ext>` que genera `/api/chat/foto`) antes de aceptar el match - sin esto,
    un mensaje escrito directo a `/api/chat` con un `[foto:ruta]` armado a mano
    hubiera permitido path traversal (ver BUGS_Y_FIXES.md, fix del 2026-08-06);
    `tools/contenido_tool.py.video_desde_foto_tool()` revalida la misma ruta con
    `os.path.realpath()` antes de tocar el disco, como defensa en profundidad.
    `tools/contenido_tool.py.video_desde_foto_tool()` (intent
    `contenido.video_desde_foto`, admin-only como el resto de "contenido") intenta
    identificar el producto con Ollama vision si el modelo pulled lo soporta (ver
    `services/ollama_service.modelo_soporta_vision()` - hoy da `False`, ni
    `qwen2.5:7b` ni `gemma2:9b` tienen vision, pero se detecta solo si en el futuro se
    hace `ollama pull` de un modelo que si la tenga); si no hay vision o no devuelve
    nada util, cae al texto que el usuario escribio junto a la foto como busqueda
    (`get_products()`, mismo fuzzy match del resto del inventario). Si encuentra el
    producto, `core/nimbo.py` (steps `videofoto_waiting_*`, flujo separado del ya
    existente `VIDEO_INICIO:` de "video de [producto] por texto") confirma
    ("Encontre X, precio QY. Quieres que genere un video?"); si no, pide nombre y
    precio en un solo mensaje (ej. "licuadora oster 350") sin crear un `Producto`
    nuevo en la base de datos (a proposito, para no mutar el inventario como efecto
    secundario de este flujo). Despues pregunta, una por una: oferta/promocion,
    plataforma (TikTok/Instagram Reels/Facebook/General - mapea a `aspect_ratio` 9:16
    o 1:1 para Facebook, ver `_resolver_plataforma_video()` en `services/video_gen.py`
    y `core/nimbo.py`), tono (urgente y llamativo/informativo/divertido y casual/
    elegante, `_resolver_tono_video()`), que mostrar en el video (uso del producto/
    caracteristicas/demostracion/unboxing - texto libre, no se valida contra una
    lista), texto en pantalla (libre, o "no"), duracion aproximada (6/15/30 segundos u
    otro numero que el usuario escriba - no se pudo verificar si Veo 3 acepta
    cualquier duracion o solo valores especificos, mismo tipo de limitacion ya
    documentada para `aspect_ratio`) y si quiere que Nimbo optimice el prompt con IA.
    Con "no" arma un prompt basico deterministico
    (`_prompt_basico_video()`) directo con las respuestas; con "si" le pide a Ollama
    (`llamar_ollama()`, no `analizar_ollama()` - mismo criterio que el resto de
    generacion de contenido de este archivo, no es un analisis largo) que redacte un
    prompt profesional de videografia siguiendo la estructura de Veo 3 (escena
    principal, sujeto, accion, ambiente, iluminacion, camara, composicion, paleta de
    colores, estilo, texto en pantalla - ver el meta-prompt `PROMPT_OPTIMIZAR_VIDEO`),
    con fallback silencioso (con aviso en la respuesta) al prompt basico si Ollama no
    responde. En cualquiera de los dos casos, el prompt final se muestra completo en
    el chat ANTES de generar nada, con dos opciones: "confirmar" (genera el video de
    una vez con ese prompt) o "editar" (pide que el usuario escriba un prompt de
    reemplazo completo - el chat no tiene un campo de texto editable real como tal,
    el "editar" en este contexto es "mandame el texto completo que quieras usar en su
    lugar" como el siguiente mensaje del chat). `_generar_video_final()` es el unico
    punto que llama a `generar_video_producto()` en este flujo (desde "confirmar" o
    desde el prompt editado), mostrando el video con boton de descarga igual que el
    flujo de texto existente.
- Recordatorios: pagos fijos, follow ups, cumpleanos, contenido
- Backup: automatico 8pm, manual, 7 backups maximos
- Login y roles: admin/empleado, onboarding /setup, gestion de usuarios, cambio y
  recuperacion de contrasena (ver seccion "Login y roles" arriba)
- Chat mas inteligente: clarificacion de intenciones vagas antes de caer a OpenClaw
- Cotizaciones: COT-XXXX, admin-only. Flujo conversacional en core/nimbo.py (steps
  cotizacion_waiting_*, arrancado por el marcador COTIZACION_INICIO: que retorna
  tools/cotizacion_tool.py) -> cliente (existente o nuevo) -> productos + cantidades en
  loop ("listo" para terminar) -> genera PDF (services/pdf_cotizacion.py) + registra
  en tabla Cotizacion, Estado inicial PENDIENTE, FechaVencimiento = +15 dias. Muestra
  link de descarga del PDF y, si el cliente tiene telefono, link wa.me con el detalle.
  Comandos de chat: "cotizacion para X" / "generar cotizacion", "ver cotizacion COT-0001",
  "cotizaciones pendientes/enviadas/aceptadas/rechazadas/vencidas", "cotizacion COT-0001
  enviada", "aceptaron la cotizacion COT-0001" (descuenta stock y crea Venta automaticamente,
  ver cotizacion.aceptar en tools/cotizacion_tool.py), "rechazaron la cotizacion COT-0001".
  Las cotizaciones ENVIADA/PENDIENTE que llegan a su FechaVencimiento pasan a VENCIDA
  automaticamente (database.nimbo_db.marcar_cotizaciones_vencidas(), se corre de forma lazy
  cada vez que se consultan) y aparecen en /api/recordatorios ("vence hoy" / "vencio").
  Widget en el dashboard (contadores Pendientes/Enviadas/Aceptadas de la semana + lista de
  activas con dias restantes) via /api/cotizaciones/resumen. Si aplica un descuento (ver
  Descuentos abajo) se muestra en el resumen del chat, en el PDF (subtotal + descuento +
  total) y se guarda como texto en Cotizacion.Notas.
- Descuentos: tabla Descuento en nimbo.db (database.nimbo_db.init_descuentos/crear_descuento/
  get_descuentos/get_descuento_por_id/buscar_descuentos/desactivar_descuento). 4 tipos:
  cliente (ClienteId), temporada (FechaInicio/FechaFin), producto (ProductoId, referencia
  al Product.Id de Aronium igual que el resto del sistema), monto (MontoMinimo, "compras
  mayores a"). Cada descuento define Porcentaje o MontoFijo (uno de los dos).
  database.nimbo_db.calcular_descuento(cliente_id, productos, total, fecha=None) evalua
  todos los descuentos activos y devuelve el mejor (mayor monto en quetzales) - los
  descuentos NO se acumulan, se aplica solo uno. Para tipo "producto" la base del calculo
  es la suma de los subtotales de los items del carrito que coincidan con ese ProductoId,
  no el total completo; para cliente/temporada/monto la base es el total completo. Se
  aplica automaticamente (sin que el usuario tenga que pedirlo) en los 3 lugares donde se
  cierra una venta: paso venta_waiting_pago del flujo de venta simple en core/nimbo.py,
  database.nimbo_db.cobrar_carrito() (caja) y _finalizar_cotizacion() en core/nimbo.py
  (cotizaciones). El descuento aplicado se muestra en la respuesta del chat, se anota en
  Venta.Descripcion / Cotizacion.Notas (no hay columnas de descuento en esas tablas) y en
  Caja tambien aparece en el ticket (services/ticket.py, lineas Subtotal/Descuento antes
  del Total) y en el PDF de cotizacion (services/pdf_cotizacion.py).
  Detector core/detectors/descuento_detector.py + herramienta tools/descuento_tool.py.
  Comandos de chat: "descuento 10% para Juan Perez" (tipo cliente, busca el cliente por
  nombre con buscar_cliente_completo), "descuento 15% del 1 al 15 de diciembre" (tipo
  temporada, si no se da anio usa el actual o el siguiente si esa fecha ya paso este anio),
  "descuento 5% en cuchillas" (tipo producto, busca con get_products igual que el resto del
  inventario), "descuento 10% en compras mayores a Q500" (tipo monto), "ver descuentos"
  (lista los activos), "eliminar descuento X" (X puede ser el Id numerico o parte del
  nombre; si el nombre matchea mas de un descuento activo, pide especificar el Id).
  Admin-only (categoria "descuento" no esta en CATEGORIAS_EMPLEADO de core/action_engine.py).
- Caja Registradora: panel "Caja" en el menu lateral (empleado y admin), pantalla tablet
  (botones grandes) en templates/index.html. Solo puede haber un turno (CajaTurno) ABIERTO
  a la vez en toda la tienda. Denominaciones fijas: Q200, Q100, Q50, Q20, Q10, Q5, Q1
  (database.nimbo_db.DENOMINACIONES).
  - "abrir caja"/"cerrar caja" por chat (flujo conversacional en core/nimbo.py, steps
    caja_abrir_denom/caja_cerrar_denom, uno por denominacion) o desde la UI (modal con grid
    de 7 inputs, mismo componente reusado para apertura/cierre/detalle de billetes al cobrar).
  - Venta: buscar/escanear producto (input con Enter, /api/caja/carrito/agregar, matchea por
    Code exacto primero y si no por nombre fuzzy) -> carrito (ItemCarrito, temporal por turno)
    -> cobrar (/api/caja/cobrar) con Efectivo/Tarjeta/Mixto. Descuenta stock (remove_stock,
    con verificacion de stock de todos los items antes de descontar ninguno) + registra Venta
    + Kardex (via remove_stock) + genera el texto del ticket (services/ticket.py) en la misma
    respuesta. Reimpresion simplificada (sin detalle por producto) via /api/caja/imprimir-ticket.
  - #caja-buscar-producto tiene auto-focus permanente (misma funcion refocusInputActivo() del
    chat, ver seccion Arquitectura del chat) mientras el panel Caja este activo Y haya un turno
    abierto (#caja-con-turno visible): al entrar al panel (loadCajaEstado, despues de resolver
    si hay turno), despues de agregar un producto al carrito (por Enter o clickeando una
    coincidencia de la lista de "multiples"), despues de cerrar cualquier modal de Caja
    (cerrarModal/cerrarModalIdentificacionCobro llaman refocusInputActivo()), y al hacer click
    en cualquier parte de la pantalla que no sea un control interactivo. Si no hay turno
    abierto no se fuerza foco (el campo ni siquiera es visible).
  - Cambio: para Efectivo, "cuanto paga el cliente" es opcional (por defecto = total exacto);
    el desglose de billetes recibidos es opcional/colapsable ("detalle de billetes") - si se
    da, database.nimbo_db._calcular_cambio_denominaciones() arma el vuelto en billetes
    disponibles (greedy, mayor a menor) para el registro anti-fraude; si no se da, solo se
    registra el monto total (sin desglose para ese movimiento).
  - Cada movimiento de caja (MovimientoCaja: FONDO/VENTA/RETIRO/AJUSTE) puede guardar un JSON
    de Denominaciones que representa el DELTA neto por denominacion (positivo = entra,
    negativo = sale). database.nimbo_db.get_denominaciones_actuales() sirve para saber el
    desglose fisico actual del turno (suma de esos deltas) y detectar sencillo bajo
    (denominaciones pequenas Q20/Q10/Q5/Q1 sumando menos de Q200).
  - Retiro de caja: "retirar Q500 de caja [para/por motivo]" (chat) o boton "Retirar" en la
    UI (oculto para empleado en el template), solo admin - gate doble: INTENTS_SOLO_ADMIN en
    core/action_engine.py (chat) y current_user.is_admin en /api/caja/retirar (UI). Avisa si
    el sencillo queda bajo despues del retiro.
  - Cierre: conteo fisico por denominacion -> EfectivoContado, Diferencia = Contado-Esperado,
    Estado=CERRADO. El conteo fisico completo tambien se guarda en un MovimientoCaja tipo
    AJUSTE para auditoria. Un empleado no puede editar ventas ya cerradas (no existe endpoint
    para eso).
  - FondoInicial es inmutable: se fija una unica vez en el INSERT de database.nimbo_db.abrir_turno()
    y no existe en todo el codebase ninguna funcion/endpoint que le haga UPDATE despues (la
    consola SQL del dashboard, aunque consulta nimbo.db directamente, es solo SELECT - no
    puede escribir). La unica forma de corregir un fondo mal capturado es que un admin anule
    el turno.
  - Fondo inicial automatico: al abrir un turno nuevo, si existe un turno CERRADO previo,
    database.nimbo_db.get_ultimo_cierre_denominaciones() recupera el desglose que se conto
    fisicamente en su cierre (el JSON guardado en el MovimientoCaja tipo AJUSTE de ese turno)
    y se ofrece como fondo inicial sugerido: por chat, Nimbo pregunta "abrir con este mismo
    fondo? (si/no)" (step caja_abrir_confirmar_sugerido en core/nimbo.py) en vez de pedir cada
    denominacion; en la UI, el modal de apertura llega prellenado con esos valores (editable
    por si el efectivo fisico cambio de un dia a otro). Si no hay ningun turno cerrado todavia,
    cae al flujo manual de siempre (contar cada denominacion).
  - Anular turno: "anular turno [por motivo]" (chat, pide el motivo si no vino en el mensaje)
    o boton "Anular turno" en la UI (oculto para empleado) - solo admin, mismo gate doble que
    Retirar (INTENTS_SOLO_ADMIN + current_user.is_admin en /api/caja/anular). Solo aplica a un
    turno ABIERTO (no se puede anular uno ya CERRADO); pone Estado=ANULADO y jamas toca
    FondoInicial. Si el turno anulado ya tenia ventas registradas, esas ventas y el stock
    descontado NO se revierten automaticamente (se avisa en la respuesta); un turno ANULADO
    tampoco cuenta para el fondo sugerido del siguiente turno (get_ultimo_cierre_denominaciones
    solo mira turnos CERRADO).
- Garantias: 2 tablas en nimbo.db. GarantiaProducto (1 fila por Product.Id de Aronium)
  define los dias de cobertura de cada producto - DiasFabrica (garantia del fabricante,
  0 = no aplica) y DiasPropia (garantia que da Mi Cocina, default 30). GarantiaVenta
  (GAR-XXXX) es una garantia real generada por una venta concreta - guarda copia del
  cliente/producto (ClienteNombre/ClienteTelefono/ProductoNombre denormalizados, igual
  que Cotizacion) y las 2 fechas de vencimiento ya calculadas (FechaVencimientoFabrica/
  FechaVencimientoPropias). Estado (VIGENTE/VENCIDA/RECLAMADA): database.nimbo_db.
  marcar_garantias_vencidas() (lazy, igual que las cotizaciones) solo marca VENCIDA
  cuando YA pasaron AMBAS fechas - si cualquiera de las dos sigue vigente, el producto
  sigue cubierto. RECLAMADA no se toca automaticamente; el unico lugar que la usa es
  "reclamacion garantia OS-XXXX" para garantias de reparacion (ver seccion Servicio
  Tecnico) - las garantias de producto no tienen todavia un comando de chat para
  reclamarlas, se marcarian igual via database.nimbo_db si hiciera falta.
  - Integracion con ventas: database.nimbo_db.generar_garantia_venta() se llama
    automaticamente (una vez por cada linea de producto distinta) desde los 3 lugares
    donde se cierra una venta - paso venta_waiting_pago/venta_waiting_pago_mixto_tarjeta
    en core/nimbo.py (via el helper _registrar_venta_chat), database.nimbo_db.
    cobrar_carrito() (caja) y tools/cotizacion_tool.py aceptar_cotizacion_tool() (cuando
    se acepta una cotizacion). Si el producto no tiene GarantiaProducto configurada usa
    30 dias propios y 0 de fabrica por defecto. El numero de garantia se muestra en la
    respuesta del chat, en el ticket de caja (services/ticket.py, seccion GARANTIAS antes
    del pie) y en el mensaje de factura por WhatsApp (services/whatsapp.py
    enviar_factura_whatsapp, parametro garantia).
  - Recordatorios: get_recordatorios() (database/nimbo_db.py) agrega un recordatorio por
    cada garantia que vence en los proximos 7 dias (get_garantias_por_vencer(dias=7)).
  - Detector core/detectors/garantia_detector.py + herramienta tools/garantia_tool.py.
    Comandos de chat: "garantia de cuchilla es 30 dias" (configura solo DiasPropia, sin
    tocar DiasFabrica), "garantia de licuadora oster es 365 dias fabrica y 180 dias
    nuestra" (configura ambos dias), "ver garantia GAR-0001" (estado + fechas), "garantias
    de Juan Perez" (todas las de un cliente, busca por ClienteNombre/ClienteTelefono),
    "garantias por vencer" (proximos 30 dias, distinto del recordatorio automatico de 7
    dias). Admin-only (categoria "garantia" no esta en CATEGORIAS_EMPLEADO de
    core/action_engine.py).
- Combos/Kits: 2 tablas en nimbo.db. ProductoCombo (Nombre/Descripcion/PrecioCombo/Activo)
  + ItemCombo (ComboId, ProductoId de Aronium, ProductoNombre, Cantidad - N filas por
  combo). database.nimbo_db.DESCUENTO_COMBO_SUGERIDO = 0.08 (8%) es el descuento por
  defecto que se sugiere sobre la suma de precios individuales, tanto en la creacion
  manual como en las sugerencias con Gemini.
  - "crear combo Kit Licuadora" inicia un flujo conversacional en core/nimbo.py (steps
    combo_crear_waiting_producto/seleccion/cantidad, igual que las cotizaciones: agrega
    productos + cantidad en loop hasta 'listo') y al terminar sugiere el precio con 8% de
    descuento (step combo_crear_waiting_precio, el admin puede aceptar con "si" o escribir
    su propio monto) antes de guardar el combo (database.nimbo_db.crear_combo).
  - "ver combos" lista los combos activos con su precio y detalle de productos
    (tools/combo_tool.py, database.nimbo_db.get_combos()).
  - "vender combo Kit Licuadora" es una venta directa de una sola vez (a diferencia de
    "crear combo", no es un flujo de varios pasos) - database.nimbo_db.vender_combo()
    busca el combo por nombre (buscar_combos, fuzzy LIKE), verifica stock de todos sus
    productos antes de descontar ninguno, descuenta el stock de cada uno, registra una
    sola Venta por el PrecioCombo (ya con el descuento incluido, via
    registrar_venta_cliente) y genera la garantia de cada producto (generar_garantia_venta,
    igual que cualquier otra venta). Vende a "Consumidor Final" sin pedir cliente ni
    metodo de pago (mantiene el comando de un solo paso); para atribuir la venta a un
    cliente especifico o cobrar por caja, hay que vender los productos del combo por
    separado con descuento manual en vez de usar este comando.
  - "sugerir combos" (database.nimbo_db via tools/combo_tool.py sugerir_combos_tool):
    manda el inventario actual con stock > 0 (nombre, precio, stock) a Ollama
    (analizar_ollama()) pidiendole exactamente 3 combos logicos en JSON estricto
    (nombre/descripcion/productos, usando los nombres exactos del inventario). El modelo
    solo decide QUE productos van juntos (criterio de negocio); Python hace el match contra
    el inventario real (get_products, mismo fuzzy fallback que el resto del sistema) y
    calcula el precio con el 8% de descuento de forma determinista, sin confiar en la
    aritmetica del modelo (mismo patron que contabilidad.sugerencias_precios). Si un
    producto sugerido no matchea con nada real se descarta esa entrada; si un combo se
    queda con menos de 2 productos reales se omite. Si Ollama no esta disponible o no
    responde con un JSON valido, avisa sin crear nada.
  - Detector core/detectors/combo_detector.py + herramienta tools/combo_tool.py.
    Admin-only (categoria "combo" no esta en CATEGORIAS_EMPLEADO de core/action_engine.py).
- Unidades de medida: tabla UnidadMedida en nimbo.db, 1 fila por (ProductoId de Aronium,
  UnidadBase) - UnidadBase es el nombre de la presentacion (docena/caja/par/paquete/trio/
  cuarteto), CantidadPorUnidad cuantas unidades base equivale, PrecioUnitario el precio
  individual al momento de configurar (referencia) y PrecioPorUnidad el precio real de esa
  presentacion (puede tener descuento por volumen, ej. docena Q1000 vs 12x Q95=Q1140).
  - "[producto] se vende por [unidad] de [N]" / "[producto] vienen en [unidad] de [N]"
    configura CantidadPorUnidad=N sin precio especial (PrecioPorUnidad = precio individual
    x N, sin descuento). "[producto] se vende por [unidad] [N] unidades precio Q[P]"
    configura ademas un precio especial. "[producto] se vende por [unidad]" (sin numero)
    solo funciona para unidades con cantidad implicita conocida (par=2, docena=12, trio=3,
    cuarteto=4 - ver UNIDADES_CANTIDAD_DEFAULT en tools/unidad_medida_tool.py); para
    cualquier otra unidad pide que se especifique la cantidad. Admin-only
    (unidadmedida.configurar esta en INTENTS_SOLO_ADMIN de core/action_engine.py, aunque
    la categoria "unidadmedida" si es de empleado para vender/listar).
  - "vendi N [unidad] de [producto]" (ej. "vendi 2 docenas de cuchillas") reutiliza el
    mismo flujo conversacional de venta simple del chat (VENTA_INICIO -> venta_waiting_nombre
    -> ... -> venta_waiting_pago en core/nimbo.py) que la venta normal por unidad -
    tools/unidad_medida_tool.py.vender_por_unidad_tool calcula la cantidad real en
    unidades base (cantidad_medida x CantidadPorUnidad), descuenta ese stock de una vez
    (igual que venta.registrar) y arma el marcador VENTA_INICIO con el PrecioPorUnidad
    como "precio unitario" y el nombre del producto con la presentacion entre parentesis
    (ej. "Cuchilla oster original (docena)") para que quede claro en el ticket/resumen/
    garantia que no es precio por pieza. Como reutiliza el flujo normal, hereda gratis los
    descuentos (Descuento tipo producto matchea por ProductoId igual que siempre) y la
    garantia automatica (una por producto_id real, sin importar la presentacion).
    Solo reconoce las palabras de unidad en UNIDADES_RECONOCIDAS de
    core/detectors/unidad_medida_detector.py (docena/caja/par/paquete/trio/cuarteto,
    singular o plural) - una unidad configurada con otro nombre no se reconoce al vender
    y hay que agregar la palabra a esa lista. Singular/plural ("docena" al configurar vs
    "docenas" al vender) se resuelve con _singularizar() en tools/unidad_medida_tool.py,
    no con el CommandNormalizer (que corrige typos por similitud, no gramatica).
    Si no se especifica ninguna unidad, "vendi N producto" sigue el flujo normal de
    venta.registrar sin cambios.
  - "ver unidades de medida" lista todas las configuradas.
  - Al mostrar un producto (core/responses.py, busqueda/inventario) se agrega una linea
    "Equivalente: X unidad(es)" por cada UnidadMedida configurada para ese producto,
    calculada como Stock / CantidadPorUnidad. Para que esto funcione en la lista completa
    de inventario tambien se agrego Product.Id al SELECT de InventoryService.list() en
    services/inventory.py (antes solo lo traia InventoryService.search(), que delega en
    database.nimbo_db.get_products()).
  - Se aprovecho para corregir un bug preexistente en core/nimbo.py venta_waiting_seleccion
    (el paso donde se elige un producto entre varios resultados similares al vender): nunca
    descontaba stock, sin importar el flujo. Ahora descuenta cantidad x CantidadPorUnidad
    (4to campo opcional en cada opcion de venta_opciones, ausente = 1 para una venta normal
    por unidad) y valida que haya stock suficiente antes de continuar.
- Programa de lealtad (puntos): 2 tablas en nimbo.db. PuntosCliente (1 fila por cliente) -
  PuntosAcumulados (historico de por vida, nunca baja), PuntosUsados y PuntosCancelados
  (ambos tambien acumulativos; el saldo disponible para canjear = Acumulados - Usados -
  Cancelados, ver database.nimbo_db.get_saldo_puntos). MovimientoPuntos es el detalle
  (GANADO/USADO/CANCELADO) de cada cambio, con VentaId para saber a que venta corresponde.
  Constantes en database/nimbo_db.py: PUNTOS_POR_QUETZAL=1 (1 punto por cada Q1 de compra,
  sobre el total ya con todos los descuentos/creditos aplicados), PUNTOS_POR_CANJE=100,
  VALOR_CANJE=Q10 (asi que 1 punto = Q0.10), DESCUENTO_EXTRA_ORO=5%. Los puntos no vencen
  (no hay ninguna funcion que reste PuntosCancelados via chat - ese campo del esquema queda
  para una integracion futura, ej. anular una venta).
  - Niveles (opcional del pedido original, si se implemento): NIVELES_LEALTAD evalua sobre
    PuntosAcumulados (no el saldo disponible - el nivel no baja solo porque el cliente
    canjeo puntos): Bronce 0-499, Plata 500-999, Oro 1000+ (5% de descuento extra en cada
    compra, ver mas abajo).
  - "Canjear" no descuenta nada de inmediato: database.nimbo_db.canjear_puntos() resta el
    saldo (PuntosUsados) y el credito en quetzales queda pendiente como un MovimientoPuntos
    Tipo='USADO' con VentaId=NULL. database.nimbo_db.calcular_ajuste_puntos(cliente_id, total)
    - llamada ANTES de insertar cualquier Venta - busca ese credito pendiente
    (peek_credito_puntos_pendiente) y lo resta del total (topado al total de esa venta, sin
    partir el canje si sobra), y encima resta el 5% extra si el cliente es nivel Oro.
    database.nimbo_db.consumir_credito_puntos_pendiente(cliente_id, venta_id) - llamada
    DESPUES de insertar, ya con el venta_id conocido - marca esos movimientos pendientes
    como aplicados a esa venta. database.nimbo_db.ganar_puntos() se llama al final con el
    Total ya ajustado (se ganan puntos sobre lo que el cliente realmente termina pagando).
    database.nimbo_db.formatear_nota_ajuste_puntos() arma la nota que se anexa a la
    Descripcion de la Venta cuando aplico alguno de los dos ajustes.
  - Integrado en los 4 lugares donde se cierra una venta: core/nimbo.py
    venta_waiting_pago/venta_waiting_pago_mixto_tarjeta (venta simple del chat),
    database.nimbo_db.cobrar_carrito() (caja) y database.nimbo_db.registrar_venta_cliente()
    (usada por cotizacion.aceptar y por combo.vender - aunque los combos hoy siempre venden
    a "Consumidor Final" sin cliente, asi que en la practica no ganan ni canjean puntos, ver
    seccion Combos arriba). En todos los casos se ganan puntos automaticamente si hay
    cliente; el mensaje final sigue el formato pedido ("Juan Perez gano 85 puntos. Total
    acumulado: 185 puntos (Q18.50 en descuentos)").
  - Solo en la venta simple del chat (core/nimbo.py) se pregunta interactivamente si
    canjear: al identificar un cliente EXISTENTE en venta_waiting_nombre, si su saldo es
    >= 100 puntos, entra al step venta_waiting_canjear_puntos ("Tiene N puntos disponibles
    (QX). Quiere canjearlos en esta compra? si/no") antes de pedir el metodo de pago; si
    acepta, canjea todo lo canjeable en multiplos de 100 (canjear_puntos()) y ese credito
    se aplica automaticamente a la MISMA venta que se esta cerrando (mismo mecanismo que
    "aplica en la siguiente compra", solo que aqui la "siguiente compra" es la actual). No
    se implemento este mismo prompt interactivo en caja/cotizacion/combo (solo se pidio
    "flujo en nimbo.py"); esos otros 3 caminos si aplican automaticamente cualquier credito
    YA canjeado previamente por el cliente.
  - Detector core/detectors/puntos_detector.py + herramienta tools/puntos_tool.py. Comandos
    de chat: "puntos de Juan Perez" (saldo, valor, nivel), "canjear 100 puntos Juan Perez"
    (canje manual fuera de una venta activa, mismo mecanismo de credito pendiente), "puntos
    disponibles" (lista clientes con saldo > 0). Categoria "puntos" SI es de empleado
    (CATEGORIAS_EMPLEADO en core/action_engine.py) - ver puntos o canjearlos no es una
    decision de precios, es una operacion de venta normal.
- Codigos de barras y etiquetas: tabla CodigoBarrasGenerado en nimbo.db (Id, ProductoId,
  ProductoNombre, CodigoEAN, FechaGenerado) - registra el historico de codigos generados,
  ya que Aronium solo guarda el Code final en Product sin quien/cuando lo asigno.
  database.nimbo_db.generar_ean13() arma un EAN-13 con prefijo 20 (rango 200-299, reservado
  por GS1 para "restricted circulation numbers" de uso interno de tienda, no requiere
  registro ante GS1) + 10 digitos random + digito verificador estandar EAN-13, y reintenta
  hasta que no choque ni con ningun Product.Code existente en Aronium ni con uno ya generado
  antes. asignar_codigo_barras(producto_id, producto_nombre) hace el UPDATE Product SET
  Code=... en Aronium (pos.db) y el INSERT en CodigoBarrasGenerado (nimbo.db).
  - "generar codigo cuchilla" / "codigo de barras para cuchilla" (codigobarras.generar):
    si el producto ya tiene Code no lo sobreescribe, avisa cual tiene y sugiere generar la
    etiqueta directamente.
  - "etiqueta de cuchilla" (etiqueta.producto): genera el PDF de una sola etiqueta; si el
    producto no tenia Code todavia se lo asigna primero (asignar_codigo_barras) para no
    exigir el paso "generar codigo" antes como requisito separado.
  - "etiquetas de todos los productos sin codigo" (etiqueta.lote_sin_codigo): recorre
    database.nimbo_db.get_productos_sin_codigo() (Product.Code NULL o vacio), genera un
    EAN-13 nuevo para cada uno y arma un solo PDF con todas las etiquetas.
  - services/barcode_service.py genera el PDF con reportlab: una pagina por etiqueta, tamano
    fijo 5x3cm (50mm x 30mm, estandar de impresora de etiquetas continua) - nombre truncado,
    precio, imagen de codigo de barras (python-barcode + ImageWriter, sin texto para ahorrar
    espacio) y un QR (libreria qrcode) que apunta a http://[IP_LOCAL]:5000/producto/[codigo].
    "etiqueta de X" reusa el Code que el producto ya tenga en Aronium si existe (no lo
    pisa con un EAN-13 nuevo, ver _asegurar_codigo en tools/codigo_barras_tool.py) - como
    muchos productos ya traian codigos manuales de Aronium que no son EAN-13 valido (ej.
    "01293428", 8 digitos, o alfanumericos como "LIC001"), _generar_imagen_barcode dibuja
    EAN-13 solo si el codigo son exactamente 13 digitos numericos; cualquier otro formato
    lo dibuja como Code128 (acepta cualquier texto/longitud) para no reventar con
    NumberOfDigitsError. El nombre de archivo del PDF sanitiza el codigo (solo
    alfanumerico/guiones) porque un Code de Aronium puede traer espacios u otros
    caracteres no aptos para un path.
    get_local_ip() detecta la IP local via un socket UDP a 8.8.8.8 (no envia datos, solo lee
    la IP de salida); en este entorno WSL2 devuelve la IP interna de WSL2, no la IP LAN de
    Windows, asi que el QR solo sera alcanzable desde un telefono si hay mirrored networking
    o port forwarding configurado entre Windows y WSL2 (mismo tipo de limitacion que el
    Pendiente #5 de mas abajo con el link de cotizaciones por WhatsApp).
  - Ruta publica /producto/<codigo> en app.py (sin login) + templates/producto_publico.html:
    busca el producto por Code (database.nimbo_db.get_product_by_code, que ahora tambien trae
    Product.Description de Aronium), muestra foto (ProductoFoto en nimbo.db) + nombre +
    precio + descripcion (ProductoInfo en nimbo.db si existe, si no la Description nativa de
    Aronium) - nunca stock ni costo. 404 con pagina propia si el codigo no matchea ningun
    producto.
  - Detector core/detectors/codigo_barras_detector.py + herramienta
    tools/codigo_barras_tool.py. Categorias "codigobarras" y "etiqueta" SI son de empleado
    (CATEGORIAS_EMPLEADO en core/action_engine.py) - generar codigos/etiquetas es una tarea
    operativa de bodega, igual que el resto de inventario, no una decision de precios.
- Grupos de cliente: columna Cliente.GrupoCliente (TEXT DEFAULT 'detallista', agregada con
  ALTER TABLE en database.nimbo_db.init_grupos_cliente() porque Cliente ya existia de antes,
  mismo patron que GarantiaVenta.Tipo). Tabla GrupoDescuento (Grupo UNIQUE, PorcentajeDescuento,
  PuntosMultiplicador) - se siembra con GRUPOS_CLIENTE_DEFAULT en el mismo init: detallista
  (0%, x1), mayorista (10%, x1), especial (0%, x1), vip (15%, x2). "Especial" no tiene
  porcentaje fijo a proposito - su "descuento personalizable por cliente" sale siempre del
  Descuento individual (tipo='cliente') que ya existia antes de este feature, nunca de
  GrupoDescuento.
  - database.nimbo_db.calcular_descuento() ahora primero recorre los Descuento normales
    (cliente/temporada/producto/monto) igual que antes; solo si el cliente NO tiene un
    Descuento individual activo (tipo='cliente') agrega el descuento automatico del grupo
    como un candidato mas a competir por "el que mas le convenga" con temporada/producto/
    monto - el individual nunca compite contra el del grupo, tiene prioridad absoluta.
    database.nimbo_db.ganar_puntos() multiplica los puntos ganados por el PuntosMultiplicador
    del grupo del cliente (VIP = puntos dobles) - como ambas funciones son el unico punto de
    entrada para descuentos/puntos en los 3-4 lugares donde se cierra una venta (venta simple
    del chat, caja, cotizacion, combo), el grupo se aplica automaticamente en todos sin tocar
    esos call sites.
  - "Juan Perez es mayorista" / "... es vip" / "... es especial" / "... es detallista"
    (cliente.grupo_set, tools/cliente_tool.py), "grupo de Juan Perez" (cliente.grupo_ver,
    tambien muestra el descuento individual si lo tiene, aclarando que ese manda sobre el del
    grupo), "ver mayoristas" / "ver vip" / "ver especiales" / "ver detallistas"
    (cliente.grupo_listar). Detector core/detectors/cliente_detector.py - estos patrones se
    revisan ANTES que los catch-all de busqueda de cliente (PATTERNS_BUSCAR) para que "Juan
    Perez es mayorista" no se interprete como buscar un cliente llamado "Juan Perez Es
    Mayorista".
  - "nuevo cliente Juan Perez 12345678" (cliente.nuevo) ya no crea el cliente de inmediato:
    tools/cliente_tool.py retorna el marcador CLIENTE_NUEVO_INICIO:nombre|telefono, que
    arranca el step cliente_waiting_grupo en core/nimbo.py ("Que tipo de cliente es?
    (detallista/mayorista/especial/vip)") - con la respuesta ya crea el cliente
    (crear_cliente_completo) y le asigna el grupo si no es detallista. Acepta el nombre
    del grupo en singular o plural, y "no"/vacio para dejarlo en detallista (el default). Los
    otros 3 lugares donde tambien se crea un cliente sobre la marcha (venta simple sin
    cliente existente, cotizacion para cliente nuevo, onboarding /setup) NO preguntan el
    grupo - se quedan en detallista por defecto para no interrumpir esos flujos con una
    pregunta ajena a lo que se esta haciendo.
  - Grupo visible tambien en cliente.buscar, cliente.historial y cliente.resumen (via
    _estadisticas_cliente/_texto_estadisticas en tools/cliente_tool.py), no solo en
    "grupo de X".
- Cuentas por cobrar: 2 tablas en nimbo.db. CuentaCobrar (Id, ClienteId, ClienteNombre,
  ClienteTelefono denormalizados igual que Cotizacion/GarantiaVenta, Descripcion, MontoTotal,
  MontoPagado, MontoPendiente, FechaCreada, FechaVencimiento, Estado, Notas, VentaId - esta
  ultima no estaba en el pedido original, se agrego para poder vincular una cuenta a la venta
  a credito que la genero, igual que OrdenServicioId en GarantiaVenta) + PagoCuenta (historial
  de abonos: Id, CuentaId, Monto, MetodoPago, Fecha, Notas). database.nimbo_db.
  DIAS_VENCIMIENTO_CUENTA_DEFAULT = 30 (no especificado en el pedido, mismo criterio que el
  resto de defaults del sistema - GarantiaProducto 30 dias propios, Cotizacion 15 dias) se usa
  cuando se crea una cuenta sin fecha de vencimiento explicita (comando "X debe QN") o cuando
  el step de fecha en el flujo de venta a credito no logra interpretar la respuesta.
  - Estado (PENDIENTE/PAGADO_PARCIAL/PAGADO/VENCIDO): database.nimbo_db.
    marcar_cuentas_vencidas() es lazy (igual que marcar_cotizaciones_vencidas()/
    marcar_garantias_vencidas() - se corre cada vez que se consultan cuentas) y marca VENCIDO
    cualquier cuenta PENDIENTE o PAGADO_PARCIAL cuya FechaVencimiento ya paso. Un abono sobre
    una cuenta VENCIDO no le quita el estado directamente (registrar_pago_cuenta solo mira
    MontoPendiente para decidir PAGADO/PAGADO_PARCIAL); si queda saldada pasa a PAGADO, pero si
    queda con saldo la siguiente llamada a marcar_cuentas_vencidas() la vuelve a marcar VENCIDO
    porque la fecha sigue en el pasado.
  - "Juan Perez pago Q100" (cuentacobrar.pagar, tools/cuenta_cobrar_tool.py) no especifica a
    que cuenta aplica el abono si el cliente tiene varias pendientes: database.nimbo_db.
    registrar_pago_cliente() lo reparte FIFO (la cuenta pendiente mas antigua primero) hasta
    agotar el monto o las cuentas; el sobrante (si el abono es mayor a toda la deuda) se
    reporta en la respuesta sin aplicarse a nada.
  - "Juan Perez debe Q200 por licuadora" (cuentacobrar.crear) / "Juan Perez debe Q200" (sin
    descripcion, usa "Deuda general") buscan el cliente con buscar_cliente_completo (mismo
    fuzzy match que el resto del sistema) - si no existe, piden registrarlo primero en vez de
    crearlo sobre la marcha (a diferencia de la venta simple del chat, una deuda nueva sin
    cliente identificado no tiene a quien cobrarsele). "cuentas por cobrar" (cuentacobrar.
    listar) lista todo lo que tenga MontoPendiente > 0 sin importar el estado; "cuentas
    vencidas" (cuentacobrar.vencidas) filtra solo Estado='VENCIDO'; "cuanto debe Juan Perez" /
    "deuda de Juan Perez" (cuentacobrar.consultar) trae solo las cuentas pendientes de ese
    cliente (database.nimbo_db.get_cuentas_cliente(query, solo_pendientes=True) por defecto).
  - Detector core/detectors/cuenta_cobrar_detector.py - se revisa antes que ClienteDetector/
    VentaDetector en core/intent_detector.py, aunque en la practica no hay ambiguedad real: a
    diferencia de "Juan Perez es mayorista" (ClienteDetector), los patrones de esta categoria
    empiezan con nombre+verbo ("X debe Q...", "X pago/abono Q...") que ningun otro detector
    reconoce. "cuanto debe X" se revisa antes que "X debe QN..." dentro del propio detector
    para que una consulta no se confunda con una deuda nueva (aunque en la practica nunca
    chocan: la regex de crear exige un numero justo despues de "debe").
  - Categoria "cuentacobrar" SI es de empleado (CATEGORIAS_EMPLEADO en
    core/action_engine.py) - cobrar y anotar deudas de clientes es una operacion de venta
    normal en mostrador, igual que puntos, no una decision de precios como descuento/garantia.
  - Integracion con la venta simple del chat: el step venta_waiting_pago (core/nimbo.py) ahora
    acepta "credito"/"fiado" ademas de efectivo/tarjeta/transferencia/mixto. Exige un cliente
    ya identificado (no permite "Consumidor Final" a credito, no hay a quien cobrarle despues)
    y arranca 2 pasos nuevos: venta_waiting_credito_enganche (monto que paga de una vez, puede
    ser 0) y venta_waiting_credito_fecha (cuando vence el resto - acepta un numero de dias o
    una fecha dd/mm/aaaa; si no logra interpretarla cae a DIAS_VENCIMIENTO_CUENTA_DEFAULT con
    aviso en la respuesta). Al terminar registra la Venta igual que cualquier otro metodo de
    pago (_registrar_venta_chat, con su garantia y puntos) y ademas crea la CuentaCobrar por el
    saldo pendiente (MontoTotal=total_final, MontoPagado=enganche). Esta integracion solo se
    implemento en el flujo de venta del chat (igual que el canje interactivo de puntos, ver
    seccion Programa de lealtad) - Caja y Cotizaciones no tienen "credito" como metodo de pago.
  - Recordatorios: get_recordatorios() agrega un recordatorio por cada cuenta que vence en
    los proximos 3 dias (get_cuentas_por_vencer(dias=3), urgencia alta).
  - Widget en el dashboard (/api/cuentascobrar/resumen, admin-only igual que el resto de
    widgets financieros del Dashboard - ver seccion "Login y roles"): total por cobrar,
    cuentas vencidas (rojo) y proximas a vencer en 3 dias (naranja, mismo color --accent que
    usa badge-orange en el resto del dashboard, no hay una variable --orange separada).
- Cuentas por pagar: version espejo de Cuentas por cobrar pero para deudas con proveedores.
  2 tablas en nimbo.db. CuentaPagar (Id, ProveedorId, ProveedorNombre, ProveedorTelefono -
  denormalizados desde Proveedor.WhatsApp igual que el resto de tablas del sistema copian
  datos del cliente/proveedor al momento, Descripcion, MontoTotal, MontoPagado,
  MontoPendiente, FechaCreada, FechaVencimiento, Estado, OrdenCompraId, Notas) + PagoPagar
  (historial de pagos: Id, CuentaId, Monto, MetodoPago, Fecha, Notas). database.nimbo_db.
  DIAS_VENCIMIENTO_PAGAR_DEFAULT = 30 (mismo criterio que DIAS_VENCIMIENTO_CUENTA_DEFAULT).
  Estado (PENDIENTE/PAGADO_PARCIAL/PAGADO/VENCIDO) usa el mismo criterio lazy que Cuentas por
  cobrar: database.nimbo_db.marcar_pagos_vencidos() se corre cada vez que se consultan cuentas.
  - "debo Q500 a Distribuidora Oster" (cuentapagar.crear) / "debo Q500 a Distribuidora Oster
    por repuestos" (con descripcion) buscan el proveedor con buscar_proveedor (mismo fuzzy
    match LIKE que el resto de proveedor_tool.py) - si no existe, piden registrarlo primero.
    "pague Q200 a Distribuidora Oster" (cuentapagar.pagar) reparte el pago FIFO entre las
    cuentas pendientes mas antiguas del proveedor (database.nimbo_db.registrar_pago_proveedor,
    misma logica que registrar_pago_cliente de Cuentas por cobrar). "cuentas por pagar"
    (cuentapagar.listar) lista todo con MontoPendiente > 0; "pagos vencidos" (cuentapagar.
    vencidas) filtra Estado='VENCIDO'; "cuanto le debo a Distribuidora Oster" (cuentapagar.
    consultar) trae solo las cuentas pendientes de ese proveedor.
  - Detector core/detectors/cuenta_pagar_detector.py, se revisa antes que ProveedorDetector
    en core/intent_detector.py (sin ambiguedad real: "debo QN a X" no coincide con ningun
    patron de ProveedorDetector). Distingue de Cuentas por cobrar por el verbo/persona: "X
    debe QN" (3ra persona, el cliente le debe a la tienda) vs "debo QN a X" (1ra persona, la
    tienda le debe al proveedor) - nunca se confunden entre si.
  - Categoria "cuentapagar" NO esta en CATEGORIAS_EMPLEADO (core/action_engine.py) - a
    diferencia de cuentacobrar, es admin-only: pagar o endeudarse con un proveedor es una
    decision financiera del negocio, no una operacion de mostrador. Mismo criterio que la
    categoria "proveedor", tambien admin-only.
  - Integracion con ordenes de compra: dos vias para crear una OrdenCompra desde el chat -
    "genera orden para X" / "crear orden para X" / "pedir a X" (proveedor.generar_orden en
    tools/proveedor_tool.py, arma la orden con database.nimbo_db.get_pedidos_sugeridos()) y
    la forma estructurada "pedir a X N producto a QN" (proveedor.orden_compra). Cuando esta
    seccion se escribio originalmente, proveedor.orden_compra todavia devolvia un marcador
    (PROVEEDOR_ORDEN_INICIO:) que core/nimbo.py no sabia interpretar - gap que quedo anotado
    aqui como pendiente. Ese gap se cerro despues, en la misma auditoria que corrigio los
    conflictos entre detectores (ver bug de deteccion de "pedir a X N producto a QN" en
    BUGS_Y_FIXES.md): orden_compra_tool se reescribio para re-parsear el texto completo
    (proveedor, cantidad, producto y precio opcional) y devolver el mismo marcador que ya
    usaba generar_orden_tool, asi que ambas vias terminan en el mismo flujo. database.
    nimbo_db.crear_orden_compra() retorna (numero, orden_id) en vez de solo numero, para
    poder vincular la CuentaPagar a la orden. Ambas tools devuelven el marcador
    ORDEN_COMPRA_PAGO_INICIO:orden_id|numero|proveedor_id|proveedor_nombre|whatsapp|
    total|resp, que arranca el step ordencompra_waiting_pago en core/nimbo.py preguntando "Se
    pago de una vez o queda pendiente?". "pagado" cierra el flujo sin crear nada; "pendiente"
    pasa a ordencompra_waiting_fecha (mismo parseo de fecha/dias que venta_waiting_credito_
    fecha de Cuentas por cobrar, con el mismo default DIAS_VENCIMIENTO_PAGAR_DEFAULT si no
    logra interpretarla) y crea la CuentaPagar por el total completo de la orden.
  - Recordatorios: get_recordatorios() agrega un recordatorio por cada cuenta por pagar que
    vence en los proximos 3 dias (get_pagos_por_vencer(dias=3), urgencia alta).
  - Widget en el dashboard (/api/cuentaspagar/resumen, admin-only): total por pagar, pagos
    vencidos (rojo) y proximos a vencer en 3 dias (naranja) - misma estructura visual que el
    widget de Cuentas por cobrar.
- Flujo de caja proyectado: database.nimbo_db.get_flujo_caja_proyectado() calcula ingresos,
  egresos y flujo neto proyectados para el mes calendario siguiente. Admin-only (categoria
  "contabilidad" no esta en CATEGORIAS_EMPLEADO).
  - Ingresos = promedio de ventas de los ultimos 3 meses YA CERRADOS (excluye el mes actual,
    todavia incompleto - toma get_comparacion_meses(meses=4) y descarta el ultimo) + un
    ajuste por tendencia (variacion promedio mes a mes de esos 3 meses, proyectada un paso
    mas hacia adelante sobre el promedio; positiva si suben, negativa si bajan) + cuentas por
    cobrar pendientes que vencen en los proximos 30 dias (get_cuentas_por_vencer(dias=30)).
  - Egresos = pagos fijos activos (get_pagos_fijos(), suma de PagoFijo.Monto) + cuentas por
    pagar pendientes que vencen en los proximos 30 dias (get_pagos_por_vencer(dias=30)) +
    estimado de compras a proveedores por reabastecimiento de stock minimo (suma de
    costo_total en get_pedidos_sugeridos(), que ahora tambien devuelve costo_unitario/
    costo_total por item usando Product.Cost de Aronium - antes solo traia cantidades).
  - "vencen el proximo mes" se aproxima como "vencen en los proximos 30 dias" en vez de
    acotar por el mes calendario exacto (mismo criterio que ya usa el resto del sistema,
    ver DIAS_VENCIMIENTO_CUENTA_DEFAULT/DIAS_VENCIMIENTO_PAGAR_DEFAULT = 30 dias).
  - PagoFijo (renta, luz, telefono, salarios, patente, etc.) no tenia columna de monto -
    solo se usaba como recordatorio (nombre, dia, frecuencia), sin monto en quetzales
    (equilibrio_tool en tools/contabilidad_tool.py ya traia un comentario explicito "No
    tenemos montos, solo recordatorios" y sumaba Q0 de pagos fijos al punto de equilibrio).
    Se agrego la columna Monto (migracion database.nimbo_db.init_pagos_fijos_ext(), ALTER
    TABLE con try/except OperationalError, mismo patron que Cliente.GrupoCliente) - ahora es
    obligatorio pedirla al crear un pago fijo nuevo por chat (step nuevo pago_waiting_monto
    en core/nimbo.py, entre pago_waiting_frecuencia y el guardado final) y se corrigio
    equilibrio_tool para sumar el monto real en vez de Q0. Los pagos fijos creados ANTES de
    esta migracion quedan en Q0 hasta que se les fije un monto manualmente: "pago fijo renta
    es Q1500" / "monto del pago fijo de renta es 1500" (intent pago.monto,
    core/detectors/evento_detector.py + tools/evento_tool.py monto_pago_tool,
    database.nimbo_db.set_monto_pago_fijo - busca por nombre con LIKE, si coincide con mas de
    un pago fijo activo pide ser mas especifico en vez de actualizar el primero al azar).
    "ver pagos" (pago.listar) ahora tambien muestra el monto de cada uno.
  - Desde el chat: "flujo de caja" / "flujo de caja proyectado" / "cuanto dinero tendre el
    proximo mes" (contabilidad.flujo_proyectado) da el resumen (ingresos/egresos/neto);
    "proyeccion financiera" (contabilidad.flujo_proyectado_detalle) da el desglose completo.
    Se movio el patron `flujo de caja` de PATTERNS_BALANCE a un set de patrones nuevo
    (core/detectors/contabilidad_detector.py) porque antes ese texto exacto caia en
    contabilidad.balance (balance del mes actual, no una proyeccion) - no pueden coexistir
    los dos intents con el mismo texto.
  - Widget en el dashboard (/api/contabilidad/flujo-caja-proyectado, admin-only): monto neto
    proyectado (verde si positivo, rojo si negativo) + totales de ingresos/egresos, con boton
    "Ver detalle completo" que abre un modal (modal-flujo-caja en templates/index.html) con el
    desglose linea por linea (mismo patron de fetch-on-click que verFotosServicio()).
- Limpieza de codigo huerfano: se identificaron (al construir mapa_nimbo.html, ver ese
  archivo) 19 archivos que existian y se cargaban al arrancar el servidor pero a los que
  ningun mensaje real del chat podia llegar, porque sus detectores nunca se importaron en
  core/intent_detector.py (a diferencia de tools/, la carpeta core/detectors/ NO se carga
  automatico por convencion - cada detector se importa a mano ahi, y estos 3 nunca se
  agregaron). Se verifico con un analisis de imports basado en ast de Python (no solo
  grep) que ninguno de los 19 tenia un importador fuera del propio grupo antes de
  borrarlos con git rm (conserva el historial). Eliminados: tools/budget_tool.py +
  core/detectors/budget_detector.py + services/budget_service.py (presupuestos, nunca
  conectados), tools/customer_tool.py + core/detectors/customer_detector.py +
  services/customer_service.py (duplicado en ingles de cliente_tool.py/
  cliente_detector.py), tools/windows_tool.py + core/detectors/windows_detector.py
  (abria apps de Windows via subprocess, sin relacion con el negocio), core/event_bus.py
  y core/workspace.py (solo los usaba tools/budget_tool.py, ya huerfano),
  core/reasoning_engine.py y core/confirmations.py (placeholders sin ningun caller real
  en el pipeline), y 7 archivos completamente vacios (0 lineas): tools/sales_tool.py,
  services/sales.py, tools/invoice_tool.py, services/invoices.py, services/customers.py,
  core/audit.py, core/permissions.py. Verificacion post-borrado: py_compile sin errores,
  import real de app.py/core.nimbo/core.action_engine/tools sin excepciones, nimbo.db
  intacta. Detalle completo (por que cada uno no se usaba, resultado de las pruebas) en
  BUGS_Y_FIXES.md; la decision de borrar en vez de terminar de conectar o dejar como
  estaba queda en DECISIONS.md. De paso, revisando el codigo real de proveedor_tool.py
  para esta limpieza se encontro que el Pendiente (ver seccion Pendientes) sobre
  proveedor.orden_compra estaba desactualizado - ya se habia corregido en el pasado sin
  actualizar esta nota, ver la seccion "Cuentas por pagar" mas arriba.
- Diagnostico de negocio + tour del dashboard + tutorial del chat: onboarding del admin
  despues del wizard de registro de empresa (/register-empresa) - flujo completo: crear
  empresa -> wizard -> diagnostico de negocio -> dashboard -> tour -> tutorial del chat.
  - Diagnostico: tabla DiagnosticoNegocio en nimbo.db (una fila logica por empresa,
    database.nimbo_db.init_diagnostico_negocio(), agregada a
    core.empresa._inicializar_tablas_empresa() para que las empresas nuevas la tengan
    desde el arranque). GET /diagnostico (solo admin, solo si Completado=0 - si ya esta
    completo redirige al dashboard) muestra un formulario de 6 bloques (el negocio,
    como opera, el control actual, equipo tecnologico, el dueno, la meta - 23 preguntas
    en total, la mayoria radio buttons, dos de texto libre) en una sola pagina
    (templates/diagnostico.html, mismo estilo oscuro que login.html/
    register_empresa.html, todos los bloques ya en el DOM, JS los muestra/oculta con
    una barra de progreso). POST /api/diagnostico/guardar (database.nimbo_db.
    guardar_diagnostico()) calcula ResumenDiagnostico (2 lineas armadas desde las
    respuestas del bloque 1), AreasOportunidad y PrimerosTresPasos: un set de reglas
    (_AREAS_CANDIDATAS en database/nimbo_db.py) evalua las respuestas del bloque 3
    (control actual) y 5 (el dueno) - ej. "lleva el inventario en la cabeza o no lo
    lleva" -> area critica Inventario, "no sabe cuanto gano" -> area critica
    Contabilidad, "se paga agarrando del cajon o no se paga" -> area critica Finanzas
    personales del dueno, "ha tenido perdidas sin saber como" -> area critica Control
    de merma, "vende al credito" -> area de atencion Cuentas por cobrar (mas 3 reglas
    adicionales de la misma naturaleza para poder completar siempre 3 areas aunque
    disparen menos de 3 de las reglas "oficiales") - las 3 con mayor severidad se
    muestran en la pantalla final del formulario junto a un primer paso concreto en
    Nimbo por cada una. GET /api/diagnostico/resumen y POST /api/diagnostico/repetir
    (database.nimbo_db.resetear_diagnostico(), solo pone Completado=0, no borra las
    respuestas anteriores) alimentan el panel Configuracion (ver mas abajo).
  - Salto automatico para empresas con datos existentes (2026-08-05, reemplaza un
    boton manual "Saltar por ahora" que existio brevemente el mismo dia - ver
    BUGS_Y_FIXES.md): index() en app.py (GET /, el dashboard) es el UNICO lugar
    donde se decide si mostrar el diagnostico o saltarlo - /diagnostico en si mismo
    no revisa nada de esto, solo su propio Completado (ver mas abajo). Cada vez que
    un admin entra al dashboard con el diagnostico sin completar, index() calcula
    contar_productos() > 0:
    - 0 productos (empresa nueva de verdad) -> redirige a /diagnostico, que muestra
      el formulario completo de 6 bloques, SIN ningun boton para saltarlo.
    - > 0 productos (empresa con datos existentes - admin re-registrado, o
      diagnostico reseteado a mano desde Configuracion con "Repetir diagnostico de
      negocio") -> nunca llega a ver /diagnostico. index() llama de una vez a
      database.nimbo_db.saltar_diagnostico() (marca Completado=1 con
      FechaCompletado/UltimaActualizacion, sin tocar ninguna columna de respuestas
      ni calcular ResumenDiagnostico/AreasOportunidad/PrimerosTresPasos - quedan en
      None/NULL, porque no hay respuestas reales sobre las que calcularlos e
      "inventar" un resumen mostraria datos enganosos en el panel Configuracion) Y
      TAMBIEN marca Configuracion.tour_completado="1" en el mismo request, para que
      el tour del dashboard (ver mas abajo) tampoco se dispare - el tour solo tiene
      sentido inmediatamente despues de un diagnostico real de una empresa nueva.
    Una vez saltado (o completado de verdad), Completado=1 hace que las siguientes
    visitas a / entren directo al dashboard sin volver a evaluar nada - y una visita
    directa a /diagnostico por URL vieja/manual tambien redirige derecho a / (mismo
    chequeo `if not current_user.is_admin or diagnostico_completado(): redirect`
    que ya existia). "Repetir diagnostico de negocio" (POST /api/diagnostico/repetir,
    database.nimbo_db.resetear_diagnostico()) sigue funcionando igual que antes -
    pone Completado=0 y el frontend redirige a /diagnostico directamente (no pasa
    por index()), asi que un admin que pide repetirlo a proposito SI ve el
    formulario real sin importar cuantos productos tenga; si lo abandona sin
    terminarlo, la siguiente vez que entre al dashboard normal (index()) se
    vuelve a saltar solo, igual que la primera vez.
  - Tour del dashboard: Shepherd.js (CDN, con integrity/crossorigin - no se instalo
    via npm) sobre 10 pasos, resaltando elementos reales del sidebar/dashboard
    (sidebar-nav, boton de Chat, #recordatorios-widget, Inventario, Caja, Analisis,
    Configuracion) - el paso "Ventas" no resalta ningun elemento particular (no existe
    un panel "Ventas" separado en el sidebar, las ventas se hacen desde Caja o por
    chat) y queda como paso informativo centrado. Arranca solo (con un pequeno delay
    para que el layout ya este pintado) si `tour_pendiente` (Jinja, calculado en
    index() como current_user.is_admin y Configuracion.tour_completado != "1") es
    true - templates/index.html. Al terminar o cancelar el tour, POST
    /api/tour/completar marca Configuracion.tour_completado="1" y cambia al panel de
    Chat. Boton "Ver tour del dashboard" en Configuracion (POST /api/tour/resetear +
    recargar la pagina) lo vuelve a mostrar cuando se quiera. tour_completado tambien
    se marca "1" automaticamente (sin mostrar el tour) cuando index() salta el
    diagnostico por tener la empresa datos existentes - ver el punto de "Salto
    automatico para empresas con datos existentes" mas arriba.
  - Tutorial del chat: mensaje fijo (ejemplos reales de comandos por categoria -
    inventario, ventas, clientes, reportes, otros) inyectado como un mensaje mas del
    chat (addMsgToUI(), no un popup aparte) la primera vez que se abre el panel Chat,
    independiente del rol (lo ve quien sea que abra el chat primero, no solo el
    admin). Controlado por Configuracion.chat_tutorial_mostrado (POST
    /api/chat/tutorial-mostrado lo marca "1" la primera vez que se muestra).
  - Panel Configuracion (solo admin): tarjeta "Diagnostico y tour" con el resumen del
    ultimo diagnostico completado (fecha + areas de oportunidad, GET
    /api/diagnostico/resumen) y los botones "Repetir diagnostico de negocio" y "Ver
    tour del dashboard" descritos arriba.

## Tablas nimbo.db
Producto, Stock, Cliente, OrdenServicio, HistorialOrden, Kardex, StockMinimo, ProductoFoto,
ProductoInfo, FotoOrdenServicio, InformeRevision, TarifaManoObra,
Venta, ResumenTrimestral, PagoFijo, RecordatorioPersonal, ChatHistorial,
Gasto, ResumenContable, Proveedor, ContactoProveedor, ProductoProveedor,
OrdenCompra, ItemOrdenCompra, HistorialPrecio, Usuario, PasswordResetToken, Configuracion,
Cotizacion, CajaTurno, MovimientoCaja, ItemCarrito, Descuento, GarantiaProducto, GarantiaVenta,
ProductoCombo, ItemCombo, UnidadMedida, PuntosCliente, MovimientoPuntos, CodigoBarrasGenerado,
GrupoDescuento, CuentaCobrar, PagoCuenta, CuentaPagar, PagoPagar, DiagnosticoNegocio

## Variables de entorno (.env)
FLASK_SECRET_KEY, OPENCLAW_TOKEN, FB_PAGE_TOKEN, FB_PAGE_ID, WA_TOKEN, WA_PHONE_ID,
IG_ACCOUNT_ID, MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, ADMIN_EMAIL

## Google Cloud
- Proyecto: pivotal-mode-499817-t7
- Veo 3: us-central1
- Gemini Vertex: us-east5

## Pendientes
1. Instagram API (esperando aprobacion Meta)
2. TikTok API (en revision)
3. Metas semanales
4. Nimbo accesible desde telefono (afecta a Cotizaciones: el link del PDF en el mensaje
   de WhatsApp solo abre en la red local hasta que el dashboard sea accesible publicamente)
5. App movil
6. Mejorar OpenClaw vs Gemini deteccion
7. Comando de chat para marcar una garantia como RECLAMADA (integracion futura con
   Servicio Tecnico)
8. Cuentas por cobrar en Caja/Cotizaciones: "credito" como metodo de pago solo se
   implemento en el flujo de venta simple del chat (ver seccion Cuentas por cobrar), no
   en /api/caja/cobrar ni en cotizacion.aceptar
9. Stock.StockMinimo (columna nueva de la tabla Stock propia, ver "Catalogo propio
   (Producto/Stock)") no esta consolidada con la tabla StockMinimo ya existente
   (ProductId/ProductName/Minimo) - son dos lugares con el mismo dato, StockMinimo
   sigue siendo el que de verdad usan las alertas/pedidos sugeridos.
10. Categoria y Unidad de la tabla Producto existen en el esquema pero ningun flujo las
    llena o las lee todavia (ver misma seccion).

FLUJO EN TIENDA (pendiente):
- Calculo automatico de comision POS solo cuando paga con tarjeta (Caja ya distingue
  TotalEfectivo/TotalTarjeta/TotalMixto por turno, pero no resta la comision del POS)
- Impresion fisica del ticket (Caja ya genera el texto completo del ticket -
  services/ticket.py, /api/caja/cobrar y /api/caja/imprimir-ticket - falta conectarlo a una
  impresora termica real)
- Reimpresion de tickets antiguos con detalle por producto (hoy /api/caja/imprimir-ticket
  solo reconstruye un ticket simplificado a partir de Venta.Descripcion, porque el detalle de
  ItemCarrito se borra al cobrar; requeriria guardar un snapshot de items por venta)

FLUJO EN LINEA (futuro):
- Pagina web para clientes con chat de Nimbo
- Nimbo muestra inventario, fotos y precios al publico
- Opcion de negociar precio por WhatsApp con vendedor
- Opcion de compra online
- Integracion con pasarela de pagos Guatemala (Visanet, BAC Credomatic)
