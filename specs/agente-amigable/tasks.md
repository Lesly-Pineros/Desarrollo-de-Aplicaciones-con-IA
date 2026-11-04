# Tareas — Agente amigable

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-001 | Guía de tono cargada y narración con bloque factual protegido | REQ-001, REQ-004 | tests/unit/test_response_style.py y test_llm.py: modelos simulados, evidencia inmutable y ataques | Completa; offline verificada |
| TASK-002 | Memoria estructurada, retención y controles de usuario | REQ-002, REQ-004 | tests/unit/test_memory.py y test_memory_dialogue.py: SQLite existente/temporal y AppTest | Completa; offline verificada |
| TASK-003 | Propuestas semánticas de preferencias con evidencia validada | REQ-003, REQ-004 | tests/unit/test_understanding.py y test_semantic_dialogue.py: modelos simulados y parches atómicos | Completa; offline verificada |
| TASK-004 | Diagnóstico seguro, eval multitur y comando opt-in live | REQ-001, REQ-002, REQ-003, REQ-004 | tests/unit/test_verify_agent.py, regresión y validador SDD; tools/verify_agent.py opt-in | Offline completa; live pendiente |

## Trazabilidad

| REQ | TASK(s) | Verificación prevista |
|---|---|---|
| REQ-001 | TASK-001, TASK-004 | Narración validada y eval de conversaciones completas |
| REQ-002 | TASK-002, TASK-004 | Reinicio/restauración, borrado y no persistir historial/secretos |
| REQ-003 | TASK-003, TASK-004 | Evidencia literal, dominio y no inferir preferencias |
| REQ-004 | TASK-001, TASK-002, TASK-003, TASK-004 | Categorías seguras, regresión offline y estado live explícito |

## Evidencia ejecutada (2026-11-04)

- `NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q` → **189 passed**, sin proveedores reales.
- Validadores SDD de piloto, conversacion-preferencias y agente-amigable pasan; `git diff --check` sin errores.
- `.venv/bin/python tools/verify_agent.py` → `status=not_run`, `reason=live-opt-in-required`, cero turnos y sin red.
- Modelos simulados verifican numerales/tickers/citas extra rechazados, bloque factual exacto, diagnósticos seguros, preferencias con evidencia literal y reanudación de diálogos.
- AppTest y SQLite temporal verifican memoria entre sesiones, desactivación, borrado de pantalla/contexto y conservación de preferencias.
- Advertencias conocidas de dependencias: deprecación LangSmith/Python 3.14 y detección de núcleos físicos de joblib.

## Validación pendiente en el entorno conectado

Tras sustituir la clave previamente expuesta: `.venv/bin/python tools/verify_agent.py --live --key-rotated`.
El flag confirma la rotación por parte de quien ejecuta; no rota la clave. El informe diferencia passed/failed/not_run y no imprime claves, conversaciones ni errores originales. Esta prueba verifica clasificación y dos turnos educativos; la naturalidad global requiere además revisar conversaciones reales con el modelo.
