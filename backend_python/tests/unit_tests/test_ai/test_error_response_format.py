"""Unit tests for error response format.

Tests that error responses include both technical and user-friendly messages.
Part of Issue #276: Improve FlightLogic Error Handling in Booker UI and AI Chat
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.utils.error_message_generator import generate_error_message
from app.domains.flight.exceptions import FlightSearchError


class TestErrorResponseFormat:
    """Test error response format includes required fields."""

    @pytest.mark.asyncio
    async def test_flight_search_error_response_format(self):
        """Test flight search error response includes all required fields."""
        error = FlightSearchError(reason="No flights found")

        # Simulate error handling logic from enhanced_flight_handler
        error_type = "FLIGHT_SEARCH_ERROR"
        error_message = error.reason or str(error)
        error_code = error.code

        # Mock LLM service
        mock_llm_service = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = (
            "I couldn't find any flights. Would you like to try different dates?"
        )
        mock_llm_service.generate_content = AsyncMock(return_value=mock_response)

        with patch(
            "app.ai.utils.error_message_generator.get_llm_service",
            return_value=mock_llm_service,
        ):
            user_friendly_message = await generate_error_message(
                error_type=error_type,
                error_message=error_message,
                operation="search",
                error_code=error_code,
            )

        # Build response (simulating enhanced_flight_handler)
        response = {
            "message": user_friendly_message,
            "type": "search_error",
            "error": str(error),  # Technical error for logging
            "error_type": error_type,  # Include error type for frontend
            "can_retry": True,
        }

        # Verify all required fields are present
        assert "message" in response
        assert "type" in response
        assert "error" in response
        assert "error_type" in response
        assert "can_retry" in response

        # Verify message is user-friendly
        assert (
            "couldn't find" in response["message"].lower()
            or "flights" in response["message"].lower()
        )

        # Verify technical error is preserved
        assert "No flights found" in response["error"]

        # Verify error type is included
        assert response["error_type"] == "FLIGHT_SEARCH_ERROR"

    @pytest.mark.asyncio
    async def test_hotel_search_error_response_format(self):
        """Test hotel search error response includes all required fields."""
        from app.domains.hotel.exceptions import HotelSearchError

        error = HotelSearchError(reason="No hotels found")

        # Simulate error handling logic from enhanced_hotel_handler
        error_type = "HOTEL_SEARCH_ERROR"
        error_message = error.message if hasattr(error, "message") else str(error)
        error_code = error.code if hasattr(error, "code") else None

        # Mock LLM service
        mock_llm_service = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = (
            "I couldn't find any hotels. Would you like to try a different location?"
        )
        mock_llm_service.generate_content = AsyncMock(return_value=mock_response)

        with patch(
            "app.ai.utils.error_message_generator.get_llm_service",
            return_value=mock_llm_service,
        ):
            user_friendly_message = await generate_error_message(
                error_type=error_type,
                error_message=error_message,
                operation="search",
                error_code=error_code,
            )

        # Build response (simulating enhanced_hotel_handler)
        response = {
            "message": user_friendly_message,
            "type": "search_error",
            "error": str(error),  # Technical error for logging
            "error_type": error_type,  # Include error type for frontend
        }

        # Verify all required fields are present
        assert "message" in response
        assert "type" in response
        assert "error" in response
        assert "error_type" in response

        # Verify message is user-friendly
        assert (
            "couldn't find" in response["message"].lower()
            or "hotels" in response["message"].lower()
        )

        # Verify technical error is preserved
        assert "No hotels found" in response["error"]

        # Verify error type is included
        assert response["error_type"] == "HOTEL_SEARCH_ERROR"

    @pytest.mark.asyncio
    async def test_error_response_with_llm_fallback(self):
        """Test error response format when LLM fails."""
        error = FlightSearchError(reason="Connection timeout")

        # Simulate error handling with LLM failure
        error_type = "FLIGHT_SEARCH_ERROR"
        error_message = error.reason or str(error)

        # Mock LLM service to fail
        mock_llm_service = AsyncMock()
        mock_llm_service.generate_content = AsyncMock(
            side_effect=Exception("LLM unavailable")
        )

        with patch(
            "app.ai.utils.error_message_generator.get_llm_service",
            return_value=mock_llm_service,
        ):
            user_friendly_message = await generate_error_message(
                error_type=error_type,
                error_message=error_message,
                operation="search",
            )

        # Build response
        response = {
            "message": user_friendly_message,
            "type": "search_error",
            "error": str(error),
            "error_type": error_type,
        }

        # Verify fallback message is used
        assert (
            "encountered an issue" in response["message"].lower()
            or "try again" in response["message"].lower()
        )

        # Verify technical error is still preserved
        assert "Connection timeout" in response["error"]

        # Verify error type is still included
        assert response["error_type"] == "FLIGHT_SEARCH_ERROR"

    @pytest.mark.asyncio
    async def test_tools_error_response_format(self):
        """Test error response format from tools (flights.py, hotels.py)."""
        error = FlightSearchError(reason="Invalid airport code")

        # Simulate error handling logic from tools/flights.py
        error_type = "FLIGHT_SEARCH_ERROR"
        error_message = error.reason or str(error)
        error_code = error.code

        # Mock LLM service
        mock_llm_service = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "Please check your airport codes and try again."
        mock_llm_service.generate_content = AsyncMock(return_value=mock_response)

        with patch(
            "app.ai.utils.error_message_generator.get_llm_service",
            return_value=mock_llm_service,
        ):
            user_friendly_message = await generate_error_message(
                error_type=error_type,
                error_message=error_message,
                operation="search",
                error_code=error_code,
            )

        # Build response (simulating tools/flights.py)
        response = {
            "status": "error",
            "error": error_message,  # Technical error for logging
            "error_type": error_type,
            "message": user_friendly_message,  # LLM-generated user-friendly message
            "instruction": "Inform the user about the error and suggest next steps.",
        }

        # Verify all required fields are present
        assert "status" in response
        assert "error" in response
        assert "error_type" in response
        assert "message" in response
        assert "instruction" in response

        # Verify status is "error"
        assert response["status"] == "error"

        # Verify both technical and user-friendly messages
        assert "Invalid airport code" in response["error"]
        assert (
            "airport codes" in response["message"].lower()
            or "try again" in response["message"].lower()
        )
