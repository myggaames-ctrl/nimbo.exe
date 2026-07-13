import re
import unicodedata

def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()

NUMEROS = {
    "un": "1", "una": "1", "dos": "2", "tres": "3", "cuatro": "4",
    "cinco": "5", "seis": "6", "siete": "7", "ocho": "8", "nueve": "9",
    "diez": "10", "once": "11", "doce": "12", "quince": "15", "veinte": "20"
}

def reemplazar_numeros(text):
    for palabra, numero in NUMEROS.items():
        text = re.sub(r"\b" + palabra + r"\b", numero, text)
    return text

def singularize(text):
    if text.endswith("es"): return text[:-2]
    if text.endswith("s"): return text[:-1]
    return text

class VentaDetector:

    PATTERNS_VENTA = [
        r"^vend[io]+\s+(\d+)\s+(.+?)(?:\s+a\s+Q?(\d+\.?\d*))?(?:\s+cliente\s+(.+))?$",
        r"^venta\s+(.+?)\s+(\d+)\s+unidades?(?:\s+Q?(\d+\.?\d*))?(?:\s+cliente\s+(.+))?$",
        r"^se\s+vendio\s+(\d+)\s+(.+?)(?:\s+a\s+Q?(\d+\.?\d*))?$",
        r"^vendimos\s+(\d+)\s+(.+?)(?:\s+a\s+Q?(\d+\.?\d*))?$",
        r"^salio\s+(\d+)\s+(.+?)(?:\s+a\s+Q?(\d+\.?\d*))?$",
    ]

    PATTERNS_RESUMEN = [
        r"^ventas?\s+(?:del?\s+)?(?:hoy|dia)$",
        r"^cuanto\s+(?:vendimos|vendio)\s+hoy$",
        r"^resumen\s+(?:del?\s+)?(?:dia|hoy)$",
        r"^caja\s+(?:del?\s+)?(?:dia|hoy)$",
        r"^total\s+(?:del?\s+)?(?:dia|hoy)$",
    ]

    PATTERNS_VENTAS_MES = [
        r"^ventas?\s+(?:del?\s+)?mes$",
        r"^cuanto\s+(?:vendimos|vendio)\s+(?:este\s+)?mes$",
        r"^resumen\s+(?:del?\s+)?mes$",
        r"^total\s+(?:del?\s+)?mes$",
    ]

    def detect(self, text: str):
        text = normalize(text)
        text = reemplazar_numeros(text)

        for pattern in self.PATTERNS_RESUMEN:
            if re.search(pattern, text):
                return {"intent": "venta.resumen_dia"}

        for pattern in self.PATTERNS_VENTAS_MES:
            if re.search(pattern, text):
                return {"intent": "venta.resumen_mes"}

        for pattern in self.PATTERNS_VENTA:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if pattern.startswith(r"^venta"):
                    producto = singularize(groups[0].strip())
                    cantidad = int(groups[1])
                    precio = float(groups[2]) if groups[2] else None
                    cliente = groups[3].strip() if len(groups) > 3 and groups[3] else None
                else:
                    cantidad = int(groups[0])
                    producto = singularize(groups[1].strip())
                    precio = float(groups[2]) if len(groups) > 2 and groups[2] else None
                    cliente = groups[3].strip() if len(groups) > 3 and groups[3] else None
                return {
                    "intent": "venta.registrar",
                    "cantidad": cantidad,
                    "query": producto,
                    "precio": precio,
                    "cliente": cliente
                }

        return None
