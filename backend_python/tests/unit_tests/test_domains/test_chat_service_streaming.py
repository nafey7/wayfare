"""Tests for ``ChatService.process_message_streaming`` — issue #1117 piece 2c.

These tests focus on the domain layer (not the HTTP route — that's in
``test_api/test_chat_stream.py``). They verify the streaming method
correctly:

- Drives ``invoke_supervisor_v2_streaming`` and translates its typed
  graph events into ``ChatStreamEvent`` objects.
- Short-circuits on duplicate resends without invoking the graph.
- Runs the same post-stream assembly (AI-CHAT-010 telemetry, persistence,
  auto-name, auto-save) as the non-streaming path on the ``final``
  terminal event.
- Surfaces an ``error`` ChatStreamEvent when the streaming supervisor
  emits an ``error`` terminal OR when something escapes the stream.
- Passes ``custom`` events through verbatim (piece 3 of #1117 will use
  this for ``itinerary_partial`` payloads from the itinerary tool).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.chat import chat_service
from app.domains.common.enums import AuthProvider
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.domains.chat.service import ChatStreamEvent


@pytest.fixture
def auth_user() -> UserPublic:
    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="user@example.com",
        first_name="U",
        last_name="Ser",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _graph_events_from(*events: dict[str, Any]) -> Any:
    """Build a fake ``invoke_supervisor_v2_streaming`` that yields ``events``."""

    async def _gen(*_args: Any, **_kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        for ev in events:
            yield ev

    return _gen


async def _collect_stream(stream: Any) -> list[ChatStreamEvent]:
    """Drain an async iterator of ChatStreamEvent into a list."""
    out: list[ChatStreamEvent] = []
    async for ev in stream:
        out.append(ev)
    return out


# ---------------------------------------------------------------------------
# Dedupe short-circuit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.domains.chat.service._is_duplicate_resend", new_callable=AsyncMock)
async def test_duplicate_resend_emits_start_complete_only(
    mock_dedupe: AsyncMock, auth_user: UserPublic
) -> None:
    """Same-message-within-window short-circuits before touching the graph."""
    mock_dedupe.return_value = True

    events = await _collect_stream(
        chat_service.process_message_streaming(
            "hi there",
            user=auth_user,
            chat_id="chat-dup-1",
        )
    )

    assert len(events) == 2
    assert events[0].event == "start"
    assert events[0].data == {"chat_id": "chat-dup-1"}

    assert events[1].event == "complete"
    # The "still working on the previous one" body.
    assert "still working on the previous" in events[1].data["message"]
    assert events[1].data["intent_name"] == "duplicate_resend"


# ---------------------------------------------------------------------------
# Happy path — progress + final → assembly + complete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.domains.chat.service._is_duplicate_resend", new_callable=AsyncMock)
@patch("app.ai.graph.supervisor_v2.invoke_supervisor_v2_streaming")
async def test_node_updates_become_progress_events(
    mock_stream: MagicMock,
    mock_dedupe: AsyncMock,
    auth_user: UserPublic,
) -> None:
    """``node_update`` graph events surface as ``progress`` ChatStreamEvents
    with the node name. The streaming pipeline's signature win."""
    mock_dedupe.return_value = False
    mock_stream.side_effect = _graph_events_from(
        {"kind": "node_update", "node": "route_or_classify", "info": {}},
        {"kind": "node_update", "node": "dispatch_general", "info": {}},
        {
            "kind": "final",
            "result": {
                "message": "Hi there!",
                "type": "message",
                "agent": "general",
                "intent": "GENERAL",
                "confidence": 1.0,
                "chain_responses": [],
                "message_id": "msg-1",
            },
        },
    )

    # Stub out the assembly side-effects so the test doesn't touch Mongo
    # or the AI-CHAT-010 telemetry helpers.
    with patch.object(
        chat_service,
        "_assemble_response_from_supervisor_result",
        new_callable=AsyncMock,
    ) as mock_assemble:
        from app.domains.chat.schemas import ChatResponse

        mock_assemble.return_value = ChatResponse(
            message="Hi there!",
            message_id="msg-1",
            chat_id="chat-progress-1",
            intent_name="general_query",
            confidence=1.0,
            type="message",
            data=None,
            places_session_token=None,
        )

        events = await _collect_stream(
            chat_service.process_message_streaming(
                "hello", user=auth_user, chat_id="chat-progress-1"
            )
        )

    event_types = [e.event for e in events]
    # start → progress → progress → complete
    assert event_types == ["start", "progress", "progress", "complete"]
    assert events[1].data == {"node": "route_or_classify"}
    assert events[2].data == {"node": "dispatch_general"}
    assert events[3].data["message"] == "Hi there!"

    # Assembly was called with the supervisor's final result.
    mock_assemble.assert_awaited_once()
    final_result_passed = mock_assemble.await_args.args[0]
    assert final_result_passed["message"] == "Hi there!"
    assert final_result_passed["agent"] == "general"


# ---------------------------------------------------------------------------
# Custom event passthrough — piece 3 will route itinerary_partial here
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.domains.chat.service._is_duplicate_resend", new_callable=AsyncMock)
@patch("app.ai.graph.supervisor_v2.invoke_supervisor_v2_streaming")
async def test_custom_event_passthrough_uses_type_field(
    mock_stream: MagicMock,
    mock_dedupe: AsyncMock,
    auth_user: UserPublic,
) -> None:
    """Custom tool-emitted events surface as ChatStreamEvent with the
    ``type`` field from the payload as the event name."""
    mock_dedupe.return_value = False
    mock_stream.side_effect = _graph_events_from(
        {
            "kind": "custom",
            "data": {
                "type": "itinerary_partial",
                "day": 1,
                "title": "Arrival & Trastevere",
            },
        },
        {
            "kind": "final",
            "result": {
                "message": "Here's your trip",
                "type": "itinerary_results",
                "agent": "itinerary",
                "intent": "ITINERARY",
                "chain_responses": [],
                "message_id": "msg-2",
            },
        },
    )

    with patch.object(
        chat_service,
        "_assemble_response_from_supervisor_result",
        new_callable=AsyncMock,
    ) as mock_assemble:
        from app.domains.chat.schemas import ChatResponse

        mock_assemble.return_value = ChatResponse(
            message="Here's your trip",
            message_id="msg-2",
            chat_id="chat-custom-1",
            intent_name="create_itinerary",
            confidence=1.0,
            type="itinerary_results",
            data=None,
            places_session_token=None,
        )

        events = await _collect_stream(
            chat_service.process_message_streaming(
                "Plan a trip", user=auth_user, chat_id="chat-custom-1"
            )
        )

    types = [e.event for e in events]
    assert types == ["start", "itinerary_partial", "complete"]
    assert events[1].data == {
        "type": "itinerary_partial",
        "day": 1,
        "title": "Arrival & Trastevere",
    }


# ---------------------------------------------------------------------------
# Error terminal from supervisor — still runs through assembly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.domains.chat.service._is_duplicate_resend", new_callable=AsyncMock)
@patch("app.ai.graph.supervisor_v2.invoke_supervisor_v2_streaming")
async def test_supervisor_error_terminal_still_runs_assembly(
    mock_stream: MagicMock,
    mock_dedupe: AsyncMock,
    auth_user: UserPublic,
) -> None:
    """When the supervisor classifies a failure and emits ``kind=error``
    (non-retryable transient → persistent failure), the post-stream
    assembly still runs so AI-CHAT-010 telemetry fires and the error bot
    message is persisted. The complete event carries the type=error
    ChatResponse — the route doesn't differentiate; the FE branches on
    ``data.type``."""
    mock_dedupe.return_value = False
    error_result = {
        "message": "I'm having trouble right now. Please try again.",
        "type": "error",
        "error_class": "transient_llm",
        "message_id": "msg-err",
        "response_time": 1.23,
    }
    mock_stream.side_effect = _graph_events_from(
        {"kind": "error", "result": error_result},
    )

    with patch.object(
        chat_service,
        "_assemble_response_from_supervisor_result",
        new_callable=AsyncMock,
    ) as mock_assemble:
        from app.domains.chat.schemas import ChatResponse

        mock_assemble.return_value = ChatResponse(
            message="I'm having trouble right now. Please try again.",
            message_id="msg-err",
            chat_id="chat-err-1",
            intent_name="error",
            confidence=0.0,
            type="error",
            data={"error_class": "transient_llm"},
            places_session_token=None,
        )

        events = await _collect_stream(
            chat_service.process_message_streaming(
                "hello", user=auth_user, chat_id="chat-err-1"
            )
        )

    # Crucial: the classified error path STILL goes through assembly
    # (not the safety-net error handler) so persistence + telemetry run.
    mock_assemble.assert_awaited_once()
    passed = mock_assemble.await_args.args[0]
    assert passed["type"] == "error"

    types = [e.event for e in events]
    # No `error` SSE event — the classified failure goes out as `complete`
    # carrying a ChatResponse with type=error inside.
    assert types == ["start", "complete"]
    assert events[1].data["type"] == "error"
    assert events[1].data["data"]["error_class"] == "transient_llm"


# ---------------------------------------------------------------------------
# Stream raises — safety net emits error event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.domains.chat.service._is_duplicate_resend", new_callable=AsyncMock)
@patch("app.ai.graph.supervisor_v2.invoke_supervisor_v2_streaming")
async def test_unhandled_stream_exception_emits_error_event(
    mock_stream: MagicMock,
    mock_dedupe: AsyncMock,
    auth_user: UserPublic,
) -> None:
    """Exception escaping the streaming wrapper (or assembly) goes through
    ``_build_supervisor_error_response`` so AI-CHAT-010 telemetry still
    fires, and is surfaced as a single ``error`` ChatStreamEvent."""
    mock_dedupe.return_value = False

    async def _bad_gen(*_args: Any, **_kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        raise RuntimeError("simulated infra failure mid-stream")
        yield  # unreachable but makes the function an async generator

    mock_stream.side_effect = _bad_gen

    with patch.object(
        chat_service,
        "_build_supervisor_error_response",
        new_callable=AsyncMock,
    ) as mock_error_resp:
        from app.domains.chat.schemas import ChatResponse

        mock_error_resp.return_value = ChatResponse(
            message="I'm having trouble — please try again.",
            message_id=None,
            chat_id="chat-bad-1",
            intent_name="error",
            confidence=0.0,
            type="error",
            data={"error_class": "unknown"},
            places_session_token=None,
        )

        events = await _collect_stream(
            chat_service.process_message_streaming(
                "hello", user=auth_user, chat_id="chat-bad-1"
            )
        )

    # start fired before the failure; then error.
    types = [e.event for e in events]
    assert types == ["start", "error"]
    assert events[1].data["type"] == "error"
    # Telemetry hook (_build_supervisor_error_response runs AI-CHAT-010).
    mock_error_resp.assert_awaited_once()


# ---------------------------------------------------------------------------
# Missing terminal event is treated as an error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.domains.chat.service._is_duplicate_resend", new_callable=AsyncMock)
@patch("app.ai.graph.supervisor_v2.invoke_supervisor_v2_streaming")
async def test_no_terminal_event_falls_through_to_error_handler(
    mock_stream: MagicMock,
    mock_dedupe: AsyncMock,
    auth_user: UserPublic,
) -> None:
    """Defensive: if the streaming wrapper ever finishes without ``final``
    or ``error`` (shouldn't happen — invariant in the docstring) the method
    surfaces an SSE error rather than emitting a half-stream."""
    mock_dedupe.return_value = False
    mock_stream.side_effect = _graph_events_from(
        {"kind": "node_update", "node": "route_or_classify", "info": {}},
    )

    with patch.object(
        chat_service,
        "_build_supervisor_error_response",
        new_callable=AsyncMock,
    ) as mock_error_resp:
        from app.domains.chat.schemas import ChatResponse

        mock_error_resp.return_value = ChatResponse(
            message="I'm having trouble — please try again.",
            message_id=None,
            chat_id="chat-no-final-1",
            intent_name="error",
            confidence=0.0,
            type="error",
            data={"error_class": "unknown"},
            places_session_token=None,
        )

        events = await _collect_stream(
            chat_service.process_message_streaming(
                "hello", user=auth_user, chat_id="chat-no-final-1"
            )
        )

    types = [e.event for e in events]
    # start + progress fired, then RuntimeError caught → error event.
    assert types == ["start", "progress", "error"]
    mock_error_resp.assert_awaited_once()
