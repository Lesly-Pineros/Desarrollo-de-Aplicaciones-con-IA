# Diseño — Exploración guiada

REQ-001: intención `explore` y campos tipados en RouterDecision para tipo, plazo y sector, reutilizando volatilidad/referencia. El componente `dialogue/exploration.py` mantiene aclaraciones en el estado pendiente existente y pregunta un criterio a la vez; las respuestas solo parametrizan esta consulta, sin escribir UserPreference. Campos permitidos se conservan en la memoria estructurada; las interrupciones educativas no destruyen la consulta pendiente. El corto plazo devuelve cautela específica desde el documento educativo de horizonte, sin candidatos presentados como solución de liquidez.

REQ-002: función pura en `ml/exploration.py` transforma features con el scaler y KMeans del artefacto aprobado. Filtra universo, tipo, volatilidad por umbrales y sector declarados. Puntúa centralidad de clúster (distancia normalizada al centro) o distancia a referencia, con orden determinista. No entrena ni consulta Internet. La herramienta en `tools.py` obtiene artefacto, features y período de una ejecución aprobada; valida disponibilidad y coherencia y devuelve resultados estructurados. No usa un mock de rankings en producción.

REQ-003: handler determinista representa tabla y criterios, período, fecha de cálculo, fuentes locales y límite histórico. El nivel de volatilidad es una preferencia para explorar, no un diagnóstico de perfil. Plazo y tipo no alteran métricas. Narración opcional mantiene el bloque factual protegido existente. Errores no revelan rutas locales completas ni excepciones del proveedor.

REQ-004: botón persistente en web envía la intención por el mismo chat. Sin formularios nuevos. Pruebas con KMeans real entrenado sobre datos sintéticos etiquetados como fixture, modelos aprobados/rechazados, criterios completos/incompletos, interrupción y regreso. ADR-001/003/004/005 conservadas; módulos Python y estado acotado bastan, por lo que LangGraph no aporta una necesidad actual.

REQ-005: ajustar el texto de cada aclaración para ofrecer ejemplos de respuestas breves sin cambiar el contrato tipado ni persistir preferencias. El símbolo se mantiene opcional y la selección/cálculo de cifras sigue siendo determinista; solo la redacción final puede usar NVIDIA.

REQ-006: el acceso y sugerencia «Recomendaciones guiadas» envían un prompt reconocido por `resolve_exploration`; reutilizan conversación, estado pendiente, modelo aprobado y representación de métricas. La navegación conserva accesos independientes a noticias y al snapshot sectorial NASDAQ; las sugerencias iniciales conducen a esos mismos tres modos.
