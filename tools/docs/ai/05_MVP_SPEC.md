# NIMBO AI
# MVP SPECIFICATION
Version: 1.0

===============================================================================
OBJETIVO
===============================================================================

Este documento define el comportamiento esperado del MVP de Nimbo AI.

No describe implementación.

No describe código.

Describe el comportamiento funcional que debe tener el sistema.

Toda implementación debe cumplir esta especificación.

===============================================================================
DEFINICIÓN DE MVP
===============================================================================

El MVP debe permitir administrar una pequeña empresa completamente
mediante conversación natural.

El usuario debe poder ejecutar las operaciones más importantes sin navegar
entre pantallas complejas.

El objetivo del MVP es ahorrar tiempo, reducir errores y automatizar procesos
repetitivos.

===============================================================================
MÓDULOS DEL MVP
===============================================================================

✓ Clientes

✓ Inventario

✓ Presupuestos

✓ Ventas

✓ Servicio Técnico

✓ Reportes

✓ Configuración

===============================================================================
MÓDULO CLIENTES
===============================================================================

ESTADO

EN DESARROLLO

FUNCIONES

[✓] Crear cliente

[✓] Buscar cliente

[✓] Editar cliente

[✓] Eliminar cliente

[✓] Listar clientes

COMPORTAMIENTO

El usuario debe poder administrar completamente los clientes mediante
comandos naturales.

Ejemplos

crear cliente Pedro

buscar cliente Pedro

editar cliente Pedro

eliminar cliente Pedro

clientes

===============================================================================
MÓDULO INVENTARIO
===============================================================================

ESTADO

EN DESARROLLO

FUNCIONES

[✓] Buscar producto

[✓] Buscar código

[✓] Buscar código de barras

[✓] Listar productos

[ ] Buscar por categoría

[ ] Buscar por marca

COMPORTAMIENTO

Toda búsqueda debe utilizar la base de datos de Aronium.

Nimbo nunca duplicará el inventario.

===============================================================================
MÓDULO PRESUPUESTOS
===============================================================================

ESTADO

EN DESARROLLO

FUNCIONES

[✓] Crear presupuesto

[✓] Mostrar presupuesto

[✓] Agregar producto

[ ] Cambiar cantidad

[ ] Eliminar producto

[ ] Vaciar presupuesto

[ ] Agregar notas

[ ] Cambiar estado

[ ] Generar PDF

[ ] Enviar WhatsApp

[ ] Enviar correo

[ ] Convertir en venta

COMPORTAMIENTO

El presupuesto es un documento vivo.

Puede modificarse hasta que sea enviado.

Después de enviarse debe conservar historial.

Debe recordar:

Cliente

Productos

Cantidades

Precios

Costos

Notas

Estado

Fecha

Hora

Usuario

===============================================================================
MÓDULO SERVICIO TÉCNICO
===============================================================================

ESTADO

PENDIENTE

OBJETIVO

Administrar completamente las reparaciones.

FUNCIONES

[ ] Crear orden

[ ] Diagnóstico

[ ] Esperando aprobación

[ ] Reparación

[ ] Pruebas

[ ] Listo para entregar

[ ] Entregado

[ ] Historial

[ ] QR

[ ] Código de barras

[ ] Ticket

[ ] WhatsApp

[ ] Correo

COMPORTAMIENTO

Cada equipo debe tener un historial completo.

Debe registrarse:

Fecha

Hora

Usuario

Estado

Observaciones

Diagnóstico

Piezas utilizadas

Costo

Garantía

===============================================================================
MÓDULO VENTAS
===============================================================================

ESTADO

PENDIENTE

FUNCIONES

[ ] Crear venta

[ ] Convertir presupuesto

[ ] Registrar pago

[ ] Descontar inventario

[ ] Historial

===============================================================================
MÓDULO REPORTES
===============================================================================

ESTADO

PENDIENTE

FUNCIONES

[ ] Ventas

[ ] Inventario

[ ] Clientes

[ ] Reparaciones

[ ] Productos más vendidos

[ ] Utilidad

[ ] Proyecciones

===============================================================================
MÓDULO CONFIGURACIÓN
===============================================================================

ESTADO

PENDIENTE

FUNCIONES

[ ] Datos de la empresa

[ ] Logo

[ ] Colores

[ ] Redes sociales

[ ] WhatsApp

[ ] Correo

[ ] Impuestos

[ ] Moneda

[ ] Usuarios

[ ] Roles

===============================================================================
REGLAS DEL MVP
===============================================================================

Todo documento debe conservar historial.

Toda operación importante debe registrar:

Fecha

Hora

Usuario

Evento

Descripción

Toda información importante debe poder exportarse.

Todo documento debe poder convertirse en PDF.

Toda acción importante debe poder enviarse por WhatsApp o correo.

===============================================================================
CRITERIOS DE ÉXITO
===============================================================================

El MVP se considera terminado cuando un negocio pueda:

✓ Registrar clientes.

✓ Consultar inventario.

✓ Crear presupuestos.

✓ Enviar presupuestos.

✓ Convertir presupuestos en ventas.

✓ Administrar reparaciones.

✓ Consultar reportes básicos.

Todo ello mediante conversación natural.