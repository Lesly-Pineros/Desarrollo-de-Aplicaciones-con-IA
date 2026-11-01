import pytest

from investiq.ml.volatility import assign_volatility_buckets, volatility_bucket


def test_volatility_buckets_are_ordered_balanced_and_deterministic():
    values = {f"S{i:02}": float(i) for i in range(12)}
    buckets = assign_volatility_buckets(values)
    assert [sum(value == label for value in buckets.values()) for label in ("baja", "media", "alta")] == [4, 4, 4]
    assert buckets == assign_volatility_buckets(dict(reversed(list(values.items()))))
    assert volatility_bucket("S11", buckets) == "alta"


def test_bucket_assignment_rejects_non_distinct_values():
    with pytest.raises(ValueError):
        assign_volatility_buckets({"A": 0.1, "B": 0.1, "C": 0.1})
