"""Tests for ``invoke_supervisor_v2_streaming`` — issue #1117 piece 2b.

Covers the streaming wrapper around the supervisor graph: event-type
translation from ``graph.astream(stream_mode=["updates", "messages",
"custom"])``, transient-error retry, terminal event emission, and final
state shaping.

Mocking pattern mirrors ``test_error_resilience.py``: patch
``get_supervisor_v2_graph`` and ``_get_sv2_checkpointer`` to bypass
LangGraph + Mongo setup, then drive a fake graph that yields the
event sequence each test needs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


def _mock_checkpointer_with_current_version() -> MagicMock:
    """Checkpointer mock that pretends an up-to-date checkpoint exists.

    Skips the version-guard clearing path inside
    ``_prepare_supervisor_invocation`` so each test goes straight to the
    streaming call.
    """
    from app.ai.graph.supervisor_v2 import SV2_CHECKPOINT_VERSION

    cp = MagicMock()
    cp.get.return_value = {
        "channel_values": {"checkpoint_version": SV2_CHECKPOINT_VERSION},
    }
    return cp


def _astream_yielding(*events: tuple[str, Any]) -> Any:
    """Return a callable that mimics ``graph.astream(...)`` yielding ``events``."""

    def _factory(*_args: Any, **_kwargs: Any) -> AsyncIterator[tuple[str, Any]]:
        async def _gen() -> AsyncIterator[tuple[str, Any]]:
            for ev in events:
                yield ev

        return _gen()

    return _factory


def _astream_raising(exc: Exception, *prelude: tuple[str, Any]) -> Any:
    """``graph.astream`` mock: yield ``prelude`` then raise ``exc``."""

    def _factory(*_args: Any, **_kwargs: Any) -> AsyncIterator[tuple[str, Any]]:
        async def _gen() -> AsyncIterator[tuple[str, Any]]:
            for ev in prelude:
                yield ev
            raise exc

        return _gen()

    return _factory


def _aget_state_returning(state_values: dict[str, Any]) -> AsyncMock:
    """Mock ``graph.aget_state(config)`` returning a snapshot with ``.values``."""
    snap = MagicMock()
    snap.values = state_values
    return AsyncMock(return_value=snap)


async def _collect(stream: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    async for ev in stream:
        out.append(ev)
    return out


# ---------------------------------------------------------------------------
# Happy path — event translation + final
# ---------------------------------------------------------------------------


class TestStreamingHappyPath:
    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._shape_supervisor_response_from_state")
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_updates_events_become_node_update(
        self,
        mock_get_graph: MagicMock,
        mock_get_cp: MagicMock,
        mock_clear_agent: MagicMock,  # noqa: ARG002
        mock_clear_sv: MagicMock,  # noqa: ARG002
        mock_shape: MagicMock,
    ) -> None:
        """``("updates", {node: state_update})`` arriving from astream
        becomes one ``kind=node_update`` event per node."""
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2_streaming

        mock_get_cp.return_value = _mock_checkpointer_with_current_version()
        graph = MagicMock()
        graph.astream = _astream_yielding(
            (
                "updates",
                {"route_or_classify": {"current_intent": "GENERAL"}},
            ),
            ("updates", {"dispatch_general": {"agent_response": {"message": "hi"}}}),
        )
        graph.aget_state = _aget_state_returning(
            {"agent_response": {"message": "hi"}, "active_agent": "general"}
        )
        mock_get_graph.return_value = graph

        mock_shape.return_value = {
            "message": "hi",
            "type": "message",
            "agent": "general",
            "intent": "GENERAL",
        }

        events = await _collect(
            invoke_supervisor_v2_streaming(
                message="hello",
                user_id="user-1",
                chat_id="chat-stream-1",
            )
        )

        kinds = [e["kind"] for e in events]
        assert kinds == ["node_update", "node_update", "final"]
        assert events[0]["node"] == "route_or_classify"
        assert events[0]["info"] == {"current_intent": "GENERAL"}
        assert events[1]["node"] == "dispatch_general"
        assert events[2]["result"]["message"] == "hi"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._shape_supervisor_response_from_state")
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_messages_events_become_tokens_with_content_filter(
        self,
        mock_get_graph: MagicMock,
        mock_get_cp: MagicMock,
        mock_clear_agent: MagicMock,  # noqa: ARG002
        mock_clear_sv: MagicMock,  # noqa: ARG002
        mock_shape: MagicMock,
    ) -> None:
        """``("messages", (chunk, meta))`` becomes ``kind=token`` events,
        but only for chunks with non-empty string content."""
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2_streaming

        mock_get_cp.return_value = _mock_checkpointer_with_current_version()
        graph = MagicMock()

        text_chunk = MagicMock()
        text_chunk.content = "Hello "
        empty_chunk = MagicMock()
        empty_chunk.content = ""  # no-op chunk (e.g. finish-reason only)
        tool_chunk = MagicMock()
        tool_chunk.content = None  # tool-call chunks have no text

        graph.astream = _astream_yielding(
            (
                "messages",
                (text_chunk, {"langgraph_node": "dispatch_general"}),
            ),
            (
                "messages",
                (empty_chunk, {"langgraph_node": "dispatch_general"}),
            ),
            (
                "messages",
                (tool_chunk, {"langgraph_node": "dispatch_general"}),
            ),
        )
        graph.aget_state = _aget_state_returning({})
        mock_get_graph.return_value = graph
        mock_shape.return_value = {"message": "Hello"}

        events = await _collect(
            invoke_supervisor_v2_streaming(
                message="hi",
                user_id="user-1",
                chat_id="chat-tokens-1",
            )
        )

        # Empty + None chunks are dropped — only the text one survives + the final.
        kinds = [e["kind"] for e in events]
        assert kinds == ["token", "final"]
        assert events[0]["text"] == "Hello "
        assert events[0]["node"] == "dispatch_general"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._shape_supervisor_response_from_state")
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_custom_events_pass_through_verbatim(
        self,
        mock_get_graph: MagicMock,
        mock_get_cp: MagicMock,
        mock_clear_agent: MagicMock,  # noqa: ARG002
        mock_clear_sv: MagicMock,  # noqa: ARG002
        mock_shape: MagicMock,
    ) -> None:
        """``("custom", payload)`` from tool ``get_stream_writer()`` calls
        flows through as ``kind=custom`` with the payload intact —
        piece 3 will use this for ``itinerary_partial`` chunks."""
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2_streaming

        mock_get_cp.return_value = _mock_checkpointer_with_current_version()
        graph = MagicMock()
        graph.astream = _astream_yielding(
            (
                "custom",
                {"type": "itinerary_partial", "day": 1, "title": "Arrival"},
            ),
        )
        graph.aget_state = _aget_state_returning({})
        mock_get_graph.return_value = graph
        mock_shape.return_value = {"message": "done"}

        events = await _collect(
            invoke_supervisor_v2_streaming(
                message="plan trip",
                user_id="user-1",
                chat_id="chat-custom-1",
            )
        )

        custom_events = [e for e in events if e["kind"] == "custom"]
        assert len(custom_events) == 1
        assert custom_events[0]["data"] == {
            "type": "itinerary_partial",
            "day": 1,
            "title": "Arrival",
        }


# ---------------------------------------------------------------------------
# Error path — non-retryable + retryable
# ---------------------------------------------------------------------------


class TestStreamingErrorPath:
    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_non_retryable_failure_emits_error_terminal(
        self,
        mock_get_graph: MagicMock,
        mock_get_cp: MagicMock,
        mock_clear_agent: MagicMock,  # noqa: ARG002
        mock_clear_sv: MagicMock,  # noqa: ARG002
    ) -> None:
        """A ``BadRequestError`` (validation class — deterministic, not
        retryable) skips retry and surfaces as a single ``kind=error``
        terminal event with the classified user message."""
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2_streaming

        mock_get_cp.return_value = _mock_checkpointer_with_current_version()
        graph = MagicMock()
        bad_request = type("BadRequestError", (Exception,), {})("input rejected")
        graph.astream = _astream_raising(bad_request)
        graph.aget_state = AsyncMock()
        mock_get_graph.return_value = graph

        events = await _collect(
            invoke_supervisor_v2_streaming(
                message="garbage",
                user_id="user-1",
                chat_id="chat-bad-1",
            )
        )

        assert len(events) == 1
        assert events[0]["kind"] == "error"
        result = events[0]["result"]
        assert result["type"] == "error"
        assert result["error_class"] == "validation"
        # Don't leak the raw exception detail.
        assert "input rejected" not in result["message"]
        # aget_state shouldn't have been called — we failed before completing.
        graph.aget_state.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._shape_supervisor_response_from_state")
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_transient_retryable_failure_before_any_yield_retries_once(
        self,
        mock_get_graph: MagicMock,
        mock_get_cp: MagicMock,
        mock_clear_agent: MagicMock,  # noqa: ARG002
        mock_clear_sv: MagicMock,  # noqa: ARG002
        mock_shape: MagicMock,
    ) -> None:
        """``RateLimitError`` (transient_llm) before any event has been
        yielded triggers exactly ONE retry. Second attempt succeeds →
        final event emitted normally."""
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2_streaming

        mock_get_cp.return_value = _mock_checkpointer_with_current_version()

        # First call raises before yielding; second call yields then succeeds.
        rate_limit = type("RateLimitError", (Exception,), {})("slow down")
        attempts: list[int] = []

        def _astream_first_fails_then_succeeds(
            *_args: Any, **_kwargs: Any
        ) -> AsyncIterator[tuple[str, Any]]:
            attempts.append(1)
            attempt = len(attempts)

            async def _gen() -> AsyncIterator[tuple[str, Any]]:
                if attempt == 1:
                    raise rate_limit
                yield ("updates", {"dispatch_general": {"agent_response": {}}})

            return _gen()

        graph = MagicMock()
        graph.astream = _astream_first_fails_then_succeeds
        graph.aget_state = _aget_state_returning({})
        mock_get_graph.return_value = graph
        mock_shape.return_value = {"message": "recovered"}

        with patch(
            "asyncio.sleep", new_callable=AsyncMock
        ):  # short-circuit retry sleep
            events = await _collect(
                invoke_supervisor_v2_streaming(
                    message="hi",
                    user_id="user-1",
                    chat_id="chat-retry-1",
                )
            )

        kinds = [e["kind"] for e in events]
        assert kinds == ["node_update", "final"]
        assert len(attempts) == 2  # one initial + one retry
        assert events[-1]["result"]["message"] == "recovered"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_retryable_failure_AFTER_yield_is_not_retried(
        self,
        mock_get_graph: MagicMock,
        mock_get_cp: MagicMock,
        mock_clear_agent: MagicMock,  # noqa: ARG002
        mock_clear_sv: MagicMock,  # noqa: ARG002
    ) -> None:
        """Once intermediate events have streamed to the client, a
        mid-flight transient failure surfaces as the terminal ``error``
        event — retrying would duplicate progress the client already saw."""
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2_streaming

        mock_get_cp.return_value = _mock_checkpointer_with_current_version()
        rate_limit = type("RateLimitError", (Exception,), {})("mid-flight 429")
        graph = MagicMock()
        graph.astream = _astream_raising(
            rate_limit,
            ("updates", {"route_or_classify": {"current_intent": "GENERAL"}}),
        )
        graph.aget_state = AsyncMock()
        mock_get_graph.return_value = graph

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            events = await _collect(
                invoke_supervisor_v2_streaming(
                    message="hi",
                    user_id="user-1",
                    chat_id="chat-mid-1",
                )
            )

        # node_update fired before the failure; then error (no retry).
        kinds = [e["kind"] for e in events]
        assert kinds == ["node_update", "error"]
        assert events[-1]["result"]["error_class"] == "transient_llm"
        # No sleep — no retry was attempted.
        mock_sleep.assert_not_called()
