"""
Autenticacion y roles
Nimbo AI
"""
import secrets
import sqlite3
from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

NIMBO_DB = '/home/ictor_axtor/micocina-dashboard/nimbo.db'

ROLES = ("admin", "empleado")
RESET_TOKEN_TTL_MINUTOS = 60


def _connect():
    conn = sqlite3.connect(NIMBO_DB)
    conn.row_factory = sqlite3.Row
    return conn


class Usuario(UserMixin):
    def __init__(self, row):
        self.id = str(row["Id"])
        self.username = row["Username"]
        self.nombre = row["Nombre"]
        self.rol = row["Rol"]
        self.activo = bool(row["Activo"])

    @property
    def is_admin(self):
        return self.rol == "admin"

    def get_id(self):
        return self.id


def init_usuarios():
    """Crea las tablas de usuarios/tokens si no existen. No crea ningun usuario:
    una instalacion nueva (tabla Usuario vacia) debe pasar por /setup."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Usuario (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Username TEXT UNIQUE NOT NULL,
            PasswordHash TEXT NOT NULL,
            Nombre TEXT,
            Rol TEXT NOT NULL DEFAULT 'empleado',
            Activo INTEGER NOT NULL DEFAULT 1,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS PasswordResetToken (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Token TEXT UNIQUE NOT NULL,
            UserId INTEGER NOT NULL,
            ExpiresAt TEXT NOT NULL,
            Usado INTEGER NOT NULL DEFAULT 0,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def existe_algun_usuario():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Usuario")
    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def get_usuario_by_id(user_id):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Usuario WHERE Id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return Usuario(row) if row else None


def verify_login(username, password):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Usuario WHERE Username = ?", (username.strip(),))
    row = cur.fetchone()
    conn.close()
    if not row or not row["Activo"]:
        return None
    if not check_password_hash(row["PasswordHash"], password):
        return None
    return Usuario(row)


def listar_usuarios():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT Id, Username, Nombre, Rol, Activo, CreatedAt FROM Usuario ORDER BY Id")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def crear_usuario(username, password, nombre, rol):
    if rol not in ROLES:
        raise ValueError("Rol invalido")
    if not username or not password:
        raise ValueError("Usuario y contrasena son obligatorios")
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Usuario (Username, PasswordHash, Nombre, Rol, Activo) VALUES (?,?,?,?,1)",
        (username.strip(), generate_password_hash(password), nombre, rol)
    )
    conn.commit()
    conn.close()


def set_usuario_activo(user_id, activo):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("UPDATE Usuario SET Activo=? WHERE Id=?", (1 if activo else 0, user_id))
    conn.commit()
    conn.close()


def cambiar_password_usuario(user_id, nueva_password):
    if not nueva_password or len(nueva_password) < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres")
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT Id FROM Usuario WHERE Id = ?", (user_id,))
    if not cur.fetchone():
        conn.close()
        raise ValueError("Usuario no encontrado")
    cur.execute("UPDATE Usuario SET PasswordHash=? WHERE Id=?",
        (generate_password_hash(nueva_password), user_id))
    conn.commit()
    conn.close()


def get_admin_activo():
    """Primer usuario con rol admin y activo (el sistema asume un solo admin de recuperacion)."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Usuario WHERE Rol = 'admin' AND Activo = 1 ORDER BY Id LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return Usuario(row) if row else None


def crear_token_reset(user_id):
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(minutes=RESET_TOKEN_TTL_MINUTOS)).strftime("%Y-%m-%d %H:%M:%S")
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO PasswordResetToken (Token, UserId, ExpiresAt, Usado) VALUES (?,?,?,0)",
        (token, user_id, expires_at)
    )
    conn.commit()
    conn.close()
    return token


def validar_token_reset(token):
    """Retorna el Usuario asociado si el token existe, no fue usado y no expiro. Si no, None."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM PasswordResetToken WHERE Token = ?", (token,))
    row = cur.fetchone()
    if not row or row["Usado"]:
        conn.close()
        return None
    if datetime.now() > datetime.strptime(row["ExpiresAt"], "%Y-%m-%d %H:%M:%S"):
        conn.close()
        return None
    cur.execute("SELECT * FROM Usuario WHERE Id = ?", (row["UserId"],))
    user_row = cur.fetchone()
    conn.close()
    return Usuario(user_row) if user_row else None


def usar_token_reset(token, nueva_password):
    """Marca el token como usado y actualiza la contrasena del usuario asociado."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM PasswordResetToken WHERE Token = ?", (token,))
    row = cur.fetchone()
    if not row or row["Usado"]:
        conn.close()
        return False
    if datetime.now() > datetime.strptime(row["ExpiresAt"], "%Y-%m-%d %H:%M:%S"):
        conn.close()
        return False
    cur.execute("UPDATE Usuario SET PasswordHash=? WHERE Id=?",
        (generate_password_hash(nueva_password), row["UserId"]))
    cur.execute("UPDATE PasswordResetToken SET Usado=1 WHERE Token=?", (token,))
    conn.commit()
    conn.close()
    return True
