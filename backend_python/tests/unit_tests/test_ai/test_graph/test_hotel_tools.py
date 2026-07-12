"""Unit tests for LangGraph hotel agent tools.

Tests the tool functions directly without invoking the full LangGraph agent.
"""

import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.common import utc_date


def _future_hotel_dates(offset_days: int = 30, stay_nights: int = 5) -> tuple[str, str]:
    """Return stable future hotel dates so tests do not drift over time."""
    checkin = utc_date() + timedelta(days=offset_days)
    checkout = checkin + timedelta(days=stay_nights)
    return checkin.isoformat(), checkout.isoformat()


async def _invoke_hotel_tool(tool: Any, args: dict[str, Any]) -> dict[str, Any]:
    """Invoke a ``response_format='content_and_artifact'`` tool and merge.

    Post #1034 the LLM-facing content (summary + instruction) and the
    frontend-facing artifact (session_id + hotels + summary) are split.
    Tests assert on the combined shape for convenience, so we invoke via a
    ToolCall (which returns a ``ToolMessage`` with both attributes), then
    merge artifact fields on top of content. On error paths the artifact is
    ``None`` — we just return the content.
    """
    tool_call = {"name": tool.name, "args": args, "id": "t1", "type": "tool_call"}
    msg = await tool.ainvoke(tool_call)
    content = msg.content
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            content = {"_raw": content}
    if not isinstance(content, dict):
        return {"_raw": content}
    merged: dict[str, Any] = dict(content)
    artifact = getattr(msg, "artifact", None)
    if isinstance(artifact, dict):
        for k, v in artifact.items():
            merged.setdefault(k, v)
    return merged


class TestResolveCityTool:
    """Tests for the resolve_city tool."""

    @pytest.mark.asyncio
    async def test_resolve_single_result(self) -> None:
        """Test resolving a city with single result."""
        from app.ai.graph.tools.city import resolve_city

        with patch("app.shared.geocoding.GeocodingService") as mock_service_class:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.city = "Paris"
            mock_result.country = "France"
            mock_result.country_code = "FR"
            mock_result.lat = 48.8566
            mock_result.lng = 2.3522
            mock_result.formatted_address = "Paris, France"

            mock_service.geocode_city = AsyncMock(return_value=[mock_result])
            mock_service_class.return_value = mock_service

            result = await resolve_city.ainvoke({"query": "Paris"})

            assert result["status"] == "resolved"
            assert result["city"] == "Paris"
            assert result["country"] == "France"
            assert result["country_code"] == "FR"

    @pytest.mark.asyncio
    async def test_resolve_needs_disambiguation(self) -> None:
        """Test disambiguation when multiple countries match."""
        from app.ai.graph.tools.city import resolve_city

        with patch("app.shared.geocoding.GeocodingService") as mock_service_class:
            mock_service = MagicMock()

            # Birmingham UK
            mock_uk = MagicMock()
            mock_uk.city = "Birmingham"
            mock_uk.country = "United Kingdom"
            mock_uk.country_code = "GB"
            mock_uk.formatted_address = "Birmingham, UK"

            # Birmingham USA
            mock_usa = MagicMock()
            mock_usa.city = "Birmingham"
            mock_usa.country = "United States"
            mock_usa.country_code = "US"
            mock_usa.formatted_address = "Birmingham, AL, USA"

            mock_service.geocode_city = AsyncMock(return_value=[mock_uk, mock_usa])
            mock_service_class.return_value = mock_service

            result = await resolve_city.ainvoke({"query": "Birmingham"})

            assert result["status"] == "needs_disambiguation"
            assert "instruction" in result
            assert len(result["options"]) == 2
            assert result["options"][0]["country"] == "United Kingdom"
            assert result["options"][1]["country"] == "United States"

    @pytest.mark.asyncio
    async def test_resolve_not_found(self) -> None:
        """Test when city is not found."""
        from app.ai.graph.tools.city import resolve_city

        with patch("app.shared.geocoding.GeocodingService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.geocode_city = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            result = await resolve_city.ainvoke({"query": "xyznotreal"})

            assert result["status"] == "not_found"
            assert "instruction" in result

    @pytest.mark.asyncio
    async def test_resolve_same_country_uses_first(self) -> None:
        """Test that multiple results in same country uses first."""
        from app.ai.graph.tools.city import resolve_city

        with patch("app.shared.geocoding.GeocodingService") as mock_service_class:
            mock_service = MagicMock()

            # Two London results (both UK)
            mock_london1 = MagicMock()
            mock_london1.city = "London"
            mock_london1.country = "United Kingdom"
            mock_london1.country_code = "GB"
            mock_london1.lat = 51.5074
            mock_london1.lng = -0.1278
            mock_london1.formatted_address = "London, UK"

            mock_london2 = MagicMock()
            mock_london2.city = "City of London"
            mock_london2.country = "United Kingdom"
            mock_london2.country_code = "GB"
            mock_london2.lat = 51.5155
            mock_london2.lng = -0.0922
            mock_london2.formatted_address = "City of London, UK"

            mock_service.geocode_city = AsyncMock(
                return_value=[mock_london1, mock_london2]
            )
            mock_service_class.return_value = mock_service

            result = await resolve_city.ainvoke({"query": "London"})

            # Should resolve to first result, not need disambiguation
            assert result["status"] == "resolved"
            assert result["city"] == "London"


class TestSearchHotelsTool:
    """Tests for the search_hotels tool."""

    @pytest.mark.asyncio
    async def test_search_invalid_date_format(self) -> None:
        """Test that invalid date format returns error."""
        from app.ai.graph.tools.hotels import search_hotels

        result = await search_hotels.ainvoke(
            {
                "city_name": "Paris",
                "country_name": "France",
                "checkin": "15-03-2026",  # Wrong format
                "checkout": "20-03-2026",
                "adults": 2,
            }
        )

        assert "error" in result
        assert "date" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_search_checkout_before_checkin(self) -> None:
        """Test that checkout before checkin returns error."""
        from app.ai.graph.tools.hotels import search_hotels

        result = await search_hotels.ainvoke(
            {
                "city_name": "Paris",
                "country_name": "France",
                "checkin": "2026-03-20",
                "checkout": "2026-03-15",  # Before checkin
                "adults": 2,
            }
        )

        assert "error" in result
        assert "after" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_search_success(self) -> None:
        """Test successful hotel search with mocked API."""
        from app.ai.graph.tools.hotels import search_hotels

        checkin, checkout = _future_hotel_dates()

        with patch(
            "integrations.flightlogic.client.FlightLogicClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()

            # Create mock hotel result
            mock_hotel = MagicMock()
            mock_hotel.hotel_id = "HTL123"
            mock_hotel.token_id = "TKN456"
            mock_hotel.product_id = "PRD789"
            mock_hotel.hotel_name = "Test Hotel Paris"
            mock_hotel.city = "Paris"
            mock_hotel.country = "France"
            mock_hotel.address = "123 Champs-Élysées"
            mock_hotel.locality = "8th Arrondissement"
            mock_hotel.hotel_rating = 4
            mock_hotel.trip_advisor_rating = 4
            mock_hotel.trip_advisor_review = 500
            mock_hotel.total = Decimal("250.00")
            mock_hotel.currency = "EUR"
            mock_hotel.fare_type = "Refundable"
            mock_hotel.facilities = ["WiFi", "Pool", "Gym"]
            mock_hotel.property_type = "Hotel"
            mock_hotel.thumbnail_url = "https://example.com/hotel.jpg"
            mock_hotel.latitude = "48.8566"
            mock_hotel.longitude = "2.3522"
            mock_hotel.distance_value = 1.5
            mock_hotel.distance_unit = "KM"
            mock_hotel.get_nights.return_value = 5

            mock_response.itineraries = [mock_hotel]
            mock_response.session_id = "SESSION123"

            mock_client.search_hotels = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _invoke_hotel_tool(
                search_hotels,
                {
                    "city_name": "Paris",
                    "country_name": "France",
                    "checkin": checkin,
                    "checkout": checkout,
                    "rooms": 1,
                    "adults": 2,
                },
            )

            # Issue #1034: session_id + hotels come from the artifact (the LLM
            # never sees them); content only has status/summary/instruction.
            assert result["status"] == "success"
            assert result["session_id"] == "SESSION123"
            assert "summary" in result
            assert result["summary"]["total_found"] >= 1
            # Flat best-value-sorted list — no categories.
            assert "hotels" in result
            first = result["hotels"][0]
            assert first["latitude"] == "48.8566"
            assert first["longitude"] == "2.3522"

    @pytest.mark.asyncio
    async def test_search_no_results(self) -> None:
        """Test search with no results."""
        from app.ai.graph.tools.hotels import search_hotels

        checkin, checkout = _future_hotel_dates()

        with patch(
            "integrations.flightlogic.client.FlightLogicClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.itineraries = []
            mock_response.session_id = "SESSION123"

            mock_client.search_hotels = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await search_hotels.ainvoke(
                {
                    "city_name": "Nowhereville",
                    "country_name": "Atlantis",
                    "checkin": checkin,
                    "checkout": checkout,
                    "adults": 2,
                }
            )

            assert result["status"] == "no_results"
            assert "suggestion" in result

    @pytest.mark.asyncio
    async def test_search_returns_full_flat_list_no_truncation(self) -> None:
        """Issue #1034: no more BEST_VALUE_POOL_SIZE / DISPLAY_TOP_N caps.

        The tool ships the full best-value-sorted hotel list to the frontend
        via the artifact. With 25 hotels mocked we expect 25 back (sort order
        is governed by ``sort_hotels_by_best_value`` and not asserted here).
        """
        from app.ai.graph.tools.hotels import search_hotels

        checkin, checkout = _future_hotel_dates()

        def make_hotel(hid: str, total: float, rating: float) -> MagicMock:
            m = MagicMock()
            m.hotel_id = hid
            m.token_id = f"TKN{hid}"
            m.product_id = f"PRD{hid}"
            m.hotel_name = f"Hotel {hid}"
            m.city = "Paris"
            m.country = "France"
            m.address = ""
            m.locality = ""
            m.hotel_rating = rating
            m.trip_advisor_rating = rating
            m.trip_advisor_review = 100
            m.total = Decimal(str(total))
            m.currency = "EUR"
            m.fare_type = "Refundable"
            m.facilities = []
            m.property_type = "Hotel"
            m.thumbnail_url = "https://example.com/h.jpg"
            m.distance_value = 1.0
            m.distance_unit = "KM"
            m.get_nights.return_value = 1
            return m

        # 25 hotels with varying price and rating
        itineraries = [
            make_hotel(f"H{i}", 100.0 + i * 10, 3.0 + (i % 5) * 0.5) for i in range(25)
        ]
        mock_response = MagicMock()
        mock_response.itineraries = itineraries
        mock_response.session_id = "SESSION123"

        with patch(
            "integrations.flightlogic.client.FlightLogicClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.search_hotels = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _invoke_hotel_tool(
                search_hotels,
                {
                    "city_name": "Paris",
                    "country_name": "France",
                    "checkin": checkin,
                    "checkout": checkout,
                    "adults": 2,
                },
            )

        assert result["status"] == "success"
        # Flat list — full set, no truncation.
        assert "hotels" in result
        assert len(result["hotels"]) == 25
        # No legacy `categories` field on content or artifact.
        assert "categories" not in result
        # Summary count matches the unfiltered list.
        assert result["summary"]["total_found"] == 25


class TestSearchHotelsTimezoneRetry:
    """Tests for the same-day checkin timezone retry logic in search_hotels."""

    def _make_mock_hotel(self) -> MagicMock:
        """Return a minimal valid mock hotel itinerary."""
        m = MagicMock()
        m.hotel_id = "HTL1"
        m.token_id = "TKN1"
        m.product_id = "PRD1"
        m.hotel_name = "Retry Hotel"
        m.city = "Tokyo"
        m.country = "Japan"
        m.address = "1 Shinjuku"
        m.locality = "Shinjuku"
        m.hotel_rating = 4
        m.trip_advisor_rating = 4
        m.trip_advisor_review = 100
        m.total = Decimal("300.00")
        m.currency = "JPY"
        m.fare_type = "Refundable"
        m.facilities = ["WiFi"]
        m.property_type = "Hotel"
        m.thumbnail_url = "https://example.com/hotel.jpg"
        m.distance_value = 1.0
        m.distance_unit = "KM"
        m.get_nights.return_value = 1
        return m

    @pytest.mark.asyncio
    async def test_past_date_error_triggers_retry_and_succeeds(self) -> None:
        """Same-day checkin rejected with 'in the past' error → retried with +1 day and succeeds."""
        from app.ai.graph.tools.hotels import search_hotels
        from app.domains.hotel.exceptions import HotelSearchError

        today = date(2030, 6, 15)

        mock_hotel = self._make_mock_hotel()
        retry_response = MagicMock()
        retry_response.itineraries = [mock_hotel]
        retry_response.session_id = "RETRY_SESSION"

        with (
            patch("app.domains.common.utc_date", return_value=today),
            patch(
                "integrations.flightlogic.client.FlightLogicClient"
            ) as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.search_hotels = AsyncMock(
                side_effect=[
                    HotelSearchError("Check-in date is in the past"),
                    retry_response,
                ]
            )
            mock_client_class.return_value = mock_client

            result = await _invoke_hotel_tool(
                search_hotels,
                {
                    "city_name": "Tokyo",
                    "country_name": "Japan",
                    "checkin": today.isoformat(),
                    "checkout": "2030-06-16",
                    "adults": 2,
                },
            )

        assert result["status"] == "success"
        assert result["session_id"] == "RETRY_SESSION"
        # Retry bumps dates by 1 day → 1 night stay
        assert result["summary"]["nights"] == 1

    @pytest.mark.asyncio
    async def test_past_date_error_retry_returns_no_results(self) -> None:
        """Same-day retry succeeds API call but returns no hotels → no_results."""
        from app.ai.graph.tools.hotels import search_hotels
        from app.domains.hotel.exceptions import HotelSearchError

        today = date(2030, 6, 15)

        retry_response = MagicMock()
        retry_response.itineraries = []
        retry_response.session_id = "RETRY_SESSION"

        with (
            patch("app.domains.common.utc_date", return_value=today),
            patch(
                "integrations.flightlogic.client.FlightLogicClient"
            ) as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.search_hotels = AsyncMock(
                side_effect=[
                    HotelSearchError("Check-in date is in the past"),
                    retry_response,
                ]
            )
            mock_client_class.return_value = mock_client

            result = await search_hotels.ainvoke(
                {
                    "city_name": "Tokyo",
                    "country_name": "Japan",
                    "checkin": today.isoformat(),
                    "checkout": "2030-06-16",
                    "adults": 2,
                }
            )

        assert result["status"] == "no_results"

    @pytest.mark.asyncio
    async def test_non_same_day_past_date_error_does_not_retry(self) -> None:
        """'In the past' error for a future checkin (not same-day) falls through to error response."""
        from app.ai.graph.tools.hotels import search_hotels
        from app.domains.hotel.exceptions import HotelSearchError

        today = date(2030, 6, 15)

        with (
            patch("app.domains.common.utc_date", return_value=today),
            patch(
                "integrations.flightlogic.client.FlightLogicClient"
            ) as mock_client_class,
            patch(
                "app.ai.utils.error_message_generator.generate_error_message",
                new_callable=AsyncMock,
                return_value="Hotel search error",
            ),
        ):
            mock_client = MagicMock()
            mock_client.search_hotels = AsyncMock(
                side_effect=HotelSearchError("Check-in date is in the past")
            )
            mock_client_class.return_value = mock_client

            result = await search_hotels.ainvoke(
                {
                    "city_name": "Tokyo",
                    "country_name": "Japan",
                    "checkin": "2030-06-20",  # Not same-day; no retry
                    "checkout": "2030-06-21",
                    "adults": 2,
                }
            )

        # Should NOT retry — error returned directly
        assert result["status"] == "error"
        assert mock_client.search_hotels.call_count == 1


class TestHotelState:
    """Tests for HotelState TypedDict."""

    def test_hotel_state_structure(self) -> None:
        """Test that HotelState has correct structure."""
        from app.ai.graph.state import HotelParams, HotelState

        # Verify HotelParams fields
        params: HotelParams = {
            "city": "Paris",
            "country": "France",
            "checkin": "2025-12-25",
            "checkout": "2025-12-30",
        }
        assert params["city"] == "Paris"

        # HotelState should be a TypedDict (just verify import works)
        assert HotelState is not None
        assert HotelParams is not None


class TestHaversineKm:
    """Tests for the shared haversine_km utility."""

    def test_same_point_is_zero(self) -> None:
        """Distance from a point to itself is 0."""
        from app.shared.geo import haversine_km

        assert haversine_km(51.5, -0.1, 51.5, -0.1) == pytest.approx(0.0, abs=1e-6)

    def test_london_to_paris(self) -> None:
        """London (51.5074°N, 0.1278°W) to Paris (48.8566°N, 2.3522°E) ≈ 340 km."""
        from app.shared.geo import haversine_km

        dist = haversine_km(51.5074, -0.1278, 48.8566, 2.3522)
        assert 330 < dist < 350

    def test_symmetry(self) -> None:
        """Distance A→B equals distance B→A."""
        from app.shared.geo import haversine_km

        d1 = haversine_km(48.8566, 2.3522, 52.3676, 4.9041)
        d2 = haversine_km(52.3676, 4.9041, 48.8566, 2.3522)
        assert d1 == pytest.approx(d2, rel=1e-9)


class TestProximityFilter:
    """Tests for _proximity_filter in hotels.py."""

    @pytest.mark.asyncio
    async def test_returns_hotels_within_radius(self) -> None:
        """Hotels within the geocoded radius are returned."""
        from app.ai.graph.tools.hotels import _proximity_filter

        hotels = [
            {
                "name": "Near Hotel",
                "latitude": 48.858,
                "longitude": 2.294,
            },  # ~0.4 km from target
            {"name": "Far Hotel", "latitude": 48.900, "longitude": 2.400},  # ~6 km away
        ]

        mock_result = MagicMock()
        mock_result.lat = 48.8584
        mock_result.lng = 2.2945

        with patch("app.shared.geocoding.GeocodingService") as mock_cls:
            mock_geo = MagicMock()
            mock_geo.geocode_city = AsyncMock(return_value=[mock_result])
            mock_cls.return_value = mock_geo

            with patch("app.ai.graph.tools.hotels.GeocodingService", mock_cls):
                result = await _proximity_filter(
                    hotels, "Eiffel Tower", "Paris", radius_km=3.0
                )

        assert len(result) == 1
        assert result[0]["name"] == "Near Hotel"

    @pytest.mark.asyncio
    async def test_geocoding_failure_returns_empty(self) -> None:
        """When geocoding raises an exception, returns empty list gracefully."""
        from app.ai.graph.tools.hotels import _proximity_filter

        hotels = [{"name": "Some Hotel", "latitude": 48.858, "longitude": 2.294}]

        with patch("app.ai.graph.tools.hotels.GeocodingService") as mock_cls:
            mock_geo = MagicMock()
            mock_geo.geocode_city = AsyncMock(side_effect=Exception("geocoding error"))
            mock_cls.return_value = mock_geo

            result = await _proximity_filter(hotels, "Unknown Place", "Paris")

        assert result == []

    @pytest.mark.asyncio
    async def test_hotels_without_coordinates_are_skipped(self) -> None:
        """Hotels missing lat/lng are silently skipped."""
        from app.ai.graph.tools.hotels import _proximity_filter

        hotels = [
            {"name": "No Coords Hotel"},
            {"name": "Partial Hotel", "latitude": 48.858},
            {"name": "With Coords", "latitude": 48.858, "longitude": 2.294},
        ]

        mock_result = MagicMock()
        mock_result.lat = 48.858
        mock_result.lng = 2.294

        with patch("app.ai.graph.tools.hotels.GeocodingService") as mock_cls:
            mock_geo = MagicMock()
            mock_geo.geocode_city = AsyncMock(return_value=[mock_result])
            mock_cls.return_value = mock_geo

            result = await _proximity_filter(
                hotels, "Eiffel Tower", "Paris", radius_km=3.0
            )

        assert len(result) == 1
        assert result[0]["name"] == "With Coords"

    @pytest.mark.asyncio
    async def test_geocode_no_results_returns_empty(self) -> None:
        """When geocode returns empty list, returns empty list."""
        from app.ai.graph.tools.hotels import _proximity_filter

        with patch("app.ai.graph.tools.hotels.GeocodingService") as mock_cls:
            mock_geo = MagicMock()
            mock_geo.geocode_city = AsyncMock(return_value=[])
            mock_cls.return_value = mock_geo

            result = await _proximity_filter([{"name": "Hotel"}], "Nowhere", "Paris")

        assert result == []


class TestNearbyLocation:
    """Tests for nearby_lat/nearby_lng proximity sorting in search_hotels."""

    def _make_mock_hotel(self, nearby_distance_km: float | None = None) -> MagicMock:
        m = MagicMock()
        m.hotel_id = "HTL1"
        m.token_id = "TKN1"
        m.product_id = "PRD1"
        m.hotel_name = "Nearby Hotel"
        m.city = "Orlando"
        m.country = "United States"
        m.address = "1 Disney Way"
        m.locality = ""
        m.hotel_rating = 4
        m.trip_advisor_rating = 4
        m.trip_advisor_review = 200
        m.total = Decimal("200.00")
        m.currency = "USD"
        m.fare_type = "Refundable"
        m.facilities = ["WiFi"]
        m.property_type = "Hotel"
        m.thumbnail_url = "https://example.com/h.jpg"
        m.latitude = "28.385"
        m.longitude = "-81.564"
        m.distance_value = 5.0
        m.distance_unit = "KM"
        m.get_nights.return_value = 3
        m.nearby_distance_km = nearby_distance_km
        return m

    @pytest.mark.asyncio
    async def test_nearby_coords_set_on_request(self) -> None:
        """When nearby_lat/nearby_lng are provided, NearbyLocation is set on the request."""
        from app.ai.graph.tools.hotels import search_hotels

        checkin, checkout = _future_hotel_dates()

        with patch(
            "integrations.flightlogic.client.FlightLogicClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.itineraries = [self._make_mock_hotel(1.2)]
            mock_response.session_id = "SESSION_NEARBY"

            mock_client.search_hotels = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            await search_hotels.ainvoke(
                {
                    "city_name": "Orlando",
                    "country_name": "United States",
                    "checkin": checkin,
                    "checkout": checkout,
                    "adults": 2,
                    "nearby_lat": 28.385,
                    "nearby_lng": -81.564,
                }
            )

            # Verify the request passed to FlightLogic has nearby_location set
            call_args = mock_client.search_hotels.call_args
            request = call_args[0][0]
            assert request.nearby_location is not None
            assert request.nearby_location.lat == pytest.approx(28.385)
            assert request.nearby_location.lng == pytest.approx(-81.564)

    @pytest.mark.asyncio
    async def test_no_nearby_coords_means_no_nearby_location(self) -> None:
        """When nearby_lat/nearby_lng are not provided, nearby_location is None."""
        from app.ai.graph.tools.hotels import search_hotels

        checkin, checkout = _future_hotel_dates()

        with patch(
            "integrations.flightlogic.client.FlightLogicClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.itineraries = [self._make_mock_hotel()]
            mock_response.session_id = "SESSION_NONE"

            mock_client.search_hotels = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            await search_hotels.ainvoke(
                {
                    "city_name": "Orlando",
                    "country_name": "United States",
                    "checkin": checkin,
                    "checkout": checkout,
                    "adults": 2,
                }
            )

            call_args = mock_client.search_hotels.call_args
            request = call_args[0][0]
            assert request.nearby_location is None

    @pytest.mark.asyncio
    async def test_partial_nearby_coords_ignored(self) -> None:
        """Only nearby_lat without nearby_lng → nearby_location is None."""
        from app.ai.graph.tools.hotels import search_hotels

        checkin, checkout = _future_hotel_dates()

        with patch(
            "integrations.flightlogic.client.FlightLogicClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.itineraries = [self._make_mock_hotel()]
            mock_response.session_id = "SESSION_PARTIAL"

            mock_client.search_hotels = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            await search_hotels.ainvoke(
                {
                    "city_name": "Orlando",
                    "country_name": "United States",
                    "checkin": checkin,
                    "checkout": checkout,
                    "adults": 2,
                    "nearby_lat": 28.385,
                    # nearby_lng not provided
                }
            )

            call_args = mock_client.search_hotels.call_args
            request = call_args[0][0]
            assert request.nearby_location is None

    @pytest.mark.asyncio
    async def test_nearby_distance_km_in_hotel_info(self) -> None:
        """nearby_distance_km is passed through _extract_hotel_info."""
        from app.ai.graph.tools.hotels import search_hotels

        checkin, checkout = _future_hotel_dates()

        with patch(
            "integrations.flightlogic.client.FlightLogicClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.itineraries = [self._make_mock_hotel(0.8)]
            mock_response.session_id = "SESSION_DIST"

            mock_client.search_hotels = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _invoke_hotel_tool(
                search_hotels,
                {
                    "city_name": "Orlando",
                    "country_name": "United States",
                    "checkin": checkin,
                    "checkout": checkout,
                    "adults": 2,
                    "nearby_lat": 28.385,
                    "nearby_lng": -81.564,
                },
            )

            assert result["status"] == "success"
            hotel = result["hotels"][0]
            assert hotel["nearby_distance_km"] == 0.8

    @pytest.mark.asyncio
    async def test_nearby_distance_km_none_without_coords(self) -> None:
        """nearby_distance_km is None when no nearby_location was provided."""
        from app.ai.graph.tools.hotels import search_hotels

        checkin, checkout = _future_hotel_dates()

        with patch(
            "integrations.flightlogic.client.FlightLogicClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.itineraries = [self._make_mock_hotel(None)]
            mock_response.session_id = "SESSION_NO_DIST"

            mock_client.search_hotels = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _invoke_hotel_tool(
                search_hotels,
                {
                    "city_name": "Orlando",
                    "country_name": "United States",
                    "checkin": checkin,
                    "checkout": checkout,
                    "adults": 2,
                },
            )

            assert result["status"] == "success"
            hotel = result["hotels"][0]
            assert hotel["nearby_distance_km"] is None


class TestExtractCollectedParamsNearby:
    """Tests for nearby_lat/nearby_lng extraction in _extract_collected_hotel_params."""

    def test_extracts_nearby_coords_from_search_tool_call(self) -> None:
        """nearby_lat/nearby_lng are extracted from search_hotels tool call args."""
        from langchain_core.messages import AIMessage

        from app.ai.graph.hotel_graph import _extract_collected_hotel_params

        msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Orlando",
                        "country_name": "United States",
                        "checkin": "2026-06-01",
                        "checkout": "2026-06-04",
                        "adults": 2,
                        "nearby_lat": 28.385,
                        "nearby_lng": -81.564,
                    },
                    "id": "call_1",
                }
            ],
        )

        params = _extract_collected_hotel_params([msg])
        assert params["nearby_lat"] == 28.385
        assert params["nearby_lng"] == -81.564
        assert params["city"] == "Orlando"

    def test_no_nearby_coords_when_absent(self) -> None:
        """When search_hotels call has no nearby params, they are absent from result."""
        from langchain_core.messages import AIMessage

        from app.ai.graph.hotel_graph import _extract_collected_hotel_params

        msg = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_hotels",
                    "args": {
                        "city_name": "Paris",
                        "country_name": "France",
                        "checkin": "2026-06-01",
                        "checkout": "2026-06-04",
                        "adults": 2,
                    },
                    "id": "call_1",
                }
            ],
        )

        params = _extract_collected_hotel_params([msg])
        assert "nearby_lat" not in params
        assert "nearby_lng" not in params


class TestHotelGraphModule:
    """Tests for the hotel graph module."""

    def test_prompt_exports(self) -> None:
        """Test that prompt module exports hotel system prompt."""
        from app.ai.graph.prompts import HOTEL_SYSTEM_PROMPT

        assert isinstance(HOTEL_SYSTEM_PROMPT, str)
        assert "Voya" in HOTEL_SYSTEM_PROMPT
        assert "hotel" in HOTEL_SYSTEM_PROMPT.lower()
