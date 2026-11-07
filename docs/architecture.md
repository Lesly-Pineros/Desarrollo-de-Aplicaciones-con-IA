# Arquitectura del agente de InvestiQ

El agente sigue la orquestación en Python de [ADR-001](../decisions/ADR-001-orquestacion.md), las reglas de ML de [ADR-003](../decisions/ADR-003-ml.md) y el alcance de [PLAN.md](../PLAN.md). La modularización se especifica en [specs/agente-modular](../specs/agente-modular/requirements.md). La organización busca que cada componente tenga una responsabilidad comprobable y que una corrección de diálogo no obligue a modificar las herramientas financieras.

## Entradas y responsabilidades

Los módulos de esta tabla están bajo `src/investiq/`.

| Componente | Responsabilidad |
|---|---|
| `web/server.py` | HTTP local y API del mismo origen, validación y recursos estáticos permitidos. |
| `web/service.py`, `web/sessions.py` | Adaptación al agente, controles de memoria y sesiones temporales acotadas. |
| `web/static/` | Web HTML/CSS/JS, catálogo, chat y tipografías locales. |
| `conversation.py` · `answer_turn` | Fachada de cada turno: coordina controles, preferencias, aclaraciones y consulta de dominio. |
| `dialogue/commands.py` | Comandos de memoria, nivel de explicación y controles conversacionales. |
| `dialogue/state.py` | Actualización del contexto del turno y limpieza de la consulta pendiente. |
| `dialogue/pending.py` | Resolución de campos pendientes y transiciones de contexto mediante lógica pura. |
| `dialogue/exploration.py` | Preguntas y criterios de una exploración de acciones/ETF, sin escribir preferencias. |
| `learning.py` | Reconocimiento compartido de aclaraciones, ejemplos y otras peticiones educativas sin sujeto nuevo. |
| `dialogue/preference_flow.py` | Coordinación de interpretación y actualización de preferencias. |
| `preferences.py`, `understanding.py`, `language.py` | Validación de preferencias, propuestas semánticas y reglas compartidas de procedencia del mensaje. |
| `memory.py` | Lectura, escritura, expiración y borrado del recuerdo estructurado entre visitas. |
| `orchestration.py` · `answer_query` | Coordinación de ruta, ejecución, narración validada y registro único de la consulta. |
| `routing.py` · `route_query`, `fallback_route` | Clasificación y normalización de la intención, con respaldo local. |
| `handlers.py` · `HandlerResult`, `execute_query` | Rutas de dominio, incluidas definiciones del catálogo, y devolución de texto, hechos, fuentes y herramientas utilizadas. |
| `responses.py` · `make_response`, `DISCLAIMER` | Construcción de la respuesta pública y aplicación del disclaimer. |
| `query_log.py` · `record_response`, `purge_query_logs` | Registro de metadatos y aplicación de la retención. |
| `response_style.py`, `prompts/`, `llm.py` | Guía de tono, narración opcional y validación de la salida del modelo. |
| `tools.py`, `providers/`, `ml/`, `data/` | Consulta de fuentes, cálculos deterministas, similitud por clustering y persistencia. |
| `knowledge/` | Modelos, biblioteca JSON revisada, búsqueda TF-IDF/alias y CLI sin red. |
| `tutor/` | Generación educativa estructurada, validación de evidencias y explicaciones locales de respaldo. |
| `education.py` | Fachada de temas y definiciones sobre la biblioteca, compatible con las herramientas existentes. |
| `sector_context.py` | Detección de actualidad sectorial, mercado canónico, separación de preguntas mixtas y límites de cobertura. |
| `news_context.py`, `newsroom.py` | Filtros de noticias, selección temporal, traducción/resumen estructurados y fuentes. |
| `providers/headlines.py`, `providers/sectors.py` | Marketaux por día/filtros y snapshots FMP completos por fecha/bolsa, con cachés y cuotas. |
| `ml/exploration.py` | Selección pura de candidatos mediante scaler/KMeans aprobado y filtros deterministas. |

Los contratos de entrada y salida se expresan en `domain.py`. Los handlers se concentran en ejecutar las herramientas; la creación del cliente LLM, la interfaz y el registro de consultas corresponden a sus componentes coordinadores.

La biblioteca separa conceptos educativos de datos de mercado y de memoria personal. Contiene 119 documentos en 16 categorías, incluidas las 20 fichas del catálogo, con fuentes y fecha de revisión. S&P 500 y SPY conservan documentos distintos. La búsqueda es léxica y por similitud TF-IDF local; no se presenta como un modelo de embeddings neuronal. Detalles y mantenimiento en [knowledge.md](knowledge.md).

## Flujo de un turno

1. La web envía el mensaje a su API local. El servicio obtiene una sesión de base propia y entrega el estado a `answer_turn`. Los controles de memoria y nivel se atienden antes de una consulta financiera.
2. El flujo de preferencias valida si el mensaje expresa un criterio de la persona. Una pregunta educativa, una cita o un texto de terceros conserva su procedencia. Una aclaración pendiente puede completarse con una respuesta corta; un cambio de tema actualiza el contexto.
3. Cuando hace falta una consulta de dominio, `answer_query` obtiene la ruta. Para educación llama al tutor: este recupera pasajes y opcionalmente los entrega a `ChatNVIDIAClient.teach`; los handlers ejecutados directamente conservan la respuesta educativa determinista. Para mercado, las herramientas aportan datos y referencias y los cálculos permanecen deterministas.
4. La generación educativa produce párrafos con evidencia literal y referencias a los pasajes suministrados. Se comprueban citas, spans, cifras, entidades y patrones de riesgo; la validación no garantiza verdad semántica. Sin evidencia se reconoce el límite; sin modelo o ante salida dudosa se usa una explicación local revisada. La narración de mercado conserva su bloque factual protegido y conectores controlados, sin adoptar el contrato educativo más flexible.
5. La construcción de la respuesta añade «No es asesoría financiera». El registro de la consulta guarda sus metadatos una sola vez y aplica la retención; la conversación actualiza el estado y su recuerdo permitido.

El cliente de lenguaje se resuelve cuando una operación lo necesita, con un solo intento de creación por turno. Ese resultado se reutiliza al pasar a la orquestación, incluso si la creación falló. Las dependencias se pasan entre funciones de Python; añadir módulos no exige introducir un framework ni precargar servicios externos.

`sector_performance` distingue «qué sectores lideran hoy» de una definición de rotación sectorial. El estado pendiente `sector_market` acepta una respuesta corta y persiste solo un mercado permitido. Para Estados Unidos, el adaptador FMP opcional valida once sectores de NASDAQ en la fecha de Nueva York y ordena la variación diaria media; declara que esa bolsa no representa todo el país. La hora de consulta no se convierte en hora del proveedor. Sin acceso, cobertura o datos actuales devuelve estado degradado, sin cifras ni líderes inventados. No construye un cliente para narrar datos ausentes. Si el mensaje contiene también una pregunta educativa, la orquestación conserva su lección y fuentes además de las del snapshot. Detalles en [actualidad-mercados](../specs/actualidad-mercados/tasks.md).

`market_news` precede a la detección de liderazgo sectorial. Marketaux recibe filtros documentados y límites UTC del día según zona IANA; la cuota se comparte con las noticias por símbolo. La caché diaria vive en la tabla nueva `MarketContextCache`, sin cambios destructivos de las tablas existentes. `newsroom` solicita a NVIDIA una reescritura estructurada acotada a un intento y valida IDs, citas originales, cifras y patrones de riesgo. Los textos son datos no confiables; el resumen solo tiene el extracto recibido. Ante error se conserva el original.

`explore` es una consulta educativa distinta de guardar preferencias. El diálogo pregunta criterios faltantes y admite interrupción educativa/cancelación. El corto plazo devuelve una explicación de límites. Para otros plazos, la herramienta exige artefacto aprobado, período/universo coherentes y huella de features cuando existe. El scaler y KMeans intervienen en las distancias/orden; tipo, sector y terciles son filtros deterministas. La respuesta muestra métricas históricas y fuentes mediante el bloque factual protegido. Diseño en [exploracion-guiada](../specs/exploracion-guiada/design.md).

La web muestra accesos persistentes y botones para resumir noticias. `AssistantResponse.actions` conserva etiqueta, mensaje natural y `news_id` oculto. `/api/chat` admite ese identificador validado además de `message`; la selección debe existir en el estado temporal y no provoca descarga de URLs. El historial muestra el mensaje natural. Una selección antigua que ya no está en el listado no se aplica a otra noticia.

## Contexto, memoria y trazabilidad

| Información | Ubicación y uso |
|---|---|
| Historial literal visible | Sesión temporal del servidor web asociada a cookie; hasta 80 mensajes y dos horas de inactividad. |
| Tema, símbolos, campo pendiente y nivel | Recuerdo opcional estructurado en la base, sanitizado y con expiración configurable. |
| Criterios de exploración y filtros de noticias | Valores canónicos de la consulta; no equivalen a preferencias financieras guardadas. |
| Hasta tres noticias y sus selecciones | Estado temporal de la sesión; se excluyen de memoria persistente y RAG. |
| Preferencias explícitas | Registro de preferencias bajo la identidad `local`, compartida por esa instalación. |
| Intención, herramientas, fuentes y consumo disponible | `QueryLog`, con purga según retención; excluye el texto de la consulta. |
| Categorías de ruta, narración y respaldo | `ResponseTrace`, para diagnóstico de desarrollo. |

El chat permite consultar o borrar el contexto y gestionar las preferencias por separado. Cada copia de desarrollo o ejecución mantiene su propia base; copiar el código no sincroniza su memoria. Las noticias, filings y otros textos recuperados se procesan como datos no confiables.

Los temas nuevos se guardan en memoria mediante títulos canónicos de documentos permitidos, sin preguntas literales ni párrafos generados. Preguntas de brókers por país o tarifas actuales conservan el contexto y muestran el límite de la biblioteca estática; no se infieren autorización, disponibilidad ni costes vigentes. Los documentos se actualizan mediante revisión editorial y reinicio del índice de proceso.

Las peticiones breves del profesor comparten interpretación entre diálogo, recuperación y respuesta local. «No entiendo» o «¿Por qué importa?» usan el tema revisado anterior; una pregunta con otro sujeto se busca de nuevo y puede abstenerse. Tras `instrument_info`, una petición educativa continúa desde su ficha sin heredar una consulta de precios. El nivel básico incluye significado y ejemplo; las peticiones de interpretación siguen priorizando la explicación. Diseño y regresiones en [continuidad-profesor](../specs/continuidad-profesor/tasks.md).

## Añadir o corregir una capacidad

Empieza por requisitos, diseño y tareas en `specs/<feature>/`, con trazabilidad a su verificación. Decide qué componente posee el comportamiento: una aclaración pertenece a diálogo; una intención a routing; una consulta o cálculo a una herramienta y su handler; la forma de expresarlo a la capa de respuesta.

Para una nueva capacidad de dominio, define el contrato y sus fuentes, implementa la herramienta determinista y devuelve su resultado mediante un handler. Conecta la intención en routing y la selección en `execute_query`. Si necesita datos adicionales de la persona, representa la aclaración en el estado y resuelve su continuación en diálogo. Mantén la obtención de datos en las herramientas y la coordinación en las fachadas.

Para mejorar el tono, ajusta las instrucciones y el estilo sobre escenarios concretos de conversación. Una petición de aprender debe generar una explicación; guardar una preferencia exige evidencia del mensaje de la persona. El modelo puede redactar, mientras que precios, métricas, similitudes y citas conservan la procedencia de las herramientas. El tamaño de un archivo se revisa junto con la cohesión de sus responsabilidades, sin imponer cortes artificiales por cantidad de líneas.

Verifica el cambio en el componente que lo posee: rutas, resultados de handlers con proveedores simulados, transiciones de diálogo o validación de narración. Revisa además que una consulta se registre una sola vez, que no se guarde texto sensible y que la respuesta mantenga su disclaimer. Actualiza las pruebas que dependían de imports privados para utilizar la API del módulo responsable.

## Verificación y límites

El [README](../README.md#validar-sin-acceder-a-proveedores-reales) mantiene los comandos de regresión, validación SDD y diagnóstico. Los resultados vigentes están en [PLAN.md](../PLAN.md) y [specs/agente-modular/tasks.md](../specs/agente-modular/tasks.md).

Las pruebas offline comprueban lógica local, proveedores simulados y el servicio/API web. La revisión en Chrome comprueba la web renderizada y sus interacciones con una base temporal. La integración con NVIDIA y la evaluación cualitativa del tono requieren el entorno conectado y su activación explícita. Un resultado offline no demuestra el comportamiento del modelo real. Las [skills de diseño](design-skills.md) ayudan a desarrollar y revisar estos componentes; no se cargan como dependencia del agente.

El frontend local sigue [ADR-004](../decisions/ADR-004-web-local.md). La API usa la biblioteca estándar en el mismo proceso Python. Las sesiones temporales se bloquean por conversación; la memoria y preferencias persistentes siguen compartidas por instalación. El servidor permite solo loopback y exige origen local en POST; no ofrece autenticación ni un servicio público.
