# Tareas — Formación de inversión y trading

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-001 | Investigar fuentes y ampliar corpus de fondos, cripto e indicadores | REQ-001, REQ-002 | 32 documentos nuevos y 29 referencias; CLI valida 119 documentos en total; consultas con corpus real | Completa |
| TASK-002 | Ruta de actualidad sectorial, aclaración y memoria | REQ-003 | Pregunta exacta, seis respuestas cortas de mercado, memoria restaurada, clasificador erróneo y proveedores bloqueados | Completa local |
| TASK-003 | Comparación a largo plazo y mensajes con varias preguntas | REQ-002, REQ-003 | Tres variantes ETF/acciones, consulta mixta con HTML escapado y ausencia de rankings inventados | Completa local |
| TASK-004 | Documentación y verificación final | REQ-001, REQ-002, REQ-003, REQ-004 | 584 tests offline, 60 checks Chrome, CLI, doce specs, sintaxis, wheel y Git | Completa local; NIM pendiente |

## Trazabilidad

| REQ | TASK(s) | Evidencia prevista |
|---|---|---|
| REQ-001 | TASK-001, TASK-004 | Documentos revisados y recuperación real |
| REQ-002 | TASK-001, TASK-003, TASK-004 | ETF/acciones con condiciones y límites |
| REQ-003 | TASK-002, TASK-003, TASK-004 | Actualidad sin simular datos |
| REQ-004 | TASK-004 | Comandos y evidencia honesta |

## Evidencia ejecutada — 2026-11-04

- `.venv/bin/python -m investiq.knowledge validate` → **119 documentos, 16 categorías, 113 referencias**. La ampliación añade 32 documentos; las 20 fichas del catálogo siguen incluidas. [Fuentes revisadas](../../docs/trading-sources.md).
- `NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q --tb=short` → **584 passed**. Biblioteca real, SQLite temporal, modelos simulados y servidor HTTP local; credenciales desactivadas. La ejecución con sandbox encontró bloqueo de puertos; la repetición autorizada con acceso a loopback pasó completa.
- `tests/unit/test_trading_education.py` → **46 passed**: definiciones, ejemplos con memoria, indicadores técnicos frente a fundamentales, ETF/acciones, mercado pendiente, clasificación errónea, preguntas mixtas y prohibición de fabricar datos. Los proveedores financieros se bloquean en el fixture.
- `node tools/check_web.mjs` → **60 comprobaciones** en Chrome real con base y perfil temporales. Los casos nuevos prueban criptomoneda, RSI, las dos preguntas en un mensaje y «Estados Unidos» como seguimiento. Sin llamadas financieras. Trece capturas en `.impeccable/review/`, excluidas de Git; se inspeccionó la captura móvil nueva, con compositor visible y sin desbordamiento.
- **Doce specs válidas**, `bash -n`, `node --check` y `git diff --check` sin errores. El wheel incluye cinco JSON, el módulo sectorial y los assets; se comprueba su coincidencia con los archivos de esta versión y su carga fuera del checkout.
- **Cuatro integraciones reales omitidas** con `RUN_LIVE_INTEGRATION=0`; `tools/verify_agent.py` sin flags → `not_run/live-opt-in-required`. No se contactó NVIDIA con claves reales ni se verificó un ranking sectorial en vivo.
- Advertencias conocidas: trece avisos de deprecación LangSmith con Python 3.14; no fallos de prueba.

## Límites conservados

El corpus no cubre cualquier pregunta posible y puede abstenerse. No consulta cotizaciones cripto ni calcula indicadores actuales. No se ha añadido un proveedor de sectores: preguntar mercado aclara el alcance, pero no habilita datos ausentes. Los indicadores no producen órdenes de trading y la comparación ETF/acciones no garantiza rentabilidad. La investigación web de fuentes durante desarrollo no constituye una integración live del agente. La generación y el tono del modelo NVIDIA real siguen pendientes; fase 5 sin iniciar.
