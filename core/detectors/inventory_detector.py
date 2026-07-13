import re
import unicodedata

def normalize(text):
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def singularize(text):
    if text.endswith('es'):
        return text[:-2]
    if text.endswith('s'):
        return text[:-1]
    return text

class InventoryDetector:

    EXACT = ["inventario", "productos", "listar productos", "mostrar productos", "que tenemos", "que hay", "que productos hay", "que productos tenemos", "que tenemos en inventario", "que hay en inventario"]

    SEARCH_PATTERNS = [
        r"^buscar?\s+(.+)$",
        r"^stock de\s+(.+)$",
        r"^cuantos?\s+(.+?)\s+(?:hay|tenemos|quedan?|existen?).*$",
        r"^cuantas?\s+(.+?)\s+(?:hay|tenemos|quedan?|existen?).*$",
        r"^(?:hay|tienes?|existen?|tienen?)\s+(.+?)(?:\s+en stock|\s+disponibles?)?$",
        r"^(?:que|cuales?)\s+(.+?)\s+(?:tenemos|hay|tienen).*$",
        r"^(.+?)\s+(?:en stock|disponibles?|en inventario)$",
    ]

    CREATE_PATTERNS = [
        r"^crear\s+(.+?)\s*/\s*precio:\s*(\d+\.?\d*)\s*/\s*costo:\s*(\d+\.?\d*)$",
    ]

    ADD_STOCK_PATTERNS = [
        r"^agrega[r]?\s+(\d+)\s+(.+?)(?:\s+al?\s+stock)?$",
        r"^entr[ao]\s+(\d+)\s+(.+)$",
        r"^ingresa[r]?\s+(\d+)\s+(.+)$",
    ]

    REMOVE_STOCK_PATTERNS = [
        r"^quita[r]?\s+(\d+)\s+(.+?)(?:\s+del?\s+stock)?$",
        r"^sal[ei][o]?\s+(\d+)\s+(.+)$",
        r"^retira[r]?\s+(\d+)\s+(.+)$",
    ]

    PRICE_PATTERNS = [
        r"^actualiza[r]?\s+precio\s+(?:de\s+)?(.+?)\s+a\s+(\d+\.?\d*)$",
        r"^cambia[r]?\s+precio\s+(?:de\s+)?(.+?)\s+a\s+(\d+\.?\d*)$",
    ]

    COST_PATTERNS = [
        r"^actualiza[r]?\s+costo\s+(?:de\s+)?(.+?)\s+a\s+(\d+\.?\d*)$",
        r"^cambia[r]?\s+costo\s+(?:de\s+)?(.+?)\s+a\s+(\d+\.?\d*)$",
        r"^(?:el\s+)?costo\s+de\s+(.+?)\s+es\s+(\d+\.?\d*)$",
    ]

    MIN_STOCK_PATTERNS = [
        r"^(?:stock|inventario)\s+minimo\s+(?:de\s+)?(.+?)\s+(?:es|sera?)\s+(\d+)$",
        r"^(?:alerta|avisar?)\s+(?:cuando\s+)?(.+?)\s+(?:tenga|baje\s+a)\s+(\d+)$",
        r"^minimo\s+(?:de\s+)?(.+?)\s+(\d+)$",
    ]

    DELETE_PATTERNS = [
        r"^elimina[r]?\s+(?:producto\s+)?(.+)$",
        r"^borra[r]?\s+(?:producto\s+)?(.+)$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        if text in self.EXACT:
            return {"intent": "inventory.list", "query": ""}

        for pattern in self.CREATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return {
                    "intent": "inventory.create",
                    "query": match.group(1).strip(),
                    "price": float(match.group(2)),
                    "cost": float(match.group(3))
                }

        for pattern in self.ADD_STOCK_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return {"intent": "inventory.add_stock", "quantity": int(match.group(1)), "query": singularize(match.group(2).strip())}

        for pattern in self.REMOVE_STOCK_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return {"intent": "inventory.remove_stock", "quantity": int(match.group(1)), "query": singularize(match.group(2).strip())}

        for pattern in self.COST_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return {
                    "intent": "inventory.update_cost",
                    "query": singularize(match.group(1).strip()),
                    "cost": float(match.group(2))
                }

        for pattern in self.PRICE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return {"intent": "inventory.update_price", "query": singularize(match.group(1).strip()), "price": float(match.group(2))}

        for pattern in self.MIN_STOCK_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return {
                    "intent": "inventory.set_min_stock",
                    "query": singularize(match.group(1).strip()),
                    "quantity": int(match.group(2))
                }

        for pattern in self.DELETE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return {"intent": "inventory.delete", "query": singularize(match.group(1).strip())}

        for pattern in self.SEARCH_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return {"intent": "inventory.search", "query": singularize(match.group(1).strip())}

        return None
