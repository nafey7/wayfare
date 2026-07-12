"""Unit tests for hotel adapter methods.

Tests conversion between domain models and FlightLogic DTOs for:
- Cancel booking requests/responses
- More results requests/responses
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.domains.hotel.schemas import (
    HotelCancelRequest,
    HotelCancelResponse,
    HotelMoreResultsRequest,
    HotelSearchResponse,
    HotelSearchResult,
)
from integrations.flightlogic.hotel_adapter import HotelSchemaAdapter
from integrations.flightlogic.hotel_dto import (
    HotelCancelRequestDTO,
    HotelCancelResponseDTO,
    HotelMoreResultsItineraryDTO,
    HotelMoreResultsRequestDTO,
    HotelMoreResultsResponseDTO,
    StatusMoreResultsDTO,
)


@pytest.fixture
def mock_settings():
    """Mock settings with test credentials."""
    settings = MagicMock()
    settings.FLIGHTLOGIC_USER_ID = "test_user"  # pragma: allowlist secret
    settings.FLIGHTLOGIC_PASSWORD = "test_pass"  # pragma: allowlist secret
    settings.FLIGHTLOGIC_ACCESS_TYPE = "Test"
    settings.FLIGHTLOGIC_IP_ADDRESS = "192.168.1.1"
    return settings


# ==============================================================================
# CANCEL BOOKING ADAPTER TESTS
# ==============================================================================


class TestCancelRequestAdapter:
    """Test cancel_request_to_dto adapter method."""

    @patch("app.core.config.settings")
    def test_cancel_request_to_dto_conversion(self, mock_settings_obj):
        """Test converting domain cancel request to DTO."""
        # Configure mock settings
        mock_settings_obj.FLIGHTLOGIC_USER_ID = "test_user"  # pragma: allowlist secret
        mock_settings_obj.FLIGHTLOGIC_PASSWORD = "test_pass"  # pragma: allowlist secret
        mock_settings_obj.FLIGHTLOGIC_ACCESS_TYPE = "Test"
        mock_settings_obj.FLIGHTLOGIC_IP_ADDRESS = "192.168.1.1"

        adapter = HotelSchemaAdapter()

        domain_request = HotelCancelRequest(
            supplier_confirmation_num="SUP123456",
            reference_num="REF789012",
        )

        dto = adapter.cancel_request_to_dto(domain_request)

        assert isinstance(dto, HotelCancelRequestDTO)
        assert dto.supplierConfirmationNum == "SUP123456"
        assert dto.referenceNum == "REF789012"
        # Credentials should be injected from settings
        assert dto.user_id == "test_user"
        assert dto.user_password == "test_pass"  # pragma: allowlist secret
        assert dto.access == "Test"
        assert dto.ip_address == "192.168.1.1"

    @patch("app.core.config.settings")
    def test_cancel_request_to_dto_with_credentials(self, mock_settings_obj):
        """Test cancel request conversion includes credentials from config."""
        # Configure mock settings
        mock_settings_obj.FLIGHTLOGIC_USER_ID = "test_user"  # pragma: allowlist secret
        mock_settings_obj.FLIGHTLOGIC_PASSWORD = "test_pass"  # pragma: allowlist secret
        mock_settings_obj.FLIGHTLOGIC_ACCESS_TYPE = "Test"
        mock_settings_obj.FLIGHTLOGIC_IP_ADDRESS = "192.168.1.1"

        adapter = HotelSchemaAdapter()

        domain_request = HotelCancelRequest(
            supplier_confirmation_num="SUP123456",
            reference_num="REF789012",
        )

        dto = adapter.cancel_request_to_dto(domain_request)

        # Verify credentials are injected
        assert dto.user_id == "test_user"
        assert dto.user_password == "test_pass"  # pragma: allowlist secret
        assert dto.access == "Test"
        assert dto.ip_address == "192.168.1.1"


class TestCancelResponseAdapter:
    """Test cancel_response_from_dto adapter method."""

    def test_cancel_response_from_dto_success(self):
        """Test converting successful cancellation DTO to domain model."""
        adapter = HotelSchemaAdapter()

        dto = HotelCancelResponseDTO(
            status="CANCELLED",
            cancelReferenceNum="CANCEL123456",
            message="Booking cancelled successfully",
        )

        domain_response = adapter.cancel_response_from_dto(dto)

        assert isinstance(domain_response, HotelCancelResponse)
        assert domain_response.status == "CANCELLED"
        assert domain_response.cancel_reference_num == "CANCEL123456"
        assert domain_response.message == "Booking cancelled successfully"
        assert domain_response.errors is None

    def test_cancel_response_from_dto_failure(self):
        """Test converting failed cancellation DTO to domain model."""
        adapter = HotelSchemaAdapter()

        dto = HotelCancelResponseDTO(
            status="FAILED",
            cancelReferenceNum=None,
            message="Cancellation failed: Booking not found",
        )

        domain_response = adapter.cancel_response_from_dto(dto)

        assert isinstance(domain_response, HotelCancelResponse)
        assert domain_response.status == "FAILED"
        assert domain_response.cancel_reference_num is None
        assert domain_response.message == "Cancellation failed: Booking not found"
        assert domain_response.errors is not None
        assert domain_response.errors["code"] == "CANCELLATION_FAILED"
        assert "Booking not found" in domain_response.errors["message"]

    def test_cancel_response_from_dto_failure_without_message(self):
        """Test converting failed cancellation DTO without message."""
        adapter = HotelSchemaAdapter()

        dto = HotelCancelResponseDTO(
            status="FAILED",
            cancelReferenceNum=None,
            message="",
        )

        domain_response = adapter.cancel_response_from_dto(dto)

        assert domain_response.status == "FAILED"
        assert domain_response.errors is not None
        assert "FAILED" in domain_response.errors["message"]


# ==============================================================================
# MORE RESULTS ADAPTER TESTS
# ==============================================================================


class TestMoreResultsRequestAdapter:
    """Test more_results_request_to_dto adapter method."""

    def test_more_results_request_to_dto_conversion(self):
        """Test converting domain more results request to DTO."""
        adapter = HotelSchemaAdapter()

        domain_request = HotelMoreResultsRequest(
            session_id="test_session_12345",
            next_token="next_token_abc123",
            max_result=20,
        )

        dto = adapter.more_results_request_to_dto(domain_request)

        assert isinstance(dto, HotelMoreResultsRequestDTO)
        assert dto.sessionId == "test_session_12345"
        assert dto.nextToken == "next_token_abc123"
        assert dto.maxResult == 20

    def test_more_results_request_to_dto_default_max_result(self):
        """Test that max_result defaults are handled correctly."""
        adapter = HotelSchemaAdapter()

        domain_request = HotelMoreResultsRequest(
            session_id="test_session",
            next_token="next_token",
            # max_result not specified, should use default
        )

        dto = adapter.more_results_request_to_dto(domain_request)

        assert dto.maxResult == 20  # Default value

    def test_more_results_request_to_dto_custom_max_result(self):
        """Test custom max_result value."""
        adapter = HotelSchemaAdapter()

        domain_request = HotelMoreResultsRequest(
            session_id="test_session",
            next_token="next_token",
            max_result=50,
        )

        dto = adapter.more_results_request_to_dto(domain_request)

        assert dto.maxResult == 50


class TestMoreResultsResponseAdapter:
    """Test more_results_response_from_dto adapter method."""

    def test_more_results_response_from_dto_conversion(self):
        """Test converting more results DTO to domain model."""
        adapter = HotelSchemaAdapter()

        dto = HotelMoreResultsResponseDTO(
            status=StatusMoreResultsDTO(
                sessionId="test_session_12345",
                moreResults=False,
                nextToken="",
            ),
            itineraries=[],
        )

        domain_response = adapter.more_results_response_from_dto(dto)

        assert isinstance(domain_response, HotelSearchResponse)
        assert domain_response.session_id == "test_session_12345"
        assert domain_response.more_results is False
        assert domain_response.next_token == ""
        assert len(domain_response.itineraries) == 0
        assert domain_response.total_results == 0  # Count of itineraries

    def test_more_results_response_with_hotels(self):
        """Test converting more results DTO with hotel data."""
        adapter = HotelSchemaAdapter()

        itinerary_dto = HotelMoreResultsItineraryDTO(
            hotelId="123",
            twxHotelId=123,
            productId="PROD001",
            tokenId="token_001",
            hotelName="Test Hotel",
            city="London",
            locality="",
            address="123 Test St",
            country="UK",
            countryCode="GB",
            postalCode="SW1A 1AA",
            latitude="51.5074",
            longitude="-0.1278",
            distanceValue=2.5,
            distanceUnit="KM",
            total=150.00,  # Numeric, not string
            currency="USD",
            fareType="Refundable",
            hotelRating=4,
            propertyType="Hotel",
            facilities=["WiFi", "Parking"],
            thumbNailUrl="https://example.com/thumb.jpg",
            phone="+44-20-1234567",
            email="info@testhotel.com",
            tripAdvisorRating=4.5,
            tripAdvisorReview=100,
            special="",
        )

        dto = HotelMoreResultsResponseDTO(
            status=StatusMoreResultsDTO(
                sessionId="test_session_12345",
                moreResults=True,
                nextToken="next_token_xyz",
            ),
            itineraries=[itinerary_dto],
        )

        domain_response = adapter.more_results_response_from_dto(dto)

        assert isinstance(domain_response, HotelSearchResponse)
        assert domain_response.session_id == "test_session_12345"
        assert domain_response.more_results is True
        assert domain_response.next_token == "next_token_xyz"
        assert len(domain_response.itineraries) == 1
        assert domain_response.total_results == 1

        # Verify hotel conversion
        hotel = domain_response.itineraries[0]
        assert isinstance(hotel, HotelSearchResult)
        assert hotel.hotel_id == "123"
        assert hotel.hotel_name == "Test Hotel"
        assert hotel.total == Decimal("150.00")
        assert hotel.currency == "USD"
        # MoreResults API doesn't provide perNightArray
        assert len(hotel.per_night_array) == 0

    def test_more_results_response_twx_hotel_id_as_string(self):
        """Test that twxHotelId is converted to string even if API returns int."""
        adapter = HotelSchemaAdapter()

        itinerary_dto = HotelMoreResultsItineraryDTO(
            hotelId="123",
            twxHotelId=123,  # API returns int
            productId="PROD001",
            tokenId="token_001",
            hotelName="Test Hotel",
            city="London",
            locality="",
            address="123 Test St",
            country="UK",
            countryCode="GB",
            postalCode="SW1A 1AA",
            latitude="51.5074",
            longitude="-0.1278",
            distanceValue=2.5,
            distanceUnit="KM",
            total=150.00,
            currency="USD",
            fareType="Refundable",
            hotelRating=4,
            propertyType="Hotel",
            facilities=[],
            thumbNailUrl="https://example.com/thumb.jpg",
            phone="+44-20-1234567",
            email="info@testhotel.com",
            tripAdvisorRating=4.5,
            tripAdvisorReview=100,
            special="",
        )

        dto = HotelMoreResultsResponseDTO(
            status=StatusMoreResultsDTO(
                sessionId="test_session",
                moreResults=False,
                nextToken="",
            ),
            itineraries=[itinerary_dto],
        )

        domain_response = adapter.more_results_response_from_dto(dto)

        # twx_hotel_id should be converted to string
        assert domain_response.itineraries[0].twx_hotel_id == "123"
        assert isinstance(domain_response.itineraries[0].twx_hotel_id, str)

    def test_more_results_response_trip_advisor_review_as_string(self):
        """Test that tripAdvisorReview is converted from string to int."""
        adapter = HotelSchemaAdapter()

        itinerary_dto = HotelMoreResultsItineraryDTO(
            hotelId="123",
            twxHotelId="123",
            productId="PROD001",
            tokenId="token_001",
            hotelName="Test Hotel",
            city="London",
            locality="",
            address="123 Test St",
            country="UK",
            countryCode="GB",
            postalCode="SW1A 1AA",
            latitude="51.5074",
            longitude="-0.1278",
            distanceValue=2.5,
            distanceUnit="KM",
            total=150.00,
            currency="USD",
            fareType="Refundable",
            hotelRating=4,
            propertyType="Hotel",
            facilities=[],
            thumbNailUrl="https://example.com/thumb.jpg",
            phone="+44-20-1234567",
            email="info@testhotel.com",
            tripAdvisorRating=4.5,
            tripAdvisorReview="100",  # String from API
            special="",
        )

        dto = HotelMoreResultsResponseDTO(
            status=StatusMoreResultsDTO(
                sessionId="test_session",
                moreResults=False,
                nextToken="",
            ),
            itineraries=[itinerary_dto],
        )

        domain_response = adapter.more_results_response_from_dto(dto)

        # trip_advisor_review should be converted to int
        assert domain_response.itineraries[0].trip_advisor_review == 100
        assert isinstance(domain_response.itineraries[0].trip_advisor_review, int)
