"""
Inventory Service
Mi Cocina AI
"""


class InventoryService:

    def search(self, text):
        # Delegado a database.aronium.get_products(), que ademas de la busqueda
        # exacta (LIKE) intenta busqueda difusa por similitud si esta no encuentra
        # nada, para tolerar errores tipograficos en el nombre del producto.
        from database.aronium import get_products
        return get_products(search=text)

    def search_barcode(self, barcode):
        # Delegado a database.aronium.get_product_by_code() (catalogo propio
        # Producto/Stock de nimbo.db, ver migracion en database/aronium.py).
        from database.aronium import get_product_by_code
        return get_product_by_code(barcode)

    def list(self, limit=20):
        # Delegado a database.aronium.get_products(), mismo criterio (sin filtro
        # de Activo) que tenia el SELECT directo contra Aronium.
        from database.aronium import get_products
        return get_products(limit=limit)
