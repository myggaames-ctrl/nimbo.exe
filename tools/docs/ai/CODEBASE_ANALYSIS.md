# NIMBO AI
# CODEBASE ANALYSIS
Versión: 1.0

===============================================================================
OBJETIVO
===============================================================================

Antes de implementar cualquier cambio, OpenClaw debe comprender completamente
el estado actual del proyecto.

Nunca debe asumir cómo funciona el código.

Debe analizarlo.

===============================================================================
REGLA PRINCIPAL
===============================================================================

Antes de escribir código, OpenClaw debe inspeccionar el proyecto.

Debe identificar:

• Arquitectura actual.
• Archivos relacionados.
• Dependencias.
• Código reutilizable.
• Posibles impactos.

===============================================================================
CHECKLIST DE ANÁLISIS
===============================================================================

Antes de modificar cualquier archivo responder:

□ ¿Existe ya una implementación similar?

□ ¿Existe un Service reutilizable?

□ ¿Existe un Tool reutilizable?

□ ¿Existe un Detector reutilizable?

□ ¿Existe un Response reutilizable?

□ ¿Existe un Evento reutilizable?

□ ¿Qué archivos dependen de este cambio?

□ ¿Qué pruebas podrían romperse?

===============================================================================
REUTILIZACIÓN
===============================================================================

La prioridad siempre será reutilizar código existente.

Nunca duplicar:

Funciones.

Consultas SQL.

Responses.

Eventos.

Lógica de negocio.

===============================================================================
ANÁLISIS DE IMPACTO
===============================================================================

Todo cambio debe indicar:

Archivos afectados.

Módulos afectados.

Dependencias afectadas.

Riesgo.

Compatibilidad.

===============================================================================
ANTES DE CREAR ARCHIVOS NUEVOS
===============================================================================

Responder:

¿Realmente es necesario?

¿Existe ya una carpeta adecuada?

¿Existe ya un módulo parecido?

¿Puedo extender uno existente?

===============================================================================
REGLA FINAL
===============================================================================

Primero comprender.

Después planificar.

Finalmente programar.