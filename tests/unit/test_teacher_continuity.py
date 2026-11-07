"""Complete lesson conversations with real local evidence and no external calls."""

import pytest
from sqlmodel import Session

from investiq.conversation import answer_turn
from investiq.data.database import create_db, make_engine
from investiq.data.models import UserPreference
from investiq.domain import ConversationState, QuoteResult, RouterDecision, SourceReference
from investiq.knowledge import get_library
from investiq.memory import load_memory
from investiq.responses import DISCLAIMER
from investiq.routing import fallback_route
from investiq.settings import Settings
from investiq.tutor import TutorEvidence, TutorNarration, TutorParagraph


@pytest.fixture
def classroom(tmp_path, monkeypatch):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'continuity.db'}"))
    settings = Settings(_env_file=None, nvidia_api_key=None, twelve_data_api_key=None,
                        marketaux_api_key=None, sec_user_agent="")

    monkeypatch.setattr("investiq.handlers.market_quote_tool", lambda session, symbol, settings: QuoteResult(
        symbol=symbol, price=100, provider="fixture", delayed=True,
        source=SourceReference(source_id=f"quote:{symbol}", title=f"Fixture {symbol}",
                               url="local://fixture", provider="fixture"),
    ))

    def blocked(*args, **kwargs):
        pytest.fail("Lessons must work without model construction or market services")

    for tool in ("news_tool", "sec_docs_tool"):
        monkeypatch.setattr(f"investiq.handlers.{tool}", blocked)
    monkeypatch.setattr("investiq.conversation.ChatNVIDIAClient", blocked)
    with Session(engine) as session:
        yield session, settings, ConversationState()
    engine.dispose()


def ask(classroom, query, *, restore=False, client=None):
    session, settings, state = classroom
    result = answer_turn(session, "learner", query, settings,
                         state=None if restore else state, client=client)
    assert result.answer.count(DISCLAIMER) == 1
    assert session.get(UserPreference, "learner") is None
    return result


@pytest.mark.parametrize("query,section", [
    ("No entiendo", "example"),
    ("¿Me lo explicas con un ejemplo?", "example"),
    ("¿Puedes explicarlo con un ejemplo, por favor?", "example"),
    ("Explícamelo más fácil", "example"),
    ("¿Cómo se interpreta?", "explanation"),
    ("¿Cómo se calcula eso?", "explanation"),
    ("¿Por qué importa?", "explanation"),
    ("¿Para qué sirve esto?", "explanation"),
    ("¿Y qué riesgos tiene?", "cautions"),
    ("¿Y cuáles son sus riesgos?", "cautions"),
    ("¿Y sus limitaciones?", "cautions"),
    ("¿Y qué costes tiene?", "explanation"),
    ("¿Y sus comisiones?", "explanation"),
    ("Más detalle", "example"),
])
def test_subject_free_requests_retrieve_the_previous_document_only(query, section):
    library = get_library()
    passages = library.search(query, topic="ETF apalancado")
    document = library.get_by_topic("ETF apalancado")
    assert {p.document_id for p in passages} == {document.id}
    assert section in {p.section for p in passages}
    assert library.search(query) == []
    assert library.search(query, topic="tema inexistente") == []
    assert library.search(query, topic="¿Qué es un ETF?") == []


@pytest.mark.parametrize("query", ["¿Y sus comisiones?", "¿Y qué costes tiene?", "¿Por qué importa?"])
def test_a_missing_context_cannot_be_invented_or_persisted(classroom, query):
    response = ask(classroom, query)
    assert response.status == "degraded" and not response.sources
    remembered = load_memory(classroom[0], "learner").state.last_decision
    assert remembered is None or remembered.education_topic is None
    example = ask(classroom, "Un ejemplo", restore=True)
    assert example.status == "degraded" and not example.sources


@pytest.mark.parametrize("query,expected", [
    ("¿Y qué es Bitcoin?", "bitcoin"),
    ("Ahora explícame la inflación", "inflacion"),
    ("¿Por qué importa la liquidez?", "liquidez"),
    ("¿Y cómo pago impuestos?", "impuestos"),
])
def test_a_new_subject_wins_over_previous_context(classroom, query, expected):
    ask(classroom, "¿Qué es un ETF apalancado?")
    result = ask(classroom, query, restore=True)
    assert result.intent == "education" and result.status == "ok"
    assert {s.source_id for s in result.sources} == {
        s.source_id for s in get_library().get_document(expected).sources
    }
    remembered = load_memory(classroom[0], "learner").state
    assert remembered.last_decision.education_topic == get_library().get_document(expected).title


@pytest.mark.parametrize("query", [
    "¿Y qué es la inflación subyacente?",
    "Ahora explícame la gestión cuántica extraterrestre",
    "¿Por qué importa la interferencia cuántica?",
])
def test_a_new_unknown_subject_cannot_borrow_the_previous_lesson(classroom, query):
    ask(classroom, "¿Qué es un ETF?")
    result = ask(classroom, query, restore=True)
    assert result.status == "degraded" and not result.sources
    assert "canasta" not in result.answer


def test_clarification_example_costs_and_topic_change_form_a_complete_lesson(classroom):
    document = get_library().get_document("etf")
    first = ask(classroom, "¿Qué es un ETF?")
    clarification = ask(classroom, "No entiendo")
    assert document.summary in clarification.answer and document.example in clarification.answer
    assert clarification.answer != first.answer
    for query in ("¿Me lo explicas con un ejemplo?", "¿Y qué costes tiene?"):
        result = ask(classroom, query, restore=True)
        assert result.intent == "education" and result.status == "ok"
        assert result.sources == first.sources
    bitcoin = ask(classroom, "Ahora quiero aprender qué es Bitcoin", restore=True)
    risks = ask(classroom, "¿Y sus riesgos?", restore=True)
    assert get_library().get_document("bitcoin").cautions in risks.answer
    assert risks.sources == bitcoin.sources


def test_interpretation_and_importance_do_not_drift_to_a_random_document(classroom):
    rsi = ask(classroom, "¿Qué es el RSI?")
    interpretation = ask(classroom, "¿Cómo se interpreta?", restore=True)
    assert get_library().get_document("rsi").explanation in interpretation.answer
    assert interpretation.sources == rsi.sources
    diversification = ask(classroom, "¿Qué es la diversificación?", restore=True)
    importance = ask(classroom, "¿Por qué importa?", restore=True)
    assert get_library().get_document("diversificacion").explanation in importance.answer
    assert importance.sources == diversification.sources
    assert "horizonte de inversión" not in importance.answer


@pytest.mark.parametrize("query", ["¿Cómo funciona esto?", "¿Para qué sirve esto?"])
def test_app_help_yields_to_an_active_lesson(classroom, query):
    help_response = ask(classroom, query)
    assert "comparar" in help_response.answer and not help_response.sources
    first = ask(classroom, "¿Qué es un ETF?")
    continuation = ask(classroom, query, restore=True)
    assert continuation.intent == "education"
    assert continuation.sources == first.sources
    assert get_library().get_document("etf").explanation in continuation.answer


def test_company_definition_continues_as_a_lesson_after_memory_restore(classroom):
    first = ask(classroom, "¿Qué es AAPL?")
    assert first.intent == "instrument_info"
    example = ask(classroom, "Un ejemplo", restore=True)
    document = get_library().get_document("instrumento-aapl")
    assert example.intent == "education" and document.example in example.answer
    risks = ask(classroom, "¿Y sus riesgos?", restore=True)
    assert document.cautions in risks.answer
    assert [s.source_id for s in risks.sources] == [s.source_id for s in document.sources]
    assert not set(risks.tools_used) & {"market_quote", "news", "sec_docs"}


def test_beginner_gets_the_meaning_and_an_example_with_sources(classroom):
    ask(classroom, "Soy principiante")
    result = ask(classroom, "¿Qué es un fondo de inversión?", restore=True)
    document = get_library().get_document("fondo-mutuo")
    assert document.summary in result.answer
    assert document.example in result.answer
    assert document.cautions in result.answer
    assert load_memory(classroom[0], "learner").state.explanation_level == "basic"
    assert result.sources


@pytest.mark.parametrize("topic,query", [
    ("rsi", "¿Cómo se interpreta?"),
    ("diversificacion", "¿Por qué importa?"),
])
def test_beginner_followup_still_answers_the_requested_explanation(classroom, topic, query):
    document = get_library().get_document(topic)
    ask(classroom, "Soy principiante")
    ask(classroom, f"¿Qué es {document.title}?", restore=True)
    result = ask(classroom, query, restore=True)
    assert document.explanation in result.answer
    assert result.sources == [s.to_reference() for s in document.sources]


@pytest.mark.parametrize("query,topic,level,section,starting_level", [
    ("No entiendo", "rsi", "basic", "example", "standard"),
    ("¿Me lo explicas con un ejemplo?", "rsi", "standard", "example", "standard"),
    ("¿Cómo se interpreta?", "rsi", "standard", "explanation", "standard"),
    ("¿Por qué importa?", "rsi", "standard", "explanation", "standard"),
    ("¿Cómo se interpreta?", "rsi", "basic", "explanation", "basic"),
    ("¿Por qué importa?", "rsi", "basic", "explanation", "basic"),
])
def test_a_simulated_teacher_receives_the_resolved_subject(classroom, query, topic, level, section, starting_level):
    document = get_library().get_document(topic)

    class Teacher:
        def classify(self, *args, **kwargs):
            pytest.fail("A resolved educational follow-up does not need classification")

        def teach(self, question, passages, context):
            assert question == query
            assert {p["document_id"] for p in passages} == {topic}
            assert context["level"] == level
            selected = next(p for p in passages if p["section"] == section)
            return TutorNarration(paragraphs=[TutorParagraph(
                text=selected["text"], evidence=[TutorEvidence(
                    passage_id=selected["passage_id"], quote=selected["text"],
                )],
            )])

    if starting_level == "basic":
        ask(classroom, "Soy principiante")
    ask(classroom, "¿Qué es el RSI?", restore=True)
    result = ask(classroom, query, restore=True, client=Teacher())
    assert result.diagnostics.narration == "used"
    assert result.sources == [s.to_reference() for s in document.sources]
    assert load_memory(classroom[0], "learner").state.explanation_level == starting_level


def test_beginner_generation_has_a_reviewed_example(classroom):
    class Teacher:
        def classify(self, *args, **kwargs):
            return RouterDecision(intent="education", education_topic="fondo de inversión")

        def teach(self, query, passages, context):
            assert context["level"] == "basic"
            assert {p["section"] for p in passages} >= {"summary", "example", "cautions"}
            selected = next(p for p in passages if p["section"] == "example")
            return TutorNarration(paragraphs=[TutorParagraph(
                text=selected["text"], evidence=[TutorEvidence(
                    passage_id=selected["passage_id"], quote=selected["text"],
                )],
            )])

    ask(classroom, "Soy principiante")
    result = ask(classroom, "¿Qué es un fondo de inversión?", restore=True, client=Teacher())
    assert result.diagnostics.narration == "used"


@pytest.mark.parametrize("query,intent", [
    ("¿Qué precio tiene AAPL hoy?", "explanation"),
    ("¿Qué sectores lideran hoy?", "sector_performance"),
    ("compara AAPL y MSFT", "compare"),
    ("busca similares a MSFT", "recommend_similar"),
])
def test_explicit_market_requests_keep_their_routes(query, intent):
    assert fallback_route(query).intent == intent
