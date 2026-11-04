from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from investiq.data.database import create_db, make_engine
from investiq.data.models import QueryLog
from investiq.domain import Narration
from investiq.orchestration import answer_query, purge_query_logs
from investiq.routing import fallback_route
from investiq.settings import Settings


def test_education_has_disclaimer_and_log_excludes_raw_query(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'app.db'}"))
    with Session(engine) as session:
        result = answer_query(session, "a@b.com", "¿Qué es beta?", Settings())
        assert "No es asesoría financiera" in result.answer
        log = session.exec(select(QueryLog)).one()
        assert not hasattr(log, "query")
        assert result.tools_used == []


def test_invalid_fabricated_citation_or_numeric_narration_is_rejected():
    from investiq.response_style import safe_narration
    from investiq.domain import SourceReference

    class Client:
        def narrate(self, *args):
            return Narration(answer="El precio subió 20%.", cited_source_ids=["invented"])

    source = SourceReference(source_id="real", title="Price", url="https://example.com", provider="test")
    assert safe_narration(Client(), "education", "q", {"x": 1}, [source]) is None


def test_log_retention_purges_old_records(tmp_path):
    engine = create_db(make_engine(f"sqlite:///{tmp_path / 'retention.db'}"))
    with Session(engine) as session:
        session.add(QueryLog(email="a@b.com", created_at=datetime.now(timezone.utc) - timedelta(days=100),
                             intent="education", tools_json="[]", sources_json="[]", status="ok"))
        session.commit()
        assert purge_query_logs(session, 90) == 1
        assert session.exec(select(QueryLog)).all() == []


import pytest


@pytest.mark.parametrize("query,intent", [
    ("¿Qué es beta?", "education"),
    ("Explica volatilidad", "education"),
    ("Define correlación", "education"),
    ("¿Qué es un ETF?", "education"),
    ("Explícame el retorno", "education"),
    ("¿Qué significa riesgo?", "education"),
    ("precio AAPL", "explanation"),
    ("movimiento de MSFT", "explanation"),
    ("¿AAPL subió hoy?", "explanation"),
    ("cotización de SPY", "explanation"),
    ("recomienda volatilidad baja", "recommend_volatility"),
    ("busca ETF volatilidad media", "recommend_volatility"),
    ("dame acciones de volatilidad alta", "recommend_volatility"),
    ("instrumentos similares a NVDA", "recommend_similar"),
    ("compara AAPL con MSFT", "compare"),
])
def test_spanish_golden_fallback_intent(query, intent):
    assert fallback_route(query).intent == intent
