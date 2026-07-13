# Nimbo AI Dashboard - Mi Cocina Electrodomesticos Guatemala

## Descripcion
Sistema de gestion empresarial con IA para tienda de electrodomesticos y repuestos en Guatemala.
Chat en lenguaje natural en espanol que controla todo el negocio.

## Stack
- Backend: Flask (Python 3.10) en WSL2, puerto 5000
- IA Principal: Google Gemini 2.5 Flash Lite via API
- Agente PC: OpenClaw con Gemini (puerto 18789)
- Base de datos 1: Aronium SQLite /mnt/c/Users/Victor Paxtor/AppData/Local/Aronium/Data/pos.db
- Base de datos 2: Nimbo SQLite /home/ictor_axtor/micocina-dashboard/nimbo.db

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
     los pasos que llaman a Gemini/OpenClaw abajo, para resolver referencias
     como "cuantas quedan?" sin repetir el nombre del producto.
-> 1. Verifica contexto activo (flujos conversacionales)
-> 2. ActionEngine -> IntentDetector -> Detectores -> Tool
-> 3. Si no detecta -> Gemini traduce (con el contexto reciente) -> intenta de nuevo
-> 3.5. Si sigue sin detectar -> Gemini analiza si es una intencion de negocio vaga
        (tambien con contexto) y genera una pregunta de clarificacion
        (context.step = "clarificando")
-> 4. Si nada -> OpenClaw responde (recibe el contexto como resumen en el
     system prompt, ver openclaw_bridge.py send_to_openclaw(message, contexto))

## Login y roles
- Flask-Login. Roles: admin (acceso total) y empleado (solo inventario, ventas y clientes;
  el resto de categorias de intent quedan bloqueadas tanto en las rutas API como dentro
  del chat, ver core/action_engine.py).
- Primera instalacion: mientras Configuracion.onboarding_completado != "1", cualquier
  ruta redirige a /setup, que a su vez redirige a /setup/<paso> (wizard de 6 pasos,
  progreso guardado en Configuracion.onboarding_step):
  1. Bienvenida (nombre del negocio, tipo, pais)
  2. Cuenta admin (nombre, usuario, contrasena, correo) -> crea el usuario admin
  3. Configuracion inicial (moneda, horario de apertura/cierre, dias laborales)
  4. Primer producto (opcional, se puede saltar) -> crea Product+Stock en Aronium
  5. Primer cliente (opcional, se puede saltar) -> crea Cliente en nimbo.db
  6. Resumen + boton "Entrar al dashboard" -> marca onboarding_completado="1" y
     redirige a /login
  No se puede saltar a un paso mas adelante del progreso guardado (antes-request
  rebota al paso actual); si se completa, /setup redirige directo a /login.
  Instalaciones que ya tenian usuarios antes de que existiera el wizard se marcan
  como completas automaticamente al arrancar (ver app.py, justo despues de
  init_usuarios()/init_configuracion()).
- Gestion de usuarios: panel "Usuarios" en el dashboard (solo admin) -> listar, crear,
  activar/desactivar, y cambiar contrasena de cualquier usuario sin pedir la actual.
  Backend: /api/usuarios (GET/POST), /api/usuarios/<id>/toggle, /api/usuarios/<id>/password.
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
  para pasarlo como contexto a Gemini y OpenClaw
- core/intent_detector.py - Carga todos los detectores
- core/command_normalizer.py - Corrige errores tipograficos comunes (ej. "cuchila"->"cuchilla")
  palabra por palabra (diccionario + difflib.get_close_matches contra un vocabulario de
  verbos/sustantivos del negocio) y quita acentos, antes de que el mensaje llegue a los
  detectores. Corre una sola vez, al inicio de IntentDetector.detect().
- core/action_engine.py - Orquestador, aplica el gate de roles admin/empleado por categoria de intent
- core/auth.py - Login, usuarios, roles, recuperacion de contrasena
- core/configuracion.py - Configuracion del negocio (clave/valor)
- core/detectors/ - inventory, service, cliente, venta, proveedor, contenido, reporte, evento, contabilidad, cotizacion
- tools/ - mismo set de modulos, carga automatica via __init__.py
- database/aronium.py - Todas las funciones de BD. get_products(search) intenta busqueda
  fuzzy con difflib.SequenceMatcher (contra el nombre completo y cada palabra del nombre)
  si la busqueda exacta (LIKE) no encuentra nada. services/inventory.py delega su search()
  aqui para heredar el mismo fallback.
- services/whatsapp.py - WhatsApp Business API
- services/social_media.py - Facebook/Instagram API
- services/video_gen.py - Veo 3 video generation
- services/mail_service.py - Envio de correo (Flask-Mail) + logging de errores SMTP
- services/pdf_cotizacion.py - Genera el PDF de cotizaciones (reportlab), logo static/icon.png,
  guardado en static/cotizaciones/COT-XXXX.pdf (publico, sin login, para poder compartirse por WhatsApp)
- static/fotos/ - Fotos de productos
- static/videos/ - Videos generados
- templates/index.html - Frontend completo (dashboard, panel Usuarios solo admin)
- templates/login.html, setup.html, forgot_password.html, reset_password.html

## Modulos completados
- Inventario: CRUD, kardex, alertas stock, fotos, descripcion
- Ventas: flujo completo, WhatsApp, descuento stock automatico
- Clientes: historial, Excel, cumpleanos
- Servicio Tecnico: OS-XXXX, flujo 7 estados, WhatsApp automatico
- Proveedores: contactos, pedidos sugeridos, ordenes compra, alertas precio
- Contabilidad: balance, IVA/ISR, margen, inventario valor, equilibrio, analisis Gemini, Excel, comparacion 6 meses,
  sugerencias de precios ("analiza mis precios" / "sugerencias de precios") -> contabilidad.sugerencias_precios
  en tools/contabilidad_tool.py. Calcula el margen real (Precio-Costo)/Precio por producto usando
  get_margen_productos(); si es menor a 30% calcula un precio sugerido deterministico en Python
  (costo / (1 - 6% comision POS - 30% margen objetivo)) y le pasa a Gemini los productos ya separados
  en dos grupos (saludable / necesita ajuste) para que solo narre el analisis sin recalcular ni inventar
  precios. Usa tambien get_balance_mes() (gastos operativos, ingresos) como contexto. Admin-only.
- Reportes: dia/mes/trimestre/semestre/anual, Excel, automatico 5:30pm, limpieza anual
- Contenido: posts, scripts, video Veo3, publicacion Facebook
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
  automaticamente (database.aronium.marcar_cotizaciones_vencidas(), se corre de forma lazy
  cada vez que se consultan) y aparecen en /api/recordatorios ("vence hoy" / "vencio").
  Widget en el dashboard (contadores Pendientes/Enviadas/Aceptadas de la semana + lista de
  activas con dias restantes) via /api/cotizaciones/resumen.

## Tablas nimbo.db
Cliente, OrdenServicio, HistorialOrden, Kardex, StockMinimo, ProductoFoto, ProductoInfo,
Venta, ResumenTrimestral, PagoFijo, RecordatorioPersonal, ChatHistorial,
Gasto, ResumenContable, Proveedor, ContactoProveedor, ProductoProveedor,
OrdenCompra, ItemOrdenCompra, HistorialPrecio, Usuario, PasswordResetToken, Configuracion,
Cotizacion

## Variables de entorno (.env)
GEMINI_API_KEY, FB_PAGE_TOKEN, FB_PAGE_ID, WA_TOKEN, WA_PHONE_ID, IG_ACCOUNT_ID,
MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, ADMIN_EMAIL

## Google Cloud
- Proyecto: pivotal-mode-499817-t7
- Veo 3: us-central1
- Gemini Vertex: us-east5

## Pendientes
1. Garantias de productos
2. Instagram API (esperando aprobacion Meta)
3. TikTok API (en revision)
4. Deudas/pagos a plazos
5. Metas semanales
6. Nimbo accesible desde telefono (afecta a Cotizaciones: el link del PDF en el mensaje
   de WhatsApp solo abre en la red local hasta que el dashboard sea accesible publicamente)
7. App movil
8. Mejorar OpenClaw vs Gemini deteccion

FLUJO EN TIENDA (pendiente):
- Multiples metodos de pago en una venta (efectivo + tarjeta)
- Calculo automatico de comision POS solo cuando paga con tarjeta
- Recibo/factura imprimible al cerrar venta

FLUJO EN LINEA (futuro):
- Pagina web para clientes con chat de Nimbo
- Nimbo muestra inventario, fotos y precios al publico
- Opcion de negociar precio por WhatsApp con vendedor
- Opcion de compra online
- Integracion con pasarela de pagos Guatemala (Visanet, BAC Credomatic)
