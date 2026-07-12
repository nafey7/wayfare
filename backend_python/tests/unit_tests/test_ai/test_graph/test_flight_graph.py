"""Unit tests for LangGraph flight graph functions.

Tests the flight graph helper functions, particularly the logic to extract
flight search results only from the current conversation turn.
"""

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.ai.graph.flight_graph import (
    _build_location,
    _detect_destination_preference,
    _enrich_city_map_from_search_results,
    _extract_airport_resolution_data,
    _extract_flight_search_results,
    _extract_search_params_from_messages,
)
from app.domains.flight.enums import JourneyType
from app.domains.flight.journey_params import normalize_search_redirect_journey_type


def _make_search_flights_tool_message(
    origin: str = "LHR",
    destination: str = "CDG",
    total_flights: int = 10,
) -> ToolMessage:
    """Create a mock search_flights ToolMessage with successful results.

    Issue #1034: the @tool uses ``response_format="content_and_artifact"``,
    so the LLM-visible ``content`` carries only the summary + instruction,
    while the full flight payload (session_id, search_params, flights) lives
    on ``ToolMessage.artifact``. The graph extractor reads ``msg.artifact``,
    so fixtures MUST set both.
    """
    summary = {
        "total_found": total_flights,
        "direct_flights": 5,
        "price_range": {"min": 100, "max": 500, "currency": "USD"},
    }
    flights = [
        {
            "id": "flight1",
            "origin_code": origin,
            "destination_code": destination,
            "price": 100,
            "airline": "Test Air",
            "airline_code": "TA",
        }
    ]
    content = json.dumps(
        {
            "status": "success",
            "summary": summary,
            "instruction": (
                f"Tell the user we found {total_flights} flight options "
                "— they're displayed above the chat."
            ),
        }
    )
    artifact: dict[str, Any] = {
        "session_id": "test_session_123",
        "search_params": {
            "origin": origin,
            "destination": destination,
            "departure_date": "2026-06-01",
            "return_date": None,
            "journey_type": "OneWay",
            "adults": 1,
            "children": 0,
            "infants": 0,
        },
        "summary": summary,
        "origin_is_city": True,
        "destination_is_city": True,
        "flights": flights,
    }
    return ToolMessage(
        content=content,
        name="search_flights",
        tool_call_id="tc1",
        artifact=artifact,
    )


def _make_resolve_airport_tool_message(
    status: str = "resolved",
    iata: str = "LHR",
    city: str = "London",
    lat: float | None = 51.47,
    lon: float | None = -0.46,
    query_is_city_name: bool = True,
    tool_call_id: str = "tc2",
) -> ToolMessage:
    """Create a mock resolve_airport ToolMessage."""
    data: dict[str, Any] = {
        "status": status,
        "iata": iata,
        "name": "London Heathrow",
        "city": city,
        "query_is_city_name": query_is_city_name,
    }
    if lat is not None:
        data["lat"] = lat
    if lon is not None:
        data["lon"] = lon
    content = json.dumps(data)
    return ToolMessage(
        content=content, name="resolve_airport", tool_call_id=tool_call_id
    )


class TestExtractFlightSearchResults:
    """Tests for _extract_flight_search_results function."""

    def test_extracts_results_from_search_flights_message(self) -> None:
        """Test that flight results are extracted from a search_flights ToolMessage."""
        messages = [
            HumanMessage(content="Find flights from London to Paris"),
            AIMessage(content="Searching..."),
            _make_search_flights_tool_message(origin="LHR", destination="CDG"),
            AIMessage(content="Here are your flight options."),
        ]

        result = _extract_flight_search_results(messages)

        assert result is not None
        assert "data" in result
        assert "flights" in result
        assert result["session_id"] == "test_session_123"
        assert len(result["flights"]) == 1
        assert result["flights"][0]["origin_code"] == "LHR"
        assert result["flights"][0]["destination_code"] == "CDG"

    def test_returns_none_when_no_search_flights_message(self) -> None:
        """Test that None is returned when no search_flights ToolMessage exists."""
        messages = [
            HumanMessage(content="Find flights from New York to London"),
            AIMessage(content="Resolving airports..."),
            _make_resolve_airport_tool_message(status="needs_user_choice"),
            AIMessage(content="Which New York airport do you prefer?"),
        ]

        result = _extract_flight_search_results(messages)

        assert result is None

    def test_returns_none_for_empty_messages(self) -> None:
        """Test that None is returned for empty message list."""
        result = _extract_flight_search_results([])
        assert result is None

    def test_returns_none_for_failed_search(self) -> None:
        """Test that None is returned when search_flights returned an error."""
        error_message = ToolMessage(
            content=json.dumps(
                {
                    "status": "error",
                    "error": "No flights found",
                }
            ),
            name="search_flights",
            tool_call_id="tc1",
        )
        messages = [
            HumanMessage(content="Find flights"),
            error_message,
        ]

        result = _extract_flight_search_results(messages)

        assert result is None

    def test_skips_date_range_artifact(self) -> None:
        """Regression for the #1034 status-guard: the date-range artifact
        carries ``status="date_range_results"`` and ``dates`` (no top-level
        ``flights``). Without the guard, this extractor would mis-claim it
        and surface a 0-flight ``flight_search_results`` payload, so the
        dedicated ``_extract_flight_date_range_results`` extractor never
        runs and the user sees "0 flights" instead of the per-date
        breakdown. The guard skips multicity / date-range statuses."""
        date_range_message = ToolMessage(
            content="3 date options found.",
            name="search_flights",
            tool_call_id="tc-dr",
            artifact={
                "status": "date_range_results",
                "dates": [
                    {"date": "2026-06-01", "best_price": 120},
                    {"date": "2026-06-02", "best_price": 135},
                    {"date": "2026-06-03", "best_price": 150},
                ],
                "searched_from": "2026-06-01",
                "searched_to": "2026-06-03",
            },
        )
        messages = [
            HumanMessage(content="Show me cheapest dates this week"),
            date_range_message,
        ]

        result = _extract_flight_search_results(messages)

        assert result is None

    def test_skips_multicity_artifact(self) -> None:
        """Same guard, multicity side: ``status="multicity_results"`` artifacts
        carry per-leg flight lists under ``multicity_legs`` (no top-level
        ``flights``) and must be claimed by
        ``_extract_multicity_flight_search_results`` instead."""
        multicity_message = ToolMessage(
            content="3-leg multicity search complete.",
            name="search_flights",
            tool_call_id="tc-mc",
            artifact={
                "status": "multicity_results",
                "search_params": {},
                "multicity_legs": [],
            },
        )
        messages = [
            HumanMessage(content="Plan a multi-city trip"),
            multicity_message,
        ]

        result = _extract_flight_search_results(messages)

        assert result is None

    def test_returns_most_recent_search_results(self) -> None:
        """Test that the most recent search_flights result is returned."""
        # First search (older)
        old_search = _make_search_flights_tool_message(
            origin="HKT", destination="CNX", total_flights=50
        )
        # Second search (newer)
        new_search = _make_search_flights_tool_message(
            origin="JFK", destination="LHR", total_flights=25
        )

        messages = [
            HumanMessage(content="Find flights from Phuket to Chiang Mai"),
            old_search,
            AIMessage(content="Here are Phuket flights."),
            HumanMessage(content="Find flights from New York to London"),
            new_search,
            AIMessage(content="Here are New York flights."),
        ]

        result = _extract_flight_search_results(messages)

        assert result is not None
        # Should return the MOST RECENT (JFK→LHR), not the old one (HKT→CNX)
        assert result["flights"][0]["origin_code"] == "JFK"
        assert result["flights"][0]["destination_code"] == "LHR"

    def test_prefers_city_names_from_tool_result_over_iata_codes(self) -> None:
        """Regression test for #796: itinerary→flight handoff showed IATA codes.

        When the tool result's search_params contains enriched city names,
        they should override the IATA codes extracted from message params.
        Post #1034: search_params lives on `msg.artifact`.
        """
        summary = {
            "total_found": 1,
            "direct_flights": 1,
            "price_range": {"min": 100, "max": 100, "currency": "USD"},
        }
        tool_content = json.dumps(
            {
                "status": "success",
                "summary": summary,
                "instruction": "Tell the user we found 1 flight option.",
            }
        )
        tool_artifact: dict[str, Any] = {
            "session_id": "s1",
            "search_params": {"origin": "London", "destination": "Cancun"},
            "summary": summary,
            "flights": [
                {
                    "id": "f1",
                    "origin_code": "LHR",
                    "destination_code": "CUN",
                    "price": 100,
                    "airline": "Test Air",
                    "airline_code": "TA",
                }
            ],
        }
        tool_msg = ToolMessage(
            content=tool_content,
            name="search_flights",
            tool_call_id="tc1",
            artifact=tool_artifact,
        )
        messages = [
            HumanMessage(content="I want flights from LHR to CUN"),
            tool_msg,
        ]

        result = _extract_flight_search_results(messages)

        assert result is not None
        sp = result["data"]["search_params"]
        assert sp["origin"] == "London"  # not "LHR"
        assert sp["destination"] == "Cancun"  # not "CUN"


class TestMessageSlicingForCurrentTurn:
    """Tests verifying that only current turn messages are checked for results.

    These tests simulate the scenario where a user has previous search results
    in their conversation history, but the current turn doesn't include a search.
    """

    def test_no_results_when_search_only_in_history(self) -> None:
        """Test that old search results are not returned when current turn has no search.

        This is the key test for issue #238: when a user starts a new search,
        we should not return cached results from previous searches.
        """
        # Simulate history: previous search for Phuket → Chiang Mai
        history_messages = [
            HumanMessage(content="Find flights from Phuket to Chiang Mai"),
            _make_search_flights_tool_message(origin="HKT", destination="CNX"),
            AIMessage(content="Here are your Phuket flights."),
        ]

        # Simulate current turn: new search, but airport disambiguation needed
        current_turn_messages = [
            HumanMessage(content="Find flights from New York to London"),
            _make_resolve_airport_tool_message(status="needs_user_choice", iata=""),
            AIMessage(content="New York has multiple airports. Which do you prefer?"),
        ]

        # If we check ALL messages (the bug), we'd find the old search
        all_messages = history_messages + current_turn_messages
        result_with_bug = _extract_flight_search_results(all_messages)
        assert result_with_bug is not None  # Bug: returns old results
        assert result_with_bug["flights"][0]["origin_code"] == "HKT"

        # If we check only CURRENT TURN messages (the fix), no search found
        result_fixed = _extract_flight_search_results(current_turn_messages)
        assert result_fixed is None  # Correct: no search in current turn

    def test_returns_results_when_search_in_current_turn(self) -> None:
        """Test that results are returned when search is in current turn."""
        # Simulate history: previous search
        history_messages = [
            HumanMessage(content="Find flights from Phuket to Chiang Mai"),
            _make_search_flights_tool_message(origin="HKT", destination="CNX"),
            AIMessage(content="Here are your Phuket flights."),
        ]

        # Simulate current turn: new search completed
        current_turn_messages = [
            HumanMessage(content="Find flights from New York to London for 2 adults"),
            _make_resolve_airport_tool_message(status="resolved", iata="JFK"),
            _make_search_flights_tool_message(origin="JFK", destination="LHR"),
            AIMessage(content="Here are your New York to London flights."),
        ]

        # Check only current turn - should find the new search
        result = _extract_flight_search_results(current_turn_messages)

        assert result is not None
        assert result["flights"][0]["origin_code"] == "JFK"
        assert result["flights"][0]["destination_code"] == "LHR"

    def test_message_count_slicing_simulation(self) -> None:
        """Test that simulates the actual fix using message count slicing.

        This mirrors the logic in invoke_flight_graph:
        1. Count messages before invoke (msg_count_before)
        2. After invoke, slice: new_messages = all_messages[msg_count_before:]
        3. Only check new_messages for flight results
        """
        # History (would be loaded from checkpoint)
        history = [
            HumanMessage(content="Find flights from Phuket to Chiang Mai"),
            _make_search_flights_tool_message(origin="HKT", destination="CNX"),
            AIMessage(content="Here are Phuket flights."),
        ]
        msg_count_before = len(history)  # 3

        # Current turn adds new messages
        current_turn = [
            HumanMessage(content="Find flights from New York to London"),
            _make_resolve_airport_tool_message(status="needs_user_choice"),
            AIMessage(content="Which NY airport?"),
        ]

        # All messages after invoke
        all_messages = history + current_turn

        # Apply the fix: slice to only new messages
        new_messages = all_messages[msg_count_before:]

        # Verify slicing works correctly
        assert len(new_messages) == 3
        assert isinstance(new_messages[0], HumanMessage)
        assert "New York" in new_messages[0].content

        # Check for flight results in sliced messages only
        result = _extract_flight_search_results(new_messages)
        assert result is None  # No search_flights in current turn


class TestEdgeCases:
    """Edge case tests for flight result extraction."""

    def test_handles_malformed_json_gracefully(self) -> None:
        """Test that malformed JSON in ToolMessage is handled gracefully."""
        bad_message = ToolMessage(
            content="not valid json {{{",
            name="search_flights",
            tool_call_id="tc1",
        )
        messages = [bad_message]

        # Should not raise, should return None
        result = _extract_flight_search_results(messages)
        assert result is None

    def test_handles_missing_artifact_gracefully(self) -> None:
        """Issue #1034: artifact is required for success-path extraction.

        A search_flights ToolMessage with content but no artifact (e.g. a
        stale pre-#1034 message format) is skipped — the extractor returns
        None rather than raising. Graceful handling is the test's intent.
        """
        partial_message = ToolMessage(
            content=json.dumps(
                {
                    "status": "success",
                    # Missing summary, instruction, and crucially: no artifact.
                }
            ),
            name="search_flights",
            tool_call_id="tc1",
        )
        messages = [partial_message]

        # Should not raise — returns None because there's no artifact to read.
        result = _extract_flight_search_results(messages)
        assert result is None

    def test_first_turn_no_history(self) -> None:
        """Test first turn behavior when there's no history (msg_count_before=0)."""
        # First turn - no history
        first_turn_messages = [
            HumanMessage(content="Find flights from London to Paris"),
            _make_search_flights_tool_message(origin="LHR", destination="CDG"),
            AIMessage(content="Here are your flights."),
        ]

        # Simulate the fix logic: if msg_count_before is 0, check all messages
        msg_count_before = 0
        all_messages = first_turn_messages
        new_messages = (
            all_messages[msg_count_before:] if msg_count_before > 0 else all_messages
        )

        result = _extract_flight_search_results(new_messages)

        assert result is not None
        assert result["flights"][0]["origin_code"] == "LHR"


# ==============================================================================
# SEARCH PARAMS EXTRACTION WITH FILTERS
# ==============================================================================


def _make_ai_message_with_search_tool_call(**kwargs: Any) -> AIMessage:
    """Create an AIMessage with a search_flights tool call containing given args."""
    default_args = {
        "origin": "LHR",
        "destination": "CDG",
        "departure_date": "2026-04-15",
        "adults": 1,
        "children": 0,
        "infants": 0,
        "origin_is_city": True,
        "destination_is_city": True,
    }
    default_args.update(kwargs)
    return AIMessage(
        content="Searching for flights...",
        tool_calls=[
            {
                "name": "search_flights",
                "args": default_args,
                "id": "tc_search",
            }
        ],
    )


class TestExtractSearchParamsFilters:
    """Tests for filter field extraction in _extract_search_params_from_messages."""

    def test_extracts_max_stops(self) -> None:
        messages = [_make_ai_message_with_search_tool_call(max_stops=1)]
        params = _extract_search_params_from_messages(messages)
        assert params["max_stops"] == 1

    def test_extracts_price_min(self) -> None:
        messages = [_make_ai_message_with_search_tool_call(price_min=100.0)]
        params = _extract_search_params_from_messages(messages)
        assert params["price_min"] == 100.0

    def test_extracts_price_max(self) -> None:
        messages = [_make_ai_message_with_search_tool_call(price_max=500.0)]
        params = _extract_search_params_from_messages(messages)
        assert params["price_max"] == 500.0

    def test_extracts_preferred_airline(self) -> None:
        messages = [_make_ai_message_with_search_tool_call(preferred_airline="BA")]
        params = _extract_search_params_from_messages(messages)
        assert params["preferred_airline"] == "BA"

    def test_extracts_max_outbound_duration(self) -> None:
        messages = [_make_ai_message_with_search_tool_call(max_outbound_duration=3.0)]
        params = _extract_search_params_from_messages(messages)
        assert params["max_outbound_duration"] == 3.0

    def test_extracts_max_inbound_duration(self) -> None:
        messages = [_make_ai_message_with_search_tool_call(max_inbound_duration=4.5)]
        params = _extract_search_params_from_messages(messages)
        assert params["max_inbound_duration"] == 4.5

    def test_extracts_all_filters_together(self) -> None:
        messages = [
            _make_ai_message_with_search_tool_call(
                max_stops=1,
                price_min=100.0,
                price_max=800.0,
                preferred_airline="EK",
                max_outbound_duration=3.0,
                max_inbound_duration=4.0,
            )
        ]
        params = _extract_search_params_from_messages(messages)
        assert params["max_stops"] == 1
        assert params["price_min"] == 100.0
        assert params["price_max"] == 800.0
        assert params["preferred_airline"] == "EK"
        assert params["max_outbound_duration"] == 3.0
        assert params["max_inbound_duration"] == 4.0

    def test_missing_filters_are_none(self) -> None:
        messages = [_make_ai_message_with_search_tool_call()]
        params = _extract_search_params_from_messages(messages)
        assert params["max_stops"] is None
        assert params["price_min"] is None
        assert params["price_max"] is None
        assert params["preferred_airline"] is None
        assert params["max_outbound_duration"] is None
        assert params["max_inbound_duration"] is None

    def test_direct_flight_flag_from_max_stops_zero(self) -> None:
        """max_stops=0 should set direct_flight=1."""
        messages = [_make_ai_message_with_search_tool_call(max_stops=0)]
        params = _extract_search_params_from_messages(messages)
        assert params["direct_flight"] == 1
        assert params["max_stops"] == 0

    def test_cabin_class_extraction(self) -> None:
        messages = [_make_ai_message_with_search_tool_call(cabin_class="business")]
        params = _extract_search_params_from_messages(messages)
        assert params["cabin_class"] == "Business"


class TestSearchRedirectJourneyTypeContract:
    """Graph emits legacy journey_type labels; API search_redirect normalizes the same way."""

    @staticmethod
    def _as_search_redirect_journey_type(params: dict[str, Any]) -> str:
        """Mirrors ``search_redirect`` use of :func:`normalize_search_redirect_journey_type`."""
        return normalize_search_redirect_journey_type(
            params.get("journey_type"),
            has_return_date=bool(params.get("return_date")),
        )

    def test_round_trip_from_tool_call_normalizes_to_return_like_search_redirect(
        self,
    ) -> None:
        """Chat tool still uses journey_type RoundTrip when return_date is set; redirect maps to Return."""
        messages = [
            _make_ai_message_with_search_tool_call(
                return_date="2026-04-22",
            )
        ]
        params = _extract_search_params_from_messages(messages)
        assert params["journey_type"] == "RoundTrip"
        assert params["return_date"] == "2026-04-22"
        assert self._as_search_redirect_journey_type(params) == JourneyType.RETURN.value

    def test_one_way_from_tool_call_normalizes_like_search_redirect(self) -> None:
        messages = [_make_ai_message_with_search_tool_call()]
        params = _extract_search_params_from_messages(messages)
        assert params["journey_type"] == "OneWay"
        assert params.get("return_date") is None
        assert (
            self._as_search_redirect_journey_type(params) == JourneyType.ONE_WAY.value
        )


class TestDetectDestinationPreference:
    """Tests for _detect_destination_preference function.

    These tests cover both true positives (preference correctly detected)
    and the false positive fixes introduced by the word-boundary regex change.
    """

    # --- True positives ---

    def test_detects_warm_preference(self) -> None:
        assert _detect_destination_preference("I want somewhere warm") == "warm"

    def test_detects_hot_as_warm(self) -> None:
        assert _detect_destination_preference("I want hot weather") == "warm"

    def test_detects_tropical_as_warm(self) -> None:
        assert (
            _detect_destination_preference("A tropical getaway sounds perfect")
            == "warm"
        )

    def test_detects_beach_preference(self) -> None:
        assert _detect_destination_preference("I want a beach holiday") == "beach"

    def test_detects_sea_as_beach(self) -> None:
        assert _detect_destination_preference("I want to swim in the sea") == "beach"

    def test_detects_island_as_beach(self) -> None:
        assert _detect_destination_preference("I want an island vacation") == "beach"

    def test_detects_ski_preference(self) -> None:
        assert _detect_destination_preference("I want to go skiing") == "ski"

    def test_detects_mountain_preference(self) -> None:
        assert (
            _detect_destination_preference("mountain hiking sounds great") == "mountain"
        )

    def test_detects_city_break_as_city(self) -> None:
        assert _detect_destination_preference("I want a city break in Europe") == "city"

    def test_detects_cool_as_cold(self) -> None:
        assert _detect_destination_preference("I want somewhere cool") == "cold"

    # --- False positive prevention (word-boundary fix) ---

    def test_hot_does_not_match_hotel(self) -> None:
        """'hot' word boundary must not fire for 'hotel' — very common in travel."""
        assert _detect_destination_preference("find me a hotel in Paris") is None

    def test_sea_does_not_match_season(self) -> None:
        """'sea' must not fire for 'season'."""
        assert _detect_destination_preference("best season to visit Thailand") is None

    def test_sea_does_not_match_search(self) -> None:
        """'sea' must not fire for 'search'."""
        assert (
            _detect_destination_preference("search for cheap flights to Tokyo") is None
        )

    def test_sea_does_not_match_seat(self) -> None:
        """'sea' must not fire for 'seat'."""
        assert _detect_destination_preference("I need a window seat please") is None

    def test_island_does_not_match_iceland(self) -> None:
        """'island' must not fire for 'Iceland'."""
        assert _detect_destination_preference("fly me to Iceland") is None

    def test_cool_does_not_match_school(self) -> None:
        """'cool' must not fire for 'school'."""
        assert _detect_destination_preference("school trip to Berlin") is None

    # --- Generic cases ---

    def test_returns_none_for_specific_city(self) -> None:
        assert _detect_destination_preference("fly me to Paris next week") is None

    def test_returns_none_for_empty_message(self) -> None:
        assert _detect_destination_preference("") is None

    def test_case_insensitive_warm(self) -> None:
        assert _detect_destination_preference("I want WARM weather") == "warm"

    def test_case_insensitive_beach(self) -> None:
        assert _detect_destination_preference("BEACH vacation please") == "beach"


class TestBuildLocation:
    """Tests for _build_location helper."""

    def test_returns_location_with_valid_coords(self) -> None:
        result = _build_location(51.47, -0.46)
        assert result == {"latitude": 51.47, "longitude": -0.46}

    def test_returns_none_when_both_none(self) -> None:
        assert _build_location(None, None) is None

    def test_returns_none_when_lat_none(self) -> None:
        assert _build_location(None, -0.46) is None

    def test_returns_none_when_lon_none(self) -> None:
        assert _build_location(51.47, None) is None

    def test_handles_zero_coords(self) -> None:
        """Zero is a valid coordinate (Gulf of Guinea)."""
        result = _build_location(0.0, 0.0)
        assert result == {"latitude": 0.0, "longitude": 0.0}


class TestExtractAirportResolutionData:
    """Tests for _extract_airport_resolution_data (merged city + coord extraction)."""

    def test_extracts_city_and_coords_from_resolved_airport(self) -> None:
        messages = [
            _make_resolve_airport_tool_message(
                iata="LHR", city="London", lat=51.47, lon=-0.46, query_is_city_name=True
            ),
        ]
        city_map, coord_map = _extract_airport_resolution_data(messages)

        assert city_map == {"LHR": "London"}
        assert coord_map == {"LHR": (51.47, -0.46)}

    def test_skips_city_map_for_iata_query(self) -> None:
        """When user searched by IATA code, don't add to city_map."""
        messages = [
            _make_resolve_airport_tool_message(
                iata="LHR",
                city="London",
                lat=51.47,
                lon=-0.46,
                query_is_city_name=False,
            ),
        ]
        city_map, coord_map = _extract_airport_resolution_data(messages)

        assert city_map == {}  # Not a city query
        assert coord_map == {"LHR": (51.47, -0.46)}  # Coords always extracted

    def test_handles_missing_coordinates(self) -> None:
        messages = [
            _make_resolve_airport_tool_message(
                iata="LHR", city="London", lat=None, lon=None
            ),
        ]
        _city_map, coord_map = _extract_airport_resolution_data(messages)

        assert coord_map == {"LHR": (None, None)}

    def test_handles_multiple_airports(self) -> None:
        messages = [
            _make_resolve_airport_tool_message(
                iata="LHR", city="London", lat=51.47, lon=-0.46, tool_call_id="tc1"
            ),
            _make_resolve_airport_tool_message(
                iata="BCN", city="Barcelona", lat=41.30, lon=2.08, tool_call_id="tc2"
            ),
        ]
        city_map, coord_map = _extract_airport_resolution_data(messages)

        assert city_map == {"LHR": "London", "BCN": "Barcelona"}
        assert coord_map == {"LHR": (51.47, -0.46), "BCN": (41.30, 2.08)}

    def test_skips_non_resolved_statuses(self) -> None:
        messages = [
            _make_resolve_airport_tool_message(
                status="needs_disambiguation", iata="LHR"
            ),
        ]
        city_map, coord_map = _extract_airport_resolution_data(messages)

        assert city_map == {}
        assert coord_map == {}

    def test_handles_malformed_json(self) -> None:
        msg = ToolMessage(
            content="not valid json", name="resolve_airport", tool_call_id="tc1"
        )
        city_map, coord_map = _extract_airport_resolution_data([msg])

        assert city_map == {}
        assert coord_map == {}

    def test_ignores_non_airport_tool_messages(self) -> None:
        msg = ToolMessage(
            content=json.dumps({"status": "resolved", "iata": "LHR"}),
            name="search_flights",
            tool_call_id="tc1",
        )
        city_map, coord_map = _extract_airport_resolution_data([msg])

        assert city_map == {}
        assert coord_map == {}

    def test_no_own_airport_populates_city_map_from_nearby(self) -> None:
        """no_own_airport status pre-populates city_map from nearby_airports list.

        When a city has no own airport, the agent shows nearby alternatives.
        The city_map must be seeded from those alternatives so that when the user
        picks one and search_flights fires, city_map.get(iata) returns the correct
        city name for shared_context population.
        """
        msg = ToolMessage(
            content=json.dumps(
                {
                    "status": "no_own_airport",
                    "query": "Mamburao",
                    "nearby_airports": [
                        {
                            "iata": "MBO",
                            "city": "Mamburao",
                            "name": "Mamburao Airport",
                        },
                        {
                            "iata": "MNL",
                            "city": "Manila",
                            "name": "Ninoy Aquino International",
                        },
                    ],
                }
            ),
            name="resolve_airport",
            tool_call_id="tc_no_own",
        )
        city_map, coord_map = _extract_airport_resolution_data([msg])

        assert city_map == {"MBO": "Mamburao", "MNL": "Manila"}
        # no_own_airport does not carry lat/lon — coord_map stays empty
        assert coord_map == {}

    def test_no_own_airport_skips_entries_missing_iata_or_city(self) -> None:
        """Nearby airports with missing iata or city fields are skipped gracefully."""
        msg = ToolMessage(
            content=json.dumps(
                {
                    "status": "no_own_airport",
                    "query": "SomeCity",
                    "nearby_airports": [
                        {"iata": "ABC", "city": "ValidCity"},  # valid
                        {"iata": None, "city": "NoIata"},  # missing iata → skip
                        {"iata": "DEF", "city": None},  # missing city → skip
                        {"city": "NoIataKey"},  # no iata key at all → skip
                    ],
                }
            ),
            name="resolve_airport",
            tool_call_id="tc_partial",
        )
        city_map, coord_map = _extract_airport_resolution_data([msg])

        assert city_map == {"ABC": "ValidCity"}
        assert coord_map == {}


class TestSearchParamsLocationCoordinates:
    """Tests for origin_location/destination_location in _extract_search_params_from_messages."""

    def _make_full_search_messages(
        self,
        origin_lat: float | None = 51.47,
        origin_lon: float | None = -0.46,
        dest_lat: float | None = 41.30,
        dest_lon: float | None = 2.08,
    ) -> list[Any]:
        """Create a realistic message sequence: resolve origin, resolve dest, search."""
        return [
            HumanMessage(content="Flights from London to Barcelona"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "resolve_airport",
                        "args": {"query": "London"},
                        "id": "tc1",
                    }
                ],
            ),
            _make_resolve_airport_tool_message(
                iata="LHR",
                city="London",
                lat=origin_lat,
                lon=origin_lon,
                tool_call_id="tc1",
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "resolve_airport",
                        "args": {"query": "Barcelona"},
                        "id": "tc2",
                    }
                ],
            ),
            _make_resolve_airport_tool_message(
                iata="BCN",
                city="Barcelona",
                lat=dest_lat,
                lon=dest_lon,
                tool_call_id="tc2",
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_flights",
                        "args": {
                            "origin": "LHR",
                            "destination": "BCN",
                            "departure_date": "2026-04-01",
                            "adults": 1,
                            "origin_is_city": True,
                            "destination_is_city": True,
                        },
                        "id": "tc3",
                    }
                ],
            ),
        ]

    def test_includes_origin_and_destination_location(self) -> None:
        messages = self._make_full_search_messages()
        params = _extract_search_params_from_messages(messages)

        assert params["origin_location"] == {"latitude": 51.47, "longitude": -0.46}
        assert params["destination_location"] == {"latitude": 41.30, "longitude": 2.08}

    def test_location_is_none_when_coords_missing(self) -> None:
        messages = self._make_full_search_messages(
            origin_lat=None, origin_lon=None, dest_lat=None, dest_lon=None
        )
        params = _extract_search_params_from_messages(messages)

        assert params["origin_location"] is None
        assert params["destination_location"] is None

    def test_location_is_none_when_partial_coords(self) -> None:
        """One coord present, other missing — should return None, not partial."""
        messages = self._make_full_search_messages(
            origin_lat=51.47, origin_lon=None, dest_lat=None, dest_lon=2.08
        )
        params = _extract_search_params_from_messages(messages)

        assert params["origin_location"] is None
        assert params["destination_location"] is None

    def test_top_level_location_in_flight_results(self) -> None:
        """Verify _extract_flight_search_results passes location to top level."""
        messages = self._make_full_search_messages()
        # Add the search_flights result ToolMessage
        messages.append(
            _make_search_flights_tool_message(origin="LHR", destination="BCN"),
        )
        messages.append(AIMessage(content="Here are your flights."))

        result = _extract_flight_search_results(messages)

        assert result is not None
        assert result["origin_location"] == {"latitude": 51.47, "longitude": -0.46}
        assert result["destination_location"] == {"latitude": 41.30, "longitude": 2.08}


class TestEnrichCityMapFromSearchResults:
    """Tests for _enrich_city_map_from_search_results.

    Covers the scenario where the LLM skips resolve_airport and uses an IATA
    code directly in search_flights (e.g., user picked from a suggestion list).
    The city name is backfilled from the search_flights result's search_params.
    """

    def test_backfills_city_names_from_search_result(self) -> None:
        """IATA codes not in city_map get backfilled from search_params."""
        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_flights",
                    "args": {"origin": "EWR", "destination": "SJO"},
                    "id": "tc_search",
                }
            ],
        )
        tool_msg = ToolMessage(
            content=json.dumps(
                {
                    "status": "success",
                    "search_params": {
                        "origin": "Newark",
                        "destination": "San Jose",
                    },
                    "summary": {"total_found": 1},
                    "categories": {},
                }
            ),
            name="search_flights",
            tool_call_id="tc_search",
        )
        city_map: dict[str, str] = {}
        _enrich_city_map_from_search_results([ai_msg, tool_msg], city_map)

        assert city_map == {"EWR": "Newark", "SJO": "San Jose"}

    def test_does_not_overwrite_existing_entries(self) -> None:
        """Existing city_map entries are preserved (never overwritten)."""
        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_flights",
                    "args": {"origin": "LHR", "destination": "CDG"},
                    "id": "tc_search",
                }
            ],
        )
        tool_msg = ToolMessage(
            content=json.dumps(
                {
                    "status": "success",
                    "search_params": {
                        "origin": "London Heathrow",
                        "destination": "Paris CDG",
                    },
                    "summary": {"total_found": 1},
                    "categories": {},
                }
            ),
            name="search_flights",
            tool_call_id="tc_search",
        )
        city_map: dict[str, str] = {"LHR": "London"}
        _enrich_city_map_from_search_results([ai_msg, tool_msg], city_map)

        assert city_map["LHR"] == "London"  # Not overwritten
        assert city_map["CDG"] == "Paris CDG"  # New entry added

    def test_skips_failed_search_results(self) -> None:
        """Error results are ignored — no city names to extract."""
        ai_msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_flights",
                    "args": {"origin": "LHR", "destination": "CDG"},
                    "id": "tc_search",
                }
            ],
        )
        tool_msg = ToolMessage(
            content=json.dumps({"status": "error", "error": "No flights found"}),
            name="search_flights",
            tool_call_id="tc_search",
        )
        city_map: dict[str, str] = {}
        _enrich_city_map_from_search_results([ai_msg, tool_msg], city_map)

        assert city_map == {}
