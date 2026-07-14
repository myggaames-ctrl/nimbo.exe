import re
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()


class CuentaPagarDetector:

    PATTERNS_LISTAR = [
        r"^(?:ver\s+)?cuentas\s+por\s+pagar$",
        r"^pagos\s+pendientes$",
        r"^deudas\s+(?:a|con)\s+proveedores$",
    ]

    PATTERNS_VENCIDOS = [
        r"^pagos\s+vencidos$",
        r"^cuentas\s+por\s+pagar\s+vencidas$",
    ]

    # Se revisan antes que PATTERNS_CREAR/PAGAR: son consultas, no crean ni pagan nada,
    # aunque tambien contienen la palabra "debo" ("cuanto le debo a X").
    PATTERNS_CONSULTA = [
        r"^cuanto\s+le\s+debo\s+a\s+(.+)$",
        r"^cuanto\s+debo\s+a\s+(.+)$",
        r"^deuda\s+con\s+(.+)$",
        r"^cuentas?\s+por\s+pagar\s+a\s+(.+)$",
    ]

    PATTERNS_PAGO = [
        r"^(?:le\s+)?pague\s+q?\s*(\d+(?:\.\d+)?)\s+a\s+(.+)$",
        r"^pago\s+de\s+q?\s*(\d+(?:\.\d+)?)\s+a\s+(.+)$",
    ]

    # Con descripcion ("... por repuestos") y sin ella.
    PATTERNS_CREAR = [
        r"^(?:le\s+)?debo\s+q?\s*(\d+(?:\.\d+)?)\s+a\s+(.+?)\s+por\s+(.+)$",
        r"^(?:le\s+)?debo\s+q?\s*(\d+(?:\.\d+)?)\s+a\s+(.+)$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_LISTAR:
            if re.search(pattern, text):
                return {"intent": "cuentapagar.listar"}

        for pattern in self.PATTERNS_VENCIDOS:
            if re.search(pattern, text):
                return {"intent": "cuentapagar.vencidas"}

        for pattern in self.PATTERNS_CONSULTA:
            match = re.search(pattern, text)
            if match:
                return {"intent": "cuentapagar.consultar", "proveedor_query": match.group(1).strip()}

        for pattern in self.PATTERNS_PAGO:
            match = re.search(pattern, text)
            if match:
                monto, proveedor_query = match.groups()
                return {"intent": "cuentapagar.pagar", "proveedor_query": proveedor_query.strip(), "monto": float(monto)}

        for pattern in self.PATTERNS_CREAR:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                monto, proveedor_query = float(groups[0]), groups[1].strip()
                descripcion = groups[2].strip() if len(groups) > 2 else "Deuda general"
                return {
                    "intent": "cuentapagar.crear",
                    "proveedor_query": proveedor_query,
                    "monto": monto,
                    "descripcion": descripcion
                }

        return None
