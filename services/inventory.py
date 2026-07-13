"""
Inventory Service
Mi Cocina AI
"""

import sqlite3
import os

ARONIUM_DB = os.environ.get(
    "ARONIUM_DB",
    "/mnt/c/Users/Victor Paxtor/AppData/Local/Aronium/Data/pos.db"
)


class InventoryService:

    def __init__(self):
        self.db = ARONIUM_DB

    def connect(self):
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        return conn

    def search(self, text):
        # Delegado a database.aronium.get_products(), que ademas de la busqueda
        # exacta (LIKE) intenta busqueda difusa por similitud si esta no encuentra
        # nada, para tolerar errores tipograficos en el nombre del producto.
        from database.aronium import get_products
        return get_products(search=text)

    def search_barcode(self, barcode):

        conn = self.connect()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                Product.Id,
                Product.Name,
                Product.Code,
                Product.Price,
                Product.Cost,
                IFNULL(Stock.Quantity,0) AS Stock
            FROM Product
            LEFT JOIN Stock
                ON Stock.ProductId = Product.Id
            WHERE Product.Code = ?
            LIMIT 1
        """, (barcode,))

        row = cur.fetchone()

        conn.close()

        if row:
            return dict(row)

    def list(self, limit=20):

        conn = self.connect()

        cur = conn.cursor()

        cur.execute("""

            SELECT
                Name,
                Code,
                Price,
                Cost,
                IFNULL(SUM(Stock.Quantity),0) AS Stock

            FROM Product

            LEFT JOIN Stock
                ON Stock.ProductId = Product.Id

            GROUP BY
                Product.Id

            ORDER BY Name

            LIMIT ?

        """, (limit,))

        rows = [
            dict(r)
            for r in cur.fetchall()
        ]

        conn.close()

        return rows
