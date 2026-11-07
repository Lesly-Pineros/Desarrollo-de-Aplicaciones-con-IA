import json
import logging
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from pydantic import ValidationError
from sqlmodel import Session

from investiq.data.models import FilingCacheEntry
from investiq.domain import FilingItem
from investiq.instruments import INSTRUMENT_BY_SYMBOL
from investiq.limits import provider_rate_limiter
from investiq.settings import Settings
from investiq.logging_config import log_stage

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
_ticker_map: dict[str, str] | None = None
_ticker_map_lock = threading.Lock()
logger = logging.getLogger(__name__)


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _fetch_json(url: str, settings: Settings, http_get) -> dict[str, Any]:
    provider_rate_limiter.acquire("sec_edgar", 10, 1.0)
    response = http_get(
        url,
        headers={"User-Agent": settings.sec_user_agent.strip(), "Accept-Encoding": "gzip, deflate"},
        timeout=settings.http_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("unexpected SEC response")
    return payload


def _company_map(settings: Settings, http_get) -> dict[str, str]:
    global _ticker_map
    if _ticker_map is not None:
        return _ticker_map
    with _ticker_map_lock:
        if _ticker_map is not None:
            return _ticker_map
        payload = _fetch_json(SEC_TICKERS_URL, settings, http_get)
        mapping: dict[str, str] = {}
        for company in payload.values():
            ticker = str(company.get("ticker", "")).upper()
            cik = company.get("cik_str")
            if ticker and cik:
                mapping[ticker] = f"{int(cik):010d}"
        _ticker_map = mapping
        return mapping


def _decode_cache(entry: FilingCacheEntry, *, delayed: bool = False) -> list[FilingItem]:
    items = []
    for raw in json.loads(entry.filings_json):
        try:
            item = FilingItem.model_validate(raw)
            if delayed:
                item.source_id = f"{item.source_id}:cached"
            items.append(item)
        except ValidationError:
            continue
    return items


def sec_docs(
    session: Session,
    symbol: str,
    settings: Settings,
    *,
    http_get=requests.get,
    limit: int = 5,
) -> tuple[list[FilingItem], str | None]:
    symbol = symbol.strip().upper()
    if symbol not in INSTRUMENT_BY_SYMBOL:
        return [], "Símbolo fuera del universo cubierto."
    cache = session.get(FilingCacheEntry, symbol)
    now = datetime.now(timezone.utc)
    if cache and _aware(cache.expires_at) > now:
        logger.info("provider.filings.cache_hit provider=sec")
        return _decode_cache(cache), None
    if not settings.sec_user_agent.strip() or not re.search(r"[^\s@]+@[^\s@]+\.[^\s@]+", settings.sec_user_agent):
        if cache:
            logger.warning("provider.filings.fallback provider=sec reason=missing_contact cache=stale")
            return _decode_cache(cache, delayed=True), "SEC_USER_AGENT con contacto es obligatorio; se muestra caché histórica."
        logger.warning("provider.filings.skipped provider=sec reason=missing_contact")
        return [], "Configura SEC_USER_AGENT con nombre y contacto antes de consultar filings de la SEC."

    try:
        with log_stage(logger, "provider.filings.company_map", failure_level=logging.WARNING,
                       provider="sec"):
            ticker_map = _company_map(settings, http_get)
        cik = ticker_map.get(symbol)
        if not cik:
            logger.warning("provider.filings.unavailable provider=sec reason=symbol_mapping_missing")
            return [], "La SEC no tiene un identificador asociado a este símbolo."
        with log_stage(logger, "provider.filings.submissions", failure_level=logging.WARNING,
                       provider="sec"):
            submission = _fetch_json(SEC_SUBMISSIONS_URL.format(cik=cik), settings, http_get)
        recent = submission.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        documents = recent.get("primaryDocument", [])
        filings = []
        for form, filed, accession, document in zip(forms, dates, accessions, documents):
            if form not in {"10-K", "10-Q", "8-K"}:
                continue
            accession_path = str(accession).replace("-", "")
            url = f"{SEC_ARCHIVES_URL}/{int(cik)}/{accession_path}/{document}"
            filings.append(
                FilingItem(
                    form=form,
                    filing_date=str(filed),
                    url=url,
                    accession=str(accession),
                    source_id=f"sec:{symbol}:{accession}",
                )
            )
            if len(filings) >= max(1, min(limit, 10)):
                break
        session.merge(
            FilingCacheEntry(
                symbol=symbol,
                filings_json=json.dumps([item.model_dump(mode="json") for item in filings], ensure_ascii=False),
                fetched_at=now,
                expires_at=now + timedelta(hours=settings.filing_cache_hours),
            )
        )
        session.commit()
        logger.info("provider.filings.done provider=sec outcome=success")
        return filings, None if filings else "La SEC no devolvió filings recientes de los formularios permitidos."
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
        if cache:
            logger.warning("provider.filings.fallback provider=sec reason=provider_or_payload_error cache=stale")
            return _decode_cache(cache, delayed=True), "La SEC no respondió; se muestra la caché histórica."
        logger.warning("provider.filings.unavailable provider=sec reason=provider_or_payload_error")
        return [], "No se pudo validar la respuesta de la SEC."
