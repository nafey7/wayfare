"""Enhanced trip details adapter for FlightLogic API responses."""

import logging
from datetime import datetime
from typing import Any

from app.domains.flight.enums import FlightAPIEnvironment
from app.domains.flight.schemas import (
    AircraftInfo,
    AirlineInfo,
    AirlinePNR,
    AirportInfo,
    BaggageAllowance,
    BookingClassCode,
    BookingNote,
    BookingStatus,
    CabinBaggageAllowance,
    CabinClass,
    ContactInformation,
    DateTime,
    Duration,
    ExtraService,
    FareBreakdown,
    FarePricing,
    FareTotals,
    FareType,
    FlightNumber,
    IndividualPassengerFare,
    MoneyAmount,
    PassengerDetails,
    PassengerType,
    PassengerTypeInfo,
    PersonalInfo,
    PostalCode,
    TerminalInfo,
    TicketStatus,
    TravelDocuments,
    TripDetailsFlightSegment,
    TripDetailsResponse,
)

from .dto import FlightLogicTripDetailsResponse, TripDetailsBooking
from .ticket_status_parsing import parse_ticket_status_from_flightlogic_string

logger = logging.getLogger(__name__)


def parse_trip_details_response(
    dto: FlightLogicTripDetailsResponse,
) -> TripDetailsResponse:
    """Convert FlightLogic trip details response to internal schema.

    This function handles multiple possible response formats from FlightLogic API.
    """
    # Find the booking data in various possible locations
    booking_data = _extract_booking_data(dto)

    if not booking_data:
        logger.error("No booking data found in FlightLogic response")
        raise ValueError("Invalid trip details response from FlightLogic")

    # Parse all the required fields
    booking_reference = _extract_booking_reference(booking_data)
    booking_status = _parse_booking_status(booking_data)
    ticket_status = _parse_ticket_status(booking_data)
    origin, destination = _parse_airports(booking_data)
    fare_type = _parse_fare_type(booking_data)
    passengers = _parse_passengers(booking_data)
    segments = _parse_flight_segments(booking_data)
    pricing, fare_breakdown = _parse_pricing(booking_data, len(passengers))
    extra_services = _parse_extra_services(booking_data)
    booking_notes = _parse_booking_notes(booking_data)

    # Determine environment from response
    environment = FlightAPIEnvironment.TEST
    if (
        booking_data.get("Environment") == "Production"
        or booking_data.get("Target") == "Production"
    ):
        environment = FlightAPIEnvironment.PRODUCTION

    # Build the response
    return TripDetailsResponse(
        success=True,
        booking_status=booking_status,
        cross_border_indicator=booking_data.get("CrossBorderIndicator", False),
        destination=destination,
        origin=origin,
        fare_type=fare_type,
        is_commissionable=booking_data.get("IsCommissionable", False),
        is_mo_fare=booking_data.get("IsMOFare", False),
        booking_reference=booking_reference,
        ticket_status=ticket_status,
        environment=environment,
        passengers=passengers,
        segments=segments,
        pricing=pricing,
        fare_breakdown=fare_breakdown,
        extra_services=extra_services,
        booking_notes=booking_notes,
        errors=[],
    )


def _extract_booking_data(dto: FlightLogicTripDetailsResponse) -> dict[str, Any]:
    """Extract booking data from various possible response structures."""
    # Try different possible locations for booking data
    if isinstance(dto.TripDetailsResult, TripDetailsBooking):
        return dto.TripDetailsResult.model_dump()
    if isinstance(dto.TripDetailsResult, dict):
        return dto.TripDetailsResult
    if dto.BookingDetails:
        if isinstance(dto.BookingDetails, TripDetailsBooking):
            return dto.BookingDetails.model_dump()
        return dto.BookingDetails
    if dto.TripDetails:
        if isinstance(dto.TripDetails, TripDetailsBooking):
            return dto.TripDetails.model_dump()
        return dto.TripDetails
    if dto.GetBookingDetailsResponse:
        return dto.GetBookingDetailsResponse

    # If none of the above, try the raw dto
    return dto.model_dump(exclude_none=True)


def _extract_booking_reference(data: dict[str, Any]) -> str:
    """Extract booking reference from various possible field names."""
    return (
        data.get("BookingReference")
        or data.get("UniqueID")
        or data.get("PNR")
        or data.get("ConfirmationNumber")
        or data.get("booking_reference")
        or "UNKNOWN"
    )


def _parse_booking_status(data: dict[str, Any]) -> BookingStatus:
    """Parse booking status from response."""
    status_raw = data.get("Status", data.get("BookingStatus", "confirmed"))

    if isinstance(status_raw, str):
        status_lower = status_raw.lower()
        if "pending" in status_lower:
            return BookingStatus.PENDING
        if "cancel" in status_lower:
            return BookingStatus.CANCELLED
        if "confirmed" in status_lower:
            return BookingStatus.CONFIRMED

    return BookingStatus.CONFIRMED


def _parse_ticket_status(data: dict[str, Any]) -> TicketStatus:
    """Parse ticket status from response."""
    ticket_raw = data.get("TicketStatus", "not_issued")

    if isinstance(ticket_raw, str):
        return parse_ticket_status_from_flightlogic_string(ticket_raw)

    return TicketStatus.NOT_ISSUED


def _parse_fare_type(data: dict[str, Any]) -> FareType:
    """Parse fare type from response."""
    fare_type_raw = data.get("FareType", "Public")

    if isinstance(fare_type_raw, str):
        fare_lower = fare_type_raw.lower()
        if "private" in fare_lower:
            return FareType.PRIVATE
        if "web" in fare_lower:
            return FareType.WEB_FARE

    return FareType.PUBLIC


def _parse_airports(data: dict[str, Any]) -> tuple[AirportInfo, AirportInfo]:
    """Parse origin and destination airports."""
    # Try to get airport info from various fields
    origin_code = data.get("Origin", data.get("DepartureAirport", ""))
    dest_code = data.get("Destination", data.get("ArrivalAirport", ""))

    # If codes are strings, create basic airport info
    if isinstance(origin_code, str) and origin_code:
        origin = AirportInfo(
            iata_code=origin_code,
            airport_name=f"{origin_code} Airport",
            city_name=origin_code,
        )
    elif isinstance(origin_code, dict):
        origin = AirportInfo(
            iata_code=origin_code.get("Code", origin_code.get("code", "UNK")),
            airport_name=origin_code.get(
                "Name", origin_code.get("name", "Unknown Airport")
            ),
            city_name=origin_code.get("City", origin_code.get("city", "Unknown")),
        )
    else:
        origin = AirportInfo(
            iata_code="UNK", airport_name="Unknown Airport", city_name="Unknown"
        )

    if isinstance(dest_code, str) and dest_code:
        destination = AirportInfo(
            iata_code=dest_code,
            airport_name=f"{dest_code} Airport",
            city_name=dest_code,
        )
    elif isinstance(dest_code, dict):
        destination = AirportInfo(
            iata_code=dest_code.get("Code", dest_code.get("code", "UNK")),
            airport_name=dest_code.get(
                "Name", dest_code.get("name", "Unknown Airport")
            ),
            city_name=dest_code.get("City", dest_code.get("city", "Unknown")),
        )
    else:
        destination = AirportInfo(
            iata_code="UNK", airport_name="Unknown Airport", city_name="Unknown"
        )

    return origin, destination


def _parse_passengers(data: dict[str, Any]) -> list[PassengerDetails]:
    """Parse passenger details from response."""
    passengers = []

    # Get passenger data from various possible fields
    pax_data = data.get("Passengers", data.get("PassengerDetails", []))

    if not pax_data and "TravelItinerary" in data:
        # Try getting from TravelItinerary structure
        pax_data = data.get("TravelItinerary", {}).get("PassengerInfo", [])

    if not isinstance(pax_data, list):
        pax_data = [pax_data]

    for idx, pax in enumerate(pax_data):
        if not isinstance(pax, dict):
            continue

        # Parse passenger type
        pax_type_raw = pax.get("PassengerType", pax.get("Type", "ADT"))
        passenger_type = PassengerType.ADULT
        if pax_type_raw == "CHD":
            passenger_type = PassengerType.CHILD
        elif pax_type_raw == "INF":
            passenger_type = PassengerType.INFANT

        # Parse personal info
        from app.domains.flight.schemas import PersonName

        person_name = PersonName(
            title=pax.get("Title", "Mr"),
            first_name=pax.get("FirstName", f"Passenger{idx + 1}"),
            last_name=pax.get("LastName", "Name"),
            full_name=f"{pax.get('FirstName', f'Passenger{idx + 1}')} {pax.get('LastName', 'Name')}",
        )

        personal_info = PersonalInfo(
            name=person_name,
            date_of_birth=pax.get("DateOfBirth"),
            nationality=pax.get("Nationality", "US"),
        )

        # Parse travel documents if available
        travel_docs = None
        if pax.get("PassportNumber"):
            travel_docs = TravelDocuments(
                passport_number=pax.get("PassportNumber"),
                passport_expiry_date=pax.get("PassportExpiryDate"),
                passport_issue_country=pax.get("PassportIssuingCountry"),
                passport_issue_date=pax.get("PassportIssueDate"),
            )

        # Parse contact info
        email = pax.get("Email") or data.get("CustomerEmail") or "passenger@example.com"
        phone = pax.get("Phone") or data.get("CustomerPhone") or "+1234567890"

        contact_info = ContactInformation(
            email=email if email else "passenger@example.com",
            phone=phone,
            area_code=data.get("AreaCode", "+1"),
            country_code=data.get("CountryCode", "US"),
        )

        # Create postal code
        postal_code = PostalCode(
            code=data.get("PostCode", "00000"), country=data.get("CountryCode", "US")
        )

        passengers.append(
            PassengerDetails(
                passenger_type=passenger_type,
                personal_info=personal_info,
                reference_id=idx + 1,
                e_ticket_number=pax.get("TicketNumber"),
                travel_documents=travel_docs,
                contact_info=contact_info,
                postal_code=postal_code,
            )
        )

    # If no passengers found, create a default one
    if not passengers:
        from app.domains.flight.schemas import PersonName

        default_name = PersonName(
            title="Mr",
            first_name="Unknown",
            last_name="Passenger",
            full_name="Unknown Passenger",
        )

        passengers.append(
            PassengerDetails(
                passenger_type=PassengerType.ADULT,
                personal_info=PersonalInfo(
                    name=default_name, date_of_birth=None, nationality="US"
                ),
                reference_id=1,
                e_ticket_number=None,
                travel_documents=None,
                contact_info=ContactInformation(
                    email="passenger@example.com",
                    phone="+1234567890",
                    area_code="+1",
                    country_code="US",
                ),
                postal_code=PostalCode(code="00000", country="US"),
            )
        )

    return passengers


def _parse_flight_segments(data: dict[str, Any]) -> list[TripDetailsFlightSegment]:
    """Parse flight segments from response."""
    segments = []

    # Get segments from various possible fields
    segments_data = (
        data.get("FlightSegments")
        or data.get("Segments")
        or data.get("OriginDestinationOptions", [])
    )

    if not isinstance(segments_data, list):
        segments_data = [segments_data]

    for idx, seg in enumerate(segments_data):
        if not isinstance(seg, dict):
            continue

        # Parse datetime strings
        dep_dt = _parse_datetime(seg.get("DepartureDateTime", ""))
        arr_dt = _parse_datetime(seg.get("ArrivalDateTime", ""))

        # Parse airports - handle both field names
        dep_code = (
            seg.get("DepartureAirportCode")
            or seg.get("DepartureAirportLocationCode")
            or "UNK"
        )
        arr_code = (
            seg.get("ArrivalAirportCode")
            or seg.get("ArrivalAirportLocationCode")
            or "UNK"
        )

        dep_airport = AirportInfo(
            iata_code=dep_code,
            airport_name=f"{dep_code} Airport",
            city_name=seg.get("DepartureCity", dep_code),
        )

        arr_airport = AirportInfo(
            iata_code=arr_code,
            airport_name=f"{arr_code} Airport",
            city_name=seg.get("ArrivalCity", arr_code),
        )

        # Parse airlines
        marketing_code = seg.get("MarketingAirlineCode", "XX")
        operating_code = seg.get(
            "OperatingAirlineCode", seg.get("MarketingAirlineCode", "XX")
        )

        marketing_airline = AirlineInfo(
            iata_code=marketing_code if marketing_code else "XX",
            icao_code=None,
            airline_name=seg.get("MarketingAirlineName", "Unknown Airline"),
        )

        operating_airline = AirlineInfo(
            iata_code=operating_code if operating_code else "XX",
            icao_code=None,
            airline_name=seg.get(
                "OperatingAirlineName",
                seg.get("MarketingAirlineName", "Unknown Airline"),
            ),
        )

        # Parse flight numbers
        flight_num = seg.get("FlightNumber", "0000")
        op_flight_num = seg.get(
            "OperatingFlightNumber", seg.get("FlightNumber", "0000")
        )

        marketing_flight = FlightNumber(
            airline_prefix=marketing_code if marketing_code else "XX",
            flight_number=flight_num if flight_num else "0000",
            formatted_number=f"{marketing_code if marketing_code else 'XX'}{flight_num if flight_num else '0000'}",
        )

        operating_flight = FlightNumber(
            airline_prefix=operating_code if operating_code else "XX",
            flight_number=op_flight_num if op_flight_num else "0000",
            formatted_number=f"{operating_code if operating_code else 'XX'}{op_flight_num if op_flight_num else '0000'}",
        )

        # Parse aircraft
        aircraft_code = seg.get("AircraftType") or seg.get("Equipment") or "Unknown"
        aircraft = AircraftInfo(
            aircraft_type_code=aircraft_code,
            aircraft_name=seg.get("AircraftName", "Unknown Aircraft"),
        )

        # Parse duration
        duration_minutes = seg.get("Duration", seg.get("JourneyDuration", 0))
        duration = Duration(total_minutes=duration_minutes if duration_minutes else 0)

        # Parse cabin class
        cabin_raw = seg.get("CabinClass", seg.get("CabinClassCode", "Y"))
        cabin_class = CabinClass.ECONOMY
        if cabin_raw in ["C", "J", "BUSINESS"]:
            cabin_class = CabinClass.BUSINESS
        elif cabin_raw in ["F", "FIRST"]:
            cabin_class = CabinClass.FIRST
        elif cabin_raw in ["S", "PREMIUM"]:
            cabin_class = CabinClass.PREMIUM_ECONOMY

        segments.append(
            TripDetailsFlightSegment(
                segment_id=idx + 1,
                departure_datetime=dep_dt,
                arrival_datetime=arr_dt,
                departure_airport=dep_airport,
                arrival_airport=arr_airport,
                departure_terminal=(
                    TerminalInfo(
                        terminal_name=seg.get("DepartureTerminal"), airport=dep_airport
                    )
                    if seg.get("DepartureTerminal")
                    else None
                ),
                arrival_terminal=(
                    TerminalInfo(
                        terminal_name=seg.get("ArrivalTerminal"), airport=arr_airport
                    )
                    if seg.get("ArrivalTerminal")
                    else None
                ),
                marketing_flight_number=marketing_flight,
                operating_airline=operating_airline,
                marketing_airline=marketing_airline,
                operating_flight_number=operating_flight,
                aircraft=aircraft,
                flight_duration=duration,
                segment_stops=seg.get("StopQuantity", 0),
                passenger_count=len(_parse_passengers(data)),
                airline_pnr=AirlinePNR(
                    pnr_code=seg.get("AirlinePNR")
                    or data.get("PNR")
                    or _extract_booking_reference(data)
                    or "UNKNOWN",
                    airline=marketing_airline,
                    status=None,
                ),
                cabin_class=cabin_class,
                booking_class_code=(
                    BookingClassCode(class_code=seg.get("BookingClass", "Y"))
                    if seg.get("BookingClass")
                    else None
                ),
                e_ticket=seg.get(
                    "Eticket", seg.get("ETicket", True)
                ),  # Default to true for most flights
            )
        )

    # If no segments found, create a minimal one
    if not segments:
        segments.append(
            TripDetailsFlightSegment(
                segment_id=1,
                departure_datetime=DateTime(value=datetime.now()),
                arrival_datetime=DateTime(value=datetime.now()),
                departure_airport=_parse_airports(data)[0],
                arrival_airport=_parse_airports(data)[1],
                departure_terminal=None,
                arrival_terminal=None,
                marketing_flight_number=FlightNumber(
                    airline_prefix="XX", flight_number="0000", formatted_number="XX0000"
                ),
                operating_airline=AirlineInfo(
                    iata_code="XX", icao_code=None, airline_name="Unknown"
                ),
                marketing_airline=AirlineInfo(
                    iata_code="XX", icao_code=None, airline_name="Unknown"
                ),
                operating_flight_number=FlightNumber(
                    airline_prefix="XX", flight_number="0000", formatted_number="XX0000"
                ),
                aircraft=AircraftInfo(
                    aircraft_type_code="Unknown", aircraft_name="Unknown"
                ),
                flight_duration=Duration(total_minutes=0),
                segment_stops=0,
                passenger_count=1,
                airline_pnr=AirlinePNR(
                    pnr_code=_extract_booking_reference(data),
                    airline=AirlineInfo(
                        iata_code="XX", icao_code=None, airline_name="Unknown"
                    ),
                    status=None,
                ),
                cabin_class=CabinClass.ECONOMY,
                booking_class_code=None,
                e_ticket=True,  # Default to e-ticket
            )
        )

    return segments


def _parse_datetime(dt_str: str) -> DateTime:
    """Parse datetime string to DateTime object.

    Keeps datetime as naive (local airport time) - no timezone conversion.
    """
    if not dt_str:
        return DateTime(value=datetime.now())

    try:
        # Try parsing ISO format
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        # Remove timezone info to keep as naive datetime (local airport time)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return DateTime(value=dt)
    except (ValueError, TypeError):
        # Try parsing as-is with datetime
        try:
            from dateutil import parser

            dt = parser.parse(dt_str)
            # Remove timezone info to keep as naive datetime (local airport time)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return DateTime(value=dt)
        except (ValueError, ImportError, TypeError):
            # Fallback to current time if all parsing fails
            return DateTime(value=datetime.now())


def _parse_pricing(
    data: dict[str, Any], passenger_count: int
) -> tuple[FarePricing, list[FareBreakdown]]:
    """Parse pricing information from response."""
    # Get fare details from various possible locations
    fare_data = (
        data.get("FareDetails")
        or data.get("TotalFare")
        or data.get("ItineraryPricing")
        or {}
    )

    # Parse amounts
    currency = data.get("Currency", fare_data.get("CurrencyCode", "EUR"))

    # Create money amounts
    base_amount = _parse_money_amount(fare_data.get("BaseFare"), currency)
    tax_amount = _parse_money_amount(fare_data.get("Tax"), currency)
    total_amount = _parse_money_amount(
        fare_data.get("TotalFare") or data.get("TotalAmount"), currency
    )

    # If total is not available, calculate it
    if total_amount.amount == 0:
        total_amount = MoneyAmount(
            amount=base_amount.amount + tax_amount.amount,
            currency=currency,
            decimal_places=2,
        )

    # Create fare totals
    fare_totals = FareTotals(
        base_fare=base_amount,
        equivalent_fare=base_amount,
        service_tax=MoneyAmount(amount=0, currency=currency, decimal_places=2),
        total_tax=tax_amount,
        total_fare=total_amount,
    )

    # Create pricing
    pricing = FarePricing(
        has_mixed_booking_classes=False,
        fare_source_code=_extract_booking_reference(data) or "UNKNOWN",
        fare_type=_parse_fare_type(data),
        is_refundable=(
            fare_data.get("IsRefundable", False)
            if isinstance(fare_data.get("IsRefundable"), bool)
            else False
        ),
        fare_totals=fare_totals,
        passenger_fare_breakdown=[],  # Will be filled below
    )

    # Create fare breakdown per passenger
    fare_breakdown = []

    # Get breakdown data if available
    breakdown_data = fare_data.get("FareBreakdown", [])
    if not isinstance(breakdown_data, list):
        breakdown_data = [breakdown_data] if breakdown_data else []

    if not breakdown_data:
        # Create default breakdown
        per_pax_base = (
            base_amount.amount / passenger_count
            if passenger_count > 0
            else base_amount.amount
        )
        per_pax_tax = (
            tax_amount.amount / passenger_count
            if passenger_count > 0
            else tax_amount.amount
        )
        per_pax_total = (
            total_amount.amount / passenger_count
            if passenger_count > 0
            else total_amount.amount
        )

        for _i in range(passenger_count):
            individual_fare = IndividualPassengerFare(
                base_fare=MoneyAmount(
                    amount=per_pax_base, currency=currency, decimal_places=2
                ),
                equi_fare=MoneyAmount(
                    amount=per_pax_base, currency=currency, decimal_places=2
                ),
                service_tax=MoneyAmount(amount=0, currency=currency, decimal_places=2),
                total_tax=MoneyAmount(
                    amount=per_pax_tax, currency=currency, decimal_places=2
                ),
                total_fare=MoneyAmount(
                    amount=per_pax_total, currency=currency, decimal_places=2
                ),
                discount=MoneyAmount(amount=0, currency=currency, decimal_places=2),
                tax_breakdown=[],
            )

            fare_breakdown.append(
                FareBreakdown(
                    passenger_type_info=PassengerTypeInfo(
                        passenger_type=PassengerType.ADULT, passenger_count=1
                    ),
                    individual_fare=individual_fare,
                    baggage_allowance=[
                        BaggageAllowance(
                            baggage_id="1",
                            baggage_pieces=1,
                            baggage_weight=23,
                            baggage_unit="KG",
                        )
                    ],
                    cabin_baggage_allowance=[
                        CabinBaggageAllowance(
                            cabin_baggage_id="1",
                            cabin_baggage_pieces=1,
                            cabin_baggage_weight=7,
                            cabin_baggage_unit="KG",
                        )
                    ],
                    fare_basis_codes=["Y"],
                    penalty_details=[],
                )
            )

    # Update pricing with fare breakdown
    pricing.passenger_fare_breakdown = fare_breakdown

    return pricing, fare_breakdown


def _parse_money_amount(amount_data: Any, default_currency: str = "EUR") -> MoneyAmount:
    """Parse money amount from various formats."""
    if isinstance(amount_data, dict):
        return MoneyAmount(
            amount=float(amount_data.get("Amount", 0)),
            currency=amount_data.get("CurrencyCode") or default_currency or "EUR",
            decimal_places=amount_data.get("DecimalPlaces", 2),
        )
    if isinstance(amount_data, int | float):
        return MoneyAmount(
            amount=float(amount_data), currency=default_currency, decimal_places=2
        )
    if isinstance(amount_data, str):
        try:
            return MoneyAmount(
                amount=float(amount_data), currency=default_currency, decimal_places=2
            )
        except (ValueError, TypeError, KeyError):
            return MoneyAmount(amount=0, currency=default_currency, decimal_places=2)
    else:
        return MoneyAmount(amount=0, currency=default_currency, decimal_places=2)


def _parse_extra_services(data: dict[str, Any]) -> list[ExtraService]:
    """Parse extra services from response."""
    services = []

    services_data = data.get("ExtraServices", [])
    if not isinstance(services_data, list):
        services_data = [services_data] if services_data else []

    for service in services_data:
        if isinstance(service, dict):
            services.append(
                ExtraService(
                    service_id=service.get("ServiceId", ""),
                    service_type=service.get("ServiceType", "OTHER"),
                    service_name=service.get("ServiceName", "Extra Service"),
                    description=service.get("Description", ""),
                    price=_parse_money_amount(
                        service.get("Price"), data.get("Currency", "EUR")
                    ),
                    currency=service.get("Currency", "EUR"),
                    is_mandatory=service.get("IsMandatory", False),
                )
            )

    return services


def _parse_booking_notes(data: dict[str, Any]) -> list[BookingNote]:
    """Parse booking notes from response."""
    notes = []

    notes_data = data.get("BookingNotes", data.get("Notes", ""))

    if isinstance(notes_data, str) and notes_data:
        notes.append(
            BookingNote(
                note_type="GENERAL",
                note_text=notes_data,
                created_date=datetime.now().isoformat(),
            )
        )
    elif isinstance(notes_data, list):
        for note in notes_data:
            if isinstance(note, dict):
                notes.append(
                    BookingNote(
                        note_type=note.get("Type", "GENERAL"),
                        note_text=note.get("Text", ""),
                        created_date=note.get(
                            "CreatedDate", datetime.now().isoformat()
                        ),
                    )
                )
            elif isinstance(note, str):
                notes.append(
                    BookingNote(
                        note_type="GENERAL",
                        note_text=note,
                        created_date=datetime.now().isoformat(),
                    )
                )

    return notes
