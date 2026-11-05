# ADR-005 — Biblioteca educativa local y generación con evidencia

- **Estado:** Aceptado para la ampliación educativa solicitada.
- **Fecha:** 2026-11-04.
- **Contexto:** siete definiciones y respuestas fijas no cubren las preguntas de una persona que aprende sobre acciones, ETF, mercados e intermediarios. El usuario solicita un profesor que consulte una base amplia para generar sus explicaciones.

## Decisión

Guardar documentos educativos revisados en JSON versionados, con fuentes oficiales, fecha de revisión, explicación, ejemplos y cautelas. Recuperar fragmentos por alias, texto y TF-IDF local con scikit-learn, ya utilizado en el proyecto. Entregar únicamente los pasajes pertinentes al modelo NVIDIA mediante una operación educativa estructurada. Sin servicio de búsqueda alojado, modelos de embeddings descargados ni framework de orquestación adicional.

La biblioteca es conocimiento del producto: no contiene la memoria del usuario ni precios/noticias actuales. Se puede ampliar con documentos revisados sin añadir ramas de Python por concepto. Las consultas de mercado y los cálculos mantienen sus herramientas y validación determinista.

## Evidencia y límites

La salida educativa vincula cada párrafo a pasajes concretos y spans textuales. El código valida citas, spans, cifras y entidades, y rechaza consejo de inversión, garantías e instrucciones recuperadas. Si no encuentra evidencia suficiente o la generación no pasa las comprobaciones, muestra una explicación local con fuentes o reconoce el límite.

Una cita válida y estos controles no demuestran formalmente que toda paráfrasis sea semánticamente correcta. Se exige evaluación de recuperación y respuestas, y la calidad con NVIDIA real sigue pendiente hasta la prueba opt-in. No se relajan los bloques factuales protegidos de precios, noticias ni recomendaciones deterministas.

Los brókers aparecen como ejemplos documentados, no como rankings ni recomendaciones personales. El contenido está fechado; país, autorización, tarifas y condiciones actuales deben verificarse en sus fuentes y registros. No se promete cobertura de cualquier pregunta financiera.

## Alternativas y consecuencias

Ampliar solo el diccionario mantiene dependencia de respuestas programadas. Un almacén vectorial remoto o embeddings neuronales añaden instalación, coste o conectividad antes de evaluar su necesidad. La recuperación elegida es léxica y por similitud de texto, no se presenta como búsqueda semántica neuronal; sus umbrales y límites se evalúan explícitamente.

Se conservan ADR-001, ADR-003 y ADR-004. No se publica ningún servicio ni se inicia la fase 5. La biblioteca y búsqueda funcionan localmente; la generación NVIDIA requiere conexión y credenciales, y tiene fallback sin modelo.

Referencias técnicas consultadas: [patrón RAG](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview), [representación TF-IDF de texto](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction).
