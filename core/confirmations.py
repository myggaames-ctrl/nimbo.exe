"""
Sistema de confirmaciones de Mi Cocina AI
"""

import uuid
from datetime import datetime


class ConfirmationManager:

    def __init__(self):
        self.pending = {}

    def create(self, action, data):

        confirmation_id = str(uuid.uuid4())[:8]

        self.pending[confirmation_id] = {
            "action": action,
            "data": data,
            "created": datetime.now(),
        }

        return confirmation_id

    def exists(self, confirmation_id):

        return confirmation_id in self.pending

    def get(self, confirmation_id):

        return self.pending.get(confirmation_id)

    def remove(self, confirmation_id):

        if confirmation_id in self.pending:
            del self.pending[confirmation_id]

    def list(self):

        return self.pending
    