# NIMBO AI
# PROJECT STRUCTURE
Versión: 1.0

===============================================================================
OBJETIVO
===============================================================================

Este documento define la estructura oficial del proyecto Nimbo AI.

Ninguna IA ni desarrollador debe reorganizar esta estructura sin autorización.

Cada carpeta tiene una responsabilidad específica.

===============================================================================
ESTRUCTURA GENERAL
===============================================================================

Nimbo/

│

├── app/

├── core/

├── modules/

├── services/

├── tools/

├── integrations/

├── database/

├── config/

├── installer/

├── docs/

├── tests/

├── logs/

├── backups/

├── workspace/

└── scripts/

===============================================================================
APP
===============================================================================

Responsabilidad:

Contener todas las interfaces de usuario.

Ejemplos:

Dashboard Web

API

Frontend

Aplicación Desktop

Nunca almacenar lógica de negocio aquí.

===============================================================================
CORE
===============================================================================

Responsabilidad:

Motor principal de Nimbo.

Contiene:

Action Engine

Intent Detector

Workspace

Responses

EventBus

Reasoning Engine

Nunca colocar lógica específica de módulos aquí.

===============================================================================
MODULES
===============================================================================

Cada módulo empresarial vive aquí.

Ejemplos:

Clientes

Inventario

Presupuestos

Ventas

Reparaciones

Compras

Contabilidad

Cada módulo debe ser independiente.

===============================================================================
SERVICES
===============================================================================

Contienen toda la lógica del negocio.

Únicamente aquí debe existir acceso a SQLite.

===============================================================================
TOOLS
===============================================================================

Coordinan las acciones entre el usuario y los Services.

Nunca contienen SQL.

===============================================================================
INTEGRATIONS
===============================================================================

Toda integración externa vive aquí.

Ejemplos:

OpenClaw

Aronium

Ollama

Gemini

WhatsApp

Correo

PDF

Ninguna integración debe mezclarse con el Core.

===============================================================================
DATABASE
===============================================================================

Contiene:

Base de datos.

Migraciones.

Backups temporales.

Nunca almacenar lógica aquí.

===============================================================================
CONFIG
===============================================================================

Configuración centralizada.

Variables de entorno.

Constantes.

Rutas.

Configuraciones del sistema.

===============================================================================
INSTALLER
===============================================================================

Responsable de instalar Nimbo desde cero.

Debe preparar completamente el entorno.

===============================================================================
DOCS
===============================================================================

Toda documentación oficial.

Incluye:

Arquitectura.

AI.

Tasks.

Templates.

Sprints.

Usuario.

===============================================================================
TESTS
===============================================================================

Pruebas automáticas.

Toda nueva funcionalidad debe tener pruebas.

===============================================================================
LOGS
===============================================================================

Registros del sistema.

Errores.

Eventos.

Auditoría.

===============================================================================
BACKUPS
===============================================================================

Respaldos automáticos.

Base de datos.

Configuración.

Documentos.

===============================================================================
WORKSPACE
===============================================================================

Información temporal del usuario.

Nunca almacenar información permanente.

===============================================================================
SCRIPTS
===============================================================================

Herramientas de mantenimiento.

Actualizaciones.

Migraciones.

Utilidades.

===============================================================================
REGLA FINAL
===============================================================================

Antes de crear un archivo nuevo OpenClaw debe preguntarse:

¿En qué carpeta pertenece realmente?

Si existe una carpeta especializada, debe utilizarla.

Nunca colocar archivos en ubicaciones incorrectas.