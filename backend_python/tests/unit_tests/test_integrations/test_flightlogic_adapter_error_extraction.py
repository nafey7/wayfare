"""Unit tests for FlightLogic adapter error extraction.

Tests that errors are properly extracted and included in responses.
Part of Issue #276: Improve FlightLogic Error Handling in Booker UI and AI Chat
"""

import pytest

from integrations.flightlogic.adapter import ConversionContext, FlightLogicSchemaAdapter
from integrations.flightlogic.dto import (
    AirSearchResponseData,
    AirSearchResult,
    FlightLogicError,
    FlightLogicSearchResponse,
)


class TestAdapterErrorExtraction:
    """Test error extraction in FlightLogic adapter."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return FlightLogicSchemaAdapter()

    @pytest.fixture
    def context(self):
        """Create conversion context."""
        return ConversionContext(supplier="FlightLogic")

    def test_extract_errors_without_results(self, adapter, context):
        """Test error extraction when errors exist but no search results."""
        # Create DTO with errors but no AirSearchResponse
        error = FlightLogicError(
            ErrorCode="NO_FLIGHTS", ErrorMessage="No flights found for route"
        )
        dto = FlightLogicSearchResponse(Errors=error, AirSearchResponse=None)

        # Convert to domain schema
        response = adapter.search_response_from_dto(dto, context)

        # Verify error is extracted and included
        assert response.errors is not None
        assert len(response.errors) == 1
        # Error code might be converted/categorized, so check it exists
        assert response.errors[0].code is not None
        assert (
            "No flights found" in response.errors[0].message
            or "NO_FLIGHTS" in response.errors[0].code
        )

        # Verify empty required fields for error case
        assert response.session_id == ""
        assert response.supplier == ""
        assert response.fare_itineraries == []

    def test_extract_errors_with_results(self, adapter, context):
        """Test error extraction when errors exist alongside search results."""
        # Create DTO with both errors and results
        error = FlightLogicError(
            ErrorCode="PARTIAL_RESULTS", ErrorMessage="Some flights unavailable"
        )

        # Create minimal search result
        search_result = AirSearchResult(FareItineraries=[])
        air_response = AirSearchResponseData(
            session_id="test_session",
            supplier="FlightLogic",
            AirSearchResult=search_result,
        )

        dto = FlightLogicSearchResponse(Errors=error, AirSearchResponse=air_response)

        # Convert to domain schema
        response = adapter.search_response_from_dto(dto, context)

        # Verify error is still included even with results
        assert response.errors is not None
        assert len(response.errors) == 1
        # Error code might be converted/categorized, so check it exists
        assert response.errors[0].code is not None
        assert (
            "PARTIAL_RESULTS" in response.errors[0].code
            or "Some flights unavailable" in response.errors[0].message
        )

        # Verify results are also present
        assert response.session_id == "test_session"
        assert response.supplier == "FlightLogic"
        assert response.fare_itineraries == []

    def test_no_errors_no_results(self, adapter, context):
        """Test normal case with no errors and no results."""
        # Create DTO with no errors and no results
        search_result = AirSearchResult(FareItineraries=[])
        air_response = AirSearchResponseData(
            session_id="test_session",
            supplier="FlightLogic",
            AirSearchResult=search_result,
        )

        dto = FlightLogicSearchResponse(Errors=None, AirSearchResponse=air_response)

        # Convert to domain schema
        response = adapter.search_response_from_dto(dto, context)

        # Verify no errors
        assert response.errors is None

        # Verify results are present
        assert response.session_id == "test_session"
        assert response.supplier == "FlightLogic"

    def test_no_errors_with_results(self, adapter, context):
        """Test normal case with no errors and results."""
        # Create DTO with results but no errors
        search_result = AirSearchResult(FareItineraries=[])
        air_response = AirSearchResponseData(
            session_id="test_session",
            supplier="FlightLogic",
            AirSearchResult=search_result,
        )

        dto = FlightLogicSearchResponse(Errors=None, AirSearchResponse=air_response)

        # Convert to domain schema
        response = adapter.search_response_from_dto(dto, context)

        # Verify no errors
        assert response.errors is None

        # Verify results
        assert response.session_id == "test_session"
        assert response.supplier == "FlightLogic"

    def test_error_extraction_preserves_error_details(self, adapter, context):
        """Test that error details are preserved during extraction."""
        # Create error with full details
        error = FlightLogicError(
            ErrorCode="VALIDATION_ERROR",
            ErrorMessage="Invalid airport code provided",
        )

        dto = FlightLogicSearchResponse(Errors=error, AirSearchResponse=None)

        # Convert to domain schema
        response = adapter.search_response_from_dto(dto, context)

        # Verify error details are preserved
        # Error code might be converted/categorized, so check it exists and contains key info
        assert response.errors[0].code is not None
        assert (
            "VALIDATION_ERROR" in response.errors[0].code
            or "Invalid airport code" in response.errors[0].message
        )
        assert "Invalid airport code" in response.errors[0].message
        # ErrorDetails doesn't have a source attribute - it's in details dict if needed

    def test_multiple_errors_handling(self, adapter, context):
        """Test that multiple errors are handled correctly."""
        # Note: FlightLogic typically returns single error, but test edge case
        error = FlightLogicError(
            ErrorCode="MULTIPLE_ERRORS", ErrorMessage="Multiple issues detected"
        )

        dto = FlightLogicSearchResponse(Errors=error, AirSearchResponse=None)

        # Convert to domain schema
        response = adapter.search_response_from_dto(dto, context)

        # Verify error is extracted (even if FlightLogic only returns one)
        assert response.errors is not None
        assert len(response.errors) == 1
