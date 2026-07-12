"""Unit tests for trip-details booking synchronization."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.domains.common import DateTime, Duration, MoneyAmount, PersonName
from app.domains.flight.enums import (
    CabinClass,
    FareType,
    FlightAPIEnvironment,
    PassengerType,
    TicketStatus,
)
from app.domains.flight.schemas import (
    AirlineInfo,
    AirlinePNR,
    AirportInfo,
    BookingStatus,
    FarePricing,
    FareTotals,
    FlightNumber,
    PassengerDetails,
    PersonalInfo,
    TicketOrderRequest,
    TicketOrderResponse,
    TripDetailsFlightSegment,
    TripDetailsRequest,
    TripDetailsResponse,
)
from app.domains.flight.service import (
    FlightService,
    _extract_booking_sync_fields_from_trip_details,
)
from app.domains.user.enums import UserRole


def _make_trip_details(
    *,
    ticket_status: str = "Ticketed",
    pnr_codes: list[str] | None = None,
    e_ticket_numbers: list[str | None] | None = None,
    fare_type: FareType = FareType.PUBLIC,
):
    pnr_codes = pnr_codes or ["ABC123"]
    e_ticket_numbers = e_ticket_numbers or ["0741234567890"]
    return SimpleNamespace(
        pricing=None,
        origin=SimpleNamespace(iata_code="JFK", country_code=None),
        destination=SimpleNamespace(iata_code="LHR", country_code=None),
        ticket_status=ticket_status,
        fare_type=fare_type,
        passengers=[
            SimpleNamespace(e_ticket_number=ticket_number)
            for ticket_number in e_ticket_numbers
        ],
        segments=[
            SimpleNamespace(airline_pnr=SimpleNamespace(pnr_code=pnr_code))
            for pnr_code in pnr_codes
        ],
        errors=[],
        external_booking_reference="EXT123",
    )


def _pydantic_segment(pnr_code: str) -> TripDetailsFlightSegment:
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


def _pydantic_passenger(e_ticket_number: str | None) -> PassengerDetails:
    return PassengerDetails(
        passenger_type=PassengerType.ADULT,
        personal_info=PersonalInfo(
            name=PersonName(first_name="Test", last_name="User")
        ),
        reference_id=1,
        e_ticket_number=e_ticket_number,
    )


def _pydantic_trip_details_response(
    *,
    segments: list[TripDetailsFlightSegment],
    passengers: list[PassengerDetails],
    ticket_status: TicketStatus = TicketStatus.TICKETED,
) -> TripDetailsResponse:
    """Real TripDetailsResponse for tests that execute get_trip_details (uses model_copy)."""
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
        external_booking_reference="EXT123",
        ticket_status=ticket_status,
        environment=FlightAPIEnvironment.TEST,
        passengers=passengers,
        segments=segments,
        pricing=pricing,
        fare_breakdown=[],
        extra_services=[],
        booking_notes=[],
        errors=[],
    )


class TestTripDetailsSyncExtraction:
    """Test trip-details field extraction helpers."""

    def test_extracts_normalized_sync_fields(self):
        """Trip-details sync extracts PNRs, ticket status, and passenger e-tickets."""
        trip_details = _make_trip_details(
            ticket_status="Ticketed",
            pnr_codes=["ABC123", "ABC123", "XYZ789", "UNKNOWN"],
            e_ticket_numbers=["0741234567890", None, "0741234567890", "0741234567891"],
        )

        trip_details.segments = [
            SimpleNamespace(
                airline_pnr=SimpleNamespace(pnr_code=pnr_code),
                departure_airport=SimpleNamespace(iata_code="JFK"),
                arrival_airport=SimpleNamespace(iata_code="LHR"),
                marketing_airline=SimpleNamespace(airline_name="Test Air"),
            )
            for pnr_code in ["ABC123", "XYZ789"]
        ]

        result = _extract_booking_sync_fields_from_trip_details(trip_details)

        assert result["pnr"] == ["ABC123", "XYZ789"]
        assert result["ticket_status"] == "Ticketed"
        assert result["e_ticket_numbers"] == ["0741234567890", "0741234567891"]
        assert result["departure_airport_iata"] == "JFK"
        assert result["flight_trip_type"] == "one_way"
        assert len(result["route_legs"]) == 1

    def test_ignores_empty_sync_fields(self):
        """Empty or unknown sync values are omitted cleanly."""
        trip_details = _make_trip_details(
            ticket_status="",
            pnr_codes=["UNKNOWN"],
            e_ticket_numbers=[None, "", "UNKNOWN"],
        )
        trip_details.segments = [
            SimpleNamespace(
                airline_pnr=SimpleNamespace(pnr_code="UNKNOWN"),
                departure_airport=SimpleNamespace(iata_code="JFK"),
                arrival_airport=SimpleNamespace(iata_code="LHR"),
                marketing_airline=SimpleNamespace(airline_name="Test"),
            ),
        ]

        result = _extract_booking_sync_fields_from_trip_details(trip_details)

        assert "pnr" not in result
        assert "ticket_status" not in result
        assert "e_ticket_numbers" not in result
        assert result["departure_airport_iata"] == "JFK"
        assert result["flight_trip_type"] == "one_way"


class TestFlightServiceTripDetailsSync:
    """Test FlightService side effects for trip-details synchronization."""

    @patch(
        "app.domains.flight.service.BookingService.get_parent_voya_booking_reference_for_leg",
        new_callable=AsyncMock,
        return_value=None,
    )
    @patch("app.domains.flight.service.BookingService.update_booking_trip_details_sync")
    @patch("app.domains.flight.service.BookingService.get_external_reference")
    @patch("app.domains.flight.service.BookingService.validate_user_owns_booking")
    @patch("app.domains.flight.service.get_flights_client")
    async def test_get_trip_details_syncs_booking_fields_after_fetch(
        self,
        mock_get_flights_client,
        mock_validate_user_owns_booking,
        mock_get_external_reference,
        mock_update_booking_trip_details_sync,
        mock_get_parent_voya_booking_reference_for_leg,
    ):
        """Trip-details reads sync booking metadata into Mongo-backed booking events."""
        trip_details = _pydantic_trip_details_response(
            segments=[_pydantic_segment("ABC123")],
            passengers=[
                _pydantic_passenger("0741234567890"),
                _pydantic_passenger("0741234567891"),
            ],
        )
        mock_client = Mock()
        mock_client.get_trip_details = AsyncMock(return_value=trip_details)
        mock_get_flights_client.return_value = mock_client
        mock_validate_user_owns_booking.return_value = None
        mock_get_external_reference.return_value = "EXT123"
        mock_update_booking_trip_details_sync.return_value = None

        current_user = SimpleNamespace(id="user-1", role=UserRole.USER)
        service = FlightService(current_user)
        service._enrich_airport_country_codes = AsyncMock()

        result = await service.get_trip_details(
            TripDetailsRequest(voya_booking_reference="VOYA-123")
        )

        assert result.voya_booking_reference == "VOYA-123"
        mock_get_parent_voya_booking_reference_for_leg.assert_awaited_once_with(
            "VOYA-123"
        )
        mock_update_booking_trip_details_sync.assert_awaited_once()
        uargs, ukwargs = mock_update_booking_trip_details_sync.call_args
        assert uargs[0] == "VOYA-123"
        assert ukwargs["pnr"] == ["ABC123"]
        assert ukwargs["ticket_status"] == "Ticketed"
        assert ukwargs["e_ticket_numbers"] == ["0741234567890", "0741234567891"]
        assert ukwargs["departure_airport_iata"] == "LHR"
        assert ukwargs["flight_trip_type"] == "one_way"
        assert ukwargs["primary_marketing_airline_name"] == "British Airways"
        assert ukwargs["route_legs"] is not None
        assert ukwargs["flight_leg_summaries"] == [
            {
                "departure_date": "2026-04-01",
                "origin_iata": "LHR",
                "destination_iata": "LHR",
            }
        ]
        assert ukwargs["flight_segment_departure_dates"] == ["2026-04-01"]
        # Verify snapshot_time is a timezone-aware UTC datetime
        snapshot_time = ukwargs["ticket_status_snapshot_time"]
        assert snapshot_time.tzinfo == UTC

    @patch("app.domains.payment.PaymentService")
    @patch("app.domains.flight.service.FlightEventHandler.handle_tickets_issued")
    @patch("app.domains.flight.service.BookingService.update_booking_dates_and_flags")
    @patch(
        "app.domains.flight.service.BookingService.get_latest_booking_by_voya_reference"
    )
    @patch("app.domains.flight.service.BookingService.get_external_reference")
    @patch("app.domains.flight.service.BookingService.validate_user_owns_booking")
    @patch("app.domains.flight.service.get_flights_client")
    async def test_issue_tickets_refreshes_trip_details_after_ticketing(
        self,
        mock_get_flights_client,
        mock_validate_user_owns_booking,
        mock_get_external_reference,
        mock_get_latest_booking,
        mock_update_booking_dates_and_flags,
        mock_handle_tickets_issued,
        mock_payment_service_cls,
    ):
        """GDS ticket issuance fetches trip details again and uses refreshed data."""
        mock_client = Mock()
        mock_client.issue_tickets = AsyncMock(
            return_value=TicketOrderResponse(
                success=True,
                external_booking_reference="EXT123",
                environment=FlightAPIEnvironment.TEST,
                errors=[],
            )
        )
        mock_get_flights_client.return_value = mock_client
        mock_validate_user_owns_booking.return_value = None
        mock_get_external_reference.return_value = "EXT123"
        mock_get_latest_booking.return_value = SimpleNamespace(
            ticket_time_limit=None,
            cancellation_policy_text=None,
        )
        mock_update_booking_dates_and_flags.return_value = None
        mock_handle_tickets_issued.return_value = None

        payment_service = Mock()
        payment_service.validate_payment_succeeded = AsyncMock(return_value=None)
        payment_service.repository = Mock()
        payment_service.repository.get_transaction_by_voya_reference = AsyncMock(
            return_value=SimpleNamespace(stripe_payment_intent_id="pi_test_123")
        )
        mock_payment_service_cls.return_value = payment_service

        current_user = SimpleNamespace(id="user-1", role=UserRole.USER)
        service = FlightService(current_user)
        service._fetch_cancellation_policy_from_fare_rules = AsyncMock(
            return_value=None
        )

        pre_ticket_trip_details = _make_trip_details(ticket_status="TktInProcess")
        post_ticket_trip_details = _make_trip_details(
            ticket_status="Ticketed",
            e_ticket_numbers=["0741234567890", "0741234567891"],
        )
        service.get_trip_details = AsyncMock(
            side_effect=[pre_ticket_trip_details, post_ticket_trip_details]
        )

        response = await service.issue_tickets(
            TicketOrderRequest(
                voya_booking_reference="VOYA-123",
                payment_id="pi_test_123",
            )
        )

        assert response.success is True
        assert service.get_trip_details.await_count == 2
        first_call, second_call = service.get_trip_details.await_args_list
        assert first_call.args[0].voya_booking_reference == "VOYA-123"
        assert first_call.kwargs == {"skip_logging": True}
        assert second_call.args[0].voya_booking_reference == "VOYA-123"
        assert second_call.kwargs == {"skip_logging": True, "skip_validation": True}
        assert mock_handle_tickets_issued.await_args.args[4] is post_ticket_trip_details


class TestIssueTicketsMulticityRevolutPayment:
    """Revolut transaction stored under parent VOYA-MC-…; ticketing uses leg ref."""

    @patch("app.domains.flight.service.FlightEventHandler.handle_tickets_issued")
    @patch("app.domains.revolut_payment.RevolutPaymentService")
    @patch(
        "app.domains.flight.service.BookingService.get_parent_voya_booking_reference_for_leg",
        new_callable=AsyncMock,
    )
    @patch("app.domains.flight.service.BookingService.update_booking_dates_and_flags")
    @patch(
        "app.domains.flight.service.BookingService.get_latest_booking_by_voya_reference"
    )
    @patch("app.domains.flight.service.BookingService.get_external_reference")
    @patch("app.domains.flight.service.BookingService.validate_user_owns_booking")
    @patch("app.domains.flight.service.get_flights_client")
    async def test_issue_tickets_revolut_resolves_transaction_via_parent(
        self,
        mock_get_flights_client,
        mock_validate_user_owns_booking,
        mock_get_external_reference,
        mock_get_latest_booking,
        mock_update_booking_dates_and_flags,
        mock_get_parent,
        mock_revolut_cls,
        mock_handle_tickets_issued,
    ):
        revolut_order = "11111111-1111-1111-1111-111111111111"
        mock_get_parent.return_value = "VOYA-MC-PARENT"
        txn_parent = SimpleNamespace(
            revolut_order_id=revolut_order,
            stripe_payment_intent_id=f"revolut_{revolut_order}",
        )
        mock_revolut = Mock()
        mock_revolut.validate_payment_succeeded = AsyncMock()
        mock_revolut.repository = Mock()
        mock_revolut.repository.get_transaction_by_voya_reference = AsyncMock(
            side_effect=[None, txn_parent]
        )
        mock_revolut_cls.return_value = mock_revolut

        mock_client = Mock()
        mock_client.issue_tickets = AsyncMock(
            return_value=TicketOrderResponse(
                success=True,
                external_booking_reference="EXT123",
                environment=FlightAPIEnvironment.TEST,
                errors=[],
            )
        )
        mock_get_flights_client.return_value = mock_client
        mock_validate_user_owns_booking.return_value = None
        mock_get_external_reference.return_value = "EXT123"
        mock_get_latest_booking.return_value = SimpleNamespace(
            ticket_time_limit=None,
            cancellation_policy_text=None,
        )
        mock_update_booking_dates_and_flags.return_value = None
        mock_handle_tickets_issued.return_value = None

        current_user = SimpleNamespace(id="user-1", role=UserRole.USER)
        service = FlightService(current_user)
        pre_ticket = _make_trip_details(ticket_status="TktInProcess")
        post_ticket = _make_trip_details(ticket_status="Ticketed")
        service.get_trip_details = AsyncMock(side_effect=[pre_ticket, post_ticket])

        response = await service.issue_tickets(
            TicketOrderRequest(
                voya_booking_reference="VOYA-LEG-1",
                payment_id=revolut_order,
            )
        )

        assert response.success is True
        assert (
            mock_revolut.repository.get_transaction_by_voya_reference.await_count == 2
        )
        calls = (
            mock_revolut.repository.get_transaction_by_voya_reference.await_args_list
        )
        assert calls[0].args[0] == "VOYA-LEG-1"
        assert calls[1].args[0] == "VOYA-MC-PARENT"
