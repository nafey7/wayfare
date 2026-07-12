"""End-to-end verification of AI-CHAT-010 error resilience.

For each :class:`~app.ai.errors.ErrorClass` we *deliberately* make
``graph.ainvoke`` raise a realistic exception of that class, call the public
entry point :func:`~app.ai.graph.supervisor_v2.invoke_supervisor_v2`, and
assert that the user actually sees the class-specific message + the response
payload carries the right ``error_class`` field.

Plus:
- Retry policy: only ``transient_llm`` / ``transient_api`` retry; one attempt
  is enough to recover when the second call succeeds.
- Consecutive-error counter + Slack alert + soft-reset offer.
- Counter reset on success.

Why this lives next to ``test_supervisor_v2.py``: it follows the same
mocking pattern (``patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")``)
and exercises the same public API. Pure unit-style — no DB, no real APIs.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.errors import (
    CONSECUTIVE_ERROR_ALERT_THRESHOLD,
    ErrorClass,
    get_error_count_for_session,
    post_consecutive_error_alert,
    record_error_for_session,
    reset_error_count_for_session,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_named_exception(name: str, message: str = "boom", **attrs: Any) -> Exception:
    """Build a one-off exception class with ``__name__`` == ``name``.

    The classifier matches on ``type(exc).__name__``, so we never need to
    import the real provider exception types — a locally-defined class with
    the right name is indistinguishable to the classifier.
    """
    cls = type(name, (Exception,), attrs)
    return cls(message)


def _mock_graph_raising(exc: Exception) -> MagicMock:
    """Build a mock supervisor graph whose ``ainvoke`` raises ``exc`` every call."""
    graph = MagicMock()
    graph.ainvoke = AsyncMock(side_effect=exc)
    return graph


def _mock_graph_raising_then_succeeding(
    exc: Exception, success_result: dict[str, Any]
) -> MagicMock:
    """Build a mock supervisor graph: 1st call raises, 2nd call returns success."""
    graph = MagicMock()
    graph.ainvoke = AsyncMock(side_effect=[exc, success_result])
    return graph


def _success_state() -> dict[str, Any]:
    """A minimal-but-valid supervisor result for the "graph succeeded" path."""
    return {
        "messages": [],
        "agent_response": {"message": "ok", "type": "message"},
        "active_agent": "general",
        "chain_responses": [],
    }


def _mock_checkpointer_returning(value: Any) -> MagicMock:
    """Build a checkpointer mock so ``invoke_supervisor_v2`` skips its clearing logic.

    Returning a checkpoint with the current schema version means no clearing
    happens (the version-guard branch is skipped) and we go straight to the
    graph invoke that we're trying to exercise.
    """
    from app.ai.graph.supervisor_v2 import SV2_CHECKPOINT_VERSION

    cp = MagicMock()
    cp.get.return_value = {
        "channel_values": {"checkpoint_version": SV2_CHECKPOINT_VERSION},
    }
    return MagicMock(return_value=cp)


# ---------------------------------------------------------------------------
# ErrorClass surface assertions: each class produces the right user message
# + the right ``error_class`` field at the public API boundary.
# ---------------------------------------------------------------------------


# (exception_name, status_code_or_None, expected_class_value, user_msg_fragment)
ERROR_CASES = [
    # OpenAI 429 — transient_llm — message attributes the wait to "Our AI"
    ("RateLimitError", None, "transient_llm", "our ai"),
    # FlightLogic 503 wrapped — transient_api — "travel-data partner is slow"
    ("FlightApiError", 503, "transient_api", "travel-data partner"),
    # OpenAI BadRequestError — validation — "rephrase"
    ("BadRequestError", None, "validation", "rephrase"),
    # OpenAI content policy — content_policy — "rephrasing" / "travel planning"
    ("ContentPolicyViolationError", None, "content_policy", "rephrasing"),
    # OpenAI 401 — quota — "quota"
    ("AuthenticationError", None, "quota", "quota"),
    # Truly unknown — unknown — "unexpected"
    ("SomethingNobodyHasSeen", None, "unknown", "unexpected"),
]


class TestEachErrorClassSurfacesThroughSupervisor:
    """End-to-end: per-class exception → ``invoke_supervisor_v2`` response shape."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("exc_name", "status_code", "expected_class", "expected_msg_fragment"),
        ERROR_CASES,
    )
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_error_class_surfaces_with_correct_message(
        self,
        mock_get_graph: MagicMock,
        mock_get_checkpointer: MagicMock,
        mock_clear_agent: MagicMock,
        mock_clear_sv: MagicMock,
        exc_name: str,
        status_code: int | None,
        expected_class: str,
        expected_msg_fragment: str,
    ) -> None:
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2

        # Build the exception. FlightApiError needs ``status_code`` for the
        # classifier's special-case routing.
        attrs: dict[str, Any] = {}
        if status_code is not None:
            attrs["status_code"] = status_code
        exc = _make_named_exception(exc_name, "deliberate test failure", **attrs)

        mock_get_graph.return_value = _mock_graph_raising(exc)
        mock_get_checkpointer.return_value = _mock_checkpointer_returning(None)()
        # Re-wrap: the call site uses ``_get_sv2_checkpointer()`` (no args)
        # so we want the factory-mock to be the callable.
        mock_get_checkpointer.side_effect = None
        cp = MagicMock()
        from app.ai.graph.supervisor_v2 import SV2_CHECKPOINT_VERSION

        cp.get.return_value = {
            "channel_values": {"checkpoint_version": SV2_CHECKPOINT_VERSION},
        }
        mock_get_checkpointer.return_value = cp

        result = await invoke_supervisor_v2(
            message=f"test for {exc_name}",
            user_id="user-err",
            chat_id=f"chat-{exc_name}",
        )

        # Public-API contract: every error path returns the same shape.
        assert result["type"] == "error", (
            f"{exc_name} should surface as type=error, got {result.get('type')!r}"
        )
        assert result["error_class"] == expected_class, (
            f"{exc_name} → expected error_class={expected_class!r}, "
            f"got {result.get('error_class')!r}"
        )
        assert expected_msg_fragment.lower() in result["message"].lower(), (
            f"{exc_name} user message should mention '{expected_msg_fragment}' — "
            f"got: {result['message']!r}"
        )
        assert result["message_id"]
        # The old opaque phrasing must never come back.
        assert "i encountered an error" not in result["message"].lower()
        assert "i'm having trouble right now" not in result["message"].lower()


# ---------------------------------------------------------------------------
# Retry behaviour: only transient classes retry; success on 2nd attempt
# means the user sees a normal response, not an error.
# ---------------------------------------------------------------------------


class TestRetryPolicy:
    """``_invoke_with_retry`` retries only on transient classes."""

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    @patch("app.ai.graph.supervisor_v2.asyncio.sleep", new_callable=AsyncMock)
    async def test_transient_llm_retries_once_and_recovers(
        self,
        mock_sleep: AsyncMock,
        mock_get_graph: MagicMock,
        mock_get_checkpointer: MagicMock,
        mock_clear_agent: MagicMock,
        mock_clear_sv: MagicMock,
    ) -> None:
        from app.ai.graph.supervisor_v2 import (
            SV2_CHECKPOINT_VERSION,
            invoke_supervisor_v2,
        )

        exc = _make_named_exception("RateLimitError", "transient blip")
        graph = _mock_graph_raising_then_succeeding(exc, _success_state())
        mock_get_graph.return_value = graph

        cp = MagicMock()
        cp.get.return_value = {
            "channel_values": {"checkpoint_version": SV2_CHECKPOINT_VERSION},
        }
        mock_get_checkpointer.return_value = cp

        result = await invoke_supervisor_v2(
            message="ratelimit then succeed",
            user_id="user-retry",
            chat_id="chat-retry-llm",
        )

        # ainvoke called twice: first raised, second succeeded.
        assert graph.ainvoke.call_count == 2
        # User sees the success result, NOT an error.
        assert result["type"] != "error"
        assert result["message"] == "ok"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    @patch("app.ai.graph.supervisor_v2.asyncio.sleep", new_callable=AsyncMock)
    async def test_transient_api_retries_once_and_recovers(
        self,
        mock_sleep: AsyncMock,
        mock_get_graph: MagicMock,
        mock_get_checkpointer: MagicMock,
        mock_clear_agent: MagicMock,
        mock_clear_sv: MagicMock,
    ) -> None:
        from app.ai.graph.supervisor_v2 import (
            SV2_CHECKPOINT_VERSION,
            invoke_supervisor_v2,
        )

        exc = _make_named_exception("TimeoutException", "FlightLogic slow")
        graph = _mock_graph_raising_then_succeeding(exc, _success_state())
        mock_get_graph.return_value = graph

        cp = MagicMock()
        cp.get.return_value = {
            "channel_values": {"checkpoint_version": SV2_CHECKPOINT_VERSION},
        }
        mock_get_checkpointer.return_value = cp

        result = await invoke_supervisor_v2(
            message="timeout then succeed",
            user_id="user-retry",
            chat_id="chat-retry-api",
        )

        assert graph.ainvoke.call_count == 2
        assert result["type"] != "error"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    @patch("app.ai.graph.supervisor_v2.asyncio.sleep", new_callable=AsyncMock)
    async def test_validation_does_not_retry(
        self,
        mock_sleep: AsyncMock,
        mock_get_graph: MagicMock,
        mock_get_checkpointer: MagicMock,
        mock_clear_agent: MagicMock,
        mock_clear_sv: MagicMock,
    ) -> None:
        """Deterministic failures should NOT burn a second graph invocation."""
        from app.ai.graph.supervisor_v2 import (
            SV2_CHECKPOINT_VERSION,
            invoke_supervisor_v2,
        )

        exc = _make_named_exception("ValueError", "bad date format")
        graph = _mock_graph_raising(exc)
        mock_get_graph.return_value = graph

        cp = MagicMock()
        cp.get.return_value = {
            "channel_values": {"checkpoint_version": SV2_CHECKPOINT_VERSION},
        }
        mock_get_checkpointer.return_value = cp

        result = await invoke_supervisor_v2(
            message="bad input",
            user_id="user-noretry",
            chat_id="chat-noretry-validation",
        )

        assert graph.ainvoke.call_count == 1, (
            "Validation errors must not retry — retrying burns time on a "
            "guaranteed-identical failure."
        )
        assert result["type"] == "error"
        assert result["error_class"] == "validation"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    @patch("app.ai.graph.supervisor_v2.asyncio.sleep", new_callable=AsyncMock)
    async def test_quota_does_not_retry(
        self,
        mock_sleep: AsyncMock,
        mock_get_graph: MagicMock,
        mock_get_checkpointer: MagicMock,
        mock_clear_agent: MagicMock,
        mock_clear_sv: MagicMock,
    ) -> None:
        from app.ai.graph.supervisor_v2 import (
            SV2_CHECKPOINT_VERSION,
            invoke_supervisor_v2,
        )

        exc = _make_named_exception("AuthenticationError", "quota exceeded")
        graph = _mock_graph_raising(exc)
        mock_get_graph.return_value = graph

        cp = MagicMock()
        cp.get.return_value = {
            "channel_values": {"checkpoint_version": SV2_CHECKPOINT_VERSION},
        }
        mock_get_checkpointer.return_value = cp

        result = await invoke_supervisor_v2(
            message="...",
            user_id="user-quota",
            chat_id="chat-quota",
        )

        assert graph.ainvoke.call_count == 1
        assert result["error_class"] == "quota"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    @patch("app.ai.graph.supervisor_v2.asyncio.sleep", new_callable=AsyncMock)
    async def test_transient_failing_both_attempts_surfaces_error(
        self,
        mock_sleep: AsyncMock,
        mock_get_graph: MagicMock,
        mock_get_checkpointer: MagicMock,
        mock_clear_agent: MagicMock,
        mock_clear_sv: MagicMock,
    ) -> None:
        """If the retry also fails, we surface the classified error to the user.

        We don't loop forever — one retry, then we hand the user back a
        useful message.
        """
        from app.ai.graph.supervisor_v2 import (
            SV2_CHECKPOINT_VERSION,
            invoke_supervisor_v2,
        )

        exc = _make_named_exception("RateLimitError", "still ratelimited")
        graph = _mock_graph_raising(exc)
        mock_get_graph.return_value = graph

        cp = MagicMock()
        cp.get.return_value = {
            "channel_values": {"checkpoint_version": SV2_CHECKPOINT_VERSION},
        }
        mock_get_checkpointer.return_value = cp

        result = await invoke_supervisor_v2(
            message="...",
            user_id="user-r",
            chat_id="chat-r",
        )

        assert graph.ainvoke.call_count == 2, "Should attempt original + one retry"
        assert result["type"] == "error"
        assert result["error_class"] == "transient_llm"


# ---------------------------------------------------------------------------
# Consecutive-error counter: increment on error, reset on success.
# Process-local state — each test uses a unique chat_id to stay isolated.
# ---------------------------------------------------------------------------


class TestConsecutiveErrorCounter:
    """Pure counter mechanics — no graph or Slack involved."""

    def test_counter_increments_on_each_error(self) -> None:
        chat_id = "counter-test-increment"
        reset_error_count_for_session(chat_id)  # clean slate

        count1, _ = record_error_for_session(chat_id, "transient_llm")
        count2, _ = record_error_for_session(chat_id, "transient_api")
        count3, classes = record_error_for_session(chat_id, "validation")

        assert count1 == 1
        assert count2 == 2
        assert count3 == 3
        assert classes == ["transient_llm", "transient_api", "validation"]

    def test_rolling_buffer_caps_at_three(self) -> None:
        chat_id = "counter-test-buffer-cap"
        reset_error_count_for_session(chat_id)

        for cls in ("a", "b", "c", "d", "e"):
            count, classes = record_error_for_session(chat_id, cls)

        assert count == 5
        assert classes == ["c", "d", "e"], (
            "Rolling buffer should keep only the most recent 3 classes"
        )

    def test_reset_clears_count(self) -> None:
        chat_id = "counter-test-reset"
        reset_error_count_for_session(chat_id)
        record_error_for_session(chat_id, "transient_llm")
        record_error_for_session(chat_id, "transient_llm")
        assert get_error_count_for_session(chat_id) == 2

        reset_error_count_for_session(chat_id)
        assert get_error_count_for_session(chat_id) == 0

    def test_threshold_constant_is_three(self) -> None:
        # Test guards against accidentally lowering the threshold in code
        # without updating tests + on-call expectations.
        assert CONSECUTIVE_ERROR_ALERT_THRESHOLD == 3

    def test_dict_is_bounded_by_max_tracked_sessions(self) -> None:
        """``_CONSECUTIVE_ERRORS`` must not grow past ``_MAX_TRACKED_ERROR_SESSIONS``.

        Regression for PR #1088 review item #4 — without the FIFO eviction,
        a stream of persistently-erroring abandoned sessions would leak.
        """
        from app.ai import errors as errors_mod

        # Snapshot + clear so the test starts from a clean slate, even if
        # other tests left entries behind.
        original = dict(errors_mod._CONSECUTIVE_ERRORS)
        errors_mod._CONSECUTIVE_ERRORS.clear()
        try:
            cap = errors_mod._MAX_TRACKED_ERROR_SESSIONS
            # Push cap + 50 distinct chat_ids — none reset (these are the
            # abandoned/failing sessions the eviction is designed for).
            for i in range(cap + 50):
                record_error_for_session(f"runaway-{i}", "transient_llm")

            assert len(errors_mod._CONSECUTIVE_ERRORS) == cap
            # Oldest 50 must be gone; newest cap must remain.
            assert "runaway-0" not in errors_mod._CONSECUTIVE_ERRORS
            assert "runaway-49" not in errors_mod._CONSECUTIVE_ERRORS
            assert f"runaway-{cap + 49}" in errors_mod._CONSECUTIVE_ERRORS
        finally:
            errors_mod._CONSECUTIVE_ERRORS.clear()
            errors_mod._CONSECUTIVE_ERRORS.update(original)

    def test_buffer_length_follows_alert_threshold(self) -> None:
        """Rolling buffer caps at ``CONSECUTIVE_ERROR_ALERT_THRESHOLD`` entries.

        Regression for PR #1088 review item #7 — bumping the threshold
        should automatically bring the buffer size with it.
        """
        chat_id = "buffer-tracks-threshold"
        reset_error_count_for_session(chat_id)
        for i in range(CONSECUTIVE_ERROR_ALERT_THRESHOLD + 5):
            _, classes = record_error_for_session(chat_id, f"class_{i}")
        assert len(classes) == CONSECUTIVE_ERROR_ALERT_THRESHOLD


# ---------------------------------------------------------------------------
# Slack alert payload + behaviour
# ---------------------------------------------------------------------------


class TestSlackAlertHelper:
    """``post_consecutive_error_alert`` posts to the configured webhook."""

    @pytest.mark.asyncio
    async def test_no_webhook_set_logs_and_returns(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

        # Should NOT raise even without a webhook — fire-and-forget contract.
        await post_consecutive_error_alert(
            chat_id="x",
            user_id="u",
            consecutive_count=3,
            recent_error_classes=["transient_llm", "transient_api", "unknown"],
        )

    @pytest.mark.asyncio
    async def test_with_webhook_posts_payload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.example.com/T/B/X")

        mock_response = MagicMock(status_code=200, text="ok")
        # Mock the httpx.AsyncClient(...) context manager and its .post()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        # __aenter__ returns the client; __aexit__ returns None
        async_cm = MagicMock()
        async_cm.__aenter__ = AsyncMock(return_value=mock_client)
        async_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=async_cm):
            await post_consecutive_error_alert(
                chat_id="chat-burning",
                user_id="user-99",
                consecutive_count=3,
                recent_error_classes=[
                    "transient_llm",
                    "transient_llm",
                    "validation",
                ],
                latest_user_message="book me a flight to Mars",
            )

        mock_client.post.assert_awaited_once()
        call_args = mock_client.post.call_args
        # First positional arg is the URL
        assert call_args.args[0] == "https://hooks.example.com/T/B/X"
        # JSON payload includes the diagnostic fields
        payload = call_args.kwargs["json"]
        text = payload["text"]
        assert "chat-burning" in text
        assert "user-99" in text
        assert "3 consecutive errors" in text
        assert "transient_llm" in text
        assert "validation" in text
        assert "book me a flight to Mars" in text

    @pytest.mark.asyncio
    async def test_slack_failure_does_not_raise(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Slack downtime must never break the chat request path."""
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.example.com/T/B/X")

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=RuntimeError("Slack down"))
        async_cm = MagicMock()
        async_cm.__aenter__ = AsyncMock(return_value=mock_client)
        async_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=async_cm):
            await post_consecutive_error_alert(
                chat_id="x",
                user_id="u",
                consecutive_count=3,
                recent_error_classes=["unknown"],
            )
        # If we got here without raising, the contract is satisfied.


# ---------------------------------------------------------------------------
# End-to-end through ChatService: 3 consecutive errors → reset offer appended
# ---------------------------------------------------------------------------


class TestChatServiceConsecutiveErrorBehavior:
    """``ChatService.process_message`` integrates counter + Slack + soft-reset."""

    @staticmethod
    def _build_user() -> Any:
        from datetime import UTC, datetime

        from app.domains.common import AuthProvider
        from app.domains.user.enums import UserStatus
        from app.domains.user.schemas import UserPublic

        return UserPublic(
            id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
            email="t@example.com",
            first_name="T",
            last_name="U",
            status=UserStatus.ACTIVE,
            email_verified=True,
            auth_provider=AuthProvider.LOCAL,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @staticmethod
    def _patches(supervisor_mock: AsyncMock) -> list[Any]:
        """Build the set of patches needed to run ChatService.process_message
        without hitting MongoDB.

        ``invoke_supervisor_v2`` is imported INSIDE
        ``_handle_via_supervisor_v2`` (lazy import), so we have to patch it
        at its source module — not at ``app.domains.chat.service``.
        """
        return [
            patch(
                "app.ai.graph.supervisor_v2.invoke_supervisor_v2",
                new=supervisor_mock,
            ),
            patch(
                "app.domains.chat.service._is_duplicate_resend",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "app.domains.chat.service.repository.create_message",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.domains.chat.service.repository.update_conversation_on_message",
                new=AsyncMock(return_value=None),
            ),
        ]

    @pytest.mark.asyncio
    async def test_three_consecutive_errors_appends_reset_offer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After 3 consecutive errors, the user sees a 'reset our conversation' offer.

        We bypass real persistence by mocking the supervisor invoke + the
        ``repository`` module functions that ChatService touches after the
        result lands.
        """
        from app.domains.chat.service import ChatService

        # No webhook → post_consecutive_error_alert just logs and returns.
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

        chat_id = "chatsvc-3-errors"
        reset_error_count_for_session(chat_id)

        # The supervisor returns a transient_llm error every time.
        error_result = {
            "message": "Our AI is a bit busy right now — give me a moment and try again.",
            "type": "error",
            "error_class": "transient_llm",
            "message_id": "m-1",
            "response_time": 0.01,
        }
        supervisor_mock = AsyncMock(return_value=error_result)

        # _get_conversation_doc is a method on ChatService — patch via the class.
        from contextlib import ExitStack

        with ExitStack() as stack:
            for p in self._patches(supervisor_mock):
                stack.enter_context(p)
            stack.enter_context(
                patch.object(
                    ChatService,
                    "_get_conversation_doc",
                    new=AsyncMock(return_value=None),
                )
            )

            service = ChatService()
            user = self._build_user()

            responses = []
            for _ in range(3):
                resp = await service.process_message(
                    message="anything",
                    user=user,
                    chat_id=chat_id,
                )
                responses.append(resp)

        # First two: classified error, no reset offer yet.
        for r in responses[:2]:
            assert r.type == "error"
            assert "reset our conversation" not in (r.message or "").lower()

        # Third: classified error PLUS the soft-reset offer.
        final = responses[2]
        assert final.type == "error"
        assert final.message is not None
        assert "reset our conversation" in final.message.lower(), (
            f"Expected soft-reset offer in 3rd-error message, got: {final.message!r}"
        )

    @pytest.mark.asyncio
    async def test_alert_fires_only_on_boundary_crossing_turn(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Past-threshold turns must NOT re-spam Slack or re-append the reset offer.

        Regression for PR #1088 review item #5 — counts of 4, 5, 6 should keep
        incrementing but not trigger another alert or stack the offer onto
        every subsequent reply.
        """
        from contextlib import ExitStack

        from app.domains.chat.service import ChatService

        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

        chat_id = "chatsvc-past-threshold"
        reset_error_count_for_session(chat_id)

        # NB: build a fresh dict per call so the ChatService's in-place
        # ``result["message"] = ...`` mutation on the boundary turn doesn't
        # leak into subsequent turns' "supervisor output".
        def _fresh_error(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            return {
                "message": (
                    "Our AI is a bit busy right now — give me a moment and try again."
                ),
                "type": "error",
                "error_class": "transient_llm",
                "message_id": "m-1",
                "response_time": 0.01,
            }

        supervisor_mock = AsyncMock(side_effect=_fresh_error)
        alert_mock = AsyncMock(return_value=None)

        with ExitStack() as stack:
            for p in self._patches(supervisor_mock):
                stack.enter_context(p)
            stack.enter_context(
                patch.object(
                    ChatService,
                    "_get_conversation_doc",
                    new=AsyncMock(return_value=None),
                )
            )
            stack.enter_context(
                patch(
                    "app.ai.errors.post_consecutive_error_alert",
                    new=alert_mock,
                )
            )

            service = ChatService()
            user = self._build_user()
            responses = []
            for _ in range(5):
                responses.append(
                    await service.process_message(
                        message="...", user=user, chat_id=chat_id
                    )
                )

        # Only the 3rd response (boundary crossing) carries the reset offer.
        assert "reset our conversation" not in (responses[0].message or "").lower()
        assert "reset our conversation" not in (responses[1].message or "").lower()
        assert "reset our conversation" in (responses[2].message or "").lower()
        # 4th and 5th must NOT append the offer again.
        assert "reset our conversation" not in (responses[3].message or "").lower()
        assert "reset our conversation" not in (responses[4].message or "").lower()
        # Slack alert fired exactly once — on the boundary.
        assert alert_mock.await_count == 1

    @pytest.mark.asyncio
    async def test_outer_exception_routes_through_classifier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An exception that escapes invoke_supervisor_v2 still gets classified.

        Regression for PR #1088 review item #2 — pre-fix, the outer
        ``except Exception`` swallowed the failure with the old opaque
        copy and never touched the counter or Slack.
        """
        from contextlib import ExitStack

        from app.domains.chat.service import ChatService

        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        chat_id = "chatsvc-outer-raise"
        reset_error_count_for_session(chat_id)

        # The supervisor RAISES (not returns) — exercises the outer except.
        raising_mock = AsyncMock(
            side_effect=_make_named_exception("RateLimitError", "boom")
        )

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "app.ai.graph.supervisor_v2.invoke_supervisor_v2",
                    new=raising_mock,
                )
            )
            stack.enter_context(
                patch(
                    "app.domains.chat.service._is_duplicate_resend",
                    new=AsyncMock(return_value=False),
                )
            )

            service = ChatService()
            user = self._build_user()
            response = await service.process_message(
                message="anything", user=user, chat_id=chat_id
            )

        # Classified — not the old "I'm having trouble processing your request" copy.
        assert response.type == "error"
        assert response.message is not None
        assert "our ai is a bit busy" in response.message.lower()
        assert (response.data or {}).get("error_class") == "transient_llm"
        # Counter bumped — proves the telemetry path ran.
        assert get_error_count_for_session(chat_id) == 1

    @pytest.mark.asyncio
    async def test_success_resets_counter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A successful turn resets the consecutive-error counter."""
        from contextlib import ExitStack

        from app.domains.chat.service import ChatService

        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

        chat_id = "chatsvc-reset-on-success"
        reset_error_count_for_session(chat_id)
        # Pre-load 2 errors — one more would trip the threshold.
        record_error_for_session(chat_id, "transient_llm")
        record_error_for_session(chat_id, "transient_llm")
        assert get_error_count_for_session(chat_id) == 2

        success_result = {
            "message": "Sure, here's your itinerary.",
            "type": "message",
            "data": None,
            "suggestions": None,
            "message_id": "m-2",
            "agent": "general",
            "intent": "general",
            "confidence": 1.0,
            "response_time": 0.01,
        }
        supervisor_mock = AsyncMock(return_value=success_result)

        with ExitStack() as stack:
            for p in self._patches(supervisor_mock):
                stack.enter_context(p)
            stack.enter_context(
                patch.object(
                    ChatService,
                    "_get_conversation_doc",
                    new=AsyncMock(return_value=None),
                )
            )

            service = ChatService()
            user = self._build_user()
            await service.process_message(message="hi", user=user, chat_id=chat_id)

        assert get_error_count_for_session(chat_id) == 0, (
            "A successful turn must reset the consecutive-error counter."
        )


# ---------------------------------------------------------------------------
# Sanity: ErrorClass values are stable strings — guards against drift
# in cross-system contracts (Langfuse / Sentry tag values).
# ---------------------------------------------------------------------------


class TestErrorClassContract:
    def test_all_class_values_are_lowercase_snake(self) -> None:
        for cls in ErrorClass:
            assert cls.value == cls.value.lower()
            assert " " not in cls.value
            assert cls.value.replace("_", "").isalnum()

    def test_class_values_are_stable_strings(self) -> None:
        # If any of these change, telemetry dashboards will silently break.
        assert ErrorClass.TRANSIENT_LLM.value == "transient_llm"
        assert ErrorClass.TRANSIENT_API.value == "transient_api"
        assert ErrorClass.VALIDATION.value == "validation"
        assert ErrorClass.CONTENT_POLICY.value == "content_policy"
        assert ErrorClass.QUOTA.value == "quota"
        assert ErrorClass.UNKNOWN.value == "unknown"
