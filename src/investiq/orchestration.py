"""Coordinate routing, deterministic execution, grounded narration and logging."""

from sqlmodel import Session

from investiq.domain import AssistantResponse, ResponseDiagnostics, RouterDecision
from investiq.handlers import execute_query
from investiq.llm import ChatNVIDIAClient, LLMUnavailable
from investiq.query_log import purge_query_logs, record_response
from investiq.response_style import provider_failure, safe_narration
from investiq.responses import make_response
from investiq.routing import normalize_decision, route_query
from investiq.settings import Settings


def answer_query(session: Session, email: str, query: str, settings: Settings,
                 client: ChatNVIDIAClient | None = None, *, decision: RouterDecision | None = None,
                 history: list[dict] | None = None, use_preferences: bool = True,
                 diagnostics: ResponseDiagnostics | None = None, explanation_level: str = "standard",
                 auto_client: bool = True) -> AssistantResponse:
    diagnostics = diagnostics if diagnostics is not None else ResponseDiagnostics()
    query = query.strip()[:2000]
    if not query:
        return make_response("unknown", "Escribe una consulta para comenzar.")
    if auto_client and client is None and settings.has_nvidia_key:
        try:
            client = ChatNVIDIAClient(settings)
        except LLMUnavailable as error:
            diagnostics.fallback_reason = provider_failure(error)
    decision = (normalize_decision(decision, query=query) if decision is not None
                else route_query(query, client, diagnostics=diagnostics))
    result = execute_query(session, email, query, settings, decision,
                           use_preferences=use_preferences, explanation_level=explanation_level)
    if result.facts:
        facts = {**result.facts, "conversation_context": history or [], "explanation_level": explanation_level}
        narrated = safe_narration(client, decision.intent, query, facts, result.sources,
                                  result=(result.answer if result.protected_narration
                                          or decision.intent != "education" else None),
                                  diagnostics=diagnostics)
        if narrated:
            result.answer = narrated
    response = make_response(decision.intent, result.answer, sources=result.sources, status=result.status,
                             tools=result.tools_used, client=client, diagnostics=diagnostics)
    record_response(session, email, response, settings.query_log_retention_days)
    return response
