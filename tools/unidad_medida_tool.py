"""
Herramienta de Unidades de Medida (docena, caja, par, paquete, etc.)
"""
from core.tool_registry import register
from database.nimbo_db import (
    get_products, set_unidad_medida, get_unidad_medida,
    get_todas_unidades_medida, remove_stock
)

# Normaliza plural/singular ("docenas"->"docena", "cajas"->"caja") para que
# configurar con "por docena" y vender con "2 docenas" resuelvan a la misma
# UnidadBase guardada. No se puede confiar en el CommandNormalizer para esto:
# corrige typos por similitud, no gramatica, y de hecho preserva sin tocar
# cualquier palabra que ya este en su VOCABULARIO (incluidos los plurales).
UNIDAD_SINGULAR = {
    "docena": "docena", "docenas": "docena",
    "caja": "caja", "cajas": "caja",
    "par": "par", "pares": "par",
    "paquete": "paquete", "paquetes": "paquete",
    "trio": "trio", "trios": "trio",
    "cuarteto": "cuarteto", "cuartetos": "cuarteto",
}


def _singularizar(unidad):
    return UNIDAD_SINGULAR.get(unidad, unidad)


# Cantidad por defecto cuando el admin no la especifica al configurar (ej.
# "reguladores se venden por par" sin decir "de 2"). Si la unidad no esta aqui,
# hay que pedirle la cantidad explicitamente. Claves ya singulares porque se
# consulta despues de pasar por _singularizar().
UNIDADES_CANTIDAD_DEFAULT = {
    "par": 2,
    "docena": 12,
    "trio": 3,
    "cuarteto": 4,
}


def configurar_unidad_tool(data):
    query = data.get("producto_query", "").strip()
    unidad = _singularizar(data.get("unidad", "").strip().lower())
    cantidad = data.get("cantidad_por_unidad")
    precio_por_unidad = data.get("precio_por_unidad")

    productos = get_products(search=query)
    if not productos:
        return f"No encontre ningun producto que coincida con '{query}'."
    producto = productos[0]
    nombre = producto["Name"].strip()

    if cantidad is None:
        cantidad = UNIDADES_CANTIDAD_DEFAULT.get(unidad)
        if cantidad is None:
            return (f"No se cuantas unidades tiene un(a) '{unidad}'. Especifica la cantidad, "
                    f"ej: '{nombre} se vende por {unidad} de 12'.")

    precio_final = set_unidad_medida(
        producto["Id"], nombre, unidad, cantidad,
        precio_unitario=producto["Price"], precio_por_unidad=precio_por_unidad
    )

    resp = f"{nombre} configurado para venderse por {unidad} ({int(cantidad)} unidades) a Q{precio_final}."
    ahorro = round(producto["Price"] * cantidad - precio_final, 2)
    if ahorro > 0:
        resp += f" Ahorro de Q{ahorro} vs comprar {int(cantidad)} unidades por separado (Q{producto['Price']} c/u)."
    return resp

register("unidadmedida.configurar", configurar_unidad_tool)


def listar_unidades_tool(data):
    unidades = get_todas_unidades_medida()
    if not unidades:
        return "No hay unidades de medida configuradas."
    resp = f"{len(unidades)} unidad(es) de medida configurada(s):\n"
    for u in unidades:
        resp += (f"- {u['ProductoNombre']}: {u['UnidadBase']} = {int(u['CantidadPorUnidad'])} unidades "
                 f"a Q{u['PrecioPorUnidad']}\n")
    return resp

register("unidadmedida.listar", listar_unidades_tool)


def vender_por_unidad_tool(data):
    query = data.get("producto_query", "").strip()
    unidad = _singularizar(data.get("unidad", "").strip().lower())
    cantidad_medida = data.get("cantidad_medida", 1)

    productos = get_products(search=query)
    if not productos:
        return f"No encontre ningun producto que coincida con '{query}'."

    candidatos = []
    for p in productos:
        config = get_unidad_medida(p["Id"], unidad)
        if config:
            candidatos.append((p, config))

    if not candidatos:
        nombre_ref = productos[0]["Name"].strip()
        return (f"'{nombre_ref}' no tiene configurada la unidad '{unidad}'. Configurala con: "
                f"'{nombre_ref} se vende por {unidad} de N'")

    if len(candidatos) > 1:
        opciones = ";".join(
            f"{p['Name'].strip()} ({unidad}):{c['PrecioPorUnidad']}:{p['Id']}:{c['CantidadPorUnidad']}"
            for p, c in candidatos[:5]
        )
        return f"VENTA_INICIO:{opciones}|{cantidad_medida}"

    p, config = candidatos[0]
    cantidad_base = cantidad_medida * config["CantidadPorUnidad"]
    if p["Stock"] < cantidad_base:
        equivalente = round(p["Stock"] / config["CantidadPorUnidad"], 2) if config["CantidadPorUnidad"] else 0
        return (f"Stock insuficiente. {p['Name'].strip()} solo tiene {int(p['Stock'])} unidades "
                f"({equivalente} {unidad}(s)).")

    remove_stock(p["Id"], cantidad_base, razon=f"Venta por {unidad}")
    total = round(cantidad_medida * config["PrecioPorUnidad"], 2)
    nombre_label = f"{p['Name'].strip()} ({unidad})"
    return f"VENTA_INICIO:{cantidad_medida}|{nombre_label}|{config['PrecioPorUnidad']}|{total}|{p['Id']}"

register("unidadmedida.vender", vender_por_unidad_tool)
