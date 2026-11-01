# Pipeline de datos y ML offline

Instala las dependencias del repo desde la raíz:

```sh
python -m pip install -e '.[dev]'
```

`DATABASE_URL` acepta una URL SQLAlchemy. Por defecto usa `sqlite:///./investiq.db`; la base local no se versiona. Ejemplos:

```sh
investiq-data ingest --period 2y
investiq-data train --seed 42
investiq-data all --period 2y
```

`ingest` descarga precios diarios ajustados de los 20 símbolos de `src/investiq/instruments.py`. `train` calcula features y el pipeline ML a partir de los cierres ya guardados. `all` ejecuta ambos pasos. `DATABASE_URL` puede apuntar a SQLite u otro dialecto soportado por SQLModel; fases posteriores podrán usar Postgres sin cambiar estos modelos.

Los artefactos versionados quedan en `ml/artifacts/`: un archivo `.joblib` para inferencia y un `.json` legible con universo, fechas, features, semilla, métricas, umbrales y conteos de cubetas. La aprobación de clustering requiere silhouette ≥0.25 y ARI ≥0.6; el manifiesto conserva el resultado aunque no alcance esos límites. Las cubetas baja/media/alta se calculan por terciles deterministas, independientemente del clustering.

La similitud se consulta con `investiq.ml.similarity.load_model_artifact()` y `similar_instruments()`. Las cubetas se consultan con `assign_volatility_buckets()` y `volatility_bucket()` de `investiq.ml.volatility`.

yfinance se usa para investigación y educación, como ingesta batch de datos históricos; no es una fuente oficial de cotizaciones en vivo ni una recomendación de inversión. Para probar con una respuesta real del proveedor, ejecuta `RUN_LIVE_INTEGRATION=1 python -m pytest tests/integration/test_yfinance_live.py`.
