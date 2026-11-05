# Tareas — Continuidad del profesor

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-001 | Interpretación educativa compartida y selección contextual de pasajes | REQ-001, REQ-002 | test_teacher_continuity.py: corpus real, contexto canónico y abstención sin sujeto | Completa offline |
| TASK-002 | Integrar continuidad tras lecciones e instrumentos y aclarar nivel básico | REQ-001, REQ-002, REQ-003 | Conversaciones con SQLite temporal, restauración de memoria, fuentes y proveedores bloqueados | Completa offline |
| TASK-003 | Verificar contexto entregado al generador simulado y conservar guardrails | REQ-001, REQ-002, REQ-003 | Generador simulado inspecciona pasajes y nivel; regresión completa conserva mercado, preferencias e inyección | Completa offline; NVIDIA real pendiente |
| TASK-004 | Ampliar recorrido Chrome y actualizar documentación y evidencia | REQ-001, REQ-002, REQ-003, REQ-004 | 627 pruebas offline, 75 checks Chrome, biblioteca, trece specs y git diff --check | Completa local |

## Trazabilidad

| REQ | TASK(s) | Evidencia de verificación esperada |
|---|---|---|
| REQ-001 | TASK-001, TASK-002, TASK-003, TASK-004 | Mismo tema y fuentes en aclaraciones, sin coincidencias incidentales |
| REQ-002 | TASK-001, TASK-002, TASK-003, TASK-004 | Sujeto nuevo y mercado prevalecen; abstención y guardrails |
| REQ-003 | TASK-002, TASK-003, TASK-004 | Fichas educativas tras instrumento y significado presente para principiantes |
| REQ-004 | TASK-004 | Evidencia actual y comandos, con NVIDIA real pendiente |

## Evidencia ejecutada — 2026-11-04

- Antes de modificar la implementación, se confirmaron **584 pruebas offline** y **60 comprobaciones en Chrome**. Los primeros intentos encontraron el bloqueo del sandbox para abrir puertos locales (570 pasan, 14 errores HTTP; Chrome no arranca). La repetición autorizada con acceso a loopback confirmó las cifras iniciales; no fue un fallo de la app.
- Regresión final: `NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q` → **627 passed**. Incluye **43 pruebas nuevas** en `tests/unit/test_teacher_continuity.py`, corpus local real y SQLite temporal. Se bloquean herramientas de cotización/noticias/filings en las nuevas conversaciones; los generadores usados son simulados.
- Casos cubiertos: ETF → aclaración → ejemplo → costes → Bitcoin → riesgos; RSI → interpretación → diversificación → importancia; AAPL → ejemplo → riesgos; definición y explicación en nivel principiante; ayuda de app sin contexto frente a lección activa; cambios de sujeto cubiertos/desconocidos; abstención sin crear memoria de un tema incidental. La simplificación de un turno no cambia el nivel persistido.
- `node tools/check_web.mjs` → **75 comprobaciones** en Chrome headless real. Base, servidor y perfil temporales; credenciales desactivadas y ninguna llamada a proveedores. Añade los seguimientos anteriores, sus fuentes y disclaimer, cambio de tema y nivel principiante. Se inspeccionó `mobile-contextual-lesson.png`: definición, ejemplo, fuente, disclaimer y compositor visibles, sin desbordamiento. Catorce capturas e informe en `.impeccable/review/`, ignorados por Git.
- `.venv/bin/python -m investiq.knowledge validate` → **119 documentos, 16 categorías y 113 referencias**, incluidas las 20 fichas. No se añadió contenido financiero ni se cambiaron fuentes en esta corrección; la validación comprueba estructura, no vigencia.
- **Trece specs válidas** con `tools/validate_spec.py`; `bash -n run_web.sh run_streamlit.sh`, `node --check tools/check_web.mjs` y `git diff --check` sin errores.
- `RUN_LIVE_INTEGRATION=0 NVIDIA_KEY_ROTATED=0 NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q tests/integration` → **4 skipped**. `tools/verify_agent.py` sin flags → `not_run/live-opt-in-required`, cero turnos. No se verificó NVIDIA real ni ranking sectorial actual.
- La regresión final registra trece avisos de deprecación de LangSmith/Python 3.14, sin fallos. Los cambios previos del workspace se conservaron; no se crearon commits ni se desplegó.

## Límites

El reconocimiento de seguimientos es acotado; no constituye comprensión universal del lenguaje. El respaldo offline utiliza ejemplos revisados y puede repetirlos; el corpus conserva sus límites de cobertura y actualidad. Los mocks comprueban el contexto entregado al generador y su validación, sin acreditar naturalidad de NVIDIA real. Las preferencias financieras siguen exigiendo declaración explícita. Fase 5 sin iniciar.
