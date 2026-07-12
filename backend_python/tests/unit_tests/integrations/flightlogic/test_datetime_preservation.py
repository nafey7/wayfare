"""Unit tests for datetime preservation in FlightLogic adapters.

Tests ensure that flight times are preserved end-to-end through the parsing
process without timezone conversion. This verifies the complete flow from
raw datetime strings to parsed flight segments.
"""

import pytest

from app.domains.common.schemas import DateTime
from integrations.flightlogic.adapter import FlightLogicSchemaAdapter
from integrations.flightlogic.trip_details_adapter import _parse_flight_segments


class TestFlightSegmentDatetimePreservation:
    """Test that flight segment datetimes are preserved through parsing."""

    @pytest.fixture
    def adapter(self):
        """Create FlightLogicSchemaAdapter instance for testing."""
        return FlightLogicSchemaAdapter()

    def test_flight_segment_preserves_departure_time(self, adapter):
        """When parsing flight segments, departure times should remain as provided."""
        segment_data = {
            "DepartureAirportCode": "JFK",
            "ArrivalAirportCode": "LHR",
            "DepartureDateTime": "2025-01-15T10:30:00",  # 10:30 AM
            "ArrivalDateTime": "2025-01-15T18:30:00",  # 6:30 PM
            "FlightNumber": "BA123",
            "MarketingAirlineCode": "BA",
            "OperatingAirlineCode": "BA",
            "OperatingFlightNumber": "BA123",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 480,
        }

        booking_data = {
            "FlightSegments": [segment_data],
            "Passengers": [{"PassengerType": "ADT"}],
        }

        segments = adapter._parse_flight_segments(booking_data, passenger_count=1)

        assert len(segments) == 1
        segment = segments[0]

        # Verify departure time is preserved
        assert segment.departure_datetime is not None
        assert isinstance(segment.departure_datetime, DateTime)
        assert segment.departure_datetime.value.tzinfo is None  # Must be naive
        assert segment.departure_datetime.value.hour == 10
        assert segment.departure_datetime.value.minute == 30

        # Verify arrival time is preserved
        assert segment.arrival_datetime is not None
        assert isinstance(segment.arrival_datetime, DateTime)
        assert segment.arrival_datetime.value.tzinfo is None  # Must be naive
        assert segment.arrival_datetime.value.hour == 18
        assert segment.arrival_datetime.value.minute == 30

    def test_flight_segment_preserves_time_with_utc_timezone(self, adapter):
        """Time should be preserved even when input has UTC timezone marker."""
        segment_data = {
            "DepartureAirportCode": "JFK",
            "ArrivalAirportCode": "LHR",
            "DepartureDateTime": "2025-01-15T10:30:00Z",  # UTC marker
            "ArrivalDateTime": "2025-01-15T18:30:00Z",
            "FlightNumber": "BA123",
            "MarketingAirlineCode": "BA",
            "OperatingAirlineCode": "BA",
            "OperatingFlightNumber": "BA123",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 480,
        }

        booking_data = {
            "FlightSegments": [segment_data],
            "Passengers": [{"PassengerType": "ADT"}],
        }

        segments = adapter._parse_flight_segments(booking_data, passenger_count=1)

        assert len(segments) == 1
        segment = segments[0]

        # Time should be preserved (10:30), not converted
        assert segment.departure_datetime.value.hour == 10
        assert segment.departure_datetime.value.minute == 30
        assert segment.departure_datetime.value.tzinfo is None

    def test_flight_segment_preserves_time_with_offset(self, adapter):
        """Time should be preserved even when input has timezone offset."""
        segment_data = {
            "DepartureAirportCode": "JFK",
            "ArrivalAirportCode": "LHR",
            "DepartureDateTime": "2025-01-15T10:30:00+05:00",  # With offset
            "ArrivalDateTime": "2025-01-15T18:30:00+05:00",
            "FlightNumber": "BA123",
            "MarketingAirlineCode": "BA",
            "OperatingAirlineCode": "BA",
            "OperatingFlightNumber": "BA123",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 480,
        }

        booking_data = {
            "FlightSegments": [segment_data],
            "Passengers": [{"PassengerType": "ADT"}],
        }

        segments = adapter._parse_flight_segments(booking_data, passenger_count=1)

        assert len(segments) == 1
        segment = segments[0]

        # Time should be preserved (10:30), not converted to 05:30
        assert segment.departure_datetime.value.hour == 10
        assert segment.departure_datetime.value.minute == 30
        assert segment.departure_datetime.value.tzinfo is None

    def test_multiple_segments_preserve_times_independently(self, adapter):
        """Multiple segments should each preserve their times independently."""
        segment1_data = {
            "DepartureAirportCode": "JFK",
            "ArrivalAirportCode": "LHR",
            "DepartureDateTime": "2025-01-15T10:00:00",
            "ArrivalDateTime": "2025-01-15T18:00:00",
            "FlightNumber": "BA123",
            "MarketingAirlineCode": "BA",
            "OperatingAirlineCode": "BA",
            "OperatingFlightNumber": "BA123",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 480,
        }

        segment2_data = {
            "DepartureAirportCode": "LHR",
            "ArrivalAirportCode": "DXB",
            "DepartureDateTime": "2025-01-16T02:00:00",  # Different time
            "ArrivalDateTime": "2025-01-16T10:00:00",
            "FlightNumber": "BA456",
            "MarketingAirlineCode": "BA",
            "OperatingAirlineCode": "BA",
            "OperatingFlightNumber": "BA456",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 480,
        }

        booking_data = {
            "FlightSegments": [segment1_data, segment2_data],
            "Passengers": [{"PassengerType": "ADT"}],
        }

        segments = adapter._parse_flight_segments(booking_data, passenger_count=1)

        assert len(segments) == 2

        # First segment times
        assert segments[0].departure_datetime.value.hour == 10
        assert segments[0].arrival_datetime.value.hour == 18

        # Second segment times (different day, different times)
        assert segments[1].departure_datetime.value.hour == 2
        assert segments[1].arrival_datetime.value.hour == 10

        # All should be naive
        assert segments[0].departure_datetime.value.tzinfo is None
        assert segments[1].departure_datetime.value.tzinfo is None


class TestTripDetailsAdapterDatetimePreservation:
    """Test that trip_details_adapter preserves datetimes correctly."""

    def test_flight_segment_preserves_departure_time(self):
        """When parsing flight segments, departure times should remain as provided."""
        segment_data = {
            "DepartureAirportCode": "JFK",
            "ArrivalAirportCode": "LHR",
            "DepartureDateTime": "2025-01-15T10:30:00",
            "ArrivalDateTime": "2025-01-15T18:30:00",
            "FlightNumber": "BA123",
            "MarketingAirlineCode": "BA",
            "OperatingAirlineCode": "BA",
            "OperatingFlightNumber": "BA123",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 480,
        }

        booking_data = {
            "FlightSegments": [segment_data],
        }

        segments = _parse_flight_segments(booking_data)

        assert len(segments) == 1
        segment = segments[0]

        # Verify departure time is preserved
        assert segment.departure_datetime is not None
        assert isinstance(segment.departure_datetime, DateTime)
        assert segment.departure_datetime.value.tzinfo is None  # Must be naive
        assert segment.departure_datetime.value.hour == 10
        assert segment.departure_datetime.value.minute == 30

    def test_flight_segment_preserves_time_with_utc_timezone(self):
        """Time should be preserved even when input has UTC timezone marker."""
        segment_data = {
            "DepartureAirportCode": "JFK",
            "ArrivalAirportCode": "LHR",
            "DepartureDateTime": "2025-01-15T10:30:00Z",
            "ArrivalDateTime": "2025-01-15T18:30:00Z",
            "FlightNumber": "BA123",
            "MarketingAirlineCode": "BA",
            "OperatingAirlineCode": "BA",
            "OperatingFlightNumber": "BA123",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 480,
        }

        booking_data = {
            "FlightSegments": [segment_data],
        }

        segments = _parse_flight_segments(booking_data)

        assert len(segments) == 1
        segment = segments[0]

        # Time should be preserved (10:30), not converted
        assert segment.departure_datetime.value.hour == 10
        assert segment.departure_datetime.value.minute == 30
        assert segment.departure_datetime.value.tzinfo is None


class TestTimePreservationAcrossDifferentInputs:
    """Test that same time is preserved across different input formats."""

    @pytest.fixture
    def adapter(self):
        """Create FlightLogicSchemaAdapter instance for testing."""
        return FlightLogicSchemaAdapter()

    def test_same_time_different_formats_produce_same_result(self, adapter):
        """Same time in different formats should produce same naive datetime."""
        # Test with adapter
        segment1_data = {
            "DepartureAirportCode": "JFK",
            "ArrivalAirportCode": "LHR",
            "DepartureDateTime": "2025-01-15T10:30:00",  # No timezone
            "ArrivalDateTime": "2025-01-15T18:30:00",
            "FlightNumber": "BA123",
            "MarketingAirlineCode": "BA",
            "OperatingAirlineCode": "BA",
            "OperatingFlightNumber": "BA123",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 480,
        }

        segment2_data = {
            "DepartureAirportCode": "JFK",
            "ArrivalAirportCode": "LHR",
            "DepartureDateTime": "2025-01-15T10:30:00Z",  # UTC
            "ArrivalDateTime": "2025-01-15T18:30:00Z",
            "FlightNumber": "BA123",
            "MarketingAirlineCode": "BA",
            "OperatingAirlineCode": "BA",
            "OperatingFlightNumber": "BA123",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 480,
        }

        booking_data1 = {
            "FlightSegments": [segment1_data],
            "Passengers": [{"PassengerType": "ADT"}],
        }

        booking_data2 = {
            "FlightSegments": [segment2_data],
            "Passengers": [{"PassengerType": "ADT"}],
        }

        segments1 = adapter._parse_flight_segments(booking_data1, passenger_count=1)
        segments2 = adapter._parse_flight_segments(booking_data2, passenger_count=1)

        # Both should produce same time
        assert (
            segments1[0].departure_datetime.value.hour
            == segments2[0].departure_datetime.value.hour
        )
        assert (
            segments1[0].departure_datetime.value.minute
            == segments2[0].departure_datetime.value.minute
        )
        assert segments1[0].departure_datetime.value.hour == 10
        assert segments1[0].departure_datetime.value.minute == 30

        # Both should be naive
        assert segments1[0].departure_datetime.value.tzinfo is None
        assert segments2[0].departure_datetime.value.tzinfo is None
