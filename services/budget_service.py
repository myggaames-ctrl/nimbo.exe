"""
Budget Service
Nimbo AI
"""

import sqlite3
from pathlib import Path
from datetime import datetime


DB = Path(__file__).parent.parent / "database" / "nimbo.db"


class BudgetService:

    def connect(self):

        conn = sqlite3.connect(DB)

        conn.row_factory = sqlite3.Row

        return conn

    def initialize(self):

        conn = self.connect()

        cur = conn.cursor()

        cur.execute("""

        CREATE TABLE IF NOT EXISTS Budget(

            Id INTEGER PRIMARY KEY AUTOINCREMENT,

            CustomerId INTEGER,

            Status TEXT,

            CreatedAt TEXT,

            UpdatedAt TEXT

        )

        """)

        cur.execute("""

        CREATE TABLE IF NOT EXISTS BudgetItem(

            Id INTEGER PRIMARY KEY AUTOINCREMENT,

            BudgetId INTEGER NOT NULL,

            ProductId TEXT NOT NULL,

            ProductName TEXT NOT NULL,

            Quantity REAL NOT NULL,

            UnitPrice REAL NOT NULL,
                    
            Cost REAL NOT NULL,

            Subtotal REAL NOT NULL

        )

        """)

        conn.commit()

        conn.close()

    def create(self, customer_id):

        self.initialize()

        conn = self.connect()

        cur = conn.cursor()

        now = datetime.now().isoformat()

        cur.execute("""

        INSERT INTO Budget(

            CustomerId,
            Status,
            CreatedAt,
            UpdatedAt

        )

        VALUES(?,?,?,?)

        """, (

        customer_id,
        "EN_EDICION",
        now,
        now

        ))

        budget_id = cur.lastrowid

        conn.commit()

        conn.close()

        return budget_id
    
        # --------------------------------------------------
    # OBTENER PRESUPUESTO
    # --------------------------------------------------

    def get(self, budget_id):

        self.initialize()

        conn = self.connect()

        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM Budget

        WHERE Id = ?

        LIMIT 1

        """, (budget_id,))

        row = cur.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    # --------------------------------------------------
    # AGREGAR PRODUCTO
    # --------------------------------------------------

    def add_item(

        self,
        budget_id,
        product

    ):

        self.initialize()

        conn = self.connect()

        cur = conn.cursor()

        quantity = 1

        unit_price = product["Price"]

        subtotal = quantity * unit_price

        cur.execute("""

        INSERT INTO BudgetItem(

            BudgetId,
            ProductId,
            ProductName,
            Quantity,
            UnitPrice,
            Cost,
            Subtotal

        )

        VALUES(?,?,?,?,?,?,?)

        """, (

            budget_id,
            str(product["Id"]),
            product["Name"],
            quantity,
            unit_price,
            product["Cost"],
            subtotal

        ))

        conn.commit()

        conn.close()

        return True
    
    # --------------------------------------------------
    # LISTAR PRODUCTOS DEL PRESUPUESTO
    # --------------------------------------------------

    def items(self, budget_id):

        self.initialize()

        conn = self.connect()

        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM BudgetItem

        WHERE BudgetId = ?

        ORDER BY Id

        """, (budget_id,))

        rows = [dict(r) for r in cur.fetchall()]

        conn.close()

        return rows