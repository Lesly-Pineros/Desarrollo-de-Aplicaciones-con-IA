"""Optional local recall of sanitized dialogue state, never literal conversation text."""

import json
from datetime import datetime, timedelta, timezone
from typing import get_args

from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session

from investiq.data.models import ConversationMemory
from investiq.domain import ConversationState, PendingField, RouterDecision
from investiq.instruments import QUOTE_INSTRUMENT_BY_SYMBOL
from investiq.language import canonical_education_topic
from investiq.sector_context import MARKETS

_PENDING_FIELDS = set(get_args(PendingField))
_LEVELS = {"basic", "standard", "advanced"}


class MemorySnapshot(BaseModel):
    enabled: bool = True
    state: ConversationState = Field(default_factory=ConversationState)
    updated_at: datetime | None = None
    summary: str = "Aún no tengo un tema o una consulta pendiente guardados."


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _covered(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip().upper()
    return candidate if candidate in QUOTE_INSTRUMENT_BY_SYMBOL else None


def _decision(decision: RouterDecision | None) -> RouterDecision | None:
    if decision is None:
        return None
    intent = decision.intent
    if intent == "education":
        # Preserve only a glossary key, never the original question or a generated summary.
        canonical = canonical_education_topic(decision.education_topic or "")
        return RouterDecision(intent="education", education_topic=canonical) if canonical else None
    if intent == "sector_performance":
        market = decision.sector_market if decision.sector_market in MARKETS else None
        universe = decision.sector_universe if decision.sector_universe in {"NASDAQ", "S&P 500"} else None
        return RouterDecision(intent=intent, sector_market=market, sector_universe=universe)
    if intent == "market_news":
        from investiq.news_context import NEWS_COUNTRIES, NEWS_SECTORS
        return RouterDecision(intent=intent, symbol=_covered(decision.symbol),
            news_sector=decision.news_sector if decision.news_sector in NEWS_SECTORS else None,
            news_country=decision.news_country if decision.news_country in NEWS_COUNTRIES else None)
    if intent == "explore":
        from investiq.preferences import SECTORS
        return RouterDecision(intent=intent, exploration_kind=decision.exploration_kind,
            exploration_horizon=decision.exploration_horizon, volatility_target=decision.volatility_target,
            reference_symbol=_covered(decision.reference_symbol), reference_skipped=bool(decision.reference_skipped),
            exploration_sector=decision.exploration_sector if decision.exploration_sector in SECTORS else None)
    if intent in {"explanation", "instrument_info"}:
        return RouterDecision(intent=intent, symbol=_covered(decision.symbol))
    if intent == "recommend_volatility":
        target = decision.volatility_target if decision.volatility_target in {"baja", "media", "alta"} else None
        return RouterDecision(intent="recommend_volatility", volatility_target=target)
    if intent == "recommend_similar":
        return RouterDecision(intent="recommend_similar", reference_symbol=_covered(decision.reference_symbol))
    if intent == "compare":
        symbols = list(dict.fromkeys(symbol for value in decision.comparison_symbols if (symbol := _covered(value))))[:4]
        return RouterDecision(intent="compare", comparison_symbols=symbols)
    if intent == "unknown":
        return RouterDecision()
    return None


def _sanitized(state: ConversationState) -> ConversationState:
    pending_field = state.pending_field if state.pending_field in _PENDING_FIELDS else None
    level = getattr(state, "explanation_level", "standard")
    clean = {
        "pending_field": pending_field,
        "pending_decision": _decision(state.pending_decision) if pending_field else None,
        "last_decision": _decision(state.last_decision),
        "preferences_offered": bool(state.preferences_offered),
        "explanation_level": level if level in _LEVELS else "standard",
    }
    return ConversationState.model_validate(clean)


def _encode(state: ConversationState) -> str:
    return json.dumps(state.model_dump(mode="json", exclude={"history"}, exclude_none=True, exclude_defaults=True),
                      ensure_ascii=False, sort_keys=True)


def _summary(state: ConversationState, *, enabled: bool) -> str:
    if not enabled:
        return "El recuerdo entre visitas está desactivado."
    pieces = []
    last = state.last_decision
    if last:
        if last.intent == "education" and last.education_topic:
            pieces.append(f"Hablamos de {last.education_topic}.")
        elif last.intent == "sector_performance":
            pieces.append("Querías consultar liderazgo sectorial actual" +
                          (f" de {last.sector_universe}" if last.sector_universe else "") +
                          (f" en {last.sector_market}." if last.sector_market else "."))
        elif last.intent == "market_news":
            pieces.append("Consultamos noticias financieras; los titulares no se guardan en esta memoria.")
        elif last.intent == "explore":
            pieces.append("Explorábamos acciones o ETF con criterios para una consulta educativa.")
        elif last.intent in {"explanation", "instrument_info"} and last.symbol:
            pieces.append(f"Estábamos explorando {last.symbol}.")
        elif last.intent == "recommend_similar" and last.reference_symbol:
            pieces.append(f"Buscábamos instrumentos parecidos a {last.reference_symbol}.")
        elif last.intent == "recommend_volatility" and last.volatility_target:
            pieces.append(f"Explorábamos volatilidad {last.volatility_target}.")
        elif last.intent == "compare" and last.comparison_symbols:
            pieces.append("Estábamos comparando " + " y ".join(last.comparison_symbols) + ".")
    pending = {
        "mode": "Quedó pendiente elegir cómo explorar instrumentos.",
        "volatility": "Quedó pendiente elegir la volatilidad que quieres explorar.",
        "reference": "Quedó pendiente elegir un símbolo de referencia.",
        "comparison_symbols": "Quedó pendiente elegir los símbolos para comparar.",
        "comparison_preference": "Quedó pendiente saber si quieres usar alguna preferencia para comparar.",
        "preference_beta": "Quedó pendiente elegir la beta objetivo que quieres usar.",
        "education_topic": "Quedó pendiente elegir qué palabra o símbolo quieres entender.",
        "sector_market": "Quedó pendiente elegir el mercado para la consulta sectorial.",
        "instrument_symbol": "Quedó pendiente elegir un símbolo del catálogo para consultar sus métricas.",
        "news_scope": "Quedó pendiente elegir sector o país de las noticias.",
        "explore_kind": "Quedó pendiente elegir acciones, ETF o ambos.",
        "explore_horizon": "Quedó pendiente conocer el plazo para explorar candidatos.",
        "explore_volatility": "Quedó pendiente elegir la variación histórica deseada.",
        "explore_reference": "Quedó pendiente elegir u omitir una referencia para explorar.",
        "explore_sector": "Quedó pendiente aclarar el sector de los candidatos.",
    }
    if state.pending_field:
        pending_summary = pending.get(state.pending_field)
        if pending_summary:
            pieces.append(pending_summary)
        if state.pending_decision and state.pending_decision.comparison_symbols:
            pieces.append("La comparación era entre " + " y ".join(state.pending_decision.comparison_symbols) + ".")
    level = getattr(state, "explanation_level", "standard")
    if level == "basic":
        pieces.append("Prefieres explicaciones sencillas.")
    elif level == "advanced":
        pieces.append("Prefieres explicaciones más detalladas.")
    return " ".join(pieces) or "Aún no tengo un tema o una consulta pendiente guardados."


def load_memory(session: Session, user_id: str, retention_days: int = 90) -> MemorySnapshot:
    entry = session.get(ConversationMemory, user_id)
    if entry is None:
        return MemorySnapshot()
    now = datetime.now(timezone.utc)
    expiry = min(_aware(entry.expires_at), _aware(entry.updated_at) + timedelta(days=max(1, retention_days)))
    try:
        state = ConversationState.model_validate(json.loads(entry.state_json))
    except (json.JSONDecodeError, ValidationError, TypeError):
        state = ConversationState()
    state = _sanitized(state) if entry.enabled and expiry > now else ConversationState()
    encoded = _encode(state)
    # Scrub legacy/malformed contents as well as expired state when it is read.
    if entry.state_json != encoded:
        entry.state_json = encoded
        session.add(entry)
        session.commit()
    updated_at = _aware(entry.updated_at) if encoded != "{}" else None
    return MemorySnapshot(enabled=entry.enabled, state=state, updated_at=updated_at,
                          summary=_summary(state, enabled=entry.enabled))


def save_memory(session: Session, user_id: str, state: ConversationState, retention_days: int = 90) -> None:
    entry = session.get(ConversationMemory, user_id)
    if entry and not entry.enabled:
        return
    now = datetime.now(timezone.utc)
    entry = entry or ConversationMemory(user_id=user_id)
    entry.state_json = _encode(_sanitized(state))
    entry.updated_at = now
    entry.expires_at = now + timedelta(days=max(1, retention_days))
    session.add(entry)
    session.commit()


def set_memory_enabled(session: Session, user_id: str, enabled: bool) -> None:
    entry = session.get(ConversationMemory, user_id)
    if entry and entry.enabled == enabled:
        return
    now = datetime.now(timezone.utc)
    entry = entry or ConversationMemory(user_id=user_id)
    entry.enabled = enabled
    entry.state_json = "{}"
    entry.updated_at = now
    entry.expires_at = now + timedelta(days=90)
    session.add(entry)
    session.commit()


def forget_memory(session: Session, user_id: str) -> None:
    entry = session.get(ConversationMemory, user_id)
    if entry is None:
        return
    entry.state_json = "{}"
    entry.updated_at = datetime.now(timezone.utc)
    session.add(entry)
    session.commit()
