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
    from investiq.education import match_education_topic

    return match_education_topic(query)


def is_educational_question(query: str) -> bool:
    text = plain(query)
    learning_request = bool(re.search(
        r"\b(?:aprender|entender|comprender|explicame|explica|que (?:es|son|significa)|"
        r"como funciona\w*|para que sirve)\b", text))
    if is_preference_command(query) or (
        is_preference_declaration(query) and not learning_request and "?" not in query and "¿" not in query
    ):
        return False
    topic = canonical_education_topic(query)
    from investiq.instruments import INSTRUMENT_BY_SYMBOL, mentioned_symbols
    from investiq.education import concept_pattern, is_education_subject
    from investiq.knowledge import get_library

    mentioned = mentioned_symbols(query)
    # A named instrument as the explicit subject retains its catalogue route.
    # Incidental symbols in "qué es la volatilidad de AAPL" do not override it.
    for symbol in mentioned:
        item = INSTRUMENT_BY_SYMBOL[symbol]
        expressions = (r"\$?" + re.escape(symbol.casefold()), re.escape(plain(item.name)))
        if any(re.fullmatch(r"(?:(?:y|ahora|tambien)\s+)?" + expression, text)
               for expression in expressions):
            return False
        if any(is_education_subject(re.sub(r"\betf\s+$", "", text[:match.start()]))
               for expression in expressions
               for match in re.finditer(r"(?<!\w)" + expression + r"(?!\w)", text)):
            return False
    if topic and any(is_education_subject(text[:match.start()])
                     for match in re.finditer(r"(?<!\w)" + concept_pattern(topic) + r"(?!\w)", text)):
        return True
    if re.search(r"\b(?:cotiza\w*|cotizacion|subio|bajo|movimiento|noticias|hoy|precio actual)\b", text):
        return False
    if mentioned and re.search(r"\b(?:precio|cuanto vale|cuanto cuesta)\b", text):
        return False
    if mentioned and re.search(r"\b(?:compara\w*|diferencias entre)\b", text):
        return False
    asking = bool("?" in query or "¿" in query or re.search(
        r"\b(?:que|cuales?|como|por que|para que|explica\w*|define\w*|ensen\w*|"
        r"aprender|entender|comprender|diferencia\w*|compar\w*|en que consiste)\b", text))
    return asking and (topic is not None or bool(get_library().search(query, limit=1)))


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
