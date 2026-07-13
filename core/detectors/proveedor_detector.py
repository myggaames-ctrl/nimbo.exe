import re
import unicodedata

def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()

class ProveedorDetector:

    PATTERNS_NUEVO = [
        r"^nuevo\s+proveedor\s+(.+?)(?:\s+(\d{7,}))?$",
        r"^registra[r]?\s+proveedor\s+(.+?)(?:\s+(\d{7,}))?$",
        r"^agrega[r]?\s+proveedor\s+(.+?)(?:\s+(\d{7,}))?$",
    ]

    PATTERNS_BUSCAR = [
        r"^busca[r]?\s+proveedor\s+(.+)$",
        r"^proveedor\s+(.+)$",
        r"^info\s+proveedor\s+(.+)$",
    ]

    PATTERNS_LISTAR = [
        r"^proveedores?$",
        r"^lista[r]?\s+proveedores?$",
        r"^todos?\s+(?:los\s+)?proveedores?$",
    ]

    PATTERNS_HISTORIAL = [
        r"^historial\s+(?:de\s+)?(?:compras?\s+(?:a|de)\s+)?(.+)$",
        r"^compras?\s+(?:a|de)\s+(.+)$",
        r"^(?:cuanto|que)\s+(?:le\s+)?compre?\s+(?:a\s+)?(.+)$",
    ]

    PATTERNS_ORDEN_COMPRA = [
        r"^pedi[r]?\s+(?:a\s+)?(.+?)\s+(\d+)\s+(.+?)\s+(?:a\s+)?Q?(\d+\.?\d*)$",
        r"^orden\s+(?:de\s+)?compra\s+(?:a\s+)?(.+)",
        r"^compra[r]?\s+(?:a\s+)?(.+?)\s+(\d+)\s+(.+)",
    ]

    PATTERNS_ORDEN_GENERAR = [
        r"^genera[r]?\s+orden\s+(?:para\s+)?(.+)$",
        r"^crear?\s+orden\s+(?:de\s+compra\s+)?(?:para\s+)?(.+)$",
        r"^pedir\s+(?:a\s+)?(.+)$",
    ]

    PATTERNS_PEDIDOS = [
        r"^pedidos?$",
        r"^que\s+(?:hay\s+que|debo|debemos)\s+pedir",
        r"^que\s+(?:productos?\s+)?(?:faltan?|necesitamos?|hay\s+que\s+comprar)",
        r"^sugerir?\s+pedidos?",
        r"^reabastecimiento$",
        r"^que\s+compra[r]?",
    ]

    PATTERNS_ASOCIAR = [
        r"^(.+?)\s+(?:es\s+de|viene\s+de|lo\s+trae)\s+(.+)$",
        r"^asocia[r]?\s+(.+?)\s+(?:con|a)\s+proveedor\s+(.+)$",
        r"^proveedor\s+(?:de\s+)?(.+?)\s+es\s+(.+)$",
    ]

    PATTERNS_ALERTAS = [
        r"^alertas?\s+(?:de\s+)?precios?$",
        r"^cambios?\s+(?:de\s+)?precios?$",
        r"^precios?\s+cambiados?$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_ORDEN_GENERAR:
            match = re.search(pattern, text)
            if match:
                return {"intent": "proveedor.generar_orden", "query": match.group(1).strip()}

        for pattern in self.PATTERNS_PEDIDOS:
            if re.search(pattern, text):
                return {"intent": "proveedor.pedidos"}

        for pattern in self.PATTERNS_ASOCIAR:
            match = re.search(pattern, text)
            if match:
                return {"intent": "proveedor.asociar", "producto": match.group(1).strip(), "proveedor": match.group(2).strip()}

        for pattern in self.PATTERNS_ALERTAS:
            if re.search(pattern, text):
                return {"intent": "proveedor.alertas"}

        for pattern in self.PATTERNS_LISTAR:
            if re.search(pattern, text):
                return {"intent": "proveedor.listar"}

        for pattern in self.PATTERNS_NUEVO:
            match = re.search(pattern, text)
            if match:
                return {
                    "intent": "proveedor.nuevo",
                    "nombre": match.group(1).strip().title(),
                    "whatsapp": match.group(2).strip() if match.group(2) else ""
                }

        for pattern in self.PATTERNS_ORDEN_COMPRA:
            match = re.search(pattern, text)
            if match:
                return {"intent": "proveedor.orden_compra", "query": text}

        for pattern in self.PATTERNS_HISTORIAL:
            match = re.search(pattern, text)
            if match:
                return {"intent": "proveedor.historial", "query": match.group(1).strip()}

        for pattern in self.PATTERNS_BUSCAR:
            match = re.search(pattern, text)
            if match:
                return {"intent": "proveedor.buscar", "query": match.group(1).strip()}

        return None
