# Tareas — Agente modular

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-001 | Extraer router, handlers, respuesta y query log de orquestación | REQ-001, REQ-004 | test_query_modules.py y regresiones por ruta; handlers sin log/LLM | Completa; offline verificada |
| TASK-002 | Extraer comandos y transiciones de diálogo; cliente único por turno | REQ-002, REQ-004 | test_dialogue_components.py, test_client_lifecycle.py y test_llm.py | Completa; offline verificada |
| TASK-003 | Aplicar correcciones de fluidez/procedencia justificadas | REQ-003 | Revisión independiente y 25 escenarios de test_learning_intents.py | Completa; offline verificada |
| TASK-004 | Actualizar docs y verificar comportamiento completo | REQ-001, REQ-002, REQ-003, REQ-004 | Regresión completa, AppTest, ocho specs, skill SDD y diff --check | Completa offline; live pendiente |

## Trazabilidad

| REQ | TASK(s) | Evidencia prevista |
|---|---|---|
| REQ-001 | TASK-001, TASK-004 | Tools separadas del LLM y trazabilidad sin duplicación |
| REQ-002 | TASK-002, TASK-004 | Transiciones de estado, memoria y cliente perezoso |
| REQ-003 | TASK-003, TASK-004 | Aprendizaje sin guardar preferencias y coincidencias ambiguas |
| REQ-004 | TASK-001, TASK-002, TASK-004 | Tests, documentación y límites live claros |

## Evidencia ejecutada (2026-11-04)

- `NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q` → **270 passed**. Incluye AppTest, SQLite temporal, memoria/restauración, las rutas y los nuevos componentes; no proveedores reales.
- `RUN_LIVE_INTEGRATION=0 NVIDIA_KEY_ROTATED=0 NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q tests/integration` → **4 skipped**. No cuenta como integración live.
- Ocho specs pasan tools/validate_spec.py; `git diff --check` y `bash -n run_streamlit.sh` sin errores.
- El validador local quick_validate.py de skill-creator devuelve **Skill is valid!** para `.codex/skills/sdd-feature`. Verifica formato, no demuestra por sí solo la calidad de una skill.
- Revisión independiente usando sdd-feature encontró los tres defectos descritos y sus regresiones pasan. El constructor NIM fallido se invoca una vez por turno y su error no expone la credencial ficticia del test.
- `tools/verify_agent.py` sin flags devuelve **not_run/live-opt-in-required**; no se contactó NIM.
- `.agents/skills/investiq-agent-review` no existe: su creación fue rechazada. La exclusión exacta en Git quedó preparada; no se declara disponible una skill nueva.
- Advertencias conocidas: deprecación LangSmith/Python 3.14 y detección de núcleos físicos de joblib.
