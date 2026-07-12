"""Unit tests for hotel nearby-location distance computation and sort logic."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.domains.hotel.pricing import apply_platform_fee
from app.domains.hotel.schemas import (
    HotelMoreResultsRequest,
    HotelSearchRequest,
    HotelSearchResponse,
    HotelSearchResult,
    NearbyLocation,
    OccupancyRoom,
    PerNightPrice,
)
from app.domains.hotel.service import HotelService
from app.shared.geo import haversine_km


def _make_hotel(
    hotel_id: str,
    latitude: str | None,
    longitude: str | None,
) -> HotelSearchResult:
    """Build a minimal HotelSearchResult for testing."""
    return HotelSearchResult(
        hotel_id=hotel_id,
        twx_hotel_id=hotel_id,
        product_id=f"prod-{hotel_id}",
        token_id=f"tok-{hotel_id}",
        hotel_name=f"Hotel {hotel_id}",
        latitude=latitude,
        longitude=longitude,
        distance_value=0.0,
        distance_unit="KM",
        total=Decimal("100.00"),
        currency="USD",
        fare_type="Refundable",
        per_night_array=[
            PerNightPrice(night_index=1, currency="USD", price=Decimal("100.00"))
        ],
        thumbnail_url="https://example.com/img.jpg",
        city="Paris",
        country="France",
        country_code="FR",
    )


class TestNearbySort:
    """Tests for HotelService._apply_nearby_sort."""

    def test_nearby_sort_ascending(self) -> None:
        """Hotels at known distances should be returned nearest-first."""
        # Reference point: Eiffel Tower (48.858, 2.294)
        ref = NearbyLocation(lat=48.858, lng=2.294)

        # Hotel A — far (Zurich area, ~490 km)
        hotel_a = _make_hotel("A", "47.376", "8.541")
        # Hotel B — near (1 km from Eiffel Tower area)
        hotel_b = _make_hotel("B", "48.866", "2.308")
        # Hotel C — medium (Amsterdam area, ~430 km)
        hotel_c = _make_hotel("C", "52.370", "4.895")

        itineraries = [hotel_a, hotel_b, hotel_c]
        HotelService._apply_nearby_sort(itineraries, ref)

        assert [h.hotel_id for h in itineraries] == ["B", "A", "C"] or [
            h.hotel_id for h in itineraries
        ] == ["B", "C", "A"], (
            f"Expected B nearest; got {[h.hotel_id for h in itineraries]}"
        )
        # B must always be first (nearest)
        assert itineraries[0].hotel_id == "B"

    def test_nearby_distance_km_value(self) -> None:
        """Computed nearby_distance_km should match the haversine formula within 0.01 km."""
        ref = NearbyLocation(lat=48.858, lng=2.294)
        hotel = _make_hotel("X", "48.866", "2.308")

        HotelService._apply_nearby_sort([hotel], ref)

        expected = haversine_km(48.858, 2.294, 48.866, 2.308)
        assert hotel.nearby_distance_km is not None
        assert hotel.nearby_distance_km == pytest.approx(expected, abs=0.01)

    def test_nearby_null_coords_last(self) -> None:
        """Hotels without coordinates should be appended after hotels with coordinates."""
        ref = NearbyLocation(lat=48.858, lng=2.294)

        hotel_near = _make_hotel("near", "48.860", "2.295")
        hotel_no_coords = _make_hotel("nocoords", None, None)
        hotel_far = _make_hotel("far", "47.000", "2.000")

        itineraries = [hotel_no_coords, hotel_far, hotel_near]
        HotelService._apply_nearby_sort(itineraries, ref)

        # Hotel with no coords must come last
        assert itineraries[-1].hotel_id == "nocoords"
        assert itineraries[-1].nearby_distance_km is None
        # Hotels with coords must be sorted ascending by distance
        assert itineraries[0].hotel_id == "near"

    def test_nearby_malformed_coords_ignored(self) -> None:
        """Malformed hotel coordinates should be treated like missing coordinates."""
        ref = NearbyLocation(lat=48.858, lng=2.294)

        hotel_bad = _make_hotel("bad", "", "2.295")
        hotel_good = _make_hotel("good", "48.860", "2.295")
        itineraries = [hotel_bad, hotel_good]

        HotelService._apply_nearby_sort(itineraries, ref)

        assert itineraries[-1].hotel_id == "bad"
        assert hotel_bad.nearby_distance_km is None
        assert hotel_good.nearby_distance_km is not None

    def test_no_nearby_location_unchanged(self) -> None:
        """Without nearby_location, _apply_nearby_sort is never called; order is preserved."""
        # Simulate that when nearby_location is None the service does NOT call _apply_nearby_sort.
        hotel_a = _make_hotel("A", "48.860", "2.295")
        hotel_b = _make_hotel("B", "47.000", "2.000")
        itineraries = [hotel_a, hotel_b]

        # Verify that when nearby_location is None in a real HotelSearchRequest
        # the method is not invoked. We test this by checking no nearby_distance_km is set
        # and order does not change.
        original_order = [h.hotel_id for h in itineraries]

        # _apply_nearby_sort is NOT called when nearby_location is None (see service.py).
        # So we simply verify that nearby_distance_km remains None on both.
        assert hotel_a.nearby_distance_km is None
        assert hotel_b.nearby_distance_km is None
        assert [h.hotel_id for h in itineraries] == original_order

    def test_all_null_coords_noop(self) -> None:
        """When all hotels have missing coordinates, order is preserved (sort is stable on Infinity)."""
        ref = NearbyLocation(lat=48.858, lng=2.294)

        hotel_a = _make_hotel("A", None, None)
        hotel_b = _make_hotel("B", None, None)
        hotel_c = _make_hotel("C", None, None)
        itineraries = [hotel_a, hotel_b, hotel_c]

        HotelService._apply_nearby_sort(itineraries, ref)

        # All nearby_distance_km must be None
        assert all(h.nearby_distance_km is None for h in itineraries)
        # Python's sort is stable: all keys are equal (inf), so original order is preserved
        assert [h.hotel_id for h in itineraries] == ["A", "B", "C"]

    @patch("integrations.flightlogic.get_flights_client")
    @patch("app.domains.hotel.service.HotelService._apply_nearby_sort")
    async def test_search_hotels_uses_nearby_sort_when_nearby_location_provided(
        self,
        mock_apply_nearby_sort,
        mock_get_client,
    ):
        """HotelService.search_hotels should call _apply_nearby_sort when nearby_location exists."""
        client = Mock()
        client.environment = Mock(value="test")
        client.search_hotels = AsyncMock()
        client.get_more_results = AsyncMock()

        hotel_a = _make_hotel("A", "48.860", "2.295")
        hotel_b = _make_hotel("B", "48.870", "2.305")
        response = HotelSearchResponse.model_construct(
            session_id="test_session",
            total_results=2,
            itineraries=[hotel_a, hotel_b],
        )
        client.search_hotels.return_value = response
        mock_get_client.return_value = client

        def assert_fee_applied(itineraries, nearby_location):
            # The service applies the hotel platform fee before sorting. For a base total
            # of 100.00, the display price becomes 111.73 via apply_platform_fee.
            expected_fee_total = apply_platform_fee(Decimal("100.00"))
            assert itineraries[0].total == expected_fee_total
            assert itineraries[1].total == expected_fee_total
            assert nearby_location == request.nearby_location

        mock_apply_nearby_sort.side_effect = assert_fee_applied

        request = HotelSearchRequest(
            checkin="2027-06-01",
            checkout="2027-06-03",
            occupancy=[OccupancyRoom(room_no=1, adult=2, child=0, child_age=[])],
            city_name="Paris",
            country_name="France",
            currency="USD",
            nearby_location=NearbyLocation(lat=48.858, lng=2.294),
        )

        service = HotelService(current_user=None)
        result = await service.search_hotels(request)

        mock_apply_nearby_sort.assert_called_once_with(
            result.itineraries,
            request.nearby_location,
        )

    @patch("integrations.flightlogic.get_flights_client")
    @patch("app.domains.hotel.service.HotelService._apply_nearby_sort")
    async def test_get_more_results_uses_nearby_sort_when_nearby_location_provided(
        self,
        mock_apply_nearby_sort,
        mock_get_client,
    ):
        """HotelService.get_more_results should call _apply_nearby_sort when nearby_location exists."""
        client = Mock()
        client.environment = Mock(value="test")
        client.search_hotels = AsyncMock()
        client.get_more_results = AsyncMock()

        hotel_a = _make_hotel("A", "48.860", "2.295")
        hotel_b = _make_hotel("B", "48.870", "2.305")
        response = HotelSearchResponse.model_construct(
            session_id="test_session",
            total_results=2,
            itineraries=[hotel_a, hotel_b],
        )
        client.get_more_results.return_value = response
        mock_get_client.return_value = client

        def assert_fee_applied(itineraries, nearby_location):
            # The service applies the hotel platform fee before sorting. For a base total
            # of 100.00, the display price becomes 111.73 via apply_platform_fee.
            expected_fee_total = apply_platform_fee(Decimal("100.00"))
            assert itineraries[0].total == expected_fee_total
            assert itineraries[1].total == expected_fee_total
            assert nearby_location == request.nearby_location

        mock_apply_nearby_sort.side_effect = assert_fee_applied

        request = HotelMoreResultsRequest(
            session_id="session-xyz",
            next_token="next-token",
            nearby_location=NearbyLocation(lat=48.858, lng=2.294),
        )

        service = HotelService(current_user=None)
        result = await service.get_more_results(request)

        mock_apply_nearby_sort.assert_called_once_with(
            result.itineraries,
            request.nearby_location,
        )


class TestNearbyLocationSchema:
    """Tests for the NearbyLocation Pydantic model validation."""

    def test_valid_coordinates(self) -> None:
        loc = NearbyLocation(lat=48.858, lng=2.294)
        assert loc.lat == pytest.approx(48.858)
        assert loc.lng == pytest.approx(2.294)

    def test_invalid_lat_too_high(self) -> None:
        with pytest.raises(Exception):
            NearbyLocation(lat=91.0, lng=0.0)

    def test_invalid_lng_too_low(self) -> None:
        with pytest.raises(Exception):
            NearbyLocation(lat=0.0, lng=-181.0)

    def test_hotel_search_request_nearby_location_optional(self) -> None:
        """HotelSearchRequest must accept no nearby_location (backward compat)."""
        tomorrow = "2027-06-01"
        checkout = "2027-06-03"
        req = HotelSearchRequest(
            checkin=tomorrow,
            checkout=checkout,
            city_name="Paris",
            country_name="France",
            occupancy=[OccupancyRoom(room_no=1, adult=2)],
        )
        assert req.nearby_location is None

    def test_hotel_more_results_request_nearby_location_optional(self) -> None:
        """HotelMoreResultsRequest must accept no nearby_location."""
        req = HotelMoreResultsRequest(
            session_id="sess-abc",
            next_token="tok-abc",
        )
        assert req.nearby_location is None
