from datetime import datetime, timezone

import pytest
from sqlmodel import Session

from investiq.conversation import answer_turn
from investiq.data.database import create_db, make_engine
from investiq.data.models import InstrumentFeature, UserPreference
from investiq.domain import (
    ConversationState,
    NewsCollection,
    QuoteResult,
    RouterDecision,
    SourceReference,
)
from investiq.orchestration import answer_query
from investiq.responses import DISCLAIMER
from investiq.settings import Settings
from investiq.tools import compare_instruments


@pytest.fixture
def chat(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'conversation.db'}"))
    settings = Settings(
        _env_file=None,
        nvidia_api_key=None,
        twelve_data_api_key=None,
        marketaux_api_key=None,
        sec_user_agent="",
    )
    with Session(engine) as session:
        yield session, settings, ConversationState()
    engine.dispose()


def ask(chat, query):
    session, settings, state = chat
    response = answer_turn(session, "local", query, settings, state=state)
    assert DISCLAIMER in response.answer
    return response


def local_fixture_source(session):
    return SourceReference(
        source_id="ml:fixture", title="Dataset simulado para diálogo",
        url="local://test-fixture", provider="fixture offline",
    )


@pytest.fixture
def comparison_calls(monkeypatch):
    calls = []

    def compare(session, user_id, symbols, *args, **kwargs):
        saved = session.get(UserPreference, user_id)
        personalized = kwargs.get("use_preferences", True) and bool(saved and any((
            saved.volatility_target,
            saved.sector,
            saved.reference_symbol,
            saved.beta_target is not None,
        )))
        calls.append(list(symbols))
        return [
            {
                "symbol": symbol,
                "score": 80.0 if personalized else None,
                "volatility": 0.2,
                "volatility_bucket": "baja",
                "beta": 1.1,
                "sector": "Technology",
                "calculated_at": "2026-11-04T00:00:00+00:00",
                "components": {"volatility": 1.0} if personalized else {},
            }
            for symbol in symbols
        ]

    monkeypatch.setattr("investiq.handlers.compare_instruments", compare)
    monkeypatch.setattr("investiq.handlers.local_model_source", local_fixture_source)
    return calls


@pytest.fixture
def quote_calls(monkeypatch):
    requested = []

    def quote(session, symbol, settings):
        requested.append(symbol)
        return QuoteResult(
            symbol=symbol,
            price=100.0,
            change_pct=1.0,
            as_of=datetime(2026, 11, 4, tzinfo=timezone.utc),
            provider="fixture",
            delayed=True,
            source=SourceReference(
                source_id=f"quote:{symbol}", title=symbol,
                url="https://example.com/quote", provider="fixture",
            ),
        )

    monkeypatch.setattr("investiq.handlers.market_quote_tool", quote)
    monkeypatch.setattr("investiq.handlers.news_tool", lambda *args: NewsCollection(articles=[]))
    monkeypatch.setattr("investiq.handlers.sec_docs_tool", lambda *args: ([], "Sin filings en la fixture."))
    return requested


@pytest.fixture
def similarity_calls(monkeypatch):
    calls = []

    def similar(session, reference):
        calls.append(reference)
        return [{"symbol": "AAPL", "cluster_label": 1}]

    monkeypatch.setattr("investiq.handlers.similar_instruments", similar)
    monkeypatch.setattr("investiq.handlers.local_model_source", local_fixture_source)
    return calls


def test_preference_reply_resumes_the_original_comparison(chat, comparison_calls):
    session, _, state = chat
    first = ask(chat, "Compara AAPL y MSFT")

    assert "?" in first.answer
    assert state.pending_field
    assert comparison_calls == []

    second = ask(chat, "baja")

    assert session.get(UserPreference, "local").volatility_target == "baja"
    assert second.intent == "compare"
    assert comparison_calls == [["AAPL", "MSFT"]]
    assert state.pending_field is None
    assert "AAPL" in second.answer and "MSFT" in second.answer


def test_reference_reply_resumes_similarity_without_creating_global_preferences(chat, similarity_calls):
    ask(chat, "Busca instrumentos similares")
    response = ask(chat, "NVDA")

    assert similarity_calls == ["NVDA"]
    assert response.intent == "recommend_similar"
    assert chat[0].get(UserPreference, "local") is None
    assert chat[2].pending_field is None


def test_one_off_volatility_filter_does_not_become_a_saved_preference(chat, monkeypatch):
    targets = []

    def bucket(session, target):
        targets.append(target)
        return [{"symbol": "AAPL"}]

    monkeypatch.setattr("investiq.handlers.volatility_bucket", bucket)
    monkeypatch.setattr("investiq.handlers.local_model_source", local_fixture_source)
    response = ask(chat, "Busca instrumentos de volatilidad baja")

    assert targets == ["baja"]
    assert response.intent == "recommend_volatility"
    assert chat[0].get(UserPreference, "local") is None


def test_education_can_interrupt_a_preference_question_without_saving_a_value(chat, comparison_calls):
    ask(chat, "Compara AAPL con MSFT")
    response = ask(chat, "¿Qué es beta?")

    assert response.intent == "education"
    assert "beta" in response.answer.casefold()
    assert chat[0].get(UserPreference, "local") is None
    assert comparison_calls == []


@pytest.mark.parametrize("question", ["¿Y qué es beta?", "¿Puedes explicarme beta?", "Explícame qué significa beta"])
def test_conversational_education_can_interrupt_and_be_followed_by_an_example(chat, comparison_calls, question):
    ask(chat, "Compara AAPL con MSFT")
    explanation = ask(chat, question)
    example = ask(chat, "Un ejemplo")

    assert explanation.intent == example.intent == "education"
    assert chat[0].get(UserPreference, "local") is None
    assert chat[2].pending_field == "comparison_preference"
    assert comparison_calls == []
    resumed = ask(chat, "baja")
    assert resumed.intent == "compare"
    assert comparison_calls == [["AAPL", "MSFT"]]


def test_explicit_sector_update_preserves_previously_saved_preferences(chat):
    session, _, _ = chat
    session.add(UserPreference(email="local", volatility_target="baja", beta_target=1.2))
    session.commit()

    ask(chat, "Prefiero tecnología")

    saved = session.get(UserPreference, "local")
    assert saved.sector == "Technology"
    assert saved.volatility_target == "baja"
    assert saved.beta_target == 1.2


@pytest.mark.parametrize("query", [
    "Prefiero beta 99",
    "No quiero volatilidad alta",
    "Prefiero volatilidad baja o alta",
    "Prefiero tecnología y beta 99",
    "Prefiero FAKE como referencia",
    "Prefiero AAPL y MSFT como referencia",
    "Quita mi sector y no quiero volatilidad alta",
])
def test_invalid_or_ambiguous_preference_does_not_overwrite_saved_criteria(chat, query):
    session, _, _ = chat
    session.add(UserPreference(email="local", sector="Health Care"))
    session.commit()

    ask(chat, query)

    saved = session.get(UserPreference, "local")
    assert saved.sector == "Health Care"
    assert saved.volatility_target is None
    assert saved.beta_target is None


def test_skipping_preferences_compares_features_without_a_fabricated_score(chat, comparison_calls):
    ask(chat, "Compara AAPL y MSFT")
    response = ask(chat, "Sin preferencias")

    assert comparison_calls == [["AAPL", "MSFT"]]
    assert response.intent == "compare"
    assert "compare_instruments" in response.tools_used
    assert "/100" not in response.answer
    assert chat[0].get(UserPreference, "local") is None


def test_preferences_can_be_read_and_cleared_in_the_chat(chat):
    session, _, _ = chat
    session.add(UserPreference(email="local", volatility_target="baja", sector="Technology"))
    session.commit()

    shown = ask(chat, "¿Cuáles son mis preferencias?")
    assert "baja" in shown.answer.casefold()

    ask(chat, "Borra mis preferencias")
    remaining = session.get(UserPreference, "local")
    assert remaining is None or all(
        value is None
        for value in (remaining.volatility_target, remaining.sector, remaining.reference_symbol, remaining.beta_target)
    )


def test_greeting_and_instrument_followup_keep_context_without_network(chat, quote_calls):
    greeting = ask(chat, "Hola")
    assert greeting.tools_used == []
    assert quote_calls == []

    ask(chat, "Precio AAPL")
    response = ask(chat, "¿Y MSFT?")
    assert quote_calls == ["AAPL", "MSFT"]
    assert response.intent == "explanation"
    assert "MSFT" in response.answer
    assert chat[0].get(UserPreference, "local") is None


def seed_comparison_features(session):
    session.add_all([
        InstrumentFeature(
            symbol="AAPL", volatility=0.3, mean_peer_correlation=0.8,
            beta=1.0, sector="Technology", volatility_bucket="alta",
        ),
        InstrumentFeature(
            symbol="MSFT", volatility=0.1, mean_peer_correlation=0.8,
            beta=0.0, sector="Technology", volatility_bucket="baja",
        ),
    ])
    session.commit()


def test_real_comparison_without_preferences_returns_features_without_a_ranking(chat):
    session, _, _ = chat
    seed_comparison_features(session)

    rows = compare_instruments(session, "local", ["MSFT", "AAPL"])

    assert [row["symbol"] for row in rows] == ["AAPL", "MSFT"]
    assert all(row["score"] is None and row["components"] == {} for row in rows)
    assert rows[0]["volatility"] == 0.3
    assert rows[1]["beta"] == 0.0


def test_zero_beta_is_a_real_preference_and_does_not_trigger_an_interview(chat, monkeypatch):
    session, _, state = chat
    seed_comparison_features(session)
    session.add(UserPreference(email="local", beta_target=0.0))
    session.commit()
    monkeypatch.setattr("investiq.handlers.local_model_source", local_fixture_source)

    rows = compare_instruments(session, "local", ["AAPL", "MSFT"])
    response = ask(chat, "Compara AAPL y MSFT")

    assert rows[0]["symbol"] == "MSFT"
    assert rows[0]["score"] == 100.0
    assert rows[1]["score"] == 50.0
    assert "compare_instruments" in response.tools_used
    assert state.pending_field is None


def test_pending_comparison_survives_serialization_and_an_educational_interruption(chat, comparison_calls):
    session, settings, state = chat
    ask(chat, "Compara AAPL con MSFT")
    restored = ConversationState.model_validate_json(state.model_dump_json())

    interruption = answer_turn(session, "local", "¿Qué es beta?", settings, state=restored)
    assert interruption.intent == "education"
    assert restored.pending_decision.comparison_symbols == ["AAPL", "MSFT"]
    assert restored.pending_field

    resumed = answer_turn(session, "local", "baja", settings, state=restored)
    assert resumed.intent == "compare"
    assert DISCLAIMER in resumed.answer
    assert comparison_calls == [["AAPL", "MSFT"]]
    assert restored.pending_field is None


def test_history_is_bounded_and_can_be_restored_between_streamlit_reruns(chat):
    for _ in range(7):
        ask(chat, "Hola")

    state = chat[2]
    assert len(state.history) == 8
    assert [message.role for message in state.history] == ["user", "assistant"] * 4
    assert all(len(message.content) <= 1200 for message in state.history)
    restored = ConversationState.model_validate_json(state.model_dump_json())
    assert restored == state


def test_education_followup_keeps_the_topic_and_an_explicit_new_concept_changes_it(chat):
    first = ask(chat, "¿Qué es beta?")
    example = ask(chat, "Un ejemplo")

    assert example.intent == "education"
    assert "beta" in example.answer.casefold()
    assert example.answer != first.answer
    assert "beta" in chat[2].last_decision.education_topic.casefold()

    changed = ask(chat, "¿Y qué es un ETF?")

    assert changed.intent == "education"
    assert "etf" in changed.answer.casefold()
    assert "beta" not in changed.answer.casefold()
    assert "etf" in chat[2].last_decision.education_topic.casefold()


def test_a_preference_invented_by_the_classifier_is_not_persisted(chat):
    class InventingClassifier:
        def __init__(self):
            self.calls = []

        def classify(self, query):
            self.calls.append(query)
            return RouterDecision(
                intent="compare", comparison_symbols=["AAPL", "MSFT"], volatility_target="alta",
            )

        def narrate(self, *args):
            raise AssertionError("A preference question must not narrate invented criteria")

    session, settings, state = chat
    client = InventingClassifier()
    response = answer_turn(session, "local", "Contrasta AAPL con MSFT", settings, state=state, client=client)

    assert len(client.calls) == 1
    assert session.get(UserPreference, "local") is None
    assert response.tools_used == []
    assert state.pending_field == "comparison_preference"
    assert "?" in response.answer
    assert DISCLAIMER in response.answer


def test_new_price_request_replaces_a_pending_preference_question(chat, comparison_calls, quote_calls):
    ask(chat, "Compara AAPL y MSFT")
    response = ask(chat, "Precio AAPL")

    assert response.intent == "explanation"
    assert quote_calls == ["AAPL"]
    assert comparison_calls == []
    assert chat[0].get(UserPreference, "local") is None
    assert chat[2].pending_field is None


def test_new_similarity_request_is_not_saved_as_an_answer_to_the_preference_question(chat, comparison_calls, similarity_calls):
    ask(chat, "Compara AAPL y MSFT")
    response = ask(chat, "Busca similares a NVDA")

    assert response.intent == "recommend_similar"
    assert similarity_calls == ["NVDA"]
    assert comparison_calls == []
    assert chat[0].get(UserPreference, "local") is None
    assert chat[2].pending_field is None


def test_inline_request_without_preferences_skips_the_interview(chat, comparison_calls):
    response = ask(chat, "Compara AAPL y MSFT sin preferencias")

    assert response.intent == "compare"
    assert comparison_calls == [["AAPL", "MSFT"]]
    assert "compare_instruments" in response.tools_used
    assert "/100" not in response.answer
    assert chat[2].pending_field is None
    assert chat[0].get(UserPreference, "local") is None


def test_real_comparison_can_ignore_saved_preferences_without_deleting_them(chat):
    session, _, _ = chat
    seed_comparison_features(session)
    session.add(UserPreference(email="local", sector="Health Care", beta_target=0.0))
    session.commit()

    personalized = compare_instruments(session, "local", ["AAPL", "MSFT"])
    general = compare_instruments(session, "local", ["AAPL", "MSFT"], use_preferences=False)

    assert all(row["score"] is not None for row in personalized)
    assert all(row["score"] is None and row["components"] == {} for row in general)
    saved = session.get(UserPreference, "local")
    assert saved.sector == "Health Care"
    assert saved.beta_target == 0.0


def test_real_comparison_exposes_feature_sources_without_a_cluster_run(chat):
    session, settings, _ = chat
    seed_comparison_features(session)

    response = answer_query(session, "local", "Compara AAPL y MSFT", settings)

    assert response.intent == "compare"
    assert "compare_instruments" in response.tools_used
    assert DISCLAIMER in response.answer
    assert len(response.sources) == 2
    assert {source.url for source in response.sources} == {"local://features/AAPL", "local://features/MSFT"}
    assert all(source.source_id.startswith("features:") for source in response.sources)
