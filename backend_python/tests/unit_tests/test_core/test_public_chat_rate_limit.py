"""Tests for in-memory public chat rate limiter."""

from collections import defaultdict, deque
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request

from app.core import public_chat_rate_limit as rl


def _http_request(
    *,
    client_host: str = "198.51.100.10",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/public/chat/message",
        "raw_path": b"/api/public/chat/message",
        "query_string": b"",
        "headers": headers or [],
        "client": (client_host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


@pytest.fixture(autouse=True)
def _reset_public_chat_rate_limit_globals() -> None:
    with rl._timestamps_lock:
        rl._timestamps.clear()
    with rl._session_message_lock:
        rl._session_message_counts.clear()
    yield
    with rl._timestamps_lock:
        rl._timestamps.clear()
    with rl._session_message_lock:
        rl._session_message_counts.clear()


def test_evict_if_over_capacity_trims_tracked_ips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rl, "_MAX_TRACKED_UNIQUE_IPS", 2)
    with rl._timestamps_lock:
        rl._timestamps.clear()
        rl._timestamps["a"].append(1.0)
        rl._timestamps["b"].append(2.0)
        rl._timestamps["c"].append(3.0)
        rl._evict_if_over_capacity(rl._timestamps)
        assert len(rl._timestamps) == 2
        assert "a" not in rl._timestamps


def test_evict_if_over_capacity_noop_when_under_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rl, "_MAX_TRACKED_UNIQUE_IPS", 10)
    d: defaultdict[str, deque[float]] = defaultdict(deque)
    d["x"].append(1.0)
    rl._evict_if_over_capacity(d)
    assert len(d) == 1


@patch("app.core.public_chat_rate_limit.settings")
def test_check_public_chat_rate_limit_allows_then_blocks(
    mock_settings: MagicMock,
) -> None:
    """With RATE_LIMIT_ENABLED, Nth+1 request from same effective IP returns False."""
    mock_settings.RATE_LIMIT_ENABLED = True
    mock_settings.TRUST_X_FORWARDED_FOR = False
    mock_settings.PUBLIC_CHAT_MESSAGES_PER_MINUTE = 3

    req = _http_request(client_host="198.51.100.1")
    assert rl.check_public_chat_rate_limit(req) is True
    assert rl.check_public_chat_rate_limit(req) is True
    assert rl.check_public_chat_rate_limit(req) is True
    assert rl.check_public_chat_rate_limit(req) is False


@patch("app.core.public_chat_rate_limit.settings")
def test_check_public_chat_rate_limit_bypass_when_disabled(
    mock_settings: MagicMock,
) -> None:
    mock_settings.RATE_LIMIT_ENABLED = False
    mock_settings.PUBLIC_CHAT_MESSAGES_PER_MINUTE = 1
    req = _http_request(client_host="198.51.100.2")
    assert rl.check_public_chat_rate_limit(req) is True
    assert rl.check_public_chat_rate_limit(req) is True


@patch("app.core.public_chat_rate_limit.settings")
def test_get_client_ip_uses_x_forwarded_for_when_trusted(
    mock_settings: MagicMock,
) -> None:
    """TRUST_X_FORWARDED_FOR uses last X-Forwarded-For segment; same bucket as direct client."""
    mock_settings.RATE_LIMIT_ENABLED = True
    mock_settings.TRUST_X_FORWARDED_FOR = True
    mock_settings.PUBLIC_CHAT_MESSAGES_PER_MINUTE = 2

    hdrs = [(b"x-forwarded-for", b"203.0.113.1, 198.51.100.99")]
    a = _http_request(client_host="10.0.0.1", headers=hdrs)
    b = _http_request(client_host="10.0.0.2", headers=hdrs)

    assert rl.check_public_chat_rate_limit(a) is True
    assert rl.check_public_chat_rate_limit(b) is True
    assert rl.check_public_chat_rate_limit(a) is False


@patch("app.core.public_chat_rate_limit.settings")
def test_check_public_chat_session_message_limit_blocks_at_cap(
    mock_settings: MagicMock,
) -> None:
    mock_settings.PUBLIC_CHAT_MESSAGES_PER_SESSION = 3
    sid = "550e8400-e29b-41d4-a716-446655440000"
    assert rl.check_public_chat_session_message_limit(sid) is True
    assert rl.check_public_chat_session_message_limit(sid) is True
    assert rl.check_public_chat_session_message_limit(sid) is True
    assert rl.check_public_chat_session_message_limit(sid) is False


def test_session_counts_eviction_trims_when_over_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rl, "_MAX_TRACKED_GUEST_SESSIONS", 2)
    s1 = "00000000-0000-4000-8000-000000000001"
    s2 = "00000000-0000-4000-8000-000000000002"
    s3 = "00000000-0000-4000-8000-000000000003"
    rl.check_public_chat_session_message_limit(s1)
    rl.check_public_chat_session_message_limit(s2)
    rl.check_public_chat_session_message_limit(s3)
    with rl._session_message_lock:
        assert len(rl._session_message_counts) == 2
