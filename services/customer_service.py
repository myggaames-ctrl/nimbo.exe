"""
Customer Service
Nimbo AI
"""

import sqlite3
from pathlib import Path
from datetime import datetime


DB = Path(__file__).parent.parent / "database" / "nimbo.db"


class CustomerService:

    def connect(self):

        conn = sqlite3.connect(DB)

        conn.row_factory = sqlite3.Row

        return conn

    def initialize(self):

        conn = self.connect()

        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS Customer(

            Id INTEGER PRIMARY KEY AUTOINCREMENT,

            Name TEXT NOT NULL,

            Phone TEXT,

            Email TEXT,

            Address TEXT,

            Notes TEXT,

            CreatedAt TEXT

        )
        """)

        conn.commit()

        conn.close()

    # --------------------------------------------------
    # CREAR
    # --------------------------------------------------

    def create(
        self,
        name,
        phone="",
        email="",
        address="",
        notes=""
    ):

        self.initialize()

        conn = self.connect()

        cur = conn.cursor()

        cur.execute("""

        INSERT INTO Customer(

            Name,
            Phone,
            Email,
            Address,
            Notes,
            CreatedAt

        )

        VALUES(?,?,?,?,?,?)

        """, (

            name,
            phone,
            email,
            address,
            notes,
            datetime.now().isoformat()

        ))

        conn.commit()

        conn.close()

        return True

    # --------------------------------------------------
    # BUSCAR
    # --------------------------------------------------

    def search(self, text):

        self.initialize()

        conn = self.connect()

        cur = conn.cursor()

        cur.execute("""

        SELECT

            *

        FROM Customer

        WHERE Name LIKE ?

        ORDER BY Name

        """, (f"%{text}%",))

        rows = [
            dict(r)
            for r in cur.fetchall()
        ]

        conn.close()

        return rows
    
        # --------------------------------------------------
    # OBTENER POR NOMBRE
    # --------------------------------------------------

    def get_by_name(self, name):

        self.initialize()

        conn = self.connect()

        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM Customer

        WHERE Name LIKE ?

        LIMIT 1

        """, (f"%{name}%",))

        row = cur.fetchone()

        conn.close()

        if row:

            return dict(row)

        return None

    # --------------------------------------------------
    # LISTAR
    # --------------------------------------------------

    def list(self):

        self.initialize()

        conn = self.connect()

        cur = conn.cursor()

        cur.execute("""

        SELECT *

        FROM Customer

        ORDER BY Name

        """)

        rows = [
            dict(r)
            for r in cur.fetchall()
        ]

        conn.close()

        return rows
    
    # --------------------------------------------------
    # ELIMINAR
    # --------------------------------------------------

    def delete(self, text):

        self.initialize()

        conn = self.connect()

        cur = conn.cursor()

        cur.execute("""

        DELETE FROM Customer

        WHERE Name LIKE ?

        """, (f"%{text}%",))

        deleted = cur.rowcount

        conn.commit()

        conn.close()

        return deleted
    
        # --------------------------------------------------
    # EDITAR
    # --------------------------------------------------

    def update(
        self,
        old_name,
        new_name
    ):

        self.initialize()

        conn = self.connect()

        cur = conn.cursor()

        cur.execute("""

        UPDATE Customer

        SET Name = ?

        WHERE Name LIKE ?

        """, (

            new_name,
            f"%{old_name}%"

        ))

        updated = cur.rowcount

        conn.commit()

        conn.close()

        return updated