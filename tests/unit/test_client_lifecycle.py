import json

import pytest
from sqlmodel import Session, select

from investiq.conversation import answer_turn
from investiq.data.database import create_db, make_engine
from investiq.data.models import ConversationMemory, QueryLog, ResponseTrace
from investiq.domain import ConversationState, Narration, RouterDecision
from investiq.llm import LLMUnavailable
from investiq.settings import Settings


@pytest.fixture
def chat(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'client-lifecycle.db'}"))
    settings = Settings(_env_file=None, nvidia_api_key="test-key", sec_user_agent="")
    with Session(engine) as session:
        yield session, settings, ConversationState()
    engine.dispose()


def test_a_failed_client_factory_is_attempted_once_and_logged_safely(chat, monkeypatch):
    calls = []

    def failing_factory(settings):
        calls.append(True)
        error = LLMUnavailable("must-not-appear-in-ui-or-storage")
        error.provider_failure_category = "timeout"
        raise error

    monkeypatch.setattr("investiq.conversation.ChatNVIDIAClient", failing_factory)
    monkeypatch.setattr("investiq.orchestration.ChatNVIDIAClient", failing_factory)
    session, settings, state = chat
    response = answer_turn(session, "local", "¿Qué es beta?", settings, state=state)

    assert len(calls) == 1
    assert response.intent == "education"
    assert "No es asesoría financiera" in response.answer
    assert "must-not-appear" not in response.answer
    trace = session.exec(select(ResponseTrace)).one()
    assert trace.fallback_reason == "provider_timeout"
    assert trace.narration == "unavailable"
    assert len(session.exec(select(QueryLog)).all()) == 1
    assert "must-not-appear" not in session.get(ConversationMemory, "local").state_json


@pytest.mark.parametrize("query", ["Hola", "soy principiante", "qué recuerdas de mí"])
def test_nonfinancial_commands_do_not_construct_a_model(chat, monkeypatch, query):
    def unexpected_factory(settings):
        raise AssertionError("A model is not needed for this command")

    monkeypatch.setattr("investiq.conversation.ChatNVIDIAClient", unexpected_factory)
    monkeypatch.setattr("investiq.orchestration.ChatNVIDIAClient", unexpected_factory)
    session, settings, state = chat
    response = answer_turn(session, "local", query, settings, state=state)
    assert response.tools_used == []
    assert len(session.exec(select(QueryLog)).all()) == 1


def test_a_supplied_client_is_reused_for_routing_and_narration(chat, monkeypatch):
    class Client:
        def __init__(self):
            self.routing_calls = self.narration_calls = 0

        def classify(self, query):
            self.routing_calls += 1
            assert json.loads(query)["current_message"] == "¿Qué es beta?"
            return RouterDecision(intent="education", education_topic="beta")

        def narrate(self, *args):
            self.narration_calls += 1
            return Narration(answer="Beta relaciona movimientos históricos con un mercado de referencia.")

    def unexpected_factory(settings):
        raise AssertionError("The caller already supplied its client")

    monkeypatch.setattr("investiq.conversation.ChatNVIDIAClient", unexpected_factory)
    monkeypatch.setattr("investiq.orchestration.ChatNVIDIAClient", unexpected_factory)
    session, settings, state = chat
    client = Client()
    response = answer_turn(session, "local", "¿Qué es beta?", settings, state=state, client=client)
    assert client.routing_calls == client.narration_calls == 1
    assert response.diagnostics.narration == "used"
    assert len(session.exec(select(QueryLog)).all()) == 1
