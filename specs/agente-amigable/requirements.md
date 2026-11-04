# Requisitos — Agente amigable con memoria y redacción verificable

- **Estado:** Implementada y verificada offline (2026-11-04). Validación NIM real pendiente en el entorno autorizado con internet y clave rotada.
- **Alcance:** naturalidad y continuidad del piloto; guía de conversación cargada por el runtime, comprensión validada de preferencias, memoria resumida opcional, diagnósticos seguros y evaluación conversacional.
- **Exclusiones:** instalación de BMAD, nuevos proveedores, login, despliegue, LangGraph, asesoría y cálculos decididos por el LLM.

### REQ-001 — Redacción cercana con evidencia

**EARS:** Cuando existan resultados deterministas, el agente deberá permitir una redacción conversacional apoyada en esos resultados conservando cifras, símbolos, citas y limitaciones verificadas.

**Criterios de aceptación:**
1. Una guía versionada cargada desde el paquete define tono claro, amable, sin simular ser una persona, sin saludos repetitivos ni preguntas innecesarias.
2. Educación, movimientos, comparaciones y similitudes pueden usar narración validada. El bloque factual se inserta desde código mediante un marcador obligatorio; el modelo no modifica sus cifras ni candidatos.
3. Citas desconocidas, cifras/símbolos/URLs agregados y consejo de compra/venta se rechazan y dejan la respuesta determinista disponible.
4. Cada respuesta conserva «No es asesoría financiera».

### REQ-002 — Memoria resumida persistente y controlable

**EARS:** Cuando se cierre o reinicie una sesión, el agente deberá poder recuperar un resumen estructurado opcional de su contexto local.

**Criterios de aceptación:**
1. Se conserva tema educativo canónico, símbolos cubiertos, consulta pendiente y nivel de explicación; no historial literal, secretos ni precios/noticias antiguos.
2. Se puede ver qué recuerda, desactivar el recuerdo y borrarlo; borrar contexto no borra preferencias por sorpresa.
3. La memoria pertenece a la identidad local compartida de la instalación, expira tras retención configurable y no se sincroniza entre copias del repo.
4. Tablas nuevas funcionan en SQLite existente sin eliminar datos ni exigir migraciones destructivas.

### REQ-003 — Comprensión semántica con validación

**EARS:** Cuando una declaración de preferencias no encaje en las reglas simples, el agente deberá poder usar una propuesta estructurada del modelo y validarla contra palabras del mensaje actual.

**Criterios de aceptación:**
1. Cada campo propuesto tiene evidencia textual literal del usuario; solo se aceptan sectores/símbolos cubiertos, volatilidad canónica y beta acotada con número expresado.
2. Preguntas, filtros puntuales, negaciones ambiguas y valores inventados no se guardan como preferencias.
3. Cambios parciales conservan otros criterios y un parche inválido no se aplica parcialmente.
4. Sin proveedor o con fallo, siguen disponibles las reglas locales y una aclaración comprensible.

### REQ-004 — Diagnóstico seguro y evaluación reproducible

**EARS:** Cuando el agente recurra a una plantilla o falle el proveedor, el sistema deberá registrar un diagnóstico acotado que permita distinguirlo de una respuesta del LLM.

**Criterios de aceptación:**
1. Diagnósticos usan categorías seguras, nunca excepciones originales, claves, prompts o respuestas completas.
2. Suite offline cubre conversaciones completas, memoria tras reinicio, preferencias ambiguas y narraciones maliciosas.
3. Un comando de diagnóstico live requiere activación explícita y una clave rotada; informa categorías y métricas sin exponer secretos.
4. No se marca NIM verificado con mocks o por disponer de una key. La validación live se ejecuta en el entorno autorizado con internet.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-04 | Spec previa para aplicar las mejoras de diálogo, memoria, comprensión y observabilidad. BMAD se evalúa como metodología de desarrollo, sin instalarlo. |
| 2026-11-04 | Implementación y regresión offline completadas: 189 pruebas pasan. Diagnóstico live preparado y ejecutado solo sin flags: not_run. |
