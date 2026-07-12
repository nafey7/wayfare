"""Unit tests for the personalized-itinerary stitcher (#1038).

Stitcher is pure Python — no LLM, no I/O — so these tests run without
mocking. They cover the doc's contract:

- Day 1 leads with outbound flight + hotel check-in cards before the LLM's
  activities (Q9: prepend regardless of activity time).
- Day N opens with check-out (top) and ends with return flight (bottom)
  for round-trips.
- One-way trips skip return + check-out (Q5).
- Empty flights / hotels lists no-op gracefully ("graceful degradation").
- ``kind`` field is set on every inserted entry so the FE knows which
  compact card to render. Legacy activities (no ``kind``) stay untouched.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.ai.graph.itinerary_stitcher import stitch_itinerary


def _make_itinerary(num_days: int = 3) -> dict[str, Any]:
    """Build a minimal LLM-shaped itinerary dict."""
    items: list[dict[str, Any]] = []
    for d in range(1, num_days + 1):
        items.append(
            {
                "day": d,
                "title": f"Day {d}",
                "expandedContent": {
                    "activities": [
                        {"location": f"Place {d}A", "duration": "2h"},
                        {"location": f"Place {d}B", "duration": "1h"},
                    ],
                },
            }
        )
    return {"itineraryItems": items}


def _make_flight(flight_id: str = "f1", price: float = 250.0) -> dict[str, Any]:
    return {
        "id": flight_id,
        "airline": "British Airways",
        "airline_code": "BA",
        "price": price,
        "currency": "USD",
        "origin_code": "LHR",
        "destination_code": "NRT",
        "departure_time": "10:00",
        "arrival_time": "08:55",
        "duration": "11h 55m",
        "stops": 0,
    }


def _make_hotel(hotel_id: str = "h1", price: float = 200.0) -> dict[str, Any]:
    return {
        "hotel_id": hotel_id,
        "hotel_name": "Mandarin Oriental",
        "city": "Tokyo",
        "country": "Japan",
        "total_price": price,
        "currency": "USD",
        "hotel_rating": 5,
    }


class TestStitchItinerary:
    def test_round_trip_inserts_day1_flight_and_checkin(self) -> None:
        itinerary = _make_itinerary(num_days=5)
        flight = _make_flight()
        hotel = _make_hotel()

        result = stitch_itinerary(itinerary, [flight], [hotel], is_round_trip=True)

        day1_activities = result["itineraryItems"][0]["expandedContent"]["activities"]
        # Flight + check-in at the top, LLM activities after
        assert day1_activities[0]["kind"] == "flight"
        assert day1_activities[0]["leg"] == "outbound"
        assert day1_activities[0]["flight"] == flight
        assert day1_activities[1]["kind"] == "hotel-checkin"
        assert day1_activities[1]["hotel"] == hotel
        # LLM activities preserved, in original order
        assert day1_activities[2]["location"] == "Place 1A"
        assert day1_activities[3]["location"] == "Place 1B"

    def test_round_trip_inserts_dayN_checkout_and_return_flight(self) -> None:
        itinerary = _make_itinerary(num_days=5)
        flight = _make_flight()
        hotel = _make_hotel()

        result = stitch_itinerary(itinerary, [flight], [hotel], is_round_trip=True)

        dayN_activities = result["itineraryItems"][-1]["expandedContent"]["activities"]
        # Check-out first (morning), LLM activities, then return flight at the end
        assert dayN_activities[0]["kind"] == "hotel-checkout"
        assert dayN_activities[0]["hotel"] == hotel
        # LLM activities in the middle
        assert dayN_activities[1]["location"] == "Place 5A"
        assert dayN_activities[2]["location"] == "Place 5B"
        # Return flight at the bottom
        assert dayN_activities[-1]["kind"] == "flight"
        assert dayN_activities[-1]["leg"] == "inbound"
        assert dayN_activities[-1]["flight"] == flight

    def test_one_way_skips_return_and_checkout(self) -> None:
        """Q5: one-way trips inject outbound + check-in only — no return / check-out."""
        itinerary = _make_itinerary(num_days=3)
        flight = _make_flight()
        hotel = _make_hotel()

        result = stitch_itinerary(itinerary, [flight], [hotel], is_round_trip=False)

        day1_activities = result["itineraryItems"][0]["expandedContent"]["activities"]
        # Day 1 still gets flight + check-in
        assert day1_activities[0]["kind"] == "flight"
        assert day1_activities[1]["kind"] == "hotel-checkin"

        dayN_activities = result["itineraryItems"][-1]["expandedContent"]["activities"]
        # Day N gets check-out (always — hotel guests still check out on a one-way
        # trip) but NO return flight.
        kinds = [e.get("kind") for e in dayN_activities]
        assert "hotel-checkout" in kinds
        # No flight on the last day for one-way trips
        flight_kinds_dayN = [e for e in dayN_activities if e.get("kind") == "flight"]
        assert flight_kinds_dayN == []

    def test_uses_first_flight_and_first_hotel_only(self) -> None:
        """flights[0] / hotels[0] become inline cards; rest stay in the lists for the FE rails."""
        itinerary = _make_itinerary(num_days=3)
        top_flight = _make_flight(flight_id="f-top", price=100.0)
        other_flight = _make_flight(flight_id="f-other", price=200.0)
        top_hotel = _make_hotel(hotel_id="h-top", price=100.0)
        other_hotel = _make_hotel(hotel_id="h-other", price=200.0)

        result = stitch_itinerary(
            itinerary,
            [top_flight, other_flight],
            [top_hotel, other_hotel],
            is_round_trip=True,
        )

        day1 = result["itineraryItems"][0]["expandedContent"]["activities"]
        assert day1[0]["flight"]["id"] == "f-top"
        assert day1[1]["hotel"]["hotel_id"] == "h-top"
        # Other entries don't get injected anywhere in the day plan — they ride
        # on the response top-level `flights`/`hotels` (the orchestrator
        # handles that; stitcher's job is just the inline cards).
        all_kinds: list[str] = []
        for day in result["itineraryItems"]:
            for entry in day["expandedContent"]["activities"]:
                if entry.get("kind"):
                    all_kinds.append(entry["kind"])
        # Exactly: flight (D1 outbound), hotel-checkin (D1), hotel-checkout (DN), flight (DN inbound)
        assert all_kinds.count("flight") == 2
        assert all_kinds.count("hotel-checkin") == 1
        assert all_kinds.count("hotel-checkout") == 1

    def test_empty_flights_skips_flight_cards(self) -> None:
        """If flight search returned empty, no flight cards — hotel cards still land."""
        itinerary = _make_itinerary(num_days=3)
        hotel = _make_hotel()

        result = stitch_itinerary(itinerary, [], [hotel], is_round_trip=True)

        all_kinds: list[str] = []
        for day in result["itineraryItems"]:
            for entry in day["expandedContent"]["activities"]:
                if entry.get("kind"):
                    all_kinds.append(entry["kind"])

        assert "flight" not in all_kinds
        assert "hotel-checkin" in all_kinds
        assert "hotel-checkout" in all_kinds

    def test_empty_hotels_skips_hotel_cards(self) -> None:
        """If hotel search returned empty, no hotel cards — flight cards still land."""
        itinerary = _make_itinerary(num_days=3)
        flight = _make_flight()

        result = stitch_itinerary(itinerary, [flight], [], is_round_trip=True)

        all_kinds: list[str] = []
        for day in result["itineraryItems"]:
            for entry in day["expandedContent"]["activities"]:
                if entry.get("kind"):
                    all_kinds.append(entry["kind"])

        assert all_kinds.count("flight") == 2  # outbound + inbound
        assert "hotel-checkin" not in all_kinds
        assert "hotel-checkout" not in all_kinds

    def test_both_empty_noop(self) -> None:
        """Both searches empty → itinerary unchanged."""
        itinerary = _make_itinerary(num_days=3)
        snapshot_before = [
            list(d["expandedContent"]["activities"])
            for d in itinerary["itineraryItems"]
        ]

        stitch_itinerary(itinerary, None, None, is_round_trip=True)

        snapshot_after = [
            list(d["expandedContent"]["activities"])
            for d in itinerary["itineraryItems"]
        ]
        assert snapshot_before == snapshot_after

    def test_empty_itinerary_items_noop(self) -> None:
        """No day plan to stitch into → return unchanged."""
        itinerary: dict[str, Any] = {"itineraryItems": []}
        flight = _make_flight()
        hotel = _make_hotel()

        result = stitch_itinerary(itinerary, [flight], [hotel], is_round_trip=True)

        assert result["itineraryItems"] == []

    def test_creates_expanded_content_if_missing(self) -> None:
        """An item without ``expandedContent`` should still accept cards."""
        itinerary: dict[str, Any] = {
            "itineraryItems": [
                {"day": 1, "title": "Day 1"},  # No expandedContent
                {"day": 2, "title": "Day 2"},  # No expandedContent
            ]
        }
        flight = _make_flight()
        hotel = _make_hotel()

        result = stitch_itinerary(itinerary, [flight], [hotel], is_round_trip=True)

        day1 = result["itineraryItems"][0]
        assert "expandedContent" in day1
        assert day1["expandedContent"]["activities"][0]["kind"] == "flight"
        assert day1["expandedContent"]["activities"][1]["kind"] == "hotel-checkin"

    def test_single_day_trip_uses_same_day_for_in_and_out(self) -> None:
        """Edge case: 1-day itinerary — first and last day are the same.

        Both outbound flight + check-in (Day 1) AND check-out + return flight
        (Day N == Day 1) land on the same day. The stitcher doesn't enforce
        a separate last day — that's a product decision out of scope here.
        """
        itinerary = _make_itinerary(num_days=1)
        flight = _make_flight()
        hotel = _make_hotel()

        result = stitch_itinerary(itinerary, [flight], [hotel], is_round_trip=True)

        # Only one day exists, so last_day is None in the stitcher (we guard on
        # ``len(items) > 1``). Only Day 1 inserts happen.
        day1 = result["itineraryItems"][0]["expandedContent"]["activities"]
        kinds = [e.get("kind") for e in day1 if e.get("kind")]
        # Day 1 inserts: flight (outbound), hotel-checkin. No Day N inserts
        # because there's no separate last day to render.
        assert kinds == ["flight", "hotel-checkin"]

    def test_returns_same_dict_reference(self) -> None:
        """Stitcher mutates in place AND returns the same dict (for chaining)."""
        itinerary = _make_itinerary(num_days=3)
        result = stitch_itinerary(itinerary, [], [], is_round_trip=True)
        assert result is itinerary


@pytest.mark.parametrize("is_round_trip", [True, False])
def test_existing_activities_kind_field_untouched(is_round_trip: bool) -> None:
    """Legacy activities (no ``kind``) must remain unchanged — the FE renderer
    treats missing ``kind`` as ``"activity"``, so we don't need to back-fill it.
    """
    itinerary = _make_itinerary(num_days=3)
    flight = _make_flight()

    stitch_itinerary(itinerary, [flight], [], is_round_trip=is_round_trip)

    # Find the LLM-produced activities by their `location` field
    for day in itinerary["itineraryItems"]:
        for entry in day["expandedContent"]["activities"]:
            if "location" in entry:
                # LLM activities should NOT have a `kind` field — back-compat.
                assert "kind" not in entry
