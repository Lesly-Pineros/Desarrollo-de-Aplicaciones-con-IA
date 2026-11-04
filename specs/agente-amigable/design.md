# Diseño — Agente amigable

## Flujo y contratos

REQ-001: `prompts/conversation.md` se carga en el cliente NIM con importlib.resources y se incluye como package data. Educación conserva narración validada; otras rutas usan una plantilla del LLM que debe incluir `{{result}}` exactamente una vez. El renderizador inserta el resultado determinista original; rechaza cifras, instrumentos y URLs ajenos al marcador, citas no entregadas y consejos de operación. La depuración posterior limita las aperturas y cierres factuales a un catálogo controlado: una cita válida por sí sola no verifica afirmaciones financieras adicionales. La revisión live y evaluación de la narración educativa siguen siendo necesarias; el detalle de cambios está en specs/depuracion-agente.

REQ-002: nueva tabla `ConversationMemory`, independiente de QueryLog. `memory.load_memory/save_memory/set_memory_enabled/forget_memory` operan sobre `ConversationState` sanitizado: última decisión y operación pendiente solo con símbolos del catálogo, tema de glosario y nivel de explicación; history se excluye. La UI restaura al iniciar una sesión, muestra un resumen amigable y controles de recuerdo. Persistencia por identidad `local` y retención configurable; preferencias siguen en UserPreference y se borran con su propia acción explícita.

REQ-003: `understanding.PreferenceProposal` contiene cambios tipados y evidencia literal del mensaje. `semantic_preference_change` se usa solo ante declaraciones o respuestas de preferencias; valida significado canónico con evidencia y reglas de dominio, y devuelve un PreferenceChange atómico. El cliente añade `interpret_preferences` sin nuevas dependencias. Ningún contenido recuperado por tools entra como instrucción ni como declaración del usuario.

REQ-004: `ResponseDiagnostics` acota ruta/narración y motivos de fallback. Una tabla separada `ResponseTrace` relaciona categorías con QueryLog, evitando ALTER de tablas existentes. El comando live produce un informe de estado y métricas; no imprime excepciones originales ni conversaciones privadas. No usar la clave previamente expuesta sin confirmar rotación.

## Decisiones y límites

Se conservan ADR-001/002/003: orquestación Python plano, tools deterministas y ML existente, SQLite local. No se añade framework ni vector store. La memoria guarda estado estructurado, no un resumen LLM sin verificar. BMAD se considera para UX/revisión/evaluación de desarrollo; no es una dependencia del runtime.

## Verificación

Pruebas offline de narración con modelos simulados, evidencia textual y atomicidad, persistencia/restauración sin secretos, UI local y conversaciones con interrupciones. Comando live separado y opt-in para el entorno de ejecución conectado. Reportar resultados reales y limitaciones.

## Evaluación de BMAD (2026-11-04)

La [documentación oficial](https://docs.bmad-method.org/) describe skills para planificar, construir y revisar software; el [método](https://www.bmadcode.com/method) incluye UX, arquitectura y verificación. Nuestra valoración para InvestiQ es adoptarlo selectivamente como apoyo a diseño de experiencia y evaluación de conversaciones, aprovechando los requisitos EARS y ADR existentes. Instalarlo completo ahora añadiría artefactos de proceso que se superponen con SDD. La naturalidad se implementa en prompts, contexto y validación del runtime; no se añade BMAD como dependencia ni se instala en esta tarea.
