"""Curated educational concepts, aliases and evidence; answering needs no network."""

from dataclasses import dataclass
import re

from investiq.domain import SourceReference


@dataclass(frozen=True)
class EducationalConcept:
    definition: str
    example: str
    aliases: tuple[str, ...] = ()
    source: SourceReference | None = None
    protected_narration: bool = False


EDUCATION_CATALOGUE = {
    "S&P 500": EducationalConcept(
        definition=(
            "El S&P 500 es un índice bursátil: una referencia que resume cómo se mueven las "
            "acciones de 500 empresas líderes de Estados Unidos.\n\n"
            "Piensa en él como un termómetro de ese conjunto de grandes empresas, "
            "en lugar de mirar una sola."
        ),
        example=(
            "Imagina que quieres observar un conjunto de grandes empresas de Estados Unidos, "
            "en vez de seguir una sola. El S&P 500 resume el comportamiento de ese conjunto de "
            "500 empresas líderes. Es una referencia para entender el mercado, no una predicción "
            "de lo que pasará después."
        ),
        aliases=(
            "sp500", "sp 500", "s&p500", "s&p 500", "s & p500", "s & p 500",
            "standard & poor's 500", "standard & poor’s 500", "standard & poors 500",
            "standard and poor's 500", "standard and poor’s 500", "standard and poors 500",
        ),
        source=SourceReference(
            source_id="spdj:sp-500", title="S&P 500 — S&P Dow Jones Indices",
            url="https://www.spglobal.com/spdji/en/indices/equity/sp-500/",
            provider="S&P Dow Jones Indices",
        ),
        protected_narration=True,
    ),
    "volatilidad": EducationalConcept(
        definition="La volatilidad describe cuánto han variado los rendimientos de una inversión en un período. Piensa en un recorrido: cuantos más saltos tiene, mayor es su volatilidad histórica. Eso no permite saber qué pasará después.",
        example="Imagina dos recorridos: uno suave y otro con muchos saltos. La volatilidad describe cuánto variaron los retornos históricos, como esos saltos; no asegura qué pasará después.",
    ),
    "beta": EducationalConcept(
        definition="Beta relaciona los movimientos históricos de una inversión con los de un mercado de referencia. Sirve para mirar cómo se han acompañado, aunque esa relación puede cambiar. No anticipa lo que ocurrirá después.",
        example="Piensa en un instrumento y un mercado de referencia. Beta resume cómo se relacionaron sus movimientos históricos. Esa relación puede cambiar; no es una promesa sobre el futuro.",
    ),
    "correlación": EducationalConcept(
        definition="La correlación describe qué tanto se movieron juntas dos inversiones durante un período. Que hayan coincidido no significa que una haya causado los cambios de la otra ni que vayan a seguir igual.",
        example="Imagina dos personas caminando: a veces avanzan juntas y a veces se separan. La correlación describe cuánto coincidieron dos series de retornos; no significa que una haya causado la otra.",
    ),
    "etf": EducationalConcept(
        definition="Un ETF es un fondo que se compra y vende en bolsa mediante participaciones. Puedes imaginarlo como una canasta de inversiones, aunque cada fondo tiene su propia composición, sus costos y sus riesgos.",
        example="Piensa en una canasta de inversiones que se compra y vende en bolsa mediante participaciones. Eso ayuda a imaginar un ETF, aunque su composición, costos y riesgos dependen del fondo.",
    ),
    "retorno": EducationalConcept(
        definition="El retorno expresa cuánto cambió el valor de una inversión durante un período. Al compararlo, conviene revisar si también incluye pagos como dividendos o solo el cambio de precio.",
        example="Si comparas el valor de una inversión al inicio y al final de un período, observas su retorno. La definición usada debe aclarar si incluye distribuciones, como dividendos.",
    ),
    "riesgo": EducationalConcept(
        definition="El riesgo es la posibilidad de que una inversión tenga un resultado distinto al esperado, incluida una pérdida. Hay distintas formas de observarlo; una sola medida no cuenta toda la historia.",
        example="Imagina que el resultado de una decisión puede ser distinto al que esperabas, incluso una pérdida. Esa posibilidad es parte del riesgo, y una sola medida no cuenta toda la historia.",
    ),
}

_EDUCATIONAL_SUBJECT = re.compile(
    r"\b(?:que (?:es|significa)|define\w*|definicion de|explica\w*|"
    r"como (?:funciona|se (?:calcula|mide|interpreta))|para que sirve|"
    r"(?:aprender|entender|comprender|no entiendo|no comprendo)"
    r"(?:\s+(?:mejor|bien|mas|un poco|algo))*)\s+"
    r"(?:(?:la|el|un|una|sobre|acerca de|esto de|indice)\s+)*$"
)


def is_education_subject(prefix: str) -> bool:
    """Whether an entity immediately follows an educational question/request."""
    return bool(_EDUCATIONAL_SUBJECT.search(prefix))


def concept_aliases(topic: str) -> tuple[str, ...]:
    entry = EDUCATION_CATALOGUE[topic]
    return (topic, *entry.aliases)


def match_education_topic(query: str) -> str | None:
    from investiq.language import plain

    text = plain(query)
    candidates = []
    for topic in EDUCATION_CATALOGUE:
        for alias in concept_aliases(topic):
            for match in re.finditer(r"(?<!\w)" + re.escape(plain(alias)) + r"(?!\w)", text):
                # A question's subject outranks incidental context; otherwise
                # preserve the person's mention order, never catalog order.
                candidates.append((not is_education_subject(text[:match.start()]),
                                   match.start(), -len(match.group()), topic))
    return min(candidates)[-1] if candidates else None


def concept_pattern(topic: str) -> str:
    """Normalized aliases for a phrase matcher, without permitting partial words."""
    from investiq.language import plain

    return "(?:" + "|".join(re.escape(plain(alias)) for alias in concept_aliases(topic)) + ")"


def education_sources(topic: str) -> list[SourceReference]:
    from investiq.language import plain

    entry = EDUCATION_CATALOGUE[topic]
    if entry.source is not None:
        return [entry.source.model_copy(deep=True)]
    return [SourceReference(
        source_id=f"glossary:{plain(topic)}", title=f"Glosario educativo: {topic}",
        url=f"local://glossary/{plain(topic)}", provider="Glosario local de InvestiQ",
    )]
