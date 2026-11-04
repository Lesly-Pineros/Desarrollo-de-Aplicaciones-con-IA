import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import inspect
from sqlmodel import Session

from investiq.data.database import create_db, make_engine
from investiq.data.models import ConversationMemory, UserPreference
from investiq.domain import ConversationMessage, ConversationState, RouterDecision
from investiq.memory import forget_memory, load_memory, save_memory, set_memory_enabled


@pytest.fixture
def store(tmp_path):
    url = f"sqlite:///{tmp_path / 'memory.db'}"
    engine = create_db(make_engine(url))
    with Session(engine) as session:
        yield session, url
    engine.dispose()


def test_restart_restores_only_canonical_context_and_learning_level(store):
    session, url = store
    state = ConversationState(
        last_decision=RouterDecision(intent="education", education_topic="¿Qué es beta? Mi clave es private-memory-secret."),
        pending_field="comparison_preference",
        pending_decision=RouterDecision(intent="compare", comparison_symbols=["AAPL", "private-memory-secret", "MSFT"]),
        preferences_offered=True,
        explanation_level="basic",
        history=[ConversationMessage(role="user", content="Mi clave private-memory-secret. El precio fue 987654.")],
    )

    save_memory(session, "local", state)
    raw = session.get(ConversationMemory, "local").state_json
    assert "private-memory-secret" not in raw
    assert "987654" not in raw
    assert "history" not in raw
    assert json.loads(raw)["last_decision"]["education_topic"] == "beta"

    reopened = make_engine(url)
    with Session(reopened) as restarted:
        snapshot = load_memory(restarted, "local")
        assert snapshot.enabled
        assert snapshot.state.history == []
        assert snapshot.state.pending_field == "comparison_preference"
        assert snapshot.state.pending_decision.comparison_symbols == ["AAPL", "MSFT"]
        assert snapshot.state.explanation_level == "basic"
        assert "beta" in snapshot.summary
        assert "AAPL" in snapshot.summary and "MSFT" in snapshot.summary
        assert "sencillas" in snapshot.summary
        assert snapshot.updated_at.tzinfo is not None
    reopened.dispose()


def test_disabling_forgets_context_and_blocks_future_saves_without_touching_preferences(store):
    session, _ = store
    session.add(UserPreference(email="local", sector="Technology"))
    session.commit()
    state = ConversationState(last_decision=RouterDecision(intent="explanation", symbol="AAPL"))
    save_memory(session, "local", state)

    set_memory_enabled(session, "local", False)
    save_memory(session, "local", state)

    snapshot = load_memory(session, "local")
    assert not snapshot.enabled
    assert snapshot.state.last_decision is None
    assert session.get(ConversationMemory, "local").state_json == "{}"
    assert session.get(UserPreference, "local").sector == "Technology"

    set_memory_enabled(session, "local", True)
    assert load_memory(session, "local").state.last_decision is None
    save_memory(session, "local", state)
    assert load_memory(session, "local").state.last_decision.symbol == "AAPL"


@pytest.mark.parametrize("enabled", [True, False])
def test_forgetting_keeps_enablement_and_persisted_preferences(store, enabled):
    session, _ = store
    session.add(UserPreference(email="local", volatility_target="baja"))
    session.commit()
    save_memory(session, "local", ConversationState(last_decision=RouterDecision(intent="explanation", symbol="NVDA")))
    set_memory_enabled(session, "local", enabled)

    forget_memory(session, "local")

    snapshot = load_memory(session, "local")
    assert snapshot.enabled is enabled
    assert snapshot.state.last_decision is None
    assert session.get(UserPreference, "local").volatility_target == "baja"


def test_configured_retention_expires_existing_state_even_if_stored_expiry_is_later(store):
    session, _ = store
    now = datetime.now(timezone.utc)
    session.add(ConversationMemory(
        user_id="local", state_json='{"last_decision":{"intent":"explanation","symbol":"AAPL"}}',
        updated_at=now - timedelta(days=15), expires_at=now + timedelta(days=75),
    ))
    session.commit()

    snapshot = load_memory(session, "local", retention_days=10)

    assert snapshot.state.last_decision is None
    assert snapshot.updated_at is None
    assert session.get(ConversationMemory, "local").state_json == "{}"


@pytest.mark.parametrize("raw", ["this is private-invalid-json", '["private-array"]', '{"history":[{"role":"unexpected","content":"private-text"}]}'])
def test_malformed_memory_is_safely_cleared(store, raw):
    session, _ = store
    session.add(ConversationMemory(user_id="local", state_json=raw))
    session.commit()

    snapshot = load_memory(session, "local")

    assert snapshot.state == ConversationState()
    assert session.get(ConversationMemory, "local").state_json == "{}"


def test_loading_legacy_memory_scrubs_history_extra_fields_and_uncovered_symbols(store):
    session, _ = store
    session.add(ConversationMemory(user_id="local", state_json=json.dumps({
        "last_decision": {"intent": "explanation", "symbol": "UNCOVERED", "education_topic": "private-price-876543"},
        "history": [{"role": "user", "content": "private-history"}],
        "other": "private-extra-field",
    })))
    session.commit()

    snapshot = load_memory(session, "local")
    raw = session.get(ConversationMemory, "local").state_json

    assert snapshot.state.last_decision.symbol is None
    assert snapshot.state.history == []
    assert "private" not in raw
    assert "876543" not in raw
    assert "UNCOVERED" not in raw


def test_memory_stays_local_to_its_database_and_identity(store, tmp_path):
    session, _ = store
    save_memory(session, "local", ConversationState(last_decision=RouterDecision(intent="explanation", symbol="AAPL")))
    assert load_memory(session, "another-local-identity").state.last_decision is None
    other_engine = create_db(make_engine(f"sqlite:///{tmp_path / 'other-copy.db'}"))
    with Session(other_engine) as other_copy:
        assert load_memory(other_copy, "local").state.last_decision is None
    other_engine.dispose()


def test_create_db_adds_memory_table_to_an_existing_database_without_losing_rows(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'existing.db'}")
    UserPreference.__table__.create(engine)
    with Session(engine) as session:
        session.add(UserPreference(email="local", sector="Health Care"))
        session.commit()

    create_db(engine)

    assert "conversationmemory" in inspect(engine).get_table_names()
    with Session(engine) as session:
        assert session.get(UserPreference, "local").sector == "Health Care"
        save_memory(session, "local", ConversationState(last_decision=RouterDecision(intent="education", education_topic="correlacion")))
        assert load_memory(session, "local").state.last_decision.education_topic == "correlación"
    engine.dispose()
