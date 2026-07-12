"""Unit tests for FlightLogic Hotel DTO validation using actual API responses.

These tests ensure our Pydantic DTOs correctly parse real FlightLogic API responses.
Fixtures are captured from actual API calls to guarantee compatibility.
"""

import json
from pathlib import Path

from integrations.flightlogic.hotel_dto import (
    HotelRateRulesResponseDTO,
    HotelRoomRatesResponseDTO,
)

# Path to fixtures
FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures" / "flightlogic"


def load_fixture(filename: str) -> dict:
    """Load JSON fixture from file."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path) as f:
        return json.load(f)


class TestHotelRoomRatesDTO:
    """Test HotelRoomRatesResponseDTO validates real API responses."""

    def test_parses_actual_room_rates_response(self):
        """Validate DTO parses actual FlightLogic get_room_rates response."""
        # Load actual API response
        data = load_fixture("hotel_room_rates_response.json")

        # Parse with Pydantic - should NOT raise validation errors
        dto = HotelRoomRatesResponseDTO(**data)

        # Validate structure
        assert (
            dto.sessionId
            == "TVRjMk16WTNPVEU1T0Y4Mk1qaGZPVGd1T0RrdU1USTFMakl3Tnc9PV8xMjE2ODcy"  # pragma: allowlist secret
        )
        assert dto.hotelId == "316798"  # String or int accepted
        assert dto.tokenId == "UrdOYqBEmvoTADJQjfFt"
        assert dto.roomRates is not None
        assert len(dto.roomRates.perBookingRates) == 3  # Fixture has 3 rooms

    def test_validates_room_option_fields(self):
        """Validate individual room option fields from actual response."""
        data = load_fixture("hotel_room_rates_response.json")
        dto = HotelRoomRatesResponseDTO(**data)

        # Check first room option
        first_room = dto.roomRates.perBookingRates[0]
        assert first_room.productId == "trx109"
        assert first_room.roomType == "Standard Double Room - Shared"
        assert first_room.rateBasisId == "NDEwNzkzMw=="  # Base64 encoded
        assert first_room.currency == "USD"
        assert first_room.netPrice in ("476.11", 476.11)  # String or float accepted
        assert first_room.boardType == "ROOM ONLY"
        assert first_room.maxOccupancyPerRoom == "2"
        assert first_room.inventoryType == "prepaid"
        assert "If cancelled" in first_room.cancellationPolicy

    def test_handles_different_room_types(self):
        """Validate DTO handles multiple room types from API."""
        data = load_fixture("hotel_room_rates_response.json")
        dto = HotelRoomRatesResponseDTO(**data)

        room_types = [room.roomType for room in dto.roomRates.perBookingRates]
        assert "Standard Double Room - Shared" in room_types
        assert "Double Standard" in room_types

        fare_types = [room.fareType for room in dto.roomRates.perBookingRates]
        assert "Non-Refundable" in fare_types
        assert "Refundable" in fare_types


class TestHotelRateRulesDTO:
    """Test HotelRateRulesResponseDTO validates real API responses."""

    def test_parses_actual_rate_rules_response(self):
        """Validate DTO parses actual FlightLogic get_rate_rules response."""
        # Load actual API response
        data = load_fixture("hotel_rate_rules_response.json")

        # Parse with Pydantic - should NOT raise validation errors
        dto = HotelRateRulesResponseDTO(**data)

        # Validate structure
        assert (
            dto.sessionId
            == "TVRjMk16WTRNRE0zTjE4NE5qVmZPVGd1T0RrdU1USTFMakl3Tnc9PV8xMjE2ODcz"  # pragma: allowlist secret
        )
        assert dto.hotelId in (316798, "316798")  # Int or string accepted
        assert dto.tokenId == "XYsMFWGhuE8vCJBgnijp"
        assert dto.roomRates is not None
        assert "perBookingRates" in dto.roomRates

    def test_validates_rate_rule_room_fields(self):
        """Validate rate rule room fields from actual response."""
        data = load_fixture("hotel_rate_rules_response.json")
        dto = HotelRateRulesResponseDTO(**data)

        # Check first room rate
        first_rate = dto.roomRates["perBookingRates"][0]
        assert first_rate.productId == "trx109"
        assert first_rate.roomType == "Standard Double Room - Shared"
        assert first_rate.rateBasisId == "NDEwODAwMQ=="  # Base64 encoded
        assert first_rate.currency == "USD"
        assert first_rate.netPrice in (476.74, "476.74")  # Float or string accepted
        assert first_rate.maxOccupancyPerRoom == "2"
        assert first_rate.inventoryType == "prepaid"


class TestDTOFieldTypeFlexibility:
    """Test DTOs handle FlightLogic's inconsistent type responses."""

    def test_hotel_id_accepts_int_or_string(self):
        """FlightLogic sometimes returns hotelId as int, sometimes as string."""
        data = load_fixture("hotel_rate_rules_response.json")

        # Test with int (actual response)
        dto_int = HotelRateRulesResponseDTO(**data)
        assert dto_int.hotelId == 316798

        # Test with string
        data_str = data.copy()
        data_str["hotelId"] = "316798"
        dto_str = HotelRateRulesResponseDTO(**data_str)
        assert dto_str.hotelId == "316798"

    def test_net_price_accepts_string_or_float(self):
        """FlightLogic sometimes returns netPrice as string, sometimes as float."""
        data = load_fixture("hotel_room_rates_response.json")

        # Test with string (actual response)
        dto = HotelRoomRatesResponseDTO(**data)
        assert dto.roomRates.perBookingRates[0].netPrice == "476.11"

        # Test with float
        data_float = json.loads(json.dumps(data))
        data_float["roomRates"]["perBookingRates"][0]["netPrice"] = 476.11
        dto_float = HotelRoomRatesResponseDTO(**data_float)
        assert dto_float.roomRates.perBookingRates[0].netPrice == 476.11
