import os

import pytest

from investiq.ingest import fetch_yfinance_history


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("RUN_LIVE_INTEGRATION") != "1", reason="set RUN_LIVE_INTEGRATION=1 to call yfinance")
def test_yfinance_returns_recent_adjusted_prices():
    frame = fetch_yfinance_history(["SPY"], period="5d")
    assert not frame.empty
    close_columns = {column[-1] if isinstance(column, tuple) else column for column in frame.columns}
    assert "Close" in close_columns or "Adj Close" in close_columns
