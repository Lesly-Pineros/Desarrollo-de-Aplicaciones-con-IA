"""Bounded evidence checks for RAG, separate from the strict market renderer.

Literal support and lexical checks cannot prove semantic entailment. They reject
known unsafe/unsupported outputs conservatively; they are not a truth verifier.
"""

import re

from investiq.language import plain
from investiq.instruments import mentioned_symbols
from investiq.tutor.models import TutorNarration

_NUMBERS = re.compile(r"[+-]?\d+(?:[.,]\d+)*(?:\s*%)?")
_WORDS = re.compile(r"[^\W\d_]{3,}", re.UNICODE)
_STOP = frozenset("""
    para como una unas unos uno los las del con por que porque cuando donde este esta
    estos estas ese esa esos esas sus son ser puede pueden puedes esto eso hay mas
    muy tambien entre sobre desde hasta cada algo solo otra otro otras otros sino
    mismo misma mediante tiene tienen tener forma manera todo toda todos todas
    ejemplo imagina piensa trata sirve permite cuenta conviene segun significa
    explica explicar podemos veamos vamos entender sencillo primero despues
""".split())
_TEACHER_STARTERS = _STOP | frozenset("""
    el la un en al a es si no su se lo le les te tu asi antes recuerda revisa
    mira fijate entender compara dicho aunque ahora dos una importante incluso
    finalmente diferencia observa ten por tanto piensa imaginemos considera
""".split())
_NEGATION = re.compile(r"\b(?:no|nunca|tampoco|sin)\b")
_QUALIFIERS = frozenset({"siempre", "nunca", "todos", "todas", "ninguno", "ninguna",
                         "seguro", "segura", "gratuito", "gratuita", "exento", "exenta"})
_INSTRUCTION = re.compile(
    r"ignora(?:r)? (?:todas? )?(?:las? |tus? )?(?:instrucciones|reglas)|"
    r"ignore (?:all |previous )?(?:instructions|rules)|"
    r"system prompt|developer message|\[/?INST\]|"
    r"(?:nvidia|openai)_api_key|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY",
    re.IGNORECASE,
)


def suspicious_passage(text: str) -> bool:
    return bool(_INSTRUCTION.search(text))


def _content_words(text: str) -> set[str]:
    return {word for word in _WORDS.findall(plain(text)) if word not in _STOP}


def _unsafe_text(text: str) -> str | None:
    folded = plain(text)
    if suspicious_passage(text) or "{{" in text or "}}" in text:
        return "unverified_claim"
    if re.search(r"https?://|www\.|local://|javascript:|<[^>]+>", text, re.IGNORECASE):
        return "extra_url"
    if re.search(
        r"(?:^|[.!?]\s+)(?:compra|vende|invierte|elige|contrata|abre una cuenta)\b|"
        r"\b(?:compres|vendas|inviertas)\b|"
        r"\b(?:debes|deberias|tienes que)\b.{0,35}\b(?:comprar|vender|invertir|contratar|elegir)\b|"
        r"(?:te |debes |deberias |tienes que )?(?:recomiendo|recomendamos)\b|"
        r"mejor (?:broker|inversion|accion|etf) (?:para ti|es)|"
        r"(?:es|resulta) (?:el )?mejor (?:broker|inversion|accion|etf)|"
        r"(?:ganancia|rentabilidad|rendimiento|beneficio)s? (?:estan? )?garantizad[oa]s?|"
        r"(?:ganaras|ganaras siempre|no puedes perder)|"
        r"\bgarantiza\w*\b.{0,35}\b(?:ganancia|rentabilidad|rendimiento|beneficio)s?\b|"
        r"(?:esta inversion|este etf|esta accion) (?:es|esta) (?:libre de riesgo|sin riesgo)",
        folded,
    ):
        return "unsafe_advice"
    if re.search(
        r"\bsoy (?:(?:un|una) )?(?:persona|humano|humana)\b|"
        r"\byo (?:tambien )?(?:invierto|inverti|perdi dinero|he invertido)\b|"
        r"en mi experiencia (?:como inversor|invirtiendo)", folded,
    ):
        return "persona_violation"
    if re.search(
        r"\b(?:hoy|ahora mismo|actualmente|en tiempo real)\b.*"
        r"\b(?:cotiza|vale|precio|comision|disponible|autorizad[oa])\b|"
        r"\b(?:subira|bajara|va a subir|va a bajar)\b",
        folded,
    ):
        return "unverified_claim"
    return None


def _unsupported_entity(text: str, support: str) -> bool:
    if set(mentioned_symbols(text)) - set(mentioned_symbols(support)):
        return True
    allowed = {plain(token).strip(".,;:()[]") for token in re.findall(r"[\w&.-]+", support)}
    for token in re.findall(r"[\w&.-]+", text):
        normalized = plain(token).strip(".,;:()[]")
        if not normalized or len(normalized) < 2:
            continue
        if any(character.isupper() for character in token):
            if normalized not in allowed and normalized not in _TEACHER_STARTERS:
                return True
    grammatical = frozenset("""
        es son puede pueden permite ofrece intermediario que para como de del en se un una
        este ese con inverso apalancado indexado diversificado negociado regulado tradicional
        digital online bursatil privado publico
    """.split())
    for match in re.finditer(r"\b(?:broker|bróker|plataforma|empresa|fondo|etf)\s+([\w.-]+)", text, re.IGNORECASE):
        candidate = plain(match.group(1))
        if candidate not in allowed and candidate not in grammatical:
            return True
    return False


def validate_narration(narration: TutorNarration, passages: list) -> tuple[str | None, list[str]]:
    """Return a safe diagnostic and ordered evidence IDs; no raw output in logs."""
    by_id = {passage.passage_id: passage for passage in passages}
    used = []
    total = 0
    for paragraph in narration.paragraphs:
        text = paragraph.text.strip()
        total += len(text)
        if not text or total > 4000:
            return "invalid_output", []
        reason = _unsafe_text(text)
        if reason:
            return reason, []
        quotes = []
        for evidence in paragraph.evidence:
            passage = by_id.get(evidence.passage_id)
            if passage is None:
                return "unknown_citation", []
            quote = " ".join(evidence.quote.split())
            if len(quote) < 18 or len(_content_words(quote)) < 3:
                return "unverified_claim", []
            if quote not in " ".join(passage.text.split()):
                return "unverified_claim", []
            quotes.append(quote)
            if evidence.passage_id not in used:
                used.append(evidence.passage_id)
        support = " ".join(quotes)
        allowed_numbers = {re.sub(r"\s", "", number) for number in _NUMBERS.findall(support)}
        if {re.sub(r"\s", "", number) for number in _NUMBERS.findall(text)} - allowed_numbers:
            return "extra_number", []
        if _unsupported_entity(text, support):
            return "extra_symbol", []
        # Require useful lexical support per sentence, not a token copied from
        # an unrelated citation. This still does not establish semantic truth.
        supported_words = _content_words(support)
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            words = _content_words(sentence)
            if words and (len(words & supported_words) < min(2, len(words))
                          or len(words & supported_words) / len(words) < .35):
                return "unverified_claim", []
            if (set(plain(sentence).split()) & _QUALIFIERS) - set(plain(support).split()):
                return "unverified_claim", []
            # Catch direct inversions of the best matching evidence sentence.
            # Paraphrases with a different logical form may fall back: this is
            # deliberately more conservative than treating a citation as proof.
            evidence_sentences = [part for quote in quotes
                                  for part in re.split(r"(?<=[.!?])\s+", quote) if part.strip()]
            closest = max(evidence_sentences, key=lambda part: len(words & _content_words(part)))
            if bool(_NEGATION.search(plain(sentence))) != bool(_NEGATION.search(plain(closest))):
                return "unverified_claim", []
    return None, used
