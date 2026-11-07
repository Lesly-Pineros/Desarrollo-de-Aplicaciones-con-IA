# Requisitos — Fase 4: hardening y MCP SEC

- **Estado:** Aprobado para ejecución por solicitud del usuario.
- **Alcance:** fortalecer aceptación/evaluación de Fase 3 y exponer consultas de filings de la SEC mediante un servidor MCP stdio reutilizando el cliente existente.
- **Límites:** no extraer FastAPI (opcional en PLAN), no cambiar el motor Python plano y no declarar Fase 3 completamente aceptada mientras la integración ChatNVIDIA dependa de una clave pendiente de rotación.

### REQ-401 — Suite de evaluación del flujo y guardrails

**EARS:** Cuando se ejecute la suite de evaluación local, el sistema deberá verificar consultas doradas en español, disclaimer, fuentes y resistencia a instrucciones maliciosas recuperadas sin depender de red.

**Criterios de aceptación:**
1. Cubre al menos 15 consultas doradas, incluye routing y respuesta con disclaimer.
2. Una narración con cifras o citas desconocidas se rechaza; contenido externo se trata como dato.
3. El reporte distingue verificación offline/mock de integración live.

### REQ-402 — Servidor MCP de filings SEC

**EARS:** Cuando un cliente MCP solicite filings de un símbolo cubierto, el servidor deberá responder mediante la integración SEC existente y devolver formulario, fecha, URL y fuente verificables.

**Criterios de aceptación:**
1. Implementa inicialización MCP, listado y llamada de herramienta por transporte stdio.
2. La herramienta acepta símbolo y límite acotado; rechaza entradas fuera de cobertura y errores sin traceback/secretos.
3. Reutiliza `sec_docs`, sus límites, caché y `SEC_USER_AGENT`; el texto recuperado se devuelve como dato sin interpretarlo.
4. Pruebas unitarias usan HTTP simulado y el protocolo se prueba localmente sin red.

### REQ-403 — Trazabilidad de Fase 4

**EARS:** Cuando se cierre cada tarea de Fase 4, la spec deberá relacionar requisito, implementación y verificación ejecutada.

**Criterios de aceptación:** cada TASK referencia REQ y comando de verificación; el plan/progreso reporta resultados reales y límites de aceptación pendientes.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-03 | Spec creada antes de implementar Fase 4; alcance centrado en eval y MCP SEC. |
