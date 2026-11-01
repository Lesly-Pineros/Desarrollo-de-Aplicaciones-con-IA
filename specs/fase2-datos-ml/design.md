# Diseño — Fase 2: datos y ML offline

## Resumen y requisitos cubiertos

Pipeline local y repetible que lleva datos diarios a SQLite, calcula features, entrena K-Means, clasifica volatilidad por terciles y escribe artefactos. Cubre REQ-201 a REQ-206.

## Componentes y flujo

`investiq.data` declara el esquema SQLModel y las operaciones de repositorio. `investiq.ingest` descarga el histórico batch mediante yfinance. `investiq.ml.features` transforma cierres ajustados en un vector por símbolo. `investiq.ml.similarity` entrena scaler + K-Means y resuelve vecinos. `investiq.ml.volatility` calcula cubetas deterministas. `investiq.ml.pipeline` orquesta `ingest`, `train` y `all` desde CLI.

```text
símbolos + histórico yfinance → barras SQLModel/SQLite → retornos/features
   → terciles de volatilidad
   → scaler + K-Means → métricas silhouette/ARI → joblib + manifiesto JSON
```

## Datos e interfaces

- `Instrument`: símbolo, nombre, tipo (equity/ETF) y sector.
- `PriceBar`: símbolo, fecha, close ajustado; clave única símbolo/fecha.
- `InstrumentFeatures`: fecha de cálculo y métricas numéricas; sector one-hot se conserva en el artefacto del modelo.
- `MLClusterRun`/`MLClusterMembership`: versión, parámetros, métricas y etiqueta por instrumento.
- Funciones públicas: `ingest_history(...)`, `build_feature_frame(...)`, `fit_similarity_model(...)`, `similar_instruments(...)`, `assign_volatility_buckets(...)`, `volatility_bucket(...)`.

`DATABASE_URL` elige SQLite local. No se requiere conexión de red para las funciones de features, clustering, cubetas ni pruebas unitarias.

## Determinista y LLM

No interviene LLM en esta fase. Precios, features, cluster, similitud, cubetas y evaluación son cálculos reproducibles.

## Seguridad, fuentes y degradación

yfinance solo se usa para ingesta batch de investigación educativa, no como cotización oficial en vivo. La respuesta de ingesta identifica símbolos faltantes/errores y conserva datos persistidos. No se guardan claves ni se emiten recomendaciones de inversión.

## Decisiones y alternativas

- ADR-003: K-Means multi-feature para similitud; terciles deterministas para volatilidad.
- ADR-001 no aplica al pipeline offline; no se añade framework de orquestación.
- SQLModel sobre SQLite se mantiene portable hacia Postgres para fases posteriores.
- Se usa la canasta aprobada en `specs/piloto/requirements.md`: `AAPL, MSFT, NVDA, AMZN, GOOGL, META, JPM, XOM, JNJ, WMT, COST, TSLA, AVGO, BRK-B, UNH, SPY, QQQ, IWM, XLK, XLF`.
