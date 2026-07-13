import re
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()


# Palabras de unidad de medida reconocidas para VENDER (no para configurar - ahi
# se acepta cualquier palabra). Si se configura una unidad con un nombre que no
# esta aqui, hay que agregarla a esta lista para que "vendi N [unidad] de X" la
# reconozca (si no, el mensaje cae al detector de venta normal).
UNIDADES_RECONOCIDAS = r"docenas?|cajas?|pares?|paquetes?|trios?|cuartetos?"


class UnidadMedidaDetector:

    PATTERNS_LISTAR = [
        r"^ver\s+unidades\s+de\s+medida$",
        r"^unidades\s+de\s+medida$",
        r"^listar\s+unidades\s+de\s+medida$",
    ]

    # Debe revisarse antes que PATTERNS_CONFIG_CANTIDAD: ambos empiezan igual
    # ("X se vende por unidad de N"), pero este exige ademas "unidades precio QP".
    PATTERNS_CONFIG_PRECIO = [
        r"^(.+?)\s+se\s+vende(?:n)?\s+por\s+(\w+)\s+(\d+)\s+unidades?\s+precio\s+q?\s*(\d+(?:\.\d+)?)$",
    ]

    PATTERNS_CONFIG_CANTIDAD = [
        r"^(.+?)\s+se\s+vende(?:n)?\s+por\s+(\w+)\s+de\s+(\d+)$",
        r"^(.+?)\s+vienen?\s+en\s+(\w+)\s+de\s+(\d+)$",
    ]

    PATTERNS_CONFIG_SIMPLE = [
        r"^(.+?)\s+se\s+vende(?:n)?\s+por\s+(\w+)$",
        r"^(.+?)\s+vienen?\s+en\s+(\w+)$",
    ]

    PATTERNS_VENDER = [
        rf"^vend[io]+\s+(\d+)\s+({UNIDADES_RECONOCIDAS})\s+(?:de\s+)?(.+)$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_LISTAR:
            if re.search(pattern, text):
                return {"intent": "unidadmedida.listar"}

        for pattern in self.PATTERNS_VENDER:
            match = re.search(pattern, text)
            if match:
                cantidad, unidad, producto = match.groups()
                return {
                    "intent": "unidadmedida.vender",
                    "cantidad_medida": int(cantidad),
                    "unidad": unidad.strip(),
                    "producto_query": producto.strip()
                }

        for pattern in self.PATTERNS_CONFIG_PRECIO:
            match = re.search(pattern, text)
            if match:
                producto, unidad, cantidad, precio = match.groups()
                return {
                    "intent": "unidadmedida.configurar",
                    "producto_query": producto.strip(),
                    "unidad": unidad.strip(),
                    "cantidad_por_unidad": int(cantidad),
                    "precio_por_unidad": float(precio)
                }

        for pattern in self.PATTERNS_CONFIG_CANTIDAD:
            match = re.search(pattern, text)
            if match:
                producto, unidad, cantidad = match.groups()
                return {
                    "intent": "unidadmedida.configurar",
                    "producto_query": producto.strip(),
                    "unidad": unidad.strip(),
                    "cantidad_por_unidad": int(cantidad),
                    "precio_por_unidad": None
                }

        for pattern in self.PATTERNS_CONFIG_SIMPLE:
            match = re.search(pattern, text)
            if match:
                producto, unidad = match.groups()
                return {
                    "intent": "unidadmedida.configurar",
                    "producto_query": producto.strip(),
                    "unidad": unidad.strip(),
                    "cantidad_por_unidad": None,
                    "precio_por_unidad": None
                }

        return None
