"""Small, explicit mutations of session-only dialogue state."""

from investiq.domain import AssistantResponse, ConversationMessage, ConversationState, PendingField, RouterDecision


def remember_turn(state: ConversationState, query: str | None, response: AssistantResponse,
                  decision: RouterDecision | None = None) -> AssistantResponse:
    if decision is not None:
        state.last_decision = decision.model_copy(deep=True)
    messages = ([ConversationMessage(role="user", content=query[:1200])] if query is not None else [])
    messages.append(ConversationMessage(role="assistant", content=response.answer[:1200]))
    state.history = (state.history + messages)[-8:]
    return response


def clear_pending(state: ConversationState) -> None:
    state.pending_field = None
    state.pending_decision = None


def set_pending(state: ConversationState, field: PendingField, decision: RouterDecision) -> None:
    state.pending_field = field
    state.pending_decision = decision.model_copy(deep=True)
