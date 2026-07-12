"""Tests for GET /api/public/places/photos/{path}/media."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.public_places import router as public_places_router
from app.core.places_session import mint_places_session_token
from app.core.public_places_rate_limit import (
    clear_public_places_rate_limit_state_for_tests,
)
from integrations.googleplaces.client import PlacesAPIError


@pytest.fixture
def app() -> FastAPI:
    fast_app = FastAPI()
    fast_app.include_router(public_places_router, prefix="/api")
    return fast_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_limits() -> None:
    clear_public_places_rate_limit_state_for_tests()
    yield
    clear_public_places_rate_limit_state_for_tests()


@pytest.fixture
def trust_loopback_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    """TestClient remote addr is not always 127.0.0.1; token IP must match validation."""
    monkeypatch.setattr(
        "app.api.public_places.get_trusted_request_client_ip",
        lambda _r: "127.0.0.1",
    )


VALID_RESOURCE = "places/ChIJabc123def456/photos/ATCDxyz789"  # pragma: allowlist secret


def _headers(session: str, token: str) -> dict[str, str]:
    return {
        "X-Public-Chat-Session": session,
        "X-Places-Session-Token": token,
    }


@patch("app.api.public_places._get_public_places_client")
def test_valid_token_returns_image(
    mock_get_client: MagicMock,
    trust_loopback_ip: None,
    client: TestClient,
) -> None:
    mock_client = MagicMock()
    mock_client.get_photo_media = AsyncMock(
        return_value=(b"\xff\xd8\xff", "image/jpeg")
    )
    mock_get_client.return_value = mock_client

    sid = str(uuid.uuid4())
    token = mint_places_session_token(sid, "127.0.0.1")
    r = client.get(
        f"/api/public/places/photos/{VALID_RESOURCE}/media",
        headers=_headers(sid, token),
    )
    assert r.status_code == 200
    assert r.content.startswith(b"\xff\xd8")
    assert "private" in r.headers.get("cache-control", "").lower()


def test_missing_token_401(client: TestClient) -> None:
    sid = str(uuid.uuid4())
    r = client.get(
        f"/api/public/places/photos/{VALID_RESOURCE}/media",
        headers={"X-Public-Chat-Session": sid},
    )
    assert r.status_code == 401


@patch("app.api.public_places._get_public_places_client")
def test_expired_token_403(mock_get: MagicMock, client: TestClient) -> None:
    import time

    import jwt

    from app.core.config import settings
    from app.core.places_session import PLACES_SESSION_JWT_TYPE, client_ip_to_prefix

    sid = str(uuid.uuid4())
    now = int(time.time())
    payload = {
        "type": PLACES_SESSION_JWT_TYPE,
        "session_id": sid,
        "ip_prefix": client_ip_to_prefix("127.0.0.1"),
        "iat": now - 100,
        "exp": now - 50,
    }
    key = f"{settings.SECRET_KEY}_places"
    bad_token = jwt.encode(payload, key, algorithm="HS256")
    r = client.get(
        f"/api/public/places/photos/{VALID_RESOURCE}/media",
        headers=_headers(sid, bad_token),
    )
    assert r.status_code == 403


@patch("app.api.public_places._get_public_places_client")
def test_session_mismatch_403(mock_get: MagicMock, client: TestClient) -> None:
    sid = str(uuid.uuid4())
    other = str(uuid.uuid4())
    token = mint_places_session_token(sid, "127.0.0.1")
    r = client.get(
        f"/api/public/places/photos/{VALID_RESOURCE}/media",
        headers=_headers(other, token),
    )
    assert r.status_code == 403


@patch("app.api.public_places._get_public_places_client")
def test_ip_mismatch_403(mock_get: MagicMock, client: TestClient) -> None:
    sid = str(uuid.uuid4())
    token = mint_places_session_token(sid, "10.0.0.1")
    r = client.get(
        f"/api/public/places/photos/{VALID_RESOURCE}/media",
        headers=_headers(sid, token),
    )
    assert r.status_code == 403


def test_invalid_resource_400(client: TestClient, trust_loopback_ip: None) -> None:
    sid = str(uuid.uuid4())
    token = mint_places_session_token(sid, "127.0.0.1")
    r = client.get(
        "/api/public/places/photos/places/bad!/photos/nope/media",
        headers=_headers(sid, token),
    )
    assert r.status_code == 400


@patch("app.api.public_places._get_public_places_client")
def test_google_error_502(
    mock_get_client: MagicMock, trust_loopback_ip: None, client: TestClient
) -> None:
    mock_client = MagicMock()
    mock_client.get_photo_media = AsyncMock(
        side_effect=PlacesAPIError("upstream", status_code=503)
    )
    mock_get_client.return_value = mock_client

    sid = str(uuid.uuid4())
    token = mint_places_session_token(sid, "127.0.0.1")
    r = client.get(
        f"/api/public/places/photos/{VALID_RESOURCE}/media",
        headers=_headers(sid, token),
    )
    assert r.status_code == 502


@patch("app.api.public_places._get_public_places_client")
def test_rate_limit_429(
    mock_get: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    trust_loopback_ip: None,
    client: TestClient,
) -> None:
    monkeypatch.setattr(
        "app.core.public_places_rate_limit.PUBLIC_PLACES_PHOTO_RATE_LIMIT_PER_MINUTE",
        1,
    )
    mock_client = MagicMock()
    mock_client.get_photo_media = AsyncMock(return_value=(b"x", "image/jpeg"))
    mock_get.return_value = mock_client

    sid = str(uuid.uuid4())
    token = mint_places_session_token(sid, "127.0.0.1")
    url = f"/api/public/places/photos/{VALID_RESOURCE}/media"
    assert client.get(url, headers=_headers(sid, token)).status_code == 200
    r = client.get(url, headers=_headers(sid, token))
    assert r.status_code == 429
    assert r.headers.get("retry-after") == "60"


def test_session_token_mints_when_public_chat_enabled(
    trust_loopback_ip: None,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.public_places.public_chat_enabled", lambda: True)
    sid = str(uuid.uuid4())
    r = client.post(
        "/api/public/places/session-token",
        headers={"X-Public-Chat-Session": sid},
    )
    assert r.status_code == 200
    body = r.json()
    assert "places_session_token" in body
    assert len(body["places_session_token"]) > 20


def test_session_token_403_when_public_chat_disabled(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.public_places.public_chat_enabled", lambda: False)
    sid = str(uuid.uuid4())
    r = client.post(
        "/api/public/places/session-token",
        headers={"X-Public-Chat-Session": sid},
    )
    assert r.status_code == 403


def test_session_token_refresh_rate_limit_429(
    trust_loopback_ip: None,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.public_places.public_chat_enabled", lambda: True)
    monkeypatch.setattr(
        "app.core.public_places_rate_limit.PUBLIC_PLACES_SESSION_TOKEN_REFRESH_PER_MINUTE",
        1,
    )
    sid = str(uuid.uuid4())
    h = {"X-Public-Chat-Session": sid}
    assert client.post("/api/public/places/session-token", headers=h).status_code == 200
    r = client.post("/api/public/places/session-token", headers=h)
    assert r.status_code == 429
    assert r.headers.get("retry-after") == "60"
