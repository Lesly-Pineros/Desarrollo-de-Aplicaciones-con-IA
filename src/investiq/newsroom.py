"""News presentation and bounded NVIDIA rewriting over retrieved excerpts only."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from investiq.domain import ConversationState, ResponseAction, RouterDecision, SourceReference
from investiq.providers.headlines import daily_headlines
from investiq.language import plain
from investiq.tutor.grounding import suspicious_passage


class NewsRewrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(max_length=100)
    title_quote: str = Field(min_length=1, max_length=300)
    title_es: str = Field(min_length=1, max_length=400)
    summary_quote: str = Field(default="", max_length=1200)
    summary_es: str = Field(default="", max_length=650)


class NewsRewrites(BaseModel):
    model_config = ConfigDict(extra="forbid")
    articles: list[NewsRewrite] = Field(min_length=1, max_length=3)


@dataclass
class NewsResult:
    answer: str
    sources: list[SourceReference] = field(default_factory=list)
    actions: list[ResponseAction] = field(default_factory=list)
    status: str = "ok"
    tools_used: list[str] = field(default_factory=lambda: ["daily_headlines"])


def display_text(text: str) -> str:
    # Render untrusted prose as text, never as Markdown links or commands.
    return re.sub(r"[\[\]`*<>|\r\n]", " ", text).strip()


def valid_rewrite(rewrite: NewsRewrite, article, *, summary: bool) -> bool:
    if rewrite.source_id != article.source_id or rewrite.title_quote != article.title:
        return False
    if summary:
        if (not article.description or len(rewrite.summary_quote.strip()) < 18
                or rewrite.summary_quote not in article.description or not rewrite.summary_es.strip()):
            return False
    elif rewrite.summary_es or rewrite.summary_quote:
        return False
    pairs = [(rewrite.title_es, article.title)]
    if summary:
        pairs.append((rewrite.summary_es, rewrite.summary_quote))
    for text, support in pairs:
        if (suspicious_passage(text) or re.search(r"https?://|www\.|<|>|\[|\]|\{", text, re.I)
                or re.search(r"\b(?:compra|vende|invierte|recomiendo|ganaras|garantizad[oa]|buy|sell|invest|guaranteed)\b", plain(text))):
            return False
        numbers = lambda value: set(re.findall(r"[+-]?\d+(?:[.,]\d+)*(?:\s*%)?", value))
        if numbers(text) - numbers(support):
            return False
        # Tickers and acronyms must exist in the actual source. This is an
        # additional guard, not a semantic equivalence proof for translation.
        if set(re.findall(r"\b[A-Z]{2,6}\b", text)) - set(re.findall(r"\b[A-Z]{2,6}\b", support)):
            return False
    return True


def _rewrite(client, articles, *, summary, diagnostics):
    method = getattr(client, "translate_news", None)
    if not callable(method):
        diagnostics.narration = "unavailable"
        diagnostics.fallback_reason = "not_configured"
        return {}
    try:
        payload = [{"source_id": a.source_id, "title": a.title,
                    "description": a.description if summary else "", "language": a.language} for a in articles]
        result = method(payload, summary=summary)
        result = result if isinstance(result, NewsRewrites) else NewsRewrites.model_validate(result)
        by_id = {a.source_id: a for a in articles}
        ids = [a.source_id for a in result.articles]
        if len(set(ids)) != len(ids) or set(ids) != set(by_id):
            raise ValueError("mismatched articles")
        if not all(valid_rewrite(item, by_id[item.source_id], summary=summary) for item in result.articles):
            raise ValueError("unsupported rewrite")
        diagnostics.narration = "used"
        return {a.source_id: a for a in result.articles}
    except Exception:
        diagnostics.narration = "fallback"
        diagnostics.fallback_reason = "invalid_output"
        return {}


def answer_news(session, query: str, decision: RouterDecision, settings, state: ConversationState,
                *, client=None, diagnostics) -> NewsResult:
    selection = decision.news_selection
    reason = None
    if not selection and re.search(r"\b(?:ayer|anteayer|semana pasada|mes pasado|esta semana)\b|\b\d{4}-\d{2}-\d{2}\b", plain(query)):
        return NewsResult("Esta consulta cubre los titulares del día de hoy. Todavía no ofrece búsqueda histórica por fechas; puedes pedir noticias de hoy por sector o país.",
                          status="degraded", tools_used=[])
    if selection:
        if selection.isdigit():
            position = int(selection) - 1
            articles = state.news_items[position:position + 1] if 0 <= position < 3 else []
        else:
            articles = [a for a in state.news_items if a.source_id == selection]
        if not articles:
            return NewsResult("¿Qué noticia quieres resumir? Elige una del listado más reciente o pide noticias de hoy.",
                              status="degraded", tools_used=[])
    else:
        collection = daily_headlines(session, decision, settings)
        articles, reason = collection.articles, collection.reason
        state.news_items = articles
        if not articles:
            return NewsResult(reason or "No encontré noticias verificadas de hoy.", status="degraded")
    sources = [SourceReference(source_id=a.source_id, title=a.title, url=str(a.url), provider=a.provider,
                              published_at=a.published_at, delayed=a.delayed) for a in articles]
    if selection and not articles[0].description.strip():
        article = articles[0]
        return NewsResult("Solo recibí el titular de esta noticia; no tengo un extracto suficiente para resumirla. "
                          "Puedes abrir la fuente para leerla completa.\n\n" + display_text(article.title),
                          sources=sources, status="degraded", tools_used=[])
    needs_rewrite = bool(selection) or any(a.language.casefold() != "es" for a in articles)
    generated = _rewrite(client, articles, summary=bool(selection), diagnostics=diagnostics) if needs_rewrite else {}
    if selection:
        article = articles[0]
        rewrite = generated.get(article.source_id)
        summary = rewrite.summary_es if rewrite else article.description
        title = rewrite.title_es if rewrite else article.title
        answer = display_text(title) + "\n\n" + display_text(summary)
        answer += ("\n\nResumen del extracto recibido de Marketaux; no del artículo completo." if rewrite else
                   "\n\nExtracto original recibido de Marketaux; no dispongo de un resumen generado.")
    else:
        today = datetime.now(timezone.utc).astimezone(ZoneInfo(settings.market_timezone)).date()
        from investiq.news_context import NEWS_COUNTRIES
        from investiq.providers.sectors import SECTOR_LABELS
        scope = ", ".join(filter(None, [SECTOR_LABELS.get(decision.news_sector),
            NEWS_COUNTRIES[decision.news_country][0].title() if decision.news_country else None,
            decision.symbol])) or "mercados globales"
        answer = f"Titulares de hoy ({today.isoformat()}, {settings.market_timezone}) · {scope}. Selección por recencia."
        if decision.news_country:
            answer += " El filtro de país usa las entidades de mercado identificadas por la fuente; no cubre toda la actualidad del país."
            sources.append(SourceReference(source_id="marketaux:country-filter", title="Marketaux · alcance del filtro de país",
                url="https://www.marketaux.com/documentation", provider="Marketaux"))
        for index, article in enumerate(articles, 1):
            rewrite = generated.get(article.source_id)
            title = rewrite.title_es if rewrite else article.title
            published = article.published_at.astimezone(ZoneInfo(settings.market_timezone)).strftime("%Y-%m-%d %H:%M %Z")
            answer += f"\n\n{index}. {display_text(title)}\nPublicado: {published}. Fuente: {article.url.host}."
    if generated:
        answer += "\n\nTraducción generada al español; el original está en las fuentes."
    elif needs_rewrite:
        answer += "\n\nMuestro el texto original; la traducción al español no está disponible o no pasó la validación."
    if reason:
        answer += "\n\n" + reason
    actions = [] if selection else [ResponseAction(label=f"Resumir noticia {i}", prompt=f"Resume la noticia {i}", news_id=a.source_id)
                                    for i, a in enumerate(articles, 1)]
    return NewsResult(answer, sources=sources, actions=actions,
                      status="degraded" if reason or (needs_rewrite and not generated) else "ok",
                      tools_used=["news_excerpt"] if selection else ["daily_headlines"])
