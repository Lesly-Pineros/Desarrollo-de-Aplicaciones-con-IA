# Requisitos — Conversación y preferencias en el chat

- **Estado:** Implementada y verificada offline (2026-11-04); sin verificación de APIs reales en este cambio.
- **Alcance:** fluidez del piloto local, contexto por sesión, preferencias opcionales en conversación y sidebar informativa con catálogo consultable.
- **Exclusiones:** despliegue, nuevos proveedores, asesoría financiera, LangGraph, multiusuario y cálculo de métricas por el LLM.

### REQ-001 — Conversación con continuidad

**EARS:** Cuando la persona responda a una aclaración, el sistema deberá completar la consulta pendiente sin exigir repetirla.

**Criterios de aceptación:**
1. «Compara AAPL y MSFT» → pregunta de preferencias → «baja» guarda volatilidad y reanuda esa comparación.
2. «Busca similares» → pregunta de referencia → «NVDA» consulta similares a NVDA.
3. Saludos y agradecimientos reciben respuestas breves; «¿y MSFT?» retoma un instrumento en contexto.
4. Una pregunta educativa interrumpe la aclaración sin tratarla como una preferencia; el historial literal se limita a la sesión y a los últimos mensajes. El recuerdo estructurado opcional entre visitas se define en specs/agente-amigable.

### REQ-002 — Preferencias opcionales y explícitas

**EARS:** Cuando una comparación necesite contexto personal, el sistema deberá preguntar dentro del chat y usar solamente criterios expresados por la persona.

**Criterios de aceptación:**
1. No existe formulario de preferencias en la izquierda; se puede expresar volatilidad, sector, referencia y beta en texto libre.
2. Una preferencia nueva conserva las demás; se pueden consultar, cambiar o borrar por chat.
3. Preguntas educativas y filtros puntuales no se convierten en preferencias persistentes.
4. Datos ambiguos, símbolos no cubiertos y beta fuera de rango piden aclaración sin modificar preferencias.
5. «Sin preferencias» omite la personalización y compara features disponibles sin fabricar un puntaje.

### REQ-003 — Sidebar amigable y símbolos consultables

**EARS:** Mientras la app esté abierta, la izquierda deberá explicar en español para qué sirve InvestiQ y mostrar los símbolos disponibles para consultar.

**Criterios de aceptación:**
1. La explicación incluye aprendizaje de conceptos, movimientos, similitudes y comparaciones, sin prometer rendimientos.
2. El catálogo usa los 20 elementos de `INSTRUMENTS`, con símbolo y nombre; seleccionarlo no cambia preferencias ni llama proveedores.
3. La pantalla inicial invita a conversar y comunica la limitación del modo local cuando no hay LLM.

### REQ-004 — Guardrails y compatibilidad

**EARS:** Siempre que cambie el flujo conversacional, el sistema deberá preservar fuentes, cálculos deterministas, disclaimer y trazabilidad operativa.

**Criterios de aceptación:**
1. Cada respuesta incluye «No es asesoría financiera»; las cifras salen de tools o de preferencias explícitas.
2. La narración LLM conserva su validación de cifras/citas y trata fuentes e historial como datos.
3. El historial no se guarda en QueryLog; estado Pydantic acotado y compatible con reruns.
4. Las verificaciones offline no llaman servicios reales; no se declara validación live.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-04 | Spec previa a implementación: contexto conversacional, preferencias por chat y sidebar de ayuda/catálogo. |
