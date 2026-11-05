"""The shipped professor library covers the product's learning promises."""

import pytest

from investiq.knowledge import KnowledgeLibrary


@pytest.fixture(scope="module")
def library():
    # Inspect the shipped library even when a local installation selects an
    # alternative reviewed collection through INVESTIQ_KNOWLEDGE_PATH.
    return KnowledgeLibrary.builtin()


def test_library_covers_learning_categories_and_remains_substantive(library):
    assert len(library.documents) >= 50
    assert {document.category for document in library.documents} >= {
        "fundamentos", "fondos", "indices", "mercados", "riesgos",
        "intermediarios", "operativa", "analisis", "proteccion",
        "planificacion", "costes", "instrumentos",
    }
    for document in library.documents:
        assert document.questions and document.sources
        assert all(len(getattr(document, section)) >= 40 for section in (
            "summary", "explanation", "example", "cautions",
        ))


@pytest.mark.parametrize("topic", [
    "S&P 500", "volatilidad", "beta", "correlación", "etf", "retorno", "riesgo",
])
def test_existing_learning_topics_keep_their_canonical_identity(library, topic):
    assert library.get_by_topic(topic).title == topic


@pytest.mark.parametrize("symbol", [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "JPM", "XOM",
    "JNJ", "WMT", "COST", "AVGO", "BRK-B", "UNH", "SPY", "QQQ", "IWM", "XLK", "XLF",
])
def test_catalogue_instruments_have_independent_issuer_profiles(library, symbol):
    document = library.get_document(f"instrumento-{symbol.lower()}")
    assert document is not None and document.category == "instrumentos"
    assert document.sources[0].source_id == f"issuer:{symbol.lower()}"
    assert library.get_by_topic(symbol).id == document.id


def test_index_fund_and_exchange_are_not_equated(library):
    assert library.get_by_topic("S&P 500").id == "sp500"
    assert library.get_by_topic("SPY").id == "instrumento-spy"
    assert library.get_by_topic("Nasdaq").id == "nasdaq-bolsa"
    assert library.get_by_topic("Nasdaq-100").id == "nasdaq100"
    assert library.get_by_topic("QQQ").id == "instrumento-qqq"


def test_broker_examples_are_documented_and_qualified(library):
    document = library.get_document("brokers")
    providers = {source.provider for source in document.sources}
    assert providers >= {"Interactive Brokers", "Charles Schwab", "Fidelity"}
    caution = document.cautions.casefold()
    assert "país" in caution
    assert "autorización" in caution and "tarifas" in caution and "actuales" in caution


def test_broad_questions_have_reviewed_sections_without_market_data(library):
    expected = {
        "accion", "dividendos", "ipo", "etf", "gestion-activa-pasiva",
        "etf-apalancado-inverso", "sp500", "brokers", "verificar-broker",
        "orden-mercado", "orden-limite", "orden-stop", "spread", "margen",
        "impuestos", "per", "eps", "estados-financieros", "fraude", "ponzi",
        "diversificacion", "empezar-invertir",
    }
    assert expected <= {document.id for document in library.documents}
    for document in library.documents:
        for source in document.sources:
            assert source.url.startswith("https://")
            assert source.provider and source.reviewed_on.isoformat() == "2026-11-04"

