from datetime import datetime
from typing import Literal

from pydantic import AnyUrl, BaseModel, Field, HttpUrl

Intent = Literal[
    "explanation",
    "education",
    "recommend_volatility",
    "recommend_similar",
    "compare",
    "unknown",
]


class SourceReference(BaseModel):
    source_id: str
    title: str
    url: str
    provider: str
    published_at: datetime | None = None
    delayed: bool = False


class RouterDecision(BaseModel):
    intent: Intent = "unknown"
    symbol: str | None = None
    reference_symbol: str | None = None
    comparison_symbols: list[str] = Field(default_factory=list, max_length=4)
    volatility_target: Literal["baja", "media", "alta"] | None = None
    education_topic: str | None = None
    needs_clarification: bool = False


class Narration(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)
    cited_source_ids: list[str] = Field(default_factory=list, max_length=20)


class QuoteResult(BaseModel):
    symbol: str
    price: float | None = None
    change_abs: float | None = None
    change_pct: float | None = None
    as_of: datetime | None = None
    provider: str | None = None
    delayed: bool = False
    source: SourceReference | None = None
    error: str | None = None


class NewsItem(BaseModel):
    title: str
    description: str = ""
    url: HttpUrl
    provider: str
    published_at: datetime | None = None
    delayed: bool = True
    source_id: str


class NewsCollection(BaseModel):
    articles: list[NewsItem] = Field(default_factory=list)
    available: bool = True
    reason: str | None = None


class FilingItem(BaseModel):
    form: str
    filing_date: str
    url: HttpUrl
    accession: str
    source_id: str


class AssistantResponse(BaseModel):
    answer: str
    intent: Intent
    sources: list[SourceReference] = Field(default_factory=list)
    status: Literal["ok", "degraded", "error"] = "ok"
    tools_used: list[str] = Field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None


class PreferenceInput(BaseModel):
    volatility_target: Literal["baja", "media", "alta"] | None = None
    sector: str | None = None
    reference_symbol: str | None = None
    beta_target: float | None = Field(default=None, ge=-3, le=5)
