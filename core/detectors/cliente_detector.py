import re
import unicodedata

def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()

class ClienteDetector:

    GRUPOS_TEXTO = {
        "detallista": "detallista", "detallistas": "detallista",
        "mayorista": "mayorista", "mayoristas": "mayorista",
        "especial": "especial", "especiales": "especial",
        "vip": "vip", "vips": "vip",
    }

    # Se revisan antes que PATTERNS_NUEVO/BUSCAR (mas genericos) para que "Juan Perez
    # es mayorista" o "grupo de Juan Perez" no terminen matcheando como busqueda de
    # cliente por nombre.
    PATTERNS_GRUPO_LISTAR = [
        r"^ver\s+(detallistas?|mayoristas?|especiales?|vips?)$",
        r"^lista(?:r)?\s+(?:clientes?\s+)?(detallistas?|mayoristas?|especiales?|vips?)$",
        r"^clientes?\s+(detallistas?|mayoristas?|especiales?|vips?)$",
    ]

    PATTERNS_GRUPO_SET = [
        r"^(.+?)\s+es\s+(detallista|mayorista|especial|vip)s?$",
    ]

    PATTERNS_GRUPO_VER = [
        r"^grupo\s+(?:de\s+)?(.+)$",
        r"^que\s+grupo\s+tiene\s+(.+)$",
        r"^tipo\s+de\s+cliente\s+(?:de\s+)?(.+)$",
    ]

    PATTERNS_NUEVO = [
        r"^(?:nuevo|crear|registra[r]?|agrega[r]?)\s+cliente\s+(.+?)\s+(\d{7,})$",
        r"^registra[r]?\s+cliente\s+(.+?)\s+(\d{7,})$",
        r"^agrega[r]?\s+cliente\s+(.+?)\s+(\d{7,})$",
        r"^cliente\s+nuevo\s+(.+?)\s+(\d{7,})$",
    ]

    PATTERNS_BUSCAR = [
        r"^busca[r]?\s+cliente\s+(.+)$",
        r"^cliente\s+(.+)$",
        r"^info\s+(?:de\s+)?(.+)$",
        r"^datos\s+(?:de\s+)?(.+)$",
    ]

    PATTERNS_HISTORIAL = [
        r"^historial\s+(?:de\s+)?(.+)$",
        r"^compras\s+(?:de\s+)?(.+)$",
        r"^(?:que|cuanto)\s+(?:ha\s+)?comprado\s+(.+)$",
    ]

    PATTERNS_RESUMEN = [
        r"^resumen\s+(?:de\s+)?(.+)$",
    ]

    PATTERNS_LISTAR = [
        r"^clientes?$",
        r"^lista(?:r)?\s+clientes?$",
        r"^todos?\s+(?:los\s+)?clientes?$",
        r"^ver\s+clientes?$",
    ]

    PATTERNS_INACTIVOS = [
        r"^clientes?\s+inactivos?$",
        r"^clientes?\s+(?:que\s+)?no\s+(?:han\s+)?compra[do]+",
        r"^clientes?\s+sin\s+compras?",
    ]

    PATTERNS_EXCEL = [
        r"^excel\s+(?:de\s+)?clientes?$",
        r"^exporta[r]?\s+(?:lista\s+de\s+)?clientes?",
        r"^dame\s+(?:un\s+)?excel\s+(?:con\s+)?(?:todos?\s+(?:los\s+)?)?clientes?",
        r"^reporte\s+(?:de\s+)?clientes?",
        r"^genera[r]?\s+excel\s+(?:de\s+)?clientes?",
        r"^lista\s+de\s+clientes?\s+en\s+excel",
        r"^exporta[r]?\s+clientes?",
        r"^reporte\s+(?:de\s+)?clientes?",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_GRUPO_LISTAR:
            match = re.search(pattern, text)
            if match:
                grupo = self.GRUPOS_TEXTO.get(match.group(1), match.group(1))
                return {"intent": "cliente.grupo_listar", "grupo": grupo}

        for pattern in self.PATTERNS_GRUPO_SET:
            match = re.search(pattern, text)
            if match:
                nombre, grupo = match.groups()
                return {"intent": "cliente.grupo_set", "nombre": nombre.strip(), "grupo": grupo}

        for pattern in self.PATTERNS_GRUPO_VER:
            match = re.search(pattern, text)
            if match:
                return {"intent": "cliente.grupo_ver", "query": match.group(1).strip()}

        for pattern in self.PATTERNS_EXCEL:
            if re.search(pattern, text):
                return {"intent": "cliente.excel"}

        for pattern in self.PATTERNS_INACTIVOS:
            if re.search(pattern, text):
                return {"intent": "cliente.inactivos"}

        for pattern in self.PATTERNS_LISTAR:
            if re.search(pattern, text):
                return {"intent": "cliente.listar"}

        for pattern in self.PATTERNS_NUEVO:
            match = re.search(pattern, text)
            if match:
                return {"intent": "cliente.nuevo", "nombre": match.group(1).strip().title(), "telefono": match.group(2).strip()}

        for pattern in self.PATTERNS_HISTORIAL:
            match = re.search(pattern, text)
            if match:
                return {"intent": "cliente.historial", "query": match.group(1).strip()}

        for pattern in self.PATTERNS_RESUMEN:
            match = re.search(pattern, text)
            if match:
                return {"intent": "cliente.resumen", "query": match.group(1).strip()}

        for pattern in self.PATTERNS_BUSCAR:
            match = re.search(pattern, text)
            if match:
                return {"intent": "cliente.buscar", "query": match.group(1).strip()}

        return None
