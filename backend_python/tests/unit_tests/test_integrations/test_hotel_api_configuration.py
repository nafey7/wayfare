"""Tests for hotel API endpoint configuration.

These tests validate that:
1. Hotel searches use correct endpoint (/hotel-api-v6/hotel_search not /aeroVE5)
2. Credentials are properly injected into requests
3. Environment variable fallbacks work correctly
4. FlightLogicClient initialization uses correct URLs

REGRESSION: Catches the 404 error bug where hotel_base_url pointed to flight endpoint.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.hotel.schemas import (
    HotelCancelRequest,
    HotelCancelResponse,
    HotelMoreResultsRequest,
    HotelSearchRequest,
    HotelSearchResponse,
    OccupancyRoom,
)
from integrations.flightlogic.client import FlightLogicClient
from integrations.flightlogic.hotel_dto import (
    HotelItineraryDTO,
    HotelSearchResponseDTO,
)


def _future_date(days: int = 7) -> str:
    """Generate a future date string in YYYY-MM-DD format."""
    return (datetime.now().date() + timedelta(days=days)).isoformat()


@pytest.fixture
def mock_settings():
    """Mock settings with test credentials."""
    settings = MagicMock()
    settings.FLIGHTLOGIC_FLIGHTS_API_BASE_URL = "https://travelnext.works/api/aeroVE5"
    settings.FLIGHTLOGIC_HOTELS_API_BASE_URL = (
        "https://travelnext.works/api/hotel-api-v6"
    )
    settings.FLIGHTLOGIC_API_KEY = "test_key"  # pragma: allowlist secret
    settings.FLIGHTLOGIC_USER_ID = "test_user"  # pragma: allowlist secret
    settings.FLIGHTLOGIC_PASSWORD = (
        "test_pass"  # pragma: allowlist secret  # pragma: allowlist secret
    )
    settings.FLIGHTLOGIC_IP_ADDRESS = "192.168.1.1"
    settings.FLIGHTLOGIC_ACCESS_TYPE = "Test"
    settings.FLIGHTLOGIC_API_URL = None  # Deprecated field not set
    return settings


@pytest.fixture
def mock_settings_with_deprecated_url():
    """Mock settings using deprecated FLIGHTLOGIC_API_URL."""
    settings = MagicMock()
    settings.FLIGHTLOGIC_API_URL = "https://travelnext.works/api/aeroVE5"
    settings.FLIGHTLOGIC_FLIGHTS_API_BASE_URL = None  # Not set
    settings.FLIGHTLOGIC_HOTELS_API_BASE_URL = (
        "https://travelnext.works/api/hotel-api-v6"
    )
    settings.FLIGHTLOGIC_API_KEY = "test_key"  # pragma: allowlist secret
    settings.FLIGHTLOGIC_USER_ID = "test_user"  # pragma: allowlist secret
    settings.FLIGHTLOGIC_PASSWORD = (
        "test_pass"  # pragma: allowlist secret  # pragma: allowlist secret
    )
    settings.FLIGHTLOGIC_IP_ADDRESS = "192.168.1.1"
    settings.FLIGHTLOGIC_ACCESS_TYPE = "Test"
    return settings


class TestFlightLogicClientInitialization:
    """Tests for FlightLogicClient URL configuration on initialization."""

    def test_uses_separate_urls_when_both_set(self, mock_settings):
        """Client should use separate URLs when both FLIGHTS and HOTELS vars are set."""
        with patch("integrations.flightlogic.client.settings", mock_settings):
            client = FlightLogicClient()

        assert client.base_url == "https://travelnext.works/api/aeroVE5"
        assert client.hotel_base_url == "https://travelnext.works/api/hotel-api-v6"

    def test_falls_back_to_deprecated_url_for_flights(
        self, mock_settings_with_deprecated_url
    ):
        """Client should fall back to deprecated FLIGHTLOGIC_API_URL for flights if new var not set."""
        with patch(
            "integrations.flightlogic.client.settings",
            mock_settings_with_deprecated_url,
        ):
            client = FlightLogicClient()

        # Flight URL should fall back to deprecated setting
        assert client.base_url == "https://travelnext.works/api/aeroVE5"
        # Hotel URL should use specific setting
        assert client.hotel_base_url == "https://travelnext.works/api/hotel-api-v6"

    def test_uses_hardcoded_defaults_when_no_urls_set(self):
        """Client should use hardcoded defaults when no environment variables set."""
        settings = MagicMock()
        settings.FLIGHTLOGIC_API_URL = None
        settings.FLIGHTLOGIC_FLIGHTS_API_BASE_URL = None
        settings.FLIGHTLOGIC_HOTELS_API_BASE_URL = (
            "https://travelnext.works/api/hotel-api-v6"
        )
        settings.FLIGHTLOGIC_API_KEY = "test_key"  # pragma: allowlist secret
        settings.FLIGHTLOGIC_USER_ID = "test_user"  # pragma: allowlist secret
        settings.FLIGHTLOGIC_PASSWORD = "test_pass"  # pragma: allowlist secret
        settings.FLIGHTLOGIC_IP_ADDRESS = "192.168.1.1"
        settings.FLIGHTLOGIC_ACCESS_TYPE = "Test"

        with patch("integrations.flightlogic.client.settings", settings):
            client = FlightLogicClient()

        # Should fall back to hardcoded default
        assert client.base_url == "https://travelnext.works/api/aeroVE5"
        assert client.hotel_base_url == "https://travelnext.works/api/hotel-api-v6"


class TestHotelSearchEndpointConfiguration:
    """Tests that hotel_search uses the correct API endpoint.

    REGRESSION: This would have caught the 404 error where hotel searches
    were incorrectly calling /aeroVE5/hotel_search instead of /hotel-api-v6/hotel_search.
    """

    @pytest.mark.asyncio
    async def test_hotel_search_uses_correct_endpoint(self, mock_settings):
        """Hotel search should call /hotel-api-v6/hotel_search, NOT /aeroVE5/hotel_search."""
        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": {
                "sessionId": "test_session",
                "moreResults": False,
                "nextToken": "",
                "totalResults": 0,
            },
            "itineraries": [],
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch("integrations.flightlogic.client.settings", mock_settings),
            patch("app.core.config.settings", mock_settings),
            patch("integrations.flightlogic.client.httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            client = FlightLogicClient()

            request = HotelSearchRequest(
                checkin=_future_date(7),
                checkout=_future_date(11),
                city_name="London",
                country_name="UK",
                occupancy=[OccupancyRoom(room_no=1, adult=2, child=0)],
            )

            response = await client.search_hotels(request)

        # Verify correct endpoint was called
        assert isinstance(response, HotelSearchResponse)
        mock_client.return_value.__aenter__.return_value.post.assert_called_once()
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        url_called = str(call_args[0][0])  # First positional argument is the URL
        assert url_called == "https://travelnext.works/api/hotel-api-v6/hotel_search"
        # Verify NOT the flight endpoint
        assert "/aeroVE5/" not in url_called

    @pytest.mark.asyncio
    async def test_hotel_search_raises_clear_error_on_404(self, mock_settings):
        """If 404 occurs, error should clearly indicate wrong endpoint was used."""
        # Simulate 404 error
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=Exception("Client error '404 Not Found'")
        )

        with (
            patch("integrations.flightlogic.client.settings", mock_settings),
            patch("app.core.config.settings", mock_settings),
            patch("integrations.flightlogic.client.httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            client = FlightLogicClient()

            request = HotelSearchRequest(
                checkin=_future_date(7),
                checkout=_future_date(11),
                city_name="London",
                country_name="UK",
                occupancy=[OccupancyRoom(room_no=1, adult=2, child=0)],
            )

            with pytest.raises(Exception) as exc_info:
                await client.search_hotels(request)

        # Error should mention 404 status
        error_msg = str(exc_info.value).lower()
        assert "404" in error_msg or "not found" in error_msg


class TestCredentialInjection:
    """Tests that credentials are properly injected into hotel API requests."""

    @pytest.mark.asyncio
    async def test_hotel_search_includes_credentials_in_request(self, mock_settings):
        """Hotel search request should include user_id, password, access, ip_address."""
        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": {
                "sessionId": "test_session",
                "moreResults": False,
                "nextToken": "",
                "totalResults": 0,
            },
            "itineraries": [],
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch("integrations.flightlogic.client.settings", mock_settings),
            patch("app.core.config.settings", mock_settings),
            patch("integrations.flightlogic.client.httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            client = FlightLogicClient()

            request = HotelSearchRequest(
                checkin=_future_date(7),
                checkout=_future_date(11),
                city_name="London",
                country_name="UK",
                occupancy=[OccupancyRoom(room_no=1, adult=2, child=0)],
            )

            await client.search_hotels(request)

        # Verify request body included credentials (from settings)
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        import json

        body_bytes = call_args.kwargs.get("json") or json.loads(
            call_args.kwargs["content"]
        )

        assert body_bytes["user_id"] == "test_user"
        assert body_bytes["user_password"] == "test_pass"  # pragma: allowlist secret
        assert body_bytes["access"] == "Test"
        assert body_bytes["ip_address"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_hotel_search_uses_credentials_from_settings(self, mock_settings):
        """Credentials should be loaded from settings if not in request DTO."""
        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": {
                "sessionId": "test_session",
                "moreResults": False,
                "nextToken": "",
                "totalResults": 0,
            },
            "itineraries": [],
        }
        mock_response.raise_for_status = MagicMock()

        # Override settings to verify they're used
        mock_settings.FLIGHTLOGIC_USER_ID = "settings_user"  # pragma: allowlist secret
        mock_settings.FLIGHTLOGIC_PASSWORD = "settings_pass"  # pragma: allowlist secret

        with (
            patch("integrations.flightlogic.client.settings", mock_settings),
            patch("app.core.config.settings", mock_settings),
            patch("integrations.flightlogic.client.httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            client = FlightLogicClient()

            # Credentials are automatically injected from settings by the adapter
            request = HotelSearchRequest(
                checkin=_future_date(7),
                checkout=_future_date(11),
                city_name="London",
                country_name="UK",
                occupancy=[OccupancyRoom(room_no=1, adult=2, child=0)],
            )

            await client.search_hotels(request)

        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        import json

        body_bytes = call_args.kwargs.get("json") or json.loads(
            call_args.kwargs["content"]
        )

        assert body_bytes["user_id"] == "settings_user"
        expected_pass = "settings_pass"  # pragma: allowlist secret
        assert body_bytes["user_password"] == expected_pass


class TestRegressionBugs:
    """Tests that catch specific bugs encountered in production.

    These tests document actual bugs found during manual testing
    and ensure they never happen again.
    """

    def test_hotel_base_url_not_using_flight_endpoint(self, mock_settings):
        """REGRESSION: hotel_base_url was incorrectly using FLIGHTLOGIC_API_URL.

        Bug History:
        - November 18, 2025: Hotel searches returned 404 error
        - Root cause: hotel_base_url = settings.FLIGHTLOGIC_API_URL
        - This pointed to /aeroVE5 (flight endpoint), not /hotel-api-v6
        - Fix: Use settings.FLIGHTLOGIC_HOTELS_API_BASE_URL

        Error seen:
        Client error '404 Not Found' for url 'https://travelnext.works/api/aeroVE5/hotel_search'
        """
        with patch("integrations.flightlogic.client.settings", mock_settings):
            client = FlightLogicClient()

        # Hotel URL should NEVER contain /aeroVE5
        assert "/aeroVE5" not in client.hotel_base_url
        # Should use hotel-api-v6 endpoint
        assert "/hotel-api-v6" in client.hotel_base_url
        # Flight URL should still use aeroVE5
        assert "/aeroVE5" in client.base_url

    def test_separate_urls_prevents_endpoint_confusion(self, mock_settings):
        """Having separate FLIGHTS and HOTELS URLs prevents confusion.

        Before: FLIGHTLOGIC_API_URL used for both → 404 errors
        After: FLIGHTLOGIC_FLIGHTS_API_BASE_URL + FLIGHTLOGIC_HOTELS_API_BASE_URL
        """
        with patch("integrations.flightlogic.client.settings", mock_settings):
            client = FlightLogicClient()

        # Flight and hotel URLs must be different
        assert client.base_url != client.hotel_base_url
        # Each should use correct endpoint
        assert "aeroVE5" in client.base_url
        assert "hotel-api-v6" in client.hotel_base_url


# ============================================================================
# REAL API RESPONSE TESTS
# ============================================================================

# Real API response sample (from actual FlightLogic Hotel API)
REAL_API_RESPONSE = {
    "status": {
        "sessionId": "TVRjMk16TTJOekUzT1Y4eU16aGZNVGc0TGprd0xqRTJNeTR4T0RNPV8xMjE1NDA0",  # pragma: allowlist secret
        "moreResults": True,
        "nextToken": "MzAx",
        "totalResults": 664,
    },
    "itineraries": [
        {
            "hotelId": "844690",
            "twxHotelId": 844690,
            "productId": "trx109",
            "tokenId": "4CWqvMpmDxjnI17NThgt",
            "hotelName": "The Bank Hotel",
            "city": "BARKING",
            "locality": "",
            "distanceValue": 14.87,
            "distanceUnit": "KM",
            "country": "",
            "countryCode": "",
            "address": "1 Ripple Road",
            "latitude": "51.53806400000000000000",
            "longitude": "0.08011600000000000000",
            "hotelRating": 3,
            "total": "10668.59",
            "perNightArray": [
                {"nightIndex": 1, "currency": "INR", "price": "10668.59"}
            ],
            "currency": "INR",
            "fareType": "Non-Refundable",
            "propertyType": "",
            "postalCode": "IG11 7NP",
            "phone": "+4485943604",
            "email": "info@prijekopalace.com",
            "thumbNailUrl": "https://photos.hotelbeds.com/giata/original/84/844690/844690a_hb_a_001.jpg",
            "facilities": ["hotel", "American Express", "City centre"],
            "tripAdvisorRating": 0,
            "tripAdvisorReview": 0,
            "special": "",
        }
    ],
}


class TestRealAPIResponseParsing:
    """Test parsing of actual FlightLogic Hotel API responses.

    CRITICAL: These tests use real API response data to catch field naming issues.
    This would have caught the snake_case vs camelCase issue that unit tests missed.
    """

    def test_parse_real_api_response(self):
        """Test parsing complete API response with real data.

        This is the critical test that would have caught the snake_case vs camelCase issue.
        """
        # Should parse without ValidationError
        response = HotelSearchResponseDTO(**REAL_API_RESPONSE)

        # Verify correct parsing
        assert (
            response.status.sessionId
            == "TVRjMk16TTJOekUzT1Y4eU16aGZNVGc0TGprd0xqRTJNeTR4T0RNPV8xMjE1NDA0"  # pragma: allowlist secret
        )
        assert response.status.totalResults == 664
        assert len(response.itineraries) == 1

    def test_parse_hotel_with_per_night_array(self):
        """Test parsing hotel itinerary with per-night price breakdown."""
        hotel_data = REAL_API_RESPONSE["itineraries"][0]

        # Should parse without ValidationError
        hotel = HotelItineraryDTO(**hotel_data)

        # Verify field names match API (camelCase, not snake_case!)
        assert hotel.hotelId == "844690"
        assert hotel.hotelName == "The Bank Hotel"
        assert len(hotel.perNightArray) == 1

        # CRITICAL: Verify nightIndex (camelCase) is parsed correctly
        assert hotel.perNightArray[0].nightIndex == 1
        assert hotel.perNightArray[0].currency == "INR"
        assert hotel.perNightArray[0].price == "10668.59"

    def test_parse_multi_night_stay(self):
        """Test parsing hotel with multiple nights (10-night stay)."""
        hotel_data = REAL_API_RESPONSE["itineraries"][0].copy()

        # Simulate 10-night stay response
        hotel_data["perNightArray"] = [
            {"nightIndex": i, "currency": "USD", "price": "233.62"}
            for i in range(1, 11)
        ]

        # Should parse all nights without ValidationError
        hotel = HotelItineraryDTO(**hotel_data)

        assert len(hotel.perNightArray) == 10
        assert hotel.perNightArray[0].nightIndex == 1
        assert hotel.perNightArray[9].nightIndex == 10
        assert all(night.currency == "USD" for night in hotel.perNightArray)

    def test_parse_hotel_with_float_rating(self):
        """Test parsing hotel with float rating (API inconsistency)."""
        hotel_data = REAL_API_RESPONSE["itineraries"][0].copy()
        hotel_data["hotelRating"] = 4.5  # Float rating

        # Should accept float rating
        hotel = HotelItineraryDTO(**hotel_data)
        assert hotel.hotelRating == 4.5

    def test_parse_hotel_with_string_rating(self):
        """Test parsing hotel with string rating (API inconsistency)."""
        hotel_data = REAL_API_RESPONSE["itineraries"][0].copy()
        hotel_data["hotelRating"] = "5"  # String rating

        # Should accept string rating
        hotel = HotelItineraryDTO(**hotel_data)
        assert hotel.hotelRating == "5"


class TestDTOToDomainConversion:
    """Test complete flow: API Response → DTO → Domain Model.

    CRITICAL: This catches mismatches between DTO and domain model field names.
    Would have caught the nightIndex vs night_index issue.
    """

    def test_complete_conversion_flow(self):
        """Test API response → DTO → Domain conversion (end-to-end)."""
        from integrations.flightlogic.hotel_adapter import HotelSchemaAdapter

        # Real API response
        response = HotelSearchResponseDTO(**REAL_API_RESPONSE)

        # Convert to domain model using adapter
        adapter = HotelSchemaAdapter()
        domain_hotel = adapter._convert_hotel_itinerary(response.itineraries[0])

        # Verify domain model was created successfully
        assert domain_hotel.hotel_id == "844690"
        assert domain_hotel.hotel_name == "The Bank Hotel"
        assert len(domain_hotel.per_night_array) == 1

        # CRITICAL: Verify per-night array conversion
        assert domain_hotel.per_night_array[0].night_index == 1
        assert domain_hotel.per_night_array[0].currency == "INR"
        # Price should be converted to Decimal
        from decimal import Decimal

        assert isinstance(domain_hotel.per_night_array[0].price, Decimal)

    def test_multi_night_conversion(self):
        """Test conversion of multi-night stay (catches array iteration issues)."""
        from integrations.flightlogic.hotel_adapter import HotelSchemaAdapter

        # API response with 10 nights
        api_data = REAL_API_RESPONSE.copy()
        api_data["itineraries"][0]["perNightArray"] = [
            {"nightIndex": i, "currency": "USD", "price": "100.00"}
            for i in range(1, 11)
        ]

        response = HotelSearchResponseDTO(**api_data)
        adapter = HotelSchemaAdapter()
        domain_hotel = adapter._convert_hotel_itinerary(response.itineraries[0])

        # All nights should convert successfully
        assert len(domain_hotel.per_night_array) == 10
        for i, night in enumerate(domain_hotel.per_night_array, 1):
            assert night.night_index == i
            assert night.currency == "USD"


# ==============================================================================
# MORE RESULTS API TESTS
# ==============================================================================


class TestMoreResultsEndpointConfiguration:
    """Tests that moreResults uses the correct API endpoint and method."""

    @pytest.mark.asyncio
    async def test_more_results_uses_get_method(self, mock_settings):
        """More results should use GET method, not POST."""
        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": {
                "sessionId": "test_session",
                "moreResults": False,
                "nextToken": "",
            },
            "itineraries": [],
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch("integrations.flightlogic.client.settings", mock_settings),
            patch("app.core.config.settings", mock_settings),
            patch("integrations.flightlogic.client.httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            client = FlightLogicClient()

            request = HotelMoreResultsRequest(
                session_id="test_session",
                next_token="next_token_abc",
                max_result=20,
            )

            response = await client.get_more_results(request)

        # Verify GET method was called (not POST)
        assert isinstance(response, HotelSearchResponse)
        mock_client.return_value.__aenter__.return_value.get.assert_called_once()
        # Verify POST was NOT called
        if hasattr(mock_client.return_value.__aenter__.return_value, "post"):
            assert not mock_client.return_value.__aenter__.return_value.post.called

    @pytest.mark.asyncio
    async def test_more_results_uses_correct_endpoint(self, mock_settings):
        """More results should call /hotel-api-v6/moreResults."""
        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": {
                "sessionId": "test_session",
                "moreResults": False,
                "nextToken": "",
            },
            "itineraries": [],
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch("integrations.flightlogic.client.settings", mock_settings),
            patch("app.core.config.settings", mock_settings),
            patch("integrations.flightlogic.client.httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            client = FlightLogicClient()

            request = HotelMoreResultsRequest(
                session_id="test_session",
                next_token="next_token_abc",
                max_result=20,
            )

            await client.get_more_results(request)

        # Verify correct endpoint was called
        call_args = mock_client.return_value.__aenter__.return_value.get.call_args
        url_called = str(call_args[0][0])  # First positional argument is the URL
        assert url_called == "https://travelnext.works/api/hotel-api-v6/moreResults"
        # Verify NOT the flight endpoint
        assert "/aeroVE5/" not in url_called

    @pytest.mark.asyncio
    async def test_more_results_includes_query_parameters(self, mock_settings):
        """More results should include sessionId, nextToken, maxResult as query params."""
        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": {
                "sessionId": "test_session",
                "moreResults": False,
                "nextToken": "",
            },
            "itineraries": [],
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch("integrations.flightlogic.client.settings", mock_settings),
            patch("app.core.config.settings", mock_settings),
            patch("integrations.flightlogic.client.httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            client = FlightLogicClient()

            request = HotelMoreResultsRequest(
                session_id="test_session_12345",
                next_token="next_token_abc123",
                max_result=50,
            )

            await client.get_more_results(request)

        # Verify query parameters were included
        call_args = mock_client.return_value.__aenter__.return_value.get.call_args
        params = call_args.kwargs.get("params", {})
        assert params["sessionId"] == "test_session_12345"
        assert params["nextToken"] == "next_token_abc123"
        assert params["maxResult"] == 50


# ==============================================================================
# CANCEL BOOKING API TESTS
# ==============================================================================


class TestCancelBookingEndpointConfiguration:
    """Tests that cancel uses the correct API endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_booking_uses_correct_endpoint(self, mock_settings):
        """Cancel should call /hotel-api-v6/cancel."""
        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "CANCELLED",
            "cancelReferenceNum": "CANCEL123456",
            "message": "Booking cancelled successfully",
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch("integrations.flightlogic.client.settings", mock_settings),
            patch("app.core.config.settings", mock_settings),
            patch("integrations.flightlogic.client.httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            client = FlightLogicClient()

            request = HotelCancelRequest(
                supplier_confirmation_num="SUP123456",
                reference_num="REF789012",
            )

            response = await client.cancel_hotel_booking(request)

        # Verify correct endpoint was called
        assert isinstance(response, HotelCancelResponse)
        mock_client.return_value.__aenter__.return_value.post.assert_called_once()
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        url_called = str(call_args[0][0])  # First positional argument is the URL
        assert url_called == "https://travelnext.works/api/hotel-api-v6/cancel"
        # Verify NOT the flight endpoint
        assert "/aeroVE5/" not in url_called

    @pytest.mark.asyncio
    async def test_cancel_booking_includes_credentials(self, mock_settings):
        """Cancel request should include authentication fields."""
        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "CANCELLED",
            "cancelReferenceNum": "CANCEL123456",
            "message": "Booking cancelled successfully",
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch("integrations.flightlogic.client.settings", mock_settings),
            patch("app.core.config.settings", mock_settings),
            patch("integrations.flightlogic.client.httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            client = FlightLogicClient()

            request = HotelCancelRequest(
                supplier_confirmation_num="SUP123456",
                reference_num="REF789012",
            )

            await client.cancel_hotel_booking(request)

        # Verify request body included credentials
        call_args = mock_client.return_value.__aenter__.return_value.post.call_args
        import json

        body_bytes = call_args.kwargs.get("json") or json.loads(
            call_args.kwargs["content"]
        )

        assert body_bytes["user_id"] == "test_user"
        assert body_bytes["user_password"] == "test_pass"  # pragma: allowlist secret
        assert body_bytes["access"] == "Test"
        assert body_bytes["ip_address"] == "192.168.1.1"
        assert body_bytes["supplierConfirmationNum"] == "SUP123456"
        assert body_bytes["referenceNum"] == "REF789012"

    @pytest.mark.asyncio
    async def test_cancel_booking_handles_failure_response(self, mock_settings):
        """Cancel should handle FAILED status correctly."""
        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "FAILED",
            "cancelReferenceNum": None,
            "message": "Cancellation failed: Booking not found",
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch("integrations.flightlogic.client.settings", mock_settings),
            patch("app.core.config.settings", mock_settings),
            patch("integrations.flightlogic.client.httpx.AsyncClient") as mock_client,
        ):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            client = FlightLogicClient()

            request = HotelCancelRequest(
                supplier_confirmation_num="SUP123456",
                reference_num="REF789012",
            )

            response = await client.cancel_hotel_booking(request)

        # Verify failure response is parsed correctly
        assert isinstance(response, HotelCancelResponse)
        assert response.status == "FAILED"
        assert response.cancel_reference_num is None
        assert response.message == "Cancellation failed: Booking not found"
        assert response.errors is not None
