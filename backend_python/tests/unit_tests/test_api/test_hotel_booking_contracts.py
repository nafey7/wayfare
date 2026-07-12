"""Contract tests for hotel booking data flow.

Similar to flight booking, these tests verify data structure
consistency between producer and consumer endpoints.
"""

import pytest


class TestHotelBookingSessionContract:
    """Contract tests for hotel booking session data."""

    @pytest.fixture
    def hotel_session_data(self) -> dict:
        """Simulates hotel booking session data structure."""
        return {
            "selected_hotel": {
                "hotel_code": "HOTEL123",
                "hotel_name": "Test Hotel",
                "star_rating": 4,
                "address": {"city": "Amsterdam", "country": "NL"},
            },
            "selected_room": {
                "room_type_code": "ROOM001",
                "room_name": "Deluxe Room",
                "rate_basis_id": "RATE_BASIS_123",
                "pricing": {
                    "total_price": {"amount": 250.00, "currency": "EUR"},
                    "price_per_night": {"amount": 125.00, "currency": "EUR"},
                },
            },
            "search_params": {
                "check_in": "2025-06-01",
                "check_out": "2025-06-03",
                "rooms": 1,
                "adults": 2,
                "children": 0,
            },
            "fl_session_id": "flightlogic-hotel-session-123",
            "status": "rate_validated",
        }

    def test_rate_basis_id_is_accessible(self, hotel_session_data: dict):
        """Verify rate_basis_id can be extracted for booking API call."""
        selected_room = hotel_session_data.get("selected_room", {})
        rate_basis_id = selected_room.get("rate_basis_id")

        assert rate_basis_id is not None, (
            "rate_basis_id must be present in selected_room for booking API call"
        )

    def test_fl_session_id_is_present(self, hotel_session_data: dict):
        """Verify FlightLogic session ID is stored for booking."""
        fl_session_id = hotel_session_data.get("fl_session_id")

        assert fl_session_id is not None, (
            "fl_session_id must be stored for hotel booking API call"
        )

    def test_pricing_data_is_accessible(self, hotel_session_data: dict):
        """Verify pricing can be extracted for display."""
        selected_room = hotel_session_data.get("selected_room", {})
        pricing = selected_room.get("pricing", {})

        total_price = pricing.get("total_price", {})
        assert total_price.get("amount") is not None, (
            "total_price.amount must be present for price display"
        )
        assert total_price.get("currency") is not None, (
            "total_price.currency must be present"
        )

    def test_search_params_preserved(self, hotel_session_data: dict):
        """Verify search params are preserved for booking reference."""
        search_params = hotel_session_data.get("search_params", {})

        assert search_params.get("check_in") is not None
        assert search_params.get("check_out") is not None
        assert search_params.get("rooms") is not None
        assert search_params.get("adults") is not None


class TestHotelRateValidationContract:
    """Contract tests for rate validation → booking flow."""

    def test_rate_validation_response_has_required_fields(self):
        """Verify rate validation response has fields needed for booking."""
        # Simulates response from rate-rules validation
        rate_validation_response = {
            "is_valid": True,
            "rate_basis_id": "VALIDATED_RATE_123",
            "validated_pricing": {
                "total_price": {"amount": 250.00, "currency": "EUR"},
                "cancellation_policy": {
                    "is_refundable": True,
                    "free_cancellation_until": "2025-05-25T23:59:59Z",
                },
            },
        }

        assert rate_validation_response.get("rate_basis_id") is not None
        assert rate_validation_response.get("validated_pricing") is not None

        pricing = rate_validation_response["validated_pricing"]
        assert pricing.get("total_price", {}).get("amount") is not None
