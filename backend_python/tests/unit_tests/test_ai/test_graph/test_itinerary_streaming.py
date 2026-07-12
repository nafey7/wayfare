"""Tests for partial-JSON streaming inside ``_generate_itinerary_with_llm``.

Piece 3 of issue #1117 — the itinerary tool now uses
``llm.with_structured_output(StructuredItineraryResult).astream(...)`` so
incremental partials (day-title-only, day-with-some-activities, fully-
populated) are surfaced to the SSE chat endpoint as ``itinerary_partial``
custom events. The non-streaming caller path (V1 ``planning_agent.py``,
``graph.ainvoke``) is unchanged — the function still returns the same
fully-populated :class:`StructuredItineraryResult`.

These tests cover:

- Streaming context (writer available): each partial → custom event
  with ``type=itinerary_partial`` and a dict ``data`` payload.
- Pydantic and dict partials both work: the writer always sees dicts so
  the FE doesn't have to deserialize provider-specific shapes.
- Non-streaming context (writer is ``None``): astream still runs and the
  function returns the final result; no events are emitted.
- ``astream`` failure → fall back to ``ainvoke`` so the FE still gets
  the final itinerary even when streaming itself breaks.
- Writer exception is swallowed (best-effort emission) — itinerary
  generation completes successfully.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.graph.tools.itinerary import (
    BudgetSnapshot,
    DayTip,
    ExpandedContent,
    ItineraryActivity,
    ItineraryDay,
    LocalExperience,
    StructuredItineraryResult,
    _generate_itinerary_with_llm,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _full_itinerary() -> StructuredItineraryResult:
    """Build a minimal but valid StructuredItineraryResult for the success case."""
    activity = ItineraryActivity(
        location="Trastevere",
        description="🌆 Wander cobblestone alleys with gelato in hand.",
        duration="2h",
    )
    expanded = ExpandedContent(
        activities=[activity],
        tip=DayTip(text="Order coffee al banco for the local rate."),
    )
    return StructuredItineraryResult(
        itineraryItems=[
            ItineraryDay(
                day=1,
                title="Arrival & Trastevere",
                description="Land in Rome and wander the prettiest neighborhood.",
                expandedContent=expanded,
            ),
        ],
        budgetSnapshot=BudgetSnapshot(
            description="Expect around $1,500-2,000 USD per person.",
        ),
        localExperiences=[
            LocalExperience(
                id="1",
                title="Espresso al banco",
                description="Stand at the bar; locals never sit down for coffee.",
            ),
        ],
    )


def _astream_yielding(*values: Any) -> Any:
    """Build a chain mock whose ``.astream({})`` yields ``values`` in order.

    The chain's ``.ainvoke({})`` returns the last value — that's the
    fallback path the production code uses when astream fails or yields
    something un-validatable.
    """

    async def _gen(_inp: Any) -> AsyncIterator[Any]:
        for v in values:
            yield v

    chain = MagicMock()
    chain.astream = _gen
    chain.ainvoke = AsyncMock(return_value=values[-1] if values else None)
    return chain


@pytest.fixture
def patched_chain(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Replace ``_build_itinerary_chain`` so each test can hand back its
    own chain instance with custom ``.astream`` / ``.ainvoke`` behavior.

    Stubs out ``_get_itinerary_llm`` so the LLM client isn't actually
    constructed during the test (Gemini SDK init would fail without
    credentials in unit-test environment).

    Forces ``TWO_STAGE_ITINERARY_ENABLED=False`` so the test exercises
    the legacy single-call path that these Phase 3 tests cover — Phase 4
    added a flag-branch at the top of ``_generate_itinerary_with_llm``
    that diverts to ``_generate_itinerary_two_stage`` when the env var
    is on, which has its own dedicated tests in
    ``test_itinerary_two_stage.py``.
    """
    holder: dict[str, Any] = {"chain": None}

    def _build(_llm: Any, _formatted: str) -> Any:
        return holder["chain"]

    from app.ai.graph.tools import itinerary as itin_module

    monkeypatch.setattr(itin_module.settings, "TWO_STAGE_ITINERARY_ENABLED", False)
    monkeypatch.setattr(
        "app.ai.graph.tools.itinerary._get_itinerary_llm", lambda: MagicMock()
    )
    monkeypatch.setattr("app.ai.graph.tools.itinerary._build_itinerary_chain", _build)
    return holder


# ---------------------------------------------------------------------------
# Streaming context — writer captures each partial
# ---------------------------------------------------------------------------


class TestStreamingWritesPartialsToWriter:
    @pytest.mark.asyncio
    async def test_pydantic_partials_become_itinerary_partial_events(
        self, patched_chain: dict[str, Any]
    ) -> None:
        """When the structured-output parser yields Pydantic instances
        (some Gemini paths), each is converted to a dict and forwarded as
        an ``itinerary_partial`` custom event."""
        final = _full_itinerary()
        # Two yields: a fully-populated-but-Pydantic partial (the only
        # form Gemini's structured output emits today), then again as the
        # final iteration.
        patched_chain["chain"] = _astream_yielding(final, final)

        captured: list[dict[str, Any]] = []

        def writer(payload: dict[str, Any]) -> None:
            captured.append(payload)

        with patch(
            "app.ai.graph.tools.itinerary._safe_get_stream_writer",
            return_value=writer,
        ):
            result = await _generate_itinerary_with_llm(
                destination="Rome",
                origin="JFK",
                departure_date="2026-06-01",
                return_date="2026-06-05",
                num_days=5,
                adults=2,
                children=0,
                infants=0,
                interests=["food"],
            )

        assert isinstance(result, StructuredItineraryResult)
        assert result.itinerary_items[0].title == "Arrival & Trastevere"

        # One event per yield, all tagged itinerary_partial.
        assert len(captured) == 2
        for payload in captured:
            assert payload["type"] == "itinerary_partial"
            # The data is a dict (Pydantic was serialized) — the FE never
            # sees a provider-specific Pydantic shape.
            assert isinstance(payload["data"], dict)
            assert "itineraryItems" in payload["data"]

    @pytest.mark.asyncio
    async def test_dict_partials_pass_through_verbatim(
        self, patched_chain: dict[str, Any]
    ) -> None:
        """When the parser yields plain dicts (OpenAI structured outputs
        with JsonOutputParser), the dict is forwarded as-is so the FE
        can render skeleton days the moment titles arrive."""
        skeleton = {"itineraryItems": [{"day": 1, "title": "Arrival"}]}
        with_activities = {
            "itineraryItems": [
                {
                    "day": 1,
                    "title": "Arrival",
                    "expanded_content": {"activities": [{"location": "Hotel"}]},
                }
            ]
        }
        # The final yield needs to validate into a StructuredItineraryResult
        # (or be a Pydantic instance) — without a validating final the
        # function falls back to ainvoke. Yield dicts then a final
        # Pydantic instance so the function returns it directly.
        full = _full_itinerary()
        patched_chain["chain"] = _astream_yielding(skeleton, with_activities, full)

        captured: list[dict[str, Any]] = []

        def writer(payload: dict[str, Any]) -> None:
            captured.append(payload)

        with patch(
            "app.ai.graph.tools.itinerary._safe_get_stream_writer",
            return_value=writer,
        ):
            result = await _generate_itinerary_with_llm(
                destination="Rome",
                origin=None,
                departure_date=None,
                return_date=None,
                num_days=5,
                adults=1,
                children=0,
                infants=0,
                interests=[],
            )

        assert isinstance(result, StructuredItineraryResult)
        # Three writes: skeleton, with-activities, and the final
        # serialized Pydantic.
        assert len(captured) == 3
        assert captured[0]["data"] == skeleton
        assert captured[1]["data"] == with_activities
        # Final is the serialized Pydantic dict.
        assert "itineraryItems" in captured[2]["data"]


# ---------------------------------------------------------------------------
# Non-streaming context — writer is None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_writer_means_no_events_but_final_returned(
    patched_chain: dict[str, Any],
) -> None:
    """When called from outside a streaming graph (V1 planning_agent,
    non-streaming invoke_supervisor_v2, unit tests), no writer is
    available. The function still runs astream and returns the final."""
    final = _full_itinerary()
    patched_chain["chain"] = _astream_yielding(final)

    with patch(
        "app.ai.graph.tools.itinerary._safe_get_stream_writer",
        return_value=None,
    ):
        result = await _generate_itinerary_with_llm(
            destination="Rome",
            origin="JFK",
            departure_date="2026-06-01",
            return_date="2026-06-05",
            num_days=5,
            adults=2,
            children=0,
            infants=0,
            interests=[],
        )

    assert isinstance(result, StructuredItineraryResult)
    assert result.itinerary_items[0].title == "Arrival & Trastevere"


# ---------------------------------------------------------------------------
# astream failure → fall back to ainvoke
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_astream_failure_falls_back_to_ainvoke(
    patched_chain: dict[str, Any],
) -> None:
    """If ``chain.astream`` blows up (provider doesn't support streaming
    on this combo, parser bug, network blip), the function falls back to
    ``chain.ainvoke`` so the FE still gets a complete itinerary."""
    final = _full_itinerary()

    async def _bad_stream(_inp: Any) -> AsyncIterator[Any]:
        raise RuntimeError("provider streaming unavailable")
        yield  # unreachable, but makes the function an async generator

    chain = MagicMock()
    chain.astream = _bad_stream
    chain.ainvoke = AsyncMock(return_value=final)
    patched_chain["chain"] = chain

    with patch(
        "app.ai.graph.tools.itinerary._safe_get_stream_writer",
        return_value=None,
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

    assert isinstance(result, StructuredItineraryResult)
    chain.ainvoke.assert_awaited_once()


# ---------------------------------------------------------------------------
# Writer exception is swallowed — itinerary still ships
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_writer_exception_does_not_break_itinerary(
    patched_chain: dict[str, Any],
) -> None:
    """A failing writer (graph stream torn down mid-flight, queue full)
    must NOT break itinerary generation. The function logs and continues
    — the final return value is unchanged."""
    final = _full_itinerary()
    patched_chain["chain"] = _astream_yielding(final, final)

    def writer(_payload: dict[str, Any]) -> None:
        raise RuntimeError("queue full")

    with patch(
        "app.ai.graph.tools.itinerary._safe_get_stream_writer",
        return_value=writer,
    ):
        result = await _generate_itinerary_with_llm(
            destination="Rome",
            origin="JFK",
            departure_date="2026-06-01",
            return_date="2026-06-05",
            num_days=5,
            adults=2,
            children=0,
            infants=0,
            interests=[],
        )

    assert isinstance(result, StructuredItineraryResult)
    assert result.itinerary_items[0].title == "Arrival & Trastevere"


# ---------------------------------------------------------------------------
# _safe_get_stream_writer behavior
# ---------------------------------------------------------------------------


class TestSafeGetStreamWriter:
    def test_returns_none_when_outside_graph_context(self) -> None:
        """RuntimeError from ``langgraph.config.get_stream_writer`` (the
        canonical "called outside a graph node" failure mode) is mapped
        to None so callers can no-op cleanly."""
        from app.ai.graph.tools.itinerary import _safe_get_stream_writer

        # Outside any langgraph node — get_stream_writer should raise
        # RuntimeError under the hood and our wrapper should return None.
        assert _safe_get_stream_writer() is None

    def test_returns_writer_when_get_stream_writer_succeeds(self) -> None:
        """When ``langgraph.config.get_stream_writer`` returns a callable
        (we're inside a node executing under ``astream``), the helper
        returns that callable verbatim."""
        from app.ai.graph.tools import itinerary as itin_module

        sentinel: Any = lambda payload: None  # noqa: E731 — test-only stub

        fake_module = MagicMock()
        fake_module.get_stream_writer = MagicMock(return_value=sentinel)

        with patch.dict("sys.modules", {"langgraph.config": fake_module}):
            assert itin_module._safe_get_stream_writer() is sentinel
