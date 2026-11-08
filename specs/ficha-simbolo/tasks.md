# Tareas — Ficha individual de símbolo

| TASK | Descripción | REQ | Verificación |
|---|---|---|---|
| TASK-001 | Formatear cotización, métricas existentes, fechas y degradación para consultas individuales | REQ-001, REQ-002 | inspección de respuesta para cotización Twelve Data, fallback histórico y características ausentes/presentes |
| TASK-002 | Integrar la ficha común en catálogo y explicador sin perder noticias/SEC | REQ-003 | inspección de ambas rutas y sus fuentes; verificar que hechos/fuentes preservan disclaimer |
| TASK-003 | Añadir sugerencia inicial, pedir símbolo y resolver la ficha | REQ-004 | validate_spec.py; inspección del prompt general, selección válida y símbolo no cubierto |
| TASK-004 | Declarar cobertura estadounidense y frescura por tipo de dato | REQ-001, REQ-002, REQ-005 | inspección de mensajes con quote live, fallback histórico, caché vencida y features históricas |
| TASK-005 | Precargar el mensaje de métricas en el composer sin enviarlo | REQ-006 | selección del acceso directo, texto visible/foco en composer y ausencia de envío automático |
| TASK-006 | Resolver nombre empresarial a ticker cubierto; habilitar consulta individual KO sin alterar universo ML | REQ-003, REQ-007 | alias conocidos, variante «Jhonson», ambigüedad y desconocidos; inspección de ticker enviado a cotización y degradación sin features; API real no usada | Implementada; prueba local del flujo pendiente pasa |

## Trazabilidad

| REQ | TASK(s) | Evidencia de verificación esperada |
|---|---|---|
| REQ-001 | TASK-001, TASK-002 | Fuente, fecha, estado de cotización y fallback comunicados |
| REQ-002 | TASK-001, TASK-002 | Todos los campos de `instr_features` visibles o declarados ausentes |
| REQ-003 | TASK-002 | Ambas rutas comparten métricas y explicador conserva noticias/SEC |
| REQ-004 | TASK-003 | La sugerencia pregunta por un símbolo y una respuesta válida abre la ficha |
| REQ-005 | TASK-004 | Cotización y features tienen etiquetas correctas de origen/frescura |
| REQ-006 | TASK-005 | El acceso directo rellena el mensaje y espera a que la persona lo envíe |
| REQ-007 | TASK-006 | Nombre reconocido resuelve al ticker permitido; símbolos no cubiertos no se adivinan; KO no entra en el universo de clustering |
