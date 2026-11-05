"""The user's screenshot reproduced as conversations, without a market provider."""

import pytest
from sqlmodel import Session

from investiq.conversation import answer_turn
from investiq.data.database import create_db, make_engine
from investiq.data.models import UserPreference
from investiq.domain import ConversationState, Narration, RouterDecision
from investiq.memory import load_memory
from investiq.responses import DISCLAIMER
from investiq.routing import fallback_route, route_query
from investiq.settings import Settings


@pytest.fixture
def chat(tmp_path, monkeypatch):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'web-dialogue.db'}"))
    settings = Settings(_env_file=None, nvidia_api_key=None, twelve_data_api_key=None,
                        marketaux_api_key=None, sec_user_agent="")

    def unexpected_provider(*args, **kwargs):
        pytest.fail("Definitions and capabilities must not request market data")

    for tool in ("market_quote_tool", "news_tool", "sec_docs_tool"):
        monkeypatch.setattr(f"investiq.handlers.{tool}", unexpected_provider)
    with Session(engine) as session:
        yield session, settings, ConversationState()
    engine.dispose()


def ask(chat, query, *, restore=False):
    session, settings, state = chat
    response = answer_turn(session, "local", query, settings, state=None if restore else state)
    assert DISCLAIMER in response.answer
    assert session.get(UserPreference, "local") is None
    return response


def test_screenshot_sequence_answers_each_question_instead_of_repeating_menu(chat):
    incomplete = ask(chat, "quiero saber que es")
    assert incomplete.answer.count("?") == 1
    assert "palabra o símbolo" in incomplete.answer

    concept = ask(chat, "volatilidad")
    assert concept.intent == "education" and concept.status == "ok"
    assert "recorrido" in concept.answer
    assert concept.sources[0].url == "local://glossary/volatilidad"
    assert chat[2].pending_field is None

    instrument = ask(chat, "que es el aapl")
    assert instrument.intent == "instrument_info" and instrument.status == "ok"
    assert "Apple" in instrument.answer and "símbolo bursátil" in instrument.answer
    assert instrument.sources[0].url == "local://catalogue/AAPL"
    assert instrument.tools_used == ["instrument_catalogue"]

    capabilities = ask(chat, "que mas puedes hacer")
    assert capabilities.intent == "unknown" and capabilities.status == "ok"
    assert "comparar" in capabilities.answer and "sobre la marcha" in capabilities.answer
    assert "No estoy seguro" not in capabilities.answer
    assert not capabilities.tools_used


@pytest.mark.parametrize("query,symbol,name", [
    ("¿Qué es AAPL?", "AAPL", "Apple"),
    ("que es el aapl", "AAPL", "Apple"),
    ("¿Qué significa AAPL?", "AAPL", "Apple"),
    ("Explícame Apple", "AAPL", "Apple"),
    ("¿Quién es Microsoft?", "MSFT", "Microsoft"),
    ("¿Qué es QQQ?", "QQQ", "Invesco QQQ ETF"),
    ("¿Qué es el ETF QQQ?", "QQQ", "Invesco QQQ ETF"),
    ("¿Qué es Invesco QQQ ETF?", "QQQ", "Invesco QQQ ETF"),
    ("Defíneme AAPL", "AAPL", "Apple"),
])
def test_instrument_definition_is_a_catalogue_lookup(chat, query, symbol, name):
    response = ask(chat, query)
    assert response.intent == "instrument_info"
    assert symbol in response.answer and name in response.answer
    assert response.sources[0].source_id == f"catalogue:{symbol}"
    assert "precio" not in response.answer.casefold()


@pytest.mark.parametrize("query", [
    "¿Qué más puedes hacer?", "Y qué más puedes hacer", "¿En qué me ayudas?",
    "¿En qué me puedes ayudar?", "¿Para qué sirve esto?",
])
def test_capabilities_accept_everyday_spanish(chat, query):
    response = ask(chat, query)
    assert response.status == "ok"
    assert "comparar" in response.answer
    assert not response.tools_used


def test_short_symbol_after_incomplete_question_defines_it_without_market_data(chat):
    ask(chat, "quiero saber que es")
    response = ask(chat, "AAPL")
    assert response.intent == "instrument_info"
    assert "Apple" in response.answer
    assert chat[2].pending_field is None


def test_short_symbol_after_reloaded_clarification_still_defines_it(chat):
    ask(chat, "qué significa")
    assert load_memory(chat[0], "local").state.pending_field == "education_topic"
    response = ask(chat, "MSFT", restore=True)
    assert response.intent == "instrument_info"
    assert "Microsoft" in response.answer


def test_instrument_definition_followup_keeps_definition_context(chat):
    ask(chat, "qué es AAPL")
    response = ask(chat, "¿Y MSFT?")
    assert response.intent == "instrument_info"
    assert "Microsoft" in response.answer
    assert load_memory(chat[0], "local").state.last_decision.symbol == "MSFT"


def test_instrument_question_can_interrupt_comparison_without_becoming_preference(chat):
    ask(chat, "compara AAPL y MSFT")
    assert chat[2].pending_field == "comparison_preference"
    response = ask(chat, "¿Qué es AAPL?")
    assert response.intent == "instrument_info"
    assert chat[2].pending_field == "comparison_preference"
    assert chat[2].pending_decision.comparison_symbols == ["AAPL", "MSFT"]


@pytest.mark.parametrize("query,intent", [
    ("Qué es la volatilidad de AAPL", "education"),
    ("Qué es beta y cómo se relaciona con AAPL", "education"),
    ("Qué es un ETF como QQQ", "education"),
    ("Explica el precio de AAPL", "explanation"),
    ("Compara AAPL y MSFT", "compare"),
    ("Busca similares a AAPL", "recommend_similar"),
])
def test_instrument_description_does_not_override_other_financial_requests(query, intent):
    assert fallback_route(query).intent == intent


def test_misclassified_llm_cannot_turn_ticker_definition_into_price_request():
    class Client:
        def classify(self, query):
            return RouterDecision(intent="explanation", symbol="AAPL")

    assert route_query("qué es AAPL", Client()).intent == "instrument_info"


def test_instrument_narration_preserves_factual_block_and_source(chat):
    class Client:
        def classify(self, query):
            return RouterDecision(intent="instrument_info", symbol="AAPL")

        def narrate(self, intent, query, facts, sources):
            assert intent == "instrument_info"
            assert "Apple" in facts["response_block"]
            return Narration(answer="Vamos paso a paso.\n\n{{result}}",
                             cited_source_ids=[source["source_id"] for source in sources])

    session, settings, state = chat
    response = answer_turn(session, "local", "qué es AAPL", settings, state=state, client=Client())
    assert response.diagnostics.narration == "used"
    assert "Apple" in response.answer and "{{result}}" not in response.answer
    assert response.sources[0].source_id == "catalogue:AAPL"
