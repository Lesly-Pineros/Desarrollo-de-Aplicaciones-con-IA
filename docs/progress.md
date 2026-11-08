# Estado del proyecto

Última actualización: **2026-11-08**. Este documento concentra el estado vigente y el historial de cambios del proyecto; `PLAN.md` conserva alcance, decisiones y fases.

## Estado vigente

- Interfaz principal: web local HTML/CSS/JS servida desde Python; Streamlit fue retirado del código activo, dependencias, entry points y pruebas específicas.
- Se conservan las tools Python locales y la API local. Las consultas de símbolos presentan cotización según disponibilidad y métricas históricas calculadas; la cobertura de mercado descrita por la app es estadounidense.
- La entrada inicial permite iniciar recomendaciones guiadas, consultar métricas de un símbolo/ETF, explorar sectores de NASDAQ y consultar actualidad. Los flujos de símbolos usan Twelve Data cuando está configurado y disponible; no se declara la integración en vivo verificada por las pruebas offline.
- Módulos de diálogo, routing, handlers, respuestas y registro mantienen responsabilidades separadas; las consultas externas se degradan cuando faltan credenciales o datos.
- La suite offline pasó **696 pruebas**; el verificador web pasó **96 comprobaciones** en Chrome con fixtures sintéticos; **17 specs** validaron. Los servicios financieros externos no se consultaron en esas verificaciones.
- Integraciones reales de proveedores/modelo siguen pendientes. La fase 5 inició su preparación para Render Free; crear el servicio y hacer el smoke test en la URL están pendientes de configurar los secretos en Render.

## Actualización — destino del POC en la nube (2026-11-08)

Por decisión del usuario, Render Free queda como proveedor elegido para el POC. Se implementaron bind por `PORT`, autenticación Basic obligatoria en Render, cookies Secure bajo HTTPS, health check, Blueprint Free y guía de secretos. El deployment live espera que la usuaria cree el Blueprint y configure `INVESTIQ_ACCESS_PASSWORD` (obligatoria) y decida si agrega `NVIDIA_API_KEY` (opcional). Se conserva SQLite solo con expectativa de datos temporales, porque el filesystem gratis es efímero; no se añade una base administrada. El nivel Free puede suspenderse por inactividad y sus límites pueden cambiar. Ver [ADR-002](../decisions/ADR-002-despliegue.md), [spec de fase 5](../specs/fase5-render/tasks.md) y [PLAN.md](../PLAN.md).

## Actualización — video original sin botón de pausa (2026-11-07)

Se restauró el video original de la bienvenida y su marco. La reproducción continúa silenciada y en bucle, pero ya no tiene botón ni controles visibles. La imagen estática sigue disponible cuando falla el video o se prefiere movimiento reducido. La variante WebM transparente se retiró por solicitud del usuario. Verificación local: **40 comprobaciones Chrome**, incluido el reinicio efectivo del bucle, nueve capturas y ausencia de llamadas a proveedores; `node --check`, especificación y `git diff --check` pasaron.

## Actualización — identidad del robot y video de bienvenida (2026-11-07)

Se sustituyó la paleta verde anterior por una derivada del robot aportado: marino `#011637`, azul `#0E64A4`, cian `#0AD6C8`, blanco frío `#EDF3F7` y naranja `#F07000` como origen de las acciones. La bienvenida reproduce localmente uno de los videos de 10 segundos, silenciado y con control de pausa; la imagen original queda de respaldo. El video se detiene al iniciar el chat y no se reproduce automáticamente con movimiento reducido. Una leyenda identifica sus gráficas como ilustrativas. Verificación: **40 checks Chrome**, **15 pruebas de servidor**, cuatro anchuras y wheel inspeccionado con los tres recursos nuevos. No se hicieron llamadas a proveedores financieros ni al modelo.

## Actualización — rediseño web y accesos independientes (2026-11-07)

La web local adopta un tema verde noche con paneles translúcidos, un profesor robot SVG local, accesos destacados y un catálogo horizontal en escritorio; en móvil conserva el explorador accesible. Noticias, recomendaciones, NASDAQ y S&P 500 tienen tarjetas propias. Cada acceso y pregunta inicial reinicia la sesión antes de consultar; métricas abre un chat nuevo con el mensaje preparado para que la persona lo complete. El botón «Nueva conversación» permanece. Las acciones dentro de respuestas continúan el hilo vigente. Las tres guías de diseño solicitadas se instalaron localmente y se leyeron; el cargador auxiliar de Impeccable no pudo iniciar por su caché global, así que se aplicó su documentación directamente. Verificación enfocada: **36 checks Chrome** y nueve capturas a cuatro anchuras, `node --check`, spec y `git diff --check`; las credenciales de proveedores estaban vacías. No se probaron FMP, Twelve Data ni el modelo en vivo.

## Actualización — respaldo de sectores S&P 500 (2026-11-07)

El acceso S&P 500 puede responder sin `FMP_API_KEY`: si FMP no entrega el cálculo por componentes, usa dos cierres recientes completos de los once ETF sectoriales Select Sector SPDR consultados mediante Yahoo Finance. La tabla identifica cada ETF, fecha, variación y fuentes, y aclara que no es el rendimiento oficial del sector ni el promedio de componentes. También se reconoce «cómo van los sectores» como consulta actual. El respaldo puede desactivarse en pruebas desconectadas. Verificación: **60 pruebas focalizadas** con fixtures, **36 checks Chrome** sin proveedores y consulta Yahoo real de los once ETF para 2026-11-06; la respuesta completa devolvió once filas y doce fuentes. FMP sigue sin clave configurada en este entorno y sus endpoints no se verificaron en vivo.

## Actualización — limpieza local y documentación

Se actualizaron `PLAN.md` y `README.md` para describir la web local y las tools locales como arquitectura vigente. El plan mantiene alcance y decisiones; este archivo concentra estado e historial. Se retiraron la interfaz heredada de Streamlit, su launcher, entry point, extra de instalación y pruebas asociadas. Los planes antiguos se conservan únicamente como registro histórico donde aplica. La verificación registrada para esta limpieza fue: 696 pruebas offline, 96 comprobaciones Chrome con fixtures sintéticos, 17 specs válidas y `git diff --check`; no se hicieron llamadas a proveedores financieros reales.

La interfaz y documentación llaman ahora a la fuente **filings de la SEC**. La ficha educativa fue renombrada a «Informes públicos de empresas» y el servidor MCP se identifica como servicio de filings SEC. Se conservan los identificadores de protocolo y las rutas técnicas oficiales necesarios para obtener y enlazar esos documentos; no aparecen como nombre del producto.

## Actualización — acceso directo a métricas

Al elegir la sugerencia de métricas, el chat ahora precarga «Dame las métricas de la acción o ETF: » en el campo de escritura, enfoca el campo y espera a que la persona agregue el símbolo y envíe el mensaje. La selección no dispara una consulta ni llama al modelo. La spec de ficha individual documenta este comportamiento.

## Actualización — logs operativos

Se añadió configuración de logs de consola (`INVESTIQ_LOG_LEVEL`, predeterminado `INFO`) y trazas correlacionadas por request para el servidor web. El recorrido registra etapas de servicio, diálogo, clasificación, tools, proveedores, LLM, degradaciones y persistencia con duraciones. Los errores inesperados registran tipo y marcos del código sin mensajes de excepción; los logs excluyen prompts, símbolos, datos financieros, claves y contenido de proveedores. También se instrumentaron los comandos de conocimiento, MCP, verificación del agente y pipeline ML. `compileall`, `node --check`, validación de `specs/logs-operativos` y `git diff --check` pasan; no se ejecutó la suite de tests ni se hicieron llamadas externas.

## Actualización — recomendaciones guiadas

Se reemplazó el prompt prefabricado del botón por una acción que muestra únicamente la intervención del asistente. La aclaración reúne en una sola pregunta los criterios obligatorios pendientes; usa una redacción del modelo configurado y una alternativa local cuando no está disponible. Se corrigió la interpretación de negaciones para conservar frases como «no soy de tomar riesgos» como preferencia de baja variación histórica, se dejó opcional el símbolo de referencia y se añadió transparencia si se menciona dinero: el monto no interviene en el ranking. `compileall`, `node --check`, validación de la spec y `git diff --check` pasan. No se ejecutaron pruebas automatizadas ni llamadas a servicios externos.

## Actualización — resumen de memoria al iniciar

Se corrigió un `KeyError` al cargar memoria cuando quedaba pendiente elegir un símbolo. Se añadió el texto de resumen para `instrument_symbol` y el resumen ahora ignora de forma segura cualquier campo pendiente sin descripción. Verificación estática: `compileall` y `git diff --check`; no se ejecutaron pruebas.

## Actualización — consulta de métricas por empresa

La ficha individual ahora resuelve nombres y alias declarados en el catálogo, incluidos Johnson & Johnson y J&J. Se habilitó Coca-Cola como consulta individual por nombre o KO para cotización opcional, manteniendo el universo histórico/ML de 20 instrumentos; las métricas locales ausentes se declaran y KO no activa noticias ni filings. `compileall`, `node --check`, validación de la spec y `git diff --check` pasan. No se ejecutaron pruebas ni llamadas a Twelve Data.

## Actualización — conversión de fuentes a referencias

Se corrigió la validación al transformar noticias y filings: sus URL tipadas (`HttpUrl`) ahora se serializan a texto antes de construir `SourceReference`, cuyo contrato usa `str`. `compileall` y `git diff --check` pasan; no se ejecutaron pruebas ni se hicieron llamadas a proveedores.

## Verificación local — 2026-11-07

Por solicitud del usuario se ejecutó la suite unitaria completa en dos grupos: 689 pruebas sin `test_web_server.py` y 15 pruebas del servidor con sockets locales autorizados; resultado combinado: 704 passed. No se ejecutaron tests de integración ni llamadas a APIs externas. La ejecución detectó expectations de exploración que aún exigían preguntas secuenciales/referencia, una regresión en el orden de tools y que faltaba aceptar «variaciones bajas»; se actualizaron esas expectativas, se restauró el orden y se amplió el parser. Se añadieron casos locales para nombres de empresa y la conversión de URLs tipadas de noticias/filings. Avisos restantes: deprecación de LangSmith y detección de núcleos de joblib en Python 3.14.

## Ajuste de la aclaración de métricas — 2026-11-07

La respuesta al acceso directo seguía ignorando KO porque el estado pendiente de símbolo solo consultaba el catálogo principal. `resume_pending` ahora combina nombres y símbolos de consulta individual con la decisión del router. La aclaración acepta explícitamente nombre de empresa o ETF. Se añadió una regresión con el mensaje «Dame las métricas de la acción o ETF: de cocacola» y otra para Johnson & Johnson. Resultado de la suite unitaria completa: **706 passed**, sin integraciones ni llamadas a proveedores reales.

## Ajuste de criterios conversacionales — 2026-11-07

La captura mostró que faltaban expresiones corrientes: «no tan volátil», «por un año», «subidas y bajas pocas» y «más estable». El router ahora inicia exploración al oír «quiero invertir…», el parser conserva esos criterios y trata «seis meses» como plazo corto para activar la cautela educativa. Pruebas focalizadas de exploración: 23 passed, incluyendo el flujo completo y el caso de seis meses; sin proveedores reales.

## Redacción contextual de aclaraciones — 2026-11-07

Se eliminó «no hace falta usar términos financieros» y otras coletillas prefabricadas del fallback local. La aclaración reconoce los criterios ya capturados y formula solo los pendientes; el validador rechaza esos cierres genéricos si los genera NVIDIA y usa el fallback contextual. Se añadieron expresiones como «medio año», «sin tantos altibajos», «un par de años» y «pocos riesgos». Resultado de pruebas locales focalizadas: 59 passed; spec SDD válida, `compileall` y `git diff --check` pasan. Sin llamadas externas.

## Historial

### Estado
**Estado de ejecución (2026-11-01):** Fases 0–2 completas según verificaciones previas. Fase 3 implementada: Streamlit, auth Argon2, router Python, tools/proveedores, cachés/cuotas, trazas, disclaimer y guía local disponibles. Última suite válida sin usar la clave NVIDIA actual: 34 pruebas pasan; smoke Streamlit y validador SDD pasan; filings de la SEC y yfinance se verificaron en vivo. La Fase 3 queda **pendiente de aceptación completa**: la clave NVIDIA debe rotarse tras quedar expuesta en un traceback y luego repetirse la integración ChatNVIDIA; el demo end-to-end con LLM también queda pendiente. Próximo paso: sustituir la clave en `.env` y ejecutar `tests/integration/test_phase3_live.py`.

**Actualización (2026-11-03):** Auditoría: Fases 0–2 conservan entregables y verificaciones previas; la suite unitaria actual (incluidos casos de hardening) pasa. Fase 3 está implementada, pero no puede considerarse aceptada por completo hasta rotar la clave previamente expuesta y pasar ChatNVIDIA live + demo end-to-end. filings de la SEC y yfinance live pasaron en esta auditoría. Fase 4 ejecutada: evaluación offline ampliada, MCP de filings SEC stdio integrado y registrado en el ejemplo de Codex. Evidencia: 41 tests offline pasan; herramienta MCP consulta filings de la SEC real y devuelve filings verificables; validadores SDD de fases 0, 1, 2 y 4 pasan. No se extrajo FastAPI porque es opcional en el plan. Próximo paso: completar la aceptación pendiente de Fase 3 con una clave NVIDIA rotada.

**Actualización (2026-11-04):** Por solicitud del usuario se retiró el login single-user. La app abre directamente y usa una identidad local fija para preferencias y trazas; las credenciales de acceso y Argon2 dejan de ser parte del piloto. Verificación posterior al cambio pendiente.

**Conversación (2026-11-04):** Preferencias opcionales recogidas por chat y contexto por sesión para completar consultas entre mensajes. La sidebar presenta ayuda y catálogo de símbolos consultables. Evidencia offline: 70 pruebas pasan, incluido smoke de Streamlit; specs piloto y conversacion-preferencias válidas. No se ejecutaron APIs reales en este cambio.

**Agente amigable (2026-11-04):** Guía de tono cargada por el runtime, narración en las rutas factuales con resultados protegidos, propuestas semánticas de preferencias con evidencia y memoria resumida opcional visible/borrable. Se añaden ConversationMemory y ResponseTrace sin alterar destructivamente SQLite existente. Regresión offline: 189 pruebas pasan. NIM real sigue pendiente en el entorno conectado con clave rotada; `tools/verify_agent.py --live --key-rotated` produce un informe seguro. BMAD evaluado como apoyo selectivo de UX/revisión, sin instalación ni dependencia nueva.

**Depuración y documentación (2026-11-04):** se unifican normalización y procedencia antes de ambos parsers; preguntas/citas ajenas no escriben preferencias. Una comparación completa sustituye la anterior y la aclaración de beta acepta un número breve incluso tras reiniciar. La prosa que acompaña datos de mercado se limita a conectores controlados. App y pipeline usan Settings/.env y el lanzador respeta INVESTIQ_PYTHON. README y guías actualizados, regresión 223 passed y 4 integraciones omitidas sin red; siete specs SDD válidas. La organización Agent Skills enlaza un ejemplo skill-creator cuya descarga fue rechazada antes de ejecutarse: no instalado ni utilizado. Se usó sdd-feature local y se reservó una exclusión exacta de Git para la instalación futura.

**Modularización (2026-11-04):** conversation y orchestration son fachadas de coordinación; dialogue separa comandos, estado, preferencias y aclaraciones, mientras routing/handlers/responses/query_log poseen sus responsabilidades. Se quitaron imports privados usados por pruebas y se trasladaron los mocks a los módulos propietarios. La revisión independiente detectó aprendizaje confundido con preferencias, META ambiguo y creación duplicada del cliente; los tres casos tienen corrección y regresiones. Se protegen además errores al iniciar el SDK para evitar exponer credenciales. Resultado: 270 pruebas offline pasan, cuatro integraciones omitidas, ocho specs válidas y sdd-feature validada. Las skills disponibles sdd-feature/skill-creator guiaron el trabajo; investiq-agent-review no se creó porque se rechazó el permiso de escritura en .agents.

**Web conversacional (2026-11-04):** por solicitud del usuario se sustituye la entrada local principal por HTML/CSS/JS servido desde Python (ADR-004). Las tres skills de diseño solicitadas se descargaron y leyeron; su CLI Impeccable no arrancó por permisos de caché y se siguió la alternativa de lectura directa, sin atribuirle checks. Backend, sesiones y frontend separados; fuentes tipográficas locales con licencia. AAPL se define desde catálogo y los conceptos usan glosario trazable. La revisión independiente corrigió contraste, texto secundario pequeño y restauración de contexto olvidado desde otras ventanas. Evidencia: 338 tests offline, 38 comprobaciones Chrome, nueve capturas válidas, nueve specs y wheel construido con los siete assets actuales. Cuatro pruebas live omitidas; NIM pendiente. README incorpora arranque y validación portable. Fase 5 no iniciada; hosting de la web se revisará allí.

**Continuidad del profesor (2026-11-04):** se confirmaron primero los 584 tests y 60 checks de Chrome previos. Se corrigieron pérdidas de tema en «No entiendo», ejemplos conversacionales, interpretación e importancia, ayuda general que interrumpía una lección y temas incidentales guardados sin evidencia. Diálogo, búsqueda y respaldo comparten el reconocimiento acotado en learning.py; las fichas de instrumentos admiten seguimientos educativos. El modo principiante conserva definición y ejemplo, con prioridad a la explicación cuando se solicita. Evidencia actual: 627 pruebas offline (43 nuevas), 75 comprobaciones Chrome, 13 specs y biblioteca válida de 119 documentos/16 categorías/113 referencias. Cuatro integraciones omitidas y diagnóstico NVIDIA not_run; sin llamadas reales. Requisitos, diseño, trazabilidad y límites en [continuidad-profesor](specs/continuidad-profesor/tasks.md). Cambios previos conservados; fase 5 sin iniciar.

**Actualidad y exploración guiada (2026-11-04):** noticias diarias por Marketaux con filtros, fechas y cuota compartida; traducción/resumen del extracto con un intento NVIDIA y selección por ID oculto. Se corrige el supuesto fijo de 24 horas conforme a documentación actual (ADR-006). La web ofrece accesos persistentes sin formularios. El flujo de candidatos pregunta criterios, utiliza distancias del clustering aprobado y muestra volatilidad anualizada, beta, sector, grupo, período y fuentes; valida datos/modelo y conserva las preferencias explícitas. El snapshot FMP opcional exige once sectores NASDAQ del mismo día/bolsa; no representa todo Estados Unidos ni se deriva de noticias o ETF. Evidencia: 704 pruebas offline (77 nuevas), 93 checks Chrome con fuentes/modelo sintéticos para las nuevas ramas, 15 specs y wheel verificados. Las regresiones conservaron la distinción entre texto citado y solicitudes, memoria y profesor. Mercado/NVIDIA reales pendientes; claves propias requeridas para fuentes externas, sin suscripciones contratadas. Se mantiene Python plano y NVIDIA configurable, fase 5 sin iniciar.

**Ranking sectorial NASDAQ y S&P 500 (2026-11-07):** el acceso NASDAQ busca el snapshot de la sesión de mercado más reciente en vez de exigir el día calendario; errores por ausencia de datos, conexión, permisos y cuota se reportan por separado. Se agrega un botón independiente para S&P 500 basado en componentes actuales FMP y cambios cierre a cierre, calculados con los dos días EOD completos más recientes y agrupados por sector. La respuesta declara el promedio simple y cantidad de componentes, sin presentarlo como índice sectorial oficial ni como ponderación del S&P 500. La especificación y código están actualizados; verificación funcional local pendiente. No se hicieron llamadas live a FMP.
