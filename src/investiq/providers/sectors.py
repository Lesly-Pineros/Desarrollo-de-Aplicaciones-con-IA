"""FMP sector snapshots for a declared exchange, with all-or-nothing coverage."""

from datetime import datetime, timedelta, timezone
import json
import logging
import math
from zoneinfo import ZoneInfo

import requests

from investiq.data.models import MarketContextCache
from investiq.domain import SourceReference
from investiq.limits import QuotaExceeded, reserve_daily_request
from investiq.providers.news import _aware
from investiq.logging_config import log_stage

logger = logging.getLogger(__name__)

SECTOR_URL = "https://financialmodelingprep.com/stable/sector-performance-snapshot"
SECTOR_LABELS = {
    "Basic Materials": "Materiales básicos", "Communication Services": "Comunicaciones",
    "Consumer Cyclical": "Consumo cíclico", "Consumer Defensive": "Consumo defensivo",
    "Energy": "Energía", "Financial Services": "Servicios financieros", "Healthcare": "Salud",
    "Industrials": "Industriales", "Real Estate": "Inmobiliario", "Technology": "Tecnología",
    "Utilities": "Servicios públicos",
}


def validated_rows(payload, day):
    if not isinstance(payload, list) or len(payload) != len(SECTOR_LABELS):
        raise ValueError("incomplete coverage")
    seen, rows = set(), []
    for item in payload:
        if (not isinstance(item, dict) or item.get("date") != day or item.get("exchange") != "NASDAQ"
                or item.get("sector") not in SECTOR_LABELS or item["sector"] in seen):
            raise ValueError("inconsistent snapshot")
        value = item.get("averageChange")
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError("invalid percentage")
        seen.add(item["sector"])
        rows.append({"sector": item["sector"], "change_pct": float(value)})
    return sorted(rows, key=lambda row: (-row["change_pct"], row["sector"]))


def sector_snapshot(session, settings, *, http_get=None, now=None):
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    day = now.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    key = "sectors:NASDAQ:" + day
    cached = session.get(MarketContextCache, key)
    if cached and _aware(cached.expires_at) > now:
        try:
            payload = json.loads(cached.payload_json)
            logger.info("provider.sectors.cache_hit provider=fmp")
            return validated_rows(payload, day), day, cached.fetched_at, None
        except (ValueError, TypeError):
            pass
    if not settings.has_fmp_key:
        logger.info("provider.sectors.skipped provider=fmp reason=no_key")
        return [], day, now, "FMP_API_KEY no está configurada."
    try:
        reserve_daily_request(session, "fmp", 100)
        with log_stage(logger, "provider.sectors.request", failure_level=logging.WARNING,
                       provider="fmp"):
            response = (http_get or requests.get)(SECTOR_URL,
                params={"date": day, "exchange": "NASDAQ", "apikey": settings.fmp_api_key.strip()},
                timeout=settings.http_timeout_seconds)
            response.raise_for_status()
            payload = response.json()
        rows = validated_rows(payload, day)
        session.merge(MarketContextCache(cache_key=key, payload_json=json.dumps(payload), fetched_at=now,
                                         expires_at=now + timedelta(minutes=15)))
        session.commit()
        logger.info("provider.sectors.done provider=fmp outcome=success")
        return rows, day, now, None
    except QuotaExceeded:
        reason = "Se alcanzó la cuota local de consultas sectoriales."
        logger.warning("provider.sectors.fallback provider=fmp reason=quota")
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        reason = "No pude verificar un snapshot completo de FMP; revisa conexión, clave y acceso de tu plan."
        logger.warning("provider.sectors.fallback provider=fmp reason=provider_or_payload_error")
    return [], day, now, reason


def snapshot_source(day, fetched):
    return SourceReference(source_id=f"fmp:NASDAQ:{day}", title=f"FMP · once sectores NASDAQ · {day}",
        url=f"{SECTOR_URL}?date={day}&exchange=NASDAQ", provider="Financial Modeling Prep")
