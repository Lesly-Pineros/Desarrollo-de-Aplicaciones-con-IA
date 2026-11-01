import hashlib
import json
from datetime import datetime, timedelta, timezone

import requests
from pydantic import ValidationError
from sqlmodel import Session

from investiq.data.models import NewsCacheEntry
from investiq.domain import NewsCollection, NewsItem
from investiq.instruments import INSTRUMENT_BY_SYMBOL
from investiq.limits import QuotaExceeded, reserve_daily_request
from investiq.settings import Settings

MARKETAUX_NEWS_URL = "https://api.marketaux.com/v1/news/all"


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _published(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return _aware(parsed)
    except ValueError:
        return None


def _decode(entry: NewsCacheEntry, *, delayed: bool = False) -> NewsCollection:
    raw = json.loads(entry.articles_json)
    articles = []
    for item in raw:
        try:
            articles.append(NewsItem.model_validate({**item, "delayed": delayed or item.get("delayed", True)}))
        except ValidationError:
            continue
    return NewsCollection(articles=articles, available=bool(articles))


def news(
    session: Session,
    symbol: str,
    settings: Settings,
    *,
    http_get=requests.get,
) -> NewsCollection:
    symbol = symbol.strip().upper()
    if symbol not in INSTRUMENT_BY_SYMBOL:
        return NewsCollection(available=False, reason="Símbolo fuera del universo cubierto.")

    now = datetime.now(timezone.utc)
    cached = session.get(NewsCacheEntry, symbol)
    if cached and _aware(cached.expires_at) > now:
        return _decode(cached)
    if not settings.has_marketaux_key:
        if cached:
            return _decode(cached, delayed=True)
        return NewsCollection(available=False, reason="Marketaux no está configurado; no se consultaron noticias.")

    try:
        reserve_daily_request(session, "marketaux", 100)
        response = http_get(
            MARKETAUX_NEWS_URL,
            params={
                "symbols": symbol,
                "filter_entities": "true",
                "language": "en",
                "limit": 5,
                "api_token": settings.marketaux_api_key.strip(),
            },
            timeout=settings.http_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        articles = []
        for item in payload.get("data", []):
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not title or not url.startswith("https://"):
                continue
            stable = str(item.get("uuid") or hashlib.sha256(url.encode()).hexdigest()[:12])
            articles.append(
                NewsItem(
                    title=title[:300],
                    description=str(item.get("description") or "")[:1600],
                    url=url,
                    provider="Marketaux",
                    published_at=_published(item.get("published_at")),
                    delayed=True,
                    source_id=f"news:{symbol}:{stable}",
                )
            )
        session.merge(
            NewsCacheEntry(
                symbol=symbol,
                articles_json=json.dumps([article.model_dump(mode="json") for article in articles], ensure_ascii=False),
                fetched_at=now,
                expires_at=now + timedelta(hours=settings.news_cache_hours),
            )
        )
        session.commit()
        return NewsCollection(articles=articles, available=bool(articles), reason=None if articles else "Marketaux no devolvió noticias pertinentes.")
    except QuotaExceeded:
        reason = "Se alcanzó la cuota diaria de noticias."
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        reason = "No se pudieron validar noticias nuevas de Marketaux."

    if cached:
        result = _decode(cached, delayed=True)
        result.reason = reason
        return result
    return NewsCollection(available=False, reason=reason)
