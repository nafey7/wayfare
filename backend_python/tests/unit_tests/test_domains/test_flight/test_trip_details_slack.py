"""Unit tests for trip details ticketed-booking Slack notification.

Tests _is_ticketed_missing_pnr_or_eticket() helper and notification invocation
when trip details API returns ticketed status but PNR or e-ticket are missing.
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.domains.common import AuthProvider, DateTime, MoneyAmount, PersonName
from app.domains.flight.enums import CabinClass, PassengerType, TicketStatus
from app.domains.flight.schemas import (
    AirlineInfo,
    AirlinePNR,
    AirportInfo,
    BookingStatus,
    FarePricing,
    FareTotals,
    FareType,
    FlightAPIEnvironment,
    FlightNumber,
    PassengerDetails,
    PersonalInfo,
    TripDetailsFlightSegment,
    TripDetailsRequest,
    TripDetailsResponse,
)
from app.domains.flight.service import (
    FlightService,
    _is_ticketed_missing_pnr_or_eticket,
)
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic


def _make_segment(pnr_code: str) -> TripDetailsFlightSegment:
    """Create minimal segment with given PNR code."""
    from app.domains.common import Duration

    airport = AirportInfo(iata_code="LHR", airport_name="Heathrow")
    airline = AirlineInfo(iata_code="BA", airline_name="British Airways")
    dt_val = datetime(2026, 4, 1, 10, 0, 0, tzinfo=UTC)
    dt = DateTime(value=dt_val)
    duration = Duration(total_minutes=90)
    flight_num = FlightNumber(
        airline_prefix="BA",
        flight_number="123",
        formatted_number="BA123",
    )
    pnr = AirlinePNR(pnr_code=pnr_code, airline=airline)
    return TripDetailsFlightSegment(
        segment_id=1,
        departure_datetime=dt,
        arrival_datetime=dt,
        departure_airport=airport,
        arrival_airport=airport,
        marketing_flight_number=flight_num,
        operating_airline=airline,
        marketing_airline=airline,
        operating_flight_number=flight_num,
        flight_duration=duration,
        segment_stops=0,
        passenger_count=1,
        airline_pnr=pnr,
        cabin_class=CabinClass.ECONOMY,
        e_ticket=True,
    )


def _make_passenger(e_ticket_number: str | None) -> PassengerDetails:
    """Create minimal passenger with given e-ticket number."""
    return PassengerDetails(
        passenger_type=PassengerType.ADULT,
        personal_info=PersonalInfo(
            name=PersonName(first_name="Test", last_name="User")
        ),
        reference_id=1,
        e_ticket_number=e_ticket_number,
    )


def _make_trip_details(
    *,
    ticket_status: TicketStatus = TicketStatus.TICKETED,
    segments: list[TripDetailsFlightSegment] | None = None,
    passengers: list[PassengerDetails] | None = None,
    external_booking_reference: str = "EXT123",
) -> TripDetailsResponse:
    """Create minimal TripDetailsResponse for testing."""
    airport = AirportInfo(iata_code="LHR", airport_name="Heathrow")
    base_fare = MoneyAmount(amount=Decimal("100"), currency="GBP")
    fare_totals = FareTotals(
        base_fare=base_fare,
        equivalent_fare=base_fare,
        service_tax=MoneyAmount(amount=Decimal("0"), currency="GBP"),
        total_tax=base_fare,
        total_fare=base_fare,
    )
    pricing = FarePricing(
        has_mixed_booking_classes=False,
        fare_source_code="FSC1",
        fare_type=FareType.PUBLIC,
        is_refundable=True,
        fare_totals=fare_totals,
        passenger_fare_breakdown=[],
    )
    return TripDetailsResponse(
        success=True,
        booking_status=BookingStatus.CONFIRMED,
        cross_border_indicator=False,
        origin=airport,
        destination=airport,
        fare_type=FareType.PUBLIC,
        is_commissionable=False,
        is_mo_fare=False,
        external_booking_reference=external_booking_reference,
        ticket_status=ticket_status,
        environment=FlightAPIEnvironment.TEST,
        passengers=passengers or [],
        segments=segments or [],
        pricing=pricing,
        fare_breakdown=[],
        extra_services=[],
        booking_notes=[],
        errors=[],
    )


def _make_mock_user() -> UserPublic:
    """Create minimal UserPublic for testing."""
    now = datetime.now(UTC)
    return UserPublic(
        id="507f1f77bcf86cd799439011",  # pragma: allowlist secret
        email="test@example.com",
        first_name="Test",
        last_name="User",
        status=UserStatus.ACTIVE,
        role=UserRole.USER,
        email_verified=True,
        created_at=now,
        auth_provider=AuthProvider.LOCAL,
        updated_at=now,
    )


class TestIsTicketedMissingPnrOrEticket:
    """Tests for _is_ticketed_missing_pnr_or_eticket()."""

    def test_ticketed_with_valid_pnr_and_eticket_returns_false(self) -> None:
        """Ticketed + valid PNR + valid e-ticket → False (no notification)."""
        trip = _make_trip_details(
            segments=[_make_segment("ABC123")],
            passengers=[_make_passenger("1234567890123")],
        )
        assert _is_ticketed_missing_pnr_or_eticket(trip) is False

    def test_ticketed_missing_pnr_returns_true(self) -> None:
        """Ticketed + missing PNR (UNKNOWN) → True."""
        trip = _make_trip_details(
            segments=[_make_segment("UNKNOWN")],
            passengers=[_make_passenger("1234567890123")],
        )
        assert _is_ticketed_missing_pnr_or_eticket(trip) is True

    def test_ticketed_pending_pnr_returns_true(self) -> None:
        """Ticketed + PNR is PENDING → True."""
        trip = _make_trip_details(
            segments=[_make_segment("PENDING")],
            passengers=[_make_passenger("1234567890123")],
        )
        assert _is_ticketed_missing_pnr_or_eticket(trip) is True

    def test_ticketed_missing_eticket_returns_true(self) -> None:
        """Ticketed + missing e-ticket → True."""
        trip = _make_trip_details(
            segments=[_make_segment("ABC123")],
            passengers=[_make_passenger(None)],
        )
        assert _is_ticketed_missing_pnr_or_eticket(trip) is True

    def test_ticketed_empty_eticket_string_returns_true(self) -> None:
        """Ticketed + e-ticket empty string → True."""
        trip = _make_trip_details(
            segments=[_make_segment("ABC123")],
            passengers=[_make_passenger("")],
        )
        assert _is_ticketed_missing_pnr_or_eticket(trip) is True

    def test_ticketed_both_missing_returns_true(self) -> None:
        """Ticketed + both PNR and e-ticket missing → True."""
        trip = _make_trip_details(
            segments=[_make_segment("UNKNOWN")],
            passengers=[_make_passenger(None)],
        )
        assert _is_ticketed_missing_pnr_or_eticket(trip) is True

    def test_not_ticketed_returns_false(self) -> None:
        """Not ticketed → False (no notification)."""
        trip = _make_trip_details(
            ticket_status=TicketStatus.NOT_ISSUED,
            segments=[_make_segment("UNKNOWN")],
            passengers=[_make_passenger(None)],
        )
        assert _is_ticketed_missing_pnr_or_eticket(trip) is False

    def test_ticketed_empty_passengers_and_segments_returns_true(self) -> None:
        """Ticketed + empty passengers/segments → True."""
        trip = _make_trip_details(
            segments=[],
            passengers=[],
        )
        assert _is_ticketed_missing_pnr_or_eticket(trip) is True


@pytest.mark.asyncio
async def test_get_trip_details_calls_notify_when_ticketed_missing_data() -> None:
    """get_trip_details triggers Slack notification when condition holds."""
    trip = _make_trip_details(
        segments=[_make_segment("UNKNOWN")],
        passengers=[_make_passenger(None)],
    )
    mock_user = _make_mock_user()
    service = FlightService(current_user=mock_user)

    with (
        patch.object(
            service.client, "get_trip_details", new_callable=AsyncMock
        ) as mock_get,
        patch.object(service, "_enrich_airport_country_codes", new_callable=AsyncMock),
        patch(
            "app.domains.flight.service.BookingService.validate_user_owns_booking",
            new_callable=AsyncMock,
        ),
        patch(
            "app.domains.flight.service.BookingService.get_external_reference",
            new_callable=AsyncMock,
            return_value="EXT123",
        ),
        patch(
            "app.domains.flight.service.BookingService.get_parent_voya_booking_reference_for_leg",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.domains.flight.service.notify_booking_error",
            new_callable=AsyncMock,
        ) as mock_notify,
    ):
        mock_get.return_value = trip
        req = TripDetailsRequest(voya_booking_reference="VOYA-123")

        result = await service.get_trip_details(req)

        # Allow fire-and-forget task to run
        await asyncio.sleep(0.05)

        assert result == trip
        mock_notify.assert_called_once_with(
            "Trip Details API",
            "PNR or e-ticket number are missing for ticketed booking",
            context={"UniqueID": "EXT123"},
        )
