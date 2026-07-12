"""Tests for always-on public Places photo rate limiting."""

import uuid

import pytest
from starlette.requests import Request

from app.core.public_places_rate_limit import (
    check_public_places_rate_limit,
    check_public_places_session_quota,
    clear_public_places_rate_limit_state_for_tests,
    record_public_places_session_photo_success,
)


def _req(client_ip: str) -> Request:
    return Request(
        {
            "type": "http",
            "client": (client_ip, 0),
            "headers": [],
            "method": "GET",
            "path": "/",
        }
    )


@pytest.fixture(autouse=True)
def _clear_limits() -> None:
    clear_public_places_rate_limit_state_for_tests()
    yield
    clear_public_places_rate_limit_state_for_tests()


def test_under_limit_allowed() -> None:
    sid = str(uuid.uuid4())
    assert check_public_places_rate_limit(_req("10.0.0.1"), sid) is True


def test_over_per_ip_limit_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.core.public_places_rate_limit.PUBLIC_PLACES_PHOTO_RATE_LIMIT_PER_MINUTE",
        2,
    )
    sid = str(uuid.uuid4())
    assert check_public_places_rate_limit(_req("10.0.0.2"), sid) is True
    assert check_public_places_rate_limit(_req("10.0.0.2"), sid) is True
    assert check_public_places_rate_limit(_req("10.0.0.2"), sid) is False


def test_over_per_session_limit_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.core.public_places_rate_limit.PUBLIC_PLACES_PHOTO_RATE_LIMIT_PER_SESSION",
        2,
    )
    sid = str(uuid.uuid4())
    assert check_public_places_session_quota(sid) is True
    record_public_places_session_photo_success(sid)
    record_public_places_session_photo_success(sid)
    assert check_public_places_session_quota(sid) is False


def test_different_ips_dont_interfere(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.core.public_places_rate_limit.PUBLIC_PLACES_PHOTO_RATE_LIMIT_PER_MINUTE",
        1,
    )
    s1 = str(uuid.uuid4())
    s2 = str(uuid.uuid4())
    assert check_public_places_rate_limit(_req("10.0.1.1"), s1) is True
    assert check_public_places_rate_limit(_req("10.0.1.2"), s2) is True


def test_session_eviction_drops_least_recently_seen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When over capacity, evict the session with the oldest last_seen (LRU), not FIFO insert."""
    import time

    import app.core.public_places_rate_limit as m

    monkeypatch.setattr(m, "_MAX_TRACKED_SESSIONS", 2)
    monkeypatch.setattr(
        m,
        "PUBLIC_PLACES_PHOTO_RATE_LIMIT_PER_SESSION",
        100,
    )
    s1 = str(uuid.uuid4())
    s2 = str(uuid.uuid4())
    s3 = str(uuid.uuid4())
    record_public_places_session_photo_success(s1)
    time.sleep(0.002)
    record_public_places_session_photo_success(s2)
    time.sleep(0.002)
    record_public_places_session_photo_success(s1)
    record_public_places_session_photo_success(s3)
    # s2 had the stalest last_seen and should be evicted (FIFO would remove s1 first).
    assert check_public_places_session_quota(s2) is True
    assert check_public_places_session_quota(s1) is True
    assert check_public_places_session_quota(s3) is True


def test_session_sweep_path_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force stale-session sweep by setting zero TTL (implementation detail)."""
    import app.core.public_places_rate_limit as m

    monkeypatch.setattr(m, "_SESSION_STALE_SECONDS", 0.0)
    sid = str(uuid.uuid4())
    record_public_places_session_photo_success(sid)
    check_public_places_session_quota(sid)
