"""Offline conversation coverage for index definitions and their evidence."""

import pytest
from sqlmodel import Session

from investiq.conversation import answer_turn
from investiq.data.database import create_db, make_engine
from investiq.data.models import UserPreference
from investiq.domain import ConversationState, Narration, QuoteResult, RouterDecision, SourceReference
from investiq.education import EDUCATION_CATALOGUE
from investiq.language import canonical_education_topic, is_educational_question
from investiq.memory import load_memory
from investiq.responses import DISCLAIMER
from investiq.routing import fallback_route, route_query
from investiq.settings import Settings
from investiq.tools import education_tool

OFFICIAL_SOURCE = "https://www.spglobal.com/spdji/en/indices/equity/sp-500/"


@pytest.fixture
def index_chat(tmp_path, monkeypatch):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'index-education.db'}"))
    settings = Settings(_env_file=None, nvidia_api_key=None, twelve_data_api_key=None,
                        marketaux_api_key=None, sec_user_agent="")

    monkeypatch.setattr("investiq.handlers.market_quote_tool", lambda session, symbol, settings: QuoteResult(
        symbol=symbol, price=100, provider="fixture", delayed=True,
        source=SourceReference(source_id=f"quote:{symbol}", title=f"Fixture {symbol}",
                               url="local://fixture", provider="fixture"),
    ))

    def unexpected_provider(*args, **kwargs):
        pytest.fail("An index definition must not request news or filings")

    for tool in ("news_tool", "sec_docs_tool"):
        monkeypatch.setattr(f"investiq.handlers.{tool}", unexpected_provider)
    with Session(engine) as session:
        yield session, settings, ConversationState()
    engine.dispose()


def ask(index_chat, query, *, restore=False, client=None):
    session, settings, state = index_chat
    response = answer_turn(session, "local", query, settings,
                           state=None if restore else state, client=client)
    assert DISCLAIMER in response.answer
    assert session.get(UserPreference, "local") is None
    return response


@pytest.mark.parametrize("query", [
    "que es el sp500", "¿Qué es el S&P 500?", "Qué significa SP 500",
    "Explícame el S&P500", "Quiero entender el sp500", "No entiendo el s & p 500",
    "¿Cómo funciona Standard & Poor's 500?", "Qué es Standard and Poor’s 500",
    "sp500", "SP 500", "s&p500", "S&P 500",
])
def test_index_variants_answer_with_official_source_without_prices(index_chat, query):
    response = ask(index_chat, query)

    assert response.intent == "education" and response.status == "ok"
    assert "S&P 500" in response.answer and "índice" in response.answer
    assert "500 empresas" in response.answer and "Estados Unidos" in response.answer
    assert [source.url for source in response.sources] == [OFFICIAL_SOURCE]
    assert response.tools_used == ["knowledge_search"]
    assert "SPY" not in response.answer


@pytest.mark.parametrize("query", ["sp5000", "sp500abc", "xsp500", "500", "S&P 5000"])
def test_partial_names_and_bare_numbers_do_not_match_the_index(query):
    assert canonical_education_topic(query) is None
    assert education_tool(query) is None


@pytest.mark.parametrize("query", [
    "¿Qué es SPDR S&P 500 ETF?", "Qué es el ETF SPY", "¿Qué es SPY?",
])
def test_named_fund_remains_instrument_info(query):
    decision = fallback_route(query)
    assert decision.intent == "instrument_info" and decision.symbol == "SPY"
    assert not is_educational_question(query)


@pytest.mark.parametrize("query,topic", [
    ("qué es la volatilidad del sp500", "volatilidad"),
    ("qué es un ETF que sigue el S&P500", "etf"),
    ("Hablando del S&P 500, ¿qué es beta?", "beta"),
    ("Hablando de beta, ¿qué es el sp500?", "S&P 500"),
    ("Explícame el índice S&P500 frente al ETF SPY", "S&P 500"),
    ("Qué es un ETF como SPDR S&P 500 ETF", "etf"),
])
def test_educational_subject_outranks_incidental_index_context(index_chat, query, topic):
    response = ask(index_chat, query)
    assert response.intent == "education"
    assert canonical_education_topic(query) == topic
    assert topic.casefold() in response.answer.casefold()
    assert response.sources[0].url == EDUCATION_CATALOGUE[topic].source.url


@pytest.mark.parametrize("query,symbol", [
    ("qué es el SPY del S&P 500", "SPY"),
    ("qué es AAPL del S&P 500", "AAPL"),
    ("qué es Apple en el S&P 500", "AAPL"),
])
def test_index_in_the_context_does_not_override_named_instrument_subject(index_chat, query, symbol):
    response = ask(index_chat, query)
    assert response.intent == "instrument_info"
    assert response.sources[0].url == f"local://catalogue/{symbol}"


def test_incomplete_question_accepts_index_name_after_memory_restore(index_chat):
    ask(index_chat, "quiero saber que es")
    assert load_memory(index_chat[0], "local").state.pending_field == "education_topic"

    response = ask(index_chat, "sp500", restore=True)

    assert response.intent == "education" and response.status == "ok"
    assert response.sources[0].url == OFFICIAL_SOURCE
    remembered = load_memory(index_chat[0], "local").state
    assert remembered.pending_field is None
    assert remembered.last_decision.education_topic == "S&P 500"
    assert remembered.history == []


@pytest.mark.parametrize("followup", ["más sencillo", "un ejemplo", "no entendí", "explícalo"])
def test_index_followups_retain_concept_and_source(index_chat, followup):
    first = ask(index_chat, "Qué es el sp500")
    response = ask(index_chat, followup, restore=True)

    assert response.intent == "education" and response.status == "ok"
    assert "S&P 500" in response.answer
    assert response.sources == first.sources
    if followup != "explícalo":
        assert response.answer != first.answer


def test_basic_learning_level_uses_an_example_with_the_same_source(index_chat):
    ask(index_chat, "soy principiante")
    response = ask(index_chat, "¿Qué es el S&P 500?")
    assert "Imagina" in response.answer
    assert response.sources[0].url == OFFICIAL_SOURCE


def test_index_education_preserves_pending_comparison_without_saving_preferences(index_chat):
    ask(index_chat, "compara AAPL y MSFT")
    response = ask(index_chat, "¿Qué es el sp500?")
    assert response.intent == "education"
    assert index_chat[2].pending_field == "comparison_preference"
    assert index_chat[2].pending_decision.comparison_symbols == ["AAPL", "MSFT"]


class MistakenIndexClient:
    def classify(self, query):
        return RouterDecision(intent="explanation", symbol="SPY")

    def teach(self, query, passages, context):
        chosen = next(passage for passage in passages if passage["section"] == "summary")
        assert "500 empresas" in chosen["text"]
        return {"paragraphs": [{"text": chosen["text"], "evidence": [{
            "passage_id": chosen["passage_id"], "quote": chosen["text"],
        }]}]}


def test_llm_cannot_substitute_fund_for_index_definition(index_chat):
    response = ask(index_chat, "que es el sp500", client=MistakenIndexClient())
    assert response.intent == "education" and "SPY" not in response.answer
    assert response.diagnostics.narration == "used"
    assert "{{result}}" not in response.answer
    assert response.sources[0].url == OFFICIAL_SOURCE


def test_index_price_does_not_fall_back_to_spy_or_call_market_data(index_chat):
    decision = route_query("precio del SP500", MistakenIndexClient())
    assert decision.intent == "explanation" and decision.symbol is None
    response = ask(index_chat, "precio del SP500")
    assert response.status == "degraded" and response.tools_used == []


@pytest.mark.parametrize("violation", ["number", "citation", "quote"])
def test_index_narration_falls_back_when_facts_or_citations_change(index_chat, violation):
    class Client(MistakenIndexClient):
        def teach(self, query, passages, context):
            chosen = passages[0]
            paragraph = {"text": chosen["text"], "evidence": [{
                "passage_id": chosen["passage_id"], "quote": chosen["text"],
            }]}
            if violation == "number":
                paragraph["text"] = "El S&P 500 incluye 5000 empresas líderes de Estados Unidos."
            elif violation == "citation":
                paragraph["evidence"][0]["passage_id"] = "not-retrieved"
            else:
                paragraph["evidence"][0]["quote"] = "Este texto no está en el documento recuperado."
            return {"paragraphs": [paragraph]}

    response = ask(index_chat, "qué es el sp500", client=Client())
    assert response.diagnostics.narration == "fallback"
    assert EDUCATION_CATALOGUE["S&P 500"].definition in response.answer
    assert response.answer.count(DISCLAIMER) == 1
    assert "5000" not in response.answer
    assert response.sources[0].url == OFFICIAL_SOURCE
