import re
import unicodedata

def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()

class ReporteDetector:

    PATTERNS_DIA = [
        r"^reporte\s+(?:de\s+)?(?:ventas?\s+)?(?:del?\s+)?(?:dia|hoy)$",
        r"^como\s+(?:vamos|cerramos|cerro)\s+(?:hoy|el\s+dia)$",
        r"^ventas?\s+(?:de\s+)?hoy$",
        r"^cierre\s+(?:del?\s+)?(?:dia|caja)$",
        r"^resumen\s+(?:del?\s+)?dia$",
    ]

    PATTERNS_MENSUAL = [
        r"^reporte\s+(?:de\s+)?(?:ventas?\s+)?(?:del?\s+)?mes$",
        r"^ventas?\s+(?:del?\s+)?mes$",
        r"^resumen\s+(?:del?\s+)?mes$",
        r"^como\s+(?:vamos|cerro)\s+(?:el\s+)?mes$",
    ]

    PATTERNS_TRIMESTRAL = [
        r"^reporte\s+(?:de\s+)?(?:ventas?\s+)?trimestral$",
        r"^ventas?\s+(?:del?\s+)?trimestre$",
        r"^reporte\s+(?:del?\s+)?trimestre$",
        r"^como\s+(?:vamos|cerro)\s+(?:el\s+)?trimestre$",
    ]

    PATTERNS_SEMESTRAL = [
        r"^reporte\s+(?:de\s+)?(?:ventas?\s+)?semestral$",
        r"^ventas?\s+(?:del?\s+)?semestre$",
        r"^reporte\s+(?:del?\s+)?semestre$",
    ]

    PATTERNS_ANUAL = [
        r"^reporte\s+(?:de\s+)?(?:ventas?\s+)?(?:del?\s+)?ano$",
        r"^ventas?\s+(?:del?\s+)?ano$",
        r"^resumen\s+(?:del?\s+)?ano$",
        r"^reporte\s+anual$",
    ]

    PATTERNS_MEJORES = [
        r"^mejores\s+clientes?\s+(?:del?\s+)?mes$",
        r"^mejores\s+clientes?\s+(?:del?\s+)?trimestre$",
        r"^clientes?\s+(?:que\s+)?mas\s+(?:compran?|compraron?)\s+(?:este\s+)?mes$",
    ]

    PATTERNS_EXCEL = [
        r"^excel\s+(?:de\s+)?(?:ventas?|reporte)\s+(?:del?\s+)?mes$",
        r"^excel\s+(?:de\s+)?(?:ventas?|reporte)\s+(?:del?\s+)?trimestre$",
        r"^excel\s+(?:de\s+)?(?:ventas?|reporte)\s+(?:del?\s+)?ano$",
        r"^exporta[r]?\s+ventas?",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_EXCEL:
            if re.search(pattern, text):
                periodo = "mes" if "mes" in text else "trimestre" if "trimestre" in text else "ano"
                return {"intent": "reporte.excel", "periodo": periodo}

        for pattern in self.PATTERNS_MEJORES:
            if re.search(pattern, text):
                periodo = "trimestre" if "trimestre" in text else "mes"
                return {"intent": "reporte.mejores_clientes", "periodo": periodo}

        for pattern in self.PATTERNS_DIA:
            if re.search(pattern, text):
                return {"intent": "reporte.dia"}

        for pattern in self.PATTERNS_MENSUAL:
            if re.search(pattern, text):
                return {"intent": "reporte.mensual"}

        for pattern in self.PATTERNS_TRIMESTRAL:
            if re.search(pattern, text):
                return {"intent": "reporte.trimestral"}

        for pattern in self.PATTERNS_SEMESTRAL:
            if re.search(pattern, text):
                return {"intent": "reporte.semestral"}

        for pattern in self.PATTERNS_ANUAL:
            if re.search(pattern, text):
                return {"intent": "reporte.anual"}

        if re.search(r"^(?:limpieza|archivar|cerrar)\s+(?:del?\s+)?ano$", text):
            return {"intent": "reporte.limpieza"}

        if re.search(r"^(?:hacer?|hacer|realiza[r]?|crea[r]?)\s+backup$", text) or text == "backup":
            return {"intent": "sistema.backup"}

        return None
