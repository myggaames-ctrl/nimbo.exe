import re
import unicodedata

def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()

class EventoDetector:

    PATTERNS_ANALISIS = [
        r"^analisis\s+(?:de\s+)?clientes?$",
        r"^como\s+(?:estan|van)\s+(?:los\s+)?clientes?$",
        r"^reporte\s+(?:de\s+)?clientes?$",
        r"^analiza\s+(?:mis\s+)?clientes?$",
    ]

    PATTERNS_AGRADECIMIENTO = [
        r"^(?:mensaje|carta)\s+(?:de\s+)?agradecimiento\s+(?:para|a)\s+(.+)$",
        r"^agradece[r]?\s+(?:a\s+)?(.+)$",
        r"^manda[r]?\s+agradecimiento\s+(?:a\s+)?(.+)$",
    ]

    PATTERNS_EVENTO = [
        r"^(?:sugerir?|crear?|planear?)\s+(?:un\s+)?evento$",
        r"^(?:que\s+)?evento\s+(?:puedo|podemos)\s+(?:hacer|organizar)$",
        r"^idea\s+(?:de\s+)?evento\s+(?:para\s+)?clientes?$",
        r"^evento\s+(?:para\s+)?clientes?$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_ANALISIS:
            if re.search(pattern, text):
                return {"intent": "evento.analisis"}

        for pattern in self.PATTERNS_EVENTO:
            if re.search(pattern, text):
                return {"intent": "evento.sugerir"}

        for pattern in self.PATTERNS_AGRADECIMIENTO:
            match = re.search(pattern, text)
            if match:
                return {"intent": "evento.agradecimiento", "query": match.group(1).strip()}

        if re.search(r"^cumpleanos\s+(?:de\s+)?(.+?)\s+(?:es\s+)?(?:el\s+)?(\d{1,2}[/\-]\d{1,2})$", text):
            match = re.search(r"^cumpleanos\s+(?:de\s+)?(.+?)\s+(?:es\s+)?(?:el\s+)?(\d{1,2}[/\-]\d{1,2})$", text)
            return {"intent": "cumpleanos.agregar", "query": match.group(1).strip(), "fecha": match.group(2).strip()}

        if re.search(r"^(?:agregar?|nuevo)\s+pago\s+(.+)$", text):
            match = re.search(r"^(?:agregar?|nuevo)\s+pago\s+(.+)$", text)
            return {"intent": "pago.agregar", "query": match.group(1).strip()}

        if re.search(r"^(?:ver|lista[r]?|mis)\s+pagos?$", text) or text == "pagos":
            return {"intent": "pago.listar"}

        if re.search(r"^(?:recuerdame|recordatorio)\s+(.+)$", text):
            match = re.search(r"^(?:recuerdame|recordatorio)\s+(.+)$", text)
            return {"intent": "recordatorio.agregar", "query": match.group(1).strip()}

        return None
