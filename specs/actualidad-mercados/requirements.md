# Requisitos — Noticias y actualidad sectorial

- **Estado:** Borrador (2026-11-04).
- **Implementación:** completada y verificada offline y en Chrome local; evidencia en [tasks.md](tasks.md). Marketaux, FMP y NVIDIA reales pendientes; sin despliegue ni aprobación editorial independiente.
- **Alcance:** noticias financieras del día por sector, país o símbolo, traducción y resumen bajo demanda; proveedor opcional de rendimiento sectorial; accesos en la web local.
- **Exclusiones:** despliegue, suscripciones de pago automáticas, prometer cobertura universal, copiar artículos completos, deducir rendimientos de titulares, usar APIs reales durante tests offline.

### REQ-001 — Noticias fechadas y filtradas

**EARS:** Cuando se pidan noticias de hoy o las últimas noticias financieras, el sistema deberá consultar Marketaux con fecha, sector, país o símbolo pertinentes y presentar hasta tres titulares con publicación y fuente.

**Criterios de aceptación:** filtros explícitos de tecnología, finanzas, energía y demás sectores disponibles; países cubiertos identificados sin asumir residencia; hoy según zona configurable, convertido a UTC para la API. Ningún artículo sin fecha, futuro o fuera del día se presenta como de hoy. Selección por recencia, sin afirmar un ranking universal de importancia. Caché por filtros/fecha, cuotas compartidas con noticias de símbolos; fallos y ausencia de clave se explican sin inventar noticias. Las consultas educativas no llaman a proveedores.

### REQ-002 — Traducción y resumen con evidencia

**EARS:** Cuando haya titulares en otro idioma, el sistema deberá ofrecer traducciones al español con NVIDIA; cuando se seleccione una noticia, deberá resumir únicamente el extracto recibido de esa noticia.

**Criterios de aceptación:** salida estructurada ligada al ID y texto original; controles de cifras, URLs, símbolos, consejo e inyección, con original accesible y límites semánticos explícitos. Si no hay modelo o la salida falla, conservar original y explicar el límite. «Resume la segunda», número y selección en frontend funcionan sin una nueva búsqueda; sin extracto no se inventa contenido. La selección de noticias es temporal, no memoria persistente ni biblioteca RAG.

### REQ-003 — Ranking sectorial con cobertura declarada

**EARS:** Cuando se pregunten sectores que lideran hoy, el sistema deberá pedir mercado si falta y consultar un proveedor de rendimiento cuando exista configuración y cobertura compatibles.

**Criterios de aceptación:** adaptador FMP opcional para snapshot de los once sectores de NASDAQ en Estados Unidos, con fecha de Nueva York, métrica y bolsa explícitas. Validar once sectores únicos, números finitos y mismo día/bolsa antes de ordenar; no afirmar cobertura de todo el país ni hora del proveedor si solo informa fecha. Datos incompletos, otros mercados, clave ausente o plan sin acceso conservan una respuesta degradada honesta. No utilizar ETF del catálogo ni noticias para inventar líderes. Caché y cuota acotadas; no contratar ningún plan.

### REQ-004 — Interfaz y seguridad

**EARS:** Cuando se usen estas ramas desde la web, el usuario deberá disponer de accesos visibles y selección de noticias conservando el chat, sus controles y accesibilidad.

**Criterios de aceptación:** acciones de noticias y sectores disponibles en escritorio/móvil; resumen por botón y por conversación; campos recibidos nunca se insertan como HTML; fechas/fuentes/disclaimer en respuestas. Secretos solo en variables de entorno; URLs de proveedor fijas y sin descargar páginas arbitrarias.

### REQ-006 — Acceso directo al ranking sectorial

**EARS:** Cuando el usuario pregunte por líderes sectoriales actuales, el sistema deberá explicar qué mercados tienen cobertura disponible y permitir continuar con uno compatible.

**Criterios de aceptación:** el acceso persistente y las consultas escritas identifican correctamente NASDAQ y el S&P 500 como universos independientes. NASDAQ presenta once variaciones porcentuales de su snapshot, fecha, fuente y límites cuando FMP dispone de datos; la consulta del S&P 500 se define en REQ-007. Colombia, España, Europa y global todavía no tienen cobertura numérica actual. Sin clave, acceso o datos válidos, presenta el motivo conocido y cómo habilitar/consultar la función. No inventa cifras.

### REQ-007 — Accesos independientes NASDAQ y S&P 500

**EARS:** Cuando una persona elija NASDAQ o S&P 500, la app deberá consultar y mostrar únicamente el universo seleccionado, sin mezclarlos ni compararlos.

**Criterios de aceptación:** la web tiene un botón independiente para cada universo y las consultas escritas reconocen ambos. NASDAQ usa el snapshot FMP por bolsa y puede recuperar el día de mercado más reciente disponible cuando hoy no haya sesión o datos publicados. S&P 500 usa la lista vigente de componentes y precios EOD de FMP, busca los dos últimos días de mercado con cobertura completa y calcula el cambio cierre a cierre, agrupado por sector mediante promedio simple. Declara cobertura, método, fecha y fuente; no lo presenta como índice sectorial oficial ni como retorno ponderado del índice. Respuestas vacías, parciales, fechas inconsistentes, falta de clave, cuota o rechazo de endpoint se explican según el caso sin atribuir siempre el problema a la conexión. Cada respuesta incluye «No es asesoría financiera».

### REQ-005 — Evidencia y operación

**EARS:** Cuando se entregue la capacidad, el repositorio deberá documentar configuración, cuotas, cobertura y verificaciones reales frente a simuladas.

**Criterios de aceptación:** tests con HTTP/NVIDIA simulados, fechas y adversarios; regresión del profesor, Chrome y SDD; README/PLAN actuales. Revisar la antigua suposición de 24 horas frente a la documentación oficial actual (100 peticiones/día, tres artículos y acceso inmediato); no acreditar integración live con mocks. Cada respuesta incluye «No es asesoría financiera».

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-04 | Borrador previo: noticias diarias, resumen seleccionado, sector por fuente y frontend solicitados. |
| 2026-11-04 | Implementación local, selección por ID oculto, controles de traducción y separación de texto citado. Regresión final: 704 pruebas offline, 93 checks Chrome y quince specs válidas. |
| 2026-11-07 | Borrador de pulido: respuestas cortas para la exploración y recorrido explícito del acceso «Sectores de hoy», con degradación visible cuando FMP no está disponible. |
| 2026-11-07 | El acceso de sectores ahora explica cobertura disponible y ofrece continuar con NASDAQ; los demás mercados se identifican como no conectados para ranking numérico. |
| 2026-11-07 | Se conserva el acceso directo «Sectores de hoy · NASDAQ» junto a los modos de noticias y recomendaciones guiadas. |
| 2026-11-07 | Se especifican dos consultas sectoriales independientes (NASDAQ y S&P 500) y la recuperación del snapshot NASDAQ más reciente disponible, distinguiendo fallos de datos de fallos de conexión. S&P 500 usa precios EOD de los dos últimos días disponibles para cubrir fines de semana, festivos y consultas posteriores al cierre. |
