import re
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()


class TarifaDetector:

    PATTERNS_AGREGAR = [
        r"^agregar\s+tarifa\s+(.+?)\s+q?\s*(\d+(?:\.\d+)?)$",
        r"^nueva\s+tarifa\s+(.+?)\s+q?\s*(\d+(?:\.\d+)?)$",
        r"^crear\s+tarifa\s+(.+?)\s+q?\s*(\d+(?:\.\d+)?)$",
    ]

    PATTERNS_LISTAR = [
        r"^ver\s+tarifas?(?:\s+de\s+mano\s+de\s+obra)?$",
        r"^listar\s+tarifas?(?:\s+de\s+mano\s+de\s+obra)?$",
        r"^tarifas?\s+de\s+mano\s+de\s+obra$",
        r"^tarifas?$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_AGREGAR:
            match = re.search(pattern, text)
            if match:
                descripcion, precio = match.groups()
                return {"intent": "tarifa.agregar", "descripcion": descripcion.strip(), "precio": float(precio)}

        for pattern in self.PATTERNS_LISTAR:
            if re.search(pattern, text):
                return {"intent": "tarifa.listar"}

        return None
