# Diseño — Agente modular

## Responsabilidades

REQ-001: routing.py decide intención y normaliza cobertura; handlers.py ejecuta las tools y produce HandlerResult tipado; responses.py forma AssistantResponse/disclaimer; query_log.py guarda/purga trazas. orchestration.answer_query coordina esos componentes y la narración validada. Los handlers no importan clientes LLM, UI o registro de consultas. Se mantienen las decisiones ADR-001/002/003.

REQ-002: conversation.answer_turn es la fachada pública. dialogue/commands.py maneja controles de memoria/nivel, dialogue/state.py recuerda y limpia estado, dialogue/preference_flow.py coordina declaraciones/actualizaciones y dialogue/pending.py resuelve campos pendientes sin BD o red. La interpretación/validación conserva preferences/understanding/language. El cliente se resuelve de forma perezosa una sola vez por turno, incluyendo un intento fallido, y se pasa a answer_query con auto_client=False. El adaptador NIM convierte también errores del constructor del SDK en fallos seguros sin encadenar su contenido.

REQ-003: language.py comparte las reglas de preguntas y procedencia; instrumentos resuelve solo menciones inequívocas de catálogo. La evaluación independiente aporta escenarios de diálogo reproducibles antes de decidir correcciones. No se pretende demostrar naturalidad subjetiva con pruebas de estructura.

Las rutas pasan por routing.normalize_decision antes de ejecutar handlers. Estos reciben la decisión preparada y no dependen del router, el cliente LLM o el log. PendingField es el contrato único para los campos de aclaración y la memoria deriva de él su lista permitida.

REQ-004: documentación incluye mapa de responsabilidades y entradas públicas. Las pruebas cambian sus imports y mocks al componente que realmente posee el comportamiento; no se conserva acoplamiento privado solo para satisfacer mocks históricos. La memoria persistente continúa estructurada y no exige cambios de esquema.

## Skills y permisos

Se leyeron skill-creator y sdd-feature disponibles y se aplica su criterio de instrucciones acotadas, decisiones verificables y spec primero. La inicialización de investiq-agent-review en .agents/skills falló por protección de escritura; el permiso para crearla fue rechazado. No se reintenta por otra ruta ni se afirma registro/instalación. Las mejoras del producto usan las skills existentes y no dependen de esa instalación.

## Verificación

Regresión de todas las rutas, registro único/purga, aislamiento de handlers, reanudación/cancelación/memoria y creación única del cliente. Conversaciones educativas expresadas como aprendizaje y lenguaje ambiguo de símbolos. AppTest local y validadores SDD. NIM real y revisión cualitativa del tono quedan pendientes del entorno autorizado.
