"""Tests for POST /public/chat/message (guest chat)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.public_chat import router as public_chat_router
from app.core.public_chat_rate_limit import (
    clear_public_chat_session_message_counts_for_tests,
)
from app.core.security_constants import MAX_CHAT_MESSAGE_LENGTH
from app.domains.chat.schemas import ChatResponse
from app.shared.chat_lock import ChatLockError


@pytest.fixture
def app() -> FastAPI:
    fast_app = FastAPI()
    fast_app.include_router(public_chat_router)
    return fast_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _session_headers() -> dict[str, str]:
    return {"X-Public-Chat-Session": str(uuid.uuid4())}


def _ok_response() -> ChatResponse:
    return ChatResponse(
        message="ok",
        message_id="m1",
        chat_id="00000000-0000-0000-0000-000000000001",
        intent_name="general_query",
        confidence=1.0,
        type="message",
        data=None,
        places_session_token=None,
    )


@patch("app.api.public_chat.public_chat_enabled", return_value=False)
def test_public_chat_disabled_returns_403(
    mock_flag: MagicMock, client: TestClient
) -> None:
    r = client.post(
        "/public/chat/message",
        json={"message": "hi"},
        headers=_session_headers(),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "public_chat_disabled"


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
def test_missing_session_header_returns_400(
    mock_flag: MagicMock, client: TestClient
) -> None:
    with patch("app.api.public_chat.check_public_chat_rate_limit", return_value=True):
        r = client.post("/public/chat/message", json={"message": "hi"})
    assert r.status_code == 400


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
def test_message_exceeds_max_length_returns_422(
    mock_flag: MagicMock, client: TestClient
) -> None:
    with patch("app.api.public_chat.check_public_chat_rate_limit", return_value=True):
        r = client.post(
            "/public/chat/message",
            json={"message": "x" * (MAX_CHAT_MESSAGE_LENGTH + 1)},
            headers=_session_headers(),
        )
    assert r.status_code == 422


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
def test_empty_message_returns_422(mock_flag: MagicMock, client: TestClient) -> None:
    with patch("app.api.public_chat.check_public_chat_rate_limit", return_value=True):
        r = client.post(
            "/public/chat/message",
            json={"message": ""},
            headers=_session_headers(),
        )
    assert r.status_code == 422


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
def test_whitespace_only_message_returns_422(
    mock_flag: MagicMock, client: TestClient
) -> None:
    with patch("app.api.public_chat.check_public_chat_rate_limit", return_value=True):
        r = client.post(
            "/public/chat/message",
            json={"message": "   \t  "},
            headers=_session_headers(),
        )
    assert r.status_code == 422


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
def test_invalid_session_uuid_returns_400(
    mock_flag: MagicMock, client: TestClient
) -> None:
    with patch("app.api.public_chat.check_public_chat_rate_limit", return_value=True):
        r = client.post(
            "/public/chat/message",
            json={"message": "hi"},
            headers={"X-Public-Chat-Session": "not-a-uuid"},
        )
    assert r.status_code == 400


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
@patch("app.api.public_chat.check_public_chat_rate_limit")
def test_rate_limit_returns_429_with_code(
    mock_rl: MagicMock,
    mock_flag: MagicMock,
    client: TestClient,
) -> None:
    mock_rl.return_value = False
    r = client.post(
        "/public/chat/message",
        json={"message": "hi"},
        headers=_session_headers(),
    )
    assert r.status_code == 429
    assert r.json()["code"] == "public_rate_limit"


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
@patch("app.api.public_chat.get_chat_lock")
@patch("app.api.public_chat._dispatch_public_message", new_callable=AsyncMock)
def test_success_calls_dispatch(
    mock_dispatch: AsyncMock,
    mock_get_lock: MagicMock,
    mock_flag: MagicMock,
    client: TestClient,
) -> None:
    mock_dispatch.return_value = _ok_response()
    fake_cm = MagicMock()
    fake_cm.__aenter__ = AsyncMock(return_value=None)
    fake_cm.__aexit__ = AsyncMock(return_value=None)
    mock_get_lock.return_value.acquire = MagicMock(return_value=fake_cm)
    with (
        patch("app.api.public_chat.check_public_chat_rate_limit", return_value=True),
        patch(
            "app.api.public_chat.check_public_chat_session_message_limit",
            return_value=True,
        ),
    ):
        r = client.post(
            "/public/chat/message",
            json={"message": "hello", "chat_id": None},
            headers=_session_headers(),
        )
    assert r.status_code == 200
    assert r.json()["message"] == "ok"
    mock_dispatch.assert_awaited()


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
@patch("app.api.public_chat.guest_session_may_use_chat_id", new_callable=AsyncMock)
def test_chat_id_from_other_session_returns_403(
    mock_may: AsyncMock,
    mock_flag: MagicMock,
    client: TestClient,
) -> None:
    mock_may.return_value = False
    with (
        patch("app.api.public_chat.check_public_chat_rate_limit", return_value=True),
        patch(
            "app.api.public_chat.check_public_chat_session_message_limit",
            return_value=True,
        ),
    ):
        r = client.post(
            "/public/chat/message",
            json={
                "message": "hello",
                "chat_id": "00000000-0000-0000-0000-000000000099",
            },
            headers=_session_headers(),
        )
    assert r.status_code == 403
    assert "does not belong" in r.json()["detail"].lower()
    mock_may.assert_awaited_once()


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
def test_invalid_chat_id_format_returns_422(
    mock_flag: MagicMock, client: TestClient
) -> None:
    with (
        patch("app.api.public_chat.check_public_chat_rate_limit", return_value=True),
        patch(
            "app.api.public_chat.check_public_chat_session_message_limit",
            return_value=True,
        ),
    ):
        r = client.post(
            "/public/chat/message",
            json={"message": "hello", "chat_id": "not-a-uuid"},
            headers=_session_headers(),
        )
    assert r.status_code == 422


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
@patch("app.api.public_chat.get_chat_lock")
def test_chat_lock_conflict_returns_429(
    mock_get_lock: MagicMock,
    mock_flag: MagicMock,
    client: TestClient,
) -> None:
    fake_cm = MagicMock()
    fake_cm.__aenter__ = AsyncMock(side_effect=ChatLockError("busy"))
    fake_cm.__aexit__ = AsyncMock(return_value=None)
    mock_get_lock.return_value.acquire = MagicMock(return_value=fake_cm)

    with (
        patch("app.api.public_chat.check_public_chat_rate_limit", return_value=True),
        patch(
            "app.api.public_chat.check_public_chat_session_message_limit",
            return_value=True,
        ),
        patch(
            "app.api.public_chat._dispatch_public_message",
            new_callable=AsyncMock,
        ) as mock_dispatch,
    ):
        r = client.post(
            "/public/chat/message",
            json={"message": "hello"},
            headers=_session_headers(),
        )
    assert r.status_code == 429
    assert r.json()["code"] == "chat_request_in_progress"
    mock_dispatch.assert_not_awaited()


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
@patch("app.api.public_chat.get_chat_lock")
@patch("app.api.public_chat._dispatch_public_message", new_callable=AsyncMock)
def test_unhandled_error_returns_generic_500(
    mock_dispatch: AsyncMock,
    mock_get_lock: MagicMock,
    mock_flag: MagicMock,
    client: TestClient,
) -> None:
    mock_dispatch.side_effect = RuntimeError("internal secret detail")
    fake_cm = MagicMock()
    fake_cm.__aenter__ = AsyncMock(return_value=None)
    fake_cm.__aexit__ = AsyncMock(return_value=None)
    mock_get_lock.return_value.acquire = MagicMock(return_value=fake_cm)

    with (
        patch("app.api.public_chat.check_public_chat_rate_limit", return_value=True),
        patch(
            "app.api.public_chat.check_public_chat_session_message_limit",
            return_value=True,
        ),
    ):
        r = client.post(
            "/public/chat/message",
            json={"message": "hello"},
            headers=_session_headers(),
        )
    assert r.status_code == 500
    body = r.json()
    assert body["code"] == "public_chat_error"
    assert "internal secret" not in str(body)
    assert "secret" not in body["detail"].lower()


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
@patch("app.api.public_chat.get_chat_lock")
@patch("app.api.public_chat._dispatch_public_message", new_callable=AsyncMock)
def test_session_message_limit_returns_429_with_code(
    mock_dispatch: AsyncMock,
    mock_get_lock: MagicMock,
    mock_flag: MagicMock,
    client: TestClient,
) -> None:
    clear_public_chat_session_message_counts_for_tests()
    mock_dispatch.return_value = _ok_response()
    fake_cm = MagicMock()
    fake_cm.__aenter__ = AsyncMock(return_value=None)
    fake_cm.__aexit__ = AsyncMock(return_value=None)
    mock_get_lock.return_value.acquire = MagicMock(return_value=fake_cm)
    fixed_session = str(uuid.uuid4())
    headers = {"X-Public-Chat-Session": fixed_session}
    with patch("app.api.public_chat.check_public_chat_rate_limit", return_value=True):
        for _ in range(20):
            r = client.post(
                "/public/chat/message",
                json={"message": "hi"},
                headers=headers,
            )
            assert r.status_code == 200
        r = client.post(
            "/public/chat/message",
            json={"message": "hi"},
            headers=headers,
        )
    assert r.status_code == 429
    assert r.json()["code"] == "public_session_limit"
    assert mock_dispatch.await_count == 20


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
@patch("app.api.public_chat.get_chat_lock")
@patch("app.api.public_chat._dispatch_public_message", new_callable=AsyncMock)
def test_itinerary_response_includes_places_session_token_when_set(
    mock_dispatch: AsyncMock,
    mock_get_lock: MagicMock,
    mock_flag: MagicMock,
    client: TestClient,
) -> None:
    mock_dispatch.return_value = ChatResponse(
        message="Your itinerary",
        message_id="m2",
        chat_id="00000000-0000-0000-0000-000000000001",
        intent_name="create_itinerary",
        confidence=1.0,
        type="itinerary_results",
        data={"structured_itinerary": {}},
        places_session_token="eyJhbG.example.token",
    )
    fake_cm = MagicMock()
    fake_cm.__aenter__ = AsyncMock(return_value=None)
    fake_cm.__aexit__ = AsyncMock(return_value=None)
    mock_get_lock.return_value.acquire = MagicMock(return_value=fake_cm)
    with (
        patch("app.api.public_chat.check_public_chat_rate_limit", return_value=True),
        patch(
            "app.api.public_chat.check_public_chat_session_message_limit",
            return_value=True,
        ),
    ):
        r = client.post(
            "/public/chat/message",
            json={"message": "plan paris"},
            headers=_session_headers(),
        )
    assert r.status_code == 200
    assert r.json()["places_session_token"] == "eyJhbG.example.token"


@patch("app.api.public_chat.public_chat_enabled", return_value=True)
@patch("app.api.public_chat.get_chat_lock")
@patch("app.api.public_chat._dispatch_public_message", new_callable=AsyncMock)
def test_non_itinerary_response_omits_places_session_token(
    mock_dispatch: AsyncMock,
    mock_get_lock: MagicMock,
    mock_flag: MagicMock,
    client: TestClient,
) -> None:
    mock_dispatch.return_value = _ok_response()
    fake_cm = MagicMock()
    fake_cm.__aenter__ = AsyncMock(return_value=None)
    fake_cm.__aexit__ = AsyncMock(return_value=None)
    mock_get_lock.return_value.acquire = MagicMock(return_value=fake_cm)
    with (
        patch("app.api.public_chat.check_public_chat_rate_limit", return_value=True),
        patch(
            "app.api.public_chat.check_public_chat_session_message_limit",
            return_value=True,
        ),
    ):
        r = client.post(
            "/public/chat/message",
            json={"message": "hi"},
            headers=_session_headers(),
        )
    assert r.status_code == 200
    body = r.json()
    assert body.get("places_session_token") is None
