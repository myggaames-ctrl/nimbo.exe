"""
Herramienta de Combos/Kits de productos
"""
import json
import re
from core.tool_registry import register
from database.nimbo_db import (
    get_products, get_combos, buscar_combos, vender_combo, DESCUENTO_COMBO_SUGERIDO
)
from services.ollama_service import analizar_ollama, MENSAJE_TIMEOUT


def crear_combo_tool(data):
    nombre = data.get("nombre", "").strip()
    if not nombre:
        return "Dime el nombre del combo. Ejemplo: crear combo Kit Licuadora"
    return f"COMBO_INICIO:{nombre}"

register("combo.crear", crear_combo_tool)


def listar_combos_tool(data):
    combos = get_combos(activo=True)
    if not combos:
        return "No hay combos activos."
    resp = f"{len(combos)} combo(s) activo(s):\n"
    for c in combos:
        detalle = ", ".join(f"{i['Cantidad']}x {i['ProductoNombre']}" for i in c["items"])
        resp += f"- {c['Nombre']}: Q{c['PrecioCombo']} ({detalle})\n"
    return resp

register("combo.listar", listar_combos_tool)


def vender_combo_tool(data):
    nombre = data.get("nombre", "").strip()
    combos = buscar_combos(nombre)
    if not combos:
        return f"No encontre ningun combo activo que coincida con '{nombre}'."
    combo = combos[0]
    resultado = vender_combo(combo["Id"])
    if resultado.get("error"):
        return resultado["error"]

    detalle = ", ".join(f"{i['Cantidad']}x {i['ProductoNombre']}" for i in resultado["items"])
    resp = f"Venta #{resultado['venta_id']} registrada. Combo {resultado['combo']['Nombre']}: {detalle}. Total: Q{resultado['total']}."
    if resultado["garantias"]:
        pares = zip(resultado["garantias"], resultado["items"])
        resp += "\nGarantias: " + ", ".join(f"{g['numero']} ({i['ProductoNombre']})" for g, i in pares)
    return resp

register("combo.vender", vender_combo_tool)


def _limpiar_bloque_json(texto):
    return re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()


def sugerir_combos_tool(data):
    productos = [p for p in get_products(limit=200) if p.get("Stock", 0) and p["Stock"] > 0]
    if not productos:
        return "No hay productos con stock disponible para sugerir combos."

    catalogo = "\n".join(f"- {p['Name'].strip()} (Q{p['Price']:.2f}, stock {int(p['Stock'])})" for p in productos)

    prompt = f"""Eres el asesor comercial de Mi Cocina Electrodomesticos, una tienda de electrodomesticos y repuestos en Guatemala.

Este es el inventario actual con stock disponible:
{catalogo}

Sugiere exactamente 3 combos/kits logicos para vender juntos (por ejemplo: un electrodomestico
con su repuesto o accesorio mas comun), usando UNICAMENTE productos que aparecen en la lista de
arriba (copia el nombre exacto tal como aparece ahi).

Responde EXCLUSIVAMENTE con un JSON valido (sin texto adicional, sin markdown, sin explicaciones),
con este formato exacto:
[
  {{"nombre": "nombre corto y comercial del combo", "descripcion": "por que tiene sentido venderlos juntos", "productos": ["nombre exacto producto 1", "nombre exacto producto 2"]}},
  ...
]"""

    texto = analizar_ollama(prompt)
    if not texto:
        return "No pude generar sugerencias de combos: Ollama no esta disponible. Verifica que este corriendo."
    if texto == MENSAJE_TIMEOUT:
        return texto

    try:
        sugerencias = json.loads(_limpiar_bloque_json(texto))
    except (json.JSONDecodeError, TypeError, AttributeError):
        return "No pude interpretar la sugerencia de combos. Intenta de nuevo."

    if not isinstance(sugerencias, list):
        return "No pude interpretar la sugerencia de combos. Intenta de nuevo."

    resp = f"Combos sugeridos (descuento del {int(DESCUENTO_COMBO_SUGERIDO * 100)}% sobre el precio normal):\n\n"
    encontrados = 0
    for s in sugerencias[:3]:
        items = []
        for nombre_prod in s.get("productos", []):
            coincidencias = get_products(search=nombre_prod)
            if coincidencias:
                items.append(coincidencias[0])
        if len(items) < 2:
            continue

        suma = round(sum(p["Price"] for p in items), 2)
        descuento = round(suma * DESCUENTO_COMBO_SUGERIDO, 2)
        precio_combo = round(suma - descuento, 2)
        encontrados += 1

        resp += f"{encontrados}. {s.get('nombre', 'Combo')}\n"
        if s.get("descripcion"):
            resp += f"   {s['descripcion']}\n"
        resp += "   Incluye: " + ", ".join(p["Name"].strip() for p in items) + "\n"
        resp += f"   Precio normal: Q{suma:.2f} | Descuento: -Q{descuento:.2f} | Precio combo: Q{precio_combo:.2f}\n\n"

    if encontrados == 0:
        return "No se logro sugerir combos con productos que coincidan con el inventario actual. Intenta de nuevo."

    resp += "Para crear alguno, escribe: crear combo [nombre]"
    return resp

register("combo.sugerir", sugerir_combos_tool)
