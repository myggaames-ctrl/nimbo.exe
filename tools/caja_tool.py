"""
Herramienta de Caja Registradora
"""
from core.tool_registry import register
from database.nimbo_db import get_turno_abierto, retirar_caja


def abrir_caja_tool(data):
    if get_turno_abierto():
        return "Ya hay un turno de caja abierto. Escribe 'cerrar caja' para cerrarlo antes de abrir uno nuevo."
    return "CAJA_ABRIR_INICIO"

register("caja.abrir", abrir_caja_tool)


def cerrar_caja_tool(data):
    if not get_turno_abierto():
        return "No hay ningun turno de caja abierto."
    return "CAJA_CERRAR_INICIO"

register("caja.cerrar", cerrar_caja_tool)


def retirar_caja_tool(data):
    turno = get_turno_abierto()
    if not turno:
        return "No hay ningun turno de caja abierto."
    monto = data.get("monto", 0) if isinstance(data, dict) else 0
    descripcion = data.get("descripcion", "") if isinstance(data, dict) else ""
    resultado = retirar_caja(turno["Id"], monto, descripcion)
    if resultado.get("error"):
        return resultado["error"]
    resp = f"Retiro de Q{monto} registrado"
    if descripcion:
        resp += f" ({descripcion})"
    resp += ". Efectivo esperado en caja actualizado."
    if resultado.get("sencillo_bajo"):
        resp += f"\n\nAtencion: el sencillo esta bajo (Q{resultado['denominaciones_pequenas']} en denominaciones pequenas, menos de Q200)."
    return resp

register("caja.retirar", retirar_caja_tool)


def efectivo_actual_tool(data):
    turno = get_turno_abierto()
    if not turno:
        return "No hay ningun turno de caja abierto."
    resp = f"Efectivo esperado en caja: Q{turno['EfectivoEsperado']}\n"
    resp += f"Ventas del turno: Q{turno['TotalVentas']} (Efectivo Q{turno['TotalEfectivo']}, Tarjeta Q{turno['TotalTarjeta']}, Mixto Q{turno['TotalMixto']})\n"
    resp += f"Turno abierto por {turno['EmpleadoNombre']} desde {turno['FechaApertura']}"
    return resp

register("caja.efectivo_actual", efectivo_actual_tool)


def anular_caja_tool(data):
    if not get_turno_abierto():
        return "No hay ningun turno de caja abierto para anular."
    motivo = data.get("motivo", "").strip() if isinstance(data, dict) else ""
    if motivo:
        return f"CAJA_ANULAR_CONFIRMAR:{motivo}"
    return "CAJA_ANULAR_INICIO"

register("caja.anular", anular_caja_tool)
