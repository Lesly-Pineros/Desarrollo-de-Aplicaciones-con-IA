# Arquitectura del agente de InvestiQ

El agente sigue la orquestación en Python de [ADR-001](../decisions/ADR-001-orquestacion.md), las reglas de ML de [ADR-003](../decisions/ADR-003-ml.md) y el alcance de [PLAN.md](../PLAN.md). La modularización se especifica en [specs/agente-modular](../specs/agente-modular/requirements.md). La organización busca que cada componente tenga una responsabilidad comprobable y que una corrección de diálogo no obligue a modificar las herramientas financieras.

## Entradas y responsabilidades

Los módulos de esta tabla están bajo `src/investiq/`.

| Componente | Responsabilidad |
|---|---|
| `web/server.py` | HTTP local y API del mismo origen, validación y recursos estáticos permitidos. |
| `web/service.py`, `web/sessions.py` | Adaptación al agente, controles de memoria y sesiones temporales acotadas. |
| `web/static/` | Web HTML/CSS/JS, catálogo, chat y tipografías locales. |
| `app.py` | Interfaz Streamlit heredada, disponible como alternativa local. |
| `conversation.py` · `answer_turn` | Fachada de cada turno: coordina controles, preferencias, aclaraciones y consulta de dominio. |
| `dialogue/commands.py` | Comandos de memoria, nivel de explicación y controles conversacionales. |
| `dialogue/state.py` | Actualización del contexto del turno y limpieza de la consulta pendiente. |
| `dialogue/pending.py` | Resolución de campos pendientes y transiciones de contexto mediante lógica pura. |
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

Los contratos de entrada y salida se expresan en `domain.py`. Los handlers se concentran en ejecutar las herramientas; la creación del cliente LLM, la interfaz y el registro de consultas corresponden a sus componentes coordinadores.

## Flujo de un turno

1. La web envía el mensaje a su API local. El servicio obtiene una sesión de base propia y entrega el estado a `answer_turn`; Streamlit conserva su adaptador directo. Los controles de memoria y nivel se atienden antes de una consulta financiera.
2. El flujo de preferencias valida si el mensaje expresa un criterio de la persona. Una pregunta educativa, una cita o un texto de terceros conserva su procedencia. Una aclaración pendiente puede completarse con una respuesta corta; un cambio de tema actualiza el contexto.
3. Cuando hace falta una consulta de dominio, `answer_query` obtiene la ruta y ejecuta su handler. Las herramientas aportan datos y referencias; los cálculos financieros permanecen deterministas.
4. La narración opcional usa el resultado de las herramientas. En respuestas financieras, el bloque factual protegido se conserva y la validación controla el texto añadido. Si falla la redacción, se utiliza la respuesta de respaldo.
5. La construcción de la respuesta añade «No es asesoría financiera». El registro de la consulta guarda sus metadatos una sola vez y aplica la retención; la conversación actualiza el estado y su recuerdo permitido.

El cliente de lenguaje se resuelve cuando una operación lo necesita, con un solo intento de creación por turno. Ese resultado se reutiliza al pasar a la orquestación, incluso si la creación falló. Las dependencias se pasan entre funciones de Python; añadir módulos no exige introducir un framework ni precargar servicios externos.

## Contexto, memoria y trazabilidad

| Información | Ubicación y uso |
|---|---|
| Historial literal visible | Sesión temporal del servidor web asociada a cookie; hasta 80 mensajes y dos horas de inactividad. La alternativa Streamlit conserva su propia sesión. |
| Tema, símbolos, campo pendiente y nivel | Recuerdo opcional estructurado en la base, sanitizado y con expiración configurable. |
| Preferencias explícitas | Registro de preferencias bajo la identidad `local`, compartida por esa instalación. |
| Intención, herramientas, fuentes y consumo disponible | `QueryLog`, con purga según retención; excluye el texto de la consulta. |
| Categorías de ruta, narración y respaldo | `ResponseTrace`, para diagnóstico de desarrollo. |

El chat permite consultar o borrar el contexto y gestionar las preferencias por separado. Cada copia de desarrollo o ejecución mantiene su propia base; copiar el código no sincroniza su memoria. Las noticias, filings y otros textos recuperados se procesan como datos no confiables.

## Añadir o corregir una capacidad

Empieza por requisitos, diseño y tareas en `specs/<feature>/`, con trazabilidad a su verificación. Decide qué componente posee el comportamiento: una aclaración pertenece a diálogo; una intención a routing; una consulta o cálculo a una herramienta y su handler; la forma de expresarlo a la capa de respuesta.

Para una nueva capacidad de dominio, define el contrato y sus fuentes, implementa la herramienta determinista y devuelve su resultado mediante un handler. Conecta la intención en routing y la selección en `execute_query`. Si necesita datos adicionales de la persona, representa la aclaración en el estado y resuelve su continuación en diálogo. Mantén la obtención de datos en las herramientas y la coordinación en las fachadas.

Para mejorar el tono, ajusta las instrucciones y el estilo sobre escenarios concretos de conversación. Una petición de aprender debe generar una explicación; guardar una preferencia exige evidencia del mensaje de la persona. El modelo puede redactar, mientras que precios, métricas, similitudes y citas conservan la procedencia de las herramientas. El tamaño de un archivo se revisa junto con la cohesión de sus responsabilidades, sin imponer cortes artificiales por cantidad de líneas.

Verifica el cambio en el componente que lo posee: rutas, resultados de handlers con proveedores simulados, transiciones de diálogo o validación de narración. Revisa además que una consulta se registre una sola vez, que no se guarde texto sensible y que la respuesta mantenga su disclaimer. Actualiza las pruebas que dependían de imports privados para utilizar la API del módulo responsable.

## Verificación y límites

El [README](../README.md#validar-sin-acceder-a-proveedores-reales) mantiene los comandos de regresión, validación SDD y diagnóstico. Los resultados vigentes están en [PLAN.md](../PLAN.md) y [specs/agente-modular/tasks.md](../specs/agente-modular/tasks.md).

Las pruebas offline comprueban lógica local, proveedores simulados, servicio/API web y Streamlit mediante AppTest. La revisión en Chrome comprueba la web renderizada y sus interacciones con una base temporal. La integración con NVIDIA y la evaluación cualitativa del tono requieren el entorno conectado y su activación explícita. Un resultado offline no demuestra el comportamiento del modelo real. Las [skills de diseño](design-skills.md) ayudan a desarrollar y revisar estos componentes; no se cargan como dependencia del agente.

El frontend local sigue [ADR-004](../decisions/ADR-004-web-local.md). La API usa la biblioteca estándar en el mismo proceso Python. Las sesiones temporales se bloquean por conversación; la memoria y preferencias persistentes siguen compartidas por instalación. El servidor permite solo loopback y exige origen local en POST; no ofrece autenticación ni un servicio público.
