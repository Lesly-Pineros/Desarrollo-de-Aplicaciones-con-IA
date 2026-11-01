import numpy as np
import pandas as pd

from investiq.ml.similarity import fit_similarity_model, similar_instruments


def sample_features():
    rng = np.random.default_rng(7)
    rows = []
    for cluster, center in enumerate(((0.08, 0.85, 0.9), (0.28, 0.45, 1.3), (0.72, 0.12, 0.5))):
        for i in range(7):
            noise = rng.normal(0, 0.015, 3)
            rows.append((f"G{cluster}-{i}", *(np.array(center) + noise), float(cluster == 0), float(cluster == 1), float(cluster == 2)))
    return pd.DataFrame(rows, columns=("symbol", "volatility", "mean_peer_correlation", "beta", "sector_A", "sector_B", "sector_C")).set_index("symbol")


def test_kmeans_evaluation_is_stable_and_similars_are_ranked():
    features = sample_features()
    first = fit_similarity_model(features, seed=11)
    second = fit_similarity_model(features, seed=11)
    assert first.labels == second.labels
    assert first.silhouette >= 0.25
    assert first.stability_ari >= 0.6
    assert first.passed_thresholds
    neighbors = similar_instruments("G0-0", features, first.model, top_n=5)
    assert len(neighbors) == 5
    assert all(label == first.labels["G0-0"] for _, label, _ in neighbors)
    assert all(symbol != "G0-0" for symbol, _, _ in neighbors)

