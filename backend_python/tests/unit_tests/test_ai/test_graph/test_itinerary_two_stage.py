"""Tests for two-stage itinerary generation — issue #1053 Phase 4 O1.

Covers the Skeleton-of-Thought split that ``_generate_itinerary_two_stage``
implements: stage-1 produces a skeleton (titles + descriptions + budget +
experiences); stage-2 fans out N parallel per-day calls bounded by a
semaphore; final merge composes them into the same
:class:`StructuredItineraryResult` shape the single-call path returns.

Mocks both ``_build_skeleton_chain`` and ``_build_day_fill_chain`` so the
tests run without a real LLM, then verify:

- Happy path: skeleton + per-day fills merge cleanly
- Concurrency cap honored (no more than N simultaneous stage-2 calls)
- Per-day retry kicks in once on transient failure
- Per-day permanent failure → placeholder substituted (partial render)
- Stage-1 astream failure → falls back to ainvoke
- Flag off → single-call path (no stage-2 invocations)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.graph.tools.itinerary import (
    BudgetSnapshot,
    DayActivitiesFill,
    DayChunkFill,
    DayChunkFillItem,
    DayTip,
    ExpandedContent,
    ItineraryActivity,
    ItineraryDaySkeleton,
    LocalExperience,
    StructuredItineraryResult,
    StructuredItinerarySkeleton,
    _chunk_skeleton_days,
    _format_chunk_context_bridge,
    _generate_itinerary_with_llm,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _skel_day(day: int, title: str = "Stub day") -> ItineraryDaySkeleton:
    return ItineraryDaySkeleton(
        day=day,
        title=f"{title} {day}",
        description=f"Day {day} description",
    )


def _skeleton(num_days: int) -> StructuredItinerarySkeleton:
    return StructuredItinerarySkeleton(
        itineraryItems=[_skel_day(i + 1) for i in range(num_days)],
        budgetSnapshot=BudgetSnapshot(
            description="Expect around $1,500 USD per person.",
        ),
        localExperiences=[
            LocalExperience(
                id="1",
                title="Local market",
                description="Eat where locals eat.",
            ),
        ],
    )


def _fill(day_number: int) -> DayActivitiesFill:
    return DayActivitiesFill(
        expandedContent=ExpandedContent(
            activities=[
                ItineraryActivity(
                    location=f"Spot {day_number}",
                    description=f"Activity on day {day_number}",
                    duration="2h",
                )
            ],
            tip=DayTip(text=f"Tip for day {day_number}"),
        )
    )


def _astream_yielding(*values: Any) -> Any:
    """Build a chain whose ``.astream({})`` yields ``values`` then closes,
    and whose ``.ainvoke({})`` returns the last value.
    """

    async def _gen(_input: Any) -> AsyncIterator[Any]:
        for v in values:
            yield v

    chain = MagicMock()
    chain.astream = _gen
    chain.ainvoke = AsyncMock(return_value=values[-1] if values else None)
    return chain


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def patched_chains(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patch skeleton + chunk-fill builders for two-stage tests.

    ``holder["skeleton_chain"]`` — stage-1 chain.
    ``holder["day_fill_chain"]`` — factory(prompt, call_idx) → chain
    returning DayActivitiesFill for ONE day. The fixture wraps this
    into a chunk-fill chain automatically (for a trip with N ≤ 7 days
    each chunk has 1 day, so the old per-day factory still works).
    ``holder["day_calls"]`` — prompts seen by the chunk-fill builder.
    """
    import re

    holder: dict[str, Any] = {
        "skeleton_chain": None,
        "day_fill_chain": None,
        "day_calls": [],
    }

    def _stub_skeleton(_llm: Any, _formatted: str) -> Any:
        return holder["skeleton_chain"]

    def _stub_chunk_fill(_llm: Any, formatted: str) -> Any:
        holder["day_calls"].append(formatted)
        factory = holder["day_fill_chain"]
        # Extract day numbers from the chunk_days_spec section.
        day_nums = [int(m) for m in re.findall(r"• Day (\d+)", formatted)]

        if callable(factory):
            # Build per-day chains and wrap their results into DayChunkFill.
            per_day_chains = {
                d: factory(formatted, len(holder["day_calls"])) for d in day_nums
            }

            async def _ainvoke(_: Any) -> DayChunkFill:
                items = []
                for d in day_nums:
                    raw: DayActivitiesFill = await per_day_chains[d].ainvoke({})
                    items.append(
                        DayChunkFillItem(
                            day=d,
                            expandedContent=raw.expanded_content,
                        )
                    )
                return DayChunkFill(days=items)

            chain = MagicMock()
            chain.ainvoke = _ainvoke
            return chain

        # factory is a static chain — wrap its ainvoke result.
        static_chain = factory

        async def _static_ainvoke(_: Any) -> DayChunkFill:
            raw: DayActivitiesFill = await static_chain.ainvoke({})
            items = [
                DayChunkFillItem(day=d, expandedContent=raw.expanded_content)
                for d in day_nums
            ]
            return DayChunkFill(days=items)

        chain = MagicMock()
        chain.ainvoke = _static_ainvoke
        return chain

    monkeypatch.setattr(
        "app.ai.graph.tools.itinerary._get_itinerary_llm", lambda: MagicMock()
    )
    monkeypatch.setattr(
        "app.ai.graph.tools.itinerary._build_skeleton_chain", _stub_skeleton
    )
    monkeypatch.setattr(
        "app.ai.graph.tools.itinerary._build_chunk_fill_chain", _stub_chunk_fill
    )
    monkeypatch.setattr(
        "app.ai.graph.tools.itinerary.get_itinerary_chunk_fill_prompt",
        lambda *_a, **_kw: (
            "PROMPT {origin} {destination} {departure_date} {return_date} "
            "{num_days} {adults} {children} {infants} {interests} "
            "{user_preferences} {chunk_size} {context_bridge} "
            "{skeleton_summary} {chunk_days_spec}"
        ),
    )
    return holder


@pytest.fixture
def two_stage_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force ``TWO_STAGE_ITINERARY_ENABLED=True`` for the test."""
    from app.ai.graph.tools import itinerary as itin_module

    monkeypatch.setattr(itin_module.settings, "TWO_STAGE_ITINERARY_ENABLED", True)


# ---------------------------------------------------------------------------
# Flag-off short-circuit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flag_off_calls_single_call_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``TWO_STAGE_ITINERARY_ENABLED=False`` (env-override / rollback),
    the function must NOT invoke the two-stage helper — the single-call
    path stays in place as the rollback escape hatch."""
    from app.ai.graph.tools import itinerary as itin_module

    monkeypatch.setattr(itin_module.settings, "TWO_STAGE_ITINERARY_ENABLED", False)

    two_stage_called = MagicMock()
    monkeypatch.setattr(itin_module, "_generate_itinerary_two_stage", two_stage_called)

    # Stub the single-call path so we don't hit the real LLM.
    chain = _astream_yielding(
        StructuredItineraryResult(
            itineraryItems=[],
            budgetSnapshot=BudgetSnapshot(description="—"),
            localExperiences=[],
        )
    )
    monkeypatch.setattr(itin_module, "_get_itinerary_llm", lambda: MagicMock())
    monkeypatch.setattr(itin_module, "_build_itinerary_chain", lambda *_a: chain)
    monkeypatch.setattr(itin_module, "_safe_get_stream_writer", lambda: None)

    result = await _generate_itinerary_with_llm(
        destination="Rome",
        origin=None,
        departure_date=None,
        return_date=None,
        num_days=3,
        adults=1,
        children=0,
        infants=0,
        interests=[],
    )

    assert isinstance(result, StructuredItineraryResult)
    two_stage_called.assert_not_called()


# ---------------------------------------------------------------------------
# Two-stage happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skeleton_plus_per_day_fills_merge_into_full_itinerary(
    patched_chains: dict[str, Any],
    two_stage_on: None,
) -> None:
    skeleton = _skeleton(num_days=3)
    patched_chains["skeleton_chain"] = _astream_yielding(skeleton)

    # Per-day fills succeed on first try. The chunk fixture wraps each
    # per-day DayActivitiesFill into DayChunkFill automatically.
    # For a 3-day trip (< cap of 7) each chunk has 1 day, so the day
    # number comes from the first "• Day N" in the prompt.
    import re

    def _make_fill_chain(prompt: str, _call_idx: int) -> Any:
        day_nums = [int(m) for m in re.findall(r"• Day (\d+)", prompt)]
        day_num = day_nums[0] if day_nums else _call_idx
        chain = MagicMock()
        chain.ainvoke = AsyncMock(return_value=_fill(day_num))
        return chain

    patched_chains["day_fill_chain"] = _make_fill_chain

    with patch(
        "app.ai.graph.tools.itinerary._safe_get_stream_writer",
        return_value=None,
    ):
        result = await _generate_itinerary_with_llm(
            destination="Rome",
            origin="JFK",
            departure_date="2026-06-01",
            return_date="2026-06-03",
            num_days=3,
            adults=2,
            children=0,
            infants=0,
            interests=["food"],
        )

    assert isinstance(result, StructuredItineraryResult)
    assert len(result.itinerary_items) == 3
    # Each day got the right title (from skeleton) AND the right
    # activities (from per-day fill — stub used the day number).
    for idx, day in enumerate(result.itinerary_items, start=1):
        assert day.day == idx
        assert f"Stub day {idx}" in day.title
        assert (
            day.expanded_content.activities[0].description == f"Activity on day {idx}"
        )
    # Stage 2 fired exactly once per day, in order.
    assert len(patched_chains["day_calls"]) == 3


# ---------------------------------------------------------------------------
# Concurrency cap honored
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrency_cap_bounds_simultaneous_stage_two_calls(
    patched_chains: dict[str, Any],
    two_stage_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """At cap=3 with 7 days, no more than 3 stage-2 calls should be
    in-flight at any moment. Verifies the semaphore is actually wired."""
    from app.ai.graph.tools import itinerary as itin_module

    monkeypatch.setattr(itin_module.settings, "TWO_STAGE_PARALLEL_LIMIT", 3)

    skeleton = _skeleton(num_days=7)
    patched_chains["skeleton_chain"] = _astream_yielding(skeleton)

    active = 0
    peak = 0
    lock = asyncio.Lock()

    import re

    def _make_slow_chain(prompt: str, _call_idx: int) -> Any:
        day_nums = [int(m) for m in re.findall(r"• Day (\d+)", prompt)]
        day_num = day_nums[0] if day_nums else _call_idx

        async def _slow_invoke(_input: Any) -> DayActivitiesFill:
            nonlocal active, peak
            async with lock:
                active += 1
                peak = max(peak, active)
            try:
                await asyncio.sleep(0.01)
                return _fill(day_num)
            finally:
                async with lock:
                    active -= 1

        chain = MagicMock()
        chain.ainvoke = AsyncMock(side_effect=_slow_invoke)
        return chain

    patched_chains["day_fill_chain"] = _make_slow_chain

    with patch(
        "app.ai.graph.tools.itinerary._safe_get_stream_writer",
        return_value=None,
    ):
        result = await _generate_itinerary_with_llm(
            destination="Rome",
            origin=None,
            departure_date=None,
            return_date=None,
            num_days=7,
            adults=1,
            children=0,
            infants=0,
            interests=[],
        )

    assert len(result.itinerary_items) == 7
    assert peak <= 3, f"Peak concurrency {peak} exceeded cap=3"
    # With chunk approach: min(7 days, cap=3) = 3 chunks fired in one batch.
    # All 7 days are covered by those 3 chunks (3, 2, 2 days each).
    assert len(patched_chains["day_calls"]) == 3


# ---------------------------------------------------------------------------
# Per-day failure → retry succeeds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_per_day_retry_recovers_from_transient_failure(
    patched_chains: dict[str, Any],
    two_stage_on: None,
) -> None:
    """Day 2 fails on first attempt, succeeds on retry. The merged
    itinerary should still have all 3 days populated normally."""
    skeleton = _skeleton(num_days=3)
    patched_chains["skeleton_chain"] = _astream_yielding(skeleton)

    day2_attempts = {"count": 0}

    import re

    def _make_chain(prompt: str, _call_idx: int) -> Any:
        day_nums = [int(m) for m in re.findall(r"• Day (\d+)", prompt)]
        day_num = day_nums[0] if day_nums else _call_idx
        chain = MagicMock()

        if day_num == 2:
            rate_limit_cls = type("RateLimitError", (Exception,), {})

            async def _flaky(_input: Any) -> DayActivitiesFill:
                day2_attempts["count"] += 1
                if day2_attempts["count"] == 1:
                    raise rate_limit_cls("simulated transient day-2 failure")
                return _fill(2)

            chain.ainvoke = AsyncMock(side_effect=_flaky)
        else:
            chain.ainvoke = AsyncMock(return_value=_fill(day_num))
        return chain

    patched_chains["day_fill_chain"] = _make_chain

    with (
        patch(
            "app.ai.graph.tools.itinerary._safe_get_stream_writer",
            return_value=None,
        ),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):  # zero-out retry backoff
        result = await _generate_itinerary_with_llm(
            destination="Rome",
            origin=None,
            departure_date=None,
            return_date=None,
            num_days=3,
            adults=1,
            children=0,
            infants=0,
            interests=[],
        )

    assert len(result.itinerary_items) == 3
    assert day2_attempts["count"] == 2  # first failed, retry succeeded
    # Day 2 got real activities (from the retry), not a placeholder.
    day2 = result.itinerary_items[1]
    assert day2.expanded_content.activities[0].description == "Activity on day 2"


# ---------------------------------------------------------------------------
# Per-day permanent failure → placeholder substituted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_per_day_permanent_failure_substitutes_placeholder(
    patched_chains: dict[str, Any],
    two_stage_on: None,
) -> None:
    """Day 2 fails with a non-retryable error. Merge step substitutes a
    placeholder so the FE still renders a complete N-day layout instead
    of failing the whole turn.

    A plain ``RuntimeError`` classifies as ``unknown`` (non-retryable)
    in ``app.ai.errors.classify_exception``, so the retry policy doesn't
    fire and the loop breaks after attempt 1 — same end state as "both
    attempts failed", just reached faster.
    """
    skeleton = _skeleton(num_days=3)
    patched_chains["skeleton_chain"] = _astream_yielding(skeleton)

    import re

    def _make_chain(prompt: str, _call_idx: int) -> Any:
        day_nums = [int(m) for m in re.findall(r"• Day (\d+)", prompt)]
        day_num = day_nums[0] if day_nums else _call_idx
        chain = MagicMock()
        if day_num == 2:
            chain.ainvoke = AsyncMock(
                side_effect=RuntimeError("simulated persistent day-2 failure")
            )
        else:
            chain.ainvoke = AsyncMock(return_value=_fill(day_num))
        return chain

    patched_chains["day_fill_chain"] = _make_chain

    with (
        patch(
            "app.ai.graph.tools.itinerary._safe_get_stream_writer",
            return_value=None,
        ),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await _generate_itinerary_with_llm(
            destination="Rome",
            origin=None,
            departure_date=None,
            return_date=None,
            num_days=3,
            adults=1,
            children=0,
            infants=0,
            interests=[],
        )

    # Days 1 + 3 have real activities; day 2 has the placeholder copy.
    assert len(result.itinerary_items) == 3
    day1, day2, day3 = result.itinerary_items
    assert day1.expanded_content.activities[0].description == "Activity on day 1"
    assert day3.expanded_content.activities[0].description == "Activity on day 3"
    # Placeholder copy comes from _placeholder_expanded_content.
    assert "regenerate day 2" in day2.expanded_content.activities[0].description.lower()


# ---------------------------------------------------------------------------
# Stage-1 astream failure → falls back to ainvoke
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skeleton_astream_failure_falls_back_to_ainvoke(
    patched_chains: dict[str, Any],
    two_stage_on: None,
) -> None:
    skeleton = _skeleton(num_days=2)

    async def _bad_astream(_input: Any) -> AsyncIterator[Any]:
        raise RuntimeError("provider streaming unavailable on stage 1")
        yield  # unreachable, makes this an async generator

    skeleton_chain = MagicMock()
    skeleton_chain.astream = _bad_astream
    skeleton_chain.ainvoke = AsyncMock(return_value=skeleton)
    patched_chains["skeleton_chain"] = skeleton_chain

    def _make_chain(prompt: str, _call_idx: int) -> Any:
        day_num = next(
            int(line.split(":")[1].split("of")[0].strip())
            for line in prompt.splitlines()
            if line.strip().startswith("- Day number:")
        )
        chain = MagicMock()
        chain.ainvoke = AsyncMock(return_value=_fill(day_num))
        return chain

    patched_chains["day_fill_chain"] = _make_chain

    with patch(
        "app.ai.graph.tools.itinerary._safe_get_stream_writer",
        return_value=None,
    ):
        result = await _generate_itinerary_with_llm(
            destination="Rome",
            origin=None,
            departure_date=None,
            return_date=None,
            num_days=2,
            adults=1,
            children=0,
            infants=0,
            interests=[],
        )

    # ainvoke fallback succeeded; itinerary composed normally.
    assert len(result.itinerary_items) == 2
    skeleton_chain.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_skeleton_both_astream_and_ainvoke_fail_propagates(
    patched_chains: dict[str, Any],
    two_stage_on: None,
) -> None:
    """Review concern (#1126): when stage-1 ``astream`` fails AND the
    ``ainvoke`` fallback also fails, the error must propagate out so
    the caller's catch path returns a classified error response.
    Otherwise the user sees no acknowledgement of the failure and the
    backend silently double-bills.

    This complements ``test_skeleton_astream_failure_falls_back_to_ainvoke``
    which exercises the happy fallback path; this one asserts the shape
    callers see when BOTH paths fail.
    """

    async def _bad_astream(_input: Any) -> AsyncIterator[Any]:
        raise RuntimeError("provider streaming unavailable on stage 1")
        yield  # unreachable

    skeleton_chain = MagicMock()
    skeleton_chain.astream = _bad_astream
    skeleton_chain.ainvoke = AsyncMock(
        side_effect=RuntimeError(
            "ainvoke fallback also failed — quota exhausted / total provider outage"
        )
    )
    patched_chains["skeleton_chain"] = skeleton_chain

    # Stage-2 chain won't even be reached, but stub it so the fixture
    # doesn't blow up looking for one.
    patched_chains["day_fill_chain"] = lambda _prompt, _idx: MagicMock()

    # Caller (``generate_itinerary`` tool) wraps this in its own
    # try/except and turns it into an agent-visible error result.
    # Here we assert the inner contract: the function raises rather
    # than silently substituting a placeholder for the whole turn.
    with (
        patch(
            "app.ai.graph.tools.itinerary._safe_get_stream_writer",
            return_value=None,
        ),
        pytest.raises(RuntimeError, match="ainvoke fallback also failed"),
    ):
        await _generate_itinerary_with_llm(
            destination="Rome",
            origin=None,
            departure_date=None,
            return_date=None,
            num_days=2,
            adults=1,
            children=0,
            infants=0,
            interests=[],
        )

    # Both attempts on stage-1 were exercised; stage-2 never reached
    # (no day-fill prompts recorded).
    skeleton_chain.ainvoke.assert_awaited_once()
    assert len(patched_chains["day_calls"]) == 0


# ---------------------------------------------------------------------------
# Chunk helpers — unit tests (#1140)
# ---------------------------------------------------------------------------


class TestChunkSkeletonDays:
    """``_chunk_skeleton_days`` must always produce ≤ n_chunks groups of
    consecutive days, distributed as evenly as possible. For a 30-day
    trip with cap=7 this produces 7 chunks (~4-5 days each) so Stage 2
    finishes in ONE parallel batch instead of 5 sequential ones."""

    def _days(self, n: int) -> list[ItineraryDaySkeleton]:
        return [_skel_day(i + 1) for i in range(n)]

    def test_30_days_cap_7_gives_7_chunks(self) -> None:
        chunks = _chunk_skeleton_days(self._days(30), 7)
        assert len(chunks) == 7
        # All 30 days present, consecutive, no gaps
        all_days = [d.day for chunk in chunks for d in chunk]
        assert all_days == list(range(1, 31))

    def test_30_days_distributed_evenly(self) -> None:
        """30 ÷ 7: first 2 chunks get 5 days, remaining 5 get 4."""
        chunks = _chunk_skeleton_days(self._days(30), 7)
        sizes = [len(c) for c in chunks]
        assert sizes == [5, 5, 4, 4, 4, 4, 4]

    def test_7_days_cap_7_gives_7_chunks_of_1(self) -> None:
        """Short trip: chunk size = 1 (same as previous per-day behaviour)."""
        chunks = _chunk_skeleton_days(self._days(7), 7)
        assert len(chunks) == 7
        assert all(len(c) == 1 for c in chunks)

    def test_5_days_cap_7_capped_at_5(self) -> None:
        """Trip shorter than cap → at most len(items) chunks."""
        chunks = _chunk_skeleton_days(self._days(5), 7)
        assert len(chunks) == 5

    def test_14_days_cap_7_gives_7_chunks_of_2(self) -> None:
        chunks = _chunk_skeleton_days(self._days(14), 7)
        assert len(chunks) == 7
        assert all(len(c) == 2 for c in chunks)

    def test_empty_input_returns_empty(self) -> None:
        assert _chunk_skeleton_days([], 7) == []

    def test_all_days_covered_no_duplicates(self) -> None:
        """Invariant: union of all chunks == original items, no repeats."""
        days = self._days(21)
        chunks = _chunk_skeleton_days(days, 7)
        flat = [d.day for chunk in chunks for d in chunk]
        assert sorted(flat) == list(range(1, 22))
        assert len(flat) == len(set(flat))


class TestFormatChunkContextBridge:
    """Context bridge carries previous-chunk day titles into the next
    chunk's prompt so adjacent-chunk seams stay coherent."""

    def test_empty_prev_chunk_returns_empty_string(self) -> None:
        assert _format_chunk_context_bridge([]) == ""

    def test_single_day_prev_chunk(self) -> None:
        prev = [_skel_day(1, "Arrival")]
        result = _format_chunk_context_bridge(prev)
        assert "Day 1" in result
        assert "Arrival" in result

    def test_multi_day_prev_chunk_uses_range(self) -> None:
        prev = [_skel_day(1, "Arrival"), _skel_day(2, "Temples"), _skel_day(3, "Food")]
        result = _format_chunk_context_bridge(prev)
        assert "Days 1" in result
        assert "Days 1-3" in result
        assert "Temples" in result


# ---------------------------------------------------------------------------
# Chunk-based Stage 2 integration — #1140
# ---------------------------------------------------------------------------


def _chunk_fill(chunk: list[ItineraryDaySkeleton]) -> DayChunkFill:
    """Build a ``DayChunkFill`` returning one activity per day in the chunk."""
    items = []
    for d in chunk:
        items.append(
            DayChunkFillItem(
                day=d.day,
                expandedContent=ExpandedContent(
                    activities=[
                        ItineraryActivity(
                            location=f"Spot {d.day}",
                            description=f"Activity on day {d.day}",
                            duration="2h",
                        )
                    ],
                    tip=DayTip(text=f"Tip for day {d.day}"),
                ),
            )
        )
    return DayChunkFill(days=items)


@pytest.fixture
def patched_chunk_chains(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patch the chunk-fill builder so tests can assert call counts and
    control per-chunk responses without a real LLM."""
    holder: dict[str, Any] = {
        "skeleton_chain": None,
        "chunk_fill_factory": None,
        "chunk_calls": [],
    }

    def _stub_skeleton(_llm: Any, _fmt: str) -> Any:
        return holder["skeleton_chain"]

    def _stub_chunk_fill(_llm: Any, formatted: str) -> Any:
        holder["chunk_calls"].append(formatted)
        factory = holder["chunk_fill_factory"]
        if callable(factory):
            return factory(formatted, len(holder["chunk_calls"]))
        return factory

    monkeypatch.setattr(
        "app.ai.graph.tools.itinerary._get_itinerary_llm", lambda: MagicMock()
    )
    monkeypatch.setattr(
        "app.ai.graph.tools.itinerary._build_skeleton_chain", _stub_skeleton
    )
    monkeypatch.setattr(
        "app.ai.graph.tools.itinerary._build_chunk_fill_chain", _stub_chunk_fill
    )
    # Patch the module-level reference in itinerary.py so tests don't
    # need real Langfuse credentials.
    monkeypatch.setattr(
        "app.ai.graph.tools.itinerary.get_itinerary_chunk_fill_prompt",
        lambda *_a, **_kw: (
            "PROMPT {origin} {destination} {departure_date} {return_date} "
            "{num_days} {adults} {children} {infants} {interests} "
            "{user_preferences} {chunk_size} {context_bridge} "
            "{skeleton_summary} {chunk_days_spec}"
        ),
    )
    return holder


@pytest.mark.asyncio
async def test_30_day_trip_fires_exactly_cap_chunk_calls(
    patched_chunk_chains: dict[str, Any],
    two_stage_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """30-day trip with cap=10 must produce exactly 10 chunk calls in ONE
    asyncio.gather — not 30 per-day calls and not 5 sequential batches.
    Cap is pinned via monkeypatch so the test doesn't drift if the
    default changes again."""
    from app.ai.graph.tools import itinerary as itin_module

    monkeypatch.setattr(itin_module.settings, "TWO_STAGE_PARALLEL_LIMIT", 10)

    skeleton = _skeleton(num_days=30)
    patched_chunk_chains["skeleton_chain"] = _astream_yielding(skeleton)

    # Each chunk-fill chain returns correct activities for all days in it.
    def _make_chunk_chain(formatted: str, call_idx: int) -> Any:
        # Which days are in this chunk? Extract from the formatted prompt.
        # The context bridge and skeleton_summary are stub strings, so
        # we identify days from the chunk_days_spec injected by
        # _format_chunk_days_spec: "• Day N [POSITION] — title: desc".
        import re

        day_nums = [int(m) for m in re.findall(r"• Day (\d+)", formatted)]
        chunk_days = [_skel_day(d) for d in day_nums]
        fill = _chunk_fill(chunk_days)

        chain = MagicMock()
        chain.ainvoke = AsyncMock(return_value=fill)
        return chain

    patched_chunk_chains["chunk_fill_factory"] = _make_chunk_chain

    with patch(
        "app.ai.graph.tools.itinerary._safe_get_stream_writer",
        return_value=None,
    ):
        result = await _generate_itinerary_with_llm(
            destination="London",
            origin="Paris",
            departure_date="2026-06-01",
            return_date="2026-06-30",
            num_days=30,
            adults=2,
            children=0,
            infants=0,
            interests=["culture"],
        )

    # Exactly 7 chunk calls — ONE parallel batch, not 30 per-day calls.
    assert len(patched_chunk_chains["chunk_calls"]) == 10, (
        f"Expected 10 chunk calls for 30 days (cap=10), "
        f"got {len(patched_chunk_chains['chunk_calls'])}"
    )
    assert isinstance(result, StructuredItineraryResult)
    assert len(result.itinerary_items) == 30


@pytest.mark.asyncio
async def test_7_day_trip_fires_7_single_day_chunks(
    patched_chunk_chains: dict[str, Any],
    two_stage_on: None,
) -> None:
    """7-day trip: 7 chunks of 1 day each — same call count as old
    per-day approach, but now goes through the chunk path."""

    skeleton = _skeleton(num_days=7)
    patched_chunk_chains["skeleton_chain"] = _astream_yielding(skeleton)

    def _make_chain(formatted: str, _idx: int) -> Any:
        import re

        day_nums = [int(m) for m in re.findall(r"• Day (\d+)", formatted)]
        fill = _chunk_fill([_skel_day(d) for d in day_nums])
        chain = MagicMock()
        chain.ainvoke = AsyncMock(return_value=fill)
        return chain

    patched_chunk_chains["chunk_fill_factory"] = _make_chain

    with patch(
        "app.ai.graph.tools.itinerary._safe_get_stream_writer", return_value=None
    ):
        result = await _generate_itinerary_with_llm(
            destination="Tokyo",
            origin="LAX",
            departure_date="2026-06-01",
            return_date="2026-06-07",
            num_days=7,
            adults=1,
            children=0,
            infants=0,
            interests=[],
        )

    assert len(patched_chunk_chains["chunk_calls"]) == 7
    assert len(result.itinerary_items) == 7


@pytest.mark.asyncio
async def test_context_bridge_present_in_second_chunk_prompt(
    patched_chunk_chains: dict[str, Any],
    two_stage_on: None,
) -> None:
    """The second chunk's prompt must contain the context bridge summary
    of the first chunk so cross-chunk coherence is maintained."""
    skeleton = _skeleton(num_days=14)
    patched_chunk_chains["skeleton_chain"] = _astream_yielding(skeleton)

    captured_prompts: list[str] = []

    def _make_chain(formatted: str, _idx: int) -> Any:
        captured_prompts.append(formatted)
        import re

        day_nums = [int(m) for m in re.findall(r"• Day (\d+)", formatted)]
        fill = _chunk_fill([_skel_day(d) for d in day_nums])
        chain = MagicMock()
        chain.ainvoke = AsyncMock(return_value=fill)
        return chain

    patched_chunk_chains["chunk_fill_factory"] = _make_chain

    with patch(
        "app.ai.graph.tools.itinerary._safe_get_stream_writer", return_value=None
    ):
        await _generate_itinerary_with_llm(
            destination="Paris",
            origin="London",
            departure_date="2026-06-01",
            return_date="2026-06-14",
            num_days=14,
            adults=2,
            children=0,
            infants=0,
            interests=["food"],
        )

    # First chunk: context bridge must be empty (no previous chunk).
    assert "Thematic context from the preceding chunk" not in captured_prompts[0]
    # Second chunk onward: context bridge must mention the previous chunk's days.
    for prompt in captured_prompts[1:]:
        assert "Thematic context from the preceding chunk" in prompt
