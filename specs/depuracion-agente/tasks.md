# Tareas — Depuración del agente

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-001 | Compartir control de procedencia y normalización entre parsers | REQ-001 | test_preference_provenance.py: preguntas/citas/terceros sin mutación | Completa; offline verificada |
| TASK-002 | Corregir nueva comparación, prioridad educativa y beta contextual | REQ-002 | test_dialogue_repairs.py: tools simuladas y restauración de memoria | Completa; offline verificada |
| TASK-003 | Cerrar prosa factual externa y adaptar prompt/catálogo | REQ-003 | test_response_style.py: afirmaciones sin cifras rechazadas y conectores válidos | Completa; offline verificada |
| TASK-004 | Unificar configuración de CLI y prioridad del Python del lanzador | REQ-004 | test_runtime_configuration.py: SQLite/.env y shell desde otro cwd | Completa; offline verificada |
| TASK-005 | README, plan, documentos coherentes y exclusión exacta local | REQ-005 | Comandos, siete specs y git check-ignore; instalación externa pendiente explícita | Completa; descarga pendiente |
| TASK-006 | Ejecutar regresión y reportar offline/live/instalación | REQ-001, REQ-002, REQ-003, REQ-004, REQ-005 | pytest offline, AppTest, SDD y diff --check | Completa offline; live pendiente |

## Trazabilidad

| REQ | TASK(s) | Evidencia prevista |
|---|---|---|
| REQ-001 | TASK-001, TASK-006 | No persistir preguntas ni preferencias ajenas |
| REQ-002 | TASK-002, TASK-006 | Continuidad correcta y campos pendientes restaurables |
| REQ-003 | TASK-003, TASK-006 | Bloque factual protegido y conectores permitidos |
| REQ-004 | TASK-004, TASK-006 | App/CLI misma BD y launcher portable |
| REQ-005 | TASK-005, TASK-006 | README reproducible e instalación externa pendiente explícita |

## Evidencia ejecutada (2026-11-04)

- Regresión: `NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q` → **223 passed**. Los tests unitarios aíslan además credenciales por fixture; usan SQLite temporal y herramientas/modelos simulados.
- Integraciones sin activación: `RUN_LIVE_INTEGRATION=0 NVIDIA_KEY_ROTATED=0 NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q tests/integration` → **4 skipped**, cero llamadas reales. No cuenta como integración verificada.
- Los siete directorios de specs activos pasan `tools/validate_spec.py`. `git diff --check` y `bash -n run_streamlit.sh` pasan.
- CLI: `.venv/bin/python -m investiq.ml.pipeline --help` muestra ingest/train/all. Pruebas simulan train con la misma BD que Settings y verifican precedencia del entorno.
- `.venv/bin/python tools/verify_agent.py` → `not_run/live-opt-in-required`; no se usaron credenciales ni red.
- `git check-ignore -v --no-index .agents/skills/skill-creator/SKILL.md` confirma la exclusión exacta. La skill SDD y las specs no están ignoradas. La ruta de instalación externa no existe.
- Advertencias conocidas de dependencias: deprecación LangSmith/Python 3.14 y detección de núcleos físicos de joblib.

## Pendientes externos

El comando de descarga con skill-installer fue rechazado por el usuario antes de crear el proceso. No se reintentó por otra herramienta ni se creó una instalación ficticia. La autorización para continuar localmente no sustituye ese permiso de red.

La aceptación live NIM requiere el entorno con internet y la clave rotada. Los comandos están en README; ningún resultado offline se presenta como live.
