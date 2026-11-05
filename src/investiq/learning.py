"""Recognize subject-free lesson requests without guessing a financial topic.

Full matches deliberately exclude new subjects: 'por qué importa' can refer to
the last lesson; 'por qué importa la liquidez' is a new retrieval request.
"""

import re
from typing import Literal

from investiq.language import plain

LessonRequest = Literal["example", "simplify", "detail", "cautions", "explanation"]

_REQUESTS: tuple[tuple[LessonRequest, str], ...] = (
    ("example", r"(?:un|otro) ejemplo|(?:dame|ponme|muestrame) (?:un|otro) ejemplo|"
     r"(?:me lo explicas|me puedes explicar|puedes explicarlo|explicamelo|explicalo) con (?:un|otro) ejemplo"),
    ("simplify", r"mas (?:sencill[oa]|simple|facil)|no (?:entendi|entiendo|comprendo)|"
     r"(?:explicalo|explicamelo)(?: mas (?:sencill[oa]|simple|facil))?"),
    ("detail", r"mas detalle|mas detallad[oa]|profundiza|mas tecnic[oa]|mas a fondo"),
    ("cautions", r"(?:(?:que|cuales(?: son)?|que son) )?(?:(?:sus|los|esos) )?riesgos?"
     r"(?: (?:tiene|tienen|hay|de eso|de esto))?|"
     r"(?:(?:que|cuales(?: son)?) )?(?:(?:sus|las|esas) )?(?:desventajas|limitaciones)"
     r"(?: (?:tiene|tienen|hay|de eso|de esto))?"),
    ("explanation", r"por que(?: (?:importa|es importante))?|para que sirve(?: (?:eso|esto))?|"
     r"como (?:asi|funciona(?: (?:eso|esto))?|se (?:interpreta|calcula|mide)(?: (?:eso|esto))?)|"
     r"(?:(?:que|cuales(?: son)?) )?(?:(?:sus|los|las|esos|esas) )?"
     r"(?:costes|costos|comisiones|ventajas)(?: (?:tiene|tienen|hay|de eso|de esto))?"),
)


def lesson_request(query: str) -> LessonRequest | None:
    text = plain(query)
    text = re.sub(r"^(?:(?:y|ahora|tambien)\s+)+", "", text)
    text = re.sub(r"(?:,? por favor| de eso| de esto)$", "", text)
    for kind, pattern in _REQUESTS:
        if re.fullmatch(pattern, text):
            return kind
    return None
