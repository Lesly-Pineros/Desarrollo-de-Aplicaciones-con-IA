# Requisitos — Web conversacional InvestiQ

- **Estado:** Implementada y verificada localmente (2026-11-04); aceptación con NIM real pendiente. No se atribuye aprobación estética adicional del usuario.
- **Alcance:** sustituir la experiencia local principal de Streamlit por una web conversacional; corregir los casos de diálogo de la captura del usuario; descargar y aplicar las tres skills de diseño solicitadas.
- **Exclusiones:** despliegue y fase 5, autenticación, nuevos proveedores, llamadas live a NIM, precios simulados, cambios en los cálculos financieros.

### REQ-005 — Nueva experiencia visual y accesos independientes

**EARS:** Cuando la persona abra InvestiQ, el sistema deberá presentar una interfaz financiera educativa con identidad verde, superficies translúcidas, un profesor robot identificable y accesos iniciales visibles. Cuando pulse un acceso de la navegación o una pregunta inicial, el sistema deberá iniciar una conversación nueva antes de realizar esa consulta.

**Criterios de aceptación:** el diseño prioriza lectura de respuestas, fuentes y disclaimer sobre adornos; el catálogo deja de ocupar una columna fija en escritorio y sigue accesible en móvil; el robot acompaña la bienvenida y distingue visualmente respuestas del profesor sin fingir datos de mercado. Noticias, recomendaciones, NASDAQ y S&P 500 usan una sola definición de acción compartida entre navegación y sugerencias. El acceso de métricas reinicia la sesión y deja la pregunta preparada para completar; no envía una consulta incompleta. Si el reinicio falla, no se envía la nueva consulta; el reintento no duplica mensajes. Se conserva el botón independiente «Nueva conversación». Las acciones de respuesta, como resumir una noticia, continúan la conversación actual. El diseño funciona con teclado, móvil, movimiento reducido y assets locales.

### REQ-006 — Identidad derivada del robot y bienvenida en video

**EARS:** Cuando la persona abra la web, el sistema deberá presentar la paleta derivada del robot suministrado y uno de sus videos al inicio, con la imagen suministrada como respaldo visual. Cuando comience una conversación o active movimiento reducido, el sistema deberá detener la reproducción automática.

**Criterios de aceptación:** azul marino, cian, azul eléctrico, blanco frío y naranja se aplican de forma coherente y legible; la nueva animación se sirve localmente, silenciada, en bucle automático y sin controles visibles. Su fondo oscuro se elimina en el recurso web para integrarla en la bienvenida sin un rectángulo opaco. Una leyenda visible indica que las gráficas son ilustrativas. La imagen de respaldo aparece si la animación no carga; el navegador no la descarga ni reproduce automáticamente bajo `prefers-reduced-motion`. Los accesos, respuestas, fuentes y disclaimer siguen visibles en móvil y escritorio. No se incorporan cifras del video como información financiera de la app.

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
| 2026-11-07 | Borrador de rediseño con verde y vidrio, profesor robot, catálogo horizontal en escritorio y reinicio de sesión en accesos iniciales. |
| 2026-11-07 | Nueva dirección visual a partir del robot aportado: paleta azul/cian/naranja, video ilustrativo y respaldo estático accesible. |
