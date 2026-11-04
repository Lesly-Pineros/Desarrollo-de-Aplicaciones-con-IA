"""Context resolution and clarification transitions without database or network access."""

import re
from dataclasses import dataclass

from investiq.dialogue.state import clear_pending, set_pending
from investiq.domain import ConversationState, PreferenceInput, RouterDecision
from investiq.instruments import mentioned_symbols
from investiq.language import canonical_education_topic, plain
from investiq.preferences import read_preference_change


@dataclass
class DialogueResolution:
    decision: RouterDecision | None = None
    reply: str | None = None
    used_context: bool = False
    interrupted: bool = False


def resume_pending(query: str, base: RouterDecision, state: ConversationState, *,
                   educational_question: bool = False) -> DialogueResolution:
    if state.pending_field is None:
        return DialogueResolution()
    if educational_question:
        return DialogueResolution(decision=base, interrupted=True)
    field = state.pending_field
    pending = state.pending_decision or RouterDecision()
    text = plain(query)
    mentioned = mentioned_symbols(query)
    slot_reply = base.intent == "unknown" or (
        field == "volatility" and base.intent in {"education", "recommend_volatility"}
    ) or (field == "reference" and base.intent == "recommend_similar") or (
        field == "comparison_symbols" and base.intent == "compare"
    ) or (field == "mode" and base.intent in {"education", "recommend_similar", "recommend_volatility"})
    if not slot_reply:
        clear_pending(state)
        return DialogueResolution()
    if field in {"mode", "volatility"}:
        criteria = read_preference_change(query, expected=True)
        target = criteria.updates.get("volatility_target") if not criteria.error else None
        if field == "mode" and (mentioned or base.intent == "recommend_similar" or "parecid" in text or "similar" in text):
            decision = RouterDecision(intent="recommend_similar", reference_symbol=mentioned[0] if len(mentioned) == 1 else None)
        elif target or "volatilidad" in text:
            decision = RouterDecision(intent="recommend_volatility", volatility_target=target)
        else:
            return DialogueResolution(reply="Podemos explorar por volatilidad —baja, media o alta— o buscar parecidos a un símbolo. ¿Cuál de esos caminos te interesa?", used_context=True)
    elif field == "reference":
        if len(mentioned) != 1:
            return DialogueResolution(reply="¿Qué símbolo disponible quieres usar como referencia? Puedes mirar la lista de la izquierda y decirme uno.", used_context=True)
        decision = pending.model_copy(update={"reference_symbol": mentioned[0], "needs_clarification": False})
    elif field == "comparison_symbols":
        symbols = mentioned if base.intent == "compare" and len(mentioned) >= 2 else list(dict.fromkeys(pending.comparison_symbols + mentioned))
        if len(symbols) < 2:
            if symbols:
                state.pending_decision = pending.model_copy(update={"comparison_symbols": symbols})
            return DialogueResolution(reply="¿Con qué otro instrumento te gustaría compararlo? Dime un símbolo de los disponibles.", used_context=True)
        decision = pending.model_copy(update={"comparison_symbols": symbols[:4], "needs_clarification": False})
    else:
        return DialogueResolution(reply="Puedes decirme un criterio como «volatilidad baja» o «sector salud». Si quieres seguir sin personalizar, escribe «sin preferencias».", used_context=True)
    clear_pending(state)
    return DialogueResolution(decision=decision, used_context=True)


def resolve_followup(query: str, base: RouterDecision, state: ConversationState) -> DialogueResolution:
    text = plain(query)
    previous = state.last_decision
    mentioned = mentioned_symbols(query)
    followup = bool(re.search(r"^(?:y\b|ahora\b|tambien\b|un ejemplo|dame un ejemplo|mas sencillo|mas facil|no entendi|explicalo|por que)", text))
    if previous and followup:
        if previous.intent == "education" and not mentioned and base.intent in {"unknown", "education"} and canonical_education_topic(query) is None:
            return DialogueResolution(decision=previous.model_copy(deep=True), used_context=True)
        if len(mentioned) == 1 and base.intent == "unknown":
            if previous.intent == "explanation":
                return DialogueResolution(decision=RouterDecision(intent="explanation", symbol=mentioned[0]), used_context=True)
            if previous.intent == "recommend_similar":
                return DialogueResolution(decision=RouterDecision(intent="recommend_similar", reference_symbol=mentioned[0]), used_context=True)
    if base.intent == "unknown" and re.search(r"recomien|sugier|(?:busco|busca|dame|muestra|quiero) (?:opciones|alternativas|instrumentos)|que instrumentos", text):
        set_pending(state, "mode", RouterDecision())
        return DialogueResolution(reply="Podemos explorar opciones de dos maneras: por cuánto han variado sus precios o por parecido a un instrumento que ya conoces. ¿Cuál te interesa más?")
    if base.intent == "unknown" and len(mentioned) == 1:
        return DialogueResolution(decision=RouterDecision(intent="explanation", symbol=mentioned[0]))
    return DialogueResolution()


def clarification_for(decision: RouterDecision, preferences: PreferenceInput, state: ConversationState) -> str | None:
    if decision.intent == "recommend_volatility" and not decision.volatility_target:
        decision.volatility_target = preferences.volatility_target
        if not decision.volatility_target:
            set_pending(state, "volatility", decision)
            return "¿Qué volatilidad histórica te interesa explorar: baja, media o alta? No hace falta definir todo un perfil; con eso podemos empezar."
    if decision.intent == "recommend_similar" and not decision.reference_symbol:
        decision.reference_symbol = preferences.reference_symbol
        if not decision.reference_symbol:
            set_pending(state, "reference", decision)
            return "Claro. ¿Qué instrumento quieres tomar como punto de partida? Dime un símbolo de la lista de la izquierda."
    if decision.intent == "compare":
        if len(decision.comparison_symbols) < 2:
            set_pending(state, "comparison_symbols", decision)
            return "¿Qué instrumentos te gustaría comparar? Puedes darme entre dos y cuatro símbolos de los disponibles."
        if not any(value is not None for value in preferences.model_dump().values()) and not state.preferences_offered:
            state.preferences_offered = True
            set_pending(state, "comparison_preference", decision)
            return "Antes de compararlos, ¿hay algo que te importe especialmente? Puedes decirme, por ejemplo, «volatilidad baja», un sector o un símbolo de referencia. Con un criterio basta; también puedes decir «sin preferencias»."
    return None
