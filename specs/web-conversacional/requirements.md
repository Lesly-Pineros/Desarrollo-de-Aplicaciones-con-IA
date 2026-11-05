# Requisitos — Web conversacional InvestiQ

- **Estado:** Implementada y verificada localmente (2026-11-04); aceptación con NIM real pendiente. No se atribuye aprobación estética adicional del usuario.
- **Alcance:** sustituir la experiencia local principal de Streamlit por una web conversacional; corregir los casos de diálogo de la captura del usuario; descargar y aplicar las tres skills de diseño solicitadas.
- **Exclusiones:** despliegue y fase 5, autenticación, nuevos proveedores, llamadas live a NIM, precios simulados, cambios en los cálculos financieros.

### REQ-001 — Web local accesible y adaptable

**EARS:** Cuando se abra la aplicación, el sistema deberá presentar una web en español con conversación central, explicación amigable del propósito, catálogo consultable y preferencias recogidas en el diálogo.

**Criterios de aceptación:** teclado y móvil utilizables; estados de carga, error y conversación vacía; fuentes y disclaimer legibles; sin cotizaciones inventadas ni controles decorativos sin función; diseño verificado en Chrome en escritorio y móvil.

### REQ-002 — Adaptador web modular

**EARS:** Cuando el navegador envíe un mensaje, el servidor local deberá invocar el agente Python existente y devolver su respuesta y trazabilidad mediante una API del mismo origen.

**Criterios de aceptación:** sin Node ni compilación para ejecutar; estado temporal aislado por cookie opaca; bloqueo por sesión; límites de entrada; archivos estáticos permitidos explícitamente; errores sin secretos; persistencia resumida opcional bajo la identidad local ya existente.

### REQ-003 — Diálogo fiel a la pregunta

**EARS:** Cuando la persona pregunte qué es AAPL, qué puede hacer el agente o formule una pregunta incompleta, el sistema deberá responder al significado de la consulta o pedir una sola aclaración breve.

**Criterios de aceptación:** variantes de la captura cubiertas con regresiones; descripción de instrumentos respaldada por catálogo local; no consultar precios para definir un símbolo; no guardar preferencias a partir de preguntas educativas; mantener guardrails financieros.

### REQ-004 — Instalación reproducible y verificación honesta

**EARS:** Cuando se entregue la web, el repositorio deberá incluir un comando portable, documentación actualizada y evidencia de las comprobaciones realizadas.

**Criterios de aceptación:** lanzador independiente de la ubicación; skills locales excluidas de Git; spec trazable, ADR y PLAN actualizados; regresiones offline y pruebas reales de navegador; integración de proveedores identificada como pendiente cuando no se ejecute.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-04 | Especificación previa del rediseño solicitado; skills descargadas en .local/design-skills. |
| 2026-11-04 | Implementación y pulido tras revisión: 338 pruebas offline, 38 comprobaciones en Chrome, nueve specs válidas y assets del wheel comprobados. |
