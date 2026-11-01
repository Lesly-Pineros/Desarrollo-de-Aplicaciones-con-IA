from datetime import date

from sqlmodel import Session

from investiq.data.database import create_db, make_engine, save_price_bars
from investiq.providers.market_data import market_quote
from investiq.providers.news import news
from investiq.providers.sec import sec_docs
from investiq.settings import Settings


def test_quote_falls_back_to_explicit_historical_price_without_key(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'quote.db'}"))
    with Session(engine) as session:
        save_price_bars(session, "AAPL", [(date(2026, 1, 1), 100), (date(2026, 1, 2), 102)])
        result = market_quote(session, "AAPL", Settings())
        assert result.price == 102
        assert result.change_pct == 2
        assert result.delayed and result.source.provider == "yfinance histórico"
        assert "no es tiempo real" in result.source.title


def test_optional_news_does_not_call_network_without_key(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'news.db'}"))
    def forbidden(*args, **kwargs):
        raise AssertionError("network should not be called")
    with Session(engine) as session:
        result = news(session, "AAPL", Settings(), http_get=forbidden)
        assert not result.available
        assert "no se consultaron" in result.reason


def test_sec_requires_contact_before_network(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'sec.db'}"))
    def forbidden(*args, **kwargs):
        raise AssertionError("network should not be called")
    with Session(engine) as session:
        filings, reason = sec_docs(session, "AAPL", Settings(sec_user_agent=""), http_get=forbidden)
        assert filings == []
        assert "SEC_USER_AGENT" in reason
