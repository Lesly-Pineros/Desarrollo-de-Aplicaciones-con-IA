"""Apply only validated preference declarations and coordinate their dialogue effects."""

import re
from dataclasses import dataclass
from typing import Any, Callable

from sqlmodel import Session

from investiq.dialogue.state import clear_pending
from investiq.domain import ConversationState, ResponseDiagnostics, RouterDecision
from investiq.language import (
    is_preference_command, is_preference_declaration, plain, preference_provenance,
)
from investiq.preferences import (
    apply_preference_change, describe_preferences, get_preferences, read_preference_change,
)
from investiq.understanding import semantic_preference_change


@dataclass
class PreferenceTurn:
    decision: RouterDecision | None = None
    reply: str | None = None
    confirmation: str = ""
    use_preferences: bool = True


def handle_preferences(session: Session, user_id: str, query: str, base: RouterDecision,
                       state: ConversationState, diagnostics: ResponseDiagnostics,
                       client_factory: Callable[[], Any], *, educational_question: bool = False) -> PreferenceTurn:
    text = plain(query)
    outcome = PreferenceTurn()
    expecting = state.pending_field in {"comparison_preference", "preference_beta"}
    provenance = preference_provenance(query, expected=expecting)
    declared = is_preference_declaration(query) or is_preference_command(query)
    if provenance == "reported" and not educational_question:
        outcome.reply = "Eso parece una preferencia citada, no una declaración tuya. ¿Quieres que explique su significado o contarme qué prefieres tú?"
        return outcome
    if provenance == "question" and declared and not educational_question:
        outcome.reply = "No voy a asumir una preferencia a partir de esa pregunta. ¿Quieres consultar lo que guardamos o indicarme un criterio nuevo?"
        return outcome
    declaration_hint = declared or bool(re.search(
        r"\b(?:prefiero|preferiria|me gustaria|me interesa|me siento|no me gusta|quiero que)\b", text,
    ))
    explicit_query = bool(re.search(
        r"\b(?:compara\w*|busca\w*|recomiend\w*|muestra\w*|dame|cotizacion|cuanto (?:vale|cuesta)|cuentame sobre)\b|^precio\b", text,
    ))
    new_actionable = base.intent in {"compare", "explanation", "recommend_similar", "recommend_volatility"} and (
        not declaration_hint or explicit_query
    )
    skip = bool(re.search(r"\bsin (?:mis )?preferencias\b|\bsin personalizar\b", text))
    if skip and (base.intent == "compare" or (
        state.pending_field is None and state.last_decision and state.last_decision.intent == "compare"
    )):
        outcome.decision = base if base.intent == "compare" else state.last_decision.model_copy(deep=True)
        outcome.use_preferences = False
        state.preferences_offered = True
        clear_pending(state)
        return outcome
    if expecting and new_actionable and not declared:
        clear_pending(state)
    change = read_preference_change(
        query, expected=state.pending_field in {"comparison_preference", "preference_beta"} and not educational_question,
        field_hint="beta_target" if state.pending_field == "preference_beta" else None,
    )
    if provenance == "own" and not educational_question and (change.error or (not change.requested and re.search(
        r"prefier|preferir|me gustaria|me interesa|me siento|no me gusta", text,
    ))):
        semantic = semantic_preference_change(query, client_factory(),
            expected=state.pending_field in {"comparison_preference", "preference_beta"},
            current=get_preferences(session, user_id).model_dump())
        if semantic is not None:
            if semantic.error and change.clarification_field:
                semantic.clarification_field = change.clarification_field
            change = semantic
    if not change.requested:
        return outcome
    if change.error:
        if change.clarification_field == "beta_target":
            if base.intent == "compare" and len(base.comparison_symbols) >= 2:
                state.pending_decision = base.model_copy(deep=True)
            state.pending_field = "preference_beta"
        elif not state.pending_field:
            state.pending_field = "comparison_preference"
        outcome.reply = change.error
    elif change.show:
        outcome.reply = "Por ahora tengo en cuenta: " + describe_preferences(get_preferences(session, user_id)) + ". Puedes decirme qué quieres cambiar o pedirme que borre tus preferencias."
    elif change.reset:
        apply_preference_change(session, user_id, change)
        clear_pending(state)
        state.preferences_offered = True
        outcome.reply = "Listo, borré tus preferencias. Podemos seguir explorando y definir otras cuando quieras."
    elif change.skip:
        outcome.decision = state.pending_decision
        outcome.use_preferences = False
        clear_pending(state)
        state.preferences_offered = True
        if outcome.decision is None:
            outcome.reply = "De acuerdo. Podemos seguir con conceptos o características de los instrumentos sin personalizar la comparación."
    else:
        saved = apply_preference_change(session, user_id, change)
        outcome.confirmation = "Tomo en cuenta " + describe_preferences(saved) + "."
        if new_actionable:
            outcome.decision = base
            clear_pending(state)
        elif state.pending_field in {"comparison_preference", "preference_beta"} and state.pending_decision:
            outcome.decision = state.pending_decision.model_copy(deep=True)
            diagnostics.routing = "context"
            clear_pending(state)
        elif educational_question:
            outcome.decision = base
        else:
            clear_pending(state)
            outcome.reply = outcome.confirmation + " Puedes cambiar cualquier criterio diciéndomelo aquí. ¿Qué te gustaría explorar?"
    return outcome
