# Tareas — Profesor RAG

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-001 | Investigar y redactar biblioteca educativa con cobertura y fuentes oficiales | REQ-001, REQ-004 | 87 documentos, 13 categorías, 84 referencias; CLI y 31 tests de cobertura | Completa |
| TASK-002 | Modelos, recuperación local y CLI de biblioteca extensible | REQ-002 | 45 pruebas de recuperación: relevancia, abstención, orden, deícticos y JSON añadido sin código | Completa |
| TASK-003 | Generación educativa y validación de evidencia/fallback | REQ-003 | 52 pruebas del tutor con LLM simulado, citas/spans/cifras, inyección, consejo y fallos | Completa offline |
| TASK-004 | Integrar profesor en rutas, diálogo, memoria e instrumentos | REQ-002, REQ-003, REQ-004 | test_teacher_rag.py y regresión de 538 tests; preguntas y seguimientos reales en Chrome | Completa local |
| TASK-005 | Documentación, empaquetado y validación final | REQ-001, REQ-002, REQ-003, REQ-004, REQ-005 | CLI, 53 checks Chrome, wheel con biblioteca, once specs y Git | Completa local; NIM pendiente |

## Trazabilidad

| REQ | TASK(s) | Evidencia prevista |
|---|---|---|
| REQ-001 | TASK-001, TASK-005 | Biblioteca revisada y fuentes con fecha |
| REQ-002 | TASK-002, TASK-004, TASK-005 | Recuperación real sobre contenido local |
| REQ-003 | TASK-003, TASK-004, TASK-005 | Generación apoyada en pasajes y fallback |
| REQ-004 | TASK-001, TASK-004, TASK-005 | Profesor, memoria y límites de contexto |
| REQ-005 | TASK-005 | Comandos y evidencia reproducible sin NIM real |

## Evidencia ejecutada — 2026-11-04

- `NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q --tb=short` → **538 passed**. Incluye corpus real local, proveedor simulado, SQLite temporal y HTTP real de loopback con permiso para puertos locales; ninguna llamada a proveedores financieros o NVIDIA.
- La investigación editorial consultó dominios oficiales mediante navegación/búsqueda. El [inventario](../../docs/knowledge-sources.md) distingue esa revisión de una integración live del agente. La CLI valida 87 documentos / 13 categorías / 84 referencias; su validación estructural no acredita por sí sola vigencia ni verdad.
- `node tools/check_web.mjs` → **53 comprobaciones** en Chrome headless real, a 1440×900, 1024×768, 768×1024 y 390×844. Prueba acciones, comparación conceptual, brókers con fuentes, límites por país/tarifas, ETF apalancado y «¿y sus riesgos?», además de teclado, menú, memoria, errores y reintento. Base y perfil temporales, credenciales desactivadas.
- Doce capturas y `browser-report.json` quedan en `.impeccable/review/`, ignorados por Git. Se abrieron las capturas nuevas de profesor/brókers y móvil para inspeccionar texto, fuentes y encuadre.
- Las cuatro pruebas de integración con `RUN_LIVE_INTEGRATION=0` se omiten; `tools/verify_agent.py` sin flags devuelve `not_run/live-opt-in-required`. No se declara probado el tono ni la generación del modelo real.
- Once specs activas válidas; `bash -n`, `node --check` y `git diff --check` sin errores. Wheel construido e inspeccionado con los cuatro JSON de la biblioteca, módulos de búsqueda/tutor y assets web actuales.
- Advertencias conocidas: deprecación LangSmith/Python 3.14; no fallos de prueba.
- Tras precisar las cautelas sobre ETF apalancados con el boletín oficial, se repitieron los cuatro módulos afectados: **153 passed**; Chrome conservó **53 checks** y se reconstruyó el wheel con los JSON actuales.

## Revisión y límites

La revisión independiente encontró y corrigió selección por tema incidental, pérdida de contexto en riesgos y consultas de brókers, confusión entre SPY y su índice, y repetición de «más detalle». Las regresiones mantienen las rutas de cotización, similitud y comparación financiera, y las preferencias explícitas.

La recuperación es léxica/TF-IDF, no un buscador neuronal universal; puede abstenerse ante expresiones o temas sin respaldo. Las comprobaciones de generación son conservadoras y no garantizan implicación semántica. La biblioteca tiene fecha editorial y no confirma datos actuales de mercado, impuestos ni intermediarios. La memoria personal permanece independiente. Fase 5 sin iniciar.

La revisión posterior [continuidad-profesor](../continuidad-profesor/tasks.md) conserva esta evidencia histórica y registra las correcciones de aclaración, interpretación, ayuda contextual, instrumentos y nivel básico. Su verificación actual es de 627 pruebas offline y 75 comprobaciones en Chrome; NVIDIA real sigue pendiente.
