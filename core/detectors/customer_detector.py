"""
Customer Detector
"""


class CustomerDetector:

    def detect(self, text):

        # -----------------------------
        # Crear
        # -----------------------------

        if text.startswith("crear cliente "):

            return {
                "intent": "customer.create",
                "query": text.replace(
                    "crear cliente ",
                    ""
                ).strip()
            }

        if text.startswith("nuevo cliente "):

            return {
                "intent": "customer.create",
                "query": text.replace(
                    "nuevo cliente ",
                    ""
                ).strip()
            }

        # -----------------------------
        # Buscar
        # -----------------------------

        if text.startswith("buscar cliente "):

            return {
                "intent": "customer.search",
                "query": text.replace(
                    "buscar cliente ",
                    ""
                ).strip()
            }

        if text.startswith("cliente "):

            return {
                "intent": "customer.search",
                "query": text.replace(
                    "cliente ",
                    ""
                ).strip()
            }

        # -----------------------------
        # Listar
        # -----------------------------

        if text == "clientes":

            return {
                "intent": "customer.list",
                "query": ""
            }

        if text == "mostrar clientes":

            return {
                "intent": "customer.list",
                "query": ""
            }

        if text == "listar clientes":

            return {
                "intent": "customer.list",
                "query": ""
            }

                # -----------------------------
        # Eliminar
        # -----------------------------

        if text.startswith("eliminar cliente "):

            return {
                "intent": "customer.delete",
                "query": text.replace(
                    "eliminar cliente ",
                    ""
                ).strip()
            }

        if text.startswith("borrar cliente "):

            return {
                "intent": "customer.delete",
                "query": text.replace(
                    "borrar cliente ",
                    ""
                ).strip()
            }

        # -----------------------------
        # Editar
        # -----------------------------

        if text.startswith("editar cliente "):

            return {
                "intent": "customer.update",
                "query": text.replace(
                    "editar cliente ",
                    ""
                ).strip()
            }

        if text.startswith("renombrar cliente "):

            return {
                "intent": "customer.update",
                "query": text.replace(
                    "renombrar cliente ",
                    ""
                ).strip()
            }

        return None