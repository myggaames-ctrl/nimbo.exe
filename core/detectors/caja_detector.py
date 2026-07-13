import re
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()


class CajaDetector:

    PATTERNS_ABRIR = [
        r"^abrir\s+caja$",
        r"^abrir\s+turno$",
        r"^iniciar\s+(?:caja|turno)$",
    ]

    PATTERNS_CERRAR = [
        r"^cerrar\s+caja$",
        r"^cerrar\s+turno$",
        r"^terminar\s+(?:caja|turno)$",
    ]

    PATTERNS_RETIRAR = [
        r"^retirar\s+q?\s*(\d+(?:\.\d+)?)\s+de\s+caja(?:\s+(?:para|por)\s+(.+))?$",
        r"^retiro\s+de\s+q?\s*(\d+(?:\.\d+)?)\s+de\s+caja(?:\s+(?:para|por)\s+(.+))?$",
        r"^sacar\s+q?\s*(\d+(?:\.\d+)?)\s+de\s+caja(?:\s+(?:para|por)\s+(.+))?$",
    ]

    PATTERNS_EFECTIVO = [
        r"^(?:cuanto\s+hay\s+en\s+caja|efectivo\s+en\s+caja|efectivo\s+actual|como\s+va\s+la\s+caja)$",
    ]

    PATTERNS_ANULAR = [
        r"^anular\s+(?:el\s+)?(?:turno|caja)(?:\s+(?:por|porque|motivo)\s+(.+))?$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_ANULAR:
            match = re.search(pattern, text)
            if match:
                return {"intent": "caja.anular", "motivo": (match.group(1) or "").strip()}

        for pattern in self.PATTERNS_RETIRAR:
            match = re.search(pattern, text)
            if match:
                return {
                    "intent": "caja.retirar",
                    "monto": float(match.group(1)),
                    "descripcion": (match.group(2) or "").strip()
                }

        for pattern in self.PATTERNS_ABRIR:
            if re.search(pattern, text):
                return {"intent": "caja.abrir", "query": text}

        for pattern in self.PATTERNS_CERRAR:
            if re.search(pattern, text):
                return {"intent": "caja.cerrar", "query": text}

        for pattern in self.PATTERNS_EFECTIVO:
            if re.search(pattern, text):
                return {"intent": "caja.efectivo_actual", "query": text}

        return None
