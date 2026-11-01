from datetime import date

from sqlmodel import Session, select

from investiq.data.database import create_db, make_engine, save_price_bars, seed_instruments
from investiq.data.models import Instrument, PriceBar


def test_sqlite_schema_and_price_upsert_are_idempotent(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'test.db'}"))
    with Session(engine) as session:
        seed_instruments(session)
        assert session.exec(select(Instrument)).all()
        bars = [(date(2025, 1, 2), 100.0), (date(2025, 1, 3), 101.0)]
        assert save_price_bars(session, "AAPL", bars) == 2
        assert save_price_bars(session, "AAPL", bars) == 0
        saved = session.exec(select(PriceBar).where(PriceBar.symbol == "AAPL")).all()
        assert len(saved) == 2

