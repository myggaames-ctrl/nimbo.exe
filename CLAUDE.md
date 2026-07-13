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
- core/detectors/ - inventory, service, cliente, venta, proveedor, contenido, reporte, evento, contabilidad, cotizacion, caja
- tools/ - mismo set de modulos, carga automatica via __init__.py
- database/aronium.py - Todas las funciones de BD. get_products(search) intenta busqueda
  fuzzy con difflib.SequenceMatcher (contra el nombre completo y cada palabra del nombre)
  si la busqueda exacta (LIKE) no encuentra nada. services/inventory.py delega su search()
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
  activas con dias restantes) via /api/cotizaciones/resumen. Si aplica un descuento (ver
  Descuentos abajo) se muestra en el resumen del chat, en el PDF (subtotal + descuento +
  total) y se guarda como texto en Cotizacion.Notas.
- Descuentos: tabla Descuento en nimbo.db (database.aronium.init_descuentos/crear_descuento/
  get_descuentos/get_descuento_por_id/buscar_descuentos/desactivar_descuento). 4 tipos:
  cliente (ClienteId), temporada (FechaInicio/FechaFin), producto (ProductoId, referencia
  al Product.Id de Aronium igual que el resto del sistema), monto (MontoMinimo, "compras
  mayores a"). Cada descuento define Porcentaje o MontoFijo (uno de los dos).
  database.aronium.calcular_descuento(cliente_id, productos, total, fecha=None) evalua
  todos los descuentos activos y devuelve el mejor (mayor monto en quetzales) - los
  descuentos NO se acumulan, se aplica solo uno. Para tipo "producto" la base del calculo
  es la suma de los subtotales de los items del carrito que coincidan con ese ProductoId,
  no el total completo; para cliente/temporada/monto la base es el total completo. Se
  aplica automaticamente (sin que el usuario tenga que pedirlo) en los 3 lugares donde se
  cierra una venta: paso venta_waiting_pago del flujo de venta simple en core/nimbo.py,
  database.aronium.cobrar_carrito() (caja) y _finalizar_cotizacion() en core/nimbo.py
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
  (database.aronium.DENOMINACIONES).
  - "abrir caja"/"cerrar caja" por chat (flujo conversacional en core/nimbo.py, steps
    caja_abrir_denom/caja_cerrar_denom, uno por denominacion) o desde la UI (modal con grid
    de 7 inputs, mismo componente reusado para apertura/cierre/detalle de billetes al cobrar).
  - Venta: buscar/escanear producto (input con Enter, /api/caja/carrito/agregar, matchea por
    Code exacto primero y si no por nombre fuzzy) -> carrito (ItemCarrito, temporal por turno)
    -> cobrar (/api/caja/cobrar) con Efectivo/Tarjeta/Mixto. Descuenta stock (remove_stock,
    con verificacion de stock de todos los items antes de descontar ninguno) + registra Venta
    + Kardex (via remove_stock) + genera el texto del ticket (services/ticket.py) en la misma
    respuesta. Reimpresion simplificada (sin detalle por producto) via /api/caja/imprimir-ticket.
  - Cambio: para Efectivo, "cuanto paga el cliente" es opcional (por defecto = total exacto);
    el desglose de billetes recibidos es opcional/colapsable ("detalle de billetes") - si se
    da, database.aronium._calcular_cambio_denominaciones() arma el vuelto en billetes
    disponibles (greedy, mayor a menor) para el registro anti-fraude; si no se da, solo se
    registra el monto total (sin desglose para ese movimiento).
  - Cada movimiento de caja (MovimientoCaja: FONDO/VENTA/RETIRO/AJUSTE) puede guardar un JSON
    de Denominaciones que representa el DELTA neto por denominacion (positivo = entra,
    negativo = sale). database.aronium.get_denominaciones_actuales() sirve para saber el
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
  - FondoInicial es inmutable: se fija una unica vez en el INSERT de database.aronium.abrir_turno()
    y no existe en todo el codebase ninguna funcion/endpoint que le haga UPDATE despues (la
    consola SQL del dashboard es solo SELECT y solo contra Aronium/pos.db, nunca contra
    nimbo.db). La unica forma de corregir un fondo mal capturado es que un admin anule el turno.
  - Fondo inicial automatico: al abrir un turno nuevo, si existe un turno CERRADO previo,
    database.aronium.get_ultimo_cierre_denominaciones() recupera el desglose que se conto
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
  FechaVencimientoPropias). Estado (VIGENTE/VENCIDA/RECLAMADA): database.aronium.
  marcar_garantias_vencidas() (lazy, igual que las cotizaciones) solo marca VENCIDA
  cuando YA pasaron AMBAS fechas - si cualquiera de las dos sigue vigente, el producto
  sigue cubierto. RECLAMADA no se toca automaticamente (no hay comando de chat para
  marcarla todavia, queda para una integracion futura con Servicio Tecnico).
  - Integracion con ventas: database.aronium.generar_garantia_venta() se llama
    automaticamente (una vez por cada linea de producto distinta) desde los 3 lugares
    donde se cierra una venta - paso venta_waiting_pago/venta_waiting_pago_mixto_tarjeta
    en core/nimbo.py (via el helper _registrar_venta_chat), database.aronium.
    cobrar_carrito() (caja) y tools/cotizacion_tool.py aceptar_cotizacion_tool() (cuando
    se acepta una cotizacion). Si el producto no tiene GarantiaProducto configurada usa
    30 dias propios y 0 de fabrica por defecto. El numero de garantia se muestra en la
    respuesta del chat, en el ticket de caja (services/ticket.py, seccion GARANTIAS antes
    del pie) y en el mensaje de factura por WhatsApp (services/whatsapp.py
    enviar_factura_whatsapp, parametro garantia).
  - Recordatorios: get_recordatorios() (database/aronium.py) agrega un recordatorio por
    cada garantia que vence en los proximos 7 dias (get_garantias_por_vencer(dias=7)).
  - Detector core/detectors/garantia_detector.py + herramienta tools/garantia_tool.py.
    Comandos de chat: "garantia de cuchilla es 30 dias" (configura solo DiasPropia, sin
    tocar DiasFabrica), "garantia de licuadora oster es 365 dias fabrica y 180 dias
    nuestra" (configura ambos dias), "ver garantia GAR-0001" (estado + fechas), "garantias
    de Juan Perez" (todas las de un cliente, busca por ClienteNombre/ClienteTelefono),
    "garantias por vencer" (proximos 30 dias, distinto del recordatorio automatico de 7
    dias). Admin-only (categoria "garantia" no esta en CATEGORIAS_EMPLEADO de
    core/action_engine.py).

## Tablas nimbo.db
Cliente, OrdenServicio, HistorialOrden, Kardex, StockMinimo, ProductoFoto, ProductoInfo,
Venta, ResumenTrimestral, PagoFijo, RecordatorioPersonal, ChatHistorial,
Gasto, ResumenContable, Proveedor, ContactoProveedor, ProductoProveedor,
OrdenCompra, ItemOrdenCompra, HistorialPrecio, Usuario, PasswordResetToken, Configuracion,
Cotizacion, CajaTurno, MovimientoCaja, ItemCarrito, Descuento, GarantiaProducto, GarantiaVenta

## Variables de entorno (.env)
GEMINI_API_KEY, FB_PAGE_TOKEN, FB_PAGE_ID, WA_TOKEN, WA_PHONE_ID, IG_ACCOUNT_ID,
MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, ADMIN_EMAIL

## Google Cloud
- Proyecto: pivotal-mode-499817-t7
- Veo 3: us-central1
- Gemini Vertex: us-east5

## Pendientes
1. Instagram API (esperando aprobacion Meta)
2. TikTok API (en revision)
3. Deudas/pagos a plazos
4. Metas semanales
5. Nimbo accesible desde telefono (afecta a Cotizaciones: el link del PDF en el mensaje
   de WhatsApp solo abre en la red local hasta que el dashboard sea accesible publicamente)
6. App movil
7. Mejorar OpenClaw vs Gemini deteccion
8. Comando de chat para marcar una garantia como RECLAMADA (integracion futura con
   Servicio Tecnico)

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
