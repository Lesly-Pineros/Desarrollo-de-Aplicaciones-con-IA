# Tareas — Actualidad de mercados

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-001 | Contratos, filtros, proveedor Marketaux, caché/fecha/cuota | REQ-001, REQ-005 | test_market_current.py: HTTP simulado, límites UTC/IANA, filtros, caché por día, cuota y errores sanitizados | Completa offline |
| TASK-002 | Traducción/resumen, selección temporal e integración conversacional | REQ-001, REQ-002, REQ-004 | test_market_current.py y test_llm.py: selección exacta, metadatos ocultos, inyección, cifras, extracto/modelo ausentes y un intento | Completa offline; NVIDIA real pendiente |
| TASK-003 | Adaptador FMP y ranking con cobertura comprobada | REQ-003, REQ-005 | Once sectores sintéticos; rechazar faltantes/duplicados/otra fecha/bolsa/NaN; denegación de plan sanitizada | Completa offline; FMP real pendiente |
| TASK-004 | Accesos web, docs, ADR y regresión final | REQ-001, REQ-002, REQ-003, REQ-004, REQ-005 | 704 pruebas, 93 checks Chrome, 119 documentos, quince specs, wheel y diff --check | Completa local |
| TASK-005 | Mantener acceso directo a NASDAQ y degradación visible si FMP no está disponible | REQ-003, REQ-004, REQ-006 | test_market_current.py: consulta explícita NASDAQ y ausencia/fallo FMP explicado; check web verifica respuesta visible | Implementación local; verificación pendiente |
| TASK-006 | Corregir días sin sesión/datos NASDAQ y agregar consulta independiente S&P 500 basada en componentes y cierres diarios FMP | REQ-007 | Tests offline: búsqueda de los dos últimos EOD completos, cierres/cálculo cierre a cierre, agrupación por sector, cobertura/fecha inconsistente, cuotas/caché; verificación web de dos botones y respuestas aisladas | Implementación local; verificaciones funcionales pendientes |
| TASK-007 | Habilitar respaldo S&P 500 mediante los once ETF sectoriales y explicitar su método | REQ-008 | 60 pruebas focalizadas, 36 checks Chrome sin proveedores y consulta real Yahoo con once sectores/fuentes; fecha, cobertura, caché y fallo comprobados | Completa local; Yahoo verificado en vivo |

## Trazabilidad

| REQ | TASK(s) | Evidencia prevista |
|---|---|---|
| REQ-001 | TASK-001, TASK-002, TASK-004 | Listado fechado real desde fixture HTTP |
| REQ-002 | TASK-002, TASK-004 | Selección estable y texto ligado a noticia |
| REQ-003 | TASK-003, TASK-004 | Ranking completo o degradación honesta |
| REQ-004 | TASK-002, TASK-004 | Chat y botones accesibles sin HTML externo |
| REQ-005 | TASK-001, TASK-003, TASK-004 | Configuración y evidencia offline/live separadas |
| REQ-006 | TASK-005 | Acceso directo devuelve tabla o degradación explicada |
| REQ-007 | TASK-006 | NASDAQ usa el último snapshot disponible; S&P 500 agrupa exclusivamente sus componentes y declara promedio/cobertura |
| REQ-008 | TASK-007 | Respaldo ETF con dos cierres comunes verificados y método/fuentes explícitos |

## Evidencia ejecutada — 2026-11-07 (TASK-007)

- `.venv/bin/python -m pytest -q tests/unit/test_market_current.py` → **60 passed**, con datos sectoriales sintéticos; no consulta proveedores.
- `node tools/check_web.mjs --front-only` → **36 comprobaciones Chrome** con `INVESTIQ_SECTOR_ETF_FALLBACK_ENABLED=false` y claves vacías; ninguna llamada externa.
- Consulta real de Yahoo Finance desde este equipo, sin clave FMP: **11 ETF, fecha 2026-11-06, sin error**. El recorrido completo `answer_turn` devolvió `status=ok`, `intent=sector_performance`, once filas ETF, doce referencias y disclaimer. Esta verificación no acredita los endpoints FMP.

## Evidencia ejecutada — 2026-11-04

- `NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= FMP_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q` → **704 passed**. Son 77 casos nuevos respecto a la entrega de 627: 75 en las dos ramas y dos en el adaptador NVIDIA. HTTP/NVIDIA simulados; biblioteca real y KMeans real con características sintéticas, SQLite temporal. Trece avisos de deprecación LangSmith/Python 3.14 en la regresión final.
- `test_market_current.py`: filtros y países (sin confundir `de` con Alemania), fechas UTC y zona IANA/DST, deduplicación, fuentes, caché/expiración/cuota y sin clave; selección por ordinal y por ID oculto estable; extracto ausente, memoria restaurada sin noticias, títulos en español, traducciones con cifras/URLs/tickers/citas falsas e inyección; once sectores completos frente a datos inconsistentes/NaN o acceso denegado. Las pruebas unitarias bloquean HTTP real.
- `test_llm.py` verifica el método nuevo mediante un SDK simulado: artículos en el mensaje de datos no confiables, salida estructurada y un solo intento con errores sin tokens privados. No valida tono ni traducciones del modelo real.
- La regresión detectó una noticia citada («La noticia dice…») confundida con una búsqueda que cancelaba una aclaración. Se corrigió su ruta y se preservaron las pruebas previas de procedencia. La revisión móvil detectó IDs internos en una burbuja del usuario: la acción ahora usa metadatos ocultos y conserva texto natural incluso tras recargar el historial.
- `node tools/check_web.mjs` → **93 comprobaciones** en Chrome headless real; diecisiete capturas e informe en `.impeccable/review/`, ignorados por Git. Primero prueba el profesor existente y después inicia otro servidor/base temporal con noticias/snapshots sintéticos y modelo KMeans entrenado sobre fixtures. Se comprueban botones persistentes, resumen exacto, fuentes, IDs ocultos, preguntas, porcentajes, procedencia ML y tabla de once sectores. Se abrieron las capturas móviles de noticias, candidatos y sectores; controles/compositor visibles y sin desbordamiento. Los fixtures no representan datos financieros actuales.
- CLI de biblioteca → **119 documentos, 16 categorías, 113 referencias**, sin cambios editoriales financieros. **Quince specs válidas**, `node --check`, `bash -n` y `git diff --check` sin errores.
- Wheel construido e inspeccionado: módulos nuevos y assets coinciden byte a byte con esta copia, cinco JSON y biblioteca de 119 documentos importados desde el wheel fuera del checkout. El primer intento encontró ausencia de setuptools/wheel; se instalaron como herramientas de construcción en `.venv` con permiso. El build posterior no utilizó red y no cambió dependencias de runtime.
- Las cuatro integraciones existentes se omiten con `RUN_LIVE_INTEGRATION=0`. `tools/verify_agent.py` sin flags devuelve **not_run/live-opt-in-required**, cero turnos. No se hicieron peticiones reales a Marketaux, FMP o NVIDIA. La consulta editorial a documentación oficial no constituye prueba live de esos adaptadores.

## Límites y operación

Configurar claves propias según [la guía](../../docs/market-branches.md). El acceso FMP depende del plan; no se contrató ninguno y no se garantiza que ese endpoint esté incluido en la cuenta gratuita. Mercado sectorial acotado a NASDAQ; noticias por recencia y filtros de entidades del proveedor, no cobertura de toda la actualidad nacional. La traducción está ligada a evidencia pero sus controles no prueban equivalencia semántica. Los resúmenes no leen el artículo completo. Sin modelo se informa y conserva el original. Python plano y NVIDIA configurable se mantienen; fase 5 sin iniciar.
