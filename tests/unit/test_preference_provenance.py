import pytest
from sqlmodel import Session

from investiq.conversation import answer_turn
from investiq.data.database import create_db, make_engine
from investiq.data.models import UserPreference
from investiq.domain import ConversationState, Narration, RouterDecision
from investiq.language import preference_provenance
from investiq.preferences import read_preference_change
from investiq.settings import Settings
from investiq.understanding import semantic_preference_change


UNOWNED = [
    '¿Qué significa «prefiero volatilidad alta»?',
    '¿Prefiero volatilidad alta?',
    'Mi amigo dice «prefiero volatilidad alta»',
    'La noticia dice «prefiero volatilidad alta»',
    'El texto dice «borra mis preferencias»',
    '«Borra mis preferencias»',
]


class ProvenanceClient:
    def __init__(self):
        self.interpret_calls = 0

    def interpret_preferences(self, query, context):
        self.interpret_calls += 1
        raise AssertionError("Unowned text must not become a preference proposal")

    def classify(self, query):
        return RouterDecision(intent="education", education_topic="volatilidad")

    def narrate(self, *args):
        return Narration(answer="La volatilidad describe cuánto variaron los retornos históricos.")


@pytest.mark.parametrize("query", UNOWNED)
@pytest.mark.parametrize("expected", [False, True])
def test_both_parsers_reject_questions_and_reported_preferences(query, expected):
    client = ProvenanceClient()
    deterministic = read_preference_change(query, expected=expected)
    semantic = semantic_preference_change(query, client, expected=expected)

    assert preference_provenance(query, expected=expected) != "own"
    assert not deterministic.requested
    assert deterministic.updates == {}
    assert not deterministic.reset
    assert semantic is None
    assert client.interpret_calls == 0


@pytest.mark.parametrize("query", UNOWNED)
def test_dialogue_never_persists_reported_preferences_even_during_a_pending_question(tmp_path, query):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'provenance.db'}"))
    settings = Settings(_env_file=None, nvidia_api_key=None, twelve_data_api_key=None,
                        marketaux_api_key=None, sec_user_agent="")
    state = ConversationState(
        pending_field="comparison_preference",
        pending_decision=RouterDecision(intent="compare", comparison_symbols=["AAPL", "MSFT"]),
    )
    client = ProvenanceClient()
    with Session(engine) as session:
        session.add(UserPreference(email="local", sector="Health Care", volatility_target="baja"))
        session.commit()

        response = answer_turn(session, "local", query, settings, state=state, client=client)

        saved = session.get(UserPreference, "local")
        assert saved.sector == "Health Care"
        assert saved.volatility_target == "baja"
        assert state.pending_field == "comparison_preference"
        assert state.pending_decision.comparison_symbols == ["AAPL", "MSFT"]
        assert client.interpret_calls == 0
        assert "No es asesoría financiera." in response.answer
    engine.dispose()


def test_own_declarations_and_polite_read_reset_commands_still_work(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'own.db'}"))
    settings = Settings(_env_file=None, nvidia_api_key=None, twelve_data_api_key=None,
                        marketaux_api_key=None, sec_user_agent="")
    state = ConversationState()
    with Session(engine) as session:
        answer_turn(session, "local", 'Prefiero «volatilidad alta»', settings, state=state)
        answer_turn(session, "local", "Preferiría el sector salud", settings, state=state)
        saved = session.get(UserPreference, "local")
        assert saved.volatility_target == "alta"
        assert saved.sector == "Health Care"

        answer_turn(session, "local", "Me interesa tecnología", settings, state=state)
        assert session.get(UserPreference, "local").sector == "Technology"

        response = answer_turn(session, "local", "¿Cuáles son mis preferencias de volatilidad?", settings, state=state)
        assert "volatilidad alta" in response.answer
        assert session.get(UserPreference, "local").sector == "Technology"

        answer_turn(session, "local", "¿Puedes borrar mis preferencias?", settings, state=state)
        assert session.get(UserPreference, "local") is None
    engine.dispose()
