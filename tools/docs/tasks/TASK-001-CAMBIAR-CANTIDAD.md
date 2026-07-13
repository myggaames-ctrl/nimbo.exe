# TASK-001
# CAMBIAR CANTIDAD DE UN PRODUCTO EN UN PRESUPUESTO

===============================================================================
ESTADO
===============================================================================

Pendiente

===============================================================================
PRIORIDAD
===============================================================================

Alta

===============================================================================
OBJETIVO
===============================================================================

Permitir que el usuario cambie la cantidad de un producto que ya fue agregado
al presupuesto activo.

===============================================================================
CONTEXTO
===============================================================================

Actualmente Nimbo permite:

✓ Crear clientes

✓ Buscar clientes

✓ Crear presupuestos

✓ Agregar productos

✓ Mostrar presupuestos

El siguiente paso es permitir modificar la cantidad de un producto.

===============================================================================
EJEMPLOS DE COMANDOS
===============================================================================

poner 3 cuchillas

cantidad 5

cambiar cantidad a 4

quiero 2 cuchillas

agrega 3 más

===============================================================================
COMPORTAMIENTO ESPERADO
===============================================================================

1.

Obtener el presupuesto activo desde Workspace.

2.

Buscar el producto correspondiente.

3.

Actualizar la cantidad.

4.

Recalcular el subtotal.

5.

Recalcular el total del presupuesto.

6.

Actualizar UpdatedAt.

7.

Emitir evento:

budget.quantity_updated

8.

Responder al usuario.

===============================================================================
RESULTADO ESPERADO
===============================================================================

✅ Cantidad actualizada.

Producto:

Cuchilla Oster Original

Cantidad:

3

Precio:

Q91.30

Subtotal:

Q273.90

===============================================================================
ARCHIVOS QUE PROBABLEMENTE SE MODIFICARÁN
===============================================================================

budget_detector.py

budget_tool.py

budget_service.py

responses.py

===============================================================================
NO DEBE MODIFICAR
===============================================================================

Arquitectura

ActionEngine

Workspace

EventBus

InventoryService

===============================================================================
CRITERIOS DE ACEPTACIÓN
===============================================================================

Debe funcionar con un presupuesto activo.

Debe recalcular el subtotal.

Debe recalcular el total.

No debe crear registros duplicados.

Debe reutilizar código existente.

Debe seguir DEVELOPER_GUIDE.md.

===============================================================================
CASOS DE PRUEBA
===============================================================================

crear presupuesto para Pedro

agregar cuchilla

poner 3 cuchillas

mostrar presupuesto

Resultado esperado:

Cantidad: 3

Subtotal: Q273.90

Total: Q273.90