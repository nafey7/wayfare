"""Tests for trip_details segments → flight_leg_summaries (leg boundary algorithm)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.domains.common import DateTime, Duration, MoneyAmount, PersonName
from app.domains.flight.enums import CabinClass, PassengerType, TicketStatus
from app.domains.flight.leg_summaries import (
    flight_leg_summaries_from_segments,
    flight_segment_departure_dates_iso,
)
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
    TripDetailsResponse,
)
from app.domains.flight.service import _extract_booking_sync_fields_from_trip_details


def _airport(code: str) -> AirportInfo:
    return AirportInfo(iata_code=code, airport_name=code)


def _seg(
    seg_id: int,
    dep: str,
    arr: str,
    dep_local: datetime,
    *,
    pnr: str = "PNR1",
) -> TripDetailsFlightSegment:
    airline = AirlineInfo(iata_code="ZZ", airline_name="Zz")
    flight_num = FlightNumber(
        airline_prefix="ZZ", flight_number="1", formatted_number="ZZ1"
    )
    arr_time = dep_local + timedelta(hours=2)
    return TripDetailsFlightSegment(
        segment_id=seg_id,
        departure_datetime=DateTime(value=dep_local),
        arrival_datetime=DateTime(value=arr_time),
        departure_airport=_airport(dep),
        arrival_airport=_airport(arr),
        marketing_flight_number=flight_num,
        operating_airline=airline,
        marketing_airline=airline,
        operating_flight_number=flight_num,
        flight_duration=Duration(total_minutes=120),
        segment_stops=0,
        passenger_count=1,
        airline_pnr=AirlinePNR(pnr_code=pnr, airline=airline),
        cabin_class=CabinClass.ECONOMY,
        e_ticket=True,
    )


def test_empty_segments() -> None:
    assert flight_leg_summaries_from_segments([]) == []


def test_one_way_single_segment() -> None:
    d = datetime(2026, 4, 6, 10, 0, 0, tzinfo=UTC)
    legs = flight_leg_summaries_from_segments([_seg(1, "JFK", "LHR", d)])
    assert len(legs) == 1
    assert legs[0].origin_iata == "JFK"
    assert legs[0].destination_iata == "LHR"
    assert legs[0].departure_date == date(2026, 4, 6)


def test_connection_collapses_to_one_leg() -> None:
    d1 = datetime(2026, 4, 6, 8, 0, 0, tzinfo=UTC)
    d2 = datetime(2026, 4, 6, 14, 0, 0, tzinfo=UTC)
    legs = flight_leg_summaries_from_segments(
        [
            _seg(1, "JFK", "ORD", d1),
            _seg(2, "ORD", "LHR", d2),
        ]
    )
    assert len(legs) == 1
    assert legs[0].origin_iata == "JFK"
    assert legs[0].destination_iata == "LHR"
    assert legs[0].departure_date == date(2026, 4, 6)


def test_open_jaw_two_legs() -> None:
    d1 = datetime(2026, 4, 6, 10, 0, 0, tzinfo=UTC)
    d2 = datetime(2026, 4, 10, 10, 0, 0, tzinfo=UTC)
    legs = flight_leg_summaries_from_segments(
        [
            _seg(1, "JFK", "LAX", d1),
            _seg(2, "SFO", "JFK", d2),
        ]
    )
    assert len(legs) == 2
    assert legs[0].destination_iata == "LAX"
    assert legs[1].origin_iata == "SFO"
    assert legs[1].departure_date == date(2026, 4, 10)


def test_round_trip_with_connections_two_legs() -> None:
    out1 = datetime(2026, 5, 1, 8, 0, 0, tzinfo=UTC)
    out2 = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
    in1 = datetime(2026, 5, 8, 9, 0, 0, tzinfo=UTC)
    in2 = datetime(2026, 5, 8, 14, 0, 0, tzinfo=UTC)
    segs = [
        _seg(1, "JFK", "ORD", out1),
        _seg(2, "ORD", "LHR", out2),
        _seg(3, "LHR", "ORD", in1),
        _seg(4, "ORD", "JFK", in2),
    ]
    # Without itinerary destination, hub-to-hub connection merges entire RT into one leg.
    merged = flight_leg_summaries_from_segments(segs)
    assert len(merged) == 1
    assert merged[0].origin_iata == "JFK"
    assert merged[0].destination_iata == "JFK"

    legs = flight_leg_summaries_from_segments(
        segs,
        primary_destination_iata="LHR",
    )
    assert len(legs) == 2
    assert legs[0].origin_iata == "JFK"
    assert legs[0].destination_iata == "LHR"
    assert legs[1].origin_iata == "LHR"
    assert legs[1].destination_iata == "JFK"


def test_round_trip_multi_segment_outbound_return_primary_dest_jfk() -> None:
    """LCY→…→JFK then JFK→…→LCY (trip_details Destination=JFK) → two legs, not LCY→LCY."""
    d_out = datetime(2026, 7, 24, 9, 20, 0, tzinfo=UTC)
    d_ret = datetime(2026, 7, 28, 16, 55, 0, tzinfo=UTC)
    segs = [
        _seg(1, "LCY", "BCN", d_out),
        _seg(2, "BCN", "MAD", d_out.replace(hour=13, minute=35)),
        _seg(3, "MAD", "JFK", d_out.replace(hour=16, minute=20)),
        _seg(4, "JFK", "MAD", d_ret),
        _seg(5, "MAD", "LCY", d_ret.replace(day=29, hour=7, minute=40)),
    ]
    legs = flight_leg_summaries_from_segments(segs, primary_destination_iata="JFK")
    assert len(legs) == 2
    assert legs[0].origin_iata == "LCY"
    assert legs[0].destination_iata == "JFK"
    assert legs[0].departure_date == date(2026, 7, 24)
    assert legs[1].origin_iata == "JFK"
    assert legs[1].destination_iata == "LCY"
    assert legs[1].departure_date == date(2026, 7, 28)


def test_extract_sync_includes_leg_summaries_for_real_segments() -> None:
    d = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    seg = _seg(1, "AMS", "FAO", d)
    trip = TripDetailsResponse(
        success=True,
        booking_status=BookingStatus.CONFIRMED,
        cross_border_indicator=False,
        destination=_airport("FAO"),
        origin=_airport("AMS"),
        fare_type=FareType.PUBLIC,
        is_commissionable=False,
        is_mo_fare=False,
        external_booking_reference="UID",
        ticket_status=TicketStatus.TICKETED,
        environment=FlightAPIEnvironment.TEST,
        passengers=[
            PassengerDetails(
                passenger_type=PassengerType.ADULT,
                personal_info=PersonalInfo(
                    name=PersonName(first_name="A", last_name="B")
                ),
                reference_id=1,
                e_ticket_number="1",
            )
        ],
        segments=[seg],
        pricing=FarePricing(
            has_mixed_booking_classes=False,
            fare_source_code="FSC1",
            fare_type=FareType.PUBLIC,
            is_refundable=True,
            fare_totals=FareTotals(
                base_fare=MoneyAmount(amount=Decimal("1"), currency="EUR"),
                equivalent_fare=MoneyAmount(amount=Decimal("1"), currency="EUR"),
                service_tax=MoneyAmount(amount=Decimal("0"), currency="EUR"),
                total_tax=MoneyAmount(amount=Decimal("0"), currency="EUR"),
                total_fare=MoneyAmount(amount=Decimal("1"), currency="EUR"),
            ),
            passenger_fare_breakdown=[],
        ),
        fare_breakdown=[],
        extra_services=[],
        booking_notes=[],
        errors=[],
    )
    sync = _extract_booking_sync_fields_from_trip_details(trip)
    assert sync["flight_segment_departure_dates"] == ["2026-06-01"]
    assert "flight_leg_summaries" in sync
    assert sync["flight_leg_summaries"] == [
        {
            "departure_date": "2026-06-01",
            "origin_iata": "AMS",
            "destination_iata": "FAO",
        }
    ]
    assert flight_segment_departure_dates_iso([seg]) == ["2026-06-01"]
