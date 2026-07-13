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
- Clientes: historial completo, Excel, cumpleanos. "historial de Juan Perez" (cliente.historial,
  tools/cliente_tool.py) muestra todo desde el primer dia: datos (telefono/email/NIT/fecha de
  alta), estadisticas (total gastado, producto favorito, frecuencia de compra en dias promedio,
  ultima visita, descuento tipo cliente si tiene uno configurado - ver database.aronium.
  get_descuentos), compras (Descripcion + Total + metodo de pago), ordenes de servicio,
  cotizaciones y garantias activas. database.aronium.get_historial_cliente(cliente_id,
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
  garantia tiene esta reparacion?", default database.aronium.DIAS_GARANTIA_REPARACION_DEFAULT
  = 30, acepta 'default' o un numero). Con la respuesta ya se marca ENTREGADO
  (actualizar_estado_orden) y se genera la garantia (database.aronium.
  generar_garantia_reparacion) - reutiliza la MISMA tabla GarantiaVenta de las garantias de
  producto, distinguida por la columna Tipo ('producto' default o 'reparacion', agregada con
  ALTER TABLE en init_garantias() porque la tabla ya existia de antes) y OrdenServicioId (para
  vincularla a la orden; no tiene VentaId porque no es una venta de producto). Numeracion
  aparte: GARR-XXXX en vez de GAR-XXXX (secuencia propia, WHERE Tipo='reparacion'). El mensaje
  de WhatsApp de entrega (antes solo se enviaba para LISTO, nunca para ENTREGADO) ahora si se
  manda en ENTREGADO e incluye "Su reparacion tiene garantia GARR-XXXX valida hasta [fecha]"
  (services/whatsapp.py enviar_notificacion_orden, parametro garantia).
  - "garantia de reparacion OS-0001" (service.ver_garantia_reparacion) muestra el estado y
    vencimiento de la garantia de esa orden (database.aronium.get_garantia_reparacion_por_orden).
  - "reclamacion garantia OS-0001" / "reclamar garantia OS-0001" (service.reclamar_garantia,
    database.aronium.reclamar_garantia_reparacion): verifica que la garantia siga VIGENTE (si
    esta VENCIDA o ya fue RECLAMADA antes, rechaza con el motivo), la marca RECLAMADA (unico
    lugar del codebase que usa ese estado - antes quedaba sin comando de chat, ver seccion
    Garantias) y crea una OrdenServicio nueva sin costo para el mismo cliente/equipo,
    anotando en Observaciones la garantia y orden originales.
  - Se aprovecho para cerrar una ambiguedad preexistente entre detectores: "garantia de
    reparacion X" coincidia tambien con el catch-all "garantias de X" (busqueda de garantias
    de un cliente) de core/detectors/garantia_detector.py, que se revisa antes que
    ServiceDetector - se le agrego un lookahead negativo para excluir "reparacion".
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
  sigue cubierto. RECLAMADA no se toca automaticamente; el unico lugar que la usa es
  "reclamacion garantia OS-XXXX" para garantias de reparacion (ver seccion Servicio
  Tecnico) - las garantias de producto no tienen todavia un comando de chat para
  reclamarlas, se marcarian igual via database.aronium si hiciera falta.
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
- Combos/Kits: 2 tablas en nimbo.db. ProductoCombo (Nombre/Descripcion/PrecioCombo/Activo)
  + ItemCombo (ComboId, ProductoId de Aronium, ProductoNombre, Cantidad - N filas por
  combo). database.aronium.DESCUENTO_COMBO_SUGERIDO = 0.08 (8%) es el descuento por
  defecto que se sugiere sobre la suma de precios individuales, tanto en la creacion
  manual como en las sugerencias con Gemini.
  - "crear combo Kit Licuadora" inicia un flujo conversacional en core/nimbo.py (steps
    combo_crear_waiting_producto/seleccion/cantidad, igual que las cotizaciones: agrega
    productos + cantidad en loop hasta 'listo') y al terminar sugiere el precio con 8% de
    descuento (step combo_crear_waiting_precio, el admin puede aceptar con "si" o escribir
    su propio monto) antes de guardar el combo (database.aronium.crear_combo).
  - "ver combos" lista los combos activos con su precio y detalle de productos
    (tools/combo_tool.py, database.aronium.get_combos()).
  - "vender combo Kit Licuadora" es una venta directa de una sola vez (a diferencia de
    "crear combo", no es un flujo de varios pasos) - database.aronium.vender_combo()
    busca el combo por nombre (buscar_combos, fuzzy LIKE), verifica stock de todos sus
    productos antes de descontar ninguno, descuenta el stock de cada uno, registra una
    sola Venta por el PrecioCombo (ya con el descuento incluido, via
    registrar_venta_cliente) y genera la garantia de cada producto (generar_garantia_venta,
    igual que cualquier otra venta). Vende a "Consumidor Final" sin pedir cliente ni
    metodo de pago (mantiene el comando de un solo paso); para atribuir la venta a un
    cliente especifico o cobrar por caja, hay que vender los productos del combo por
    separado con descuento manual en vez de usar este comando.
  - "sugerir combos" (database.aronium via tools/combo_tool.py sugerir_combos_tool):
    manda el inventario actual con stock > 0 (nombre, precio, stock) a Gemini pidiendole
    exactamente 3 combos logicos en JSON estricto (nombre/descripcion/productos, usando
    los nombres exactos del inventario). Gemini solo decide QUE productos van juntos
    (criterio de negocio); Python hace el match contra el inventario real (get_products,
    mismo fuzzy fallback que el resto del sistema) y calcula el precio con el 8% de
    descuento de forma determinista, sin confiar en la aritmetica de Gemini (mismo patron
    que contabilidad.sugerencias_precios). Si un producto sugerido no matchea con nada
    real se descarta esa entrada; si un combo se queda con menos de 2 productos reales se
    omite. Requiere GEMINI_API_KEY; sin esa variable devuelve un mensaje explicando que
    Gemini no esta configurado, sin crear nada.
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
    database.aronium.get_products()).
  - Se aprovecho para corregir un bug preexistente en core/nimbo.py venta_waiting_seleccion
    (el paso donde se elige un producto entre varios resultados similares al vender): nunca
    descontaba stock, sin importar el flujo. Ahora descuenta cantidad x CantidadPorUnidad
    (4to campo opcional en cada opcion de venta_opciones, ausente = 1 para una venta normal
    por unidad) y valida que haya stock suficiente antes de continuar.
- Programa de lealtad (puntos): 2 tablas en nimbo.db. PuntosCliente (1 fila por cliente) -
  PuntosAcumulados (historico de por vida, nunca baja), PuntosUsados y PuntosCancelados
  (ambos tambien acumulativos; el saldo disponible para canjear = Acumulados - Usados -
  Cancelados, ver database.aronium.get_saldo_puntos). MovimientoPuntos es el detalle
  (GANADO/USADO/CANCELADO) de cada cambio, con VentaId para saber a que venta corresponde.
  Constantes en database/aronium.py: PUNTOS_POR_QUETZAL=1 (1 punto por cada Q1 de compra,
  sobre el total ya con todos los descuentos/creditos aplicados), PUNTOS_POR_CANJE=100,
  VALOR_CANJE=Q10 (asi que 1 punto = Q0.10), DESCUENTO_EXTRA_ORO=5%. Los puntos no vencen
  (no hay ninguna funcion que reste PuntosCancelados via chat - ese campo del esquema queda
  para una integracion futura, ej. anular una venta).
  - Niveles (opcional del pedido original, si se implemento): NIVELES_LEALTAD evalua sobre
    PuntosAcumulados (no el saldo disponible - el nivel no baja solo porque el cliente
    canjeo puntos): Bronce 0-499, Plata 500-999, Oro 1000+ (5% de descuento extra en cada
    compra, ver mas abajo).
  - "Canjear" no descuenta nada de inmediato: database.aronium.canjear_puntos() resta el
    saldo (PuntosUsados) y el credito en quetzales queda pendiente como un MovimientoPuntos
    Tipo='USADO' con VentaId=NULL. database.aronium.calcular_ajuste_puntos(cliente_id, total)
    - llamada ANTES de insertar cualquier Venta - busca ese credito pendiente
    (peek_credito_puntos_pendiente) y lo resta del total (topado al total de esa venta, sin
    partir el canje si sobra), y encima resta el 5% extra si el cliente es nivel Oro.
    database.aronium.consumir_credito_puntos_pendiente(cliente_id, venta_id) - llamada
    DESPUES de insertar, ya con el venta_id conocido - marca esos movimientos pendientes
    como aplicados a esa venta. database.aronium.ganar_puntos() se llama al final con el
    Total ya ajustado (se ganan puntos sobre lo que el cliente realmente termina pagando).
    database.aronium.formatear_nota_ajuste_puntos() arma la nota que se anexa a la
    Descripcion de la Venta cuando aplico alguno de los dos ajustes.
  - Integrado en los 4 lugares donde se cierra una venta: core/nimbo.py
    venta_waiting_pago/venta_waiting_pago_mixto_tarjeta (venta simple del chat),
    database.aronium.cobrar_carrito() (caja) y database.aronium.registrar_venta_cliente()
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
  database.aronium.generar_ean13() arma un EAN-13 con prefijo 20 (rango 200-299, reservado
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
    database.aronium.get_productos_sin_codigo() (Product.Code NULL o vacio), genera un
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
    busca el producto por Code (database.aronium.get_product_by_code, que ahora tambien trae
    Product.Description de Aronium), muestra foto (ProductoFoto en nimbo.db) + nombre +
    precio + descripcion (ProductoInfo en nimbo.db si existe, si no la Description nativa de
    Aronium) - nunca stock ni costo. 404 con pagina propia si el codigo no matchea ningun
    producto.
  - Detector core/detectors/codigo_barras_detector.py + herramienta
    tools/codigo_barras_tool.py. Categorias "codigobarras" y "etiqueta" SI son de empleado
    (CATEGORIAS_EMPLEADO en core/action_engine.py) - generar codigos/etiquetas es una tarea
    operativa de bodega, igual que el resto de inventario, no una decision de precios.

## Tablas nimbo.db
Cliente, OrdenServicio, HistorialOrden, Kardex, StockMinimo, ProductoFoto, ProductoInfo,
Venta, ResumenTrimestral, PagoFijo, RecordatorioPersonal, ChatHistorial,
Gasto, ResumenContable, Proveedor, ContactoProveedor, ProductoProveedor,
OrdenCompra, ItemOrdenCompra, HistorialPrecio, Usuario, PasswordResetToken, Configuracion,
Cotizacion, CajaTurno, MovimientoCaja, ItemCarrito, Descuento, GarantiaProducto, GarantiaVenta,
ProductoCombo, ItemCombo, UnidadMedida, PuntosCliente, MovimientoPuntos, CodigoBarrasGenerado

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
