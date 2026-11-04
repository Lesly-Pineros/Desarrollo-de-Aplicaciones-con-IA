from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

Intent = Literal[
    "explanation",
    "education",
    "recommend_volatility",
    "recommend_similar",
    "compare",
    "unknown",
]

PendingField = Literal[
    "mode", "volatility", "reference", "comparison_symbols", "comparison_preference", "preference_beta",
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


class ResponseDiagnostics(BaseModel):
    routing: Literal["rules", "llm", "context"] = "rules"
    narration: Literal["not_requested", "used", "fallback", "unavailable"] = "not_requested"
    fallback_reason: Literal[
        "not_configured", "provider_timeout", "provider_authentication", "provider_forbidden",
        "provider_rate_limited", "provider_unavailable", "provider_error", "invalid_output",
        "unknown_citation", "extra_number", "extra_symbol", "extra_url", "missing_result",
        "unsafe_advice", "persona_violation", "unverified_claim",
    ] | None = None


class AssistantResponse(BaseModel):
    answer: str
    intent: Intent
    sources: list[SourceReference] = Field(default_factory=list)
    status: Literal["ok", "degraded", "error"] = "ok"
    tools_used: list[str] = Field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    diagnostics: ResponseDiagnostics = Field(default_factory=ResponseDiagnostics)
    clear_history: bool = False


class PreferenceInput(BaseModel):
    volatility_target: Literal["baja", "media", "alta"] | None = None
    sector: str | None = None
    reference_symbol: str | None = None
    beta_target: float | None = Field(default=None, ge=-3, le=5)


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=1200)


class ConversationState(BaseModel):
    """Bounded dialogue state; sanitized recall is stored outside QueryLog."""

    pending_field: PendingField | None = None
    pending_decision: RouterDecision | None = None
    last_decision: RouterDecision | None = None
    preferences_offered: bool = False
    explanation_level: Literal["basic", "standard", "advanced"] = "standard"
    history: list[ConversationMessage] = Field(default_factory=list, max_length=8)
