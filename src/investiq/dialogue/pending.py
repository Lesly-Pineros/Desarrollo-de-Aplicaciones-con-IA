"""Context resolution and clarification transitions without database or network access."""

import re
from dataclasses import dataclass

from investiq.dialogue.state import clear_pending, set_pending
from investiq.domain import ConversationState, PreferenceInput, RouterDecision
from investiq.instruments import mentioned_symbols
from investiq.knowledge import get_library
from investiq.language import canonical_education_topic, plain
from investiq.learning import lesson_request
from investiq.preferences import read_preference_change
from investiq.sector_context import sector_market
from investiq.news_context import news_decision


@dataclass
class DialogueResolution:
    decision: RouterDecision | None = None
    reply: str | None = None
    used_context: bool = False
    interrupted: bool = False


def resolve_education_followup(query: str, base: RouterDecision,
                               state: ConversationState) -> RouterDecision | None:
    """Resolve short lessons and attributes without treating a new subject as old."""
    previous = state.last_decision
    if previous is None or mentioned_symbols(query):
        return None
    library = get_library()
    if previous.intent == "instrument_info" and lesson_request(query):
        document = library.get_by_topic(previous.symbol or "")
        if document is not None and document.category == "instrumentos":
            return RouterDecision(intent="education", education_topic=document.title)
    if previous.intent != "education":
        return None
    text = plain(query)
    topic = canonical_education_topic(query)
    if lesson_request(query) and library.get_by_topic(previous.education_topic or "") is not None:
        return previous.model_copy(deep=True)
    document = library.get_by_topic(previous.education_topic or "")
    broker_context = document is not None and document.category == "intermediarios"
    broker_followup = bool(re.search(
        r"\b(?:puedo (?:usar|utilizar|abrir|acceder)|disponib\w*|autorizad\w*|regulad\w*|"
        r"cuanto (?:cobra\w*|cuesta)|tarifas?|comision\w*|mi pais|residencia|jurisdiccion)\b", text))
    if broker_context and broker_followup and topic is None:
        return previous.model_copy(deep=True)
    return None


def resume_pending(query: str, base: RouterDecision, state: ConversationState, *,
                   educational_question: bool = False) -> DialogueResolution:
    if state.pending_field is None:
        return DialogueResolution()
    if state.pending_field == "education_topic":
        mentioned = mentioned_symbols(query)
        clear_pending(state)
        if base.intent == "unknown" and len(mentioned) == 1:
            return DialogueResolution(
                decision=RouterDecision(intent="instrument_info", symbol=mentioned[0]), used_context=True,
            )
        if base.intent in {"education", "instrument_info"}:
            return DialogueResolution(decision=base, used_context=True)
        if base.intent == "unknown":
            return DialogueResolution(decision=RouterDecision(intent="education", education_topic=query),
                                      used_context=True)
        return DialogueResolution()
    if educational_question:
        return DialogueResolution(decision=base, interrupted=True)
    if state.pending_field == "news_scope":
        if base.intent not in {"unknown", "education", "market_news"}:
            clear_pending(state)
            return DialogueResolution()
        decision = news_decision(query, scope_reply=True)
        if decision.needs_clarification:
            return DialogueResolution(reply="¿Qué sector o país quieres consultar? Por ejemplo: tecnología, finanzas, energía, Colombia o Estados Unidos.", used_context=True)
        previous = state.pending_decision
        if previous:
            decision = previous.model_copy(update={"news_sector": decision.news_sector or previous.news_sector,
                "news_country": decision.news_country or previous.news_country, "needs_clarification": False})
        clear_pending(state)
        return DialogueResolution(decision=decision, used_context=True)
    if state.pending_field == "sector_market":
        market = sector_market(query)
        if market:
            clear_pending(state)
            return DialogueResolution(decision=RouterDecision(
                intent="sector_performance", sector_market=market), used_context=True)
        if base.intent == "unknown":
            return DialogueResolution(reply="¿Qué mercado quieres consultar: Estados Unidos, Colombia, España, Europa o el global?", used_context=True)
        clear_pending(state)
        return DialogueResolution()
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
    lesson = resolve_education_followup(query, base, state)
    if lesson is not None:
        return DialogueResolution(decision=lesson, used_context=True)
    followup = bool(re.search(r"^(?:y\b|ahora\b|tambien\b|un ejemplo|dame un ejemplo|otro ejemplo|mas sencillo|mas simple|mas facil|mas detalle|profundiza|no entendi|explicalo|por que)", text))
    if previous and followup:
        if len(mentioned) == 1 and base.intent == "unknown":
            if previous.intent == "instrument_info":
                return DialogueResolution(decision=RouterDecision(intent="instrument_info", symbol=mentioned[0]),
                                          used_context=True)
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
    if decision.intent == "market_news" and decision.needs_clarification:
        set_pending(state, "news_scope", decision)
        return "¿Qué sector o país quieres consultar? Por ejemplo: tecnología, finanzas, energía, Colombia o Estados Unidos."
    if decision.intent == "sector_performance" and decision.sector_market is None:
        # The handler supplies both the question and the explicit data limit;
        # it can also preserve an educational part of a combined message.
        set_pending(state, "sector_market", decision)
        return None
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
