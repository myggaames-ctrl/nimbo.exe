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
sistema, la respuesta es JSON: `{"ollama": false, "aronium": true, "time": "18/07/2026
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

---

### rate limiting (límite de solicitudes)
**Qué es:** una regla que limita cuántas veces se puede llamar a una misma ruta (URL)
en un período de tiempo, contando por dirección IP (la "dirección" de internet desde
donde llega cada visitante). Pasado el límite, el servidor responde con el código
`429 Too Many Requests` en vez de procesar la solicitud.

**Para qué sirve en Nimbo:** `/login` acepta como máximo 5 intentos fallidos por IP
cada 15 minutos (Flask-Limiter, `app.py`) - así alguien no puede probar miles de
contraseñas seguidas contra la cuenta de un usuario real ("fuerza bruta"). Todas las
rutas `/api/*` además tienen un límite general de 100 solicitudes por minuto por IP,
para que un script que llame a la API sin parar no sature el servidor.

**Ejemplo de la vida real:** es como un guardia de seguridad que deja pasar a alguien
que se equivocó de PIN un par de veces, pero le pide esperar si sigue intentando una y
otra vez sin parar - una persona normal nunca llega a ese límite, solo alguien
probando contraseñas al voleo.

---

### CSRF (Cross-Site Request Forgery, falsificación de solicitud entre sitios)
**Qué es:** un ataque donde una página web MALICIOSA hace que tu navegador mande, sin
que te des cuenta, una solicitud a OTRO sitio donde ya tenés sesión iniciada (por
ejemplo Nimbo) - el navegador manda tu cookie de sesión automáticamente, así que el
sitio de destino no puede distinguir esa solicitud de una que hiciste vos a propósito.
La defensa es un "token CSRF": un código secreto que solo el formulario legítimo de
Nimbo conoce: si la solicitud no lo trae, se rechaza.

**Para qué sirve en Nimbo:** cada formulario que realmente se envía como el navegador
manda un `<form>` normal (login, seleccionar empresa, recuperar/cambiar contraseña, el
asistente de instalación `/setup`) incluye un campo oculto
`<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` (Flask-WTF). Las
rutas `/api/*` que reciben JSON desde el propio dashboard (fetch()) quedan exentas -
un sitio externo no puede lograr que el navegador mande la cookie de sesión en ese
tipo de solicitud (Nimbo usa `CORS(app)` en `app.py` sin habilitar credenciales
cross-origin), así que ahí un token adicional no suma protección real.

**Ejemplo de la vida real:** es como si alguien te hiciera firmar un cheque en blanco
sin que te dieras cuenta de qué estabas firmando, aprovechando que ya tenías la
chequera abierta - el token CSRF es como un sello único que solo el banco (Nimbo)
conoce, así un cheque fotocopiado desde otro lado nunca pasa.

---

### XSS (Cross-Site Scripting)
**Qué es:** un ataque donde alguien logra que su propio código JavaScript se ejecute
dentro de la página de OTRA persona - por ejemplo, guardando un `<script>` malicioso
en un campo de texto que después se muestra sin filtrar en el navegador de otro
usuario.

**Para qué sirve en Nimbo:** es la razón por la que se corrigió un bug real de esta
naturaleza en la importación de Excel (escapar HTML en el preview/resultado, ver
`BUGS_Y_FIXES.md`, 2026-08-05) y una de las cosas que el CSP (ver ese término más
abajo) ayuda a contener, aunque no reemplaza escapar bien cada dato antes de mostrarlo.

**Ejemplo de la vida real:** es como si alguien pudiera escribir en el cartel de
"próximos turnos" de una clínica un mensaje que en realidad ejecuta una orden para
todos los que lo lean, en vez de solo mostrar texto - el cartel debería mostrar
cualquier texto tal cual, nunca "obedecerlo".

---

### CSP (Content Security Policy, política de seguridad de contenido)
**Qué es:** un header HTTP que le dice al navegador de qué orígenes (dominios) tiene
permitido cargar scripts, estilos, fuentes e imágenes para una página - cualquier cosa
fuera de esa lista se bloquea, aunque un atacante lograra inyectarla (ver XSS arriba).

**Para qué sirve en Nimbo:** Flask-Talisman (`app.py`) manda un CSP en cada respuesta
que permite `'self'` (el propio Nimbo) más los CDNs que el dashboard ya usaba antes de
este cambio: `fonts.googleapis.com`/`fonts.gstatic.com` (Google Fonts),
`cdn.jsdelivr.net` (Shepherd.js, el tour del dashboard) y `cdnjs.cloudflare.com`
(Chart.js, los gráficos de Análisis) - cualquier otro origen queda bloqueado por el
navegador. Incluye `'unsafe-inline'` en scripts/estilos porque el dashboard usa mucho
`onclick="..."` y `<style>` inline en el HTML - una limitación conocida, ver
`BUGS_Y_FIXES.md`.

**Ejemplo de la vida real:** es como una lista de proveedores autorizados para una
obra - aunque alguien intente colar materiales de otro lado, el control de acceso los
rechaza en la puerta, vengan de quien vengan.

---

### HSTS (HTTP Strict Transport Security)
**Qué es:** un header HTTP que le dice al navegador "de ahora en adelante, conectate a
este sitio SIEMPRE por HTTPS (la versión cifrada), nunca por HTTP plano, aunque
alguien te pase un link http://" - solo tiene sentido si el sitio de verdad se sirve
por HTTPS.

**Para qué sirve en Nimbo:** por ahora está DESACTIVADO (`strict_transport_security=False`
en la configuración de Flask-Talisman, `app.py`) porque este entorno (WSL2, desarrollo)
todavía sirve por HTTP plano, sin certificado TLS - activarlo ahora rompería el acceso
normal. Queda documentado para activarlo el día que Nimbo se sirva con HTTPS real en
producción.

**Ejemplo de la vida real:** es como decirle a alguien "de ahora en más, entrá siempre
por la puerta con guardia de seguridad, nunca por la de atrás" - no tiene sentido dar
esa instrucción si todavía no existe la puerta con guardia.

---

### toast (notificación)
**Qué es:** una notificación pequeña que aparece en la pantalla por unos segundos y
después desaparece sola, sin interrumpir lo que estabas haciendo (a diferencia de un
`alert()` o un modal, que bloquean la pantalla hasta que le hagas clic). El nombre
viene de que "salta" a la vista como una tostada que salta de la tostadora.

**Para qué sirve en Nimbo:** el sistema de notificaciones del dashboard (ver
`BUGS_Y_FIXES.md`, 2026-08-06) muestra alertas de negocio (stock en cero, pagos por
vencer, etc.) como toasts que se deslizan desde la esquina superior derecha y se
cierran solos a los 6 segundos (o antes, con el botón ✕) - hasta 4 a la vez, el resto
espera en una cola (`alertasCola` en `templates/index.html`).

**Ejemplo de la vida real:** es como las notificaciones que aparecen arriba de la
pantalla de un teléfono cuando llega un mensaje - las ves, y si no hacés nada
desaparecen solas después de un rato, sin que tengas que cerrarlas a la fuerza para
seguir usando el teléfono.

---

### polling
**Qué es:** la técnica de preguntarle al servidor "¿hay algo nuevo?" a intervalos
regulares (cada tantos segundos/minutos), en vez de que el servidor avise por su
cuenta cuando pasa algo (eso último se llama "push", y necesita una conexión especial
tipo WebSocket que Nimbo no usa).

**Para qué sirve en Nimbo:** el reloj del dashboard llama a `refreshStatus()` cada 30
segundos, y el sistema de notificaciones llama a `cargarAlertasToast()` cada 5 minutos
(`ALERTAS_POLL_MS` en `templates/index.html`) para revisar si hay alertas nuevas -
ambos son polling: el navegador pregunta, el servidor no avisa solo.

**Ejemplo de la vida real:** es como llamar por teléfono cada rato para preguntar "¿ya
llegó el paquete?" en vez de que el cartero te llame a vos apenas llega - funciona,
pero es el que pregunta el que tiene que acordarse de insistir.

---

### sessionStorage y localStorage
**Qué es:** dos lugares donde el navegador puede guardar datos pequeños (texto)
asociados a un sitio web, sin necesidad de mandarlos al servidor. La diferencia entre
los dos es cuánto dura lo guardado: `sessionStorage` se borra solo al cerrar esa
pestaña/ventana; `localStorage` queda guardado aunque cierres el navegador y lo
vuelvas a abrir otro día.

**Para qué sirve en Nimbo:** el sistema de notificaciones usa `sessionStorage` para
recordar qué alertas cerraste con la X **en esta sesión** (no repetirlas mientras
sigas con la pestaña abierta) y `localStorage` para el historial de la campana
(**todas** las alertas de hoy, se hayan cerrado o no - tiene que sobrevivir a que
recargues la página con F5, algo que `sessionStorage` también permite, pero se pensó
como el lugar más natural para "lo de hoy" independientemente de la pestaña).

**Ejemplo de la vida real:** `sessionStorage` es como una nota adhesiva pegada al
escritorio de hoy - desaparece cuando levantás el escritorio (cerrás la pestaña).
`localStorage` es como una libreta que dejás guardada en el cajón - sigue ahí mañana,
la abras cuando la abras.

---

### multimodal (modelo de IA con visión)
**Qué es:** un modelo de inteligencia artificial que puede recibir no solo texto sino
también imágenes (u otros formatos como audio/video) como parte de la pregunta, y
responder analizando lo que "ve" en esa imagen.

**Para qué sirve en Nimbo:** `services/ollama_service.py.analizar_imagen_ollama()`
manda una foto subida al chat al endpoint `/api/chat` de Ollama en formato
multimodal (la imagen va codificada en base64 dentro del mensaje) para intentar
identificar qué producto aparece en la foto - pero solo si el modelo que Nimbo tiene
instalado soporta esto (ver `modelo_soporta_vision()` más abajo); hoy ninguno de los
dos modelos pulled en este entorno (`qwen2.5:7b`, `gemma2:9b`) lo soporta, así que en
la práctica el sistema cae siempre al texto que el usuario escribió junto a la foto.

**Ejemplo de la vida real:** es la diferencia entre pedirle algo a alguien por
teléfono (solo puede escuchar lo que decís) o en persona mostrándole una foto (puede
"ver" de qué estás hablando, además de escucharte).

---

### capabilities (de un modelo de Ollama)
**Qué es:** una lista que Ollama expone (desde una versión reciente) en
`GET /api/tags` por cada modelo instalado, indicando qué puede hacer ese modelo en
particular - por ejemplo `"vision"` si soporta imágenes, o `"tools"` si soporta
function calling.

**Para qué sirve en Nimbo:** `services/ollama_service.py.modelo_soporta_vision()`
revisa esta lista para decidir, en el momento (no con un valor fijo escrito a mano),
si vale la pena mandarle una foto al modelo de chat o si hay que pedirle al usuario
que describa el producto a mano. Así, si en el futuro se instala un modelo con visión
(ej. `llava`), Nimbo empieza a usarla automáticamente sin que haya que tocar código.

**Ejemplo de la vida real:** es como revisar la ficha técnica de un empleado nuevo
("sabe manejar", "habla inglés") antes de asignarle una tarea, en vez de asumir que
puede hacer cualquier cosa y descubrir a mitad de camino que no.

---

### aspect ratio (relación de aspecto)
**Qué es:** la proporción entre el ancho y el alto de una imagen o video - por
ejemplo `9:16` es un video alto y angosto (como una pantalla de teléfono en
vertical), y `1:1` es un video cuadrado.

**Para qué sirve en Nimbo:** `services/video_gen.py.generar_video_producto()` recibe
un parámetro `aspect_ratio` que se le pasa a Veo 3 (Vertical Video, el generador de
video de Google) para que el video salga con la forma correcta según dónde se vaya a
publicar - `9:16` para TikTok/Instagram Reels (donde el celular se sostiene en
vertical) y `1:1` para Facebook (donde un video cuadrado se ve bien tanto en celular
como en computadora).

**Ejemplo de la vida real:** es como elegir entre tomar una foto "acostada" (horizontal)
o "parada" (vertical) con el celular, según si la vas a poner en una historia de
Instagram o en un marco de foto de escritorio - el contenido puede ser el mismo, pero
la forma tiene que encajar donde se va a mostrar.

---

### marcador (texto sintético como puente entre dos partes del sistema)
**Qué es:** en Nimbo, un texto con un formato especial y reconocible (ej.
`VIDEO_INICIO:...`, `[FOTO:ruta]`) que una parte del código genera y otra parte del
código sabe interpretar, para pasarse información sin tener que cambiar la firma de
ninguna función.

**Para qué sirve en Nimbo:** `core.nimbo.send()` solo recibe texto (el mensaje del
chat) - cuando hace falta que arranque un flujo especial con datos que no vinieron
como texto normal (ej. una foto subida por `POST /api/chat/foto`, o un código de
barras escaneado), en vez de agregarle un parámetro nuevo a `send()`, el resto del
sistema arma un mensaje de texto con un marcador al principio (`[FOTO:ruta] mensaje`)
que un detector reconoce y convierte en el flujo correspondiente. Las herramientas
(`tools/*.py`) también usan marcadores para decirle a `core/nimbo.py` "arrancá este
flujo de varios pasos" (ej. `VIDEOFOTO_ENCONTRADO_INICIO:id|nombre|precio|foto`).

**Ejemplo de la vida real:** es como escribir "URGENTE:" al principio de un correo
para que quien lo reciba sepa, con solo ver esa palabra, que tiene que tratarlo
distinto al resto de correos normales - sin necesidad de un sistema de correo
completamente distinto solo para los urgentes.

---

### meta-prompt (un prompt que le pide a la IA que escriba otro prompt)
**Qué es:** un prompt (la instrucción que se le manda a un modelo de IA) cuyo trabajo
no es responder la pregunta final del usuario, sino generar OTRO prompt más elaborado
que después se usa para la tarea real.

**Para qué sirve en Nimbo:** en el flujo de "video desde foto" (ver
`core/nimbo.py.PROMPT_OPTIMIZAR_VIDEO`), cuando el usuario pide que Nimbo optimice el
video con IA, no se le manda a Veo 3 directamente lo que el usuario escribió - primero
se le pide a Ollama (con `PROMPT_OPTIMIZAR_VIDEO`, el meta-prompt) que, a partir de los
datos recolectados (producto, precio, tono, plataforma, etc.), redacte un prompt
profesional de videografía (con iluminación, movimiento de cámara, composición, etc.)
- y ES ESE prompt, el que devuelve Ollama, el que finalmente se le manda a Veo 3.

**Ejemplo de la vida real:** es como pedirle a un redactor publicitario profesional
que convierta tu idea suelta ("quiero un anuncio de la licuadora, que se vea bien") en
un guion detallado y técnico, en vez de dárselo tú mismo al camarógrafo sin pulir -
el redactor no filma nada, solo mejora las instrucciones que después usa otra persona
(o, en este caso, otro sistema de IA) para hacer el trabajo final.

---

### llava (modelo de IA con visión, "Large Language and Vision Assistant")
**Qué es:** un modelo de IA de código abierto entrenado específicamente para
entender imágenes además de texto (a diferencia de `qwen2.5:7b`, el modelo de chat
que usa Nimbo para todo lo demás, que NO tiene esa capacidad).

**Para qué sirve en Nimbo:** el análisis visual real de la foto de un producto (ver
`tools/contenido_tool.py.video_desde_foto_tool()`, flujo de video desde foto en el
chat) le pide específicamente a `llava` - no al modelo de chat por defecto - que
describa el color, material, forma y condición reales del producto en la foto, para
que el video generado por Veo 3 muestre el producto tal como es, no una versión
inventada. Esto es una excepción deliberada a la política de "un solo modelo para
todo" que documenta `CLAUDE.md` (ver esa sección para el porqué de esa política) -
`llava` solo se usa si está `ollama pull`eado, se detecta en el momento (ver
`modelo_soporta_vision()`) y nunca se alterna con el modelo de chat dentro de la
misma llamada, así que no reintroduce el problema de recarga que esa política evita.

**Ejemplo de la vida real:** es como llamar a un fotógrafo especializado para que
describa en detalle una pieza (color exacto, textura, desperfectos) en vez de
pedírselo a un asistente general que nunca ha visto una foto en su vida - cada uno
tiene su especialidad.

---

### code fences (bloques de código delimitados con \`\`\`)
**Qué es:** la forma en que Markdown (y muchos modelos de IA al responder) marcan un
bloque de texto como "código" o "datos", envolviéndolo entre tres comillas invertidas
(\`\`\`), a veces con el nombre del lenguaje después de las primeras (ej. \`\`\`json).

**Para qué sirve en Nimbo:** cuando se le pide a `llava` que responda con JSON
estricto (ver `tools/contenido_tool.py.video_desde_foto_tool()`), el modelo a veces
envuelve la respuesta en fences (\`\`\`json ... \`\`\`) a pesar de que el prompt le
pide explícitamente que no lo haga - hay que quitarlos antes de poder leer el JSON
con `json.loads()`, o la llamada falla porque `\`\`\`json` no es JSON válido.

**Ejemplo de la vida real:** es como si alguien te dictara un número de teléfono pero
lo metiera entre paréntesis ("el número es (555-1234)") - en el fondo el dato real
sigue siendo "555-1234", pero primero hay que quitarle los paréntesis antes de
poder marcarlo en el teléfono.
