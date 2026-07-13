"""
Generacion de texto de ticket de venta (impresion fisica pendiente)
Nimbo AI
"""

ANCHO = 32


def generar_texto_ticket(numero_venta, fecha, items, total, metodo_pago,
                          cliente_nombre="", efectivo_recibido=None, cambio=None, cajero="",
                          subtotal=None, descuento=None):
    linea = "-" * ANCHO
    out = []
    out.append("MI COCINA ELECTRODOMESTICOS".center(ANCHO))
    out.append("Guatemala".center(ANCHO))
    out.append(linea)
    out.append(f"Venta #{numero_venta}")
    out.append(f"Fecha: {fecha}")
    if cajero:
        out.append(f"Cajero: {cajero}")
    if cliente_nombre:
        out.append(f"Cliente: {cliente_nombre}")
    out.append(linea)
    for i in items:
        nombre = str(i.get("nombre", ""))[:ANCHO]
        out.append(nombre)
        cantidad = i.get("cantidad", 0)
        precio_unit = i.get("precio_unit", 0)
        subtotal = i.get("subtotal", 0)
        out.append(f"  {cantidad} x Q{precio_unit:.2f} = Q{subtotal:.2f}")
    out.append(linea)
    if descuento:
        if subtotal is not None:
            out.append(f"Subtotal: Q{subtotal:.2f}".rjust(ANCHO))
        out.append(f"Descuento ({descuento['nombre']}): -Q{descuento['monto_descuento']:.2f}".rjust(ANCHO))
    out.append(f"TOTAL: Q{total:.2f}".rjust(ANCHO))
    out.append(f"Pago: {metodo_pago}")
    if efectivo_recibido is not None:
        out.append(f"Recibido: Q{efectivo_recibido:.2f}")
    if cambio is not None and cambio > 0:
        out.append(f"Cambio: Q{cambio:.2f}")
    out.append(linea)
    out.append("Gracias por su compra!".center(ANCHO))
    return "\n".join(out)
