"""Unit tests for error message generator.

Tests the LLM-powered error message generation functionality for FlightLogic API errors.
Part of Issue #276: Improve FlightLogic Error Handling in Booker UI and AI Chat
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.utils.error_message_generator import (
    _categorize_error_for_llm,
    generate_error_message,
)


class TestErrorCategorization:
    """Test error categorization logic."""

    def test_categorize_authentication_error(self):
        """Test authentication/configuration errors are categorized correctly."""
        category = _categorize_error_for_llm(
            "INVALID_USER", "Invalid user_id/user_password"
        )
        assert "authentication/configuration error" in category
        assert "system issue" in category

    def test_categorize_validation_error(self):
        """Test validation errors are categorized correctly."""
        category = _categorize_error_for_llm("VALIDATION_ERROR", "Invalid date format")
        assert "validation error" in category
        assert "check user input" in category

    def test_categorize_no_results_error(self):
        """Test no results errors are categorized correctly."""
        category = _categorize_error_for_llm(None, "No flights found for route")
        assert "no results found" in category
        assert "search criteria" in category

    def test_categorize_session_error(self):
        """Test session/timeout errors are categorized correctly."""
        category = _categorize_error_for_llm("SESSION_EXPIRED", "Session has expired")
        assert "session/timeout error" in category
        assert "retry" in category

    def test_categorize_rate_limit_error(self):
        """Test rate limit errors are categorized correctly."""
        category = _categorize_error_for_llm("RATE_LIMIT", "Too many requests")
        assert "rate limit error" in category
        assert "wait and retry" in category

    def test_categorize_general_error(self):
        """Test general errors fall back to generic category."""
        category = _categorize_error_for_llm("UNKNOWN", "Something went wrong")
        assert category == "general error"

    def test_categorize_empty_error(self):
        """Test empty error returns unknown category."""
        category = _categorize_error_for_llm(None, "")
        assert category == "unknown error"


class TestGenerateErrorMessage:
    """Test error message generation with LLM."""

    @pytest.mark.asyncio
    async def test_generate_message_success(self):
        """Test successful LLM message generation."""
        mock_llm_service = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "I couldn't find any flights for that route. Would you like to try different dates?"
        mock_llm_service.generate_content = AsyncMock(return_value=mock_response)

        with patch(
            "app.ai.utils.error_message_generator.get_llm_service",
            return_value=mock_llm_service,
        ):
            message = await generate_error_message(
                error_type="FLIGHT_SEARCH_ERROR",
                error_message="No flights found",
                operation="search",
            )

        assert "couldn't find" in message.lower() or "flights" in message.lower()
        mock_llm_service.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_message_with_error_code(self):
        """Test message generation includes error code in prompt."""
        mock_llm_service = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "We're experiencing a temporary issue. Please try again."
        mock_llm_service.generate_content = AsyncMock(return_value=mock_response)

        with patch(
            "app.ai.utils.error_message_generator.get_llm_service",
            return_value=mock_llm_service,
        ):
            await generate_error_message(
                error_type="FLIGHT_API_ERROR",
                error_message="Invalid credentials",
                operation="search",
                error_code="INVALID_USER",
                status_code=401,
            )

        # Verify prompt includes error code
        call_args = mock_llm_service.generate_content.call_args[0][0]
        assert "INVALID_USER" in call_args
        assert "401" in call_args

    @pytest.mark.asyncio
    async def test_generate_message_with_additional_context(self):
        """Test message generation includes additional context."""
        mock_llm_service = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "Error message"
        mock_llm_service.generate_content = AsyncMock(return_value=mock_response)

        with patch(
            "app.ai.utils.error_message_generator.get_llm_service",
            return_value=mock_llm_service,
        ):
            await generate_error_message(
                error_type="FLIGHT_SEARCH_ERROR",
                error_message="No flights",
                operation="search",
                additional_context={"origin": "AMS", "destination": "LHR"},
            )

        # Verify context is included in prompt
        call_args = mock_llm_service.generate_content.call_args[0][0]
        assert "AMS" in call_args
        assert "LHR" in call_args

    @pytest.mark.asyncio
    async def test_generate_message_removes_quotes(self):
        """Test that quotes are removed from LLM response."""
        mock_llm_service = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = '"I couldn\'t find any flights. Try again?"'
        mock_llm_service.generate_content = AsyncMock(return_value=mock_response)

        with patch(
            "app.ai.utils.error_message_generator.get_llm_service",
            return_value=mock_llm_service,
        ):
            message = await generate_error_message(
                error_type="FLIGHT_SEARCH_ERROR",
                error_message="No flights found",
                operation="search",
            )

        # Quotes should be removed
        assert not message.startswith('"')
        assert not message.endswith('"')
        assert "couldn't find" in message.lower()

    @pytest.mark.asyncio
    async def test_generate_message_llm_failure_fallback(self):
        """Test fallback message when LLM service fails."""
        mock_llm_service = AsyncMock()
        mock_llm_service.generate_content = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )

        with patch(
            "app.ai.utils.error_message_generator.get_llm_service",
            return_value=mock_llm_service,
        ):
            message = await generate_error_message(
                error_type="FLIGHT_SEARCH_ERROR",
                error_message="No flights found",
                operation="search",
            )

        # Should return fallback message
        assert (
            "encountered an issue" in message.lower() or "try again" in message.lower()
        )
        assert "search" in message.lower() or "searching" in message.lower()

    @pytest.mark.asyncio
    async def test_generate_message_different_operations(self):
        """Test message generation for different operations."""
        mock_llm_service = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "Booking failed"
        mock_llm_service.generate_content = AsyncMock(return_value=mock_response)

        with patch(
            "app.ai.utils.error_message_generator.get_llm_service",
            return_value=mock_llm_service,
        ):
            # Test booking operation
            await generate_error_message(
                error_type="FLIGHT_BOOKING_ERROR",
                error_message="Booking failed",
                operation="booking",
            )

            call_args = mock_llm_service.generate_content.call_args[0][0]
            assert "booking" in call_args.lower()

            # Test validation operation
            await generate_error_message(
                error_type="FLIGHT_VALIDATION_ERROR",
                error_message="Invalid input",
                operation="validation",
            )

            call_args = mock_llm_service.generate_content.call_args[0][0]
            assert (
                "validating" in call_args.lower() or "validation" in call_args.lower()
            )

    @pytest.mark.asyncio
    async def test_generate_message_hotel_errors(self):
        """Test message generation for hotel-specific errors."""
        mock_llm_service = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "Hotel search error"
        mock_llm_service.generate_content = AsyncMock(return_value=mock_response)

        with patch(
            "app.ai.utils.error_message_generator.get_llm_service",
            return_value=mock_llm_service,
        ):
            message = await generate_error_message(
                error_type="HOTEL_SEARCH_ERROR",
                error_message="No hotels found",
                operation="search",
            )

        assert message is not None
        call_args = mock_llm_service.generate_content.call_args[0][0]
        assert "HOTEL_SEARCH_ERROR" in call_args
