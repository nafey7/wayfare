"""Tests for ``hand_back_to_supervisor`` — #1133 follow-up.

The itinerary agent (and any other sub-agent) must NOT call hand-back as a
substitute for asking the user about missing fields. The tool rejects
hand-back reasons that look like *"missing origin"* / *"need a specific
city"* / *"clarification needed"* so the agent receives an error and is
forced to ask the user directly.
"""

from __future__ import annotations

import pytest

from app.ai.graph.tools.handback import (
    _INVALID_HANDBACK_REASON_PATTERN,
    hand_back_to_supervisor,
)


class TestInvalidHandbackReasonPattern:
    """The pattern must catch missing-field hand-back reasons while leaving
    legitimate out-of-scope reasons alone."""

    def test_matches_missing_field_reasons(self) -> None:
        for reason in [
            "Need a specific US city origin before generating itinerary; current origin is country-level only.",
            "missing origin city",
            "missing destination",
            "missing date",
            "Need a specific city for the origin",
            "Origin is country-level only",
            "Need to ask the user for a specific airport",
            "Ask the user which city of the US",
            "Clarification needed on dates",
            # PR #1138 review: ``which X`` must be paired with an
            # agent-intent verb (``ask``, ``need to know``). Bare phrases
            # like ``which city in the UK?`` (paraphrasing a user
            # question) intentionally PASS THROUGH now — see negative
            # cases below.
            "Need to know which city in the UK",
            "Ask which airport they prefer",
        ]:
            assert _INVALID_HANDBACK_REASON_PATTERN.search(reason), (
                f"should match: {reason!r}"
            )

    def test_does_not_match_legitimate_handback_reasons(self) -> None:
        for reason in [
            "User wants to book flights",
            "User asking about hotels in Tokyo",
            "User asked about visa requirements",
            "User wants travel advice for Japan",
            "planning_complete: book flights and hotels",
            "flight_search: user explicitly asked for cheapest flights",
            "User switched topic to hotel search",
            "Weather question — detour",
            # PR #1138 review: ``which X`` paraphrasing a user's QUESTION
            # (not an agent bail-out) must pass through. These describe what
            # the user asked, not what the agent failed to do.
            "User asking which airport is closer to downtown",
            "User wonders which city has cheaper flights",
            "User wants to know which date is better for sakura season",
        ]:
            assert not _INVALID_HANDBACK_REASON_PATTERN.search(reason), (
                f"should NOT match: {reason!r}"
            )


class TestHandBackToSupervisor:
    @pytest.mark.asyncio
    async def test_rejects_missing_origin_reason(self) -> None:
        """The exact reason observed in real logs must be rejected."""
        result = await hand_back_to_supervisor.ainvoke(
            {
                "reason": (
                    "Need a specific US city origin before generating "
                    "itinerary; current origin is country-level only."
                ),
                "is_detour": False,
            }
        )
        assert result["status"] == "error"
        assert "ask the user" in result["error"].lower()
        # Instruction must direct the agent to ask the user instead of retrying.
        instr = result["instruction"].lower()
        assert "asking" in instr or "ask the user" in instr
        assert "do not call hand_back_to_supervisor again" in instr

    @pytest.mark.asyncio
    async def test_accepts_legitimate_handback(self) -> None:
        """User wanting to book flights is a real hand-back — must pass through."""
        result = await hand_back_to_supervisor.ainvoke(
            {
                "reason": "User wants to book flights",
                "is_detour": False,
            }
        )
        assert result["status"] == "hand_back"
        assert result["reason"] == "User wants to book flights"
        assert result["is_detour"] is False

    @pytest.mark.asyncio
    async def test_accepts_detour_handback(self) -> None:
        """Out-of-scope weather question is a valid detour hand-back."""
        result = await hand_back_to_supervisor.ainvoke(
            {
                "reason": "User asked about visa requirements",
                "is_detour": True,
            }
        )
        assert result["status"] == "hand_back"
        assert result["is_detour"] is True

    @pytest.mark.asyncio
    async def test_rejects_clarification_handback(self) -> None:
        result = await hand_back_to_supervisor.ainvoke(
            {"reason": "Clarification needed on dates", "is_detour": False}
        )
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_rejects_which_city_handback(self) -> None:
        result = await hand_back_to_supervisor.ainvoke(
            {"reason": "Need to know which city in the US", "is_detour": False}
        )
        assert result["status"] == "error"
