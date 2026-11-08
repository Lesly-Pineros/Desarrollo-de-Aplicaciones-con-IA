"""Public dialogue facade; interpretation, transitions and execution live in separate modules."""

import logging
from sqlmodel import Session

from investiq.dialogue.commands import handle_context_command, smalltalk_reply
from investiq.dialogue.pending import clarification_for, resolve_education_followup, resolve_followup, resume_pending
from investiq.dialogue.preference_flow import PreferenceTurn, handle_preferences
from investiq.dialogue.exploration import (CRITERIA_LABELS, REQUIRED_CRITERIA, known_exploration_criteria,
                                           offline_exploration_clarification, resolve_exploration)
from investiq.dialogue.state import clear_pending, remember_turn, set_pending
from investiq.domain import AssistantResponse, ConversationState, ResponseDiagnostics, RouterDecision
from investiq.language import is_educational_question
from investiq.llm import ChatNVIDIAClient, LLMUnavailable
from investiq.knowledge import get_library
from investiq.memory import load_memory, save_memory
from investiq.orchestration import answer_query
from investiq.preferences import get_preferences
from investiq.query_log import record_response
from investiq.response_style import provider_failure
from investiq.responses import DISCLAIMER, make_response
from investiq.routing import fallback_route, route_query
from investiq.settings import Settings
from investiq.logging_config import log_stage

logger = logging.getLogger(__name__)

WELCOME_MESSAGE = (
    "Hola, soy InvestiQ, tu profesor de educación financiera. ¿Qué te gustaría entender hoy? "
    "Podemos hablar de acciones, ETF, bolsas, brókers o conceptos de inversión.\n\n"
    "Cuéntamelo en tus palabras. Si para una comparación hace falta conocer tus preferencias, "
    "te las preguntaré aquí; también puedes omitirlas.\n\n" + DISCLAIMER
)


def answer_turn(session: Session, email: str, query: str, settings: Settings,
                state: ConversationState | None = None,
                client: ChatNVIDIAClient | None = None, *, news_selection_id: str | None = None) -> AssistantResponse:
    """Restore optional recall, answer, then save only its sanitized summary."""
    query = query.strip()[:2000]
    logger.info("dialogue.start mode=%s", "configured" if settings.has_nvidia_key else "local")
    if state is None:
        with log_stage(logger, "dialogue.restore_state"):
            state = load_memory(session, email, settings.conversation_memory_days).state
    logger.debug("dialogue.context pending=%s history_messages=%d", state.pending_field is not None,
                 len(state.history))
    command = handle_context_command(session, email, query, settings, state)
    if command is not None:
        response = make_response("unknown", command.answer)
        response.clear_history = command.clear_history
        record_response(session, email, response, settings.query_log_retention_days)
        if not command.clear_history:
            remember_turn(state, query, response)
    else:
        response = _answer_turn(session, email, query, settings, state, client, news_selection_id=news_selection_id)
    with log_stage(logger, "dialogue.save_state"):
        save_memory(session, email, state, settings.conversation_memory_days)
    return response


def _answer_turn(session: Session, email: str, query: str, settings: Settings,
                 state: ConversationState, client: ChatNVIDIAClient | None, *, news_selection_id=None) -> AssistantResponse:
    diagnostics = ResponseDiagnostics()
    client_attempted = client is not None

    def ensure_client():
        nonlocal client, client_attempted
        if not client_attempted:
            client_attempted = True
            if settings.has_nvidia_key:
                try:
                    logger.info("llm.client.initialize.start")
                    client = ChatNVIDIAClient(settings)
                    logger.info("llm.client.initialize.done")
                except LLMUnavailable as error:
                    diagnostics.fallback_reason = provider_failure(error)
                    logger.warning("llm.client.initialize.fallback category=%s",
                                   getattr(error, "provider_failure_category", "provider-error"))
        return client

    def reply(answer: str, *, intent: str = "unknown") -> AssistantResponse:
        response = make_response(intent, answer, client=client, diagnostics=diagnostics)
        record_response(session, email, response, settings.query_log_retention_days)
        return remember_turn(state, query, response)

    courtesy = smalltalk_reply(query, state)
    if courtesy is not None:
        return reply(courtesy)

    base = (RouterDecision(intent="market_news", news_selection=news_selection_id)
            if news_selection_id else fallback_route(query))
    logger.info("dialogue.initial_route intent=%s", base.intent)
    concept_question = base.intent not in {"sector_performance", "market_news", "explore", "instrument_info"} and is_educational_question(query)
    educational_question = concept_question or base.intent == "instrument_info"
    if concept_question:
        base = RouterDecision(intent="education", education_topic=query)
    lesson = resolve_education_followup(query, base, state)
    if lesson is not None:
        base = lesson
        educational_question = True

    exploration = resolve_exploration(query, base, state)
    if exploration.reply is not None:
        return reply(exploration.reply, intent="explore")
    if exploration.clarification_fields:
        missing = [CRITERIA_LABELS[field] for field in exploration.clarification_fields]
        known_decision = state.pending_decision or RouterDecision(intent="explore")
        known = known_exploration_criteria(known_decision)
        text = None
        clarification_client = ensure_client()
        if clarification_client is not None:
            try:
                text = clarification_client.clarify_exploration(known, missing)
            except LLMUnavailable as error:
                logger.info("exploration.clarification.fallback category=%s",
                            getattr(error, "provider_failure_category", "provider-error"))
        return reply(text or offline_exploration_clarification(
            exploration.clarification_fields, known_decision), intent="explore")
    if exploration.decision is not None:
        diagnostics.routing = "context" if exploration.used_context else "rules"
        response = answer_query(session, email, query, settings, decision=exploration.decision,
            client=ensure_client(), auto_client=False, diagnostics=diagnostics,
            explanation_level=state.explanation_level, conversation_state=state)
        return remember_turn(state, query, response, exploration.decision)

    if base.intent == "market_news":
        preference = PreferenceTurn()
    else:
        with log_stage(logger, "dialogue.preferences"):
            preference = handle_preferences(session, email, query, base, state, diagnostics, ensure_client,
                                            educational_question=educational_question)
    if preference.reply is not None:
        return reply(preference.reply)
    decision = preference.decision
    interrupted = False
    if decision is None:
        pending = resume_pending(query, base, state, educational_question=educational_question)
        interrupted = pending.interrupted
        decision = pending.decision
        if pending.used_context:
            diagnostics.routing = "context"
        if pending.reply is not None:
            return reply(pending.reply)
    if decision is None:
        followup = resolve_followup(query, base, state)
        decision = followup.decision
        if followup.used_context:
            diagnostics.routing = "context"
        if followup.reply is not None:
            return reply(followup.reply)
    if decision is None and base.intent in {"sector_performance", "market_news"}:
        decision = base
    if decision is None:
        current_client = ensure_client()
        decision = route_query(query, current_client, context={
            "last_decision": state.last_decision.model_dump() if state.last_decision else None,
            "recent_messages": [message.model_dump() for message in state.history[-4:]],
        }, diagnostics=diagnostics) if current_client else base

    logger.info("dialogue.decision intent=%s routing=%s", decision.intent, diagnostics.routing)

    question = clarification_for(decision, get_preferences(session, email), state)
    if question is not None:
        logger.info("dialogue.clarification intent=%s", decision.intent)
        return reply(question, intent=decision.intent)
    if not interrupted and not (decision.intent == "sector_performance" and not decision.sector_market):
        clear_pending(state)
    if decision.intent == "education":
        passages = get_library().search(query, topic=decision.education_topic, limit=1)
        # Persist only a recovered identity, never an ungrounded question that
        # could later resolve to an incidental word such as 'costes'.
        decision = decision.model_copy(update={"education_topic": passages[0].title if passages else None})
    response = answer_query(session, email, query, settings,
                            client=None if decision.intent == "sector_performance" else ensure_client(), decision=decision,
                            history=[message.model_dump() for message in state.history[-4:]],
                            use_preferences=preference.use_preferences, diagnostics=diagnostics,
                            conversation_state=state,
                            explanation_level=state.explanation_level, auto_client=False)
    if preference.confirmation:
        response.answer = preference.confirmation + "\n\n" + response.answer
    return remember_turn(state, query, response, decision)


def start_guided_exploration(session: Session, email: str, settings: Settings,
                             state: ConversationState | None = None) -> AssistantResponse:
    """Start a guided exploration with an assistant-only, combined clarification."""
    if state is None:
        with log_stage(logger, "dialogue.restore_state"):
            state = load_memory(session, email, settings.conversation_memory_days).state
    clear_pending(state)
    decision = RouterDecision(intent="explore")
    missing = [CRITERIA_LABELS[field] for field, _ in REQUIRED_CRITERIA]
    set_pending(state, REQUIRED_CRITERIA[0][1], decision)
    diagnostics = ResponseDiagnostics()
    client = None
    if settings.has_nvidia_key:
        try:
            logger.info("llm.client.initialize.start")
            client = ChatNVIDIAClient(settings)
            logger.info("llm.client.initialize.done")
        except LLMUnavailable as error:
            diagnostics.fallback_reason = provider_failure(error)
            logger.warning("llm.client.initialize.fallback category=%s",
                           getattr(error, "provider_failure_category", "provider-error"))
    text = None
    if client is not None:
        try:
            text = client.clarify_exploration({}, missing)
        except LLMUnavailable as error:
            logger.info("exploration.clarification.fallback category=%s",
                        getattr(error, "provider_failure_category", "provider-error"))
    response = make_response("explore", text or offline_exploration_clarification(
        tuple(field for _, field in REQUIRED_CRITERIA), decision), client=client, diagnostics=diagnostics)
    record_response(session, email, response, settings.query_log_retention_days)
    remember_turn(state, None, response, decision)
    with log_stage(logger, "dialogue.save_state"):
        save_memory(session, email, state, settings.conversation_memory_days)
    return response
