# Requisitos — Ficha individual de símbolo

- **Estado:** Borrador
- **Alcance:** Mostrar en consultas sobre un símbolo del catálogo la ficha local, cotización disponible y métricas históricas ya calculadas por las tools.
- **Exclusiones:** símbolos fuera del catálogo, métricas nuevas, predicciones, asesoría u órdenes, llamadas forzadas a proveedores cuando faltan credenciales.

## Requisitos y criterios de aceptación

### REQ-001 — Cotización y contexto del símbolo

**EARS:** Cuando se consulte un símbolo individual cubierto, el sistema deberá mostrar el precio y la variación diaria disponibles junto con fuente, fecha y condición histórica/demorada.

**Criterios de aceptación:** usa `market_quote` y su caché; Twelve Data solo se llama si está configurada su clave y, si falla o no hay clave, se informa el fallback histórico de yfinance cuando existe. Si no hay precio, se declara sin suprimir el resto de la ficha.

### REQ-002 — Métricas históricas existentes

**EARS:** Cuando haya características locales calculadas para el símbolo, el sistema deberá exponer todos los valores numéricos ya disponibles en `instr_features`.

**Criterios de aceptación:** muestra volatilidad anualizada, volatilidad por tercil, beta, correlación media con pares, sector y fecha de cálculo. Explica que son métricas históricas, añade el período del modelo cuando se encuentre, y enlaza las fuentes locales. Si faltan características, lo declara sin inventar valores.

### REQ-003 — Consistencia de respuestas individuales

**EARS:** Cuando el símbolo llegue por una ficha de catálogo o una consulta de movimiento, el sistema deberá presentar las mismas métricas disponibles y mantener los datos existentes de noticias/SEC en la ruta de movimientos.

**Criterios de aceptación:** precios, retornos y características se obtienen de funciones deterministas; el LLM puede explicar, pero no calcular ni modificar cifras. La respuesta conserva metadatos del instrumento, evidencia por fuente y el disclaimer «No es asesoría financiera».

### REQ-004 — Descubrimiento desde el inicio

**EARS:** Cuando la persona vea las sugerencias iniciales, la interfaz deberá mostrar que puede pedir las métricas de un símbolo individual.

**Criterios de aceptación:** la pregunta general «¿Quieres conocer las métricas de una acción o ETF?» solicita un símbolo; la respuesta «AAPL» abre la misma ficha que una consulta directa. Se aceptan los símbolos del catálogo y se indican ejemplos/cobertura cuando la respuesta no corresponde a un símbolo.

### REQ-005 — Frescura y mercado de referencia

**EARS:** Cuando se muestren cotizaciones y métricas, el sistema deberá declarar su origen geográfico y frescura sin presentar métricas históricas como valores en tiempo real.

**Criterios de aceptación:** la descripción indica que la cobertura corresponde a instrumentos de Estados Unidos. Distingue la cotización del proveedor (que puede ser en tiempo real si Twelve Data y el plan lo permiten) de volatilidad, beta y correlación calculadas sobre retornos históricos. Si se usa yfinance histórico o caché vencida, se etiqueta como histórica/demorada. No promete cotización en tiempo real no verificada.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-07 | Borrador inicial para mostrar cotizaciones y todos los campos históricos existentes al consultar símbolos individuales. |
| 2026-11-07 | Se añade una sugerencia inicial de métricas por símbolo y resolución determinista de esa pregunta. |
| 2026-11-07 | La sugerencia inicia aclaración de símbolo y la respuesta explica cobertura estadounidense y frescura de cada grupo de valores. |
