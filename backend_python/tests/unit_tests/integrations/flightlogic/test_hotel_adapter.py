"""Unit tests for FlightLogic Hotel Adapter DTO ↔ Domain conversions.

These tests ensure the adapter correctly converts between FlightLogic DTOs
and our domain models using actual API responses as test data.
"""

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from app.domains.hotel.schemas import HotelRateRulesResponse, HotelRoomRatesResponse
from integrations.flightlogic.hotel_adapter import HotelSchemaAdapter
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


@pytest.fixture
def hotel_adapter():
    """Create HotelSchemaAdapter instance for testing."""
    return HotelSchemaAdapter()


@pytest.fixture(autouse=True)
def mock_imgproxy():
    """Mock imgproxy transformation functions to return original URLs.

    This allows tests to verify data flow without imgproxy URL transformation.
    Applied automatically to all tests in this module.
    """
    with (
        patch(
            "integrations.flightlogic.hotel_adapter.transform_image_urls",
            side_effect=lambda urls: urls or [],
        ),
        patch(
            "integrations.flightlogic.hotel_adapter.get_imgproxy_url",
            side_effect=lambda url, **_: url if url else "",
        ),
    ):
        yield


class TestRoomRatesAdapterConversion:
    """Test room rates DTO → Domain model conversion."""

    def test_converts_room_rates_response(self, hotel_adapter):
        """Validate adapter converts room rates DTO to domain model."""
        # Load and parse DTO
        data = load_fixture("hotel_room_rates_response.json")
        dto = HotelRoomRatesResponseDTO(**data)

        # Convert to domain model
        domain_model = hotel_adapter.room_rates_response_from_dto(dto)

        # Validate conversion
        assert isinstance(domain_model, HotelRoomRatesResponse)
        assert domain_model.hotel_id == "316798"
        assert domain_model.session_id == dto.sessionId
        assert domain_model.token_id == dto.tokenId
        assert len(domain_model.rooms) == 3  # Fixture has 3 rooms

    def test_converts_room_option_fields(self, hotel_adapter):
        """Validate individual room option fields are correctly converted."""
        data = load_fixture("hotel_room_rates_response.json")
        dto = HotelRoomRatesResponseDTO(**data)
        domain_model = hotel_adapter.room_rates_response_from_dto(dto)

        # Check first room
        first_room = domain_model.rooms[0]
        assert first_room.room_type == "Standard Double Room - Shared"
        assert first_room.rate_basis_id == "NDEwNzkzMw=="  # CRITICAL for booking
        assert isinstance(first_room.total_price, Decimal)
        assert first_room.currency == "USD"
        assert first_room.meal_plan == "ROOM ONLY"
        assert "If cancelled" in first_room.cancellation_policy

    def test_converts_price_to_decimal(self, hotel_adapter):
        """Validate price conversion from string/float to Decimal."""
        data = load_fixture("hotel_room_rates_response.json")
        dto = HotelRoomRatesResponseDTO(**data)
        domain_model = hotel_adapter.room_rates_response_from_dto(dto)

        # All prices should be Decimal
        for room in domain_model.rooms:
            assert isinstance(room.total_price, Decimal)
            assert isinstance(room.price_per_night, Decimal)
            assert room.total_price > Decimal("0")

    def test_preserves_rate_basis_id(self, hotel_adapter):
        """Ensure rate_basis_id (critical for booking) is preserved correctly."""
        data = load_fixture("hotel_room_rates_response.json")
        dto = HotelRoomRatesResponseDTO(**data)
        domain_model = hotel_adapter.room_rates_response_from_dto(dto)

        # All rooms must have rate_basis_id
        for i, room in enumerate(domain_model.rooms):
            assert room.rate_basis_id, f"Room {i} missing rate_basis_id"
            assert room.rate_basis_id == dto.roomRates.perBookingRates[i].rateBasisId


class TestRateRulesAdapterConversion:
    """Test rate rules DTO → Domain model conversion."""

    def test_converts_rate_rules_response(self, hotel_adapter):
        """Validate adapter converts rate rules DTO to domain model."""
        # Load and parse DTO
        data = load_fixture("hotel_rate_rules_response.json")
        dto = HotelRateRulesResponseDTO(**data)

        # Convert to domain model
        domain_model = hotel_adapter.rate_rules_response_from_dto(dto)

        # Validate conversion
        assert isinstance(domain_model, HotelRateRulesResponse)
        assert domain_model.session_id == dto.sessionId
        assert domain_model.hotel_id == str(dto.hotelId)  # Converted to string
        assert domain_model.token_id == dto.tokenId

    def test_converts_rate_rule_fields(self, hotel_adapter):
        """Validate rate rule fields are correctly converted."""
        data = load_fixture("hotel_rate_rules_response.json")
        dto = HotelRateRulesResponseDTO(**data)
        domain_model = hotel_adapter.rate_rules_response_from_dto(dto)

        # Validate domain model fields
        assert domain_model.room_type == "Standard Double Room - Shared"
        assert domain_model.rate_basis_id == "NDEwODAwMQ=="  # CRITICAL
        assert isinstance(domain_model.net_price, Decimal)
        assert domain_model.currency == "USD"
        assert domain_model.board_basis == "ROOM ONLY"
        assert domain_model.inventory_type == "prepaid"

    def test_converts_net_price_to_decimal(self, hotel_adapter):
        """Validate netPrice (string or float) converts to Decimal."""
        data = load_fixture("hotel_rate_rules_response.json")
        dto = HotelRateRulesResponseDTO(**data)
        domain_model = hotel_adapter.rate_rules_response_from_dto(dto)

        # netPrice should be Decimal
        assert isinstance(domain_model.net_price, Decimal)
        assert domain_model.net_price == Decimal("476.74")

    def test_preserves_validated_rate_basis_id(self, hotel_adapter):
        """Ensure validated rate_basis_id is correctly preserved."""
        data = load_fixture("hotel_rate_rules_response.json")
        dto = HotelRateRulesResponseDTO(**data)
        domain_model = hotel_adapter.rate_rules_response_from_dto(dto)

        # Validated rateBasisId must match
        first_rate = dto.roomRates["perBookingRates"][0]
        assert domain_model.rate_basis_id == first_rate.rateBasisId


class TestAdapterHandlesAPIInconsistencies:
    """Test adapter handles FlightLogic's inconsistent response types."""

    def test_handles_hotel_id_as_int(self, hotel_adapter):
        """Rate rules returns hotelId as int - adapter should handle it."""
        data = load_fixture("hotel_rate_rules_response.json")
        dto = HotelRateRulesResponseDTO(**data)
        domain_model = hotel_adapter.rate_rules_response_from_dto(dto)

        # Adapter should convert int to string
        assert isinstance(domain_model.hotel_id, str)
        assert domain_model.hotel_id == "316798"

    def test_handles_net_price_as_float(self, hotel_adapter):
        """Some responses return netPrice as float - adapter should handle it."""
        data = load_fixture("hotel_rate_rules_response.json")

        # netPrice is float in this fixture
        dto = HotelRateRulesResponseDTO(**data)
        domain_model = hotel_adapter.rate_rules_response_from_dto(dto)

        # Should convert to Decimal regardless of source type
        assert isinstance(domain_model.net_price, Decimal)

    def test_handles_max_occupancy_as_string(self, hotel_adapter):
        """FlightLogic returns maxOccupancyPerRoom as string - adapter parses it."""
        data = load_fixture("hotel_room_rates_response.json")
        dto = HotelRoomRatesResponseDTO(**data)
        domain_model = hotel_adapter.room_rates_response_from_dto(dto)

        # Adapter should parse string "2" to dict {"adults": 2}
        first_room = domain_model.rooms[0]
        assert isinstance(first_room.max_occupancy, dict)
        assert first_room.max_occupancy.get("adults") == 2


class TestImageMapping:
    """Test that room images are correctly mapped from DTO to domain model."""

    def test_maps_room_images_from_room_rates_dto(self, hotel_adapter):
        """Verify roomImages from DTO are mapped to images field in RoomOption."""
        data = load_fixture("hotel_room_rates_response.json")
        dto = HotelRoomRatesResponseDTO(**data)
        domain_model = hotel_adapter.room_rates_response_from_dto(dto)

        # All rooms should have images field (even if empty)
        for i, room in enumerate(domain_model.rooms):
            assert hasattr(room, "images"), f"Room {i} missing images field"
            assert isinstance(room.images, list), f"Room {i} images should be a list"
            # Fixture has empty roomImages arrays
            assert room.images == [], f"Room {i} should have empty images from fixture"

    def test_maps_room_images_with_actual_urls(self, hotel_adapter):
        """Verify roomImages with actual valid URLs are correctly mapped."""
        data = load_fixture("hotel_room_rates_response.json")

        # Use real valid HotelBeds image URLs
        valid_image_urls = [
            "https://photos.hotelbeds.com/giata/original/99/995945/995945a_hb_a_001.jpg",
            "https://photos.hotelbeds.com/giata/original/10/1094319/1094319a_hb_a_001_20251007_090327.jpg",
        ]
        data["roomRates"]["perBookingRates"][0]["roomImages"] = valid_image_urls

        dto = HotelRoomRatesResponseDTO(**data)
        domain_model = hotel_adapter.room_rates_response_from_dto(dto)

        # First room should have the image URLs
        first_room = domain_model.rooms[0]
        assert first_room.images == valid_image_urls
        assert len(first_room.images) == 2
        assert all(isinstance(url, str) for url in first_room.images)
        # Verify URLs are from hotelbeds.com domain
        assert all("photos.hotelbeds.com" in url for url in first_room.images)

    def test_handles_missing_room_images(self, hotel_adapter):
        """Verify adapter handles missing roomImages field gracefully."""
        data = load_fixture("hotel_room_rates_response.json")

        # Remove roomImages field from first room
        del data["roomRates"]["perBookingRates"][0]["roomImages"]

        dto = HotelRoomRatesResponseDTO(**data)
        domain_model = hotel_adapter.room_rates_response_from_dto(dto)

        # Should default to empty list
        first_room = domain_model.rooms[0]
        assert isinstance(first_room.images, list)
        assert first_room.images == []

    def test_maps_room_images_from_rate_rules_dto(self, hotel_adapter):
        """Verify roomImages from rate rules DTO are mapped to images field."""
        data = load_fixture("hotel_rate_rules_response.json")
        dto = HotelRateRulesResponseDTO(**data)
        domain_model = hotel_adapter.rate_rules_response_from_dto(dto)

        # Rate rules response should have images field
        assert hasattr(domain_model, "images")
        assert isinstance(domain_model.images, list)
        # Fixture has empty roomImages array
        assert domain_model.images == []

    def test_maps_room_images_with_urls_in_rate_rules(self, hotel_adapter):
        """Verify roomImages with URLs in rate rules are correctly mapped."""
        data = load_fixture("hotel_rate_rules_response.json")

        # Use real valid HotelBeds image URLs
        valid_image_urls = [
            "https://photos.hotelbeds.com/giata/original/99/995945/995945a_hb_a_001.jpg",
            "https://photos.hotelbeds.com/giata/original/10/1094319/1094319a_hb_a_001_20251007_090327.jpg",
        ]
        data["roomRates"]["perBookingRates"][0]["roomImages"] = valid_image_urls

        dto = HotelRateRulesResponseDTO(**data)
        domain_model = hotel_adapter.rate_rules_response_from_dto(dto)

        # Should have the image URLs
        assert domain_model.images == valid_image_urls
        assert len(domain_model.images) == 2
        assert all(isinstance(url, str) for url in domain_model.images)
        # Verify URLs are from hotelbeds.com domain
        assert all("photos.hotelbeds.com" in url for url in domain_model.images)

    def test_handles_invalid_image_urls(self, hotel_adapter):
        """Verify adapter handles invalid image URLs gracefully (still maps them as strings)."""
        data = load_fixture("hotel_room_rates_response.json")

        # Use invalid URLs (with trailing colon or other issues)
        # Adapter should still map them as strings, validation happens elsewhere
        invalid_image_urls = [
            "https://photos.hotelbeds.com/giata/original/43/438779/438779a_hb_a_001.jpg:",
            "https://photos.hotelbeds.com/giata/original/68/684039/684039a_hb_a_001.jpg",
        ]
        data["roomRates"]["perBookingRates"][0]["roomImages"] = invalid_image_urls

        dto = HotelRoomRatesResponseDTO(**data)
        domain_model = hotel_adapter.room_rates_response_from_dto(dto)

        # Adapter should still map invalid URLs (validation happens at proxy/UI level)
        first_room = domain_model.rooms[0]
        assert first_room.images == invalid_image_urls
        assert len(first_room.images) == 2
        assert all(isinstance(url, str) for url in first_room.images)
        # Verify URLs are still stored as provided (adapter doesn't validate)
        assert first_room.images[0].endswith(":")
