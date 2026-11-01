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
