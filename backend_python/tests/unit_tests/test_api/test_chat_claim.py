"""Tests for ``POST /chat/claim`` (guest chat claim endpoint)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.chat import router as chat_router
from app.domains.auth.dependencies import require_authenticated
from app.domains.chat.schemas import ClaimChatResponse, ClaimOutcomeStatus
from app.domains.user.schemas import UserPublic

CHAT_ID = "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def app_with_user(fake_user_public: UserPublic) -> FastAPI:
    fast_app = FastAPI()
    fast_app.include_router(chat_router)
    fast_app.dependency_overrides[require_authenticated] = lambda: fake_user_public
    return fast_app


@pytest.fixture
def app_no_auth() -> FastAPI:
    fast_app = FastAPI()
    fast_app.include_router(chat_router)
    return fast_app


def _session_headers() -> dict[str, str]:
    return {"X-Public-Chat-Session": str(uuid.uuid4())}


def test_claim_requires_session_header(app_with_user: FastAPI) -> None:
    client = TestClient(app_with_user)
    r = client.post("/chat/claim", json={"chat_id": CHAT_ID})
    assert r.status_code == 400


def test_claim_invalid_session_header(app_with_user: FastAPI) -> None:
    client = TestClient(app_with_user)
    r = client.post(
        "/chat/claim",
        json={"chat_id": CHAT_ID},
        headers={"X-Public-Chat-Session": "not-a-uuid"},
    )
    assert r.status_code == 400


def test_claim_no_chat_id_is_nothing_to_claim(app_with_user: FastAPI) -> None:
    client = TestClient(app_with_user)
    r = client.post("/chat/claim", json={}, headers=_session_headers())
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "nothing_to_claim"
    assert body["chat_id"] is None


def test_claim_happy_path(app_with_user: FastAPI) -> None:
    client = TestClient(app_with_user)

    fake_response = ClaimChatResponse(
        status=ClaimOutcomeStatus.CLAIMED,
        chat_id=CHAT_ID,
        message_count=3,
    )
    with patch(
        "app.api.chat.chat_service.claim_guest_thread",
        new=AsyncMock(return_value=fake_response),
    ):
        r = client.post(
            "/chat/claim",
            json={"chat_id": CHAT_ID},
            headers=_session_headers(),
        )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "claimed"
    assert body["chat_id"] == CHAT_ID
    assert body["message_count"] == 3


def test_claim_fingerprint_mismatch_returns_403(app_with_user: FastAPI) -> None:
    client = TestClient(app_with_user)
    rejected = ClaimChatResponse(
        status=ClaimOutcomeStatus.REJECTED_FINGERPRINT_MISMATCH,
        chat_id=CHAT_ID,
        message_count=0,
    )
    with patch(
        "app.api.chat.chat_service.claim_guest_thread",
        new=AsyncMock(return_value=rejected),
    ):
        r = client.post(
            "/chat/claim",
            json={"chat_id": CHAT_ID},
            headers=_session_headers(),
        )
    assert r.status_code == 403


def test_claim_too_old_returns_409(app_with_user: FastAPI) -> None:
    client = TestClient(app_with_user)
    rejected = ClaimChatResponse(
        status=ClaimOutcomeStatus.REJECTED_TOO_OLD,
        chat_id=CHAT_ID,
        message_count=0,
    )
    with patch(
        "app.api.chat.chat_service.claim_guest_thread",
        new=AsyncMock(return_value=rejected),
    ):
        r = client.post(
            "/chat/claim",
            json={"chat_id": CHAT_ID},
            headers=_session_headers(),
        )
    assert r.status_code == 409


def test_claim_unauthenticated_returns_401(app_no_auth: FastAPI) -> None:
    client = TestClient(app_no_auth)
    r = client.post(
        "/chat/claim",
        json={"chat_id": CHAT_ID},
        headers=_session_headers(),
    )
    # FastAPI auth dep returns 401 (or 403 depending on scheme); accept either.
    assert r.status_code in (401, 403)
