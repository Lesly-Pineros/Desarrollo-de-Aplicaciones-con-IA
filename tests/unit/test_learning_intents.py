"""Learning and everyday Spanish must not silently change financial intent."""

import pytest
from sqlmodel import Session

from investiq.conversation import answer_turn
from investiq.data.database import create_db, make_engine
from investiq.data.models import UserPreference
from investiq.domain import ConversationState, NewsCollection, QuoteResult
from investiq.instruments import mentioned_symbols
from investiq.preferences import read_preference_change
from investiq.routing import fallback_route
from investiq.settings import Settings


@pytest.fixture
def chat(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'learning.db'}"))
    settings = Settings(_env_file=None, nvidia_api_key=None, twelve_data_api_key=None,
                        marketaux_api_key=None, sec_user_agent="")
    with Session(engine) as session:
        yield session, settings, ConversationState()
    engine.dispose()


def ask(chat, query):
    session, settings, state = chat
    response = answer_turn(session, "local", query, settings, state=state)
    assert "No es asesoría financiera." in response.answer
    return response


@pytest.fixture
def financial_calls(monkeypatch):
    calls = []

    def quote(session, symbol, settings):
        calls.append(("quote", [symbol]))
        return QuoteResult(symbol=symbol, price=None, provider="fixture offline", delayed=True,
                           error="Sin datos en esta prueba.")

    def compare(session, user_id, symbols, **kwargs):
        calls.append(("compare", list(symbols)))
        return []

    monkeypatch.setattr("investiq.handlers.market_quote_tool", quote)
    monkeypatch.setattr("investiq.handlers.news_tool", lambda *args: NewsCollection(articles=[]))
    monkeypatch.setattr("investiq.handlers.sec_docs_tool", lambda *args: ([], "Fixture sin filings."))
    monkeypatch.setattr("investiq.handlers.compare_instruments", compare)
    monkeypatch.setattr("investiq.handlers.local_model_source", lambda *args: None)
    monkeypatch.setattr("investiq.handlers.feature_sources", lambda *args: [])
    return calls


@pytest.mark.parametrize("query", [
    "Me gustaría entender la volatilidad alta",
    "Me interesa aprender sobre beta",
    "Quiero comprender mejor la correlación",
    "Quiero aprender un poco sobre ETF",
    "No entiendo la volatilidad baja",
    "Quiero entender esto de la volatilidad alta",
    "Me gustaría aprender acerca de beta",
    "Me interesa entender el riesgo alto",
])
def test_learning_requests_teach_without_saving_preferences(chat, query):
    assert fallback_route(query).intent == "education"
    assert not read_preference_change(query, expected=True).requested
    response = ask(chat, query)
    assert response.intent == "education"
    assert response.status == "ok"
    assert chat[0].get(UserPreference, "local") is None
    assert chat[2].pending_field is None


@pytest.mark.parametrize("query", [
    "Me gustaría entender la volatilidad alta",
    "Me interesa aprender sobre beta",
])
def test_learning_interrupts_and_resumes_a_pending_comparison(chat, financial_calls, query):
    ask(chat, "Compara AAPL y MSFT")
    assert chat[2].pending_field == "comparison_preference"
    response = ask(chat, query)
    assert response.intent == "education"
    assert chat[0].get(UserPreference, "local") is None
    assert chat[2].pending_field == "comparison_preference"
    assert chat[2].pending_decision.comparison_symbols == ["AAPL", "MSFT"]
    assert not financial_calls

    resumed = ask(chat, "sector salud")
    assert resumed.intent == "compare"
    assert financial_calls == [("compare", ["AAPL", "MSFT"])]
    assert chat[2].pending_field is None
    saved = chat[0].get(UserPreference, "local")
    assert saved.sector == "Health Care"
    assert saved.volatility_target is None
    assert saved.beta_target is None


def test_a_real_preference_declaration_still_changes_preferences(chat):
    ask(chat, "Prefiero volatilidad baja")
    assert chat[0].get(UserPreference, "local").volatility_target == "baja"


@pytest.mark.parametrize("query", [
    "Mi meta es aprender",
    "Una meta importante es mejorar",
    "Mi META es aprender sobre inversiones",
])
def test_goal_word_does_not_call_financial_tools(chat, financial_calls, query):
    assert mentioned_symbols(query) == []
    response = ask(chat, query)
    assert response.intent in {"unknown", "education"}
    assert set(response.tools_used).issubset({"knowledge_search"})
    assert not financial_calls


@pytest.mark.parametrize("query", [
    "META", "mEtA", "meta", "precio META", "precio meta", "consulta Meta",
    "cuéntame sobre Meta", "Meta Platforms", "compara META AAPL", "compara meta aapl",
])
def test_explicit_meta_queries_and_company_names_remain_available(chat, financial_calls, query):
    chat[2].preferences_offered = True
    response = ask(chat, query)
    if query.casefold().startswith("compara"):
        assert response.intent == "compare"
        assert financial_calls == [("compare", ["META", "AAPL"])]
    else:
        assert response.intent == "explanation"
        assert financial_calls == [("quote", ["META"])]


def test_other_lowercase_symbols_still_resolve():
    assert mentioned_symbols("compara aapl, msft y nvda") == ["AAPL", "MSFT", "NVDA"]
