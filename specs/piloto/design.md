# Diseño — piloto InvestiQ v0.1

## Resumen y requisitos cubiertos

La spec cubre REQ-001 a REQ-014. Streamlit sirve la interfaz educativa; el proceso Python contiene un router simple, tools deterministas, acceso a ChatNVIDIA, persistencia SQLModel y cachés. La UI llama directamente a la orquestación, sin API FastAPI separada.

## Componentes y flujo

```text
Streamlit (acceso local directo)
  → router Python + estado Pydantic
  → {Explicador | Educador | Recomendador | Comparador}
  → tools deterministas + SQLite/SQLModel + cachés
  → ChatNVIDIA redacta/clarifica con contexto estructurado
  → validador de salida/citas/disclaimer
  → respuesta ES con fuentes originales
```

- `Explicador`: `market_quote` + `news` + `sec_docs`; calcula el movimiento con datos, el LLM solo narra.
- `Educador`: glosario determinista como grounding; el LLM adapta nivel y ejemplos generales.
- `Recomendador`: clarifica si se pide cubeta o instrumento parecido; llama `volatility_bucket` o `similar_instruments`.
- `Comparador`: `instr_features` + preferencias; score determinista, narración LLM.
- Fallback de reglas del router permite resolver intenciones claras cuando ChatNVIDIA falla. No se incorporan LangGraph ni LangChain como motor; ChatNVIDIA usa su cliente proveedor conforme a ADR-001.

El score inicial de comparación normaliza solo criterios disponibles y usa pesos explícitos: compatibilidad con volatilidad objetivo 0.40, sector 0.30, similitud con referencia 0.15 y beta objetivo 0.15. Si la persona usuaria no da un criterio, su peso se excluye y los restantes se renormalizan; los pesos quedan versionados junto al resultado. El score es una explicación de preferencias declaradas, no una recomendación.

## Datos e interfaces

### Tools puras

- `market_quote(symbol, as_of) -> QuoteResult`: valor, variación, fecha, proveedor, stale/delay y `PriceCacheEntry`.
- `news(symbol, query) -> list[NewsRef]`: titular, resumen/fuente original, publicación, retraso y `NewsCacheEntry`.
- `sec_docs(symbol, form_types, limit) -> list[FilingRef]`: accession, formulario, fecha y enlace EDGAR.
- `instr_features(symbol) -> InstrumentFeatures`: retornos, volatilidad, correlación, beta, sector, fecha/horizonte y run del modelo.
- `volatility_bucket(target) -> list[InstrumentFeatures]`: candidatos por tercil determinista.
- `similar_instruments(ref, top_n) -> list[InstrumentFeatures]`: vecinos del clúster evaluado ordenados por distancia.
- `compare_instruments(symbols, preferences) -> ComparisonResult`: score determinista y desglose reproducible.

Los resultados de tools son modelos Pydantic y contienen identificadores/enlaces de fuente. La capa de datos SQLModel contempla `User`, `Session`, `Instrument`, `UserPreference`, `PriceCacheEntry`, `NewsCacheEntry`, `FilingRef`, `InstrumentFeatures`, `MLClusterRun`, `MLClusterMembership`, `VolatilityBucket` y `QueryLog`. Se reutiliza la persistencia/modelos de Fase 2 donde encaje.

### Proveedores y degradación

- ChatNVIDIA es obligatorio; `NVIDIA_API_KEY`, `NVIDIA_MODEL`, timeout y presupuesto máximo de tokens se configuran por entorno/secret manager.
- Twelve Data es opcional para cotización; caché de 15 min; cuota limitada internamente a 8/min y 800/día. Fallback: último precio histórico yfinance, rotulado con su fecha; sin dato, no se calcula variación.
- Marketaux es opcional para noticias; caché configurable 6–12 h y aviso de retraso de hasta 24 h. Sin key se oculta/deshabilita la integración y se declara la falta de fuente.
- SEC EDGAR no requiere key. El cliente usa `User-Agent` identificable con contacto configurado (por ejemplo, `SEC_USER_AGENT`) y rate limit ≤10 req/s. Filing unavailable o CIK sin mapping se informa explícitamente.
- Las cachés preservan último dato válido ante timeout/cuota y nunca lo presentan como actual si caducó.

## Determinista y LLM

| Área | Determinista | LLM |
|---|---|---|
| Precios, variaciones, volatilidad, beta, correlación | proveedor + cálculo validado | explicación verbal, no cifra |
| Similaridad y cubetas | artefacto scikit-learn y terciles | no elige/inventa candidatos |
| Comparación | score, reglas y desglose | narra el resultado |
| Educación | glosario y referencias | adaptación pedagógica |
| Router | reglas de fallback y validación | clasificación estructurada y preguntas |
| Citas, cuotas, caché, identidad local y logs | enteramente determinista | no modifica controles |

## Seguridad, fuentes y degradación

La app local es de una sola persona y abre sin login; preferencias y `QueryLog` usan una identidad local fija, sin almacenar credenciales. Secretos desde entorno o secrets; `.env.example` solo con placeholders. Noticias/filings se encapsulan como datos no confiables, con instrucción de sistema de no seguir instrucciones recuperadas. La salida LLM debe cumplir un esquema Pydantic y asociar afirmaciones a referencias entregadas por las tools; si falla se reintenta de forma acotada y se devuelve un mensaje seguro. El disclaimer se añade en capa de respuesta independientemente del LLM. `QueryLog` excluye secretos; retención objetivo 90 días. Los enlaces visibles llevan a la fuente original, incluso si el resumen es español.

## Decisiones y alternativas

- ADR-001: router Python plano y tools puras en v0.1; LangGraph se aplaza hasta que el flujo justifique estado/bucles/checkpointing.
- ADR-002: el piloto corre local con SQLite; el diseño deja `DATABASE_URL` portable. Streamlit Community Cloud + Neon son fase posterior; Vercel no forma parte del piloto.
- ADR-003: clustering K-Means multi-feature para similitud y terciles deterministas para volatilidad. Reutilizar artefacto evaluado de Fase 2.
- Universo de 20 instrumentos fijado en `requirements.md` y sincronizado con `src/investiq/instruments.py`.

## No funcionales

- UI y respuestas en español claro; disclaimer visible en cada respuesta.
- Integraciones externas con timeout, errores tipados, caché y avisos de frescura.
- Lógica de dominio comprobable sin red; APIs reales solo en tests marcados.
- No prometer que similitud histórica o buckets predicen resultados futuros.
