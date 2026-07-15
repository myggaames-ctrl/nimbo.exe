"""
Herramienta de Reportes
"""
from core.tool_registry import register
from database.aronium import get_reporte_dia, get_reporte_periodo

def reporte_dia_tool(data):
    r = get_reporte_dia()
    resp = "Cierre del dia:\n"
    resp += f"Ventas: {r['total_ventas']}\n"
    resp += f"Total vendido: Q{r['total_vendido']}\n"
    resp += f"Costo productos: Q{r['total_costo']}\n"
    resp += f"Ganancia bruta: Q{r['ganancia_bruta']}\n"
    resp += f"Comision POS (6%): Q{r['comision_pos']}\n"
    resp += f"Ganancia neta: Q{r['ganancia_neta']}"
    if r["ventas_por_cobrador"]:
        resp += "\n\nVentas por cobrador:\n"
        resp += "\n".join(
            f"- {c['cobrador']}: {c['ventas']} venta(s), Q{c['total']}"
            for c in r["ventas_por_cobrador"]
        )
    return resp

register("reporte.dia", reporte_dia_tool)

def reporte_mensual_tool(data):
    from datetime import datetime
    r = get_reporte_periodo(mes=datetime.now().month, anio=datetime.now().year)
    resp = f"Reporte mensual - {datetime.now().strftime('%B %Y')}:\n"
    resp += f"Ventas: {r['total_ventas']}\n"
    resp += f"Total vendido: Q{r['total_vendido']}\n"
    resp += f"Comision POS: Q{r['comision_pos']}\n"
    resp += f"Ganancia estimada: Q{r['ganancia_estimada']}\n"
    if r['mejores_clientes']:
        resp += "\nMejores clientes:\n"
        for c in r['mejores_clientes']:
            resp += f"- {c['Nombre']}: Q{c['total']} ({c['compras']} compras)\n"
    return resp

register("reporte.mensual", reporte_mensual_tool)

def reporte_trimestral_tool(data):
    from datetime import datetime
    mes = datetime.now().month
    trimestre = (mes - 1) // 3 + 1
    r = get_reporte_periodo(trimestre=trimestre, anio=datetime.now().year)
    resp = f"Reporte trimestral Q{trimestre} {datetime.now().year}:\n"
    resp += f"Ventas: {r['total_ventas']}\n"
    resp += f"Total vendido: Q{r['total_vendido']}\n"
    resp += f"Comision POS: Q{r['comision_pos']}\n"
    resp += f"Ganancia estimada: Q{r['ganancia_estimada']}\n"
    if r['mejores_clientes']:
        resp += "\nMejores clientes:\n"
        for c in r['mejores_clientes']:
            resp += f"- {c['Nombre']}: Q{c['total']} ({c['compras']} compras)\n"
    return resp

register("reporte.trimestral", reporte_trimestral_tool)

def reporte_semestral_tool(data):
    from datetime import datetime
    mes = datetime.now().month
    semestre = 1 if mes <= 6 else 2
    r = get_reporte_periodo(semestre=semestre, anio=datetime.now().year)
    resp = f"Reporte semestral S{semestre} {datetime.now().year}:\n"
    resp += f"Ventas: {r['total_ventas']}\n"
    resp += f"Total vendido: Q{r['total_vendido']}\n"
    resp += f"Comision POS: Q{r['comision_pos']}\n"
    resp += f"Ganancia estimada: Q{r['ganancia_estimada']}\n"
    return resp

register("reporte.semestral", reporte_semestral_tool)

def reporte_anual_tool(data):
    from datetime import datetime
    r = get_reporte_periodo(anio=datetime.now().year)
    resp = f"Reporte anual {datetime.now().year}:\n"
    resp += f"Ventas: {r['total_ventas']}\n"
    resp += f"Total vendido: Q{r['total_vendido']}\n"
    resp += f"Comision POS: Q{r['comision_pos']}\n"
    resp += f"Ganancia estimada: Q{r['ganancia_estimada']}\n"
    if r['mejores_clientes']:
        resp += "\nMejores clientes del año:\n"
        for c in r['mejores_clientes']:
            resp += f"- {c['Nombre']}: Q{c['total']} ({c['compras']} compras)\n"
    return resp

register("reporte.anual", reporte_anual_tool)

def mejores_clientes_tool(data):
    periodo = data.get("periodo", "mes") if isinstance(data, dict) else "mes"
    from datetime import datetime
    mes = datetime.now().month
    trimestre = (mes - 1) // 3 + 1
    anio = datetime.now().year
    if periodo == "trimestre":
        r = get_reporte_periodo(trimestre=trimestre, anio=anio)
        titulo = f"trimestre Q{trimestre}"
    else:
        r = get_reporte_periodo(mes=mes, anio=anio)
        titulo = "mes"
    if not r['mejores_clientes']:
        return f"No hay clientes registrados este {titulo}."
    resp = f"Mejores clientes del {titulo}:\n"
    for i, c in enumerate(r['mejores_clientes'], 1):
        resp += f"{i}. {c['Nombre']}: Q{c['total']} ({c['compras']} compras)\n"
    return resp

register("reporte.mejores_clientes", mejores_clientes_tool)

def excel_reporte_tool(data):
    periodo = data.get("periodo", "mes") if isinstance(data, dict) else "mes"
    import openpyxl
    from datetime import datetime
    from database.aronium import nimbo_connect

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ventas"
    ws.append(["Fecha", "Descripcion", "Total", "Cliente"])

    conn = nimbo_connect()
    cur = conn.cursor()
    mes = datetime.now().month
    anio = datetime.now().year
    trimestre = (mes - 1) // 3 + 1

    if periodo == "mes":
        cur.execute("""SELECT v.Fecha, v.Descripcion, v.Total, IFNULL(c.Nombre,'Sin cliente')
            FROM Venta v LEFT JOIN Cliente c ON v.ClienteId=c.Id
            WHERE v.Mes=? AND v.Anio=? ORDER BY v.Fecha""", (mes, anio))
        titulo = f"ventas_mes_{mes}_{anio}"
    elif periodo == "trimestre":
        meses = {1:[1,2,3], 2:[4,5,6], 3:[7,8,9], 4:[10,11,12]}
        m = meses.get(trimestre, [1,2,3])
        cur.execute("""SELECT v.Fecha, v.Descripcion, v.Total, IFNULL(c.Nombre,'Sin cliente')
            FROM Venta v LEFT JOIN Cliente c ON v.ClienteId=c.Id
            WHERE v.Mes IN (?,?,?) AND v.Anio=? ORDER BY v.Fecha""", (*m, anio))
        titulo = f"ventas_Q{trimestre}_{anio}"
    else:
        cur.execute("""SELECT v.Fecha, v.Descripcion, v.Total, IFNULL(c.Nombre,'Sin cliente')
            FROM Venta v LEFT JOIN Cliente c ON v.ClienteId=c.Id
            WHERE v.Anio=? ORDER BY v.Fecha""", (anio,))
        titulo = f"ventas_{anio}"

    for row in cur.fetchall():
        ws.append(list(row))
    conn.close()

    filename = f"/home/ictor_axtor/micocina-dashboard/{titulo}.xlsx"
    wb.save(filename)
    return f"DOWNLOAD:{titulo}.xlsx"

register("reporte.excel", excel_reporte_tool)


def limpieza_anual_tool(data):
    from datetime import datetime
    from database.aronium import archivar_y_limpiar_anio
    anio = datetime.now().year - 1
    try:
        archivo = archivar_y_limpiar_anio(anio)
        return f"DOWNLOAD:{archivo.split('/')[-1]}"
    except Exception as e:
        return f"Error: {e}"

register("reporte.limpieza", limpieza_anual_tool)


def backup_tool(data):
    from database.aronium import hacer_backup
    try:
        fecha = hacer_backup()
        return f"Backup completado exitosamente. Archivo guardado: nimbo_{fecha}.db"
    except Exception as e:
        return f"Error en backup: {e}"

register("sistema.backup", backup_tool)


def cuando_vendo_mas_tool(data):
    from database.aronium import get_patrones_ventas
    p = get_patrones_ventas()
    if p["total_ventas_analizadas"] == 0:
        return f"No hay ventas registradas en los ultimos {p['periodo_dias']} dias para analizar."

    resp = "Cuando vendes mas:\n\n"
    if p["mejor_dia"]:
        resp += f"Mejor dia: {p['mejor_dia']['dia']} ({p['mejor_dia']['ventas']} ventas, Q{p['mejor_dia']['total']:.2f})\n"
    if p["ratio_mejor_peor_dia"] and p["peor_dia"]["dia"] != p["mejor_dia"]["dia"]:
        resp += f"Vendes {p['ratio_mejor_peor_dia']}x mas los {p['mejor_dia']['dia']} que los {p['peor_dia']['dia']}\n"
    if p["mejor_hora"]:
        resp += f"Mejor hora: {p['mejor_hora']['hora']}:00 ({p['mejor_hora']['ventas']} ventas)\n"

    resp += "\nDesglose por dia de la semana:\n"
    for d in p["dias_semana"]:
        resp += f"- {d['dia']}: {d['ventas']} ventas (Q{d['total']:.2f})\n"
    return resp.strip()

register("reporte.cuando_vendo_mas", cuando_vendo_mas_tool)


def _texto_patrones(p):
    dias_txt = "\n".join(f"- {d['dia']}: {d['ventas']} ventas, Q{d['total']:.2f}" for d in p["dias_semana"])
    horas_txt = "\n".join(
        f"- {h['hora']}:00: {h['ventas']} ventas, Q{h['total']:.2f}" for h in p["horas_pico"]
    ) or "(sin datos suficientes de hora)"
    juntos_txt = "\n".join(
        f"- {j['producto_a']} + {j['producto_b']}: {j['veces']} veces juntos" for j in p["productos_juntos"]
    ) or "(no se detectaron productos que se compren juntos con frecuencia)"
    ciclicos_txt = "\n".join(
        f"- {c['cliente']}: compra cada {c['frecuencia_dias']:.0f} dias en promedio, "
        f"ultima compra {c['ultima_compra']}, proxima estimada {c['proxima_compra_estimada']}"
        for c in p["clientes_ciclicos"]
    ) or "(no se detectaron clientes con un ciclo de compra regular)"

    t = p["tendencia"]
    if t["cambio_pct"] is not None:
        tendencia_txt = (f"Ultimas 4 semanas: Q{t['total_ultimas_4_semanas']:.2f} vs 4 semanas anteriores: "
                          f"Q{t['total_4_semanas_anteriores']:.2f} ({t['cambio_pct']:+.1f}%)")
    else:
        tendencia_txt = (f"Ultimas 4 semanas: Q{t['total_ultimas_4_semanas']:.2f} "
                          "(sin datos suficientes del periodo anterior para comparar)")

    return dias_txt, horas_txt, juntos_txt, ciclicos_txt, tendencia_txt


def _resumen_patrones_sin_gemini(p, dias_txt, horas_txt, juntos_txt, ciclicos_txt, tendencia_txt):
    resp = f"Patrones de venta ({p['periodo_dias']} dias, {p['total_ventas_analizadas']} ventas):\n\n"
    resp += f"VENTAS POR DIA:\n{dias_txt}\n\n"
    resp += f"VENTAS POR HORA:\n{horas_txt}\n\n"
    resp += f"PRODUCTOS QUE SE VENDEN JUNTOS:\n{juntos_txt}\n\n"
    resp += f"TENDENCIA:\n{tendencia_txt}\n\n"
    resp += f"CLIENTES CICLICOS:\n{ciclicos_txt}"
    return resp


def patrones_ventas_tool(data):
    from database.aronium import get_patrones_ventas
    import os

    p = get_patrones_ventas()
    if p["total_ventas_analizadas"] == 0:
        return f"No hay suficientes ventas registradas (ultimos {p['periodo_dias']} dias) para analizar patrones."

    dias_txt, horas_txt, juntos_txt, ciclicos_txt, tendencia_txt = _texto_patrones(p)

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if not gemini_key:
        return _resumen_patrones_sin_gemini(p, dias_txt, horas_txt, juntos_txt, ciclicos_txt, tendencia_txt)

    from google import genai
    cliente = genai.Client(api_key=gemini_key)

    prompt = f"""Eres el analista de ventas de Mi Cocina Electrodomesticos, tienda de electrodomesticos y repuestos en Guatemala.
Analiza estos datos REALES de los ultimos {p['periodo_dias']} dias ({p['total_ventas_analizadas']} ventas) y da recomendaciones practicas.

VENTAS POR DIA DE LA SEMANA:
{dias_txt}

VENTAS POR HORA DEL DIA (top 5):
{horas_txt}

PRODUCTOS QUE SE VENDEN JUNTOS CON FRECUENCIA:
{juntos_txt}

TENDENCIA:
{tendencia_txt}

CLIENTES CON CICLO DE COMPRA REGULAR:
{ciclicos_txt}

Responde en espanol, directo y practico, con:
1. El dia y hora en que mas se vende (compara con el mas flojo, usa los numeros reales que te di)
2. Que combos de productos conviene ofrecer juntos en mostrador (solo si hay datos, no inventes)
3. Si la tendencia esta subiendo o bajando y una posible razon o accion concreta
4. Que clientes ciclicos conviene contactar pronto por su proxima compra estimada
No inventes numeros que no te di, y si algun apartado no tiene datos suficientes dilo claramente."""

    r = cliente.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    return r.text

register("reporte.patrones_ventas", patrones_ventas_tool)


def proxima_compra_tool(query):
    from database.aronium import buscar_cliente_completo, get_prediccion_compra_cliente
    clientes = buscar_cliente_completo(query)
    if not clientes:
        return f"No encontre cliente con '{query}'."

    prediccion = get_prediccion_compra_cliente(query)
    if not prediccion:
        return (f"{clientes[0]['Nombre']} no tiene suficiente historial de compras (minimo 3) "
                f"para predecir su proxima compra.")

    resp = f"{prediccion['cliente']} compra en promedio cada {prediccion['frecuencia_dias']:.0f} dias"
    if not prediccion["regular"]:
        resp += " (patron irregular, esta prediccion es menos confiable)"
    resp += (f". Ultima compra: {prediccion['ultima_compra']}. "
             f"Proxima compra estimada: {prediccion['proxima_compra_estimada']}.")
    return resp

register("reporte.proxima_compra", proxima_compra_tool)


def _texto_progreso_meta(p):
    resp = f"Llevas Q{p['ventas_actuales']:.2f} de Q{p['meta_q']:.2f} esta semana ({p['porcentaje']}%)."
    if p["estado"] == "CUMPLIDA":
        resp += (f"\n🎉 Meta cumplida! Te sugiero una nueva meta de Q{p['nueva_meta_sugerida']:.2f} "
                 f"para la proxima semana.")
    elif p["atrasado"]:
        resp += f"\n⚠️ Vas atrasado: llevas {p['porcentaje']}% y quedan {p['dias_restantes']} dia(s) de la semana."
    else:
        resp += f"\nQuedan {p['dias_restantes']} dia(s) de la semana."
    return resp


def meta_semanal_definir_tool(data):
    monto = data.get("monto") if isinstance(data, dict) else None
    if monto is None:
        return "No entendi el monto de la meta. Escribe 'meta semanal Q[monto]'."
    monto = float(monto)
    if monto <= 0:
        return "La meta semanal debe ser un monto positivo."

    from database.aronium import set_meta_semanal
    p = set_meta_semanal(monto)
    return (f"Meta semanal definida: Q{p['meta_q']:.2f} (semana del {p['fecha_inicio']} al {p['fecha_fin']}).\n"
            + _texto_progreso_meta(p))

register("reporte.meta_definir", meta_semanal_definir_tool)


def meta_semanal_progreso_tool(data):
    from database.aronium import get_progreso_meta_semanal
    p = get_progreso_meta_semanal()
    if not p:
        return "No has definido una meta de ventas para esta semana. Escribe 'meta semanal Q[monto]' para definirla."
    return _texto_progreso_meta(p)

register("reporte.meta_progreso", meta_semanal_progreso_tool)


def meta_semanal_falta_tool(data):
    from database.aronium import get_progreso_meta_semanal
    p = get_progreso_meta_semanal()
    if not p:
        return "No has definido una meta de ventas para esta semana. Escribe 'meta semanal Q[monto]' para definirla."
    if p["estado"] == "CUMPLIDA":
        return (f"Ya cumpliste la meta de esta semana! Llevas Q{p['ventas_actuales']:.2f} de Q{p['meta_q']:.2f}. "
                f"Te sugiero una nueva meta de Q{p['nueva_meta_sugerida']:.2f} para la proxima semana.")
    return f"Te faltan Q{p['falta_q']:.2f} para llegar a la meta de Q{p['meta_q']:.2f} esta semana."

register("reporte.meta_falta", meta_semanal_falta_tool)
