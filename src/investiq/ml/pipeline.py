import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlmodel import Session, delete, select

from investiq.data.database import create_db, ensure_sqlite_parent, make_engine
from investiq.data.models import InstrumentFeature, MLClusterMembership, MLClusterRun, PriceBar
from investiq.ingest import IngestResult, ingest_history
from investiq.instruments import INSTRUMENTS
from investiq.logging_config import configure_logging, log_stage
from investiq.ml.features import build_feature_frame
from investiq.ml.similarity import fit_similarity_model, save_model_artifact
from investiq.ml.volatility import assign_volatility_buckets

logger = logging.getLogger(__name__)


def closes_from_session(session: Session) -> pd.DataFrame:
    rows = session.exec(select(PriceBar).order_by(PriceBar.date)).all()
    if not rows:
        raise ValueError("no price history found; run the ingest command first")
    frame = pd.DataFrame(
        ((bar.date, bar.symbol, bar.adjusted_close) for bar in rows),
        columns=("date", "symbol", "adjusted_close"),
    )
    return frame.pivot(index="date", columns="symbol", values="adjusted_close").sort_index()


def run_training(
    session: Session,
    *,
    artifact_dir: str | Path = "ml/artifacts",
    seed: int = 42,
    min_observations: int = 60,
) -> dict[str, object]:
    with log_stage(logger, "ml.load_history"):
        closes = closes_from_session(session)
    sectors = {item.symbol: item.sector for item in INSTRUMENTS}
    with log_stage(logger, "ml.build_features"):
        feature_result = build_feature_frame(closes, sectors, min_observations=min_observations)
    buckets = assign_volatility_buckets(feature_result.values["volatility"])
    feature_columns = ["volatility", "mean_peer_correlation", "beta", "sector"]
    feature_values = feature_result.values[feature_columns]
    for symbol, row in feature_values.iterrows():
        session.merge(
            InstrumentFeature(
                symbol=symbol,
                calculated_at=datetime.now(timezone.utc),
                volatility=float(row.volatility),
                mean_peer_correlation=float(row.mean_peer_correlation),
                beta=float(row.beta),
                sector=str(row.sector),
                volatility_bucket=buckets[symbol],
            )
        )
    session.commit()

    numeric = feature_result.values.drop(columns=["sector"])
    with log_stage(logger, "ml.train_similarity"):
        evaluation = fit_similarity_model(numeric, seed=seed)
    feature_fingerprint = hashlib.sha256(
        numeric.round(12).to_csv(float_format="%.12g").encode("utf-8")
    ).hexdigest()
    run_id = f"kmeans-{feature_fingerprint[:12]}-s{seed}"
    artifact = dict(evaluation.model)
    artifact.update({
        "run_id": run_id,
        "feature_fingerprint": feature_fingerprint,
        "observation_start": str(pd.Timestamp(feature_result.returns.index.min()).date()),
        "observation_end": str(pd.Timestamp(feature_result.returns.index.max()).date()),
        "excluded": feature_result.excluded,
        "volatility_buckets": buckets,
        "universe_size": len(numeric),
    })
    artifact_path = save_model_artifact(artifact, Path(artifact_dir) / f"{run_id}.joblib")
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "algorithm": "KMeans",
        "universe_size": len(numeric),
        "observation_start": artifact["observation_start"],
        "observation_end": artifact["observation_end"],
        "seed": seed,
        "n_clusters": len(set(evaluation.labels.values())),
        "features": list(numeric.columns),
        "excluded": feature_result.excluded,
        "silhouette": evaluation.silhouette,
        "stability_ari": evaluation.stability_ari,
        "thresholds": {"silhouette": 0.25, "stability_ari": 0.6},
        "passed_thresholds": evaluation.passed_thresholds,
        "feature_fingerprint": feature_fingerprint,
        "artifact": artifact_path.name,
        "volatility_buckets": {name: sum(value == name for value in buckets.values()) for name in ("baja", "media", "alta")},
    }
    manifest_path = artifact_path.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    start = pd.Timestamp(feature_result.returns.index.min()).date()
    end = pd.Timestamp(feature_result.returns.index.max()).date()
    session.merge(MLClusterRun(
        run_id=run_id,
        artifact_path=str(artifact_path),
        universe_size=len(numeric),
        observation_start=start,
        observation_end=end,
        seed=seed,
        n_clusters=manifest["n_clusters"],
        silhouette=evaluation.silhouette,
        stability_ari=evaluation.stability_ari,
        passed_thresholds=evaluation.passed_thresholds,
    ))
    session.exec(delete(MLClusterMembership).where(MLClusterMembership.run_id == run_id))
    for symbol, label in evaluation.labels.items():
        session.add(MLClusterMembership(run_id=run_id, symbol=symbol, cluster_label=label))
    session.commit()
    logger.info("ml.train.done instruments=%d clusters=%d passed_thresholds=%s",
                len(numeric), manifest["n_clusters"], evaluation.passed_thresholds)
    return {**manifest, "manifest_path": str(manifest_path), "artifact_path": str(artifact_path)}


def run_ingest(session: Session, *, period: str = "2y") -> IngestResult:
    with log_stage(logger, "ml.ingest"):
        result = ingest_history(session, period=period)
    logger.info("ml.ingest.result downloaded=%d errors=%d", result.downloaded, len(result.errors))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingesta batch y entrenamiento ML offline de InvestiQ")
    parser.add_argument("command", choices=("ingest", "train", "all"))
    parser.add_argument("--period", default="2y", help="Horizonte yfinance (por defecto: 2y)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--artifact-dir", default="ml/artifacts")
    args = parser.parse_args()

    from investiq.settings import get_settings
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("startup.begin component=data_pipeline command=%s", args.command)
    from investiq.data.database import database_url

    url = database_url()
    with log_stage(logger, "pipeline.database"):
        ensure_sqlite_parent(url)
        engine = create_db(make_engine(url))
    try:
        with Session(engine) as session:
            if args.command in ("ingest", "all"):
                result = run_ingest(session, period=args.period)
                print(json.dumps({"downloaded": result.downloaded, "errors": result.errors}, indent=2))
                if result.errors and not result.downloaded:
                    raise SystemExit("ingestion failed for all requested instruments")
            if args.command in ("train", "all"):
                report = run_training(session, artifact_dir=args.artifact_dir, seed=args.seed)
                print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        engine.dispose()
        logger.info("shutdown.done component=data_pipeline")


if __name__ == "__main__":
    main()
