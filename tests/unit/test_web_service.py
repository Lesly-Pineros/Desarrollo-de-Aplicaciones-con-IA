import pytest
from sqlmodel import Session

from investiq.data.database import create_db, make_engine, seed_instruments
from investiq.data.models import UserPreference
from investiq.domain import AssistantResponse, ConversationState, RouterDecision
from investiq.memory import load_memory, save_memory
from investiq.settings import Settings
from investiq.web.service import InvalidRequest, MAX_VISIBLE_MESSAGES, WebService
from investiq.web.sessions import BrowserSession


@pytest.fixture
def service(tmp_path):
    settings = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'web.db'}",
                        nvidia_api_key=None, twelve_data_api_key=None, marketaux_api_key=None)
    engine = create_db(make_engine(settings.database_url))
    with Session(engine) as db:
        seed_instruments(db)
    yield WebService(engine, settings)
    engine.dispose()


def test_bootstrap_restores_only_sanitized_memory_without_initial_chat(service):
    with Session(service.engine) as db:
        save_memory(db, "local", ConversationState(
            last_decision=RouterDecision(intent="education", education_topic="volatilidad")))
    browser = BrowserSession("temporary")
    result = service.bootstrap(browser)
    assert len(result["instruments"]) == 20
    assert result["messages"] == []
    assert result["mode"] == "local"
    assert "volatilidad" in result["memory"]["summary"]
    assert browser.state.history == []


def test_chat_uses_existing_agent_and_keeps_raw_turns_temporary(service):
    browser = BrowserSession("temporary")
    result = service.chat(browser, {"message": "volatilidad"})
    assert result["response"]["intent"] == "education"
    assert "No es asesoría financiera" in result["response"]["answer"]
    assert browser.messages[0] == {"role": "user", "content": "volatilidad"}
    assert browser.messages[1]["role"] == "assistant"
    second = BrowserSession("other-browser")
    assert service.bootstrap(second)["messages"] == []
    assert second.state.history == []


@pytest.mark.parametrize("payload", [
    {}, {"message": ""}, {"message": "  "}, {"message": 12}, {"message": True},
    {"message": "\ud800"},
    {"message": "x" * 2001}, {"message": "hola", "secret": "extra"},
])
def test_invalid_chat_never_changes_browser_state(service, payload):
    browser = BrowserSession("temporary")
    with pytest.raises(InvalidRequest):
        service.chat(browser, payload)
    assert browser.messages == []
    assert browser.state is None


def test_reset_and_forget_keep_explicit_preferences(service):
    browser = BrowserSession("temporary")
    with Session(service.engine) as db:
        db.add(UserPreference(email="local", volatility_target="baja"))
        db.commit()
    service.chat(browser, {"message": "volatilidad"})
    reset = service.reset(browser, {})
    assert reset["messages"] == []
    assert browser.messages == []
    assert browser.state.last_decision is None
    service.chat(browser, {"message": "beta"})
    forgotten = service.memory(browser, {"forget": True})
    assert forgotten["messages"] == []
    assert browser.state.history == []
    with Session(service.engine) as db:
        assert db.get(UserPreference, "local").volatility_target == "baja"
        assert load_memory(db, "local").state.last_decision is None


def test_disabled_memory_does_not_remember_new_turns(service):
    browser = BrowserSession("temporary")
    disabled = service.memory(browser, {"enabled": False})
    assert disabled["memory"]["enabled"] is False
    service.chat(browser, {"message": "volatilidad"})
    assert browser.messages
    with Session(service.engine) as db:
        saved = load_memory(db, "local")
        assert saved.enabled is False
        assert saved.state.last_decision is None
    assert service.memory(browser, {"enabled": True})["memory"]["enabled"] is True


@pytest.mark.parametrize("payload", [{}, {"enabled": "false"}, {"enabled": 0},
                                    {"forget": 1}, {"forget": False},
                                    {"forget": True, "enabled": False}])
def test_memory_operations_are_explicit_booleans(service, payload):
    with pytest.raises(InvalidRequest):
        service.memory(BrowserSession("temporary"), payload)


def test_visible_history_is_bounded_and_can_be_cleared_by_agent(service, monkeypatch):
    browser = BrowserSession("temporary")
    browser.messages = [{"role": "assistant", "content": "anterior"}] * MAX_VISIBLE_MESSAGES
    monkeypatch.setattr("investiq.web.service.answer_turn", lambda *args, **kwargs:
                        AssistantResponse(answer="Respuesta. No es asesoría financiera.", intent="unknown"))
    service.chat(browser, {"message": "hola"})
    assert len(browser.messages) == MAX_VISIBLE_MESSAGES
    monkeypatch.setattr("investiq.web.service.answer_turn", lambda *args, **kwargs:
                        AssistantResponse(answer="Contexto olvidado. No es asesoría financiera.",
                                          intent="unknown", clear_history=True))
    result = service.chat(browser, {"message": "olvida nuestra conversación"})
    assert result["response"]["clear_history"] is True
    assert len(browser.messages) == 1
    assert browser.messages[0]["role"] == "assistant"


def test_failure_keeps_prior_temporary_state(service, monkeypatch):
    browser = BrowserSession("temporary", state=ConversationState(explanation_level="basic"))

    def fail(*args, **kwargs):
        kwargs["state"].explanation_level = "advanced"
        raise RuntimeError("provider failure")

    monkeypatch.setattr("investiq.web.service.answer_turn", fail)
    with pytest.raises(RuntimeError):
        service.chat(browser, {"message": "hola"})
    assert browser.state.explanation_level == "basic"
    assert browser.messages == []


@pytest.mark.parametrize("operation", ["forget", "reset", "conversation_command"])
def test_forgotten_context_is_not_restored_by_another_open_browser(service, operation):
    first = BrowserSession("first-browser")
    service.chat(first, {"message": "volatilidad"})
    other = BrowserSession("other-browser")
    service.bootstrap(other)
    service.chat(other, {"message": "un ejemplo"})
    assert other.state.last_decision.education_topic == "volatilidad"

    if operation == "forget":
        service.memory(first, {"forget": True})
    elif operation == "reset":
        service.reset(first, {})
    else:
        service.chat(first, {"message": "olvida lo conversado"})

    service.chat(other, {"message": "hola"})

    assert other.state.last_decision is None
    assert len(other.messages) == 2
    assert other.messages[0]["content"] == "hola"
    with Session(service.engine) as db:
        assert load_memory(db, "local").state.last_decision is None
