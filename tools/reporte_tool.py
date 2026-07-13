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
