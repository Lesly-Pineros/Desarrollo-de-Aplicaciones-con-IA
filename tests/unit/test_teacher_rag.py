"""End-to-end educational turns over the actual local financial library."""

import pytest
from sqlmodel import Session

from investiq.conversation import answer_turn
from investiq.data.database import create_db, make_engine
from investiq.data.models import UserPreference
from investiq.domain import ConversationState, RouterDecision
from investiq.knowledge import get_library
from investiq.memory import load_memory
from investiq.responses import DISCLAIMER
from investiq.routing import fallback_route
from investiq.settings import Settings


@pytest.fixture
def classroom(tmp_path, monkeypatch):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'classroom.db'}"))
    settings = Settings(_env_file=None, nvidia_api_key=None, twelve_data_api_key=None,
                        marketaux_api_key=None, sec_user_agent="")

    def no_market_lookup(*args, **kwargs):
        pytest.fail("A lesson must not request current prices, news or filings")

    for tool in ("market_quote_tool", "news_tool", "sec_docs_tool"):
        monkeypatch.setattr(f"investiq.handlers.{tool}", no_market_lookup)
    with Session(engine) as session:
        yield session, settings, ConversationState()
    engine.dispose()


def ask(classroom, question, *, restore=False, client=None):
    session, settings, state = classroom
    response = answer_turn(session, "local", question, settings,
                           state=None if restore else state, client=client)
    assert DISCLAIMER in response.answer
    assert session.get(UserPreference, "local") is None
    return response


@pytest.mark.parametrize("question,expected", [
    ("¿Qué es una acción?", "acción"),
    ("¿Qué es un ETF?", "ETF"),
    ("¿Cómo funciona la bolsa de valores?", "bolsa"),
    ("¿Qué son los dividendos?", "dividendo"),
    ("¿Qué significa diversificar?", "diversifica"),
    ("¿Cómo funciona una orden límite?", "límite"),
    ("¿Qué es el valor liquidativo?", "liquidativo"),
    ("¿Qué es la capitalización bursátil?", "capitalización"),
    ("¿Qué costes tiene un ETF?", "cost"),
    ("¿Qué es el sp500?", "500"),
])
def test_teacher_answers_financial_basics_with_official_evidence(classroom, question, expected):
    response = ask(classroom, question)
    assert response.intent == "education"
    assert response.status == "ok"
    assert expected.casefold() in response.answer.casefold()
    assert "knowledge_search" in response.tools_used
    assert response.sources and all(source.url.startswith("https://") for source in response.sources)


def test_broker_question_has_examples_and_jurisdiction_limits(classroom):
    response = ask(classroom, "¿Qué brokers existen para invertir?")
    assert response.intent == "education"
    assert response.sources and "knowledge_search" in response.tools_used
    assert any(name in response.answer for name in ("Interactive Brokers", "Fidelity", "Schwab"))
    assert any(word in response.answer.casefold() for word in ("país", "residencia", "jurisdicción"))
    assert "el mejor" not in response.answer.casefold()


def test_concept_comparison_does_not_ask_for_stock_tickers(classroom):
    response = ask(classroom, "¿En qué se diferencia un ETF de una acción?")
    assert response.intent == "education"
    assert "ETF" in response.answer and "acción" in response.answer
    assert "entre dos y cuatro símbolos" not in response.answer
    assert response.sources


def test_new_topic_and_example_survive_a_memory_restore(classroom):
    first = ask(classroom, "¿Qué son los dividendos?")
    remembered = load_memory(classroom[0], "local").state.last_decision
    assert remembered.intent == "education"
    assert get_library().get_by_topic(remembered.education_topic) is not None
    second = ask(classroom, "un ejemplo", restore=True)
    assert second.intent == "education"
    assert get_library().get_by_topic(remembered.education_topic).example in second.answer
    assert second.sources == first.sources


def test_company_explanation_uses_issuer_information_without_a_quote(classroom):
    response = ask(classroom, "¿A qué se dedica Apple?")
    assert response.intent in {"education", "instrument_info"}
    assert "Apple" in response.answer
    assert response.sources
    assert all(tool not in response.tools_used for tool in ("market_quote", "news", "sec_docs"))


def test_an_uncovered_question_is_acknowledged_without_inventing_evidence(classroom):
    response = ask(classroom, "¿Qué es la interferencia cuántica de galaxias?")
    assert response.status == "degraded"
    assert not response.sources


def test_deictic_risk_question_keeps_the_specific_fund_lesson(classroom):
    ask(classroom, "¿Qué es un ETF apalancado?")
    document = get_library().get_by_topic(classroom[2].last_decision.education_topic)
    response = ask(classroom, "¿Y sus riesgos?", restore=True)
    assert response.status == "ok"
    assert document.cautions in response.answer
    assert response.sources


def test_request_for_detail_expands_the_lesson_without_a_model(classroom):
    first = ask(classroom, "¿Qué es un ETF apalancado?")
    response = ask(classroom, "más detalle", restore=True)
    assert response.intent == "education" and response.status == "ok"
    assert response.answer != first.answer
    assert len(response.answer) > len(first.answer)


def test_deepening_makes_the_curated_example_available_to_generation():
    passages = get_library().search("más detalle", topic="ETF apalancado", limit=4)
    assert any(passage.section == "example" for passage in passages)
    assert any(passage.section == "cautions" for passage in passages)


def test_broker_country_and_current_fees_do_not_invent_availability(classroom):
    ask(classroom, "¿Qué brókers existen para invertir?")
    country = ask(classroom, "¿Qué puedo usar en Colombia?")
    assert country.intent == "education" and country.status == "degraded"
    assert country.sources
    assert "no permite confirmar" in country.answer
    fees = ask(classroom, "¿Y cuánto cobra hoy?")
    assert fees.intent == "education" and fees.status == "degraded"
    assert "no permite confirmar" in fees.answer
    assert not any(character.isdigit() for character in fees.answer)


@pytest.mark.parametrize("question,intent", [
    ("precio de AAPL", "explanation"),
    ("¿Por qué subió AAPL hoy?", "explanation"),
    ("compara AAPL y MSFT", "compare"),
    ("busca similares a AAPL", "recommend_similar"),
    ("busca instrumentos con volatilidad baja", "recommend_volatility"),
])
def test_market_routes_keep_their_deterministic_tools(question, intent):
    assert fallback_route(question).intent == intent


def test_education_uses_retrieved_passages_instead_of_the_market_narrator(classroom):
    from investiq.tutor.models import TutorEvidence, TutorNarration, TutorParagraph

    class Teacher:
        def classify(self, query):
            return RouterDecision(intent="education", education_topic="dividendos")

        def teach(self, query, passages, context):
            assert 1 <= len(passages) <= 4
            assert all("passage_id" in passage and "text" in passage for passage in passages)
            assert context["level"] in {"basic", "standard", "advanced"}
            chosen = next(passage for passage in passages if passage["section"] == "summary")
            return TutorNarration(paragraphs=[TutorParagraph(
                text=chosen["text"], evidence=[TutorEvidence(
                    passage_id=chosen["passage_id"], quote=chosen["text"],
                )],
            )])

        def narrate(self, *args, **kwargs):
            pytest.fail("A lesson has its own grounded generation contract")

    response = ask(classroom, "¿Qué son los dividendos?", client=Teacher())
    assert response.diagnostics.narration == "used"
    assert response.sources
