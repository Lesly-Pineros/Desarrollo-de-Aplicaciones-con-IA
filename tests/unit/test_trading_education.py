"""Lessons and current-data limits requested for the financial teacher."""

import pytest
from sqlmodel import Session

from investiq.conversation import answer_turn
from investiq.data.database import create_db, make_engine
from investiq.data.models import UserPreference
from investiq.domain import ConversationState, RouterDecision
from investiq.knowledge import get_library
from investiq.memory import load_memory
from investiq.responses import DISCLAIMER
from investiq.routing import fallback_route, route_query
from investiq.sector_context import educational_part, is_current_sector_query
from investiq.settings import Settings

LONG_TERM = "¿Qué es mejor para obtener mayores rentabilidades a largo plazo: un ETF o acciones individuales?"
SECTORS = "¿Qué sectores lideran hoy?"


@pytest.fixture
def classroom(tmp_path, monkeypatch):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'trading-lessons.db'}"))
    settings = Settings(_env_file=None, nvidia_api_key=None, twelve_data_api_key=None,
                        marketaux_api_key=None, sec_user_agent="")

    def no_market_calls(*args, **kwargs):
        pytest.fail("Educational lessons and unavailable sector rankings must not request quotes")

    for name in ("market_quote_tool", "news_tool", "sec_docs_tool"):
        monkeypatch.setattr(f"investiq.handlers.{name}", no_market_calls)
    with Session(engine) as db:
        yield db, settings, ConversationState()
    engine.dispose()


def ask(classroom, query, *, restore=False):
    db, settings, state = classroom
    response = answer_turn(db, "local", query, settings, state=None if restore else state)
    assert DISCLAIMER in response.answer
    assert db.get(UserPreference, "local") is None
    return response


@pytest.mark.parametrize("query,expected", [
    ("¿Qué es un fondo de inversión?", "fondo"),
    ("¿Qué tipos de fondos de inversión existen?", "fondo"),
    ("¿Qué es una criptomoneda?", "cripto"),
    ("¿Qué es Bitcoin?", "Bitcoin"),
    ("¿Qué es Ethereum?", "Ethereum"),
    ("¿Qué es blockchain?", "registro"),
    ("¿Qué es una wallet?", "clave"),
    ("¿Qué es una stablecoin?", "referencia"),
    ("¿Qué es staking?", "staking"),
    ("¿Qué es un smart contract?", "programa"),
    ("¿Qué indicadores utiliza un trader?", "indicador"),
    ("¿Qué es el RSI?", "RSI"),
    ("¿Qué es MACD?", "MACD"),
    ("¿Qué es una SMA?", "media"),
    ("¿Qué es una EMA?", "media"),
    ("¿Qué mide el ATR?", "ATR"),
    ("¿Qué es ADX?", "ADX"),
    ("¿Qué son las bandas de Bollinger?", "Bollinger"),
    ("¿Qué es OBV?", "OBV"),
    ("¿Qué es CCI?", "CCI"),
    ("¿Qué es VWAP?", "VWAP"),
    ("¿Qué es el oscilador estocástico?", "estocástico"),
    ("¿Qué son soporte y resistencia?", "zona"),
    ("¿Cómo se lee una vela japonesa?", "vela"),
    ("¿Qué es backtesting?", "históric"),
    ("¿Qué es drawdown?", "caída"),
    ("¿Qué es el tamaño de posición?", "expos"),
    ("¿Qué es el margen operativo?", "operativ"),
    ("¿Qué es el current ratio?", "corriente"),
])
def test_new_lessons_use_the_real_reviewed_library(classroom, query, expected):
    response = ask(classroom, query)
    assert response.intent == "education"
    assert response.status == "ok"
    assert expected.casefold() in response.answer.casefold()
    assert response.sources and all(source.url.startswith("https://") for source in response.sources)
    assert "knowledge_search" in response.tools_used


@pytest.mark.parametrize("question", [
    LONG_TERM,
    "¿Los ETF dan más rentabilidad que las acciones?",
    "¿Es mejor invertir a largo plazo en ETF o acciones individuales?",
])
def test_long_term_question_has_no_guaranteed_winner_or_ticker_request(classroom, question):
    response = ask(classroom, question)
    assert response.intent == "education" and response.status == "ok"
    assert "no hay un ganador universal" in response.answer.casefold()
    assert "ETF" in response.answer and "acciones" in response.answer
    assert "entre dos y cuatro símbolos" not in response.answer
    assert response.sources


def test_technical_and_fundamental_indicators_are_distinguished(classroom):
    response = ask(classroom, "¿Qué diferencia hay entre indicadores técnicos y fundamentales?")
    assert response.intent == "education" and response.status == "ok"
    assert "fundamental estudia información" in response.answer
    assert "precios y volumen" in response.answer
    assert response.sources


def test_indicator_example_keeps_its_topic_after_restoring_memory(classroom):
    ask(classroom, "¿Qué es el RSI?")
    response = ask(classroom, "un ejemplo", restore=True)
    assert response.intent == "education" and response.status == "ok"
    assert get_library().get_by_topic("RSI").example in response.answer


def test_current_sector_question_asks_market_and_admits_missing_feed(classroom):
    response = ask(classroom, SECTORS)
    assert response.intent == "sector_performance" and response.status == "degraded"
    assert "¿De qué mercado" in response.answer
    assert "no tengo un ranking sectorial actual" in response.answer
    assert not response.sources and not response.tools_used
    assert classroom[2].pending_field == "sector_market"
    restored = load_memory(classroom[0], "local").state
    assert restored.pending_field == "sector_market"


@pytest.mark.parametrize("market", ["Estados Unidos", "Colombia", "España", "Europa", "global", "S&P500"])
def test_short_market_reply_is_restored_without_fabricating_leaders(classroom, market):
    ask(classroom, SECTORS)
    response = ask(classroom, market, restore=True)
    assert response.intent == "sector_performance" and response.status == "degraded"
    assert "ranking sectorial actual verificado" in response.answer
    assert not response.sources and not response.tools_used
    assert not any(character.isdigit() for character in response.answer)


def test_classifier_cannot_turn_current_sector_question_into_education():
    class Client:
        def classify(self, query):
            return RouterDecision(intent="education", education_topic="liderazgo sectorial")

    assert route_query(SECTORS, Client()).intent == "sector_performance"


def test_combined_message_answers_comparison_and_preserves_market_question(classroom):
    response = ask(classroom, LONG_TERM + SECTORS + "&#x20;")
    assert response.intent == "sector_performance" and response.status == "degraded"
    assert "no hay un ganador universal" in response.answer.casefold()
    assert "¿De qué mercado" in response.answer
    assert response.sources and response.answer.count(DISCLAIMER) == 1
    assert classroom[2].pending_field == "sector_market"
    assert educational_part(LONG_TERM + SECTORS) == LONG_TERM


@pytest.mark.parametrize("question", ["¿Qué es la rotación sectorial?", "¿Qué significa liderazgo sectorial?"])
def test_sector_definitions_remain_educational(question):
    assert not is_current_sector_query(question)
    assert fallback_route(question).intent == "education"


def test_sector_limit_does_not_construct_or_call_a_model(classroom, monkeypatch):
    def unexpected_model(*args, **kwargs):
        pytest.fail("A model cannot provide missing current sector data")

    monkeypatch.setattr("investiq.conversation.ChatNVIDIAClient", unexpected_model)
    monkeypatch.setattr("investiq.orchestration.ChatNVIDIAClient", unexpected_model)
    classroom[1].nvidia_api_key = "configured-only-for-this-test"
    assert ask(classroom, SECTORS).status == "degraded"
