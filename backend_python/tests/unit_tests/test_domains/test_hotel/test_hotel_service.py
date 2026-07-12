"""Unit tests for HotelService."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bson import ObjectId
from dateutil.relativedelta import relativedelta

from app.domains.hotel.exceptions import HotelBookingError, HotelSearchError
from app.domains.hotel.schemas import (
    GuestInfo,
    HotelBookingDetailsRequest,
    HotelBookingDetailsResponse,
    HotelBookingRequest,
    HotelBookingResponse,
    HotelCancelRequest,
    HotelCancelResponse,
    HotelMoreResultsRequest,
    HotelRoomRatesRequest,
    HotelRoomRatesResponse,
    HotelSearchRequest,
    HotelSearchResponse,
    HotelSearchResult,
    OccupancyRoom,
    RoomOption,
)
from app.domains.hotel.service import HotelService
from app.domains.user import UserPublic

# ==============================================================================
# HELPERS
# ==============================================================================


def get_future_checkin() -> str:
    """Generate a checkin date 1 month and 5 days from now."""
    future_date = datetime.now(UTC) + relativedelta(months=1) + timedelta(days=5)
    return future_date.strftime("%Y-%m-%d")


def get_future_checkout() -> str:
    """Generate a checkout date 1 month and 10 days from now."""
    future_date = datetime.now(UTC) + relativedelta(months=1) + timedelta(days=10)
    return future_date.strftime("%Y-%m-%d")


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    from app.domains.common import AuthProvider
    from app.domains.user.enums import UserStatus

    return UserPublic(
        id=str(ObjectId()),
        email="testuser@example.com",
        first_name="Test",
        last_name="User",
        role="user",
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_search_request():
    """Sample hotel search request."""
    return HotelSearchRequest(
        checkin=get_future_checkin(),
        checkout=get_future_checkout(),
        occupancy=[
            OccupancyRoom(room_no=1, adult=2, child=0, child_age=[]),
        ],
        city_name="Bangalore",
        country_name="India",
        currency="USD",
        max_result=50,
    )


@pytest.fixture
def sample_search_response():
    """Sample hotel search response from FlightLogic."""
    # Use model_construct to bypass validation for test fixtures
    search_result = HotelSearchResult.model_construct(
        hotel_id="123",
        twx_hotel_id="TWX123",
        product_id="PROD001",
        token_id="hotel_token_001",
        hotel_name="Grand Palace Hotel",
        city="Bangalore",
        address="123 Main Street",
        country_code="IN",
        postal_code="560001",
        latitude="12.9716",
        longitude="77.5946",
        distance_value=2.5,
        distance_unit="km",
        total=Decimal("15000.00"),
        currency="USD",
        fare_type="Refundable",
        per_night_array=[],
        hotel_rating=5,
        thumbnail_url="https://example.com/thumb.jpg",
        phone="+91-80-1234567",
    )

    return HotelSearchResponse.model_construct(
        session_id="test_session_12345",
        total_results=10,
        itineraries=[search_result],
    )


@pytest.fixture
def sample_room_rates_request():
    """Sample room rates request."""
    return HotelRoomRatesRequest(
        session_id="test_session_12345",
        token_id="hotel_token_001",
        product_id="PROD001",
        hotel_id="123",
    )


@pytest.fixture
def sample_room_rates_response():
    """Sample room rates response from FlightLogic."""
    room_option = RoomOption.model_construct(
        rate_basis_id="rate_abc123",
        room_type="Deluxe Room",
        meal_plan="Breakfast Included",
        cancellation_policy="Free cancellation until 24h before checkin",
        price=Decimal("15000.00"),
        price_per_night=Decimal("3000.00"),
        total_price=Decimal("15000.00"),
        currency="USD",
    )

    return HotelRoomRatesResponse.model_construct(
        hotel_id="123",
        session_id="test_session_12345",
        token_id="hotel_token_001",
        rooms=[room_option],
    )


@pytest.fixture
def sample_booking_request():
    """Sample hotel booking request."""
    return HotelBookingRequest(
        session_id="test_session_12345",
        rate_basis_id="rate_abc123",
        product_id="product_123",
        token_id="token_123",
        client_ref="VOYA-TEST-001",
        customer_email="john.doe@example.com",
        customer_phone="+1234567890",
        booking_note="Test booking",
        guests=[
            GuestInfo(
                title="Mr",
                first_name="John",
                last_name="Doe",
            )
        ],
    )


@pytest.fixture
def sample_booking_response_success():
    """Sample successful booking response."""
    return HotelBookingResponse(
        status="Success",
        reference_num="VOYA-HOTEL-001",
        supplier_confirmation_num="SUP123456",
        booking_details={
            "hotel_name": "Grand Palace Hotel",
            "checkin": "2026-03-15",
            "checkout": "2026-03-20",
            "room_type": "Deluxe Room",
            "guest_name": "John Doe",
        },
        errors=None,
    )


@pytest.fixture
def sample_booking_response_failure():
    """Sample failed booking response."""
    return HotelBookingResponse.model_construct(
        status="Failed",
        reference_num=None,
        supplier_confirmation_num=None,
        booking_details={},  # Empty dict instead of None
        errors={"message": "Room no longer available"},
    )


@pytest.fixture
def mock_flights_client():
    """Mock FlightLogic client."""
    client = Mock()
    client.environment = Mock(value="test")
    client.search_hotels = AsyncMock()
    client.get_room_rates = AsyncMock()
    client.book_hotel = AsyncMock()
    client.get_more_results = AsyncMock()
    client.cancel_hotel_booking = AsyncMock()
    client.get_booking_details = AsyncMock()
    return client


# ==============================================================================
# HOTEL SEARCH TESTS
# ==============================================================================


class TestSearchHotels:
    """Test HotelService.search_hotels()."""

    @patch("integrations.flightlogic.get_flights_client")
    @patch("app.domains.hotel.service.HotelSessionCache.set")
    async def test_search_hotels_success(
        self,
        mock_cache_set,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_search_request,
        sample_search_response,
    ):
        """Test successful hotel search."""
        # Setup mocks
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.search_hotels.return_value = sample_search_response

        # Create service and call method
        service = HotelService(current_user=mock_user)

        result = await service.search_hotels(sample_search_request)

        # Verify client was called correctly
        mock_flights_client.search_hotels.assert_called_once_with(sample_search_request)

        # Verify cache was set
        mock_cache_set.assert_called_once_with(
            user_id=str(mock_user.id),
            session_id="test_session_12345",
            search_response=sample_search_response,
        )

        # Verify response
        assert isinstance(result, HotelSearchResponse)
        assert result.session_id == "test_session_12345"
        assert result.total_results == 10
        assert len(result.itineraries) == 1
        assert result.itineraries[0].hotel_name == "Grand Palace Hotel"

    @patch("integrations.flightlogic.get_flights_client")
    async def test_search_hotels_without_user(
        self,
        mock_get_client,
        mock_flights_client,
        sample_search_request,
        sample_search_response,
    ):
        """Test hotel search without authenticated user."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.search_hotels.return_value = sample_search_response

        # Service without user
        service = HotelService(current_user=None)

        result = await service.search_hotels(sample_search_request)

        # Should still work
        assert result.session_id == "test_session_12345"
        assert result.total_results == 10

    @patch("integrations.flightlogic.get_flights_client")
    async def test_search_hotels_api_error(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_search_request,
    ):
        """Test hotel search when API fails."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.search_hotels.side_effect = Exception(
            "API connection failed"
        )

        service = HotelService(current_user=mock_user)

        # Should raise HotelSearchError
        with pytest.raises(HotelSearchError) as exc_info:
            await service.search_hotels(sample_search_request)

        assert "API connection failed" in str(exc_info.value)

    @patch("integrations.flightlogic.get_flights_client")
    @patch("app.domains.hotel.service.validate_search_request")
    async def test_search_hotels_validation_error(
        self,
        mock_validate,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_search_request,
    ):
        """Test hotel search with validation error."""
        mock_get_client.return_value = mock_flights_client
        mock_validate.side_effect = ValueError("Invalid checkin date")

        service = HotelService(current_user=mock_user)

        with pytest.raises(HotelSearchError):
            await service.search_hotels(sample_search_request)

    @patch("integrations.flightlogic.get_flights_client")
    async def test_search_hotels_geolocation(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_search_response,
    ):
        """Test hotel search with geolocation."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.search_hotels.return_value = sample_search_response

        # Geolocation search request
        geo_request = HotelSearchRequest(
            checkin=get_future_checkin(),
            checkout=get_future_checkout(),
            occupancy=[OccupancyRoom(room_no=1, adult=2, child=0, child_age=[])],
            latitude=Decimal("12.9716"),
            longitude=Decimal("77.5946"),
            radius=5,
            currency="USD",
        )

        service = HotelService(current_user=mock_user)
        result = await service.search_hotels(geo_request)

        assert result.session_id == "test_session_12345"

    @patch("integrations.flightlogic.get_flights_client")
    async def test_search_hotels_by_codes(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_search_response,
    ):
        """Test hotel search with specific hotel codes."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.search_hotels.return_value = sample_search_response

        # Hotel codes search request
        codes_request = HotelSearchRequest(
            checkin=get_future_checkin(),
            checkout=get_future_checkout(),
            occupancy=[OccupancyRoom(room_no=1, adult=2, child=0, child_age=[])],
            hotel_codes=["BLR123", "BLR456"],
            currency="USD",
        )

        service = HotelService(current_user=mock_user)
        result = await service.search_hotels(codes_request)

        assert result.session_id == "test_session_12345"


# ==============================================================================
# ROOM RATES TESTS
# ==============================================================================


class TestGetRoomRates:
    """Test HotelService.get_room_rates()."""

    @patch("integrations.flightlogic.get_flights_client")
    async def test_get_room_rates_success(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_room_rates_request,
        sample_room_rates_response,
    ):
        """Test successful room rates retrieval."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.get_room_rates.return_value = sample_room_rates_response

        service = HotelService(current_user=mock_user)

        result = await service.get_room_rates(sample_room_rates_request)

        # Verify client was called correctly
        mock_flights_client.get_room_rates.assert_called_once_with(
            sample_room_rates_request
        )

        # Verify response
        assert isinstance(result, HotelRoomRatesResponse)
        assert result.session_id == "test_session_12345"
        assert result.hotel_id  # Hotel ID exists
        assert len(result.rooms) == 1
        assert result.rooms[0].rate_basis_id == "rate_abc123"
        assert result.rooms[0].room_type == "Deluxe Room"

    @patch("integrations.flightlogic.get_flights_client")
    async def test_get_room_rates_api_error(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_room_rates_request,
    ):
        """Test room rates retrieval when API fails."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.get_room_rates.side_effect = Exception("Session expired")

        service = HotelService(current_user=mock_user)

        with pytest.raises(HotelSearchError) as exc_info:
            await service.get_room_rates(sample_room_rates_request)

        assert "Room rates error" in str(exc_info.value)
        assert "Session expired" in str(exc_info.value)

    @patch("integrations.flightlogic.get_flights_client")
    @patch("app.domains.hotel.service.validate_session_id")
    async def test_get_room_rates_invalid_session(
        self,
        mock_validate_session,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_room_rates_request,
    ):
        """Test room rates with invalid session ID."""
        mock_get_client.return_value = mock_flights_client
        mock_validate_session.side_effect = ValueError("Invalid session ID")

        service = HotelService(current_user=mock_user)

        with pytest.raises(HotelSearchError):
            await service.get_room_rates(sample_room_rates_request)


# ==============================================================================
# HOTEL BOOKING TESTS
# ==============================================================================


class TestCreateBooking:
    """Test HotelService.create_booking()."""

    @patch("integrations.flightlogic.get_flights_client")
    @patch("app.domains.hotel.service.HotelEventHandler.handle_booking_confirmed")
    async def test_create_booking_success(
        self,
        mock_handle_confirmed,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_booking_request,
        sample_booking_response_success,
    ):
        """Test successful hotel booking."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.book_hotel.return_value = sample_booking_response_success
        mock_handle_confirmed.return_value = None

        service = HotelService(current_user=mock_user)

        result = await service.create_booking(sample_booking_request)

        # Verify client was called
        mock_flights_client.book_hotel.assert_called_once_with(sample_booking_request)

        # Verify response
        assert isinstance(result, HotelBookingResponse)
        assert result.status == "Success"
        assert result.supplier_confirmation_num == "SUP123456"

    @patch("integrations.flightlogic.get_flights_client")
    @patch("app.domains.hotel.service.HotelEventHandler.handle_booking_failed")
    async def test_create_booking_failure(
        self,
        mock_handle_failed,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_booking_request,
        sample_booking_response_failure,
    ):
        """Test failed hotel booking."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.book_hotel.return_value = sample_booking_response_failure
        mock_handle_failed.return_value = None

        service = HotelService(current_user=mock_user)

        with pytest.raises(HotelBookingError) as exc_info:
            await service.create_booking(sample_booking_request)

        # Verify failure email was sent
        mock_handle_failed.assert_called_once()
        email_args = mock_handle_failed.call_args[1]
        assert email_args["user_id"] == str(mock_user.id)
        assert "Room no longer available" in email_args["error_message"]

        assert "Room no longer available" in str(exc_info.value)

    @patch("integrations.flightlogic.get_flights_client")
    async def test_create_booking_api_error(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_booking_request,
    ):
        """Test booking when API fails."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.book_hotel.side_effect = Exception("Connection timeout")

        service = HotelService(current_user=mock_user)

        with pytest.raises(HotelBookingError) as exc_info:
            await service.create_booking(sample_booking_request)

        assert "Connection timeout" in str(exc_info.value)

    @patch("integrations.flightlogic.get_flights_client")
    async def test_create_booking_without_rate_basis_id(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
    ):
        """Test booking without rate basis ID."""
        mock_get_client.return_value = mock_flights_client

        # Request without rate_basis_id
        invalid_request = HotelBookingRequest(
            session_id="test_session_12345",
            rate_basis_id="",  # Empty rate basis ID
            product_id="product_123",
            token_id="token_123",
            client_ref="VOYA-TEST-001",
            customer_email="john@example.com",
            customer_phone="+1234567890",
            booking_note="Test",
            guests=[
                GuestInfo(
                    title="Mr",
                    first_name="John",
                    last_name="Doe",
                )
            ],
        )

        service = HotelService(current_user=mock_user)

        with pytest.raises(HotelBookingError) as exc_info:
            await service.create_booking(invalid_request)

        assert "Rate basis ID is required" in str(exc_info.value)

    @patch("integrations.flightlogic.get_flights_client")
    @patch("app.domains.hotel.events.HotelEventHandler.handle_booking_confirmed")
    async def test_create_booking_event_handler_failure(
        self,
        mock_handle_confirmed,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_booking_request,
        sample_booking_response_success,
    ):
        """Test booking succeeds even if event handler fails."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.book_hotel.return_value = sample_booking_response_success
        mock_handle_confirmed.side_effect = Exception("Email service down")

        service = HotelService(current_user=mock_user)

        # Should not raise exception - booking succeeds even if email fails
        result = await service.create_booking(sample_booking_request)

        assert result.status == "Success"
        assert result.supplier_confirmation_num == "SUP123456"

    @patch("integrations.flightlogic.get_flights_client")
    async def test_create_booking_without_user(
        self,
        mock_get_client,
        mock_flights_client,
        sample_booking_request,
        sample_booking_response_success,
    ):
        """Test booking without authenticated user."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.book_hotel.return_value = sample_booking_response_success

        # Service without user
        service = HotelService(current_user=None)

        result = await service.create_booking(sample_booking_request)

        # Should still work (no database or email events)
        assert result.status == "Success"
        assert result.supplier_confirmation_num == "SUP123456"


# ==============================================================================
# HELPER METHOD TESTS
# ==============================================================================


class TestHelperMethods:
    """Test HotelService helper methods."""

    @patch("integrations.flightlogic.get_flights_client")
    def test_get_base_log_context_with_user(
        self, mock_get_client, mock_flights_client, mock_user
    ):
        """Test base log context includes user_id when authenticated."""
        mock_get_client.return_value = mock_flights_client

        service = HotelService(current_user=mock_user)
        context = service._get_base_log_context()

        assert "environment" in context
        assert context["environment"] == "test"
        assert "user_id" in context
        assert context["user_id"] == str(mock_user.id)

    @patch("integrations.flightlogic.get_flights_client")
    def test_get_base_log_context_without_user(
        self, mock_get_client, mock_flights_client
    ):
        """Test base log context without user_id when not authenticated."""
        mock_get_client.return_value = mock_flights_client

        service = HotelService(current_user=None)
        context = service._get_base_log_context()

        assert "environment" in context
        assert context["environment"] == "test"
        assert "user_id" not in context

    @patch("integrations.flightlogic.get_flights_client")
    def test_truncate_session_id(self, mock_get_client, mock_flights_client):
        """Test session ID truncation for logging."""
        mock_get_client.return_value = mock_flights_client

        service = HotelService(current_user=None)

        # Long session ID
        long_id = "very_long_session_id_12345678901234567890"
        truncated = service._truncate_session_id(long_id, max_len=12)
        assert truncated == "very_long_se..."
        assert len(truncated) == 15  # 12 chars + "..."

        # Short session ID
        short_id = "short"
        truncated = service._truncate_session_id(short_id, max_len=12)
        assert truncated == "short"

        # None session ID
        truncated = service._truncate_session_id(None)
        assert truncated == "N/A"


# ==============================================================================
# SESSION MANAGEMENT TESTS
# ==============================================================================


class TestHotelSessionManagement:
    """Tests for hotel session caching and validation.

    Verifies that:
    1. Sessions are properly cached after successful searches
    2. Session IDs are validated before use
    3. Invalid session IDs are rejected
    4. Session cache stores and retrieves correctly
    """

    @patch("integrations.flightlogic.get_flights_client")
    @pytest.mark.asyncio
    async def test_session_cached_after_successful_search(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_search_request,
        sample_search_response,
    ):
        """Test that successful hotel searches cache the session."""
        from app.domains.hotel.cache import HotelSessionCache

        mock_get_client.return_value = mock_flights_client
        mock_flights_client.search_hotels = AsyncMock(
            return_value=sample_search_response
        )

        service = HotelService(current_user=mock_user)

        # Clear cache before test
        HotelSessionCache.clear_user(user_id=mock_user.id)

        # Perform search
        result = await service.search_hotels(sample_search_request)

        # Verify session was cached
        cached_response = HotelSessionCache.get(
            user_id=mock_user.id, session_id=result.session_id
        )

        assert cached_response is not None
        assert cached_response.session_id == result.session_id
        assert len(cached_response.itineraries) > 0

    @patch("integrations.flightlogic.get_flights_client")
    @pytest.mark.asyncio
    async def test_session_not_cached_without_user(
        self,
        mock_get_client,
        mock_flights_client,
        sample_search_request,
        sample_search_response,
    ):
        """Test that sessions are NOT cached when user is not authenticated."""
        from app.domains.hotel.cache import HotelSessionCache

        mock_get_client.return_value = mock_flights_client
        mock_flights_client.search_hotels = AsyncMock(
            return_value=sample_search_response
        )

        service = HotelService(current_user=None)

        # Get initial cache size
        initial_cache_size = len(HotelSessionCache._cache)

        # Perform search without user
        result = await service.search_hotels(sample_search_request)

        # Verify cache size didn't change
        assert len(HotelSessionCache._cache) == initial_cache_size
        assert result.session_id == sample_search_response.session_id

    @patch("integrations.flightlogic.get_flights_client")
    @pytest.mark.asyncio
    async def test_invalid_session_id_rejected_in_room_rates(
        self, mock_get_client, mock_flights_client, mock_user
    ):
        """Test that invalid session IDs are rejected when getting room rates."""
        from app.domains.hotel.exceptions import HotelSearchError

        mock_get_client.return_value = mock_flights_client

        service = HotelService(current_user=mock_user)

        # Create request with invalid session ID (empty string)
        invalid_request = HotelRoomRatesRequest(
            session_id="",  # Invalid: empty string
            token_id="valid_token_123",
            product_id="PROD001",
            hotel_id="123",
        )

        with pytest.raises(HotelSearchError, match="Session ID is required"):
            await service.get_room_rates(invalid_request)

    @patch("integrations.flightlogic.get_flights_client")
    @pytest.mark.asyncio
    async def test_invalid_session_id_rejected_in_booking(
        self, mock_get_client, mock_flights_client, mock_user
    ):
        """Test that invalid session IDs are rejected when creating booking."""
        from app.domains.hotel.exceptions import HotelBookingError

        mock_get_client.return_value = mock_flights_client

        service = HotelService(current_user=mock_user)

        # Create request with invalid session ID (whitespace only)
        invalid_request = HotelBookingRequest(
            session_id="   ",  # Invalid: whitespace only
            rate_basis_id="valid_rate_basis_id",
            product_id="product_123",
            token_id="token_123",
            client_ref="VOYA-TEST-001",
            customer_email="test@example.com",
            customer_phone="+1234567890",
            booking_note="Test",
            guests=[
                GuestInfo(
                    title="Mr",
                    first_name="Test",
                    last_name="User",
                )
            ],
        )

        with pytest.raises(HotelBookingError, match="Session ID cannot be empty"):
            await service.create_booking(invalid_request)

    @patch("integrations.flightlogic.get_flights_client")
    def test_session_cache_clear_for_user(
        self, mock_get_client, mock_flights_client, mock_user, sample_search_response
    ):
        """Test that session cache can be cleared for a specific user."""
        from app.domains.hotel.cache import HotelSessionCache

        mock_get_client.return_value = mock_flights_client

        # Add session to cache
        HotelSessionCache.set(
            user_id=mock_user.id,
            session_id="test_session_1",
            search_response=sample_search_response,
        )

        # Verify session exists
        assert HotelSessionCache.get(mock_user.id, "test_session_1") is not None

        # Clear cache for user
        HotelSessionCache.clear_user(user_id=mock_user.id)

        # Verify session is gone
        assert HotelSessionCache.get(mock_user.id, "test_session_1") is None

    @patch("integrations.flightlogic.get_flights_client")
    def test_session_cache_isolates_users(
        self, mock_get_client, mock_flights_client, mock_user, sample_search_response
    ):
        """Test that session cache isolates sessions between different users."""
        from app.domains.hotel.cache import HotelSessionCache

        mock_get_client.return_value = mock_flights_client

        # Create second user
        from app.domains.common import AuthProvider
        from app.domains.user.enums import UserStatus

        user2 = UserPublic(
            id=str(ObjectId()),
            email="user2@example.com",
            first_name="User",
            last_name="Two",
            role="user",
            status=UserStatus.ACTIVE,
            email_verified=True,
            auth_provider=AuthProvider.LOCAL,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Create second response (different city)
        response2 = HotelSearchResponse.model_construct(
            session_id="test_session_12345",
            total_results=5,
            itineraries=[
                HotelSearchResult.model_construct(
                    hotel_id="456",
                    twx_hotel_id="TWX456",
                    product_id="PROD002",
                    token_id="hotel_token_002",
                    hotel_name="Mumbai Palace",
                    city="Mumbai",
                    address="456 Marine Drive",
                    country_code="IN",
                    postal_code="400001",
                    latitude="18.9388",
                    longitude="72.8354",
                    distance_value=1.5,
                    distance_unit="km",
                    total=Decimal("12000.00"),
                    currency="USD",
                    fare_type="Refundable",
                    per_night_array=[],
                    hotel_rating=4,
                    thumbnail_url="https://example.com/mumbai.jpg",
                    phone="+91-22-1234567",
                )
            ],
        )

        # Add sessions for both users with same session_id
        session_id = "shared_session_id"

        HotelSessionCache.set(
            user_id=mock_user.id,
            session_id=session_id,
            search_response=sample_search_response,
        )

        HotelSessionCache.set(
            user_id=user2.id,
            session_id=session_id,
            search_response=response2,
        )

        # Verify each user gets their own session
        user1_response = HotelSessionCache.get(mock_user.id, session_id)
        user2_response = HotelSessionCache.get(user2.id, session_id)

        assert user1_response.itineraries[0].city == "Bangalore"
        assert user2_response.itineraries[0].city == "Mumbai"

        # Clear user1's cache
        HotelSessionCache.clear_user(user_id=mock_user.id)

        # Verify user1's session is gone but user2's remains
        assert HotelSessionCache.get(mock_user.id, session_id) is None
        assert HotelSessionCache.get(user2.id, session_id) is not None


# ==============================================================================
# MORE RESULTS TESTS
# ==============================================================================


@pytest.fixture
def sample_more_results_request():
    """Sample more results request."""
    return HotelMoreResultsRequest(
        session_id="test_session_12345",
        next_token="next_token_abc123",
        max_result=20,
    )


@pytest.fixture
def sample_more_results_response():
    """Sample more results response from FlightLogic."""
    # Use model_construct to bypass validation for test fixtures
    search_result = HotelSearchResult.model_construct(
        hotel_id="456",
        twx_hotel_id="TWX456",
        product_id="PROD002",
        token_id="hotel_token_002",
        hotel_name="Another Hotel",
        city="Mumbai",
        address="456 Marine Drive",
        country_code="IN",
        postal_code="400001",
        latitude="18.9388",
        longitude="72.8354",
        distance_value=1.5,
        distance_unit="km",
        total=Decimal("12000.00"),
        currency="USD",
        fare_type="Refundable",
        per_night_array=[],
        hotel_rating=4,
        thumbnail_url="https://example.com/mumbai.jpg",
        phone="+91-22-1234567",
    )

    return HotelSearchResponse.model_construct(
        session_id="test_session_12345",
        total_results=5,
        more_results=False,
        next_token="",
        itineraries=[search_result],
    )


class TestGetMoreResults:
    """Test HotelService.get_more_results()."""

    @patch("integrations.flightlogic.get_flights_client")
    async def test_get_more_results_success(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_more_results_request,
        sample_more_results_response,
    ):
        """Test successful more results retrieval."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.get_more_results.return_value = sample_more_results_response

        service = HotelService(current_user=mock_user)

        result = await service.get_more_results(sample_more_results_request)

        # Verify client was called correctly
        mock_flights_client.get_more_results.assert_called_once_with(
            sample_more_results_request
        )

        # Verify response
        assert isinstance(result, HotelSearchResponse)
        assert result.session_id == "test_session_12345"
        assert result.total_results == 5
        assert len(result.itineraries) == 1
        assert result.itineraries[0].hotel_name == "Another Hotel"
        assert result.more_results is False

    @patch("integrations.flightlogic.get_flights_client")
    async def test_get_more_results_without_user(
        self,
        mock_get_client,
        mock_flights_client,
        sample_more_results_request,
        sample_more_results_response,
    ):
        """Test more results retrieval without authenticated user."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.get_more_results.return_value = sample_more_results_response

        # Service without user
        service = HotelService(current_user=None)

        result = await service.get_more_results(sample_more_results_request)

        # Should still work
        assert result.session_id == "test_session_12345"
        assert result.total_results == 5

    @patch("integrations.flightlogic.get_flights_client")
    async def test_get_more_results_api_error(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_more_results_request,
    ):
        """Test more results when API fails."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.get_more_results.side_effect = Exception("Session expired")

        service = HotelService(current_user=mock_user)

        # Should raise HotelSearchError
        with pytest.raises(HotelSearchError) as exc_info:
            await service.get_more_results(sample_more_results_request)

        assert "Session expired" in str(exc_info.value)

    @patch("integrations.flightlogic.get_flights_client")
    @patch("app.domains.hotel.service.validate_session_id")
    async def test_get_more_results_invalid_session(
        self,
        mock_validate_session,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_more_results_request,
    ):
        """Test more results with invalid session ID."""
        mock_get_client.return_value = mock_flights_client
        mock_validate_session.side_effect = ValueError("Invalid session ID")

        service = HotelService(current_user=mock_user)

        with pytest.raises(HotelSearchError):
            await service.get_more_results(sample_more_results_request)


# ==============================================================================
# CANCELLATION TESTS
# ==============================================================================


@pytest.fixture
def sample_cancel_request():
    """Sample hotel cancellation request."""
    return HotelCancelRequest(
        supplier_confirmation_num="SUP123456",
        reference_num="REF789012",
    )


@pytest.fixture
def sample_cancel_response_success():
    """Sample successful cancellation response."""
    return HotelCancelResponse(
        status="CANCELLED",
        cancel_reference_num="CANCEL123456",
        message="Booking cancelled successfully",
        errors=None,
    )


@pytest.fixture
def sample_cancel_response_failure():
    """Sample failed cancellation response."""
    return HotelCancelResponse.model_construct(
        status="FAILED",
        cancel_reference_num=None,
        message="Cancellation failed: Booking not found",
        errors={
            "code": "CANCELLATION_FAILED",
            "message": "Cancellation failed: Booking not found",
            "details": None,
        },
    )


class TestCancelBooking:
    """Test HotelService.cancel_booking()."""

    @patch("integrations.flightlogic.get_flights_client")
    async def test_cancel_booking_success(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_cancel_request,
        sample_cancel_response_success,
    ):
        """Test successful hotel booking cancellation."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.cancel_hotel_booking.return_value = (
            sample_cancel_response_success
        )

        service = HotelService(current_user=mock_user)

        result = await service.cancel_booking(sample_cancel_request)

        # Verify client was called
        mock_flights_client.cancel_hotel_booking.assert_called_once_with(
            sample_cancel_request
        )

        # Verify response
        assert isinstance(result, HotelCancelResponse)
        assert result.status == "CANCELLED"
        assert result.cancel_reference_num == "CANCEL123456"
        assert result.message == "Booking cancelled successfully"

    @patch("integrations.flightlogic.get_flights_client")
    async def test_cancel_booking_failure(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_cancel_request,
        sample_cancel_response_failure,
    ):
        """Test failed hotel booking cancellation."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.cancel_hotel_booking.return_value = (
            sample_cancel_response_failure
        )

        service = HotelService(current_user=mock_user)

        with pytest.raises(HotelBookingError) as exc_info:
            await service.cancel_booking(sample_cancel_request)

        assert "Cancellation failed" in str(exc_info.value)

    @patch("integrations.flightlogic.get_flights_client")
    async def test_cancel_booking_api_error(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_cancel_request,
    ):
        """Test cancellation when API fails."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.cancel_hotel_booking.side_effect = Exception(
            "Connection timeout"
        )

        service = HotelService(current_user=mock_user)

        with pytest.raises(HotelBookingError) as exc_info:
            await service.cancel_booking(sample_cancel_request)

        assert "Connection timeout" in str(exc_info.value)

    @patch("integrations.flightlogic.get_flights_client")
    async def test_cancel_booking_missing_supplier_confirmation(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
    ):
        """Test cancellation without supplier confirmation number."""
        mock_get_client.return_value = mock_flights_client

        # Request without supplier_confirmation_num
        invalid_request = HotelCancelRequest(
            supplier_confirmation_num="",  # Empty
            reference_num="REF789012",
        )

        service = HotelService(current_user=mock_user)

        with pytest.raises(HotelBookingError) as exc_info:
            await service.cancel_booking(invalid_request)

        assert "Supplier confirmation number is required" in str(exc_info.value)

    @patch("integrations.flightlogic.get_flights_client")
    async def test_cancel_booking_missing_reference_num(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
    ):
        """Test cancellation without reference number."""
        mock_get_client.return_value = mock_flights_client

        # Request without reference_num
        invalid_request = HotelCancelRequest(
            supplier_confirmation_num="SUP123456",
            reference_num="",  # Empty
        )

        service = HotelService(current_user=mock_user)

        with pytest.raises(HotelBookingError) as exc_info:
            await service.cancel_booking(invalid_request)

        assert "Reference number is required" in str(exc_info.value)

    @patch("integrations.flightlogic.get_flights_client")
    async def test_cancel_booking_without_user(
        self,
        mock_get_client,
        mock_flights_client,
        sample_cancel_request,
        sample_cancel_response_success,
    ):
        """Test cancellation without authenticated user."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.cancel_hotel_booking.return_value = (
            sample_cancel_response_success
        )

        # Service without user
        service = HotelService(current_user=None)

        result = await service.cancel_booking(sample_cancel_request)

        # Should still work
        assert result.status == "CANCELLED"
        assert result.cancel_reference_num == "CANCEL123456"


@pytest.fixture
def sample_booking_details_request():
    """Sample booking details request."""
    return HotelBookingDetailsRequest(
        supplier_confirmation_num="SUP12345678901234567890",
        reference_num="REF789012345678901234567",
    )


@pytest.fixture
def sample_booking_details_response():
    """Sample booking details response."""
    return HotelBookingDetailsResponse(
        booking_details={
            "hotel_name": "Grand Palace Hotel",
            "check_in": "2026-03-15",
            "check_out": "2026-03-20",
            "total_price": 15000.00,
            "currency": "USD",
            "status": "CONFIRMED",
            "address": "123 Main Street",
            "city": "Bangalore",
            "hotel_rating": 5,
            "guests": [
                {
                    "title": "Mr",
                    "first_name": "John",
                    "last_name": "Doe",
                    "room_number": 1,
                    "is_child": False,
                }
            ],
        },
        errors=None,
    )


class TestGetBookingDetails:
    """Test HotelService.get_booking_details()."""

    @patch("integrations.flightlogic.get_flights_client")
    async def test_get_booking_details_success(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_booking_details_request,
        sample_booking_details_response,
    ):
        """Test successful booking details retrieval."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.get_booking_details.return_value = (
            sample_booking_details_response
        )

        service = HotelService(current_user=mock_user)

        result = await service.get_booking_details(sample_booking_details_request)

        # Verify client was called
        mock_flights_client.get_booking_details.assert_called_once_with(
            sample_booking_details_request
        )

        # Verify response
        assert isinstance(result, HotelBookingDetailsResponse)
        assert result.booking_details is not None
        assert result.booking_details["hotel_name"] == "Grand Palace Hotel"
        assert result.booking_details["status"] == "CONFIRMED"
        assert result.errors is None

    @patch("integrations.flightlogic.get_flights_client")
    async def test_get_booking_details_client_error(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_booking_details_request,
    ):
        """Test booking details when client raises HotelBookingError."""
        mock_get_client.return_value = mock_flights_client
        from app.domains.hotel.exceptions import HotelBookingError

        mock_flights_client.get_booking_details.side_effect = HotelBookingError(
            reason="Booking not found"
        )

        service = HotelService(current_user=mock_user)

        with pytest.raises(HotelBookingError) as exc_info:
            await service.get_booking_details(sample_booking_details_request)

        assert "Booking not found" in str(exc_info.value)

    @patch("integrations.flightlogic.get_flights_client")
    async def test_get_booking_details_unexpected_error(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_booking_details_request,
    ):
        """Test booking details when unexpected error occurs."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.get_booking_details.side_effect = Exception(
            "Connection timeout"
        )

        service = HotelService(current_user=mock_user)

        with pytest.raises(HotelBookingError) as exc_info:
            await service.get_booking_details(sample_booking_details_request)

        assert "Connection timeout" in str(exc_info.value)
        assert "Booking details retrieval failed" in str(exc_info.value)

    @patch("integrations.flightlogic.get_flights_client")
    async def test_get_booking_details_without_user(
        self,
        mock_get_client,
        mock_flights_client,
        sample_booking_details_request,
        sample_booking_details_response,
    ):
        """Test booking details retrieval without authenticated user."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.get_booking_details.return_value = (
            sample_booking_details_response
        )

        # Service without user
        service = HotelService(current_user=None)

        result = await service.get_booking_details(sample_booking_details_request)

        # Should still work
        assert isinstance(result, HotelBookingDetailsResponse)
        assert result.booking_details is not None

    @patch("integrations.flightlogic.get_flights_client")
    async def test_get_booking_details_logging_context(
        self,
        mock_get_client,
        mock_flights_client,
        mock_user,
        sample_booking_details_request,
        sample_booking_details_response,
    ):
        """Test that logging context includes masked confirmation numbers."""
        mock_get_client.return_value = mock_flights_client
        mock_flights_client.get_booking_details.return_value = (
            sample_booking_details_response
        )

        service = HotelService(current_user=mock_user)

        # Mock logger to capture log context
        with patch("app.domains.hotel.service.HotelLogger") as mock_logger_class:
            mock_logger = Mock()
            mock_logger.started = Mock()
            mock_logger.success = Mock()
            mock_logger_class.return_value = mock_logger

            await service.get_booking_details(sample_booking_details_request)

            # Verify logger was called with masked confirmation numbers
            mock_logger_class.assert_called_once()
            call_kwargs = mock_logger_class.call_args[1]
            assert "supplier_confirmation" in call_kwargs
            # Check that confirmation is masked (first 15 chars + "...")
            assert call_kwargs["supplier_confirmation"].endswith("...")
            assert len(call_kwargs["supplier_confirmation"]) > 15
            assert "reference_num" in call_kwargs
            # Check that reference is masked (first 15 chars + "...")
            assert call_kwargs["reference_num"].endswith("...")
            assert len(call_kwargs["reference_num"]) > 15
