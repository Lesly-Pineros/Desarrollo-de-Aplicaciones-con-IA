"""Offline integration of evidence-backed preferences with ongoing dialogue."""

import json

import pytest
from sqlmodel import Session, select

from investiq.conversation import answer_turn
from investiq.data.database import create_db, make_engine
from investiq.data.models import ConversationMemory, QueryLog, UserPreference
from investiq.domain import ConversationState, Narration, SourceReference
from investiq.llm import LLMUnavailable
from investiq.responses import DISCLAIMER
from investiq.routing import fallback_route
from investiq.settings import Settings


class SemanticClient:
    def __init__(self, output):
        self.output = output
        self.interpret_calls = []
        self.classify_calls = []

    def interpret_preferences(self, query, context):
        self.interpret_calls.append((query, context))
        if isinstance(self.output, Exception):
            raise self.output
        return self.output

    def classify(self, query):
        try:
            message = json.loads(query).get("current_message", query)
        except (ValueError, AttributeError):
            message = query
        self.classify_calls.append(message)
        return fallback_route(message)

    def narrate(self, intent, query, facts, sources):
        return Narration(
            answer="{{result}}" if "response_block" in facts else facts["definition"],
            cited_source_ids=[source["source_id"] for source in sources],
        )


class RulesOnlyClient:
    """Older injected clients remain compatible without semantic capability."""

    def classify(self, query):
        return fallback_route(query)

    def narrate(self, *args):
        raise AssertionError("An unresolved preference declaration has no factual narration")


def proposed_volatility(evidence, target="baja"):
    return {"kind": "preference", "changes": [{
        "field": "volatility_target", "value": target, "evidence": evidence,
    }]}


@pytest.fixture
def dialogue(tmp_path, monkeypatch):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'semantic-dialogue.db'}"))
    settings = Settings(
        _env_file=None, nvidia_api_key=None,
        twelve_data_api_key=None, marketaux_api_key=None, sec_user_agent="",
    )
    calls = {"compare": [], "similar": []}

    def no_market_call(*args, **kwargs):
        raise AssertionError("Preference dialogues must not trigger a market provider")

    monkeypatch.setattr("investiq.handlers.market_quote_tool", no_market_call)
    monkeypatch.setattr("investiq.handlers.news_tool", no_market_call)
    monkeypatch.setattr("investiq.handlers.sec_docs_tool", no_market_call)

    def compare(session, user_id, symbols, **kwargs):
        calls["compare"].append(list(symbols))
        return [{
            "symbol": symbol, "score": 80.0, "components": {"volatility": 1.0},
            "volatility": 0.2, "volatility_bucket": "baja", "beta": 1.0,
            "sector": "Technology", "calculated_at": "2026-11-04T00:00:00+00:00",
        } for symbol in symbols]

    def similar(session, reference):
        calls["similar"].append(reference)
        return [{"symbol": "AAPL", "cluster_label": 1}]

    source = SourceReference(
        source_id="ml:semantic-fixture", title="Simulación offline",
        provider="fixture", url="local://semantic-fixture",
    )
    monkeypatch.setattr("investiq.handlers.compare_instruments", compare)
    monkeypatch.setattr("investiq.handlers.similar_instruments", similar)
    monkeypatch.setattr("investiq.handlers.local_model_source", lambda session: source)
    with Session(engine) as session:
        yield session, settings, ConversationState(), calls
    engine.dispose()


def ask(dialogue, query, client=None):
    session, settings, state, _ = dialogue
    response = answer_turn(session, "local", query, settings, state=state, client=client)
    assert DISCLAIMER in response.answer
    return response


@pytest.mark.parametrize("query,evidence", [
    ("Prefiero pocos sobresaltos en el precio", "pocos sobresaltos en el precio"),
    ("Me gustaría que el precio se mueva poquito", "que el precio se mueva poquito"),
])
def test_paraphrased_declaration_preserves_other_preferences_without_a_market_query(dialogue, query, evidence):
    session, _, state, calls = dialogue
    session.add(UserPreference(email="local", sector="Health Care", beta_target=0.8))
    session.commit()
    client = SemanticClient(proposed_volatility(evidence))

    response = ask(dialogue, query, client)

    saved = session.get(UserPreference, "local")
    assert saved.volatility_target == "baja"
    assert saved.sector == "Health Care"
    assert saved.beta_target == 0.8
    assert response.intent == "unknown"
    assert response.tools_used == []
    assert state.pending_field is None
    assert len(client.interpret_calls) == 1
    assert calls == {"compare": [], "similar": []}


def test_paraphrase_with_price_word_completes_the_pending_comparison(dialogue):
    session, _, state, calls = dialogue
    ask(dialogue, "Compara AAPL y MSFT")
    assert state.pending_field == "comparison_preference"
    client = SemanticClient(proposed_volatility("pocos sobresaltos en el precio"))

    response = ask(dialogue, "Prefiero pocos sobresaltos en el precio", client)

    assert session.get(UserPreference, "local").volatility_target == "baja"
    assert response.intent == "compare"
    assert calls["compare"] == [["AAPL", "MSFT"]]
    assert state.pending_field is None
    assert "compare_instruments" in response.tools_used


def test_missing_literal_evidence_does_not_save_even_a_canonical_value(dialogue):
    session, _, _, calls = dialogue
    session.add(UserPreference(email="local", sector="Health Care"))
    session.commit()
    client = SemanticClient(proposed_volatility("volatilidad baja"))

    response = ask(dialogue, "Prefiero pocos sobresaltos en el precio", client)

    saved = session.get(UserPreference, "local")
    assert saved.sector == "Health Care"
    assert saved.volatility_target is None
    assert response.tools_used == []
    assert calls == {"compare": [], "similar": []}
    assert "?" in response.answer


def test_general_risk_statement_does_not_become_a_volatility_target(dialogue):
    client = SemanticClient(proposed_volatility("riesgo bajo"))
    response = ask(dialogue, "Prefiero riesgo bajo", client)

    assert dialogue[0].get(UserPreference, "local") is None
    assert response.tools_used == []
    assert "?" in response.answer


def test_new_similarity_filter_interrupts_preference_question_without_semantic_updates(dialogue):
    session, _, state, calls = dialogue
    ask(dialogue, "Compara AAPL y MSFT")
    client = SemanticClient(proposed_volatility("baja"))

    response = ask(dialogue, "Busca instrumentos similares a NVDA", client)

    assert response.intent == "recommend_similar"
    assert calls == {"compare": [], "similar": ["NVDA"]}
    assert client.interpret_calls == []
    assert session.get(UserPreference, "local") is None
    assert state.pending_field is None


def test_semantic_provider_failure_uses_local_clarification_without_leaking_payload(dialogue):
    secret = "Bearer private-semantic-provider-payload"
    client = SemanticClient(LLMUnavailable(secret))

    response = ask(dialogue, "Prefiero pocos sobresaltos en el precio", client)

    session = dialogue[0]
    assert session.get(UserPreference, "local") is None
    assert response.tools_used == []
    assert secret not in json.dumps(response.model_dump(mode="json"))
    for row in session.exec(select(QueryLog)).all():
        assert secret not in json.dumps(row.model_dump(mode="json"))
    assert secret not in session.get(ConversationMemory, "local").state_json


@pytest.mark.parametrize("client", [None, RulesOnlyClient()])
def test_local_fallback_remains_available_without_semantic_capability(dialogue, client):
    response = ask(dialogue, "Prefiero pocos sobresaltos en el precio", client)
    assert dialogue[0].get(UserPreference, "local") is None
    assert response.tools_used == []
    assert response.intent == "unknown"
    assert dialogue[2].pending_field == "comparison_preference"
