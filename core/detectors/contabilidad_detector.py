import re
import unicodedata

def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()

class ContabilidadDetector:

    PATTERNS_GASTO = [
        r"^(?:registra[r]?|agrega[r]?|anota[r]?)\s+gasto\s+(?:de\s+)?(.+?)\s+[Qq]?(\d+\.?\d*)$",
        r"^gasto\s+(?:de\s+)?(.+?)\s+[Qq]?(\d+\.?\d*)$",
        r"^gasto\s+(.+?)\s+(\d+\.?\d*)$",
        r"^pague?\s+(?:el?\s+|la\s+)?(.+?)\s+[Qq]?(\d+\.?\d*)$",
        r"^gaste?\s+[Qq]?(\d+\.?\d*)\s+(?:en\s+)?(.+)$",
        r"^gaste?\s+(\d+\.?\d*)\s+(?:en\s+)?(.+)$",
        r"^(.+?)\s+costo\s+[Qq]?(\d+\.?\d*)$",
        r"^costo\s+(?:de\s+)?(.+?)\s+[Qq]?(\d+\.?\d*)$",
    ]

    PATTERNS_BALANCE = [
        r"^balance\s+(?:del?\s+)?mes$",
        r"^(?:como\s+)?(?:vamos|estamos)\s+(?:de\s+)?(?:dinero|caja|balance)$",
        r"^flujo\s+(?:de\s+)?caja$",
        r"^estado\s+(?:de\s+)?cuenta$",
        r"^contabilidad\s+(?:del?\s+)?mes$",
    ]

    PATTERNS_GASTOS_LIST = [
        r"^(?:ver|lista[r]?|mis)\s+gastos?$",
        r"^gastos?\s+(?:del?\s+)?mes$",
        r"^cuanto\s+(?:gaste|hemos\s+gastado)\s+(?:este\s+)?mes$",
    ]

    PATTERNS_INVENTARIO_VALOR = [
        r"^valor\s+(?:del?\s+)?inventario$",
        r"^cuanto\s+(?:vale|tengo\s+invertido)\s+(?:en\s+)?(?:el\s+)?inventario$",
        r"^inventario\s+(?:en\s+)?quetzales$",
    ]

    PATTERNS_COMPARACION = [
        r"^comparacion\s+(?:de\s+)?(?:ventas?\s+)?(?:mes\s+a\s+mes|meses?)$",
        r"^como\s+(?:hemos\s+)?crecido\s+(?:los\s+ultimos?\s+meses?)?$",
        r"^evolucion\s+(?:de\s+)?ventas?$",
        r"^tendencia\s+(?:de\s+)?ventas?$",
        r"^ventas?\s+(?:de\s+)?(?:los\s+)?ultimos?\s+(?:\d+\s+)?meses?$",
        r"^historial\s+(?:de\s+)?ventas?$",
    ]

    PATTERNS_EXCEL_CONTABILIDAD = [
        r"^excel\s+(?:de\s+)?contabilidad$",
        r"^reporte\s+(?:contable|de\s+contabilidad)\s+(?:del?\s+)?mes$",
        r"^exporta[r]?\s+contabilidad$",
        r"^excel\s+(?:del?\s+)?balance$",
    ]

    PATTERNS_ANALISIS_COMPLETO = [
        r"^analisis\s+(?:completo|general)\s+(?:de\s+)?(?:la\s+)?empresa$",
        r"^como\s+va\s+(?:la\s+)?empresa$",
        r"^analiza\s+(?:la\s+)?empresa$",
        r"^reporte\s+(?:general|completo)\s+(?:de\s+)?(?:la\s+)?empresa$",
        r"^estado\s+(?:general|completo)\s+(?:del?\s+)?negocio$",
        r"^como\s+estamos?\s+(?:como\s+empresa)?$",
    ]

    PATTERNS_EQUILIBRIO = [
        r"^punto\s+(?:de\s+)?equilibrio$",
        r"^cuanto\s+(?:necesito|debo)\s+vender\s+(?:para\s+)?(?:cubrir|pagar)\s+(?:los\s+)?gastos?$",
        r"^cuanto\s+necesito\s+vender\s+al\s+mes$",
        r"^cuanto\s+vender\s+para\s+no\s+perder$",
    ]

    PATTERNS_MARGEN = [
        r"^margen\s+(?:de\s+)?ganancia\s+(?:de\s+)?productos?$",
        r"^margen\s+(?:de\s+)?(?:ganancia|productos?)$",
        r"^(?:que|cuales?)\s+productos?\s+(?:dejan|son)\s+mas\s+(?:rentables?|ganancias?)$",
        r"^rentabilidad\s+(?:de\s+)?productos?$",
        r"^cuanto\s+gano\s+(?:por|en)\s+(?:cada\s+)?producto$",
        r"^margen\s+productos?$",
    ]

    PATTERNS_SUGERENCIAS_PRECIOS = [
        r"^analiza\s+(?:mis\s+)?precios?$",
        r"^analisis\s+de\s+precios?$",
        r"^sugerenc(?:ia|ias)\s+de\s+precios?$",
        r"^sugiere\s+precios?$",
        r"^revisa\s+(?:mis\s+)?precios?$",
        r"^ajuste\s+de\s+precios?$",
        r"^que\s+precios?\s+(?:debo|deberia)\s+(?:subir|ajustar|cambiar)$",
        r"^estan\s+bien\s+mis\s+precios?$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_BALANCE:
            if re.search(pattern, text):
                return {"intent": "contabilidad.balance"}

        for pattern in self.PATTERNS_GASTOS_LIST:
            if re.search(pattern, text):
                return {"intent": "contabilidad.gastos"}

        for pattern in self.PATTERNS_INVENTARIO_VALOR:
            if re.search(pattern, text):
                return {"intent": "contabilidad.inventario_valor"}

        for pattern in self.PATTERNS_COMPARACION:
            if re.search(pattern, text):
                return {"intent": "contabilidad.comparacion"}

        for pattern in self.PATTERNS_EXCEL_CONTABILIDAD:
            if re.search(pattern, text):
                return {"intent": "contabilidad.excel"}

        for pattern in self.PATTERNS_ANALISIS_COMPLETO:
            if re.search(pattern, text):
                return {"intent": "contabilidad.analisis_completo"}

        for pattern in self.PATTERNS_EQUILIBRIO:
            if re.search(pattern, text):
                return {"intent": "contabilidad.equilibrio"}

        for pattern in self.PATTERNS_MARGEN:
            if re.search(pattern, text):
                return {"intent": "contabilidad.margen"}

        for pattern in self.PATTERNS_SUGERENCIAS_PRECIOS:
            if re.search(pattern, text):
                return {"intent": "contabilidad.sugerencias_precios"}

        for pattern in self.PATTERNS_GASTO:
            match = re.search(pattern, text)
            if match:
                grupos = match.groups()
                if pattern.startswith(r"^gaste"):
                    return {"intent": "contabilidad.gasto", "monto": float(grupos[0]), "descripcion": grupos[1].strip()}
                return {"intent": "contabilidad.gasto", "descripcion": grupos[0].strip(), "monto": float(grupos[1])}

        return None
