from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class SimilarityEvaluation:
    model: dict[str, Any]
    labels: dict[str, int]
    silhouette: float
    stability_ari: float
    passed_thresholds: bool


def _normalized_label_map(centers: np.ndarray) -> dict[int, int]:
    ordered = sorted(range(len(centers)), key=lambda i: tuple(np.round(centers[i], 12)))
    return {original: normalized for normalized, original in enumerate(ordered)}


def fit_similarity_model(
    features: pd.DataFrame,
    *,
    seed: int = 42,
    min_silhouette: float = 0.25,
    min_stability_ari: float = 0.6,
    max_clusters: int = 6,
    stability_seeds: tuple[int, ...] = (43, 44, 45),
) -> SimilarityEvaluation:
    numeric = features.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan).dropna(axis=0)
    numeric = numeric.sort_index()
    if len(numeric) < 4:
        raise ValueError("at least 4 complete instrument feature rows are required")
    if numeric.shape[1] < 2:
        raise ValueError("at least 2 numeric features are required")
    scaler = StandardScaler().fit(numeric)
    scaled = scaler.transform(numeric)
    candidates: list[tuple[float, int, KMeans]] = []
    for k in range(2, min(max_clusters, len(numeric) - 1) + 1):
        candidate = KMeans(n_clusters=k, random_state=seed, n_init=20).fit(scaled)
        if len(set(candidate.labels_)) < 2 or len(set(candidate.labels_)) >= len(numeric):
            continue
        score = float(silhouette_score(scaled, candidate.labels_))
        candidates.append((score, k, candidate))
    if not candidates:
        raise ValueError("no valid K-Means candidate could be evaluated")
    score, k, model = max(candidates, key=lambda item: (item[0], -item[1]))
    stability_scores = []
    for repeat_seed in stability_seeds:
        repeated = KMeans(n_clusters=k, random_state=repeat_seed, n_init=20).fit(scaled)
        stability_scores.append(adjusted_rand_score(model.labels_, repeated.labels_))
    stability = float(np.mean(stability_scores)) if stability_scores else 1.0
    label_map = _normalized_label_map(model.cluster_centers_)
    labels = {symbol: label_map[int(label)] for symbol, label in zip(numeric.index, model.labels_, strict=True)}
    artifact = {
        "schema_version": 1,
        "algorithm": "KMeans",
        "seed": seed,
        "columns": list(numeric.columns),
        "symbols": list(numeric.index),
        "scaler": scaler,
        "model": model,
        "label_map": label_map,
        "labels": labels,
        "silhouette": score,
        "stability_ari": stability,
        "passed_thresholds": score >= min_silhouette and stability >= min_stability_ari,
    }
    return SimilarityEvaluation(artifact, labels, score, stability, artifact["passed_thresholds"])


def save_model_artifact(artifact: dict[str, Any], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, path)
    return path


def load_model_artifact(path: str | Path) -> dict[str, Any]:
    return joblib.load(path)


def similar_instruments(
    symbol: str,
    features: pd.DataFrame,
    artifact: dict[str, Any],
    *,
    top_n: int = 5,
) -> list[tuple[str, int, float]]:
    """Return (symbol, cluster, scaled distance), preferring same-cluster peers."""
    if symbol not in features.index:
        raise KeyError(f"unknown instrument: {symbol}")
    columns = artifact["columns"]
    rows = features.reindex(columns=columns).replace([np.inf, -np.inf], np.nan).dropna()
    if symbol not in rows.index:
        raise ValueError(f"incomplete features for {symbol}")
    scaled = artifact["scaler"].transform(rows)
    scaled_frame = pd.DataFrame(scaled, index=rows.index)
    query_label = artifact["labels"][symbol]
    query = scaled_frame.loc[symbol].to_numpy()
    scored = []
    label_map = artifact["label_map"]
    for candidate in rows.index:
        if candidate == symbol:
            continue
        original_label = int(artifact["model"].predict(scaled_frame.loc[[candidate]])[0])
        label = label_map[original_label]
        distance = float(np.linalg.norm(scaled_frame.loc[candidate].to_numpy() - query))
        scored.append((0 if label == query_label else 1, distance, candidate, label))
    scored.sort()
    return [(candidate, label, distance) for _, distance, candidate, label in scored[:max(0, top_n)]]
