# NIMBO AI
# CODING STANDARDS
Version: 1.0

===============================================================================
OBJETIVO
===============================================================================

Este documento define los estándares oficiales de programación de Nimbo AI.

Toda IA y todo desarrollador deben seguir estas reglas.

La prioridad es escribir código:

- claro
- mantenible
- reutilizable
- consistente
- fácil de probar

Nunca escribir código solamente para que funcione.

===============================================================================
FILOSOFÍA
===============================================================================

Cada archivo debe tener una única responsabilidad.

Cada función debe hacer una sola cosa.

Cada módulo debe ser independiente.

La simplicidad siempre tiene prioridad sobre la complejidad.

===============================================================================
NOMBRES
===============================================================================

Usar nombres claros.

Correcto

create_budget()

search_customer()

update_quantity()

Incorrecto

run()

test()

process()

data()

info()

tmp()

===============================================================================
FUNCIONES
===============================================================================

Cada función debe ser pequeña.

Idealmente menor a 50 líneas.

Si una función comienza a hacer varias tareas debe dividirse.

Cada función debe tener un objetivo claro.

===============================================================================
COMENTARIOS
===============================================================================

Usar siempre encabezados.

Ejemplo

# ==========================================
# CREAR PRESUPUESTO
# ==========================================

No escribir comentarios innecesarios.

Incorrecto

# suma uno

total += 1

Correcto

Explicar únicamente reglas del negocio o decisiones importantes.

===============================================================================
IMPORTS
===============================================================================

Todos los imports deben ir al inicio del archivo.

Agruparlos por tipo.

Primero librerías estándar.

Luego librerías del proyecto.

No importar módulos innecesarios.

===============================================================================
RESPUESTAS
===============================================================================

Todo texto visible para el usuario debe construirse mediante:

responses.py

Nunca construir respuestas grandes dentro de Tools o Services.

===============================================================================
ERRORES
===============================================================================

Toda operación importante debe manejar errores.

Nunca dejar que una excepción termine el programa.

Siempre devolver mensajes claros.

Registrar errores cuando sea posible.

===============================================================================
REUTILIZACIÓN
===============================================================================

Antes de crear una función nueva responder:

¿Ya existe?

¿Puedo reutilizarla?

¿Estoy duplicando código?

Si existe una función equivalente debe reutilizarse.

Nunca copiar y pegar lógica.

===============================================================================
SERVICES
===============================================================================

Toda consulta SQL pertenece únicamente a Services.

Los Services contienen la lógica del negocio.

No deben construir respuestas.

===============================================================================
TOOLS
===============================================================================

Los Tools coordinan.

No implementan lógica compleja.

No escriben SQL.

No duplican lógica.

===============================================================================
DETECTORES
===============================================================================

Los Detectores únicamente interpretan el mensaje.

No consultan bases de datos.

No modifican información.

No llaman APIs.

===============================================================================
WORKSPACE
===============================================================================

Guardar únicamente contexto temporal.

Ejemplos

active_budget_id

active_customer_name

last_product

Nunca usar Workspace como base de datos.

===============================================================================
EVENTOS
===============================================================================

Toda acción importante debe emitir un evento.

Ejemplos

budget.created

budget.item_added

budget.sent

repair.started

sale.completed

===============================================================================
BASE DE DATOS
===============================================================================

No modificar tablas existentes sin autorización.

Toda modificación importante debe realizarse mediante migraciones cuando el
proyecto esté en producción.

Nunca borrar información del usuario automáticamente.

===============================================================================
PRUEBAS
===============================================================================

Toda funcionalidad nueva debe incluir una explicación de cómo probarla.

Como mínimo indicar:

Comando de entrada.

Resultado esperado.

Posibles errores.

===============================================================================
ANTES DE ENTREGAR CÓDIGO
===============================================================================

Verificar:

[ ] Compila correctamente.

[ ] Sigue la arquitectura.

[ ] No rompe funcionalidades existentes.

[ ] Reutiliza código.

[ ] Maneja errores.

[ ] Usa responses.py.

[ ] Usa Services correctamente.

[ ] Emite eventos cuando corresponde.

[ ] La funcionalidad puede probarse fácilmente.

===============================================================================
REGLA FINAL
===============================================================================

La mejor solución no es la que utiliza menos líneas de código.

La mejor solución es la que otro desarrollador podrá entender y mantener
dentro de cinco años.