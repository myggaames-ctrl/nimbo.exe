"""
Action Engine
"""
from core.tool_registry import get
from core.intent_detector import IntentDetector

# Categorias de intent (prefijo antes del punto) permitidas para el rol empleado.
# Todo lo demas (proveedor, contabilidad, contenido, reporte, evento, service, budget, windows) es solo admin.
CATEGORIAS_EMPLEADO = {"inventory", "venta", "cliente", "customer"}

MENSAJE_SIN_PERMISO = "No tienes permiso para realizar esa accion. Contacta a un administrador."


class ActionEngine:

    def __init__(self):
        self.detector = IntentDetector()

    def execute(self, message: str, role: str = "admin"):
        result = self.detector.detect(message)
        if result is None:
            return None
        print("INTENT:", result)

        categoria = result["intent"].split(".")[0]
        if role != "admin" and categoria not in CATEGORIAS_EMPLEADO:
            return MENSAJE_SIN_PERMISO

        tool = get(result["intent"])
        if tool:
            # Si el resultado tiene solo query, pasar como string
            # Si tiene campos adicionales (quantity, price), pasar el dict completo
            if set(result.keys()) == {"intent", "query"}:
                return tool(result["query"])
            else:
                return tool(result)
        return None
