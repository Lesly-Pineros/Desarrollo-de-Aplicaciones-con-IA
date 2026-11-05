"""Public dialogue facade; interpretation, transitions and execution live in separate modules."""

import re

from sqlmodel import Session

from investiq.dialogue.commands import handle_context_command, smalltalk_reply
from investiq.dialogue.pending import clarification_for, resolve_followup, resume_pending
from investiq.dialogue.preference_flow import handle_preferences
from investiq.dialogue.state import clear_pending, remember_turn
from investiq.domain import AssistantResponse, ConversationState, ResponseDiagnostics, RouterDecision
from investiq.language import is_educational_question, plain
from investiq.llm import ChatNVIDIAClient, LLMUnavailable
from investiq.memory import load_memory, save_memory
from investiq.orchestration import answer_query
from investiq.preferences import get_preferences
from investiq.query_log import record_response
from investiq.response_style import provider_failure
from investiq.responses import DISCLAIMER, make_response
from investiq.routing import fallback_route, route_query
from investiq.settings import Settings

WELCOME_MESSAGE = (
    "Hola, soy InvestiQ. ¿Qué te gustaría entender hoy? Podemos hablar de un concepto, "
    "explorar un instrumento o comparar opciones.\n\n"
    "Cuéntamelo en tus palabras. Si para una comparación hace falta conocer tus preferencias, "
    "te las preguntaré aquí; también puedes omitirlas.\n\n" + DISCLAIMER
)


def answer_turn(session: Session, email: str, query: str, settings: Settings,
                state: ConversationState | None = None,
                client: ChatNVIDIAClient | None = None) -> AssistantResponse:
    """Restore optional recall, answer, then save only its sanitized summary."""
    query = query.strip()[:2000]
    state = state if state is not None else load_memory(session, email, settings.conversation_memory_days).state
    command = handle_context_command(session, email, query, settings, state)
    if command is not None:
        response = make_response("unknown", command.answer)
        response.clear_history = command.clear_history
        record_response(session, email, response, settings.query_log_retention_days)
        if not command.clear_history:
            remember_turn(state, query, response)
    else:
        response = _answer_turn(session, email, query, settings, state, client)
    save_memory(session, email, state, settings.conversation_memory_days)
    return response


def _answer_turn(session: Session, email: str, query: str, settings: Settings,
                 state: ConversationState, client: ChatNVIDIAClient | None) -> AssistantResponse:
    diagnostics = ResponseDiagnostics()
    client_attempted = client is not None

    def ensure_client():
        nonlocal client, client_attempted
        if not client_attempted:
            client_attempted = True
            if settings.has_nvidia_key:
                try:
                    client = ChatNVIDIAClient(settings)
                except LLMUnavailable as error:
                    diagnostics.fallback_reason = provider_failure(error)
        return client

    def reply(answer: str, *, intent: str = "unknown") -> AssistantResponse:
        response = make_response(intent, answer, client=client, diagnostics=diagnostics)
        record_response(session, email, response, settings.query_log_retention_days)
        return remember_turn(state, query, response)

    courtesy = smalltalk_reply(query, state)
    if courtesy is not None:
        return reply(courtesy)

    base = fallback_route(query)
    concept_question = is_educational_question(query)
    educational_question = concept_question or base.intent == "instrument_info"
    if concept_question:
        base = RouterDecision(intent="education", education_topic=query)
    if state.last_decision and state.last_decision.intent == "education" and base.intent == "unknown" and re.search(
        r"\b(?:ejemplo|mas sencillo|mas facil|no entendi)\b", plain(query)
    ):
        base = state.last_decision.model_copy(deep=True)
        educational_question = True

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
    if decision is None:
        current_client = ensure_client()
        decision = route_query(query, current_client, context={
            "last_decision": state.last_decision.model_dump() if state.last_decision else None,
            "recent_messages": [message.model_dump() for message in state.history[-4:]],
        }, diagnostics=diagnostics) if current_client else base

    question = clarification_for(decision, get_preferences(session, email), state)
    if question is not None:
        return reply(question, intent=decision.intent)
    if not interrupted:
        clear_pending(state)
    response = answer_query(session, email, query, settings, client=ensure_client(), decision=decision,
                            history=[message.model_dump() for message in state.history[-4:]],
                            use_preferences=preference.use_preferences, diagnostics=diagnostics,
                            explanation_level=state.explanation_level, auto_client=False)
    if preference.confirmation:
        response.answer = preference.confirmation + "\n\n" + response.answer
    return remember_turn(state, query, response, decision)
