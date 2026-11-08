# Requisitos — Exploración guiada de acciones y ETF

- **Estado:** Borrador (2026-11-04).
- **Implementación:** completada y verificada offline y en Chrome local; evidencia en [tasks.md](tasks.md). No implica aprobación editorial ni aceptación de NVIDIA real.
- **Alcance:** acceso web a recomendación educativa; preguntas conversacionales, candidatos apoyados en clustering aprobado y métricas históricas trazables.
- **Exclusiones:** órdenes de compra/venta, predicción de rentabilidad, puntuación como probabilidad de ganar, perfil financiero inferido, nuevos instrumentos, entrenamiento o ingesta automática en el chat, despliegue.

### REQ-001 — Criterios en conversación

**EARS:** Cuando se pida explorar acciones o ETF, el sistema deberá aprovechar todos los criterios explícitos del mensaje y, si faltan criterios necesarios, pedirlos juntos en una sola aclaración natural.

**Criterios de aceptación:** tipo (acciones/ETF/ambos), plazo y variación histórica deseada; sector cuando se declare. La referencia es opcional y no bloquea la búsqueda. Aceptar criterios expresados juntos y en lenguaje cotidiano, incluidos «no tan volátil», «por un año», «subidas y bajas pocas», «seis meses» y «más estable»; aceptar respuestas cortas, correcciones, interrupción educativa y cancelación. No repetir criterios ya entendidos ni convertir cualquier negación en rechazo. Sin formularios ni guardar automáticamente preferencias financieras. Reconocer que un objetivo de usar el dinero hoy/corto plazo no se resuelve presentando acciones como seguras.

### REQ-002 — Candidatos desde ML real local

**EARS:** Cuando haya criterios suficientes y un modelo aprobado disponible, el sistema deberá seleccionar candidatos del catálogo con participación comprobable del clustering entrenado.

**Criterios de aceptación:** leer artefacto aprobado y features coherentes; agrupar/puntuar mediante distancias del modelo entrenado y filtros explícitos de tipo, sector y volatilidad determinista. Referencia opcional prioriza parecido en el espacio entrenado; sin referencia se usa distancia al centro del clúster, explicando el método. Mostrar hasta tres candidatos y no rellenar resultados incompatibles. Si falta modelo/datos o no hay coincidencias, explicar la causa sin inventar métricas. Describir candidatos para estudiar, no una instrucción de invertir hoy.

### REQ-003 — Respuesta completa y trazable

**EARS:** Cuando se devuelvan candidatos, el sistema deberá mostrar volatilidad histórica anualizada en porcentaje, categoría de volatilidad, beta, sector y procedencia/fecha del período de observación.

**Criterios de aceptación:** cifras calculadas por código, con fuentes al modelo y features, tipo de activo y explicación de coincidencia. No convertir baja volatilidad en perfil personal conservador ni en protección de capital; no prometer rendimientos. Una puntuación de coincidencia no es rentabilidad ni probabilidad. NVIDIA puede narrar el bloque protegido; no decide candidatos ni altera cifras. Disclaimer en cada respuesta.

### REQ-004 — Frontend y verificación

**EARS:** Cuando se entregue la rama, la web deberá ofrecer un acceso visible y el repositorio deberá verificar el flujo junto al profesor existente.

**Criterios de aceptación:** acceso persistente «Recomendaciones guiadas» inicia el flujo por chat, sin formulario; se puede usar en móvil y teclado. Las sugerencias iniciales conducen a modos reales de la app (recomendaciones, sectores NASDAQ y noticias). Flujo probado con artefacto KMeans de fixture sintético y SQLite temporal, ausencia de modelo y memoria restaurada; regresión web sin proveedores, SDD, README y PLAN. Mantener rutas dinámicas, NVIDIA configurable y ADR-001/003/004. No migrar a LangGraph sin necesidad demostrada.

### REQ-005 — Preguntas fáciles de contestar

**EARS:** Cuando falten criterios para explorar, el sistema deberá hacer una pregunta breve con respuestas de ejemplo fáciles de expresar.

**Criterios de aceptación:** una sola intervención natural reúne únicamente los criterios obligatorios que falten y reconoce brevemente lo que ya entendió; evita listas de campos, preguntas repetidas y cierres genéricos como «no hace falta usar términos financieros». El modo local también pregunta en lenguaje claro, sin una coletilla fija. Reconoce frases cotidianas de plazo y variación (por ejemplo «medio año», «sin tantos altibajos», «más estable» y «pocas subidas y bajadas»). La referencia puede omitirse sin confirmación. Las frases «no soy de tomar riesgos» y similares pueden mapearse al filtro histórico de variación baja solo para esa búsqueda, aclarando que no es un perfil ni protección de capital. Al finalizar muestra candidatos con cifras históricas, período y fuentes conforme a REQ-002/003.

### REQ-006 — Acceso guiado visible y sugerencias de modo

**EARS:** Cuando el usuario active «Recomendaciones guiadas» o elija la sugerencia inicial correspondiente, el sistema deberá iniciar la exploración conversacional con preguntas fáciles de responder.

**Criterios de aceptación:** el acceso y sugerencia inician la conversación sin simular un mensaje de usuario. El asistente pregunta en una sola intervención natural por los criterios necesarios, y termina en candidatos con métricas/fuentes cuando hay criterios y modelo disponibles. Las demás sugerencias llevan a noticias o ranking sectorial NASDAQ. No inicia una orden ni crea un perfil financiero.

### REQ-007 — Inicio del modo sin mensaje prefabricado

**EARS:** Cuando la persona active «Recomendaciones guiadas», la interfaz deberá iniciar el modo de recomendación sin mostrar ni enviar una frase como si la hubiera escrito la persona.

**Criterios de aceptación:** aparece una única intervención del asistente que invita a compartir criterios faltantes en lenguaje natural. Si hay modelo configurado, la redacción se adapta a los criterios pendientes; sin modelo, se usa una alternativa local clara. La conversación conserva el estado para interpretar la respuesta.

### REQ-008 — Transparencia sobre criterios no usados

**EARS:** Cuando la persona incluya un monto disponible, el sistema deberá aclarar que ese monto no se utiliza para ordenar candidatos mientras el modelo no tenga un criterio presupuestal.

**Criterios de aceptación:** no se inventa un ajuste al presupuesto; los candidatos se describen como instrumentos para estudiar y no como una recomendación personalizada de compra.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-04 | Borrador previo para la exploración guiada solicitada y su conexión al clustering existente. |
| 2026-11-04 | Flujo por chat, KMeans aprobado, huella de características, métricas/fuentes y frontend verificados dentro de 704 pruebas offline y 93 comprobaciones Chrome. |
| 2026-11-07 | Se ofrece «Recomendaciones guiadas» y se alinean las sugerencias iniciales con modos disponibles; se conserva el acceso sectorial NASDAQ. |
| 2026-11-07 | Se corrige la aclaración repetida por negaciones; se agrupan criterios faltantes, la referencia queda opcional y el botón deja de enviar un mensaje prefabricado. |
| 2026-11-07 | Se amplía la interpretación determinista de frases cotidianas sobre volatilidad, estabilidad y plazos para evitar repetir criterios que la persona ya indicó. |
| 2026-11-07 | Se elimina la coletilla prefabricada de la aclaración local y se exige que el modelo evite cierres genéricos; la pregunta reconoce los criterios ya expresados. |
