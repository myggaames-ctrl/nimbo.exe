# Historial de bugs y correcciones de Nimbo

Este documento reconstruye, a partir del historial real de `git log` y de las notas de
auditoría dejadas en `CLAUDE.md`, todos los bugs identificados y corregidos durante el
desarrollo de Nimbo. Están ordenados cronológicamente. Cada uno indica el commit de git
donde se corrigió, para que se pueda verificar el cambio exacto con
`git show <hash>`.

No se incluyen aquí features nuevas ni decisiones de diseño (esas están en
`DECISIONS.md`) - solo comportamientos que estaban rotos y se corrigieron.

---

## 1. La venta con selección múltiple nunca descontaba stock

**Qué pasaba:** cuando un usuario vendía un producto y el nombre coincidía con VARIOS
productos parecidos (ej. "cuchilla" matcheando "Cuchilla Oster" y "Cuchilla Osterizer"),
Nimbo mostraba una lista para elegir. Sin importar qué opción eligiera el usuario, la
venta se registraba y se cobraba, pero el inventario nunca se descontaba - el stock
quedaba desactualizado después de cada venta con selección múltiple.

**Por qué pasaba:** el paso `venta_waiting_seleccion` (en `core/nimbo.py`, donde el
usuario responde con el número de la opción elegida) armaba el resto del flujo de venta
pero se le olvidó llamar a la función que resta el stock - a diferencia del flujo normal
de un solo producto, que sí la llamaba.

**Cómo se arregló:** se agregó el descuento de stock en ese paso, multiplicando la
cantidad por el `CantidadPorUnidad` correspondiente (para que también funcionara bien
con unidades de medida como "docena"), y validando que hubiera stock suficiente antes de
continuar.

**Archivo(s) cambiados:** `core/nimbo.py`

**Fecha aproximada:** 2026-07-13 (commit `e0eaa2a`, "Unidades de medida: docena, caja,
par con precios por volumen" - se corrigió de paso al tocar ese mismo flujo)

---

## 2. "Garantía de reparación X" se confundía con una búsqueda de garantías de cliente

**Qué pasaba:** al escribir "garantía de reparación OS-0001" para consultar la garantía
de una reparación específica, Nimbo respondía como si se estuviera buscando "las
garantías de un cliente llamado Reparación Os-0001" - una respuesta sin sentido.

**Por qué pasaba:** `GarantiaDetector` tiene un patrón genérico ("garantías de X" =
buscar las garantías de un cliente por nombre) que se revisa ANTES que el patrón
específico de garantía de reparación, y ese patrón genérico también coincidía con la
frase "garantía de reparación X".

**Cómo se arregló:** se agregó una excepción (lookahead negativo) al patrón genérico
para que ignore explícitamente la palabra "reparación" en esa posición, dejando que el
patrón correcto la reconozca.

**Archivo(s) cambiados:** `core/detectors/garantia_detector.py`

**Fecha aproximada:** 2026-07-13 (commit `0636187`, "Garantias de reparacion GARR-0001
con reclamacion automatica")

---

## 3. Generar etiquetas fallaba con códigos que no eran EAN-13 válido

**Qué pasaba:** al pedir la etiqueta de un producto cuyo código venía heredado de
Aronium (por ejemplo "01293428", de solo 8 dígitos, o alfanumérico como "LIC001"),
Nimbo fallaba con un error en vez de generar el PDF de la etiqueta.

**Por qué pasaba:** la función que dibuja el código de barras asumía que TODO código
tenía exactamente 13 dígitos numéricos (formato EAN-13, el que Nimbo genera para
productos nuevos) y trataba de dibujarlo como tal sin comprobarlo primero - con un
código de 8 dígitos o con letras, la librería de códigos de barras lanzaba un error
(`NumberOfDigitsError`) en vez de completar el PDF.

**Cómo se arregló:** ahora se revisa el formato del código antes de dibujarlo: si son
exactamente 13 dígitos numéricos se dibuja como EAN-13; cualquier otro formato se dibuja
como Code128 (un formato de código de barras que acepta cualquier texto o longitud). De
paso, se corrigió también el nombre del archivo PDF generado, que podía tener caracteres
no válidos para un nombre de archivo si el código original traía espacios.

**Archivo(s) cambiados:** `services/barcode_service.py`

**Fecha aproximada:** 2026-07-13 (commit `56846a4`, "Fix etiquetas: Code128 para codigos
cortos, EAN-13 para los generados")

---

## 4. El detector de garantías no reconocía la palabra "nuestra"

**Qué pasaba:** el comando "garantía de licuadora oster es 365 días fábrica y 180 días
**nuestra**" (para configurar tanto los días de garantía del fabricante como los propios
de la tienda) no se reconocía como un comando de garantía válido.

**Por qué pasaba:** el corrector de errores tipográficos de Nimbo (que corre ANTES que
cualquier detector) no tenía la palabra "nuestra" en su lista de vocabulario conocido, así
que la interpretaba como un posible error de tipeo y la "corregía" automáticamente por la
palabra del vocabulario de negocio más parecida - corrompiendo la frase antes de que
`GarantiaDetector` la viera.

**Cómo se arregló:** se agregaron "nuestra", "nuestro", "propia" y "propio" a la lista de
vocabulario conocido, para que el corrector las deje tal cual en vez de intentar
"corregirlas". De paso se agregó también una forma más corta de escribir el comando (sin
la palabra "es").

**Archivo(s) cambiados:** `core/command_normalizer.py`, `core/detectors/garantia_detector.py`

**Fecha aproximada:** 2026-07-13 (commit `616ff3d`, "Fix detector garantias - normalizer
corrompia 'nuestra'")

---

## 5. "Mano de obra" se corrompía a "cobrar" en los informes de servicio técnico

**Qué pasaba:** al escribir un informe de revisión con "...mano de obra 75", o al fijar
un presupuesto con "...mano de obra N", Nimbo no reconocía el comando correctamente - el
monto de mano de obra se perdía o el comando completo fallaba.

**Por qué pasaba:** las palabras "mano" y "obra" no estaban en el vocabulario conocido
del corrector ortográfico, y "obra" en particular se "corregía" sola a "cobrar" (la
palabra del vocabulario de negocio más parecida en distancia de edición) antes de que el
detector de servicio técnico viera el mensaje - rompiendo en silencio tanto el comando de
informe nuevo como el de presupuesto (que ya existía desde antes).

**Cómo se arregló:** se agregaron "mano", "obra", "presupuesto", "técnico(s)",
"informe(s)", "tarifa(s)", "aprobó", "rechazó", "asignada/o", "necesita" y "revisión" al
vocabulario conocido del corrector.

**Archivo(s) cambiados:** `core/command_normalizer.py`

**Fecha aproximada:** 2026-07-13 (commit `9d41fa6`, "Flujo completo servicio tecnico: rol
tecnico, informe revision, presupuesto automatico, aprobacion cliente")

---

## 6. Las alertas de inventario buscaban "s cuchillas" en vez de "cuchillas"

**Qué pasaba:** al preguntar "¿cuándo se acaban **las** cuchillas?", Nimbo a veces
buscaba un producto con un nombre roto, como si el usuario hubiera escrito "s cuchillas"
en vez de "cuchillas" - fallando en encontrar el producto que sí existía.

**Por qué pasaba:** el patrón de regex reconocía un artículo opcional ("el", "la", "los",
"las") seguido de espacios opcionales antes del nombre del producto. Como en una lista de
alternativas regex prueba las opciones en orden y "la" es literalmente el principio de
la palabra "las", el motor de regex encontraba "la" primero dentro de "las cuchillas",
y con los espacios siguientes marcados como opcionales (en vez de obligatorios), se
quedaba pegada la "s" sobrante al nombre del producto buscado.

**Cómo se arregló:** se revisan primero los patrones que sí llevan artículo, y se exige
al menos un espacio (no cero) inmediatamente después del artículo - así "la" nunca
alcanza a robarse solo el prefijo de "las".

**Archivo(s) cambiados:** `core/detectors/inventory_detector.py`

**Fecha aproximada:** 2026-07-14 (commit `2803853`, "Alertas predictivas de inventario
con dias estimados de agotamiento")

---

## 7. El punto de equilibrio ignoraba por completo los pagos fijos reales

**Qué pasaba:** al pedir el "punto de equilibrio del mes", el cálculo siempre sumaba
Q0 de pagos fijos (renta, luz, salarios), aunque esos pagos existieran y fueran una parte
importante de los costos reales del negocio - el resultado final quedaba subestimado.

**Por qué pasaba:** la tabla de pagos fijos (`PagoFijo`) solo se usaba como recordatorio
(nombre, día del mes, frecuencia) - nunca tuvo una columna para guardar el MONTO en
quetzales de cada pago. El código de punto de equilibrio literalmente tenía escrito
`total_pagos_fijos += 0  # No tenemos montos, solo recordatorios` - un comentario que
reconocía el hueco a propósito, a la espera de que se agregara esa columna.

**Cómo se arregló:** se agregó la columna `Monto` a la tabla `PagoFijo` (con una
migración `ALTER TABLE`), se hizo obligatorio capturarla al crear un pago fijo nuevo por
chat, y se corrigió el cálculo del punto de equilibrio para sumar el monto real en vez de
Q0. Los pagos fijos creados ANTES de este cambio quedan en Q0 hasta que alguien les fije
un monto manualmente con el comando "pago fijo renta es Q1500".

**Archivo(s) cambiados:** `tools/contabilidad_tool.py`, `database/nimbo_db.py`,
`core/nimbo.py`, `core/detectors/evento_detector.py`, `tools/evento_tool.py`

**Fecha aproximada:** 2026-07-14 (commit `7e70910`, "Flujo de caja proyectado con
ingresos, egresos y tendencia")

---

## 8. "Cotización para X" y otros comandos con la palabra "para" se rompían en silencio

**Qué pasaba:** comandos como "cotización **para** Juan Pérez", "genera orden **para**
Distribuidora Oster" o el nuevo "mejor hora **para** vender" a veces no se reconocían -
Nimbo respondía como si no hubiera entendido nada, sin ninguna pista de por qué.

**Por qué pasaba:** la palabra "para" no estaba en el vocabulario conocido del corrector
ortográfico, así que se autocorregía sola a "par" (la unidad de medida "par", muy
parecida en distancia de edición) ANTES de que cualquier detector viera el mensaje -
rompiendo en silencio cualquier comando que dependiera de la palabra "para" literal. Lo
mismo pasaba con "vendo", que se autocorregía a "vendió" y rompía "cuándo vendo más".

**Cómo se arregló:** se agregaron "para" y "vendo" al vocabulario conocido del corrector.

**Archivo(s) cambiados:** `core/command_normalizer.py`

**Fecha aproximada:** 2026-07-14 (commit `2d31f22`, "Deteccion de patrones de ventas con
predicciones y Gemini")

---

## 9. No existía forma de cancelar un flujo de conversación a mitad de camino

**Qué pasaba:** si un usuario estaba a mitad de un flujo de varios pasos (vendiendo un
producto, creando una cotización, abriendo caja) y escribía "cancelar" porque se
arrepintió o se equivocó, Nimbo interpretaba literalmente esa palabra como si fuera la
respuesta al paso actual - por ejemplo, si preguntaba "¿nombre del cliente?", escribir
"cancelar" registraba un cliente llamado "Cancelar".

**Por qué pasaba:** cada uno de los ~15 flujos conversacionales de Nimbo procesaba
cualquier texto que llegara como si fuera necesariamente el dato que estaba esperando, sin
ningún chequeo previo de "¿el usuario en realidad quiere salir de este flujo?".

**Cómo se arregló:** se agregó una salida universal centralizada: una lista de palabras
de cancelación ("cancelar", "cancela", "salir", "olvida", "stop", etc.) que se revisa UNA
sola vez, al principio de la función que procesa cualquier mensaje, antes de que ningún
flujo específico tenga oportunidad de interpretar el texto como su propio dato esperado.
Un ajuste posterior movió este chequeo todavía más arriba (antes de cargar el historial
de contexto) para que corriera lo antes posible dentro de la función.

**Archivo(s) cambiados:** `core/nimbo.py`

**Fecha aproximada:** 2026-07-14 (commits `21b8075` y `2518a47`, "Auditoria completa" y
su ajuste de orden)

---

## 10. El método de pago de una venta no se validaba - cualquier texto la cerraba

**Qué pasaba:** al preguntar "¿método de pago? (efectivo, tarjeta, transferencia, mixto,
crédito)", si el usuario escribía cualquier otra cosa - un typo, una pregunta sin
relación, un texto vacío - Nimbo cerraba la venta igual, guardando ese texto tal cual
como si fuera un método de pago válido.

**Por qué pasaba:** el paso `venta_waiting_pago` (en `core/nimbo.py`) solo tenía
condiciones para reconocer "mixto" y "crédito" como casos especiales; cualquier otro
texto caía directo al camino final que registra la venta, sin ningún chequeo de que ese
texto fuera realmente uno de los métodos de pago válidos.

**Cómo se arregló:** se agregó una validación explícita al principio del paso: si el
texto no es ninguno de los métodos reconocidos (efectivo, tarjeta, transferencia, mixto,
crédito), se le pide al usuario que lo escriba de nuevo, sin cerrar la venta.

**Archivo(s) cambiados:** `core/nimbo.py`

**Fecha aproximada:** 2026-07-14 (commit `21b8075`, "Auditoria completa")

---

## 11. Palabras comunes del español se corrompían por el corrector ortográfico

**Qué pasaba:** frases completamente normales que usaban palabras muy comunes como
"esta", "como" o "monto" podían salir corrompidas de forma silenciosa antes de llegar a
cualquier detector - por ejemplo, "esta" podía convertirse en "estufa", "como" en
"combo", y "monto" en "motor".

**Por qué pasaba:** el corrector ortográfico de Nimbo corrige errores de tipeo
comparando cada palabra del mensaje contra un vocabulario de palabras de negocio, usando
"qué tan parecidas se ven" las cadenas de texto (similitud de caracteres). Palabras
comunes del español que NO estaban en ese vocabulario de negocio quedaban a merced de esa
comparación, y si por casualidad se parecían mucho a una palabra de negocio, se
"corregían" a esa palabra aunque estuvieran perfectamente bien escritas.

**Cómo se arregló:** se agregaron esas palabras comunes ("esta", "esto", "eso", "como",
"disponible", entre otras) al vocabulario conocido, para que el corrector las reconozca
tal cual y no intente "arreglarlas". Además, se agregó una protección aparte: cualquier
palabra que empiece con mayúscula en el mensaje ORIGINAL (y no sea la primera palabra) se
trata como un probable nombre propio (de cliente, de proveedor) y se excluye por completo
del corrector, para que un nombre real no se corrompa por parecerse a una palabra de
negocio.

**Archivo(s) cambiados:** `core/command_normalizer.py`

**Fecha aproximada:** 2026-07-14 (commit `21b8075`, "Auditoria completa")

---

## 12. "Pedir a [proveedor] N producto a QN" nunca se ejecutaba

**Qué pasaba:** el comando estructurado "pedir a Distribuidora Oster 5 licuadoras a
Q200" (para crear una orden de compra con precio explícito) nunca llegaba a ejecutar esa
lógica específica - en su lugar, siempre se ejecutaba una lógica más genérica y menos
completa.

**Por qué pasaba:** dos problemas relacionados en `ProveedorDetector`: primero, el
patrón para este comando estructurado se revisaba DESPUÉS que un patrón mucho más
genérico ("pedir a X", sin exigir cantidad ni producto), así que ese patrón genérico
siempre lo interceptaba primero. Segundo, el patrón en sí tenía un error de mayúsculas:
buscaba una "Q" mayúscula justo antes del precio, pero el texto ya le llegaba en
minúsculas (todo el texto se normaliza a minúsculas antes de llegar a los detectores), así
que ese fragmento del patrón nunca podía coincidir con un precio real.

**Cómo se arregló:** se movió el patrón estructurado para que se revise ANTES que el
genérico, y se corrigió la "Q" mayúscula por minúscula. De paso, se completó la
implementación de la tool para que de verdad cree la orden de compra con el precio
indicado (antes solo devolvía un marcador que no se conectaba a nada).

**Archivo(s) cambiados:** `core/detectors/proveedor_detector.py`,
`tools/proveedor_tool.py`, `database/nimbo_db.py`

**Fecha aproximada:** 2026-07-14 (commit `21b8075`, "Auditoria completa")

> **Nota de verificación:** `CLAUDE.md` todavía lista esto como un pendiente abierto
> ("Pendiente #9") en su versión actual, pero al revisar el código de hoy
> (`tools/proveedor_tool.py` y `core/nimbo.py`) el marcador que genera esta tool
> (`ORDEN_COMPRA_PAGO_INICIO:`) sí está conectado y manejado - es posible que esa nota de
> `CLAUDE.md` haya quedado desactualizada después de esta corrección. Vale la pena
> confirmarlo con una prueba real antes de asumir cualquiera de las dos versiones.

---

## 13. Los comandos de caja y cuentas por cobrar/pagar no reconocían variantes conjugadas

**Qué pasaba:** comandos como "**abre** la caja" (en vez de "abrir caja"), "Juan
**deben**... " en plural, o "**pagamos**/**pagaron**/**abonaron**" no se reconocían,
aunque fueran formas perfectamente naturales de decir lo mismo que sus versiones ya
soportadas.

**Por qué pasaba:** los patrones de regex de varios detectores (`CajaDetector`,
`CuentaCobrarDetector`, `CuentaPagarDetector`) solo cubrían una forma verbal específica
(el infinitivo "abrir", la tercera persona singular "debe", etc.) y un artículo
obligatorio o inexistente, sin contemplar las conjugaciones y formas coloquiales más
comunes con las que un cajero real escribe.

**Cómo se arregló:** se ampliaron los patrones para aceptar más conjugaciones ("abre/
abrir", "cierra/cerrar", "anula/anular", "debe/deben", "pagó/pagamos/pagaron/abonaron") y
artículos opcionales ("la caja"/"caja", "el turno"/"turno").

**Archivo(s) cambiados:** `core/detectors/caja_detector.py`,
`core/detectors/cuenta_cobrar_detector.py`, `core/detectors/cuenta_pagar_detector.py`

**Fecha aproximada:** 2026-07-14 (commit `21b8075`, "Auditoria completa")

---

## 14. Detectores duplicados en inglés quedaban activos, generando ambigüedad

**Qué pasaba:** existían tres detectores completos (`CustomerDetector`, `BudgetDetector`,
`WindowsDetector`) activos en el pipeline de detección, con nombres e intents en inglés
que duplicaban o se superponían con funcionalidad ya existente en español (por ejemplo,
`CustomerDetector` duplicaba a `ClienteDetector`), y `"customer"` incluso estaba
permitido para el rol empleado.

**Por qué pasaba:** eran módulos escritos en una etapa anterior del proyecto, en inglés,
que nunca se terminaron de integrar de forma consistente con el resto del sistema (que
es completamente en español) y quedaban activos sin necesidad real.

**Cómo se arregló:** se desconectaron los tres detectores del pipeline de
`core/intent_detector.py` (dejaron de importarse ahí) y se quitó `"customer"` de las
categorías permitidas para el rol empleado. Los archivos de esos detectores y sus tools
correspondientes (`tools/customer_tool.py`, `tools/budget_tool.py`,
`tools/windows_tool.py`) se dejaron en el proyecto pero sin ninguna forma de alcanzarlos
desde un mensaje real del chat (código huérfano - ver `mapa_nimbo.html` para más detalle
de qué archivos quedaron en ese estado).

**Archivo(s) cambiados:** `core/intent_detector.py`, `core/action_engine.py`

**Fecha aproximada:** 2026-07-14 (commit `21b8075`, "Auditoria completa")

---

## 15. Un error de JavaScript bloqueaba abrir turno de caja y el popup de cobrador

**Qué pasaba:** en ciertas pantallas del dashboard, el botón de "Abrir turno" de Caja (y
el popup para identificar al cobrador antes de cerrar una venta) simplemente no
respondía al hacer clic - sin ningún mensaje de error visible para el usuario.

**Por qué pasaba:** en el `<script>` principal del dashboard había una línea que
llamaba, de forma incondicional y apenas se cargaba la página,
`renderPermisosGrid('usr-permisos-grid', ...)` - una función que dibuja la lista de
permisos en el panel "Usuarios". El problema es que ese elemento HTML
(`#usr-permisos-grid`) solo existe cuando el panel de Usuarios está en el DOM - en
cualquier otra pantalla, `document.getElementById(...)` devolvía `null`, y llamar a la
función sobre `null` lanzaba un error de JavaScript no capturado. Ese error detenía la
ejecución del resto del script en esa carga de página, incluyendo el código que
conectaba los botones de Caja con sus acciones.

**Cómo se arregló:** se agregó un chequeo (`if (document.getElementById('usr-permisos-
grid')) { ... }`) para que esa función solo se llame cuando el elemento de verdad existe
en la pantalla actual.

**Archivo(s) cambiados:** `templates/index.html`

**Fecha aproximada:** 2026-07-15 (commit `bc57c9a`, "Fix caja: error JavaScript
bloqueaba abrir turno y popup cobrador")

---

## 16. "Nuevo producto X precio N costo N" se registraba como un gasto

**Qué pasaba:** al crear un producto nuevo con el comando "nuevo producto Cuchilla Oster
precio 95 costo 28" (sin especificar stock al final), Nimbo lo registraba como un GASTO
de Q28 en vez de crear el producto.

**Por qué pasaba:** `ContabilidadDetector` tiene un patrón genérico para reconocer
gastos con la forma "cualquier cosa costo N" (pensado para frases como "la reparación
costó 200"), y ese detector se revisa ANTES que `InventoryDetector` en el orden de
detección. Como el comando de creación de producto, cuando no traía cantidad de stock al
final, terminaba literalmente en "... costo 28", el patrón genérico de gastos lo
interceptaba primero.

**Cómo se arregló:** se agregó una excepción (lookahead negativo) al patrón de gastos
para que ignore mensajes que empiecen con "agregar/agrega/nuevo/crear producto " - el
mismo tipo de corrección que ya se había aplicado antes para otras ambigüedades similares
entre detectores (ver bugs #2 y #4 arriba).

**Archivo(s) cambiados:** `core/detectors/contabilidad_detector.py`

**Fecha aproximada:** 2026-07-17 (commit `446c7be`, "Importacion masiva Excel/CSV y
flujo de productos desde chat")

---

## 17. El escaneo de código de barras mostraba "stock insuficiente" de forma incorrecta

**Qué pasaba:** al escanear un producto con el lector de código de barras, Nimbo
preguntaba "¿quieres vender este producto? (sí/no) o escribe la cantidad". Si el cajero,
en vez de responder, escaneaba OTRO producto (muy común escaneando varios artículos
seguidos), Nimbo respondía "Stock insuficiente" - un mensaje confuso y técnicamente
incorrecto, porque el problema real no era falta de stock.

**Por qué pasaba:** el lector de código de barras escribe el código como si fuera un
teclado, seguido de Enter - Nimbo no tiene forma de distinguir "esto es un código nuevo"
de "esto es la respuesta a la pregunta anterior" a menos que lo revise explícitamente. El
paso que esperaba la respuesta (`barcode_waiting_accion`) intentaba interpretar
CUALQUIER texto entrante como la cantidad a vender del producto ya escaneado - un código
de barras completo (13 dígitos) interpretado como "cantidad" es un número gigantesco, que
siempre es mayor al stock real disponible, así que siempre disparaba el aviso de stock
insuficiente.

**Cómo se arregló:** se agregó un chequeo al principio de ese paso (y del paso
equivalente para códigos no encontrados): si el mensaje que llega ES EN SÍ MISMO un
código de barras válido, se trata como el inicio de un escaneo nuevo en vez de intentar
interpretarlo como la respuesta pendiente.

**Archivo(s) cambiados:** `core/nimbo.py`, `core/detectors/inventory_detector.py`

**Fecha aproximada:** 2026-07-17 (commit `0fd2863`, "Fix escaneo codigo de barras -
mostraba stock insuficiente incorrectamente")

---

## 18. El lector de código de barras no siempre escribía en el campo correcto

**Qué pasaba:** si el cajero (o quien usara el chat) hacía clic en cualquier parte de la
pantalla que no fuera el campo de texto - por ejemplo, para leer una respuesta anterior -
y luego escaneaba un producto, el código escaneado no llegaba a ningún campo útil, porque
el lector escribe literalmente donde esté el foco del teclado en ese momento.

**Por qué pasaba:** un lector de código de barras USB/Bluetooth funciona exactamente
como un teclado: escribe los caracteres del código (y un Enter) en el elemento que tenga
el foco en ese momento, sin ninguna forma de "apuntar" a un campo específico por sí
mismo. Nada en la interfaz obligaba a que el campo correcto (el chat o el buscador de
Caja) mantuviera el foco todo el tiempo.

**Cómo se arregló:** se agregó una función (`refocusInputActivo()`) que devuelve el foco
automáticamente al campo correcto - al entrar al panel de Chat o Caja, después de mandar
un mensaje o agregar un producto al carrito, después de cerrar cualquier modal, y al
hacer clic en cualquier parte de la pantalla que no sea un botón, link o campo
interactivo (evitando robarle el foco a un modal abierto, como el de contraseña de
identificación de cobro).

**Archivo(s) cambiados:** `templates/index.html`

**Fecha aproximada:** 2026-07-17 (commit `7372d3b`, "Auto-focus permanente en chat y
caja para lector de codigo de barras")

---

## 19. Ollama: tiempo de espera muy corto y mensaje de error engañoso

**Qué pasaba:** con mensajes o análisis largos, Nimbo con frecuencia mostraba el mismo
aviso de "no se pudo generar la respuesta" tanto cuando Ollama estaba realmente caído
como cuando Ollama SÍ estaba corriendo pero simplemente estaba tardando más de la
cuenta - confundiendo más de un chequeo manual de "¿está Ollama corriendo o no?".
Además, la función que llamaba a Ollama podía lanzar una excepción sin capturar,
arriesgando tumbar el flujo que la llamó.

**Por qué pasaba:** el tiempo de espera máximo (timeout) estaba fijo en 120 segundos
para todo, tanto para el chat rápido como para los análisis financieros largos - muy
corto para este hardware (CPU sin GPU, sin aceleración gráfica) con prompts largos. Y no
existía ninguna forma de diferenciar, en el mensaje de respuesta, "Ollama no está
corriendo" (error de conexión) de "Ollama está corriendo pero tardó demasiado" (error de
timeout) - ambos casos cazan como el mismo texto genérico.

**Cómo se arregló:** se subieron los tiempos de espera a 180 segundos (chat/traducción)
y 300 segundos (análisis largos), se envolvió la llamada en un manejo de errores que
nunca deja que la excepción se propague, y se agregó un mensaje distinto
(`MENSAJE_TIMEOUT`, "Ollama está procesando, esto puede tardar un momento...") que se
devuelve específicamente cuando la causa fue timeout, distinto de cuando Ollama
simplemente no responde. De paso, se eliminó el segundo modelo (`gemma2:9b`) que se usaba
aparte para análisis largos, dejando un solo modelo (`qwen2.5:7b`) para todo - alternar
entre dos modelos distintos causaba una "penalidad de recarga" en Ollama que por sí sola
podía agotar el tiempo de espera completo (ver decisión #3 de `DECISIONS.md`).

**Archivo(s) cambiados:** `services/ollama_service.py`

**Fecha aproximada:** 2026-07-17 (commit `73f406b`, "Ollama: timeouts 180s/300s y
mensaje de timeout claro")

---

## Limpieza de código huérfano (2026-07-18)

Se identificaron 19 archivos huérfanos durante la construcción de `mapa_nimbo.html`
(ver ese archivo y `DECISIONS.md`): código que existe, se carga o se registra al
arrancar el servidor, pero al que ningún mensaje real del chat puede llegar porque su
detector nunca se importó en `core/intent_detector.py` (o, en el caso de los servicios
de soporte, porque solo los usaban las tools ya huérfanas). Antes de borrar nada se
verificó, con un análisis de imports basado en `ast` de Python (no solo `grep`), que
NINGUNO de los 19 archivos tiene un importador fuera de ese mismo grupo.

**Archivos eliminados y por qué no se usaban:**

- `tools/budget_tool.py` / `core/detectors/budget_detector.py` - un detector de
  "presupuestos" (`BudgetDetector`) que nunca se importó en `core/intent_detector.py`
  (se desconectó del pipeline en el commit `21b8075`, "Auditoria completa" - ver bug
  #14 más arriba en este documento). Sin ese detector, `budget.create` nunca se
  dispara desde el chat.
- `tools/customer_tool.py` / `core/detectors/customer_detector.py` - versión en
  inglés de `cliente_tool.py`/`cliente_detector.py`, duplicaba funcionalidad ya
  existente en español. Tampoco estaba importado en `core/intent_detector.py`.
- `tools/windows_tool.py` / `core/detectors/windows_detector.py` - abría programas de
  Windows (bloc de notas, etc.) vía `subprocess`. Sin relación con el negocio de
  Nimbo y, de nuevo, sin detector conectado.
- `services/budget_service.py` - CRUD de presupuestos sobre `nimbo.db`, usado
  únicamente por `tools/budget_tool.py` (ya huérfano).
- `services/customer_service.py` - CRUD de clientes en una tabla/ruta paralela,
  usado únicamente por `tools/customer_tool.py` y `tools/budget_tool.py` (ambos
  huérfanos).
- `core/event_bus.py` - un event bus pub/sub simple, sin ningún suscriptor real; su
  único uso era `tools/budget_tool.py`.
- `core/workspace.py` - un diccionario en memoria (set/get); su único uso también
  era `tools/budget_tool.py`.
- `core/reasoning_engine.py` - el propio docstring del archivo decía "por ahora este
  motor solo delega la ejecución" - un placeholder para un razonamiento futuro que
  nunca se conectó a `core/action_engine.py` ni a `core/nimbo.py`.
- `core/confirmations.py` - un `ConfirmationManager` para crear confirmaciones
  pendientes con uuid, sin ningún caller en el pipeline real del chat.
- `tools/sales_tool.py`, `services/sales.py` - archivos completamente vacíos (0
  líneas), el inicio nunca terminado de una tercera versión (en inglés) del módulo
  de ventas.
- `tools/invoice_tool.py`, `services/invoices.py` - archivos completamente vacíos,
  el inicio nunca terminado de un módulo de facturación en inglés.
- `services/customers.py` - archivo completamente vacío.
- `core/audit.py`, `core/permissions.py` - archivos completamente vacíos,
  reservados aparentemente para un futuro sistema de auditoría/permisos que nunca
  se escribió (el control de permisos real vive en `core/action_engine.py`,
  `CATEGORIAS_POR_ROL`).

**Cómo se verificó antes de borrar:** se corrió un análisis con el módulo `ast` de
Python sobre los 87 archivos `.py` del proyecto, resolviendo cada `import`/`from ...
import` a su archivo real, y se confirmó que ninguno de los 19 archivos tenía un
importador FUERA del propio grupo a eliminar (sí había imports ENTRE ellos - por
ejemplo `tools/budget_tool.py` importaba `core/event_bus.py` y `core/workspace.py` -
pero como los dos lados de esa relación estaban en la lista de borrado, no queda
ninguna referencia rota). Se usó `git rm` (no borrado directo del disco) para
conservar el historial de esos archivos en git por si hace falta consultarlos más
adelante.

**Verificación después de borrar:** `python3 -m py_compile` sobre todos los `.py`
del proyecto sin errores; se importaron `app.py`, `core.nimbo`, `core.action_engine`
y el paquete `tools` completo en un proceso de Python real - todo cargó sin
excepciones. El registro de tools activas bajó de 155 a 146 funciones (las que
registraba `tools/budget_tool.py`), y el número de detectores activos en
`ActionEngine` se mantuvo en 21 (los 3 detectores huérfanos ya no contaban desde
antes, porque nunca estuvieron en esa lista). La base de datos real (`nimbo.db`) se
revisó después y sigue intacta (mismos usuarios y productos que antes de la
limpieza).

---

## Prueba del wizard de registro de nueva empresa (2026-07-18)

**Cómo se probó:** se copió el proyecto completo a una carpeta aislada (fuera de
`/home/victor/nimbo.exe`, en un directorio temporal), excluyendo `.git`,
`__pycache__`, `.env` y el `nimbo.db` real - para que la copia arrancara como una
instalación totalmente nueva, sin usuarios ni configuración. Se usó
`app.test_client()` de Flask (sin necesidad de un navegador real) para simular a
alguien llenando el wizard de `/setup`, paso por paso, con datos de una empresa de
prueba ("Ferretería La Prueba").

**Qué se verificó** (cada paso a través de `app.test_client()`, confirmando después
directo en la `nimbo.db` de la copia con `sqlite3`):
- Que una instalación nueva (sin `nimbo.db`) redirige automáticamente a `/setup/1`.
- Los 7 pasos completos: datos del negocio, cuenta admin, configuración financiera
  (IVA/POS/ISR), horario, fondo de caja, primer empleado, y resumen final.
- Que `Configuracion` queda con todos los valores esperados, incluyendo los
  derivados (ej. `iva_porcentaje=12` a partir de `cobra_iva=si`) y el efecto
  secundario de que el fondo de caja del paso 5 también se guarda como
  `caja_fondo_sugerido`.
- Que se crea exactamente 1 usuario con rol `admin`, con sus datos correctos
  (username, nombre, activo).
- Que se crea el primer empleado con su teléfono.
- Que `onboarding_completado` queda en `"1"` al terminar el paso 7.
- Que el admin recién creado puede iniciar sesión de verdad (`/login`) y llegar al
  dashboard (`GET /` responde 200, sin redirigir a `/setup` ni a `/login`).
- Que un login con la contraseña equivocada se rechaza con el mensaje de error
  esperado, sin dejar entrar.

**Casos borde probados aparte** (en una segunda copia aislada, para no mezclar con
la prueba principal):
- Paso 1 sin los campos obligatorios (nombre/tipo/país): no avanza, muestra el error.
- Intentar saltar directo a `/setup/3` sin haber completado el paso 1: rebota al
  paso actual en vez de dejar avanzar.
- Paso 2 con una contraseña de menos de 6 caracteres: no avanza, muestra el error, y
  NO deja ningún usuario a medio crear en la base de datos.
- Reenviar el paso 2 después de que el admin ya se creó (ej. si alguien le da
  "atrás" en el navegador y reenvía el formulario): avanza sin error y sin crear un
  segundo admin.
- Los botones "saltar" de los pasos 5 (fondo de caja) y 6 (primer empleado): avanzan
  correctamente sin guardar ni crear nada de ese paso.
- Con el onboarding ya completo, visitar `/setup/1` de nuevo redirige a `/login` en
  vez de dejar reabrir el wizard.

**Resultado:** las 24 verificaciones (10 del flujo principal + 6 de datos guardados
+ 8 de casos borde) pasaron. **No se encontró ningún bug en el wizard de registro** -
el flujo de onboarding, tanto en su camino feliz como en los casos borde probados,
guarda correctamente el usuario admin y toda la configuración del negocio, y protege
correctamente contra reenvíos duplicados, contraseñas cortas, campos faltantes y
saltos de paso.

**Archivos involucrados en la prueba (sin cambios, solo verificados):** `app.py`
(rutas `/setup`, `/setup/<paso>`, `/login`), `core/auth.py` (`crear_usuario`,
`existe_admin`, `verify_login`), `core/configuracion.py`
(`set_config`/`get_config`).

---

## Nota sobre esta reconstrucción

Esta lista se armó revisando los commits de git uno por uno (`git log`, `git show`) y
cruzándolos con las notas de auditoría que ya existían en `CLAUDE.md`. Los bugs #1 a #8
y #16 a #19 se identificaron por su mensaje de commit explícito ("Fix ...") o por una
nota de "bug preexistente" dejada en `CLAUDE.md`; los bugs #9 a #14 vienen todos del
mismo commit de auditoría (`21b8075`, "Auditoria completa: fixes command normalizer,
cancelacion universal, conflictos detectores") que agrupó varias correcciones
relacionadas en una sola sesión de trabajo, por eso comparten fecha y se listan por
separado según el problema técnico real que resolvió cada una.
