"""Meaningful local search checks: no model, network or financial database."""

import json

import pytest
from pydantic import ValidationError

from investiq.knowledge import KnowledgeDocument, KnowledgeLibrary, KnowledgeValidationError, get_library
from investiq.knowledge.__main__ import main
from investiq.knowledge.models import KnowledgeSource


def document(identifier, title, *, aliases=(), questions=(), summary=None,
             explanation=None, related_ids=()):
    return {
        "id": identifier, "title": title, "category": "prueba",
        "aliases": list(aliases), "questions": list(questions),
        "summary": summary or f"Una explicación de {title} con sus características educativas.",
        "explanation": explanation or f"El tema {title} se explica a partir de una fuente de prueba revisada.",
        "example": f"Un ejemplo didáctico para entender {title} sin cotizaciones.",
        "cautions": "La información histórica no garantiza resultados futuros.",
        "related_ids": list(related_ids),
        "sources": [{"source_id": "test:education", "title": "Fuente de prueba",
                     "url": "https://example.org/education", "provider": "Fuente de prueba",
                     "reviewed_on": "2026-11-04"}],
    }


@pytest.fixture
def library():
    documents = [
        document("accion", "acción", aliases=("acciones",),
                 questions=("¿Qué significa tener un pedacito de una empresa?",),
                 summary="Una acción representa participación en una empresa.",
                 explanation="Tener acciones significa poseer una parte de la compañía."),
        document("etf", "etf", aliases=("fondo cotizado",),
                 summary="Un ETF es un fondo que se negocia en bolsa.",
                 explanation="Un fondo cotizado reúne una cartera de inversiones y tiene costes y riesgos."),
        document("sp500", "S&P 500", aliases=("sp500", "sp 500", "s&p500"),
                 summary="El S&P 500 sigue el conjunto de empresas que componen el índice."),
        document("volatilidad", "volatilidad",
                 summary="La volatilidad describe la variación histórica de los rendimientos."),
        document("beta", "beta", summary="Beta relaciona movimientos con un mercado de referencia."),
        document("dividendos", "dividendos", aliases=("dividendo",),
                 summary="Los dividendos son distribuciones de una empresa a sus accionistas."),
    ]
    return KnowledgeLibrary(documents)


def test_retrieval_answers_a_paraphrase_without_the_concept_name(library):
    passages = library.search("¿Qué significa tener un pedacito de una empresa?")
    assert passages and passages[0].document_id == "accion"
    assert "participación" in passages[0].text
    assert passages[0].sources[0].to_reference().url == "https://example.org/education"
    assert passages[0].sources[0].to_reference().published_at is None


@pytest.mark.parametrize("query", ["Qué es Kubernetes", "cómo cocinar un pastel", "sp5000", "xsp500", "",
                                 "qué es staking en un ETF",
                                 "qué es física cuántica aplicada a acciones",
                                 "cómo invierto en NFTs", "qué es un ETF cuántico",
                                 "quiero entender staking en un ETF",
                                 "háblame de física cuántica aplicada a acciones"])
def test_unknown_subjects_do_not_receive_a_confident_guess(library, query):
    assert library.search(query) == []
    assert library.search(query, topic="etf") == []


@pytest.mark.parametrize("query,expected", [
    ("Hablando del S&P500, ¿qué es beta?", "beta"),
    ("qué es la volatilidad del sp500", "volatilidad"),
    ("Hablando de beta, ¿qué es el sp500?", "S&P 500"),
    ("¿Qué es volatilidad y cómo se relaciona con el movimiento del precio?", "volatilidad"),
    ("qué es un ETF que sigue el SP500", "etf"),
    ("Qué es un ETF como SPDR S&P 500 ETF", "etf"),
    ("Me gustaría entender la volatilidad alta", "volatilidad"),
    ("No entiendo la volatilidad baja", "volatilidad"),
    ("Quiero entender esto de la volatilidad alta", "volatilidad"),
    ("¿Qué es el SP 500?", "S&P 500"),
    ("dividendo", "dividendos"),
])
def test_canonical_subject_and_search_are_not_catalog_order_dependent(library, query, expected):
    reversed_library = KnowledgeLibrary(reversed(library.documents))
    assert library.resolve_topic(query) == expected
    assert reversed_library.resolve_topic(query) == expected
    assert library.search(query)[0].title == expected
    assert reversed_library.search(query)[0].title == expected


def test_a_multi_concept_question_retrieves_evidence_for_both_topics(library):
    results = library.search("¿Qué diferencia hay entre una acción y un ETF?")
    assert {passage.document_id for passage in results} == {"accion", "etf"}
    assert len(results) <= 4


def test_short_followup_uses_topic_but_a_new_question_wins(library):
    passages = library.search("un ejemplo", topic="etf")
    assert {passage.document_id for passage in passages} == {"etf"}
    assert {passage.section for passage in passages} >= {"example", "cautions"}
    new_topic = library.search("¿Qué es un dividendo?", topic="etf")
    assert new_topic[0].document_id == "dividendos"


@pytest.mark.parametrize("query", ["¿Y sus riesgos?", "¿Y cuáles son sus riesgos?",
                                 "¿Qué riesgos tiene?", "¿Y sus costes?", "¿Y cómo funciona eso?"])
def test_deictic_followup_keeps_a_specific_subject_instead_of_generic_risk(library, query):
    passages = library.search(query, topic="etf")
    assert {passage.document_id for passage in passages} == {"etf"}
    assert any(passage.section == "cautions" for passage in passages)


@pytest.mark.parametrize("query", ["¿Qué puedo usar en Colombia?", "¿Y cuánto cobra hoy?"])
def test_broker_followup_retrieves_general_evidence_without_inventing_current_availability(query):
    broker = document("broker", "bróker de prueba", aliases=("intermediario",))
    broker["category"] = "intermediarios"
    broker["cautions"] = "Autorización, disponibilidad y costes requieren comprobación actual por país."
    library = KnowledgeLibrary([broker])
    passages = library.search(query, topic="bróker de prueba")
    assert {passage.document_id for passage in passages} == {"broker"}
    assert any("comprobación actual" in passage.text for passage in passages)
    assert all("Colombia" not in passage.text for passage in passages)


def test_passages_are_bounded_and_match_the_relevant_chunk_of_a_long_document():
    explanation = ("El documento presenta contexto general para aprender con calma. " * 35
                   + "Una orden limitada establece el precio límite que acepta la persona. "
                   + "Es una condición de ejecución y no promete que la operación se realice.")
    item = document("ordenes", "órdenes", aliases=("orden",), explanation=explanation)
    result = KnowledgeLibrary([item]).search("¿Cómo establece una orden limitada el precio límite?", limit=8)
    assert any("precio límite" in passage.text for passage in result)
    assert all(len(passage.text) <= 700 for passage in result)
    assert sum(len(passage.text) for passage in result) <= 4800
    assert len({passage.passage_id for passage in result}) == len(result)


def test_new_json_document_can_be_used_without_a_code_change(tmp_path, monkeypatch):
    payload = {"schema_version": 1, "documents": [document("custodia", "custodia", aliases=("depositario",))]}
    (tmp_path / "new.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("INVESTIQ_KNOWLEDGE_PATH", str(tmp_path))
    get_library.cache_clear()
    try:
        library = get_library()
        assert library.resolve_topic("¿Qué es un depositario?") == "custodia"
        assert library.search("Qué es custodia")[0].document_id == "custodia"
        assert library.get_document("custodia").title == "custodia"
    finally:
        get_library.cache_clear()


def test_custom_corpus_and_cli_are_validated_before_search(tmp_path, monkeypatch, capsys):
    (tmp_path / "invalid.json").write_text('{"schema_version":1,"documents":[]}', encoding="utf-8")
    monkeypatch.setenv("INVESTIQ_KNOWLEDGE_PATH", str(tmp_path))
    get_library.cache_clear()
    try:
        assert main(["validate"]) == 1
        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "invalid"
        assert "invalid.json" in output["error"]
    finally:
        get_library.cache_clear()


def test_cli_inspects_a_valid_corpus_without_contacting_a_provider(tmp_path, monkeypatch, capsys):
    (tmp_path / "valid.json").write_text(json.dumps({"schema_version": 1, "documents": [
        document("accion", "acción", aliases=("acciones",))]}), encoding="utf-8")
    monkeypatch.setenv("INVESTIQ_KNOWLEDGE_PATH", str(tmp_path))
    get_library.cache_clear()
    try:
        assert main(["stats"]) == 0
        assert json.loads(capsys.readouterr().out)["documents"] == 1
        assert main(["search", "qué es una acción"]) == 0
        assert json.loads(capsys.readouterr().out)["passages"][0]["title"] == "acción"
    finally:
        get_library.cache_clear()


@pytest.mark.parametrize("url", ["http://example.org/education", "javascript:alert(1)",
                                 "https://user:password@example.org/education"])
def test_sources_require_https_without_embedded_credentials(url):
    item = document("test", "test")
    item["sources"][0]["url"] = url
    with pytest.raises(ValidationError):
        KnowledgeDocument.model_validate(item)


def test_duplicate_ids_and_unresolved_relationships_fail_validation():
    with pytest.raises(KnowledgeValidationError):
        KnowledgeLibrary([document("test", "tema"), document("test", "otro tema")])
    with pytest.raises(KnowledgeValidationError):
        KnowledgeLibrary([document("test", "tema", related_ids=("missing",))])


def test_same_source_id_cannot_refer_to_different_evidence():
    first, second = document("first", "tema"), document("second", "otro tema")
    second["sources"][0]["url"] = "https://example.org/different"
    with pytest.raises(KnowledgeValidationError):
        KnowledgeLibrary([first, second])


def test_ambiguous_alias_does_not_become_a_canonical_memory_identifier():
    library = KnowledgeLibrary([document("first", "tema primero", aliases=("termino",)),
                                document("second", "tema segundo", aliases=("termino",)),
                                document("third", "tema tercero", aliases=("termino",))])
    assert library.resolve_topic("termino") is None
    assert library.resolve_topic("qué es termino") is None


def test_source_review_date_does_not_become_a_publication_date():
    source = KnowledgeSource.model_validate(document("test", "tema")["sources"][0])
    assert source.reviewed_on.isoformat() == "2026-11-04"
    assert source.to_reference().published_at is None


def test_document_identity_can_resolve_a_subject_with_a_familiar_incidental_topic():
    library = KnowledgeLibrary([
        document("impuestos", "impuestos de inversión", aliases=("tributación",),
                 summary="Los dividendos y operaciones pueden tener consecuencias tributarias."),
        document("bolsa", "bolsa de valores", aliases=("bolsa",)),
    ])
    query = "¿Cómo pago impuestos por invertir en bolsa?"
    assert library.resolve_topic(query) == "impuestos de inversión"
    assert library.search(query)[0].document_id == "impuestos"


def test_one_shared_generic_word_does_not_establish_an_unknown_comparison():
    library = KnowledgeLibrary([document("gestion", "gestión financiera",
                                        summary="La gestión financiera organiza información sobre inversiones.")])
    assert library.search("¿En qué se diferencian gestión cuántica y gestión extraterrestre?") == []
