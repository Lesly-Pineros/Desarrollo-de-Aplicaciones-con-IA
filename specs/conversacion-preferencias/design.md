# Diseño — Conversación y preferencias en el chat

## Componentes y flujo

REQ-001/002: `conversation.answer_turn(session, user_id, query, settings, state, client=None)` coordina un `ConversationState` Pydantic por sesión, extracción determinista de preferencias y `answer_query`. Guarda la consulta pendiente y el campo solicitado; una respuesta corta completa ese campo y reanuda la tool original. Preguntas educativas pueden interrumpir el flujo. Solo se pregunta un dato a la vez y no se exige completar todo un perfil.

REQ-002: `preferences.py` normaliza sectores del catálogo y valida parches con `PreferenceInput`. Solo declaraciones explícitas o respuestas a una pregunta de preferencias se persisten en `UserPreference` bajo la identidad local existente. Filtros de recomendación no se guardan por sí solos. Los parches son atómicos, conservan criterios anteriores y admiten consulta/borrado. Omitir criterios devuelve comparación de features sin ranking personalizado.

REQ-003: Streamlit mantiene estado y mensajes en `session_state`. La sidebar explica el propósito y ofrece un selector informativo de símbolos/nombres de `INSTRUMENTS`. El chat incluye bienvenida, indicador de procesamiento y aclaraciones breves. Seleccionar un símbolo solo muestra ayuda para consultarlo.

REQ-004: la interfaz existente `answer_query` se conserva y acepta decisión/contexto opcionales. Se mantiene Python plano (ADR-001), clustering/umbrales deterministas (ADR-003) y ausencia de cambios de despliegue (ADR-002). La narración educativa puede recibir contexto acotado; las cifras y clasificaciones continúan renderizadas por código. Fuentes e historial son datos no confiables, no instrucciones.

## Estado y persistencia

- Estado de sesión: decisión pendiente, campo esperado, última decisión, preferencia ofrecida y últimos mensajes acotados. No se persiste historial en BD.
- `UserPreference`: criterios expresados, sin cambio de esquema ni credenciales.
- `QueryLog`: intención, herramientas, fuentes y estado; no texto de consulta.
- Entradas ambiguas o inválidas dejan preferencias intactas. Si NIM falla o no hay key, siguen disponibles preguntas y resolución deterministas.

## Verificación prevista

Diálogos offline con tools simuladas para reanudación, cambios de tema, persistencia de preferencias, omisión y errores. Smoke de Streamlit con SQLite temporal sin credenciales reales. Suite existente y validador SDD. No se consultan APIs live en esta feature.
