from datetime import datetime, time, timedelta, timezone
import logging
import math

import requests
from sqlmodel import Session, select

from investiq.data.models import PriceBar, PriceCacheEntry
from investiq.domain import QuoteResult, SourceReference
from investiq.instruments import QUOTE_INSTRUMENT_BY_SYMBOL
from investiq.limits import QuotaExceeded, provider_rate_limiter, reserve_daily_request
from investiq.settings import Settings
from investiq.logging_config import log_stage

TWELVE_DATA_QUOTE_URL = "https://api.twelvedata.com/quote"
logger = logging.getLogger(__name__)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _quote_from_cache(entry: PriceCacheEntry, *, expired: bool = False) -> QuoteResult:
    source = SourceReference(
        source_id=f"price:{entry.symbol}:{entry.provider}",
        title=f"Precio de {entry.symbol} — {entry.provider}" + (" (histórico/demorado)" if entry.delayed or expired else ""),
        url=entry.source_url,
        provider=entry.provider,
        published_at=_aware(entry.as_of),
        delayed=entry.delayed or expired,
    )
    return QuoteResult(
        symbol=entry.symbol,
        price=entry.price,
        change_abs=entry.change_abs,
        change_pct=entry.change_pct,
        as_of=_aware(entry.as_of),
        provider=entry.provider,
        delayed=entry.delayed or expired,
        source=source,
    )


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return _aware(value)
    if value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return _aware(parsed)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _historical_quote(session: Session, symbol: str) -> QuoteResult | None:
    bars = session.exec(
        select(PriceBar).where(PriceBar.symbol == symbol).order_by(PriceBar.date.desc()).limit(2)
    ).all()
    if not bars:
        return None
    current = bars[0]
    previous = bars[1] if len(bars) > 1 else None
    change = current.adjusted_close - previous.adjusted_close if previous else None
    change_pct = change / previous.adjusted_close * 100 if previous and previous.adjusted_close else None
    as_of = datetime.combine(current.date, time(23, 59), tzinfo=timezone.utc)
    result = QuoteResult(
        symbol=symbol,
        price=current.adjusted_close,
        change_abs=change,
        change_pct=change_pct,
        as_of=as_of,
        provider="yfinance histórico",
        delayed=True,
        source=SourceReference(
            source_id=f"price:{symbol}:yfinance",
            title=f"Histórico ajustado de {symbol} en Yahoo Finance (no es tiempo real)",
            url=f"https://finance.yahoo.com/quote/{symbol}/",
            provider="yfinance histórico",
            published_at=as_of,
            delayed=True,
        ),
    )
    return result


def _store_quote(session: Session, quote: QuoteResult, ttl: timedelta) -> None:
    if quote.price is None or quote.as_of is None or quote.source is None:
        return
    session.merge(
        PriceCacheEntry(
            symbol=quote.symbol,
            price=quote.price,
            change_abs=quote.change_abs,
            change_pct=quote.change_pct,
            as_of=quote.as_of,
            fetched_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + ttl,
            provider=quote.provider or "unknown",
            delayed=quote.delayed,
            source_url=str(quote.source.url),
        )
    )
    session.commit()


def market_quote(
    session: Session,
    symbol: str,
    settings: Settings,
    *,
    http_get=requests.get,
) -> QuoteResult:
    """Prefer Twelve Data; otherwise return explicitly dated yfinance history."""
    symbol = symbol.strip().upper()
    if symbol not in QUOTE_INSTRUMENT_BY_SYMBOL:
        return QuoteResult(symbol=symbol, error="Símbolo fuera del universo cubierto.")

    now = datetime.now(timezone.utc)
    cached = session.get(PriceCacheEntry, symbol)
    if cached and _aware(cached.expires_at) > now:
        cached_provider = cached.provider if cached.provider in {"Twelve Data", "yfinance histórico"} else "other"
        logger.info("provider.quote.cache_hit provider=%s", cached_provider)
        return _quote_from_cache(cached)
    logger.debug("provider.quote.cache_miss")

    provider_error = None
    if settings.has_twelve_data_key:
        try:
            provider_rate_limiter.acquire("twelve_data", 8, 60.0)
            reserve_daily_request(session, "twelve_data", 800)
            with log_stage(logger, "provider.quote.request", failure_level=logging.WARNING,
                           provider="twelve_data"):
                response = http_get(
                    TWELVE_DATA_QUOTE_URL,
                    params={"symbol": symbol, "apikey": settings.twelve_data_api_key.strip()},
                    timeout=settings.http_timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
            if payload.get("status") == "error" or "close" not in payload:
                raise ValueError("invalid quote response")
            price = float(payload["close"])
            change = float(payload["change"]) if payload.get("change") not in (None, "") else None
            change_pct = float(payload["percent_change"]) if payload.get("percent_change") not in (None, "") else None
            if not math.isfinite(price) or price <= 0 or (change is not None and not math.isfinite(change)) or (
                change_pct is not None and not math.isfinite(change_pct)
            ):
                raise ValueError("invalid quote values")
            as_of = _parse_datetime(payload.get("datetime"))
            quote = QuoteResult(
                symbol=symbol,
                price=price,
                change_abs=change,
                change_pct=change_pct,
                as_of=as_of,
                provider="Twelve Data",
                source=SourceReference(
                    source_id=f"price:{symbol}:twelve_data:{as_of.date()}",
                    title=f"Cotización Twelve Data de {symbol}",
                    url=f"https://twelvedata.com/markets/stocks/{symbol}",
                    provider="Twelve Data",
                    published_at=as_of,
                ),
            )
            _store_quote(session, quote, timedelta(minutes=settings.price_cache_minutes))
            logger.info("provider.quote.done provider=twelve_data freshness=provider")
            return quote
        except QuotaExceeded:
            provider_error = "Se alcanzó la cuota diaria de cotizaciones; se usa el dato histórico disponible."
            logger.warning("provider.quote.fallback provider=twelve_data reason=quota")
        except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
            provider_error = "No se pudo validar la cotización en vivo; se usa el dato histórico disponible."
            logger.warning("provider.quote.fallback provider=twelve_data reason=provider_or_payload_error")
    else:
        logger.info("provider.quote.skipped provider=twelve_data reason=no_key")

    if cached:
        quote = _quote_from_cache(cached, expired=True)
        quote.error = provider_error
        logger.info("provider.quote.fallback provider=cache freshness=stale")
        return quote

    quote = _historical_quote(session, symbol)
    if quote:
        _store_quote(session, quote, timedelta(minutes=settings.price_cache_minutes))
        quote.error = provider_error
        logger.info("provider.quote.fallback provider=yfinance_historical available=true")
        return quote
    logger.warning("provider.quote.unavailable")
    return QuoteResult(symbol=symbol, error=provider_error or "No hay precio verificable en caché ni histórico local.")
