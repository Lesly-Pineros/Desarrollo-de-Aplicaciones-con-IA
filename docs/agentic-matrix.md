# Matriz de workflows y herramientas agénticas

Comparación orientada a las necesidades del proyecto, no a una medición de rendimiento. Las capacidades concretas dependen de la versión y configuración instaladas.

| Criterio | Codex (elegido para desarrollar) | Agentes de IDE | Frameworks de grafo (p. ej., LangGraph en runtime) |
|---|---|---|---|
| Personalización | Instrucciones de repo (`AGENTS.md`), skills y agentes acotados versionables | Reglas y extensiones propias del IDE; portabilidad variable | Nodos, estado y transiciones definidos en código |
| Soporte MCP | Puede conectarse a herramientas MCP según configuración local | Depende del IDE y sus extensiones | Se integra mediante adaptadores/cliente MCP en la aplicación |
| Tool-calling | Herramientas del entorno de desarrollo con permisos configurables | Herramientas integradas al IDE | Llamadas explícitas desde nodos; el framework organiza el flujo |
| Control de contexto | Contexto de repo y reglas por directorio | Contexto del workspace abierto y funciones del IDE | Estado y contexto definidos por la aplicación |
| Costo | Depende del plan/modelo y uso de Codex | Depende del IDE y modelo/proveedor | El framework no elimina el costo del modelo ni de infraestructura |
| Encaje con SDD | Alto: instrucciones, skill de scaffolding y agente para TASK | Posible mediante plantillas y reglas, con formato dependiente del IDE | No sustituye requisitos, diseño, tareas ni trazabilidad |
| Madurez para este proyecto | Elegido para el flujo de trabajo de desarrollo del repo | Alternativa viable si el equipo ya trabaja en un IDE agéntico | Diferido en runtime: Python plano en v0.1; evaluar LangGraph en v0.2 según disparadores del ADR-001 |

## Decisión

Se elige Codex para el desarrollo porque el proceso SDD puede quedar versionado junto al proyecto y aplicarse por tarea. La matriz no afirma que sea superior en todos los equipos; la elección prioriza trazabilidad repo-céntrica.

En el runtime de InvestiQ, la decisión es distinta: v0.1 usa Python plano (router y tools deterministas). LangGraph queda para v0.2 si aparecen bucles con estado, checkpointing, estado compartido complejo o paralelismo que lo justifique, conforme a `decisions/ADR-001-orquestacion.md`.

## Skills, metodología y conversación

| Artefacto | Papel en InvestiQ | Estado |
|---|---|---|
| `.codex/skills/sdd-feature/` | Definir requisitos EARS, diseño, tareas y verificaciones antes de implementar | Disponible y utilizada |
| [Agent Skills](https://github.com/agentskills/agentskills) | Formato de instrucciones reutilizables para agentes de desarrollo | Referencia del formato; no es una skill concreta |
| Ejemplo externo `skill-creator` | Ayudar a crear o mantener otras skills | Descarga intentada, permiso de red rechazado; instalación pendiente |
| BMAD | Apoyo posible para UX, planificación y revisión, aprovechando el SDD existente | Evaluado; sin instalación ni dependencia del runtime |
| Taste, Emil e Impeccable | Diseño de la web local, detalles de interacción y revisión visual | Descargadas y utilizadas en `.local/design-skills/`; ignoradas por Git |
| `prompts/conversation.md`, estado y validadores | Voz del asistente, continuidad, contexto recordado y respuestas apoyadas en resultados verificables | Implementados en la app; ver specs y evidencias actuales |

La instalación anterior de `/.agents/skills/skill-creator/` sigue pendiente. Las tres skills de diseño sí están descargadas localmente; sus fuentes y límites se documentan en [design-skills.md](design-skills.md). Los planes, specs y pruebas del proyecto permanecen versionables. El estado real está en [PLAN.md](../PLAN.md); las simulaciones, el navegador local y las APIs externas se reportan por separado.
