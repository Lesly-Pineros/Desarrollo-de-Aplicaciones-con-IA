# Pipeline de datos y ML offline

Prepara el entorno siguiendo el [README principal](../README.md). Todos los comandos de esta guía se ejecutan desde la raíz del repositorio con el Python de esa copia:

```sh
.venv/bin/python -m pip install -e '.[dev]'
```

`DATABASE_URL` acepta una URL SQLAlchemy. App y pipeline usan `.env` y las variables del entorno, con prioridad del entorno. Por defecto se utiliza `sqlite:///./investiq.db`; la base local no se versiona. Para una instalación nueva con internet, `all` descarga el histórico y ejecuta el entrenamiento:

```sh
.venv/bin/python -m investiq.ml.pipeline all --period 2y --seed 42
```

No hace falta ejecutar `train` de nuevo después de `all`. Si quieres separar los pasos:

```sh
.venv/bin/python -m investiq.ml.pipeline ingest --period 2y
.venv/bin/python -m investiq.ml.pipeline train --seed 42
```

`ingest` descarga precios diarios ajustados de los 20 símbolos de `src/investiq/instruments.py`. `train` calcula features y el clustering sobre los cierres ya guardados, sin llamar proveedores de datos. El entrypoint instalado `investiq-data` ofrece los mismos subcomandos. La persistencia usa SQLModel; el despliegue Postgres pertenece a una fase posterior.

Los artefactos versionados quedan en `ml/artifacts/`: un archivo `.joblib` para inferencia y un `.json` legible con universo, fechas, features, semilla, métricas, umbrales y conteos de cubetas. La aprobación de clustering requiere silhouette ≥0.25 y ARI ≥0.6; el manifiesto conserva el resultado aunque no alcance esos límites. Las cubetas baja/media/alta se calculan por terciles deterministas, independientemente del clustering.

La app necesita además las features y el registro de una ejecución aprobada en SQLite para localizar el artefacto y explicar la similitud. Un `.joblib` aislado no prepara una base vacía. Al trabajar con dos copias, cada una tiene su base independiente; usa `all` para preparar una nueva o conserva el conjunto de base y artefactos correspondientes.

La similitud se consulta con `investiq.ml.similarity.load_model_artifact()` y `similar_instruments()`. Las cubetas se consultan con `assign_volatility_buckets()` y `volatility_bucket()` de `investiq.ml.volatility`.

yfinance se usa para investigación y educación, como ingesta batch de datos históricos; no es una fuente oficial de cotizaciones en vivo ni una recomendación de inversión. Para probar con una respuesta real del proveedor en el equipo autorizado con internet:

```sh
RUN_LIVE_INTEGRATION=1 .venv/bin/python -m pytest -q tests/integration/test_yfinance_live.py
```

Este test consulta el proveedor real y se reporta aparte de las verificaciones offline.
