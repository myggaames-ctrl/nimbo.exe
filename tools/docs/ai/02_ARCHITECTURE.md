# NIMBO AI
# ARCHITECTURE
Version: 1.0

===============================================================================
OBJETIVO
===============================================================================

Este documento describe la arquitectura oficial de Nimbo AI.

Toda IA o desarrollador debe comprender esta arquitectura antes de modificar
el proyecto.

La arquitectura NO puede modificarse sin autorización.

===============================================================================
VISIÓN GENERAL
===============================================================================

Nimbo está construido mediante una arquitectura modular.

Cada módulo tiene responsabilidades claramente definidas.

Cada componente conoce únicamente aquello que necesita conocer.

La comunicación entre componentes sigue un flujo único.

===============================================================================
FLUJO GENERAL
===============================================================================

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

SQLite / Workspace

↓

Tool

↓

Responses

↓

Usuario

Este flujo nunca debe romperse.

===============================================================================
ESTRUCTURA DEL PROYECTO
===============================================================================

micocina-dashboard/

│

├── app.py

│

├── core/

│   ├── action_engine.py

│   ├── intent_detector.py

│   ├── workspace.py

│   ├── event_bus.py

│   ├── responses.py

│   └── detectors/

│

├── services/

│

├── tools/

│

├── database/

│

├── docs/

│

└── tests/

===============================================================================
CAPAS DEL SISTEMA
===============================================================================

CAPA 1

Interfaz

Responsable:

Comunicación con el usuario.

Archivos:

app.py

Frontend

API

-------------------------------------------------------------------------------

CAPA 2

Comprensión

Responsable:

Detectar intención.

Archivos:

core/detectors/

-------------------------------------------------------------------------------

CAPA 3

Coordinación

Responsable:

Seleccionar la herramienta correcta.

Archivos:

intent_detector.py

action_engine.py

-------------------------------------------------------------------------------

CAPA 4

Acciones

Responsable:

Coordinar operaciones.

Archivos:

tools/

-------------------------------------------------------------------------------

CAPA 5

Negocio

Responsable:

Implementar lógica empresarial.

Archivos:

services/

-------------------------------------------------------------------------------

CAPA 6

Persistencia

Responsable:

Guardar información.

SQLite

Workspace

-------------------------------------------------------------------------------

CAPA 7

Comunicación

Responsable:

Construir respuestas.

responses.py

===============================================================================
DEPENDENCIAS PERMITIDAS
===============================================================================

Detector

↓

Nada

-------------------------------------------------------------------------------

Action Engine

↓

Detector

Tool Registry

-------------------------------------------------------------------------------

Tool

↓

Workspace

Responses

Services

EventBus

-------------------------------------------------------------------------------

Service

↓

SQLite

Otros Services (solo cuando sea necesario)

-------------------------------------------------------------------------------

Responses

↓

Ninguna dependencia.

===============================================================================
DEPENDENCIAS PROHIBIDAS
===============================================================================

Detector

↓

SQLite

❌

-------------------------------------------------------------------------------

Detector

↓

Workspace

❌

-------------------------------------------------------------------------------

Tool

↓

SQLite

❌

-------------------------------------------------------------------------------

Responses

↓

SQLite

❌

-------------------------------------------------------------------------------

Responses

↓

Workspace

❌

-------------------------------------------------------------------------------

Service

↓

Responses

❌

===============================================================================
WORKSPACE
===============================================================================

El Workspace solamente almacena contexto temporal.

Ejemplos:

active_budget_id

active_customer_id

last_product

Nunca guardar información permanente.

===============================================================================
SQLITE
===============================================================================

SQLite solamente puede ser utilizado por Services.

Ningún otro componente debe escribir SQL.

===============================================================================
EVENT BUS
===============================================================================

Toda acción importante genera un evento.

Ejemplos:

budget.created

budget.item_added

budget.sent

sale.created

repair.started

repair.finished

===============================================================================
MÓDULOS OFICIALES
===============================================================================

Clientes

Inventario

Presupuestos

Ventas

Compras

Reparaciones

Reportes

Contabilidad

Usuarios

Configuración

Todos los módulos deben seguir exactamente esta arquitectura.

===============================================================================
CREACIÓN DE UN MÓDULO NUEVO
===============================================================================

Todo módulo nuevo debe contener como mínimo:

Detector

Tool

Service

Responses

Tests

Eventos

Documentación

===============================================================================
REGLA FINAL
===============================================================================

La arquitectura de Nimbo tiene prioridad sobre cualquier implementación.

Es preferible escribir más código respetando la arquitectura que escribir
menos código rompiéndola.