import re
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()


class GarantiaDetector:

    PATTERNS_POR_VENCER = [
        r"^garantias?\s+por\s+vencer$",
        r"^garantias?\s+(?:que\s+)?vencen\s+pronto$",
        r"^que\s+garantias?\s+(?:hay\s+)?por\s+vencer$",
    ]

    PATTERNS_VER = [
        r"^ver\s+garantia\s+(?:gar[- ]?)?(\w+)$",
        r"^garantia\s+(?:gar[- ]?)?(\d+)$",
        r"^estado\s+de\s+(?:la\s+)?garantia\s+(?:gar[- ]?)?(\w+)$",
    ]

    # Debe revisarse antes que PATTERNS_SIMPLE: ambos empiezan igual ("garantia
    # de X es N dias"), pero este exige ademas "... fabrica y M dias nuestra".
    PATTERNS_DOBLE = [
        r"^garantia(?:s)?\s+(?:de\s+|del\s+)?(.+?)\s+es\s+(\d+)\s+dias?\s+f[ae]brica\s+y\s+(\d+)\s+dias?\s+(?:nuestra|nuestro|propia|propio|de\s+la\s+tienda)$",
    ]

    PATTERNS_SIMPLE = [
        r"^garantia(?:s)?\s+(?:de\s+|del\s+)?(.+?)\s+es\s+(\d+)\s+dias?$",
    ]

    # Forma corta sin "de"/"es": "garantia [producto] [N] dias". Se revisa despues
    # de PATTERNS_SIMPLE (que exige "es") para no interceptar ese caso primero.
    PATTERNS_SIMPLE_CORTO = [
        r"^garantia(?:s)?\s+(?:de\s+|del\s+)?(.+?)\s+(\d+)\s+dias?$",
    ]

    # Catch-all: se revisa al final para no comerse los patrones de configuracion
    # de arriba (esos tambien empiezan con "garantia de ..."). El lookahead negativo
    # excluye "garantia de reparacion OS-XXXX", que es de core/detectors/
    # service_detector.py (garantia de una reparacion de Servicio Tecnico, no de
    # un cliente).
    PATTERNS_CLIENTE = [
        r"^garantias?\s+de\s+(?!reparacion\b)(.+)$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_POR_VENCER:
            if re.search(pattern, text):
                return {"intent": "garantia.por_vencer"}

        for pattern in self.PATTERNS_VER:
            match = re.search(pattern, text)
            if match:
                return {"intent": "garantia.ver", "numero": match.group(1).upper()}

        for pattern in self.PATTERNS_DOBLE:
            match = re.search(pattern, text)
            if match:
                producto, dias_fabrica, dias_propia = match.groups()
                return {
                    "intent": "garantia.configurar",
                    "producto_query": producto.strip(),
                    "dias_fabrica": int(dias_fabrica),
                    "dias_propia": int(dias_propia)
                }

        for pattern in self.PATTERNS_SIMPLE:
            match = re.search(pattern, text)
            if match:
                producto, dias = match.groups()
                return {
                    "intent": "garantia.configurar",
                    "producto_query": producto.strip(),
                    "dias_fabrica": None,
                    "dias_propia": int(dias)
                }

        for pattern in self.PATTERNS_SIMPLE_CORTO:
            match = re.search(pattern, text)
            if match:
                producto, dias = match.groups()
                return {
                    "intent": "garantia.configurar",
                    "producto_query": producto.strip(),
                    "dias_fabrica": None,
                    "dias_propia": int(dias)
                }

        for pattern in self.PATTERNS_CLIENTE:
            match = re.search(pattern, text)
            if match:
                return {"intent": "garantia.por_cliente", "cliente_query": match.group(1).strip()}

        return None
