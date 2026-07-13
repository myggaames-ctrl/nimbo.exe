"""
Budget Detector
"""


class BudgetDetector:

    def detect(self, text):

        if text.startswith("crear presupuesto para "):

            return {
                "intent": "budget.create",
                "query": text.replace(
                    "crear presupuesto para ",
                    ""
                ).strip()
            }

        if text.startswith("nuevo presupuesto para "):

            return {
                "intent": "budget.create",
                "query": text.replace(
                    "nuevo presupuesto para ",
                    ""
                ).strip()
            }

            # -----------------------------
        # Mostrar presupuesto
        # -----------------------------

        if text == "presupuesto":

            return {
                "intent": "budget.show",
                "query": ""
            }

        if text == "mostrar presupuesto":

            return {
                "intent": "budget.show",
                "query": ""
            }

            # -----------------------------
        # Agregar producto
        # -----------------------------

        if text.startswith("agregar "):

            return {
                "intent": "budget.add_item",
                "query": text.replace(
                    "agregar ",
                    ""
                ).strip()
            }
        
        return None