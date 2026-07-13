import re
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()


class ComboDetector:

    PATTERNS_SUGERIR = [
        r"^sugerir\s+combos?$",
        r"^sugiere(?:me)?\s+combos?$",
        r"^que\s+combos?\s+(?:me\s+)?sugieres$",
    ]

    PATTERNS_LISTAR = [
        r"^ver\s+combos?$",
        r"^listar\s+combos?$",
        r"^combos$",
    ]

    PATTERNS_VENDER = [
        r"^vender\s+combo\s+(.+)$",
        r"^vendi\s+(?:el\s+)?combo\s+(.+)$",
        r"^se\s+vendio\s+(?:el\s+)?combo\s+(.+)$",
    ]

    PATTERNS_CREAR = [
        r"^crear\s+combo\s+(.+)$",
        r"^nuevo\s+combo\s+(.+)$",
        r"^agregar\s+combo\s+(.+)$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_SUGERIR:
            if re.search(pattern, text):
                return {"intent": "combo.sugerir"}

        for pattern in self.PATTERNS_LISTAR:
            if re.search(pattern, text):
                return {"intent": "combo.listar"}

        for pattern in self.PATTERNS_VENDER:
            match = re.search(pattern, text)
            if match:
                return {"intent": "combo.vender", "nombre": match.group(1).strip()}

        for pattern in self.PATTERNS_CREAR:
            match = re.search(pattern, text)
            if match:
                return {"intent": "combo.crear", "nombre": match.group(1).strip()}

        return None
