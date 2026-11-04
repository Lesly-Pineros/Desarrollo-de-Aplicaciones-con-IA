# Tareas — Conversación y preferencias en el chat

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-001 | Estado tipado, continuidad y preguntas contextuales en el motor | REQ-001, REQ-004 | Diálogos offline en tests/unit/test_conversation.py | Completa; offline verificada |
| TASK-002 | Preferencias por texto y comparación opcional sin ranking | REQ-002, REQ-004 | Persistencia, validación, comparador real local y tools simuladas en tests/unit/test_conversation.py | Completa; offline verificada |
| TASK-003 | Sidebar de ayuda/catálogo y chat con estado | REQ-003, REQ-001 | Smoke AppTest con SQLite temporal en tests/unit/test_chat_ui.py, sin proveedores | Completa; offline verificada |
| TASK-004 | Verificar regresión y documentar resultados reales | REQ-001, REQ-002, REQ-003, REQ-004 | pytest offline, tools/validate_spec.py y git diff --check | Completa; offline verificada |

## Trazabilidad

| REQ | TASK(s) | Evidencia prevista |
|---|---|---|
| REQ-001 | TASK-001, TASK-003, TASK-004 | Respuestas cortas reanudan consultas y estado sobrevive rerun |
| REQ-002 | TASK-002, TASK-004 | Preferencias explícitas y omisión sin puntaje inventado |
| REQ-003 | TASK-003, TASK-004 | Catálogo completo sin formulario lateral |
| REQ-004 | TASK-001, TASK-002, TASK-004 | Guardrails y suite offline; no integración live |

## Evidencia ejecutada (2026-11-04)

- Conversación e interfaz: **30 casos offline** en `tests/unit/test_conversation.py` y `tests/unit/test_chat_ui.py`, ejecutados dentro de la regresión. SQLite temporal y herramientas simuladas; comparador real local en los casos de puntaje, omisión y trazabilidad de fuentes.
- Regresión: `NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q` → **70 passed**. Credenciales deshabilitadas para impedir llamadas reales.
- Validador SDD: specs piloto y conversacion-preferencias válidas. `git diff --check` sin errores.
- Advertencias de dependencias: deprecaciones de LangSmith/Python 3.14 y detección de núcleos físicos de joblib; no fallos de prueba.
- No se verificó ChatNVIDIA ni otros servicios en vivo en esta feature.
