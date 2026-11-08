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
REQUIRED_CRITERIA = (
    ("exploration_kind", "explore_kind"),
    ("exploration_horizon", "explore_horizon"),
    ("volatility_target", "explore_volatility"),
)
CRITERIA_LABELS = {
    "exploration_kind": "tipo de instrumento: acciones, ETF o ambos",
    "exploration_horizon": "plazo aproximado en que se mantendría el dinero",
    "volatility_target": "preferencia por variaciones históricas bajas, moderadas o altas",
}


def known_exploration_criteria(decision: RouterDecision) -> dict[str, str]:
    values = {
        "exploration_kind": {"equity": "acciones", "etf": "ETF", "any": "acciones y ETF"},
        "exploration_horizon": {"short": "menos de un año", "medium": "entre uno y cinco años",
                                "long": "más de cinco años"},
        "volatility_target": {"baja": "variaciones históricas bajas", "media": "variaciones históricas moderadas",
                              "alta": "variaciones históricas altas"},
    }
    result = {}
    for field, _ in REQUIRED_CRITERIA:
        value = getattr(decision, field)
        if value is not None:
            result[CRITERIA_LABELS[field]] = values[field][value]
    if decision.exploration_sector and decision.exploration_sector != "unsupported":
        result["sector"] = decision.exploration_sector
    return result


def offline_exploration_clarification(
    missing: tuple[str, ...] | list[str], known: RouterDecision | None = None,
) -> str:
    """Ask only for missing criteria and briefly acknowledge anything understood."""
    missing_set = set(missing)
    known = known or RouterDecision(intent="explore")
    known_parts = []
    if known.exploration_kind:
        known_parts.append({"equity": "te interesan las acciones", "etf": "te interesan los ETF",
                            "any": "te interesan acciones o ETF"}[known.exploration_kind])
    if known.exploration_horizon:
        known_parts.append({"short": "piensas mantener el dinero a corto plazo",
                            "medium": "piensas mantener el dinero entre uno y cinco años",
                            "long": "piensas mantener el dinero a largo plazo"}[known.exploration_horizon])
    if known.volatility_target:
        known_parts.append({"baja": "prefieres pocos vaivenes", "media": "prefieres cambios moderados",
                            "alta": "no te incomoda que haya más movimiento"}[known.volatility_target])

    acknowledgement = ""
    if known_parts:
        if len(known_parts) == 1:
            description = known_parts[0]
        elif len(known_parts) == 2:
            description = " y ".join(known_parts)
        else:
            description = f"{known_parts[0]}, {known_parts[1]} y {known_parts[2]}"
        acknowledgement = f"Veo que {description}. "

    ordered = [field for field, _ in REQUIRED_CRITERIA if field in missing_set]
    if ordered == ["exploration_kind"]:
        question = "¿Te interesan más las acciones, los ETF o te da igual?"
    elif ordered == ["exploration_horizon"]:
        question = "¿Qué plazo tienes en mente para mantener el dinero: meses, alrededor de un año o varios años?"
    elif ordered == ["volatility_target"]:
        question = "¿Qué tanto te acomodan las subidas y bajadas del precio: pocas, moderadas o marcadas?"
    elif ordered == ["exploration_kind", "exploration_horizon"]:
        question = "¿Te interesan más las acciones, los ETF o ambos, y por cuánto tiempo piensas mantener la inversión?"
    elif ordered == ["exploration_kind", "volatility_target"]:
        question = ("¿Prefieres acciones, ETF o ambos, y qué tanto te acomodan las subidas y bajadas: "
                    "pocas, moderadas o marcadas?")
    elif ordered == ["exploration_horizon", "volatility_target"]:
        question = ("¿Qué plazo tienes en mente y qué tanto te acomodan las subidas y bajadas: "
                    "pocas, moderadas o marcadas?")
    else:
        question = ("¿Te interesan más las acciones, los ETF o ambos, por cuánto tiempo piensas mantener "
                    "la inversión y qué tanto te acomodan las subidas y bajadas del precio: pocas, "
                    "moderadas o marcadas?")
    return acknowledgement + question


def is_exploration_query(query):
    text = plain(query)
    return bool(re.search(r"\b(?:recomiend\w*|recomendacion\w*|explorar|exploremos|opciones para invertir|"
                         r"quiero invertir|busco invertir|estoy buscando invertir)\b", text)
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
    if re.search(r"\b(?:corto plazo|menos de un ano|meses|medio ano|semestre|intrad[a-z]*|"
                 r"necesito (?:el )?dinero (?:hoy|manana))\b", text):
        horizons.add("short")
    if re.search(r"\b(?:medio plazo|mediano plazo|entre (?:uno|1) y (?:cinco|5)(?: anos)?)\b", text):
        horizons.add("medium")
    if re.search(r"\b(?:algunos|varios|un par de) anos\b", text):
        horizons.add("medium")
    if re.search(r"\b(?:largo plazo|mas de (?:cinco|5) anos)\b", text):
        horizons.add("long")
    if re.search(r"\b(?:por|durante|en)\s+(?:un|uno|1)\s+ano\b", text):
        horizons.add("medium")
    years = re.search(r"\b(\d{1,2})\s+anos?\b", text)
    if years:
        value = int(years[1])
        horizons.add("long" if value > 5 else "medium" if value >= 1 else "short")
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
    low_risk = bool(re.search(
        r"\b(?:no soy de tomar riesgos?|no me gusta arriesgar|no quiero asumir riesgos?|"
        r"prefiero evitar riesgos?|no quiero (?:tomar|asumir|correr) (?:mucho )?riesgos?|"
        r"riesgo bajo|pocos? riesgos?|conservador(?:a)?|"
        r"no sea tan volatil|no quiero que sea tan volatil|no tan volatil|no muy volatil|"
        r"menos volatil|poco volatil|mas estable|algo estable|estable|tranquil[oa]|"
        r"sin tantos altibajos|pocos altibajos|sin tantos movimientos?|sin mucho movimiento|"
        r"que no fluctue mucho|pocas fluctuaciones?|"
        r"pocas? subidas y bajadas?|subidas y bajas? pocas?)\b", text))
    if low_risk:
        result["volatility_target"] = "baja"
    elif ("volatil" in text or "variacion" in text or "subida" in text or "bajada" in text
          or expected == "explore_volatility"):
        negated = bool(re.search(
            r"\b(?:no quiero|no me gusta|prefiero evitar|evito)\b.{0,28}"
            r"\b(?:variacion|volatilidad|movimiento)\b.{0,12}\b(?:alt[oa]|much[oa])\b", text))
        targets = set() if negated else {
            target for target, pattern in {
                "baja": r"\b(?:baj[oa]s?|suaves?|poco movimiento|pocas variaciones?|pocos cambios|"
                        r"pocas? subidas y bajadas?|subidas y bajas? pocas?)\b",
                "media": r"\b(?:medi[oa]s?|moderad[oa]s?)\b",
                "alta": r"\b(?:alt[oa]s?|mucho movimiento|muchas variaciones?|muchos cambios)\b",
            }.items() if re.search(pattern, text)
        }
        if len(targets) == 1:
            result["volatility_target"] = targets.pop()
    sector = matching_filter(query, SECTORS)
    if sector:
        result["exploration_sector"] = sector
    elif "sector" in text:
        result["exploration_sector"] = "unsupported"
    if "sin sector" in text or "cualquier sector" in text:
        result["exploration_sector"] = None
    if re.search(r"\b(?:sin referencia|no tengo referencia|ninguna referencia|no conozco(?: ninguno)?|no se cual)\b", text):
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
    previous = state.pending_decision if active else None
    decision = (previous or RouterDecision(intent="explore")).model_copy(deep=True)
    updates = criteria_patch(query, expected=state.pending_field if active else None)
    decision = decision.model_copy(update=updates)
    if decision.exploration_sector == "unsupported" or (state.pending_field == "explore_sector" and "exploration_sector" not in updates):
        set_pending(state, "explore_sector", decision)
        return DialogueResolution(reply="Ese sector no está en el catálogo del modelo. ¿Quieres tecnología, finanzas, salud, energía, consumo, comunicaciones o seguir «sin sector»?", used_context=active)
    if decision.exploration_horizon == "short":
        clear_pending(state)
        return DialogueResolution(decision=decision, used_context=active)
    missing = tuple(field for field, _ in REQUIRED_CRITERIA if getattr(decision, field) is None)
    if missing:
        pending_field = dict(REQUIRED_CRITERIA)[missing[0]]
        set_pending(state, pending_field, decision)
        return DialogueResolution(used_context=active, clarification_fields=missing)
    clear_pending(state)
    return DialogueResolution(decision=decision, used_context=active)
