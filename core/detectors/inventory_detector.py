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

    # Sintaxis natural: "agregar/nuevo/crear producto NOMBRE precio N [costo N] [stock N]".
    # Costo y stock son opcionales y se buscan en cualquier orden dentro del resto
    # del texto (group 3) en detect() - a diferencia de CREATE_PATTERNS (que exige
    # la sintaxis rigida "NOMBRE / precio: N / costo: N" y siempre trae costo), este
    # patron puede devolver el intent sin "cost" (falta costo) para que el flujo
    # conversacional en core/nimbo.py (PRODUCTO_NUEVO_INICIO:) pregunte lo que falte.
    CREATE_NATURAL_PATTERNS = [
        r"^(?:agregar|agrega|nuevo|crear)\s+producto\s+(.+?)\s+precio\s+(\d+\.?\d*)(.*)$",
    ]

    IMPORTAR_EXACT = [
        "importar productos", "cargar productos", "importar producto", "cargar producto",
        "importar productos desde excel", "importar productos desde csv",
        "cargar productos desde excel", "cargar productos desde csv",
        "importar excel", "cargar excel", "importar inventario",
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
        r"^actualiza[r]?\s+(?:el\s+)?precio\s+(?:de\s+)?(.+?)\s+a\s+(\d+\.?\d*)$",
        r"^cambia[r]?\s+(?:el\s+)?precio\s+(?:de\s+)?(.+?)\s+a\s+(\d+\.?\d*)$",
    ]

    COST_PATTERNS = [
        r"^actualiza[r]?\s+(?:el\s+)?costo\s+(?:de\s+)?(.+?)\s+a\s+(\d+\.?\d*)$",
        r"^cambia[r]?\s+(?:el\s+)?costo\s+(?:de\s+)?(.+?)\s+a\s+(\d+\.?\d*)$",
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

    ALERTAS_PREDICTIVAS_EXACT = [
        "alertas de inventario", "alertas predictivas", "alerta predictiva",
        "prediccion de inventario", "predicciones de inventario",
        "cuando se acaba el stock", "cuando se acaba el inventario",
    ]

    KARDEX_EXACT = [
        "kardex", "ver kardex", "historial de movimientos", "historial de inventario",
        "movimientos de inventario", "movimientos de stock", "movimientos",
    ]

    KARDEX_PATTERNS = [
        r"^kardex\s+(?:de\s+|del?\s+)?(?:el|la|los|las)\s+(.+)$",
        r"^kardex\s+(?:de\s+|del?\s+)?(.+)$",
        r"^historial\s+de\s+movimientos\s+(?:de\s+|del?\s+)?(?:el|la|los|las)\s+(.+)$",
        r"^historial\s+de\s+movimientos\s+(?:de\s+|del?\s+)?(.+)$",
        r"^movimientos\s+(?:de\s+|del?\s+)?(?:el|la|los|las)\s+(.+)$",
        r"^movimientos\s+(?:de\s+|del?\s+)?(.+)$",
    ]

    # Los patrones "con articulo" van primero (mas especificos) para que (.+) no
    # termine capturando el articulo como si fuera parte del nombre del producto -
    # requieren \s+ (no \s*) despues del articulo para que "la" no matchee como
    # prefijo de "las" y deje una "s" suelta pegada al nombre.
    PREDICCION_PRODUCTO_PATTERNS = [
        r"^cuando\s+se\s+acaba[n]?\s+(?:el|la|los|las)\s+(.+)$",
        r"^cuando\s+se\s+acaba[n]?\s+(.+)$",
        r"^en\s+cuantos\s+dias\s+se\s+acaba[n]?\s+(?:el|la|los|las)\s+(.+)$",
        r"^en\s+cuantos\s+dias\s+se\s+acaba[n]?\s+(.+)$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        if text in self.EXACT:
            return {"intent": "inventory.list", "query": ""}

        if text in self.ALERTAS_PREDICTIVAS_EXACT:
            return {"intent": "inventory.alertas_predictivas"}

        if text in self.IMPORTAR_EXACT:
            return {"intent": "inventory.importar_instrucciones"}

        if text in self.KARDEX_EXACT:
            return {"intent": "inventory.kardex", "query": ""}

        for pattern in self.KARDEX_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return {"intent": "inventory.kardex", "query": singularize(match.group(1).strip())}

        for pattern in self.PREDICCION_PRODUCTO_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return {"intent": "inventory.prediccion_producto", "query": singularize(match.group(1).strip())}

        for pattern in self.CREATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return {
                    "intent": "inventory.create",
                    "query": match.group(1).strip(),
                    "price": float(match.group(2)),
                    "cost": float(match.group(3))
                }

        for pattern in self.CREATE_NATURAL_PATTERNS:
            match = re.search(pattern, text)
            if match:
                data = {"intent": "inventory.create", "query": match.group(1).strip(), "price": float(match.group(2))}
                resto = match.group(3) or ""
                m_costo = re.search(r"costo\s+(\d+\.?\d*)", resto)
                m_stock = re.search(r"(?:stock|cantidad)\s+(\d+\.?\d*)", resto)
                if m_costo:
                    data["cost"] = float(m_costo.group(1))
                if m_stock:
                    data["quantity"] = float(m_stock.group(1))
                return data

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
