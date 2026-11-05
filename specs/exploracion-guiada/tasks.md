# Tareas — Exploración guiada

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-001 | Contratos y preguntas/criterios conversacionales con memoria sanitizada | REQ-001, REQ-004 | test_guided_exploration.py: varios turnos/restauración, criterios completos, educación, cancelación, negación y preferencias intactas | Completa offline |
| TASK-002 | Selección con scaler/KMeans aprobado y filtros deterministas | REQ-002, REQ-003 | Modelo real entrenado sobre fixture sintético; distancias/orden, filtros, referencia y rechazo de datos/modelo inválidos | Completa offline |
| TASK-003 | Handler con métricas, período, fuentes y narración protegida | REQ-001, REQ-002, REQ-003 | Ratios como porcentaje, período, fuentes, modelo ausente, corto plazo sin ranking y huella de features | Completa offline |
| TASK-004 | Acceso web y documentación/verificación final | REQ-001, REQ-002, REQ-003, REQ-004 | 704 pruebas offline, 93 checks Chrome, quince specs, wheel, README/PLAN y diff --check | Completa local; NVIDIA real pendiente |

## Trazabilidad

| REQ | TASK(s) | Evidencia prevista |
|---|---|---|
| REQ-001 | TASK-001, TASK-003, TASK-004 | Criterios por chat sin formulario ni perfil inferido |
| REQ-002 | TASK-002, TASK-003, TASK-004 | Participación del modelo entrenado en candidatos |
| REQ-003 | TASK-002, TASK-003, TASK-004 | Porcentajes, fechas y fuentes deterministas |
| REQ-004 | TASK-001, TASK-004 | Web operativa y profesor sin regresiones |

## Evidencia ejecutada — 2026-11-04

La [evidencia compartida de actualidad](../actualidad-mercados/tasks.md) registra los comandos y resultados de la entrega conjunta: **704 pruebas offline**, **93 comprobaciones Chrome**, **quince specs válidas** y wheel verificado fuera del checkout. El corpus conserva 119 documentos/16 categorías/113 referencias; no se añadieron métricas o noticias ficticias al producto.

`tests/unit/test_guided_exploration.py` entrena un **KMeans real sobre características sintéticas** y registra artefacto/features en SQLite temporal. Comprueba el efecto de sus distancias en el orden, filtros de tipo/sector/tercil, referencia opcional, transformación a porcentaje, período, fuentes, restauración de las preguntas y preferencias financieras intactas. Datos incompletos/NaN, artefacto rechazado, timestamp posterior al modelo y valores que incumplen la huella se rechazan. Un sector no cubierto se aclara; negaciones no se convierten en el criterio contrario. El corto plazo no llama al ranking.

Chrome ejercita el acceso visible, varias preguntas y la tabla generada por ese modelo en una segunda base temporal, con artifacts también temporales. Se revisó `mobile-exploration-offline-fixture.png`: tabla desplazable, fuentes y compositor accesibles, sin desbordamiento de página. La selección de noticias y el snapshot sectorial tienen recorridos separados. Las capturas son evidencia de fixtures, no una recomendación actual ni una integración de proveedores reales.

Se conservan los tests del profesor, memoria, procedencia, mercado y narración factual protegida. Las verificaciones no hicieron ingesta/entrenamiento con datos reales ni tocaron modelos/base del usuario. La construcción del wheel incluye el módulo de selección, diálogo, providers y assets actuales. Python plano y el cliente NVIDIA existente bastan; no se introdujo LangGraph.

## Límites

La herramienta clasifica/ordena características históricas, no prevé retornos. El score de distancia y el tercil no determinan un perfil financiero completo ni la conveniencia de invertir hoy. El horizonte es declarado y no altera los cálculos. Una instalación necesita datos y artefacto coherentes; las claves o disponibilidad del LLM no sustituyen esa preparación. NVIDIA real y las APIs nuevas siguen pendientes; sin despliegue/fase 5.
