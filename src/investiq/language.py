"""Shared Spanish normalization and provenance checks for user declarations."""

import re
import unicodedata
from typing import Literal

PreferenceProvenance = Literal["own", "question", "reported", "none"]

_DECLARATION = re.compile(
    r"\b(?:prefiero|preferiria|preferencias?|"
    r"me (?:gusta\w*|interesa\w*|acomoda\w*|siento comod\w*|resulta comod\w*)|"
    r"quiero (?:guardar|cambiar|actualizar|definir|que el precio)|"
    r"no quiero (?:volatilidad|el sector|sector|beta)|"
    r"mi (?:volatilidad|beta|sector|referencia)|como (?:mi )?referencia|"
    r"(?:guarda|cambia|actualiza|establece|quita|olvida|borra|elimina)\b.*"
    r"(?:volatilidad|beta|sector|referencia|preferencia))\b"
)
_REPORTED = re.compile(
    r"\b(?:mi (?:amigo|amiga|pareja|padre|madre|hermano|hermana|colega)|"
    r"(?:otra|una) persona|alguien|el texto|la noticia|el filing|el documento|"
    r"el articulo|segun (?:el|la)|dice que|dice|dijo|escribio|"
    r"prefiere|(?:el|ella) preferiria|le gusta|le interesa)\b"
)
_QUESTION = re.compile(
    r"\b(?:que (?:es|significa)|por que|como (?:funciona|se (?:calcula|mide|interpreta))|"
    r"explica\w*|define|definicion|cual(?:es)? son)\b"
)
_CONTROL = re.compile(
    r"^(?:(?:puedes|podrias|quiero que)\s+)?"
    r"(?:borra(?:r)?|olvida(?:r)?|elimina(?:r)?|reinicia(?:r)?|quita(?:r)?|"
    r"muestra(?:me)?|mostrar|dime|ver|consulta(?:r)?)\s+"
    r"(?:(?:mis?|las?|el|tu|tus)\s+)?"
    r"(?:preferencias?|sector|volatilidad|beta|referencia)\b"
)
_OWN_PREFERENCE_QUERY = re.compile(
    r"^(?:(?:cuales? (?:son|eran)|que|como (?:son|eran))\s+)?"
    r"(?:son\s+)?mis preferencias\b"
)


def plain(text: str) -> str:
    normalized = "".join(c for c in unicodedata.normalize("NFD", text.casefold())
                         if not unicodedata.combining(c))
    return " ".join(normalized.split()).strip(" ¿?¡!.,")


def contains_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(plain(phrase)) + r"(?!\w)", plain(text)))


def canonical_education_topic(query: str) -> str | None:
    # Lazy import keeps language helpers independent of tool initialization.
    from investiq.tools import GLOSSARY

    return next((topic for topic in GLOSSARY if contains_phrase(query, topic)), None)


def is_educational_question(query: str) -> bool:
    topic = canonical_education_topic(query)
    if topic is None:
        return False
    text = plain(query)
    if topic == "etf":
        # In "qué es el ETF QQQ", ETF qualifies the named instrument. It is
        # different from "qué es un ETF como QQQ", which asks for the concept.
        from investiq.instruments import INSTRUMENT_BY_SYMBOL, mentioned_symbols

        for symbol in mentioned_symbols(query):
            item = INSTRUMENT_BY_SYMBOL[symbol]
            if item.kind == "ETF" and (
                re.search(r"\betf\s+\$?" + re.escape(symbol.casefold()) + r"\b", text)
                or contains_phrase(query, item.name)
            ):
                return False
    term = re.escape(plain(topic))
    # Concept questions take precedence over incidental references to price.
    # A request such as "explica el movimiento del ETF" remains a market query.
    return bool(re.search(
        r"\b(?:que (?:es|significa)|define|definicion de)\b|"
        r"\bexplica\w*\s+(?:(?:la|el|un|una|sobre)\s+)?" + term + r"\b|"
        r"\b(?:aprender|entender|comprender|no entiendo|no comprendo)\s+"
        r"(?:(?:mejor|bien|mas|un poco|algo)\s+)*"
        r"(?:(?:sobre|acerca de|de|esto de)\s+)?"
        r"(?:(?:la|el|un|una)\s+)?" + term + r"\b|"
        r"\bcomo (?:funciona|se (?:calcula|mide|interpreta))\b|"
        r"\b(?:por que|para que sirve)\s+(?:(?:la|el|un|una)\s+)?" + term + r"\b",
        text,
    ))


def is_preference_query(query: str) -> bool:
    text = plain(query)
    return bool(_OWN_PREFERENCE_QUERY.search(text) or re.search(
        r"^(?:(?:puedes|podrias)\s+)?(?:muestra(?:me)?|mostrar|dime|ver|consulta(?:r)?)\s+"
        r"(?:(?:mis|las)\s+)?preferencias\b", text,
    ) or text in {"preferencias", "mis preferencias"})


def is_preference_command(query: str) -> bool:
    text = plain(query)
    return bool(_CONTROL.search(text) or is_preference_query(query))


def is_preference_declaration(query: str) -> bool:
    return bool(_DECLARATION.search(plain(query)))


def preference_provenance(query: str, *, expected: bool = False) -> PreferenceProvenance:
    """Only current first-person declarations or direct answers can change data."""
    text = plain(query)
    # Commands quoted as data are never executed, including a whole quoted message.
    quoted_message = bool(re.fullmatch(r"[\"'«“].+[\"'»”]", query.strip(), re.DOTALL))
    if quoted_message or _REPORTED.search(text):
        return "reported"
    # Reading/resetting one's configuration can naturally be phrased as a question.
    if is_preference_command(query):
        return "own"
    if is_educational_question(query) or "?" in query or "¿" in query or _QUESTION.search(text):
        return "question"
    if is_preference_declaration(query) or expected:
        return "own"
    return "none"
