"""Deterministic query execution; no language model, UI or query logging."""

from dataclasses import dataclass, field
from typing import Literal

from sqlmodel import Session

from investiq.domain import RouterDecision, SourceReference
from investiq.education import EDUCATION_CATALOGUE, education_sources
from investiq.instruments import INSTRUMENTS, INSTRUMENT_BY_SYMBOL
from investiq.language import canonical_education_topic
from investiq.settings import Settings
from investiq.tools import (
    compare_instruments, education_tool, feature_sources, local_model_source, market_quote_tool,
    news_tool, normalize_symbol, sec_docs_tool, similar_instruments, source_references,
    volatility_bucket,
)

_COVERAGE = ", ".join(sorted(item.symbol for item in INSTRUMENTS))


@dataclass
class HandlerResult:
    answer: str
    facts: dict = field(default_factory=dict)
    sources: list[SourceReference] = field(default_factory=list)
    status: Literal["ok", "degraded", "error"] = "ok"
    tools_used: list[str] = field(default_factory=list)
    protected_narration: bool = False


def _explain(session: Session, settings: Settings, decision: RouterDecision) -> HandlerResult:
    symbol = normalize_symbol(decision.symbol)
    if not symbol:
        return HandlerResult(
            f"No pude identificar un símbolo cubierto. El universo disponible es: {_COVERAGE}.",
            status="degraded",
        )
    quote = market_quote_tool(session, symbol, settings)
    news_result = news_tool(session, symbol, settings)
    filings, sec_reason = sec_docs_tool(session, symbol, settings)
    sources = source_references(quote, news_result.articles, filings)
    tools = ["market_quote", "news", "sec_docs"]
    if quote.price is None:
        return HandlerResult(f"No hay un precio verificable para {symbol}. {quote.error or ''}",
                             sources=sources, status="degraded", tools_used=tools)
    when = quote.as_of.isoformat() if quote.as_of else "fecha no disponible"
    freshness = "dato histórico/demorado" if quote.delayed else "dato del proveedor"
    pct = f"{quote.change_pct:.2f}%" if quote.change_pct is not None else "variación no disponible"
    answer = f"{symbol}: {pct} al {when} ({quote.provider}; {freshness})."
    if news_result.articles:
        answer += " Noticias disponibles: " + "; ".join(article.title for article in news_result.articles[:2]) + "."
    else:
        answer += f" No hay noticia disponible: {news_result.reason or 'sin resultados'}."
    if filings:
        answer += " Hay filings SEC recientes en las fuentes enlazadas."
    else:
        answer += f" No hay filing verificable: {sec_reason or 'sin resultados'}"
    if quote.error:
        answer += f" Aviso: {quote.error}"
    return HandlerResult(
        answer,
        facts={"symbol": symbol, "price": quote.price, "change_pct": quote.change_pct,
               "news_titles": [article.title for article in news_result.articles[:2]],
               "filings": [filing.source_id for filing in filings]},
        sources=sources, status="ok" if sources else "degraded", tools_used=tools,
    )


def _educate(query: str, decision: RouterDecision, explanation_level: str) -> HandlerResult:
    followup = query + " sencillo" if explanation_level == "basic" else query
    definition = education_tool(decision.education_topic or query, followup=followup)
    if not definition:
        return HandlerResult(
            "Todavía no tengo una explicación verificada para ese término. "
            "Podemos empezar por volatilidad, beta, correlación, ETF, retorno o riesgo.",
            status="degraded",
        )
    topic = canonical_education_topic(decision.education_topic or query)
    return HandlerResult(
        definition, facts={"definition": definition}, sources=education_sources(topic),
        protected_narration=EDUCATION_CATALOGUE[topic].protected_narration,
    )


def _instrument_info(decision: RouterDecision) -> HandlerResult:
    symbol = normalize_symbol(decision.symbol)
    item = INSTRUMENT_BY_SYMBOL.get(symbol)
    if item is None:
        return HandlerResult("¿Qué empresa o símbolo quieres conocer? Puedes elegir uno del catálogo.",
                             status="degraded")
    sectors = {
        "Technology": "tecnología", "Consumer Discretionary": "consumo discrecional",
        "Communication Services": "servicios de comunicación", "Financials": "finanzas",
        "Energy": "energía", "Health Care": "salud", "Consumer Staples": "consumo básico",
        "Broad Market": "mercado amplio",
    }
    kind = "una acción" if item.kind == "equity" else "un ETF"
    answer = (
        f"**{item.symbol}** es el símbolo bursátil de **{item.name}**. "
        f"En nuestro catálogo es {kind}, en la categoría de {sectors.get(item.sector, item.sector)}.\n\n"
        "Puedes usar ese símbolo para consultar sus movimientos o compararlo con otro instrumento."
    )
    source = SourceReference(
        source_id=f"catalogue:{item.symbol}", title=f"Catálogo local: {item.symbol} · {item.name}",
        url=f"local://catalogue/{item.symbol}", provider="Catálogo de instrumentos de InvestiQ",
    )
    return HandlerResult(answer, facts={"symbol": item.symbol, "name": item.name, "kind": item.kind,
                                        "sector": item.sector}, sources=[source], tools_used=["instrument_catalogue"])


def _recommend_volatility(session: Session, decision: RouterDecision) -> HandlerResult:
    target = decision.volatility_target
    if target not in {"baja", "media", "alta"}:
        return HandlerResult("¿Buscas volatilidad baja, media o alta?", status="degraded")
    rows = volatility_bucket(session, target)
    source = local_model_source(session)
    sources = [source] if source else feature_sources(session, [row["symbol"] for row in rows[:8]])
    if rows:
        answer = (f"Si exploramos volatilidad histórica {target}, aparecen: "
                  + ", ".join(row["symbol"] for row in rows[:8])
                  + ". Esta agrupación usa terciles históricos y no predice riesgo futuro.")
    else:
        answer = "Todavía no tengo datos históricos calculados para ese grupo. Podemos explorar un concepto mientras tanto."
    return HandlerResult(answer, facts={"target": target, "symbols": [row["symbol"] for row in rows[:8]]},
                         sources=sources, status="ok" if rows else "degraded", tools_used=["volatility_bucket"])


def _recommend_similar(session: Session, decision: RouterDecision) -> HandlerResult:
    reference = normalize_symbol(decision.reference_symbol)
    if not reference:
        return HandlerResult("¿Qué símbolo cubierto quieres usar como referencia?", status="degraded")
    tools = []
    sources = []
    try:
        rows = similar_instruments(session, reference)
        tools.append("similar_instruments")
        sources = [source for source in [local_model_source(session)] if source]
        neighbors = ", ".join(f"{row['symbol']} (grupo {row['cluster_label']})" for row in rows)
        answer = (f"Tomando {reference} como referencia, encuentro: "
                  + (neighbors or "ningún vecino con los datos disponibles")
                  + ". La similitud histórica no predice rendimiento.")
        return HandlerResult(answer, facts={"reference": reference, "neighbors": [row["symbol"] for row in rows]},
                             sources=sources, status="ok" if rows else "degraded", tools_used=tools)
    except (RuntimeError, KeyError, ValueError):
        return HandlerResult(
            "Todavía no tengo los datos y el modelo histórico listos para buscar similitudes. Podemos consultar un instrumento o hablar de cómo se mide la similitud.",
            sources=sources, status="degraded", tools_used=tools,
        )


def _compare(session: Session, email: str, decision: RouterDecision, use_preferences: bool) -> HandlerResult:
    tools = []
    sources = []
    try:
        rows = compare_instruments(session, email, decision.comparison_symbols, use_preferences=use_preferences)
        tools.append("compare_instruments")
        source = local_model_source(session)
        sources = [source] if source else feature_sources(session, [row["symbol"] for row in rows])
        if not rows:
            answer = "Todavía no tengo características históricas calculadas para esos instrumentos. ¿Quieres que exploremos un concepto o consultemos uno de ellos?"
        elif all(row.get("score") is not None for row in rows):
            answer = "Con los criterios que me compartiste, la comparación queda así:\n\n"
            answer += "\n".join(f"- **{row['symbol']}**: {row['score']:.2f}/100 de coincidencia." for row in rows)
            answer += "\n\nEl puntaje describe coincidencia con tus preferencias, no rendimiento esperado. Puedes cambiar un criterio y volvemos a comparar."
        else:
            answer = "Claro, veamos sus características históricas sin personalizar un puntaje:\n\n"
            answer += "| Símbolo | Volatilidad anualizada | Beta | Sector |\n|---|---:|---:|---|\n"
            answer += "\n".join(f"| {row['symbol']} | {row['volatility']:.2%} | {row['beta']:.2f} | {row['sector']} |" for row in rows)
            answer += "\n\nEstas métricas describen el pasado; no garantizan cómo se comportarán después."
        return HandlerResult(answer, facts={"scores": rows}, sources=sources,
                             status="ok" if rows else "degraded", tools_used=tools)
    except ValueError as error:
        return HandlerResult(str(error), sources=sources, status="degraded", tools_used=tools)


def execute_query(session: Session, email: str, query: str, settings: Settings, decision: RouterDecision,
                  *, use_preferences: bool = True, explanation_level: str = "standard") -> HandlerResult:
    if decision.intent == "explanation":
        return _explain(session, settings, decision)
    if decision.intent == "education":
        return _educate(query, decision, explanation_level)
    if decision.intent == "instrument_info":
        return _instrument_info(decision)
    if decision.intent == "recommend_volatility":
        return _recommend_volatility(session, decision)
    if decision.intent == "recommend_similar":
        return _recommend_similar(session, decision)
    if decision.intent == "compare":
        return _compare(session, email, decision, use_preferences)
    return HandlerResult(
        "No estoy seguro de qué quieres explorar. Dime un concepto o un símbolo y empezamos por ahí; "
        "por ejemplo, «qué es AAPL» o «explícame la volatilidad».",
        status="degraded",
    )
