"""Unit tests for _apply_post_filters in flight search tool.

Tests the post-API filtering logic that runs after FlightLogic API results
are returned. Covers: max_stops, price_min/price_max, max_outbound_duration,
max_inbound_duration, and combined filters.
"""

import pytest

from app.ai.graph.tools.flights import _apply_post_filters

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def sample_flights() -> list[dict]:
    """Sample flight data for testing filters."""
    return [
        {
            "id": "flight1",
            "price": 100.0,
            "stops": 0,
            "outbound_duration_minutes": 90,
            "inbound_duration_minutes": None,
        },
        {
            "id": "flight2",
            "price": 250.0,
            "stops": 1,
            "outbound_duration_minutes": 180,
            "inbound_duration_minutes": 200,
        },
        {
            "id": "flight3",
            "price": 500.0,
            "stops": 2,
            "outbound_duration_minutes": 300,
            "inbound_duration_minutes": 280,
        },
        {
            "id": "flight4",
            "price": 150.0,
            "stops": 0,
            "outbound_duration_minutes": 120,
            "inbound_duration_minutes": 130,
        },
    ]


# ==============================================================================
# NO FILTERS
# ==============================================================================


class TestNoFilters:
    """Test that no filters returns all flights unchanged."""

    def test_no_filters_returns_all(self, sample_flights: list[dict]) -> None:
        result = _apply_post_filters(sample_flights)
        assert len(result) == 4

    def test_empty_list_returns_empty(self) -> None:
        result = _apply_post_filters([])
        assert result == []

    def test_all_none_filters_returns_all(self, sample_flights: list[dict]) -> None:
        result = _apply_post_filters(
            sample_flights,
            max_stops=None,
            price_min=None,
            price_max=None,
            max_outbound_duration=None,
            max_inbound_duration=None,
        )
        assert len(result) == 4


# ==============================================================================
# MAX STOPS FILTER
# ==============================================================================


class TestMaxStopsFilter:
    """Test max_stops post-filter."""

    def test_max_stops_zero_not_applied(self, sample_flights: list[dict]) -> None:
        """max_stops=0 is handled at API level (direct_flight=1), not post-filter."""
        result = _apply_post_filters(sample_flights, max_stops=0)
        assert len(result) == 4  # 0 is not > 0, so no filtering

    def test_max_stops_one(self, sample_flights: list[dict]) -> None:
        result = _apply_post_filters(sample_flights, max_stops=1)
        assert len(result) == 3
        assert all(f["stops"] <= 1 for f in result)

    def test_max_stops_two(self, sample_flights: list[dict]) -> None:
        result = _apply_post_filters(sample_flights, max_stops=2)
        assert len(result) == 4  # All flights have <= 2 stops

    def test_max_stops_filters_out_all(self) -> None:
        flights = [{"id": "f1", "stops": 3}, {"id": "f2", "stops": 5}]
        result = _apply_post_filters(flights, max_stops=1)
        assert len(result) == 0


# ==============================================================================
# PRICE FILTERS
# ==============================================================================


class TestPriceFilters:
    """Test price_min and price_max post-filters."""

    def test_price_min_only(self, sample_flights: list[dict]) -> None:
        result = _apply_post_filters(sample_flights, price_min=200.0)
        assert len(result) == 2
        assert all(f["price"] >= 200.0 for f in result)

    def test_price_max_only(self, sample_flights: list[dict]) -> None:
        result = _apply_post_filters(sample_flights, price_max=200.0)
        assert len(result) == 2
        assert all(f["price"] <= 200.0 for f in result)

    def test_price_range(self, sample_flights: list[dict]) -> None:
        result = _apply_post_filters(sample_flights, price_min=100.0, price_max=250.0)
        assert len(result) == 3
        assert all(100.0 <= f["price"] <= 250.0 for f in result)

    def test_price_exact_boundary(self, sample_flights: list[dict]) -> None:
        """Exact boundary values should be included."""
        result = _apply_post_filters(sample_flights, price_min=100.0, price_max=100.0)
        assert len(result) == 1
        assert result[0]["id"] == "flight1"

    def test_price_range_no_match(self, sample_flights: list[dict]) -> None:
        result = _apply_post_filters(sample_flights, price_min=600.0, price_max=900.0)
        assert len(result) == 0


# ==============================================================================
# OUTBOUND DURATION FILTER
# ==============================================================================


class TestOutboundDurationFilter:
    """Test max_outbound_duration post-filter."""

    def test_outbound_duration_filters_correctly(
        self, sample_flights: list[dict]
    ) -> None:
        """max_outbound_duration=2.0 (120 min) should keep flights <= 120 min."""
        result = _apply_post_filters(sample_flights, max_outbound_duration=2.0)
        assert len(result) == 2
        ids = {f["id"] for f in result}
        assert ids == {"flight1", "flight4"}

    def test_outbound_duration_1_5_hours(self, sample_flights: list[dict]) -> None:
        """1.5 hours = 90 minutes, only flight1 qualifies."""
        result = _apply_post_filters(sample_flights, max_outbound_duration=1.5)
        assert len(result) == 1
        assert result[0]["id"] == "flight1"

    def test_outbound_duration_large_value_keeps_all(
        self, sample_flights: list[dict]
    ) -> None:
        result = _apply_post_filters(sample_flights, max_outbound_duration=10.0)
        assert len(result) == 4

    def test_outbound_duration_none_value_kept(self) -> None:
        """Flights with outbound_duration_minutes=None should NOT be filtered out."""
        flights = [
            {"id": "f1", "outbound_duration_minutes": None},
            {"id": "f2", "outbound_duration_minutes": 200},
        ]
        result = _apply_post_filters(flights, max_outbound_duration=1.0)
        assert len(result) == 1
        assert result[0]["id"] == "f1"

    def test_outbound_duration_missing_key_kept(self) -> None:
        """Flights without outbound_duration_minutes key should NOT be filtered out."""
        flights = [
            {"id": "f1"},  # No outbound_duration_minutes key
            {"id": "f2", "outbound_duration_minutes": 200},
        ]
        result = _apply_post_filters(flights, max_outbound_duration=1.0)
        assert len(result) == 1
        assert result[0]["id"] == "f1"

    def test_outbound_duration_zero_kept(self) -> None:
        """Flights with outbound_duration_minutes=0 should be kept (0 <= any max)."""
        flights = [
            {"id": "f1", "outbound_duration_minutes": 0},
            {"id": "f2", "outbound_duration_minutes": 120},
        ]
        result = _apply_post_filters(flights, max_outbound_duration=1.0)
        assert len(result) == 1
        assert result[0]["id"] == "f1"

    def test_outbound_duration_very_small_max(self) -> None:
        """Very small max_outbound_duration (e.g. 0.1h = 6 min) filters correctly."""
        flights = [
            {"id": "f1", "outbound_duration_minutes": 5},
            {"id": "f2", "outbound_duration_minutes": 10},
        ]
        result = _apply_post_filters(flights, max_outbound_duration=0.1)  # 6 minutes
        assert len(result) == 1
        assert result[0]["id"] == "f1"


# ==============================================================================
# INBOUND DURATION FILTER
# ==============================================================================


class TestInboundDurationFilter:
    """Test max_inbound_duration post-filter."""

    def test_inbound_duration_filters_correctly(
        self, sample_flights: list[dict]
    ) -> None:
        """max_inbound_duration=3.0 (180 min) keeps flights with inbound <= 180 or None."""
        result = _apply_post_filters(sample_flights, max_inbound_duration=3.0)
        # flight1: None (kept), flight2: 200 (filtered), flight3: 280 (filtered), flight4: 130 (kept)
        assert len(result) == 2
        ids = {f["id"] for f in result}
        assert ids == {"flight1", "flight4"}

    def test_inbound_duration_none_value_kept(self) -> None:
        """Flights with inbound_duration_minutes=None should NOT be filtered out."""
        flights = [
            {"id": "f1", "inbound_duration_minutes": None},
            {"id": "f2", "inbound_duration_minutes": 300},
        ]
        result = _apply_post_filters(flights, max_inbound_duration=2.0)
        assert len(result) == 1
        assert result[0]["id"] == "f1"

    def test_inbound_duration_exact_boundary(self) -> None:
        flights = [{"id": "f1", "inbound_duration_minutes": 120}]
        result = _apply_post_filters(flights, max_inbound_duration=2.0)  # 120 min
        assert len(result) == 1


# ==============================================================================
# COMBINED FILTERS
# ==============================================================================


class TestCombinedFilters:
    """Test multiple filters applied together."""

    def test_stops_and_price(self, sample_flights: list[dict]) -> None:
        result = _apply_post_filters(sample_flights, max_stops=1, price_max=200.0)
        assert len(result) == 2
        ids = {f["id"] for f in result}
        assert ids == {"flight1", "flight4"}

    def test_price_and_outbound_duration(self, sample_flights: list[dict]) -> None:
        result = _apply_post_filters(
            sample_flights, price_max=300.0, max_outbound_duration=2.0
        )
        # price<=300: flight1(100), flight2(250), flight4(150) → 3 flights
        # outbound<=120min: flight1(90), flight4(120) → 2 flights
        assert len(result) == 2
        ids = {f["id"] for f in result}
        assert ids == {"flight1", "flight4"}

    def test_all_filters_combined(self, sample_flights: list[dict]) -> None:
        result = _apply_post_filters(
            sample_flights,
            max_stops=1,
            price_min=100.0,
            price_max=300.0,
            max_outbound_duration=3.0,
            max_inbound_duration=3.0,
        )
        # max_stops<=1: flight1, flight2, flight4
        # price 100-300: flight1, flight2, flight4
        # outbound<=180: flight1(90), flight2(180), flight4(120)
        # inbound<=180: flight1(None→kept), flight4(130→kept) — flight2(200→filtered)
        assert len(result) == 2
        ids = {f["id"] for f in result}
        assert ids == {"flight1", "flight4"}

    def test_all_filters_no_match(self, sample_flights: list[dict]) -> None:
        result = _apply_post_filters(
            sample_flights,
            max_stops=0,  # Not applied (0 not > 0)
            price_min=400.0,
            max_outbound_duration=1.0,
        )
        # price>=400: flight3(500) only
        # outbound<=60min: flight3(300) → filtered
        assert len(result) == 0
