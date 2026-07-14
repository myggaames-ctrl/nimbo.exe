import difflib
import sqlite3
from datetime import datetime

DB_PATH = '/mnt/c/Users/Victor Paxtor/AppData/Local/Aronium/Data/pos.db'

UMBRAL_SIMILITUD_PRODUCTO = 0.6

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _buscar_productos_similares(search, limit=100, umbral=UMBRAL_SIMILITUD_PRODUCTO):
    """Busqueda difusa por similitud de nombres (difflib), usada como respaldo
    cuando la busqueda exacta (LIKE) no encuentra ningun producto. Compara la
    busqueda tanto contra el nombre completo del producto como contra cada
    palabra individual del nombre, para que un typo en una sola palabra de un
    nombre compuesto (ej: "cuchila" en "Cuchilla oster original") tambien matchee."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.Id, p.Name, p.Code, p.Price, p.Cost,
               IFNULL(SUM(s.Quantity),0) AS Stock
        FROM Product p
        LEFT JOIN Stock s ON p.Id = s.ProductId
        WHERE p.IsEnabled=1
        GROUP BY p.Id
    """)
    todos = [dict(r) for r in cur.fetchall()]
    conn.close()

    busqueda = search.lower().strip()
    if not todos or not busqueda:
        return []

    candidatos = []
    for p in todos:
        nombre = (p["Name"] or "").lower().strip()
        if not nombre:
            continue
        ratio_completo = difflib.SequenceMatcher(None, busqueda, nombre).ratio()
        ratio_palabras = max(
            (difflib.SequenceMatcher(None, busqueda, palabra).ratio() for palabra in nombre.split()),
            default=0
        )
        ratio = max(ratio_completo, ratio_palabras)
        if ratio >= umbral:
            candidatos.append((ratio, p))

    candidatos.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in candidatos[:limit]]

def get_products(search="", limit=100):
    conn = connect()
    cur = conn.cursor()
    if search:
        cur.execute("""
            SELECT p.Id, p.Name, p.Code, p.Price, p.Cost,
                   IFNULL(SUM(s.Quantity),0) AS Stock
            FROM Product p
            LEFT JOIN Stock s ON p.Id = s.ProductId
            WHERE p.Name LIKE ? OR p.Code LIKE ?
            GROUP BY p.Id ORDER BY p.Name LIMIT ?
        """, (f"%{search}%", f"%{search}%", limit))
    else:
        cur.execute("""
            SELECT p.Id, p.Name, p.Code, p.Price, p.Cost,
                   IFNULL(SUM(s.Quantity),0) AS Stock
            FROM Product p
            LEFT JOIN Stock s ON p.Id = s.ProductId
            GROUP BY p.Id ORDER BY p.Name LIMIT ?
        """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    # Si la busqueda exacta no encontro nada, se intenta por similitud de cadenas
    # (typos, letras faltantes/de mas) antes de devolver una lista vacia.
    if not rows and search:
        rows = _buscar_productos_similares(search, limit=limit)

    return rows

def get_product_by_code(code):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.Id, p.Name, p.Code, p.Price, p.Cost, p.Description,
               IFNULL(SUM(s.Quantity),0) AS Stock
        FROM Product p
        LEFT JOIN Stock s ON p.Id = s.ProductId
        WHERE p.Code = ?
        GROUP BY p.Id LIMIT 1
    """, (code,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_product_by_id(product_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.Id, p.Name, p.Code, p.Price, p.Cost,
               IFNULL(SUM(s.Quantity),0) AS Stock
        FROM Product p
        LEFT JOIN Stock s ON p.Id = s.ProductId
        WHERE p.Id = ?
        GROUP BY p.Id LIMIT 1
    """, (product_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_low_stock(min_stock=5):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.Id, p.Name, p.Code, p.Price,
               IFNULL(SUM(s.Quantity),0) AS Stock
        FROM Product p
        LEFT JOIN Stock s ON p.Id = s.ProductId
        GROUP BY p.Id
        HAVING Stock < ?
        ORDER BY Stock ASC
    """, (min_stock,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_sales_today():
    conn = connect()
    cur = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    cur.execute("""
        SELECT COUNT(*) as Cantidad, IFNULL(SUM(Total),0) as Total
        FROM Document
        WHERE DATE(Date) = ?
    """, (today,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else {"Cantidad": 0, "Total": 0}

def get_sales_month():
    conn = connect()
    cur = conn.cursor()
    month = datetime.now().strftime('%Y-%m')
    cur.execute("""
        SELECT COUNT(*) as Cantidad, IFNULL(SUM(Total),0) as Total
        FROM Document
        WHERE STRFTIME('%Y-%m', Date) = ?
    """, (month,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else {"Cantidad": 0, "Total": 0}

def get_top_products(limit=10):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.Name, SUM(di.Quantity) as Vendidos,
               SUM(di.Total) as Total
        FROM DocumentItem di
        JOIN Product p ON di.ProductId = p.Id
        GROUP BY p.Id
        ORDER BY Vendidos DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_customers(search="", limit=50):
    conn = connect()
    cur = conn.cursor()
    if search:
        cur.execute("""
            SELECT Id, Name, Email, PhoneNumber
            FROM Customer
            WHERE Name LIKE ? AND IsEnabled = 1
            ORDER BY Name LIMIT ?
        """, (f"%{search}%", limit))
    else:
        cur.execute("""
            SELECT Id, Name, Email, PhoneNumber
            FROM Customer
            WHERE IsEnabled = 1
            ORDER BY Name LIMIT ?
        """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def add_stock(product_id, quantity, warehouse_id=1, razon="Entrada manual"):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT Id, Quantity FROM Stock WHERE ProductId=? AND WarehouseId=?", (product_id, warehouse_id))
    row = cur.fetchone()
    stock_antes = row["Quantity"] if row else 0
    if row:
        cur.execute("UPDATE Stock SET Quantity=Quantity+? WHERE ProductId=? AND WarehouseId=?",
            (quantity, product_id, warehouse_id))
    else:
        cur.execute("INSERT INTO Stock (ProductId, WarehouseId, Quantity) VALUES (?,?,?)",
            (product_id, warehouse_id, quantity))
    conn.commit()
    cur.execute("SELECT Name FROM Product WHERE Id=?", (product_id,))
    p = cur.fetchone()
    conn.close()
    name = p["Name"] if p else str(product_id)
    registrar_kardex(product_id, name, "ENTRADA", quantity, stock_antes, stock_antes + quantity, razon)
    return True

def remove_stock(product_id, quantity, warehouse_id=1, razon="Salida manual"):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT Quantity FROM Stock WHERE ProductId=? AND WarehouseId=?", (product_id, warehouse_id))
    row = cur.fetchone()
    if not row or row[0] < quantity:
        conn.close()
        return False
    stock_antes = row[0]
    cur.execute("UPDATE Stock SET Quantity=Quantity-? WHERE ProductId=? AND WarehouseId=?",
        (quantity, product_id, warehouse_id))
    conn.commit()
    cur.execute("SELECT Name FROM Product WHERE Id=?", (product_id,))
    p = cur.fetchone()
    conn.close()
    name = p["Name"] if p else str(product_id)
    registrar_kardex(product_id, name, "SALIDA", quantity, stock_antes, stock_antes - quantity, razon)
    return True

def get_stock(product_id, warehouse_id=1):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT Quantity FROM Stock WHERE ProductId=? AND WarehouseId=?", (product_id, warehouse_id))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0



# Kardex y Stock Minimo
import sqlite3 as _sqlite3
NIMBO_DB = '/home/ictor_axtor/micocina-dashboard/nimbo.db'

def nimbo_connect():
    conn = _sqlite3.connect(NIMBO_DB)
    conn.row_factory = _sqlite3.Row
    return conn

def registrar_kardex(product_id, product_name, tipo, cantidad, stock_antes, stock_despues, razon=""):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO Kardex (ProductId, ProductName, Tipo, Cantidad, StockAntes, StockDespues, Razon) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (product_id, product_name, tipo, cantidad, stock_antes, stock_despues, razon))
    conn.commit()
    conn.close()

def get_kardex(product_id=None, limit=50):
    conn = nimbo_connect()
    cur = conn.cursor()
    if product_id:
        cur.execute("SELECT * FROM Kardex WHERE ProductId=? ORDER BY Fecha DESC LIMIT ?", (product_id, limit))
    else:
        cur.execute("SELECT * FROM Kardex ORDER BY Fecha DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def set_stock_minimo(product_id, product_name, minimo):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO StockMinimo (ProductId, ProductName, Minimo) VALUES (?, ?, ?)",
        (product_id, product_name, minimo))
    conn.commit()
    conn.close()

def get_alertas_stock():
    productos = get_products()
    alertas = []
    conn = nimbo_connect()
    cur = conn.cursor()
    for p in productos:
        cur.execute("SELECT Minimo FROM StockMinimo WHERE ProductId=?", (p["Id"],))
        row = cur.fetchone()
        minimo = row["Minimo"] if row else 5
        if p["Stock"] <= minimo:
            alertas.append({**p, "Minimo": minimo})
    conn.close()
    return alertas


# ── ALERTAS PREDICTIVAS DE INVENTARIO ─────────────────

DIAS_HISTORIAL_CONSUMO = 30
DIAS_CRITICO_STOCK = 7
DIAS_ADVERTENCIA_STOCK = 21


def _consumo_diario_por_producto(dias=DIAS_HISTORIAL_CONSUMO, product_id=None):
    """Promedio de unidades de salida (ventas + salidas manuales, cualquier
    egreso real de Kardex) por dia en los ultimos `dias` dias, por producto."""
    conn = nimbo_connect()
    cur = conn.cursor()
    sql = """SELECT ProductId, SUM(Cantidad) as total_salida FROM Kardex
        WHERE Tipo='SALIDA' AND date(Fecha) >= date('now', ?)"""
    params = [f"-{dias} days"]
    if product_id is not None:
        sql += " AND ProductId=?"
        params.append(product_id)
    sql += " GROUP BY ProductId"
    cur.execute(sql, params)
    consumo = {r["ProductId"]: float(r["total_salida"]) / dias for r in cur.fetchall()}
    conn.close()
    return consumo


def _clasificar_urgencia_stock(dias_restantes):
    if dias_restantes is None:
        return "SIN_DATOS"
    if dias_restantes < DIAS_CRITICO_STOCK:
        return "CRITICO"
    if dias_restantes <= DIAS_ADVERTENCIA_STOCK:
        return "ADVERTENCIA"
    return "OK"


def get_alertas_predictivas(dias_historial=DIAS_HISTORIAL_CONSUMO):
    """Para cada producto calcula el promedio de unidades de salida por dia en
    los ultimos `dias_historial` dias (Kardex) y proyecta cuantos dias de stock
    quedan (stock_actual / promedio_diario). Productos sin ninguna salida en el
    periodo quedan con dias_restantes=None y urgencia SIN_DATOS (no hay tasa de
    consumo con la que proyectar agotamiento). Ordenado de mas a menos urgente."""
    consumo = _consumo_diario_por_producto(dias_historial)
    productos = get_products()
    resultado = []
    for p in productos:
        promedio_diario = consumo.get(p["Id"], 0)
        stock = float(p["Stock"])
        dias_restantes = round(stock / promedio_diario, 1) if promedio_diario > 0 else None
        resultado.append({
            "producto_id": p["Id"],
            "producto": p["Name"].strip(),
            "stock_actual": stock,
            "promedio_diario": round(promedio_diario, 2),
            "dias_restantes": dias_restantes,
            "urgencia": _clasificar_urgencia_stock(dias_restantes)
        })

    orden_urgencia = {"CRITICO": 0, "ADVERTENCIA": 1, "OK": 2, "SIN_DATOS": 3}
    resultado.sort(key=lambda r: (
        orden_urgencia[r["urgencia"]],
        r["dias_restantes"] if r["dias_restantes"] is not None else float("inf")
    ))
    return resultado


def get_prediccion_producto(query, dias_historial=DIAS_HISTORIAL_CONSUMO):
    """Prediccion de agotamiento de un solo producto (busqueda fuzzy por nombre,
    get_products(), mismo criterio que el resto del sistema). None si no se
    encuentra ningun producto."""
    productos = get_products(search=query)
    if not productos:
        return None
    p = productos[0]
    consumo = _consumo_diario_por_producto(dias_historial, product_id=p["Id"])
    promedio_diario = consumo.get(p["Id"], 0)
    stock = float(p["Stock"])
    dias_restantes = round(stock / promedio_diario, 1) if promedio_diario > 0 else None
    return {
        "producto_id": p["Id"],
        "producto": p["Name"].strip(),
        "stock_actual": stock,
        "promedio_diario": round(promedio_diario, 2),
        "dias_restantes": dias_restantes,
        "urgencia": _clasificar_urgencia_stock(dias_restantes)
    }


# ── SERVICIO TECNICO ──────────────────────────────────

def init_servicio_tecnico_ext():
    """Migracion: OrdenServicio ya existia antes del flujo de tecnicos. TecnicoId/
    TecnicoNombre reemplazan a la columna vieja 'Tecnico' (texto libre, nunca se
    conecto a ningun flujo de chat) - se agregan aparte, sin tocar esa columna."""
    conn = nimbo_connect()
    cur = conn.cursor()
    for columna, definicion in [("TecnicoId", "INTEGER"), ("TecnicoNombre", "TEXT")]:
        try:
            cur.execute(f"ALTER TABLE OrdenServicio ADD COLUMN {columna} {definicion}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


def crear_cliente(nombre, telefono="", email="", direccion="", nit=""):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT Id FROM Cliente WHERE Nombre LIKE ? AND Telefono=?", (nombre, telefono))
    exists = cur.fetchone()
    if exists:
        conn.close()
        return exists["Id"]
    cur.execute("INSERT INTO Cliente (Nombre, Telefono, Email, Direccion, Nit) VALUES (?,?,?,?,?)",
        (nombre, telefono, email, direccion, nit))
    conn.commit()
    client_id = cur.lastrowid
    conn.close()
    return client_id

def buscar_cliente(query):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Cliente WHERE Nombre LIKE ? OR Telefono LIKE ?",
        (f"%{query}%", f"%{query}%"))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def crear_orden(cliente_id, equipo, marca, modelo, problema, serie="", tecnico="",
                 tecnico_id=None, tecnico_nombre=""):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM OrdenServicio")
    total = cur.fetchone()["total"] + 1
    numero = f"OS-{total:04d}"
    cur.execute("""INSERT INTO OrdenServicio
        (NumeroOrden, ClienteId, Equipo, Marca, Modelo, Serie, Problema, Tecnico, TecnicoId, TecnicoNombre)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (numero, cliente_id, equipo, marca, modelo, serie, problema, tecnico, tecnico_id, tecnico_nombre))
    conn.commit()
    orden_id = cur.lastrowid
    cur.execute("INSERT INTO HistorialOrden (OrdenId, Estado, Nota) VALUES (?,?,?)",
        (orden_id, "RECEPCION", f"Equipo recibido: {equipo} {marca} {modelo}"))
    conn.commit()
    conn.close()
    return numero

def get_ordenes(estado=None, limit=50):
    conn = nimbo_connect()
    cur = conn.cursor()
    if estado:
        cur.execute("""SELECT o.*, c.Nombre as ClienteNombre, c.Telefono as ClienteTelefono
            FROM OrdenServicio o JOIN Cliente c ON o.ClienteId=c.Id
            WHERE o.Estado=? ORDER BY o.FechaRecepcion DESC LIMIT ?""", (estado, limit))
    else:
        cur.execute("""SELECT o.*, c.Nombre as ClienteNombre, c.Telefono as ClienteTelefono
            FROM OrdenServicio o JOIN Cliente c ON o.ClienteId=c.Id
            ORDER BY o.FechaRecepcion DESC LIMIT ?""", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_orden(numero):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT o.*, c.Nombre as ClienteNombre, c.Telefono as ClienteTelefono
        FROM OrdenServicio o JOIN Cliente c ON o.ClienteId=c.Id
        WHERE o.NumeroOrden=?""", (numero,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def actualizar_estado_orden(numero, estado, nota=""):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("UPDATE OrdenServicio SET Estado=? WHERE NumeroOrden=?", (estado, numero))
    cur.execute("INSERT INTO HistorialOrden (OrdenId, Estado, Nota) SELECT Id, ?, ? FROM OrdenServicio WHERE NumeroOrden=?",
        (estado, nota, numero))
    conn.commit()
    conn.close()
    return True

def set_presupuesto_orden(numero, presupuesto, mano_obra):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("UPDATE OrdenServicio SET Presupuesto=?, ManoObra=?, Estado='PRESUPUESTO' WHERE NumeroOrden=?",
        (presupuesto, mano_obra, numero))
    cur.execute("INSERT INTO HistorialOrden (OrdenId, Estado, Nota) SELECT Id, 'PRESUPUESTO', ? FROM OrdenServicio WHERE NumeroOrden=?",
        (f"Presupuesto: Q{presupuesto} + Mano de obra: Q{mano_obra}", numero))
    conn.commit()
    conn.close()
    return True


# ── INFORMES DE REVISION (SERVICIO TECNICO) ────────────

def init_informes_revision():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS InformeRevision (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            OrdenId INTEGER,
            NumeroOrden TEXT,
            TecnicoId INTEGER,
            TecnicoNombre TEXT,
            Descripcion TEXT,
            ProductosNecesarios TEXT,
            ManoObra NUMERIC DEFAULT 0,
            Total NUMERIC DEFAULT 0,
            Fecha DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def crear_informe_revision(orden_id, numero_orden, tecnico_id, tecnico_nombre, descripcion,
                            productos_necesarios, mano_obra):
    """productos_necesarios: lista de dicts {nombre, cantidad, costo} (costo ya resuelto
    contra el inventario, ver tools/service_tool.py informe_tool). Guarda el informe y
    actualiza la orden via set_presupuesto_orden (que ya cambia Estado a PRESUPUESTO y
    lo anota en HistorialOrden - PASO 4 del flujo). Retorna el desglose ya calculado."""
    import json
    presupuesto_repuestos = round(sum(p["costo"] * p["cantidad"] for p in productos_necesarios), 2)
    total = round(presupuesto_repuestos + mano_obra, 2)

    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""INSERT INTO InformeRevision
        (OrdenId, NumeroOrden, TecnicoId, TecnicoNombre, Descripcion, ProductosNecesarios, ManoObra, Total)
        VALUES (?,?,?,?,?,?,?,?)""",
        (orden_id, numero_orden, tecnico_id, tecnico_nombre, descripcion,
         json.dumps(productos_necesarios), mano_obra, total))
    conn.commit()
    informe_id = cur.lastrowid
    conn.close()

    set_presupuesto_orden(numero_orden, presupuesto_repuestos, mano_obra)

    return {"id": informe_id, "presupuesto_repuestos": presupuesto_repuestos, "mano_obra": mano_obra, "total": total}


def get_informes_orden(numero_orden):
    import json
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM InformeRevision WHERE NumeroOrden=? ORDER BY Fecha DESC", (numero_orden,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["ProductosNecesarios"] = json.loads(r["ProductosNecesarios"] or "[]")
    return rows


# ── TARIFAS DE MANO DE OBRA ────────────────────────────

def init_tarifas_mano_obra():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS TarifaManoObra (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Descripcion TEXT,
            Precio NUMERIC DEFAULT 0,
            Activo INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


def crear_tarifa(descripcion, precio):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO TarifaManoObra (Descripcion, Precio) VALUES (?,?)", (descripcion, precio))
    conn.commit()
    tarifa_id = cur.lastrowid
    conn.close()
    return tarifa_id


def get_tarifas(activo=True):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM TarifaManoObra WHERE Activo=? ORDER BY Descripcion", (1 if activo else 0,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ── PIPELINE DE SERVICIO TECNICO (widget del dashboard) ─

PIPELINE_ESTADOS_SERVICIO = ["RECEPCION", "REVISION", "PRESUPUESTO", "APROBADO", "REPARACION", "LISTO", "ENTREGADO"]


def get_pipeline_servicio():
    """Conteo de ordenes por estado, para el widget visual del dashboard (7 columnas
    fijas del pipeline + RECHAZADO aparte, que no es parte de la secuencia normal)."""
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT Estado, COUNT(*) as total FROM OrdenServicio GROUP BY Estado")
    conteos = {row["Estado"]: row["total"] for row in cur.fetchall()}
    conn.close()
    return {
        "pipeline": [{"estado": e, "total": conteos.get(e, 0)} for e in PIPELINE_ESTADOS_SERVICIO],
        "rechazado": conteos.get("RECHAZADO", 0)
    }


def get_historial_orden(numero):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT h.* FROM HistorialOrden h
        JOIN OrdenServicio o ON h.OrdenId=o.Id
        WHERE o.NumeroOrden=? ORDER BY h.Fecha ASC""", (numero,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ── FOTOS DE ORDEN DE SERVICIO ─────────────────────────

def init_fotos_servicio():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS FotoOrdenServicio (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            OrdenId INTEGER,
            NumeroOrden TEXT,
            RutaFoto TEXT,
            Descripcion TEXT,
            Fecha DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def agregar_foto_orden(orden_id, numero_orden, ruta_foto, descripcion=""):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO FotoOrdenServicio (OrdenId, NumeroOrden, RutaFoto, Descripcion) VALUES (?,?,?,?)",
        (orden_id, numero_orden, ruta_foto, descripcion))
    conn.commit()
    conn.close()


def get_fotos_orden(numero_orden):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM FotoOrdenServicio WHERE NumeroOrden=? ORDER BY Fecha ASC", (numero_orden,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ── CLIENTES NIMBO ────────────────────────────────────

def get_cliente_por_id(cliente_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Cliente WHERE Id=?", (cliente_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def crear_cliente_completo(nombre, telefono="", email="", nit="", direccion="", notas=""):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT Id FROM Cliente WHERE Telefono=?", (telefono,))
    exists = cur.fetchone()
    if exists:
        conn.close()
        return exists["Id"], False
    cur.execute(
        "INSERT INTO Cliente (Nombre, Telefono, Email, Nit, Direccion, Notas) VALUES (?,?,?,?,?,?)",
        (nombre, telefono, email, nit, direccion, notas)
    )
    conn.commit()
    client_id = cur.lastrowid
    conn.close()
    return client_id, True

def buscar_cliente_completo(query):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT c.*,
        (SELECT COUNT(*) FROM OrdenServicio o WHERE o.ClienteId=c.Id) as TotalOrdenes,
        (SELECT COUNT(*) FROM Venta v WHERE v.ClienteId=c.Id) as TotalCompras,
        (SELECT SUM(v.Total) FROM Venta v WHERE v.ClienteId=c.Id) as TotalGastado
        FROM Cliente c
        WHERE c.Nombre LIKE ? OR c.Telefono LIKE ? OR c.Nit LIKE ?
        ORDER BY c.Nombre""",
        (f"%{query}%", f"%{query}%", f"%{query}%"))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_todos_clientes(limit=100):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT c.*,
        (SELECT COUNT(*) FROM OrdenServicio o WHERE o.ClienteId=c.Id) as TotalOrdenes,
        (SELECT COUNT(*) FROM Venta v WHERE v.ClienteId=c.Id) as TotalCompras,
        (SELECT SUM(v.Total) FROM Venta v WHERE v.ClienteId=c.Id) as TotalGastado
        FROM Cliente c ORDER BY c.Nombre LIMIT ?""", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def registrar_venta_cliente(cliente_id, descripcion, total):
    """Registra una Venta aplicando el ajuste de puntos de lealtad (credito de un
    canje pendiente + 5% extra de nivel Oro, ver calcular_ajuste_puntos) sobre
    `total` antes de insertar, y luego gana puntos nuevos sobre el monto ya
    ajustado. Retorna (venta_id, total_final_cobrado, puntos_info)."""
    from datetime import datetime

    ajuste = calcular_ajuste_puntos(cliente_id, total)
    total_final = ajuste["total_final"]
    descripcion += formatear_nota_ajuste_puntos(ajuste)

    now = datetime.now()
    mes = now.month
    trimestre = (mes - 1) // 3 + 1
    anio = now.year
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Venta (ClienteId, Descripcion, Total, Mes, Trimestre, Anio) VALUES (?,?,?,?,?,?)",
        (cliente_id, descripcion, total_final, mes, trimestre, anio)
    )
    venta_id = cur.lastrowid
    cur.execute("UPDATE Cliente SET UltimaCompra=? WHERE Id=?", (now.isoformat(), cliente_id))
    conn.commit()
    conn.close()

    puntos_info = None
    if cliente_id:
        consumir_credito_puntos_pendiente(cliente_id, venta_id)
        cliente = get_cliente_por_id(cliente_id)
        nombre = cliente["Nombre"] if cliente else "Consumidor Final"
        puntos_info = ganar_puntos(cliente_id, nombre, total_final, venta_id)

    return venta_id, total_final, puntos_info

def get_historial_cliente(cliente_id, meses=None):
    """Historial completo del cliente desde el primer dia (meses=None, default) o
    acotado a los ultimos `meses` meses si se especifica. Incluye ventas, ordenes
    de servicio, cotizaciones y garantias vigentes (las vencidas/reclamadas no se
    incluyen aqui, ver marcar_garantias_vencidas)."""
    marcar_garantias_vencidas()
    conn = nimbo_connect()
    cur = conn.cursor()
    if meses:
        cur.execute("""SELECT v.*, c.Nombre as ClienteNombre FROM Venta v
            JOIN Cliente c ON v.ClienteId=c.Id
            WHERE v.ClienteId=?
            AND v.Fecha >= datetime('now', ? || ' months')
            ORDER BY v.Fecha DESC""",
            (cliente_id, f"-{meses}"))
    else:
        cur.execute("""SELECT v.*, c.Nombre as ClienteNombre FROM Venta v
            JOIN Cliente c ON v.ClienteId=c.Id
            WHERE v.ClienteId=?
            ORDER BY v.Fecha DESC""", (cliente_id,))
    ventas = [dict(r) for r in cur.fetchall()]

    cur.execute("""SELECT * FROM OrdenServicio
        WHERE ClienteId=? ORDER BY FechaRecepcion DESC""", (cliente_id,))
    ordenes = [dict(r) for r in cur.fetchall()]

    cur.execute("""SELECT * FROM Cotizacion
        WHERE ClienteId=? ORDER BY FechaCreada DESC""", (cliente_id,))
    cotizaciones = [dict(r) for r in cur.fetchall()]

    cur.execute("""SELECT * FROM GarantiaVenta
        WHERE ClienteId=? AND Estado='VIGENTE' ORDER BY FechaVencimientoPropias ASC""", (cliente_id,))
    garantias = [dict(r) for r in cur.fetchall()]

    conn.close()
    return {"ventas": ventas, "ordenes": ordenes, "cotizaciones": cotizaciones, "garantias": garantias}


# ── GRUPOS DE CLIENTE ──────────────────────────────────

# (grupo, PorcentajeDescuento, PuntosMultiplicador). "Especial" queda en 0% aqui a
# proposito - su descuento no es fijo por grupo, se configura por cliente con el
# mecanismo de Descuento individual (tipo='cliente', ver calcular_descuento) que ya
# existia antes de este feature.
GRUPOS_CLIENTE_DEFAULT = [
    ("detallista", 0, 1),
    ("mayorista", 10, 1),
    ("especial", 0, 1),
    ("vip", 15, 2),
]

GRUPOS_CLIENTE = {g for g, _, _ in GRUPOS_CLIENTE_DEFAULT}


def init_grupos_cliente():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS GrupoDescuento (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Grupo TEXT UNIQUE,
            PorcentajeDescuento NUMERIC DEFAULT 0,
            PuntosMultiplicador NUMERIC DEFAULT 1
        )
    """)
    for grupo, porcentaje, multiplicador in GRUPOS_CLIENTE_DEFAULT:
        cur.execute("INSERT OR IGNORE INTO GrupoDescuento (Grupo, PorcentajeDescuento, PuntosMultiplicador) VALUES (?,?,?)",
            (grupo, porcentaje, multiplicador))

    # Migracion: Cliente ya existia antes de agregar GrupoCliente.
    try:
        cur.execute("ALTER TABLE Cliente ADD COLUMN GrupoCliente TEXT DEFAULT 'detallista'")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def get_grupos_descuento():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM GrupoDescuento ORDER BY Grupo")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_grupo_descuento(grupo):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM GrupoDescuento WHERE Grupo=?", (grupo,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def set_grupo_cliente(cliente_id, grupo):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("UPDATE Cliente SET GrupoCliente=? WHERE Id=?", (grupo, cliente_id))
    conn.commit()
    conn.close()


def get_clientes_por_grupo(grupo):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Cliente WHERE GrupoCliente=? ORDER BY Nombre", (grupo,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_clientes_inactivos(meses=3):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT * FROM Cliente
        WHERE UltimaCompra < datetime('now', ? || ' months')
        OR UltimaCompra IS NULL
        ORDER BY UltimaCompra ASC""", (f"-{meses}",))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ── PROVEEDORES ───────────────────────────────────────

def crear_proveedor(nombre, whatsapp="", email="", direccion="", notas=""):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT Id FROM Proveedor WHERE Nombre LIKE ?", (nombre,))
    exists = cur.fetchone()
    if exists:
        conn.close()
        return exists["Id"], False
    cur.execute("INSERT INTO Proveedor (Nombre, WhatsApp, Email, Direccion, Notas) VALUES (?,?,?,?,?)",
        (nombre, whatsapp, email, direccion, notas))
    conn.commit()
    proveedor_id = cur.lastrowid
    conn.close()
    return proveedor_id, True

def agregar_contacto_proveedor(proveedor_id, nombre, whatsapp="", cargo="Vendedor", es_principal=1):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO ContactoProveedor (ProveedorId, Nombre, Cargo, WhatsApp, EsPrincipal) VALUES (?,?,?,?,?)",
        (proveedor_id, nombre, cargo, whatsapp, es_principal))
    conn.commit()
    conn.close()

def buscar_proveedor(query):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT p.*,
        (SELECT COUNT(*) FROM OrdenCompra o WHERE o.ProveedorId=p.Id) as TotalOrdenes,
        (SELECT SUM(o.Total) FROM OrdenCompra o WHERE o.ProveedorId=p.Id) as TotalComprado
        FROM Proveedor p
        WHERE p.Nombre LIKE ? OR p.WhatsApp LIKE ?
        ORDER BY p.Nombre""", (f"%{query}%", f"%{query}%"))
    proveedores = [dict(r) for r in cur.fetchall()]
    for p in proveedores:
        cur.execute("SELECT * FROM ContactoProveedor WHERE ProveedorId=?", (p["Id"],))
        p["contactos"] = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM ProductoProveedor WHERE ProveedorId=?", (p["Id"],))
        p["productos"] = [dict(r) for r in cur.fetchall()]
    conn.close()
    return proveedores

def get_todos_proveedores():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT p.*,
        (SELECT COUNT(*) FROM OrdenCompra o WHERE o.ProveedorId=p.Id) as TotalOrdenes,
        (SELECT SUM(o.Total) FROM OrdenCompra o WHERE o.ProveedorId=p.Id) as TotalComprado
        FROM Proveedor p ORDER BY p.Nombre""")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def crear_orden_compra(proveedor_id, items, contacto_id=None, notas=""):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM OrdenCompra")
    total = cur.fetchone()["total"] + 1
    numero = f"OC-{total:04d}"
    total_orden = sum(i["cantidad"] * i["precio"] for i in items)
    cur.execute("INSERT INTO OrdenCompra (NumeroOrden, ProveedorId, ContactoId, Total, Notas) VALUES (?,?,?,?,?)",
        (numero, proveedor_id, contacto_id, total_orden, notas))
    orden_id = cur.lastrowid
    for item in items:
        cur.execute("INSERT INTO ItemOrdenCompra (OrdenId, ProductoNombre, ProductoId, Cantidad, PrecioUnitario, Total) VALUES (?,?,?,?,?,?)",
            (orden_id, item["nombre"], item.get("producto_id", 0), item["cantidad"], item["precio"], item["cantidad"] * item["precio"]))
        # Verificar cambio de precio
        cur.execute("""SELECT PrecioUnitario FROM ItemOrdenCompra i
            JOIN OrdenCompra o ON i.OrdenId=o.Id
            WHERE o.ProveedorId=? AND i.ProductoNombre LIKE ?
            ORDER BY o.Fecha DESC LIMIT 1 OFFSET 1""", (proveedor_id, f"%{item['nombre']}%"))
        precio_anterior = cur.fetchone()
        if precio_anterior and precio_anterior["PrecioUnitario"] != item["precio"]:
            diff = item["precio"] - precio_anterior["PrecioUnitario"]
            pct = (diff / precio_anterior["PrecioUnitario"]) * 100
            cur.execute("INSERT INTO HistorialPrecio (ProveedorId, ProductoNombre, PrecioAnterior, PrecioNuevo, Diferencia, PorcentajeCambio) VALUES (?,?,?,?,?,?)",
                (proveedor_id, item["nombre"], precio_anterior["PrecioUnitario"], item["precio"], diff, round(pct, 2)))
    conn.commit()
    conn.close()
    return numero, orden_id

def get_alertas_precios():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT h.*, p.Nombre as ProveedorNombre FROM HistorialPrecio h
        JOIN Proveedor p ON h.ProveedorId=p.Id
        ORDER BY h.Fecha DESC LIMIT 20""")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_historial_proveedor(proveedor_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT o.*, GROUP_CONCAT(i.ProductoNombre || ' x' || i.Cantidad || ' Q' || i.PrecioUnitario, ' | ') as Items
        FROM OrdenCompra o
        LEFT JOIN ItemOrdenCompra i ON i.OrdenId=o.Id
        WHERE o.ProveedorId=? GROUP BY o.Id ORDER BY o.Fecha DESC""", (proveedor_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def asociar_producto_proveedor(proveedor_id, producto_nombre, producto_id=0):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT Id FROM ProductoProveedor WHERE ProveedorId=? AND ProductoNombre LIKE ?",
        (proveedor_id, producto_nombre))
    if not cur.fetchone():
        cur.execute("INSERT INTO ProductoProveedor (ProveedorId, ProductoNombre, ProductoId) VALUES (?,?,?)",
            (proveedor_id, producto_nombre, producto_id))
        conn.commit()
    conn.close()

def get_productos_por_proveedor():
    productos = get_products()
    conn = nimbo_connect()
    cur = conn.cursor()
    resultado = []
    for p in productos:
        cur.execute("""SELECT pr.*, pp.ProductoNombre FROM ProductoProveedor pp
            JOIN Proveedor pr ON pp.ProveedorId=pr.Id
            WHERE pp.ProductoNombre LIKE ? OR pp.ProductoId=?""",
            (f"%{p['Name'].strip()}%", p["Id"]))
        proveedores = [dict(r) for r in cur.fetchall()]
        resultado.append({**p, "proveedores": proveedores})
    conn.close()
    return resultado

def get_pedidos_sugeridos():
    conn = nimbo_connect()
    cur = conn.cursor()
    productos = get_products()
    sugeridos = []
    for p in productos:
        cur.execute("SELECT Minimo FROM StockMinimo WHERE ProductId=?", (p["Id"],))
        row = cur.fetchone()
        minimo = row["Minimo"] if row else 5
        if p["Stock"] <= minimo:
            cur.execute("""SELECT pr.Id, pr.Nombre, pr.WhatsApp FROM ProductoProveedor pp
                JOIN Proveedor pr ON pp.ProveedorId=pr.Id
                WHERE pp.ProductoNombre LIKE ? OR pp.ProductoId=?""",
                (f"%{p['Name'].strip()}%", p["Id"]))
            proveedores = [dict(r) for r in cur.fetchall()]
            cantidad_sugerida = max(minimo * 2 - int(p["Stock"]), minimo)
            costo_unitario = float(p["Cost"] or 0)
            sugeridos.append({
                "producto": p["Name"].strip(),
                "stock_actual": int(p["Stock"]),
                "minimo": minimo,
                "cantidad_sugerida": cantidad_sugerida,
                "proveedores": proveedores,
                "costo_unitario": costo_unitario,
                "costo_total": round(costo_unitario * cantidad_sugerida, 2)
            })
    conn.close()
    return sugeridos


# ── COTIZACIONES ──────────────────────────────────────

def init_cotizaciones():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Cotizacion (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            NumeroC TEXT UNIQUE,
            ClienteId INTEGER,
            ClienteNombre TEXT,
            ClienteTelefono TEXT,
            Items TEXT,
            Total NUMERIC DEFAULT 0,
            Estado TEXT DEFAULT 'PENDIENTE',
            FechaCreada DATETIME DEFAULT CURRENT_TIMESTAMP,
            FechaEnviada DATETIME,
            FechaVencimiento DATETIME,
            FechaRespuesta DATETIME,
            Notas TEXT,
            FOREIGN KEY (ClienteId) REFERENCES Cliente(Id)
        )
    """)
    conn.commit()
    conn.close()


def crear_cotizacion(cliente_id, cliente_nombre, cliente_telefono, items, total, notas=""):
    import json
    from datetime import timedelta
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM Cotizacion")
    total_cot = cur.fetchone()["total"] + 1
    numero = f"COT-{total_cot:04d}"
    vencimiento = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""INSERT INTO Cotizacion
        (NumeroC, ClienteId, ClienteNombre, ClienteTelefono, Items, Total, FechaVencimiento, Notas)
        VALUES (?,?,?,?,?,?,?,?)""",
        (numero, cliente_id, cliente_nombre, cliente_telefono, json.dumps(items), total, vencimiento, notas))
    conn.commit()
    conn.close()
    return numero, vencimiento


def get_cotizacion(numero):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Cotizacion WHERE NumeroC=?", (numero,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_cotizaciones(estado=None, limit=50):
    conn = nimbo_connect()
    cur = conn.cursor()
    if estado:
        cur.execute("SELECT * FROM Cotizacion WHERE Estado=? ORDER BY FechaCreada DESC LIMIT ?", (estado, limit))
    else:
        cur.execute("SELECT * FROM Cotizacion ORDER BY FechaCreada DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def actualizar_estado_cotizacion(numero, estado):
    conn = nimbo_connect()
    cur = conn.cursor()
    if estado in ("ACEPTADA", "RECHAZADA"):
        cur.execute("UPDATE Cotizacion SET Estado=?, FechaRespuesta=? WHERE NumeroC=?",
            (estado, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), numero))
    else:
        cur.execute("UPDATE Cotizacion SET Estado=? WHERE NumeroC=?", (estado, numero))
    conn.commit()
    conn.close()


def marcar_cotizacion_enviada(numero):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("UPDATE Cotizacion SET Estado='ENVIADA', FechaEnviada=? WHERE NumeroC=?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), numero))
    conn.commit()
    conn.close()


def marcar_cotizaciones_vencidas():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""UPDATE Cotizacion SET Estado='VENCIDA'
        WHERE Estado IN ('PENDIENTE','ENVIADA') AND date(FechaVencimiento) < date('now')""")
    conn.commit()
    conn.close()


def get_cotizaciones_seguimiento():
    """Cotizaciones que vencen hoy (para dar seguimiento) o que acaban de vencer."""
    marcar_cotizaciones_vencidas()
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT * FROM Cotizacion
        WHERE (Estado IN ('PENDIENTE','ENVIADA') AND date(FechaVencimiento) = date('now'))
        OR (Estado='VENCIDA' AND date(FechaVencimiento) >= date('now','-3 days'))
        ORDER BY FechaVencimiento ASC""")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_resumen_cotizaciones():
    marcar_cotizaciones_vencidas()
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM Cotizacion WHERE Estado='PENDIENTE'")
    pendientes = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) as total FROM Cotizacion WHERE Estado='ENVIADA'")
    enviadas = cur.fetchone()["total"]
    cur.execute("""SELECT COUNT(*) as total FROM Cotizacion
        WHERE Estado='ACEPTADA' AND date(FechaRespuesta) >= date('now','-7 days')""")
    aceptadas_semana = cur.fetchone()["total"]
    cur.execute("""SELECT * FROM Cotizacion WHERE Estado IN ('PENDIENTE','ENVIADA')
        ORDER BY FechaVencimiento ASC LIMIT 10""")
    activas = []
    hoy = datetime.now()
    for r in cur.fetchall():
        c = dict(r)
        try:
            vencimiento = datetime.strptime(c["FechaVencimiento"][:19], "%Y-%m-%d %H:%M:%S")
            dias_restantes = (vencimiento.date() - hoy.date()).days
        except Exception:
            dias_restantes = None
        c["DiasRestantes"] = dias_restantes
        activas.append(c)
    conn.close()
    return {
        "pendientes": pendientes,
        "enviadas": enviadas,
        "aceptadas_semana": aceptadas_semana,
        "activas": activas
    }


# ── DESCUENTOS ────────────────────────────────────────

def init_descuentos():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Descuento (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Nombre TEXT,
            Tipo TEXT,
            Porcentaje NUMERIC,
            MontoFijo NUMERIC,
            ClienteId INTEGER,
            ProductoId INTEGER,
            FechaInicio TEXT,
            FechaFin TEXT,
            MontoMinimo NUMERIC,
            Activo INTEGER DEFAULT 1,
            FechaCreado DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ClienteId) REFERENCES Cliente(Id)
        )
    """)
    conn.commit()
    conn.close()


def crear_descuento(nombre, tipo, porcentaje=None, monto_fijo=None, cliente_id=None,
                     producto_id=None, fecha_inicio=None, fecha_fin=None, monto_minimo=None):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""INSERT INTO Descuento
        (Nombre, Tipo, Porcentaje, MontoFijo, ClienteId, ProductoId, FechaInicio, FechaFin, MontoMinimo)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (nombre, tipo, porcentaje, monto_fijo, cliente_id, producto_id, fecha_inicio, fecha_fin, monto_minimo))
    conn.commit()
    descuento_id = cur.lastrowid
    conn.close()
    return descuento_id


def get_descuentos(activo=True, tipo=None):
    conn = nimbo_connect()
    cur = conn.cursor()
    query = "SELECT * FROM Descuento WHERE Activo=?"
    params = [1 if activo else 0]
    if tipo:
        query += " AND Tipo=?"
        params.append(tipo)
    query += " ORDER BY FechaCreado DESC"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_descuento_por_id(descuento_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Descuento WHERE Id=?", (descuento_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_descuentos(query):
    """Busca descuentos activos por nombre (usado por 'eliminar descuento X' cuando X
    no es un Id numerico)."""
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Descuento WHERE Activo=1 AND Nombre LIKE ?", (f"%{query}%",))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def desactivar_descuento(descuento_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("UPDATE Descuento SET Activo=0 WHERE Id=?", (descuento_id,))
    conn.commit()
    conn.close()


def _monto_descuento(d, base):
    if base <= 0:
        return 0
    if d.get("Porcentaje"):
        return round(base * float(d["Porcentaje"]) / 100, 2)
    if d.get("MontoFijo"):
        return round(min(float(d["MontoFijo"]), base), 2)
    return 0


def calcular_descuento(cliente_id=None, productos=None, total=0, fecha=None):
    """Calcula el mejor descuento aplicable a una venta/cotizacion. No se acumulan
    varios descuentos: si mas de uno aplica (ej. el cliente tiene descuento fijo Y la
    compra supera el monto minimo de otro descuento), se usa el que le convenga mas al
    cliente (mayor monto en quetzales).
    productos: lista de dicts {producto_id, subtotal}, usada solo para descuentos tipo
    'producto' (la base de ese descuento es la suma de los subtotales de los items que
    coincidan con ese producto, no el total completo del carrito).
    Retorna un dict con el descuento a aplicar, o None si no aplica ninguno."""
    fecha = fecha or datetime.now().date()
    productos = productos or []
    candidatos = []
    tiene_descuento_individual = False
    for d in get_descuentos(activo=True):
        tipo = d["Tipo"]
        base = None
        if tipo == "cliente" and cliente_id and d["ClienteId"] == cliente_id:
            base = total
            tiene_descuento_individual = True
        elif tipo == "temporada" and d["FechaInicio"] and d["FechaFin"]:
            try:
                fi = datetime.strptime(d["FechaInicio"][:10], "%Y-%m-%d").date()
                ff = datetime.strptime(d["FechaFin"][:10], "%Y-%m-%d").date()
            except (TypeError, ValueError):
                continue
            if fi <= fecha <= ff:
                base = total
        elif tipo == "producto" and d["ProductoId"]:
            base = sum(p["subtotal"] for p in productos if p.get("producto_id") == d["ProductoId"])
        elif tipo == "monto" and d["MontoMinimo"] is not None and total >= d["MontoMinimo"]:
            base = total
        if base is None or base <= 0:
            continue
        monto = _monto_descuento(d, base)
        if monto <= 0:
            continue
        candidatos.append((monto, d, base))

    # Descuento automatico de grupo (ver GRUPOS_CLIENTE_DEFAULT): solo entra a competir
    # si el cliente NO tiene un descuento individual (tipo 'cliente') configurado - el
    # individual siempre tiene prioridad sobre el automatico del grupo, nunca se compara
    # cual conviene mas. "Especial" no tiene porcentaje fijo en GrupoDescuento (queda en
    # 0), asi que en la practica su descuento sale siempre del Descuento individual.
    if cliente_id and not tiene_descuento_individual and total > 0:
        cliente = get_cliente_por_id(cliente_id)
        grupo = (cliente.get("GrupoCliente") if cliente else None) or "detallista"
        grupo_descuento = get_grupo_descuento(grupo)
        if grupo_descuento and grupo_descuento["PorcentajeDescuento"]:
            monto_grupo = round(total * float(grupo_descuento["PorcentajeDescuento"]) / 100, 2)
            if monto_grupo > 0:
                d_grupo = {
                    "Id": None, "Nombre": f"Grupo {grupo.capitalize()}", "Tipo": "grupo",
                    "Porcentaje": grupo_descuento["PorcentajeDescuento"], "MontoFijo": None
                }
                candidatos.append((monto_grupo, d_grupo, total))

    if not candidatos:
        return None
    candidatos.sort(key=lambda x: x[0], reverse=True)
    monto, d, base = candidatos[0]
    return {
        "descuento_id": d["Id"],
        "nombre": d["Nombre"],
        "tipo": d["Tipo"],
        "porcentaje": d["Porcentaje"],
        "monto_fijo": d["MontoFijo"],
        "base": round(base, 2),
        "monto_descuento": monto
    }


# ── GARANTIAS ─────────────────────────────────────────

DIAS_GARANTIA_PROPIA_DEFAULT = 30


def init_garantias():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS GarantiaProducto (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            ProductoId INTEGER UNIQUE,
            ProductoNombre TEXT,
            DiasFabrica INTEGER DEFAULT 0,
            DiasPropia INTEGER DEFAULT 30,
            Notas TEXT,
            FechaActualizado DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS GarantiaVenta (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            NumeroGarantia TEXT UNIQUE,
            VentaId INTEGER,
            ClienteId INTEGER,
            ClienteNombre TEXT,
            ClienteTelefono TEXT,
            ProductoNombre TEXT,
            ProductoId INTEGER,
            FechaVenta DATETIME,
            FechaVencimientoFabrica DATETIME,
            FechaVencimientoPropias DATETIME,
            Estado TEXT DEFAULT 'VIGENTE',
            Notas TEXT,
            Tipo TEXT DEFAULT 'producto',
            OrdenServicioId INTEGER
        )
    """)
    # Migracion: GarantiaVenta ya existia antes de agregar Tipo/OrdenServicioId
    # (garantias de reparacion de Servicio Tecnico) - CREATE TABLE IF NOT EXISTS no
    # modifica una tabla que ya existe, hay que agregar las columnas aparte.
    for columna, definicion in [("Tipo", "TEXT DEFAULT 'producto'"), ("OrdenServicioId", "INTEGER")]:
        try:
            cur.execute(f"ALTER TABLE GarantiaVenta ADD COLUMN {columna} {definicion}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


def set_garantia_producto(producto_id, producto_nombre, dias_fabrica=None, dias_propia=None, notas=None):
    """Configura (crea o actualiza) la garantia de un producto. Los campos que
    llegan en None no se tocan si ya existia una configuracion previa, para poder
    ajustar solo fabrica o solo propia sin pisar el otro valor con un default."""
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM GarantiaProducto WHERE ProductoId=?", (producto_id,))
    existente = cur.fetchone()
    if existente:
        nuevo_fabrica = dias_fabrica if dias_fabrica is not None else existente["DiasFabrica"]
        nuevo_propia = dias_propia if dias_propia is not None else existente["DiasPropia"]
        nuevas_notas = notas if notas is not None else existente["Notas"]
        cur.execute("""UPDATE GarantiaProducto SET DiasFabrica=?, DiasPropia=?, Notas=?,
            FechaActualizado=CURRENT_TIMESTAMP WHERE ProductoId=?""",
            (nuevo_fabrica, nuevo_propia, nuevas_notas, producto_id))
    else:
        cur.execute("""INSERT INTO GarantiaProducto (ProductoId, ProductoNombre, DiasFabrica, DiasPropia, Notas)
            VALUES (?,?,?,?,?)""",
            (producto_id, producto_nombre,
             dias_fabrica if dias_fabrica is not None else 0,
             dias_propia if dias_propia is not None else DIAS_GARANTIA_PROPIA_DEFAULT,
             notas))
    conn.commit()
    conn.close()


def get_garantia_producto(producto_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM GarantiaProducto WHERE ProductoId=?", (producto_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def generar_garantia_venta(venta_id, producto_id, producto_nombre, cliente_id=None,
                            cliente_nombre="Consumidor Final", cliente_telefono="", fecha_venta=None):
    """Genera la garantia de un producto vendido (una por cada linea de producto de
    la venta, sin importar la cantidad). Si el producto no tiene GarantiaProducto
    configurada usa 30 dias propios por defecto y 0 de fabrica (sin garantia de
    fabrica), tal como se pide en la integracion con ventas."""
    from datetime import timedelta
    fecha_venta = fecha_venta or datetime.now()
    config = get_garantia_producto(producto_id)
    dias_fabrica = config["DiasFabrica"] if config else 0
    dias_propia = config["DiasPropia"] if config else DIAS_GARANTIA_PROPIA_DEFAULT

    vencimiento_fabrica = (fecha_venta + timedelta(days=dias_fabrica)).strftime("%Y-%m-%d") if dias_fabrica else None
    vencimiento_propia = (fecha_venta + timedelta(days=dias_propia)).strftime("%Y-%m-%d")

    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM GarantiaVenta WHERE Tipo='producto'")
    total = cur.fetchone()["total"] + 1
    numero = f"GAR-{total:04d}"
    cur.execute("""INSERT INTO GarantiaVenta
        (NumeroGarantia, Tipo, VentaId, ClienteId, ClienteNombre, ClienteTelefono,
         ProductoNombre, ProductoId, FechaVenta, FechaVencimientoFabrica, FechaVencimientoPropias)
        VALUES (?,'producto',?,?,?,?,?,?,?,?,?)""",
        (numero, venta_id, cliente_id, cliente_nombre, cliente_telefono,
         producto_nombre, producto_id, fecha_venta.strftime("%Y-%m-%d %H:%M:%S"),
         vencimiento_fabrica, vencimiento_propia))
    conn.commit()
    conn.close()
    return {
        "numero": numero,
        "dias_fabrica": dias_fabrica,
        "dias_propia": dias_propia,
        "vencimiento_fabrica": vencimiento_fabrica,
        "vencimiento_propia": vencimiento_propia
    }


DIAS_GARANTIA_REPARACION_DEFAULT = 30


def generar_garantia_reparacion(orden, dias=None):
    """Genera la garantia de una reparacion de Servicio Tecnico al marcarla como
    ENTREGADO. Usa la misma tabla GarantiaVenta que las garantias de producto,
    distinguida por Tipo='reparacion' y numerada aparte (GARR-XXXX en vez de
    GAR-XXXX, cada una con su propia secuencia). No hay VentaId (no es una venta
    de producto) pero si OrdenServicioId para vincularla con la orden. `orden` es
    el dict que devuelve get_orden() (incluye Id, Equipo, Marca, ClienteId,
    ClienteNombre, ClienteTelefono)."""
    from datetime import timedelta
    dias = dias if dias is not None else DIAS_GARANTIA_REPARACION_DEFAULT
    fecha_entrega = datetime.now()
    vencimiento = (fecha_entrega + timedelta(days=dias)).strftime("%Y-%m-%d")
    equipo = f"{orden['Equipo']} {orden['Marca']}".strip()

    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM GarantiaVenta WHERE Tipo='reparacion'")
    total = cur.fetchone()["total"] + 1
    numero = f"GARR-{total:04d}"
    cur.execute("""INSERT INTO GarantiaVenta
        (NumeroGarantia, Tipo, OrdenServicioId, ClienteId, ClienteNombre, ClienteTelefono,
         ProductoNombre, FechaVenta, FechaVencimientoPropias)
        VALUES (?,'reparacion',?,?,?,?,?,?,?)""",
        (numero, orden["Id"], orden.get("ClienteId"), orden.get("ClienteNombre"),
         orden.get("ClienteTelefono"), equipo, fecha_entrega.strftime("%Y-%m-%d %H:%M:%S"), vencimiento))
    conn.commit()
    conn.close()
    return {"numero": numero, "dias": dias, "fecha_vencimiento": vencimiento}


def get_garantia_reparacion_por_orden(orden_id):
    marcar_garantias_vencidas()
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT * FROM GarantiaVenta WHERE Tipo='reparacion' AND OrdenServicioId=?
        ORDER BY Id DESC LIMIT 1""", (orden_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def reclamar_garantia_reparacion(orden_id, numero_orden_original):
    """Reclama la garantia de una reparacion: si sigue VIGENTE la marca RECLAMADA
    (nunca se vuelve a tocar automaticamente, ver marcar_garantias_vencidas) y crea
    una OrdenServicio nueva sin costo para la misma reparacion (mismo cliente y
    equipo), anotando en Observaciones la garantia y orden originales."""
    garantia = get_garantia_reparacion_por_orden(orden_id)
    if not garantia:
        return {"error": f"La orden {numero_orden_original} no tiene una garantia de reparacion registrada."}
    if garantia["Estado"] == "RECLAMADA":
        return {"error": f"La garantia {garantia['NumeroGarantia']} de esta reparacion ya fue reclamada antes."}
    if garantia["Estado"] == "VENCIDA":
        return {"error": (f"La garantia {garantia['NumeroGarantia']} vencio el "
                           f"{str(garantia['FechaVencimientoPropias'])[:10]}. No se puede reclamar.")}

    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("UPDATE GarantiaVenta SET Estado='RECLAMADA' WHERE Id=?", (garantia["Id"],))
    cur.execute("SELECT * FROM OrdenServicio WHERE Id=?", (orden_id,))
    row = cur.fetchone()
    conn.commit()
    conn.close()
    orden_original = dict(row) if row else None

    numero_nueva = None
    if orden_original:
        problema = f"Reclamo de garantia {garantia['NumeroGarantia']} de la orden {numero_orden_original}"
        numero_nueva = crear_orden(
            orden_original["ClienteId"], orden_original["Equipo"], orden_original["Marca"],
            orden_original["Modelo"], problema, serie=orden_original.get("Serie") or ""
        )
        conn = nimbo_connect()
        cur = conn.cursor()
        cur.execute("UPDATE OrdenServicio SET Observaciones=? WHERE NumeroOrden=?",
            (f"Reparacion sin costo por garantia {garantia['NumeroGarantia']} (orden original {numero_orden_original})",
             numero_nueva))
        conn.commit()
        conn.close()

    return {"garantia": garantia, "numero_nueva_orden": numero_nueva}


def marcar_garantias_vencidas():
    """Una garantia solo pasa a VENCIDA cuando ya vencieron tanto la de fabrica (si
    aplica) como la propia - mientras cualquiera de las dos siga vigente, el
    producto sigue cubierto. Nunca toca una garantia ya RECLAMADA."""
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""UPDATE GarantiaVenta SET Estado='VENCIDA'
        WHERE Estado='VIGENTE'
        AND date(FechaVencimientoPropias) < date('now')
        AND (FechaVencimientoFabrica IS NULL OR date(FechaVencimientoFabrica) < date('now'))""")
    conn.commit()
    conn.close()


def get_garantia_por_numero(numero):
    marcar_garantias_vencidas()
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM GarantiaVenta WHERE NumeroGarantia=?", (numero,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_garantias_cliente(query):
    marcar_garantias_vencidas()
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT * FROM GarantiaVenta
        WHERE ClienteNombre LIKE ? OR ClienteTelefono LIKE ?
        ORDER BY FechaVenta DESC""", (f"%{query}%", f"%{query}%"))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_garantias_por_vencer(dias=30):
    """Garantias VIGENTE cuya cobertura (la fecha mas lejana entre fabrica y
    propia, que es la que de verdad sigue cubriendo al cliente) vence dentro de
    los proximos `dias` dias."""
    marcar_garantias_vencidas()
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT * FROM (
            SELECT *, MAX(IFNULL(FechaVencimientoFabrica, FechaVencimientoPropias), FechaVencimientoPropias) as VenceEfectivo
            FROM GarantiaVenta WHERE Estado='VIGENTE'
        )
        WHERE date(VenceEfectivo) BETWEEN date('now') AND date('now', '+' || ? || ' days')
        ORDER BY VenceEfectivo ASC""", (dias,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ── COMBOS ────────────────────────────────────────────

DESCUENTO_COMBO_SUGERIDO = 0.08


def init_combos():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ProductoCombo (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Nombre TEXT,
            Descripcion TEXT,
            PrecioCombo NUMERIC DEFAULT 0,
            Activo INTEGER DEFAULT 1,
            FechaCreado DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ItemCombo (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            ComboId INTEGER,
            ProductoId INTEGER,
            ProductoNombre TEXT,
            Cantidad NUMERIC DEFAULT 1,
            FOREIGN KEY (ComboId) REFERENCES ProductoCombo(Id)
        )
    """)
    conn.commit()
    conn.close()


def crear_combo(nombre, descripcion, precio_combo, items):
    """items: lista de dicts {producto_id, producto_nombre, cantidad}."""
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO ProductoCombo (Nombre, Descripcion, PrecioCombo) VALUES (?,?,?)",
        (nombre, descripcion, precio_combo))
    combo_id = cur.lastrowid
    for item in items:
        cur.execute("INSERT INTO ItemCombo (ComboId, ProductoId, ProductoNombre, Cantidad) VALUES (?,?,?,?)",
            (combo_id, item["producto_id"], item["producto_nombre"], item["cantidad"]))
    conn.commit()
    conn.close()
    return combo_id


def _combos_con_items(cur, combos):
    for c in combos:
        cur.execute("SELECT * FROM ItemCombo WHERE ComboId=?", (c["Id"],))
        c["items"] = [dict(r) for r in cur.fetchall()]
    return combos


def get_combos(activo=True):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ProductoCombo WHERE Activo=? ORDER BY FechaCreado DESC", (1 if activo else 0,))
    combos = _combos_con_items(cur, [dict(r) for r in cur.fetchall()])
    conn.close()
    return combos


def get_combo_por_id(combo_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ProductoCombo WHERE Id=?", (combo_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    combo = _combos_con_items(cur, [dict(row)])[0]
    conn.close()
    return combo


def buscar_combos(query):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ProductoCombo WHERE Activo=1 AND Nombre LIKE ?", (f"%{query}%",))
    combos = _combos_con_items(cur, [dict(r) for r in cur.fetchall()])
    conn.close()
    return combos


def desactivar_combo(combo_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("UPDATE ProductoCombo SET Activo=0 WHERE Id=?", (combo_id,))
    conn.commit()
    conn.close()


def vender_combo(combo_id, cliente_id=None, cliente_nombre="Consumidor Final", cliente_telefono=""):
    """Vende un combo completo: verifica stock de todos los productos antes de
    descontar ninguno, descuenta stock de cada uno, registra una sola Venta por el
    PrecioCombo (ya con el descuento del combo incluido) y genera la garantia de
    cada producto (igual que una venta normal)."""
    combo = get_combo_por_id(combo_id)
    if not combo:
        return {"error": "Combo no encontrado."}
    if not combo["Activo"]:
        return {"error": f"El combo '{combo['Nombre']}' esta desactivado."}
    items = combo["items"]
    if not items:
        return {"error": f"El combo '{combo['Nombre']}' no tiene productos configurados."}

    for item in items:
        producto = get_product_by_id(item["ProductoId"])
        stock = producto["Stock"] if producto else 0
        if stock < item["Cantidad"]:
            return {"error": (f"Stock insuficiente de {item['ProductoNombre']} "
                               f"({int(stock)} disponibles, se necesitan {item['Cantidad']}) para vender el combo.")}

    for item in items:
        remove_stock(item["ProductoId"], item["Cantidad"], razon=f"Venta combo {combo['Nombre']}")

    descripcion = f"Combo {combo['Nombre']}: " + ", ".join(f"{i['Cantidad']}x {i['ProductoNombre']}" for i in items)
    total = combo["PrecioCombo"]
    venta_id, total_cobrado, puntos_info = registrar_venta_cliente(cliente_id, descripcion, total)

    garantias = [
        generar_garantia_venta(
            venta_id, item["ProductoId"], item["ProductoNombre"],
            cliente_id=cliente_id, cliente_nombre=cliente_nombre, cliente_telefono=cliente_telefono
        )
        for item in items
    ]

    return {
        "venta_id": venta_id,
        "combo": combo,
        "items": items,
        "total": total_cobrado,
        "garantias": garantias,
        "puntos": puntos_info
    }


# ── UNIDADES DE MEDIDA ────────────────────────────────

def init_unidades_medida():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS UnidadMedida (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            ProductoId INTEGER,
            ProductoNombre TEXT,
            UnidadBase TEXT,
            CantidadPorUnidad NUMERIC DEFAULT 1,
            PrecioUnitario NUMERIC,
            PrecioPorUnidad NUMERIC,
            Activo INTEGER DEFAULT 1,
            FechaCreado DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def set_unidad_medida(producto_id, producto_nombre, unidad_base, cantidad_por_unidad,
                       precio_unitario, precio_por_unidad=None):
    """Configura (crea o actualiza) una unidad de medida para un producto. Si no se
    da un precio especial para la unidad, se calcula multiplicando el precio
    individual por la cantidad (sin descuento por volumen)."""
    conn = nimbo_connect()
    cur = conn.cursor()
    precio_final = round(precio_por_unidad, 2) if precio_por_unidad is not None else round(precio_unitario * cantidad_por_unidad, 2)
    cur.execute("SELECT Id FROM UnidadMedida WHERE ProductoId=? AND UnidadBase=?", (producto_id, unidad_base))
    existente = cur.fetchone()
    if existente:
        cur.execute("""UPDATE UnidadMedida SET CantidadPorUnidad=?, PrecioUnitario=?, PrecioPorUnidad=?,
            Activo=1 WHERE Id=?""", (cantidad_por_unidad, precio_unitario, precio_final, existente["Id"]))
    else:
        cur.execute("""INSERT INTO UnidadMedida
            (ProductoId, ProductoNombre, UnidadBase, CantidadPorUnidad, PrecioUnitario, PrecioPorUnidad)
            VALUES (?,?,?,?,?,?)""",
            (producto_id, producto_nombre, unidad_base, cantidad_por_unidad, precio_unitario, precio_final))
    conn.commit()
    conn.close()
    return precio_final


def get_unidad_medida(producto_id, unidad_base):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM UnidadMedida WHERE ProductoId=? AND UnidadBase=? AND Activo=1",
        (producto_id, unidad_base))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_unidades_medida_producto(producto_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM UnidadMedida WHERE ProductoId=? AND Activo=1", (producto_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_todas_unidades_medida():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM UnidadMedida WHERE Activo=1 ORDER BY ProductoNombre, UnidadBase")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ── PROGRAMA DE LEALTAD (PUNTOS) ───────────────────────

PUNTOS_POR_QUETZAL = 1     # 1 punto por cada Q1 de compra
PUNTOS_POR_CANJE = 100     # unidad minima de canje (multiplos de esto)
VALOR_CANJE = 10.0         # cuantos quetzales valen PUNTOS_POR_CANJE puntos
DESCUENTO_EXTRA_ORO = 0.05  # 5% extra para clientes nivel Oro

# Umbrales de nivel evaluados sobre PuntosAcumulados (historico de por vida, no el
# saldo disponible - el nivel no baja solo porque el cliente canjeo puntos).
NIVELES_LEALTAD = [
    (1000, "Oro"),
    (500, "Plata"),
    (0, "Bronce"),
]


def init_puntos():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS PuntosCliente (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            ClienteId INTEGER UNIQUE,
            ClienteNombre TEXT,
            PuntosAcumulados NUMERIC DEFAULT 0,
            PuntosUsados NUMERIC DEFAULT 0,
            PuntosCancelados NUMERIC DEFAULT 0,
            FechaUltimaActualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS MovimientoPuntos (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            ClienteId INTEGER,
            Tipo TEXT,
            Puntos NUMERIC,
            Descripcion TEXT,
            VentaId INTEGER,
            Fecha DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def puntos_a_quetzales(puntos):
    return round((puntos or 0) / PUNTOS_POR_CANJE * VALOR_CANJE, 2)


def get_nivel_lealtad(puntos_acumulados):
    for umbral, nivel in NIVELES_LEALTAD:
        if (puntos_acumulados or 0) >= umbral:
            return nivel
    return "Bronce"


def get_puntos_cliente(cliente_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM PuntosCliente WHERE ClienteId=?", (cliente_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_saldo_puntos(cliente_id):
    """Puntos disponibles para canjear ahora mismo (acumulados - usados - cancelados)."""
    p = get_puntos_cliente(cliente_id)
    if not p:
        return 0
    return int(p["PuntosAcumulados"] - p["PuntosUsados"] - p["PuntosCancelados"])


def get_clientes_con_puntos():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT *, (PuntosAcumulados - PuntosUsados - PuntosCancelados) as Saldo
        FROM PuntosCliente
        WHERE (PuntosAcumulados - PuntosUsados - PuntosCancelados) > 0
        ORDER BY Saldo DESC""")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def _get_o_crear_puntos_cliente(cur, cliente_id, cliente_nombre):
    cur.execute("SELECT * FROM PuntosCliente WHERE ClienteId=?", (cliente_id,))
    row = cur.fetchone()
    if row:
        return dict(row)
    cur.execute("INSERT INTO PuntosCliente (ClienteId, ClienteNombre) VALUES (?,?)", (cliente_id, cliente_nombre))
    cur.execute("SELECT * FROM PuntosCliente WHERE ClienteId=?", (cliente_id,))
    return dict(cur.fetchone())


def ganar_puntos(cliente_id, cliente_nombre, total, venta_id):
    """Suma puntos ganados por una compra (1 punto por cada Q1 de `total`, ya con
    todos los descuentos/creditos aplicados - se gana sobre lo que el cliente
    realmente termina pagando), multiplicado por el PuntosMultiplicador del grupo
    del cliente (VIP = puntos dobles, ver GRUPOS_CLIENTE_DEFAULT). No hace nada si
    no hay cliente (Consumidor Final no acumula puntos) o si el total no alcanza
    para al menos 1 punto."""
    if not cliente_id or not total or total <= 0:
        return None

    cliente = get_cliente_por_id(cliente_id)
    grupo = (cliente.get("GrupoCliente") if cliente else None) or "detallista"
    grupo_descuento = get_grupo_descuento(grupo)
    multiplicador = float(grupo_descuento["PuntosMultiplicador"]) if grupo_descuento else 1

    puntos_ganados = int(total * PUNTOS_POR_QUETZAL * multiplicador)
    if puntos_ganados <= 0:
        return None

    conn = nimbo_connect()
    cur = conn.cursor()
    _get_o_crear_puntos_cliente(cur, cliente_id, cliente_nombre)
    cur.execute("""UPDATE PuntosCliente SET PuntosAcumulados=PuntosAcumulados+?, ClienteNombre=?,
        FechaUltimaActualizacion=CURRENT_TIMESTAMP WHERE ClienteId=?""",
        (puntos_ganados, cliente_nombre, cliente_id))
    cur.execute("""INSERT INTO MovimientoPuntos (ClienteId, Tipo, Puntos, Descripcion, VentaId)
        VALUES (?, 'GANADO', ?, ?, ?)""",
        (cliente_id, puntos_ganados, f"Compra Q{total}", venta_id))
    conn.commit()
    cur.execute("SELECT * FROM PuntosCliente WHERE ClienteId=?", (cliente_id,))
    p = dict(cur.fetchone())
    conn.close()

    saldo = int(p["PuntosAcumulados"] - p["PuntosUsados"] - p["PuntosCancelados"])
    return {
        "puntos_ganados": puntos_ganados,
        "saldo_disponible": saldo,
        "valor_disponible": puntos_a_quetzales(saldo),
        "nivel": get_nivel_lealtad(p["PuntosAcumulados"])
    }


def canjear_puntos(cliente_id, cliente_nombre, puntos):
    """Canjea puntos ahora mismo: se descuentan del saldo de inmediato (PuntosUsados),
    pero el credito en quetzales queda pendiente (MovimientoPuntos con VentaId=NULL)
    hasta que se aplique a una venta - ver consumir_credito_puntos_pendiente(), que se
    llama automaticamente al cerrar la siguiente venta del cliente. Esto es lo que
    permite "aplica Q de descuento en la siguiente compra" sin una venta activa."""
    if not cliente_id:
        return {"error": "No se puede canjear puntos sin un cliente."}
    if not puntos or puntos <= 0:
        return {"error": "La cantidad de puntos a canjear debe ser mayor a 0."}
    if puntos % PUNTOS_POR_CANJE != 0:
        return {"error": f"Los puntos se canjean en multiplos de {PUNTOS_POR_CANJE}."}
    saldo = get_saldo_puntos(cliente_id)
    if saldo < puntos:
        return {"error": f"{cliente_nombre} solo tiene {saldo} puntos disponibles, no alcanza para canjear {puntos}."}

    credito = puntos_a_quetzales(puntos)
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""UPDATE PuntosCliente SET PuntosUsados=PuntosUsados+?,
        FechaUltimaActualizacion=CURRENT_TIMESTAMP WHERE ClienteId=?""", (puntos, cliente_id))
    cur.execute("""INSERT INTO MovimientoPuntos (ClienteId, Tipo, Puntos, Descripcion, VentaId)
        VALUES (?, 'USADO', ?, ?, NULL)""",
        (cliente_id, puntos, f"Canje de {puntos} puntos por Q{credito} (pendiente de aplicar en la siguiente compra)"))
    conn.commit()
    conn.close()
    return {"puntos": puntos, "credito": credito, "saldo_restante": saldo - puntos}


def peek_credito_puntos_pendiente(cliente_id):
    """Puntos ya canjeados (ver canjear_puntos) que todavia no se han aplicado a
    ninguna venta. Solo consulta, no modifica nada."""
    if not cliente_id:
        return 0
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT IFNULL(SUM(Puntos),0) as puntos FROM MovimientoPuntos
        WHERE ClienteId=? AND Tipo='USADO' AND VentaId IS NULL""", (cliente_id,))
    puntos = cur.fetchone()["puntos"]
    conn.close()
    return int(puntos or 0)


def consumir_credito_puntos_pendiente(cliente_id, venta_id):
    """Marca todos los canjes pendientes del cliente como aplicados a esta venta
    (les asigna el VentaId). Debe llamarse justo despues de insertar la Venta cuyo
    Total ya reflejaba ese credito (ver calcular_ajuste_puntos)."""
    if not cliente_id:
        return
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""UPDATE MovimientoPuntos SET VentaId=?
        WHERE ClienteId=? AND Tipo='USADO' AND VentaId IS NULL""", (venta_id, cliente_id))
    conn.commit()
    conn.close()


def calcular_ajuste_puntos(cliente_id, total):
    """Calcula (sin modificar nada todavia) cuanto se le resta a `total` por credito
    de puntos ya canjeado y pendiente de aplicar, y por el 5% extra de nivel Oro.
    Se usa ANTES de insertar la Venta para saber el Total final real; despues de
    insertarla hay que llamar consumir_credito_puntos_pendiente() y ganar_puntos()
    con el venta_id ya conocido. Si el credito pendiente supera el total de esta
    venta, se aplica solo hasta cubrirlo (el resto no se parte, se da por usado)."""
    if not cliente_id or not total or total <= 0:
        return {"credito_puntos": 0, "descuento_oro": 0, "total_final": round(total or 0, 2)}

    credito_puntos = min(puntos_a_quetzales(peek_credito_puntos_pendiente(cliente_id)), total)
    restante = round(total - credito_puntos, 2)

    p = get_puntos_cliente(cliente_id)
    nivel = get_nivel_lealtad(p["PuntosAcumulados"]) if p else "Bronce"
    descuento_oro = round(restante * DESCUENTO_EXTRA_ORO, 2) if nivel == "Oro" else 0

    total_final = round(restante - descuento_oro, 2)
    return {"credito_puntos": credito_puntos, "descuento_oro": descuento_oro, "total_final": total_final}


def formatear_nota_ajuste_puntos(ajuste):
    """Texto para anexar a la Descripcion de una Venta cuando calcular_ajuste_puntos
    resto algo del total (credito de puntos y/o el 5% extra de nivel Oro). Vacio si
    no aplico ninguno de los dos."""
    extra = []
    if ajuste.get("credito_puntos"):
        extra.append(f"credito de puntos -Q{ajuste['credito_puntos']}")
    if ajuste.get("descuento_oro"):
        extra.append(f"5% nivel Oro -Q{ajuste['descuento_oro']}")
    return " | " + " + ".join(extra) if extra else ""


# ── CAJA REGISTRADORA ─────────────────────────────────

DENOMINACIONES = [200, 100, 50, 20, 10, 5, 1]


def _total_denominaciones(denoms):
    return sum(int(v) * int(d) for d, v in (denoms or {}).items())


def _calcular_cambio_denominaciones(monto, disponible):
    """Desglose codicioso (billete mas grande primero) usando solo lo disponible.
    Retorna dict de denominaciones a entregar, o {} si monto no es entero o no alcanza."""
    monto = round(monto, 2)
    if monto <= 0:
        return {}
    if monto != int(monto):
        return {}
    restante = int(monto)
    resultado = {}
    for d in DENOMINACIONES:
        disp = int(disponible.get(str(d), 0))
        usar = min(disp, restante // d)
        if usar > 0:
            resultado[str(d)] = usar
            restante -= usar * d
    if restante != 0:
        return {}
    return resultado


def init_caja():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS CajaTurno (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            EmpleadoId INTEGER,
            EmpleadoNombre TEXT,
            FechaApertura DATETIME DEFAULT CURRENT_TIMESTAMP,
            FechaCierre DATETIME,
            FondoInicial TEXT,
            EfectivoEsperado NUMERIC DEFAULT 0,
            EfectivoContado NUMERIC,
            TotalVentas NUMERIC DEFAULT 0,
            TotalEfectivo NUMERIC DEFAULT 0,
            TotalTarjeta NUMERIC DEFAULT 0,
            TotalMixto NUMERIC DEFAULT 0,
            Diferencia NUMERIC,
            Estado TEXT DEFAULT 'ABIERTO'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS MovimientoCaja (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            TurnoId INTEGER,
            Tipo TEXT,
            Monto NUMERIC DEFAULT 0,
            Descripcion TEXT,
            Denominaciones TEXT,
            Fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            VentaId INTEGER,
            FOREIGN KEY (TurnoId) REFERENCES CajaTurno(Id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ItemCarrito (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            TurnoId INTEGER,
            ProductoId INTEGER,
            ProductoNombre TEXT,
            Cantidad NUMERIC,
            PrecioUnit NUMERIC,
            Total NUMERIC,
            FOREIGN KEY (TurnoId) REFERENCES CajaTurno(Id)
        )
    """)
    conn.commit()
    conn.close()


def get_turno_abierto():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM CajaTurno WHERE Estado='ABIERTO' ORDER BY Id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_turno(turno_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM CajaTurno WHERE Id=?", (turno_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def abrir_turno(empleado_id, empleado_nombre, fondo_inicial):
    """Crea el turno con su fondo inicial. FondoInicial queda fijo desde este INSERT:
    no existe en todo el codebase ninguna funcion ni endpoint que haga UPDATE de esa
    columna despues de creada (la consola SQL del dashboard es solo SELECT y solo
    contra la base de Aronium, no contra nimbo.db). Si se abrio con datos incorrectos,
    la unica correccion posible es que un admin anule el turno (ver anular_turno) y
    se abra uno nuevo."""
    import json
    total = _total_denominaciones(fondo_inicial)
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""INSERT INTO CajaTurno
        (EmpleadoId, EmpleadoNombre, FondoInicial, EfectivoEsperado, Estado)
        VALUES (?,?,?,?, 'ABIERTO')""",
        (empleado_id, empleado_nombre, json.dumps(fondo_inicial), total))
    turno_id = cur.lastrowid
    cur.execute("""INSERT INTO MovimientoCaja (TurnoId, Tipo, Monto, Descripcion, Denominaciones)
        VALUES (?, 'FONDO', ?, 'Fondo inicial de caja', ?)""",
        (turno_id, total, json.dumps(fondo_inicial)))
    conn.commit()
    conn.close()
    return turno_id, total


def abrir_turno_simple(empleado_id, empleado_nombre, monto_total):
    """Igual que abrir_turno pero con el fondo inicial dado como un monto total, sin
    desglose por denominacion (usado cuando el cierre anterior solo dejo un monto
    sugerido, ver get_fondo_sugerido)."""
    import json
    monto_total = round(float(monto_total), 2)
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""INSERT INTO CajaTurno
        (EmpleadoId, EmpleadoNombre, FondoInicial, EfectivoEsperado, Estado)
        VALUES (?,?,?,?, 'ABIERTO')""",
        (empleado_id, empleado_nombre, json.dumps({"total": monto_total}), monto_total))
    turno_id = cur.lastrowid
    cur.execute("""INSERT INTO MovimientoCaja (TurnoId, Tipo, Monto, Descripcion)
        VALUES (?, 'FONDO', ?, 'Fondo inicial de caja')""",
        (turno_id, monto_total))
    conn.commit()
    conn.close()
    return turno_id, monto_total


def get_ultimo_cierre_denominaciones():
    """Desglose de denominaciones que se conto fisicamente al cerrar el turno CERRADO
    mas reciente (turnos ANULADOS no cuentan, nunca llegan a un conteo real). Se usa
    para que el fondo inicial del siguiente turno se sugiera solo, sin volver a contar
    billete por billete. Retorna None si no hay ningun turno cerrado todavia."""
    import json
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT Id FROM CajaTurno WHERE Estado='CERRADO' ORDER BY FechaCierre DESC LIMIT 1")
    turno = cur.fetchone()
    if not turno:
        conn.close()
        return None
    cur.execute("""SELECT Denominaciones FROM MovimientoCaja
        WHERE TurnoId=? AND Tipo='AJUSTE' AND Denominaciones IS NOT NULL
        ORDER BY Id DESC LIMIT 1""", (turno["Id"],))
    mov = cur.fetchone()
    conn.close()
    if not mov or not mov["Denominaciones"]:
        return None
    return json.loads(mov["Denominaciones"])


def get_fondo_sugerido():
    """Monto total sugerido como fondo inicial del siguiente turno (lo que quedo
    contado en caja al cerrar el turno anterior, menos lo retirado a caja fuerte en
    ese cierre). Se guarda en Configuracion al cerrar (ver cerrar_turno) porque, a
    diferencia de get_ultimo_cierre_denominaciones, no depende de que se haya
    contado por denominacion. Retorna None si todavia no se ha cerrado ningun turno."""
    from core.configuracion import get_config
    valor = get_config("caja_fondo_sugerido")
    if valor is None:
        return None
    try:
        return round(float(valor), 2)
    except (TypeError, ValueError):
        return None


def get_caja_fuerte_acumulada():
    """Total historico acumulado en la caja fuerte, sumado cada vez que un cierre de
    turno incluye un retiro (ver cerrar_turno). Vive en Configuracion, no en CajaTurno,
    porque es un saldo que persiste entre turnos."""
    from core.configuracion import get_config
    return round(float(get_config("caja_fuerte_acumulada", "0") or "0"), 2)


def anular_turno(turno_id, motivo, anulado_por=""):
    """Anula un turno ABIERTO por un error grave (ej. fondo mal capturado, apertura
    duplicada). Solo cambia Estado/FechaCierre - jamas toca FondoInicial. Las ventas
    que ya se hayan registrado en ese turno NO se revierten automaticamente (stock,
    Venta y Kardex quedan igual); el llamador debe avisar de eso si aplica."""
    turno = get_turno(turno_id)
    if not turno:
        return {"error": "Turno no encontrado."}
    if turno["Estado"] != "ABIERTO":
        return {"error": f"Solo se puede anular un turno abierto (este esta {turno['Estado']})."}
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("UPDATE CajaTurno SET Estado='ANULADO', FechaCierre=CURRENT_TIMESTAMP WHERE Id=?", (turno_id,))
    cur.execute("""INSERT INTO MovimientoCaja (TurnoId, Tipo, Monto, Descripcion)
        VALUES (?, 'ANULACION', 0, ?)""",
        (turno_id, f"Anulado por {anulado_por or 'admin'}: {motivo}"))
    conn.commit()
    conn.close()
    resultado = get_turno(turno_id)
    resultado["ventas_no_revertidas"] = turno["TotalVentas"]
    return resultado


def cerrar_turno(turno_id, contado_total, retiro_caja_fuerte=0, conteo_fisico=None):
    """Cierra el turno con el monto total contado en caja. El desglose por
    denominacion (conteo_fisico) es opcional, solo para auditoria - ya no es
    obligatorio contar billete por billete. Si retiro_caja_fuerte > 0 se separa de lo
    contado, se registra como movimiento RETIRO y se suma al acumulado historico de
    caja fuerte (Configuracion.caja_fuerte_acumulada). Lo que sobra
    (contado - retiro) queda guardado como fondo sugerido para el siguiente turno
    (Configuracion.caja_fondo_sugerido, ver get_fondo_sugerido)."""
    import json
    from core.configuracion import get_config, set_config
    turno = get_turno(turno_id)
    if not turno:
        return None
    contado = round(float(contado_total), 2)
    retiro = round(float(retiro_caja_fuerte or 0), 2)
    diferencia = round(contado - turno["EfectivoEsperado"], 2)

    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""UPDATE CajaTurno SET EfectivoContado=?, Diferencia=?, Estado='CERRADO',
        FechaCierre=CURRENT_TIMESTAMP WHERE Id=?""", (contado, diferencia, turno_id))
    cur.execute("""INSERT INTO MovimientoCaja (TurnoId, Tipo, Monto, Descripcion, Denominaciones)
        VALUES (?, 'AJUSTE', ?, 'Cierre de turno - conteo fisico', ?)""",
        (turno_id, diferencia, json.dumps(conteo_fisico) if conteo_fisico else None))
    if retiro > 0:
        cur.execute("""INSERT INTO MovimientoCaja (TurnoId, Tipo, Monto, Descripcion)
            VALUES (?, 'RETIRO', ?, 'Retiro a caja fuerte (cierre de turno)')""",
            (turno_id, retiro))
    conn.commit()
    conn.close()

    fondo_manana = round(contado - retiro, 2)
    set_config("caja_fondo_sugerido", str(fondo_manana))
    acumulado = round(float(get_config("caja_fuerte_acumulada", "0") or "0") + retiro, 2)
    if retiro > 0:
        set_config("caja_fuerte_acumulada", str(acumulado))

    turno = get_turno(turno_id)
    turno["RetiroCajaFuerte"] = retiro
    turno["FondoSugerido"] = fondo_manana
    turno["CajaFuerteAcumulada"] = acumulado
    return turno


def get_denominaciones_actuales(turno_id):
    import json
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT Denominaciones FROM MovimientoCaja
        WHERE TurnoId=? AND Tipo IN ('FONDO','VENTA','RETIRO') AND Denominaciones IS NOT NULL""", (turno_id,))
    actuales = {str(d): 0 for d in DENOMINACIONES}
    for row in cur.fetchall():
        deltas = json.loads(row["Denominaciones"])
        for k, v in deltas.items():
            if k in actuales:
                actuales[k] += int(v)
    conn.close()
    return actuales


def sencillo_bajo(turno_id):
    actuales = get_denominaciones_actuales(turno_id)
    pequenas = sum(int(actuales.get(str(d), 0)) * d for d in [20, 10, 5, 1])
    return pequenas < 200, pequenas


def get_carrito(turno_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ItemCarrito WHERE TurnoId=? ORDER BY Id", (turno_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def agregar_a_carrito(turno_id, producto_id, producto_nombre, cantidad, precio_unit):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ItemCarrito WHERE TurnoId=? AND ProductoId=?", (turno_id, producto_id))
    existente = cur.fetchone()
    if existente:
        nueva_cantidad = existente["Cantidad"] + cantidad
        nuevo_total = round(nueva_cantidad * precio_unit, 2)
        cur.execute("UPDATE ItemCarrito SET Cantidad=?, Total=? WHERE Id=?",
            (nueva_cantidad, nuevo_total, existente["Id"]))
    else:
        total = round(cantidad * precio_unit, 2)
        cur.execute("""INSERT INTO ItemCarrito (TurnoId, ProductoId, ProductoNombre, Cantidad, PrecioUnit, Total)
            VALUES (?,?,?,?,?,?)""", (turno_id, producto_id, producto_nombre, cantidad, precio_unit, total))
    conn.commit()
    conn.close()
    return get_carrito(turno_id)


def quitar_de_carrito(item_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT TurnoId FROM ItemCarrito WHERE Id=?", (item_id,))
    row = cur.fetchone()
    turno_id = row["TurnoId"] if row else None
    cur.execute("DELETE FROM ItemCarrito WHERE Id=?", (item_id,))
    conn.commit()
    conn.close()
    return get_carrito(turno_id) if turno_id else []


def vaciar_carrito(turno_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM ItemCarrito WHERE TurnoId=?", (turno_id,))
    conn.commit()
    conn.close()


def cobrar_carrito(turno_id, metodo_pago, cliente_id=None, monto_efectivo=None, monto_tarjeta=None, denominaciones_recibidas=None):
    import json
    items = get_carrito(turno_id)
    if not items:
        return {"error": "El carrito esta vacio."}

    subtotal = round(sum(i["Total"] for i in items), 2)
    descuento = calcular_descuento(
        cliente_id=cliente_id,
        productos=[{"producto_id": i["ProductoId"], "subtotal": i["Total"]} for i in items],
        total=subtotal
    )
    total = round(subtotal - descuento["monto_descuento"], 2) if descuento else subtotal

    ajuste_puntos = calcular_ajuste_puntos(cliente_id, total)
    total = ajuste_puntos["total_final"]

    metodo_pago = (metodo_pago or "").lower()

    if metodo_pago == "efectivo":
        monto_efectivo = total if monto_efectivo is None else monto_efectivo
        monto_tarjeta = 0
        if monto_efectivo < total:
            return {"error": f"El monto recibido (Q{monto_efectivo}) es menor al total (Q{total})."}
    elif metodo_pago == "tarjeta":
        monto_efectivo = 0
        monto_tarjeta = total
    elif metodo_pago == "mixto":
        if monto_efectivo is None or monto_tarjeta is None:
            return {"error": "Especifica el monto en efectivo y en tarjeta."}
        if round(monto_efectivo + monto_tarjeta, 2) != total:
            return {"error": f"Los montos de efectivo y tarjeta deben sumar el total (Q{total})."}
    else:
        return {"error": "Metodo de pago invalido. Usa efectivo, tarjeta o mixto."}

    # Verificar stock de todos los productos antes de descontar nada
    for item in items:
        producto = get_product_by_id(item["ProductoId"])
        stock = producto["Stock"] if producto else 0
        if stock < item["Cantidad"]:
            return {"error": f"Stock insuficiente de {item['ProductoNombre']} ({int(stock)} disponibles, se necesitan {item['Cantidad']})."}

    for item in items:
        remove_stock(item["ProductoId"], item["Cantidad"], razon="Venta en caja")

    descripcion = ", ".join([f"{i['Cantidad']}x {i['ProductoNombre']}" for i in items])
    if descuento:
        descripcion += f" | Descuento {descuento['nombre']}: -Q{descuento['monto_descuento']}"
    descripcion += formatear_nota_ajuste_puntos(ajuste_puntos)
    now = datetime.now()
    mes, anio = now.month, now.year
    trimestre = (mes - 1) // 3 + 1

    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO Venta (ClienteId, Descripcion, Total, Mes, Trimestre, Anio) VALUES (?,?,?,?,?,?)",
        (cliente_id, descripcion, total, mes, trimestre, anio))
    venta_id = cur.lastrowid
    if cliente_id:
        cur.execute("UPDATE Cliente SET UltimaCompra=? WHERE Id=?", (now.isoformat(), cliente_id))

    cambio = round(monto_efectivo - total, 2) if metodo_pago == "efectivo" else 0
    efectivo_retenido = total if metodo_pago in ("efectivo", "mixto") else 0

    denom_delta = None
    if denominaciones_recibidas and efectivo_retenido > 0:
        actuales = get_denominaciones_actuales(turno_id)
        disponible_para_vuelto = {
            str(d): int(actuales.get(str(d), 0)) + int(denominaciones_recibidas.get(str(d), 0))
            for d in DENOMINACIONES
        }
        vuelto_denoms = _calcular_cambio_denominaciones(cambio, disponible_para_vuelto) if cambio > 0 else {}
        denom_delta = {
            str(d): int(denominaciones_recibidas.get(str(d), 0)) - int(vuelto_denoms.get(str(d), 0))
            for d in DENOMINACIONES
        }

    cur.execute("""INSERT INTO MovimientoCaja (TurnoId, Tipo, Monto, Descripcion, Denominaciones, VentaId)
        VALUES (?, 'VENTA', ?, ?, ?, ?)""",
        (turno_id, efectivo_retenido, descripcion, json.dumps(denom_delta) if denom_delta else None, venta_id))

    campo_total = {"efectivo": "TotalEfectivo", "tarjeta": "TotalTarjeta", "mixto": "TotalMixto"}[metodo_pago]
    cur.execute(f"""UPDATE CajaTurno SET TotalVentas=TotalVentas+?, {campo_total}={campo_total}+?,
        EfectivoEsperado=EfectivoEsperado+? WHERE Id=?""", (total, total, efectivo_retenido, turno_id))

    conn.commit()
    conn.close()

    vaciar_carrito(turno_id)

    cliente_nombre_garantia = "Consumidor Final"
    cliente_telefono_garantia = ""
    if cliente_id:
        cliente_row = get_cliente_por_id(cliente_id)
        if cliente_row:
            cliente_nombre_garantia = cliente_row["Nombre"]
            cliente_telefono_garantia = cliente_row.get("Telefono") or ""

    garantias = [
        generar_garantia_venta(
            venta_id, item["ProductoId"], item["ProductoNombre"],
            cliente_id=cliente_id, cliente_nombre=cliente_nombre_garantia,
            cliente_telefono=cliente_telefono_garantia, fecha_venta=now
        )
        for item in items
    ]

    puntos_info = None
    if cliente_id:
        consumir_credito_puntos_pendiente(cliente_id, venta_id)
        puntos_info = ganar_puntos(cliente_id, cliente_nombre_garantia, total, venta_id)

    return {
        "venta_id": venta_id,
        "items": items,
        "subtotal": subtotal,
        "descuento": descuento,
        "credito_puntos": ajuste_puntos["credito_puntos"],
        "descuento_oro": ajuste_puntos["descuento_oro"],
        "total": total,
        "metodo_pago": metodo_pago,
        "monto_efectivo": monto_efectivo,
        "monto_tarjeta": monto_tarjeta,
        "cambio": cambio,
        "garantias": garantias,
        "puntos": puntos_info,
        "fecha": now.strftime("%Y-%m-%d %H:%M:%S")
    }


def retirar_caja(turno_id, monto, descripcion="", denominaciones=None):
    import json
    turno = get_turno(turno_id)
    if not turno:
        return {"error": "No hay turno abierto."}
    if monto <= 0:
        return {"error": "El monto a retirar debe ser mayor a cero."}
    if monto > turno["EfectivoEsperado"]:
        return {"error": f"No hay suficiente efectivo esperado en caja (Q{turno['EfectivoEsperado']}) para retirar Q{monto}."}

    denom_delta = {k: -int(v) for k, v in denominaciones.items()} if denominaciones else None

    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""INSERT INTO MovimientoCaja (TurnoId, Tipo, Monto, Descripcion, Denominaciones)
        VALUES (?, 'RETIRO', ?, ?, ?)""",
        (turno_id, monto, descripcion or "Retiro de caja", json.dumps(denom_delta) if denom_delta else None))
    cur.execute("UPDATE CajaTurno SET EfectivoEsperado=EfectivoEsperado-? WHERE Id=?", (monto, turno_id))
    conn.commit()
    conn.close()

    bajo, pequenas = sencillo_bajo(turno_id)
    return {"ok": True, "monto": monto, "sencillo_bajo": bajo, "denominaciones_pequenas": pequenas}


def get_movimientos_caja(turno_id, limit=100):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM MovimientoCaja WHERE TurnoId=? ORDER BY Id DESC LIMIT ?", (turno_id, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ── INFORMACION DE PRODUCTOS ──────────────────────────

def set_descripcion_producto(producto_id, producto_nombre, descripcion, descripcion_corta=""):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""INSERT OR REPLACE INTO ProductoInfo 
        (ProductoId, ProductoNombre, Descripcion, DescripcionCorta, FechaActualizado)
        VALUES (?,?,?,?,CURRENT_TIMESTAMP)""",
        (producto_id, producto_nombre, descripcion, descripcion_corta))
    conn.commit()
    conn.close()

def get_descripcion_producto(producto_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ProductoInfo WHERE ProductoId=?", (producto_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_foto_producto(producto_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT RutaFoto FROM ProductoFoto WHERE ProductoId=? ORDER BY FechaSubida DESC LIMIT 1", (producto_id,))
    row = cur.fetchone()
    conn.close()
    return row["RutaFoto"] if row else None


# ── REPORTES ──────────────────────────────────────────

def get_reporte_dia():
    from datetime import datetime
    conn = nimbo_connect()
    cur = conn.cursor()
    hoy = datetime.now().strftime("%Y-%m-%d")
    cur.execute("""
        SELECT 
            COUNT(*) as total_ventas,
            IFNULL(SUM(Total), 0) as total_vendido
        FROM Venta 
        WHERE DATE(Fecha) >= DATE('now', '-1 day')
        AND Mes=? AND Anio=?
    """, (datetime.now().month, datetime.now().year))
    row = dict(cur.fetchone())
    conn.close()
    
    total_vendido = float(row["total_vendido"])
    
    # Obtener costo de productos vendidos desde Aronium
    conn_aronium = connect()
    cur2 = conn_aronium.cursor()
    
    nimbo_conn = nimbo_connect()
    cur3 = nimbo_conn.cursor()
    cur3.execute("""
        SELECT Descripcion, Total FROM Venta 
        WHERE DATE(Fecha) >= DATE('now', '-1 day')
        AND Mes=? AND Anio=?
    """, (datetime.now().month, datetime.now().year))
    ventas = cur3.fetchall()
    nimbo_conn.close()
    
    total_costo = 0
    for venta in ventas:
        desc = venta["Descripcion"]
        import re
        match = re.search(r'(\d+)x (.+?) a Q', desc)
        if match:
            cantidad = int(match.group(1))
            nombre = match.group(2).strip()
            cur2.execute("SELECT Cost FROM Product WHERE Name LIKE ?", (f"%{nombre}%",))
            prod = cur2.fetchone()
            if prod:
                total_costo += float(prod["Cost"]) * cantidad
    
    conn_aronium.close()
    
    comision_pos = total_vendido * 0.06
    ganancia_bruta = total_vendido - total_costo
    ganancia_neta = ganancia_bruta - comision_pos
    
    return {
        "total_ventas": row["total_ventas"],
        "total_vendido": round(total_vendido, 2),
        "total_costo": round(total_costo, 2),
        "comision_pos": round(comision_pos, 2),
        "ganancia_bruta": round(ganancia_bruta, 2),
        "ganancia_neta": round(ganancia_neta, 2)
    }

def get_reporte_periodo(mes=None, trimestre=None, anio=None, semestre=None):
    from datetime import datetime
    if not anio:
        anio = datetime.now().year
    conn = nimbo_connect()
    cur = conn.cursor()
    
    if mes:
        cur.execute("SELECT COUNT(*) as ventas, SUM(Total) as total FROM Venta WHERE Mes=? AND Anio=?", (mes, anio))
    elif trimestre:
        meses = {1:[1,2,3], 2:[4,5,6], 3:[7,8,9], 4:[10,11,12]}
        m = meses.get(trimestre, [1,2,3])
        cur.execute("SELECT COUNT(*) as ventas, SUM(Total) as total FROM Venta WHERE Mes IN (?,?,?) AND Anio=?", (*m, anio))
    elif semestre:
        if semestre == 1:
            cur.execute("SELECT COUNT(*) as ventas, SUM(Total) as total FROM Venta WHERE Mes BETWEEN 1 AND 6 AND Anio=?", (anio,))
        else:
            cur.execute("SELECT COUNT(*) as ventas, SUM(Total) as total FROM Venta WHERE Mes BETWEEN 7 AND 12 AND Anio=?", (anio,))
    else:
        cur.execute("SELECT COUNT(*) as ventas, SUM(Total) as total FROM Venta WHERE Anio=?", (anio,))
    
    row = dict(cur.fetchone())
    
    cur.execute("""
        SELECT c.Nombre, COUNT(*) as compras, SUM(v.Total) as total
        FROM Venta v JOIN Cliente c ON v.ClienteId=c.Id
        WHERE v.Anio=?
        GROUP BY v.ClienteId ORDER BY total DESC LIMIT 5
    """, (anio,))
    mejores = [dict(r) for r in cur.fetchall()]
    
    conn.close()
    
    total = float(row["total"] or 0)
    comision = total * 0.06
    
    return {
        "total_ventas": row["ventas"] or 0,
        "total_vendido": round(total, 2),
        "comision_pos": round(comision, 2),
        "ganancia_estimada": round(total - comision, 2),
        "mejores_clientes": mejores
    }


def archivar_y_limpiar_anio(anio):
    import openpyxl
    from datetime import datetime
    
    # 1. Generar Excel de respaldo completo del año
    conn = nimbo_connect()
    cur = conn.cursor()
    
    wb = openpyxl.Workbook()
    
    # Hoja de ventas
    ws1 = wb.active
    ws1.title = "Ventas"
    ws1.append(["Fecha", "Descripcion", "Total", "Mes", "Trimestre", "Cliente"])
    cur.execute("""SELECT v.Fecha, v.Descripcion, v.Total, v.Mes, v.Trimestre,
        IFNULL(c.Nombre,'Sin cliente') FROM Venta v
        LEFT JOIN Cliente c ON v.ClienteId=c.Id
        WHERE v.Anio=? ORDER BY v.Fecha""", (anio,))
    for row in cur.fetchall():
        ws1.append(list(row))
    
    # Hoja de resumen
    ws2 = wb.create_sheet("Resumen")
    cur.execute("SELECT Mes, COUNT(*) as ventas, SUM(Total) as total FROM Venta WHERE Anio=? GROUP BY Mes ORDER BY Mes", (anio,))
    ws2.append(["Mes", "Ventas", "Total", "Comision POS 6%", "Ganancia"])
    for row in cur.fetchall():
        mes, ventas, total = row
        total = float(total or 0)
        comision = total * 0.06
        ws2.append([mes, ventas, total, round(comision, 2), round(total - comision, 2)])
    
    # Hoja de mejores clientes
    ws3 = wb.create_sheet("Mejores Clientes")
    ws3.append(["Cliente", "Compras", "Total"])
    cur.execute("""SELECT c.Nombre, COUNT(*) as compras, SUM(v.Total) as total
        FROM Venta v JOIN Cliente c ON v.ClienteId=c.Id
        WHERE v.Anio=? GROUP BY v.ClienteId ORDER BY total DESC""", (anio,))
    for row in cur.fetchall():
        ws3.append(list(row))
    
    filename = f"/home/ictor_axtor/micocina-dashboard/archivo_ventas_{anio}.xlsx"
    wb.save(filename)
    
    # 2. Guardar resumen anual en ResumenTrimestral
    cur.execute("SELECT SUM(Total) as total, COUNT(*) as ventas FROM Venta WHERE Anio=?", (anio,))
    resumen = cur.fetchone()
    cur.execute("""INSERT OR REPLACE INTO ResumenTrimestral 
        (Anio, Trimestre, TotalVentas, TotalOrdenes, ClientesActivos)
        VALUES (?, 0, ?, ?, 0)""",
        (anio, float(resumen["total"] or 0), resumen["ventas"] or 0))
    
    # 3. Borrar ventas del año
    cur.execute("DELETE FROM Venta WHERE Anio=?", (anio,))
    conn.commit()
    conn.close()
    
    return filename


def get_analisis_clientes():
    from datetime import datetime
    conn = nimbo_connect()
    cur = conn.cursor()
    mes = datetime.now().month
    trimestre = (mes - 1) // 3 + 1
    anio = datetime.now().year
    
    # Mejores clientes del trimestre
    meses = {1:[1,2,3], 2:[4,5,6], 3:[7,8,9], 4:[10,11,12]}
    m = meses.get(trimestre, [1,2,3])
    cur.execute("""SELECT c.Nombre, c.Telefono, COUNT(*) as compras, SUM(v.Total) as total,
        MAX(v.Fecha) as ultima_compra
        FROM Venta v JOIN Cliente c ON v.ClienteId=c.Id
        WHERE v.Mes IN (?,?,?) AND v.Anio=?
        GROUP BY v.ClienteId ORDER BY total DESC LIMIT 10""", (*m, anio))
    mejores = [dict(r) for r in cur.fetchall()]
    
    # Clientes inactivos (mas de 3 meses sin comprar)
    cur.execute("""SELECT Nombre, Telefono, UltimaCompra FROM Cliente
        WHERE UltimaCompra < datetime('now', '-3 months')
        OR UltimaCompra IS NULL
        ORDER BY UltimaCompra ASC LIMIT 10""")
    inactivos = [dict(r) for r in cur.fetchall()]
    
    # Total clientes
    cur.execute("SELECT COUNT(*) as total FROM Cliente")
    total_clientes = cur.fetchone()["total"]
    
    conn.close()
    return {
        "mejores": mejores,
        "inactivos": inactivos,
        "total_clientes": total_clientes,
        "trimestre": trimestre,
        "anio": anio
    }


def get_recordatorios():
    from datetime import datetime
    conn = nimbo_connect()
    cur = conn.cursor()
    recordatorios = []
    hoy = datetime.now()
    mes = hoy.month
    dia = hoy.day
    anio = hoy.year
    trimestre = (mes - 1) // 3 + 1
    
    # Pagos proximos
    pagos = get_pagos_proximos()
    for p in pagos:
        recordatorios.append({
            "tipo": "pago",
            "mensaje": f"Pago pendiente: {p['Nombre']} (dia {p['DiaPago']} de cada mes)",
            "urgencia": "alta" if dia >= p["DiaPago"] - 1 else "media"
        })
    
    # Recordatorios personales
    personales = get_recordatorios_personales()
    for r in personales:
        recordatorios.append({
            "tipo": "personal",
            "mensaje": r["Mensaje"],
            "urgencia": "media"
        })
    
    # Clientes sin comprar en 3 meses
    cur.execute("""SELECT Nombre, Telefono, UltimaCompra FROM Cliente
        WHERE UltimaCompra < datetime('now', '-3 months')
        AND UltimaCompra IS NOT NULL""")
    inactivos = cur.fetchall()
    if inactivos:
        recordatorios.append({
            "tipo": "clientes_inactivos",
            "mensaje": f"{len(inactivos)} cliente(s) sin comprar en 3 meses",
            "urgencia": "alta",
            "clientes": [dict(r) for r in inactivos]
        })
    
    # Inicio de mes - agradecimiento mejores clientes
    if dia <= 5:
        cur.execute("""SELECT c.Nombre FROM Venta v JOIN Cliente c ON v.ClienteId=c.Id
            WHERE v.Mes=? AND v.Anio=?
            GROUP BY v.ClienteId ORDER BY SUM(v.Total) DESC LIMIT 3""",
            (mes - 1 if mes > 1 else 12, anio if mes > 1 else anio - 1))
        mejores = cur.fetchall()
        if mejores:
            recordatorios.append({
                "tipo": "agradecimiento",
                "mensaje": f"Inicio de mes: agradece a tus mejores clientes del mes pasado ({', '.join([r['Nombre'] for r in mejores])})",
                "urgencia": "media"
            })
    
    # Analisis de evento cada trimestre (primer semana del trimestre)
    inicio_trimestre = {1: 1, 2: 4, 3: 7, 4: 10}
    if mes == inicio_trimestre[trimestre] and dia <= 7:
        recordatorios.append({
            "tipo": "evento",
            "mensaje": f"Inicio del trimestre Q{trimestre}: momento de analizar si conviene hacer un evento para clientes",
            "urgencia": "media"
        })
    
    # Fin de mes - reporte
    if dia >= 28:
        recordatorios.append({
            "tipo": "reporte",
            "mensaje": "Fin de mes: genera tu reporte mensual de ventas",
            "urgencia": "alta"
        })
    
    # Punto de equilibrio al inicio del mes
    if dia <= 3:
        recordatorios.append({
            "tipo": "equilibrio",
            "mensaje": f"Inicio de mes: verifica tu punto de equilibrio. Escribe 'punto de equilibrio' en el chat.",
            "urgencia": "media"
        })
    
    # Cumpleanos de clientes
    cumpleanos_hoy = get_cumpleanos_hoy()
    for c in cumpleanos_hoy:
        recordatorios.append({
            "tipo": "cumpleanos",
            "mensaje": f"Hoy es el cumpleanos de {c['Nombre']}! Enviale un mensaje de felicitacion.",
            "urgencia": "alta"
        })
    
    cumpleanos_proximos = get_cumpleanos_proximos(dias=3)
    for c in cumpleanos_proximos:
        recordatorios.append({
            "tipo": "cumpleanos",
            "mensaje": f"En {c['dias_para']} dia(s) es el cumpleanos de {c['Nombre']} ({c['Telefono'] or 'sin tel'})",
            "urgencia": "media"
        })
    
    # Recordatorio de publicar contenido
    from datetime import timedelta
    # Verificar si hay publicaciones recientes en Facebook (tabla de ventas como proxy)
    # Por ahora recordatorio fijo cada dia
    hora_actual = hoy.hour
    if hora_actual >= 8 and hora_actual <= 10:
        recordatorios.append({
            "tipo": "contenido",
            "mensaje": "Buenos dias. Recuerda publicar contenido hoy en Facebook, Instagram y TikTok.",
            "urgencia": "media"
        })
    
    # Follow ups de ordenes de reparacion
    ordenes_pendientes = get_ordenes_sin_followup(dias=3)
    for o in ordenes_pendientes:
        recordatorios.append({
            "tipo": "followup",
            "mensaje": f"Orden {o['NumeroOrden']} - {o['ClienteNombre']} ({o['ClienteTelefono']}): {o['Estado']} desde {o['FechaRecepcion'][:10]}",
            "urgencia": "alta"
        })

    # Cotizaciones por vencer o recien vencidas
    cotizaciones_seg = get_cotizaciones_seguimiento()
    for c in cotizaciones_seg:
        if c["Estado"] == "VENCIDA":
            mensaje = f"{c['NumeroC']} para {c['ClienteNombre']} vencio - dar seguimiento urgente"
        else:
            mensaje = f"{c['NumeroC']} para {c['ClienteNombre']} vence hoy - dar seguimiento"
        recordatorios.append({
            "tipo": "cotizacion",
            "mensaje": mensaje,
            "urgencia": "alta"
        })

    # Garantias que vencen en los proximos 7 dias
    garantias_por_vencer = get_garantias_por_vencer(dias=7)
    for g in garantias_por_vencer:
        recordatorios.append({
            "tipo": "garantia",
            "mensaje": f"{g['NumeroGarantia']} de {g['ClienteNombre']} ({g['ProductoNombre']}) vence pronto",
            "urgencia": "media"
        })

    # Cuentas por cobrar que vencen en los proximos 3 dias
    cuentas_por_vencer = get_cuentas_por_vencer(dias=3)
    for c in cuentas_por_vencer:
        recordatorios.append({
            "tipo": "cuentacobrar",
            "mensaje": f"{c['ClienteNombre']} debe Q{c['MontoPendiente']} ({c['Descripcion']}) - vence pronto",
            "urgencia": "alta"
        })

    # Cuentas por pagar (a proveedores) que vencen en los proximos 3 dias
    pagos_por_vencer = get_pagos_por_vencer(dias=3)
    for c in pagos_por_vencer:
        recordatorios.append({
            "tipo": "cuentapagar",
            "mensaje": f"Le debes Q{c['MontoPendiente']} a {c['ProveedorNombre']} ({c['Descripcion']}) - vence pronto",
            "urgencia": "alta"
        })

    # Productos con menos de DIAS_CRITICO_STOCK dias de stock proyectado
    alertas_predictivas = get_alertas_predictivas()
    for a in alertas_predictivas:
        if a["urgencia"] != "CRITICO":
            continue
        recordatorios.append({
            "tipo": "stock_predictivo",
            "mensaje": f"CRITICO: a este ritmo, {a['producto']} se agota en {a['dias_restantes']} dia(s) (stock: {a['stock_actual']:.0f}, vende {a['promedio_diario']:.1f}/dia)",
            "urgencia": "alta"
        })

    # Declaracion mensual de IVA ante la SAT: se declara dentro de los primeros
    # 10 dias (habiles, aproximado aqui como dias de calendario) del mes en
    # curso, correspondiente al mes recien cerrado.
    if dia <= 10:
        recordatorios.append({
            "tipo": "iva",
            "mensaje": "Recuerda declarar el IVA del mes pasado (formulario SAT-2046, "
                       "declaraguate.com). Escribe 'declaracion de IVA' en el chat para el resumen.",
            "urgencia": "alta"
        })

    conn.close()
    return recordatorios


# ── PAGOS FIJOS ───────────────────────────────────────

def init_pagos_fijos_ext():
    """Migracion: PagoFijo ya existia sin monto (solo guardaba nombre/dia/frecuencia
    como recordatorio) - se necesita el monto en quetzales para el flujo de caja
    proyectado (ver contabilidad.flujo_proyectado)."""
    conn = nimbo_connect()
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE PagoFijo ADD COLUMN Monto NUMERIC DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def agregar_pago_fijo(nombre, frecuencia="mensual", dia_pago=1, dias_antes=2, monto=0):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""INSERT INTO PagoFijo (Nombre, Frecuencia, DiaPago, DiasAntes, Monto)
        VALUES (?,?,?,?,?)""", (nombre, frecuencia, dia_pago, dias_antes, monto))
    conn.commit()
    conn.close()

def get_pagos_fijos():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM PagoFijo WHERE Activo=1 ORDER BY DiaPago")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def set_monto_pago_fijo(nombre, monto):
    """Fija/corrige el monto de un pago fijo ya registrado (los creados antes de
    que existiera la columna Monto quedaron en Q0)."""
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT Id, Nombre FROM PagoFijo WHERE Activo=1 AND Nombre LIKE ?", (f"%{nombre}%",))
    coincidencias = [dict(r) for r in cur.fetchall()]
    if len(coincidencias) == 1:
        cur.execute("UPDATE PagoFijo SET Monto=? WHERE Id=?", (monto, coincidencias[0]["Id"]))
        conn.commit()
    conn.close()
    return coincidencias

def get_pagos_proximos(dias=7):
    from datetime import datetime, timedelta
    conn = nimbo_connect()
    cur = conn.cursor()
    hoy = datetime.now()
    dia_hoy = hoy.day
    pagos = get_pagos_fijos()
    proximos = []
    for p in pagos:
        dia_recordatorio = p["DiaPago"] - p["DiasAntes"]
        if dia_recordatorio <= dia_hoy <= p["DiaPago"]:
            proximos.append(p)
    conn.close()
    return proximos

def agregar_recordatorio(mensaje, fecha=None, hora="08:00", repetir="no"):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO RecordatorioPersonal (Mensaje, Fecha, Hora, Repetir) VALUES (?,?,?,?)",
        (mensaje, fecha, hora, repetir))
    conn.commit()
    conn.close()

def get_recordatorios_personales():
    from datetime import datetime
    conn = nimbo_connect()
    cur = conn.cursor()
    hoy = datetime.now().strftime("%Y-%m-%d")
    cur.execute("SELECT * FROM RecordatorioPersonal WHERE Completado=0 AND (Fecha<=? OR Fecha IS NULL) ORDER BY Fecha", (hoy,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def borrar_pago_fijo(nombre):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("UPDATE PagoFijo SET Activo=0 WHERE Nombre LIKE ?", (f"%{nombre}%",))
    conn.commit()
    conn.close()


def get_ordenes_sin_followup(dias=3):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT o.*, c.Nombre as ClienteNombre, c.Telefono as ClienteTelefono
        FROM OrdenServicio o JOIN Cliente c ON o.ClienteId=c.Id
        WHERE o.Estado NOT IN ('ENTREGADO', 'LISTO')
        AND datetime(o.FechaRecepcion) < datetime('now', ? || ' days')
        ORDER BY o.FechaRecepcion ASC""", (f"-{dias}",))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def set_cumpleanos_cliente(cliente_id, fecha):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("UPDATE Cliente SET FechaCumpleanos=? WHERE Id=?", (fecha, cliente_id))
    conn.commit()
    conn.close()

def get_cumpleanos_hoy():
    from datetime import datetime
    hoy = datetime.now().strftime("%m-%d")
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT * FROM Cliente 
        WHERE strftime('%m-%d', FechaCumpleanos)=?
        AND FechaCumpleanos IS NOT NULL""", (hoy,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_cumpleanos_proximos(dias=7):
    from datetime import datetime, timedelta
    conn = nimbo_connect()
    cur = conn.cursor()
    proximos = []
    hoy = datetime.now()
    for i in range(1, dias+1):
        fecha = (hoy + timedelta(days=i)).strftime("%m-%d")
        cur.execute("""SELECT *, ? as dias_para FROM Cliente
            WHERE strftime('%m-%d', FechaCumpleanos)=?
            AND FechaCumpleanos IS NOT NULL""", (i, fecha))
        proximos.extend([dict(r) for r in cur.fetchall()])
    conn.close()
    return proximos


# ── HISTORIAL DE CHAT ─────────────────────────────────

def guardar_mensaje_chat(role, content, sesion="default"):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO ChatHistorial (Role, Content, Sesion) VALUES (?,?,?)",
        (role, content, sesion))
    conn.commit()
    conn.close()

def get_historial_chat(sesion="default", limit=50):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT Role, Content, Fecha FROM ChatHistorial
        WHERE Sesion=? ORDER BY Fecha DESC LIMIT ?""", (sesion, limit))
    rows = [dict(r) for r in reversed(cur.fetchall())]
    conn.close()
    return rows

def limpiar_historial_chat(sesion="default"):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM ChatHistorial WHERE Sesion=?", (sesion,))
    conn.commit()
    conn.close()


def archivar_chat_trimestral():
    import openpyxl
    from datetime import datetime
    conn = nimbo_connect()
    cur = conn.cursor()
    
    # Solo archivar mensajes de mas de 3 meses
    cur.execute("""SELECT * FROM ChatHistorial 
        WHERE Fecha < datetime('now', '-3 months')
        ORDER BY Fecha""")
    mensajes = [dict(r) for r in cur.fetchall()]
    
    if not mensajes:
        conn.close()
        return None
    
    # Generar Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Historial Chat"
    ws.append(["Fecha", "Role", "Mensaje"])
    for m in mensajes:
        ws.append([m["Fecha"], m["Role"], m["Content"][:500]])
    
    trimestre = (datetime.now().month - 1) // 3 + 1
    anio = datetime.now().year
    filename = f"/home/ictor_axtor/micocina-dashboard/chat_Q{trimestre}_{anio}.xlsx"
    wb.save(filename)
    
    # Borrar mensajes archivados
    cur.execute("DELETE FROM ChatHistorial WHERE Fecha < datetime('now', '-3 months')")
    
    # Mantener solo ultimos 500 mensajes
    cur.execute("""DELETE FROM ChatHistorial WHERE Id NOT IN (
        SELECT Id FROM ChatHistorial ORDER BY Fecha DESC LIMIT 500
    )""")
    
    conn.commit()
    conn.close()
    return filename


# ── CONTABILIDAD ──────────────────────────────────────

def registrar_gasto(descripcion, monto, categoria="general"):
    from datetime import datetime
    now = datetime.now()
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""INSERT INTO Gasto (Descripcion, Monto, Categoria, Mes, Trimestre, Anio)
        VALUES (?,?,?,?,?,?)""",
        (descripcion, monto, categoria, now.month, (now.month-1)//3+1, now.year))
    conn.commit()
    conn.close()

def get_gastos(mes=None, anio=None):
    from datetime import datetime
    if not anio: anio = datetime.now().year
    if not mes: mes = datetime.now().month
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Gasto WHERE Mes=? AND Anio=? ORDER BY Fecha DESC", (mes, anio))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def get_balance_mes(mes=None, anio=None):
    from datetime import datetime
    if not anio: anio = datetime.now().year
    if not mes: mes = datetime.now().month
    
    conn_nimbo = nimbo_connect()
    cur = conn_nimbo.cursor()
    
    # Ingresos (ventas)
    cur.execute("SELECT IFNULL(SUM(Total),0) as total FROM Venta WHERE Mes=? AND Anio=?", (mes, anio))
    ingresos = float(cur.fetchone()["total"])
    
    # Gastos registrados
    cur.execute("SELECT IFNULL(SUM(Monto),0) as total FROM Gasto WHERE Mes=? AND Anio=?", (mes, anio))
    gastos = float(cur.fetchone()["total"])
    
    conn_nimbo.close()
    
    # Costos de productos vendidos desde Aronium
    conn_aronium = connect()
    cur2 = conn_aronium.cursor()
    cur2.execute("""SELECT di.Quantity, p.Cost FROM DocumentItem di
        JOIN Product p ON di.ProductId=p.Id
        JOIN Document d ON di.DocumentId=d.Id
        WHERE strftime('%m', d.Date)=? AND strftime('%Y', d.Date)=?""",
        (str(mes).zfill(2), str(anio)))
    costos_aronium = sum(float(r[0]) * float(r[1]) for r in cur2.fetchall())
    conn_aronium.close()
    
    comision_pos = ingresos * 0.06
    iva = ingresos * 0.12
    isr_estimado = max(0, (ingresos - gastos - costos_aronium) * 0.05)
    utilidad_bruta = ingresos - costos_aronium - gastos
    utilidad_neta = utilidad_bruta - comision_pos
    
    return {
        "mes": mes,
        "anio": anio,
        "ingresos": round(ingresos, 2),
        "costos_productos": round(costos_aronium, 2),
        "gastos_operativos": round(gastos, 2),
        "comision_pos": round(comision_pos, 2),
        "iva_estimado": round(iva, 2),
        "isr_estimado": round(isr_estimado, 2),
        "utilidad_bruta": round(utilidad_bruta, 2),
        "utilidad_neta": round(utilidad_neta, 2)
    }

TASA_IVA_GUATEMALA = 0.12


def get_declaracion_iva(mes=None, anio=None):
    """Calculo de referencia para la declaracion mensual de IVA ante la SAT
    (formulario SAT-2046, declaraguate.com).

    Si no se especifica mes/anio, se usa el mes recien cerrado (mes actual - 1),
    no el mes en curso todavia incompleto - es el periodo que efectivamente
    toca declarar dentro de los primeros 10 dias habiles del mes actual.

    Debito fiscal (IVA cobrado): se asume que los precios de venta ya incluyen
    IVA (practica estandar en Guatemala para ventas a consumidor final), por lo
    que se calcula ventas x 12/112 para extraer el IVA ya incluido en el precio.

    Credito fiscal (IVA pagado a proveedores): 12% sobre el total de las
    OrdenCompra del periodo con Total > 0. Las ordenes creadas hoy por "genera
    orden para X" (tools/proveedor_tool.py) siempre quedan en Q0 porque ese
    flujo no captura precio de compra (ver Pendiente #9 en CLAUDE.md) - por eso
    se filtra Total > 0 y se avisa en la respuesta cuando el credito fiscal
    calculado es Q0, para que no se confunda con "no compraste nada"."""
    from datetime import datetime
    import calendar

    if not mes and not anio:
        now = datetime.now()
        mes = now.month - 1
        anio = now.year
        if mes == 0:
            mes = 12
            anio -= 1
    else:
        if not anio: anio = datetime.now().year
        if not mes: mes = datetime.now().month

    conn = nimbo_connect()
    cur = conn.cursor()

    cur.execute("SELECT IFNULL(SUM(Total),0) as total, COUNT(*) as cnt FROM Venta WHERE Mes=? AND Anio=?", (mes, anio))
    row = cur.fetchone()
    total_ventas = float(row["total"])
    cantidad_ventas = row["cnt"]

    cur.execute("""SELECT IFNULL(SUM(Total),0) as total, COUNT(*) as cnt FROM OrdenCompra
        WHERE strftime('%m', Fecha)=? AND strftime('%Y', Fecha)=? AND Total > 0""",
        (str(mes).zfill(2), str(anio)))
    row2 = cur.fetchone()
    total_compras = float(row2["total"])
    cantidad_ordenes = row2["cnt"]

    conn.close()

    debito_fiscal = round(total_ventas * TASA_IVA_GUATEMALA / (1 + TASA_IVA_GUATEMALA), 2)
    credito_fiscal = round(total_compras * TASA_IVA_GUATEMALA, 2)
    iva_a_pagar = round(debito_fiscal - credito_fiscal, 2)

    mes_siguiente = mes + 1 if mes < 12 else 1
    anio_siguiente = anio if mes < 12 else anio + 1

    return {
        "mes": mes,
        "anio": anio,
        "periodo": f"{calendar.month_abbr[mes]} {anio}",
        "total_ventas": round(total_ventas, 2),
        "cantidad_ventas": cantidad_ventas,
        "debito_fiscal": debito_fiscal,
        "total_compras": round(total_compras, 2),
        "cantidad_ordenes_compra": cantidad_ordenes,
        "credito_fiscal": credito_fiscal,
        "iva_a_pagar": iva_a_pagar,
        "a_favor": iva_a_pagar < 0,
        "plazo": (f"Declarar (formulario SAT-2046, declaraguate.com) dentro de los primeros "
                  f"10 dias habiles de {calendar.month_abbr[mes_siguiente]} {anio_siguiente}")
    }


def get_valor_inventario():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""SELECT p.Name, p.Cost, IFNULL(SUM(s.Quantity),0) as Stock,
        p.Cost * IFNULL(SUM(s.Quantity),0) as ValorTotal
        FROM Product p LEFT JOIN Stock s ON p.Id=s.ProductId
        WHERE p.IsEnabled=1
        GROUP BY p.Id HAVING Stock > 0
        ORDER BY ValorTotal DESC""")
    rows = [dict(r) for r in cur.fetchall()]
    total = sum(float(r["ValorTotal"]) for r in rows)
    conn.close()
    return {"productos": rows, "total_inventario": round(total, 2)}

def get_margen_productos():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""SELECT Name, Price, Cost, 
        CASE WHEN Cost > 0 THEN ROUND((Price-Cost)/Cost*100, 1) ELSE 0 END as Margen
        FROM Product WHERE IsEnabled=1 AND Price > 0
        ORDER BY Margen DESC""")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_datos_completos_empresa():
    from datetime import datetime
    now = datetime.now()
    mes = now.month
    anio = now.year
    trimestre = (mes - 1) // 3 + 1
    
    # Ventas del mes
    reporte_mes = get_reporte_periodo(mes=mes, anio=anio)
    
    # Balance
    balance = get_balance_mes(mes=mes, anio=anio)
    
    # Inventario
    valor_inv = get_valor_inventario()
    
    # Margen productos
    margenes = get_margen_productos()
    
    # Clientes
    analisis_cli = get_analisis_clientes()
    
    # Stock bajo
    alertas = get_alertas_stock()
    
    # Kardex reciente
    kardex = get_kardex(limit=10)
    
    return {
        "fecha": now.strftime("%d/%m/%Y"),
        "mes": mes,
        "anio": anio,
        "trimestre": trimestre,
        "ventas": {
            "total_mes": reporte_mes["total_vendido"],
            "transacciones": reporte_mes["total_ventas"],
            "comision_pos": reporte_mes["comision_pos"],
            "ganancia_estimada": reporte_mes["ganancia_estimada"]
        },
        "balance": balance,
        "inventario": {
            "valor_total": valor_inv["total_inventario"],
            "productos": len(valor_inv["productos"])
        },
        "margenes": margenes[:5],
        "clientes": {
            "total": analisis_cli["total_clientes"],
            "mejores": analisis_cli["mejores"][:3],
            "inactivos": len(analisis_cli["inactivos"])
        },
        "alertas_stock": len(alertas),
        "movimientos_recientes": len(kardex)
    }


def get_comparacion_meses(meses=6):
    from datetime import datetime
    now = datetime.now()
    conn = nimbo_connect()
    cur = conn.cursor()
    resultados = []
    
    for i in range(meses-1, -1, -1):
        mes_target = now.month - i
        anio_target = now.year
        while mes_target <= 0:
            mes_target += 12
            anio_target -= 1
        
        cur.execute("""SELECT COUNT(*) as ventas, IFNULL(SUM(Total),0) as total
            FROM Venta WHERE Mes=? AND Anio=?""", (mes_target, anio_target))
        row = dict(cur.fetchone())
        
        cur.execute("""SELECT IFNULL(SUM(Monto),0) as gastos
            FROM Gasto WHERE Mes=? AND Anio=?""", (mes_target, anio_target))
        gastos = float(cur.fetchone()["gastos"])
        
        total = float(row["total"])
        comision = total * 0.06
        utilidad = total - gastos - comision
        
        import calendar
        nombre_mes = calendar.month_abbr[mes_target]
        
        resultados.append({
            "mes": mes_target,
            "anio": anio_target,
            "nombre": f"{nombre_mes} {anio_target}",
            "ventas": row["ventas"],
            "total": round(total, 2),
            "gastos": round(gastos, 2),
            "utilidad": round(utilidad, 2)
        })

    conn.close()
    return resultados


def get_flujo_caja_proyectado():
    """Proyecta ingresos, egresos y flujo neto del proximo mes calendario.

    "vencen el proximo mes" para cuentas por cobrar/pagar se aproxima como
    "vencen en los proximos 30 dias" (mismo criterio de DIAS_VENCIMIENTO_CUENTA_DEFAULT/
    DIAS_VENCIMIENTO_PAGAR_DEFAULT que ya usa el resto del sistema), en vez de acotar
    por el mes calendario exacto."""
    import calendar
    now = datetime.now()
    mes_prox = now.month + 1
    anio_prox = now.year
    if mes_prox > 12:
        mes_prox = 1
        anio_prox += 1
    nombre_mes_prox = f"{calendar.month_abbr[mes_prox]} {anio_prox}"

    # ── Ingresos proyectados ──
    # Ultimos 3 meses ya cerrados (se excluye el mes actual, todavia incompleto).
    historico = get_comparacion_meses(meses=4)
    meses_completos = historico[:-1]
    ventas_meses = [m["total"] for m in meses_completos]
    promedio_ventas = sum(ventas_meses) / len(ventas_meses)

    # Tendencia: variacion promedio mes a mes en esos 3 meses, proyectada un paso
    # mas hacia adelante sobre el promedio (positiva si las ventas suben, negativa
    # si bajan).
    variaciones = []
    for i in range(1, len(ventas_meses)):
        anterior = ventas_meses[i - 1]
        if anterior > 0:
            variaciones.append((ventas_meses[i] - anterior) / anterior)
    tendencia_pct = sum(variaciones) / len(variaciones) if variaciones else 0
    ajuste_tendencia = round(promedio_ventas * tendencia_pct, 2)
    ventas_proyectadas = round(promedio_ventas + ajuste_tendencia, 2)

    cuentas_cobrar_prox = get_cuentas_por_vencer(dias=30)
    total_cobrar_prox = round(sum(c["MontoPendiente"] for c in cuentas_cobrar_prox), 2)

    ingresos_total = round(ventas_proyectadas + total_cobrar_prox, 2)

    # ── Egresos proyectados ──
    pagos_fijos = get_pagos_fijos()
    total_pagos_fijos = round(sum(float(p["Monto"] or 0) for p in pagos_fijos), 2)
    pagos_fijos_sin_monto = sum(1 for p in pagos_fijos if not p["Monto"])

    cuentas_pagar_prox = get_pagos_por_vencer(dias=30)
    total_pagar_prox = round(sum(c["MontoPendiente"] for c in cuentas_pagar_prox), 2)

    pedidos_sugeridos = get_pedidos_sugeridos()
    total_compras_estimadas = round(sum(p["costo_total"] for p in pedidos_sugeridos), 2)

    egresos_total = round(total_pagos_fijos + total_pagar_prox + total_compras_estimadas, 2)

    flujo_neto = round(ingresos_total - egresos_total, 2)

    return {
        "mes_proyectado": nombre_mes_prox,
        "ingresos": {
            "promedio_ventas_3_meses": round(promedio_ventas, 2),
            "tendencia_pct": round(tendencia_pct * 100, 1),
            "ajuste_tendencia": ajuste_tendencia,
            "ventas_proyectadas": ventas_proyectadas,
            "cuentas_por_cobrar": total_cobrar_prox,
            "cantidad_cuentas_cobrar": len(cuentas_cobrar_prox),
            "total": ingresos_total
        },
        "egresos": {
            "pagos_fijos": total_pagos_fijos,
            "cantidad_pagos_fijos": len(pagos_fijos),
            "pagos_fijos_sin_monto": pagos_fijos_sin_monto,
            "cuentas_por_pagar": total_pagar_prox,
            "cantidad_cuentas_pagar": len(cuentas_pagar_prox),
            "compras_estimadas": total_compras_estimadas,
            "cantidad_productos_reabastecer": len(pedidos_sugeridos),
            "total": egresos_total
        },
        "flujo_neto": flujo_neto,
        "positivo": flujo_neto >= 0
    }


def hacer_backup():
    import shutil
    from datetime import datetime
    import os
    
    backup_dir = "/home/ictor_axtor/micocina-dashboard/backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    fecha = datetime.now().strftime("%Y%m%d_%H%M")
    
    # Backup nimbo.db
    shutil.copy2(
        "/home/ictor_axtor/micocina-dashboard/nimbo.db",
        f"{backup_dir}/nimbo_{fecha}.db"
    )
    
    # Backup Aronium
    try:
        shutil.copy2(
            "/mnt/c/Users/Victor Paxtor/AppData/Local/Aronium/Data/pos.db",
            f"{backup_dir}/aronium_{fecha}.db"
        )
    except: pass
    
    # Mantener solo los ultimos 7 backups
    backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("nimbo_")])
    while len(backups) > 7:
        os.remove(f"{backup_dir}/{backups.pop(0)}")

    return fecha


# ── CODIGOS DE BARRAS ─────────────────────────────────

# Rango 200-299: GS1 lo reserva para "restricted circulation numbers" de uso interno
# (tiendas/almacenes), no requiere registro ante GS1 ni riesgo de chocar con un
# codigo de fabricante real.
PREFIJO_EAN_INTERNO = "20"


def init_codigos_barras():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS CodigoBarrasGenerado (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            ProductoId INTEGER,
            ProductoNombre TEXT,
            CodigoEAN TEXT,
            FechaGenerado DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def _digito_verificador_ean13(doce_digitos):
    """Algoritmo estandar EAN-13: posiciones impares (1a, 3a, ...) x1, pares x3."""
    total = sum(int(d) if i % 2 == 0 else int(d) * 3 for i, d in enumerate(doce_digitos))
    return (10 - (total % 10)) % 10


def _codigo_ean_existe(codigo):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM Product WHERE Code=? LIMIT 1", (codigo,))
    existe_aronium = cur.fetchone() is not None
    conn.close()
    if existe_aronium:
        return True

    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM CodigoBarrasGenerado WHERE CodigoEAN=? LIMIT 1", (codigo,))
    existe_nimbo = cur.fetchone() is not None
    conn.close()
    return existe_nimbo


def generar_ean13():
    """Genera un codigo EAN-13 unico (no choca con ningun Product.Code existente en
    Aronium ni con uno ya generado antes en CodigoBarrasGenerado)."""
    import random
    while True:
        cuerpo = PREFIJO_EAN_INTERNO + "".join(str(random.randint(0, 9)) for _ in range(10))
        codigo = cuerpo + str(_digito_verificador_ean13(cuerpo))
        if not _codigo_ean_existe(codigo):
            return codigo


def get_productos_sin_codigo(limit=500):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.Id, p.Name, p.Code, p.Price, p.Cost,
               IFNULL(SUM(s.Quantity),0) AS Stock
        FROM Product p
        LEFT JOIN Stock s ON p.Id = s.ProductId
        WHERE p.IsEnabled=1 AND (p.Code IS NULL OR TRIM(p.Code)='')
        GROUP BY p.Id ORDER BY p.Name LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def asignar_codigo_barras(producto_id, producto_nombre):
    """Genera un EAN-13 nuevo y lo asigna como Code del producto en Aronium; registra
    el evento en CodigoBarrasGenerado (nimbo.db) porque Aronium no guarda quien/cuando
    se genero el codigo. No revisa si el producto ya tenia un Code - eso lo decide
    quien llama (ver codigobarras.generar en tools/codigo_barras_tool.py)."""
    codigo = generar_ean13()

    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE Product SET Code=? WHERE Id=?", (codigo, producto_id))
    conn.commit()
    conn.close()

    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO CodigoBarrasGenerado (ProductoId, ProductoNombre, CodigoEAN) VALUES (?,?,?)",
        (producto_id, producto_nombre, codigo))
    conn.commit()
    conn.close()
    return codigo


# ── CUENTAS POR COBRAR ────────────────────────────────

DIAS_VENCIMIENTO_CUENTA_DEFAULT = 30  # no especificado en el pedido original; mismo
# criterio que DIAS_GARANTIA_PROPIA_DEFAULT/COTIZACION (15 dias) - un plazo razonable
# por defecto que el admin puede ajustar dando una fecha explicita al vender a credito.

ESTADOS_CUENTA_COBRAR = ("PENDIENTE", "PAGADO_PARCIAL", "PAGADO", "VENCIDO")


def init_cuentas_cobrar():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS CuentaCobrar (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            ClienteId INTEGER,
            ClienteNombre TEXT,
            ClienteTelefono TEXT,
            Descripcion TEXT,
            MontoTotal NUMERIC,
            MontoPagado NUMERIC DEFAULT 0,
            MontoPendiente NUMERIC,
            FechaCreada DATETIME DEFAULT CURRENT_TIMESTAMP,
            FechaVencimiento TEXT,
            Estado TEXT DEFAULT 'PENDIENTE',
            Notas TEXT,
            VentaId INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS PagoCuenta (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            CuentaId INTEGER,
            Monto NUMERIC,
            MetodoPago TEXT,
            Fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            Notas TEXT,
            FOREIGN KEY (CuentaId) REFERENCES CuentaCobrar(Id)
        )
    """)
    conn.commit()
    conn.close()


def crear_cuenta_cobrar(cliente_id, cliente_nombre, cliente_telefono, descripcion, monto_total,
                         monto_pagado=0, fecha_vencimiento=None, notas="", venta_id=None):
    """monto_pagado > 0 se usa para el enganche de una venta a credito (ver
    core/nimbo.py venta_waiting_credito_fecha) - se registra tambien como el primer
    PagoCuenta para que quede en el detalle de abonos."""
    from datetime import timedelta
    conn = nimbo_connect()
    cur = conn.cursor()
    monto_total = round(float(monto_total), 2)
    monto_pagado = round(float(monto_pagado or 0), 2)
    monto_pendiente = round(monto_total - monto_pagado, 2)
    if not fecha_vencimiento:
        fecha_vencimiento = (datetime.now() + timedelta(days=DIAS_VENCIMIENTO_CUENTA_DEFAULT)).strftime("%Y-%m-%d")
    estado = "PAGADO" if monto_pendiente <= 0 else ("PAGADO_PARCIAL" if monto_pagado > 0 else "PENDIENTE")
    cur.execute("""INSERT INTO CuentaCobrar
        (ClienteId, ClienteNombre, ClienteTelefono, Descripcion, MontoTotal, MontoPagado, MontoPendiente,
         FechaVencimiento, Estado, Notas, VentaId)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (cliente_id, cliente_nombre, cliente_telefono, descripcion, monto_total, monto_pagado,
         max(monto_pendiente, 0), fecha_vencimiento, estado, notas, venta_id))
    cuenta_id = cur.lastrowid
    if monto_pagado > 0:
        cur.execute("INSERT INTO PagoCuenta (CuentaId, Monto, MetodoPago, Notas) VALUES (?,?,?,?)",
            (cuenta_id, monto_pagado, "enganche", "Enganche inicial"))
    conn.commit()
    conn.close()
    return cuenta_id


def get_cuenta_por_id(cuenta_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM CuentaCobrar WHERE Id=?", (cuenta_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def marcar_cuentas_vencidas():
    """Lazy, igual que marcar_cotizaciones_vencidas()/marcar_garantias_vencidas():
    se corre cada vez que se consultan cuentas. Una cuenta VENCIDO que recibe un abono
    y queda saldada pasa a PAGADO (ver registrar_pago_cuenta); si queda con saldo y la
    fecha ya paso, esta funcion la vuelve a marcar VENCIDO en la siguiente consulta."""
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""UPDATE CuentaCobrar SET Estado='VENCIDO'
        WHERE Estado IN ('PENDIENTE','PAGADO_PARCIAL') AND MontoPendiente > 0
        AND date(FechaVencimiento) < date('now')""")
    conn.commit()
    conn.close()


def registrar_pago_cuenta(cuenta_id, monto, metodo_pago="efectivo", notas=""):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM CuentaCobrar WHERE Id=?", (cuenta_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    cuenta = dict(row)
    monto = round(float(monto), 2)
    nuevo_pagado = round(cuenta["MontoPagado"] + monto, 2)
    nuevo_pendiente = round(cuenta["MontoTotal"] - nuevo_pagado, 2)
    estado = "PAGADO" if nuevo_pendiente <= 0 else "PAGADO_PARCIAL"
    cur.execute("UPDATE CuentaCobrar SET MontoPagado=?, MontoPendiente=?, Estado=? WHERE Id=?",
        (nuevo_pagado, max(nuevo_pendiente, 0), estado, cuenta_id))
    cur.execute("INSERT INTO PagoCuenta (CuentaId, Monto, MetodoPago, Notas) VALUES (?,?,?,?)",
        (cuenta_id, monto, metodo_pago, notas))
    conn.commit()
    conn.close()
    return {"cuenta_id": cuenta_id, "monto_pagado": nuevo_pagado, "monto_pendiente": max(nuevo_pendiente, 0), "estado": estado}


def registrar_pago_cliente(cliente_id, monto, metodo_pago="efectivo"):
    """'Juan Perez pago Q100' (tools/cuenta_cobrar_tool.py) no dice a que cuenta
    especifica aplica el abono, asi que se reparte FIFO: primero a la cuenta pendiente
    mas antigua, y lo que sobre a la siguiente, hasta agotar el monto o las cuentas.
    Retorna None si el cliente no tiene ninguna cuenta pendiente."""
    marcar_cuentas_vencidas()
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT * FROM CuentaCobrar
        WHERE ClienteId=? AND Estado IN ('PENDIENTE','PAGADO_PARCIAL','VENCIDO') AND MontoPendiente > 0
        ORDER BY FechaCreada ASC""", (cliente_id,))
    cuentas = [dict(r) for r in cur.fetchall()]
    conn.close()
    if not cuentas:
        return None

    restante = round(float(monto), 2)
    aplicados = []
    for c in cuentas:
        if restante <= 0:
            break
        a_aplicar = round(min(restante, c["MontoPendiente"]), 2)
        if a_aplicar <= 0:
            continue
        resultado = registrar_pago_cuenta(c["Id"], a_aplicar, metodo_pago=metodo_pago)
        aplicados.append({
            "cuenta_id": c["Id"], "descripcion": c["Descripcion"],
            "monto": a_aplicar, "estado": resultado["estado"]
        })
        restante = round(restante - a_aplicar, 2)
    return {"aplicados": aplicados, "sobrante": restante}


def get_cuentas_cobrar(estado=None, limit=100):
    marcar_cuentas_vencidas()
    conn = nimbo_connect()
    cur = conn.cursor()
    query = "SELECT * FROM CuentaCobrar WHERE MontoPendiente > 0"
    params = []
    if estado:
        query += " AND Estado=?"
        params.append(estado)
    query += " ORDER BY FechaVencimiento ASC LIMIT ?"
    params.append(limit)
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_cuentas_cliente(query, solo_pendientes=True):
    marcar_cuentas_vencidas()
    conn = nimbo_connect()
    cur = conn.cursor()
    sql = "SELECT * FROM CuentaCobrar WHERE (ClienteNombre LIKE ? OR ClienteTelefono LIKE ?)"
    params = [f"%{query}%", f"%{query}%"]
    if solo_pendientes:
        sql += " AND MontoPendiente > 0"
    sql += " ORDER BY FechaCreada DESC"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_cuentas_por_vencer(dias=3):
    marcar_cuentas_vencidas()
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT * FROM CuentaCobrar
        WHERE Estado IN ('PENDIENTE','PAGADO_PARCIAL') AND MontoPendiente > 0
        AND date(FechaVencimiento) BETWEEN date('now') AND date('now', '+' || ? || ' days')
        ORDER BY FechaVencimiento ASC""", (dias,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_resumen_cuentas_cobrar():
    """Alimenta el widget de Dashboard: total por cobrar, cuentas vencidas (rojo) y
    proximas a vencer en 3 dias (naranja) - ver /api/cuentascobrar/resumen."""
    marcar_cuentas_vencidas()
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(MontoPendiente),0) as total, COUNT(*) as cnt FROM CuentaCobrar WHERE MontoPendiente > 0")
    r = cur.fetchone()
    total_por_cobrar, cantidad_total = r["total"], r["cnt"]
    cur.execute("SELECT COALESCE(SUM(MontoPendiente),0) as total, COUNT(*) as cnt FROM CuentaCobrar WHERE Estado='VENCIDO'")
    r = cur.fetchone()
    vencidas_total, vencidas_cantidad = r["total"], r["cnt"]
    conn.close()

    proximas = get_cuentas_por_vencer(dias=3)
    proximas_total = round(sum(c["MontoPendiente"] for c in proximas), 2)

    return {
        "total_por_cobrar": round(total_por_cobrar, 2),
        "cantidad_total": cantidad_total,
        "vencidas_total": round(vencidas_total, 2),
        "vencidas_cantidad": vencidas_cantidad,
        "proximas_total": proximas_total,
        "proximas_cantidad": len(proximas)
    }


# ── CUENTAS POR PAGAR ──────────────────────────────────

DIAS_VENCIMIENTO_PAGAR_DEFAULT = 30  # mismo criterio que DIAS_VENCIMIENTO_CUENTA_DEFAULT
# (cuentas por cobrar) - no especificado en el pedido, plazo razonable por defecto.


def init_cuentas_pagar():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS CuentaPagar (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            ProveedorId INTEGER,
            ProveedorNombre TEXT,
            ProveedorTelefono TEXT,
            Descripcion TEXT,
            MontoTotal NUMERIC,
            MontoPagado NUMERIC DEFAULT 0,
            MontoPendiente NUMERIC,
            FechaCreada DATETIME DEFAULT CURRENT_TIMESTAMP,
            FechaVencimiento TEXT,
            Estado TEXT DEFAULT 'PENDIENTE',
            OrdenCompraId INTEGER,
            Notas TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS PagoPagar (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            CuentaId INTEGER,
            Monto NUMERIC,
            MetodoPago TEXT,
            Fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            Notas TEXT,
            FOREIGN KEY (CuentaId) REFERENCES CuentaPagar(Id)
        )
    """)
    conn.commit()
    conn.close()


def crear_cuenta_pagar(proveedor_id, proveedor_nombre, proveedor_telefono, descripcion, monto_total,
                        monto_pagado=0, fecha_vencimiento=None, notas="", orden_compra_id=None):
    from datetime import timedelta
    conn = nimbo_connect()
    cur = conn.cursor()
    monto_total = round(float(monto_total), 2)
    monto_pagado = round(float(monto_pagado or 0), 2)
    monto_pendiente = round(monto_total - monto_pagado, 2)
    if not fecha_vencimiento:
        fecha_vencimiento = (datetime.now() + timedelta(days=DIAS_VENCIMIENTO_PAGAR_DEFAULT)).strftime("%Y-%m-%d")
    estado = "PAGADO" if monto_pendiente <= 0 else ("PAGADO_PARCIAL" if monto_pagado > 0 else "PENDIENTE")
    cur.execute("""INSERT INTO CuentaPagar
        (ProveedorId, ProveedorNombre, ProveedorTelefono, Descripcion, MontoTotal, MontoPagado, MontoPendiente,
         FechaVencimiento, Estado, OrdenCompraId, Notas)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (proveedor_id, proveedor_nombre, proveedor_telefono, descripcion, monto_total, monto_pagado,
         max(monto_pendiente, 0), fecha_vencimiento, estado, orden_compra_id, notas))
    cuenta_id = cur.lastrowid
    if monto_pagado > 0:
        cur.execute("INSERT INTO PagoPagar (CuentaId, Monto, MetodoPago, Notas) VALUES (?,?,?,?)",
            (cuenta_id, monto_pagado, "enganche", "Enganche inicial"))
    conn.commit()
    conn.close()
    return cuenta_id


def get_cuenta_pagar_por_id(cuenta_id):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM CuentaPagar WHERE Id=?", (cuenta_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def marcar_pagos_vencidos():
    """Lazy, igual que marcar_cuentas_vencidas() (cuentas por cobrar)."""
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""UPDATE CuentaPagar SET Estado='VENCIDO'
        WHERE Estado IN ('PENDIENTE','PAGADO_PARCIAL') AND MontoPendiente > 0
        AND date(FechaVencimiento) < date('now')""")
    conn.commit()
    conn.close()


def registrar_pago_cuenta_pagar(cuenta_id, monto, metodo_pago="efectivo", notas=""):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM CuentaPagar WHERE Id=?", (cuenta_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    cuenta = dict(row)
    monto = round(float(monto), 2)
    nuevo_pagado = round(cuenta["MontoPagado"] + monto, 2)
    nuevo_pendiente = round(cuenta["MontoTotal"] - nuevo_pagado, 2)
    estado = "PAGADO" if nuevo_pendiente <= 0 else "PAGADO_PARCIAL"
    cur.execute("UPDATE CuentaPagar SET MontoPagado=?, MontoPendiente=?, Estado=? WHERE Id=?",
        (nuevo_pagado, max(nuevo_pendiente, 0), estado, cuenta_id))
    cur.execute("INSERT INTO PagoPagar (CuentaId, Monto, MetodoPago, Notas) VALUES (?,?,?,?)",
        (cuenta_id, monto, metodo_pago, notas))
    conn.commit()
    conn.close()
    return {"cuenta_id": cuenta_id, "monto_pagado": nuevo_pagado, "monto_pendiente": max(nuevo_pendiente, 0), "estado": estado}


def registrar_pago_proveedor(proveedor_id, monto, metodo_pago="efectivo"):
    """'pague Q200 a Distribuidora Oster' (tools/cuenta_pagar_tool.py) no dice a que
    cuenta especifica aplica el pago, asi que se reparte FIFO igual que
    registrar_pago_cliente() (cuentas por cobrar): la cuenta pendiente mas antigua
    primero. Retorna None si el proveedor no tiene ninguna cuenta pendiente."""
    marcar_pagos_vencidos()
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT * FROM CuentaPagar
        WHERE ProveedorId=? AND Estado IN ('PENDIENTE','PAGADO_PARCIAL','VENCIDO') AND MontoPendiente > 0
        ORDER BY FechaCreada ASC""", (proveedor_id,))
    cuentas = [dict(r) for r in cur.fetchall()]
    conn.close()
    if not cuentas:
        return None

    restante = round(float(monto), 2)
    aplicados = []
    for c in cuentas:
        if restante <= 0:
            break
        a_aplicar = round(min(restante, c["MontoPendiente"]), 2)
        if a_aplicar <= 0:
            continue
        resultado = registrar_pago_cuenta_pagar(c["Id"], a_aplicar, metodo_pago=metodo_pago)
        aplicados.append({
            "cuenta_id": c["Id"], "descripcion": c["Descripcion"],
            "monto": a_aplicar, "estado": resultado["estado"]
        })
        restante = round(restante - a_aplicar, 2)
    return {"aplicados": aplicados, "sobrante": restante}


def get_cuentas_pagar(estado=None, limit=100):
    marcar_pagos_vencidos()
    conn = nimbo_connect()
    cur = conn.cursor()
    query = "SELECT * FROM CuentaPagar WHERE MontoPendiente > 0"
    params = []
    if estado:
        query += " AND Estado=?"
        params.append(estado)
    query += " ORDER BY FechaVencimiento ASC LIMIT ?"
    params.append(limit)
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_cuentas_proveedor(query, solo_pendientes=True):
    marcar_pagos_vencidos()
    conn = nimbo_connect()
    cur = conn.cursor()
    sql = "SELECT * FROM CuentaPagar WHERE (ProveedorNombre LIKE ? OR ProveedorTelefono LIKE ?)"
    params = [f"%{query}%", f"%{query}%"]
    if solo_pendientes:
        sql += " AND MontoPendiente > 0"
    sql += " ORDER BY FechaCreada DESC"
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_pagos_por_vencer(dias=3):
    marcar_pagos_vencidos()
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT * FROM CuentaPagar
        WHERE Estado IN ('PENDIENTE','PAGADO_PARCIAL') AND MontoPendiente > 0
        AND date(FechaVencimiento) BETWEEN date('now') AND date('now', '+' || ? || ' days')
        ORDER BY FechaVencimiento ASC""", (dias,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_resumen_cuentas_pagar():
    """Alimenta el widget de Dashboard: total por pagar, pagos vencidos (rojo) y
    proximos a vencer en 3 dias (naranja) - ver /api/cuentaspagar/resumen."""
    marcar_pagos_vencidos()
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(MontoPendiente),0) as total, COUNT(*) as cnt FROM CuentaPagar WHERE MontoPendiente > 0")
    r = cur.fetchone()
    total_por_pagar, cantidad_total = r["total"], r["cnt"]
    cur.execute("SELECT COALESCE(SUM(MontoPendiente),0) as total, COUNT(*) as cnt FROM CuentaPagar WHERE Estado='VENCIDO'")
    r = cur.fetchone()
    vencidos_total, vencidos_cantidad = r["total"], r["cnt"]
    conn.close()

    proximos = get_pagos_por_vencer(dias=3)
    proximos_total = round(sum(c["MontoPendiente"] for c in proximos), 2)

    return {
        "total_por_pagar": round(total_por_pagar, 2),
        "cantidad_total": cantidad_total,
        "vencidos_total": round(vencidos_total, 2),
        "vencidos_cantidad": vencidos_cantidad,
        "proximos_total": proximos_total,
        "proximos_cantidad": len(proximos)
    }
