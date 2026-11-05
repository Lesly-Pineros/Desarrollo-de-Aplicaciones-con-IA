# Biblioteca financiera y profesor RAG

InvestiQ consulta una biblioteca educativa local para responder preguntas generales sobre acciones, fondos, ETF, bolsas, índices, intermediarios, criptoactivos, indicadores e inversión. Contiene 119 documentos en 16 categorías. Los documentos están en `src/investiq/knowledge/data/`, versionados e incluidos en el paquete. No se descargan fuentes ni modelos de búsqueda al arrancar.

## Cómo responde

1. El router distingue una lección, una consulta de instrumento y una petición de datos de mercado.
2. La búsqueda local combina alias, preguntas de ejemplo y similitud de texto TF-IDF para recuperar unos pocos pasajes. Prioriza el sujeto de la pregunta y se abstiene si no encuentra evidencia suficiente.
3. Si NVIDIA está disponible, el profesor recibe la pregunta, el nivel, contexto reciente y esos pasajes. Genera párrafos con evidencias textuales vinculadas a los fragmentos.
4. Se validan referencias, spans, cifras, entidades y patrones de consejo, garantías o inyección. Una salida dudosa se sustituye por una explicación local con fuentes. Sin modelo se utiliza directamente ese respaldo local.

Las citas y comprobaciones léxicas son controles acotados: no prueban formalmente que toda paráfrasis sea correcta. La calidad con el modelo real requiere evaluación en el entorno conectado. Las rutas financieras conservan sus herramientas y bloques factuales protegidos.

## Probar desde consola

Desde la raíz, con el entorno instalado:

```bash
.venv/bin/python -m investiq.knowledge validate
.venv/bin/python -m investiq.knowledge stats
.venv/bin/python -m investiq.knowledge search 'qué brokers existen para invertir'
.venv/bin/python -m investiq.knowledge search 'en qué se diferencia un ETF de una acción'
.venv/bin/python -m investiq.knowledge search 'qué es un fondo de inversión'
.venv/bin/python -m investiq.knowledge search 'qué es una criptomoneda'
.venv/bin/python -m investiq.knowledge search 'qué mide el RSI'
```

Estos comandos validan y prueban la recuperación; no llaman al modelo ni a proveedores de mercado. Para conversar, ejecuta `bash run_web.sh` y abre `http://127.0.0.1:8000`.

Puedes preguntar «¿qué es una acción?», «¿cómo funciona la bolsa?», «¿qué brókers existen?», «¿qué son los dividendos?», «¿cómo funciona una orden límite?» o «¿a qué se dedica Apple?». «Un ejemplo», «más sencillo» y «más detalle» usan el contexto educativo. Las respuestas sobre países, impuestos o condiciones actuales explican los límites cuando la biblioteca no permite verificarlos.

«No entiendo», «¿Me lo explicas con un ejemplo?», «¿Cómo se interpreta?» y «¿Por qué importa?» también continúan el tema. Diálogo y búsqueda comparten el reconocimiento acotado de estas peticiones en `learning.py`; no eligen otro documento por palabras genéricas. Los riesgos o costes sin sujeto conservan el documento anterior. Un sujeto nuevo, como «¿Por qué importa la liquidez?», utiliza la búsqueda normal. Tras definir un instrumento, los seguimientos educativos usan su ficha y no consultan cotizaciones. La memoria conserva únicamente la identidad del tema; sin contexto suficiente se pide concretar.

En nivel principiante, el respaldo local incluye definición, ejemplo y cautelas. El generador recibe también el ejemplo revisado; simplificar una respuesta ajusta su nivel solo para ese turno. El catálogo de ejemplos locales es limitado y puede repetir un ejemplo al solicitar otro; no se promete variedad generada sin modelo.

## Contenido y fuentes

La biblioteca cubre fundamentos, fondos/ETF, índices, mercados, riesgos, planificación, operativa, costes, análisis, protección frente a fraude e instrumentos del catálogo. La ampliación incluye Bitcoin, Ethereum, blockchain, custodia, stablecoins, staking y contratos inteligentes; RSI, MACD, SMA/EMA, Bollinger, ATR, ADX, estocástico, OBV, CCI y VWAP; velas, soporte/resistencia, tamaño de posición, drawdown y backtesting. Incluye explicaciones, ejemplos y cautelas, con enlaces oficiales y fecha de revisión. [knowledge-sources.md](knowledge-sources.md) y [trading-sources.md](trading-sources.md) registran las fuentes y alcance de la revisión.

La pregunta «¿qué es mejor para obtener mayores rentabilidades a largo plazo: un ETF o acciones individuales?» tiene un documento propio que explica diversificación, concentración, costes y riesgo, sin ganador universal. No requiere tickers ni preferencias personales. Los indicadores se explican como herramientas de análisis con límites, sin convertir cruces o umbrales en órdenes de operación ni calcular sus valores actuales.

«¿Qué sectores lideran hoy?» sigue una ruta de actualidad separada. Pide el mercado si falta y puede utilizar FMP configurado para un snapshot completo de once sectores de NASDAQ; sin acceso o datos válidos reconoce el límite. La integración real sigue pendiente. La definición de liderazgo o rotación sectorial sí se explica desde la biblioteca, sin usarla como una tabla de rendimientos actuales. Dos ETF sectoriales no representan cobertura suficiente de todos los sectores. La consulta mixta con ETF/acciones atiende ambas preguntas y conserva sus fuentes. Noticias y exploración guiada utilizan rutas propias, descritas en [market-branches.md](market-branches.md); los artículos actuales no se añaden a este corpus.

Los nombres de brókers son ejemplos documentados, no un ranking. Disponibilidad, autorización, requisitos y costes pueden cambiar y dependen del país y de la entidad concreta. No se guardan precios, noticias recientes, rendimientos esperados ni recomendaciones personales como definiciones permanentes. Las fichas de empresas describen información básica de emisores; las cotizaciones siguen requiriendo sus fuentes de mercado.

## Añadir conocimiento

Crea o amplía un JSON de la biblioteca y valídalo antes de usarlo. No necesitas añadir una condición de Python por cada concepto. Cada documento tiene esta estructura:

```json
{
  "schema_version": 1,
  "documents": [{
    "id": "concepto-revisado",
    "title": "Título del concepto",
    "category": "fundamentos",
    "aliases": ["otra forma de nombrarlo"],
    "questions": ["Una pregunta habitual que responde"],
    "summary": "Definición breve escrita a partir de la fuente revisada.",
    "explanation": "Explicación propia que desarrolla el concepto con sus condiciones.",
    "example": "Un ejemplo didáctico identificado como tal, sin cotizaciones inventadas.",
    "cautions": "Límites, excepciones o precauciones respaldados por la fuente.",
    "related_ids": [],
    "sources": [{
      "source_id": "fuente-revisada",
      "title": "Título real de la fuente",
      "url": "https://organismo.example/documento",
      "provider": "Autor real",
      "reviewed_on": "2026-11-04"
    }]
  }]
}
```

El ejemplo de formato usa una URL ficticia: debe reemplazarse por el enlace HTTPS real que se haya consultado. No se debe cargar como contenido financiero. Comprueba que la fuente respalda cada afirmación, parafrasea respetando derechos de autor y revisa vigencia. `reviewed_on` es fecha de revisión del contenido, no publicación de la página. Un mismo `source_id` debe conservar metadatos coherentes; usa una nueva versión del identificador cuando corresponda.

Los IDs y títulos son únicos, las referencias relacionadas deben existir y los campos obligatorios no pueden estar vacíos. La validación comprueba estructura y coherencia; no acredita por sí sola la veracidad, vigencia ni pertinencia de una fuente. Reinicia la app tras cambiar los archivos porque el índice se conserva en memoria del proceso.

## Biblioteca externa revisada

Para utilizar una biblioteca propia sin modificar el paquete:

```bash
export INVESTIQ_KNOWLEDGE_PATH='/ruta/a/biblioteca-revisada'
.venv/bin/python -m investiq.knowledge validate
bash run_web.sh
```

La variable debe exportarse en esa consola; el cargador no la lee directamente de `.env`. El directorio o archivo JSON indicado **reemplaza** la biblioteca incluida. Mantén sus documentos y relaciones necesarios; si deseas ampliarla, copia primero los JSON incluidos y añade los nuevos allí. Ningún archivo recuperado se trata como una instrucción.

## Conectividad y memoria

La biblioteca, su validación, búsqueda y respuestas locales funcionan sin Internet. La generación NVIDIA requiere su conexión y credenciales. La biblioteca es independiente de SQLite, preferencias y recuerdos de la persona. El historial literal sigue temporal; la memoria persistente guarda solamente identidades de temas permitidas y el contexto estructurado, no documentos completos ni respuestas generadas.

Las decisiones están en [ADR-005](../decisions/ADR-005-profesor-rag-local.md); requisitos y evidencia en [specs/profesor-rag](../specs/profesor-rag/tasks.md), [formacion-trading](../specs/formacion-trading/tasks.md) y [continuidad-profesor](../specs/continuidad-profesor/tasks.md). Esta capacidad no inicia el despliegue de fase 5.
