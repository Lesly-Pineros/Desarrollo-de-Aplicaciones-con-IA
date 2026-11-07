# Tareas — Fase 4: hardening y MCP SEC

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-401 | Crear harness de evaluación offline ampliado con disclaimer/guardrails | REQ-401 | `.venv/bin/python -m pytest -q tests/unit/test_phase4_eval.py` | Completa |
| TASK-402 | Implementar servidor MCP stdio para consulta SEC existente | REQ-402 | `.venv/bin/python -m pytest -q tests/unit/test_mcp_sec.py tests/integration/test_phase4_mcp_sec_live.py` | Completa |
| TASK-403 | Ejecutar suite/validator y actualizar trazabilidad y estado real | REQ-403 | `.venv/bin/python -m pytest -q` + `.venv/bin/python tools/validate_spec.py specs/fase4-hardening` | Completa |

## Evidencia ejecutada

- Suite offline: `41 passed`; incluye golden locales y ciclo stdio simulado. No usa proveedores reales.
- MCP SEC live: `1 passed`; `sec_filings(AAPL, limit=2)` consultó la fuente real y devolvió enlaces SEC. La prueba heredada SEC live también pasó.
- Integración histórica yfinance live: `RUN_LIVE_INTEGRATION=1 .venv/bin/python -m pytest -q tests/integration/test_yfinance_live.py` → `1 passed`.
- Validador: `Spec SDD válida: specs/fase4-hardening`.
- Compilación estática: `python -m compileall -q src tests` completó sin errores.
- ChatNVIDIA live y demo completo de Fase 3 no se consideran verificados en esta fase; ver estado en `PLAN.md`.

## Trazabilidad

| REQ | TASK(s) | Evidencia |
|---|---|---|
| REQ-401 | TASK-401 | Suite dorada offline y casos de guardrail |
| REQ-402 | TASK-402 | Prueba protocolo MCP con provider simulado; integración SEC live reportada aparte |
| REQ-403 | TASK-403 | Suite y validador SDD |
