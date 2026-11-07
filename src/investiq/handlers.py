"""Deterministic query execution; no language model, UI or query logging."""

import logging
from dataclasses import dataclass, field
from typing import Literal

from sqlmodel import Session

from investiq.domain import RouterDecision, SourceReference
from investiq.knowledge import get_library
from investiq.instruments import INSTRUMENTS, INSTRUMENT_BY_SYMBOL
from investiq.language import plain
from investiq.settings import Settings
from investiq.sector_context import sector_limitation
from investiq.tools import (
    compare_instruments, feature_sources, instr_features, local_model_source, market_quote_tool,
    news_tool, normalize_symbol, sec_docs_tool, similar_instruments, source_references,
    volatility_bucket,
    exploration_candidates,
)
from investiq.logging_config import log_stage

logger = logging.getLogger(__name__)

_COVERAGE = ", ".join(sorted(item.symbol for item in INSTRUMENTS))


@dataclass
class HandlerResult:
    answer: str
    facts: dict = field(default_factory=dict)
    sources: list[SourceReference] = field(default_factory=list)
    status: Literal["ok", "degraded", "error"] = "ok"
    tools_used: list[str] = field(default_factory=list)


def _symbol_feature_block(session: Session, symbol: str, quote=None) -> tuple[str, list[SourceReference], dict]:
    """Render all precomputed single-instrument metrics without deriving new values."""
    lines = ["**Cotización y métricas disponibles**"]
    sources: list[SourceReference] = []
    facts: dict = {}
    if quote is not None and quote.price is not None:
        freshness = "histórico/demorado" if quote.delayed else "del proveedor"
        when = quote.as_of.isoformat() if quote.as_of else "fecha no disponible"
        lines.append(f"- Precio: {quote.price:.2f} ({quote.provider or 'proveedor no indicado'}; {when}; {freshness}).")
        if quote.change_abs is not None or quote.change_pct is not None:
            absolute = f"{quote.change_abs:+.2f}" if quote.change_abs is not None else "no disponible"
            percentage = f"{quote.change_pct:+.2f}%" if quote.change_pct is not None else "no disponible"
            lines.append(f"- Variación reportada: {absolute} ({percentage}).")
        facts.update(price=quote.price, change_abs=quote.change_abs, change_pct=quote.change_pct,
                     quote_as_of=when, quote_provider=quote.provider, quote_delayed=quote.delayed)
        if quote.source:
            sources.append(quote.source)
    else:
        error = quote.error if quote is not None else None
        lines.append(f"- Cotización: no disponible{(': ' + error) if error else ''}.")

    with log_stage(logger, "tool.symbol_features"):
        feature = instr_features(session, symbol)
        model_source = local_model_source(session)
    logger.debug("tool.symbol_features.availability quote=%s features=%s model_metadata=%s",
                 quote is not None and quote.price is not None, feature is not None, model_source is not None)
    if feature:
        lines.append(f"- Volatilidad histórica anualizada: {feature['volatility']:.2%}.")
        lines.append(f"- Tercil de volatilidad del universo: {feature['volatility_bucket']}.")
        lines.append(f"- Beta: {feature['beta']:.2f}.")
        lines.append(f"- Correlación media con pares del universo: {feature['mean_peer_correlation']:.2f}.")
        lines.append(f"- Sector: {feature['sector']}.")
        lines.append(f"- Características calculadas: {feature['calculated_at']}.")
        facts["features"] = feature
        sources.extend(feature_sources(session, [symbol]))
        if model_source:
            lines.append(f"- Período de referencia del modelo: {model_source.title}.")
            sources.append(model_source)
    else:
        lines.append("- Métricas históricas: todavía no hay características locales calculadas para este símbolo.")
    lines.append(
        "Cobertura: instrumentos de los mercados de Estados Unidos. La cotización puede ser en tiempo real "
        "si Twelve Data y el plan de la cuenta lo permiten; de lo contrario, se presenta con su fecha y como "
        "histórica o demorada. "
        "Volatilidad, beta y correlación son cálculos sobre retornos históricos y no predicen resultados futuros."
    )
    return "\n".join(lines), sources, facts


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
    metrics, metric_sources, metric_facts = _symbol_feature_block(session, symbol, quote)
    sources = source_references(quote, news_result.articles, filings)
    sources.extend(source for source in metric_sources if source.source_id not in {item.source_id for item in sources})
    tools = ["market_quote", "news", "sec_docs"]
    tools.append("instr_features")
    if quote.price is None:
        return HandlerResult(f"No hay un precio verificable para {symbol}. {quote.error or ''}\n\n{metrics}",
                             facts={"symbol": symbol, **metric_facts}, sources=sources,
                             status="degraded", tools_used=tools)
    when = quote.as_of.isoformat() if quote.as_of else "fecha no disponible"
    freshness = "dato histórico/demorado" if quote.delayed else "dato del proveedor"
    pct = f"{quote.change_pct:.2f}%" if quote.change_pct is not None else "variación no disponible"
    answer = f"{symbol}: {pct} al {when} ({quote.provider}; {freshness}).\n\n{metrics}"
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
        facts={"symbol": symbol, "price": quote.price, "change_pct": quote.change_pct, **metric_facts,
               "news_titles": [article.title for article in news_result.articles[:2]],
               "filings": [filing.source_id for filing in filings]},
        sources=sources, status="ok" if sources else "degraded", tools_used=tools,
    )


def _educate(query: str, decision: RouterDecision, explanation_level: str) -> HandlerResult:
    # Direct tool execution remains deterministic. The coordinator supplies the
    # optional model only in its dedicated education branch.
    from investiq.tutor import answer_from_knowledge

    result = answer_from_knowledge(query, topic=decision.education_topic,
                                   level=explanation_level, client=None)
    return HandlerResult(
        result.answer, facts=result.facts, sources=result.sources, status=result.status,
        tools_used=result.tools_used,
    )


def _instrument_info(session: Session, settings: Settings, decision: RouterDecision) -> HandlerResult:
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
    sources = [source]
    tools = ["instrument_catalogue"]
    quote = market_quote_tool(session, item.symbol, settings)
    metric_block, metric_sources, metric_facts = _symbol_feature_block(session, item.symbol, quote)
    answer += "\n\n" + metric_block
    sources.extend(metric_sources)
    tools.extend(["market_quote", "instr_features"])
    document = None
    for identity in (item.symbol, item.name):
        candidate = get_library().get_by_topic(identity)
        if candidate and any(plain(identity) == plain(alias)
                             for alias in (candidate.title, *candidate.aliases)):
            document = candidate
            break
    if document is not None:
        answer += "\n\n" + document.summary
        sources.extend(reference.to_reference() for reference in document.sources)
        tools.append("knowledge_search")
    return HandlerResult(answer, facts={"symbol": item.symbol, "name": item.name, "kind": item.kind,
                                        "sector": item.sector, **metric_facts}, sources=sources, tools_used=tools)


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
    except (RuntimeError, KeyError, ValueError) as error:
        logger.warning("tool.similar_instruments.degraded error_type=%s", type(error).__name__)
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
        logger.warning("tool.compare_instruments.degraded error_type=%s", type(error).__name__)
        return HandlerResult(str(error), sources=sources, status="degraded", tools_used=tools)


def _explore(session: Session, decision: RouterDecision) -> HandlerResult:
    from investiq.preferences import SECTOR_NAMES

    if decision.exploration_horizon == "short":
        document = get_library().get_by_topic("horizonte de inversión")
        return HandlerResult(
            "Para un dinero que necesitarías en menos de un año, esta exploración de acciones y ETF "
            "no determina una opción que preserve tu capital o esté disponible sin pérdidas. "
            "Podemos estudiar liquidez y horizonte antes de buscar candidatos.\n\n"
            + (document.summary + " " + document.cautions if document else ""),
            sources=[s.to_reference() for s in document.sources] if document else [], status="degraded")
    required = (decision.exploration_kind, decision.exploration_horizon, decision.volatility_target)
    if not all(required):
        return HandlerResult("Necesito conocer tipo de instrumento, plazo y variación histórica deseada para explorar candidatos.", status="degraded")
    try:
        rows, run = exploration_candidates(session, decision)
    except (RuntimeError, ValueError, KeyError, OSError, TypeError, AttributeError):
        return HandlerResult(
            "Todavía no tengo un modelo aprobado y características históricas coherentes para esa exploración. "
            "Puedes seguir explorando conceptos mientras se preparan los datos y el modelo local.",
            status="degraded", tools_used=["exploration_candidates"])
    sources = [source for source in [local_model_source(session)] if source]
    sources.extend(feature_sources(session, [row["symbol"] for row in rows]))
    if not rows:
        return HandlerResult("No hay candidatos del catálogo que cumplan todos esos criterios con el modelo disponible. "
                             "Puedes cambiar el tipo, sector o variación histórica que quieres explorar.",
                             sources=sources, status="degraded", tools_used=["exploration_candidates"])
    kind = {"equity": "acciones", "etf": "ETF", "any": "acciones y ETF"}[decision.exploration_kind]
    horizon = "más de cinco años" if decision.exploration_horizon == "long" else "entre uno y cinco años"
    answer = (f"Candidatos para estudiar: {kind}; plazo que indicaste: {horizon}; "
              f"variación histórica deseada: {decision.volatility_target}. "
              "Es un criterio de exploración, no una evaluación completa de tu perfil financiero.\n\n")
    if decision.reference_symbol:
        answer += f"El clustering prioriza el mismo grupo y la cercanía a {decision.reference_symbol}.\n\n"
    else:
        answer += "Dentro de tus filtros, el modelo prioriza cercanía al centro de su clúster en el espacio de características entrenado.\n\n"
    answer += "| Instrumento | Tipo | Volatilidad anualizada | Nivel | Beta | Sector | Grupo ML | Coincidencia |\n|---|---|---:|---|---:|---|---:|---:|\n"
    answer += "\n".join(
        f"| {row['symbol']} · {row['name']} | {'ETF' if row['kind'] == 'ETF' else 'Acción'} | "
        f"{row['volatility']:.2%} | {row['volatility_bucket']} | {row['beta']:.2f} | "
        f"{SECTOR_NAMES.get(row['sector'], row['sector'])} | {row['cluster_label']} | {row['coincidence']:.1f}/100 |"
        for row in rows)
    answer += (f"\n\nPeríodo histórico del modelo: {run.observation_start} a {run.observation_end}. "
               f"Entrenamiento: {run.created_at.strftime('%Y-%m-%d %H:%M')} UTC. Universo entrenado: {run.universe_size} instrumentos. "
               "Las fuentes de características muestran su fecha de cálculo.\n\n"
               "La coincidencia es 100/(1 + distancia en el espacio entrenado), no una probabilidad ni una rentabilidad. "
               "Los niveles de volatilidad son terciles del universo histórico, no perfiles personales. "
               "El modelo agrupa comportamientos pasados; no identifica qué conviene comprar hoy ni garantiza resultados.")
    return HandlerResult(answer, facts={"candidates": rows}, sources=sources, tools_used=["exploration_candidates"])


def execute_query(session: Session, email: str, query: str, settings: Settings, decision: RouterDecision,
                  *, use_preferences: bool = True, explanation_level: str = "standard") -> HandlerResult:
    with log_stage(logger, "handler.execute", intent=decision.intent):
        result = _execute_query(session, email, query, settings, decision,
                                use_preferences=use_preferences, explanation_level=explanation_level)
    logger.info("handler.result intent=%s status=%s tools=%s", decision.intent, result.status,
                ",".join(result.tools_used) or "none")
    return result


def _execute_query(session: Session, email: str, query: str, settings: Settings, decision: RouterDecision,
                   *, use_preferences: bool = True, explanation_level: str = "standard") -> HandlerResult:
    if decision.intent == "sector_performance":
        if decision.sector_market != "Estados Unidos":
            return HandlerResult(sector_limitation(decision.sector_market), status="degraded")
        from investiq.providers.sectors import SECTOR_LABELS, sector_snapshot, snapshot_source
        rows, day, fetched, error = sector_snapshot(session, settings)
        if not rows:
            return HandlerResult(sector_limitation(decision.sector_market) + "\n\n" + (error or ""),
                                 status="degraded", tools_used=["sector_snapshot"] if settings.has_fmp_key else [])
        answer = (f"Sectores de NASDAQ, Estados Unidos · {day} (fecha de Nueva York). "
                  "Ordenados por variación diaria media de FMP; esta bolsa no representa todo el país.\n\n"
                  "| Sector | Variación diaria media |\n|---|---:|\n")
        answer += "\n".join(f"| {SECTOR_LABELS[row['sector']]} | {row['change_pct']:+.2f}% |" for row in rows)
        answer += (f"\n\nConsulta: {fetched.strftime('%Y-%m-%d %H:%M')} UTC. El proveedor informa fecha, no hora exacta del dato. "
                   "El orden diario no predice rentabilidad futura.")
        return HandlerResult(answer, sources=[snapshot_source(day, fetched)], tools_used=["sector_snapshot"])
    if decision.intent == "explore":
        return _explore(session, decision)
    if decision.intent == "explanation":
        return _explain(session, settings, decision)
    if decision.intent == "education":
        return _educate(query, decision, explanation_level)
    if decision.intent == "instrument_info":
        return _instrument_info(session, settings, decision)
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
