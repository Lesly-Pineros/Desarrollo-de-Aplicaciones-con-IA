import json
import re
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from investiq.data.models import QueryLog
from investiq.domain import AssistantResponse, RouterDecision, SourceReference
from investiq.instruments import INSTRUMENTS
from investiq.llm import ChatNVIDIAClient, LLMUnavailable
from investiq.settings import Settings
from investiq.tools import (
    compare_instruments, education_tool, local_model_source, market_quote_tool,
    news_tool, normalize_symbol, sec_docs_tool, similar_instruments,
    source_references, volatility_bucket,
)

DISCLAIMER = "No es asesoría financiera."
_SYMBOLS = {item.symbol for item in INSTRUMENTS}
_COVERAGE = ", ".join(sorted(_SYMBOLS))


def _fallback_route(query: str) -> RouterDecision:
    text = query.casefold()
    symbols = re.findall(r"(?<![A-Z0-9])(?:BRK-B|[A-Z]{1,5})(?![A-Z0-9])", query.upper())
    covered = [symbol for symbol in symbols if symbol in _SYMBOLS]
    if any(word in text for word in ("volatilidad", "riesgo bajo", "riesgo medio", "riesgo alto")) and any(
        word in text for word in ("recom", "busca", "dame", "instrumentos", "acciones", "etf")
    ):
        target = next((bucket for bucket in ("baja", "media", "alta") if bucket in text), None)
        return RouterDecision(intent="recommend_volatility", volatility_target=target,
                              needs_clarification=target is None)
    if any(word in text for word in ("similar", "parecido", "semejante")):
        return RouterDecision(intent="recommend_similar", reference_symbol=covered[0] if covered else None,
                              needs_clarification=not bool(covered))
    if any(word in text for word in ("compara", "comparar", "comparación")):
        return RouterDecision(intent="compare", comparison_symbols=covered[:4],
                              needs_clarification=len(covered) < 2)
    if any(word in text for word in ("qué es", "que es", "qué significa", "que significa", "explica", "explícame", "explicame", "define", "beta", "volatilidad", "etf", "correlación", "retorno", "riesgo")):
        return RouterDecision(intent="education", education_topic=query)
    if covered and any(word in text for word in ("precio", "movimiento", "subió", "bajó", "acción", "cotización")):
        return RouterDecision(intent="explanation", symbol=covered[0])
    return RouterDecision(intent="unknown")


def _route(query: str, settings: Settings, client: ChatNVIDIAClient | None) -> RouterDecision:
    if client:
        try:
            decision = client.classify(query)
            if decision.symbol:
                decision.symbol = normalize_symbol(decision.symbol)
            if decision.reference_symbol:
                decision.reference_symbol = normalize_symbol(decision.reference_symbol)
            decision.comparison_symbols = [s for value in decision.comparison_symbols if (s := normalize_symbol(value))]
            return decision
        except LLMUnavailable:
            pass
    return _fallback_route(query)


def _response(intent: str, answer: str, *, sources=None, status="ok", tools=None, client=None):
    return AssistantResponse(answer=f"{answer.rstrip()}\n\n{DISCLAIMER}", intent=intent,
                             sources=sources or [], status=status, tools_used=tools or [],
                             input_tokens=getattr(client, "last_input_tokens", None),
                             output_tokens=getattr(client, "last_output_tokens", None))


def _safe_narrate(client, intent: str, query: str, facts: dict, sources: list[SourceReference]) -> str | None:
    if not client:
        return None
    try:
        narration = client.narrate(intent, query, facts, [s.model_dump(mode="json") for s in sources])
    except LLMUnavailable:
        return None
    ids = {source.source_id for source in sources}
    if any(source_id not in ids for source_id in narration.cited_source_ids):
        return None
    # All numerals in financial responses are rendered by deterministic templates below.
    if re.search(r"\d", narration.answer):
        return None
    return narration.answer


def _record(session: Session, email: str, response: AssistantResponse, retention_days: int) -> None:
    session.add(QueryLog(email=email, intent=response.intent,
                         tools_json=json.dumps(response.tools_used),
                         sources_json=json.dumps([s.source_id for s in response.sources]),
                         status=response.status, input_tokens=response.input_tokens,
                         output_tokens=response.output_tokens))
    # No raw query text or secrets are stored; retention is purged with configured policy.
    session.commit()
    purge_query_logs(session, retention_days)


def purge_query_logs(session: Session, retention_days: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    old = session.exec(select(QueryLog).where(QueryLog.created_at < cutoff)).all()
    for record in old:
        session.delete(record)
    session.commit()
    return len(old)


def answer_query(session: Session, email: str, query: str, settings: Settings,
                 client: ChatNVIDIAClient | None = None) -> AssistantResponse:
    query = query.strip()[:2000]
    if not query:
        return _response("unknown", "Escribe una consulta para comenzar.")
    if client is None and settings.has_nvidia_key:
        try:
            client = ChatNVIDIAClient(settings)
        except LLMUnavailable:
            client = None
    decision = _route(query, settings, client)
    used: list[str] = []
    sources: list[SourceReference] = []
    status = "ok"
    facts: dict = {}

    if decision.intent == "explanation":
        symbol = normalize_symbol(decision.symbol) or normalize_symbol(_fallback_route(query).symbol)
        if not symbol:
            answer = f"No pude identificar un símbolo cubierto. El universo disponible es: {_COVERAGE}."
            status = "degraded"
        else:
            quote = market_quote_tool(session, symbol, settings); used.append("market_quote")
            news_result = news_tool(session, symbol, settings); used.append("news")
            filings, sec_reason = sec_docs_tool(session, symbol, settings); used.append("sec_docs")
            sources = source_references(quote, news_result.articles, filings)
            if quote.price is None:
                answer = f"No hay un precio verificable para {symbol}. {quote.error or ''}"
                status = "degraded"
            else:
                when = quote.as_of.isoformat() if quote.as_of else "fecha no disponible"
                freshness = "dato histórico/demorado" if quote.delayed else "dato del proveedor"
                pct = f"{quote.change_pct:.2f}%" if quote.change_pct is not None else "variación no disponible"
                answer = f"{symbol}: {pct} al {when} ({quote.provider}; {freshness})."
                if news_result.articles:
                    answer += " Noticias disponibles: " + "; ".join(a.title for a in news_result.articles[:2]) + "."
                else:
                    answer += f" No hay noticia disponible: {news_result.reason or 'sin resultados'}."
                if filings:
                    answer += " Hay filings SEC recientes en las fuentes enlazadas."
                else:
                    answer += f" No hay filing verificable: {sec_reason or 'sin resultados'}"
                if quote.error: answer += f" Aviso: {quote.error}"
                facts = {"symbol": symbol, "price": quote.price, "change_pct": quote.change_pct,
                         "news_titles": [a.title for a in news_result.articles[:2]],
                         "filings": [f.source_id for f in filings]}
                if not sources: status = "degraded"
    elif decision.intent == "education":
        definition = education_tool(decision.education_topic or query)
        if not definition:
            answer = "Puedo explicar volatilidad, beta, correlación, ETF, retorno o riesgo. ¿Cuál te interesa?"
            status = "degraded"
        else:
            answer = definition
            facts = {"definition": definition}
    elif decision.intent == "recommend_volatility":
        target = decision.volatility_target
        if target not in {"baja", "media", "alta"}:
            answer = "¿Buscas volatilidad baja, media o alta?"
            status = "degraded"
        else:
            rows = volatility_bucket(session, target); used.append("volatility_bucket")
            source = local_model_source(session)
            if source: sources = [source]
            answer = (f"Instrumentos con volatilidad histórica {target}: " + ", ".join(r["symbol"] for r in rows[:8])
                      + ". La clasificación usa terciles históricos y no predice riesgo futuro.") if rows else "No hay features válidas para esa cubeta."
            facts = {"target": target, "symbols": [r["symbol"] for r in rows[:8]]}
            if not rows: status = "degraded"
    elif decision.intent == "recommend_similar":
        ref = normalize_symbol(decision.reference_symbol)
        if not ref:
            answer = "¿Qué símbolo cubierto quieres usar como referencia?"
            status = "degraded"
        else:
            try:
                rows = similar_instruments(session, ref); used.append("similar_instruments")
                sources = [source for source in [local_model_source(session)] if source]
                answer = f"Instrumentos similares a {ref}: " + (", ".join(f"{r['symbol']} (clúster {r['cluster_label']})" for r in rows) or "no hay vecinos disponibles") + ". La similitud histórica no predice rendimiento."
                facts = {"reference": ref, "neighbors": [r["symbol"] for r in rows]}
                if not rows: status = "degraded"
            except (RuntimeError, KeyError, ValueError) as exc:
                answer = str(exc); status = "degraded"
    elif decision.intent == "compare":
        try:
            rows = compare_instruments(session, email, decision.comparison_symbols); used.append("compare_instruments")
            sources = [source for source in [local_model_source(session)] if source]
            answer = "Comparación determinista según tus preferencias: " + "; ".join(f"{r['symbol']} {r['score']:.2f}/100" for r in rows) + ". El puntaje describe coincidencia con preferencias, no rendimiento esperado."
            facts = {"scores": rows}
        except ValueError as exc:
            answer = str(exc); status = "degraded"
    else:
        answer = "Puedo explicar precios, enseñar conceptos, buscar instrumentos similares o filtrar por volatilidad. ¿Qué necesitas?"
        status = "degraded"

    # LLM can add prose only when it validates; numbers and factual data remain in deterministic templates.
    if facts and client and decision.intent in {"education"}:
        narrated = _safe_narrate(client, decision.intent, query, facts, sources)
        if narrated:
            answer = narrated
    response = _response(decision.intent, answer, sources=sources, status=status, tools=used, client=client)
    _record(session, email, response, settings.query_log_retention_days)
    return response
