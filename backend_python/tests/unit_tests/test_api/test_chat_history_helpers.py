"""Unit tests for chat history helpers.

Covers ``_infer_message_type`` and ``_build_extra_data_for_history`` in
``app.api.chat`` — the back-fill and trimming logic that powers rich
flight/hotel/itinerary history restore.
"""

from app.api.chat import (
    _ITINERARY_HISTORY_KEYS,
    _build_extra_data_for_history,
    _infer_message_type,
    _strip_flights_from_items,
)

# ---------------------------------------------------------------------------
# _infer_message_type
# ---------------------------------------------------------------------------


class TestInferMessageType:
    def test_returns_none_for_non_dict(self) -> None:
        assert _infer_message_type(None) is None
        assert _infer_message_type("string") is None
        assert _infer_message_type(42) is None

    def test_returns_none_for_empty_dict(self) -> None:
        assert _infer_message_type({}) is None

    def test_detects_multicity_via_multicity_legs(self) -> None:
        assert (
            _infer_message_type({"multicity_legs": []})
            == "multicity_flight_search_results"
        )

    def test_detects_date_range_via_dates_and_searched_from(self) -> None:
        assert (
            _infer_message_type({"dates": [], "searched_from": "2026-06-01"})
            == "flight_date_range_results"
        )

    def test_detects_hotel_via_check_in_date(self) -> None:
        assert (
            _infer_message_type({"search_params": {"check_in_date": "2026-06-01"}})
            == "hotel_search_results"
        )

    def test_detects_hotel_via_checkout(self) -> None:
        assert (
            _infer_message_type({"search_params": {"checkout": "2026-06-05"}})
            == "hotel_search_results"
        )

    def test_detects_flight_via_origin(self) -> None:
        assert (
            _infer_message_type({"search_params": {"origin": "AMS"}})
            == "flight_search_results"
        )

    def test_detects_flight_via_departure_date(self) -> None:
        assert (
            _infer_message_type({"search_params": {"departure_date": "2026-06-01"}})
            == "flight_search_results"
        )

    def test_detects_itinerary_via_structured_itinerary(self) -> None:
        assert (
            _infer_message_type({"structured_itinerary": {"itineraryItems": []}})
            == "itinerary_results"
        )

    def test_chain_flight_with_saved_itinerary_id_is_flight_not_itinerary(self) -> None:
        """Regression: chain auto-save leaks saved_itinerary_id into chained
        flight/hotel action_data. The inferred type must still be flight, not
        itinerary — ``saved_itinerary_id`` alone is not sufficient evidence.
        """
        action_data = {
            "search_params": {"origin": "AMS", "destination": "BCN"},
            "saved_itinerary_id": "abc123",
        }
        assert _infer_message_type(action_data) == "flight_search_results"

    def test_chain_hotel_with_saved_itinerary_id_is_hotel_not_itinerary(self) -> None:
        action_data = {
            "search_params": {"check_in_date": "2026-06-01"},
            "saved_itinerary_id": "abc123",
        }
        assert _infer_message_type(action_data) == "hotel_search_results"

    def test_saved_itinerary_id_alone_does_not_match(self) -> None:
        """A bare ``saved_itinerary_id`` (no structured_itinerary, no
        search_params) is ambiguous — return None and let the caller
        treat it as a plain text message."""
        assert _infer_message_type({"saved_itinerary_id": "abc"}) is None


# ---------------------------------------------------------------------------
# _strip_flights_from_items
# ---------------------------------------------------------------------------


class TestStripFlightsFromItems:
    def test_returns_none_for_non_list(self) -> None:
        assert _strip_flights_from_items(None) is None
        assert _strip_flights_from_items({}) is None
        assert _strip_flights_from_items("not a list") is None

    def test_returns_empty_list_for_empty_input(self) -> None:
        assert _strip_flights_from_items([]) == []

    def test_strips_flights_key_from_dict_items(self) -> None:
        result = _strip_flights_from_items(
            [
                {
                    "origin": "AMS",
                    "destination": "BCN",
                    "flights": [{"id": "f1"}, {"id": "f2"}],
                },
                {
                    "origin": "BCN",
                    "destination": "MAD",
                    "flights": [{"id": "f3"}],
                },
            ]
        )
        assert result == [
            {"origin": "AMS", "destination": "BCN"},
            {"origin": "BCN", "destination": "MAD"},
        ]

    def test_preserves_other_keys(self) -> None:
        result = _strip_flights_from_items(
            [{"date": "2026-06-01", "min_price": 100, "flights": [1, 2]}]
        )
        assert result == [{"date": "2026-06-01", "min_price": 100}]

    def test_handles_items_without_flights_key(self) -> None:
        result = _strip_flights_from_items([{"origin": "AMS"}])
        assert result == [{"origin": "AMS"}]


# ---------------------------------------------------------------------------
# _build_extra_data_for_history
# ---------------------------------------------------------------------------


class TestBuildExtraDataForHistory:
    def test_returns_none_for_non_dict_action_data(self) -> None:
        assert _build_extra_data_for_history("flight_search_results", None) is None
        assert _build_extra_data_for_history("flight_search_results", "x") is None

    def test_returns_none_when_msg_type_is_none(self) -> None:
        assert _build_extra_data_for_history(None, {"search_params": {}}) is None

    def test_returns_none_for_non_rich_message_types(self) -> None:
        assert _build_extra_data_for_history("message", {"search_params": {}}) is None
        assert _build_extra_data_for_history("error", {"foo": "bar"}) is None

    def test_flight_search_results_returned_as_is(self) -> None:
        action_data = {
            "search_params": {"origin": "AMS", "destination": "BCN"},
            "summary": {"total_flights": 12},
        }
        result = _build_extra_data_for_history("flight_search_results", action_data)
        assert result == action_data
        # Defensive copy: result must not be the same dict as input
        assert result is not action_data

    def test_hotel_search_results_returned_as_is(self) -> None:
        action_data = {"summary": {"total_hotels": 5}}
        result = _build_extra_data_for_history("hotel_search_results", action_data)
        assert result == action_data

    def test_itinerary_keeps_only_allowed_keys(self) -> None:
        action_data = {
            "origin": "AMS",
            "destination": "Barcelona",
            "departure_date": "2026-06-01",
            "return_date": "2026-06-08",
            "adults": 2,
            "children": 1,
            "infants": 0,
            "trip_type": "round_trip",
            "saved_itinerary_id": "abc123",
            # Heavy fields that must be stripped:
            "structured_itinerary": {"itineraryItems": [1] * 100},
            "flights": [{"id": "f"}] * 50,
            "hotels": [{"id": "h"}] * 30,
            "flight_session_id": "ses_x",
        }
        result = _build_extra_data_for_history("itinerary_results", action_data)
        assert result is not None
        assert "structured_itinerary" not in result
        assert "flights" not in result
        assert "hotels" not in result
        assert "flight_session_id" not in result
        # Allowed keys preserved
        assert result["origin"] == "AMS"
        assert result["destination"] == "Barcelona"
        assert result["saved_itinerary_id"] == "abc123"
        # Every retained key is in the allowlist
        assert set(result.keys()) <= _ITINERARY_HISTORY_KEYS

    def test_multicity_strips_per_leg_flights(self) -> None:
        action_data = {
            "search_params": {"cabin_class": "Economy"},
            "multicity_parallel": True,
            "multicity_legs": [
                {
                    "origin": "AMS",
                    "destination": "BCN",
                    "flights": [{"id": f"f{i}"} for i in range(50)],
                },
                {
                    "origin": "BCN",
                    "destination": "MAD",
                    "flights": [{"id": f"f{i}"} for i in range(40)],
                },
            ],
        }
        result = _build_extra_data_for_history(
            "multicity_flight_search_results", action_data
        )
        assert result is not None
        assert result["search_params"] == {"cabin_class": "Economy"}
        assert result["multicity_parallel"] is True
        for leg in result["multicity_legs"]:
            assert "flights" not in leg
        assert result["multicity_legs"][0]["origin"] == "AMS"

    def test_date_range_strips_per_date_flights(self) -> None:
        action_data = {
            "searched_from": "2026-06-01",
            "searched_to": "2026-06-07",
            "dates": [
                {
                    "date": "2026-06-01",
                    "min_price": 120,
                    "flights": [{"id": f"f{i}"} for i in range(20)],
                },
                {
                    "date": "2026-06-02",
                    "min_price": 130,
                    "flights": [{"id": f"f{i}"} for i in range(20)],
                },
            ],
        }
        result = _build_extra_data_for_history("flight_date_range_results", action_data)
        assert result is not None
        assert result["searched_from"] == "2026-06-01"
        for date in result["dates"]:
            assert "flights" not in date
            assert "min_price" in date

    def test_multicity_without_legs_key_passes_through(self) -> None:
        action_data = {"search_params": {"foo": "bar"}}
        result = _build_extra_data_for_history(
            "multicity_flight_search_results", action_data
        )
        assert result == action_data
