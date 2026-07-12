"""Unit tests for /api/flights/select endpoint.

Tests the select flight for booking functionality that generates URLs for redirecting
users to the flight-booker UI with initial_step=rules parameter.
"""

from unittest.mock import AsyncMock, Mock, patch

import jwt
import pytest
from fastapi import HTTPException

from app.api.flights import (
    FlightSelectionRequest,
    FlightSelectionResponse,
    select_flight_for_booking,
)
from app.domains.flight import PassengerType
from app.domains.flight.service import FlightService

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_flight_service():
    """Mock FlightService for testing."""
    service = Mock(spec=FlightService)
    service.current_user = None
    return service


@pytest.fixture
def mock_authenticated_flight_service():
    """Mock FlightService with authenticated user."""
    service = Mock(spec=FlightService)
    mock_user = Mock()
    mock_user.id = "user-123"
    service.current_user = mock_user
    return service


@pytest.fixture
def sample_flight_selection_request():
    """Sample flight selection request."""
    return FlightSelectionRequest(
        session_id="fl_session_123",
        flight_id="fare_source_code_456",
        adults=2,
        children=1,
        infants=0,
    )


@pytest.fixture
def mock_validated_flight():
    """Mock validated flight from revalidate response."""
    flight = Mock()
    flight.model_dump = Mock(
        return_value={
            "flight_legs": [
                {
                    "flight_segments": [
                        {
                            "departure_airport": {"iata_code": "JFK"},
                            "arrival_airport": {"iata_code": "LHR"},
                            "departure_datetime": "2026-04-15T10:00:00",
                        }
                    ]
                }
            ]
        }
    )
    return flight


@pytest.fixture
def mock_revalidate_response(mock_validated_flight):
    """Mock revalidate response with validated flight."""
    response = Mock()
    response.is_fare_available = True
    response.validated_fare_itineraries = [mock_validated_flight]

    # Mock passenger fare breakdown
    mock_breakdown = Mock()
    mock_breakdown.passenger_type_info = Mock()
    mock_breakdown.passenger_type_info.passenger_type = PassengerType.ADULT
    mock_breakdown.passenger_type_info.passenger_count = 2

    mock_pricing = Mock()
    mock_pricing.passenger_fare_breakdown = [mock_breakdown]
    mock_validated_flight.updated_pricing = mock_pricing

    return response


# ==============================================================================
# SUCCESS CASES
# ==============================================================================


class TestSelectFlightForBookingSuccess:
    """Test successful flight selection and redirect URL generation."""

    @pytest.mark.asyncio
    @patch("app.domains.booking_sessions.service.BookingSessionService")
    @patch("app.api.flights.settings")
    @patch("app.api.flights.logger")
    async def test_select_flight_includes_initial_step_rules(
        self,
        mock_logger,
        mock_settings,
        mock_booking_session_service,
        sample_flight_selection_request,
        mock_flight_service,
        mock_revalidate_response,
    ):
        """Test that redirect URL includes initial_step=rules parameter."""
        mock_settings.BACKEND_URL = "http://localhost:8000"
        mock_settings.SECRET_KEY = "test-secret-key"  # pragma: allowlist secret

        # Mock revalidate_fare
        mock_flight_service.revalidate_fare = AsyncMock(
            return_value=mock_revalidate_response
        )

        # Mock BookingSessionService.store_session
        mock_booking_session_service.store_session = AsyncMock(return_value=True)

        result = await select_flight_for_booking(
            sample_flight_selection_request, mock_flight_service
        )

        assert isinstance(result, FlightSelectionResponse)
        assert "redirect_url" in result.model_dump()
        assert result.session_id is not None

        # Verify URL structure
        assert (
            "http://localhost:8000/dev/flight-booker/index.html" in result.redirect_url
        )

        # Verify required parameters are present
        assert f"session_id={result.session_id}" in result.redirect_url
        assert "source=api" in result.redirect_url
        assert "initial_step=rules" in result.redirect_url

        # Verify parameter values
        url_parts = result.redirect_url.split("?")
        assert len(url_parts) == 2
        params = url_parts[1].split("&")
        param_dict = {p.split("=")[0]: p.split("=")[1] for p in params}

        assert param_dict["session_id"] == result.session_id
        assert param_dict["source"] == "api"
        assert param_dict["initial_step"] == "rules"

    @pytest.mark.asyncio
    @patch("app.domains.booking_sessions.service.BookingSessionService")
    @patch("app.api.flights.settings")
    @patch("app.api.flights.logger")
    async def test_select_flight_includes_auth_token_when_authenticated(
        self,
        mock_logger,
        mock_settings,
        mock_booking_session_service,
        sample_flight_selection_request,
        mock_authenticated_flight_service,
        mock_revalidate_response,
    ):
        """Test that redirect URL includes auth_token when user is authenticated."""
        mock_settings.BACKEND_URL = "http://localhost:8000"
        mock_settings.SECRET_KEY = "test-secret-key"  # pragma: allowlist secret

        # Mock revalidate_fare
        mock_authenticated_flight_service.revalidate_fare = AsyncMock(
            return_value=mock_revalidate_response
        )

        # Mock BookingSessionService.store_session
        mock_booking_session_service.store_session = AsyncMock(return_value=True)

        result = await select_flight_for_booking(
            sample_flight_selection_request, mock_authenticated_flight_service
        )

        # Verify auth_token is present
        assert "auth_token=" in result.redirect_url

        # Verify all required parameters
        assert f"session_id={result.session_id}" in result.redirect_url
        assert "source=api" in result.redirect_url
        assert "initial_step=rules" in result.redirect_url

        # Extract and verify JWT token
        url_parts = result.redirect_url.split("auth_token=")
        assert len(url_parts) == 2
        token = url_parts[1]

        decoded = jwt.decode(
            token,
            mock_settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_exp": False},
        )
        assert decoded["user_id"] == "user-123"
        assert decoded["session_id"] == result.session_id
        assert decoded["type"] == "booking_auth"

    @pytest.mark.asyncio
    @patch("app.domains.booking_sessions.service.BookingSessionService")
    @patch("app.api.flights.settings")
    @patch("app.api.flights.logger")
    async def test_select_flight_no_auth_token_when_unauthenticated(
        self,
        mock_logger,
        mock_settings,
        mock_booking_session_service,
        sample_flight_selection_request,
        mock_flight_service,
        mock_revalidate_response,
    ):
        """Test that redirect URL does not include auth_token when user is not authenticated."""
        mock_settings.BACKEND_URL = "http://localhost:8000"
        mock_settings.SECRET_KEY = "test-secret-key"  # pragma: allowlist secret

        # Mock revalidate_fare
        mock_flight_service.revalidate_fare = AsyncMock(
            return_value=mock_revalidate_response
        )

        # Mock BookingSessionService.store_session
        mock_booking_session_service.store_session = AsyncMock(return_value=True)

        result = await select_flight_for_booking(
            sample_flight_selection_request, mock_flight_service
        )

        # Verify auth_token is NOT present
        assert "auth_token=" not in result.redirect_url

        # Verify required parameters are still present
        assert f"session_id={result.session_id}" in result.redirect_url
        assert "source=api" in result.redirect_url
        assert "initial_step=rules" in result.redirect_url

    @pytest.mark.asyncio
    @patch("app.domains.booking_sessions.service.BookingSessionService")
    @patch("app.api.flights.settings")
    @patch("app.api.flights.logger")
    async def test_select_flight_url_parameter_order(
        self,
        mock_logger,
        mock_settings,
        mock_booking_session_service,
        sample_flight_selection_request,
        mock_flight_service,
        mock_revalidate_response,
    ):
        """Test that URL parameters are in the correct order."""
        mock_settings.BACKEND_URL = "http://localhost:8000"
        mock_settings.SECRET_KEY = "test-secret-key"  # pragma: allowlist secret

        # Mock revalidate_fare
        mock_flight_service.revalidate_fare = AsyncMock(
            return_value=mock_revalidate_response
        )

        # Mock BookingSessionService.store_session
        mock_booking_session_service.store_session = AsyncMock(return_value=True)

        result = await select_flight_for_booking(
            sample_flight_selection_request, mock_flight_service
        )

        # Parse URL to check parameter order
        url_parts = result.redirect_url.split("?")
        assert len(url_parts) == 2
        params = url_parts[1].split("&")

        # Verify expected order: session_id, source, initial_step
        assert "session_id=" in params[0]
        assert "source=api" in params[1]
        assert "initial_step=rules" in params[2]

    @pytest.mark.asyncio
    @patch("app.domains.booking_sessions.service.BookingSessionService")
    @patch("app.api.flights.settings")
    @patch("app.api.flights.logger")
    async def test_select_flight_auth_token_at_end_when_present(
        self,
        mock_logger,
        mock_settings,
        mock_booking_session_service,
        sample_flight_selection_request,
        mock_authenticated_flight_service,
        mock_revalidate_response,
    ):
        """Test that auth_token is appended at the end of URL parameters."""
        mock_settings.BACKEND_URL = "http://localhost:8000"
        mock_settings.SECRET_KEY = "test-secret-key"  # pragma: allowlist secret

        # Mock revalidate_fare
        mock_authenticated_flight_service.revalidate_fare = AsyncMock(
            return_value=mock_revalidate_response
        )

        # Mock BookingSessionService.store_session
        mock_booking_session_service.store_session = AsyncMock(return_value=True)

        result = await select_flight_for_booking(
            sample_flight_selection_request, mock_authenticated_flight_service
        )

        # Parse URL
        url_parts = result.redirect_url.split("?")
        params = url_parts[1].split("&")

        # auth_token should be the last parameter
        assert "auth_token=" in params[-1]

        # Verify other parameters are before auth_token
        assert "session_id=" in params[0]
        assert "source=api" in params[1]
        assert "initial_step=rules" in params[2]


# ==============================================================================
# ERROR HANDLING
# ==============================================================================


class TestSelectFlightForBookingErrorHandling:
    """Test error handling in select flight endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.flights.logger")
    async def test_fare_not_available_returns_410(
        self,
        mock_logger,
        sample_flight_selection_request,
        mock_flight_service,
    ):
        """Test that unavailable fare returns HTTP 410."""
        # Mock revalidate_fare to return unavailable fare
        mock_response = Mock()
        mock_response.is_fare_available = False
        mock_flight_service.revalidate_fare = AsyncMock(return_value=mock_response)

        with pytest.raises(HTTPException) as exc_info:
            await select_flight_for_booking(
                sample_flight_selection_request, mock_flight_service
            )

        assert exc_info.value.status_code == 410
        assert "no longer available" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("app.api.flights.logger")
    async def test_no_validated_itineraries_returns_500(
        self,
        mock_logger,
        sample_flight_selection_request,
        mock_flight_service,
    ):
        """Test that missing validated itineraries returns HTTP 500."""
        # Mock revalidate_fare to return response with no itineraries
        mock_response = Mock()
        mock_response.is_fare_available = True
        mock_response.validated_fare_itineraries = []
        mock_flight_service.revalidate_fare = AsyncMock(return_value=mock_response)

        with pytest.raises(HTTPException) as exc_info:
            await select_flight_for_booking(
                sample_flight_selection_request, mock_flight_service
            )

        assert exc_info.value.status_code == 500
        assert "no itinerary data" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("app.domains.booking_sessions.service.BookingSessionService")
    @patch("app.api.flights.logger")
    async def test_session_storage_failure_returns_500(
        self,
        mock_logger,
        mock_booking_session_service,
        sample_flight_selection_request,
        mock_flight_service,
        mock_revalidate_response,
    ):
        """Test that session storage failure returns HTTP 500."""
        mock_settings = patch("app.api.flights.settings")
        mock_settings.BACKEND_URL = "http://localhost:8000"

        # Mock revalidate_fare
        mock_flight_service.revalidate_fare = AsyncMock(
            return_value=mock_revalidate_response
        )

        # Mock BookingSessionService.store_session to fail
        mock_booking_session_service.store_session = AsyncMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await select_flight_for_booking(
                sample_flight_selection_request, mock_flight_service
            )

        assert exc_info.value.status_code == 500
        assert "Failed to create booking session" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.domains.booking_sessions.service.BookingSessionService")
    @patch("app.api.flights.settings")
    @patch("app.api.flights.logger")
    async def test_generic_exception_returns_500(
        self,
        mock_logger,
        mock_settings,
        mock_booking_session_service,
        sample_flight_selection_request,
        mock_flight_service,
    ):
        """Test that generic exceptions are converted to HTTP 500."""
        mock_settings.BACKEND_URL = "http://localhost:8000"

        # Mock revalidate_fare to raise exception
        mock_flight_service.revalidate_fare = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        with pytest.raises(HTTPException) as exc_info:
            await select_flight_for_booking(
                sample_flight_selection_request, mock_flight_service
            )

        assert exc_info.value.status_code == 500
        assert "Failed to select flight" in exc_info.value.detail

        # Should log error
        mock_logger.error.assert_called_once()
        assert "Failed to select flight" in str(mock_logger.error.call_args)
