# Requisitos — Fondos, criptoactivos e indicadores

- **Estado:** Borrador (2026-11-04).
- **Implementación:** completada y verificada localmente; evidencia en [tasks.md](tasks.md). El estado de la especificación no supone una aprobación editorial independiente.
- **Ampliación posterior:** [actualidad-mercados](../actualidad-mercados/requirements.md) incorpora el adaptador FMP opcional; conserva aquí la evidencia histórica de la ausencia de ranking y mantiene la degradación sin datos verificados.
- **Alcance:** ampliar el profesor RAG con fundamentos de fondos, criptoactivos, indicadores y disciplina de trading; resolver comparación ETF/acciones a largo plazo; distinguir consultas sectoriales actuales de definiciones.
- **Exclusiones:** ejecutar operaciones, asesoría personalizada, prometer rentabilidad, cotizaciones de criptomonedas, calcular indicadores en vivo, ampliar el universo de mercado, incorporar proveedor de ranking sectorial o desplegar fase 5.

### REQ-001 — Formación amplia y trazable

**EARS:** Cuando se pregunte por fondos, criptomonedas o indicadores, el profesor deberá recuperar explicaciones revisadas con ejemplos, limitaciones y fuentes oficiales.

**Criterios de aceptación:** fondos y su diferencia con ETF; criptomoneda, Bitcoin, Ethereum, blockchain, custodia, stablecoins y staking; indicadores técnicos de tendencia, momentum, volatilidad y volumen; fundamentos, control de riesgo y sesgos de evaluación. Al menos 20 documentos adicionales sustantivos, sin copiar extensamente fuentes ni presentar señales técnicas como órdenes de compra/venta. Sin precios ni rentabilidades ficticias.

### REQ-002 — Comparación de rentabilidades sin garantía

**EARS:** Cuando se pregunte si un ETF o acciones individuales ofrecen mayores rentabilidades a largo plazo, el profesor deberá explicar concentración, diversificación, costes y riesgo sin declarar un ganador universal.

**Criterios de aceptación:** responder al caso textual del usuario; distinguir ETF diversificado de sectorial/concentrado; no equiparar mayor concentración a ganancia garantizada; no clasificar la pregunta como comparación de dos tickers ni guardar preferencias a partir de ella.

### REQ-003 — Actualidad sectorial honesta

**EARS:** Cuando se pregunte qué sectores lideran hoy, el sistema deberá tratarlo como una consulta de datos actuales y pedir el mercado si falta, sin generar un ranking desde la biblioteca estática.

**Criterios de aceptación:** ruta explícita, mercado canónico y seguimiento de la aclaración; estado degradado cuando no haya ranking actual verificado; sin nombres de líderes ni porcentajes inventados, sin utilizar dos ETF disponibles para afirmar cobertura total del mercado. La pregunta no activa una llamada de cotización o narración que fabrique la clasificación. Los mensajes con comparación educativa y consulta sectorial deberán atender ambas partes.

### REQ-004 — Validación y documentación

**EARS:** Cuando se entregue la ampliación, el repositorio deberá documentar cobertura, comandos y límites y conservar las regresiones del agente.

**Criterios de aceptación:** corpus validado, pruebas de recuperación y diálogo, memoria/guardrails, navegador y specs; README/PLAN actualizados. Verificaciones locales separadas de servicios reales; NVIDIA y ranking sectorial actual no se declaran verificados en vivo.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-04 | Especificación previa de la ampliación y de los dos casos propuestos por el usuario. |
| 2026-11-04 | Implementación local y evidencia: 32 documentos nuevos, ruta sectorial sin datos inventados y pruebas reproducibles. |
