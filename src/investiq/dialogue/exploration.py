"""One-off exploration criteria; no database, inference of profile or provider."""

import re

from investiq.dialogue.pending import DialogueResolution
from investiq.dialogue.state import clear_pending, set_pending
from investiq.domain import RouterDecision
from investiq.instruments import mentioned_symbols
from investiq.language import is_educational_question, is_preference_command, plain
from investiq.news_context import matching_filter
from investiq.preferences import SECTORS

EXPLORATION_FIELDS = {"explore_kind", "explore_horizon", "explore_volatility", "explore_reference", "explore_sector"}
QUESTIONS = (
    ("exploration_kind", "explore_kind", "¿Qué quieres explorar: acciones, ETF o ambos? Puedes responder solo «ETF», por ejemplo."),
    ("exploration_horizon", "explore_horizon", "¿Cuándo podrías necesitar ese dinero: en menos de un año, en 1–5 años o después de 5 años?"),
    ("volatility_target", "explore_volatility", "¿Qué variación histórica prefieres revisar: baja, media o alta? Es un filtro de búsqueda, no un perfil financiero."),
    ("reference_symbol", "explore_reference", "¿Tienes un símbolo de referencia, como AAPL o SPY? También puedes responder «sin referencia»."),
)


def is_exploration_query(query):
    text = plain(query)
    return bool(re.search(r"\b(?:recomiend\w*|recomendacion\w*|explorar|exploremos|opciones para invertir)\b", text)
                and re.search(r"\b(?:acciones?|etfs?|efts?|invertir|inversion)\b", text)
                and not re.search(r"\b(?:que es|como (?:se|funciona)|significa)\b", text)
                and not re.search(r"\b(?:similares?|parecid\w*)\b", text))


def criteria_patch(query, *, expected=None):
    text = plain(query)
    result = {}
    equity = bool(re.search(r"\bacciones?\b", text))
    fund = bool(re.search(r"\b(?:etfs?|efts?)\b", text))
    if equity or fund or (expected == "explore_kind" and re.search(r"\b(?:ambos|cualquiera|los dos)\b", text)):
        result["exploration_kind"] = "any" if (equity and fund) or not (equity or fund) else "equity" if equity else "etf"
    horizons = set()
    if re.search(r"\b(?:corto plazo|menos de un ano|meses|intrad[a-z]*|necesito (?:el )?dinero (?:hoy|manana))\b", text):
        horizons.add("short")
    if re.search(r"\b(?:medio plazo|mediano plazo|entre (?:uno|1) y (?:cinco|5)(?: anos)?)\b", text):
        horizons.add("medium")
    if re.search(r"\b(?:largo plazo|mas de (?:cinco|5) anos)\b", text):
        horizons.add("long")
    if expected == "explore_horizon":
        if text in {"corto", "corto plazo", "menos de un ano"}:
            horizons.add("short")
        if text in {"medio", "mediano", "intermedio"}:
            horizons.add("medium")
        if text in {"largo", "muchos anos"}:
            horizons.add("long")
        if re.fullmatch(r"(?:entre )?1\s*(?:a|y|[-–])\s*5 anos?", text):
            horizons.add("medium")
        if re.fullmatch(r"(?:mas de |despues de )?5 anos?", text):
            horizons.add("long")
        years = re.fullmatch(r"(\d{1,2}) anos", text)
        if years:
            value = int(years[1])
            horizons.add("long" if value > 5 else "medium" if value >= 1 else "short")
    if len(horizons) == 1:
        result["exploration_horizon"] = horizons.pop()
    if "volatilidad" in text or "variacion" in text or expected == "explore_volatility":
        targets = {target for target, pattern in {"baja": r"\b(?:baj[oa]|suave|poco movimiento)\b",
                   "media": r"\b(?:medi[oa]|moderad[oa])\b", "alta": r"\b(?:alt[oa]|mucho movimiento)\b"}.items()
                   if re.search(pattern, text)}
        if len(targets) == 1:
            result["volatility_target"] = targets.pop()
        elif len(targets) > 1:
            result["volatility_target"] = None
    sector = matching_filter(query, SECTORS)
    if sector:
        result["exploration_sector"] = sector
    elif "sector" in text:
        result["exploration_sector"] = "unsupported"
    if "sin sector" in text or "cualquier sector" in text:
        result["exploration_sector"] = None
    if re.search(r"\b(?:sin referencia|no tengo referencia|ninguna referencia|no conozco ninguno)\b", text):
        result.update(reference_symbol=None, reference_skipped=True)
    elif expected == "explore_reference" or re.search(r"\b(?:referencia|como|parecid\w*)\b", text):
        symbols = mentioned_symbols(query)
        if len(symbols) == 1:
            result.update(reference_symbol=symbols[0], reference_skipped=False)
    return result


def resolve_exploration(query, base, state):
    active = state.pending_field in EXPLORATION_FIELDS
    if base.intent != "explore" and not active:
        return DialogueResolution()
    if active and (base.intent == "instrument_info" or is_educational_question(query)):
        return DialogueResolution()  # Education may interrupt; resume_pending preserves the pending operation.
    if active and (base.intent in {"market_news", "sector_performance", "compare", "explanation", "recommend_similar"}
                   or is_preference_command(query)):
        clear_pending(state)
        return DialogueResolution()
    affirmation = re.sub(r"\b(?:no tengo referencia|no conozco ninguno)\b", "", plain(query))
    if re.search(r"\b(?:no|nunca|excepto|evitar)\b", affirmation):
        set_pending(state, state.pending_field if active else "explore_kind",
                    state.pending_decision if active else RouterDecision(intent="explore"))
        return DialogueResolution(reply="Para usar el criterio que quieres, dime qué tipo de instrumento, plazo o variación sí te interesa explorar.", used_context=active)
    previous = state.pending_decision if active else None
    decision = (previous or RouterDecision(intent="explore")).model_copy(deep=True)
    updates = criteria_patch(query, expected=state.pending_field if active else None)
    decision = decision.model_copy(update=updates)
    if decision.exploration_sector == "unsupported" or (state.pending_field == "explore_sector" and "exploration_sector" not in updates):
        set_pending(state, "explore_sector", decision)
        return DialogueResolution(reply="Ese sector no está en el catálogo del modelo. ¿Quieres tecnología, finanzas, salud, energía, consumo, comunicaciones o seguir «sin sector»?", used_context=active)
    if decision.exploration_kind and decision.exploration_horizon == "short":
        clear_pending(state)
        return DialogueResolution(decision=decision, used_context=active)
    for field, pending, question in QUESTIONS:
        if field == "reference_symbol" and decision.reference_skipped:
            continue
        if getattr(decision, field) is None:
            set_pending(state, pending, decision)
            return DialogueResolution(reply=question, used_context=active)
    clear_pending(state)
    return DialogueResolution(decision=decision, used_context=active)
