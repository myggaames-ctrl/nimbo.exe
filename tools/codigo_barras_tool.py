"""
Herramienta de Codigos de Barras y Etiquetas
"""
from core.tool_registry import register
from database.aronium import get_products, asignar_codigo_barras, get_productos_sin_codigo
from services.barcode_service import generar_etiqueta_producto_pdf, generar_etiquetas_lote_pdf


def _link_pdf(ruta, texto="Descargar PDF"):
    return f'<a href="/static/{ruta}" target="_blank" style="color:var(--accent)">📄 {texto}</a>'


def generar_codigo_tool(data):
    query = (data.get("query", "") if isinstance(data, dict) else str(data)).strip()
    if not query:
        return "Dime el producto. Ejemplo: generar codigo cuchilla"

    productos = get_products(search=query)
    if not productos:
        return f"No encontre ningun producto que coincida con '{query}'."
    producto = productos[0]
    nombre = producto["Name"].strip()

    if producto.get("Code"):
        return (f"{nombre} ya tiene el codigo {producto['Code']}. "
                f"Escribe 'etiqueta de {nombre}' para generar su etiqueta.")

    codigo = asignar_codigo_barras(producto["Id"], nombre)
    return f"Codigo generado para {nombre}: {codigo}. Escribe 'etiqueta de {nombre}' para generar su etiqueta."

register("codigobarras.generar", generar_codigo_tool)


def _asegurar_codigo(producto):
    """Si el producto no tiene Code, le genera un EAN-13 antes de armar la etiqueta."""
    if producto.get("Code"):
        return producto["Code"]
    return asignar_codigo_barras(producto["Id"], producto["Name"].strip())


def generar_etiqueta_tool(data):
    query = (data.get("query", "") if isinstance(data, dict) else str(data)).strip()
    if not query:
        return "Dime el producto. Ejemplo: etiqueta de cuchilla"

    productos = get_products(search=query)
    if not productos:
        return f"No encontre ningun producto que coincida con '{query}'."
    producto = productos[0]
    nombre = producto["Name"].strip()
    codigo = _asegurar_codigo(producto)

    ruta = generar_etiqueta_producto_pdf(nombre, producto["Price"], codigo)
    return f"Etiqueta de {nombre} ({codigo}) generada.\n{_link_pdf(ruta)}"

register("etiqueta.producto", generar_etiqueta_tool)


def generar_etiquetas_lote_tool(data):
    productos = get_productos_sin_codigo()
    if not productos:
        return "Todos los productos ya tienen codigo de barras asignado."

    items = []
    for p in productos:
        nombre = p["Name"].strip()
        codigo = asignar_codigo_barras(p["Id"], nombre)
        items.append({"nombre": nombre, "precio": p["Price"], "codigo": codigo})

    ruta = generar_etiquetas_lote_pdf(items)
    resp = f"{len(items)} codigo(s) generado(s) y etiquetas listas:\n"
    resp += "\n".join(f"- {i['nombre']}: {i['codigo']}" for i in items)
    resp += f"\n{_link_pdf(ruta, 'Descargar etiquetas')}"
    return resp

register("etiqueta.lote_sin_codigo", generar_etiquetas_lote_tool)
