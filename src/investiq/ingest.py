from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlmodel import Session

from investiq.data.database import save_price_bars, seed_instruments
from investiq.instruments import INSTRUMENTS


@dataclass(frozen=True)
class IngestResult:
    downloaded: dict[str, int]
    errors: dict[str, str]


def fetch_yfinance_history(symbols: list[str], period: str = "2y") -> pd.DataFrame:
    import yfinance as yf

    return yf.download(
        tickers=symbols,
        period=period,
        interval="1d",
        auto_adjust=True,
        group_by="ticker",
        progress=False,
        threads=True,
    )


def _symbol_frame(data: pd.DataFrame, symbol: str, symbol_count: int) -> pd.DataFrame:
    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        if symbol in data.columns.get_level_values(0):
            frame = data[symbol]
        elif symbol in data.columns.get_level_values(-1):
            frame = data.xs(symbol, axis=1, level=-1)
        else:
            return pd.DataFrame()
    elif symbol_count == 1:
        frame = data
    else:
        return pd.DataFrame()
    column = "Close" if "Close" in frame.columns else "Adj Close" if "Adj Close" in frame.columns else None
    return frame[[column]].rename(columns={column: "adjusted_close"}) if column else pd.DataFrame()


def ingest_history(
    session: Session,
    *,
    symbols: Iterable[str] | None = None,
    period: str = "2y",
    downloader: Callable[[list[str], str], pd.DataFrame] = fetch_yfinance_history,
) -> IngestResult:
    symbols = list(symbols or [item.symbol for item in INSTRUMENTS])
    seed_instruments(session)
    errors: dict[str, str] = {}
    downloaded: dict[str, int] = {}
    try:
        data = downloader(symbols, period)
    except Exception as exc:  # the provider may fail as a whole; existing rows remain intact
        return IngestResult({}, {symbol: f"batch download failed: {exc}" for symbol in symbols})

    for symbol in symbols:
        frame = _symbol_frame(data, symbol, len(symbols))
        if frame.empty:
            errors[symbol] = "no adjusted closing prices returned"
            continue
        values: list[tuple[date, float]] = []
        for stamp, row in frame.iterrows():
            raw = row["adjusted_close"]
            if pd.isna(raw):
                continue
            values.append((pd.Timestamp(stamp).date(), float(raw)))
        if not values:
            errors[symbol] = "no valid prices returned"
            continue
        downloaded[symbol] = save_price_bars(session, symbol, values)
    return IngestResult(downloaded, errors)
