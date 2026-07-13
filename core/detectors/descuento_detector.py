import re
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()


MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


class DescuentoDetector:

    PATTERNS_CLIENTE = [
        r"^descuento(?:s)?\s+(?:de\s+|del\s+)?(\d+(?:\.\d+)?)\s*(?:%|por\s*ciento)\s+para\s+(.+)$",
        r"^(\d+(?:\.\d+)?)\s*(?:%|por\s*ciento)\s+de\s+descuento\s+para\s+(.+)$",
    ]

    PATTERNS_TEMPORADA = [
        r"^descuento(?:s)?\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*(?:%|por\s*ciento)\s+del\s+(\d{1,2})\s+al\s+(\d{1,2})\s+de\s+(\w+)(?:\s+(?:de\s+|del\s+)?(\d{4}))?$",
    ]

    PATTERNS_MONTO = [
        r"^descuento(?:s)?\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*(?:%|por\s*ciento)\s+en\s+compras\s+mayores\s+a\s+q?\s*(\d+(?:\.\d+)?)$",
        r"^descuento(?:s)?\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*(?:%|por\s*ciento)\s+(?:si|cuando)\s+(?:la\s+)?compra\s+(?:supera|es\s+mayor\s+a)\s+q?\s*(\d+(?:\.\d+)?)$",
    ]

    PATTERNS_PRODUCTO = [
        r"^descuento(?:s)?\s+(?:de\s+)?(\d+(?:\.\d+)?)\s*(?:%|por\s*ciento)\s+en\s+(.+)$",
    ]

    PATTERNS_LISTAR = [
        r"^ver\s+descuentos$",
        r"^descuentos$",
        r"^listar\s+descuentos$",
        r"^que\s+descuentos\s+(?:hay|tenemos?)$",
    ]

    PATTERNS_ELIMINAR = [
        r"^eliminar\s+descuento\s+(.+)$",
        r"^quitar\s+descuento\s+(.+)$",
        r"^desactivar\s+descuento\s+(.+)$",
        r"^borrar\s+descuento\s+(.+)$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_LISTAR:
            if re.search(pattern, text):
                return {"intent": "descuento.listar"}

        for pattern in self.PATTERNS_ELIMINAR:
            match = re.search(pattern, text)
            if match:
                return {"intent": "descuento.eliminar", "descuento_query": match.group(1).strip()}

        for pattern in self.PATTERNS_CLIENTE:
            match = re.search(pattern, text)
            if match:
                return {
                    "intent": "descuento.crear_cliente",
                    "porcentaje": float(match.group(1)),
                    "cliente_query": match.group(2).strip()
                }

        for pattern in self.PATTERNS_TEMPORADA:
            match = re.search(pattern, text)
            if match:
                porcentaje, dia_inicio, dia_fin, mes_texto, anio = match.groups()
                mes = MESES.get(mes_texto.strip())
                if not mes:
                    continue
                return {
                    "intent": "descuento.crear_temporada",
                    "porcentaje": float(porcentaje),
                    "dia_inicio": int(dia_inicio),
                    "dia_fin": int(dia_fin),
                    "mes": mes,
                    "anio": int(anio) if anio else None
                }

        for pattern in self.PATTERNS_MONTO:
            match = re.search(pattern, text)
            if match:
                return {
                    "intent": "descuento.crear_monto",
                    "porcentaje": float(match.group(1)),
                    "monto_minimo": float(match.group(2))
                }

        for pattern in self.PATTERNS_PRODUCTO:
            match = re.search(pattern, text)
            if match:
                return {
                    "intent": "descuento.crear_producto",
                    "porcentaje": float(match.group(1)),
                    "producto_query": match.group(2).strip()
                }

        return None
