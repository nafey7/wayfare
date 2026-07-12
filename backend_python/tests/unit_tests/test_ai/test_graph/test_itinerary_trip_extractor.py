"""Unit tests for the cold-turn trip-parameter extractor (#1038).

The extractor combines:
- One small LLM call producing a ``TripParamsExtraction`` pydantic object
- ``parse_dates`` (existing tool) on the natural-language date expression
- ``resolve_airport`` (existing tool) on origin + destination city names

We mock all three so the tests exercise the orchestration logic and the
graceful-degradation paths only — no real LLM / FlightLogic calls.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.graph.itinerary_trip_extractor import (
    TripParamsExtraction,
    extract_and_resolve,
)


def _full_extraction() -> TripParamsExtraction:
    """The 'ideal' extractor output for a complete user message."""
    return TripParamsExtraction(
        origin_city="London",
        destination_city="Paris",
        date_expression="June 20 to 25",
        adults=2,
        children=0,
        infants=0,
        trip_type="round-trip",
    )


def _airport_resolved(iata: str, country: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"status": "resolved", "iata": iata}
    if country is not None:
        out["country"] = country
    return out


def _dates_resolved(
    departure: str | None = "2026-06-20",
    return_date: str | None = "2026-06-25",
) -> dict[str, Any]:
    return {
        "departure_date": departure,
        "return_date": return_date,
        "is_range": True,
        "error": None,
    }


def _patch_extraction(extracted: TripParamsExtraction) -> Any:
    """Patch the LLM extraction with a fixed pydantic result."""
    return patch(
        "app.ai.graph.itinerary_trip_extractor._extract_with_llm",
        new=AsyncMock(return_value=extracted),
    )


def _patch_resolve_airport(side_effect: Any) -> Any:
    """Patch the airport-resolver tool used by the extractor."""
    tool_mock = MagicMock()
    tool_mock.ainvoke = AsyncMock(side_effect=side_effect)
    return patch(
        "app.ai.graph.tools.airport.resolve_airport",
        new=tool_mock,
    )


def _patch_parse_dates(return_value: Any) -> Any:
    tool_mock = MagicMock()
    tool_mock.ainvoke = AsyncMock(return_value=return_value)
    return patch(
        "app.ai.graph.tools.dates.parse_dates",
        new=tool_mock,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestExtractAndResolveHappyPath:
    @pytest.mark.asyncio
    async def test_full_round_trip_populates_all_fields(self) -> None:
        airport_results = [
            _airport_resolved("LHR", country="GB"),  # origin
            _airport_resolved("CDG", country="FR"),  # destination
        ]
        with (
            _patch_extraction(_full_extraction()),
            _patch_resolve_airport(airport_results),
            _patch_parse_dates(_dates_resolved()),
        ):
            result = await extract_and_resolve(
                "Plan a trip from London to Paris June 20-25 for 2 adults"
            )

        # IATA codes resolved
        assert result["origin"] == "London"
        assert result["origin_iata"] == "LHR"
        assert result["destination"] == "Paris"
        assert result["destination_iata"] == "CDG"
        assert result["destination_country"] == "FR"
        # Dates parsed
        assert result["departure_date"] == "2026-06-20"
        assert result["return_date"] == "2026-06-25"
        # Passengers
        assert result["adults"] == 2
        assert result["children"] == 0
        assert result["infants"] == 0
        # Trip type
        assert result["trip_type"] == "round-trip"

    @pytest.mark.asyncio
    async def test_one_way_omits_return_date(self) -> None:
        """parse_dates can return None for return_date on a one-way mention."""
        extraction = TripParamsExtraction(
            origin_city="London",
            destination_city="Paris",
            date_expression="next Friday",
            adults=1,
            trip_type="one-way",
        )
        with (
            _patch_extraction(extraction),
            _patch_resolve_airport(
                [_airport_resolved("LHR"), _airport_resolved("CDG", country="FR")]
            ),
            _patch_parse_dates(_dates_resolved(return_date=None)),
        ):
            result = await extract_and_resolve("London to Paris next Friday, one-way")

        assert result["departure_date"] == "2026-06-20"
        assert "return_date" not in result
        assert result["trip_type"] == "one-way"
        assert result["adults"] == 1


# ---------------------------------------------------------------------------
# Partial / ambiguous inputs — fields are OMITTED, not None
# ---------------------------------------------------------------------------


class TestExtractAndResolvePartial:
    @pytest.mark.asyncio
    async def test_missing_origin_omits_iata_but_keeps_destination(self) -> None:
        """User said only destination — origin keys absent, dest keys present."""
        extraction = TripParamsExtraction(
            origin_city=None,
            destination_city="Paris",
            date_expression="June 20",
            adults=2,
        )
        with (
            _patch_extraction(extraction),
            _patch_resolve_airport([_airport_resolved("CDG", country="FR")]),
            _patch_parse_dates(_dates_resolved(return_date=None)),
        ):
            result = await extract_and_resolve("Take me to Paris on June 20, 2 adults")

        assert "origin" not in result
        assert "origin_iata" not in result
        assert result["destination"] == "Paris"
        assert result["destination_iata"] == "CDG"
        assert result["departure_date"] == "2026-06-20"

    @pytest.mark.asyncio
    async def test_ambiguous_city_omits_iata_keeps_name(self) -> None:
        """resolve_airport returning needs_disambiguation → no IATA written.

        The doc says: 'leave the IATA field empty and let the itinerary agent
        do the resolution as it does today.'
        """
        airport_results = [
            {
                "status": "needs_disambiguation",
                "options": [
                    {"display": "London, GB"},
                    {"display": "London, CA"},
                ],
            },  # origin: ambiguous
            _airport_resolved("CDG", country="FR"),  # destination: clean
        ]
        with (
            _patch_extraction(_full_extraction()),
            _patch_resolve_airport(airport_results),
            _patch_parse_dates(_dates_resolved()),
        ):
            result = await extract_and_resolve("London to Paris June 20-25 for 2")

        # Origin city name surfaces but no IATA (orchestrator gates flight
        # search on origin_iata, so it'll skip silently — fine).
        assert result["origin"] == "London"
        assert "origin_iata" not in result
        # Destination resolved cleanly
        assert result["destination_iata"] == "CDG"

    @pytest.mark.asyncio
    async def test_unparseable_date_omits_dates(self) -> None:
        """parse_dates returns an error → no departure/return on the output."""
        extraction = TripParamsExtraction(
            origin_city="London",
            destination_city="Paris",
            date_expression="some time later",
            adults=2,
        )
        with (
            _patch_extraction(extraction),
            _patch_resolve_airport(
                [_airport_resolved("LHR"), _airport_resolved("CDG", country="FR")]
            ),
            _patch_parse_dates(
                {
                    "departure_date": None,
                    "return_date": None,
                    "error": "Could not parse 'some time later'",
                }
            ),
        ):
            result = await extract_and_resolve("London to Paris some time later for 2")

        assert "departure_date" not in result
        assert "return_date" not in result
        # Other fields still surface
        assert result["destination_iata"] == "CDG"
        assert result["adults"] == 2


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


class TestExtractAndResolveGraceful:
    @pytest.mark.asyncio
    async def test_empty_message_returns_empty_dict(self) -> None:
        result = await extract_and_resolve("")
        assert result == {}

    @pytest.mark.asyncio
    async def test_whitespace_message_returns_empty_dict(self) -> None:
        result = await extract_and_resolve("   \n\t  ")
        assert result == {}

    @pytest.mark.asyncio
    async def test_llm_exception_returns_empty_dict(self) -> None:
        """LLM call raising → caller falls back to today's behaviour."""
        with patch(
            "app.ai.graph.itinerary_trip_extractor._extract_with_llm",
            new=AsyncMock(side_effect=RuntimeError("LLM 502")),
        ):
            result = await extract_and_resolve("Plan a trip somewhere")
        assert result == {}

    @pytest.mark.asyncio
    async def test_resolve_airport_exception_omits_iata(self) -> None:
        """Tool exception → keys absent, no crash."""
        tool_mock = MagicMock()
        tool_mock.ainvoke = AsyncMock(side_effect=RuntimeError("airport API down"))
        with (
            _patch_extraction(_full_extraction()),
            patch("app.ai.graph.tools.airport.resolve_airport", new=tool_mock),
            _patch_parse_dates(_dates_resolved()),
        ):
            result = await extract_and_resolve("London to Paris June 20-25 for 2")

        # Names preserved, IATA absent, dates still flow through
        assert result.get("origin") == "London"
        assert "origin_iata" not in result
        assert "destination_iata" not in result
        assert result.get("departure_date") == "2026-06-20"

    @pytest.mark.asyncio
    async def test_parse_dates_exception_omits_dates(self) -> None:
        tool_mock = MagicMock()
        tool_mock.ainvoke = AsyncMock(side_effect=RuntimeError("dates LLM 502"))
        with (
            _patch_extraction(_full_extraction()),
            _patch_resolve_airport(
                [_airport_resolved("LHR"), _airport_resolved("CDG", country="FR")]
            ),
            patch("app.ai.graph.tools.dates.parse_dates", new=tool_mock),
        ):
            result = await extract_and_resolve("London to Paris June 20-25 for 2")

        assert "departure_date" not in result
        # Airport resolution unaffected
        assert result["origin_iata"] == "LHR"
        assert result["destination_iata"] == "CDG"


# ---------------------------------------------------------------------------
# pre_resolve_trip supervisor node (integration with shared_context)
# ---------------------------------------------------------------------------


class TestPreResolveTripNode:
    @pytest.mark.asyncio
    async def test_node_writes_extracted_fields_to_shared_context(self) -> None:
        """The supervisor node merges trip_update into shared_context.trip."""
        from langchain_core.messages import HumanMessage

        from app.ai.graph.supervisor_v2 import pre_resolve_trip

        trip_update = {
            "origin": "London",
            "origin_iata": "LHR",
            "destination": "Paris",
            "destination_iata": "CDG",
            "destination_country": "FR",
            "departure_date": "2026-06-20",
            "return_date": "2026-06-25",
            "adults": 2,
            "trip_type": "round-trip",
        }
        state: dict[str, Any] = {
            "messages": [
                HumanMessage(
                    content="Plan a trip from London to Paris June 20-25 for 2 adults"
                )
            ],
            "shared_context": {},
        }
        with patch(
            "app.ai.graph.itinerary_trip_extractor.extract_and_resolve",
            new=AsyncMock(return_value=trip_update),
        ):
            result = await pre_resolve_trip(state)  # type: ignore[arg-type]

        ctx = result["shared_context"]
        assert ctx["trip"]["origin_iata"] == "LHR"
        assert ctx["trip"]["destination_iata"] == "CDG"
        assert ctx["trip"]["departure_date"] == "2026-06-20"
        assert ctx["trip"]["return_date"] == "2026-06-25"
        assert ctx["trip"]["adults"] == 2

    @pytest.mark.asyncio
    async def test_node_no_message_returns_empty_update(self) -> None:
        from app.ai.graph.supervisor_v2 import pre_resolve_trip

        state: dict[str, Any] = {"messages": [], "shared_context": {}}
        result = await pre_resolve_trip(state)  # type: ignore[arg-type]
        assert result == {}

    @pytest.mark.asyncio
    async def test_node_empty_extraction_returns_empty_update(self) -> None:
        """Extractor returns {} → node leaves shared_context unchanged."""
        from langchain_core.messages import HumanMessage

        from app.ai.graph.supervisor_v2 import pre_resolve_trip

        state: dict[str, Any] = {
            "messages": [HumanMessage(content="hello")],
            "shared_context": {"trip": {"destination": "old"}},
        }
        with patch(
            "app.ai.graph.itinerary_trip_extractor.extract_and_resolve",
            new=AsyncMock(return_value={}),
        ):
            result = await pre_resolve_trip(state)  # type: ignore[arg-type]
        assert result == {}

    @pytest.mark.asyncio
    async def test_node_extractor_exception_returns_empty_update(self) -> None:
        """Extractor raising → graceful pass-through, no state mutation."""
        from langchain_core.messages import HumanMessage

        from app.ai.graph.supervisor_v2 import pre_resolve_trip

        state: dict[str, Any] = {
            "messages": [HumanMessage(content="Plan a trip somewhere")],
            "shared_context": {},
        }
        with patch(
            "app.ai.graph.itinerary_trip_extractor.extract_and_resolve",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            result = await pre_resolve_trip(state)  # type: ignore[arg-type]
        assert result == {}

    @pytest.mark.asyncio
    async def test_node_does_not_overwrite_existing_trip_fields(self) -> None:
        """Defensive: extracted fields fill gaps, existing fields win on overlap.

        Routing only sends us here when trip_ctx is empty, but the merge
        semantics must be safe regardless.
        """
        from langchain_core.messages import HumanMessage

        from app.ai.graph.supervisor_v2 import pre_resolve_trip

        state: dict[str, Any] = {
            "messages": [HumanMessage(content="actually change destination to Rome")],
            "shared_context": {
                "trip": {"destination_iata": "CDG", "adults": 2},
            },
        }
        trip_update = {
            "destination_iata": "FCO",  # would clobber existing "CDG" if overwriting
            "departure_date": "2026-06-20",
        }
        with patch(
            "app.ai.graph.itinerary_trip_extractor.extract_and_resolve",
            new=AsyncMock(return_value=trip_update),
        ):
            result = await pre_resolve_trip(state)  # type: ignore[arg-type]

        ctx = result["shared_context"]
        # Existing destination_iata preserved (CDG, NOT FCO)
        assert ctx["trip"]["destination_iata"] == "CDG"
        # New field filled in
        assert ctx["trip"]["departure_date"] == "2026-06-20"
        # Existing passenger count preserved
        assert ctx["trip"]["adults"] == 2


# ---------------------------------------------------------------------------
# _route_to_agent gating
# ---------------------------------------------------------------------------


class TestRouteToAgentItineraryGating:
    def _state(self, agent: str, trip: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx: dict[str, Any] = {}
        if trip is not None:
            ctx["trip"] = trip
        return {"active_agent": agent, "shared_context": ctx}

    def test_itinerary_cold_turn_routes_to_pre_resolve(self) -> None:
        from app.ai.graph.supervisor_v2 import AgentName, _route_to_agent

        state = self._state(AgentName.ITINERARY, trip={})
        assert _route_to_agent(state) == "pre_resolve_trip"  # type: ignore[arg-type]

    def test_itinerary_with_populated_trip_routes_direct(self) -> None:
        from app.ai.graph.supervisor_v2 import AgentName, _route_to_agent

        state = self._state(
            AgentName.ITINERARY,
            trip={
                "destination": "Paris",
                "destination_iata": "CDG",
                "departure_date": "2026-06-20",
            },
        )
        assert _route_to_agent(state) == "dispatch_itinerary"  # type: ignore[arg-type]

    def test_itinerary_with_only_destination_routes_to_pre_resolve(self) -> None:
        """Need destination_iata + departure_date for the side-search orchestrator."""
        from app.ai.graph.supervisor_v2 import AgentName, _route_to_agent

        state = self._state(AgentName.ITINERARY, trip={"destination": "Paris"})
        assert _route_to_agent(state) == "pre_resolve_trip"  # type: ignore[arg-type]

    def test_itinerary_with_destination_but_no_iata_routes_to_pre_resolve(self) -> None:
        """An ambiguous-city turn that wrote only ``destination`` (no IATA) should still
        re-detour through pre_resolve_trip so the IATA gets resolved before
        side-search fires — gating on ``destination_iata`` instead of
        ``destination`` ensures this."""
        from app.ai.graph.supervisor_v2 import AgentName, _route_to_agent

        state = self._state(
            AgentName.ITINERARY,
            trip={"destination": "Paris", "departure_date": "2026-06-20"},
        )
        assert _route_to_agent(state) == "pre_resolve_trip"  # type: ignore[arg-type]

    def test_other_agents_unaffected(self) -> None:
        from app.ai.graph.supervisor_v2 import AgentName, _route_to_agent

        assert _route_to_agent(self._state(AgentName.FLIGHT)) == "dispatch_flight"  # type: ignore[arg-type]
        assert _route_to_agent(self._state(AgentName.HOTEL)) == "dispatch_hotel"  # type: ignore[arg-type]
        assert _route_to_agent(self._state(AgentName.GENERAL)) == "dispatch_general"  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Phase 3 O4 — regex fast-path
# ---------------------------------------------------------------------------


class TestFastPathRegex:
    """Direct unit tests for ``_try_fast_path`` — the regex skips the
    extraction LLM call for ~30% of cold-turn shapes."""

    @pytest.mark.parametrize(
        ("message", "expected_dest", "expected_origin", "expected_days"),
        [
            ("Plan a 5-day trip to Paris", "Paris", None, "5 days"),
            # Surrounding structural words are case-insensitive ("plan a" works
            # in any case) but the destination must be Title-Case — see the
            # negative test_misses_lowercase_destination below.
            ("plan a 5 day trip to Paris", "Paris", None, "5 days"),
            ("5 days in Rome", "Rome", None, "5 days"),
            ("5-day trip to Tokyo", "Tokyo", None, "5 days"),
            (
                "Plan a 7-day trip to Tokyo from London",
                "Tokyo",
                "London",
                "7 days",
            ),
            (
                "I want a 3-day trip to Lisbon",
                "Lisbon",
                None,
                "3 days",
            ),
            (
                "I would like a 4-day trip to Barcelona",
                "Barcelona",
                None,
                "4 days",
            ),
            (
                "Plan a 3-day trip to New York",
                "New York",
                None,
                "3 days",
            ),
            (
                "Plan a 5-day trip to San Francisco from Tokyo",
                "San Francisco",
                "Tokyo",
                "5 days",
            ),
            (
                "Plan a 5-day trip to Paris.",
                "Paris",
                None,
                "5 days",
            ),
        ],
    )
    def test_matches_canonical_shapes(
        self,
        message: str,
        expected_dest: str,
        expected_origin: str | None,
        expected_days: str,
    ) -> None:
        from app.ai.graph.itinerary_trip_extractor import _try_fast_path

        result = _try_fast_path(message)
        assert result is not None, f"Expected fast-path match for: {message!r}"
        assert result.destination_city == expected_dest
        assert result.origin_city == expected_origin
        assert result.date_expression == expected_days
        # Fast-path leaves these null — downstream handlers default them.
        assert result.adults is None
        assert result.children is None
        assert result.trip_type is None

    @pytest.mark.parametrize(
        "message",
        [
            # No duration
            "Plan a trip to Paris",
            # No destination
            "Plan a 5-day trip",
            # Extra date info — must defer to LLM so parse_dates handles "in June"
            "Plan a 5-day trip to Tokyo in June",
            # Vibe phrasing — must defer to LLM (and O11 suggestion flow)
            "Plan a 5-day Mexican beach resort",
            "Plan a 5-day trip to somewhere warm",
            # Multi-city — fast path can't model phases
            "5 days in Paris and 3 days in Rome",
            # Empty / blank
            "",
            "   ",
            # Vague verb without duration
            "Take me to Paris",
            # Lowercase destination — defers to LLM (same as vague phrasing).
            # Acceptable design tradeoff: regex covers the well-formed canonical
            # shape; off-shape inputs (including lowercase typing) go to LLM.
            "plan a 5 day trip to paris",
            # Region — would trigger gate downstream; we still match the shape,
            # but separately verify the gate test catches it.
            # (intentionally NOT in negative list — see test_matches_region_destination)
        ],
    )
    def test_misses_non_canonical_shapes(self, message: str) -> None:
        from app.ai.graph.itinerary_trip_extractor import _try_fast_path

        assert _try_fast_path(message) is None, (
            f"Expected fast-path MISS for: {message!r}"
        )

    def test_matches_region_destination(self) -> None:
        """The fast-path is happy to match region names like 'Europe' — the
        downstream block_region_destination gate (Phase 2 R5/R6 fix) handles
        the refusal. Fast-path's job is just the shape detection."""
        from app.ai.graph.itinerary_trip_extractor import _try_fast_path

        result = _try_fast_path("Plan a 5-day trip to Europe")
        assert result is not None
        assert result.destination_city == "Europe"

    def test_handles_extra_whitespace(self) -> None:
        from app.ai.graph.itinerary_trip_extractor import _try_fast_path

        result = _try_fast_path("  Plan a 5-day trip to Paris  ")
        assert result is not None
        assert result.destination_city == "Paris"

    def test_returns_none_for_invalid_input(self) -> None:
        from app.ai.graph.itinerary_trip_extractor import _try_fast_path

        assert _try_fast_path("") is None
        assert _try_fast_path(None) is None  # type: ignore[arg-type]


class TestExtractAndResolveFastPath:
    """End-to-end: when the fast-path matches, the extraction LLM must NOT
    be called."""

    @pytest.mark.asyncio
    async def test_fast_path_skips_extraction_llm(self) -> None:
        """Canonical 'Plan a N-day trip to X' must not invoke _extract_with_llm."""
        from app.ai.graph.itinerary_trip_extractor import extract_and_resolve

        # Mock _extract_with_llm so we can assert it wasn't called, AND mock
        # the downstream resolvers so the test doesn't hit real APIs.
        with (
            patch(
                "app.ai.graph.itinerary_trip_extractor._extract_with_llm",
                new=AsyncMock(),
            ) as llm_mock,
            patch(
                "app.ai.graph.itinerary_trip_extractor._resolve_airport",
                new=AsyncMock(
                    return_value={"status": "resolved", "iata": "CDG", "country": "FR"}
                ),
            ),
            patch(
                "app.ai.graph.itinerary_trip_extractor._parse_dates",
                new=AsyncMock(
                    return_value={"departure_date": None, "return_date": None}
                ),
            ),
            patch(
                "app.ai.graph.itinerary_trip_extractor._is_origin_country_only",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = await extract_and_resolve("Plan a 5-day trip to Paris")

        # The LLM extraction was NOT called — fast-path covered it.
        assert llm_mock.await_count == 0
        # Destination still ends up in the result via the resolver.
        assert result.get("destination") == "Paris"

    @pytest.mark.asyncio
    async def test_fallback_to_llm_when_fast_path_misses(self) -> None:
        """Off-shape message ('Plan a trip to Paris in June') falls through
        to the extraction LLM."""
        from app.ai.graph.itinerary_trip_extractor import (
            TripParamsExtraction,
            extract_and_resolve,
        )

        mock_extraction = TripParamsExtraction(
            origin_city=None,
            destination_city="Paris",
            date_expression="June",
            adults=None,
            children=None,
            infants=None,
            trip_type=None,
        )
        with (
            patch(
                "app.ai.graph.itinerary_trip_extractor._extract_with_llm",
                new=AsyncMock(return_value=mock_extraction),
            ) as llm_mock,
            patch(
                "app.ai.graph.itinerary_trip_extractor._resolve_airport",
                new=AsyncMock(
                    return_value={"status": "resolved", "iata": "CDG", "country": "FR"}
                ),
            ),
            patch(
                "app.ai.graph.itinerary_trip_extractor._parse_dates",
                new=AsyncMock(
                    return_value={"departure_date": None, "return_date": None}
                ),
            ),
            patch(
                "app.ai.graph.itinerary_trip_extractor._is_origin_country_only",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = await extract_and_resolve("Plan a trip to Paris in June")

        # Fast-path missed → LLM was invoked.
        assert llm_mock.await_count == 1
        assert result.get("destination") == "Paris"


# ---------------------------------------------------------------------------
# #1133 follow-up: duration-extraction fallback
#
# When the extractor LLM splits a combined "<N> day trip starting <anchor>"
# expression and only forwards "<anchor>" to parse_dates, the hotel
# side-search silently skips for lack of return_date. The deterministic
# regex fallback recovers the duration from the user's full message.
# ---------------------------------------------------------------------------


class TestExtractTripDurationDays:
    """Pattern must match clear duration phrases and reject anchor phrases."""

    def test_matches_explicit_duration_phrases(self) -> None:
        from app.ai.graph.itinerary_trip_extractor import _extract_trip_duration_days

        assert _extract_trip_duration_days("Plan a 7 day trip to Tokyo") == 7
        assert _extract_trip_duration_days("5-day Tokyo trip") == 5
        assert _extract_trip_duration_days("stay for 10 days") == 10
        assert _extract_trip_duration_days("2 weeks in Bali") == 14
        assert _extract_trip_duration_days("a week in Tokyo") == 7
        assert _extract_trip_duration_days("one week trip") == 7
        assert _extract_trip_duration_days("trip for three days") == 3
        assert _extract_trip_duration_days("14-day expedition") == 14

    def test_rejects_relative_anchor_phrases(self) -> None:
        """'N days from now' / 'N days ago' are anchors, NOT trip durations."""
        from app.ai.graph.itinerary_trip_extractor import _extract_trip_duration_days

        assert _extract_trip_duration_days("departure 30 days from now") is None
        assert _extract_trip_duration_days("5 days ago I went") is None
        assert _extract_trip_duration_days("2 weeks later we return") is None
        assert _extract_trip_duration_days("3 days before the wedding") is None
        assert _extract_trip_duration_days("a week away") is None

    def test_rejects_pre_position_anchor_phrases(self) -> None:
        """PR #1138 review: 'in 5 days' / 'after 2 weeks' / 'by 3 days' are
        relative anchors (offset from today), NOT a trip-duration spec. The
        post-position lookahead in the regex doesn't catch these — they need
        a pre-position word check too. Regression scenario from the review:
        'Plan a trip to Tokyo, leaving in 5 days' was wrongly producing a
        5-day trip the user never asked for."""
        from app.ai.graph.itinerary_trip_extractor import _extract_trip_duration_days

        assert (
            _extract_trip_duration_days("Plan a trip to Tokyo, leaving in 5 days")
            is None
        )
        assert _extract_trip_duration_days("flying out in 2 weeks") is None
        assert _extract_trip_duration_days("after 5 days I'll be there") is None
        assert _extract_trip_duration_days("by 3 days we should know") is None
        assert _extract_trip_duration_days("around 7 days from today") is None
        assert _extract_trip_duration_days("about 10 days into the trip") is None
        assert _extract_trip_duration_days("within 14 days of booking") is None
        assert _extract_trip_duration_days("since 2 weeks ago") is None

    def test_returns_none_when_no_duration(self) -> None:
        from app.ai.graph.itinerary_trip_extractor import _extract_trip_duration_days

        assert _extract_trip_duration_days("") is None
        assert _extract_trip_duration_days("Plan a trip to Tokyo") is None
        assert _extract_trip_duration_days("flying from London") is None

    def test_caps_at_30_days(self) -> None:
        """``generate_itinerary``'s ``num_days`` field maxes at 30 — durations
        beyond that aren't useful (and signal a regex mis-fire)."""
        from app.ai.graph.itinerary_trip_extractor import _extract_trip_duration_days

        assert _extract_trip_duration_days("60 day journey") is None
        # 30 is OK; 31 isn't.
        assert _extract_trip_duration_days("30 day trip") == 30

    def test_prefers_first_duration_match(self) -> None:
        """When the message has both a duration AND an anchor, the duration
        match (which comes first in canonical prompts) should win."""
        from app.ai.graph.itinerary_trip_extractor import _extract_trip_duration_days

        # "7 day trip starting 30 days from now" — '7 day' matches first; the
        # second '30 days' is rejected by the lookahead anyway.
        assert (
            _extract_trip_duration_days(
                "Plan a 7 day trip to Tokyo, departure 30 days from now"
            )
            == 7
        )


class TestDeriveReturnDate:
    def test_inclusive_day_count(self) -> None:
        from app.ai.graph.itinerary_trip_extractor import _derive_return_date

        # 7 day trip starting Jun 21 → return Jun 27 (7 calendar days inclusive)
        assert _derive_return_date("2026-06-21", 7) == "2026-06-27"
        # 1 day trip = same-day return
        assert _derive_return_date("2026-06-21", 1) == "2026-06-21"

    def test_invalid_input_returns_none(self) -> None:
        from app.ai.graph.itinerary_trip_extractor import _derive_return_date

        assert _derive_return_date("", 7) is None
        assert _derive_return_date("not-a-date", 7) is None
        assert _derive_return_date("2026-06-21", 0) is None
        assert _derive_return_date("2026-06-21", -3) is None


class TestExtractAndResolveDurationFallback:
    """End-to-end: when parse_dates returns only departure_date (LLM split
    the combined expression), the duration fallback must derive return_date
    so the hotel side-search gate is satisfied."""

    @pytest.mark.asyncio
    async def test_fallback_fires_when_parse_dates_drops_duration(self) -> None:
        """Real-world scenario from #1133 followup: extractor only forwarded
        '30 days from now' to parse_dates, return_date came back null. The
        fallback must scan the full message for '7 day' and derive
        return_date = Jun 27."""
        extraction = TripParamsExtraction(
            origin_city="the US",
            destination_city="Tokyo",
            date_expression="30 days from now",  # LLM split the expression
            adults=None,
        )
        # parse_dates returns only departure_date — no duration, no return.
        with (
            _patch_extraction(extraction),
            _patch_resolve_airport([{"status": "resolved", "iata": "HND"}]),
            _patch_parse_dates(
                {
                    "departure_date": "2026-06-21",
                    "return_date": None,
                    "trip_duration_days": None,
                    "error": None,
                }
            ),
            patch(
                "app.ai.graph.itinerary_trip_extractor._is_country_only",
                new=AsyncMock(return_value=True),  # "the US" → country
            ),
            patch(
                "app.ai.graph.itinerary_trip_extractor._is_destination_country_only",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = await extract_and_resolve(
                "Plan a 7 days trip to Tokyo, flying in from the US, "
                "staying in Shibuya hotel, with departure 30 days from now"
            )

        # Fallback recovered duration and derived return_date.
        assert result["departure_date"] == "2026-06-21"
        assert result["return_date"] == "2026-06-27"
        assert result["trip_duration_days"] == 7

    @pytest.mark.asyncio
    async def test_no_fallback_when_parse_dates_already_resolved_dates(
        self,
    ) -> None:
        """Happy path: parse_dates returned both dates → fallback no-op."""
        extraction = TripParamsExtraction(
            origin_city=None,
            destination_city="Paris",
            date_expression="June 20-25",
            adults=None,
        )
        with (
            _patch_extraction(extraction),
            _patch_resolve_airport([{"status": "resolved", "iata": "CDG"}]),
            _patch_parse_dates(
                {
                    "departure_date": "2026-06-20",
                    "return_date": "2026-06-25",
                    "trip_duration_days": 6,
                    "error": None,
                }
            ),
            patch(
                "app.ai.graph.itinerary_trip_extractor._is_destination_country_only",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = await extract_and_resolve("Paris June 20-25")

        # parse_dates already gave us both dates; fallback didn't override.
        assert result["departure_date"] == "2026-06-20"
        assert result["return_date"] == "2026-06-25"
        assert result["trip_duration_days"] == 6

    @pytest.mark.asyncio
    async def test_no_fallback_when_no_duration_in_message(self) -> None:
        """When the user really didn't state a duration, fallback stays
        silent (return_date remains absent)."""
        extraction = TripParamsExtraction(
            origin_city=None,
            destination_city="Tokyo",
            date_expression="June 21",
            adults=None,
        )
        with (
            _patch_extraction(extraction),
            _patch_resolve_airport([{"status": "resolved", "iata": "HND"}]),
            _patch_parse_dates(
                {
                    "departure_date": "2026-06-21",
                    "return_date": None,
                    "trip_duration_days": None,
                    "error": None,
                }
            ),
            patch(
                "app.ai.graph.itinerary_trip_extractor._is_destination_country_only",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = await extract_and_resolve("Take me to Tokyo on June 21")

        assert result["departure_date"] == "2026-06-21"
        assert "return_date" not in result
        assert "trip_duration_days" not in result
