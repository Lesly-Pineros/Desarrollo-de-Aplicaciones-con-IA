"""Intent routing and normalization, with an offline Spanish fallback."""

import json
import re

from investiq.domain import ResponseDiagnostics, RouterDecision
from investiq.instruments import mentioned_symbols
from investiq.knowledge import get_library
from investiq.language import canonical_education_topic, is_educational_question, plain
from investiq.learning import lesson_request
from investiq.llm import ChatNVIDIAClient, LLMUnavailable
from investiq.response_style import provider_failure
from investiq.tools import normalize_symbol
from investiq.sector_context import is_current_sector_query, sector_market
from investiq.news_context import news_decision


def fallback_route(query: str) -> RouterDecision:
    text = query.casefold()
    normalized = plain(query)
    covered = mentioned_symbols(query)
    if (headlines := news_decision(query)) is not None:
        return headlines
    from investiq.dialogue.exploration import criteria_patch, is_exploration_query
    if is_exploration_query(query):
        return RouterDecision(intent="explore", **criteria_patch(query))
    if is_current_sector_query(query):
        market = sector_market(query)
        return RouterDecision(intent="sector_performance", sector_market=market,
                              needs_clarification=market is None)
    if (re.search(r"\b(?:metricas?|indicadores?|valores)\b", normalized)
            and (bool(covered) or re.search(r"\b(?:accion(?:es)?|etf|simbolo|ticker)\b", normalized))):
        return RouterDecision(intent="instrument_info", symbol=covered[0] if len(covered) == 1 else None,
                              needs_clarification=not bool(covered))
    if is_educational_question(query):
        return RouterDecision(intent="education", education_topic=query)
    if any(word in text for word in ("compara", "comparar", "comparación", "comparacion", "diferencias entre")):
        return RouterDecision(intent="compare", comparison_symbols=covered[:4],
                              needs_clarification=len(covered) < 2)
    if any(word in text for word in ("similar", "parecido", "semejante")):
        return RouterDecision(intent="recommend_similar", reference_symbol=covered[0] if covered else None,
                              needs_clarification=not bool(covered))
    if any(word in text for word in ("precio", "movimiento", "subió", "bajó", "cotización", "cotizacion", "cuéntame sobre", "cuentame sobre")):
        return RouterDecision(intent="explanation", symbol=covered[0] if covered else None,
                              needs_clarification=not bool(covered))
    if len(covered) == 1 and re.search(
        r"\b(?:que (?:es|significa)|quien es|que empresa es|explica\w*|define\w*|"
        r"hablame de|a que se dedica|que hace|(?:saber|conocer|entender)(?: mas)? (?:sobre|que es|a))\b", normalized,
    ):
        return RouterDecision(intent="instrument_info", symbol=covered[0])
    if any(word in text for word in ("volatilidad", "riesgo bajo", "riesgo medio", "riesgo alto")) and any(
        word in text for word in ("recom", "busca", "dame", "instrumentos", "acciones", "etf")
    ):
        target = next((bucket for bucket in ("baja", "media", "alta") if re.search(r"\b" + bucket + r"\b", text)), None)
        return RouterDecision(intent="recommend_volatility", volatility_target=target,
                              needs_clarification=target is None)
    topic = canonical_education_topic(query)
    document = get_library().get_by_topic(topic) if topic else None
    if (document is not None and document.category != "instrumentos") or any(word in text for word in ("qué es", "que es", "qué significa", "que significa", "explica", "explícame", "explicame", "define", "beta", "volatilidad", "etf", "correlación", "retorno", "riesgo")):
        return RouterDecision(intent="education", education_topic=query)
    return RouterDecision(intent="unknown")


def normalize_decision(decision: RouterDecision, *, query: str) -> RouterDecision:
    """Resolve supported symbols before deterministic handlers consume a decision."""
    # Defining a known ticker is a catalogue lookup, even if the model mistakes
    # the phrase "qué es" for a glossary question or a live market request.
    explicit = fallback_route(query)
    if explicit.intent in {"market_news", "explore"}:
        return decision if decision.intent == explicit.intent else explicit
    if explicit.intent == "sector_performance":
        return explicit
    if explicit.intent == "instrument_info":
        return explicit
    if (explicit.intent == "education" and is_educational_question(query)
            and not (decision.intent == "education" and lesson_request(query))):
        # Retrieved educational evidence never turns into a market-data lookup
        # because a classifier supplied an incidental or invented ticker.
        return explicit
    if canonical_education_topic(query) == "S&P 500" and explicit.intent == "explanation" and not mentioned_symbols(query):
        return explicit
    decision = decision.model_copy(deep=True)
    if decision.symbol:
        decision.symbol = normalize_symbol(decision.symbol)
    if decision.reference_symbol:
        decision.reference_symbol = normalize_symbol(decision.reference_symbol)
    decision.comparison_symbols = [symbol for value in decision.comparison_symbols
                                   if (symbol := normalize_symbol(value))]
    if decision.intent in {"explanation", "instrument_info"} and not decision.symbol:
        decision.symbol = fallback_route(query).symbol
    return decision


def route_query(query: str, client: ChatNVIDIAClient | None, *, context: dict | None = None,
                diagnostics: ResponseDiagnostics | None = None) -> RouterDecision:
    if client:
        try:
            classifier_input = json.dumps({"current_message": query, "conversation_context": context}, ensure_ascii=False) if context else query
            decision = normalize_decision(client.classify(classifier_input), query=query)
            if diagnostics is not None:
                diagnostics.routing = "llm"
            return decision
        except LLMUnavailable as error:
            if diagnostics is not None:
                diagnostics.fallback_reason = provider_failure(error)
    return fallback_route(query)
