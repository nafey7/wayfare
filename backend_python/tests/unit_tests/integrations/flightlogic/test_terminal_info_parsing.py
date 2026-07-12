"""Unit tests for TerminalInfo parsing in FlightLogic adapters.

Tests the fix for GitHub issue #219: TerminalInfo parsing failure due to
incorrect data mapping. The TerminalInfo model requires:
- terminal_name: str (required)
- airport: AirportInfo (required)

But the code was incorrectly using:
- terminal=... (wrong parameter name)
- Missing airport parameter

This test ensures both adapters correctly construct TerminalInfo objects.
"""

import pytest

from app.domains.flight.schemas import AirportInfo, TerminalInfo
from integrations.flightlogic.adapter import FlightLogicSchemaAdapter
from integrations.flightlogic.trip_details_adapter import _parse_flight_segments


class TestTerminalInfoParsingInAdapter:
    """Test TerminalInfo parsing in FlightLogicSchemaAdapter._parse_flight_segments."""

    @pytest.fixture
    def adapter(self):
        """Create FlightLogicSchemaAdapter instance for testing."""
        return FlightLogicSchemaAdapter()

    def test_parses_terminal_info_with_correct_parameters(self, adapter):
        """Test that TerminalInfo is constructed with terminal_name and airport.

        This test verifies the fix for issue #219 where TerminalInfo was
        incorrectly constructed with 'terminal=' instead of 'terminal_name='
        and missing the required 'airport' parameter.
        """
        # Mock data matching the bug scenario from issue #219
        segment_data = {
            "DepartureAirportCode": "JFK",
            "ArrivalAirportCode": "LHR",
            "DepartureTerminal": "S",  # This is what FlightLogic returns
            "ArrivalTerminal": "5",
            "DepartureDateTime": "2025-01-15T10:00:00",
            "ArrivalDateTime": "2025-01-15T18:30:00",
            "FlightNumber": "BA123",
            "MarketingAirlineCode": "BA",
            "OperatingAirlineCode": "BA",
            "OperatingFlightNumber": "BA123",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 510,  # 8.5 hours
        }

        booking_data = {
            "FlightSegments": [segment_data],
            "Passengers": [{"PassengerType": "ADT"}],
        }

        # Parse segments
        segments = adapter._parse_flight_segments(booking_data, passenger_count=1)

        # Verify segment was created
        assert len(segments) == 1
        segment = segments[0]

        # Verify TerminalInfo objects are correctly constructed
        assert segment.departure_terminal is not None
        assert isinstance(segment.departure_terminal, TerminalInfo)
        assert segment.departure_terminal.terminal_name == "S"
        assert segment.departure_terminal.airport is not None
        assert isinstance(segment.departure_terminal.airport, AirportInfo)
        assert segment.departure_terminal.airport.iata_code == "JFK"

        assert segment.arrival_terminal is not None
        assert isinstance(segment.arrival_terminal, TerminalInfo)
        assert segment.arrival_terminal.terminal_name == "5"
        assert segment.arrival_terminal.airport is not None
        assert isinstance(segment.arrival_terminal.airport, AirportInfo)
        assert segment.arrival_terminal.airport.iata_code == "LHR"

    def test_handles_missing_terminal_info(self, adapter):
        """Test that missing terminal info results in None (not an error)."""
        segment_data = {
            "DepartureAirportCode": "JFK",
            "ArrivalAirportCode": "LHR",
            # No DepartureTerminal or ArrivalTerminal
            "DepartureDateTime": "2025-01-15T10:00:00",
            "ArrivalDateTime": "2025-01-15T18:30:00",
            "FlightNumber": "BA123",
            "MarketingAirlineCode": "BA",
            "OperatingAirlineCode": "BA",
            "OperatingFlightNumber": "BA123",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 510,
        }

        booking_data = {
            "FlightSegments": [segment_data],
            "Passengers": [{"PassengerType": "ADT"}],
        }

        segments = adapter._parse_flight_segments(booking_data, passenger_count=1)

        assert len(segments) == 1
        segment = segments[0]
        assert segment.departure_terminal is None
        assert segment.arrival_terminal is None

    def test_handles_partial_terminal_info(self, adapter):
        """Test that only departure or arrival terminal can be present."""
        segment_data = {
            "DepartureAirportCode": "JFK",
            "ArrivalAirportCode": "LHR",
            "DepartureTerminal": "4",  # Only departure terminal
            # No ArrivalTerminal
            "DepartureDateTime": "2025-01-15T10:00:00",
            "ArrivalDateTime": "2025-01-15T18:30:00",
            "FlightNumber": "BA123",
            "MarketingAirlineCode": "BA",
            "OperatingAirlineCode": "BA",
            "OperatingFlightNumber": "BA123",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 510,
        }

        booking_data = {
            "FlightSegments": [segment_data],
            "Passengers": [{"PassengerType": "ADT"}],
        }

        segments = adapter._parse_flight_segments(booking_data, passenger_count=1)

        assert len(segments) == 1
        segment = segments[0]
        assert segment.departure_terminal is not None
        assert segment.departure_terminal.terminal_name == "4"
        assert segment.departure_terminal.airport.iata_code == "JFK"
        assert segment.arrival_terminal is None

    def test_terminal_info_airport_matches_segment_airport(self, adapter):
        """Test that terminal airport matches the segment's departure/arrival airport."""
        segment_data = {
            "DepartureAirportCode": "AMS",
            "ArrivalAirportCode": "CDG",
            "DepartureTerminal": "1",
            "ArrivalTerminal": "2F",
            "DepartureDateTime": "2025-01-15T10:00:00",
            "ArrivalDateTime": "2025-01-15T12:00:00",
            "FlightNumber": "KL1234",
            "MarketingAirlineCode": "KL",
            "OperatingAirlineCode": "KL",
            "OperatingFlightNumber": "KL1234",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 120,
        }

        booking_data = {
            "FlightSegments": [segment_data],
            "Passengers": [{"PassengerType": "ADT"}],
        }

        segments = adapter._parse_flight_segments(booking_data, passenger_count=1)

        assert len(segments) == 1
        segment = segments[0]

        # Verify terminal airports match segment airports
        assert (
            segment.departure_terminal.airport.iata_code
            == segment.departure_airport.iata_code
        )
        assert segment.departure_terminal.airport.iata_code == "AMS"
        assert (
            segment.arrival_terminal.airport.iata_code
            == segment.arrival_airport.iata_code
        )
        assert segment.arrival_terminal.airport.iata_code == "CDG"


class TestTerminalInfoParsingInTripDetailsAdapter:
    """Test TerminalInfo parsing in trip_details_adapter._parse_flight_segments."""

    def test_parses_terminal_info_with_correct_parameters(self):
        """Test that TerminalInfo is constructed correctly in trip_details_adapter.

        This test verifies the fix for issue #219 in the standalone
        trip_details_adapter module.
        """
        segment_data = {
            "DepartureAirportCode": "DXB",
            "ArrivalAirportCode": "SIN",
            "DepartureTerminal": "3",
            "ArrivalTerminal": "1",
            "DepartureDateTime": "2025-01-15T14:00:00",
            "ArrivalDateTime": "2025-01-15T22:00:00",
            "FlightNumber": "EK123",
            "MarketingAirlineCode": "EK",
            "OperatingAirlineCode": "EK",
            "OperatingFlightNumber": "EK123",
            "CabinClass": "Business",
            "BookingClass": "J",
            "Duration": 480,
        }

        booking_data = {
            "FlightSegments": [segment_data],
        }

        # Parse segments
        segments = _parse_flight_segments(booking_data)

        # Verify segment was created
        assert len(segments) == 1
        segment = segments[0]

        # Verify TerminalInfo objects are correctly constructed
        assert segment.departure_terminal is not None
        assert isinstance(segment.departure_terminal, TerminalInfo)
        assert segment.departure_terminal.terminal_name == "3"
        assert segment.departure_terminal.airport is not None
        assert isinstance(segment.departure_terminal.airport, AirportInfo)
        assert segment.departure_terminal.airport.iata_code == "DXB"

        assert segment.arrival_terminal is not None
        assert isinstance(segment.arrival_terminal, TerminalInfo)
        assert segment.arrival_terminal.terminal_name == "1"
        assert segment.arrival_terminal.airport is not None
        assert isinstance(segment.arrival_terminal.airport, AirportInfo)
        assert segment.arrival_terminal.airport.iata_code == "SIN"

    def test_handles_missing_terminal_info(self):
        """Test that missing terminal info results in None."""
        segment_data = {
            "DepartureAirportCode": "LAX",
            "ArrivalAirportCode": "JFK",
            # No terminal information
            "DepartureDateTime": "2025-01-15T08:00:00",
            "ArrivalDateTime": "2025-01-15T16:30:00",
            "FlightNumber": "AA456",
            "MarketingAirlineCode": "AA",
            "OperatingAirlineCode": "AA",
            "OperatingFlightNumber": "AA456",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 330,
        }

        booking_data = {
            "FlightSegments": [segment_data],
        }

        segments = _parse_flight_segments(booking_data)

        assert len(segments) == 1
        segment = segments[0]
        assert segment.departure_terminal is None
        assert segment.arrival_terminal is None

    def test_handles_empty_string_terminal(self):
        """Test that empty string terminal values are treated as missing."""
        segment_data = {
            "DepartureAirportCode": "ORD",
            "ArrivalAirportCode": "MIA",
            "DepartureTerminal": "",  # Empty string
            "ArrivalTerminal": "D",  # Valid terminal
            "DepartureDateTime": "2025-01-15T06:00:00",
            "ArrivalDateTime": "2025-01-15T10:00:00",
            "FlightNumber": "UA789",
            "MarketingAirlineCode": "UA",
            "OperatingAirlineCode": "UA",
            "OperatingFlightNumber": "UA789",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 240,
        }

        booking_data = {
            "FlightSegments": [segment_data],
        }

        segments = _parse_flight_segments(booking_data)

        assert len(segments) == 1
        segment = segments[0]
        # Empty string should result in None (falsy check)
        assert segment.departure_terminal is None
        # Valid terminal should be parsed
        assert segment.arrival_terminal is not None
        assert segment.arrival_terminal.terminal_name == "D"


class TestTerminalInfoBugScenario:
    """Test the specific bug scenario from GitHub issue #219."""

    @pytest.fixture
    def adapter(self):
        """Create FlightLogicSchemaAdapter instance for testing."""
        return FlightLogicSchemaAdapter()

    def test_issue_219_scenario_single_terminal(self, adapter):
        """Test the exact scenario from issue #219: single terminal 'S'.

        FlightLogic API returned only {"terminal": "S"} but the code was
        passing it directly to TerminalInfo constructor with wrong parameter.
        """
        # Simulate the exact scenario from the issue
        segment_data = {
            "DepartureAirportCode": "JFK",
            "ArrivalAirportCode": "LHR",
            "DepartureTerminal": "S",  # Single character terminal as in issue
            "DepartureDateTime": "2025-01-15T10:00:00",
            "ArrivalDateTime": "2025-01-15T18:30:00",
            "FlightNumber": "BA123",
            "MarketingAirlineCode": "BA",
            "OperatingAirlineCode": "BA",
            "OperatingFlightNumber": "BA123",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 510,
        }

        booking_data = {
            "FlightSegments": [segment_data],
            "Passengers": [{"PassengerType": "ADT"}],
        }

        # This should not raise an error
        segments = adapter._parse_flight_segments(booking_data, passenger_count=1)

        assert len(segments) == 1
        segment = segments[0]

        # Verify TerminalInfo is correctly constructed
        assert segment.departure_terminal is not None
        assert segment.departure_terminal.terminal_name == "S"
        assert segment.departure_terminal.airport.iata_code == "JFK"

        # Verify the TerminalInfo object is valid (can be serialized)
        terminal_dict = segment.departure_terminal.model_dump()
        assert terminal_dict["terminal_name"] == "S"
        assert terminal_dict["airport"]["iata_code"] == "JFK"

    def test_multiple_segments_with_terminals(self, adapter):
        """Test multiple segments with terminal information."""
        segment1 = {
            "DepartureAirportCode": "LHR",
            "ArrivalAirportCode": "DXB",
            "DepartureTerminal": "5",
            "ArrivalTerminal": "3",
            "DepartureDateTime": "2025-01-15T10:00:00",
            "ArrivalDateTime": "2025-01-15T22:00:00",
            "FlightNumber": "EK001",
            "MarketingAirlineCode": "EK",
            "OperatingAirlineCode": "EK",
            "OperatingFlightNumber": "EK001",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 420,
        }

        segment2 = {
            "DepartureAirportCode": "DXB",
            "ArrivalAirportCode": "SIN",
            "DepartureTerminal": "3",
            "ArrivalTerminal": "1",
            "DepartureDateTime": "2025-01-16T02:00:00",
            "ArrivalDateTime": "2025-01-16T08:00:00",
            "FlightNumber": "EK402",
            "MarketingAirlineCode": "EK",
            "OperatingAirlineCode": "EK",
            "OperatingFlightNumber": "EK402",
            "CabinClass": "Economy",
            "BookingClass": "Y",
            "Duration": 360,
        }

        booking_data = {
            "FlightSegments": [segment1, segment2],
            "Passengers": [{"PassengerType": "ADT"}],
        }

        segments = adapter._parse_flight_segments(booking_data, passenger_count=1)

        assert len(segments) == 2

        # Verify first segment terminals
        assert segments[0].departure_terminal.terminal_name == "5"
        assert segments[0].departure_terminal.airport.iata_code == "LHR"
        assert segments[0].arrival_terminal.terminal_name == "3"
        assert segments[0].arrival_terminal.airport.iata_code == "DXB"

        # Verify second segment terminals
        assert segments[1].departure_terminal.terminal_name == "3"
        assert segments[1].departure_terminal.airport.iata_code == "DXB"
        assert segments[1].arrival_terminal.terminal_name == "1"
        assert segments[1].arrival_terminal.airport.iata_code == "SIN"
