from datetime import date as Date
from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Instrument(SQLModel, table=True):
    symbol: str = Field(primary_key=True)
    name: str
    kind: str
    sector: str


class PriceBar(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("symbol", "date"), {"sqlite_autoincrement": True})

    id: int | None = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    date: Date = Field(index=True)
    adjusted_close: float


class InstrumentFeature(SQLModel, table=True):
    symbol: str = Field(primary_key=True)
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    volatility: float
    mean_peer_correlation: float
    beta: float
    sector: str
    volatility_bucket: str


class MLClusterRun(SQLModel, table=True):
    run_id: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    artifact_path: str
    universe_size: int
    observation_start: Date
    observation_end: Date
    seed: int
    n_clusters: int
    silhouette: float
    stability_ari: float
    passed_thresholds: bool


class MLClusterMembership(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("run_id", "symbol"), {"sqlite_autoincrement": True})

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(index=True)
    symbol: str = Field(index=True)
    cluster_label: int


class UserPreference(SQLModel, table=True):
    email: str = Field(primary_key=True)
    volatility_target: str | None = None
    sector: str | None = None
    reference_symbol: str | None = None
    beta_target: float | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PriceCacheEntry(SQLModel, table=True):
    symbol: str = Field(primary_key=True)
    price: float
    change_abs: float | None = None
    change_pct: float | None = None
    as_of: datetime
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(index=True)
    provider: str
    delayed: bool = False
    source_url: str


class NewsCacheEntry(SQLModel, table=True):
    symbol: str = Field(primary_key=True)
    articles_json: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(index=True)


class FilingCacheEntry(SQLModel, table=True):
    symbol: str = Field(primary_key=True)
    filings_json: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(index=True)


class ProviderUsage(SQLModel, table=True):
    quota_key: str = Field(primary_key=True)
    provider: str = Field(index=True)
    request_count: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QueryLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    intent: str
    tools_json: str
    sources_json: str
    status: str
    input_tokens: int | None = None
    output_tokens: int | None = None
