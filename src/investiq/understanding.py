"""Ground semantic preference proposals in words supplied by the current user.

The model may suggest a normalization. It cannot persist data, invent values or
use previous turns as evidence of a new preference declaration.
"""

from __future__ import annotations

import math
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from investiq.domain import PreferenceInput
from investiq.instruments import INSTRUMENT_BY_SYMBOL, mentioned_symbols
from investiq.preferences import PreferenceChange, SECTORS, plain
from investiq.language import (
    contains_phrase as _contains, is_preference_command, is_preference_declaration, preference_provenance,
)

PreferenceField = Literal["volatility_target", "sector", "reference_symbol", "beta_target"]


class PreferenceEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: PreferenceField
    value: str | float | None
    evidence: str = Field(min_length=1, max_length=2000)
    operation: Literal["set", "clear"] = "set"

    @field_validator("value", mode="before")
    @classmethod
    def reject_bool_or_complex_value(cls, value):
        if value is not None and (isinstance(value, bool) or not isinstance(value, (str, int, float))):
            raise ValueError("Preference values must be scalar")
        return value


class PreferenceProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["preference", "question", "one_off", "none"] = "none"
    changes: list[PreferenceEvidence] = Field(default_factory=list, max_length=4)
    needs_clarification: bool = False


_ACTION = re.compile(r"\b(?:busc\w*|filtra\w*|dame|muestra\w*|compara\w*|recomien\w*)\b")
_NEGATION = re.compile(r"\b(?:no|nunca|excepto|evitar|evita)\b|\bsin\s+(?!preferencia\b)")
_NUMBERS = re.compile(r"(?<![\w.])[-+]?\d+(?:[.,]\d+)?(?![\w.])")
_PRICE_CONTEXT = re.compile(r"\b(?:volatilidad|precio|movimientos?|cambios?|variaciones?|sobresaltos?|subidas?|bajadas?)\b")
_VOLATILITY_WORDS = {
    "baja": (
        "baja", "bajo", "suave", "suaves", "poco movimiento", "pocos cambios",
        "pocas variaciones", "pocos sobresaltos", "movimientos pequenos",
        "se mueva poco", "se mueva poquito", "precio tranquilo",
    ),
    "media": ("media", "medio", "moderada", "moderado", "intermedia", "intermedio", "intermedios"),
    "alta": (
        "alta", "alto", "mucho movimiento", "grandes movimientos", "movimientos grandes",
        "muchos cambios", "muchas variaciones", "cambios fuertes", "sube y baja mucho", "se mueva mucho",
    ),
}
_FIELD_NAMES = {
    "volatility_target": "volatilidad",
    "sector": "sector",
    "reference_symbol": "referencia",
    "beta_target": "beta",
}
_CLARIFICATION = (
    "Quiero asegurarme de entenderte. ¿Qué criterio te gustaría guardar? Puedes decirme "
    "una volatilidad, un sector, una beta o un símbolo de referencia."
)


def _volatility_values(text: str, *, expected: bool) -> set[str]:
    if not _PRICE_CONTEXT.search(text) and not expected:
        return set()
    # "Beta alta" and "riesgo bajo" are not volatility declarations.
    if not _PRICE_CONTEXT.search(text) and re.search(r"\b(?:beta|riesgo)\b", text):
        return set()
    return {
        target for target, aliases in _VOLATILITY_WORDS.items()
        if any(_contains(text, alias) and not (alias == "baja" and "sube y baja" in text) for alias in aliases)
    }


def _sector_values(text: str) -> set[str]:
    return {
        sector for sector, aliases in SECTORS.items()
        if any(_contains(text, alias) for alias in aliases)
    }


def _numeric_values(text: str) -> list[float]:
    return [float(match[0].replace(",", ".")) for match in _NUMBERS.finditer(text)]


def _safe_current(current: dict | None) -> dict[str, str | float]:
    """Never forward arbitrary fields or private/raw state to the model."""
    if not isinstance(current, dict):
        return {}
    safe: dict[str, str | float] = {}
    if isinstance(current.get("volatility_target"), str) and current["volatility_target"] in _VOLATILITY_WORDS:
        safe["volatility_target"] = current["volatility_target"]
    if isinstance(current.get("sector"), str) and current["sector"] in SECTORS:
        safe["sector"] = current["sector"]
    if isinstance(current.get("reference_symbol"), str) and current["reference_symbol"] in INSTRUMENT_BY_SYMBOL:
        safe["reference_symbol"] = current["reference_symbol"]
    beta = current.get("beta_target")
    if isinstance(beta, (int, float)) and not isinstance(beta, bool) and -3 <= beta <= 5 and math.isfinite(beta):
        safe["beta_target"] = float(beta)
    return safe


def _clears_field(text: str, field: PreferenceField) -> bool:
    return bool(re.search(
        r"(?:\b(?:quita|olvida|borra|elimina)\s+(?:mi |el |la )?|\bsin preferencia\s+(?:de |en |para )?)"
        + re.escape(_FIELD_NAMES[field]) + r"\b",
        text,
    ))


def _supported_change(change: PreferenceEvidence, query: str, *, expected: bool) -> bool:
    # An exact excerpt, rather than a model-written explanation, is the evidence.
    if change.evidence not in query:
        return False
    evidence = plain(change.evidence)
    whole_message = plain(query)
    if change.operation == "clear":
        return change.value is None and _clears_field(evidence, change.field)
    if change.value is None:
        return False
    if _clears_field(whole_message, change.field):
        return False
    if change.field == "volatility_target":
        return (
            change.value in _VOLATILITY_WORDS
            and _volatility_values(evidence, expected=expected) == {change.value}
            and len(_volatility_values(whole_message, expected=expected)) == 1
        )
    if change.field == "sector":
        return change.value in SECTORS and _sector_values(evidence) == {change.value} and len(_sector_values(whole_message)) == 1
    if change.field == "reference_symbol":
        return (
            isinstance(change.value, str)
            and change.value in INSTRUMENT_BY_SYMBOL
            and mentioned_symbols(change.evidence) == [change.value]
            and not (re.search(r"\bo\b", whole_message) and len(mentioned_symbols(query)) > 1)
        )
    if change.field == "beta_target":
        return (
            isinstance(change.value, (int, float))
            and not isinstance(change.value, bool)
            and math.isfinite(change.value)
            and -3 <= change.value <= 5
            and _contains(evidence, "beta")
            and _numeric_values(evidence) == [float(change.value)]
            and not (re.search(r"\bo\b", whole_message) and len(_numeric_values(whole_message)) > 1)
        )
    return False


def semantic_preference_change(
    query: str,
    client: Any,
    *,
    expected: bool = False,
    current: dict | None = None,
) -> PreferenceChange | None:
    """Return an atomic validated patch, or let the deterministic dialogue continue.

    Only current user words can justify a change. A model or provider error is
    never copied into the returned explanation or logs.
    """
    interpret = getattr(client, "interpret_preferences", None)
    if not callable(interpret):
        return None
    text = plain(query)
    if re.fullmatch(r"(?:hola|buenas|gracias|muchas gracias|perfecto|genial|listo|adios)", text):
        return None
    if preference_provenance(query, expected=expected) != "own":
        return None
    explicit = is_preference_declaration(query) or is_preference_command(query)
    if _ACTION.search(text) and not explicit:
        return None
    if _NEGATION.search(text):
        return PreferenceChange(
            requested=True,
            error="Para guardar lo que realmente quieres, dime qué criterio sí prefieres. Podemos dejar los demás sin definir.",
        )
    try:
        result = interpret(query, {
            "expecting_preference": bool(expected),
            "current_preferences": _safe_current(current),
        })
    except Exception:
        # The provider wrapper owns the safe diagnostic. Preserve local fallback.
        return None
    try:
        proposal = result if isinstance(result, PreferenceProposal) else PreferenceProposal.model_validate(result)
    except (ValidationError, TypeError, ValueError):
        return PreferenceChange(requested=True, error=_CLARIFICATION)
    if proposal.kind != "preference":
        return None
    if proposal.needs_clarification or not proposal.changes:
        return PreferenceChange(requested=True, error=_CLARIFICATION)
    updates = {}
    for change in proposal.changes:
        if change.field in updates or not _supported_change(change, query, expected=expected):
            return PreferenceChange(requested=True, error=_CLARIFICATION)
        updates[change.field] = change.value
    try:
        validated = PreferenceInput.model_validate(updates)
    except (ValidationError, TypeError, ValueError):
        return PreferenceChange(requested=True, error=_CLARIFICATION)
    return PreferenceChange(requested=True, updates=validated.model_dump(exclude_unset=True))
