import numpy as np
import pandas as pd

from investiq.ml.features import build_feature_frame


def test_features_are_finite_aligned_and_encode_sector():
    rng = np.random.default_rng(12)
    dates = pd.bdate_range("2025-01-01", periods=100)
    market = rng.normal(0.0004, 0.01, len(dates))
    returns = {
        "AAA": market + rng.normal(0, 0.004, len(dates)),
        "BBB": market * 0.7 + rng.normal(0, 0.006, len(dates)),
        "CCC": -market * 0.2 + rng.normal(0, 0.01, len(dates)),
        "SHORT": rng.normal(0, 0.01, len(dates)),
    }
    prices = pd.DataFrame({key: 100 * np.cumprod(1 + values) for key, values in returns.items()}, index=dates)
    prices.loc[dates[-20]:, "SHORT"] = np.nan
    result = build_feature_frame(prices, {"AAA": "Tech", "BBB": "Tech", "CCC": "Health", "SHORT": "Unknown"}, min_observations=85)
    assert set(result.values.index) == {"AAA", "BBB", "CCC"}
    assert result.excluded["SHORT"]
    assert {"volatility", "mean_peer_correlation", "beta", "sector_Tech", "sector_Health"} <= set(result.values)
    assert np.isfinite(result.values.select_dtypes(include=[np.number]).to_numpy()).all()

