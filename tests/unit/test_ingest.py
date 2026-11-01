import pandas as pd
from sqlmodel import Session, select

from investiq.data.database import create_db, make_engine
from investiq.data.models import PriceBar
from investiq.ingest import ingest_history


def test_batch_ingestion_uses_injected_provider_and_persists_idempotently(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'prices.db'}"))
    dates = pd.bdate_range("2025-01-01", periods=3)
    columns = pd.MultiIndex.from_product([["AAPL", "MSFT"], ["Close"]])
    data = pd.DataFrame([[100, 200], [101, 201], [102, 202]], index=dates, columns=columns)
    calls = []

    def downloader(symbols, period):
        calls.append((symbols, period))
        return data

    with Session(engine) as session:
        first = ingest_history(session, symbols=["AAPL", "MSFT"], downloader=downloader)
        second = ingest_history(session, symbols=["AAPL", "MSFT"], downloader=downloader)
        assert first.errors == {}
        assert first.downloaded == {"AAPL": 3, "MSFT": 3}
        assert second.downloaded == {"AAPL": 0, "MSFT": 0}
        assert len(session.exec(select(PriceBar)).all()) == 6
    assert calls == [(["AAPL", "MSFT"], "2y"), (["AAPL", "MSFT"], "2y")]
