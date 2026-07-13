import re
import unicodedata

def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()

class ServiceDetector:

    ESTADOS = {
        "recepcion": "RECEPCION",
        "revision": "REVISION", 
        "revisando": "REVISION",
        "presupuesto": "PRESUPUESTO",
        "aprobado": "APROBADO",
        "aprobaron": "APROBADO",
        "reparacion": "REPARACION",
        "reparando": "REPARACION",
        "listo": "LISTO",
        "terminado": "LISTO",
        "entregado": "ENTREGADO",
        "entregaron": "ENTREGADO",
    }

    PATTERNS_NUEVA_ORDEN = [
        r"^nueva?\s+(?:orden|reparacion|servicio|equipo)$",
        r"^(?:nueva?\s+orden|recibir?|ingresa[r]?|registra[r]?)\s+(?:equipo|reparacion)?",
        r"^(?:el\s+cliente|cliente)\s+(.+?)\s+(?:trajo|dejo|entrego)\s+(.+)$",
        r"^recib[io]+\s+(?:una?\s+)?(.+?)\s+de\s+(.+)$",
    ]

    PATTERNS_BUSCAR_ORDEN = [
        r"^(?:busca[r]?|ver?|estado\s+de?|info\s+de?)\s+(?:la\s+)?(?:orden|os)[- ]?(\w+)$",
        r"^(?:ver|busca[r]?|estado)\s+(?:orden\s+)?(?:os[- ]?)?(\d+)$",
        r"^(?:orden|os)[- ]?(\d+)$",
        r"^como\s+(?:va|esta)\s+(?:la\s+)?(?:orden|os)[- ]?(\w+)$",
    ]

    PATTERNS_VER_GARANTIA_REPARACION = [
        r"^garantia\s+(?:de\s+)?reparacion\s+(?:de\s+)?(?:la\s+)?(?:orden\s+)?(?:os[- ]?)?(\w+)$",
    ]

    PATTERNS_RECLAMAR_GARANTIA = [
        r"^reclamacion\s+(?:de\s+)?garantia\s+(?:de\s+)?(?:la\s+)?(?:orden\s+)?(?:os[- ]?)?(\w+)$",
        r"^reclamar\s+garantia\s+(?:de\s+)?(?:la\s+)?(?:orden\s+)?(?:os[- ]?)?(\w+)$",
    ]

    PATTERNS_CAMBIAR_ESTADO = [
        r"^(?:os[- ]?)?(\d+)\s+(?:esta|paso|cambio|quedo)\s+(.+)$",
        r"^(?:os[- ]?)?(\d+)\s+(.+)$",
        r"^(?:cambiar?\s+)?estado\s+(?:de\s+)?(?:orden\s+)?(?:os[- ]?)?(\w+)\s+a\s+(.+)$",
        r"^(?:orden\s+)?(?:os[- ]?)?(\w+)\s+(?:esta|paso\s+a|cambio\s+a)\s+(.+)$",
        r"^(?:marcar?\s+)?(?:orden\s+)?(?:os[- ]?)?(\w+)\s+como\s+(.+)$",
    ]

    PATTERNS_PRESUPUESTO = [
        r"^presupuesto\s+(?:de\s+)?(?:os[- ]?)?(\w+)\s+(?:es|repuestos?)\s+(\d+\.?\d*)\s+(?:mano\s+de\s+obra|mdo)\s+(\d+\.?\d*)$",
    ]

    PATTERNS_LISTAR = [
        r"^(?:ordenes?|servicios?|reparaciones?)(?:\s+en\s+(.+))?$",
        r"^que\s+(?:ordenes?|equipos?|reparaciones?)\s+(?:hay|tenemos?|estan?)(?:\s+en\s+(.+))?$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_RECLAMAR_GARANTIA:
            match = re.search(pattern, text)
            if match:
                return {"intent": "service.reclamar_garantia", "numero": match.group(1).upper()}

        for pattern in self.PATTERNS_VER_GARANTIA_REPARACION:
            match = re.search(pattern, text)
            if match:
                return {"intent": "service.ver_garantia_reparacion", "numero": match.group(1).upper()}

        for pattern in self.PATTERNS_BUSCAR_ORDEN:
            match = re.search(pattern, text)
            if match:
                return {"intent": "service.buscar_orden", "numero": match.group(1).upper()}

        for pattern in self.PATTERNS_CAMBIAR_ESTADO:
            match = re.search(pattern, text)
            if match:
                estado_texto = match.group(2).strip()
                estado = self.ESTADOS.get(estado_texto, estado_texto.upper())
                return {"intent": "service.cambiar_estado", "numero": match.group(1).upper(), "estado": estado}

        for pattern in self.PATTERNS_PRESUPUESTO:
            match = re.search(pattern, text)
            if match:
                return {
                    "intent": "service.presupuesto",
                    "numero": match.group(1).upper(),
                    "repuestos": float(match.group(2)),
                    "mano_obra": float(match.group(3))
                }

        for pattern in self.PATTERNS_LISTAR:
            match = re.search(pattern, text)
            if match:
                estado = match.group(1).strip() if match.group(1) else None
                if estado:
                    estado = self.ESTADOS.get(estado, estado.upper())
                return {"intent": "service.listar", "estado": estado}

        for pattern in self.PATTERNS_NUEVA_ORDEN:
            if re.search(pattern, text):
                return {"intent": "service.nueva_orden", "query": text}

        return None
