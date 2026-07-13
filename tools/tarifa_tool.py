"""
Herramienta de Tarifas de Mano de Obra (Servicio Tecnico)
"""
from core.tool_registry import register
from database.aronium import crear_tarifa, get_tarifas


def agregar_tarifa_tool(data):
    descripcion = data.get("descripcion", "").strip()
    precio = data.get("precio", 0)
    if not descripcion:
        return "Dime la descripcion y el precio. Ejemplo: agregar tarifa revision basica Q50"
    crear_tarifa(descripcion, precio)
    return f"Tarifa '{descripcion}' agregada: Q{precio:.2f}."

register("tarifa.agregar", agregar_tarifa_tool)


def listar_tarifas_tool(data):
    tarifas = get_tarifas(activo=True)
    if not tarifas:
        return "No hay tarifas de mano de obra configuradas. Agrega una con: agregar tarifa [descripcion] Q[monto]"
    resp = f"{len(tarifas)} tarifa(s) de mano de obra:\n"
    for t in tarifas:
        resp += f"- {t['Descripcion']}: Q{t['Precio']:.2f}\n"
    return resp

register("tarifa.listar", listar_tarifas_tool)
