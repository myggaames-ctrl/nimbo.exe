# NIMBO AI
# BUSINESS RULES
Versión: 1.0

===============================================================================
OBJETIVO
===============================================================================

Este documento define las reglas del negocio.

No son reglas de programación.

Son reglas que Nimbo nunca debe romper.

Toda implementación debe respetar estas reglas.

===============================================================================
REGLAS GENERALES
===============================================================================

Nimbo siempre protegerá la información del negocio.

Nunca eliminará información importante sin autorización.

Toda acción importante debe quedar registrada.

Toda modificación importante debe poder auditarse.

===============================================================================
CLIENTES
===============================================================================

Un cliente nunca se elimina físicamente.

Los clientes podrán marcarse como:

Activo

Inactivo

Bloqueado

Todo historial debe conservarse.

===============================================================================
INVENTARIO
===============================================================================

La fuente oficial del inventario es Aronium.

Nimbo nunca modificará directamente el inventario de Aronium sin autorización.

Toda consulta de existencias debe realizarse utilizando Aronium.

===============================================================================
PRESUPUESTOS
===============================================================================

Un presupuesto representa una fotografía del momento en que fue creado.

Debe conservar:

Cliente.

Productos.

Cantidad.

Precio.

Costo.

Fecha.

Hora.

Usuario.

Notas.

Estado.

Aunque el precio cambie posteriormente en Aronium, el presupuesto conservará
el precio original.

===============================================================================
VENTAS
===============================================================================

Toda venta debe tener origen identificable.

Puede originarse desde:

Presupuesto.

Venta directa.

Toda venta debe registrar:

Fecha.

Hora.

Usuario.

Forma de pago.

Cliente.

Productos.

===============================================================================
SERVICIO TÉCNICO
===============================================================================

Cada equipo debe tener un número único.

Cada reparación conserva un historial completo.

Estados mínimos:

Recibido.

Diagnóstico.

Esperando aprobación.

En reparación.

Listo.

Entregado.

Cancelado.

Toda llamada al cliente debe quedar registrada.

Toda autorización debe quedar registrada.

===============================================================================
DOCUMENTOS
===============================================================================

Todo documento importante debe poder exportarse.

PDF.

Correo.

WhatsApp.

Impresión.

===============================================================================
USUARIOS
===============================================================================

Toda acción debe registrar el usuario responsable.

Toda modificación importante debe poder auditarse.

===============================================================================
AUTOMATIZACIONES
===============================================================================

Nimbo puede sugerir automatizaciones.

Nunca ejecutará acciones críticas sin autorización del usuario.

===============================================================================
ANÁLISIS
===============================================================================

Toda información histórica podrá utilizarse para:

Reportes.

Proyecciones.

Indicadores.

Estadísticas.

Recomendaciones.

===============================================================================
OBJETIVO FINAL
===============================================================================

Las reglas del negocio tienen prioridad sobre la implementación técnica.

Si existe un conflicto entre el código y estas reglas, deberán respetarse
las reglas del negocio.