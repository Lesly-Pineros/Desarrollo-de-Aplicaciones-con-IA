import json
from datetime import datetime, timedelta, timezone
from importlib.resources import files

import pytest
from langchain_core.messages import AIMessage
from sqlmodel import Session, select

from investiq.data.database import create_db, make_engine
from investiq.data.models import QueryLog, ResponseTrace
from investiq.domain import (
    Narration, NewsCollection, QuoteResult, ResponseDiagnostics,
    RouterDecision, SourceReference,
)
from investiq.llm import ChatNVIDIAClient, LLMUnavailable, conversation_style
from investiq.orchestration import answer_query, purge_query_logs
from investiq.responses import DISCLAIMER
from investiq.response_style import provider_failure, safe_narration
from investiq.settings import Settings
from investiq.tutor import TutorEvidence, TutorNarration, TutorParagraph


SOURCE = SourceReference(source_id="verified-source", title="Verified local fixture",
                         url="local://fixture", provider="fixture")


class Narrator:
    def __init__(self, answer, citations=None, error=None):
        self.answer = answer
        self.citations = citations if citations is not None else [SOURCE.source_id]
        self.error = error
        self.calls = []

    def narrate(self, intent, query, facts, sources):
        self.calls.append((intent, query, facts, sources))
        if self.error:
            raise self.error
        return Narration(answer=self.answer, cited_source_ids=self.citations)

    def teach(self, query, passages, context):
        self.calls.append(("education", query, {"retrieved_passages": passages}, context))
        if self.error:
            raise self.error
        return TutorNarration(paragraphs=[TutorParagraph(text=passages[0]["text"], evidence=[
            TutorEvidence(passage_id=passages[0]["passage_id"], quote=passages[0]["text"])])])


def test_grounded_narration_preserves_the_factual_block_exactly():
    result = "AAPL: 2.10% al 2026-11-04T00:00:00+00:00.\n\n| AAPL | 20.00% | 1.10 |"
    client = Narrator("Con lo que tenemos:\n\n{{result}}\n\nPodemos revisarlo paso a paso.")
    diagnostics = ResponseDiagnostics()

    answer = safe_narration(client, "compare", "Compara", {"scores": []}, [SOURCE],
                            result=result, diagnostics=diagnostics)

    assert answer == "Con lo que tenemos:\n\n" + result + "\n\nPodemos revisarlo paso a paso."
    assert client.calls[0][2]["response_block"] == result
    assert diagnostics.narration == "used"
    assert diagnostics.fallback_reason is None


@pytest.mark.parametrize("answer,citations,reason", [
    ("Ya revisé los datos.", [SOURCE.source_id], "missing_result"),
    ("{{result}}\n{{result}}", [SOURCE.source_id], "missing_result"),
    ("{{other}}\n{{result}}", [SOURCE.source_id], "missing_result"),
    ("La variación fue de 25%. {{result}}", [SOURCE.source_id], "extra_number"),
    ("AAPL aparece aquí. {{result}}", [SOURCE.source_id], "extra_symbol"),
    ("XYZ es una alternativa. {{result}}", [SOURCE.source_id], "extra_symbol"),
    ("Apple aparece aquí. {{result}}", [SOURCE.source_id], "extra_symbol"),
    ("Mira https://invented.example. {{result}}", [SOURCE.source_id], "extra_url"),
    ("{{result}}", ["invented-source"], "unknown_citation"),
    ("{{result}}", [], "unknown_citation"),
    ("Compra para aprovecharlo. {{result}}", [SOURCE.source_id], "unsafe_advice"),
    ("Te sugiero vender. {{result}}", [SOURCE.source_id], "unsafe_advice"),
    ("Soy una persona real y te entiendo. {{result}}", [SOURCE.source_id], "persona_violation"),
    ("Soy un humano real y te entiendo. {{result}}", [SOURCE.source_id], "persona_violation"),
    ("Yo he invertido y conozco esa sensación. {{result}}", [SOURCE.source_id], "persona_violation"),
    ("Como humano te acompaño. {{result}}", [SOURCE.source_id], "persona_violation"),
    ("Subió porque hubo optimismo. {{result}}", [SOURCE.source_id], "unverified_claim"),
    ("{{result}} Los dividendos aumentaron y la demanda se disparó.", [SOURCE.source_id], "unverified_claim"),
    ("El sector crece sin parar. {{result}}", [SOURCE.source_id], "unverified_claim"),
    ("{{result}} La empresa anunció una fusión.", [SOURCE.source_id], "unverified_claim"),
])
def test_invalid_financial_prose_cannot_replace_verified_results(answer, citations, reason):
    diagnostics = ResponseDiagnostics()

    assert safe_narration(Narrator(answer, citations), "explanation", "q", {}, [SOURCE],
                          result="AAPL: 2.10% según la fuente.", diagnostics=diagnostics) is None
    assert diagnostics.narration == "fallback"
    assert diagnostics.fallback_reason == reason


def test_absent_client_is_distinguished_from_a_rejected_model_response():
    diagnostics = ResponseDiagnostics()

    assert safe_narration(None, "education", "q", {}, [], diagnostics=diagnostics) is None
    assert diagnostics.narration == "unavailable"
    assert diagnostics.fallback_reason == "not_configured"


@pytest.mark.parametrize("category,reason", [
    ("timeout", "provider_timeout"),
    ("authentication", "provider_authentication"),
    ("rate-limited", "provider_rate_limited"),
    ("Authorization: Bearer sentinel-secret", "provider_error"),
])
def test_provider_fallback_uses_safe_categories_without_exception_payloads(category, reason):
    error = LLMUnavailable("Authorization: Bearer sentinel-secret")
    error.provider_failure_category = category
    diagnostics = ResponseDiagnostics()

    assert provider_failure(error) == reason
    assert safe_narration(Narrator("unused", error=error), "education", "q", {}, [],
                          diagnostics=diagnostics) is None
    assert diagnostics.narration == "fallback"
    assert diagnostics.fallback_reason == reason
    assert "sentinel-secret" not in diagnostics.model_dump_json()


@pytest.fixture
def local_session(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'response-style.db'}"))
    settings = Settings(_env_file=None, nvidia_api_key=None, twelve_data_api_key=None,
                        marketaux_api_key=None, sec_user_agent="")
    with Session(engine) as session:
        yield session, settings
    engine.dispose()


class RoutedNarrator:
    def __init__(self, decision):
        self.decision = decision
        self.calls = []

    def classify(self, query):
        return self.decision.model_copy(deep=True)

    def narrate(self, intent, query, facts, sources):
        self.calls.append((intent, query, facts, sources))
        answer = ("Beta relaciona movimientos históricos; podemos verlo con un ejemplo."
                  if intent == "education" else "Con lo que tenemos:\n\n{{result}}")
        return Narration(answer=answer, cited_source_ids=[source["source_id"] for source in sources])

    def teach(self, query, passages, context):
        self.calls.append(("education", query, {"retrieved_passages": passages}, context))
        return TutorNarration(paragraphs=[TutorParagraph(text=passages[0]["text"], evidence=[
            TutorEvidence(passage_id=passages[0]["passage_id"], quote=passages[0]["text"])])])


@pytest.mark.parametrize("decision,query,expected_tool", [
    (RouterDecision(intent="education", education_topic="beta"), "¿Qué es beta?", None),
    (RouterDecision(intent="explanation", symbol="AAPL"), "Precio AAPL", "market_quote"),
    (RouterDecision(intent="recommend_volatility", volatility_target="baja"), "Busca volatilidad baja", "volatility_bucket"),
    (RouterDecision(intent="recommend_similar", reference_symbol="NVDA"), "Busca similares a NVDA", "similar_instruments"),
    (RouterDecision(intent="compare", comparison_symbols=["AAPL", "MSFT"]), "Compara AAPL MSFT", "compare_instruments"),
])
def test_all_tool_routes_can_narrate_and_persist_safe_diagnostics(local_session, monkeypatch, decision, query, expected_tool):
    session, settings = local_session
    monkeypatch.setattr("investiq.handlers.market_quote_tool", lambda *args: QuoteResult(
        symbol="AAPL", price=100.0, change_pct=2.1,
        as_of=datetime(2026, 11, 4, tzinfo=timezone.utc), provider="fixture", delayed=True, source=SOURCE,
    ))
    monkeypatch.setattr("investiq.handlers.news_tool", lambda *args: NewsCollection(articles=[], reason="sin noticias en fixture"))
    monkeypatch.setattr("investiq.handlers.sec_docs_tool", lambda *args: ([], "sin filings en fixture"))
    monkeypatch.setattr("investiq.handlers.local_model_source", lambda *args: SOURCE)
    monkeypatch.setattr("investiq.handlers.volatility_bucket", lambda *args: [{"symbol": "AAPL"}])
    monkeypatch.setattr("investiq.handlers.similar_instruments", lambda *args: [{"symbol": "AAPL", "cluster_label": 1}])
    monkeypatch.setattr("investiq.handlers.compare_instruments", lambda *args, **kwargs: [
        {"symbol": "AAPL", "score": 80.0}, {"symbol": "MSFT", "score": 60.0},
    ])
    client = RoutedNarrator(decision)

    response = answer_query(session, "local", query, settings, client=client)

    assert response.intent == decision.intent
    assert response.answer.count(DISCLAIMER) == 1
    assert response.diagnostics.routing == "llm"
    assert response.diagnostics.narration == "used"
    assert response.diagnostics.fallback_reason is None
    if expected_tool:
        assert expected_tool in response.tools_used
        factual_block = client.calls[0][2]["response_block"]
        assert response.answer == "Con lo que tenemos:\n\n" + factual_block + "\n\n" + DISCLAIMER
        assert [source.source_id for source in response.sources] == [SOURCE.source_id]
    else:
        assert "response_block" not in client.calls[0][2]
        assert "knowledge_search" in response.tools_used
        assert client.calls[0][2]["retrieved_passages"]
        assert response.sources and all(source.url.startswith("https://") for source in response.sources)
    log = session.exec(select(QueryLog)).one()
    trace = session.get(ResponseTrace, log.id)
    assert trace.routing == "llm"
    assert trace.narration == "used"
    assert trace.fallback_reason is None
    assert not hasattr(log, "query")
    assert not hasattr(trace, "prompt")


def test_no_key_and_provider_failure_have_different_persisted_diagnostics(local_session):
    session, settings = local_session
    decision = RouterDecision(intent="education", education_topic="beta")
    local = answer_query(session, "local", "¿Qué es beta?", settings, decision=decision)
    error = LLMUnavailable("Authorization: Bearer sentinel-secret")
    error.provider_failure_category = "authentication"
    failed = answer_query(session, "local", "¿Qué es beta?", settings,
                          decision=decision, client=Narrator("unused", error=error))

    assert local.diagnostics.narration == "unavailable"
    assert local.diagnostics.fallback_reason == "not_configured"
    assert failed.diagnostics.narration == "fallback"
    assert failed.diagnostics.fallback_reason == "provider_authentication"
    traces = session.exec(select(ResponseTrace).order_by(ResponseTrace.query_log_id)).all()
    assert [trace.fallback_reason for trace in traces] == ["not_configured", "provider_authentication"]
    persisted = json.dumps([row.model_dump(mode="json") for row in session.exec(select(QueryLog)).all()] +
                           [row.model_dump(mode="json") for row in traces])
    assert "sentinel-secret" not in persisted + failed.answer


def test_no_evidence_query_is_not_stored_or_sent_to_the_teacher(local_session):
    session, settings = local_session
    client = Narrator("unused", error=LLMUnavailable("must not be called"))
    response = answer_query(session, "local", "private-user-input-sentinel", settings,
                            decision=RouterDecision(intent="education", education_topic="beta"), client=client)

    assert response.status == "degraded"
    assert response.diagnostics.narration == "not_requested"
    assert client.calls == []
    logs = session.exec(select(QueryLog)).all()
    traces = session.exec(select(ResponseTrace)).all()
    persisted = json.dumps([row.model_dump(mode="json") for row in [*logs, *traces]])
    assert "private-user-input-sentinel" not in persisted + response.answer
    assert all(not hasattr(row, "query") for row in logs)


def test_query_retention_purges_corresponding_diagnostics_without_removing_recent_rows(local_session):
    session, _ = local_session
    old = QueryLog(email="local", created_at=datetime.now(timezone.utc) - timedelta(days=100),
                   intent="education", tools_json="[]", sources_json="[]", status="ok")
    recent = QueryLog(email="local", intent="education", tools_json="[]", sources_json="[]", status="ok")
    session.add(old)
    session.add(recent)
    session.flush()
    old_id, recent_id = old.id, recent.id
    session.add(ResponseTrace(query_log_id=old_id, narration="fallback", fallback_reason="provider_timeout"))
    session.add(ResponseTrace(query_log_id=recent_id, narration="used"))
    session.commit()

    assert purge_query_logs(session, 90) == 1
    assert session.get(QueryLog, old_id) is None
    assert session.get(ResponseTrace, old_id) is None
    assert session.get(QueryLog, recent_id) is not None
    assert session.get(ResponseTrace, recent_id).narration == "used"


def test_nvidia_prompt_loads_the_packaged_style_and_requires_a_single_factual_marker():
    class Model:
        def __init__(self):
            self.calls = []

        def invoke(self, messages):
            self.calls.append(messages)
            return AIMessage(content='{"answer":"{{result}}","cited_source_ids":["verified-source"]}')

    model = Model()
    client = ChatNVIDIAClient(Settings(_env_file=None, nvidia_api_key=None), model=model)
    factual_block = "AAPL: 2.10% según la fuente."
    narration = client.narrate("explanation", "Precio AAPL", {"response_block": factual_block}, [SOURCE.model_dump(mode="json")])

    style = conversation_style()
    assert style == files("investiq").joinpath("prompts/conversation.md").read_text(encoding="utf-8")
    assert "# Voz de InvestiQ" in style
    assert "No termines cada respuesta con una pregunta" in style
    assert model.calls[0][0].content.startswith(style)
    assert "{{result}} EXACTAMENTE una vez" in model.calls[0][0].content
    user_payload = json.loads(model.calls[0][1].content)
    assert user_payload["deterministic_facts"]["response_block"] == factual_block
    assert user_payload["untrusted_sources"][0]["source_id"] == SOURCE.source_id
    assert "Con lo que tenemos:" in user_payload["deterministic_facts"]["allowed_openings"]
    assert "Podemos revisarlo paso a paso." in user_payload["deterministic_facts"]["allowed_closings"]
    assert narration.answer == "{{result}}"


def test_a_recovered_narration_preserves_a_classifier_failure_diagnostic():
    diagnostics = ResponseDiagnostics(routing="rules", fallback_reason="provider_timeout")
    answer = safe_narration(Narrator("{{result}}"), "compare", "q", {}, [SOURCE],
                            result="AAPL: 80/100.", diagnostics=diagnostics)
    assert answer == "AAPL: 80/100."
    assert diagnostics.narration == "used"
    assert diagnostics.fallback_reason == "provider_timeout"
