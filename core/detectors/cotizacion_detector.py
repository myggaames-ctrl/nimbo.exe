import re
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()


class CotizacionDetector:

    ESTADOS = {
        "pendientes": "PENDIENTE",
        "pendiente": "PENDIENTE",
        "enviadas": "ENVIADA",
        "enviada": "ENVIADA",
        "aceptadas": "ACEPTADA",
        "aceptada": "ACEPTADA",
        "rechazadas": "RECHAZADA",
        "rechazada": "RECHAZADA",
        "vencidas": "VENCIDA",
        "vencida": "VENCIDA",
    }

    PATTERNS_BUSCAR = [
        r"^(?:ver|busca[r]?|estado\s+de)\s+(?:la\s+)?cotizacion\s+(?:cot[- ]?)?(\w+)$",
        r"^cotizacion\s+(?:cot[- ]?)?(\d+)$",
    ]

    PATTERNS_ACEPTAR = [
        r"^(?:aceptaron|acepto|aprobaron|aprobo)\s+(?:la\s+)?cotizacion\s+(?:cot[- ]?)?(\w+)$",
        r"^cotizacion\s+(?:cot[- ]?)?(\w+)\s+(?:fue\s+)?(?:aceptada|aprobada)$",
    ]

    PATTERNS_RECHAZAR = [
        r"^(?:rechazaron|rechazo|no\s+acepto|no\s+quiso|no\s+quisieron)\s+(?:la\s+)?cotizacion\s+(?:cot[- ]?)?(\w+)$",
        r"^cotizacion\s+(?:cot[- ]?)?(\w+)\s+(?:fue\s+)?rechazada$",
    ]

    PATTERNS_MARCAR_ENVIADA = [
        r"^(?:marcar?\s+)?cotizacion\s+(?:cot[- ]?)?(\w+)\s+(?:como\s+)?enviada$",
        r"^envie\s+(?:la\s+)?cotizacion\s+(?:cot[- ]?)?(\w+)$",
    ]

    PATTERNS_LISTAR = [
        r"^cotizacion(?:es)?(?:\s+(pendientes|pendiente|enviadas|enviada|aceptadas|aceptada|rechazadas|rechazada|vencidas|vencida))?$",
        r"^que\s+cotizaciones\s+(?:hay|tenemos?)(?:\s+(pendientes|enviadas|aceptadas|rechazadas|vencidas))?$",
    ]

    PATTERNS_NUEVA = [
        r"^cotizacion(?:es)?\s+para\s+(.+)$",
        r"^cotiza[r]?\s+para\s+(.+)$",
        r"^(?:generar?|crear|nueva)\s+cotizacion(?:\s+para\s+(.+))?$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_ACEPTAR:
            match = re.search(pattern, text)
            if match:
                return {"intent": "cotizacion.aceptar", "numero": match.group(1).upper()}

        for pattern in self.PATTERNS_RECHAZAR:
            match = re.search(pattern, text)
            if match:
                return {"intent": "cotizacion.rechazar", "numero": match.group(1).upper()}

        for pattern in self.PATTERNS_MARCAR_ENVIADA:
            match = re.search(pattern, text)
            if match:
                return {"intent": "cotizacion.marcar_enviada", "numero": match.group(1).upper()}

        for pattern in self.PATTERNS_BUSCAR:
            match = re.search(pattern, text)
            if match:
                return {"intent": "cotizacion.buscar", "numero": match.group(1).upper()}

        for pattern in self.PATTERNS_LISTAR:
            match = re.search(pattern, text)
            if match:
                estado_texto = match.group(1).strip() if match.group(1) else None
                estado = self.ESTADOS.get(estado_texto) if estado_texto else None
                return {"intent": "cotizacion.listar", "estado": estado}

        for pattern in self.PATTERNS_NUEVA:
            match = re.search(pattern, text)
            if match:
                cliente = match.group(1).strip() if match.groups() and match.group(1) else ""
                return {"intent": "cotizacion.nueva", "cliente": cliente}

        return None
