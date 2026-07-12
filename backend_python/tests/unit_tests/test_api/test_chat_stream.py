"""Tests for POST /chat/message/stream — issue #1117 (SSE transport).

Pieces 1 + 2 land together: the route + ``ChatService.process_message_streaming``
together emit start → progress* → complete (or error) events as the
supervisor graph runs. These tests cover the route layer — auth, lock,
feature flag, headers, and faithful relay of the events the streaming
method yields.

- Feature flag gating (404 when CHAT_STREAMING_ENABLED is False).
- ``require_authenticated`` is enforced.
- ChatLockError → 429 with the same detail body as POST /chat/message.
- Happy path: SSE response with correct media_type + headers, and the
  events the streaming method yields appear in order with valid envelopes.
- Progress events surface to the wire (Piece 2 win — proves the streaming
  pipeline is wired, not just start/complete).
- Each event has a stable, unique ``id:`` field for ``Last-Event-ID``
  reconnect support.
- Exception escaping the streaming method surfaces as a route-level
  safety-net ``error`` event on the open stream.
- New conversation creation when chat_id is None.
- Lock is released when the stream terminates.

The tests parse the SSE wire format directly rather than relying on a
helper, so the framing itself is part of the contract under test.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.chat import router as chat_router
from app.api.chat_sse import SSEEventType
from app.domains.auth.dependencies import require_authenticated
from app.domains.chat.schemas import ChatResponse
from app.domains.chat.service import ChatStreamEvent
from app.domains.common.enums import AuthProvider
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic
from app.shared.chat_lock import ChatLockError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_user() -> UserPublic:
    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="streaming-user@example.com",
        first_name="Streaming",
        last_name="User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def app_with_auth(auth_user: UserPublic) -> FastAPI:
    app = FastAPI()
    app.include_router(chat_router)

    async def override_auth() -> UserPublic:
        return auth_user

    app.dependency_overrides[require_authenticated] = override_auth
    return app


@pytest.fixture
def client(app_with_auth: FastAPI) -> TestClient:
    return TestClient(app_with_auth)


def _ok_response(chat_id: str = "00000000-0000-0000-0000-000000000001") -> ChatResponse:
    return ChatResponse(
        message="Hello from streaming",
        message_id="msg-stream-1",
        chat_id=chat_id,
        intent_name="general_query",
        confidence=1.0,
        type="message",
        data=None,
        places_session_token=None,
    )


def _stream_from(
    events: list[ChatStreamEvent],
    *,
    raise_after: int | None = None,
) -> Any:
    """Build a fake ``process_message_streaming`` that yields the given events.

    ``raise_after`` — if set, raises RuntimeError after yielding that many
    events. Used to exercise the route-level safety-net error handler
    (Piece 2c's own error handling catches exceptions internally and yields
    its own ``error`` event, but we still want defense-in-depth on the
    route).
    """

    async def _gen(*_args: Any, **_kwargs: Any) -> AsyncIterator[ChatStreamEvent]:
        for i, ev in enumerate(events):
            if raise_after is not None and i >= raise_after:
                raise RuntimeError("simulated stream failure after partial events")
            yield ev
        if raise_after is not None and raise_after >= len(events):
            raise RuntimeError("simulated stream failure at end")

    return _gen


def _ok_stream(
    chat_id: str = "00000000-0000-0000-0000-000000000001",
    *,
    with_progress: bool = False,
) -> Any:
    """Build a fake streaming response with start [+ progress*] + complete."""
    events: list[ChatStreamEvent] = [
        ChatStreamEvent(event="start", data={"chat_id": chat_id})
    ]
    if with_progress:
        events.append(
            ChatStreamEvent(event="progress", data={"node": "route_or_classify"})
        )
        events.append(
            ChatStreamEvent(event="progress", data={"node": "dispatch_general"})
        )
    events.append(
        ChatStreamEvent(
            event="complete",
            data=_ok_response(chat_id).model_dump(mode="json"),
        )
    )
    return _stream_from(events)


class _LockAcquirerStub:
    """Async context manager stub for ChatLock.acquire(chat_id).

    ``raise_on_enter=True`` makes ``__aenter__`` raise ``ChatLockError``,
    simulating the "another request already in flight" case. Otherwise the
    enter is a no-op and we record release for the lock-release test.
    """

    def __init__(self, *, raise_on_enter: bool = False) -> None:
        self.raise_on_enter = raise_on_enter
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> _LockAcquirerStub:
        if self.raise_on_enter:
            raise ChatLockError("simulated lock contention")
        self.entered = True
        return self

    async def __aexit__(self, *args: Any) -> None:
        self.exited = True


def _make_lock(*, busy: bool = False) -> tuple[MagicMock, _LockAcquirerStub]:
    """Build a ChatLock mock whose ``acquire(chat_id)`` returns the stub."""
    acquirer = _LockAcquirerStub(raise_on_enter=busy)
    lock = MagicMock()
    lock.acquire = MagicMock(return_value=acquirer)
    return lock, acquirer


def _parse_sse_events(body: str) -> list[dict[str, str]]:
    """Parse the SSE wire format into a list of event dicts.

    Each dict has the raw header fields seen in the event block:
    ``{"id": "...", "event": "...", "data": "..."}``. ``data`` is left as
    the raw JSON string — callers ``json.loads`` it when they care.
    """
    events = []
    for block in body.split("\n\n"):
        block = block.strip("\n")
        if not block:
            continue
        fields: dict[str, str] = {}
        for line in block.split("\n"):
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            fields[key.strip()] = value.lstrip()
        events.append(fields)
    return events


# ---------------------------------------------------------------------------
# Feature flag
# ---------------------------------------------------------------------------


@patch("app.api.chat.settings")
def test_streaming_disabled_returns_404(
    mock_settings: MagicMock, client: TestClient
) -> None:
    mock_settings.CHAT_STREAMING_ENABLED = False
    resp = client.post(
        "/chat/message/stream",
        json={"message": "Hi", "chat_id": str(uuid4())},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_streaming_unauthenticated_returns_401() -> None:
    app = FastAPI()
    app.include_router(chat_router)

    async def deny() -> UserPublic:
        raise HTTPException(status_code=401, detail="not signed in")

    app.dependency_overrides[require_authenticated] = deny
    unauth_client = TestClient(app)

    with patch("app.api.chat.settings") as mock_settings:
        mock_settings.CHAT_STREAMING_ENABLED = True
        resp = unauth_client.post(
            "/chat/message/stream",
            json={"message": "Hi", "chat_id": str(uuid4())},
        )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Lock contention
# ---------------------------------------------------------------------------


@patch("app.api.chat.chat_service")
@patch("app.api.chat.get_chat_lock")
@patch("app.api.chat.settings")
def test_lock_contention_returns_429_with_shared_detail(
    mock_settings: MagicMock,
    mock_get_lock: MagicMock,
    mock_chat_service: MagicMock,
    client: TestClient,
) -> None:
    mock_settings.CHAT_STREAMING_ENABLED = True
    lock, _acquirer = _make_lock(busy=True)
    mock_get_lock.return_value = lock

    resp = client.post(
        "/chat/message/stream",
        json={"message": "Hi", "chat_id": str(uuid4())},
    )
    assert resp.status_code == 429
    # The 429 detail must match the non-streaming endpoint verbatim so the
    # frontend's "another request in flight" handler works on either path.
    assert (
        resp.json()["detail"]
        == "Another request is already processing for this conversation. "
        "Please wait for the previous request to complete."
    )
    # process_message_streaming must NOT have been called when the lock is busy.
    mock_chat_service.process_message_streaming.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path — headers, event order, envelope shape
# ---------------------------------------------------------------------------


@patch("app.api.chat.chat_service")
@patch("app.api.chat.get_chat_lock")
@patch("app.api.chat.settings")
def test_happy_path_emits_start_then_complete(
    mock_settings: MagicMock,
    mock_get_lock: MagicMock,
    mock_chat_service: MagicMock,
    client: TestClient,
) -> None:
    mock_settings.CHAT_STREAMING_ENABLED = True
    lock, acquirer = _make_lock()
    mock_get_lock.return_value = lock

    chat_id = str(uuid4())
    mock_chat_service.process_message_streaming = _ok_stream(chat_id)

    resp = client.post(
        "/chat/message/stream",
        json={"message": "Plan a 5-day trip to Paris", "chat_id": chat_id},
    )
    assert resp.status_code == 200

    # SSE headers — proxies must not buffer or transform.
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers["cache-control"] == "no-cache, no-transform"
    assert resp.headers["x-accel-buffering"] == "no"

    events = _parse_sse_events(resp.text)
    assert len(events) == 2

    start, complete = events
    assert start["event"] == SSEEventType.START.value
    assert start["id"]  # non-empty stable id
    start_payload = json.loads(start["data"])
    assert start_payload == {"chat_id": chat_id}

    assert complete["event"] == SSEEventType.COMPLETE.value
    assert complete["id"]
    complete_payload = json.loads(complete["data"])
    # Full ChatResponse round-trips on the wire.
    assert complete_payload["chat_id"] == chat_id
    assert complete_payload["message"] == "Hello from streaming"
    assert complete_payload["message_id"] == "msg-stream-1"
    assert complete_payload["intent_name"] == "general_query"

    # Lock acquired, then released after the stream completed.
    assert acquirer.entered is True
    assert acquirer.exited is True


@patch("app.api.chat.chat_service")
@patch("app.api.chat.get_chat_lock")
@patch("app.api.chat.settings")
def test_progress_events_pass_through_to_wire(
    mock_settings: MagicMock,
    mock_get_lock: MagicMock,
    mock_chat_service: MagicMock,
    client: TestClient,
) -> None:
    """Piece 2 win — the route should faithfully relay every event the
    streaming method yields, not just start + complete. Verifies that the
    SSE pipeline is wired (the chain doesn't break at the route)."""
    mock_settings.CHAT_STREAMING_ENABLED = True
    lock, _acquirer = _make_lock()
    mock_get_lock.return_value = lock

    chat_id = str(uuid4())
    mock_chat_service.process_message_streaming = _ok_stream(
        chat_id, with_progress=True
    )

    resp = client.post(
        "/chat/message/stream",
        json={"message": "Plan a 5-day trip", "chat_id": chat_id},
    )
    assert resp.status_code == 200

    events = _parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]
    # Exact sequence: start → progress → progress → complete
    assert event_types == [
        SSEEventType.START.value,
        SSEEventType.PROGRESS.value,
        SSEEventType.PROGRESS.value,
        SSEEventType.COMPLETE.value,
    ]
    progress_events = [e for e in events if e["event"] == SSEEventType.PROGRESS.value]
    nodes = [json.loads(e["data"])["node"] for e in progress_events]
    assert nodes == ["route_or_classify", "dispatch_general"]


@patch("app.api.chat.chat_service")
@patch("app.api.chat.get_chat_lock")
@patch("app.api.chat.settings")
def test_each_event_has_stable_id(
    mock_settings: MagicMock,
    mock_get_lock: MagicMock,
    mock_chat_service: MagicMock,
    client: TestClient,
) -> None:
    """``id:`` field must be present so the client can replay-from-id on
    reconnect. Two events should not share an id."""
    mock_settings.CHAT_STREAMING_ENABLED = True
    lock, _acquirer = _make_lock()
    mock_get_lock.return_value = lock

    chat_id = str(uuid4())
    mock_chat_service.process_message_streaming = _ok_stream(
        chat_id, with_progress=True
    )

    resp = client.post(
        "/chat/message/stream",
        json={"message": "Hi", "chat_id": chat_id},
    )
    events = _parse_sse_events(resp.text)
    ids = [e["id"] for e in events]
    assert all(ids)  # every event has a non-empty id
    assert len(set(ids)) == len(ids)  # ids are unique per-event


# ---------------------------------------------------------------------------
# Error path — uncaught exception inside the streaming method
# ---------------------------------------------------------------------------


@patch("app.api.chat.chat_service")
@patch("app.api.chat.get_chat_lock")
@patch("app.api.chat.settings")
def test_stream_exception_emits_safety_net_error_event(
    mock_settings: MagicMock,
    mock_get_lock: MagicMock,
    mock_chat_service: MagicMock,
    client: TestClient,
) -> None:
    """Once the response headers go out (200, text/event-stream) the server
    can't change its mind to 500. ChatService.process_message_streaming
    is supposed to catch all internal failures and yield its own ``error``
    event — but the route still has a safety-net try/except in case
    something escapes anyway (e.g. supervisor import failure). This test
    exercises that net by making the generator raise after the start event.
    """
    mock_settings.CHAT_STREAMING_ENABLED = True
    lock, acquirer = _make_lock()
    mock_get_lock.return_value = lock

    chat_id = str(uuid4())
    mock_chat_service.process_message_streaming = _stream_from(
        [ChatStreamEvent(event="start", data={"chat_id": chat_id})],
        raise_after=1,
    )

    resp = client.post(
        "/chat/message/stream",
        json={"message": "Hi", "chat_id": chat_id},
    )
    # Stream itself succeeded (response already committed); failure is
    # inside the event payload.
    assert resp.status_code == 200

    events = _parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]
    assert SSEEventType.START.value in event_types
    assert SSEEventType.ERROR.value in event_types
    assert SSEEventType.COMPLETE.value not in event_types

    err = next(e for e in events if e["event"] == SSEEventType.ERROR.value)
    payload = json.loads(err["data"])
    # Don't leak the raw exception message to the client. Class name is
    # fine — clients use it to branch on retryable vs fatal.
    assert "simulated stream failure" not in payload.get("message", "")
    assert payload.get("error_class") == "RuntimeError"

    # Lock must still be released even on the failure path.
    assert acquirer.exited is True


# ---------------------------------------------------------------------------
# New-conversation path — chat_id omitted
# ---------------------------------------------------------------------------


@patch("app.api.chat.create_conv_repo")
@patch("app.api.chat.chat_service")
@patch("app.api.chat.get_chat_lock")
@patch("app.api.chat.settings")
def test_null_chat_id_creates_new_conversation(
    mock_settings: MagicMock,
    mock_get_lock: MagicMock,
    mock_chat_service: MagicMock,
    mock_create_conv: AsyncMock,
    client: TestClient,
) -> None:
    """Same ChatGPT-style "no chat_id = new conversation" semantics as the
    non-streaming endpoint, so a fresh thread doesn't need a separate
    POST /chat/conversations round-trip."""
    mock_settings.CHAT_STREAMING_ENABLED = True
    lock, _acquirer = _make_lock()
    mock_get_lock.return_value = lock

    fresh_chat_id = "00000000-0000-0000-0000-0000000000aa"
    mock_create_conv.return_value = {"chat_id": fresh_chat_id}
    mock_chat_service.process_message_streaming = _ok_stream(fresh_chat_id)

    resp = client.post(
        "/chat/message/stream",
        json={"message": "Hi", "chat_id": None},
    )
    assert resp.status_code == 200
    mock_create_conv.assert_awaited_once()

    events = _parse_sse_events(resp.text)
    start = next(e for e in events if e["event"] == SSEEventType.START.value)
    assert json.loads(start["data"]) == {"chat_id": fresh_chat_id}
