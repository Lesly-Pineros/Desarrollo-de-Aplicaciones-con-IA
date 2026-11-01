# Tareas — piloto InvestiQ v0.1

El backlog está aprobado; las tareas se ejecutan después de esta fase y no implican que la app ya esté implementada.

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-001 | Sincronizar catálogo de 20 instrumentos y validar cobertura/normalización | REQ-002, REQ-006, REQ-007 | Catálogo comparte `INSTRUMENTS`; suite existente Fase 2 | Implementado; validación focal pendiente |
| TASK-002 | Implementar `market_quote`, proveedor opcional, caché y fallback histórico | REQ-001, REQ-003 | `test_phase3_providers.py` prueba fallback histórico; Twelve Data live requiere key opcional | Implementado; local verificado |
| TASK-003 | Implementar `news` Marketaux y `sec_docs` EDGAR con caché/rate limit | REQ-001, REQ-003, REQ-004 | `test_phase3_providers.py` no-red sin credenciales; prueba SEC EDGAR live pasa | Implementado; SEC live verificado |
| TASK-004 | Crear glosario determinista y nodo Educador | REQ-005, REQ-010 | Tests de respuesta educativa y golden de intención en `test_phase3_orchestration.py` | Implementado; offline verificado |
| TASK-005 | Integrar `instr_features`, `volatility_bucket` y `similar_instruments` del artefacto Fase 2 | REQ-006, REQ-007 | Reutiliza herramientas/artefactos Fase 2; cobertura directa de rutas parcial | Implementado; validación parcial |
| TASK-006 | Implementar preferencias y score determinista de comparación | REQ-008 | `compare_instruments` y UI implementados; faltan casos unitarios del score | Implementado; validación parcial |
| TASK-007 | Implementar estado Pydantic y router Python con fallback de reglas | REQ-009, REQ-014 | 15 casos golden offline en `test_phase3_orchestration.py` | Implementado; 15/15 intenciones |
| TASK-008 | Añadir guardrails comunes de citas, disclaimer, contenido no confiable y validación LLM | REQ-001, REQ-004, REQ-005, REQ-007, REQ-010, REQ-014 | Disclaimer y rechazo de cita/cifra inventada probados; eval amplia de inyección pendiente | Implementado; validación parcial |
| TASK-009 | Crear UI Streamlit que llama orquestación en el mismo proceso | REQ-001, REQ-002, REQ-005, REQ-006, REQ-007, REQ-008, REQ-010 | `AppTest` smoke sin excepción; flujo end-to-end NIM pendiente | Implementado; smoke verificado |
| TASK-010 | Añadir auth Argon2, configuración de secretos/contacto SEC, cuotas, logging y retención | REQ-003, REQ-004, REQ-011, REQ-012, REQ-013, REQ-014 | Auth/sesión hash, log sin query y purga 90d probados; cobertura de cuota parcial | Implementado; validación parcial |
| TASK-011 | Ejecutar suite golden ES y pruebas de integración con reporte mocked/live | REQ-001, REQ-003, REQ-004, REQ-009, REQ-010, REQ-013, REQ-014 | 15/15 intenciones offline; SEC live pasa; yfinance live pasa; NIM pendiente de rotar clave y verificar | Parcial; aceptación global pendiente |

## Trazabilidad

| REQ | TASK(s) | Evidencia de verificación esperada |
|---|---|---|
| REQ-001 | TASK-002, TASK-003, TASK-008, TASK-009, TASK-011 | Fuentes, variación determinista, degradación y eval golden |
| REQ-002 | TASK-001, TASK-009 | Catálogo exacto y prueba de símbolo no cubierto |
| REQ-003 | TASK-002, TASK-003, TASK-010, TASK-011 | Mocks de fallos/cuotas, TTL y aviso de retraso |
| REQ-004 | TASK-003, TASK-008, TASK-011 | Test SEC live, enlace/fecha y rate limit |
| REQ-005 | TASK-004, TASK-008, TASK-009, TASK-011 | Fixtures del glosario y eval en español |
| REQ-006 | TASK-001, TASK-005, TASK-009 | Unit de cubetas deterministas |
| REQ-007 | TASK-001, TASK-005, TASK-008, TASK-009 | Unit de similitud/clúster y casos de artefacto ausente |
| REQ-008 | TASK-006, TASK-009 | Unit de score y preferencias faltantes |
| REQ-009 | TASK-007, TASK-011 | Unit de router/clarificación/fallback |
| REQ-010 | TASK-004, TASK-008, TASK-009, TASK-011 | Presencia de disclaimer, trazabilidad numérica y eval de inyección |
| REQ-011 | TASK-010 | Unit de Argon2, sesión y ausencia de secretos en logs |
| REQ-012 | TASK-010 | Unit de referencias de QueryLog/purga y revisión de retención |
| REQ-013 | TASK-010, TASK-011 | Reporte de cuotas, suite de eval y distinción mocked/live |
| REQ-014 | TASK-007, TASK-008, TASK-010, TASK-011 | Unit de timeout/reintentos, configuración y validación Pydantic |
