"""Bounded, temporary browser sessions; persistent recall stays in memory.py."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
import secrets
import threading
import time

from investiq.domain import ConversationState


class SessionCapacityError(RuntimeError):
    """The local server is already handling its configured session limit."""


@dataclass
class BrowserSession:
    token: str
    context_version: int = 0
    state: ConversationState | None = None
    messages: list[dict] = field(default_factory=list)
    last_seen: float = field(default_factory=time.monotonic)
    active: int = 0
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)


class SessionStore:
    """Serialize turns within a browser and expire idle sessions without raw logs."""

    def __init__(self, *, max_sessions: int = 128, ttl_seconds: float = 7200):
        if max_sessions < 1 or ttl_seconds <= 0:
            raise ValueError("Session limits must be positive")
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, BrowserSession] = {}
        self._lock = threading.Lock()

    @contextmanager
    def acquire(self, token: str | None = None) -> Iterator[tuple[BrowserSession, bool]]:
        now = time.monotonic()
        with self._lock:
            expired = [key for key, item in self._sessions.items()
                       if not item.active and now - item.last_seen >= self.ttl_seconds]
            for key in expired:
                del self._sessions[key]
            item = self._sessions.get(token) if token else None
            created = item is None
            if item is None:
                if len(self._sessions) >= self.max_sessions:
                    idle = [entry for entry in self._sessions.values() if not entry.active]
                    if not idle:
                        raise SessionCapacityError("No idle browser session available")
                    del self._sessions[min(idle, key=lambda entry: entry.last_seen).token]
                item = BrowserSession(token=secrets.token_urlsafe(32))
                self._sessions[item.token] = item
            # Reserve under the registry lock so pruning never evicts an in-flight turn.
            item.active += 1
            item.last_seen = now
        try:
            with item.lock:
                yield item, created
        finally:
            with self._lock:
                item.active -= 1
                item.last_seen = time.monotonic()
