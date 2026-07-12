"""Per-turn token + cost tracking for LangGraph agent invocations.

Issue #1053 P0.4: every supervisor-v2 turn produces multiple LLM calls
(supervisor classify, pre_resolve extraction, parse_dates, agent ReAct loop,
generate_itinerary, etc.). Today the per-call costs are visible in Langfuse
spans but there's no per-turn aggregate that we can dashboard or alert on.

This module provides a langchain ``BaseCallbackHandler`` that accumulates
prompt + completion tokens per model across an invocation, plus a helper
that converts that into USD using a static pricing table.

Integration: ``app/ai/graph/tracing.py``'s ``traced_observation`` adds this
collector to the callbacks list alongside the Langfuse handler. On exit it
computes the totals, logs them, and attaches them as Langfuse trace tags
(``tokens_per_turn:NNN``, ``cost_per_turn_usd:0.0123``).

Pricing is per **1M tokens** and is best-effort — the actual invoice is
authoritative. Keep MODEL_PRICING in sync with OpenAI / xAI / Bedrock /
Google public prices; refresh manually when prices drift.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.outputs import LLMResult
except ImportError:  # pragma: no cover — langchain is always installed in prod
    BaseCallbackHandler = object  # type: ignore[misc,assignment]
    LLMResult = Any  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)


# Pricing in USD per 1,000,000 tokens. Source: published OpenAI / xAI prices
# as of May 2026. Keep model keys lowercase + substring-matched (case-
# insensitive) so model identifier variants (gpt-5.4-mini-2026-01,
# gpt-5.4-mini-preview, etc.) hit the right row.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-5.4-nano": {"input": 0.05, "output": 0.40},
    "gpt-5.4-mini": {"input": 0.25, "output": 2.00},
    "gpt-5.4": {"input": 2.50, "output": 10.00},
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    "grok-4-1-fast-non-reasoning": {"input": 0.20, "output": 1.50},
}


def _resolve_pricing(model_name: str) -> dict[str, float] | None:
    """Best-effort match: try exact key, then substring containment."""
    name = (model_name or "").lower().strip()
    if not name:
        return None
    if name in MODEL_PRICING:
        return MODEL_PRICING[name]
    # Substring fallback — match the longest key that's contained in the
    # model name. Handles "gpt-5.4-mini-2026-01" → "gpt-5.4-mini".
    matches = sorted(
        (k for k in MODEL_PRICING if k in name),
        key=len,
        reverse=True,
    )
    if matches:
        return MODEL_PRICING[matches[0]]
    return None


class TokenUsageCollector(BaseCallbackHandler):
    """Accumulates token usage across an entire LangGraph invocation.

    Subclasses ``langchain_core.callbacks.BaseCallbackHandler`` so it can sit
    alongside Langfuse's handler in the ``callbacks`` list passed to
    ``graph.ainvoke``. Aggregates per-model so we can both report grand totals
    and break costs down by which model handled which slice of the turn.
    """

    def __init__(self) -> None:
        # {model_name: {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}}
        self.usage_by_model: dict[str, dict[str, int]] = {}

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID | None = None,  # noqa: ARG002 — required by BaseCallbackHandler signature
        parent_run_id: UUID | None = None,  # noqa: ARG002
        **kwargs: Any,
    ) -> None:
        """Extract token usage from each LLM completion.

        Different providers/wrappers place usage in slightly different spots:
        - Modern langchain-openai / chat models: AIMessage.usage_metadata
        - Legacy OpenAI: llm_output.token_usage
        - Gemini via langchain-google-genai: generations[i][j].generation_info.usage_metadata
        - Some chat models put it on response.usage directly.
        We probe in that order and bail silently if none fits — cost tracking
        is best-effort and must never affect the user-facing response.
        """
        try:
            llm_output = getattr(response, "llm_output", None) or {}
            model_name = (
                llm_output.get("model_name")
                or llm_output.get("model")
                or kwargs.get("invocation_params", {}).get("model")
                or "unknown"
            )

            # Shape 1 — modern langchain-openai / chat models: usage is on
            # ``generations[0][0].message.usage_metadata`` as an AIMessage attr.
            # This is the dominant path in 2025+ langchain-core.
            token_usage: dict[str, Any] | None = None
            generations = getattr(response, "generations", None) or []
            if generations and generations[0]:
                first_gen = generations[0][0]
                msg = getattr(first_gen, "message", None)
                if msg is not None:
                    msg_usage = getattr(msg, "usage_metadata", None)
                    if isinstance(msg_usage, dict):
                        token_usage = msg_usage
                    # Some chat models also expose response_metadata.model_name
                    response_metadata = getattr(msg, "response_metadata", None) or {}
                    candidate_model = response_metadata.get(
                        "model_name"
                    ) or response_metadata.get("model")
                    if candidate_model:
                        model_name = candidate_model

                # Fallback within the same generation
                if not token_usage:
                    info = getattr(first_gen, "generation_info", None) or {}
                    token_usage = info.get("usage_metadata") or info.get("token_usage")

            # Shape 2 — legacy OpenAI: llm_output.token_usage
            if not token_usage and isinstance(llm_output, dict):
                token_usage = llm_output.get("token_usage")

            # Shape 3 — directly on response.usage
            if not token_usage:
                token_usage = getattr(response, "usage", None)

            if not token_usage or not isinstance(token_usage, dict):
                return

            prompt = int(
                token_usage.get("prompt_tokens")
                or token_usage.get("input_tokens")
                or token_usage.get("prompt_token_count")
                or 0
            )
            completion = int(
                token_usage.get("completion_tokens")
                or token_usage.get("output_tokens")
                or token_usage.get("candidates_token_count")
                or 0
            )
            total = int(token_usage.get("total_tokens") or (prompt + completion))

            bucket = self.usage_by_model.setdefault(
                model_name,
                {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )
            bucket["prompt_tokens"] += prompt
            bucket["completion_tokens"] += completion
            bucket["total_tokens"] += total

        except Exception:
            # Cost tracking is best-effort and must never break the turn.
            logger.debug("TokenUsageCollector.on_llm_end failed", exc_info=True)

    def totals(self) -> dict[str, int]:
        """Sum across all models — for the headline ``tokens_per_turn`` tag."""
        out = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for bucket in self.usage_by_model.values():
            out["prompt_tokens"] += bucket["prompt_tokens"]
            out["completion_tokens"] += bucket["completion_tokens"]
            out["total_tokens"] += bucket["total_tokens"]
        return out

    def cost_usd(self) -> float:
        """Sum USD cost across all models using ``MODEL_PRICING``."""
        cost = 0.0
        for model_name, bucket in self.usage_by_model.items():
            pricing = _resolve_pricing(model_name)
            if not pricing:
                continue
            cost += (bucket["prompt_tokens"] / 1_000_000.0) * pricing["input"]
            cost += (bucket["completion_tokens"] / 1_000_000.0) * pricing["output"]
        return round(cost, 6)


__all__ = ["MODEL_PRICING", "TokenUsageCollector"]
