"""Educational topic facade backed by the reviewed, extensible knowledge library."""

from collections.abc import Mapping
from dataclasses import dataclass
import re

from investiq.domain import SourceReference
from investiq.knowledge import get_library


@dataclass(frozen=True)
class EducationalConcept:
    definition: str
    example: str
    aliases: tuple[str, ...] = ()
    source: SourceReference | None = None
    protected_narration: bool = True


class _Concepts(Mapping):
    """Public catalogue view; loading is deferred until knowledge is requested."""

    def __getitem__(self, topic: str) -> EducationalConcept:
        document = get_library().get_by_topic(topic)
        if document is None:
            raise KeyError(topic)
        return EducationalConcept(
            definition=document.summary, example=document.example,
            aliases=document.aliases, source=document.sources[0].to_reference(),
        )

    def __iter__(self):
        return (document.title for document in get_library().documents)

    def __len__(self):
        return len(get_library().documents)


class DefinitionView(Mapping):
    """Read-only definition API shared by tools and the opt-in live verifier."""

    def __getitem__(self, topic: str) -> str:
        return EDUCATION_CATALOGUE[topic].definition

    def __iter__(self):
        return iter(EDUCATION_CATALOGUE)

    def __len__(self):
        return len(EDUCATION_CATALOGUE)


EDUCATION_CATALOGUE = _Concepts()

_EDUCATIONAL_SUBJECT = re.compile(
    r"\b(?:que (?:es|son|significa)|quien es|define\w*|definicion de|explica\w*|"
    r"como (?:funciona\w*|se (?:calcula|mide|interpreta))|para que sirve|"
    r"(?:aprender|entender|comprender|no entiendo|no comprendo)"
    r"(?:\s+(?:mejor|bien|mas|un poco|algo))*)\s+"
    r"(?:(?:la|el|los|las|un|una|unos|unas|sobre|acerca de|esto de|indice)\s+)*$"
)


def is_education_subject(prefix: str) -> bool:
    return bool(_EDUCATIONAL_SUBJECT.search(prefix))


def concept_aliases(topic: str) -> tuple[str, ...]:
    return (topic, *EDUCATION_CATALOGUE[topic].aliases)


def match_education_topic(query: str) -> str | None:
    return get_library().resolve_topic(query)


def concept_pattern(topic: str) -> str:
    from investiq.language import plain

    return "(?:" + "|".join(re.escape(plain(alias)) for alias in concept_aliases(topic)) + ")"


def education_sources(topic: str) -> list[SourceReference]:
    document = get_library().get_by_topic(topic)
    return [source.to_reference() for source in document.sources] if document else []
