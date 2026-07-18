# Decisiones técnicas de Nimbo (explicadas para quien está aprendiendo a programar)

Este documento no es un manual de uso de Nimbo. Es un "por qué se hizo así" de las
decisiones más importantes del proyecto. La idea es que si estás aprendiendo a programar
y te preguntas "¿por qué no simplemente...?", encuentres la respuesta aquí, con ejemplos
de código simplificados y explicados línea por línea.

Cada decisión sigue la misma estructura:
- **Qué problema resolvía**
- **Qué opciones había**
- **Por qué se eligió esta solución**
- **Qué archivo(s) la implementan**
- **Ejemplo de código simplificado, explicado línea por línea**

---

## 1. Por qué usamos detectores de regex en lugar de solo IA para los comandos

### Qué problema resolvía
Nimbo tiene que entender frases como "vendí 2 licuadoras", "cuánto debe Juan Pérez" o
"abrir caja" y convertirlas en una acción concreta (descontar stock, consultar una deuda,
abrir un turno de caja). Necesitábamos una forma de reconocer estos comandos que fuera
**rápida**, **gratis** y, sobre todo, **predecible**: si el sistema va a descontar stock
real o registrar dinero real, no nos podemos dar el lujo de que a veces lo interprete bien
y a veces mal.

### Qué opciones había
1. **Mandar todo a una IA (un modelo de lenguaje)**: el usuario escribe cualquier cosa, la
   IA decide qué acción ejecutar.
2. **Reglas escritas a mano con expresiones regulares (regex)**: patrones de texto exactos
   que reconocen una frase y extraen sus datos (cantidad, nombre del producto, etc).
3. **Un híbrido**: probar primero las reglas de regex (rápidas y exactas) y, solo si
   ninguna reconoce el mensaje, recién ahí preguntarle a la IA.

### Por qué se eligió esta solución
Se eligió el híbrido (opción 3), con las reglas de regex como primera línea:

- **Velocidad**: un regex tarda microsegundos. Una llamada a un modelo de IA en esta PC
  (sin GPU) tarda entre varios segundos y varios minutos (ver decisión #3, sobre Ollama).
  Si el 90% de los mensajes son comandos de rutina, no tiene sentido hacerlos esperar por
  una IA.
- **Predecibilidad**: un regex que matchea SIEMPRE hace exactamente lo mismo. Una IA puede
  "alucinar" un número o interpretar mal una cantidad de dinero - inaceptable cuando de por
  medio hay stock real o ventas reales.
- **Disponibilidad**: si Ollama (la IA local) está caído, lento o recargando otro modelo,
  los comandos de rutina siguen funcionando exactamente igual, porque no dependen de él.
- La IA se reserva como **red de seguridad**: solo entra en juego cuando ningún patrón de
  regex reconoció el mensaje (ver `Arquitectura del chat` en `CLAUDE.md`), primero para
  traducir el mensaje a un comando conocido, y si tampoco eso funciona, para responder
  directamente en lenguaje natural.

### Qué archivo(s) implementan la solución
- `core/detectors/*.py` - un detector por área de negocio (ventas, inventario, clientes,
  servicio técnico, etc.), cada uno con su propia lista de patrones regex.
- `core/intent_detector.py` - prueba cada detector, en orden, hasta que alguno reconozca
  el mensaje.
- `core/command_normalizer.py` - corrige errores de tipeo comunes antes de que el mensaje
  llegue a los detectores (para que un regex no falle solo porque alguien escribió
  "cuchila" en vez de "cuchilla").
- `core/nimbo.py` - si ningún detector reconoce el mensaje, ahí recién se llama a Ollama.

### Ejemplo de código simplificado, explicado línea por línea

```python
import re

class VentaDetectorSimplificado:

    # Un patron de regex que reconoce "vendi 2 licuadoras" o "vendio 3 cuchillas"
    PATRON_VENTA = r"^vend[io]+\s+(\d+)\s+(.+)$"

    def detect(self, texto: str):
        match = re.search(self.PATRON_VENTA, texto)
        if match:
            cantidad = match.group(1)
            producto = match.group(2)
            return {"intent": "venta.registrar", "cantidad": int(cantidad), "query": producto}
        return None
```

Línea por línea:
- `import re`: importa el módulo de expresiones regulares de Python.
- `PATRON_VENTA = r"^vend[io]+\s+(\d+)\s+(.+)$"`: define el patrón. Se lee así:
  - `^` - el texto debe EMPEZAR aquí (no basta con que la frase "contenga" esto en cualquier lado).
  - `vend[io]+` - la palabra debe empezar con "vend" y seguir con una o más letras "i" u "o"
    (así reconoce tanto "vendi" como "vendio", incluso "vendii" por error de tipeo).
  - `\s+` - uno o más espacios en blanco.
  - `(\d+)` - uno o más dígitos, **capturados entre paréntesis** para poder leerlos después
    (esta será la cantidad).
  - `\s+` - otro espacio.
  - `(.+)` - "cualquier cosa" hasta el final, también capturada (este será el nombre del
    producto, que puede tener varias palabras: "licuadora oster mini").
  - `$` - el texto debe TERMINAR aquí.
- `def detect(self, texto: str):` - el método que cada detector implementa: recibe el
  mensaje ya normalizado y responde si lo reconoce o no.
- `match = re.search(self.PATRON_VENTA, texto)` - intenta encajar el patrón contra el
  texto. Si no encaja, `match` queda en `None`.
- `if match:` - solo entramos aquí si el patrón sí encajó.
- `cantidad = match.group(1)` - `group(1)` es lo que capturó el primer paréntesis: la cantidad.
- `producto = match.group(2)` - `group(2)` es lo que capturó el segundo paréntesis: el nombre.
- `return {"intent": "venta.registrar", ...}` - devuelve un diccionario con el "intent"
  (qué tool hay que ejecutar) y los datos ya extraídos, listos para usar.
- `return None` - si el patrón no encajó, se devuelve `None` para que `IntentDetector`
  siga probando el siguiente detector de la lista.

(El archivo real, `core/detectors/venta_detector.py`, tiene varios patrones más para
cubrir distintas formas de decir lo mismo: "venta X 2 unidades", "se vendió 2 X", etc.)

---

## 2. Por qué el archivo de base de datos se llamaba aronium.py y ahora es nimbo_db.py

### Qué problema resolvía
Antes de que Nimbo tuviera su propio catálogo de productos, TODO el acceso a datos
(productos, stock, ventas, clientes) pasaba por **Aronium**, un programa de punto de venta
de un tercero que ya estaba instalado en la tienda, leyendo y escribiendo directamente su
base de datos SQLite (`pos.db`). Por eso el archivo que concentraba esas funciones se llamó
`database/aronium.py`.

Con el tiempo, Nimbo migró su propio catálogo de productos y stock a tablas propias dentro
de `nimbo.db` (ver la sección "Catálogo propio" de `CLAUDE.md`), y hoy Aronium solo se usa
para un puñado de cosas que siguen siendo su dominio: reportes de ventas hechas en la caja
física y el catálogo nativo de clientes. El archivo, sin embargo, seguía llamándose
`aronium.py` - un nombre que ya no describía lo que el archivo hace en su mayoría, y que
podía confundir a cualquiera que lo abriera pensando que TODO ahí adentro habla con
Aronium.

### Qué opciones había
1. **Dejarlo como estaba** y solo aclarar en un comentario o en `CLAUDE.md` que el nombre
   es "histórico" (esto es lo que se hizo primero, como solución provisional).
2. **Partir el archivo en dos**: uno solo para las funciones que hablan con Aronium/pos.db,
   y otro para las tablas propias de nimbo.db.
3. **Renombrar el archivo completo** a algo que refleje lo que hace hoy
   (`nimbo_db.py`), sin dividirlo.

### Por qué se eligió esta solución
Se eligió renombrar (opción 3) en vez de dividir en dos (opción 2) porque el archivo mezcla
ambas fuentes de forma entrelazada dentro de varias funciones - por ejemplo,
`migrar_productos_desde_aronium()` necesita LEER de Aronium y ESCRIBIR en nimbo.db en la
misma operación. Separarlas hubiera sido una refactorización mucho más grande y riesgosa
(más archivos que tocar, más superficie para romper algo) solo para arreglar un nombre.

Renombrar es una operación mecánica y de bajo riesgo: cambiar el nombre del archivo y
actualizar cada `import` que lo mencionaba. Resuelve exactamente el problema real (que el
nombre mienta sobre lo que hace) sin tocar ni una línea de la lógica interna.

### Qué archivo(s) implementan la solución
- `database/nimbo_db.py` - el archivo renombrado (antes `database/aronium.py`).
- Los ~30 archivos que lo importaban: `app.py` y prácticamente todos los `core/detectors/*.py`,
  `tools/*.py` y `services/*.py` que hacían `from database.aronium import ...`.

### Ejemplo de código simplificado, explicado línea por línea

```bash
# Paso 1: renombrar el archivo conservando su historial en git
git mv database/aronium.py database/nimbo_db.py

# Paso 2: buscar y reemplazar el import en cada archivo del proyecto
sed -i 's/from database\.aronium import/from database.nimbo_db import/g' *.py
```

Línea por línea:
- `git mv database/aronium.py database/nimbo_db.py`: renombra el archivo usando `git mv`
  en vez de borrar y crear uno nuevo - así git sabe que es el MISMO archivo con otro
  nombre, y conserva su historial de cambios (`git log` sigue mostrando los commits
  anteriores al rename).
- `sed -i 's/patron/reemplazo/g' *.py`: `sed` es una herramienta de línea de comandos que
  busca y reemplaza texto dentro de archivos.
  - `-i` significa "in place": modifica el archivo directamente (sin esto, solo mostraría
    el resultado en pantalla sin guardar nada).
  - `'s/.../.../g'` es el comando de sustitución: `s` de "substitute", y la `g` al final
    significa "global" (reemplaza TODAS las coincidencias en cada línea, no solo la primera).
  - `from database\.aronium import` - el patrón a buscar. El `\.` significa "un punto
    literal" (sin la barra invertida, el punto en regex significa "cualquier carácter").
  - `from database.nimbo_db import` - el texto de reemplazo.
  - `*.py` - aplica el reemplazo a todos los archivos `.py` de la carpeta actual.

En el proyecto real esto se hizo con un poco más de cuidado: se revisó cada mención
restante de la palabra "aronium" uno por uno, porque muchas de ellas (por ejemplo
`ARONIUM_DB_PATH`, o comentarios que dicen "esto todavía consulta a Aronium") se refieren
al programa Aronium de verdad, no al archivo renombrado - esas NO se tocaron.

---

## 3. Por qué usamos Ollama en lugar de solo Gemini API

### Qué problema resolvía
Nimbo necesita una IA para tres cosas: (1) traducir un mensaje ambiguo a un comando que los
detectores puedan reconocer, (2) redactar contenido para redes sociales, y (3) analizar
finanzas/estrategia del negocio y redactar recomendaciones. Usar solo una API en la nube
(Gemini, de Google) para todo esto tiene dos costos: dinero por cada llamada, y una
dependencia total de tener internet funcionando.

### Qué opciones había
1. **Solo Gemini** (API de pago, en la nube) para todo.
2. **Solo un modelo local** corriendo con Ollama (gratis, en la misma PC, sin internet)
   para todo.
3. **Gemini para lo rápido y frecuente** (chat diario) + **un modelo local aparte, más
   grande**, solo para los análisis largos (se probó con `gemma2:9b`).
4. **Un único modelo local** (`qwen2.5:7b`) para absolutamente todo.

### Por qué se eligió esta solución
Se terminó en la opción 4, pero se llegó ahí después de probar la opción 3 y encontrar un
problema serio: Ollama solo mantiene **un modelo cargado en memoria de forma eficiente a la
vez**. Alternar entre `qwen2.5:7b` (para el chat) y `gemma2:9b` (para los análisis) obligaba
a Ollama a descargar uno de la RAM y cargar el otro en CADA llamada - esa "penalidad de
recarga" por sí sola podía agotar el tiempo de espera (timeout). Y si en cambio se
mantenían los dos modelos cargados a la vez para evitar la recarga, sumaban ~11GB de RAM
combinados, lo que hizo que el servidor de Nimbo se cayera por presión de memoria durante
las pruebas.

Usar un único modelo para todo elimina ese problema de raíz: siempre está cargado, nunca
hay que intercambiarlo. Y usar Ollama (local) en vez de Gemini (nube) para todo evita el
costo por llamada y la dependencia de internet - a cambio de aceptar que, sin GPU, las
respuestas tardan más. Por eso los tiempos de espera se subieron de 60 segundos a 180s
(chat/traducción) y 300s (análisis largos), y se agregó un mensaje distinto para "está
procesando, tarda un poco" en vez de confundirlo con "está caído".

### Qué archivo(s) implementan la solución
- `services/ollama_service.py` - el único punto de entrada a Ollama en todo el proyecto:
  `llamar_ollama()`, `analizar_ollama()` y `ollama_disponible()`.
- `core/nimbo.py` - usa `llamar_ollama()` para traducir mensajes y para el fallback final.
- `tools/contabilidad_tool.py`, `tools/contenido_tool.py`, `tools/evento_tool.py` - usan
  `analizar_ollama()` para los análisis/contenido más largos.

### Ejemplo de código simplificado, explicado línea por línea

```python
import requests

TIMEOUT_SEGUNDOS = 180
MENSAJE_TIMEOUT = "Ollama esta procesando, esto puede tardar un momento..."

def llamar_ollama(prompt, modelo="qwen2.5:7b", timeout=TIMEOUT_SEGUNDOS):
    try:
        respuesta = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": modelo, "prompt": prompt, "stream": False},
            timeout=timeout
        )
        return respuesta.json().get("response")
    except requests.exceptions.Timeout:
        return MENSAJE_TIMEOUT
    except requests.exceptions.RequestException:
        return None
```

Línea por línea:
- `import requests`: librería para hacer peticiones HTTP (hablar con Ollama, que expone
  una API local en `http://localhost:11434`).
- `TIMEOUT_SEGUNDOS = 180`: cuántos segundos esperar como máximo antes de dar por perdida
  la respuesta. 180 en vez de los 60 originales, porque en esta PC (sin GPU) un prompt
  largo puede tardar más que eso.
- `MENSAJE_TIMEOUT = "..."`: el texto que se muestra cuando Ollama SÍ está corriendo pero
  tardó más de la cuenta - a propósito distinto del caso "Ollama no está corriendo", para
  no confundir al usuario.
- `def llamar_ollama(prompt, modelo="qwen2.5:7b", timeout=TIMEOUT_SEGUNDOS):` - la función
  recibe el texto a enviarle a la IA, qué modelo usar (siempre el mismo por defecto) y
  cuánto esperar.
- `try:` - todo lo que puede fallar (que Ollama no responda, que tarde demasiado) se
  intenta dentro de este bloque, para nunca dejar que el programa se caiga por esto.
- `respuesta = requests.post(...)` - envía la petición a Ollama:
  - `"http://localhost:11434/api/generate"` - la dirección local donde corre Ollama.
  - `json={"model": modelo, "prompt": prompt, "stream": False}` - qué modelo usar, qué
    preguntarle, y `stream=False` significa "dame toda la respuesta de una vez", no
    palabra por palabra.
  - `timeout=timeout` - si pasa este tiempo sin respuesta, Python lanza una excepción
    de timeout en vez de esperar para siempre.
- `return respuesta.json().get("response")` - saca el texto de la respuesta del JSON que
  devuelve Ollama.
- `except requests.exceptions.Timeout:` - si se agotó el tiempo de espera (Ollama está
  vivo pero lento), devuelve `MENSAJE_TIMEOUT` en vez de fallar en silencio.
- `except requests.exceptions.RequestException:` - cualquier otro error de conexión
  (Ollama no está corriendo, por ejemplo) devuelve `None`. Quien llama a esta función
  ya sabe distinguir "None" (no está corriendo) de "MENSAJE_TIMEOUT" (está corriendo
  pero tardó).

---

## 4. Cómo funciona el sistema de cancelación universal (cancelar en cualquier flujo)

### Qué problema resolvía
Nimbo tiene muchos "flujos conversacionales" de varios pasos: vender un producto, crear
una cotización, abrir caja, etc. En cada paso, Nimbo pregunta un dato y guarda en un
diccionario llamado `context` lo que ya sabe, hasta terminar el flujo.

Si a mitad de uno de estos flujos el usuario escribe "cancelar" (porque se arrepintió, o
se equivocó), sin ningún mecanismo especial ese mensaje se interpretaría como si fuera la
respuesta al paso actual. Por ejemplo, si Nimbo preguntó "¿nombre del cliente?" y el
usuario escribe "cancelar", el sistema literalmente crearía un cliente llamado "Cancelar".

Había un problema todavía más serio: el flujo de venta **ya descuenta el stock del
producto ANTES de que termine de preguntar cliente y método de pago** (para poder mostrar
el total de una vez). Si el usuario cancelaba a mitad de camino, ese stock quedaba
descontado sin que existiera ninguna venta real detrás - el inventario mentía.

### Qué opciones había
1. Agregar un chequeo de "¿el usuario escribió cancelar?" dentro de cada uno de los ~15
   flujos existentes, uno por uno.
2. Un único chequeo centralizado, al principio de la función que procesa cualquier
   mensaje entrante, que corre ANTES que cualquier flujo específico, y que sabe revertir
   los efectos secundarios que puedan haber quedado pendientes (como el stock).

### Por qué se eligió esta solución
Se eligió la opción 2. La opción 1 es propensa a errores humanos: bastaría con olvidar
agregar el chequeo en un flujo nuevo (o en uno de los ya existentes) para que ese flujo en
particular quedara con el bug, sin que nada avisara. Centralizarlo en un solo lugar
garantiza que TODO flujo -los que ya existen y los que se agreguen en el futuro- hereda la
cancelación gratis, sin tener que acordarse de escribirla cada vez.

### Qué archivo(s) implementan la solución
- `core/nimbo.py` - `_es_cancelacion()`, la lista `_PALABRAS_CANCELACION`, y el chequeo al
  principio de la función `send()` (el punto de entrada de cualquier mensaje del chat).

### Ejemplo de código simplificado, explicado línea por línea

```python
PALABRAS_CANCELACION = ["cancelar", "cancela", "salir", "olvida", "stop"]

def es_cancelacion(mensaje):
    texto = mensaje.lower().strip()
    return texto in PALABRAS_CANCELACION

def send(mensaje, context):
    # Este chequeo corre PRIMERO, antes de mirar en que flujo estamos
    if context.get("step") and es_cancelacion(mensaje):
        venta_ctx = context.get("venta_ctx")
        aviso = ""
        if venta_ctx and venta_ctx.get("producto_id"):
            reponer_stock(venta_ctx["producto_id"], venta_ctx["cantidad"])
            aviso = f" Se repuso el stock de {venta_ctx['producto']}."
        return f"De acuerdo, empecemos de nuevo.{aviso}", {}

    # A partir de aca sigue la logica normal de cada flujo especifico
    step = context.get("step")
    if step == "venta_waiting_nombre":
        ...
```

Línea por línea:
- `PALABRAS_CANCELACION = [...]`: la lista de palabras que, escritas a mitad de un flujo,
  significan "quiero salir de esto" en vez de "esta es mi respuesta".
- `def es_cancelacion(mensaje):` - función que responde sí/no a "¿este mensaje es una
  cancelación?".
- `texto = mensaje.lower().strip()` - normaliza el mensaje (minúsculas, sin espacios
  sobrantes) para comparar de forma consistente.
- `return texto in PALABRAS_CANCELACION` - verdadero si el texto completo es exactamente
  una de esas palabras.
- `def send(mensaje, context):` - la función que procesa CUALQUIER mensaje que llega al chat.
- `if context.get("step") and es_cancelacion(mensaje):` - dos condiciones: (1) que haya un
  flujo activo (`context` tiene un "step" guardado - sin flujo activo, "cancelar" sigue el
  camino normal de un comando cualquiera) Y (2) que el mensaje sea una cancelación. Esto
  corre ANTES que cualquier `if step == "..."` de un flujo específico, así ningún flujo
  llega a "atrapar" la palabra "cancelar" como si fuera su respuesta esperada.
- `venta_ctx = context.get("venta_ctx")` - si el flujo activo era una venta, ahí está
  guardado qué producto y cuánta cantidad ya se había descontado del stock.
- `if venta_ctx and venta_ctx.get("producto_id"):` - solo si efectivamente había una venta
  en curso con stock ya descontado.
- `reponer_stock(...)` - devuelve esa cantidad al inventario, deshaciendo el efecto
  secundario que había quedado a medias.
- `return f"...", {}` - responde confirmando la cancelación y devuelve un `context` vacío
  (`{}`) - "sin flujo activo", listo para el siguiente mensaje del usuario.

---

## 5. Por qué el mapa de intención va de detectores → action_engine → tools

### Qué problema resolvía
Cada mensaje del chat necesita pasar por tres pasos distintos: (1) reconocer QUÉ quiere
hacer el usuario, (2) verificar SI tiene permiso para hacerlo (un empleado no puede ver
contabilidad, un técnico solo ve servicio técnico), y (3) EJECUTAR la acción real. Había
que decidir si estas tres responsabilidades vivían todas juntas en una sola función gigante,
o separadas en piezas independientes.

### Qué opciones había
1. Una sola función que reconoce el texto, chequea el rol, y ejecuta la acción, todo
   mezclado en el mismo bloque de código.
2. Tres capas separadas, cada una con una sola responsabilidad:
   - **Detectores** (`core/detectors/`): reconocen texto → devuelven un "intent" (un
     nombre como `"venta.registrar"`) más los datos ya extraídos.
   - **ActionEngine** (`core/action_engine.py`): recibe el intent, decide si el rol del
     usuario tiene permiso para esa categoría.
   - **Tools** (`tools/`): reciben los datos y ejecutan la acción real (descontar stock,
     guardar en la base de datos, etc.).

### Por qué se eligió esta solución
Con las capas separadas (opción 2), cada pieza se puede cambiar sin tocar las otras:
agregar un detector nuevo no requiere tocar el código de permisos ni el de las tools;
agregar una categoría nueva que sea solo-admin no requiere tocar ningún detector; y se
puede probar cada capa por separado (por ejemplo, verificar que un detector reconoce un
texto sin tener que ejecutar de verdad la tool que descuenta stock). Es el mismo principio
de "una responsabilidad por pieza" que hace más fácil entender y modificar el código con
el tiempo, sobre todo en un proyecto que ya tiene más de 20 categorías de comandos.

### Qué archivo(s) implementan la solución
- `core/detectors/*.py` - reconocen texto.
- `core/intent_detector.py` - prueba cada detector en orden.
- `core/action_engine.py` - valida el rol y llama a la tool correcta.
- `core/tool_registry.py` - el directorio de todas las tools disponibles.
- `tools/*.py` - ejecutan la acción real.

### Ejemplo de código simplificado, explicado línea por línea

```python
CATEGORIAS_EMPLEADO = {"inventory", "venta", "cliente", "caja"}
MENSAJE_SIN_PERMISO = "No tienes permiso para realizar esa accion."

class ActionEngine:

    def __init__(self):
        self.detector = IntentDetector()

    def execute(self, mensaje, rol="admin"):
        resultado = self.detector.detect(mensaje)
        if resultado is None:
            return None

        categoria = resultado["intent"].split(".")[0]
        if rol != "admin" and categoria not in CATEGORIAS_EMPLEADO:
            return MENSAJE_SIN_PERMISO

        tool = TOOLS.get(resultado["intent"])
        if tool:
            return tool(resultado)
        return None
```

Línea por línea:
- `CATEGORIAS_EMPLEADO = {...}` - un conjunto (set) con los nombres de categoría que un
  empleado (no-admin) sí puede usar.
- `MENSAJE_SIN_PERMISO = "..."` - el mensaje que se muestra cuando el rol no tiene acceso.
- `class ActionEngine:` - la clase que orquesta todo.
- `def __init__(self):` - al crear un `ActionEngine`, también crea su propio
  `IntentDetector` (la capa de detectores).
- `def execute(self, mensaje, rol="admin"):` - el método principal: recibe el mensaje del
  usuario y su rol (admin por defecto).
- `resultado = self.detector.detect(mensaje)` - le pasa el mensaje al detector de
  intenciones, que prueba cada detector de `core/detectors/` en orden.
- `if resultado is None: return None` - si ningún detector reconoció el mensaje, no hay
  nada más que hacer aquí (el mensaje seguirá su camino hacia Ollama, ver decisión #1).
- `categoria = resultado["intent"].split(".")[0]` - el intent viene con forma
  `"categoria.accion"` (ej. `"venta.registrar"`); `.split(".")[0]` se queda solo con la
  parte antes del punto: `"venta"`.
- `if rol != "admin" and categoria not in CATEGORIAS_EMPLEADO:` - si el usuario NO es
  admin Y su rol no tiene permitida esta categoría, se corta aquí.
- `return MENSAJE_SIN_PERMISO` - no se llega a ejecutar ninguna tool.
- `tool = TOOLS.get(resultado["intent"])` - busca, en el directorio global de tools, la
  función registrada bajo ese nombre exacto de intent (ej. `"venta.registrar"`).
- `if tool: return tool(resultado)` - si existe, la ejecuta pasándole los datos ya
  extraídos por el detector, y devuelve lo que la tool responda.
- `return None` - si por alguna razón no hay ninguna tool registrada con ese nombre.

---

## 6. Cómo funciona el sistema de rutas relativas para que Nimbo corra en cualquier PC

### Qué problema resolvía
Nimbo necesita saber en qué carpeta está `nimbo.db`, dónde guardar las fotos subidas, dónde
dejar los backups, etc. Si esas rutas estuvieran escritas a mano como texto fijo (por
ejemplo `"/home/victor/nimbo.exe/nimbo.db"`), el proyecto dejaría de funcionar apenas se
copiara a otra PC, a otro usuario, o incluso a otra carpeta en la misma PC.

### Qué opciones había
1. **Rutas absolutas escritas a mano** en el código (`"/home/victor/nimbo.exe/..."`).
2. **Variables de entorno** para cada ruta, que alguien tiene que configurar a mano en
   cada instalación nueva.
3. **Calcular la ruta de forma relativa a la ubicación del propio archivo de código**,
   usando la variable especial `__file__` (que Python llena automáticamente con la ruta
   del archivo que se está ejecutando) para subir la cantidad justa de carpetas hasta
   llegar a la raíz del proyecto.

### Por qué se eligió esta solución
Para todo lo que vive DENTRO del propio proyecto (`nimbo.db`, la carpeta `static/`, los
backups), se eligió la opción 3: no depende de que alguien recuerde configurar una
variable de entorno correctamente en cada PC nueva - simplemente funciona, sin importar en
qué carpeta se clone o mueva el proyecto, porque la ruta se calcula en el momento a partir
de dónde está el propio archivo `.py`.

Para lo que NO vive dentro del proyecto - la base de datos de Aronium, que puede estar en
cualquier lado del disco de Windows según cómo esté instalado ese programa - sí se usa una
variable de entorno (`ARONIUM_DB_PATH`), porque ahí no hay forma de "calcular" la ruta: es
información externa que depende de cada instalación.

### Qué archivo(s) implementan la solución
- `app.py`, `core/auth.py`, `core/configuracion.py`, `database/nimbo_db.py` y varios
  `services/*.py` - cada uno calcula su propio `BASE_DIR` al principio del archivo.

### Ejemplo de código simplificado, explicado línea por línea

```python
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NIMBO_DB = os.path.join(BASE_DIR, "nimbo.db")
```

Este código vive, por ejemplo, en `database/nimbo_db.py`. Línea por línea:
- `import os`: módulo estándar de Python para trabajar con rutas de archivos y del sistema
  operativo.
- `os.path.abspath(__file__)`: `__file__` es una variable que Python llena solo con la
  ruta del archivo actual (ej. `/home/victor/nimbo.exe/database/nimbo_db.py`).
  `abspath()` se asegura de que sea una ruta completa (absoluta), no relativa.
- `os.path.dirname(...)`: sube UN nivel, quedándose con la carpeta que contiene el
  archivo. Aplicado una vez: `/home/victor/nimbo.exe/database`.
- `os.path.dirname(os.path.dirname(...))`: se aplica una SEGUNDA vez, subiendo otro nivel
  más: `/home/victor/nimbo.exe` - la raíz del proyecto. (Se aplica dos veces porque este
  archivo en particular vive un nivel más adentro, dentro de la carpeta `database/`; un
  archivo directamente en la raíz, como `app.py`, solo necesita subir un nivel, es decir,
  llamar a `dirname()` una sola vez.)
- `BASE_DIR = ...`: guarda esa ruta calculada en una variable, para reusarla.
- `NIMBO_DB = os.path.join(BASE_DIR, "nimbo.db")`: arma la ruta completa a la base de
  datos, uniendo `BASE_DIR` con el nombre del archivo. `os.path.join()` se encarga de
  poner la barra (`/` o `\`) correcta según el sistema operativo, en vez de escribirla a
  mano.

Gracias a esto, si alguien clona el proyecto Nimbo en otra PC, en otra carpeta, o con otro
nombre de usuario, `BASE_DIR` se recalcula solo y todo sigue funcionando sin tocar una
sola línea de configuración.

---

## 7. Por qué se usó Flask y no Django u otro framework

### Qué problema resolvía
Había que elegir con qué framework de Python construir el servidor web: las rutas del
dashboard, la API que usa el chat, el login, etc.

### Qué opciones había
- **Django**: un framework "con baterías incluidas" - trae su propio ORM (una capa que
  traduce clases de Python a tablas de base de datos), un panel de administración
  automático, un sistema de autenticación completo, y un generador de migraciones.
- **Flask**: un "microframework" - solo trae el servidor web y el enrutamiento (decidir
  qué función atiende cada URL). Todo lo demás (base de datos, login, envío de correo) se
  agrega como piezas sueltas, eligiendo cada una por separado.

### Por qué se eligió esta solución
Se eligió Flask por tres razones concretas de este proyecto en particular:

1. **La base de datos ya tenía dueño y forma propia.** Nimbo convive con Aronium, un
   programa de terceros con su propio esquema de base de datos, con particularidades que
   no siguen las convenciones que un ORM como el de Django esperaría (ver decisión #2).
   El ORM de Django hubiera sido más un obstáculo que una ayuda; Flask no impone ningún
   ORM, así que Nimbo usa `sqlite3` directo, con control total sobre cada consulta.
2. **No hace falta un panel de administración genérico.** La interfaz real del negocio es
   el dashboard hecho a medida (`templates/index.html`) y el chat en español - no un CRUD
   automático como el que genera Django admin.
3. **El proyecto creció módulo por módulo, no de una vez.** Nimbo empezó pequeño y fue
   agregando funcionalidades con el tiempo (cotizaciones, garantías, cuentas por cobrar,
   programa de lealtad...). Con Flask, agregar una funcionalidad nueva es escribir una
   función y decorarla con una ruta; con Django hubiera significado crear una "app" nueva,
   sus modelos, sus migraciones y registrarla en el proyecto - más ceremonia para un
   equipo de un solo desarrollador iterando rápido.

El costo de esta decisión es honesto: Django hubiera dado más funcionalidad "gratis" (auth,
admin, migraciones) si el proyecto hubiera sabido desde el día uno todo lo que iba a
necesitar. Pero Nimbo no arrancó así - y la flexibilidad de Flask (agregar piezas sueltas
solo cuando hacen falta) encajó mejor con esa forma orgánica de crecer.

### Qué archivo(s) implementan la solución
- `app.py` - toda la aplicación Flask: rutas, configuración, arranque del servidor.
- Piezas sueltas agregadas encima: Flask-Login (`core/auth.py`), Flask-Mail
  (`services/mail_service.py`), Flask-CORS.

### Ejemplo de código simplificado, explicado línea por línea

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/api/status")
def status():
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=5000, debug=True)
```

Línea por línea:
- `from flask import Flask, jsonify`: importa la clase principal de Flask y una función
  para convertir un diccionario de Python en una respuesta JSON.
- `app = Flask(__name__)`: crea la aplicación. `__name__` le dice a Flask "en qué archivo
  está definida esta app", para que sepa dónde buscar, por ejemplo, la carpeta `static/`.
- `@app.route("/api/status")`: un **decorador** - lo que sigue justo debajo (la función
  `status`) queda registrado para atender peticiones a la URL `/api/status`. Esta única
  línea es todo lo que Flask exige para "crear una ruta nueva" - no hay que crear ninguna
  clase, archivo de configuración, ni registrar nada en otro lado.
- `def status():`: la función que se ejecuta cuando alguien visita esa URL.
- `return jsonify({"ok": True})`: convierte el diccionario en una respuesta JSON válida
  (con el `Content-Type` correcto) y la devuelve al navegador o a quien haya hecho la
  petición.
- `if __name__ == "__main__":`: solo se ejecuta si este archivo se corrió directamente
  (con `python app.py`), no si se importó desde otro archivo.
- `app.run(port=5000, debug=True)`: arranca el servidor web en el puerto 5000.
  `debug=True` hace que Flask reinicie solo cuando detecta un cambio en el código, y
  muestre errores detallados en el navegador durante el desarrollo.

---

## 8. Cómo funciona el flujo de una venta de principio a fin

### Qué problema resolvía
Vender un producto por chat necesita varios datos (producto, cantidad, cliente, método de
pago) que no siempre vienen todos juntos en un solo mensaje. Había que diseñar un flujo
que pudiera arrancar con la info mínima ("vendí 2 licuadoras") y fuera preguntando el
resto paso a paso, sin perder lo que ya se sabía entre un mensaje y el siguiente (recordar
que Flask, y HTTP en general, no "recuerda" nada entre una petición y la siguiente por sí
solo - por eso hace falta guardar el estado en algún lado: el diccionario `context`).

### Qué opciones había
No es una decisión de "A vs B" como las anteriores, sino una arquitectura que combina
varias de las decisiones ya explicadas en este documento. Vale la pena trazarla completa
porque es el recorrido más largo y más usado de todo Nimbo.

### Por qué se eligió esta solución
Reusar el mismo mecanismo de `context` (un diccionario que viaja de mensaje en mensaje,
guardando el "step" o paso actual y los datos ya recolectados) para TODOS los flujos
conversacionales del chat, en vez de inventar un mecanismo distinto para cada uno. Así,
vender un producto, crear una cotización o abrir caja funcionan todos con la misma lógica
de fondo, y heredan gratis cosas como la cancelación universal (decisión #4).

### Qué archivo(s) implementan la solución
- `core/detectors/venta_detector.py` - reconoce "vendí 2 licuadoras".
- `core/action_engine.py` - valida que el rol (admin o empleado) pueda vender.
- `tools/venta_tool.py` - busca el producto, valida stock, lo descuenta, y arranca el flujo.
- `core/nimbo.py` - los pasos `venta_waiting_nombre`, `venta_waiting_pago`, etc., y
  `_registrar_venta_chat()` al final.
- `database/nimbo_db.py` - `remove_stock()`, `calcular_descuento()`,
  `calcular_ajuste_puntos()`, `generar_garantia_venta()`.

### El recorrido completo, paso a paso

1. **El usuario escribe**: `"vendi 2 licuadoras"`.
2. **`VentaDetector`** (decisión #1) reconoce el patrón y devuelve
   `{"intent": "venta.registrar", "cantidad": 2, "query": "licuadoras"}`.
3. **`ActionEngine`** (decisión #5) ve que la categoría es `"venta"`, que sí está
   permitida para el rol `empleado`, y ejecuta la tool `venta.registrar`.
4. **`tools/venta_tool.py` → `registrar_venta_tool()`**: busca el producto con
   `get_products("licuadoras")`. Si encuentra un único resultado, valida que haya stock
   suficiente, y **ya descuenta el stock ahí mismo** con `remove_stock()` - antes incluso
   de saber quién es el cliente o cómo va a pagar. Devuelve un texto especial:
   `"VENTA_INICIO:2|Licuadora Oster|350.0|700.0|17"` (cantidad, nombre, precio unitario,
   total, id del producto).
5. **`core/nimbo.py`** reconoce el prefijo `VENTA_INICIO:`, separa esos datos, los guarda
   en `context["venta_ctx"]`, cambia `context["step"]` a `"venta_waiting_nombre"`, y le
   responde al usuario: *"Venta: 2x Licuadora Oster = Q700. Nombre del cliente (o 'sin
   nombre'):"*.
6. **El usuario responde** con un nombre. Si es un cliente que ya existe y tiene 100+
   puntos de lealtad acumulados, se le pregunta primero si quiere canjearlos
   (`venta_waiting_canjear_puntos`); si es nuevo, se le pide teléfono y NIT.
7. Finalmente llega al paso **`venta_waiting_pago`**: el usuario responde, por ejemplo,
   `"efectivo"`. Aquí Nimbo:
   - valida que sea un método reconocido (efectivo, tarjeta, transferencia, mixto o crédito),
   - calcula si aplica algún **descuento** (`calcular_descuento()`),
   - calcula el ajuste por **puntos ya canjeados** (`calcular_ajuste_puntos()`),
   - y llama a **`_registrar_venta_chat()`**.
8. **`_registrar_venta_chat()`** inserta la fila en la tabla `Venta`, actualiza la fecha de
   última compra del cliente, y genera la **garantía** del producto vendido
   (`generar_garantia_venta()`).
9. Nimbo responde con el resumen final: total cobrado, puntos ganados, número de garantía
   generado, y limpia el `context` (`{}`) - el flujo terminó, el próximo mensaje empieza
   de cero.

Este mismo recorrido es la razón por la que existe la **cancelación universal** (decisión
#4): como el stock ya se descontó en el paso 4, mucho antes de que el flujo termine, si el
usuario escribe "cancelar" en cualquier punto entre el paso 5 y el 8, Nimbo necesita
reponer ese stock - si no lo hiciera, el inventario quedaría descontado sin ninguna venta
real detrás.

### Ejemplo de código simplificado, explicado línea por línea

```python
def registrar_venta_tool(data):
    cantidad = data["cantidad"]
    productos = buscar_productos(data["query"])
    p = productos[0]
    total = p["Precio"] * cantidad

    if p["Stock"] < cantidad:
        return f"Stock insuficiente. {p['Nombre']} solo tiene {p['Stock']} unidades."

    descontar_stock(p["Id"], cantidad)  # se descuenta ANTES de saber cliente/pago

    return f"VENTA_INICIO:{cantidad}|{p['Nombre']}|{p['Precio']}|{total}|{p['Id']}"
```

Línea por línea:
- `def registrar_venta_tool(data):` - la tool que `ActionEngine` ejecuta cuando el intent
  es `"venta.registrar"`. `data` es el diccionario que armó el detector (`cantidad`, `query`).
- `cantidad = data["cantidad"]` - cuántas unidades pidió el usuario.
- `productos = buscar_productos(data["query"])` - busca el producto por nombre (con
  tolerancia a errores de tipeo, ver `CLAUDE.md` sección de búsqueda difusa).
- `p = productos[0]` - toma el primer resultado (en el código real, si hay varios
  resultados parecidos, en vez de esto se le muestra una lista al usuario para que elija).
- `total = p["Precio"] * cantidad` - calcula el total de la venta.
- `if p["Stock"] < cantidad:` - si no hay stock suficiente, se corta aquí.
- `return f"Stock insuficiente...` - devuelve el aviso, sin tocar nada más.
- `descontar_stock(p["Id"], cantidad)` - **este es el paso clave**: el stock se descuenta
  ACÁ, antes de que exista ningún registro de "Venta" en la base de datos todavía. Por eso
  hace falta la cancelación universal (decisión #4): si el flujo se corta después de esta
  línea y antes de terminar, hay que acordarse de deshacer esto.
- `return f"VENTA_INICIO:...` - devuelve un texto especial con un prefijo reconocible
  (`VENTA_INICIO:`) seguido de los datos separados por `|`. `core/nimbo.py` reconoce ese
  prefijo y arranca el resto del flujo de varios pasos (pedir cliente, pedir método de
  pago) a partir de esos datos.

---

## 9. Por qué se eliminó el código huérfano en vez de conectarlo o dejarlo como estaba

### Qué problema resolvía
Al construir `mapa_nimbo.html` (un mapa visual de qué archivo importa a cuál) se
descubrieron 19 archivos que existían, se cargaban al arrancar el servidor e incluso se
registraban correctamente (`tools/budget_tool.py` y otros quedaban en `TOOLS{}`, listos
para ejecutarse) - pero a los que ningún mensaje real de un usuario podía llegar nunca,
porque sus detectores nunca se importaron en `core/intent_detector.py` (a diferencia de
`tools/`, la carpeta `core/detectors/` no se carga automático por convención de carpeta -
cada detector se agrega a mano en una lista, y estos 3 nunca se agregaron ahí). Sumado a
eso, había 7 archivos completamente vacíos (0 líneas), inicios nunca terminados de
módulos en inglés que duplicaban funcionalidad ya existente en español. Había que decidir
qué hacer con todo ese código: quedaba código de verdad en el repositorio que nadie podía
usar, y que además podía confundir a futuro a cualquiera (incluida una IA asistente) que
lo leyera pensando que SÍ estaba en uso.

### Qué opciones había
1. **Dejarlo tal cual estaba**, documentando en `CLAUDE.md`/`BUGS_Y_FIXES.md` que estaba
   huérfano, para no arriesgar borrar algo que en el futuro se quisiera retomar.
2. **Terminar de conectarlo**: agregar los 3 detectores faltantes a
   `core/intent_detector.py` y escribir el código que faltaba en los 7 archivos vacíos,
   para que las funcionalidades (presupuestos, clientes en inglés, abrir apps de
   Windows, ventas/facturas en inglés) quedaran completas y utilizables.
3. **Eliminarlo por completo**, después de verificar rigurosamente que ningún otro
   archivo dependía de él.

### Por qué se eligió esta solución
Se eligió la opción 3 (eliminar) por varias razones concretas:

- **Duplicaba funcionalidad ya construida y en uso.** `customer_tool.py`/
  `customer_detector.py` volvían a hacer, en inglés, exactamente lo que ya hacían
  `cliente_tool.py`/`cliente_detector.py` en español - terminarlos de conectar hubiera
  significado mantener DOS caminos para lo mismo, con el riesgo de que un día
  respondieran distinto ante el mismo tipo de mensaje.
- **No encajaba con el resto del proyecto.** `windows_tool.py` (abrir el Bloc de notas de
  Windows) no tiene relación con ninguna operación real de la tienda - conectarlo no
  resolvía ningún problema de negocio, solo agregaba superficie de código para mantener.
- **El costo de "dejarlo como estaba" crece con el tiempo.** Cada archivo huérfano que se
  deja "por si acaso" es una trampa para el próximo cambio: alguien (persona o IA) puede
  leerlo, asumir que está en uso, y perder tiempo modificándolo o razonando sobre un
  comportamiento que en realidad nunca se ejecuta.
- **Se verificó a fondo antes de borrar, así que el riesgo real era bajo.** No fue un
  borrado a ciegas: se corrió un análisis con el módulo `ast` de Python (lee el código
  real, no solo busca texto como `grep`) que confirmó que ninguno de los 19 archivos
  tenía un importador fuera del propio grupo a eliminar - incluyendo las dependencias
  ENTRE ellos mismos (`tools/budget_tool.py` importaba `core/event_bus.py` y
  `core/workspace.py`, pero como los tres estaban en la lista de borrado, no queda
  ninguna referencia rota). Se usó `git rm` (no borrado directo del disco), así que el
  código sigue disponible en el historial de git si alguna vez hace falta recuperarlo.

### Qué archivo(s) implementan la solución
Los 19 archivos eliminados están listados completos, con el motivo específico de cada
uno, en `BUGS_Y_FIXES.md` (sección "Limpieza de código huérfano"). El script de análisis
de imports (basado en `ast`) es el mismo que genera los datos de `mapa_nimbo.html`.

### Ejemplo de código simplificado, explicado línea por línea

```python
import ast, os

def encuentra_importadores_externos(archivo_a_borrar, todos_los_archivos, grupo_a_borrar):
    importadores = []
    for otro_archivo in todos_los_archivos:
        if otro_archivo in grupo_a_borrar:
            continue  # un import DENTRO del propio grupo no cuenta como "externo"
        codigo = open(otro_archivo, encoding="utf-8").read()
        arbol = ast.parse(codigo)
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and nodo.module == archivo_a_borrar:
                importadores.append(otro_archivo)
    return importadores
```

Línea por línea:
- `import ast, os`: `ast` (Abstract Syntax Tree, "árbol de sintaxis abstracta") es el
  módulo que trae Python para LEER su propio código como una estructura de datos, en vez
  de tratarlo como texto plano - por eso es más confiable que buscar la palabra "import"
  con `grep`, que podría confundirse con un comentario o un string que menciona esa
  palabra sin ser un import real.
- `def encuentra_importadores_externos(...)`: recibe el archivo que se quiere borrar, la
  lista de todos los archivos del proyecto, y el grupo completo que se piensa borrar
  junto (para poder ignorar los imports internos entre ellos).
- `importadores = []`: aquí se va a acumular la lista de archivos que sí lo necesitan.
- `for otro_archivo in todos_los_archivos:`: revisa cada archivo del proyecto, uno por
  uno.
- `if otro_archivo in grupo_a_borrar: continue`: si ese archivo TAMBIÉN se va a borrar,
  no cuenta como un importador "externo" - se salta al siguiente sin revisarlo.
- `codigo = open(otro_archivo, ...).read()`: lee el contenido del archivo como texto.
- `arbol = ast.parse(codigo)`: convierte ese texto en un árbol de sintaxis - una
  estructura que Python puede recorrer nodo por nodo, entendiendo qué es una función, qué
  es un import, qué es un comentario, etc.
- `for nodo in ast.walk(arbol):`: recorre TODOS los nodos del árbol (cada línea, cada
  expresión) uno por uno.
- `if isinstance(nodo, ast.ImportFrom) and nodo.module == archivo_a_borrar:`: pregunta
  "¿este nodo es específicamente un `from ALGO import ALGO`? ¿Y ese ALGO es el archivo
  que quiero borrar?".
- `importadores.append(otro_archivo)`: si sí, anota que ESTE archivo depende del que se
  quiere borrar.
- `return importadores`: al final, devuelve la lista completa. Si la lista viene vacía
  para los 19 archivos, es seguro borrarlos.

---

## Nota final

Los ejemplos de código de este documento están **simplificados** a propósito para que se
entiendan sin tener que leer archivos de miles de líneas. El código real en
`core/nimbo.py`, `database/nimbo_db.py` y el resto de archivos mencionados tiene más
validaciones, más casos especiales, y más comentarios explicando decisiones puntuales -
pero la lógica central de cada decisión es la que está documentada aquí.
