from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from investiq.instruments import INSTRUMENT_BY_SYMBOL, BENCHMARK_SYMBOL


@dataclass(frozen=True)
class FeatureResult:
    values: pd.DataFrame
    excluded: dict[str, str]
    returns: pd.DataFrame


def build_feature_frame(
    closes: pd.DataFrame,
    sectors: Mapping[str, str] | None = None,
    *,
    benchmark: str = BENCHMARK_SYMBOL,
    min_observations: int = 60,
) -> FeatureResult:
    """Compute annualized volatility, peer correlation, beta and one-hot sector."""
    prices = closes.apply(pd.to_numeric, errors="coerce").sort_index()
    returns = prices.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    sectors = sectors or {symbol: INSTRUMENT_BY_SYMBOL.get(symbol).sector for symbol in prices.columns if symbol in INSTRUMENT_BY_SYMBOL}
    valid_symbols = [symbol for symbol in prices if returns[symbol].count() >= min_observations]
    excluded = {symbol: f"fewer than {min_observations} daily returns" for symbol in prices if symbol not in valid_symbols}
    if len(valid_symbols) < 3:
        raise ValueError("at least 3 instruments with sufficient history are required")
    returns = returns[valid_symbols]
    market = returns[benchmark] if benchmark in returns else returns.mean(axis=1)
    peer_corr = returns.corr().replace([np.inf, -np.inf], np.nan)
    sectors = {symbol: sectors.get(symbol, "Unknown") for symbol in valid_symbols}
    categories = sorted(set(sectors.values()))
    rows: list[dict[str, float | str]] = []
    for symbol in valid_symbols:
        aligned = pd.concat([returns[symbol], market], axis=1).dropna()
        asset_returns = aligned.iloc[:, 0]
        market_returns = aligned.iloc[:, 1]
        market_variance = float(market_returns.var(ddof=1))
        beta = float(asset_returns.cov(market_returns) / market_variance) if market_variance > 0 else 0.0
        correlations = peer_corr.loc[symbol].drop(labels=[symbol], errors="ignore").dropna()
        row: dict[str, float | str] = {
            "volatility": float(asset_returns.std(ddof=1) * np.sqrt(252)),
            "mean_peer_correlation": float(correlations.mean()) if not correlations.empty else 0.0,
            "beta": beta,
            "sector": sectors[symbol],
        }
        row.update({f"sector_{category}": float(sectors[symbol] == category) for category in categories})
        rows.append(row)
    feature_frame = pd.DataFrame(rows, index=valid_symbols).sort_index()
    return FeatureResult(feature_frame, excluded, returns)
