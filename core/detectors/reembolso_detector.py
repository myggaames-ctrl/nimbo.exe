import re
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()


class ReembolsoDetector:

    PATTERNS_CAMBIO = [
        r"^cambio\s+de\s+producto\s+(?:de\s+la\s+)?venta\s+#?(\d+)$",
        r"^cambiar\s+(?:un\s+)?producto\s+(?:de\s+la\s+)?venta\s+#?(\d+)$",
    ]

    PATTERNS_REEMBOLSO = [
        r"^reembolso\s+(?:de\s+la\s+)?venta\s+#?(\d+)$",
        r"^reembolsar\s+(?:la\s+)?venta\s+#?(\d+)$",
        r"^(?:hacer|procesar)\s+(?:un\s+)?reembolso\s+(?:de\s+la\s+)?venta\s+#?(\d+)$",
    ]

    PATTERNS_VER = [
        r"^ver\s+reembolso\s+(?:rem[- ]?)?(\d+)$",
        r"^reembolso\s+rem[- ]?(\d+)$",
    ]

    PATTERNS_CREDITO = [
        r"^credito(?:\s+(?:de\s+)?tienda)?\s+de\s+(.+)$",
        r"^credito\s+disponible\s+de\s+(.+)$",
        r"^(?:cuanto\s+)?credito\s+(?:disponible\s+)?tiene\s+(.+)$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        # Se revisa antes que PATTERNS_REEMBOLSO: "cambio de producto venta X"
        # tambien contiene la palabra "venta" y un numero, pero es un flujo distinto.
        for pattern in self.PATTERNS_CAMBIO:
            match = re.search(pattern, text)
            if match:
                return {"intent": "reembolso.iniciar_cambio", "venta_id": int(match.group(1))}

        for pattern in self.PATTERNS_VER:
            match = re.search(pattern, text)
            if match:
                return {"intent": "reembolso.buscar", "numero": match.group(1)}

        for pattern in self.PATTERNS_REEMBOLSO:
            match = re.search(pattern, text)
            if match:
                return {"intent": "reembolso.iniciar", "venta_id": int(match.group(1))}

        for pattern in self.PATTERNS_CREDITO:
            match = re.search(pattern, text)
            if match:
                return {"intent": "reembolso.credito", "query": match.group(1).strip()}

        return None
