# Tareas — Web conversacional

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-001 | Servidor, servicio y sesiones web sobre answer_turn | REQ-002 | 41 tests web, incluido HTTP real en loopback y SQLite temporal, sin proveedores | Completa |
| TASK-002 | Interfaz web adaptable con catálogo, chat y memoria | REQ-001 | 38 checks Chrome y nueve capturas, con teclado, errores, fuentes y contraste | Completa |
| TASK-003 | Corregir definición de símbolos y aclaraciones conversacionales | REQ-003 | test_conversational_web_dialogue.py y regresión offline completa | Completa offline |
| TASK-004 | Lanzador, empaquetado, ADR, documentación y validación final | REQ-001, REQ-002, REQ-003, REQ-004 | 338 tests, nueve specs, shell/JS/Git, wheel y revisión independiente; NIM pendiente | Completa local |
| TASK-005 | Aplicar la nueva identidad visual, profesor robot y catálogo horizontal adaptable | REQ-001, REQ-005 | Nueve capturas Chrome y checks de desborde, contraste, foco y movimiento a 1440/1024/768/390 px; sin datos financieros ficticios | Completa local |
| TASK-006 | Unificar accesos iniciales y reiniciar antes de abrir cada consulta | REQ-002, REQ-005 | Chrome local con sesión temporal: NASDAQ, S&P 500 y recomendaciones abren hilos separados; métricas solo prellena; reinicio bloquea envío ante error | Completa local |
| TASK-007 | Aplicar la paleta del robot e integrar video de bienvenida con respaldo | REQ-006 | 40 checks Chrome, 15 pruebas de servidor, wheel con video/imagen/tema y capturas a cuatro tamaños | Completa local |

## Trazabilidad

| REQ | TASK(s) | Evidencia prevista |
|---|---|---|
| REQ-001 | TASK-002, TASK-004 | Capturas de Chrome e interacciones de navegador |
| REQ-002 | TASK-001, TASK-004 | API con SQLite temporal y sin red externa |
| REQ-003 | TASK-003, TASK-004 | Conversaciones completas con datos locales y fuentes |
| REQ-004 | TASK-004 | Comandos documentados y resultados reales, sin declarar NIM verificado |
| REQ-005 | TASK-005, TASK-006 | Nuevo diseño adaptable y transición de sesión por acceso |
| REQ-006 | TASK-007 | Paleta basada en asset, video original local en bucle sin controles, respaldo y legibilidad |

## Evidencia ejecutada — 2026-11-07 (TASK-007)

- Corrección posterior: se restauró el MP4 original y su marco, se retiró la variante WebM y se quitó el botón de pausa. `node tools/check_web.mjs --front-only` pasó **40 comprobaciones** con bucle efectivo, sin controles y con respaldo bajo movimiento reducido; nueve capturas revisadas. `node --check`, spec y `git diff --check` pasaron. Sin proveedores externos.
- `node tools/check_web.mjs --front-only` → **40 comprobaciones** en Chrome local, con reproducción y pausa del video, pausa al comenzar el chat, respaldo con movimiento reducido, contraste y cuatro tamaños de pantalla. Nueve capturas revisadas; proveedores financieros desactivados.
- `.venv/bin/python -m pytest -q tests/unit/test_web_server.py` → **15 passed** con sockets locales; el primer intento dentro de sandbox no pudo abrir el puerto y se repitió con autorización.
- `pip wheel --no-deps --no-build-isolation` generó el paquete; se comprobó que contiene `robot-theme.css`, el MP4 y el PNG. `node --check`, validador SDD y `git diff --check` pasaron. No se consultaron proveedores financieros.

## Evidencia ejecutada — 2026-11-07 (TASK-005 y TASK-006)

- `node tools/check_web.mjs --front-only` → **36 comprobaciones** en Chrome headless a 1440×900, 1024×768, 768×1024 y 390×844. Nueve capturas en `.impeccable/review/`; base y perfil temporales, claves de proveedores vacías. Incluye accesos NASDAQ y S&P 500, recomendaciones en sesión nueva, borrador de métricas, navegación móvil, contraste de ayudas y ausencia de errores JavaScript.
- `node --check` del frontend y verificador, `tools/validate_spec.py specs/web-conversacional` y `git diff --check` completados. No se llamaron proveedores ni modelo reales.

## Evidencia ejecutada — 2026-11-04

- `NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q` → **338 passed**. Incluye 41 pruebas web; HTTP real en localhost, SQLite temporal y proveedores simulados, con permiso para abrir puertos locales. No acredita servicios externos.
- `RUN_LIVE_INTEGRATION=0 NVIDIA_KEY_ROTATED=0 NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q tests/integration` → **4 skipped**.
- `node tools/check_web.mjs` → **38 comprobaciones pasan** en Chrome headless real: 1440×900, 1024×768, 768×1024 y 390×844. Base y perfil de Chrome temporales; credenciales desactivadas. Incluye secuencia de la captura, fuentes, búsqueda, memoria, olvido, recarga, sugerencias, Enter/Shift+Enter, menú/foco, pérdida de conexión y reintento sin duplicación, texto HTML literal y ausencia de excepciones JS.
- El script generó nueve capturas en `.impeccable/review/` y `browser-report.json`, ignorados por Git. Cada captura se abrió en la revisión visual; no solo se comprobó la existencia del archivo. Textos secundarios comprobados a ≥4.5:1 y ≥11 px.
- Las nueve specs activas pasan `tools/validate_spec.py`; `bash -n run_web.sh run_streamlit.sh`, `node --check` de app y verificador, y `git diff --check` sin errores. El lanzador también se invocó desde fuera del repositorio.
- `pip wheel --no-deps --wheel-dir .local/browser-review/wheels .` construyó el paquete tras descargar sus requisitos de build declarados. Se inspeccionó el ZIP: HTML, CSS, JS, dos tipografías y sus dos licencias coinciden con los archivos actuales; entrada `investiq-web` presente, sin `.env` ni skills.
- `tools/verify_agent.py` sin flags devuelve `not_run/live-opt-in-required`; no se contactó NIM. Advertencias de deprecación de LangSmith/Python 3.14, sin fallos de pruebas.

## Revisión y pulido

| Before | After | Why |
|---|---|---|
| Streamlit con bloques de chat y avatares de robot | Web con conversación amplia, catálogo buscable y explorador móvil | Resolver la petición de una interfaz web amigable |
| Preguntar qué es AAPL abría un menú genérico | Consulta local de nombre, símbolo y tipo, con referencia al catálogo | Responder a la pregunta real sin depender de precios |
| Ayudas con contraste insuficiente y fuentes de 8–10 px | Texto secundario más oscuro y mínimo 11 px, comprobado en Chrome | Avisos y fuentes legibles en móvil |
| Otra ventana podía volver a guardar un contexto olvidado | Invalidación por versión del contexto compartido y tres regresiones | Respetar el olvido solicitado |

La revisión visual no requiere añadir efectos decorativos: el diseño sirve a la conversación. El CLI auxiliar de Impeccable no funcionó y no se declara validado; se usaron sus referencias y revisión independiente. La naturalidad con NVIDIA real requiere la prueba opt-in en el entorno conectado. Fase 5 sin iniciar.
