import pytest
from sqlmodel import Session

from investiq.conversation import answer_turn
from investiq.data.database import create_db, make_engine
from investiq.data.models import UserPreference
from investiq.domain import ConversationState
from investiq.memory import load_memory
from investiq.settings import Settings


@pytest.fixture
def dialogue(tmp_path, monkeypatch):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'repairs.db'}"))
    settings = Settings(_env_file=None, nvidia_api_key=None, twelve_data_api_key=None,
                        marketaux_api_key=None, sec_user_agent="")
    calls = []

    def compare(session, user_id, symbols, **kwargs):
        calls.append(list(symbols))
        return [{"symbol": symbol, "score": 80.0, "volatility": .2, "beta": 1.1,
                 "sector": "Technology"} for symbol in symbols]

    monkeypatch.setattr("investiq.handlers.compare_instruments", compare)
    monkeypatch.setattr("investiq.handlers.local_model_source", lambda session: None)
    with Session(engine) as session:
        yield session, settings, ConversationState(), calls
    engine.dispose()


def ask(dialogue, query, *, restore=False):
    session, settings, state, _ = dialogue
    response = answer_turn(session, "local", query, settings, state=None if restore else state)
    assert "No es asesoría financiera." in response.answer
    return response


def test_complete_comparison_replaces_pending_symbols(dialogue):
    session, _, state, calls = dialogue
    session.add(UserPreference(email="local", volatility_target="baja"))
    session.commit()

    ask(dialogue, "Compara AAPL")
    assert state.pending_field == "comparison_symbols"
    ask(dialogue, "Compara NVDA y MSFT")

    assert calls == [["NVDA", "MSFT"]]
    assert state.pending_field is None


def test_short_symbol_reply_completes_the_previous_comparison(dialogue):
    session, _, _, calls = dialogue
    session.add(UserPreference(email="local", sector="Technology"))
    session.commit()

    ask(dialogue, "Compara AAPL")
    ask(dialogue, "MSFT")

    assert calls == [["AAPL", "MSFT"]]


def test_concept_question_with_incidental_price_preserves_pending_comparison(dialogue):
    _, _, state, calls = dialogue
    ask(dialogue, "Compara AAPL y MSFT")
    response = ask(dialogue, "¿Qué es volatilidad y cómo se relaciona con el movimiento del precio?")

    assert response.intent == "education"
    assert "volatilidad" in response.answer.casefold()
    assert state.pending_field == "comparison_preference"
    assert calls == []

    ask(dialogue, "baja")
    assert calls == [["AAPL", "MSFT"]]


@pytest.mark.parametrize("reply,value", [("1.2", 1.2), ("+1.2", 1.2), ("1,2", 1.2), ("0", 0)])
def test_invalid_beta_can_be_answered_with_only_a_valid_number(dialogue, reply, value):
    session, _, state, _ = dialogue
    ask(dialogue, "Prefiero beta 99")
    assert state.pending_field == "preference_beta"

    ask(dialogue, reply)

    assert session.get(UserPreference, "local").beta_target == value
    assert state.pending_field is None


def test_beta_clarification_and_original_comparison_survive_restart(dialogue):
    session, _, state, calls = dialogue
    ask(dialogue, "Compara AAPL y MSFT")
    ask(dialogue, "Prefiero beta 99")
    assert state.pending_field == "preference_beta"
    assert load_memory(session, "local").state.pending_field == "preference_beta"

    response = ask(dialogue, "1.2", restore=True)

    assert session.get(UserPreference, "local").beta_target == 1.2
    assert response.intent == "compare"
    assert calls == [["AAPL", "MSFT"]]
    assert load_memory(session, "local").state.pending_field is None


def test_still_invalid_beta_is_not_written_and_keeps_the_typed_clarification(dialogue):
    session, _, state, _ = dialogue
    ask(dialogue, "Prefiero beta 99")
    ask(dialogue, "10")

    assert session.get(UserPreference, "local") is None
    assert state.pending_field == "preference_beta"

    ask(dialogue, "omitir")
    assert state.pending_field is None
    assert session.get(UserPreference, "local") is None
