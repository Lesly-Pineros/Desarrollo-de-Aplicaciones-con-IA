"""Offline lexical retrieval over reviewed, versioned educational documents.

TF-IDF is used for text similarity. No neural embedding model or vector service
is downloaded, and the user's financial database is never opened here.
"""

from collections import Counter
from functools import lru_cache
from importlib.resources import files
import json
import os
from pathlib import Path
import re
import unicodedata

import numpy as np
from pydantic import ValidationError
from sklearn.feature_extraction.text import TfidfVectorizer

from investiq.knowledge.models import KnowledgeDocument, KnowledgeFile, KnowledgePassage
from investiq.learning import lesson_request

_STOPWORDS = frozenset("a al algo algunas algunos ante antes aquel aquella aquellos aqui asi aun aunque bajo bien cada casi como con contra cual cuales cuando cuanto de del desde donde dos el ella ellas ellos en entre era es esa esas ese esos esta estaban estamos estan estar este esto estos fue fueron ha habia han hasta hay la las le les lo los mas me mi mis mucho muy nada ni no nos nosotros o otra otras otro otros para pero poco por porque que quien quienes se sea ser si sin sobre solo su sus te tiene tienen todo todos tu tus un una unas uno unos usted ustedes y ya yo favor puedes podria podrias quiero quisiera saber dime explicame explicar explica entender aprender comprender pregunta significado significa son sirve funcionan funciona existe existen muestra ejemplo sencillo sencilla ayuda gustaria".split())
_SUBJECT = re.compile(
    r"\b(?:que (?:es|son|significa)|define\w*|definicion de|explica\w*|"
    r"como (?:funciona\w*|se (?:calcula|mide|interpreta))|para que sirve|"
    r"(?:aprender|entender|comprender|no entiendo|no comprendo)"
    r"(?:\s+(?:mejor|bien|mas|un poco|algo))*)\s+"
    r"(?:(?:la|el|los|las|un|una|unos|unas|sobre|acerca de|esto de|indice)\s+)*$"
)
_BROKER_CONTEXT_FOLLOWUP = re.compile(
    r"^(?:y\s+)?(?:que (?:puedo|podria) (?:usar|utilizar) en [a-z]+(?: [a-z]+){0,3}|"
    r"cuanto (?:cobra|cobran|cuesta|cuestan)(?: (?:hoy|ahora))?|"
    r"(?:esta|estan|es|son) (?:disponibles?|autorizados?) en [a-z]+(?: [a-z]+){0,3})$"
)
_QUESTION_FOCUS = re.compile(
    r"\b(?:que (?:es|son|significa)|define\w*|definicion de|explica\w*|"
    r"como (?:funciona\w*|se (?:calcula|mide|interpreta))|para que sirve|"
    r"(?:aprender|entender|comprender|no entiendo|no comprendo)"
    r"(?:\s+(?:mejor|bien|mas|un poco|algo))*"
    r"(?:\s+(?:sobre|acerca de))?|(?:hablame|habla) (?:de|sobre)|"
    r"en que se diferencian|(?:cual es la |que )?diferencia(?:s)?(?: hay)? entre)\s+(.+)$"
)
_INVESTMENT_FOCUS = re.compile(
    r"\b(?:invierto|invertir|invertimos|invertido)\s+en\s+(.+)$"
)
_DESCRIPTIVE_QUALIFIERS = frozenset("alta baja media alto bajo medio altas bajas altos bajos mayor menor historica historico historicas historicos".split())


class KnowledgeValidationError(ValueError):
    """The local corpus cannot be used safely or reproducibly."""


def _plain(text: str) -> str:
    text = "".join(char for char in unicodedata.normalize("NFD", text.casefold())
                   if not unicodedata.combining(char))
    return " ".join(text.split()).strip(" ¿?¡!.,")


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", _plain(text))
            if token not in _STOPWORDS and (len(token) > 2 or token.isdigit())}


def _requested_focus(text: str) -> set[str] | None:
    """Separate an unfamiliar requested subject from familiar incidental context.

    For example, ETF in 'qué es staking en un ETF' does not establish evidence
    about staking. This check uses the reviewed document's vocabulary instead
    of permitting a keyword anywhere in the question to license an answer.
    """
    investment = _INVESTMENT_FOCUS.search(text)
    if investment is not None and _tokens(text[:investment.start()]):
        # In 'cómo pago impuestos por invertir en bolsa', investing is the
        # context of a tax question rather than the subject of the request.
        investment = None
    question = _QUESTION_FOCUS.search(text)
    match = investment or question
    if match is None:
        return None
    subject = re.split(r"\b(?:en|aplicad[oa]s?|frente|respecto|para|que|sobre|como)\b",
                       match.group(1), maxsplit=1)[0]
    return (_tokens(subject) - _DESCRIPTIVE_QUALIFIERS) or None


def _chunks(text: str, maximum: int = 700) -> tuple[str, ...]:
    # Split only on natural text boundaries, with a hard cap for malformed prose.
    sentences = re.split(r"(?<=[.!?])\s+|\n\s*\n", text.strip())
    chunks, current = [], ""
    for sentence in sentences:
        while len(sentence) > maximum:
            boundary = sentence.rfind(" ", 0, maximum)
            boundary = boundary if boundary > maximum // 2 else maximum
            if current:
                chunks.append(current)
                current = ""
            chunks.append(sentence[:boundary].strip())
            sentence = sentence[boundary:].strip()
        if current and len(current) + len(sentence) + 1 > maximum:
            chunks.append(current)
            current = sentence
        else:
            current = (current + " " + sentence).strip()
    if current:
        chunks.append(current)
    return tuple(chunks)


class KnowledgeLibrary:
    def __init__(self, documents):
        self.documents = tuple(sorted((KnowledgeDocument.model_validate(doc) for doc in documents),
                                      key=lambda doc: doc.id))
        if not self.documents:
            raise KnowledgeValidationError("La biblioteca no contiene documentos.")
        ids = [doc.id for doc in self.documents]
        titles = [_plain(doc.title) for doc in self.documents]
        if len(set(ids)) != len(ids) or len(set(titles)) != len(titles):
            raise KnowledgeValidationError("La biblioteca contiene IDs o títulos duplicados.")
        self._by_id = {doc.id: doc for doc in self.documents}
        self._exact = {}
        sources = {}
        for doc in self.documents:
            if any(related not in self._by_id for related in doc.related_ids):
                raise KnowledgeValidationError(f"{doc.id}: referencia a un documento relacionado inexistente.")
            for source in doc.sources:
                previous = sources.setdefault(source.source_id, source)
                if previous != source:
                    raise KnowledgeValidationError("Un source_id tiene metadatos diferentes entre documentos.")
            for alias in (doc.id, doc.title, *doc.aliases):
                key = _plain(alias)
                if key in self._exact and (self._exact[key] is None or self._exact[key].id != doc.id):
                    # An ambiguous alias can be used for retrieval but not as a
                    # canonical persisted identity. Titles and IDs stay unique.
                    self._exact[key] = None
                elif key not in self._exact:
                    self._exact[key] = doc
        texts = [self._index_text(doc) for doc in self.documents]
        self._words = TfidfVectorizer(strip_accents="unicode", lowercase=True,
                                     ngram_range=(1, 2), sublinear_tf=True,
                                     stop_words=sorted(_STOPWORDS))
        self._characters = TfidfVectorizer(strip_accents="unicode", lowercase=True,
                                          analyzer="char_wb", ngram_range=(3, 5),
                                          sublinear_tf=True)
        self._word_matrix = self._words.fit_transform(texts)
        self._char_matrix = self._characters.fit_transform(texts)
        self._document_tokens = tuple(_tokens(text) for text in texts)

    @staticmethod
    def _index_text(doc: KnowledgeDocument) -> str:
        terms = " ".join((doc.title, *doc.aliases, *doc.questions))
        return f"{terms} {terms} {doc.summary} {doc.explanation} {doc.example} {doc.cautions}"

    @classmethod
    def from_path(cls, directory: str | Path):
        location = Path(directory)
        paths = sorted(location.glob("*.json")) if location.is_dir() else [location]
        return cls._from_files(paths)

    @classmethod
    def builtin(cls):
        resource = files("investiq.knowledge").joinpath("data")
        try:
            paths = sorted((item for item in resource.iterdir() if item.name.endswith(".json")),
                           key=lambda item: item.name)
        except OSError as error:
            raise KnowledgeValidationError("No encontré los documentos de la biblioteca instalada.") from error
        return cls._from_files(paths)

    @classmethod
    def _from_files(cls, paths):
        documents = []
        for filename in paths:
            try:
                if len(filename.read_bytes()) > 4 * 1024 * 1024:
                    raise KnowledgeValidationError("Un archivo de biblioteca supera el límite de 4 MiB.")
                payload = KnowledgeFile.model_validate_json(filename.read_text(encoding="utf-8"))
                documents.extend(payload.documents)
            except (OSError, UnicodeError, ValidationError) as error:
                raise KnowledgeValidationError(f"No pude validar la biblioteca: {filename.name}.") from error
        return cls(documents)

    def get_document(self, document_id: str) -> KnowledgeDocument | None:
        return self._by_id.get(document_id)

    def _mentions(self, query: str):
        text = _plain(query)
        candidates = []
        for doc in self.documents:
            for alias in (doc.id, doc.title, *doc.aliases):
                for match in re.finditer(r"(?<!\w)" + re.escape(_plain(alias)) + r"(?!\w)", text):
                    if _plain(alias) == "meta" and re.search(r"\b(?:mi|tu|su|una|la|esta)\s+$", text[:match.start()]):
                        continue
                    candidates.append((not bool(_SUBJECT.search(text[:match.start()])),
                                       match.start(), -len(match.group()), doc.id))
        candidates = sorted(set(candidates))
        # A specific reviewed phrase owns its span: 'ETF apalancado' should
        # not also boost the generic ETF document at the very same position.
        return [candidate for candidate in candidates if not any(
            other[1] == candidate[1] and other[2] < candidate[2]
            for other in candidates
        )]

    def resolve_topic(self, text: str) -> str | None:
        key = _plain(text)
        exact = self._exact.get(key)
        if exact is not None:
            return exact.title
        if key in self._exact:
            return None
        mentions = self._mentions(text)
        if (len(mentions) > 1 and mentions[0][:3] == mentions[1][:3]
                and mentions[0][-1] != mentions[1][-1]):
            return None
        return self._by_id[mentions[0][-1]].title if mentions else None

    def get_by_topic(self, text: str) -> KnowledgeDocument | None:
        if not isinstance(text, str) or not text.strip():
            return None
        exact = self._exact.get(_plain(text))
        if exact is not None:
            return exact
        title = self.resolve_topic(text)
        return self._exact.get(_plain(title)) if title is not None else None

    def _scores(self, query: str):
        word = (self._word_matrix @ self._words.transform([query]).T).toarray().ravel()
        chars = (self._char_matrix @ self._characters.transform([query]).T).toarray().ravel()
        scores = .75 * word + .25 * chars
        tokens = _tokens(query)
        if not tokens:
            return np.zeros(len(self.documents))
        # Character similarity alone must never manufacture topical evidence.
        for index, document_tokens in enumerate(self._document_tokens):
            overlap = tokens & document_tokens
            if not overlap:
                scores[index] = 0
        return scores

    def _best_chunk(self, query: str, text: str):
        chunks = _chunks(text)
        if len(chunks) == 1:
            return 0, chunks[0]
        words = (self._words.transform(chunks) @ self._words.transform([query]).T).toarray().ravel()
        chars = (self._characters.transform(chunks) @ self._characters.transform([query]).T).toarray().ravel()
        offset = int(np.argmax(.75 * words + .25 * chars))
        return offset, chunks[offset]

    def search(self, query: str, *, topic: str | None = None, limit: int = 4,
               include_example: bool = False) -> list[KnowledgePassage]:
        if not isinstance(query, str) or not query.strip() or limit < 1:
            return []
        limit = min(limit, 8)
        text = _plain(query[:2000])
        request = lesson_request(text)
        context = (self._exact.get(_plain(topic)) if request else self.get_by_topic(topic)) if topic else None
        if request is not None and context is None:
            # Generic words such as 'importa' do not establish a new subject.
            return []
        mentions = self._mentions(text)
        scores = self._scores(text)
        by_index = {doc.id: index for index, doc in enumerate(self.documents)}
        for is_context, position, negative_length, document_id in mentions:
            bonus = 1.0 if not is_context else .4 / (1 + position / 200)
            scores[by_index[document_id]] += bonus
        focus = _requested_focus(text)
        if focus and mentions and not mentions[0][0]:
            _, start, negative_length, _ = mentions[0]
            end = start - negative_length
            # A known subject followed by context stays the subject: 'la
            # volatilidad del SP500'. Unknown leading nouns never get this
            # exception ('staking en un ETF' still has no supported subject).
            if re.match(r"\s+(?:de|del|en|frente|respecto|para|que|sobre|como|y)\b", text[end:]):
                focus = _tokens(text[start:end])
        if focus and mentions:
            known_terms = set().union(*(_tokens(text[start:start - negative_length])
                                       for _, start, negative_length, _ in mentions))
            # Known concepts can collectively answer a comparison. Unknown
            # qualifiers stay subject to evidence coverage instead of letting
            # one familiar noun license an unrelated explanation.
            if focus <= known_terms:
                focus = None
        if focus:
            for index, document_tokens in enumerate(self._document_tokens):
                if len(focus & document_tokens) / len(focus) < .67:
                    scores[index] = 0
        elif not mentions:
            # Weak similarity on one generic noun ('gestión') does not cover a
            # new multiword subject ('gestión cuántica extraterrestre').
            query_tokens = _tokens(text)
            if query_tokens:
                for index, document_tokens in enumerate(self._document_tokens):
                    if len(query_tokens & document_tokens) / len(query_tokens) < .5:
                        scores[index] = 0
        followup = bool(request or (context is not None and context.category == "intermediarios"
                            and _BROKER_CONTEXT_FOLLOWUP.fullmatch(text)))
        if context is not None and followup:
            scores = np.zeros(len(self.documents))
            scores[by_index[context.id]] = 1
        ranked = sorted(zip(self.documents, scores), key=lambda item: (-item[1], item[0].id))
        if ranked[0][1] < .12:
            return []
        best_score = ranked[0][1]
        # Only closely related secondary documents enter generation context.
        selected = [(doc, float(score)) for doc, score in ranked
                    if score >= max(.12, best_score * .45)][:max(1, limit // 2)]
        passages = []
        wants_example = include_example or request in {"example", "simplify"} or bool(re.search(r"ejemplo|sencill|simple|facil|no entendi|no entiendo", text))
        wants_depth = request == "detail" or bool(re.search(r"mas detalle|profundiza|mas a fondo|mas tecnico", text))
        wants_caution = request == "cautions" or bool(re.search(r"riesgo|peligro|fraude|desventaja|perder|precaucion", text))
        for index, (doc, score) in enumerate(selected):
            # The principal topic carries its caveats into model context too;
            # fallback access to the full document is not enough grounding for
            # a generated explanation about brokers or leveraged products.
            sections = (["summary", "example" if wants_example else "explanation", "cautions"]
                        if index == 0 else ["summary"])
            if wants_caution:
                sections = ["summary", "cautions", "explanation"] if index == 0 else ["summary"]
            elif wants_depth and index == 0:
                sections = ["summary", "explanation", "example", "cautions"]
            for section in sections:
                offset, chunk = self._best_chunk(text, getattr(doc, section))
                passages.append(KnowledgePassage(
                    passage_id=f"{doc.id}:{section}:{offset}", document_id=doc.id,
                    title=doc.title, section=section, text=chunk, score=score, sources=doc.sources,
                ))
        bounded, characters = [], 0
        for passage in passages[:limit]:
            if characters + len(passage.text) > 4800:
                break
            bounded.append(passage)
            characters += len(passage.text)
        return bounded

    def stats(self) -> dict:
        return {"documents": len(self.documents),
                "categories": dict(sorted(Counter(doc.category for doc in self.documents).items())),
                "sources": len({source.source_id for doc in self.documents for source in doc.sources})}


@lru_cache(maxsize=1)
def get_library() -> KnowledgeLibrary:
    location = os.environ.get("INVESTIQ_KNOWLEDGE_PATH", "").strip()
    return KnowledgeLibrary.from_path(location) if location else KnowledgeLibrary.builtin()
