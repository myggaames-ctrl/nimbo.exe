"""
Generacion de PDF de referencia para la declaracion mensual de IVA (SAT-2046)
Nimbo AI
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = BASE_DIR
LOGO_PATH = os.path.join(BASE_DIR, 'static', 'icon.png')

ACCENT = colors.HexColor("#2563eb")


def generar_pdf_declaracion_iva(datos):
    """datos: dict de database.aronium.get_declaracion_iva(). Guarda el PDF en
    la raiz del proyecto (no es publico como las cotizaciones - es informacion
    financiera interna, se sirve solo via /api/download/<filename>, con
    login). Retorna el nombre de archivo (sin ruta)."""
    filename = f"iva_{datos['anio']}_{datos['mes']:02d}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle("Titulo", parent=styles["Heading1"], fontSize=18, textColor=ACCENT, spaceAfter=2)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.grey)

    doc = SimpleDocTemplate(filepath, pagesize=letter,
        topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=18 * mm, rightMargin=18 * mm)
    elementos = []

    if os.path.exists(LOGO_PATH):
        header_data = [[
            Image(LOGO_PATH, width=18 * mm, height=18 * mm),
            [Paragraph("Mi Cocina Electrodomésticos", titulo_style),
             Paragraph("Guatemala", sub_style)]
        ]]
        header_table = Table(header_data, colWidths=[22 * mm, None])
        header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        elementos.append(header_table)
    else:
        elementos.append(Paragraph("Mi Cocina Electrodomésticos", titulo_style))
        elementos.append(Paragraph("Guatemala", sub_style))

    elementos.append(Spacer(1, 10 * mm))
    elementos.append(Paragraph(f"Declaración mensual de IVA - {datos['periodo']}", styles["Heading2"]))
    elementos.append(Paragraph("Referencia para el formulario SAT-2046 (declaraguate.com)", sub_style))
    elementos.append(Spacer(1, 8 * mm))

    filas = [
        ["Concepto", "Monto Q"],
        [f"Ventas totales del periodo ({datos['cantidad_ventas']} ventas)", f"{datos['total_ventas']:.2f}"],
        ["Debito fiscal (IVA cobrado, ventas x 12/112)", f"{datos['debito_fiscal']:.2f}"],
        [f"Compras a proveedores registradas ({datos['cantidad_ordenes_compra']} ordenes)", f"{datos['total_compras']:.2f}"],
        ["Credito fiscal (IVA pagado, compras x 12%)", f"{datos['credito_fiscal']:.2f}"],
    ]
    tabla = Table(filas, colWidths=[120 * mm, 30 * mm])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 6 * mm))

    if datos["a_favor"]:
        resultado_txt = f"Crédito fiscal a favor: Q{abs(datos['iva_a_pagar']):.2f} (remanente para el siguiente período, no se paga IVA este mes)"
    else:
        resultado_txt = f"IVA a pagar: Q{datos['iva_a_pagar']:.2f}"
    resultado_style = ParagraphStyle("Resultado", parent=styles["Heading3"], textColor=colors.black)
    elementos.append(Paragraph(resultado_txt, resultado_style))
    elementos.append(Spacer(1, 8 * mm))

    elementos.append(Paragraph(datos["plazo"], sub_style))
    elementos.append(Spacer(1, 4 * mm))
    elementos.append(Paragraph(
        "Este documento es solo de referencia interna. Verifica los montos contra tus "
        "facturas de venta y de compra antes de presentar la declaración oficial.",
        sub_style))

    doc.build(elementos)
    return filename
