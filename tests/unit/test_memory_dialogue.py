from pathlib import Path

import pytest
from sqlmodel import Session

from investiq.conversation import answer_turn
from investiq.data.database import create_db, make_engine
from investiq.data.models import ConversationMemory, UserPreference
from investiq.domain import SourceReference
from investiq.memory import load_memory
from investiq.responses import DISCLAIMER
from investiq.settings import Settings


@pytest.fixture
def memory_chat(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'dialogue-memory.db'}"))
    settings = Settings(
        _env_file=None, nvidia_api_key=None, twelve_data_api_key=None,
        marketaux_api_key=None, sec_user_agent="",
    )
    yield engine, settings
    engine.dispose()


def turn(engine, settings, query):
    # Each turn opens a new DB session and provides no in-memory dialogue state.
    with Session(engine) as session:
        response = answer_turn(session, "local", query, settings, state=None)
        assert DISCLAIMER in response.answer
        return response


def test_restart_restores_education_topic_for_an_example(memory_chat):
    engine, settings = memory_chat
    assert turn(engine, settings, "¿Qué es beta?").intent == "education"

    response = turn(engine, settings, "Un ejemplo")

    assert response.intent == "education"
    assert "beta" in response.answer.casefold()
    with Session(engine) as session:
        snapshot = load_memory(session, "local")
        assert snapshot.state.last_decision.education_topic == "beta"
        assert snapshot.state.history == []
        assert "Un ejemplo" not in session.get(ConversationMemory, "local").state_json


def test_restart_resumes_pending_comparison_when_the_preference_arrives(memory_chat, monkeypatch):
    engine, settings = memory_chat
    calls = []

    def compare(session, user_id, symbols, **kwargs):
        calls.append(list(symbols))
        assert session.get(UserPreference, user_id).volatility_target == "baja"
        return [{"symbol": symbol, "score": 75.0} for symbol in symbols]

    monkeypatch.setattr("investiq.handlers.compare_instruments", compare)
    monkeypatch.setattr("investiq.handlers.local_model_source", lambda session: SourceReference(
        source_id="ml:memory-fixture", title="Datos simulados de comparación",
        url="local://memory-fixture", provider="fixture offline",
    ))
    asked = turn(engine, settings, "Compara AAPL con MSFT")
    assert "?" in asked.answer
    assert calls == []

    resumed = turn(engine, settings, "baja")

    assert resumed.intent == "compare"
    assert calls == [["AAPL", "MSFT"]]
    with Session(engine) as session:
        snapshot = load_memory(session, "local")
        assert snapshot.state.pending_field is None
        assert snapshot.state.last_decision.comparison_symbols == ["AAPL", "MSFT"]


def test_simple_explanation_preference_is_persisted_and_visible(memory_chat):
    engine, settings = memory_chat
    turn(engine, settings, "Prefiero explicaciones sencillas")
    turn(engine, settings, "¿Qué es beta?")

    shown = turn(engine, settings, "¿Qué recuerdas de mí?")

    assert "sencillas" in shown.answer
    assert "beta" in shown.answer.casefold()
    with Session(engine) as session:
        assert load_memory(session, "local").state.explanation_level == "basic"
        assert session.get(UserPreference, "local") is None


def test_forgetting_context_preserves_preferences_and_clears_displayed_history(memory_chat):
    engine, settings = memory_chat
    turn(engine, settings, "Prefiero tecnología")
    turn(engine, settings, "¿Qué es beta?")

    forgotten = turn(engine, settings, "Olvida el contexto")

    assert forgotten.clear_history
    with Session(engine) as session:
        assert load_memory(session, "local").state.last_decision is None
        assert session.get(UserPreference, "local").sector == "Technology"


def test_deleting_preferences_preserves_conversation_topic(memory_chat):
    engine, settings = memory_chat
    turn(engine, settings, "Prefiero tecnología")
    turn(engine, settings, "¿Qué es beta?")

    cleared = turn(engine, settings, "Borra mis preferencias")

    assert not cleared.clear_history
    with Session(engine) as session:
        assert session.get(UserPreference, "local") is None
        assert load_memory(session, "local").state.last_decision.education_topic == "beta"


def test_disabled_memory_does_not_save_new_topics_until_explicitly_reenabled(memory_chat):
    engine, settings = memory_chat
    turn(engine, settings, "¿Qué es beta?")
    turn(engine, settings, "Desactiva la memoria")
    turn(engine, settings, "¿Qué es un ETF?")

    with Session(engine) as session:
        snapshot = load_memory(session, "local")
        assert not snapshot.enabled
        assert snapshot.state.last_decision is None
        assert session.get(ConversationMemory, "local").state_json == "{}"

    turn(engine, settings, "Activa la memoria")
    turn(engine, settings, "¿Qué es riesgo?")
    with Session(engine) as session:
        snapshot = load_memory(session, "local")
        assert snapshot.enabled
        assert snapshot.state.last_decision.education_topic == "riesgo"


@pytest.fixture
def ui_memory(tmp_path, monkeypatch):
    AppTest = pytest.importorskip("streamlit.testing.v1", reason="Interfaz heredada opcional: instala .[legacy-ui]").AppTest
    monkeypatch.chdir(tmp_path)
    url = f"sqlite:///{tmp_path / 'memory-ui.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    for key in ("NVIDIA_API_KEY", "TWELVE_DATA_API_KEY", "MARKETAUX_API_KEY", "SEC_USER_AGENT"):
        monkeypatch.setenv(key, "")
    path = Path(__file__).resolve().parents[2] / "src/investiq/app.py"
    app = AppTest.from_file(str(path)).run(timeout=30)
    assert not app.exception
    yield app, url


def test_ui_forget_button_clears_chat_and_context_but_keeps_preferences(ui_memory):
    app, url = ui_memory
    app.chat_input[0].set_value("Prefiero tecnología").run(timeout=30)
    app.chat_input[0].set_value("¿Qué es beta?").run(timeout=30)
    assert not app.exception
    assert len(app.chat_message) > 1

    app.button(key="investiq_forget_context").click().run(timeout=30)

    assert not app.exception
    assert len(app.chat_message) == 1
    engine = make_engine(url)
    with Session(engine) as session:
        assert load_memory(session, "local").state.last_decision is None
        assert session.get(UserPreference, "local").sector == "Technology"
    engine.dispose()


def test_ui_toggle_and_chat_commands_stay_synchronized_without_reenabling(ui_memory):
    app, url = ui_memory
    app.chat_input[0].set_value("¿Qué es beta?").run(timeout=30)
    assert app.toggle(key="investiq_memory_enabled").value

    app.toggle(key="investiq_memory_enabled").set_value(False).run(timeout=30)
    app.chat_input[0].set_value("¿Qué es un ETF?").run(timeout=30)
    assert not app.exception
    assert not app.toggle(key="investiq_memory_enabled").value
    engine = make_engine(url)
    with Session(engine) as session:
        assert not load_memory(session, "local").enabled
        assert session.get(ConversationMemory, "local").state_json == "{}"

    app.chat_input[0].set_value("Activa la memoria").run(timeout=30)
    assert not app.exception
    assert app.toggle(key="investiq_memory_enabled").value
    app.chat_input[0].set_value("Desactiva la memoria").run(timeout=30)
    assert not app.exception
    assert not app.toggle(key="investiq_memory_enabled").value
    app.run(timeout=30)
    assert not app.toggle(key="investiq_memory_enabled").value
    with Session(engine) as session:
        assert not load_memory(session, "local").enabled
    engine.dispose()


def test_ui_forget_command_removes_old_chat_messages(ui_memory):
    app, url = ui_memory
    app.chat_input[0].set_value("¿Qué es beta?").run(timeout=30)

    app.chat_input[0].set_value("Olvida el contexto").run(timeout=30)

    assert not app.exception
    assert len(app.chat_message) == 1
    assert "olvidé" in app.chat_message[0].markdown[0].value
    engine = make_engine(url)
    with Session(engine) as session:
        assert load_memory(session, "local").state.last_decision is None
    engine.dispose()
