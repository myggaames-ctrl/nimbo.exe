# Glosario técnico de Nimbo (para quien nunca ha programado)

Este glosario explica, en español simple, los términos técnicos que aparecen en el
código de Nimbo. Para cada uno: **qué es**, **para qué sirve en Nimbo** (con un ejemplo
real del proyecto) y un **ejemplo de la vida real** para que la idea se quede pegada.

Están ordenados en el mismo orden en que se pidieron, agrupados libremente por tema
para que los relacionados queden cerca.

---

### regex (expresión regular)
**Qué es:** una forma de escribir un "patrón de texto" para que la computadora reconozca
frases que tienen una cierta forma, aunque no sean exactamente iguales letra por letra.

**Para qué sirve en Nimbo:** todos los `core/detectors/*.py` usan regex para reconocer
comandos como "vendí 2 licuadoras" sin tener que escribir a mano cada frase posible que
un usuario podría escribir.

**Ejemplo de la vida real:** es como decirle a alguien "si el recibo empieza con 'FAC-'
seguido de números, es una factura" - no necesitas memorizar cada número de factura
posible, solo la FORMA que tienen todas.

---

### import
**Qué es:** una instrucción que trae código escrito en OTRO archivo para poder usarlo en
el archivo actual, sin tener que copiarlo y pegarlo.

**Para qué sirve en Nimbo:** por ejemplo, `tools/venta_tool.py` empieza con
`from database.nimbo_db import get_products, remove_stock, ...` - así la tool de ventas
puede usar funciones que en realidad viven en otro archivo (`database/nimbo_db.py`).

**Ejemplo de la vida real:** es como pedir prestada una herramienta del vecino en vez de
comprar una copia para cada casa de la cuadra - la herramienta vive en un solo lugar y
cualquiera que la necesite "la importa" quien la tiene.

---

### función
**Qué es:** un bloque de código con un nombre, que recibe algunos datos, hace algo con
ellos, y devuelve un resultado. Se puede llamar (usar) tantas veces como haga falta.

**Para qué sirve en Nimbo:** `remove_stock(producto_id, cantidad, razon="Venta")` en
`database/nimbo_db.py` es una función: recibe qué producto y cuánta cantidad descontar,
y se encarga de restarlo del inventario. Se llama desde `tools/venta_tool.py`, desde el
escaneo de código de barras, desde Caja... siempre la misma función, sin reescribir esa
lógica en cada lugar.

**Ejemplo de la vida real:** es como una receta de cocina: le das los ingredientes
(datos de entrada) y siempre que la sigas obtienes el mismo plato (resultado) - y la
puedes cocinar las veces que quieras sin tener que reinventarla cada vez.

---

### variable
**Qué es:** un nombre que guarda un valor (un número, un texto, una lista de cosas) para
poder usarlo más adelante en el código.

**Para qué sirve en Nimbo:** `BASE_DIR` (en `database/nimbo_db.py`, `app.py`, etc.) guarda
la ruta de la carpeta del proyecto; `total_final` (en el flujo de venta de
`core/nimbo.py`) guarda cuánto tiene que pagar el cliente después de descuentos.

**Ejemplo de la vida real:** es como una etiqueta pegada a una caja: la caja puede
cambiar de contenido con el tiempo, pero mientras tenga la etiqueta "Total a pagar" vas
a saber qué buscar ahí adentro.

---

### base de datos
**Qué es:** un archivo (o sistema) organizado para guardar información de forma
permanente, para poder buscarla, actualizarla y relacionarla después.

**Para qué sirve en Nimbo:** Nimbo usa DOS bases de datos SQLite: `nimbo.db` (la propia,
con productos, ventas, clientes, cotizaciones, etc.) y `pos.db` (la de Aronium, el
programa de punto de venta de terceros, que hoy solo se usa para reportes de ventas de
caja física y el catálogo nativo de clientes).

**Ejemplo de la vida real:** es como el archivero de una tienda donde se guardan todas
las facturas, las fichas de clientes y el inventario - organizado en carpetas (tablas)
para poder encontrar cualquier cosa rápido.

---

### tabla
**Qué es:** dentro de una base de datos, una tabla es como una hoja de cálculo: tiene
columnas (los tipos de dato que guarda) y filas (cada registro individual).

**Para qué sirve en Nimbo:** la tabla `Venta` tiene columnas como `ClienteId`, `Total`,
`MetodoPago`, `Fecha`; cada fila es una venta real que se registró. La tabla `Producto`
tiene una fila por cada artículo del inventario.

**Ejemplo de la vida real:** es como una hoja de Excel donde cada columna es un dato
("Nombre", "Precio", "Stock") y cada fila es un producto distinto.

---

### endpoint
**Qué es:** una dirección específica del servidor a la que se le puede pedir (o mandar)
información, generalmente usada por el código (JavaScript, otra app) en vez de por una
persona navegando con el mouse.

**Para qué sirve en Nimbo:** `/api/status` es un endpoint que responde si Ollama y la
base de datos están conectados; `/api/caja/cobrar` es el endpoint que el dashboard llama
cuando el cajero aprieta "Cobrar".

**Ejemplo de la vida real:** es como el número de extensión de un departamento
específico dentro de una empresa - marcas ese número exacto para hablar con "cobros",
no con toda la empresa a la vez.

---

### ruta (route)
**Qué es:** en Flask, la definición de qué función se ejecuta cuando alguien visita una
URL específica.

**Para qué sirve en Nimbo:** en `app.py`, `@app.route("/pos")` seguido de
`def pos(): return render_template("pos.html")` define que visitar `/pos` en el
navegador muestra la pantalla de punto de venta.

**Ejemplo de la vida real:** es como el directorio de un edificio: "piso 3 = Recursos
Humanos" - la "ruta" te dice a qué piso (función) llegas según qué botón (URL) apretaste
en el elevador.

---

### frontend
**Qué es:** la parte de una aplicación que el usuario VE y con la que interactúa
directamente: pantallas, botones, formularios.

**Para qué sirve en Nimbo:** `templates/index.html` (el dashboard completo: chat,
inventario, caja, servicio técnico) es el frontend - todo lo que corre en el navegador
del usuario.

**Ejemplo de la vida real:** es como el mostrador y la vitrina de una tienda: lo que el
cliente ve y toca, aunque la bodega (backend) esté detrás, fuera de su vista.

---

### backend
**Qué es:** la parte de una aplicación que corre en el servidor, fuera de la vista del
usuario: la lógica de negocio, el acceso a la base de datos, las reglas.

**Para qué sirve en Nimbo:** `app.py`, todo `core/`, `tools/`, `services/` y
`database/nimbo_db.py` son el backend - deciden qué pasa cuando el usuario aprieta un
botón o escribe un mensaje, sin que el usuario vea ese código directamente.

**Ejemplo de la vida real:** es la bodega y la caja registradora por dentro: el cliente
no ve cómo se calculó su cambio o se descontó el stock, solo ve el resultado en el
mostrador.

---

### template
**Qué es:** un archivo HTML con "huecos" que se rellenan con datos reales al momento de
mostrarlo (por ejemplo, el nombre del negocio, la lista de productos).

**Para qué sirve en Nimbo:** `templates/index.html`, `templates/login.html`,
`templates/setup.html`, etc. Flask usa `render_template("login.html")` para tomar ese
archivo, rellenar lo que haga falta, y mandarlo al navegador ya armado. No confundir con
el "template de importación (Excel)" (ver ese término más abajo) - son dos cosas
distintas que en este proyecto comparten la misma palabra.

**Ejemplo de la vida real:** es como una plantilla de carta con espacios en blanco
("Estimado ____") que se llenan con el nombre de cada destinatario antes de imprimirla.

---

### HTML
**Qué es:** el lenguaje que describe la ESTRUCTURA de una página web: qué es un título,
qué es un botón, qué es una tabla.

**Para qué sirve en Nimbo:** todos los archivos en `templates/*.html` están escritos en
HTML - por ejemplo las tarjetas del dashboard, los formularios de login y del wizard de
`/setup`.

**Ejemplo de la vida real:** es como el esqueleto de un edificio: define dónde va cada
cuarto (encabezado, contenido, pie de página) antes de pintar las paredes (ese "pintado"
lo hace CSS, que no está en esta lista pero suele ir junto a HTML).

---

### JSON
**Qué es:** un formato de texto muy simple para representar datos organizados (números,
texto, listas, y pares "clave: valor"), fácil de leer tanto para una persona como para
una computadora.

**Para qué sirve en Nimbo:** cuando el dashboard le pide a `/api/status` cómo está el
sistema, la respuesta es JSON: `{"gemini": false, "aronium": true, "time": "18/07/2026
14:32"}` - `jsonify()` en `app.py` convierte un diccionario de Python a este formato.

**Ejemplo de la vida real:** es como una ficha de datos llenada con etiquetas claras:
"Nombre: Juan", "Edad: 30" - cualquiera que lea la ficha sabe exactamente qué dato es
cuál, sin adivinar.

---

### API (Interfaz de Programación de Aplicaciones)
**Qué es:** un conjunto de "puertas" que un programa expone para que OTRO programa (no
una persona) pueda pedirle cosas o mandarle información.

**Para qué sirve en Nimbo:** Nimbo tanto EXPONE una API (todas las rutas `/api/*` de
`app.py`, que el frontend consume) como CONSUME varias APIs externas: la de Ollama
(`http://localhost:11434`), la de WhatsApp Business, la de Facebook/Instagram.

**Ejemplo de la vida real:** es como el menú de un restaurante para pedidos por
teléfono: no entras a la cocina tú mismo, pides "quiero el platillo 4" y la cocina (el
otro programa) sabe exactamente qué preparar y te lo devuelve.

---

### token
**Qué es:** una pieza de texto (generalmente larga y aleatoria) que sirve como
"credencial" temporal o permanente para probar que alguien tiene permiso de hacer algo,
sin tener que mandar su contraseña real cada vez.

**Para qué sirve en Nimbo:** la tabla `PasswordResetToken` (en `core/auth.py`) genera un
token único cuando alguien pide recuperar su contraseña, válido por 1 hora, que se manda
por correo en el link de `/reset-password?token=...`. También `WA_TOKEN` y
`FB_PAGE_TOKEN` (variables de entorno) son tokens que autentican a Nimbo frente a las
APIs de WhatsApp y Facebook.

**Ejemplo de la vida real:** es como un boleto de un solo uso para el baño de un
restaurante: te lo dan en la caja, lo usas una vez, y no sirve después de usado o de que
pase el tiempo.

---

### hash
**Qué es:** una operación matemática que convierte cualquier texto en una cadena de
caracteres de longitud fija, de forma que sea prácticamente imposible "deshacer" la
operación para recuperar el texto original - pero siempre da el MISMO resultado para el
mismo texto de entrada.

**Para qué sirve en Nimbo:** `core/auth.py` nunca guarda la contraseña real de un
usuario - guarda su hash (`generate_password_hash(password)`, de la librería werkzeug) en
la columna `PasswordHash`. Al iniciar sesión, se compara el hash de lo que escribiste
(`check_password_hash(...)`) contra el guardado, sin que Nimbo (ni nadie con acceso a la
base de datos) sepa nunca la contraseña real.

**Ejemplo de la vida real:** es como una licuadora de un solo sentido: puedes meter una
fruta y sacar jugo (el hash), pero no hay forma de meter el jugo y sacar la fruta
original de vuelta. Aun así, si dos personas meten la MISMA fruta, sacan el MISMO jugo -
por eso sirve para comparar sin guardar el original.

---

### encriptación
**Qué es:** convertir información en un formato ilegible para quien no tenga la "llave"
correcta - a diferencia del hash, la encriptación SÍ se puede deshacer (desencriptar) si
tienes esa llave.

**Para qué sirve en Nimbo:** Nimbo hoy corre en la red local de la tienda (WSL2), sin
HTTPS propio configurado en `app.run()` - por eso la contraseña, aunque nunca se guarda
en texto plano (ver **hash** arriba), viaja del navegador al servidor sin encriptar
dentro de esa red local. Es una diferencia importante para tener en cuenta si Nimbo se
expusiera fuera de la red local (ver Pendiente #4 de `CLAUDE.md`, "Nimbo accesible desde
el teléfono").

**Ejemplo de la vida real:** el hash es como la licuadora de un solo sentido de arriba;
la encriptación es como una caja fuerte con llave: cualquiera puede meter algo adentro y
cerrarla, pero solo quien tiene la llave correcta puede abrirla y sacar lo mismo que se
guardó.

---

### timeout
**Qué es:** el tiempo máximo que un programa espera una respuesta antes de darse por
vencido y seguir con otra cosa, en vez de quedarse esperando para siempre.

**Para qué sirve en Nimbo:** `services/ollama_service.py` define
`TIMEOUT_SEGUNDOS = 180` (para chat/traducción) y `TIMEOUT_ANALISIS_SEGUNDOS = 300` (para
análisis largos) - si Ollama no responde en ese tiempo, Nimbo deja de esperar y muestra
`MENSAJE_TIMEOUT` ("Ollama está procesando, esto puede tardar un momento...") en vez de
congelar el chat indefinidamente.

**Ejemplo de la vida real:** es como decidir de antemano "si el mesero no viene en 10
minutos, voy yo a la caja a pedir" - un límite de paciencia para no quedarte esperando
para siempre.

---

### deploy (despliegue)
**Qué es:** el proceso de poner una aplicación a correr en el lugar donde de verdad va a
ser usada (un servidor, la nube, o en este caso, la PC de la tienda), a diferencia de
tenerla solo en la computadora de quien la programó.

**Para qué sirve en Nimbo:** Nimbo no tiene un proceso de deploy hacia la nube - "se
despliega" arrancando el servidor Flask directamente en la PC de la tienda
(`app.run(debug=True, port=5000)` al final de `app.py`), como describe la sección
"Arranque diario" de `CLAUDE.md`.

**Ejemplo de la vida real:** es la diferencia entre ensayar una obra de teatro en la sala
de tu casa y de verdad montarla en el teatro con público real - "deployar" es "ya está
funcionando donde la gente de verdad lo va a usar".

---

### debug (depuración)
**Qué es:** el proceso de encontrar y corregir errores en el código, generalmente
revisando paso a paso qué está pasando en vez de adivinar.

**Para qué sirve en Nimbo:** `app.run(debug=True, port=5000)` activa el modo debug de
Flask, que reinicia el servidor solo cuando detecta un cambio en el código y muestra
errores detallados en el navegador. `core/action_engine.py` también tiene un
`print("INTENT:", result)` que ayuda a ver, en la terminal, qué intent se detectó para
cada mensaje - una forma simple de "depurar" el chat mientras se prueba.

**Ejemplo de la vida real:** es como cuando un electricista prueba cable por cable con un
multímetro para encontrar dónde está el corto circuito, en vez de cambiar toda la
instalación a ciegas.

---

### commit
**Qué es:** un "punto de guardado" en git (el sistema de control de versiones) que
registra un conjunto de cambios en el código, con un mensaje que explica qué se hizo.

**Para qué sirve en Nimbo:** cada funcionalidad de Nimbo quedó registrada como uno o más
commits - por ejemplo `0fd2863 Fix escaneo codigo de barras - mostraba stock
insuficiente incorrectamente` es el commit que corrigió ese bug específico (ver
`BUGS_Y_FIXES.md`).

**Ejemplo de la vida real:** es como guardar una foto del progreso de una obra de
construcción cada semana, con una nota de qué se avanzó - si algo sale mal más adelante,
puedes volver a ver exactamente cómo se veía en cualquier semana anterior.

---

### push
**Qué es:** subir los commits que tienes guardados localmente en tu computadora hacia un
repositorio remoto (por ejemplo, GitHub), para que queden respaldados o que otros los
vean.

**Para qué sirve en Nimbo:** el proyecto tiene configurado un remoto en GitHub
(`git@github.com:myggaames-ctrl/nimbo.exe.git`) - hacer `git push` manda los commits
locales hacia allá.

**Ejemplo de la vida real:** es como subir las fotos de tu cámara a una nube compartida:
las fotos ya existían en tu cámara (tus commits locales), "push" es el acto de subirlas
para que también estén en un lugar central.

---

### pull
**Qué es:** lo opuesto a push: bajar a tu computadora los commits que otra persona (o tú
mismo desde otra máquina) ya subió al repositorio remoto.

**Para qué sirve en Nimbo:** si Nimbo se instalara en otra PC (ver decisión #6 de
`DECISIONS.md`, sobre rutas relativas), un `git pull` traería ahí todos los cambios ya
guardados en GitHub.

**Ejemplo de la vida real:** siguiendo el ejemplo de las fotos en la nube: "pull" es
bajar a tu celular las fotos que alguien más ya subió, para tener la misma colección
actualizada en tu propio dispositivo.

---

### módulo
**Qué es:** un archivo de código (generalmente `.py`) que agrupa funciones y datos
relacionados, para poder importarlo desde otros archivos.

**Para qué sirve en Nimbo:** `tools/venta_tool.py` es un módulo completo dedicado solo a
las herramientas de venta; `database/nimbo_db.py` es el módulo con todo el acceso a
datos.

**Ejemplo de la vida real:** es como un capítulo de un libro de recetas dedicado
solamente a postres - un grupo de contenido relacionado, separado del capítulo de
entradas o platos fuertes, pero parte del mismo libro.

---

### clase
**Qué es:** un molde para crear objetos que agrupan datos y funciones relacionadas
(llamadas "métodos" cuando pertenecen a una clase).

**Para qué sirve en Nimbo:** `class VentaDetector:` (en
`core/detectors/venta_detector.py`) agrupa los patrones de regex de ventas y el método
`detect()` que los usa; `class ActionEngine:` agrupa la lógica de orquestación completa
del chat.

**Ejemplo de la vida real:** es como el molde de un cortador de galletas: el molde
(clase) define la forma, y cada galleta que sale de él (objeto/instancia) tiene esa
misma forma, aunque sea una galleta distinta de las demás.

---

### loop (bucle)
**Qué es:** una instrucción que repite un bloque de código varias veces, generalmente
una vez por cada elemento de una lista.

**Para qué sirve en Nimbo:** `core/intent_detector.py` tiene
`for detector in self.detectors:` - un loop que prueba, uno por uno, cada uno de los ~20
detectores hasta que alguno reconozca el mensaje.

**Ejemplo de la vida real:** es como revisar uno por uno los casilleros de un edificio
buscando el que tiene tu nombre - repites la misma acción ("revisar este casillero") por
cada casillero, hasta encontrar el correcto o terminar la fila.

---

### condicional
**Qué es:** una instrucción que hace que el código tome un camino distinto según si algo
es verdadero o falso.

**Para qué sirve en Nimbo:** `if p["Stock"] < cantidad:` (en `tools/venta_tool.py`)
decide si hay que rechazar la venta por falta de stock o seguir adelante - el camino que
toma el código depende de ese resultado.

**Ejemplo de la vida real:** es como una señal de tránsito con dos caminos: "si el
semáforo está en rojo, detente; si no, sigue" - la decisión depende de una condición que
puede cambiar.

---

### if/else
**Qué es:** la forma más común de escribir un condicional: "si (if) se cumple esto, haz
A; si no (else), haz B".

**Para qué sirve en Nimbo:** en el flujo de venta (`core/nimbo.py`,
`venta_waiting_nombre`),
`if msg in ["sin nombre", "sin cliente", ...]: ... else: (buscar el cliente)` decide si
la venta es a "Consumidor Final" o a un cliente identificado por nombre.

**Ejemplo de la vida real:** "si llueve, llevo paraguas; si no, no lo llevo" - una sola
decisión con exactamente dos caminos posibles.

---

### string (cadena de texto)
**Qué es:** un tipo de dato que representa texto: letras, números como texto, símbolos,
espacios.

**Para qué sirve en Nimbo:** el mensaje que un usuario escribe en el chat
(`message: str` en `core/nimbo.py`) es un string - "vendí 2 licuadoras" es una cadena de
caracteres, no un número que se pueda sumar directamente.

**Ejemplo de la vida real:** es como una frase escrita en un papel: se puede leer,
recortar en pedazos, o pegar con otra frase, pero no se puede "sumar" con otro papel
como si fueran números.

---

### integer (entero)
**Qué es:** un tipo de dato que representa un número sin decimales (positivo, negativo o
cero).

**Para qué sirve en Nimbo:** `cantidad = int(match.group(1))` (en los detectores de
venta) convierte el texto "2" (que llegó como string desde el regex) a el número entero
`2`, para poder multiplicarlo por el precio.

**Ejemplo de la vida real:** es la diferencia entre escribir "dos" en una carta (texto) y
tener de verdad 2 monedas en la mano (un número con el que puedes hacer cuentas).

---

### boolean
**Qué es:** un tipo de dato que solo puede valer una de dos cosas: verdadero (`True`) o
falso (`False`).

**Para qué sirve en Nimbo:** `_es_cancelacion(message) -> bool` (en `core/nimbo.py`)
responde exactamente eso: ¿es este mensaje una cancelación? Sí o no, sin términos medios.
La columna `Activo` de la tabla `Producto` también es, en esencia, un booleano (1 o 0).

**Ejemplo de la vida real:** es como un interruptor de luz: solo puede estar encendido o
apagado, no hay una posición "a medias" que cuente como una tercera opción.

---

### array (lista, en Python)
**Qué es:** una colección ordenada de varios valores, guardados bajo un solo nombre, a
los que se puede acceder por posición.

**Para qué sirve en Nimbo:** `_PALABRAS_CANCELACION = ["cancelar", "cancela", "salir",
"olvida", "olvidalo", "mejor no", "stop"]` (en `core/nimbo.py`) es una lista de todas las
palabras que cuentan como cancelación - se recorre con un loop para revisar si el
mensaje coincide con alguna.

**Ejemplo de la vida real:** es como una lista de compras escrita en un papel: los
artículos están en un orden, y puedes decir "el segundo de la lista" para referirte a
uno específico.

---

### objeto
**Qué es:** una "cosa" en el código que agrupa datos relacionados bajo un solo nombre -
puede ser una instancia de una clase, o (en JSON/Python) un diccionario de pares
clave-valor.

**Para qué sirve en Nimbo:** el `context` que viaja de mensaje en mensaje en
`core/nimbo.py` es un objeto tipo diccionario: `{"step": "venta_waiting_pago",
"venta_ctx": {...}, "venta_cliente_id": 5}` - agrupa todo lo que Nimbo necesita recordar
sobre esa conversación en un solo lugar.

**Ejemplo de la vida real:** es como una carpeta con el expediente de un cliente: adentro
hay varios documentos (nombre, teléfono, historial), pero se maneja como una sola unidad
("el expediente de Juan Pérez") en vez de papeles sueltos.

---

### servidor
**Qué es:** un programa (corriendo en una computadora) que espera peticiones de otros
programas o de navegadores, y les responde.

**Para qué sirve en Nimbo:** el servidor Flask de Nimbo corre en el puerto 5000 y atiende
el navegador del dashboard; el servidor de Ollama corre en el puerto 11434 y atiende las
peticiones de IA que le manda `services/ollama_service.py`.

**Ejemplo de la vida real:** es como el mesero de un restaurante: se queda esperando que
alguien pida algo, y cuando alguien pide, va, lo prepara (o lo manda a preparar) y trae
la respuesta.

---

### puerto
**Qué es:** un número que identifica, dentro de una misma computadora, A CUÁL programa
va dirigida una petición de red (una misma PC puede tener varios servidores corriendo a
la vez, cada uno "escuchando" en su propio puerto).

**Para qué sirve en Nimbo:** Flask usa el puerto 5000 (`app.run(..., port=5000)`), Ollama
el puerto 11434 (`http://localhost:11434`), y OpenClaw el puerto 18789 - tres programas
distintos, corriendo en la misma PC, cada uno en su propia "puerta numerada".

**Ejemplo de la vida real:** es como los números de departamento en un edificio: la
dirección del edificio (la IP) es la misma para todos, pero el número de depa (puerto)
te dice exactamente a cuál tocar.

---

### cookie
**Qué es:** un pequeño dato que el servidor le pide al navegador que guarde, y que el
navegador vuelve a mandar en cada petición siguiente - sirve para que el servidor
"recuerde" algo del usuario entre una visita y otra.

**Para qué sirve en Nimbo:** Flask-Login (usado en `core/auth.py`) guarda una cookie de
sesión en el navegador cuando alguien inicia sesión, para no tener que pedirle usuario y
contraseña en cada clic dentro del dashboard.

**Ejemplo de la vida real:** es como un sello en la mano al entrar a un evento: no
necesitas mostrar tu boleto otra vez cada vez que quieres volver a entrar por la misma
puerta, el sello (cookie) ya demuestra que pagaste.

---

### sesión
**Qué es:** el período de tiempo en que un usuario está "reconocido" por el sistema
después de iniciar sesión, hasta que cierra sesión o la sesión expira.

**Para qué sirve en Nimbo:** mientras dura la sesión de un usuario logueado, `@login_
required` (en las rutas de `app.py`) permite el acceso sin volver a pedir contraseña, y
`current_user` (de Flask-Login) sabe quién es y qué rol tiene (admin/empleado/técnico).

**Ejemplo de la vida real:** es como estar "fichado" en el trabajo: desde que marcas
tarjeta de entrada hasta que marcas de salida, el sistema sabe que estás presente sin que
tengas que volver a identificarte en cada puerta interna.

---

### middleware
**Qué es:** código que se ejecuta AUTOMÁTICAMENTE antes (o después) de que se atienda
una petición, sin que cada ruta tenga que acordarse de llamarlo.

**Para qué sirve en Nimbo:** `@app.before_request` en `app.py` (la función que revisa si
el onboarding está completo, `require_setup`) es middleware: corre antes de CUALQUIER
ruta, redirigiendo a `/setup` si hace falta, sin que cada una de las decenas de rutas de
`app.py` tenga que chequear eso por su cuenta. `@login_required` es otro ejemplo: se
"engancha" delante de una ruta para exigir sesión iniciada antes de dejarla correr.

**Ejemplo de la vida real:** es como el guardia de seguridad en la entrada de un
edificio: revisa la identificación de TODOS antes de que lleguen a cualquier piso,
en vez de que cada oficina tenga que poner su propio guardia en su puerta.

---

### migración
**Qué es:** un cambio en la estructura de una base de datos ya existente (agregar una
columna nueva, por ejemplo) sin borrar los datos que ya estaban guardados.

**Para qué sirve en Nimbo:** `Usuario.Telefono` (agregada con `ALTER TABLE` en
`core/auth.py`, `init_usuarios()`) es una migración: la tabla `Usuario` ya existía con
datos reales, y se le agregó una columna nueva sin perder ningún usuario ya creado. Lo
mismo con `Cliente.GrupoCliente` y `PagoFijo.Monto` (ver `CLAUDE.md`).

**Ejemplo de la vida real:** es como agregarle una columna nueva a un archivero físico ya
lleno de carpetas (por ejemplo, empezar a anotar el "Teléfono" en cada ficha) sin tener
que rehacer todas las fichas que ya existían desde cero.

---

### ORM (Mapeo Objeto-Relacional)
**Qué es:** una capa de software que traduce clases de un lenguaje de programación
(objetos) a tablas de una base de datos, para escribir consultas usando código en vez de
SQL directo.

**Para qué sirve en Nimbo:** Nimbo **no usa** ningún ORM - todo el acceso a datos en
`database/nimbo_db.py` se hace con SQL directo vía `sqlite3` (`cur.execute("SELECT ...
FROM Producto WHERE ...")`). Fue una decisión deliberada (ver decisión #7 de
`DECISIONS.md`, Flask vs Django): la base de Aronium tiene un esquema heredado y
particular que un ORM tradicional no modelaría con comodidad, así que se prefirió
control total con SQL escrito a mano.

**Ejemplo de la vida real:** un ORM es como un traductor automático que convierte tus
frases en español a otro idioma; Nimbo, en cambio, prefirió escribir directamente en el
idioma nativo de la base de datos (SQL) para no perder matices en la traducción.

---

### CRUD (Crear, Leer, Actualizar, Borrar)
**Qué es:** las cuatro operaciones básicas que casi cualquier sistema necesita hacer
sobre sus datos: Crear un registro nuevo, Leer (consultar) uno existente, Actualizar sus
datos, o Borrarlo.

**Para qué sirve en Nimbo:** el panel "Usuarios" del dashboard es un CRUD completo:
crear un usuario nuevo, listarlos (leer), activar/desactivar o cambiar su contraseña
(actualizar) - por diseño, Nimbo no permite borrar usuarios, solo desactivarlos, para no
perder el rastro de quién hizo qué en el historial.

**Ejemplo de la vida real:** es como llevar un cuaderno de clientes: puedes anotar uno
nuevo (crear), buscar uno que ya anotaste (leer), tachar y corregir un dato (actualizar),
o arrancar la hoja completa (borrar) - las cuatro acciones básicas que se hacen sobre
cualquier registro.

---

### REST (Transferencia de Estado Representacional)
**Qué es:** un estilo común de diseñar una API web, donde cada URL representa un
"recurso" (ej. "un usuario", "un producto") y el tipo de petición HTTP (GET, POST, PUT,
DELETE) indica qué acción hacer sobre ese recurso.

**Para qué sirve en Nimbo:** las rutas `/api/usuarios` (GET para listar, POST para crear)
y `/api/usuarios/<id>/toggle` siguen ese mismo espíritu: la URL identifica QUÉ (usuarios,
o un usuario específico) y el método HTTP identifica la acción. Nimbo no sigue las
convenciones REST de manera estricta en todos sus endpoints (hay rutas con verbos en la
URL, como `/toggle` o `/retirar`), pero la idea general - una URL por recurso - se usa en
buena parte de la API.

**Ejemplo de la vida real:** es como pedirle algo a un mesero usando siempre la misma
estructura de frase: "[verbo] el/un [platillo]" - "tráeme la sopa", "cambia la sopa",
"quita la sopa" - una gramática consistente para pedir cualquier cosa del menú.

---

### single-tenant
**Qué es:** un diseño de software donde una sola instalación del sistema atiende a UN
solo cliente/negocio - todos los datos, usuarios y configuración viven juntos, sin
ninguna separación entre "de quién es qué".

**Para qué sirve en Nimbo:** así nació Nimbo originalmente: un solo `nimbo.db` en la
raíz del proyecto, pensado solo para Mi Cocina Electrodomésticos - no había forma de que
una segunda tienda usara el mismo Nimbo sin mezclar su inventario, sus ventas y sus
usuarios con los de Mi Cocina.

**Ejemplo de la vida real:** es como una casa unifamiliar - una sola familia, un solo
buzón, no hay que distinguir de quién es cada cosa porque todo es de los mismos dueños.

---

### multi-tenant
**Qué es:** un diseño de software donde una sola instalación atiende a VARIOS
clientes/negocios distintos ("inquilinos", tenants en inglés) al mismo tiempo, cada uno
con sus propios datos completamente separados de los demás, aunque compartan el mismo
código corriendo.

**Para qué sirve en Nimbo:** desde la migración del 2026-07-18, Nimbo dejó de ser
single-tenant - ahora cada empresa (Mi Cocina, Surti La Unión, y cualquier otra que se
registre) tiene su propio `nimbo.db` completamente aparte, en
`data/empresas/<slug>/nimbo.db`, aunque las dos corran sobre el mismo `app.py`. `core/
empresa.py`, `nimbo_master.db` y `flask.g.empresa_db` (ver esos términos abajo) son las
piezas que hacen posible esa separación.

**Ejemplo de la vida real:** es como un edificio de apartamentos - un solo edificio (el
código de Nimbo), pero cada apartamento (cada empresa) tiene su propia llave, sus
propias cosas adentro, y un vecino jamás puede entrar sin querer al apartamento de otro.

---

### slug
**Qué es:** una versión de un nombre simplificada para usarse como identificador
técnico: todo en minúsculas, sin espacios ni tildes ni símbolos, generalmente con
guiones en vez de espacios - pensada para aparecer en una URL o una ruta de archivo sin
causar problemas.

**Para qué sirve en Nimbo:** `core/empresa.py._generar_slug()` convierte el nombre de
una empresa (ej. "Surti La Unión") en su slug ("surti-la-union"), que se usa como
nombre de la carpeta de esa empresa (`data/empresas/surti-la-union/`) y como el
identificador que viaja en `session['empresa_slug']` para saber, en cada request, con
cuál empresa está trabajando el usuario.

**Ejemplo de la vida real:** es como el "@usuario" que elegís en una red social en vez de
tu nombre completo con acentos y espacios - "María José Pérez" podría ser
`@maria-jose-perez`, algo más simple y sin caracteres raros para que el sistema lo use
como identificador.

---

### nimbo_master.db
**Qué es:** (no es un término genérico de programación, sino el nombre real de un
archivo de este proyecto) la base de datos "maestra" que Nimbo usa para saber qué
empresas existen y dónde está el `nimbo.db` de cada una.

**Para qué sirve en Nimbo:** vive en la raíz del proyecto, separada de los `nimbo.db` de
cada empresa. Tiene una sola tabla, `Empresa` (Nombre, Slug, DbPath, Activo,
CreatedAt) - nunca guarda datos de negocio (productos, ventas, clientes) de ninguna
empresa, solo el directorio que le dice a `app.py` a qué archivo conectarse según la
empresa que el usuario elija en `/select-empresa`.

**Ejemplo de la vida real:** es como el directorio de un edificio de oficinas en la
recepción: no tiene los documentos de cada empresa adentro, solo dice "la empresa X está
en la oficina 301, la empresa Y en la 402" - para saber a qué puerta tocar.

---

### flask.g
**Qué es:** un objeto especial de Flask que guarda datos válidos solo durante UN
request - se limpia solo y automáticamente en cuanto ese request termina, así que no hay
riesgo de que datos de una petición se mezclen con la siguiente.

**Para qué sirve en Nimbo:** `set_empresa_context()` (en `app.py`, corre en cada
request) lee `session['empresa_slug']` (que sí persiste entre requests, ver **sesión**
más arriba en este glosario) y calcula `g.empresa_slug`/`g.empresa_db` de nuevo cada
vez. Todas las funciones de acceso a datos (`core/auth.py._connect()`,
`database/nimbo_db.py.nimbo_connect()`, `core/configuracion.py._connect()`) leen
`g.empresa_db` para saber a qué `nimbo.db` conectarse en ESE request específico, sin que
cada una de las cientos de funciones del proyecto tenga que recibir la empresa como
parámetro explícito.

**Ejemplo de la vida real:** es como una etiqueta con el número de mesa que un mesero
lleva prendida solo mientras atiende esa mesa - la usa mientras dura el servicio, y la
suelta antes de atender la siguiente, sin confundir los pedidos de una mesa con los de
otra.

---

### empresa_slug
**Qué es:** (no es un término genérico, es el nombre real de una clave usada en este
proyecto) el dato que identifica, dentro de la sesión de un usuario, con cuál empresa
está trabajando en ese momento.

**Para qué sirve en Nimbo:** `session['empresa_slug']` se guarda cuando el usuario elige
una empresa en `/select-empresa` (o al registrar una nueva vía `/api/empresa/crear`), y
se vuelve a confirmar al hacer login exitoso. `set_empresa_context()` lo lee en cada
request para resolver `g.empresa_db` (ver **flask.g** arriba) - sin `empresa_slug` en la
sesión, `GET /` redirige directo a `/select-empresa` en vez de mostrar el dashboard.

**Ejemplo de la vida real:** es como la pulserita de color que te ponen en un hotel
todo-incluido para saber a cuál de varios resorts del mismo dueño perteneces - el
personal la mira para saber en qué restaurante/piscina tenés acceso, sin tener que
preguntarte cada vez de dónde venís.

### hook
**Qué es:** un comando que Claude Code corre automáticamente en un momento específico
(antes o después de que Claude use una herramienta, por ejemplo), sin que nadie tenga
que pedirlo cada vez.

**Para qué sirve en Nimbo:** `.claude/hooks/py_syntax_check.py` corre `python3 -m
py_compile` automáticamente cada vez que se edita un archivo `.py` del proyecto, y
`.claude/hooks/block_db_edit.py` bloquea cualquier intento de editar un `.db` como si
fuera texto - ambos configurados en `.claude/settings.json` para que se disparen solos,
sin que haya que acordarse de correrlos a mano.

**Ejemplo de la vida real:** es como el sensor que hace sonar una alarma si abrís la
puerta de emergencia de un edificio - no hace falta que un guardia esté mirando esa
puerta todo el día, el sensor reacciona solo cuando pasa el evento que le importa.

---

### PreToolUse / PostToolUse
**Qué es:** los dos momentos más comunes en los que puede dispararse un **hook** (ver
arriba) de Claude Code: `PreToolUse` corre ANTES de que una herramienta se ejecute (y
puede bloquearla), `PostToolUse` corre DESPUÉS de que ya se ejecutó (y puede avisar de
un problema, pero ya no puede evitar que pasara).

**Para qué sirve en Nimbo:** `block_db_edit.py` está registrado como `PreToolUse` -
tiene que correr ANTES de que Edit/Write toquen un `.db`, para poder impedirlo a
tiempo. `py_syntax_check.py` está registrado como `PostToolUse` - corre DESPUÉS de que
el archivo `.py` ya se guardó, porque recién ahí existe el archivo completo para poder
revisar su sintaxis con `py_compile`.

**Ejemplo de la vida real:** es la diferencia entre el guardia que te para en la puerta
ANTES de entrar a un evento sin entrada (`PreToolUse`, todavía se puede evitar) y el
que te encuentra adentro y te pide que te retires (`PostToolUse`, el problema ya pasó,
pero se puede corregir).

---

### subagente
**Qué es:** una instancia separada de Claude, con su propia ventana de contexto y su
propio set de herramientas permitidas, dedicada a una tarea específica - se puede
invocar para que trabaje en paralelo sin llenar la conversación principal de detalles.

**Para qué sirve en Nimbo:** `.claude/agents/schema-consistency-reviewer.md` define un
subagente que revisa que el esquema de base de datos sea consistente entre todas las
empresas (multi-tenant) y entre el código y las bases de datos reales - la misma clase
de chequeo que habría atrapado el bug de `crear_empresa()` (19 tablas faltantes) antes
de que afectara a una empresa real.

**Ejemplo de la vida real:** es como llamar a un inspector externo especializado solo en
revisar instalaciones eléctricas, en vez de pedirle al arquitecto general del edificio
que también sepa de electricidad - el inspector se enfoca en una sola cosa y da su
reporte sin necesidad de conocer el resto del proyecto.


---

### onboarding
**Qué es:** el proceso guiado que ayuda a un usuario nuevo a arrancar a usar un
sistema por primera vez, en vez de dejarlo solo frente a una pantalla vacía sin saber
qué hacer.

**Para qué sirve en Nimbo:** hay dos onboardings distintos en el proyecto: el wizard
de `/setup` (7 pasos, datos del negocio/cuenta admin/configuración financiera, se
completa una sola vez por instalación) y, más nuevo, el diagnóstico de negocio +
tour del dashboard + tutorial del chat que ve el admin la primera vez que entra a una
empresa recién registrada (ver `DiagnosticoNegocio` y `tour guiado` abajo).

**Ejemplo de la vida real:** es como el recorrido que te da un guía turístico el primer
día en un lugar nuevo, en vez de soltarte solo en el centro de la ciudad con un mapa en
blanco - te muestra lo esencial primero, para que el resto lo explores con más
confianza.

---

### tour guiado (Shepherd.js)
**Qué es:** una secuencia de recuadros que van resaltando, uno por uno, distintas
partes de una pantalla, con una explicación corta de qué es cada una - el usuario
avanza con un botón "Siguiente" hasta terminar el recorrido.

**Para qué sirve en Nimbo:** el tour del dashboard (`templates/index.html`,
función `iniciarTourDashboard()`) usa la librería Shepherd.js (cargada por CDN, no
instalada con npm - el proyecto no tiene un paso de build de JavaScript) para resaltar
10 elementos reales del sidebar y el dashboard (el chat, las alertas, Inventario,
Caja...) la primera vez que un admin entra después de completar el diagnóstico de
negocio. Se controla con la clave `tour_completado` en `Configuracion` - una vez
cerrado, no se vuelve a mostrar solo, salvo que se pida de nuevo desde el botón "Ver
tour del dashboard" en Configuración.

**Ejemplo de la vida real:** es como cuando alguien te muestra una casa nueva
señalando cuarto por cuarto ("aquí la cocina, aquí el baño...") en vez de dejarte
explorarla solo desde el primer día - después de esa vuelta ya sabes dónde está todo.

---

### DiagnosticoNegocio
**Qué es:** (no es un término genérico, es el nombre real de una tabla de este
proyecto) una tabla que guarda las respuestas de un cuestionario sobre cómo funciona
un negocio: qué vende, cómo lleva el inventario, si el dueño se paga un sueldo, etc.

**Para qué sirve en Nimbo:** cuando un admin entra por primera vez a una empresa
recién registrada, `/diagnostico` le hace 23 preguntas en 6 bloques (el negocio, cómo
opera, el control actual, su equipo tecnológico, él como dueño, y su meta) antes de
dejarlo entrar al dashboard. Con las respuestas, `database.nimbo_db.
guardar_diagnostico()` calcula automáticamente un resumen del negocio y las 3 "áreas
de oportunidad" con más problema (por ejemplo, si el dueño contesta que lleva el
inventario "en la cabeza", esa se marca como un área crítica) junto con un primer paso
concreto para cada una dentro de Nimbo.

**Ejemplo de la vida real:** es como el cuestionario de salud que llena un paciente
antes de su primera cita con un médico nuevo - las respuestas ayudan al médico a saber
por dónde empezar, en vez de partir de cero sin ningún antecedente.


---

### importación masiva
**Qué es:** cargar muchos registros de una sola vez a partir de un archivo (Excel o
CSV), en vez de escribirlos uno por uno a mano en un formulario.

**Para qué sirve en Nimbo:** el admin puede subir un archivo con su inventario completo
(botón "📦 Importar desde Excel" en el panel Inventario, o "Subir mi Excel" en el chat
cuando la empresa todavía no tiene productos cargados) y Nimbo crea todos los productos
de una vez (`app.py`, ruta `POST /api/db/products/import` → `database.nimbo_db.
crear_producto_importado()`), en vez de tener que decir "agregar producto X" decenas o
cientos de veces.

**Ejemplo de la vida real:** es como llevarle al banco una lista completa de cheques
para depositar de una vez, en vez de ir ventanilla por ventanilla depositando cada uno
por separado.

---

### mapeo de columnas
**Qué es:** hacer corresponder cada columna de un archivo externo (con sus propios
nombres de encabezado, que pueden ser cualquier cosa) con el campo interno que el
sistema realmente espera - por ejemplo, que una columna llamada "Precio Venta" se
entienda como el campo `precio`.

**Para qué sirve en Nimbo:** al importar un Excel de inventario, `app.py.
_mapeo_automatico()` intenta adivinar solo qué columna es cuál (comparando los
encabezados contra una lista de sinónimos conocidos: "Precio", "Precio Venta", etc. -
todos apuntan al mismo campo interno `precio`). Si el archivo del usuario usa
encabezados que Nimbo no reconoce, el modal de importación muestra un `<select>` por
columna para que el admin corrija el mapeo a mano antes de confirmar, en vez de que la
importación falle o adivine mal en silencio.

**Ejemplo de la vida real:** es como cuando llenás un formulario migrado de otro
sistema y tenés que indicar "esta columna de tu archivo va en este campo de acá" -
alguien tiene que decidir la correspondencia cuando los nombres no son idénticos.

---

### template de importación (Excel)
**Qué es:** (no confundir con el "template" de Flask/Jinja, ver ese término más arriba
- comparten la palabra pero son conceptos distintos) un archivo Excel de ejemplo, ya
con las columnas correctas y una fila de muestra llena, que el usuario descarga, llena
con sus propios datos, y vuelve a subir.

**Para qué sirve en Nimbo:** `GET /api/db/products/plantilla` genera
`template_inventario_nimbo.xlsx` al vuelo (con `openpyxl`, sin guardar nada en disco):
columnas Nombre/Codigo/Precio/Costo/Stock/Descripcion/Unidad, una fila ya llena con un
producto de ejemplo, una fila en blanco para empezar a escribir, y una segunda hoja
"Instrucciones" explicando qué va en cada columna - para que alguien que nunca usó
Nimbo entienda el formato esperado sin tener que adivinarlo.

**Ejemplo de la vida real:** es como el formulario de muestra "ya lleno" que te dan de
ejemplo antes de entregarte el formulario en blanco - ver un caso resuelto ayuda a
entender qué se espera en cada casilla.
