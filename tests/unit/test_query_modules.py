"""Behavioral boundaries for deterministic execution and query coordination."""

from datetime import datetime, timezone

import pytest
from sqlmodel import Session, select

from investiq.data.database import create_db, make_engine
from investiq.data.models import QueryLog, ResponseTrace
from investiq.domain import FilingItem, NewsCollection, NewsItem, QuoteResult, RouterDecision, SourceReference
from investiq.handlers import execute_query
from investiq.orchestration import answer_query
from investiq.routing import fallback_route, route_query
from investiq.settings import Settings
from investiq.tools import source_references
from investiq.tutor import TutorEvidence, TutorNarration, TutorParagraph


@pytest.fixture
def local_query_session(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'query-modules.db'}"))
    settings = Settings(_env_file=None, nvidia_api_key=None, twelve_data_api_key=None,
                        marketaux_api_key=None, sec_user_agent="")
    with Session(engine) as session:
        yield session, settings
    engine.dispose()


@pytest.mark.parametrize("decision,expected_tool", [
    (RouterDecision(intent="education", education_topic="beta"), None),
    (RouterDecision(intent="explanation", symbol="AAPL"), "market_quote"),
    (RouterDecision(intent="recommend_volatility", volatility_target="baja"), "volatility_bucket"),
    (RouterDecision(intent="recommend_similar", reference_symbol="NVDA"), "similar_instruments"),
    (RouterDecision(intent="compare", comparison_symbols=["AAPL", "MSFT"]), "compare_instruments"),
    (RouterDecision(intent="unknown"), None),
])
def test_handlers_return_results_without_recording_queries(local_query_session, monkeypatch, decision, expected_tool):
    session, settings = local_query_session
    source = SourceReference(source_id="fixture", title="Local fixture", url="local://fixture", provider="fixture")
    monkeypatch.setattr("investiq.handlers.market_quote_tool", lambda *args: QuoteResult(
        symbol="AAPL", price=100, change_pct=2.1, provider="fixture", source=source,
        as_of=datetime(2026, 11, 4, tzinfo=timezone.utc),
    ))
    monkeypatch.setattr("investiq.handlers.news_tool", lambda *args: NewsCollection(articles=[]))
    monkeypatch.setattr("investiq.handlers.sec_docs_tool", lambda *args: ([], "Sin filings en fixture."))
    monkeypatch.setattr("investiq.handlers.local_model_source", lambda *args: source)
    monkeypatch.setattr("investiq.handlers.volatility_bucket", lambda *args: [{"symbol": "AAPL"}])
    monkeypatch.setattr("investiq.handlers.similar_instruments", lambda *args: [{"symbol": "AAPL", "cluster_label": 1}])
    monkeypatch.setattr("investiq.handlers.compare_instruments", lambda *args, **kwargs: [
        {"symbol": "AAPL", "score": 80}, {"symbol": "MSFT", "score": 60},
    ])

    result = execute_query(session, "local", "Consulta de prueba", settings, decision)

    assert result.answer
    assert result.status == ("degraded" if decision.intent == "unknown" else "ok")
    if expected_tool:
        assert expected_tool in result.tools_used
        assert result.sources == [source]
    assert session.exec(select(QueryLog)).all() == []
    assert session.exec(select(ResponseTrace)).all() == []


def test_orchestration_records_one_trace_per_response(local_query_session):
    session, settings = local_query_session

    first = answer_query(session, "local", "¿Qué es beta?", settings)
    second = answer_query(session, "local", "¿Qué es volatilidad?", settings)

    logs = session.exec(select(QueryLog).order_by(QueryLog.id)).all()
    traces = session.exec(select(ResponseTrace).order_by(ResponseTrace.query_log_id)).all()
    assert len(logs) == len(traces) == 2
    assert [trace.query_log_id for trace in traces] == [log.id for log in logs]
    assert [log.intent for log in logs] == [first.intent, second.intent]


def test_auto_client_false_never_constructs_a_configured_client(local_query_session, monkeypatch):
    session, settings = local_query_session
    settings.nvidia_api_key = "configured-only-for-constructor-test"

    def unexpected_construction(*args, **kwargs):
        pytest.fail("auto_client=False must not construct an LLM client")

    monkeypatch.setattr("investiq.orchestration.ChatNVIDIAClient", unexpected_construction)

    response = answer_query(session, "local", "¿Qué es beta?", settings, auto_client=False)

    assert response.intent == "education"
    assert response.diagnostics.routing == "rules"
    assert response.diagnostics.narration == "unavailable"


def test_auto_client_false_still_uses_an_injected_client(local_query_session, monkeypatch):
    session, settings = local_query_session
    settings.nvidia_api_key = "configured-only-for-constructor-test"
    calls = []

    class Client:
        def classify(self, query):
            calls.append("classify")
            return RouterDecision(intent="education", education_topic="beta")

        def teach(self, query, passages, context):
            calls.append("teach")
            return TutorNarration(paragraphs=[TutorParagraph(text=passages[0]["text"], evidence=[
                TutorEvidence(passage_id=passages[0]["passage_id"], quote=passages[0]["text"])])])

    def unexpected_construction(*args, **kwargs):
        pytest.fail("An injected client must be reused")

    monkeypatch.setattr("investiq.orchestration.ChatNVIDIAClient", unexpected_construction)

    response = answer_query(session, "local", "¿Qué es beta?", settings,
                            client=Client(), auto_client=False)

    assert calls == ["classify", "teach"]
    assert response.diagnostics.routing == "llm"
    assert response.diagnostics.narration == "used"
    assert response.tools_used == ["knowledge_search"]
    assert response.sources and "Beta" in response.answer


@pytest.mark.parametrize("symbol", [None, "OUTSIDE_COVERAGE"])
def test_coordinator_resolves_explanation_symbols_before_executing_tools(local_query_session, monkeypatch, symbol):
    session, settings = local_query_session
    received = []

    def quote(session, symbol, settings):
        received.append(symbol)
        return QuoteResult(symbol=symbol, error="No quote in fixture.")

    monkeypatch.setattr("investiq.handlers.market_quote_tool", quote)
    monkeypatch.setattr("investiq.handlers.news_tool", lambda *args: NewsCollection(articles=[]))
    monkeypatch.setattr("investiq.handlers.sec_docs_tool", lambda *args: ([], "No filings in fixture."))

    response = answer_query(session, "local", "Precio de AAPL", settings,
                            decision=RouterDecision(intent="explanation", symbol=symbol))

    assert received == ["AAPL"]
    assert response.tools_used == ["market_quote", "news", "sec_docs", "instr_features"]
    assert response.status == "degraded"
    assert "AAPL" in response.answer


@pytest.mark.parametrize(("query", "symbol"), [
    ("Dame las métricas de la acción Coca-Cola", "KO"),
    ("Métricas de Coca Cola", "KO"),
    ("Dame las métricas de CocaCola", "KO"),
    ("Métricas de Coke", "KO"),
    ("Métricas de Johnson & Johnson", "JNJ"),
    ("Métricas de J&J", "JNJ"),
    ("Métricas de Jhonson & Jhonson", "JNJ"),
])
def test_company_names_resolve_to_supported_quote_symbols(query, symbol):
    decision = fallback_route(query)
    assert decision.intent == "instrument_info"
    assert decision.symbol == symbol


def test_news_and_filing_http_urls_convert_to_source_reference_strings():
    news = NewsItem(title="Titular de prueba", url="https://example.com/news", provider="fixture",
                    source_id="news:fixture")
    filing = FilingItem(form="10-K", filing_date="2026-11-07", url="https://www.sec.gov/Archives/",
                        accession="fixture", source_id="sec:fixture")

    sources = source_references(None, [news], [filing])

    assert [source.url for source in sources] == [str(news.url), str(filing.url)]
    assert all(isinstance(source.url, str) for source in sources)


def test_router_completes_missing_llm_symbol_from_the_current_query():
    class Client:
        def classify(self, query):
            return RouterDecision(intent="explanation")

    decision = route_query("Precio AAPL", Client())

    assert decision.symbol == "AAPL"
