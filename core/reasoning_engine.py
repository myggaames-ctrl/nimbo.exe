"""
Reasoning Engine
Nimbo AI

Por ahora este motor solo delega la ejecución.
En el futuro será el encargado del razonamiento,
comprensión del contexto y toma de decisiones.
"""


class ReasoningEngine:

    def __init__(self, action_engine):

        self.action_engine = action_engine

    def execute(self, message):

        return self.action_engine.execute(
            message
        )
    