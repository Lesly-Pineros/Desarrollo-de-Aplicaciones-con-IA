# Tareas — Logs operativos de InvestiQ

| TASK | Descripción | REQ | Verificación |
|---|---|---|---|
| TASK-001 | Crear configuración, nivel por entorno, contexto de request y helpers seguros de etapa/error | REQ-001, REQ-003 | inspección de salida de consola: formato, nivel y ausencia de mensajes/valores de excepción |
| TASK-002 | Instrumentar arranque, API local, servicio de chat, diálogo, routing, orquestación y handlers | REQ-002, REQ-003 | recorrido manual con consultas educativas y de símbolo; correlación por request ID |
| TASK-003 | Instrumentar LLM, proveedores, degradaciones y comandos MCP/ML | REQ-002, REQ-004 | inspección manual de modo local, proveedor configurado y fallback; sin servicios reales necesarios |
| TASK-004 | Documentar configuración, eventos y límites de privacidad en README y progreso | REQ-001, REQ-003, REQ-004 | revisión de documentación contra los nombres/campos que realmente registra el código |

## Trazabilidad

| REQ | TASK(s) | Evidencia de verificación esperada |
|---|---|---|
| REQ-001 | TASK-001, TASK-004 | inicio de cada entry point con nivel configurable |
| REQ-002 | TASK-002, TASK-003 | etapas correlacionadas desde API hasta respuesta/tool |
| REQ-003 | TASK-001, TASK-002 | excepción inesperada con ubicación interna y sin datos brutos |
| REQ-004 | TASK-003, TASK-004 | omisión, error recuperable y fallback identificables sin solicitud/respuesta externa |
