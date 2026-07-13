import re
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()


class CodigoBarrasDetector:

    PATTERNS_GENERAR_CODIGO = [
        r"^genera(?:r)?\s+codigo(?:\s+de\s+barras)?\s+(?:de\s+|para\s+)?(.+)$",
        r"^codigo(?:\s+de\s+barras)?\s+(?:de\s+|para\s+)(.+)$",
    ]

    # Se revisa antes de PATTERNS_ETIQUETA_PRODUCTO, que es un catch-all mas generico
    # y matchearia tambien "etiquetas de productos sin codigo" capturando "productos
    # sin codigo" como si fuera el nombre de un producto.
    PATTERNS_ETIQUETAS_LOTE = [
        r"^(?:generar\s+|imprimir\s+)?etiquetas?\s+de\s+(?:todos\s+los\s+)?productos\s+sin\s+codigo(?:\s+de\s+barras)?$",
    ]

    PATTERNS_ETIQUETA_PRODUCTO = [
        r"^etiquetas?\s+de\s+(.+)$",
        r"^genera(?:r)?\s+etiquetas?\s+(?:de\s+|para\s+)?(.+)$",
        r"^imprimir\s+etiquetas?\s+(?:de\s+|para\s+)?(.+)$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_ETIQUETAS_LOTE:
            if re.search(pattern, text):
                return {"intent": "etiqueta.lote_sin_codigo"}

        for pattern in self.PATTERNS_GENERAR_CODIGO:
            match = re.search(pattern, text)
            if match:
                return {"intent": "codigobarras.generar", "query": match.group(1).strip()}

        for pattern in self.PATTERNS_ETIQUETA_PRODUCTO:
            match = re.search(pattern, text)
            if match:
                return {"intent": "etiqueta.producto", "query": match.group(1).strip()}

        return None
