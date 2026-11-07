"""Coordinate routing, deterministic execution, grounded narration and logging."""

import logging
import re

from sqlmodel import Session

from investiq.domain import AssistantResponse, ConversationState, ResponseDiagnostics, RouterDecision
from investiq.newsroom import answer_news
from investiq.handlers import execute_query
from investiq.llm import ChatNVIDIAClient, LLMUnavailable
from investiq.query_log import purge_query_logs, record_response
from investiq.response_style import provider_failure, safe_narration
from investiq.responses import make_response
from investiq.routing import normalize_decision, route_query
from investiq.settings import Settings
from investiq.tutor import answer_from_knowledge
from investiq.sector_context import educational_part, is_current_sector_query, sector_market
from investiq.logging_config import log_stage

logger = logging.getLogger(__name__)


def answer_query(session: Session, email: str, query: str, settings: Settings,
                 client: ChatNVIDIAClient | None = None, *, decision: RouterDecision | None = None,
                 history: list[dict] | None = None, use_preferences: bool = True,
                 diagnostics: ResponseDiagnostics | None = None, explanation_level: str = "standard",
                 auto_client: bool = True, conversation_state: ConversationState | None = None) -> AssistantResponse:
    diagnostics = diagnostics if diagnostics is not None else ResponseDiagnostics()
    query = query.strip()[:2000]
    if not query:
        return make_response("unknown", "Escribe una consulta para comenzar.")
    if is_current_sector_query(query) and not (decision and decision.intent == "market_news"):
        decision = RouterDecision(intent="sector_performance", sector_market=sector_market(query))
    if auto_client and client is None and settings.has_nvidia_key and not (
        decision is not None and decision.intent == "sector_performance"
    ):
        try:
            logger.info("llm.client.initialize.start")
            client = ChatNVIDIAClient(settings)
            logger.info("llm.client.initialize.done")
        except LLMUnavailable as error:
            diagnostics.fallback_reason = provider_failure(error)
            logger.warning("llm.client.initialize.fallback category=%s",
                           getattr(error, "provider_failure_category", "provider-error"))
    decision = (normalize_decision(decision, query=query) if decision is not None
                else route_query(query, client, diagnostics=diagnostics))
    logger.info("orchestration.decision intent=%s routing=%s", decision.intent, diagnostics.routing)
    if decision.intent == "market_news":
        with log_stage(logger, "orchestration.news"):
            result = answer_news(session, query, decision, settings,
                conversation_state if conversation_state is not None else ConversationState(),
                client=client, diagnostics=diagnostics)
    elif decision.intent == "education":
        with log_stage(logger, "orchestration.education"):
            result = answer_from_knowledge(query, topic=decision.education_topic,
                                           level=explanation_level, history=history,
                                           client=client, diagnostics=diagnostics)
    else:
        with log_stage(logger, "orchestration.tools", intent=decision.intent):
            result = execute_query(session, email, query, settings, decision,
                                   use_preferences=use_preferences, explanation_level=explanation_level)
    logger.info("orchestration.result intent=%s status=%s tools=%s",
                decision.intent, result.status, ",".join(result.tools_used) or "none")
    if decision.intent == "sector_performance" and (lesson := educational_part(query)):
        teaching = answer_from_knowledge(lesson, level=explanation_level, history=history,
                                        client=client, diagnostics=diagnostics)
        result.answer = teaching.answer + "\n\n" + result.answer
        result.sources = teaching.sources + result.sources
        result.tools_used = teaching.tools_used + result.tools_used
    if getattr(result, "facts", None) and decision.intent not in {"education", "market_news"}:
        facts = {**result.facts, "conversation_context": history or [], "explanation_level": explanation_level}
        if client is None:
            logger.info("orchestration.narration.skipped reason=no_model")
        else:
            with log_stage(logger, "orchestration.narration"):
                narrated = safe_narration(client, decision.intent, query, facts, result.sources,
                                          result=result.answer,
                                          diagnostics=diagnostics)
            if narrated:
                result.answer = narrated
    if decision.intent == "explore" and re.search(
            r"(?:\$\s*\d|\b(?:capital|presupuesto|monto|dolares?|euros?)\b)", query.lower()):
        result.answer += ("\n\nEl monto que mencionas no se utiliza para filtrar ni ordenar estos candidatos; "
                          "la exploración se basa en los criterios históricos indicados.")
    response = make_response(decision.intent, result.answer, sources=result.sources, status=result.status,
                             tools=result.tools_used, client=client, diagnostics=diagnostics)
    response.actions = getattr(result, "actions", [])
    with log_stage(logger, "orchestration.record_response"):
        record_response(session, email, response, settings.query_log_retention_days)
    logger.info("orchestration.done intent=%s status=%s", response.intent, response.status)
    return response
