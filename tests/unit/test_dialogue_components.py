"""Dialogue transitions can be exercised without creating a database or a client."""

from investiq.dialogue.commands import smalltalk_reply
from investiq.dialogue.pending import clarification_for, resume_pending
from investiq.domain import ConversationState, PreferenceInput, RouterDecision


def test_reference_completion_only_updates_the_pending_operation():
    state = ConversationState(
        pending_field="reference", pending_decision=RouterDecision(intent="recommend_similar"),
    )
    outcome = resume_pending("NVDA", RouterDecision(), state)

    assert outcome.decision.reference_symbol == "NVDA"
    assert outcome.used_context
    assert state.pending_field is None
    assert state.history == []


def test_education_interrupts_a_missing_symbol_and_a_short_reply_can_resume_it():
    state = ConversationState(pending_field="comparison_symbols",
                              pending_decision=RouterDecision(intent="compare", comparison_symbols=["AAPL"]))
    education = RouterDecision(intent="education", education_topic="beta")
    interrupted = resume_pending("¿Qué es beta?", education, state, educational_question=True)
    assert interrupted.interrupted and interrupted.decision.intent == "education"
    assert state.pending_decision.comparison_symbols == ["AAPL"]

    completed = resume_pending("MSFT", RouterDecision(), state)
    assert completed.decision.comparison_symbols == ["AAPL", "MSFT"]
    assert state.pending_field is None


def test_beta_zero_counts_as_a_preference_without_a_questionnaire():
    state = ConversationState()
    decision = RouterDecision(intent="compare", comparison_symbols=["AAPL", "MSFT"])
    assert clarification_for(decision, PreferenceInput(beta_target=0), state) is None
    assert state.pending_field is None


def test_pending_comparison_is_copied_and_cancellation_preserves_the_last_topic():
    state = ConversationState(last_decision=RouterDecision(intent="education", education_topic="beta"))
    decision = RouterDecision(intent="compare", comparison_symbols=["AAPL", "MSFT"])
    assert clarification_for(decision, PreferenceInput(), state)
    decision.comparison_symbols.append("NVDA")
    assert state.pending_decision.comparison_symbols == ["AAPL", "MSFT"]

    assert smalltalk_reply("cancelar", state)
    assert state.pending_field is None
    assert state.last_decision.education_topic == "beta"
