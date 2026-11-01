# Tareas — validador de trazabilidad SDD

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-001 | Implementar el validador CLI de requisitos, referencias y verificaciones | REQ-001 | Unit: fixture válido, trazabilidad incompleta y documentos faltantes; smoke CLI | Completa |

## Trazabilidad

| REQ | TASK(s) | Evidencia de verificación esperada |
|---|---|---|
| REQ-001 | TASK-001 | `tests/unit/test_validate_spec.py`; solo archivos temporales locales |

## Evidencia ejecutada

- `/private/tmp/investiq-phase2-venv/bin/python -m pytest -q tests/unit/test_validate_spec.py`: 4 passed.
- `/private/tmp/investiq-phase2-venv/bin/python tools/validate_spec.py specs/fase0-sdd-validator`: `Spec SDD válida`.
- TASK-001 fue ejecutada por el subagente siguiendo `.codex/agents/dev-agent.md`.
