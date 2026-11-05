# Diseño — Formación de inversión y trading

REQ-001 y REQ-002: nuevo JSON en knowledge/data con documentos propios en español, alias, preguntas y fuentes por tema; se mantiene el formato de ADR-005. Recuperación local de indicadores por nombre/acrónimo y de comparaciones conceptuales. Los ejemplos son conceptuales y no se convierten en reglas de operación.

REQ-003: intención `sector_performance` y campo `sector_market` permiten separar actualidad sectorial de educación. Un componente puro identifica la consulta, normaliza el mercado y produce una explicación de límites cuando falta información actual. No hay un proveedor de cobertura sectorial completa: por ello la respuesta es degradada y no presenta un ranking. La memoria solo conserva mercado canónico/campo pendiente, nunca noticias ni datos obsoletos. Preguntas de definición sobre sectores o rotación siguen usando la biblioteca.

En consultas mixtas, la parte educativa se recupera por separado y se combina con la aclaración/límite de actualidad. Se evita que el clasificador sustituya esta ruta por conocimiento estático. No se narran cifras de mercado sin evidencia.

REQ-004: pruebas con biblioteca real, modelo simulado donde proceda y proveedores de mercado bloqueados; verificación de las preguntas exactas, seguimiento y contraste entre conceptos e información actual. Fuentes de contenido consultadas durante desarrollo, sin llamar a las APIs financieras del usuario.

Se conservan ADR-001/003/004/005, el frontend web y el alcance single-user. Fase 5 no iniciada.
