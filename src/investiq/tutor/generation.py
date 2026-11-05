"""Retrieve bounded evidence and teach, with a readable offline fallback."""

from dataclasses import asdict, is_dataclass
import re

from pydantic import ValidationError

from investiq.domain import ResponseDiagnostics, SourceReference
from investiq.llm import LLMUnavailable
from investiq.learning import lesson_request
from investiq.response_style import provider_failure
from investiq.tutor.grounding import suspicious_passage, validate_narration
from investiq.tutor.models import TutorNarration, TutorResult

_CURRENT_BROKER_LIMIT = (
    "La biblioteca no permite confirmar disponibilidad, autorización o tarifas vigentes "
    "de una entidad concreta; hay que comprobarlas en las fuentes oficiales de tu país."
)


def _wants_detail(query: str) -> bool:
    from investiq.language import plain

    return lesson_request(query) == "detail" or bool(re.search(r"mas detalle|mas detallad|profundiza|mas tecnico|mas a fondo", plain(query)))


def _current_broker_question(query: str, passages: list, library) -> bool:
    from investiq.language import plain

    documents = [library.get_document(passage.document_id) for passage in passages]
    broker_context = any(document is not None and (
        plain(document.category) == "intermediarios"
        or re.search(r"broker|intermediario", plain(document.title))
    ) for document in documents)
    if not broker_context:
        return False
    text = plain(query)
    explicit = re.search(
        r"hoy|actual|vigente|cuanto (?:cobra|cuesta|pago)|tarifas?|comisiones? actuales?|"
        r"disponib|autorizad|jurisdiccion|pais|residen|elegib|acepta|puedo usar|puedo abrir|se puede usar",
        text,
    )
    # Country names need not be stored or echoed. A geographic phrase is useful
    # even when the application does not maintain a list of every jurisdiction.
    geographic_phrase = bool(re.search(r"\b(?:en|desde)\s+\w+", text)) and not bool(re.search(
        r"\ben (?:bolsa|linea|internet|general|acciones|etfs?|fondos?|inversion|"
        r"el mercado|la bolsa|un(?:a)?|los|las|que)\b", text,
    ))
    return bool(explicit or geographic_phrase)


def _library():
    # Lazy import keeps the LLM contract independent of retrieval initialization.
    from investiq.knowledge import get_library

    return get_library()


def _source_reference(source) -> SourceReference:
    if hasattr(source, "to_reference"):
        return source.to_reference()
    if isinstance(source, SourceReference):
        return source.model_copy(deep=True)
    value = source.model_dump(mode="json") if hasattr(source, "model_dump") else dict(source)
    return SourceReference.model_validate({key: value[key] for key in ("source_id", "title", "url", "provider")})


def _sources(passages: list, used: list[str] | None = None) -> list[SourceReference]:
    seen = set()
    result = []
    for passage in passages:
        if used is not None and passage.passage_id not in used:
            continue
        for source in passage.sources:
            reference = _source_reference(source)
            if reference.source_id not in seen:
                seen.add(reference.source_id)
                result.append(reference)
    return result


def _serialize(passage) -> dict:
    if hasattr(passage, "model_dump"):
        return passage.model_dump(mode="json")
    result = asdict(passage) if is_dataclass(passage) else dict(vars(passage))
    result["sources"] = [_source_reference(source).model_dump(mode="json") for source in passage.sources]
    return result


def _local_answer(query: str, passages: list, library, level: str) -> tuple[str, list]:
    from investiq.language import plain

    request = lesson_request(query)
    example = request == "example" or "ejemplo" in plain(query)
    simple = (request == "simplify" or (level == "basic" and request != "explanation")
              or bool(re.search(r"sencill|mas facil|no entend", plain(query))))
    comparison = bool(re.search(r"diferencia|compara|\bvs\b|versus|relacion|frente a", plain(query)))
    caution_question = request == "cautions" or bool(re.search(
        r"(?:que|cuales|sus)\s+(?:son\s+)?(?:los\s+)?riesgos?|riesgos? (?:de|del)|"
        r"cuidado|perdid|desventaj|peligro|precauci|que debo evitar|salir mal|limitacion", plain(query),
    ))
    selected = []
    answers = []
    for passage in passages:
        if passage.document_id in {item.document_id for item in selected}:
            continue
        document = library.get_document(passage.document_id)
        if document is None:
            continue
        if any(suspicious_passage(part) for part in
               (document.summary, document.explanation, document.example, document.cautions)):
            continue
        selected.append(passage)
        if _wants_detail(query):
            text = "\n\n".join(dict.fromkeys(part.strip() for part in
                                 (document.summary, document.explanation, document.example) if part.strip()))
        elif caution_question and document.cautions:
            text = document.cautions
        elif example:
            text = document.example or document.summary
        elif simple:
            text = "\n\n".join(dict.fromkeys(part.strip() for part in
                                 (document.summary, document.example) if part.strip()))
        elif level == "advanced":
            text = "\n\n".join(dict.fromkeys(part.strip() for part in
                                 (document.summary, document.explanation) if part.strip()))
        else:
            text = "\n\n".join(dict.fromkeys(part.strip() for part in
                                 (document.summary, document.explanation.split("\n\n")[0]) if part.strip()))
        caution = document.cautions.strip()
        if caution and caution not in text:
            text += "\n\n" + caution
        answers.append(text)
        if len(selected) == (2 if comparison else 1):
            break
    if not answers:
        return "No encontré una explicación respaldada para esa pregunta. ¿Qué concepto de inversión te gustaría entender?", []
    return "\n\n".join(answers), selected


def answer_from_knowledge(query: str, *, topic: str | None = None, level: str = "standard",
                          history: list[dict] | None = None, client=None,
                          diagnostics: ResponseDiagnostics | None = None) -> TutorResult:
    """No client is instantiated here. The application applies its disclaimer."""
    diagnostics = diagnostics if diagnostics is not None else ResponseDiagnostics()
    library = _library()
    request = lesson_request(query)
    passages = [passage for passage in library.search(
                    query, topic=topic, limit=4, include_example=level == "basic" and request != "explanation")
                if passage.text.strip() and passage.sources and not suspicious_passage(passage.text)]
    # Retrieval already bounds its own context; retain a second hard ceiling at
    # the generation boundary, including custom/reviewed libraries.
    bounded = []
    size = 0
    for passage in passages:
        size += len(passage.text)
        if size > 7000:
            break
        bounded.append(passage)
    passages = bounded
    facts = {"knowledge_document_ids": list(dict.fromkeys(p.document_id for p in passages)),
             "knowledge_passage_ids": [p.passage_id for p in passages]}
    if not passages:
        facts["knowledge_mode"] = "insufficient"
        diagnostics.narration = "not_requested"
        return TutorResult(
            "No encontré evidencia suficiente en mi biblioteca para responder eso con confianza. "
            "¿Puedes concretar el concepto o decirme qué parte te gustaría entender?",
            facts=facts, status="degraded", diagnostics=diagnostics,
        )
    fallback, selected = _local_answer(query, passages, library, level)
    if not selected:
        facts["knowledge_mode"] = "insufficient"
        diagnostics.narration = "not_requested"
        return TutorResult(fallback, facts=facts, status="degraded", diagnostics=diagnostics)
    facts["knowledge_mode"] = "local"
    result = TutorResult(fallback, sources=_sources(selected), facts=facts,
                         diagnostics=diagnostics)
    if _current_broker_question(query, selected, library):
        result.answer += "\n\n" + _CURRENT_BROKER_LIMIT
        result.status = "degraded"
        result.facts["current_broker_check_required"] = True
        diagnostics.narration = "not_requested"
        return result
    teach = getattr(client, "teach", None) if client is not None else None
    if not callable(teach):
        diagnostics.narration = "unavailable" if client is None else "fallback"
        if diagnostics.fallback_reason is None:
            diagnostics.fallback_reason = "not_configured" if client is None else "invalid_output"
        if client is not None:
            result.status = "degraded"
        return result
    try:
        raw = teach(query, [_serialize(passage) for passage in passages], {
            "level": ("advanced" if _wants_detail(query) else
                      "basic" if request == "simplify" else
                      level if level in {"basic", "standard", "advanced"} else "standard"),
            "recent_messages": (history or [])[-4:],
        })
        narration = raw if isinstance(raw, TutorNarration) else TutorNarration.model_validate(raw)
    except LLMUnavailable as error:
        diagnostics.narration = "fallback"
        diagnostics.fallback_reason = provider_failure(error)
        result.status = "degraded"
        return result
    except (ValidationError, TypeError, ValueError, AttributeError):
        diagnostics.narration = "fallback"
        diagnostics.fallback_reason = "invalid_output"
        result.status = "degraded"
        return result
    except Exception as error:
        # Third-party client failures are sanitized at this boundary too. Never
        # interpolate an exception that might contain request headers or keys.
        diagnostics.narration = "fallback"
        diagnostics.fallback_reason = "provider_timeout" if isinstance(error, TimeoutError) else "provider_error"
        result.status = "degraded"
        return result
    reason, used = validate_narration(narration, passages)
    if reason:
        diagnostics.narration = "fallback"
        diagnostics.fallback_reason = reason
        result.status = "degraded"
        return result
    diagnostics.narration = "used"
    if diagnostics.routing != "rules":
        diagnostics.fallback_reason = None
    result.answer = "\n\n".join(paragraph.text.strip() for paragraph in narration.paragraphs)
    result.sources = _sources(passages, used)
    result.facts = {**facts, "knowledge_mode": "generated", "knowledge_passage_ids": used}
    return result
