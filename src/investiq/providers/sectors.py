"""FMP sector snapshots for NASDAQ and an explicitly calculated S&P 500 view."""

from collections import defaultdict
import csv
from datetime import datetime, timedelta, timezone
import io
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
SP500_URL = "https://financialmodelingprep.com/stable/sp500-constituent"
EOD_BULK_URL = "https://financialmodelingprep.com/stable/eod-bulk"
NEW_YORK = ZoneInfo("America/New_York")
SECTOR_LABELS = {
    "Basic Materials": "Materiales básicos", "Communication Services": "Comunicaciones",
    "Consumer Cyclical": "Consumo cíclico", "Consumer Defensive": "Consumo defensivo",
    "Energy": "Energía", "Financial Services": "Servicios financieros", "Healthcare": "Salud",
    "Industrials": "Industriales", "Real Estate": "Inmobiliario", "Technology": "Tecnología",
    "Utilities": "Servicios públicos",
}
SP500_SECTORS = {
    "Basic Materials": "Basic Materials", "Materials": "Basic Materials",
    "Communication Services": "Communication Services",
    "Consumer Cyclical": "Consumer Cyclical", "Consumer Discretionary": "Consumer Cyclical",
    "Consumer Defensive": "Consumer Defensive", "Consumer Staples": "Consumer Defensive",
    "Energy": "Energy", "Financial Services": "Financial Services", "Financials": "Financial Services",
    "Healthcare": "Healthcare", "Health Care": "Healthcare", "Industrials": "Industrials",
    "Real Estate": "Real Estate", "Technology": "Technology", "Information Technology": "Technology",
    "Utilities": "Utilities",
}
SECTOR_ETFS = {
    "Basic Materials": "XLB", "Communication Services": "XLC",
    "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP", "Energy": "XLE",
    "Financial Services": "XLF", "Healthcare": "XLV", "Industrials": "XLI",
    "Real Estate": "XLRE", "Technology": "XLK", "Utilities": "XLU",
}
SECTOR_ETF_GUIDE = "https://www.ssga.com/us/en/individual/capabilities/equities/sector-investing/select-sector-etfs"


def validated_rows(payload, day, exchange="NASDAQ"):
    if not isinstance(payload, list) or len(payload) != len(SECTOR_LABELS):
        raise ValueError("incomplete coverage")
    seen, rows = set(), []
    for item in payload:
        if (not isinstance(item, dict) or item.get("date") != day or item.get("exchange") != exchange
                or item.get("sector") not in SECTOR_LABELS or item["sector"] in seen):
            raise ValueError("inconsistent snapshot")
        value = item.get("averageChange")
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError("invalid percentage")
        seen.add(item["sector"])
        rows.append({"sector": item["sector"], "change_pct": float(value)})
    return sorted(rows, key=lambda row: (-row["change_pct"], row["sector"]))


def _cache_read(session, key, now):
    cached = session.get(MarketContextCache, key)
    if not cached or _aware(cached.expires_at) <= now:
        return None
    try:
        record = json.loads(cached.payload_json)
        rows = record["rows"]
        day = record["date"]
        if not isinstance(rows, list) or not isinstance(day, str):
            return None
        return rows, day, cached.fetched_at
    except (ValueError, TypeError, KeyError):
        return None


def _cache_write(session, key, rows, day, now, ttl_minutes=15):
    payload = json.dumps({"rows": rows, "date": day}, ensure_ascii=False)
    session.merge(MarketContextCache(cache_key=key, payload_json=payload, fetched_at=now,
                                     expires_at=now + timedelta(minutes=ttl_minutes)))
    session.commit()


def _business_days(now, limit=8):
    day = now.astimezone(NEW_YORK).date()
    result = []
    for offset in range(0, 12):
        candidate = day - timedelta(days=offset)
        if candidate.weekday() < 5:
            result.append(candidate.isoformat())
            if len(result) >= limit:
                break
    return result


def _provider_error(error):
    if isinstance(error, requests.Timeout):
        return "La consulta a FMP agotó el tiempo de espera."
    if isinstance(error, requests.ConnectionError):
        return "No pude conectar con FMP."
    if isinstance(error, requests.HTTPError):
        status = getattr(getattr(error, "response", None), "status_code", None)
        if status in {401, 403}:
            return "FMP rechazó el acceso a este endpoint; puede depender de la clave o del plan de la cuenta."
        return "FMP respondió con un error al consultar los datos sectoriales."
    return "FMP devolvió datos con un formato o cobertura inesperados."


def _request_json(http_get, url, params, settings):
    response = http_get(url, params=params, timeout=settings.http_timeout_seconds)
    response.raise_for_status()
    return response.json()


def _nasdaq_snapshot(session, settings, http_get, now):
    cached = _cache_read(session, "sectors:NASDAQ:latest", now)
    if cached:
        rows, day, fetched = cached
        try:
            if (len(rows) != len(SECTOR_LABELS) or {row.get("sector") for row in rows} != set(SECTOR_LABELS)
                    or any(isinstance(row.get("change_pct"), bool)
                           or not isinstance(row.get("change_pct"), (int, float))
                           or not math.isfinite(row["change_pct"]) for row in rows)):
                raise ValueError("invalid cached snapshot")
            rows = sorted(rows, key=lambda row: (-row["change_pct"], row["sector"]))
        except (AttributeError, TypeError, ValueError):
            rows = None
        if rows is not None:
            logger.info("provider.sectors.cache_hit provider=fmp universe=NASDAQ")
            return rows, day, fetched, None
    last_error = None
    saw_empty = False
    for day in _business_days(now):
        try:
            reserve_daily_request(session, "fmp", 100)
            with log_stage(logger, "provider.sectors.request", failure_level=logging.WARNING,
                           provider="fmp", universe="NASDAQ", market_day=day):
                payload = _request_json(http_get, SECTOR_URL,
                    {"date": day, "exchange": "NASDAQ", "apikey": settings.fmp_api_key.strip()}, settings)
            if payload == []:
                saw_empty = True
                continue
            rows = validated_rows(payload, day)
            _cache_write(session, "sectors:NASDAQ:latest", rows, day, now)
            logger.info("provider.sectors.done provider=fmp universe=NASDAQ market_day=%s", day)
            return rows, day, now, None
        except QuotaExceeded:
            return [], day, now, "Se alcanzó la cuota local de consultas a FMP."
        except requests.RequestException as error:
            return [], day, now, _provider_error(error)
        except (ValueError, TypeError, AttributeError) as error:
            last_error = _provider_error(error)
            logger.warning("provider.sectors.invalid provider=fmp universe=NASDAQ market_day=%s", day)
    if saw_empty:
        return [], _business_days(now)[0], now, "FMP no publicó un snapshot sectorial reciente para los últimos días de mercado."
    return [], _business_days(now)[0], now, last_error or "FMP no devolvió un snapshot sectorial utilizable."


def _constituents(payload):
    if not isinstance(payload, list) or len(payload) < 450:
        raise ValueError("incomplete S&P 500 membership")
    sectors, seen = {}, set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("invalid constituent")
        symbol, sector = item.get("symbol"), SP500_SECTORS.get(item.get("sector"))
        if not isinstance(symbol, str) or not symbol.strip() or not sector or symbol in seen:
            raise ValueError("invalid constituent")
        seen.add(symbol)
        sectors[symbol] = sector
    return sectors


def _eod_rows(response):
    content = response.text.lstrip("\ufeff").strip()
    if not content:
        return []
    if content.startswith("["):
        payload = json.loads(content)
        if not isinstance(payload, list):
            raise ValueError("invalid EOD payload")
        return payload
    if content.startswith("{"):
        raise ValueError("FMP returned an EOD error object")
    return list(csv.DictReader(io.StringIO(content)))


def _prices_by_symbol(payload, day, constituents):
    if not isinstance(payload, list):
        raise ValueError("invalid EOD rows")
    prices, seen = {}, set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("invalid EOD row")
        symbol = item.get("symbol")
        if symbol not in constituents:
            continue
        if symbol in seen or item.get("date") != day:
            raise ValueError("duplicate or inconsistent EOD row")
        close = item.get("close")
        try:
            close = float(close)
        except (TypeError, ValueError):
            raise ValueError("invalid EOD close") from None
        if not math.isfinite(close) or close <= 0:
            raise ValueError("invalid EOD close")
        seen.add(symbol)
        prices[symbol] = close
    if seen != set(constituents):
        return None
    return prices


def _sp500_rows(constituents, current_prices, previous_prices):
    changes = defaultdict(list)
    for symbol, current_close in current_prices.items():
        previous_close = previous_prices[symbol]
        changes[constituents[symbol]].append((current_close / previous_close - 1) * 100)
    if set(changes) != set(SECTOR_LABELS):
        raise ValueError("inconsistent sector coverage")
    rows = [{"sector": sector, "change_pct": sum(values) / len(values), "member_count": len(values)}
            for sector, values in changes.items()]
    return sorted(rows, key=lambda row: (-row["change_pct"], row["sector"]))


def _sp500_snapshot(session, settings, http_get, now):
    cached = _cache_read(session, "sectors:SP500:latest", now)
    if cached:
        rows, day, fetched = cached
        logger.info("provider.sectors.cache_hit provider=fmp universe=SP500")
        return rows, day, fetched, None
    try:
        reserve_daily_request(session, "fmp", 100)
        with log_stage(logger, "provider.sectors.constituents", failure_level=logging.WARNING, provider="fmp"):
            members = _constituents(_request_json(http_get, SP500_URL,
                {"apikey": settings.fmp_api_key.strip()}, settings))
        days = _business_days(now)
        current_prices = None
        current_day_index = None
        for index, day in enumerate(days):
            reserve_daily_request(session, "fmp", 100)
            with log_stage(logger, "provider.sectors.eod", failure_level=logging.WARNING,
                           provider="fmp", universe="SP500", market_day=day):
                response = http_get(EOD_BULK_URL,
                    params={"date": day, "apikey": settings.fmp_api_key.strip()},
                    timeout=settings.http_timeout_seconds)
                response.raise_for_status()
                payload = _eod_rows(response)
            current_prices = _prices_by_symbol(payload, day, members)
            if current_prices is not None:
                current_day_index = index
                break
        if current_prices is None or current_day_index is None:
            return [], days[0], now, "FMP no publicó cierres completos recientes para los componentes del S&P 500."

        previous_prices = None
        for day in days[current_day_index + 1:]:
            reserve_daily_request(session, "fmp", 100)
            with log_stage(logger, "provider.sectors.eod", failure_level=logging.WARNING,
                           provider="fmp", universe="SP500", market_day=day):
                response = http_get(EOD_BULK_URL,
                    params={"date": day, "apikey": settings.fmp_api_key.strip()},
                    timeout=settings.http_timeout_seconds)
                response.raise_for_status()
                payload = _eod_rows(response)
            previous_prices = _prices_by_symbol(payload, day, members)
            if previous_prices is not None:
                break
        if previous_prices is None:
            return [], days[current_day_index], now, "FMP no publicó cierres completos del día anterior para calcular la variación diaria."
        day = days[current_day_index]
        rows = _sp500_rows(members, current_prices, previous_prices)
        _cache_write(session, "sectors:SP500:latest", rows, day, now, ttl_minutes=15)
        logger.info("provider.sectors.done provider=fmp universe=SP500 market_day=%s members=%d", day, len(current_prices))
        return rows, day, now, None
    except QuotaExceeded:
        reason = "Se alcanzó la cuota local de consultas a FMP."
    except requests.RequestException as error:
        reason = _provider_error(error)
    except (ValueError, TypeError, AttributeError, OverflowError) as error:
        reason = _provider_error(error)
    logger.warning("provider.sectors.fallback provider=fmp universe=SP500 reason=data_unavailable")
    return [], now.astimezone(NEW_YORK).date().isoformat(), now, reason


def _download_sector_etfs(symbols, timeout):
    import yfinance as yf

    return yf.download(symbols, period="14d", interval="1d", auto_adjust=False,
                       progress=False, threads=False, timeout=timeout)


def _sector_etf_rows(history, now):
    if history is None or getattr(history, "empty", True) or "Close" not in history:
        raise ValueError("missing sector ETF closes")
    closes = history["Close"]
    symbols = set(SECTOR_ETFS.values())
    if not symbols.issubset(set(closes.columns)):
        raise ValueError("incomplete sector ETF coverage")
    valid = []
    seen_days = set()
    today = now.astimezone(NEW_YORK).date().isoformat()
    for timestamp, values in closes.iterrows():
        day = timestamp.date().isoformat()
        if day > today:
            continue
        if day in seen_days:
            raise ValueError("duplicate sector ETF date")
        seen_days.add(day)
        prices = {}
        for symbol in symbols:
            try:
                close = float(values[symbol])
            except (TypeError, ValueError, KeyError):
                break
            if not math.isfinite(close) or close <= 0:
                break
            prices[symbol] = close
        if len(prices) == len(symbols):
            valid.append((day, prices))
    if len(valid) < 2 or valid[-1][0] not in _business_days(now):
        raise ValueError("no two recent complete sector ETF sessions")
    day, current = valid[-1]
    _, previous = valid[-2]
    rows = [{"sector": sector, "proxy_symbol": symbol,
             "change_pct": (current[symbol] / previous[symbol] - 1) * 100}
            for sector, symbol in SECTOR_ETFS.items()]
    return sorted(rows, key=lambda row: (-row["change_pct"], row["sector"])), day


def _sp500_etf_snapshot(session, settings, now, history_fetch):
    cached = _cache_read(session, "sectors:SP500:etf:latest", now)
    if cached:
        rows, day, fetched = cached
        if (len(rows) == len(SECTOR_ETFS)
                and {row.get("sector"): row.get("proxy_symbol") for row in rows} == SECTOR_ETFS
                and all(isinstance(row.get("change_pct"), (int, float))
                            and not isinstance(row["change_pct"], bool)
                            and math.isfinite(row["change_pct"]) for row in rows)):
            logger.info("provider.sectors.cache_hit provider=yahoo universe=SP500 method=etf")
            return rows, day, fetched, None
    try:
        with log_stage(logger, "provider.sectors.etf_history", failure_level=logging.WARNING,
                       provider="yahoo", universe="SP500"):
            history = history_fetch(list(SECTOR_ETFS.values()), settings.http_timeout_seconds)
        rows, day = _sector_etf_rows(history, now)
        _cache_write(session, "sectors:SP500:etf:latest", rows, day, now)
        logger.info("provider.sectors.done provider=yahoo universe=SP500 method=etf market_day=%s", day)
        return rows, day, now, None
    except Exception:
        logger.warning("provider.sectors.fallback_unavailable provider=yahoo universe=SP500")
        return [], now.astimezone(NEW_YORK).date().isoformat(), now, (
            "No pude verificar dos cierres recientes y completos para los once ETF sectoriales del S&P 500.")


def sector_snapshot(session, settings, *, universe="NASDAQ", http_get=None, now=None, history_fetch=None):
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    getter = http_get or requests.get
    if universe == "NASDAQ":
        if not settings.has_fmp_key:
            logger.info("provider.sectors.skipped provider=fmp reason=no_key")
            return [], now.astimezone(NEW_YORK).date().isoformat(), now, "FMP_API_KEY no está configurada."
        return _nasdaq_snapshot(session, settings, getter, now)
    if universe == "S&P 500":
        fmp_error = None
        if settings.has_fmp_key:
            rows, day, fetched, fmp_error = _sp500_snapshot(session, settings, getter, now)
            if rows:
                return rows, day, fetched, None
        if not settings.sector_etf_fallback_enabled:
            return [], now.astimezone(NEW_YORK).date().isoformat(), now, (
                fmp_error or "La consulta sectorial externa está desactivada en esta ejecución.")
        rows, day, fetched, fallback_error = _sp500_etf_snapshot(
            session, settings, now, history_fetch or _download_sector_etfs)
        if rows:
            return rows, day, fetched, None
        return rows, day, fetched, (f"{fmp_error} {fallback_error}" if fmp_error else fallback_error)
    raise ValueError("unsupported sector universe")


def snapshot_sources(universe, day, fetched, *, proxy=False):
    if universe == "S&P 500" and proxy:
        return [SourceReference(source_id="ssga:select-sector-etfs", title="State Street · ETF de los once sectores S&P 500",
                                url=SECTOR_ETF_GUIDE, provider="State Street")] + [
            SourceReference(source_id=f"yahoo:{symbol}:{day}", title=f"Yahoo Finance · cierres de {symbol} · {day}",
                            url=f"https://finance.yahoo.com/quote/{symbol}/history/", provider="Yahoo Finance")
            for symbol in SECTOR_ETFS.values()]
    if universe == "S&P 500":
        return [
            SourceReference(source_id=f"fmp:sp500-constituents:{day}", title=f"FMP · componentes del S&P 500 · {day}",
                            url=SP500_URL, provider="Financial Modeling Prep"),
            SourceReference(source_id=f"fmp:sp500-eod:{day}", title=f"FMP · cierres diarios de componentes S&P 500 · {day}",
                            url=f"{EOD_BULK_URL}?date={day}", provider="Financial Modeling Prep"),
        ]
    return [SourceReference(source_id=f"fmp:NASDAQ:{day}", title=f"FMP · once sectores NASDAQ · {day}",
                            url=f"{SECTOR_URL}?date={day}&exchange=NASDAQ", provider="Financial Modeling Prep")]
