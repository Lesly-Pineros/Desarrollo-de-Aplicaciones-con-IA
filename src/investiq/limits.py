from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock
from time import monotonic, sleep

from sqlmodel import Session

from investiq.data.models import ProviderUsage


class QuotaExceeded(RuntimeError):
    pass


def reserve_daily_request(session: Session, provider: str, limit: int) -> None:
    day = datetime.now(timezone.utc).date().isoformat()
    key = f"{provider}:{day}"
    usage = session.get(ProviderUsage, key)
    if usage and usage.request_count >= limit:
        raise QuotaExceeded(f"daily request quota reached for {provider}")
    if usage is None:
        session.add(ProviderUsage(quota_key=key, provider=provider, request_count=1))
    else:
        usage.request_count += 1
        usage.updated_at = datetime.now(timezone.utc)
        session.add(usage)
    session.commit()


class SlidingWindowRateLimiter:
    """Small process-local limiter; daily quotas are persisted separately."""

    def __init__(self):
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def acquire(self, provider: str, limit: int, window_seconds: float = 60.0) -> None:
        if limit < 1 or window_seconds <= 0:
            raise ValueError("rate limit and window must be positive")
        while True:
            with self._lock:
                now = monotonic()
                events = self._events[provider]
                while events and now - events[0] >= window_seconds:
                    events.popleft()
                if len(events) < limit:
                    events.append(now)
                    return
                wait_for = max(0.01, window_seconds - (now - events[0]))
            sleep(wait_for)


provider_rate_limiter = SlidingWindowRateLimiter()
