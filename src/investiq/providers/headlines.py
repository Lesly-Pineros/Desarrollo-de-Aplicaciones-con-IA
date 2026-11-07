"""Day-scoped Marketaux adapter. Network is optional and injectable for tests."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import ValidationError
import requests
from sqlmodel import Session

from investiq.data.models import MarketContextCache
from investiq.domain import NewsCollection, NewsItem, RouterDecision
from investiq.limits import QuotaExceeded, reserve_daily_request
from investiq.news_context import NEWS_COUNTRIES, NEWS_SECTORS
from investiq.providers.news import MARKETAUX_NEWS_URL, _aware, _published
from investiq.settings import Settings
from investiq.tutor.grounding import suspicious_passage
from investiq.logging_config import log_stage

logger = logging.getLogger(__name__)


def safe_news_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        return bool(parsed.scheme == "https" and parsed.hostname and not parsed.username
                    and not parsed.password and not any(c.isspace() for c in value))
    except ValueError:
        return False


def daily_headlines(session: Session, decision: RouterDecision, settings: Settings, *,
                    http_get=None, now: datetime | None = None) -> NewsCollection:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    local = now.astimezone(ZoneInfo(settings.market_timezone))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    params = {"published_after": start.strftime("%Y-%m-%dT%H:%M:%S"),
              "published_before": now.strftime("%Y-%m-%dT%H:%M:%S"),
              "language": "en,es", "sort": "published_on", "sort_order": "desc", "limit": 3}
    if decision.news_sector:
        if decision.news_sector not in NEWS_SECTORS:
            return NewsCollection(available=False, reason="No reconozco ese sector de noticias.")
        params["industries"] = decision.news_sector
    if decision.news_country:
        if decision.news_country not in NEWS_COUNTRIES:
            return NewsCollection(available=False, reason="No reconozco ese país para el filtro de noticias.")
        params["countries"] = decision.news_country
    if decision.symbol:
        from investiq.instruments import INSTRUMENT_BY_SYMBOL
        if decision.symbol not in INSTRUMENT_BY_SYMBOL:
            return NewsCollection(available=False, reason="Símbolo fuera del catálogo.")
        params["symbols"] = decision.symbol
    # The current time is a request bound, not part of the reusable cache key.
    key_params = {k: v for k, v in params.items() if k != "published_before"}
    key = "headlines:" + hashlib.sha256(json.dumps(key_params, sort_keys=True).encode()).hexdigest()
    cached = session.get(MarketContextCache, key)

    def validated(raw):
        result, seen = [], set()
        if not isinstance(raw, list):
            return result
        for item in raw[:30]:
            try:
                article = NewsItem.model_validate(item)
            except (ValidationError, TypeError):
                continue
            when = article.published_at
            if (when is None or not start <= _aware(when) <= now or str(article.url) in seen
                    or not safe_news_url(str(article.url))
                    or suspicious_passage(article.title + " " + article.description)):
                continue
            seen.add(str(article.url))
            result.append(article)
        return sorted(result, key=lambda a: a.published_at, reverse=True)[:3]

    if cached and _aware(cached.expires_at) > now:
        try:
            articles = validated(json.loads(cached.payload_json))
            logger.info("provider.headlines.cache_hit provider=marketaux")
            return NewsCollection(articles=articles, available=bool(articles),
                                  reason=None if articles else "No hay titulares verificados de hoy con esos filtros.")
        except (ValueError, TypeError):
            pass
    reason = "Configura MARKETAUX_API_KEY para consultar noticias del día; no se consultaron noticias."
    if settings.has_marketaux_key:
        try:
            reserve_daily_request(session, "marketaux", 100)
            with log_stage(logger, "provider.headlines.request", failure_level=logging.WARNING,
                           provider="marketaux"):
                response = (http_get or requests.get)(MARKETAUX_NEWS_URL,
                    params={**params, "api_token": settings.marketaux_api_key.strip()},
                    timeout=settings.http_timeout_seconds)
                response.raise_for_status()
                payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise ValueError("invalid collection")
            raw = []
            for item in payload["data"][:30]:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url") or "")[:2000]
                title = str(item.get("title") or "").strip()[:300]
                if not title or not safe_news_url(url):
                    continue
                raw.append({"title": title, "description": str(item.get("description") or "")[:1200],
                    "url": url, "provider": "Marketaux", "published_at": _published(item.get("published_at")),
                    "delayed": False, "language": str(item.get("language") or "en")[:8],
                    "source_id": "news:day:" + hashlib.sha256(url.encode()).hexdigest()[:16]})
            articles = validated(raw)
            session.merge(MarketContextCache(cache_key=key,
                payload_json=json.dumps([a.model_dump(mode="json") for a in articles]), fetched_at=now,
                expires_at=min(now + timedelta(minutes=settings.headlines_cache_minutes),
                               start + timedelta(days=1))))
            session.commit()
            logger.info("provider.headlines.done provider=marketaux outcome=success")
            return NewsCollection(articles=articles, available=bool(articles),
                reason=None if articles else "No hay titulares verificados de hoy con esos filtros.")
        except QuotaExceeded:
            reason = "Se alcanzó la cuota diaria de noticias; vuelve a intentarlo más tarde."
            logger.warning("provider.headlines.fallback provider=marketaux reason=quota")
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            reason = "No pude validar noticias nuevas de Marketaux; puede faltar acceso o conexión."
            logger.warning("provider.headlines.fallback provider=marketaux reason=provider_or_payload_error")
    else:
        logger.info("provider.headlines.skipped provider=marketaux reason=no_key")
    # Expired same-day data can still be useful, but is explicitly marked stale.
    if cached:
        try:
            articles = [a.model_copy(update={"delayed": True}) for a in validated(json.loads(cached.payload_json))]
            if articles:
                logger.warning("provider.headlines.fallback provider=cache freshness=stale")
                return NewsCollection(articles=articles, reason=reason + " Muestro el caché de hoy sin actualizar.")
        except (ValueError, TypeError):
            pass
    logger.warning("provider.headlines.unavailable provider=marketaux")
    return NewsCollection(available=False, reason=reason)
