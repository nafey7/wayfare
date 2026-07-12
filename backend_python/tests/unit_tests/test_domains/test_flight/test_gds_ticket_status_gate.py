"""Unit tests for GDS ticket status gate (PLAN_GDS_TICKET_STATUS_GATE).

Tests the gate logic in isolation: FlightService._should_skip_ticket_order_for_gds().
No async, no database, no complex mocking - only Mock objects and enums.
"""

from unittest.mock import Mock

from app.domains.flight.enums import FareType, TicketStatus
from app.domains.flight.service import FlightService


def _make_trip(fare_type: FareType, ticket_status: TicketStatus) -> Mock:
    """Build minimal mock trip_details for gate tests."""
    trip = Mock()
    trip.fare_type = fare_type
    trip.ticket_status = ticket_status
    return trip


# --- Skip when ticketed or cancelled (GDS only) ---


def test_should_skip_when_ticketed_gds() -> None:
    """GDS + TICKETED -> skip ticket order API."""
    trip = _make_trip(FareType.PUBLIC, TicketStatus.TICKETED)
    assert FlightService._should_skip_ticket_order_for_gds(trip) is True


def test_should_skip_when_cancelled_gds() -> None:
    """GDS + CANCELLED -> skip ticket order API."""
    trip = _make_trip(FareType.PUBLIC, TicketStatus.CANCELLED)
    assert FlightService._should_skip_ticket_order_for_gds(trip) is True


def test_should_skip_when_ticketed_private() -> None:
    """GDS (Private) + TICKETED -> skip."""
    trip = _make_trip(FareType.PRIVATE, TicketStatus.TICKETED)
    assert FlightService._should_skip_ticket_order_for_gds(trip) is True


# --- Proceed when not issued or in process (GDS) ---


def test_should_not_skip_when_not_issued() -> None:
    """GDS + NOT_ISSUED -> proceed with ticket order API."""
    trip = _make_trip(FareType.PUBLIC, TicketStatus.NOT_ISSUED)
    assert FlightService._should_skip_ticket_order_for_gds(trip) is False


def test_should_not_skip_when_in_process() -> None:
    """GDS + IN_PROCESS -> proceed with ticket order API."""
    trip = _make_trip(FareType.PUBLIC, TicketStatus.IN_PROCESS)
    assert FlightService._should_skip_ticket_order_for_gds(trip) is False


# --- LCC (WebFare) always proceeds (gate does not apply) ---


def test_should_not_skip_when_lcc_ticketed() -> None:
    """LCC + TICKETED -> gate does not apply, proceed (is_gds=False)."""
    trip = _make_trip(FareType.WEB_FARE, TicketStatus.TICKETED)
    assert FlightService._should_skip_ticket_order_for_gds(trip) is False


def test_should_not_skip_when_lcc_cancelled() -> None:
    """LCC + CANCELLED -> gate does not apply (is_gds=False)."""
    trip = _make_trip(FareType.WEB_FARE, TicketStatus.CANCELLED)
    assert FlightService._should_skip_ticket_order_for_gds(trip) is False
