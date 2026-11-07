# Diseño — Exploración guiada

REQ-001/005: `dialogue/exploration.py` extrae tipo, plazo, volatilidad y sector de cada mensaje. Si faltan campos obligatorios, devuelve el conjunto completo de campos pendientes en una sola transición; `conversation.py` pide una sola redacción natural al LLM, con un fallback local. No se usan negaciones genéricas para resetear criterios. El símbolo de referencia es opcional. Las interrupciones educativas no destruyen la consulta pendiente; el corto plazo conserva su cautela educativa.

REQ-002: función pura en `ml/exploration.py` transforma features con el scaler y KMeans del artefacto aprobado. Filtra universo, tipo, volatilidad por umbrales y sector declarados. Puntúa centralidad de clúster (distancia normalizada al centro) o distancia a referencia, con orden determinista. No entrena ni consulta Internet. La herramienta en `tools.py` obtiene artefacto, features y período de una ejecución aprobada; valida disponibilidad y coherencia y devuelve resultados estructurados. No usa un mock de rankings en producción.

REQ-003: handler determinista representa tabla y criterios, período, fecha de cálculo, fuentes locales y límite histórico. El nivel de volatilidad es una preferencia para explorar, no un diagnóstico de perfil. Plazo y tipo no alteran métricas. Narración opcional mantiene el bloque factual protegido existente. Errores no revelan rutas locales completas ni excepciones del proveedor.

REQ-004/006/007: botón persistente envía una acción de inicio (`start_recommendations`), sin burbuja de usuario ni prompt prefabricado. `WebService` crea la aclaración del asistente y guarda el estado; la siguiente respuesta libre de la persona se interpreta en `resolve_exploration`. ADR-001/003/004/005 conservadas; módulos Python y estado acotado bastan.

REQ-005: ajustar el texto de cada aclaración para ofrecer ejemplos de respuestas breves sin cambiar el contrato tipado ni persistir preferencias. El símbolo se mantiene opcional y la selección/cálculo de cifras sigue siendo determinista; solo la redacción final puede usar NVIDIA.

REQ-006/007: el acceso y sugerencia «Recomendaciones guiadas» envían la acción `start_recommendations`; no agregan burbuja de usuario. El backend inicia estado pendiente y formula en una intervención natural los criterios obligatorios que falten, usando el modelo configurado o una alternativa local. La siguiente respuesta libre se interpreta por `resolve_exploration`; las demás sugerencias conducen a noticias y snapshot sectorial NASDAQ.

REQ-008: el handler detecta únicamente si el mensaje menciona un monto, sin registrar ni convertir su valor; añade una nota fija de transparencia que aclara que el ranking no incorpora presupuesto.
