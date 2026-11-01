# Tareas — Fase 2: datos y ML offline

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-201 | Configuración, modelos SQLModel y persistencia SQLite idempotente | REQ-201 | Unit: DB temporal, esquema, upsert repetido | Completa |
| TASK-202 | Canasta de 20 instrumentos e ingesta yfinance batch configurable | REQ-202 | Unit: proveedor fake, errores parciales; batch live 20 símbolos | Completa |
| TASK-203 | Cálculo de features alineadas, sector one-hot y persistencia | REQ-203 | Unit: fixture sintético y datos insuficientes | Completa |
| TASK-204 | Selección K-Means, similitud, silhouette y estabilidad ARI | REQ-204, REQ-206 | Unit: fixture sintético reproducible y batch live evaluado | Completa |
| TASK-205 | Terciles deterministas y consulta de instrumentos por bucket | REQ-205 | Unit: orden, empates, valores ausentes; 7/7/6 en batch live | Completa |
| TASK-206 | CLI offline, versionado de joblib/manifiesto e integración del pipeline | REQ-202, REQ-204, REQ-206 | Unit: pipeline completo offline y artefacto live versionado | Completa |

## Trazabilidad

| REQ | TASK(s) | Evidencia de verificación esperada |
|---|---|---|
| REQ-201 | TASK-201 | `tests/unit/test_database.py`, SQLite temporal |
| REQ-202 | TASK-202, TASK-206 | `tests/unit/test_ingest.py`; integration marcada para API real |
| REQ-203 | TASK-203 | `tests/unit/test_features.py` |
| REQ-204 | TASK-204, TASK-206 | `tests/unit/test_similarity.py` |
| REQ-205 | TASK-205 | `tests/unit/test_volatility.py` |
| REQ-206 | TASK-204, TASK-206 | `tests/unit/test_pipeline.py`; artefactos aislados en `tmp_path` |

## Evidencia ejecutada

- `/private/tmp/investiq-phase2-venv/bin/python -m pytest -q`: 7 passed.
- `/private/tmp/investiq-phase2-venv/bin/investiq-data all --period 2y`: 20/20 símbolos descargados, 501 cierres cada uno, sin errores por símbolo.
- Artefacto live: `ml/artifacts/kmeans-d797a2a74aac-s42.joblib` y manifiesto JSON; silhouette 0.4838 (≥0.25), ARI 0.8356 (≥0.6); aprobado.
- La integración real usó red yfinance; los unit tests usan datos sintéticos/proveedor simulado.
