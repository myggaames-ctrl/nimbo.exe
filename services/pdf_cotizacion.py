"""
Generacion de PDF de cotizaciones
Nimbo AI
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

OUTPUT_DIR = '/home/ictor_axtor/micocina-dashboard/static/cotizaciones'
LOGO_PATH = '/home/ictor_axtor/micocina-dashboard/static/icon.png'

ACCENT = colors.HexColor("#2563eb")


def generar_pdf_cotizacion(cotizacion):
    """cotizacion: dict con numero, cliente_nombre, cliente_tel, items, total, fecha_vencimiento.
    Retorna la ruta relativa del PDF (servible desde /static/...)."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    numero = cotizacion["numero"]
    filepath = os.path.join(OUTPUT_DIR, f"{numero}.pdf")

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle("Titulo", parent=styles["Heading1"], fontSize=18, textColor=ACCENT, spaceAfter=2)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.grey)
    normal_style = styles["Normal"]

    doc = SimpleDocTemplate(filepath, pagesize=letter,
        topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=18 * mm, rightMargin=18 * mm)
    elementos = []

    # Encabezado con logo
    if os.path.exists(LOGO_PATH):
        header_data = [[
            Image(LOGO_PATH, width=18 * mm, height=18 * mm),
            [Paragraph("Mi Cocina Electrodomésticos", titulo_style),
             Paragraph("Guatemala", sub_style)]
        ]]
        header_table = Table(header_data, colWidths=[22 * mm, None])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elementos.append(header_table)
    else:
        elementos.append(Paragraph("Mi Cocina Electrodomésticos", titulo_style))
        elementos.append(Paragraph("Guatemala", sub_style))

    elementos.append(Spacer(1, 10 * mm))
    elementos.append(Paragraph(f"COTIZACIÓN {numero}", styles["Heading2"]))
    elementos.append(Spacer(1, 4 * mm))

    fecha_creada = cotizacion.get("fecha_creada", "")
    info_data = [
        ["Cliente:", cotizacion.get("cliente_nombre", "")],
        ["Teléfono:", cotizacion.get("cliente_tel", "") or "-"],
        ["Fecha:", fecha_creada or ""],
        ["Válida hasta:", str(cotizacion.get("fecha_vencimiento", ""))[:10]],
    ]
    info_table = Table(info_data, colWidths=[35 * mm, None])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elementos.append(info_table)
    elementos.append(Spacer(1, 8 * mm))

    items = cotizacion.get("items", [])
    tabla_items = [["Producto", "Cantidad", "Precio Unit.", "Subtotal"]]
    for i in items:
        tabla_items.append([
            i["nombre"],
            str(i["cantidad"]),
            f"Q{i['precio_unit']:.2f}",
            f"Q{i['subtotal']:.2f}",
        ])
    total = cotizacion.get("total", 0)
    tabla_items.append(["", "", "Total", f"Q{total:.2f}"])

    items_table = Table(tabla_items, colWidths=[80 * mm, 25 * mm, 30 * mm, 30 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.lightgrey),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    elementos.append(items_table)
    elementos.append(Spacer(1, 10 * mm))

    elementos.append(Paragraph(
        "Esta cotización tiene una validez de 15 días a partir de la fecha de emisión.",
        sub_style))
    elementos.append(Spacer(1, 4 * mm))
    elementos.append(Paragraph(
        "Gracias por su preferencia. Mi Cocina Electrodomésticos Guatemala.",
        sub_style))

    doc.build(elementos)
    return f"cotizaciones/{numero}.pdf"
