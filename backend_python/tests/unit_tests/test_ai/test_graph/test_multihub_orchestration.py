"""Unit tests for multi-hub country destination orchestration (#1152)."""

from __future__ import annotations

import pytest

from app.ai.graph.itinerary_orchestrator import _merge_hotel_results

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HUB_LIST = [
    {"city": "Kotor", "iata": "TIV"},
    {"city": "Podgorica", "iata": "TGD"},
]

_HOTEL_KOTOR = {
    "status": "success",
    "session_id": "sess-hotel-tiv",
    "hotels": [
        {"hotel_id": "h1", "name": "Kotor Bay Hotel", "price": 150},
        {"hotel_id": "h2", "name": "Old Town Rooms", "price": 90},
    ],
}
_HOTEL_PODGORICA = {
    "status": "success",
    "session_id": "sess-hotel-tgd",
    "hotels": [
        {"hotel_id": "h3", "name": "Capital Plaza", "price": 120},
    ],
}


# ---------------------------------------------------------------------------
# _merge_hotel_results
# ---------------------------------------------------------------------------


class TestMergeHotelResults:
    def test_merges_hotels_from_both_hubs(self) -> None:
        merged = _merge_hotel_results([_HOTEL_KOTOR, _HOTEL_PODGORICA], _HUB_LIST)
        assert merged is not None
        assert len(merged["hotels"]) == 3

    def test_deduplicates_by_hotel_id(self) -> None:
        dup_hotel = {
            "status": "success",
            "session_id": "s2",
            "hotels": [{"hotel_id": "h1", "name": "Kotor Bay Hotel duplicate"}],
        }
        merged = _merge_hotel_results([_HOTEL_KOTOR, dup_hotel], _HUB_LIST)
        assert merged is not None
        ids = [h["hotel_id"] for h in merged["hotels"]]
        assert ids.count("h1") == 1  # deduped

    def test_tags_search_city(self) -> None:
        merged = _merge_hotel_results([_HOTEL_KOTOR, _HOTEL_PODGORICA], _HUB_LIST)
        assert merged is not None
        kotor_hotels = [h for h in merged["hotels"] if h.get("search_city") == "Kotor"]
        podgorica_hotels = [
            h for h in merged["hotels"] if h.get("search_city") == "Podgorica"
        ]
        assert len(kotor_hotels) == 2
        assert len(podgorica_hotels) == 1

    def test_returns_none_when_all_fail(self) -> None:
        assert _merge_hotel_results([None, None], _HUB_LIST) is None


# ---------------------------------------------------------------------------
# Unmapped country hotel skip
# ---------------------------------------------------------------------------


class TestUnmappedCountryHotelSkip:
    @pytest.mark.asyncio
    async def test_skips_hotel_search_for_unmapped_country(self) -> None:
        """When destination_is_country=True but no hub, hotel search skips."""
        from app.ai.graph.itinerary_orchestrator import _safe_hotel_search

        trip_ctx = {
            "destination": "Atlantis",
            "destination_is_country": True,
            "destination_search_city": None,
            "departure_date": "2026-07-20",
            "return_date": "2026-08-02",
        }
        result = await _safe_hotel_search(trip_ctx, "user123")
        assert result is None
