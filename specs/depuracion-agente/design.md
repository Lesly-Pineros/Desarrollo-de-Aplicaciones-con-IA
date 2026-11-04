# Diseño — Depuración del agente

## Componentes y contratos

- REQ-001: módulo de lenguaje compartido para normalización, detección de preguntas y procedencia. Los parsers de preferencias lo consultan antes de proponer cualquier escritura; se conserva la evidencia literal del parser semántico.
- REQ-002: campos pendientes tipados, incluyendo beta. Una nueva petición completa reemplaza símbolos antiguos; una respuesta breve completa la operación anterior. El router prioriza preguntas sobre conceptos del glosario frente a menciones incidentales de precio.
- REQ-003: el renderer factual valida {{result}} y un catálogo cerrado de aperturas/cierres, compartido con el prompt del modelo. No basta buscar cifras o palabras prohibidas para demostrar que una afirmación está respaldada. Educación sigue su contrato existente.
- REQ-004: database_url reutiliza Settings, igual que la UI. El shell usa primero INVESTIQ_PYTHON, después .venv y finalmente Python disponible, siempre desde la raíz del script.
- REQ-005: README es la entrada de comandos; documentos específicos amplían sin contradecirlo. No cambia ninguna fase de despliegue ni las ADR.

## Skill y límites de autorización

Agent Skills es un formato/especificación, no una dependencia de la app. La instalación externa con skill-installer requiere red y fue rechazada; no se reintenta por un canal alternativo. Se conserva pendiente y se usa el flujo sdd-feature ya existente para esta revisión local. Se reserva una exclusión exacta en Git, sin ocultar toda .agents o .codex.

## Verificación

Regresiones de preferencias preguntadas/citadas, nueva comparación, beta corta/reinicio y prosa no respaldada; SQLite temporal para .env y prioridad del entorno; lanzador con Python simulado desde otro cwd; smoke UI, suite offline completa, validación SDD y comprobación de gitignore. No se ejecutan servicios reales ni se imprimen secretos.
