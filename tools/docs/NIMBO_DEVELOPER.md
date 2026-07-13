# NIMBO AI
## Developer Guide

Version: MVP 0.1

---

# ¿Qué es Nimbo AI?

Nimbo AI es una plataforma de inteligencia empresarial.

Su objetivo es ayudar a pequeñas y medianas empresas a operar su negocio mediante Inteligencia Artificial.

Nimbo no es un chatbot.

Nimbo no es un ERP.

Nimbo es un asistente operativo inteligente capaz de comprender instrucciones en lenguaje natural y ejecutar acciones dentro del negocio.

Mi Cocina es únicamente el primer negocio donde Nimbo será implementado para validar su funcionamiento en un entorno real.

---

# Objetivo del proyecto

Crear un sistema que elimine procesos manuales y reduzca errores humanos.

Nimbo debe convertirse en el centro de operaciones del negocio.

Debe ayudar al usuario a ahorrar tiempo, automatizar tareas y tomar mejores decisiones.

---

# Objetivo del MVP

El MVP debe estar listo para operar un negocio real.

No necesita ser perfecto.

Debe funcionar correctamente.

Cada nueva función debe aportar valor inmediato al usuario.

---

# Filosofía

Funciona primero.

Optimiza después.

Embellece al final.

Nunca detener el desarrollo intentando alcanzar la perfección.

---

# Principios

Cada módulo debe resolver un problema real.

Cada módulo debe ser reutilizable.

Cada módulo debe poder utilizarse mediante lenguaje natural.

Toda funcionalidad importante debe exponerse mediante una API.

---

# Arquitectura General

Nimbo está dividido en módulos independientes.

Services

Contienen la lógica del negocio.

Tools

Ejecutan acciones concretas.

Routes

Exponen APIs.

Templates

Contienen únicamente la interfaz.

Core

Infraestructura interna.

OpenClaw

Amplía las capacidades del sistema.

---

# Reglas de desarrollo

Nunca escribir lógica del negocio dentro de app.py.

Nunca escribir consultas SQL desde la interfaz.

Toda lógica pertenece a Services.

Las rutas únicamente llaman Services.

El Dashboard consume APIs.

Toda nueva funcionalidad debe mantener la arquitectura existente.

---

# Estilo de código

Python

PEP8

4 espacios

Métodos pequeños

Clases simples

Responsabilidad única

Código fácil de leer.

---

# Visión

Nimbo AI será una plataforma utilizada por múltiples empresas.

Mi Cocina únicamente será el primer caso de uso real.

Todo desarrollo debe realizarse pensando en que cualquier empresa pueda utilizar el sistema en el futuro.