"""
Autenticacion y roles
Nimbo AI
"""
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NIMBO_DB = os.path.join(BASE_DIR, 'nimbo.db')

ROLES = ("admin", "empleado", "tecnico")
RESET_TOKEN_TTL_MINUTOS = 60

# Modulos que se pueden asignar/quitar por usuario (columna Usuario.Permisos, JSON
# array). Un admin tiene siempre todos los modulos sin importar lo que diga el campo
# (ver Usuario.tiene_permiso). Estos nombres son independientes de las categorias de
# intent del chat (core/action_engine.py CATEGORIAS_POR_ROL) - ese gate por rol sigue
# existiendo tal cual para el chat; Permisos controla que ve/usa cada usuario en el
# dashboard (sidebar) y el popup de identificacion de Caja.
MODULOS_DISPONIBLES = (
    "inventario", "ventas", "clientes", "caja", "servicio",
    "cotizaciones", "contenido", "reportes", "proveedores", "contabilidad",
)

# Permisos por defecto al crear un usuario nuevo sin especificar ninguno, segun su
# rol - mismo criterio que ya usaba el gate de rol para empleado/tecnico.
PERMISOS_DEFAULT_POR_ROL = {
    "empleado": ["inventario", "ventas", "clientes", "caja"],
    "tecnico": ["servicio"],
}


def _connect(db_path=None):
    """Si no se pasa db_path, usa la base de la empresa activa en la sesion actual
    (flask.g.empresa_db, seteado por app.py en before_request segun la empresa
    elegida en /select-empresa) - asi cada empresa queda aislada en su propio
    nimbo.db sin que cada caller tenga que pasar la ruta a mano. Si no hay
    contexto de Flask (scripts sueltos, tests sin request) o todavia no se eligio
    empresa, cae a NIMBO_DB (el nimbo.db de la raiz, compatibilidad con el modo
    single-tenant de antes de esta migracion)."""
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


def normalizar_permisos(valor):
    """Convierte lo que sea (JSON string, lista, None) a una lista de modulos
    validos (subset de MODULOS_DISPONIBLES), sin duplicados."""
    if valor is None:
        lista = []
    elif isinstance(valor, str):
        try:
            lista = json.loads(valor) if valor.strip() else []
        except (json.JSONDecodeError, ValueError):
            lista = []
    else:
        lista = list(valor)
    return sorted({m for m in lista if m in MODULOS_DISPONIBLES})


class Usuario(UserMixin):
    def __init__(self, row):
        self.id = str(row["Id"])
        self.username = row["Username"]
        self.nombre = row["Nombre"]
        self.rol = row["Rol"]
        self.activo = bool(row["Activo"])
        self.telefono = row["Telefono"] if "Telefono" in row.keys() else ""
        permisos_raw = row["Permisos"] if "Permisos" in row.keys() else None
        self.permisos = normalizar_permisos(permisos_raw)

    @property
    def is_admin(self):
        return self.rol == "admin"

    @property
    def is_tecnico(self):
        return self.rol == "tecnico"

    def tiene_permiso(self, modulo):
        """Admin siempre tiene todos los permisos, sin importar el campo Permisos."""
        return self.is_admin or modulo in self.permisos

    def get_id(self):
        return self.id


def init_usuarios(db_path=None):
    """Crea las tablas de usuarios/tokens si no existen. No crea ningun usuario:
    una instalacion nueva (tabla Usuario vacia) debe pasar por /setup."""
    conn = _connect(db_path)
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
    # Migracion: Usuario ya existia antes de agregar Telefono (necesario para que
    # Nimbo pueda avisar por WhatsApp a un tecnico cuando se le asigna una orden).
    try:
        cur.execute("ALTER TABLE Usuario ADD COLUMN Telefono TEXT")
    except sqlite3.OperationalError:
        pass
    # Migracion: Usuario ya existia antes de agregar Permisos (sistema de permisos
    # modulares por usuario, independiente del rol - ver MODULOS_DISPONIBLES).
    try:
        cur.execute("ALTER TABLE Usuario ADD COLUMN Permisos TEXT")
    except sqlite3.OperationalError:
        pass
    # Usuarios creados antes de este feature quedan con Permisos NULL (no "[]" -
    # esa distincion importa: NULL significa "nunca se configuro", no "sin ningun
    # permiso"). Se backfillean una sola vez con el default de su rol para no
    # perder de golpe el acceso a Inventario/Caja/Servicio que ya tenian por rol.
    for rol, permisos_default in PERMISOS_DEFAULT_POR_ROL.items():
        cur.execute(
            "UPDATE Usuario SET Permisos=? WHERE Rol=? AND Permisos IS NULL",
            (json.dumps(permisos_default), rol)
        )
    conn.commit()
    conn.close()


def existe_algun_usuario(db_path=None):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Usuario")
    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def existe_admin(db_path=None):
    """A diferencia de existe_algun_usuario(), solo cuenta usuarios con Rol='admin'.
    Lo usa el paso 2 del wizard de /setup para decidir si la cuenta admin ya se
    creo en un intento anterior de ese mismo paso - existe_algun_usuario() conto
    tambien empleados/tecnicos creados por otras vias (ej. el paso 6, opcional, de
    un intento de onboarding anterior que se reinicio sin completarse), lo que
    hacia que el paso 2 se saltara crear_usuario() en silencio aunque todavia no
    hubiera ningun admin."""
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Usuario WHERE Rol='admin'")
    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def get_usuario_by_id(user_id, db_path=None):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM Usuario WHERE Id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return Usuario(row) if row else None


def verify_login(username, password, db_path=None):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM Usuario WHERE Username = ?", (username.strip(),))
    row = cur.fetchone()
    conn.close()
    if not row or not row["Activo"]:
        return None
    if not check_password_hash(row["PasswordHash"], password):
        return None
    return Usuario(row)


def listar_usuarios(db_path=None):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT Id, Username, Nombre, Rol, Activo, Telefono, Permisos, CreatedAt FROM Usuario ORDER BY Id")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["Permisos"] = normalizar_permisos(r["Permisos"])
    return rows


def listar_tecnicos():
    """Tecnicos activos, para ofrecerlos al asignar una orden de servicio nueva
    (ver step service_waiting_tecnico en core/nimbo.py)."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT Id, Nombre, Username, Telefono FROM Usuario WHERE Rol='tecnico' AND Activo=1 ORDER BY Nombre")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def crear_usuario(username, password, nombre, rol, telefono="", permisos=None, db_path=None):
    if rol not in ROLES:
        raise ValueError("Rol invalido")
    username = (username or "").strip()[:80]
    nombre = (nombre or "").strip()[:120]
    telefono = (telefono or "").strip()[:30]
    if not username or not password:
        raise ValueError("Usuario y contrasena son obligatorios")
    if len(password) > 200:
        # Limite generoso (nadie escribe una contrasena de 200 caracteres a
        # mano) solo para no mandarle un string arbitrariamente largo al
        # hashing de werkzeug - no es una restriccion real de uso normal.
        raise ValueError("La contraseña es demasiado larga")
    if permisos is None:
        permisos = PERMISOS_DEFAULT_POR_ROL.get(rol, [])
    permisos = normalizar_permisos(permisos)
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Usuario (Username, PasswordHash, Nombre, Rol, Activo, Telefono, Permisos) VALUES (?,?,?,?,1,?,?)",
        (username, generate_password_hash(password), nombre, rol, telefono, json.dumps(permisos))
    )
    conn.commit()
    conn.close()


def set_permisos_usuario(user_id, permisos, db_path=None):
    permisos = normalizar_permisos(permisos)
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT Id FROM Usuario WHERE Id = ?", (user_id,))
    if not cur.fetchone():
        conn.close()
        raise ValueError("Usuario no encontrado")
    cur.execute("UPDATE Usuario SET Permisos=? WHERE Id=?", (json.dumps(permisos), user_id))
    conn.commit()
    conn.close()
    return permisos


def set_usuario_activo(user_id, activo, db_path=None):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE Usuario SET Activo=? WHERE Id=?", (1 if activo else 0, user_id))
    conn.commit()
    conn.close()


def cambiar_password_usuario(user_id, nueva_password, db_path=None):
    if not nueva_password or len(nueva_password) < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres")
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT Id FROM Usuario WHERE Id = ?", (user_id,))
    if not cur.fetchone():
        conn.close()
        raise ValueError("Usuario no encontrado")
    cur.execute("UPDATE Usuario SET PasswordHash=? WHERE Id=?",
        (generate_password_hash(nueva_password), user_id))
    conn.commit()
    conn.close()


def get_admin_activo(db_path=None):
    """Primer usuario con rol admin y activo (el sistema asume un solo admin de recuperacion)."""
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM Usuario WHERE Rol = 'admin' AND Activo = 1 ORDER BY Id LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return Usuario(row) if row else None


def crear_token_reset(user_id, db_path=None):
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(minutes=RESET_TOKEN_TTL_MINUTOS)).strftime("%Y-%m-%d %H:%M:%S")
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO PasswordResetToken (Token, UserId, ExpiresAt, Usado) VALUES (?,?,?,0)",
        (token, user_id, expires_at)
    )
    conn.commit()
    conn.close()
    return token


def validar_token_reset(token, db_path=None):
    """Retorna el Usuario asociado si el token existe, no fue usado y no expiro. Si no, None."""
    conn = _connect(db_path)
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


def usar_token_reset(token, nueva_password, db_path=None):
    """Marca el token como usado y actualiza la contrasena del usuario asociado."""
    conn = _connect(db_path)
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
