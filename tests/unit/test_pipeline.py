import json

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from investiq.data.database import create_db, make_engine
from investiq.data.models import Instrument, MLClusterMembership, MLClusterRun, PriceBar
from investiq.instruments import INSTRUMENTS
from investiq.ml.pipeline import run_training


def test_offline_pipeline_persists_features_evaluation_and_versioned_artifacts(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'pipeline.db'}"))
    dates = pd.bdate_range("2024-01-01", periods=180)
    rng = np.random.default_rng(24)
    market = rng.normal(0.0003, 0.01, len(dates))
    with Session(engine) as session:
        for index, item in enumerate(INSTRUMENTS):
            session.add(Instrument(symbol=item.symbol, name=item.name, kind=item.kind, sector=item.sector))
            group = index % 3
            idio_scale = (0.003, 0.009, 0.022)[group]
            loading = (0.85, 1.0, 1.2)[group]
            returns = market * loading + rng.normal(0, idio_scale, len(dates))
            prices = 100 * np.cumprod(1 + returns)
            session.add_all(
                PriceBar(symbol=item.symbol, date=stamp.date(), adjusted_close=float(price))
                for stamp, price in zip(dates, prices, strict=True)
            )
        session.commit()
        report = run_training(session, artifact_dir=tmp_path / "artifacts", min_observations=60)
        assert report["universe_size"] == 20
        assert report["n_clusters"] >= 2
        assert report["silhouette"] is not None
        assert (tmp_path / "artifacts" / f"{report['run_id']}.joblib").exists()
        manifest = json.loads((tmp_path / "artifacts" / f"{report['run_id']}.json").read_text())
        assert manifest["features"]
        assert set(manifest["volatility_buckets"]) == {"baja", "media", "alta"}
        assert session.get(MLClusterRun, report["run_id"])
        assert len(session.exec(select(MLClusterMembership).where(MLClusterMembership.run_id == report["run_id"])).all()) == 20
