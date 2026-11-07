# Tareas — Educación sobre índices

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-001 | Catálogo educativo, alias y explicación del S&P 500 con fuente | REQ-001 | test_index_education.py: variantes, falsos positivos y sujeto frente a contexto | Completa |
| TASK-002 | Seguimiento, memoria y narración factual protegida | REQ-001, REQ-002 | 41 regresiones educativas, conversación restaurada y LLM simulado | Completa offline |
| TASK-003 | Entrada web única y retiro del frontend heredado | REQ-003 | pruebas de configuración y launcher; dependencias y scripts de consola solo locales web | Completa |
| TASK-004 | Documentación y validación de la ampliación | REQ-001, REQ-002, REQ-003 | 380 tests offline, 43 checks Chrome, diez specs y revisión independiente | Completa local |

## Trazabilidad

| REQ | TASK(s) | Evidencia prevista |
|---|---|---|
| REQ-001 | TASK-001, TASK-002, TASK-004 | Variantes SP500 y fuente oficial sin precios |
| REQ-002 | TASK-002, TASK-004 | Seguimiento, recuerdo y narración sin hechos añadidos |
| REQ-003 | TASK-003, TASK-004 | Web como única interfaz instalable |

## Evidencia histórica antes de retirar Streamlit — 2026-11-04

- `NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q` → **380 passed**. SQLite temporal, LLM simulado y HTTP real en localhost con permiso para puertos locales. En este entorno está instalado el extra legado y sus AppTest también se ejecutaron.
- `test_index_education.py` aporta **41 casos**: alias, límites de palabra, fuente oficial, aclaración/restauración, ejemplos, preferencias intactas y narración sin añadir cifras. La revisión independiente reprodujo y cerró el fallo de priorizar S&P 500 por orden del catálogo; nueve regresiones específicas de sujeto/contexto pasan.
- `node tools/check_web.mjs` → **43 checks** pasan en Chrome headless real. Incluye la pregunta «que es el sp500», el enlace HTTPS oficial de S&P, «un ejemplo» y ausencia de overflow en móvil; el resto del flujo web sigue funcionando. Base y perfil temporales, credenciales desactivadas, sin proveedores financieros. Diez capturas y reporte en `.impeccable/review/`, ignorados por Git; la nueva captura `mobile-sp500.png` se abrió para inspeccionar la respuesta y su referencia.
- Diez specs activas válidas; shell/JS y `git diff --check` sin errores. Las pruebas de integración con `RUN_LIVE_INTEGRATION=0` dan **4 skipped**. `tools/verify_agent.py` sin flags devuelve `not_run/live-opt-in-required` y no llama a NVIDIA.
- La fuente oficial se consultó por separado durante el desarrollo para redactar el contenido estático; esa lectura no se presenta como una integración live del agente. No se incluyeron cotización, composición actual, rentabilidad ni recomendaciones.

## Operación

`bash run_web.sh` abre la web de este checkout en `http://127.0.0.1:8000`. Las entradas instaladas anteriormente requieren reinstalar el proyecto para regenerar el script de consola `investiq-app`; no se afirma haber actualizado otras copias del repositorio ni su entorno Python. Fase 5 sin iniciar.

## Revisión de limpieza — 2026-11-07

- Se retiraron la interfaz heredada, su launcher, entry point, extra de instalación y pruebas específicas. La web HTML/CSS/JS y las tools Python locales son la única arquitectura vigente.
- Suite offline actual: **696 passed**. Check de Chrome local: **96 comprobaciones** con fixtures sintéticos, sin llamadas a proveedores financieros reales. Las 17 specs validan; `bash -n`, comprobaciones JavaScript y `git diff --check` pasan.
