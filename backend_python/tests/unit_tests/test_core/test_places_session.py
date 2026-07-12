"""Unit tests for guest Places session JWT minting and validation."""

import time

import jwt
import pytest

from app.core.config import settings
from app.core.places_session import (
    PLACES_SESSION_JWT_TYPE,
    PlacesSessionTokenError,
    client_ip_to_prefix,
    mint_places_session_token,
    validate_places_session_token,
)


def test_mint_validate_round_trip() -> None:
    sid = "550e8400-e29b-41d4-a716-446655440000"
    ip = "203.0.113.42"
    token = mint_places_session_token(sid, ip)
    validate_places_session_token(token, sid, ip)


def test_expired_token_rejected() -> None:
    sid = "550e8400-e29b-41d4-a716-446655440000"
    key = f"{settings.SECRET_KEY}_places"
    now = int(time.time())
    payload = {
        "type": PLACES_SESSION_JWT_TYPE,
        "session_id": sid,
        "ip_prefix": client_ip_to_prefix("10.0.0.1"),
        "iat": now - 7200,
        "exp": now - 3600,
    }
    token = jwt.encode(payload, key, algorithm="HS256")
    with pytest.raises(PlacesSessionTokenError) as exc:
        validate_places_session_token(token, sid, "10.0.0.1")
    assert exc.value.reason == "expired"


def test_wrong_type_rejected() -> None:
    sid = "550e8400-e29b-41d4-a716-446655440000"
    key = f"{settings.SECRET_KEY}_places"
    now = int(time.time())
    payload = {
        "type": "other",
        "session_id": sid,
        "ip_prefix": client_ip_to_prefix("10.0.0.1"),
        "iat": now,
        "exp": now + 3600,
    }
    token = jwt.encode(payload, key, algorithm="HS256")
    with pytest.raises(PlacesSessionTokenError) as exc:
        validate_places_session_token(token, sid, "10.0.0.1")
    assert exc.value.reason == "wrong_type"


def test_session_mismatch() -> None:
    sid = "550e8400-e29b-41d4-a716-446655440000"
    token = mint_places_session_token(sid, "10.0.0.1")
    with pytest.raises(PlacesSessionTokenError) as exc:
        validate_places_session_token(
            token, "660e8400-e29b-41d4-a716-446655440001", "10.0.0.1"
        )
    assert exc.value.reason == "session_mismatch"


def test_ip_prefix_mismatch() -> None:
    sid = "550e8400-e29b-41d4-a716-446655440000"
    token = mint_places_session_token(sid, "10.0.0.1")
    with pytest.raises(PlacesSessionTokenError) as exc:
        validate_places_session_token(token, sid, "192.168.1.1")
    assert exc.value.reason == "ip_mismatch"


def test_key_fallback_when_places_secret_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "PLACES_SESSION_TOKEN_SECRET", "")
    sid = "550e8400-e29b-41d4-a716-446655440000"
    token = mint_places_session_token(sid, "10.0.0.2")
    validate_places_session_token(token, sid, "10.0.0.2")


def test_explicit_places_secret_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "PLACES_SESSION_TOKEN_SECRET", "dedicated-secret-key")
    sid = "550e8400-e29b-41d4-a716-446655440000"
    token = mint_places_session_token(sid, "10.0.0.3")
    validate_places_session_token(token, sid, "10.0.0.3")

    payload = jwt.decode(token, options={"verify_signature": False})
    bad = jwt.encode(payload, "wrong-key", algorithm="HS256")
    with pytest.raises(PlacesSessionTokenError):
        validate_places_session_token(bad, sid, "10.0.0.3")


def test_ipv6_prefix_stable() -> None:
    sid = "550e8400-e29b-41d4-a716-446655440000"
    ip = "2001:db8::1"
    token = mint_places_session_token(sid, ip)
    validate_places_session_token(token, sid, ip)
