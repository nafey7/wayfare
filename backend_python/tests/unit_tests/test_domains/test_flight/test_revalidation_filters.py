"""Unit tests for revalidation filters."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.domains.flight.revalidation_filters import (
    filter_category_flights_after_revalidation,
    get_flight_ids_to_remove_after_revalidation,
)
from app.domains.flight.schemas import (
    FlightRevalidateRequest,
    FlightRevalidateResponse,
)
from tests.unit_tests.test_domains.test_flight.test_city_wise_filtering import (
    create_mock_fare_itinerary,
)


def _make_fare_itinerary(fare_source_code: str):
    """Create FareItinerary with given fare_source_code."""
    return create_mock_fare_itinerary("LHR", "JFK", fare_source_code=fare_source_code)


@pytest.mark.asyncio
async def test_skips_when_count_zero():
    """Count 0 skips revalidation entirely."""
    result = await get_flight_ids_to_remove_after_revalidation(
        session_id="sess",
        flights=[_make_fare_itinerary("F1")],
        adults=1,
        children=0,
        infants=0,
        revalidate_flights_count=0,
        revalidate_fn=AsyncMock(),
    )
    assert result == set()


@pytest.mark.asyncio
async def test_skips_when_flights_empty():
    """Empty flights list returns empty set."""
    revalidate_fn = AsyncMock()
    result = await get_flight_ids_to_remove_after_revalidation(
        session_id="sess",
        flights=[],
        adults=1,
        children=0,
        infants=0,
        revalidate_flights_count=5,
        revalidate_fn=revalidate_fn,
    )
    assert result == set()
    revalidate_fn.assert_not_called()


@pytest.mark.asyncio
async def test_successful_revalidation_keeps_flight():
    """When revalidate returns is_fare_available=True, flight is kept."""
    revalidate_fn = AsyncMock(
        return_value=FlightRevalidateResponse(
            session_id="sess",
            fare_source_code="F1",
            return_fare_source_code=None,
            is_fare_available=True,
            validated_fare_itineraries=[],
        )
    )
    result = await get_flight_ids_to_remove_after_revalidation(
        session_id="sess",
        flights=[_make_fare_itinerary("F1")],
        adults=1,
        children=0,
        infants=0,
        revalidate_flights_count=5,
        revalidate_fn=revalidate_fn,
    )
    assert result == set()
    revalidate_fn.assert_called_once()


@pytest.mark.asyncio
async def test_unavailable_fare_removes_flight():
    """When is_fare_available=False, flight ID is returned for removal."""
    revalidate_fn = AsyncMock(
        return_value=FlightRevalidateResponse(
            session_id="sess",
            fare_source_code="F1",
            return_fare_source_code=None,
            is_fare_available=False,
            validated_fare_itineraries=[],
        )
    )
    result = await get_flight_ids_to_remove_after_revalidation(
        session_id="sess",
        flights=[_make_fare_itinerary("F1")],
        adults=1,
        children=0,
        infants=0,
        revalidate_flights_count=5,
        revalidate_fn=revalidate_fn,
    )
    assert result == {"F1"}


@pytest.mark.asyncio
async def test_exception_removes_flight():
    """When revalidate raises, that flight is marked for removal."""
    revalidate_fn = AsyncMock(side_effect=Exception("API error"))
    result = await get_flight_ids_to_remove_after_revalidation(
        session_id="sess",
        flights=[_make_fare_itinerary("F1")],
        adults=1,
        children=0,
        infants=0,
        revalidate_flights_count=5,
        revalidate_fn=revalidate_fn,
    )
    assert result == {"F1"}


@pytest.mark.asyncio
async def test_respects_count_limit():
    """Only first N flights are revalidated."""
    calls = []

    async def track_calls(req: FlightRevalidateRequest):
        calls.append(req.fare_source_code)
        return FlightRevalidateResponse(
            session_id="sess",
            fare_source_code=req.fare_source_code,
            return_fare_source_code=None,
            is_fare_available=True,
            validated_fare_itineraries=[],
        )

    flights = [
        _make_fare_itinerary("F1"),
        _make_fare_itinerary("F2"),
        _make_fare_itinerary("F3"),
        _make_fare_itinerary("F4"),
        _make_fare_itinerary("F5"),
    ]
    result = await get_flight_ids_to_remove_after_revalidation(
        session_id="sess",
        flights=flights,
        adults=1,
        children=0,
        infants=0,
        revalidate_flights_count=3,
        revalidate_fn=track_calls,
    )
    assert len(calls) == 3
    assert set(calls) == {"F1", "F2", "F3"}
    assert result == set()


@pytest.mark.asyncio
async def test_executes_in_parallel():
    """Revalidations run via asyncio.gather (parallel execution)."""
    order = []
    lock = asyncio.Lock()

    async def record_order(req: FlightRevalidateRequest):
        async with lock:
            order.append(req.fare_source_code)
        await asyncio.sleep(0.01)  # Small delay to allow interleaving
        return FlightRevalidateResponse(
            session_id="sess",
            fare_source_code=req.fare_source_code,
            return_fare_source_code=None,
            is_fare_available=True,
            validated_fare_itineraries=[],
        )

    flights = [_make_fare_itinerary("F1"), _make_fare_itinerary("F2")]
    await get_flight_ids_to_remove_after_revalidation(
        session_id="sess",
        flights=flights,
        adults=1,
        children=0,
        infants=0,
        revalidate_flights_count=2,
        revalidate_fn=record_order,
    )
    # Both should have been called (parallel via gather)
    assert set(order) == {"F1", "F2"}


@pytest.mark.asyncio
async def test_mixed_revalidate_removal_scenarios():
    """Unavailable, exception, and timeout candidates are removed; valid fares kept."""
    import app.domains.flight.revalidation_filters as rf_module

    async def mixed_revalidate(req: FlightRevalidateRequest):
        if req.fare_source_code == "F2":
            return FlightRevalidateResponse(
                session_id="sess",
                fare_source_code=req.fare_source_code,
                return_fare_source_code=None,
                is_fare_available=False,
                validated_fare_itineraries=[],
            )
        if req.fare_source_code == "F3":
            raise Exception("API error")
        # F4: simulate timeout (exceed patched timeout)
        if req.fare_source_code == "F4":
            await asyncio.sleep(10)  # Will be cut by patched timeout
        return FlightRevalidateResponse(
            session_id="sess",
            fare_source_code=req.fare_source_code,
            return_fare_source_code=None,
            is_fare_available=True,
            validated_fare_itineraries=[],
        )

    flights = [
        _make_fare_itinerary("F1"),
        _make_fare_itinerary("F2"),
        _make_fare_itinerary("F3"),
        _make_fare_itinerary("F4"),
    ]
    with patch.object(rf_module, "REVALIDATE_CALL_TIMEOUT_SECONDS", 0.05):
        result = await get_flight_ids_to_remove_after_revalidation(
            session_id="sess",
            flights=flights,
            adults=1,
            children=0,
            infants=0,
            revalidate_flights_count=4,
            revalidate_fn=mixed_revalidate,
        )
    # F2 (unavailable), F3 (exception), F4 (timeout) must be removed
    assert result == {"F2", "F3", "F4"}
    # F1 must not be removed
    assert "F1" not in result


@pytest.mark.asyncio
async def test_gather_does_not_skip_candidates_when_middle_raises():
    """All candidates are evaluated; a raised error on one fare still removes only that fare."""
    calls = []

    async def failing_middle(req: FlightRevalidateRequest):
        calls.append(req.fare_source_code)
        if req.fare_source_code == "F2":
            raise Exception("middle failure")
        return FlightRevalidateResponse(
            session_id="sess",
            fare_source_code=req.fare_source_code,
            return_fare_source_code=None,
            is_fare_available=True,
            validated_fare_itineraries=[],
        )

    flights = [
        _make_fare_itinerary("F1"),
        _make_fare_itinerary("F2"),
        _make_fare_itinerary("F3"),
    ]
    result = await get_flight_ids_to_remove_after_revalidation(
        session_id="sess",
        flights=flights,
        adults=1,
        children=0,
        infants=0,
        revalidate_flights_count=3,
        revalidate_fn=failing_middle,
    )
    assert len(calls) == 3
    assert set(calls) == {"F1", "F2", "F3"}
    assert result == {"F2"}


# --- filter_category_flights_after_revalidation tests ---


def _make_flight_dict(fare_source_code: str):
    """Create dict with 'id' key (graph tool shape)."""
    return {"id": fare_source_code, "price": 100, "duration_minutes": 120}


@pytest.mark.asyncio
async def test_filter_category_empty_categories():
    """Empty categories return unchanged."""
    categories = {
        "cheapest": {"label": "Cheapest", "flights": []},
        "fastest": {"label": "Fastest", "flights": []},
        "best_value": {"label": "Best Value", "flights": []},
    }
    revalidate_fn = AsyncMock()
    result = await filter_category_flights_after_revalidation(
        session_id="sess",
        categories=dict(categories),
        adults=1,
        children=0,
        infants=0,
        revalidate_fn=revalidate_fn,
        get_fare_source_code=lambda f: f.get("id"),
    )
    assert result["cheapest"]["flights"] == []
    assert result["fastest"]["flights"] == []
    assert result["best_value"]["flights"] == []
    revalidate_fn.assert_not_called()


@pytest.mark.asyncio
async def test_filter_category_removes_invalid():
    """Invalid fares are filtered from categories."""

    async def revalidate_impl(req):
        return FlightRevalidateResponse(
            session_id="sess",
            fare_source_code=req.fare_source_code,
            return_fare_source_code=None,
            is_fare_available=(req.fare_source_code != "F1"),
            validated_fare_itineraries=[],
        )

    revalidate_fn = AsyncMock(side_effect=revalidate_impl)

    categories = {
        "cheapest": {
            "label": "Cheapest",
            "flights": [
                _make_flight_dict("F1"),
                _make_flight_dict("F2"),
                _make_flight_dict("F3"),
            ],
        },
        "fastest": {"label": "Fastest", "flights": []},
        "best_value": {"label": "Best Value", "flights": []},
    }
    result = await filter_category_flights_after_revalidation(
        session_id="sess",
        categories=dict(categories),
        adults=1,
        children=0,
        infants=0,
        revalidate_fn=revalidate_fn,
        get_fare_source_code=lambda f: f.get("id"),
        candidates_per_category=8,
        revalidate_per_category=4,
        max_per_category=3,
    )
    # F1 invalid, removed; F2, F3 valid
    assert len(result["cheapest"]["flights"]) == 2
    assert result["cheapest"]["flights"][0]["id"] == "F2"
    assert result["cheapest"]["flights"][1]["id"] == "F3"


@pytest.mark.asyncio
async def test_filter_category_overlap_deduplication():
    """Same flight in multiple categories is revalidated once."""
    calls = []

    async def track_calls(req):
        calls.append(req.fare_source_code)
        return FlightRevalidateResponse(
            session_id="sess",
            fare_source_code=req.fare_source_code,
            return_fare_source_code=None,
            is_fare_available=True,
            validated_fare_itineraries=[],
        )

    # F1 appears in cheapest and fastest
    categories = {
        "cheapest": {
            "label": "Cheapest",
            "flights": [
                _make_flight_dict("F1"),
                _make_flight_dict("F2"),
                _make_flight_dict("F3"),
            ],
        },
        "fastest": {
            "label": "Fastest",
            "flights": [
                _make_flight_dict("F1"),
                _make_flight_dict("F4"),
            ],
        },
        "best_value": {"label": "Best Value", "flights": []},
    }
    await filter_category_flights_after_revalidation(
        session_id="sess",
        categories=dict(categories),
        adults=1,
        children=0,
        infants=0,
        revalidate_fn=track_calls,
        get_fare_source_code=lambda f: f.get("id"),
        candidates_per_category=8,
        revalidate_per_category=2,
        max_per_category=3,
    )
    # F1 should be revalidated once (deduped from cheapest + fastest)
    assert "F1" in calls
    assert calls.count("F1") == 1


@pytest.mark.asyncio
async def test_filter_category_truncates_to_max():
    """Categories truncated to max_per_category."""

    async def valid_resp(req):
        return FlightRevalidateResponse(
            session_id="sess",
            fare_source_code=req.fare_source_code,
            return_fare_source_code=None,
            is_fare_available=True,
            validated_fare_itineraries=[],
        )

    revalidate_fn = AsyncMock(side_effect=valid_resp)

    categories = {
        "cheapest": {
            "label": "Cheapest",
            "flights": [
                _make_flight_dict("F1"),
                _make_flight_dict("F2"),
                _make_flight_dict("F3"),
                _make_flight_dict("F4"),
                _make_flight_dict("F5"),
            ],
        },
        "fastest": {"label": "Fastest", "flights": []},
        "best_value": {"label": "Best Value", "flights": []},
    }
    result = await filter_category_flights_after_revalidation(
        session_id="sess",
        categories=dict(categories),
        adults=1,
        children=0,
        infants=0,
        revalidate_fn=revalidate_fn,
        get_fare_source_code=lambda f: f.get("id"),
        max_per_category=2,
    )
    assert len(result["cheapest"]["flights"]) == 2
    assert result["cheapest"]["flights"][0]["id"] == "F1"
    assert result["cheapest"]["flights"][1]["id"] == "F2"
