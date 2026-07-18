"""
Configuracion del negocio (clave/valor)
Nimbo AI
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NIMBO_DB = os.path.join(BASE_DIR, 'nimbo.db')

DEFAULTS = {
    "negocio_nombre": "Mi Cocina",
    "moneda": "Q",
}


def _connect(db_path=None):
    """Mismo criterio que core.auth._connect(db_path) y database.nimbo_db.
    nimbo_connect(db_path): sin db_path explicito, usa la empresa activa en la
    sesion actual (flask.g.empresa_db); sin contexto de Flask o sin empresa
    elegida todavia, cae a NIMBO_DB (compatibilidad con scripts sueltos y con el
    modo single-tenant de antes de esta migracion)."""
    if db_path is None:
        try:
            from flask import g
            db_path = getattr(g, "empresa_db", None)
        except RuntimeError:
            db_path = None
    if not db_path:
        db_path = NIMBO_DB
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_configuracion(db_path=None):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Configuracion (
            Clave TEXT PRIMARY KEY,
            Valor TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_config(clave, default=None, db_path=None):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT Valor FROM Configuracion WHERE Clave = ?", (clave,))
    row = cur.fetchone()
    conn.close()
    if row is not None:
        return row["Valor"]
    return DEFAULTS.get(clave, default)


def set_config(clave, valor, db_path=None):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO Configuracion (Clave, Valor) VALUES (?, ?)
        ON CONFLICT(Clave) DO UPDATE SET Valor = excluded.Valor
    """, (clave, valor))
    conn.commit()
    conn.close()
