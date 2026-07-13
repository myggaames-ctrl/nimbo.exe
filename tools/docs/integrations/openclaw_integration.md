## OpenClaw Event Handling y Adaptación del AI Bridge

Este documento describe la integración de Nimbo con OpenClaw, detallando la arquitectura de comunicación actual, el propósito del AI Bridge, el manejo de eventos y las adaptaciones realizadas para mantener la compatibilidad con las versiones recientes de OpenClaw.

## Propósito del AI Bridge

El AI Bridge actúa como un componente de orquestación en la arquitectura de Nimbo. Su propósito principal es facilitar la comunicación entre los componentes de IA de Nimbo y las herramientas o servicios externos, como OpenClaw. En la etapa actual, el AI Bridge se integra dentro de la aplicación Flask principal y trabaja en conjunto con el Task Planner y el Context Engine para dirigir las interacciones.

## Arquitectura de Comunicación Actual

La comunicación entre el Dashboard, el backend Flask de Nimbo y OpenClaw sigue el siguiente flujo:

1.  **Dashboard (Frontend):** El usuario interactúa aquí, enviando mensajes.
2.  **Nimbo Flask Backend (`app.py`):** Recibe el mensaje del usuario y lo procesa.
    *   El `ActionEngine` (dentro del backend) intenta resolver la acción usando herramientas disponibles.
    *   Si ninguna herramienta aplica, el mensaje se envía a OpenClaw a través del puente de Python.
3.  **Python Bridge (`openclaw_bridge.py`):** Ejecuta el script de Node.js (`openclaw_bridge.js`) que maneja la comunicación con OpenClaw Gateway.
4.  **JavaScript Bridge (`openclaw_bridge.js`):** Recibe la respuesta de OpenClaw Gateway, maneja eventos de chat (streaming y final), y expone la respuesta.
5.  **OpenClaw Gateway:** Recibe la solicitud y la enruta al sistema OpenClaw (modelo de IA, etc.).
6.  **OpenClaw:** Procesa la solicitud y envía la respuesta de vuelta a través del flujo inverso.

## Estructura de Eventos de OpenClaw 2026.6.8

Con la versión OpenClaw 2026.6.8, la estructura de los eventos finales de chat ha sido actualizada para mejorar el manejo de respuestas en streaming y la estandarización.

### Estructura del Objeto Evento

Los eventos desde el gateway de OpenClaw siguen este formato:

```javascript
{
  event: string,   // Tipo de evento (ej. "chat")
  payload: object  // Datos asociados al evento
}
```

### Estructura del Payload del Evento de Chat

El `payload` para eventos de tipo `"chat"` se adapta a los siguientes campos:

*   `payload.state` (string):
    *   `"delta"`: Para partes de respuesta en streaming. El texto se acumula en `payload.deltaText`.
    *   `"final"`: Indica la respuesta completa.
*   `payload.deltaText` (string, opcional): Texto recibido en streaming.
*   `payload.message` (object, opcional): Contiene el contenido final del mensaje cuando `payload.state` es `"final"`.
    *   `payload.message.content` (Array<object>): Array de objetos, cada uno con una propiedad `text`, que componen el mensaje final.

## Motivo del Cambio y Estrategia de Compatibilidad

*   **Motivo del Cambio:** La evolución de `payload.message.text` a `payload.message.content[].text` permite un manejo más granular y estructurado de las respuestas, especialmente para contenido en streaming o formatos complejos. Esto también facilita la implementación de mecanismos de streaming más efectivos.
*   **Estrategia de Compatibilidad:** El script `openclaw_bridge.js` (JavaScript Bridge) ha sido adaptado para manejar ambas posibilidades:
    *   Si `payload.state` es `"delta"`, el texto se acumula en `response` usando `payload.deltaText`.
    *   Si `payload.state` es `"final"`, y `payload.message.content` es un array, el script itera sobre este array y concatena `part.text` para reconstruir la respuesta completa.
    *   Esta estrategia asegura que el sistema reciba y muestre la respuesta completa correctamente, independientemente de si llega en un solo bloque o en fragmentos de streaming.

## Arquitectura Prevista (Roadmap)

Los siguientes componentes de IA para Nimbo están planificados para desarrollarse en futuras fases y se integrarán en la arquitectura:

*   **AI Core:** Un conjunto de servicios modulares que incluirán:
    *   **Task Planner:** Para analizar solicitudes y planificar acciones.
    *   **Context Engine:** Para construir el contexto de IA.
    *   **Workspace Memory:** Para gestionar el estado temporal.
    *   **Knowledge Hub:** Para almacenar conocimiento permanente.
    *   **AI Bridge:** Para orquestar la interacción entre componentes y herramientas.
*   **Provider Manager:** Para gestionar diferentes modelos de IA.
*   **Prompt Builder:** Para optimizar prompts para modelos de IA.

Estos componentes se integrarán dentro del paquete `services/knowledge/` y se gestionarán a través de la fachada `KnowledgeService`, evolucionando la arquitectura actual de manera incremental.

## Recomendaciones para Futuras Actualizaciones de OpenClaw

*   Monitorear cambios en la estructura de eventos y payloads.
*   Adaptar el manejo de errores en los puentes de comunicación.
*   Mantener esta documentación actualizada.
*   Implementar pruebas automatizadas para la integración con OpenClaw que validen el manejo de diferentes tipos de eventos y estados de respuesta.
