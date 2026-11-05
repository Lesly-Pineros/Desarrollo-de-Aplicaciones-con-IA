# Requisitos — Exploración guiada de acciones y ETF

- **Estado:** Borrador (2026-11-04).
- **Implementación:** completada y verificada offline y en Chrome local; evidencia en [tasks.md](tasks.md). No implica aprobación editorial ni aceptación de NVIDIA real.
- **Alcance:** acceso web a recomendación educativa; preguntas conversacionales, candidatos apoyados en clustering aprobado y métricas históricas trazables.
- **Exclusiones:** órdenes de compra/venta, predicción de rentabilidad, puntuación como probabilidad de ganar, perfil financiero inferido, nuevos instrumentos, entrenamiento o ingesta automática en el chat, despliegue.

### REQ-001 — Criterios en conversación

**EARS:** Cuando se pida recomendar una acción o ETF para invertir hoy, el sistema deberá preguntar solo los criterios que falten para una exploración educativa.

**Criterios de aceptación:** tipo (acciones/ETF/ambos), plazo de necesidad del dinero, variación histórica deseada y referencia opcional; sector cuando se declare. Aceptar varios criterios en un mensaje, respuestas cortas, correcciones, interrupción educativa y cancelación. Una pregunta por turno; sin formularios ni guardar automáticamente preferencias financieras. Reconocer que un objetivo de usar el dinero hoy/corto plazo no se resuelve presentando acciones como seguras.

### REQ-002 — Candidatos desde ML real local

**EARS:** Cuando haya criterios suficientes y un modelo aprobado disponible, el sistema deberá seleccionar candidatos del catálogo con participación comprobable del clustering entrenado.

**Criterios de aceptación:** leer artefacto aprobado y features coherentes; agrupar/puntuar mediante distancias del modelo entrenado y filtros explícitos de tipo, sector y volatilidad determinista. Referencia opcional prioriza parecido en el espacio entrenado; sin referencia se usa distancia al centro del clúster, explicando el método. Mostrar hasta tres candidatos y no rellenar resultados incompatibles. Si falta modelo/datos o no hay coincidencias, explicar la causa sin inventar métricas. Describir candidatos para estudiar, no una instrucción de invertir hoy.

### REQ-003 — Respuesta completa y trazable

**EARS:** Cuando se devuelvan candidatos, el sistema deberá mostrar volatilidad histórica anualizada en porcentaje, categoría de volatilidad, beta, sector y procedencia/fecha del período de observación.

**Criterios de aceptación:** cifras calculadas por código, con fuentes al modelo y features, tipo de activo y explicación de coincidencia. No convertir baja volatilidad en perfil personal conservador ni en protección de capital; no prometer rendimientos. Una puntuación de coincidencia no es rentabilidad ni probabilidad. NVIDIA puede narrar el bloque protegido; no decide candidatos ni altera cifras. Disclaimer en cada respuesta.

### REQ-004 — Frontend y verificación

**EARS:** Cuando se entregue la rama, la web deberá ofrecer un acceso visible y el repositorio deberá verificar el flujo junto al profesor existente.

**Criterios de aceptación:** acceso persistente «Explorar acciones y ETF», chat sin formularios, móvil/teclado; tests con artefacto KMeans entrenado con datos sintéticos offline y SQLite temporal, ausencia de modelo y memoria restaurada; Chrome sin proveedores, SDD, README y PLAN. Mantener rutas dinámicas, NVIDIA configurable y ADR-001/003/004. No migrar a LangGraph sin una necesidad demostrada.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-04 | Borrador previo para la exploración guiada solicitada y su conexión al clustering existente. |
| 2026-11-04 | Flujo por chat, KMeans aprobado, huella de características, métricas/fuentes y frontend verificados dentro de 704 pruebas offline y 93 comprobaciones Chrome. |
