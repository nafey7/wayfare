"""Tests for Circle (multi-city) mapping in FlightLogic adapter."""

from datetime import date

from app.domains.flight.enums import CabinClass, FlightAPIEnvironment, JourneyType
from app.domains.flight.schemas import (
    AirportInfo,
    FlightSearchRequest,
    OriginDestinationSegment,
)
from integrations.flightlogic.adapter import FlightLogicSchemaAdapter


def _segment_template():
    return {
        "FlightSegment": {
            "DepartureAirportLocationCode": "DEL",
            "ArrivalAirportLocationCode": "BOM",
            "DepartureDateTime": "2026-02-01T08:00:00",
            "ArrivalDateTime": "2026-02-01T10:30:00",
            "FlightNumber": "6E123",
            "MarketingAirlineCode": "6E",
            "MarketingAirlineName": "IndiGo",
            "OperatingAirline": {
                "Code": "6E",
                "Name": "IndiGo",
                "Equipment": "320",
                "FlightNumber": "6E123",
            },
            "JourneyDuration": 150,
            "CabinClassCode": "Y",
            "Eticket": True,
        },
        "StopQuantity": 0,
        "SeatsRemaining": {"Number": 9, "BelowMinimum": False},
    }


def _fare_info():
    return {
        "DivideInPartyIndicator": False,
        "FareSourceCode": "CIRCLE_FARE_TEST",
        "FareType": "Public",
        "IsRefundable": True,
        "ItinTotalFares": {
            "BaseFare": {
                "Amount": "400.00",
                "CurrencyCode": "USD",
                "DecimalPlaces": "2",
            },
            "EquivFare": {
                "Amount": "400.00",
                "CurrencyCode": "USD",
                "DecimalPlaces": "2",
            },
            "ServiceTax": {
                "Amount": "0.00",
                "CurrencyCode": "USD",
                "DecimalPlaces": "2",
            },
            "TotalTax": {
                "Amount": "50.00",
                "CurrencyCode": "USD",
                "DecimalPlaces": "2",
            },
            "TotalFare": {
                "Amount": "450.00",
                "CurrencyCode": "USD",
                "DecimalPlaces": "2",
            },
        },
        "FareBreakdown": [
            {
                "PassengerTypeQuantity": {"Code": "ADT", "Quantity": 1},
                "PassengerFare": {
                    "BaseFare": {
                        "Amount": "400.00",
                        "CurrencyCode": "USD",
                        "DecimalPlaces": "2",
                    },
                    "EquivFare": {
                        "Amount": "400.00",
                        "CurrencyCode": "USD",
                        "DecimalPlaces": "2",
                    },
                    "ServiceTax": {
                        "Amount": "0.00",
                        "CurrencyCode": "USD",
                        "DecimalPlaces": "2",
                    },
                    "Surcharges": {
                        "Amount": "0.00",
                        "CurrencyCode": "USD",
                        "DecimalPlaces": "2",
                    },
                    "Taxes": [
                        {
                            "TaxCode": "YQ",
                            "Amount": "50.00",
                            "CurrencyCode": "USD",
                            "DecimalPlaces": "2",
                        }
                    ],
                    "TotalFare": {
                        "Amount": "450.00",
                        "CurrencyCode": "USD",
                        "DecimalPlaces": "2",
                    },
                },
                "Baggage": ["15KG"],
                "CabinBaggage": ["7KG"],
            }
        ],
    }


def test_search_request_to_dto_circle_emits_one_row_per_leg():
    adapter = FlightLogicSchemaAdapter()
    d0 = date(2026, 2, 1)
    d1 = date(2026, 2, 5)
    d2 = date(2026, 2, 10)
    request = FlightSearchRequest(
        user_id="u",
        user_password="p",
        access=FlightAPIEnvironment.TEST,
        journey_type=JourneyType.CIRCLE,
        origin_destination_info=[
            OriginDestinationSegment(
                departure_date=d0,
                origin_airport=AirportInfo(iata_code="DEL"),
                destination_airport=AirportInfo(iata_code="BOM"),
            ),
            OriginDestinationSegment(
                departure_date=d1,
                origin_airport=AirportInfo(iata_code="BOM"),
                destination_airport=AirportInfo(iata_code="DXB"),
            ),
            OriginDestinationSegment(
                departure_date=d2,
                origin_airport=AirportInfo(iata_code="DXB"),
                destination_airport=AirportInfo(iata_code="DEL"),
            ),
        ],
        cabin_class=CabinClass.ECONOMY,
        adults=1,
        children=0,
        infants=0,
    )
    dto = adapter.search_request_to_dto(request)
    assert dto.journeyType == "Circle"
    assert len(dto.OriginDestinationInfo) == 3
    rows = dto.OriginDestinationInfo
    assert rows[0].airportOriginCode == "DEL"
    assert rows[0].airportDestinationCode == "BOM"
    assert rows[0].departureDate == "2026-02-01"
    assert rows[0].returnDate is None
    assert rows[2].airportOriginCode == "DXB"
    assert rows[2].airportDestinationCode == "DEL"


def test_convert_fare_itinerary_circle_single_odo_multiple_segments():
    adapter = FlightLogicSchemaAdapter()
    opt = _segment_template()
    opt2 = {
        **_segment_template(),
        "FlightSegment": {
            **(_segment_template()["FlightSegment"]),
            "DepartureAirportLocationCode": "BOM",
            "ArrivalAirportLocationCode": "DXB",
            "DepartureDateTime": "2026-02-05T14:00:00",
            "ArrivalDateTime": "2026-02-05T18:00:00",
        },
    }
    opt3 = {
        **_segment_template(),
        "FlightSegment": {
            **(_segment_template()["FlightSegment"]),
            "DepartureAirportLocationCode": "DXB",
            "ArrivalAirportLocationCode": "DEL",
            "DepartureDateTime": "2026-02-10T09:00:00",
            "ArrivalDateTime": "2026-02-10T14:00:00",
        },
    }
    fare_data = {
        "DirectionInd": "Circle",
        "AirItineraryFareInfo": _fare_info(),
        "OriginDestinationOptions": [
            {
                "OriginDestinationOption": [opt, opt2, opt3],
                "TotalStops": 2,
            }
        ],
        "ValidatingAirlineCode": "6E",
        "IsPassportMandatory": "false",
    }
    itin = adapter._convert_fare_itinerary(fare_data)
    assert itin.journey_type == JourneyType.CIRCLE
    assert len(itin.flight_legs) == 1
    assert len(itin.flight_legs[0].flight_segments) == 3
    assert itin.flight_legs[0].flight_segments[0].departure_airport.iata_code == "DEL"
    assert itin.flight_legs[0].flight_segments[-1].arrival_airport.iata_code == "DEL"
