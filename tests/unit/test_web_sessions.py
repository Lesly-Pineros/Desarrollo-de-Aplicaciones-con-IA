from concurrent.futures import ThreadPoolExecutor
import threading
import time

import pytest

from investiq.web.sessions import SessionCapacityError, SessionStore


def test_sessions_are_opaque_reused_and_expire(monkeypatch):
    clock = [10.0]
    monkeypatch.setattr("investiq.web.sessions.time.monotonic", lambda: clock[0])
    store = SessionStore(ttl_seconds=30)
    with store.acquire("attacker-selected-token") as (first, created):
        assert created
        assert first.token != "attacker-selected-token"
        token = first.token
        first.messages.append({"role": "user", "content": "temporal"})
    clock[0] = 20
    with store.acquire(token) as (same, created):
        assert not created
        assert same.messages[0]["content"] == "temporal"
    clock[0] = 51
    with store.acquire(token) as (fresh, created):
        assert created
        assert fresh.token != token
        assert fresh.messages == []


def test_capacity_never_evicts_an_active_session():
    store = SessionStore(max_sessions=1)
    with store.acquire() as (active, _):
        token = active.token
        with pytest.raises(SessionCapacityError):
            with store.acquire():
                pass
    with store.acquire() as (replacement, created):
        assert created
        assert replacement.token != token


def test_turns_from_the_same_browser_are_serialized():
    store = SessionStore()
    with store.acquire() as (browser, _):
        token = browser.token
    inside = 0
    overlapping = []
    count_lock = threading.Lock()

    def turn(index):
        nonlocal inside
        with store.acquire(token) as (session, created):
            assert not created
            with count_lock:
                inside += 1
                overlapping.append(inside)
            time.sleep(0.003)
            session.messages.append({"content": str(index)})
            with count_lock:
                inside -= 1

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(turn, range(8)))
    assert max(overlapping) == 1
    with store.acquire(token) as (session, _):
        assert len(session.messages) == 8
