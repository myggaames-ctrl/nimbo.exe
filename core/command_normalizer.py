"""
Command Normalizer
Nimbo AI
"""
import difflib
import unicodedata


def _sin_acentos(texto: str) -> str:
    return unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode("utf-8")


# Vocabulario de referencia (correctamente escrito, sin acentos) usado para corregir
# errores tipograficos por similitud de cadenas. Cubre los verbos/sustantivos mas
# frecuentes en los comandos de Nimbo y los electrodomesticos/repuestos tipicos de
# la tienda, para que un error de tipeo no le impida a un detector reconocer el mensaje.
VOCABULARIO = [
    # verbos / acciones
    "busca", "buscar", "agrega", "agregar", "quita", "quitar", "elimina", "eliminar",
    "cambia", "cambiar", "crear", "registra", "registrar", "vende", "vendi", "vendio", "vender",
    "cotiza", "cotizar", "genera", "generar", "actualiza", "actualizar", "muestra",
    "mostrar", "listar", "abrir", "cerrar", "retirar", "cobrar", "sugerir", "sugiere",
    "canjear", "canjea", "canje",
    # sustantivos generales del negocio
    "producto", "productos", "inventario", "precio", "costo", "cliente", "clientes",
    "venta", "ventas", "factura", "gasto", "gastos", "balance", "proveedor", "proveedores",
    "orden", "ordenes", "servicio", "reparacion", "garantia", "garantias", "fabrica", "stock", "existencias",
    "margen", "ganancia", "reporte", "descripcion", "cotizacion",
    "caja", "turno", "efectivo", "tarjeta", "denominacion", "denominaciones", "cambio",
    "billete", "billetes", "moneda", "monedas", "carrito", "ticket", "sencillo",
    "descuento", "descuentos", "temporada", "porciento",
    "nuestra", "nuestro", "propia", "propio", "combo", "combos", "kit", "kits",
    "docena", "docenas", "cajas", "par", "pares", "paquete", "paquetes",
    "trio", "trios", "cuarteto", "cuartetos", "vienen", "unidad", "unidades",
    "puntos", "punto", "disponibles", "nivel", "niveles", "bronce", "plata", "lealtad",
    "codigo", "codigos", "barras", "etiqueta", "etiquetas", "imprimir",
    "mano", "obra", "presupuesto", "tecnico", "tecnicos", "informe", "informes",
    "tarifa", "tarifas", "aprobo", "rechazo", "asigna", "asignada", "asignado",
    "necesita", "revision",
    "debe", "debo", "pago", "pagos", "abono", "abonos", "cobrar", "cobro",
    "deuda", "deudas", "vencida", "vencidas", "pendiente", "pendientes",
    "credito", "enganche", "fiado",
    # electrodomesticos y repuestos comunes en la tienda
    "licuadora", "licuadoras", "refrigerador", "refrigeradores", "cuchilla", "cuchillas",
    "empaque", "empaques", "adaptador", "adaptadores", "regulador", "reguladores",
    "tambo", "tambos", "gas", "plancha", "planchas", "cafetera", "cafeteras",
    "olla", "ollas", "horno", "hornos", "microondas", "batidora", "batidoras",
    "extractor", "extractores", "ventilador", "ventiladores", "congelador", "congeladores",
    "lavadora", "lavadoras", "secadora", "secadoras", "estufa", "estufas", "cocina",
    "abanico", "abanicos", "resistencia", "resistencias", "motor", "motores",
]

# Correcciones directas para errores muy comunes (garantiza el resultado sin depender
# del umbral de similitud, que a veces falla con palabras muy cortas o muy distintas
# en longitud a la palabra correcta).
CORRECCIONES_DIRECTAS = {
    "cuchila": "cuchilla",
    "cuchilas": "cuchillas",
    "licuadra": "licuadora",
    "licuadras": "licuadoras",
    "refridgerador": "refrigerador",
    "refrijerador": "refrigerador",
    "refrigirador": "refrigerador",
    "empaqe": "empaque",
    "empake": "empaque",
    "vusca": "busca",
    "vuscar": "buscar",
}

UMBRAL_SIMILITUD = 0.8
LONGITUD_MINIMA = 4


def _separar_puntuacion(palabra: str):
    inicio, fin = 0, len(palabra)
    while inicio < fin and not palabra[inicio].isalnum():
        inicio += 1
    while fin > inicio and not palabra[fin - 1].isalnum():
        fin -= 1
    return palabra[:inicio], palabra[inicio:fin], palabra[fin:]


def _corregir_palabra(palabra: str) -> str:
    prefijo, core, sufijo = _separar_puntuacion(palabra)
    if not core:
        return palabra

    # El texto ya llega en minuscula (ver normalize()); solo falta quitar acentos
    # para comparar de forma consistente contra el vocabulario y el diccionario.
    limpia = _sin_acentos(core)

    if limpia in CORRECCIONES_DIRECTAS:
        return prefijo + CORRECCIONES_DIRECTAS[limpia] + sufijo

    if limpia in VOCABULARIO:
        return palabra

    if len(limpia) < LONGITUD_MINIMA or not limpia.isalpha():
        return palabra

    match = difflib.get_close_matches(limpia, VOCABULARIO, n=1, cutoff=UMBRAL_SIMILITUD)
    if match:
        return prefijo + match[0] + sufijo

    return palabra


def corregir_texto(texto: str) -> str:
    """Corrige errores tipograficos comunes palabra por palabra. No toca numeros,
    precios ni codigos de producto (se conservan tal cual)."""
    if not texto:
        return texto
    return " ".join(_corregir_palabra(p) for p in texto.split(" "))


class CommandNormalizer:

    def normalize(self, text: str):

        text = text.lower().strip()
        text = _sin_acentos(text)
        text = corregir_texto(text)

        replacements = {

            # ----------------------------
            # CLIENTES
            # ----------------------------

            "agrega cliente ": "crear cliente ",
            "agregar cliente ": "crear cliente ",
            "anade cliente ": "crear cliente ",
            "nuevo cliente ": "crear cliente ",
            "registra cliente ": "crear cliente ",
            "registrar cliente ": "crear cliente ",

            # ----------------------------
            # INVENTARIO
            # ----------------------------

            "busca ": "buscar ",
            "buscame ": "buscar ",
            "encuentra ": "buscar ",

            # ----------------------------
            # PRODUCTOS
            # ----------------------------

            "lista productos": "listar productos",
            "muestra productos": "mostrar productos",
            "ensename productos": "mostrar productos",

        }

        for old, new in replacements.items():

            if text.startswith(old):

                text = new + text[len(old):]

                break

        return text
