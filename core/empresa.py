"""
Empresas (multi-tenant)
Nimbo AI

Cada empresa tiene su propio nimbo.db, aislado del resto, en
data/empresas/<slug>/nimbo.db. Este modulo maneja el "maestro" - un unico
nimbo_master.db en la raiz del proyecto, con la tabla Empresa (Nombre, Slug,
DbPath) - que le dice a app.py a que archivo conectarse segun la empresa que el
usuario elija en /select-empresa. El maestro en si NO tiene datos de negocio,
solo el directorio de empresas.
"""
import os
import re
import sqlite3
import unicodedata

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_DB = os.path.join(BASE_DIR, "nimbo_master.db")


def _connect_master():
    conn = sqlite3.connect(MASTER_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_master():
    """Crea nimbo_master.db y la tabla Empresa si no existen. Idempotente -
    se llama una vez al arrancar app.py, sin importar cuantas empresas haya."""
    conn = _connect_master()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Empresa (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Nombre TEXT NOT NULL,
            Slug TEXT UNIQUE NOT NULL,
            DbPath TEXT NOT NULL,
            Activo INTEGER DEFAULT 1,
            CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_empresa_by_slug(slug):
    conn = _connect_master()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Empresa WHERE Slug = ?", (slug,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def listar_empresas():
    """Solo empresas activas (Activo=1), para la lista de /select-empresa."""
    conn = _connect_master()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Empresa WHERE Activo = 1 ORDER BY Nombre")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_db_path(slug):
    """Path ABSOLUTO al nimbo.db de la empresa (Empresa.DbPath se guarda
    relativo a BASE_DIR, ej. "data/empresas/mi-cocina/nimbo.db") - listo para
    pasarle directo a sqlite3.connect() o guardarlo en flask.g.empresa_db.
    None si el slug no existe."""
    empresa = get_empresa_by_slug(slug)
    if not empresa:
        return None
    return os.path.join(BASE_DIR, empresa["DbPath"])


def _generar_slug(nombre):
    """minusculas, sin tildes, espacios a guiones, sin caracteres especiales.
    Ej. "Surti La Unión" -> "surti-la-union"."""
    texto = unicodedata.normalize("NFD", nombre).encode("ascii", "ignore").decode("utf-8")
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9\s-]", "", texto)
    texto = re.sub(r"[\s_-]+", "-", texto).strip("-")
    return texto or "empresa"


def crear_empresa(nombre, slug=None):
    """Crea una empresa nueva de punta a punta:
    1. Genera el slug automaticamente desde el nombre (o usa el que se pase,
       saneado igual) - si ya existe, le agrega un numero (-2, -3...) para
       que el Slug siga siendo unico.
    2. Crea la carpeta data/empresas/<slug>/.
    3. Inserta la fila en Empresa (master DB).
    4. Inicializa TODAS las tablas de esa empresa contra su nimbo.db propio,
       llamando a cada funcion init_* de database/nimbo_db.py y core/auth.py
       con el db_path nuevo - la empresa arranca con las tablas creadas pero
       vacias (sin usuarios, sin productos), lista para el primer admin.
    Retorna un dict con id/nombre/slug/db_path (relativo)."""
    if not nombre or not nombre.strip():
        raise ValueError("El nombre de la empresa es obligatorio")

    slug_base = _generar_slug(slug) if slug else _generar_slug(nombre)
    slug_final = slug_base
    contador = 2
    while get_empresa_by_slug(slug_final):
        slug_final = f"{slug_base}-{contador}"
        contador += 1

    carpeta_relativa = f"data/empresas/{slug_final}"
    carpeta_absoluta = os.path.join(BASE_DIR, carpeta_relativa)
    os.makedirs(carpeta_absoluta, exist_ok=True)

    db_path_relativo = f"{carpeta_relativa}/nimbo.db"
    db_path_absoluto = os.path.join(BASE_DIR, db_path_relativo)

    conn = _connect_master()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Empresa (Nombre, Slug, DbPath) VALUES (?, ?, ?)",
        (nombre.strip(), slug_final, db_path_relativo)
    )
    empresa_id = cur.lastrowid
    conn.commit()
    conn.close()

    _inicializar_tablas_empresa(db_path_absoluto)

    return {
        "id": empresa_id,
        "nombre": nombre.strip(),
        "slug": slug_final,
        "db_path": db_path_relativo,
    }


def _inicializar_tablas_empresa(db_path_absoluto):
    """Llama a todas las funciones init_* de core/auth.py y database/nimbo_db.py
    con el db_path de la empresa nueva - cada una crea sus propias tablas (CREATE
    TABLE IF NOT EXISTS) directo contra ese archivo, que a esta altura ya existe
    vacio (sqlite3.connect crea el archivo si no existe). Imports adentro de la
    funcion (no al inicio del modulo) para evitar import circular con
    database/nimbo_db.py y core/auth.py, que en teoria podrian llegar a
    necesitar algo de core/ en el futuro."""
    from core.auth import init_usuarios
    from core.configuracion import init_configuracion
    from database.nimbo_db import (
        init_productos, init_cotizaciones, init_caja, init_descuentos,
        init_garantias, init_combos, init_unidades_medida, init_puntos,
        init_codigos_barras, init_grupos_cliente, init_fotos_servicio,
        init_servicio_tecnico_ext, init_informes_revision, init_tarifas_mano_obra,
        init_cuentas_cobrar, init_cuentas_pagar, init_pagos_fijos_ext,
        init_metas_semanales, init_venta_cobrador_ext, init_reembolsos,
        init_venta_metodo_pago_ext, init_ajuste_pos,
    )

    init_usuarios(db_path_absoluto)
    init_configuracion(db_path_absoluto)
    for init_fn in (
        init_productos, init_cotizaciones, init_caja, init_descuentos,
        init_garantias, init_combos, init_unidades_medida, init_puntos,
        init_codigos_barras, init_grupos_cliente, init_fotos_servicio,
        init_servicio_tecnico_ext, init_informes_revision, init_tarifas_mano_obra,
        init_cuentas_cobrar, init_cuentas_pagar, init_pagos_fijos_ext,
        init_metas_semanales, init_venta_cobrador_ext, init_reembolsos,
        init_venta_metodo_pago_ext, init_ajuste_pos,
    ):
        init_fn(db_path_absoluto)
