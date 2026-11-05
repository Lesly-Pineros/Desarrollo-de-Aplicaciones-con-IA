"""Rank study candidates with a fitted model; never forecast investment returns."""

import numpy as np

from investiq.instruments import INSTRUMENT_BY_SYMBOL
from investiq.ml.volatility import assign_volatility_buckets


def rank_candidates(features, artifact, decision, *, limit=3):
    if not artifact.get("passed_thresholds"):
        raise ValueError("El modelo no supera los umbrales de aceptación.")
    if set(features.index) != set(artifact["symbols"]):
        raise ValueError("Las características no cubren el universo entrenado.")
    values = features.reindex(columns=artifact["columns"]).sort_index()
    if not np.isfinite(values.to_numpy(dtype=float)).all() or (values["volatility"] < 0).any():
        raise ValueError("Características incompletas o no finitas.")
    scaled = artifact["scaler"].transform(values)
    predicted = artifact["model"].predict(scaled)
    distances_to_centers = artifact["model"].transform(scaled)
    buckets = assign_volatility_buckets(values["volatility"])
    reference = decision.reference_symbol
    if reference and reference not in values.index:
        raise ValueError("La referencia no está en el modelo aprobado.")
    reference_position = list(values.index).index(reference) if reference else None
    results = []
    for position, symbol in enumerate(values.index):
        item = INSTRUMENT_BY_SYMBOL.get(symbol)
        if item is None or symbol == reference:
            continue
        if decision.exploration_kind != "any" and item.kind.casefold() != decision.exploration_kind:
            continue
        if buckets[symbol] != decision.volatility_target:
            continue
        if decision.exploration_sector and item.sector != decision.exploration_sector:
            continue
        label = int(predicted[position])
        if reference_position is not None:
            distance = float(np.linalg.norm(scaled[position] - scaled[reference_position]))
            other_cluster = int(predicted[reference_position]) != label
        else:
            distance = float(distances_to_centers[position, label])
            other_cluster = False
        results.append({"symbol": symbol, "name": item.name, "kind": item.kind,
            "sector": item.sector, "volatility": float(values.loc[symbol, "volatility"]),
            "beta": float(values.loc[symbol, "beta"]), "volatility_bucket": buckets[symbol],
            "cluster_label": int(artifact["label_map"][label]), "distance": distance,
            "coincidence": 100 / (1 + distance), "different_cluster": bool(other_cluster)})
    return sorted(results, key=lambda row: (row["different_cluster"], row["distance"], row["symbol"]))[:limit]
