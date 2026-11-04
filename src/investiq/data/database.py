import threading
from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from investiq.data.models import (
    ConversationMemory,
    FilingCacheEntry,
    Instrument,
    InstrumentFeature,
    MLClusterMembership,
    MLClusterRun,
    NewsCacheEntry,
    PriceBar,
    PriceCacheEntry,
    ProviderUsage,
    QueryLog,
    ResponseTrace,
    UserPreference,
)
from investiq.instruments import INSTRUMENTS
from investiq.settings import get_settings

_schema_init_lock = threading.Lock()


def database_url() -> str:
    return get_settings().database_url


def make_engine(url: str | None = None):
    resolved = url or database_url()
    kwargs = {"check_same_thread": False} if resolved.startswith("sqlite") else {}
    return create_engine(resolved, connect_args=kwargs)


def create_db(engine=None):
    engine = engine or make_engine()
    # Importing every table model registers it in SQLModel.metadata.
    _ = (
        ConversationMemory,
        FilingCacheEntry,
        InstrumentFeature,
        MLClusterMembership,
        MLClusterRun,
        NewsCacheEntry,
        PriceCacheEntry,
        ProviderUsage,
        QueryLog,
        ResponseTrace,
        UserPreference,
    )
    # Streamlit may execute the app for multiple sessions at once. Serialize
    # create_all so two threads cannot both observe a missing table and race
    # to create it in SQLite.
    with _schema_init_lock:
        SQLModel.metadata.create_all(engine)
    return engine


def get_session(engine=None) -> Iterator[Session]:
    with Session(engine or make_engine()) as session:
        yield session


def seed_instruments(session: Session) -> None:
    for spec in INSTRUMENTS:
        current = session.get(Instrument, spec.symbol)
        if current is None:
            session.add(Instrument(symbol=spec.symbol, name=spec.name, kind=spec.kind, sector=spec.sector))
    session.commit()


def save_price_bars(session: Session, symbol: str, bars: list[tuple[object, float]]) -> int:
    """Idempotent upsert keyed by (symbol, date), preserving newer ingested values."""
    existing = {
        bar.date: bar
        for bar in session.exec(select(PriceBar).where(PriceBar.symbol == symbol)).all()
    }
    count = 0
    for day, close in bars:
        if close is None:
            continue
        value = float(close)
        if value <= 0:
            continue
        current = existing.get(day)
        if current is None:
            session.add(PriceBar(symbol=symbol, date=day, adjusted_close=value))
            count += 1
        elif current.adjusted_close != value:
            current.adjusted_close = value
            session.add(current)
            count += 1
    session.commit()
    return count


def ensure_sqlite_parent(url: str) -> None:
    prefix = "sqlite:///"
    if url.startswith(prefix) and url != "sqlite:///:memory:":
        path = Path(url.removeprefix(prefix))
        path.parent.mkdir(parents=True, exist_ok=True)
