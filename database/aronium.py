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
        SELECT p.Id, p.Name, p.Code, p.Price, p.Cost,
               IFNULL(SUM(s.Quantity),0) AS Stock
        FROM Product p
        LEFT JOIN Stock s ON p.Id = s.ProductId
        WHERE p.Code = ?
        GROUP BY p.Id LIMIT 1
    """, (code,))
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


# ── SERVICIO TECNICO ──────────────────────────────────

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

def crear_orden(cliente_id, equipo, marca, modelo, problema, serie="", tecnico=""):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM OrdenServicio")
    total = cur.fetchone()["total"] + 1
    numero = f"OS-{total:04d}"
    cur.execute("""INSERT INTO OrdenServicio 
        (NumeroOrden, ClienteId, Equipo, Marca, Modelo, Serie, Problema, Tecnico)
        VALUES (?,?,?,?,?,?,?,?)""",
        (numero, cliente_id, equipo, marca, modelo, serie, problema, tecnico))
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

def get_historial_orden(numero):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT h.* FROM HistorialOrden h
        JOIN OrdenServicio o ON h.OrdenId=o.Id
        WHERE o.NumeroOrden=? ORDER BY h.Fecha ASC""", (numero,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ── CLIENTES NIMBO ────────────────────────────────────

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
    from datetime import datetime
    now = datetime.now()
    mes = now.month
    trimestre = (mes - 1) // 3 + 1
    anio = now.year
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Venta (ClienteId, Descripcion, Total, Mes, Trimestre, Anio) VALUES (?,?,?,?,?,?)",
        (cliente_id, descripcion, total, mes, trimestre, anio)
    )
    cur.execute("UPDATE Cliente SET UltimaCompra=? WHERE Id=?", (now.isoformat(), cliente_id))
    conn.commit()
    conn.close()

def get_historial_cliente(cliente_id, meses=12):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""SELECT v.*, c.Nombre as ClienteNombre FROM Venta v
        JOIN Cliente c ON v.ClienteId=c.Id
        WHERE v.ClienteId=?
        AND v.Fecha >= datetime('now', ? || ' months')
        ORDER BY v.Fecha DESC""",
        (cliente_id, f"-{meses}"))
    ventas = [dict(r) for r in cur.fetchall()]
    cur.execute("""SELECT * FROM OrdenServicio
        WHERE ClienteId=? ORDER BY FechaRecepcion DESC""", (cliente_id,))
    ordenes = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"ventas": ventas, "ordenes": ordenes}

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
    return numero

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
            sugeridos.append({
                "producto": p["Name"].strip(),
                "stock_actual": int(p["Stock"]),
                "minimo": minimo,
                "cantidad_sugerida": cantidad_sugerida,
                "proveedores": proveedores
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

    conn.close()
    return recordatorios


# ── PAGOS FIJOS ───────────────────────────────────────

def agregar_pago_fijo(nombre, frecuencia="mensual", dia_pago=1, dias_antes=2):
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("""INSERT INTO PagoFijo (Nombre, Frecuencia, DiaPago, DiasAntes)
        VALUES (?,?,?,?)""", (nombre, frecuencia, dia_pago, dias_antes))
    conn.commit()
    conn.close()

def get_pagos_fijos():
    conn = nimbo_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM PagoFijo WHERE Activo=1 ORDER BY DiaPago")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

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
