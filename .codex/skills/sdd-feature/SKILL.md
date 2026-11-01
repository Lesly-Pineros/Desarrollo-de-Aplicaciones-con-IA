---
name: sdd-feature
description: Andamia una especificación SDD de InvestiQ con requisitos EARS, diseño, tareas y trazabilidad. Úsala al iniciar una feature.
---

# Skill: especificación SDD de InvestiQ

Al recibir el nombre y contexto de una feature:

1. Lee `PLAN.md`, los ADR pertinentes y cualquier documentación existente de esa feature. Respeta la fase activa y no amplíes el alcance.
2. Crea `specs/<slug>/requirements.md`, `design.md` y `tasks.md` usando las plantillas de `specs/_templates/`.
3. En `requirements.md`, registra alcance, exclusiones, requisitos numerados `REQ-001...` con forma EARS (evento/estado/condición → el sistema deberá...) y criterios de aceptación observables. Incluye errores, degradación, fuentes y disclaimer cuando correspondan.
4. En `design.md`, relaciona cada requisito con componentes, contratos, datos, flujo, seguridad y decisiones aplicables. Distingue claramente comportamiento determinista y generación LLM.
5. En `tasks.md`, desglosa trabajo implementable como `TASK-001...`; cada fila debe enlazar uno o más REQ y una verificación concreta (unit, integration marcada, eval o procedimiento manual). No declares verificación ejecutada.
6. Añade al final de `requirements.md` un changelog inicial con fecha y resumen. No inventes aprobación: deja el estado como «Borrador».
7. Revisa que todo REQ tenga al menos una TASK y verificación, y que cada TASK enlace a un REQ. Resume rutas creadas, decisiones y dudas abiertas.

No implementes código ni ejecutes la feature salvo que el usuario lo pida expresamente. No generes la spec del piloto como parte del bootstrap: corresponde a la Fase 1.
