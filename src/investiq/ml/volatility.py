from collections.abc import Mapping

import pandas as pd

BUCKETS = ("baja", "media", "alta")


def assign_volatility_buckets(volatility: Mapping[str, float] | pd.Series) -> dict[str, str]:
    """Assign approximately equal sized, ordered tertiles with stable tie handling."""
    values = pd.Series(dict(volatility), dtype="float64").dropna().sort_index()
    values = values[values.map(lambda value: pd.notna(value) and value >= 0)]
    if len(values) < 3 or values.nunique() < 3:
        raise ValueError("three non-empty volatility buckets require at least 3 distinct values")
    order = values.sort_values(kind="mergesort").index.tolist()
    size = len(order)
    result: dict[str, str] = {}
    for rank, symbol in enumerate(order):
        bucket_index = min(2, (rank * 3) // size)
        result[symbol] = BUCKETS[bucket_index]
    return result


def volatility_bucket(symbol: str, buckets: Mapping[str, str]) -> str | None:
    return buckets.get(symbol)
