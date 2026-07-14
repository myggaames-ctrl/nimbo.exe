import re
import unicodedata


def normalize(text):
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("utf-8").lower().strip()


class CuentaCobrarDetector:

    PATTERNS_LISTAR = [
        r"^(?:ver\s+)?cuentas\s+por\s+cobrar$",
        r"^cuentas\s+pendientes$",
        r"^deudas\s+pendientes$",
    ]

    PATTERNS_VENCIDAS = [
        r"^cuentas\s+vencidas$",
        r"^deudas\s+vencidas$",
    ]

    # Se revisan antes que PATTERNS_CREAR/PAGAR: son consultas, no crean ni cobran nada,
    # aunque tambien contienen la palabra "debe" ("cuanto debe X").
    PATTERNS_CONSULTA = [
        r"^cuanto\s+debe\s+(.+)$",
        r"^cuanta\s+deuda\s+tiene\s+(.+)$",
        r"^deuda\s+de\s+(.+)$",
        r"^cuentas?\s+por\s+cobrar\s+de\s+(.+)$",
    ]

    PATTERNS_PAGO = [
        r"^(.+?)\s+(?:pago|abono)\s+q?\s*(\d+(?:\.\d+)?)$",
        r"^(?:pago|abono)\s+de\s+(.+?)\s+(?:por\s+)?q?\s*(\d+(?:\.\d+)?)$",
    ]

    # Con descripcion ("... por licuadora") y sin ella. Se revisan al final: son las
    # mas genericas (cualquier "X debe Q..." que no matcheo arriba cae aqui).
    PATTERNS_CREAR = [
        r"^(.+?)\s+debe\s+q?\s*(\d+(?:\.\d+)?)\s+por\s+(.+)$",
        r"^(.+?)\s+debe\s+q?\s*(\d+(?:\.\d+)?)$",
    ]

    def detect(self, text: str):
        text = normalize(text)

        for pattern in self.PATTERNS_LISTAR:
            if re.search(pattern, text):
                return {"intent": "cuentacobrar.listar"}

        for pattern in self.PATTERNS_VENCIDAS:
            if re.search(pattern, text):
                return {"intent": "cuentacobrar.vencidas"}

        for pattern in self.PATTERNS_CONSULTA:
            match = re.search(pattern, text)
            if match:
                return {"intent": "cuentacobrar.consultar", "cliente_query": match.group(1).strip()}

        for pattern in self.PATTERNS_PAGO:
            match = re.search(pattern, text)
            if match:
                cliente_query, monto = match.groups()
                return {"intent": "cuentacobrar.pagar", "cliente_query": cliente_query.strip(), "monto": float(monto)}

        for pattern in self.PATTERNS_CREAR:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                cliente_query, monto = groups[0].strip(), float(groups[1])
                descripcion = groups[2].strip() if len(groups) > 2 else "Deuda general"
                return {
                    "intent": "cuentacobrar.crear",
                    "cliente_query": cliente_query,
                    "monto": monto,
                    "descripcion": descripcion
                }

        return None
