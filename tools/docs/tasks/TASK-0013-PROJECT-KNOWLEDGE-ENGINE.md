# TASK-0013
# PROJECT KNOWLEDGE ENGINE

Versión: 1.0

===============================================================================
OBJETIVO
===============================================================================

Construir el primer componente oficial de Nimbo Brain.

Este componente permitirá que cualquier modelo de IA utilizado por Nimbo
(OpenClaw, Ollama, Gemini, OpenAI u otros) reciba automáticamente el contexto
del proyecto antes de responder.

El usuario nunca deberá copiar manualmente la documentación en el chat.

===============================================================================
PROBLEMA ACTUAL
===============================================================================

Actualmente OpenClaw únicamente conoce el mensaje escrito por el usuario.

No conoce automáticamente:

- Arquitectura
- Reglas del negocio
- MVP
- Tasks
- Sprints
- Documentación
- Contexto del proyecto

Esto limita considerablemente su capacidad para desarrollar Nimbo.

===============================================================================
OBJETIVO FUNCIONAL
===============================================================================

Crear un motor de conocimiento que:

1. Descubra automáticamente toda la documentación.

2. Indexe los documentos.

3. Permita consultar documentos por categoría.

4. Construya el contexto adecuado según la tarea.

5. Envíe automáticamente dicho contexto al modelo de IA.

===============================================================================
ESTRUCTURA ESPERADA
===============================================================================

services/

knowledge/

document_loader.py

document_index.py

context_builder.py

knowledge_service.py

===============================================================================
FUNCIONALIDADES
===============================================================================

Document Loader

- Leer archivos .md

- Leer archivos .txt

- Descubrir documentos automáticamente

------------------------------------------------------------

Document Index

- Clasificar documentos

- Crear índice

- Buscar documentos

------------------------------------------------------------

Context Builder

Construir contexto según:

- Presupuestos

- Inventario

- Reparaciones

- Clientes

- Ventas

No cargar toda la documentación cuando no sea necesario.

------------------------------------------------------------

Knowledge Service

API única para acceder al conocimiento.

Ejemplo:

knowledge.load_context("budget")

===============================================================================
INTEGRACIÓN
===============================================================================

Este componente deberá integrarse posteriormente con:

OpenClaw

Ollama

Gemini

OpenAI

Nimbo Brain

===============================================================================
REGLAS
===============================================================================

No modificar funcionalidades existentes.

No romper el Dashboard.

No romper OpenClaw.

Mantener compatibilidad.

Reutilizar código siempre que sea posible.

===============================================================================
CRITERIOS DE ACEPTACIÓN
===============================================================================

Debe descubrir automáticamente los documentos.

Debe indexarlos.

Debe construir contexto.

Debe poder reutilizarse con cualquier modelo de IA.

Debe estar documentado.

===============================================================================
ENTREGA
===============================================================================

Antes de escribir código presentar:

- Arquitectura propuesta.

- Archivos a crear.

- Riesgos.

- Dependencias.

- Orden de implementación.

Esperar aprobación antes de programar.