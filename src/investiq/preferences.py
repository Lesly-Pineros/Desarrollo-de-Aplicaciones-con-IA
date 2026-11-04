"""Explicit preference changes, validated independently of the language model."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from sqlmodel import Session

from investiq.data.models import UserPreference
from investiq.domain import PreferenceInput
from investiq.instruments import INSTRUMENT_BY_SYMBOL, mentioned_symbols
from investiq.language import contains_phrase as _contains, is_preference_query, plain, preference_provenance

SECTORS = {
    "Technology": ("tecnologia", "tecnologico", "tecnologica", "technology"),
    "Financials": ("financiero", "financieros", "financiera", "finanzas", "financials"),
    "Health Care": ("salud", "sanitario", "health care"),
    "Energy": ("energia", "energetico", "energy"),
    "Consumer Staples": ("consumo basico", "consumer staples"),
    "Consumer Discretionary": ("consumo discrecional", "consumer discretionary"),
    "Communication Services": ("comunicaciones", "comunicacion", "communication services"),
    "Broad Market": ("mercado amplio", "broad market"),
}
SECTOR_NAMES = dict(zip(SECTORS, (
    "tecnología", "finanzas", "salud", "energía", "consumo básico",
    "consumo discrecional", "comunicaciones", "mercado amplio",
)))


@dataclass
class PreferenceChange:
    requested: bool = False
    updates: dict = field(default_factory=dict)
    error: str | None = None
    show: bool = False
    reset: bool = False
    skip: bool = False
    clarification_field: Literal["beta_target"] | None = None


def read_preference_change(query: str, *, expected: bool = False, field_hint: str | None = None) -> PreferenceChange:
    """Parse declarations or answers to a preference question, never ordinary filters."""
    text = plain(query)
    change = PreferenceChange()
    if preference_provenance(query, expected=expected) != "own":
        return change
    if expected and re.fullmatch(r"(?:sin preferencias?|no (?:tengo|se|quiero definir)(?: preferencias?)?|paso|saltar|omitir|ninguna|me da igual)", text):
        return PreferenceChange(requested=True, skip=True)
    change.requested = True
    fields = {"volatilidad": "volatility_target", "sector": "sector", "beta": "beta_target", "referencia": "reference_symbol"}
    if re.search(r"\b(?:borra(?:r)?|olvida(?:r)?|elimina(?:r)?|reinicia(?:r)?)\b.*\bpreferencias\b", text):
        change.reset = True
        return change
    if is_preference_query(query):
        change.show = True
        return change
    if "preferencias" in text and not re.search(r"\b(prefiero|preferiria|cambia|cambiar|actualiza|establece)\b", text) and not any(
        _contains(text, term) for term in fields
    ) and not any(_contains(text, alias) for aliases in SECTORS.values() for alias in aliases):
        change.show = True
        return change
    for label, name in fields.items():
        if re.search(r"(?:sin preferencia (?:de |en |para )?|(?:quita|olvida|borra|elimina) (?:mi |el |la )?)" + label, text):
            change.updates[name] = None
    if re.search(r"\b(no|evitar|excepto)\b", text):
        change.error = "Para no interpretar lo contrario de lo que quieres, dime qué criterio sí prefieres. Por ejemplo: «prefiero volatilidad baja»."
        return change

    labels = {"baja": ("baja", "bajo", "suave", "suaves", "poco movimiento", "pocos cambios"),
              "media": ("media", "medio", "moderada", "moderado", "intermedia", "intermedio"),
              "alta": ("alta", "alto", "grandes movimientos", "mucho movimiento")}
    volatility_context = any(word in text for word in ("volatilidad", "movimiento", "cambios")) or (expected and "beta" not in text)
    targets = [target for target, aliases in labels.items() if volatility_context and any(_contains(text, a) for a in aliases)]
    if len(targets) > 1:
        change.error = "Mencionaste varias volatilidades. ¿Cuál quieres usar: baja, media o alta?"
        return change
    if targets and "volatility_target" not in change.updates:
        change.updates["volatility_target"] = targets[0]

    sectors = [sector for sector, aliases in SECTORS.items() if any(_contains(text, alias) for alias in aliases)]
    if len(sectors) > 1:
        change.error = "Por ahora puedo guardar un sector a la vez. ¿Con cuál quieres quedarte?"
        return change
    if sectors and "sector" not in change.updates:
        change.updates["sector"] = sectors[0]
    if "sector" in text and not sectors and "sector" not in change.updates:
        change.error = "Ese sector no está en nuestro catálogo. Podemos usar tecnología, salud, finanzas, energía, comunicaciones, consumo básico, consumo discrecional o mercado amplio. ¿Cuál te interesa?"
        return change

    beta_reply = field_hint == "beta_target" and bool(re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?", text))
    if ("beta" in text or beta_reply) and "beta_target" not in change.updates:
        match = re.search(r"\bbeta\s*(?:(?:objetivo|de|en|ideal|es|igual a)\s*|[:=]\s*)*([-+]?\d+(?:[.,]\d+)?)", "beta " + text if beta_reply else text)
        if not match or not -3 <= float(match[1].replace(",", ".")) <= 5:
            change.error = "¿Qué beta objetivo quieres usar? Puedo guardar un valor entre -3 y 5; si aún no lo tienes claro, podemos omitirlo."
            change.clarification_field = "beta_target"
            return change
        change.updates["beta_target"] = float(match[1].replace(",", "."))

    reference_context = bool(re.search(r"\b(?:referencia|parecid\w*|similar\w*)\b", text))
    bare_symbol = expected and query.strip().upper() in INSTRUMENT_BY_SYMBOL
    if (reference_context or bare_symbol) and "reference_symbol" not in change.updates:
        symbols = mentioned_symbols(query)
        if len(symbols) != 1:
            change.error = "¿Qué símbolo disponible quieres usar como referencia? Puedes elegirlo en la lista de la izquierda."
            return change
        change.updates["reference_symbol"] = symbols[0]
    if not change.updates:
        change.error = "Cuéntame un criterio que te interese: por ejemplo, «volatilidad baja», «sector salud» o «NVDA como referencia». También puedes decir «sin preferencias»."
    else:
        # Validate the complete patch before touching persistent data.
        PreferenceInput.model_validate(change.updates)
    return change


def get_preferences(session: Session, user_id: str) -> PreferenceInput:
    saved = session.get(UserPreference, user_id)
    return PreferenceInput.model_validate(saved.model_dump()) if saved else PreferenceInput()


def has_preferences(session: Session, user_id: str) -> bool:
    return any(value is not None for value in get_preferences(session, user_id).model_dump().values())


def apply_preference_change(session: Session, user_id: str, change: PreferenceChange) -> PreferenceInput:
    current = get_preferences(session, user_id)
    updated = PreferenceInput.model_validate({**current.model_dump(), **change.updates})
    if change.reset:
        saved = session.get(UserPreference, user_id)
        if saved:
            session.delete(saved)
        updated = PreferenceInput()
    else:
        session.merge(UserPreference(email=user_id, **updated.model_dump(), updated_at=datetime.now(timezone.utc)))
    session.commit()
    return updated


def describe_preferences(preferences: PreferenceInput) -> str:
    parts = []
    if preferences.volatility_target:
        parts.append(f"volatilidad {preferences.volatility_target}")
    if preferences.sector:
        parts.append(f"sector {SECTOR_NAMES.get(preferences.sector, preferences.sector)}")
    if preferences.reference_symbol:
        parts.append(f"{preferences.reference_symbol} como referencia")
    if preferences.beta_target is not None:
        parts.append(f"beta objetivo {preferences.beta_target:g}")
    return ", ".join(parts) or "ningún criterio guardado"
