"""
Configuracion del negocio (clave/valor)
Nimbo AI
"""
import sqlite3

NIMBO_DB = '/home/ictor_axtor/micocina-dashboard/nimbo.db'

DEFAULTS = {
    "negocio_nombre": "Mi Cocina",
    "moneda": "Q",
}


def _connect():
    conn = sqlite3.connect(NIMBO_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_configuracion():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Configuracion (
            Clave TEXT PRIMARY KEY,
            Valor TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_config(clave, default=None):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT Valor FROM Configuracion WHERE Clave = ?", (clave,))
    row = cur.fetchone()
    conn.close()
    if row is not None:
        return row["Valor"]
    return DEFAULTS.get(clave, default)


def set_config(clave, valor):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO Configuracion (Clave, Valor) VALUES (?, ?)
        ON CONFLICT(Clave) DO UPDATE SET Valor = excluded.Valor
    """, (clave, valor))
    conn.commit()
    conn.close()
