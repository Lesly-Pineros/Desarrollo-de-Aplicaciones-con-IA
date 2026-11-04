"""Validate conversational wording while keeping factual rendering in code."""

import re

from investiq.domain import ResponseDiagnostics, SourceReference
from investiq.instruments import mentioned_symbols
from investiq.llm import LLMUnavailable
from investiq.language import plain

RESULT_MARKER = "{{result}}"

# Only these conversational connectors may accompany a verified market block.
# A valid citation alone cannot prove that arbitrary additional prose is true.
FACTUAL_OPENINGS = (
    "", "Con lo que tenemos:", "Veámoslo juntos.", "Vamos paso a paso.",
    "Esto es lo que muestran los datos disponibles.", "Te comparto lo que encontré.",
    "Con los criterios que me compartiste:", "Podemos partir de aquí:",
)
FACTUAL_CLOSINGS = (
    "", "Podemos revisarlo paso a paso.", "Puedes cambiar el criterio y lo revisamos.",
    "Si quieres, podemos explorar alguno con más detalle.", "¿Qué parte te gustaría entender mejor?",
    "¿Quieres que explique cómo interpretar esta comparación?",
    "Si algo no queda claro, lo vemos con un ejemplo.",
)


def _allowed_factual_frame(answer: str) -> bool:
    opening, _, closing = answer.partition(RESULT_MARKER)
    normalize = lambda value: " ".join(value.split()).casefold()
    return normalize(opening) in {normalize(value) for value in FACTUAL_OPENINGS} and normalize(closing) in {
        normalize(value) for value in FACTUAL_CLOSINGS
    }


def provider_failure(error: Exception) -> str:
    category = getattr(error, "provider_failure_category", None)
    return {
        "timeout": "provider_timeout", "authentication": "provider_authentication",
        "forbidden": "provider_forbidden", "rate-limited": "provider_rate_limited",
        "provider-unavailable": "provider_unavailable", "structured-output": "invalid_output",
    }.get(category, "provider_error")


def _prose_failure(text: str) -> str | None:
    folded = plain(text)
    if re.search(r"\d", text):
        return "extra_number"
    if re.search(r"(?:https?://|www\.|local://|javascript:)", text, re.IGNORECASE):
        return "extra_url"
    if mentioned_symbols(text) or any(
        token not in {"ETF", "SEC"} for token in re.findall(r"\b[A-Z]{2,5}(?:-[A-Z])?\b", text)
    ):
        return "extra_symbol"
    if re.search(r"\b(?:compra|compres|comprar|vende|vendas|vender|invierte|inviertas)\b|invertir en|rentabilidad garantizada|mejor inversion", folded):
        return "unsafe_advice"
    if re.search(
        r"\bsoy (?:(?:un|una) )?(?:persona|humano|humana)\b|"
        r"\bcomo (?:(?:un|una|ser) )?(?:persona|humano|humana)\b|"
        r"\byo (?:tambien )?(?:invierto|inverti|perdi dinero|he (?:invertido|perdido dinero|ganado dinero))\b|"
        r"en mi experiencia (?:como inversor|invirtiendo)", folded,
    ):
        return "persona_violation"
    if re.search(r"(?:subio|bajo|subira|bajara) porque|va a (?:subir|bajar)|(?:precio|accion|empresa) (?:sube|baja|vale|rinde)", folded):
        return "unverified_claim"
    return None


def safe_narration(client, intent: str, query: str, facts: dict, sources: list[SourceReference], *,
                   result: str | None = None, diagnostics: ResponseDiagnostics | None = None) -> str | None:
    diagnostics = diagnostics if diagnostics is not None else ResponseDiagnostics()
    if not client:
        diagnostics.narration = "unavailable"
        if diagnostics.fallback_reason is None:
            diagnostics.fallback_reason = "not_configured"
        return None
    payload = {**facts, "response_block": result} if result is not None else facts
    try:
        narration = client.narrate(intent, query, payload, [s.model_dump(mode="json") for s in sources])
    except LLMUnavailable as error:
        diagnostics.narration = "fallback"
        diagnostics.fallback_reason = provider_failure(error)
        return None
    ids = {source.source_id for source in sources}
    cited = set(narration.cited_source_ids)
    reason = None
    if cited - ids or (result is not None and not ids.issubset(cited)):
        reason = "unknown_citation"
    answer = narration.answer.strip()
    if not answer:
        reason = reason or "invalid_output"
    if result is not None and answer.count(RESULT_MARKER) != 1:
        reason = reason or "missing_result"
    prose = answer.replace(RESULT_MARKER, "") if result is not None else answer
    if "{{" in prose or "}}" in prose:
        reason = reason or "missing_result"
    reason = reason or _prose_failure(prose)
    if result is not None and answer.count(RESULT_MARKER) == 1 and not _allowed_factual_frame(answer):
        reason = reason or "unverified_claim"
    if reason:
        diagnostics.narration = "fallback"
        diagnostics.fallback_reason = reason
        return None
    diagnostics.narration = "used"
    # A recovered narration must not erase an earlier classifier failure.
    if diagnostics.routing != "rules":
        diagnostics.fallback_reason = None
    return answer.replace(RESULT_MARKER, result) if result is not None else answer
