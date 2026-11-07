# Diseño — Ficha individual de símbolo

## Resumen y requisitos cubiertos

REQ-001 a REQ-003: extender las dos rutas actuales de un solo instrumento (`instrument_info` y `explanation`) con una presentación compartida de cotización y características existentes.

## Componentes y flujo

`handlers._instrument_info` y `handlers._explain` consultan `market_quote_tool` y `instr_features`. Un formateador determinista común presenta los campos y estado de disponibilidad. La ruta `_explain` conserva además las llamadas actuales a noticias y SEC. `tools.feature_sources` atribuye las características; `local_model_source` aporta período del clustering cuando hay ejecución aprobada.

REQ-004: la sugerencia inicia `instrument_info` sin símbolo, que activa un pending field `instrument_symbol`; al responder con un símbolo del catálogo, `resume_pending` despacha a la ficha. Las preguntas que ya incluyen símbolo van directamente a `instrument_info`. La orquestación respeta esta intención y no la reescribe como lección.

REQ-005: el bloque determinista explica que la cotización se obtiene al consultar la fuente y su frescura depende de proveedor/plan/caché, mientras las features se calcularon desde históricos. El mercado cubierto es Estados Unidos; no se anuncia que beta, volatilidad o correlación sean datos en tiempo real.

## Datos e interfaces

Cotización: precio, cambio absoluto/porcentual, timestamp, proveedor y marca de retraso desde `QuoteResult`. Características: volatilidad anualizada, `volatility_bucket`, beta, correlación media entre pares, sector y `calculated_at` desde `InstrumentFeature`. No se añaden cálculos ni columnas. El beta usa SPY como benchmark cuando está en el universo de datos; en caso contrario usa el promedio del universo. El período ML se incluye solo cuando existe un registro local aprobado.

## Determinista y LLM

Datos, cálculos, selección de fuentes y formato de cifras son deterministas. NVIDIA puede redactar una explicación protegida sin alterar métricas.

## Seguridad, fuentes y degradación

Twelve Data es opcional: la clave vacía no provoca solicitud externa. Se conserva caché y límite existente y fallback histórico yfinance. Métricas ausentes se identifican individualmente, no se sustituyen por ceros. Noticias/filings siguen sus fuentes y límites actuales. Cada respuesta conserva el disclaimer.

## Decisiones y alternativas

Se reutilizan ADR-001/003/004 y las tools existentes; no se incorpora proveedor, modelo, cálculo ni interfaz nueva.
