"""End-to-end tests for AI-CHAT-011 verification + retry + fallback wiring.

These complement ``test_output_verification.py`` (which covers the pure
detector). Here we test the wiring in ``invoke_supervisor_v2``:

- Telemetry-only path: detection fires, logs warning, **no behaviour change**.
- Retry path (feature-flag on): false claim → retry → success swaps in.
- Retry path (feature-flag on): false claim → retry → still false → honest
  fallback replaces the message.
- Retry path (feature-flag off): detection logs, no retry, behaviour unchanged.

Each test mocks the underlying ``graph.ainvoke`` + ``_dispatch_agent`` so we
exercise the supervisor's verification-handling logic without invoking real
LLMs or tools.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — build the LangGraph "final state" the supervisor's verification
# call inspects. Matches the shape ``graph.ainvoke`` returns in production.
# ---------------------------------------------------------------------------


def _result_state_with(
    *,
    active_agent: str,
    agent_response: dict[str, Any],
) -> dict[str, Any]:
    """Build the dict ``await graph.ainvoke(...)`` returns to invoke_supervisor_v2."""
    from langchain_core.messages import HumanMessage

    return {
        "messages": [HumanMessage(content="Plan a 5-day Tokyo trip")],
        "active_agent": active_agent,
        "agent_response": agent_response,
        "chain_responses": [],
        "current_intent": "GENERAL",
        "classification_confidence": 1.0,
    }


def _mock_checkpointer() -> MagicMock:
    """Bypass the checkpoint version-guard branch — returns a checkpoint
    that matches the current schema so no clearing fires."""
    from app.ai.graph.supervisor_v2 import SV2_CHECKPOINT_VERSION

    cp = MagicMock()
    cp.get.return_value = {
        "channel_values": {"checkpoint_version": SV2_CHECKPOINT_VERSION},
    }
    return cp


def _real_itinerary_response() -> dict[str, Any]:
    """A real itinerary_results response (artifact populated)."""
    return {
        "message": "Here's your 5-day Tokyo trip!",
        "type": "itinerary_results",
        "metadata": {
            "structured_itinerary": {
                "itineraryItems": [
                    {"day": 1, "activities": ["Asakusa"]},
                    {"day": 2, "activities": ["Shibuya"]},
                ],
            },
        },
    }


def _hallucinated_itinerary_response() -> dict[str, Any]:
    """An itinerary_results response with the artifact missing — the bug."""
    return {
        "message": "Here's your 5-day Tokyo trip!",
        "type": "itinerary_results",
        # NB: no `metadata` — the smoking gun
    }


# ---------------------------------------------------------------------------
# Telemetry-only behaviour (retry flag OFF)
# ---------------------------------------------------------------------------


class TestVerificationTelemetryOnly:
    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._dispatch_agent")
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_false_completion_logs_warning_and_passes_through(
        self,
        mock_get_graph: MagicMock,
        mock_get_cp: MagicMock,
        mock_clear_a: MagicMock,
        mock_clear_sv: MagicMock,
        mock_dispatch: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Retry flag OFF: detected false claim logs but ships unchanged."""
        import logging

        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2

        # Default-on flag — kill switch off via explicit false.
        monkeypatch.setenv("AI_CHAT_011_VERIFICATION_ENABLED", "false")

        mock_get_cp.return_value = _mock_checkpointer()
        graph = MagicMock()
        graph.ainvoke = AsyncMock(
            return_value=_result_state_with(
                active_agent="itinerary",
                agent_response=_hallucinated_itinerary_response(),
            )
        )
        mock_get_graph.return_value = graph

        with caplog.at_level(logging.WARNING, logger="app.ai.graph.supervisor_v2"):
            result = await invoke_supervisor_v2(
                message="Plan a 5-day Tokyo trip",
                user_id="u1",
                chat_id="chat-telemetry-only",
            )

        # Behaviour unchanged: user still gets the hallucinated message.
        assert result["type"] == "itinerary_results"
        assert "Here's your 5-day Tokyo trip!" in result["message"]
        # Retry never fired — _dispatch_agent NOT called.
        mock_dispatch.assert_not_called()
        # But the warning IS logged.
        assert any(
            "ai_chat_011.false_completion_detected" in rec.message
            for rec in caplog.records
        )

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._dispatch_agent")
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_real_itinerary_does_not_trigger_telemetry(
        self,
        mock_get_graph: MagicMock,
        mock_get_cp: MagicMock,
        mock_clear_a: MagicMock,
        mock_clear_sv: MagicMock,
        mock_dispatch: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Happy path: no detection, no warning, no retry."""
        import logging

        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2

        # Default-on flag — kill switch off via explicit false.
        monkeypatch.setenv("AI_CHAT_011_VERIFICATION_ENABLED", "false")

        mock_get_cp.return_value = _mock_checkpointer()
        graph = MagicMock()
        graph.ainvoke = AsyncMock(
            return_value=_result_state_with(
                active_agent="itinerary",
                agent_response=_real_itinerary_response(),
            )
        )
        mock_get_graph.return_value = graph

        with caplog.at_level(logging.WARNING, logger="app.ai.graph.supervisor_v2"):
            await invoke_supervisor_v2(
                message="Plan a 5-day Tokyo trip",
                user_id="u1",
                chat_id="chat-happy",
            )

        mock_dispatch.assert_not_called()
        assert not any(
            "ai_chat_011.false_completion_detected" in rec.message
            for rec in caplog.records
        )


# ---------------------------------------------------------------------------
# Retry behaviour (flag ON)
# ---------------------------------------------------------------------------


class TestVerificationRetry:
    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._dispatch_agent")
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_retry_recovers_to_real_itinerary(
        self,
        mock_get_graph: MagicMock,
        mock_get_cp: MagicMock,
        mock_clear_a: MagicMock,
        mock_clear_sv: MagicMock,
        mock_dispatch: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """First response false → retry → real itinerary → user sees it."""
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2

        monkeypatch.setenv("AI_CHAT_011_VERIFICATION_ENABLED", "true")

        mock_get_cp.return_value = _mock_checkpointer()
        # graph.ainvoke returns the hallucinated response
        graph = MagicMock()
        graph.ainvoke = AsyncMock(
            return_value=_result_state_with(
                active_agent="itinerary",
                agent_response=_hallucinated_itinerary_response(),
            )
        )
        mock_get_graph.return_value = graph
        # _dispatch_agent (the retry) returns a REAL itinerary
        mock_dispatch.return_value = {"agent_response": _real_itinerary_response()}

        result = await invoke_supervisor_v2(
            message="Plan a 5-day Tokyo trip",
            user_id="u1",
            chat_id="chat-retry-success",
        )

        # _dispatch_agent called exactly once (the retry — strict 1-budget)
        assert mock_dispatch.await_count == 1
        # User sees the REAL itinerary
        assert result["type"] == "itinerary_results"
        # And the artifact survived through to the response payload
        # (passed through via the **agent_response.items() spread)
        assert "metadata" in result

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._dispatch_agent")
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_retry_also_fails_falls_back_to_honest_message(
        self,
        mock_get_graph: MagicMock,
        mock_get_cp: MagicMock,
        mock_clear_a: MagicMock,
        mock_clear_sv: MagicMock,
        mock_dispatch: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """First false → retry → retry also false → honest fallback wins."""
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2

        monkeypatch.setenv("AI_CHAT_011_VERIFICATION_ENABLED", "true")

        mock_get_cp.return_value = _mock_checkpointer()
        graph = MagicMock()
        graph.ainvoke = AsyncMock(
            return_value=_result_state_with(
                active_agent="itinerary",
                agent_response=_hallucinated_itinerary_response(),
            )
        )
        mock_get_graph.return_value = graph
        # Retry ALSO hallucinates
        mock_dispatch.return_value = {
            "agent_response": _hallucinated_itinerary_response()
        }

        result = await invoke_supervisor_v2(
            message="Plan a 5-day Tokyo trip",
            user_id="u1",
            chat_id="chat-retry-fail",
        )

        # Strict 1-retry budget — only one retry dispatch
        assert mock_dispatch.await_count == 1
        # User sees the HONEST fallback, NOT either hallucination
        assert "having trouble" in result["message"].lower()
        assert "rephrasing" in result["message"].lower()
        # Type downgraded to plain message so the FE doesn't try to render cards
        assert result["type"] == "message"
        # Structured tag for downstream telemetry / Sentry
        assert result.get("error_class") == "verification_failed"
        assert result.get("verification_claim_type") == "itinerary"

    @pytest.mark.asyncio
    @patch("app.ai.graph.supervisor_v2._dispatch_agent")
    @patch("app.ai.graph.supervisor_v2._clear_supervisor_checkpoint")
    @patch("app.ai.graph.supervisor_v2._clear_stale_agent_checkpoints")
    @patch("app.ai.graph.supervisor_v2._get_sv2_checkpointer")
    @patch("app.ai.graph.supervisor_v2.get_supervisor_v2_graph")
    async def test_retry_raises_exception_falls_back_to_honest_message(
        self,
        mock_get_graph: MagicMock,
        mock_get_cp: MagicMock,
        mock_clear_a: MagicMock,
        mock_clear_sv: MagicMock,
        mock_dispatch: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Retry returns no response (exception / empty) → honest fallback."""
        from app.ai.graph.supervisor_v2 import invoke_supervisor_v2

        monkeypatch.setenv("AI_CHAT_011_VERIFICATION_ENABLED", "true")

        mock_get_cp.return_value = _mock_checkpointer()
        graph = MagicMock()
        graph.ainvoke = AsyncMock(
            return_value=_result_state_with(
                active_agent="itinerary",
                agent_response=_hallucinated_itinerary_response(),
            )
        )
        mock_get_graph.return_value = graph
        # Retry raises (simulated infra failure)
        mock_dispatch.side_effect = RuntimeError("agent crashed")

        result = await invoke_supervisor_v2(
            message="Plan a 5-day Tokyo trip",
            user_id="u1",
            chat_id="chat-retry-raised",
        )

        # User still gets the honest message — retry path is best-effort,
        # never lets the exception ship the hallucination.
        assert "having trouble" in result["message"].lower()
        assert result["type"] == "message"
        assert result.get("error_class") == "verification_failed"


# ---------------------------------------------------------------------------
# Feature flag parsing
# ---------------------------------------------------------------------------


class TestKillSwitch:
    """``AI_CHAT_011_VERIFICATION_ENABLED`` is a kill switch — default ON,
    explicit ``false``/``0``/``no`` (case-insensitive) disables it."""

    @pytest.mark.parametrize(
        ("env_value", "expected"),
        [
            # Kill switch values — OFF
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("NO", False),
            # Everything else — ON (including unrecognised values; safer to
            # default to enabled than silently disable on a typo).
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("YES", True),
            ("", True),
            ("maybe", True),
        ],
    )
    def test_kill_switch_disables_only_for_explicit_false_values(
        self,
        env_value: str,
        expected: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from app.ai.graph.supervisor_v2 import _ai_chat_011_retry_enabled

        monkeypatch.setenv("AI_CHAT_011_VERIFICATION_ENABLED", env_value)
        assert _ai_chat_011_retry_enabled() is expected

    def test_flag_default_is_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unset env var → ON (kill-switch semantics)."""
        from app.ai.graph.supervisor_v2 import _ai_chat_011_retry_enabled

        monkeypatch.delenv("AI_CHAT_011_VERIFICATION_ENABLED", raising=False)
        assert _ai_chat_011_retry_enabled() is True
