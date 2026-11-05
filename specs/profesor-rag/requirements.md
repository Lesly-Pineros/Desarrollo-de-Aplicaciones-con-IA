# Requisitos — Profesor con biblioteca financiera y RAG local

- **Estado:** Implementada y verificada localmente (2026-11-04). Generación NVIDIA real pendiente; sin despliegue.
- **Alcance:** biblioteca financiera amplia y ampliable con procedencia; recuperación local de documentos; explicaciones del modelo basadas en esos documentos; diálogo educativo y validación offline, con documentación de operación.
- **Exclusiones:** despliegue/fase 5, ejecutar operaciones, recomendar inversiones o brókers según perfil personal, garantías de cobertura universal, precios/noticias en la biblioteca, APIs financieras reales y NVIDIA live en este entorno.

### REQ-001 — Biblioteca educativa con fuentes

**EARS:** Cuando la aplicación arranque, el sistema deberá disponer de documentos educativos locales sobre acciones, ETF, mercados e inversión, con fuentes verificadas y fecha de revisión.

**Criterios de aceptación:** al menos 50 documentos sustantivos cubren fundamentos, ETF/fondos, índices/bolsas, riesgo, intermediarios, operativa, costes, análisis y prevención del fraude. Incluyen ejemplos de brókers con enlaces oficiales sin rankings ni prometer disponibilidad por país; explicaciones de instrumentos específicos cubiertos. Cada documento conserva título, alias, explicación, ejemplo, cautelas y referencias HTTPS. Contenido parafraseado, sin copiar extensamente fuentes; sin secretos ni datos del usuario.

### REQ-002 — Recuperación real y extensible sin servicios de pago

**EARS:** Cuando una persona formule una pregunta educativa, el sistema deberá recuperar fragmentos pertinentes de la biblioteca local y entregar solo ese contexto acotado a la generación.

**Criterios de aceptación:** búsqueda por texto, alias y similitud TF-IDF local, sin descargar embeddings ni servicios externos; selección independiente del orden de los documentos; consultas expresadas de varias maneras y preguntas de comparación conceptual; umbral de evidencia y abstención ante temas no cubiertos. Se pueden añadir documentos JSON revisados sin programar otra respuesta. CLI para validar, inspeccionar cobertura y probar búsqueda. No llamar cotizaciones para una definición.

### REQ-003 — Profesor con generación apoyada en evidencia

**EARS:** Cuando haya evidencia suficiente y un modelo disponible, el sistema deberá generar una explicación en español adaptada a la pregunta y nivel de la persona, usando únicamente los fragmentos recuperados.

**Criterios de aceptación:** contexto de consulta explícito, salida estructurada con evidencias textuales y referencias válidas; validación de citas, cifras, entidades y consejo de inversión; referencias filtradas a las utilizadas. Las fuentes se tratan como datos no confiables. Si falta modelo, falla o la salida no supera la validación, se ofrece una explicación local trazable. La validación no se presenta como prueba formal de verdad semántica ni una prueba con mocks como integración live. Las rutas de mercado conservan sus guardrails estrictos.

### REQ-004 — Continuidad, límites y brókers

**EARS:** Cuando la persona continúe con una pregunta corta o cambie de tema, el sistema deberá conservar el tema educativo pertinente, sin convertir aprendizaje en preferencias ni confundir documentos con memoria del usuario.

**Criterios de aceptación:** preguntas sobre acciones, ETF, brókers, bolsas, dividendos, órdenes, costes, índices y riesgos; ejemplos/nivel/restauración; preguntas de instrumentos específicos conservan fuentes y separan datos actuales. Las consultas de idoneidad o disponibilidad de brókers explican que dependen del país y requieren comprobación actual, sin clasificar uno como «el mejor». Ante evidencia insuficiente se reconoce el límite o se pide una aclaración concreta.

### REQ-005 — Entrega y verificación reproducible

**EARS:** Cuando se entregue la capacidad, el repositorio deberá incluir comandos de consola, fuentes de la biblioteca, trazabilidad y resultados de pruebas ejecutadas.

**Criterios de aceptación:** README, PLAN, arquitectura y decisiones actualizados; datos incluidos en el paquete; pruebas de recuperación sobre consultas reales, generación simulada/adversarial, memoria, regresión y navegador web. Sin credenciales reales ni adelantar fases; distinguir búsqueda local, generación remota y fallback.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-04 | Especificación previa solicitada para transformar el glosario en profesor con biblioteca y recuperación local. |
| 2026-11-04 | Biblioteca de 87 documentos integrada con recuperación, generación evidenciada y fallback; 538 tests offline y 53 checks de Chrome pasan. |
