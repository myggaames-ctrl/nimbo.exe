import re
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()


class PuntosDetector:

    PATTERNS_DISPONIBLES = [
        r"^puntos\s+disponibles?$",
        r"^que\s+clientes?\s+tienen\s+puntos$",
    ]

    PATTERNS_CANJEAR = [
        r"^canjea[r]?\s+(\d+)\s+puntos?\s+(?:de\s+|para\s+)?(.+)$",
    ]

    # Catch-all: se revisa al final para no comerse "puntos disponibles".
    PATTERNS_VER = [
        r"^puntos\s+(?:de\s+)?(.+)$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_DISPONIBLES:
            if re.search(pattern, text):
                return {"intent": "puntos.disponibles"}

        for pattern in self.PATTERNS_CANJEAR:
            match = re.search(pattern, text)
            if match:
                puntos, cliente_query = match.groups()
                return {
                    "intent": "puntos.canjear",
                    "puntos": int(puntos),
                    "cliente_query": cliente_query.strip()
                }

        for pattern in self.PATTERNS_VER:
            match = re.search(pattern, text)
            if match:
                return {"intent": "puntos.ver", "cliente_query": match.group(1).strip()}

        return None
