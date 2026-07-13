"""
Generacion de codigos de barras (EAN-13), QR y etiquetas PDF de productos
Nimbo AI
"""
import os
import re
import socket
import tempfile
from datetime import datetime

import barcode
from barcode.writer import ImageWriter
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

OUTPUT_DIR = '/home/ictor_axtor/micocina-dashboard/static/etiquetas'
PUERTO = 5000

# Tamano estandar de etiqueta para impresoras de etiquetas
ANCHO_ETIQUETA = 50 * mm
ALTO_ETIQUETA = 30 * mm


def get_local_ip():
    """IP de la maquina en la red local, para que el QR de la etiqueta funcione
    escaneado desde un telefono en la misma red (ver Pendiente #5 en CLAUDE.md:
    Nimbo todavia no es accesible fuera de la red local)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "localhost"


def _truncar(texto, largo=26):
    texto = (texto or "").strip()
    if len(texto) <= largo:
        return texto
    return texto[:largo - 1].rstrip() + "…"


def _generar_imagen_barcode(codigo, tmp_dir):
    """codigo puede ser un EAN-13 generado por nosotros (13 digitos, ver
    database.aronium.generar_ean13) o un Code de Aronium ya existente antes de esta
    funcionalidad, que no necesariamente es un EAN-13 valido (ej. "01293428", 8 digitos,
    o alfanumerico tipo "LIC001"). Si son 13 digitos numericos se dibuja como EAN-13
    (python-barcode recalcula el digito verificador con el mismo algoritmo estandar que
    database.aronium._digito_verificador_ean13, asi que coincide); cualquier otro formato
    se dibuja como Code128, que acepta cualquier texto/longitud sin lanzar error."""
    if codigo.isdigit() and len(codigo) == 13:
        bc = barcode.get('ean13', codigo[:12], writer=ImageWriter())
    else:
        bc = barcode.get('code128', codigo, writer=ImageWriter())

    nombre_archivo = re.sub(r"[^A-Za-z0-9_-]", "_", codigo)
    ruta_base = os.path.join(tmp_dir, f"barcode_{nombre_archivo}")
    return bc.save(ruta_base, options={"write_text": False, "quiet_zone": 1.0, "module_height": 9.0})


def _generar_imagen_qr(url, codigo_ean, tmp_dir):
    img = qrcode.make(url, box_size=6, border=1)
    ruta = os.path.join(tmp_dir, f"qr_{codigo_ean}.png")
    img.save(ruta)
    return ruta


def _url_producto(codigo_ean):
    return f"http://{get_local_ip()}:{PUERTO}/producto/{codigo_ean}"


def _dibujar_etiqueta(c, tmp_dir, producto):
    """Dibuja una etiqueta (nombre, precio, codigo de barras, QR) en la pagina actual
    del canvas. producto: dict con nombre, precio, codigo."""
    nombre = _truncar(producto["nombre"])
    precio = producto["precio"]
    codigo = producto["codigo"]

    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(ANCHO_ETIQUETA / 2, ALTO_ETIQUETA - 4 * mm, nombre)

    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(ANCHO_ETIQUETA / 2, ALTO_ETIQUETA - 9.5 * mm, f"Q{precio:.2f}")

    barcode_path = _generar_imagen_barcode(codigo, tmp_dir)
    bw, bh = 30 * mm, 9 * mm
    c.drawImage(barcode_path, 2 * mm, 3 * mm, width=bw, height=bh,
        preserveAspectRatio=True, mask='auto')

    qr_path = _generar_imagen_qr(_url_producto(codigo), codigo, tmp_dir)
    qw = 12 * mm
    c.drawImage(qr_path, ANCHO_ETIQUETA - qw - 2 * mm, 3 * mm, width=qw, height=qw,
        preserveAspectRatio=True, mask='auto')

    c.setFont("Helvetica", 4.5)
    c.drawCentredString(2 * mm + bw / 2, 2 * mm, codigo)


def generar_etiquetas_pdf(productos, nombre_archivo):
    """productos: lista de dicts {nombre, precio, codigo}. Genera un PDF con una
    etiqueta de 5x3cm por pagina (una pagina = una etiqueta fisica, listo para una
    impresora de etiquetas continua). Retorna la ruta relativa servible desde /static."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, nombre_archivo)

    c = canvas.Canvas(filepath, pagesize=(ANCHO_ETIQUETA, ALTO_ETIQUETA))
    with tempfile.TemporaryDirectory() as tmp_dir:
        for producto in productos:
            _dibujar_etiqueta(c, tmp_dir, producto)
            c.showPage()
        c.save()

    return f"etiquetas/{nombre_archivo}"


def generar_etiqueta_producto_pdf(nombre, precio, codigo):
    nombre_archivo = f"ETQ-{re.sub(r'[^A-Za-z0-9_-]', '_', codigo)}.pdf"
    return generar_etiquetas_pdf([{"nombre": nombre, "precio": precio, "codigo": codigo}], nombre_archivo)


def generar_etiquetas_lote_pdf(productos):
    nombre_archivo = f"ETIQUETAS-{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return generar_etiquetas_pdf(productos, nombre_archivo)
