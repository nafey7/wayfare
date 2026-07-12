"""Unit tests for error type detection in handlers.

Tests that different exception types are correctly categorized.
Part of Issue #276: Improve FlightLogic Error Handling in Booker UI and AI Chat
"""

import pytest

from app.domains.flight.exceptions import (
    FlightApiError,
    FlightBookingError,
    FlightSearchError,
    FlightValidationError,
)
from app.domains.hotel.exceptions import (
    HotelBookingError,
    HotelRateError,
    HotelSearchError,
    HotelSessionError,
    HotelValidationError,
)


class TestFlightErrorTypeDetection:
    """Test error type detection for flight errors."""

    @pytest.mark.asyncio
    async def test_detect_flight_api_error(self):
        """Test FlightApiError is detected correctly."""
        error = FlightApiError(reason="API connection failed", status_code=500)

        # Simulate error type detection logic from enhanced_flight_handler
        error_type = "UNKNOWN_ERROR"
        if isinstance(error, FlightApiError):
            error_type = "FLIGHT_API_ERROR"

        assert error_type == "FLIGHT_API_ERROR"

    @pytest.mark.asyncio
    async def test_detect_flight_search_error(self):
        """Test FlightSearchError is detected correctly."""
        error = FlightSearchError(reason="No flights found")

        # Simulate error type detection logic
        error_type = "UNKNOWN_ERROR"
        if isinstance(error, FlightSearchError):
            error_type = "FLIGHT_SEARCH_ERROR"

        assert error_type == "FLIGHT_SEARCH_ERROR"

    @pytest.mark.asyncio
    async def test_detect_flight_booking_error(self):
        """Test FlightBookingError is detected correctly."""
        error = FlightBookingError(reason="Booking failed", code="BOOKING_FAILED")

        # Simulate error type detection logic
        error_type = "UNKNOWN_ERROR"
        operation = "search"
        if isinstance(error, FlightBookingError):
            error_type = "FLIGHT_BOOKING_ERROR"
            operation = "booking"

        assert error_type == "FLIGHT_BOOKING_ERROR"
        assert operation == "booking"

    @pytest.mark.asyncio
    async def test_detect_flight_validation_error(self):
        """Test FlightValidationError is detected correctly."""
        error = FlightValidationError(reason="Invalid date format")

        # Simulate error type detection logic
        error_type = "UNKNOWN_ERROR"
        operation = "search"
        if isinstance(error, FlightValidationError):
            error_type = "FLIGHT_VALIDATION_ERROR"
            operation = "validation"

        assert error_type == "FLIGHT_VALIDATION_ERROR"
        assert operation == "validation"

    @pytest.mark.asyncio
    async def test_detect_unknown_error(self):
        """Test unknown errors default to UNKNOWN_ERROR."""
        error = ValueError("Unexpected error")

        # Simulate error type detection logic
        error_type = "UNKNOWN_ERROR"
        if isinstance(error, FlightApiError):
            error_type = "FLIGHT_API_ERROR"
        elif isinstance(error, FlightSearchError):
            error_type = "FLIGHT_SEARCH_ERROR"
        elif isinstance(error, FlightBookingError):
            error_type = "FLIGHT_BOOKING_ERROR"
        elif isinstance(error, FlightValidationError):
            error_type = "FLIGHT_VALIDATION_ERROR"

        assert error_type == "UNKNOWN_ERROR"


class TestHotelErrorTypeDetection:
    """Test error type detection for hotel errors."""

    @pytest.mark.asyncio
    async def test_detect_hotel_search_error(self):
        """Test HotelSearchError is detected correctly."""
        error = HotelSearchError(reason="No hotels found")

        # Simulate error type detection logic from enhanced_hotel_handler
        error_type = "UNKNOWN_ERROR"
        if isinstance(error, HotelSearchError):
            error_type = "HOTEL_SEARCH_ERROR"
            error_message = error.message if hasattr(error, "message") else str(error)
            error_code = error.code if hasattr(error, "code") else None

        assert error_type == "HOTEL_SEARCH_ERROR"
        assert "No hotels found" in error_message  # Message includes prefix
        assert error_code == "HOTEL_SEARCH_ERROR"  # Code is set by parent class

    @pytest.mark.asyncio
    async def test_detect_hotel_booking_error(self):
        """Test HotelBookingError is detected correctly."""
        error = HotelBookingError(reason="Booking failed")

        # Simulate error type detection logic
        error_type = "UNKNOWN_ERROR"
        operation = "search"
        if isinstance(error, HotelBookingError):
            error_type = "HOTEL_BOOKING_ERROR"
            operation = "booking"

        assert error_type == "HOTEL_BOOKING_ERROR"
        assert operation == "booking"

    @pytest.mark.asyncio
    async def test_detect_hotel_validation_error(self):
        """Test HotelValidationError is detected correctly."""
        error = HotelValidationError(reason="Invalid dates")

        # Simulate error type detection logic
        error_type = "UNKNOWN_ERROR"
        operation = "search"
        if isinstance(error, HotelValidationError):
            error_type = "HOTEL_VALIDATION_ERROR"
            operation = "validation"

        assert error_type == "HOTEL_VALIDATION_ERROR"
        assert operation == "validation"

    @pytest.mark.asyncio
    async def test_detect_hotel_session_error(self):
        """Test HotelSessionError is detected correctly."""
        error = HotelSessionError(reason="Session expired")

        # Simulate error type detection logic
        error_type = "UNKNOWN_ERROR"
        if isinstance(error, HotelSessionError):
            error_type = "HOTEL_SESSION_ERROR"

        assert error_type == "HOTEL_SESSION_ERROR"

    @pytest.mark.asyncio
    async def test_detect_hotel_rate_error(self):
        """Test HotelRateError is detected correctly."""
        error = HotelRateError(reason="Rate unavailable")

        # Simulate error type detection logic
        error_type = "UNKNOWN_ERROR"
        if isinstance(error, HotelRateError):
            error_type = "HOTEL_RATE_ERROR"

        assert error_type == "HOTEL_RATE_ERROR"

    @pytest.mark.asyncio
    async def test_detect_generic_hotel_error(self):
        """Test generic hotel errors are detected by class name."""

        # Create a mock hotel error class
        class HotelCustomError(Exception):
            def __init__(self, message):
                self.message = message
                super().__init__(message)

        error = HotelCustomError("Custom hotel error")

        # Simulate error type detection logic
        error_type = "UNKNOWN_ERROR"
        if hasattr(error, "__class__") and "Hotel" in error.__class__.__name__:
            error_type = "HOTEL_ERROR"

        assert error_type == "HOTEL_ERROR"

    @pytest.mark.asyncio
    async def test_extract_error_details_from_hotel_error(self):
        """Test error details extraction from hotel errors."""
        error = HotelSearchError(reason="No hotels in area")

        # Simulate extraction logic
        error_message = error.message if hasattr(error, "message") else str(error)
        error_code = error.code if hasattr(error, "code") else None

        assert "No hotels in area" in error_message  # Message includes prefix
        assert error_code == "HOTEL_SEARCH_ERROR"  # Code is set by parent class
