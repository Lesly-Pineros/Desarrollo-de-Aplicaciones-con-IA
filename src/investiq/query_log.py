"""Persist response metadata and purge expired rows without storing raw queries."""

import json
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from investiq.data.models import QueryLog, ResponseTrace
from investiq.domain import AssistantResponse


def record_response(session: Session, email: str, response: AssistantResponse, retention_days: int) -> None:
    record = QueryLog(
        email=email, intent=response.intent,
        tools_json=json.dumps(response.tools_used),
        sources_json=json.dumps([source.source_id for source in response.sources]),
        status=response.status, input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
    )
    session.add(record)
    session.flush()
    session.add(ResponseTrace(query_log_id=record.id, **response.diagnostics.model_dump()))
    session.commit()
    purge_query_logs(session, retention_days)


def purge_query_logs(session: Session, retention_days: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    old = session.exec(select(QueryLog).where(QueryLog.created_at < cutoff)).all()
    for record in old:
        trace = session.get(ResponseTrace, record.id)
        if trace:
            session.delete(trace)
        session.delete(record)
    session.commit()
    return len(old)
