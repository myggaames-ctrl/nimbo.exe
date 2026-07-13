# NIMBO AI
# DEVELOPER GUIDE
Version: 1.0

===============================================================================
OBJETIVO
===============================================================================

Este documento define las reglas oficiales para desarrollar Nimbo AI.

Toda IA, desarrollador o colaborador debe seguir estas reglas.

El objetivo NO es solamente escribir código.

El objetivo es construir un sistema estable, escalable y mantenible durante
muchos años.

Todas las decisiones deben favorecer la arquitectura antes que la velocidad.

===============================================================================
¿QUÉ ES NIMBO?
===============================================================================

Nimbo NO es un chatbot.

Nimbo NO es solamente un ERP.

Nimbo es un compañero de trabajo inteligente.

Debe ayudar a administrar una empresa mediante conversación natural.

Debe recordar contexto.

Debe automatizar procesos.

Debe reducir trabajo repetitivo.

Debe ayudar al usuario a tomar mejores decisiones.

Cada módulo nuevo debe respetar esta filosofía.

===============================================================================
ARQUITECTURA GENERAL
===============================================================================

Toda funcionalidad sigue este flujo.

Usuario

↓

Detector

↓

Intent

↓

Action Engine

↓

Tool

↓

Service

↓

Workspace / SQLite

↓

Responses

↓

Usuario

Nunca romper este flujo.

===============================================================================
RESPONSABILIDAD DE CADA COMPONENTE
===============================================================================

DETECTOR

Su única responsabilidad es detectar la intención.

Puede:

✓ interpretar texto

✓ devolver intent

No puede:

✗ consultar SQLite

✗ modificar datos

✗ acceder a APIs

✗ construir respuestas

Debe devolver únicamente:

{
    "intent": "...",
    "query": "..."
}

-------------------------------------------------------------------------------

ACTION ENGINE

Responsabilidad:

Conectar Detectores con Tools.

Nunca contiene lógica del negocio.

-------------------------------------------------------------------------------

TOOLS

Responsabilidad:

Coordinar el flujo.

Puede:

✓ llamar Services

✓ usar Workspace

✓ emitir eventos

✓ llamar Responses

No puede:

✗ escribir SQL

✗ construir consultas

✗ contener lógica compleja

✗ duplicar código existente

-------------------------------------------------------------------------------

SERVICES

Responsabilidad:

Implementar la lógica del negocio.

Puede:

✓ consultar SQLite

✓ modificar SQLite

✓ realizar cálculos

✓ validar datos

No puede:

✗ responder al usuario

✗ acceder al Workspace

✗ imprimir mensajes

-------------------------------------------------------------------------------

WORKSPACE

Responsabilidad:

Guardar contexto temporal.

Ejemplos:

active_budget_id

active_customer_id

last_product

Nunca guardar información permanente aquí.

===============================================================================
RESPONSES
===============================================================================

Toda respuesta visible al usuario debe construirse en:

core/responses.py

Nunca construir respuestas largas dentro de:

Tools

Services

Detectores

===============================================================================
EVENT BUS
===============================================================================

Toda acción importante debe emitir un evento.

Ejemplos:

budget.created

budget.item_added

budget.sent

sale.created

repair.started

repair.finished

customer.created

customer.deleted

Esto permitirá:

historial

estadísticas

automatizaciones

auditoría

===============================================================================
BASE DE DATOS
===============================================================================

SQLite solamente puede ser accedido desde Services.

Nunca desde Tools.

Nunca desde Detectores.

Toda modificación importante debe registrar:

CreatedAt

UpdatedAt

Cuando aplique también:

CreatedBy

UpdatedBy

===============================================================================
REUTILIZACIÓN
===============================================================================

Antes de crear cualquier función nueva preguntarse:

¿Ya existe?

¿Puedo reutilizarla?

¿Estoy duplicando código?

Si la respuesta es SI

Debe reutilizarse.

Nunca copiar código.

===============================================================================
ANTES DE CREAR UN ARCHIVO NUEVO
===============================================================================

Responder:

¿Existe uno parecido?

¿Puedo extenderlo?

¿Rompo la arquitectura?

¿Es realmente necesario?

===============================================================================
ANTES DE ESCRIBIR SQL
===============================================================================

Preguntarse:

¿Existe un Service?

↓

SI

↓

Usarlo.

↓

NO

↓

Crear uno nuevo.

===============================================================================
ANTES DE MODIFICAR LA BASE DE DATOS
===============================================================================

Preguntarse:

¿La modificación rompe compatibilidad?

¿Debe hacerse mediante migración?

¿Afecta otros módulos?

===============================================================================
PROHIBIDO
===============================================================================

Duplicar lógica.

Consultar SQLite desde Tools.

Modificar Workspace desde Services.

Construir respuestas fuera de responses.py.

Cambiar arquitectura sin autorización.

Eliminar módulos existentes.

Renombrar tablas sin autorización.

===============================================================================
CHECKLIST OBLIGATORIO
===============================================================================

Antes de finalizar cualquier tarea verificar:

[ ] Compila correctamente.

[ ] Sigue la arquitectura.

[ ] Reutiliza código existente.

[ ] No rompe compatibilidad.

[ ] Maneja errores.

[ ] Emite eventos cuando corresponde.

[ ] Usa responses.py.

[ ] Explica cómo probar la implementación.

===============================================================================
FILOSOFÍA FINAL
===============================================================================

Cada línea de código debe hacer que Nimbo sea:

más simple

más reutilizable

más mantenible

más inteligente

Nunca solamente más grande.

La calidad de la arquitectura siempre tiene prioridad sobre la velocidad de desarrollo.