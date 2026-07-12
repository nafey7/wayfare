"""Unit tests for hotel booking DTO serialization.

Tests that our DTOs match FlightLogic's expected structure exactly.
"""

import json

import pytest

from integrations.flightlogic.hotel_dto import (
    AdultDetailsDTO,
    ChildDetailsDTO,
    HotelBookingRequestDTO,
    HotelCancelRequestDTO,
    HotelCancelResponseDTO,
    HotelMoreResultsRequestDTO,
    HotelMoreResultsResponseDTO,
    PaxDetailsDTO,
    StatusMoreResultsDTO,
)


class TestAdultDetailsDTO:
    """Test AdultDetailsDTO serialization."""

    def test_single_adult_serialization(self):
        """Test single adult serializes with camelCase fields."""
        adult = AdultDetailsDTO(
            title=["Mr"],
            firstName=["John"],
            lastName=["Doe"],
        )

        result = adult.model_dump()

        assert result == {
            "title": ["Mr"],
            "firstName": ["John"],
            "lastName": ["Doe"],
        }

    def test_multiple_adults_serialization(self):
        """Test multiple adults in arrays."""
        adult = AdultDetailsDTO(
            title=["Mr", "Mrs"],
            firstName=["John", "Jane"],
            lastName=["Doe", "Doe"],
        )

        result = adult.model_dump()

        assert result == {
            "title": ["Mr", "Mrs"],
            "firstName": ["John", "Jane"],
            "lastName": ["Doe", "Doe"],
        }


class TestChildDetailsDTO:
    """Test ChildDetailsDTO serialization."""

    def test_single_child_serialization(self):
        """Test child serializes with camelCase fields."""
        child = ChildDetailsDTO(
            title=["Master"],
            firstName=["Tom"],
            lastName=["Doe"],
        )

        result = child.model_dump()

        assert result == {
            "title": ["Master"],
            "firstName": ["Tom"],
            "lastName": ["Doe"],
        }


class TestPaxDetailsDTO:
    """Test PaxDetailsDTO serialization."""

    def test_room_with_adult_only(self):
        """Test room with only adult details."""
        pax = PaxDetailsDTO(
            room_no=1,
            adult=AdultDetailsDTO(
                title=["Mr"],
                firstName=["John"],
                lastName=["Doe"],
            ),
            child=None,
        )

        result = pax.model_dump(exclude_none=True)

        assert result == {
            "room_no": 1,
            "adult": {
                "title": ["Mr"],
                "firstName": ["John"],
                "lastName": ["Doe"],
            },
        }

    def test_room_with_adult_and_child(self):
        """Test room with adult and child details."""
        pax = PaxDetailsDTO(
            room_no=1,
            adult=AdultDetailsDTO(
                title=["Mr"],
                firstName=["John"],
                lastName=["Doe"],
            ),
            child=ChildDetailsDTO(
                title=["Master"],
                firstName=["Tom"],
                lastName=["Doe"],
            ),
        )

        result = pax.model_dump(exclude_none=True)

        assert result == {
            "room_no": 1,
            "adult": {
                "title": ["Mr"],
                "firstName": ["John"],
                "lastName": ["Doe"],
            },
            "child": {
                "title": ["Master"],
                "firstName": ["Tom"],
                "lastName": ["Doe"],
            },
        }


class TestHotelBookingRequestDTO:
    """Test complete HotelBookingRequestDTO serialization."""

    def test_matches_flightlogic_documentation(self):
        """Test that our DTO matches FlightLogic documentation exactly."""
        # This is the structure from FlightLogic docs (Example 1)
        expected = {
            "sessionId": "TEST_SESSION",
            "productId": "trx101",
            "tokenId": "TEST_TOKEN",
            "rateBasisId": "393165",
            "clientRef": "VOYA-TEST",
            "customerEmail": "test@example.com",
            "customerPhone": "1234567890",
            "bookingNote": "Test booking",
            "paxDetails": [
                {
                    "room_no": 1,
                    "adult": {
                        "title": ["Mr"],
                        "firstName": ["Roel"],
                        "lastName": ["Sadza"],
                    },
                }
            ],
        }

        # Create our DTO
        booking = HotelBookingRequestDTO(
            sessionId="TEST_SESSION",
            productId="trx101",
            tokenId="TEST_TOKEN",
            rateBasisId="393165",
            clientRef="VOYA-TEST",
            customerEmail="test@example.com",
            customerPhone="1234567890",
            bookingNote="Test booking",
            paxDetails=[
                PaxDetailsDTO(
                    room_no=1,
                    adult=AdultDetailsDTO(
                        title=["Mr"],
                        firstName=["Roel"],
                        lastName=["Sadza"],
                    ),
                    child=None,
                )
            ],
        )

        result = booking.model_dump(by_alias=True, exclude_none=True)

        # Compare as JSON to ensure exact match
        assert json.dumps(result, sort_keys=True) == json.dumps(
            expected, sort_keys=True
        )

    def test_matches_successful_curl_test(self):
        """Test that our DTO matches the successful curl test structure."""
        # This is the exact structure from our successful curl test
        booking = HotelBookingRequestDTO(
            sessionId="TVRjMk16WTJOemc1TWw4ME1UUmZPVGd1T0RrdU1USTFMakl3Tnc9PV8xMjE2ODYx",  # pragma: allowlist secret
            productId="trx109",
            tokenId="H5I0cL4u2QDb6gWjFLs3",  # pragma: allowlist secret
            rateBasisId="NDEwNzg0MA==",  # pragma: allowlist secret
            clientRef="VOYA-CURL-TEST-1763667907",
            customerEmail="rsadza@gmail.com",
            customerPhone="31633746383",
            bookingNote="Test booking via curl",
            paxDetails=[
                PaxDetailsDTO(
                    room_no=1,
                    adult=AdultDetailsDTO(
                        title=["Mr"],
                        firstName=["Roel"],
                        lastName=["Sadza"],
                    ),
                    child=None,
                )
            ],
        )

        result = booking.model_dump(by_alias=True, exclude_none=True)

        # Verify structure
        assert (
            result["sessionId"]
            == "TVRjMk16WTJOemc1TWw4ME1UUmZPVGd1T0RrdU1USTFMakl3Tnc9PV8xMjE2ODYx"  # pragma: allowlist secret  # noqa: E501
        )
        assert result["paxDetails"][0]["room_no"] == 1
        assert result["paxDetails"][0]["adult"]["title"] == ["Mr"]
        assert result["paxDetails"][0]["adult"]["firstName"] == ["Roel"]
        assert result["paxDetails"][0]["adult"]["lastName"] == ["Sadza"]
        assert "child" not in result["paxDetails"][0]  # excluded by exclude_none=True

    def test_two_rooms_with_adults_and_children(self):
        """Test FlightLogic Example 2: 2 rooms with mixed occupancy."""
        booking = HotelBookingRequestDTO(
            sessionId="TEST_SESSION",
            productId="trx101",
            tokenId="TEST_TOKEN",
            rateBasisId="393165",
            clientRef="VOYA-TEST",
            customerEmail="test@example.com",
            customerPhone="1234567890",
            bookingNote="Test",
            paxDetails=[
                # Room 1: 2 adults
                PaxDetailsDTO(
                    room_no=1,
                    adult=AdultDetailsDTO(
                        title=["Mr", "Mr"],
                        firstName=["test1", "test2"],
                        lastName=["last1", "last2"],
                    ),
                    child=None,
                ),
                # Room 2: 1 adult + 2 children
                PaxDetailsDTO(
                    room_no=2,
                    adult=AdultDetailsDTO(
                        title=["Mr"],
                        firstName=["test"],
                        lastName=["last"],
                    ),
                    child=ChildDetailsDTO(
                        title=["Mr", "Mr"],
                        firstName=["test1", "last1"],
                        lastName=["last1", "last2"],
                    ),
                ),
            ],
        )

        result = booking.model_dump(by_alias=True, exclude_none=True)

        # Verify Room 1
        assert result["paxDetails"][0]["room_no"] == 1
        assert result["paxDetails"][0]["adult"]["title"] == ["Mr", "Mr"]
        assert result["paxDetails"][0]["adult"]["firstName"] == ["test1", "test2"]
        assert result["paxDetails"][0]["adult"]["lastName"] == ["last1", "last2"]

        # Verify Room 2
        assert result["paxDetails"][1]["room_no"] == 2
        assert result["paxDetails"][1]["adult"]["title"] == ["Mr"]
        assert result["paxDetails"][1]["child"]["title"] == ["Mr", "Mr"]
        assert result["paxDetails"][1]["child"]["firstName"] == ["test1", "last1"]


# ==============================================================================
# CANCEL BOOKING DTO TESTS
# ==============================================================================


class TestHotelCancelRequestDTO:
    """Test HotelCancelRequestDTO serialization and validation."""

    def test_cancel_request_serialization(self):
        """Test cancel request serializes with camelCase fields."""
        cancel_request = HotelCancelRequestDTO(
            user_id="test_user",
            user_password="test_pass",  # pragma: allowlist secret
            access="Test",
            ip_address="192.168.1.1",
            supplierConfirmationNum="SUP123456",
            referenceNum="REF789012",
        )

        result = cancel_request.model_dump(by_alias=True)

        assert result["user_id"] == "test_user"
        assert result["user_password"] == "test_pass"  # pragma: allowlist secret
        assert result["access"] == "Test"
        assert result["ip_address"] == "192.168.1.1"
        assert result["supplierConfirmationNum"] == "SUP123456"
        assert result["referenceNum"] == "REF789012"

    def test_cancel_request_requires_all_fields(self):
        """Test that all required fields must be provided."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            HotelCancelRequestDTO(
                user_id="test_user",
                # Missing other required fields
            )

    def test_cancel_request_access_validation(self):
        """Test that access field only accepts 'Test' or 'Production'."""
        # Valid values
        cancel_request_test = HotelCancelRequestDTO(
            user_id="test_user",
            user_password="test_pass",  # pragma: allowlist secret
            access="Test",
            ip_address="192.168.1.1",
            supplierConfirmationNum="SUP123456",
            referenceNum="REF789012",
        )
        assert cancel_request_test.access == "Test"

        cancel_request_prod = HotelCancelRequestDTO(
            user_id="test_user",
            user_password="test_pass",  # pragma: allowlist secret
            access="Production",
            ip_address="192.168.1.1",
            supplierConfirmationNum="SUP123456",
            referenceNum="REF789012",
        )
        assert cancel_request_prod.access == "Production"

        # Invalid value should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            HotelCancelRequestDTO(
                user_id="test_user",
                user_password="test_pass",  # pragma: allowlist secret
                access="Invalid",
                ip_address="192.168.1.1",
                supplierConfirmationNum="SUP123456",
                referenceNum="REF789012",
            )


class TestHotelCancelResponseDTO:
    """Test HotelCancelResponseDTO parsing and validation."""

    def test_cancel_response_success_parsing(self):
        """Test parsing successful cancellation response."""
        response_data = {
            "status": "CANCELLED",
            "cancelReferenceNum": "CANCEL123456",
            "message": "Booking cancelled successfully",
        }

        response = HotelCancelResponseDTO(**response_data)

        assert response.status == "CANCELLED"
        assert response.cancelReferenceNum == "CANCEL123456"
        assert response.message == "Booking cancelled successfully"

    def test_cancel_response_failure_parsing(self):
        """Test parsing failed cancellation response."""
        response_data = {
            "status": "FAILED",
            "cancelReferenceNum": None,
            "message": "Cancellation failed: Booking not found",
        }

        response = HotelCancelResponseDTO(**response_data)

        assert response.status == "FAILED"
        assert response.cancelReferenceNum is None
        assert response.message == "Cancellation failed: Booking not found"

    def test_cancel_response_requires_status(self):
        """Test that status field is required."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            HotelCancelResponseDTO(
                # Missing status
                cancelReferenceNum="CANCEL123456",
                message="Test",
            )

    def test_cancel_response_requires_message(self):
        """Test that message field is required."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            HotelCancelResponseDTO(
                status="CANCELLED",
                cancelReferenceNum="CANCEL123456",
                # Missing message
            )


# ==============================================================================
# MORE RESULTS DTO TESTS
# ==============================================================================


class TestHotelMoreResultsRequestDTO:
    """Test HotelMoreResultsRequestDTO serialization and validation."""

    def test_more_results_request_serialization(self):
        """Test more results request serializes with camelCase fields."""
        request = HotelMoreResultsRequestDTO(
            sessionId="test_session_12345",
            nextToken="next_token_abc123",
            maxResult=20,
        )

        result = request.model_dump(by_alias=True)

        assert result["sessionId"] == "test_session_12345"
        assert result["nextToken"] == "next_token_abc123"
        assert result["maxResult"] == 20

    def test_more_results_request_default_max_result(self):
        """Test that maxResult defaults to 20."""
        request = HotelMoreResultsRequestDTO(
            sessionId="test_session",
            nextToken="next_token",
        )

        assert request.maxResult == 20

    def test_more_results_request_max_result_validation(self):
        """Test that maxResult must be >= 1."""
        # Valid value
        request = HotelMoreResultsRequestDTO(
            sessionId="test_session",
            nextToken="next_token",
            maxResult=1,
        )
        assert request.maxResult == 1

        # Invalid value should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            HotelMoreResultsRequestDTO(
                sessionId="test_session",
                nextToken="next_token",
                maxResult=0,  # Invalid: must be >= 1
            )

    def test_more_results_request_requires_all_fields(self):
        """Test that all required fields must be provided."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            HotelMoreResultsRequestDTO(
                sessionId="test_session",
                # Missing nextToken
            )


class TestStatusMoreResultsDTO:
    """Test StatusMoreResultsDTO parsing."""

    def test_status_more_results_parsing(self):
        """Test parsing status object from moreResults response."""
        status_data = {
            "sessionId": "test_session_12345",
            "moreResults": True,
            "nextToken": "next_token_abc123",
        }

        status = StatusMoreResultsDTO(**status_data)

        assert status.sessionId == "test_session_12345"
        assert status.moreResults is True
        assert status.nextToken == "next_token_abc123"

    def test_status_more_results_defaults(self):
        """Test that moreResults and nextToken have defaults."""
        status_data = {
            "sessionId": "test_session",
        }

        status = StatusMoreResultsDTO(**status_data)

        assert status.moreResults is False
        assert status.nextToken == ""


class TestHotelMoreResultsResponseDTO:
    """Test HotelMoreResultsResponseDTO parsing."""

    def test_more_results_response_parsing(self):
        """Test parsing complete moreResults response."""
        response_data = {
            "status": {
                "sessionId": "test_session_12345",
                "moreResults": False,
                "nextToken": "",
            },
            "itineraries": [],
        }

        response = HotelMoreResultsResponseDTO(**response_data)

        assert response.status.sessionId == "test_session_12345"
        assert response.status.moreResults is False
        assert len(response.itineraries) == 0

    def test_more_results_response_with_hotels(self):
        """Test parsing moreResults response with hotel data."""
        response_data = {
            "status": {
                "sessionId": "test_session_12345",
                "moreResults": True,
                "nextToken": "next_token_xyz",
            },
            "itineraries": [
                {
                    "hotelId": "123",
                    "twxHotelId": 123,
                    "productId": "PROD001",
                    "tokenId": "token_001",
                    "hotelName": "Test Hotel",
                    "city": "London",
                    "locality": "",
                    "address": "123 Test St",
                    "country": "UK",
                    "countryCode": "GB",
                    "postalCode": "SW1A 1AA",
                    "latitude": "51.5074",
                    "longitude": "-0.1278",
                    "distanceValue": 2.5,
                    "distanceUnit": "KM",
                    "total": 150.00,  # Numeric, not string
                    "currency": "USD",
                    "fareType": "Refundable",
                    "hotelRating": 4,
                    "propertyType": "Hotel",
                    "facilities": ["WiFi", "Parking"],
                    "thumbNailUrl": "https://example.com/thumb.jpg",
                    "phone": "+44-20-1234567",
                    "email": "info@testhotel.com",
                    "tripAdvisorRating": 4.5,
                    "tripAdvisorReview": 100,
                    "special": "",
                }
            ],
        }

        response = HotelMoreResultsResponseDTO(**response_data)

        assert len(response.itineraries) == 1
        assert response.itineraries[0].hotelId == "123"
        assert response.itineraries[0].hotelName == "Test Hotel"
        assert response.itineraries[0].total == 150.00  # Numeric
        assert response.status.moreResults is True
        assert response.status.nextToken == "next_token_xyz"
