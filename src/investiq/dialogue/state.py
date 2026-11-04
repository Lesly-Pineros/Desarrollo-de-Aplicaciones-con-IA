"""Small, explicit mutations of session-only dialogue state."""

from investiq.domain import AssistantResponse, ConversationMessage, ConversationState, PendingField, RouterDecision


def remember_turn(state: ConversationState, query: str, response: AssistantResponse,
                  decision: RouterDecision | None = None) -> AssistantResponse:
    if decision is not None:
        state.last_decision = decision.model_copy(deep=True)
    state.history = (state.history + [
        ConversationMessage(role="user", content=query[:1200]),
        ConversationMessage(role="assistant", content=response.answer[:1200]),
    ])[-8:]
    return response


def clear_pending(state: ConversationState) -> None:
    state.pending_field = None
    state.pending_decision = None


def set_pending(state: ConversationState, field: PendingField, decision: RouterDecision) -> None:
    state.pending_field = field
    state.pending_decision = decision.model_copy(deep=True)
