"""Tests for ``cost_tracking.TokenUsageCollector`` and its wiring in
``traced_observation`` (#1053 Phase 0 P0.4).

Two layers:
1. ``TokenUsageCollector`` unit tests — feed synthetic ``LLMResult`` shapes
   for the three providers the collector understands (modern langchain
   ``usage_metadata``, legacy ``llm_output.token_usage``, ``response.usage``).
2. ``traced_observation`` integration — patch Langfuse + verify that on
   context exit the collector's totals are submitted as ``tokens_per_turn``
   and ``cost_per_turn_usd`` numeric scores.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.ai.graph.cost_tracking import (
    MODEL_PRICING,
    TokenUsageCollector,
    _resolve_pricing,
)

# ---------------------------------------------------------------------------
# Helpers — build fake LLMResult-like objects for each provider shape
# ---------------------------------------------------------------------------


def _make_modern_chat_response(
    *,
    model_name: str = "gpt-5.4-mini",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
) -> Any:
    """Shape 1: usage_metadata on the AIMessage (langchain-openai 2024+)."""
    message = SimpleNamespace(
        usage_metadata={
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        response_metadata={"model_name": model_name},
    )
    generation = SimpleNamespace(message=message, generation_info=None)
    return SimpleNamespace(
        generations=[[generation]],
        llm_output={"model_name": model_name},
    )


def _make_legacy_openai_response(
    *,
    model_name: str = "gpt-5.4",
    prompt_tokens: int = 200,
    completion_tokens: int = 80,
) -> Any:
    """Shape 2: llm_output.token_usage (legacy OpenAI wrapper)."""
    return SimpleNamespace(
        generations=[],
        llm_output={
            "model_name": model_name,
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        },
    )


def _make_gemini_response(
    *,
    model_name: str = "gemini-2.5-flash",
    prompt_tokens: int = 300,
    completion_tokens: int = 120,
) -> Any:
    """Shape 1 variant: Gemini via langchain-google-genai also surfaces
    usage_metadata on the AIMessage but uses ``prompt_token_count`` /
    ``candidates_token_count`` aliases in some versions. Collector handles
    both via the alias fallback at cost_tracking.py:151-160."""
    message = SimpleNamespace(
        usage_metadata={
            "prompt_token_count": prompt_tokens,
            "candidates_token_count": completion_tokens,
        },
        response_metadata={"model_name": model_name},
    )
    generation = SimpleNamespace(message=message, generation_info=None)
    return SimpleNamespace(
        generations=[[generation]],
        llm_output={"model_name": model_name},
    )


# ---------------------------------------------------------------------------
# Pricing table
# ---------------------------------------------------------------------------


class TestResolvePricing:
    def test_exact_match_returns_row(self) -> None:
        assert _resolve_pricing("gpt-5.4-mini") == MODEL_PRICING["gpt-5.4-mini"]

    def test_substring_fallback_picks_longest(self) -> None:
        # gpt-5.4-mini is a substring of "gpt-5.4-mini-2026-01" — collector must
        # prefer the longer key match over generic "gpt-5.4".
        result = _resolve_pricing("gpt-5.4-mini-2026-01")
        assert result == MODEL_PRICING["gpt-5.4-mini"]

    def test_unknown_returns_none(self) -> None:
        assert _resolve_pricing("does-not-exist") is None

    def test_empty_returns_none(self) -> None:
        assert _resolve_pricing("") is None
        assert _resolve_pricing(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Collector: accumulates across calls + computes cost correctly
# ---------------------------------------------------------------------------


class TestTokenUsageCollector:
    def test_modern_chat_shape_accumulates(self) -> None:
        collector = TokenUsageCollector()
        collector.on_llm_end(_make_modern_chat_response())
        totals = collector.totals()
        assert totals == {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }

    def test_legacy_openai_shape_accumulates(self) -> None:
        collector = TokenUsageCollector()
        collector.on_llm_end(_make_legacy_openai_response())
        totals = collector.totals()
        assert totals == {
            "prompt_tokens": 200,
            "completion_tokens": 80,
            "total_tokens": 280,
        }

    def test_gemini_alias_keys_accumulate(self) -> None:
        collector = TokenUsageCollector()
        collector.on_llm_end(_make_gemini_response())
        totals = collector.totals()
        assert totals == {
            "prompt_tokens": 300,
            "completion_tokens": 120,
            "total_tokens": 420,
        }

    def test_per_model_breakdown(self) -> None:
        """When a turn spans multiple models we accumulate per-model so the
        cost calc applies the right pricing row."""
        collector = TokenUsageCollector()
        collector.on_llm_end(
            _make_modern_chat_response(
                model_name="gpt-5.4-nano", prompt_tokens=10, completion_tokens=5
            )
        )
        collector.on_llm_end(
            _make_modern_chat_response(
                model_name="gpt-5.4", prompt_tokens=100, completion_tokens=50
            )
        )
        # Per-model bucket
        assert "gpt-5.4-nano" in collector.usage_by_model
        assert "gpt-5.4" in collector.usage_by_model
        assert collector.usage_by_model["gpt-5.4-nano"]["total_tokens"] == 15
        assert collector.usage_by_model["gpt-5.4"]["total_tokens"] == 150

    def test_cost_calculation(self) -> None:
        """1000 input + 1000 output tokens on gpt-5.4-mini should equal
        (1000/1M * 0.25) + (1000/1M * 2.00) = 0.000250 + 0.002000 = 0.002250."""
        collector = TokenUsageCollector()
        collector.on_llm_end(
            _make_modern_chat_response(
                model_name="gpt-5.4-mini",
                prompt_tokens=1000,
                completion_tokens=1000,
            )
        )
        assert collector.cost_usd() == pytest.approx(0.00225)

    def test_unknown_model_contributes_zero_cost(self) -> None:
        """Unrecognized models contribute tokens to totals but zero cost — we
        never want to invent a number for an un-priced provider."""
        collector = TokenUsageCollector()
        collector.on_llm_end(
            _make_modern_chat_response(
                model_name="unknown-model",
                prompt_tokens=1000,
                completion_tokens=1000,
            )
        )
        assert collector.totals()["total_tokens"] == 2000
        assert collector.cost_usd() == 0.0

    def test_no_usage_data_is_silent(self) -> None:
        """If the LLMResult has no usage metadata at all, the collector must
        not raise and totals must remain zero."""
        empty_response = SimpleNamespace(
            generations=[],
            llm_output={"model_name": "gpt-5.4"},
        )
        collector = TokenUsageCollector()
        collector.on_llm_end(empty_response)  # must not raise
        assert collector.totals()["total_tokens"] == 0

    def test_malformed_response_is_swallowed(self) -> None:
        """Anything weird (e.g. None response) must be a no-op, not a crash —
        cost tracking must never affect the user-facing response."""
        collector = TokenUsageCollector()
        collector.on_llm_end(None)  # type: ignore[arg-type]
        assert collector.totals()["total_tokens"] == 0


# ---------------------------------------------------------------------------
# traced_observation integration
# ---------------------------------------------------------------------------


class TestTracedObservationCostScores:
    """End-to-end: enter the context, record tokens, exit, verify Langfuse
    received the expected ``tokens_per_turn`` + ``cost_per_turn_usd`` scores.

    We patch the Langfuse package surface that ``tracing.py`` imports inside
    the context manager — the langfuse 3.x ``get_client()`` returns the
    mocked client; ``CallbackHandler`` is a no-op so we don't try to make
    network calls.
    """

    def _build_langfuse_module_mocks(self) -> tuple[MagicMock, MagicMock]:
        """Returns (langfuse_module_mock, langfuse_client_mock)."""
        client = MagicMock()
        client.create_score = MagicMock()

        langfuse_module = MagicMock()
        langfuse_module.get_client.return_value = client
        langfuse_module.Langfuse.create_trace_id.return_value = "trace-fixture-id"
        return langfuse_module, client

    @pytest.fixture
    def langfuse_enabled(self) -> Any:
        """Force settings.LANGFUSE_ENABLED + keys so traced_observation runs."""
        with patch("app.ai.graph.tracing.settings") as fake_settings:
            fake_settings.LANGFUSE_ENABLED = True
            fake_settings.LANGFUSE_SECRET_KEY = "sk-test"
            fake_settings.LANGFUSE_PUBLIC_KEY = "pk-test"
            fake_settings.LANGFUSE_BASE_URL = "https://cloud.langfuse.com"
            yield fake_settings

    def test_scores_submitted_when_tokens_recorded(self, langfuse_enabled: Any) -> None:
        from app.ai.graph import tracing

        langfuse_module, client = self._build_langfuse_module_mocks()

        # langfuse 3.x exposes Langfuse, get_client, langchain.CallbackHandler.
        # Build a fake module tree so the `from langfuse import ...` lines
        # inside traced_observation hit our mocks.
        langfuse_langchain = MagicMock()
        langfuse_langchain.CallbackHandler.return_value = MagicMock()

        with (
            patch.dict(
                "sys.modules",
                {
                    "langfuse": langfuse_module,
                    "langfuse.langchain": langfuse_langchain,
                },
            ),
            tracing.traced_observation(
                message_id="msg_test_001",
                session_id="chat-1",
                user_id="user-1",
            ) as (lf_client, callbacks, _meta),
        ):
            # callbacks should now contain both the langfuse handler and
            # our TokenUsageCollector.
            collector = next(
                (c for c in callbacks if isinstance(c, TokenUsageCollector)),
                None,
            )
            assert collector is not None, "TokenUsageCollector not in callbacks list"
            assert lf_client is client

            # Simulate one LLM call inside the context
            collector.on_llm_end(
                _make_modern_chat_response(
                    model_name="gpt-5.4-mini",
                    prompt_tokens=1000,
                    completion_tokens=1000,
                )
            )

        # Exit triggers the finally block — verify both scores went out.
        called = [c.kwargs for c in client.create_score.call_args_list]
        score_names = [k.get("name") for k in called]
        assert "tokens_per_turn" in score_names
        assert "cost_per_turn_usd" in score_names

        tokens_call = next(k for k in called if k["name"] == "tokens_per_turn")
        cost_call = next(k for k in called if k["name"] == "cost_per_turn_usd")

        assert tokens_call["value"] == 2000.0
        assert cost_call["value"] == pytest.approx(0.00225)
        assert tokens_call["trace_id"] == "trace-fixture-id"
        assert tokens_call["data_type"] == "NUMERIC"

    def test_no_scores_when_zero_tokens(self, langfuse_enabled: Any) -> None:
        from app.ai.graph import tracing

        langfuse_module, client = self._build_langfuse_module_mocks()
        langfuse_langchain = MagicMock()
        langfuse_langchain.CallbackHandler.return_value = MagicMock()

        with (
            patch.dict(
                "sys.modules",
                {
                    "langfuse": langfuse_module,
                    "langfuse.langchain": langfuse_langchain,
                },
            ),
            tracing.traced_observation(message_id="msg_test_002") as (
                _lf,
                _callbacks,
                _meta,
            ),
        ):
            pass  # no LLM calls

        # No scores should be created when the turn recorded zero tokens
        # (e.g. an early-routing short-circuit). We don't want noisy zeros
        # cluttering the dashboard.
        assert client.create_score.call_count == 0

    def test_score_submission_failure_is_swallowed(self, langfuse_enabled: Any) -> None:
        """If Langfuse client raises on create_score, the chat turn must
        still succeed — cost tracking is best-effort."""
        from app.ai.graph import tracing

        langfuse_module, client = self._build_langfuse_module_mocks()
        client.create_score.side_effect = RuntimeError("Langfuse outage")
        langfuse_langchain = MagicMock()
        langfuse_langchain.CallbackHandler.return_value = MagicMock()

        with (
            patch.dict(
                "sys.modules",
                {
                    "langfuse": langfuse_module,
                    "langfuse.langchain": langfuse_langchain,
                },
            ),
            tracing.traced_observation(message_id="msg_test_003") as (
                _lf,
                callbacks,
                _meta,
            ),
        ):
            collector = next(c for c in callbacks if isinstance(c, TokenUsageCollector))
            collector.on_llm_end(
                _make_modern_chat_response(prompt_tokens=10, completion_tokens=10)
            )
        # If we reach this line, the failure was swallowed correctly. Also
        # assert ``create_score`` was actually invoked — otherwise this test
        # would still pass if the failing path silently stopped being
        # exercised (e.g. token totals dropped to zero, scores skipped).
        assert client.create_score.call_count >= 1
