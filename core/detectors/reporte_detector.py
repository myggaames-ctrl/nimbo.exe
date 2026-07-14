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

    PATTERNS_PATRONES = [
        r"^analiza\s+(?:mis\s+)?patrones?\s+(?:de\s+)?venta[s]?$",
        r"^analisis\s+de\s+patrones?\s+(?:de\s+)?venta[s]?$",
        r"^patrones?\s+de\s+venta[s]?$",
    ]

    PATTERNS_CUANDO_VENDO_MAS = [
        r"^cuando\s+vendo\s+mas$",
        r"^cuales?\s+son\s+mis\s+(?:dias|horas)\s+pico$",
        r"^dias?\s+(?:y\s+horas?\s+)?pico\s+de\s+venta[s]?$",
        r"^mejor\s+hora\s+para\s+vender$",
    ]

    PATTERNS_PROXIMA_COMPRA = [
        r"^proxima\s+compra\s+de\s+(.+)$",
        r"^cuando\s+(?:vuelve|va)\s+a\s+comprar\s+(.+)$",
        r"^cuando\s+compra\s+de\s+nuevo\s+(.+)$",
    ]

    # Metas semanales de ventas (ver database.aronium.set_meta_semanal /
    # get_progreso_meta_semanal). Se revisa antes que PATTERNS_META_PROGRESO
    # porque este exige un monto (digitos) y es mas especifico.
    PATTERNS_META_DEFINIR = [
        r"^meta\s+semanal\s+(?:de\s+|es\s+)?q?\s*(\d+(?:\.\d+)?)$",
        r"^(?:define|definir|pon|establece)\s+(?:la\s+)?meta\s+semanal\s+(?:de\s+|en\s+)?q?\s*(\d+(?:\.\d+)?)$",
        r"^nueva\s+meta\s+semanal\s+(?:de\s+)?q?\s*(\d+(?:\.\d+)?)$",
    ]

    PATTERNS_META_FALTA = [
        r"^cuanto\s+me\s+falta\s+para\s+(?:la\s+)?meta(?:\s+semanal)?$",
        r"^cuanto\s+falta\s+para\s+(?:la\s+)?meta(?:\s+semanal)?$",
        r"^que\s+me\s+falta\s+para\s+(?:la\s+)?meta(?:\s+semanal)?$",
    ]

    PATTERNS_META_PROGRESO = [
        r"^como\s+voy\s+esta\s+semana$",
        r"^como\s+vamos\s+esta\s+semana$",
        r"^meta\s+(?:de\s+)?(?:la\s+)?semana$",
        r"^meta\s+semanal$",
        r"^progreso\s+(?:de\s+)?(?:la\s+)?meta(?:\s+semanal)?$",
        r"^como\s+voy\s+(?:con\s+)?(?:la\s+)?meta(?:\s+semanal)?$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_META_DEFINIR:
            match = re.search(pattern, text)
            if match:
                return {"intent": "reporte.meta_definir", "monto": float(match.group(1))}

        for pattern in self.PATTERNS_META_FALTA:
            if re.search(pattern, text):
                return {"intent": "reporte.meta_falta"}

        for pattern in self.PATTERNS_META_PROGRESO:
            if re.search(pattern, text):
                return {"intent": "reporte.meta_progreso"}

        for pattern in self.PATTERNS_PROXIMA_COMPRA:
            match = re.search(pattern, text)
            if match:
                return {"intent": "reporte.proxima_compra", "query": match.group(1).strip()}

        for pattern in self.PATTERNS_PATRONES:
            if re.search(pattern, text):
                return {"intent": "reporte.patrones_ventas"}

        for pattern in self.PATTERNS_CUANDO_VENDO_MAS:
            if re.search(pattern, text):
                return {"intent": "reporte.cuando_vendo_mas"}

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
