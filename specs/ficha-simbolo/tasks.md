# Tareas — Ficha individual de símbolo

| TASK | Descripción | REQ | Verificación |
|---|---|---|---|
| TASK-001 | Formatear cotización, métricas existentes, fechas y degradación para consultas individuales | REQ-001, REQ-002 | inspección de respuesta para cotización Twelve Data, fallback histórico y características ausentes/presentes |
| TASK-002 | Integrar la ficha común en catálogo y explicador sin perder noticias/SEC | REQ-003 | inspección de ambas rutas y sus fuentes; verificar que hechos/fuentes preservan disclaimer |
| TASK-003 | Añadir sugerencia inicial, pedir símbolo y resolver la ficha | REQ-004 | validate_spec.py; inspección del prompt general, selección válida y símbolo no cubierto |
| TASK-004 | Declarar cobertura estadounidense y frescura por tipo de dato | REQ-001, REQ-002, REQ-005 | inspección de mensajes con quote live, fallback histórico, caché vencida y features históricas |

## Trazabilidad

| REQ | TASK(s) | Evidencia de verificación esperada |
|---|---|---|
| REQ-001 | TASK-001, TASK-002 | Fuente, fecha, estado de cotización y fallback comunicados |
| REQ-002 | TASK-001, TASK-002 | Todos los campos de `instr_features` visibles o declarados ausentes |
| REQ-003 | TASK-002 | Ambas rutas comparten métricas y explicador conserva noticias/SEC |
| REQ-004 | TASK-003 | La sugerencia pregunta por un símbolo y una respuesta válida abre la ficha |
| REQ-005 | TASK-004 | Cotización y features tienen etiquetas correctas de origen/frescura |
