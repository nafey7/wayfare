"""Mock data for FlightLogic API responses.

This module contains sample responses that match the FlightLogic API structure.
Used by the mock server to return realistic test data.

Request-Keyed Fixtures:
    Route fixtures are loaded from tests/fixtures/flightlogic/route_fixtures.json
    Key format: "{origin}-{destination}-{journey_type}" (e.g., "AMS-BCN-oneway")
    Each route has unique airlines and pricing for realistic test scenarios.
"""

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def _date_price_multiplier(departure_date: str | None) -> float:
    """Return a deterministic price multiplier based on departure date.

    Makes mock prices vary by date so date-range searches show meaningful
    differences across days. Multiplier range: ~0.75 to ~1.35.
    """
    if not departure_date:
        return 1.0
    try:
        dt = datetime.strptime(departure_date, "%Y-%m-%d").date()
    except ValueError:
        return 1.0
    # Use day-of-week: weekends are more expensive
    dow_factors = {
        0: 0.90,  # Monday
        1: 0.85,  # Tuesday (cheapest)
        2: 0.88,  # Wednesday
        3: 0.95,  # Thursday
        4: 1.10,  # Friday
        5: 1.25,  # Saturday (most expensive)
        6: 1.05,  # Sunday
    }
    dow_factor = dow_factors.get(dt.weekday(), 1.0)
    # Add a small hash-based jitter from the day number so consecutive
    # weekdays of the same type still differ slightly.
    day_jitter = ((dt.day * 7 + dt.month * 13) % 20 - 10) / 100  # -0.10..+0.10
    return round(dow_factor + day_jitter, 2)


# City-to-airports mapping for multi-airport search simulation
# Maps primary airport code to all airports in that city
CITY_AIRPORTS = {
    "LHR": ["LHR", "LGW", "STN", "LCY", "LTN"],  # London
    "LGW": ["LHR", "LGW", "STN", "LCY", "LTN"],  # London
    "STN": ["LHR", "LGW", "STN", "LCY", "LTN"],  # London
    "LCY": ["LHR", "LGW", "STN", "LCY", "LTN"],  # London
    "LTN": ["LHR", "LGW", "STN", "LCY", "LTN"],  # London
    "CDG": ["CDG", "ORY"],  # Paris
    "ORY": ["CDG", "ORY"],  # Paris
    "JFK": ["JFK", "LGA", "EWR"],  # New York
    "LGA": ["JFK", "LGA", "EWR"],  # New York
    "EWR": ["JFK", "LGA", "EWR"],  # New York
    "NRT": ["NRT", "HND"],  # Tokyo
    "HND": ["NRT", "HND"],  # Tokyo
    # Single-airport cities return themselves
}

# Mock session tracking - maps session_id to valid fare_source_codes
MOCK_SESSIONS = {}

# Load route fixtures
_ROUTE_FIXTURES: dict = {}
_ROUTE_FIXTURES_PATH = (
    Path(__file__).parent.parent.parent
    / "fixtures"
    / "flightlogic"
    / "route_fixtures.json"
)

# Load hotel city fixtures
_HOTEL_CITY_FIXTURES: dict = {}
_HOTEL_FIXTURES_PATH = (
    Path(__file__).parent.parent.parent
    / "fixtures"
    / "flightlogic"
    / "hotel_city_fixtures.json"
)


def _load_route_fixtures() -> dict:
    """Load route fixtures from JSON file."""
    global _ROUTE_FIXTURES
    if _ROUTE_FIXTURES:
        return _ROUTE_FIXTURES

    try:
        if _ROUTE_FIXTURES_PATH.exists():
            with open(_ROUTE_FIXTURES_PATH) as f:
                data = json.load(f)
                _ROUTE_FIXTURES = data.get("routes", {})
                logger.info(
                    f"Loaded {len(_ROUTE_FIXTURES)} route fixtures from {_ROUTE_FIXTURES_PATH}"
                )
        else:
            logger.warning(f"Route fixtures not found at {_ROUTE_FIXTURES_PATH}")
    except Exception as e:
        logger.error(f"Failed to load route fixtures: {e}")

    return _ROUTE_FIXTURES


def _load_hotel_city_fixtures() -> dict:
    """Load hotel city fixtures from JSON file."""
    global _HOTEL_CITY_FIXTURES
    if _HOTEL_CITY_FIXTURES:
        return _HOTEL_CITY_FIXTURES

    try:
        if _HOTEL_FIXTURES_PATH.exists():
            with open(_HOTEL_FIXTURES_PATH) as f:
                data = json.load(f)
                _HOTEL_CITY_FIXTURES = data.get("cities", {})
                logger.info(
                    f"Loaded {len(_HOTEL_CITY_FIXTURES)} hotel city fixtures from {_HOTEL_FIXTURES_PATH}"
                )
        else:
            logger.warning(f"Hotel city fixtures not found at {_HOTEL_FIXTURES_PATH}")
    except Exception as e:
        logger.error(f"Failed to load hotel city fixtures: {e}")

    return _HOTEL_CITY_FIXTURES


def _get_city_airports(airport_code: str) -> list[str]:
    """Get all airports in the city for a given airport code.

    Args:
        airport_code: IATA airport code (e.g., "LHR", "CDG")

    Returns:
        List of airport codes in the same city

    Examples:
        "LHR" -> ["LHR", "LGW", "STN", "LCY", "LTN"]
        "CDG" -> ["CDG", "ORY"]
        "AMS" -> ["AMS"] (single-airport city)
    """
    return CITY_AIRPORTS.get(airport_code.upper(), [airport_code.upper()])


def _get_city_key(city_name: str) -> str:
    """Generate city key for hotel fixture lookup."""
    return city_name.lower().strip()


def _build_hotel_from_fixture(
    hotel: dict,
    session_id: str,
    index: int,
    currency: str = "EUR",
) -> dict:
    """Build FlightLogic Hotel API v6 hotel structure from simplified fixture data.

    Args:
        hotel: Hotel fixture data
        session_id: Session ID for token generation
        index: Hotel index for token generation
        currency: Currency code (default EUR)

    Returns:
        Hotel dict matching FlightLogic Hotel API v6 structure
    """
    price = hotel["price_per_night_eur"]

    # Convert EUR to other currencies if needed (simple mock conversion)
    if currency == "INR":
        price = price * 90  # Approximate EUR to INR
    elif currency == "USD":
        price = price * 1.1  # Approximate EUR to USD
    elif currency == "GBP":
        price = price * 0.86  # Approximate EUR to GBP

    return {
        "hotelId": hotel["hotel_id"],
        "twxHotelId": f"TWX_{hotel['hotel_id']}",
        "productId": "trx109",
        "tokenId": f"MOCK_TOKEN_{session_id[-8:]}_{index:03d}",
        "hotelName": hotel["name"],
        "city": hotel["city"],
        "locality": hotel.get("locality", ""),
        "distanceValue": round(1.0 + index * 2.5, 2),  # Mock distance
        "distanceUnit": "KM",
        "country": "",
        "countryCode": "",
        "address": hotel["address"],
        "latitude": hotel.get("latitude", "0.00000000000000000000"),
        "longitude": hotel.get("longitude", "0.00000000000000000000"),
        "hotelRating": hotel["star_rating"],
        "total": f"{price:.2f}",
        "perNightArray": [
            {"nightIndex": 1, "currency": currency, "price": f"{price:.2f}"}
        ],
        "currency": currency,
        "fareType": "Refundable",
        "propertyType": "",
        "postalCode": "",
        "phone": "",
        "email": "",
        "thumbNailUrl": f"https://example.com/hotels/{hotel['hotel_id']}/thumb.jpg",
        "facilities": hotel.get("facilities", ["Wi-fi"]),
        "tripAdvisorRating": hotel.get("review_score", 0),
        "tripAdvisorReview": hotel.get("review_count", 0),
        "special": "",
    }


def _build_generic_fare_itinerary(
    origin: str,
    destination: str,
    price: float,
    tax: float,
    total: float,
    flight: dict,
    origin_dest_options: list,
    fare_code: str,
    currency: str = "USD",
) -> dict:
    """Build a generic fare itinerary structure.

    Args:
        origin: Origin airport code
        destination: Destination airport code
        price: Base price
        tax: Tax amount
        total: Total price
        flight: Flight details dict
        origin_dest_options: Origin destination options list
        fare_code: Unique fare source code

    Returns:
        Fare itinerary dict matching FlightLogic API structure
    """
    return {
        "DirectionInd": "OneWay",
        "AirItineraryFareInfo": {
            "DivideInPartyIndicator": False,
            "FareSourceCode": fare_code,
            "FareType": "Public",
            "IsRefundable": flight["refundable"],
            "ItinTotalFares": {
                "BaseFare": {
                    "Amount": f"{price:.2f}",
                    "CurrencyCode": currency,
                    "DecimalPlaces": "2",
                },
                "EquivFare": {
                    "Amount": f"{price:.2f}",
                    "CurrencyCode": currency,
                    "DecimalPlaces": "2",
                },
                "ServiceTax": {
                    "Amount": f"{tax * 0.1:.2f}",
                    "CurrencyCode": currency,
                    "DecimalPlaces": "2",
                },
                "TotalTax": {
                    "Amount": f"{tax:.2f}",
                    "CurrencyCode": currency,
                    "DecimalPlaces": "2",
                },
                "TotalFare": {
                    "Amount": f"{total:.2f}",
                    "CurrencyCode": currency,
                    "DecimalPlaces": "2",
                },
            },
        },
        "OriginDestinationOptions": origin_dest_options,
        "ValidatingAirlineCode": flight["airline_code"],
        "IsPassportMandatory": "true",
    }


def _get_route_key(origin: str, destination: str, journey_type: str = "oneway") -> str:
    """Generate route key for fixture lookup."""
    return f"{origin.upper()}-{destination.upper()}-{journey_type}"


# Common hub airports for multi-stop flights
MOCK_HUB_AIRPORTS = {
    "FRA": {"city": "Frankfurt", "name": "Frankfurt Airport"},
    "CDG": {"city": "Paris", "name": "Charles de Gaulle Airport"},
    "MAD": {"city": "Madrid", "name": "Madrid-Barajas Airport"},
    "FCO": {"city": "Rome", "name": "Rome Fiumicino Airport"},
    "MUC": {"city": "Munich", "name": "Munich Airport"},
    "ZRH": {"city": "Zurich", "name": "Zurich Airport"},
}


def _build_multi_segment_flight(
    origin: str,
    destination: str,
    departure_date: str,
    stops: int,
    airline_code: str,
    airline_name: str,
    base_flight_number: str,
    base_departure_time: str = "09:30",
    cabin_class_code: str = "Y",
) -> tuple[list[dict], int]:
    """Build multiple flight segments for multi-stop flights.

    Args:
        origin: Origin airport IATA code
        destination: Destination airport IATA code
        departure_date: Departure date (YYYY-MM-DD)
        stops: Number of stops (0=direct, 1=one stop, 2=two stops)
        airline_code: Airline code
        airline_name: Airline name
        base_flight_number: Base flight number (will be incremented for each segment)
        base_departure_time: Starting departure time (HH:MM)
        cabin_class_code: CabinClassCode for segments (Y/S/C/F)

    Returns:
        Tuple of (list of OriginDestinationOption segments, total duration in minutes)
    """
    if stops == 0:
        # Direct flight - single segment
        segment_duration = 120  # 2 hours
        dep_hour, dep_min = map(int, base_departure_time.split(":"))
        arr_hour = dep_hour + 2
        arr_min = dep_min

        return [
            {
                "FlightSegment": {
                    "DepartureAirportLocationCode": origin,
                    "ArrivalAirportLocationCode": destination,
                    "DepartureDateTime": f"{departure_date}T{base_departure_time}:00",
                    "ArrivalDateTime": f"{departure_date}T{arr_hour:02d}:{arr_min:02d}:00",
                    "FlightNumber": base_flight_number,
                    "MarketingAirlineCode": airline_code,
                    "MarketingAirlineName": airline_name,
                    "OperatingAirline": {
                        "Code": airline_code,
                        "Name": airline_name,
                        "Equipment": "320",
                        "FlightNumber": base_flight_number,
                    },
                    "JourneyDuration": segment_duration,
                    "CabinClassCode": cabin_class_code,
                    "Eticket": True,
                },
                "StopQuantity": 0,
                "SeatsRemaining": {"Number": 5, "BelowMinimum": True},
            }
        ], segment_duration

    # Multi-stop flight - need intermediate airports
    hub_codes = list(MOCK_HUB_AIRPORTS.keys())
    # Filter out origin and destination from hub options
    available_hubs = [h for h in hub_codes if h not in (origin, destination)]

    segments = []
    total_duration = 0
    current_origin = origin
    dep_hour, dep_min = map(int, base_departure_time.split(":"))

    for i in range(stops + 1):  # stops + 1 segments needed
        is_last_segment = i == stops
        current_dest = (
            destination if is_last_segment else available_hubs[i % len(available_hubs)]
        )

        # Segment duration: 90-150 minutes per segment
        segment_duration = 90 + (i * 30)
        arr_minutes = dep_hour * 60 + dep_min + segment_duration
        arr_hour = (arr_minutes // 60) % 24
        arr_min = arr_minutes % 60

        flight_num = f"{airline_code}{int(base_flight_number[-4:]) + i}"

        segment = {
            "FlightSegment": {
                "DepartureAirportLocationCode": current_origin,
                "ArrivalAirportLocationCode": current_dest,
                "DepartureDateTime": f"{departure_date}T{dep_hour:02d}:{dep_min:02d}:00",
                "ArrivalDateTime": f"{departure_date}T{arr_hour:02d}:{arr_min:02d}:00",
                "FlightNumber": flight_num,
                "MarketingAirlineCode": airline_code,
                "MarketingAirlineName": airline_name,
                "OperatingAirline": {
                    "Code": airline_code,
                    "Name": airline_name,
                    "Equipment": "320" if i % 2 == 0 else "738",
                    "FlightNumber": flight_num,
                },
                "JourneyDuration": segment_duration,
                "CabinClassCode": cabin_class_code,
                "Eticket": True,
            },
            "StopQuantity": 0 if is_last_segment else 1,
            "SeatsRemaining": {"Number": 9 - i, "BelowMinimum": False},
        }

        # Add StopQuantityInfo for non-final segments (layover info)
        if not is_last_segment:
            layover_minutes = 60 + (i * 15)  # 60-90 minute layovers
            next_dep_minutes = arr_minutes + layover_minutes
            next_dep_hour = (next_dep_minutes // 60) % 24
            next_dep_min = next_dep_minutes % 60

            segment["StopQuantityInfo"] = {
                "ArrivalDateTime": f"{departure_date}T{arr_hour:02d}:{arr_min:02d}:00",
                "DepartureDateTime": f"{departure_date}T{next_dep_hour:02d}:{next_dep_min:02d}:00",
                "Duration": f"{layover_minutes // 60}h {layover_minutes % 60}m",
                "LocationCode": current_dest,
            }

            # Update for next segment
            dep_hour = next_dep_hour
            dep_min = next_dep_min
            total_duration += layover_minutes

        segments.append(segment)
        total_duration += segment_duration
        current_origin = current_dest

    return segments, total_duration


def _build_origin_destination_options(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None,
    stops: int,
    airline_code: str,
    airline_name: str,
    base_flight_number: str,
    cabin_class_code: str = "Y",
) -> list[dict]:
    """Build OriginDestinationOptions for one-way or round-trip flights.

    Args:
        origin: Origin airport IATA code
        destination: Destination airport IATA code
        departure_date: Departure date (YYYY-MM-DD)
        return_date: Return date for round trips (YYYY-MM-DD) or None for one-way
        stops: Number of stops
        airline_code: Airline code
        airline_name: Airline name
        base_flight_number: Base flight number

    Returns:
        List of OriginDestinationOptions (1 for one-way, 2 for round-trip)
    """
    # Build outbound leg
    outbound_segments, _outbound_duration = _build_multi_segment_flight(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        stops=stops,
        airline_code=airline_code,
        airline_name=airline_name,
        base_flight_number=base_flight_number,
        base_departure_time="09:30",
        cabin_class_code=cabin_class_code,
    )

    options = [
        {
            "OriginDestinationOption": outbound_segments,
            "TotalStops": stops,
        }
    ]

    # Add return leg if round trip
    if return_date:
        # Return flight with potentially different number of stops
        return_stops = max(0, stops - 1)  # Return often has fewer stops
        return_flight_num = f"{airline_code}{int(base_flight_number[-4:]) + 100}"

        return_segments, _return_duration = _build_multi_segment_flight(
            origin=destination,  # Swap origin/destination
            destination=origin,
            departure_date=return_date,
            stops=return_stops,
            airline_code=airline_code,
            airline_name=airline_name,
            base_flight_number=return_flight_num,
            base_departure_time="14:30",  # Later departure for return
            cabin_class_code=cabin_class_code,
        )

        options.append(
            {
                "OriginDestinationOption": return_segments,
                "TotalStops": return_stops,
            }
        )

    return options


def _build_fare_itinerary_from_fixture(
    flight: dict,
    origin: str,
    destination: str,
    departure_date: str,
    fare_code: str,
    return_date: str | None = None,
    cabin_class_code: str = "Y",
    price_multiplier: float = 1.0,
    currency: str = "USD",
) -> dict:
    """Build FlightLogic FareItinerary structure from simplified fixture data.

    Args:
        flight: Flight fixture data with airline_code, price_eur, stops, etc.
        origin: Origin airport IATA code
        destination: Destination airport IATA code
        departure_date: Departure date (YYYY-MM-DD)
        fare_code: Fare source code for this flight
        return_date: Return date for round trips (YYYY-MM-DD) or None
        cabin_class_code: CabinClassCode for segments (Y/S/C/F)
        price_multiplier: Price multiplier based on cabin class

    Returns:
        Dict with FareItinerary structure matching FlightLogic API
    """
    date_mult = _date_price_multiplier(departure_date)
    price = flight["price_eur"] * price_multiplier * date_mult
    # For round trips, double the price
    if return_date:
        price = price * 1.8  # Round trip is slightly less than 2x
    tax = round(price * 0.15, 2)  # 15% tax
    total = round(price + tax, 2)

    # Build proper multi-segment flights using helper function
    stops = flight.get("stops", 0)
    origin_dest_options = _build_origin_destination_options(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        stops=stops,
        airline_code=flight["airline_code"],
        airline_name=flight["airline_name"],
        base_flight_number=flight["flight_number"],
        cabin_class_code=cabin_class_code,
    )

    return {
        "FareItinerary": {
            "DirectionInd": "Return" if return_date else "OneWay",
            "AirItineraryFareInfo": {
                "DivideInPartyIndicator": False,
                "FareSourceCode": fare_code,
                "FareType": "Public",
                "IsRefundable": flight.get("refundable", True),
                "ItinTotalFares": {
                    "BaseFare": {
                        "Amount": f"{price:.2f}",
                        "CurrencyCode": currency,
                        "DecimalPlaces": "2",
                    },
                    "EquivFare": {
                        "Amount": f"{price:.2f}",
                        "CurrencyCode": currency,
                        "DecimalPlaces": "2",
                    },
                    "ServiceTax": {
                        "Amount": "0.00",
                        "CurrencyCode": currency,
                        "DecimalPlaces": "2",
                    },
                    "TotalTax": {
                        "Amount": f"{tax:.2f}",
                        "CurrencyCode": currency,
                        "DecimalPlaces": "2",
                    },
                    "TotalFare": {
                        "Amount": f"{total:.2f}",
                        "CurrencyCode": currency,
                        "DecimalPlaces": "2",
                    },
                },
                "FareBreakdown": [
                    {
                        "PassengerTypeQuantity": {"Code": "ADT", "Quantity": 1},
                        "PassengerFare": {
                            "BaseFare": {
                                "Amount": f"{price:.2f}",
                                "CurrencyCode": currency,
                                "DecimalPlaces": "2",
                            },
                            "EquivFare": {
                                "Amount": f"{price:.2f}",
                                "CurrencyCode": currency,
                                "DecimalPlaces": "2",
                            },
                            "ServiceTax": {
                                "Amount": "0.00",
                                "CurrencyCode": currency,
                                "DecimalPlaces": "2",
                            },
                            "Surcharges": {
                                "Amount": "0.00",
                                "CurrencyCode": currency,
                                "DecimalPlaces": "2",
                            },
                            "Taxes": [
                                {
                                    "TaxCode": "VAT",
                                    "Amount": f"{tax:.2f}",
                                    "CurrencyCode": currency,
                                    "DecimalPlaces": "2",
                                }
                            ],
                            "TotalFare": {
                                "Amount": f"{total:.2f}",
                                "CurrencyCode": currency,
                                "DecimalPlaces": "2",
                            },
                        },
                        "Baggage": ["23KG"] if flight.get("refundable") else ["20KG"],
                        "CabinBaggage": ["7KG"],
                    }
                ],
            },
            "OriginDestinationOptions": origin_dest_options,
            "ValidatingAirlineCode": flight["airline_code"],
            "IsPassportMandatory": "true",
        }
    }


def generate_mock_session_id() -> str:
    """Generate a mock session ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"MOCK_SESSION_{timestamp}"


# Cabin class code mapping: API request value → FlightLogic CabinClassCode
CABIN_CLASS_TO_CODE = {
    "Economy": "Y",
    "PremiumEconomy": "S",
    "Business": "C",
    "First": "F",
}

# Price multipliers by cabin class (relative to Economy base price)
CABIN_CLASS_PRICE_MULTIPLIER = {
    "Y": 1.0,  # Economy - base price
    "S": 1.6,  # Premium Economy - 1.6x
    "C": 2.8,  # Business - 2.8x
    "F": 4.5,  # First - 4.5x
}


def get_mock_search_response(
    origin: str = "AMS",
    destination: str = "LHR",
    departure_date: str | None = None,
    return_date: str | None = None,
    city_wise_search_origin: bool = False,
    city_wise_search_destination: bool = False,
    cabin_class: str | None = None,
    direct_flight: int | None = None,
    preferred_airline: str | None = None,
    currency: str = "USD",
) -> dict:
    """Generate a mock flight search response.

    Uses route-specific fixtures when available for realistic, deterministic results.
    Falls back to generic mock data for routes not in fixtures.

    Supports flight filters:
    - cabin_class: Sets CabinClassCode on segments and adjusts pricing
    - direct_flight: When 1, only returns direct (0-stop) flights
    - preferred_airline: IATA code to filter flights by airline

    Args:
        origin: Origin airport IATA code
        destination: Destination airport IATA code
        departure_date: Departure date (YYYY-MM-DD)
        return_date: Return date for round trips (YYYY-MM-DD)
        city_wise_search_origin: Whether to search all airports in origin city
        city_wise_search_destination: Whether to search all airports in destination city
        cabin_class: Cabin class filter ("Economy", "Business", "First", "PremiumEconomy")
        direct_flight: 1 for direct flights only, 0 or None for all flights
        preferred_airline: IATA airline code to filter by (e.g., "BA", "EK")

    Returns:
        Mock FlightLogicSearchResponse matching the API structure

    Special Test Cases:
        - destination="XXX" -> Returns 0 flights (for testing "no results" scenario)
        - origin="XXX" -> Returns 0 flights (for testing "no results" scenario)
    """
    # Generate session ID
    session_id = generate_mock_session_id()

    # Resolve cabin class code (default to Economy "Y")
    cabin_class_code = CABIN_CLASS_TO_CODE.get(cabin_class or "Economy", "Y")
    price_multiplier = CABIN_CLASS_PRICE_MULTIPLIER.get(cabin_class_code, 1.0)

    logger.info(
        f"🚀 MOCK API CALLED: origin={origin}, dest={destination}, dep={departure_date}, ret={return_date}, "
        f"cabin_class={cabin_class} (code={cabin_class_code}), direct_flight={direct_flight}, "
        f"preferred_airline={preferred_airline}"
    )

    # Set default dates if not provided
    if not departure_date:
        departure_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

    # TEST CASE: Return empty results for airports with no flights
    # XXX: generic no-results test
    # IFU: Ifuru (small Maldives domestic airport, no international flights)
    _NO_RESULTS_AIRPORTS = {"XXX", "IFU"}
    if (
        origin.upper() in _NO_RESULTS_AIRPORTS
        or destination.upper() in _NO_RESULTS_AIRPORTS
    ):
        return {
            "AirSearchResponse": {
                "session_id": session_id,
                "supplier": "MockAir",
                "AirSearchResult": {
                    "FareItineraries": [],  # Empty results
                },
            }
        }

    # TODO(#616): Remove _UNSUPPORTED_TEST_AIRPORTS once nearby-airport suggestions are
    # verified working end-to-end in staging. BUF (Buffalo) simulates INVALID_AIRPORT.
    _UNSUPPORTED_TEST_AIRPORTS = {"BUF"}
    if (
        origin.upper() in _UNSUPPORTED_TEST_AIRPORTS
        or destination.upper() in _UNSUPPORTED_TEST_AIRPORTS
    ):
        problem = (
            origin.upper()
            if origin.upper() in _UNSUPPORTED_TEST_AIRPORTS
            else destination.upper()
        )
        return {
            "Errors": {
                "ErrorCode": "INVALID_AIRPORT",
                "ErrorMessage": f"Airport {problem} is not supported by our search system.",
            }
        }

    # MULTI-AIRPORT SEARCH: Get all airports if city_wise_search flags are True
    origin_airports = (
        _get_city_airports(origin) if city_wise_search_origin else [origin]
    )
    destination_airports = (
        _get_city_airports(destination)
        if city_wise_search_destination
        else [destination]
    )

    logger.info(
        f"Multi-airport search: {len(origin_airports)} origin x {len(destination_airports)} destination "
        f"= {len(origin_airports) * len(destination_airports)} routes "
        f"(city_wise_origin={city_wise_search_origin}, city_wise_dest={city_wise_search_destination})"
    )

    # Generate flights for all airport combinations
    all_fare_itineraries = []
    journey_type = "roundtrip" if return_date else "oneway"
    route_fixtures = _load_route_fixtures()

    for orig_airport in origin_airports:
        for dest_airport in destination_airports:
            route_key = _get_route_key(orig_airport, dest_airport, journey_type)

            if route_key in route_fixtures:
                # Use route-specific fixture data
                route_data = route_fixtures[route_key]
                flights = route_data.get("flights", [])

                # Filter direct flights if requested
                if direct_flight == 1:
                    flights = [f for f in flights if f.get("stops", 0) == 0]

                # Filter by preferred airline if requested
                if preferred_airline:
                    flights = [
                        f
                        for f in flights
                        if f.get("airline_code", "").upper()
                        == preferred_airline.upper()
                    ]

                # Build fare itineraries from fixture data
                for _i, flight in enumerate(flights):
                    fare_code = f"MOCK_FARE_{flight['airline_code']}_{orig_airport}_{dest_airport}_{session_id[-6:]}"
                    fare_itinerary = _build_fare_itinerary_from_fixture(
                        flight=flight,
                        origin=orig_airport,
                        destination=dest_airport,
                        departure_date=departure_date,
                        fare_code=fare_code,
                        return_date=return_date,
                        cabin_class_code=cabin_class_code,
                        price_multiplier=price_multiplier,
                        currency=currency,
                    )
                    all_fare_itineraries.append(fare_itinerary)

                logger.info(
                    f"Using route fixture: {route_key} ({len(flights)} flights)"
                )
            else:
                # Fallback to generic mock data for routes not in fixtures
                logger.info(
                    f"No fixture for route {route_key}, using generic mock data"
                )

                # Generate 3 mock flights for this route
                is_round_trip = return_date is not None
                mock_flights = [
                    {
                        "airline_code": "BA",
                        "airline_name": "British Airways",
                        "flight_number": "BA1234",
                        "stops": 1,
                        "price_eur": 250.00 * (1.8 if is_round_trip else 1.0),
                        "refundable": True,
                    },
                    {
                        "airline_code": "FR",
                        "airline_name": "Ryanair",
                        "flight_number": "FR5678",
                        "stops": 2,
                        "price_eur": 180.00 * (1.8 if is_round_trip else 1.0),
                        "refundable": False,
                    },
                    {
                        "airline_code": "KL",
                        "airline_name": "KLM Royal Dutch Airlines",
                        "flight_number": "KL9012",
                        "stops": 0,
                        "price_eur": 320.00 * (1.8 if is_round_trip else 1.0),
                        "refundable": True,
                    },
                ]

                # Filter direct flights if requested
                if direct_flight == 1:
                    mock_flights = [f for f in mock_flights if f["stops"] == 0]

                # Filter by preferred airline if requested
                if preferred_airline:
                    mock_flights = [
                        f
                        for f in mock_flights
                        if f["airline_code"].upper() == preferred_airline.upper()
                    ]

                date_mult = _date_price_multiplier(departure_date)
                for flight in mock_flights:
                    price = flight["price_eur"] * price_multiplier * date_mult
                    tax = round(price * 0.15, 2)
                    total = round(price + tax, 2)

                    origin_dest_options = _build_origin_destination_options(
                        origin=orig_airport,
                        destination=dest_airport,
                        departure_date=departure_date,
                        return_date=return_date,
                        stops=flight["stops"],
                        airline_code=flight["airline_code"],
                        airline_name=flight["airline_name"],
                        base_flight_number=flight["flight_number"],
                        cabin_class_code=cabin_class_code,
                    )

                    fare_itinerary = {
                        "FareItinerary": _build_generic_fare_itinerary(
                            origin=orig_airport,
                            destination=dest_airport,
                            price=price,
                            tax=tax,
                            total=total,
                            flight=flight,
                            origin_dest_options=origin_dest_options,
                            fare_code=f"MOCK_FARE_{flight['airline_code']}_{orig_airport}_{dest_airport}_{session_id[-6:]}",
                            currency=currency,
                        )
                    }
                    all_fare_itineraries.append(fare_itinerary)

    # Return combined results from all airport combinations
    logger.info(
        f"Returning {len(all_fare_itineraries)} flights from multi-airport search"
    )

    return {
        "AirSearchResponse": {
            "session_id": session_id,
            "supplier": "MockAir",
            "AirSearchResult": {
                "FareItineraries": all_fare_itineraries,
            },
        }
    }


def get_mock_booking_response(
    session_id: str,
    fare_source_code: str,
    success: bool = True,
) -> dict:
    """Generate a mock booking response.

    Args:
        session_id: Session ID from search response
        fare_source_code: Fare source code from selected flight
        success: Whether booking should succeed

    Returns:
        Mock FlightLogicBookingResponse
    """
    if success:
        unique_id = f"MOCK_BOOKING_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        return {
            "BookFlightResponse": {
                "BookFlightResult": {
                    "Status": "CONFIRMED",
                    "Success": True,
                    "Target": "Test",
                    "UniqueID": unique_id,
                    "TktTimeLimit": (
                        datetime.utcnow() + timedelta(hours=24)
                    ).isoformat(),
                    "Errors": None,
                }
            }
        }
    return {
        "Errors": {
            "ErrorCode": "INVALID_SESSION",
            "ErrorMessage": f"Invalid session_id or fare_source_code. Session: {session_id}, Fare: {fare_source_code}",
        }
    }


def validate_booking_request(
    session_id: str, fare_source_code: str
) -> tuple[bool, str]:
    """Validate booking request against stored sessions.

    Args:
        session_id: Session ID to validate
        fare_source_code: Fare source code to validate

    Returns:
        Tuple of (is_valid, error_message)

    MVP Mode: Accepts any session_id and fare_source_code that start with "MOCK_"
    to support n8n workflows that generate mock data without calling /availability.
    """
    # MVP: Accept any MOCK_ prefixed session_id and fare_source_code
    # This allows n8n workflows to book flights using mock data generated in-workflow
    # without needing to call the /availability endpoint first
    if session_id.startswith("MOCK_SESSION_") and fare_source_code.startswith(
        "MOCK_FARE_"
    ):
        return True, ""

    # Standard validation for real API sessions
    if session_id not in MOCK_SESSIONS:
        return False, f"Invalid session_id: {session_id} not found"

    session = MOCK_SESSIONS[session_id]
    if fare_source_code not in session["fare_codes"]:
        return (
            False,
            f"Invalid fare_source_code: {fare_source_code} not in session {session_id}",
        )

    return True, ""


# Store mock bookings for trip_details endpoint
MOCK_BOOKINGS = {}


def get_mock_ticket_order_response(unique_id: str, success: bool = True) -> dict:
    """Generate mock ticket order response.

    Args:
        unique_id: FlightLogic UniqueID (booking reference)
        success: Whether ticket order should succeed

    Returns:
        Mock TicketResponse matching FlightLogic API format
    """
    if success:
        return {
            "AirOrderTicketRS": {
                "TicketOrderResult": {
                    "Success": "true",
                    "UniqueID": unique_id,
                    "Target": "Test",
                    "Errors": None,
                }
            }
        }

    return {
        "Errors": {
            "ErrorCode": "TICKET_ERROR",
            "ErrorMessage": f"Failed to issue tickets for booking {unique_id}",
        }
    }


def get_mock_trip_details_response(unique_id: str) -> dict:
    """Generate mock trip details response.

    Args:
        unique_id: FlightLogic UniqueID (booking reference)

    Returns:
        Mock TripDetailsResponse matching FlightLogic API format
    """
    # For mock testing, generate realistic trip details
    # In production, this would be retrieved from actual booking data

    return {
        "TripDetailsResult": {
            "UniqueID": unique_id,
            "BookingReference": unique_id,
            "Status": "CONFIRMED",
            "BookingDate": datetime.utcnow().isoformat(),
            "TicketTimeLimit": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "JourneyType": "OneWay",
            "FareType": "Public",
            "IsRefundable": True,
            "CrossBorderIndicator": False,  # Same country flights
            "IsCommissionable": False,
            "IsMOFare": False,
            "Environment": "Test",
            "Target": "Test",
            "Origin": {
                "AirportCode": "AMS",
                "AirportName": "Amsterdam Schiphol Airport",
                "CityName": "Amsterdam",
                "CountryCode": "NL",
                "CountryName": "Netherlands",
            },
            "Destination": {
                "AirportCode": "FAO",
                "AirportName": "Faro Airport",
                "CityName": "Faro",
                "CountryCode": "PT",
                "CountryName": "Portugal",
            },
            "Passengers": [
                {
                    "Title": "Mr",
                    "FirstName": "John",
                    "LastName": "Doe",
                    "PassengerType": "ADT",
                    "DateOfBirth": "1990-01-01",
                    "Nationality": "NL",
                    "Email": "john.doe@example.com",
                    "Phone": "+31612345678",
                }
            ],
            "FlightSegments": [
                {
                    "DepartureAirportLocationCode": "AMS",
                    "ArrivalAirportLocationCode": "FAO",
                    "DepartureDateTime": (
                        datetime.utcnow() + timedelta(days=7)
                    ).strftime("%Y-%m-%dT09:30:00"),
                    "ArrivalDateTime": (datetime.utcnow() + timedelta(days=7)).strftime(
                        "%Y-%m-%dT12:45:00"
                    ),
                    "FlightNumber": "BA1234",
                    "MarketingAirlineCode": "BA",
                    "OperatingAirlineCode": "BA",
                    "OperatingFlightNumber": "BA1234",
                    "CabinClass": "Economy",
                    "BookingClass": "Y",
                    "Status": "CONFIRMED",
                }
            ],
            "FareDetails": {
                "BaseFare": {
                    "Amount": "250.00",
                    "CurrencyCode": "EUR",
                    "DecimalPlaces": "2",
                },
                "Tax": {
                    "Amount": "45.50",
                    "CurrencyCode": "EUR",
                    "DecimalPlaces": "2",
                },
                "TotalFare": {
                    "Amount": "295.50",
                    "CurrencyCode": "EUR",
                    "DecimalPlaces": "2",
                },
                "FareBreakdown": [
                    {
                        "PassengerTypeQuantity": {"Code": "ADT", "Quantity": 1},
                        "PassengerFare": {
                            "BaseFare": {
                                "Amount": "250.00",
                                "CurrencyCode": "EUR",
                                "DecimalPlaces": "2",
                            },
                            "TotalFare": {
                                "Amount": "295.50",
                                "CurrencyCode": "EUR",
                                "DecimalPlaces": "2",
                            },
                            "Taxes": [
                                {
                                    "TaxCode": "VAT",
                                    "Amount": "45.50",
                                    "CurrencyCode": "EUR",
                                    "DecimalPlaces": "2",
                                }
                            ],
                        },
                    }
                ],
            },
        }
    }


def get_mock_airline_list_response() -> list[dict]:
    """Generate mock airline list response for FlightLogic airline_list API.

    Returns:
        List of airlines with AirLineCode, AirLineName, AirLineLogo.
        Includes airlines used in mock search (BA, FR, KL, EK) for logo enrichment.
    """
    return [
        {
            "AirLineCode": "BA",
            "AirLineName": "British Airways",
            "AirLineLogo": "https://travelnext.works/api/airlines/BA.gif",
        },
        {
            "AirLineCode": "FR",
            "AirLineName": "Ryanair",
            "AirLineLogo": "https://travelnext.works/api/airlines/FR.gif",
        },
        {
            "AirLineCode": "KL",
            "AirLineName": "KLM Royal Dutch Airlines",
            "AirLineLogo": "https://travelnext.works/api/airlines/KL.gif",
        },
        {
            "AirLineCode": "EK",
            "AirLineName": "Emirates",
            "AirLineLogo": "https://travelnext.works/api/airlines/EK.gif",
        },
        {
            "AirLineCode": "AA",
            "AirLineName": "American Airlines",
            "AirLineLogo": "https://travelnext.works/api/airlines/AA.gif",
        },
        {
            "AirLineCode": "DL",
            "AirLineName": "Delta Air Lines",
            "AirLineLogo": "https://travelnext.works/api/airlines/DL.gif",
        },
        {
            "AirLineCode": "B6",
            "AirLineName": "JetBlue Airways",
            "AirLineLogo": "https://travelnext.works/api/airlines/B6.gif",
        },
        {
            "AirLineCode": "U2",
            "AirLineName": "easyJet",
            "AirLineLogo": "https://travelnext.works/api/airlines/U2.gif",
        },
    ]


def get_mock_accommodation_response(
    destination: str = "Barcelona",
    check_in_date: str | None = None,
    check_out_date: str | None = None,
    guests: dict | None = None,
) -> dict:
    """Generate a mock accommodation search response.

    Args:
        destination: Destination city name
        check_in_date: Check-in date (YYYY-MM-DD)
        check_out_date: Check-out date (YYYY-MM-DD)
        guests: Guest details {adults, children}

    Returns:
        Mock AccommodationSearchResponse matching the API structure

    Special Test Cases:
        - destination="NOHOTELS" -> Returns 0 hotels (for testing "no results" scenario)
    """
    # Set default dates if not provided
    if not check_in_date:
        check_in_date = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")
    if not check_out_date:
        check_out_date = (datetime.utcnow() + timedelta(days=14)).strftime("%Y-%m-%d")

    # Parse dates to calculate nights
    check_in = date.fromisoformat(check_in_date)
    check_out = date.fromisoformat(check_out_date)
    nights = (check_out - check_in).days

    if not guests:
        guests = {"adults": 2, "children": 0}

    # TEST CASE: Return empty results for NOHOTELS
    if destination == "NOHOTELS":
        return {
            "AccommodationSearchResponse": {
                "destination": destination,
                "check_in_date": check_in_date,
                "check_out_date": check_out_date,
                "AccommodationResult": {
                    "total_hotels_found": 0,
                    "hotels": [],
                },
                "Success": True,
            }
        }

    # Generate 3 mock hotels with different price ranges
    hotels = [
        {
            "hotel_id": "FL_HOTEL_DEST_001",
            "name": "Luxury Hotel & Spa",
            "destination_city": destination,
            "destination_area": "City Center",
            "star_rating": 5.0,
            "review_score": 4.7,
            "total_reviews": 1240,
            "room_type": "Deluxe Double Room",
            "occupancy": f"{guests.get('adults', 2)} adults",
            "price_per_night": {
                "Amount": "215.00",
                "CurrencyCode": "EUR",
                "DecimalPlaces": "2",
            },
            "total_price": {
                "Amount": f"{215.00 * nights:.2f}",
                "CurrencyCode": "EUR",
                "DecimalPlaces": "2",
            },
            "taxes_fees": {
                "Amount": f"{215.00 * nights * 0.12:.2f}",
                "CurrencyCode": "EUR",
                "DecimalPlaces": "2",
            },
            "final_price": {
                "Amount": f"{215.00 * nights * 1.12:.2f}",
                "CurrencyCode": "EUR",
                "DecimalPlaces": "2",
            },
            "amenities": [
                "WiFi",
                "Air Conditioning",
                "Spa",
                "Fitness Center",
                "Restaurant",
                "Bar",
            ],
            "cancellation_policy": "Free cancellation until 24 hours before arrival",
            "breakfastIncluded": False,
            "rate_code": f"MOCK_HOTEL_{destination.upper()}_001_LUXURY",
            "availability": "Available",
        },
        {
            "hotel_id": "FL_HOTEL_DEST_002",
            "name": "Standard Hotel",
            "destination_city": destination,
            "destination_area": "Downtown",
            "star_rating": 4.0,
            "review_score": 4.5,
            "total_reviews": 890,
            "room_type": "Standard Double Room",
            "occupancy": f"{guests.get('adults', 2)} adults",
            "price_per_night": {
                "Amount": "125.00",
                "CurrencyCode": "EUR",
                "DecimalPlaces": "2",
            },
            "total_price": {
                "Amount": f"{125.00 * nights:.2f}",
                "CurrencyCode": "EUR",
                "DecimalPlaces": "2",
            },
            "taxes_fees": {
                "Amount": f"{125.00 * nights * 0.12:.2f}",
                "CurrencyCode": "EUR",
                "DecimalPlaces": "2",
            },
            "final_price": {
                "Amount": f"{125.00 * nights * 1.12:.2f}",
                "CurrencyCode": "EUR",
                "DecimalPlaces": "2",
            },
            "amenities": ["WiFi", "Air Conditioning", "Fitness Center", "Restaurant"],
            "cancellation_policy": "Free cancellation until 3 days before arrival",
            "breakfastIncluded": True,
            "rate_code": f"MOCK_HOTEL_{destination.upper()}_002_STANDARD",
            "availability": "Available",
        },
        {
            "hotel_id": "FL_HOTEL_DEST_003",
            "name": "Budget Hostel",
            "destination_city": destination,
            "destination_area": "Residential Area",
            "star_rating": 2.0,
            "review_score": 4.2,
            "total_reviews": 450,
            "room_type": "Shared Dormitory",
            "occupancy": f"{guests.get('adults', 2)} guests in shared room",
            "price_per_night": {
                "Amount": "45.00",
                "CurrencyCode": "EUR",
                "DecimalPlaces": "2",
            },
            "total_price": {
                "Amount": f"{45.00 * nights:.2f}",
                "CurrencyCode": "EUR",
                "DecimalPlaces": "2",
            },
            "taxes_fees": {
                "Amount": f"{45.00 * nights * 0.12:.2f}",
                "CurrencyCode": "EUR",
                "DecimalPlaces": "2",
            },
            "final_price": {
                "Amount": f"{45.00 * nights * 1.12:.2f}",
                "CurrencyCode": "EUR",
                "DecimalPlaces": "2",
            },
            "amenities": ["WiFi", "Common Kitchen", "Lounge", "Free Walking Tour"],
            "cancellation_policy": "Non-refundable",
            "breakfastIncluded": False,
            "rate_code": f"MOCK_HOTEL_{destination.upper()}_003_BUDGET",
            "availability": "Limited Availability (2 rooms left)",
        },
    ]

    return {
        "AccommodationSearchResponse": {
            "destination": destination,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "nights": nights,
            "guests": guests,
            "AccommodationResult": {
                "total_hotels_found": len(hotels),
                "currency": "EUR",
                "hotels": hotels,
            },
            "Success": True,
            "Errors": None,
        }
    }


# =============================================================================
# Hotel API v6 Mock Data
# =============================================================================

MOCK_HOTEL_SESSIONS = {}


def generate_mock_hotel_session_id() -> str:
    """Generate a mock hotel session ID (base64-like format)."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"TU9DS19IT1RFTF9TRVNTSU9OX3t0aW1lc3RhbXB9X{timestamp}"


def get_mock_hotel_search_response(
    city_name: str = "Bangalore",
    checkin: str | None = None,
    checkout: str | None = None,
    currency: str = "EUR",
) -> dict:
    """Generate mock hotel search response.

    Uses city-specific fixtures when available for realistic, deterministic results.
    Falls back to generic Bangalore hotels for cities not in fixtures.

    Args:
        city_name: City to search (defaults to Bangalore for real data)
        checkin: Check-in date (YYYY-MM-DD)
        checkout: Check-out date (YYYY-MM-DD)
        currency: Currency code (default EUR)

    Returns:
        Mock hotel search response matching FlightLogic Hotel API v6 structure

    Special Test Cases:
        - city_name="NOHOTELS" -> Returns 0 hotels (for testing "no results" scenario)
    """
    # Generate session ID
    session_id = generate_mock_hotel_session_id()

    # Store session for validation
    MOCK_HOTEL_SESSIONS[session_id] = {
        "created_at": datetime.utcnow().isoformat(),
        "city_name": city_name,
        "checkin": checkin,
        "checkout": checkout,
    }

    # TEST CASE: Return empty results for NOHOTELS
    if city_name == "NOHOTELS":
        return {
            "status": {
                "sessionId": session_id,
                "moreResults": False,
                "nextToken": "",
                "totalResults": 0,
            },
            "itineraries": [],
        }

    # Try to load city-specific fixtures
    city_key = _get_city_key(city_name)
    city_fixtures = _load_hotel_city_fixtures()

    if city_key in city_fixtures:
        # Use city-specific fixture data
        city_data = city_fixtures[city_key]
        fixture_hotels = city_data.get("hotels", [])

        # Build hotels from fixture data
        hotels = [
            _build_hotel_from_fixture(
                hotel=hotel,
                session_id=session_id,
                index=i + 1,
                currency=currency,
            )
            for i, hotel in enumerate(fixture_hotels)
        ]

        logger.info(f"Using hotel city fixture: {city_key} ({len(hotels)} hotels)")

        return {
            "status": {
                "sessionId": session_id,
                "moreResults": False,
                "nextToken": "",
                "totalResults": len(hotels),
            },
            "itineraries": hotels,
        }

    # Fallback to generic Bangalore hotels for cities not in fixtures
    logger.info(f"No fixture for city '{city_name}', using generic Bangalore mock data")

    hotels = [
        {
            "hotelId": "1094726",
            "twxHotelId": "1775029",
            "productId": "trx109",
            "tokenId": f"MOCK_TOKEN_{session_id[-8:]}_001",
            "hotelName": "Athithi International",
            "city": city_name,
            "locality": "City Center",
            "distanceValue": 14.47,
            "distanceUnit": "KM",
            "country": "",
            "countryCode": "",
            "address": "No.41, 2nd Cross, Satish Reddy Electronic City",
            "latitude": "12.85160270000000000000",
            "longitude": "77.64882460000000000000",
            "hotelRating": 3,
            "total": "1729.60",
            "perNightArray": [
                {"nightIndex": 1, "currency": currency, "price": "1729.60"}
            ],
            "currency": currency,
            "fareType": "Refundable",
            "propertyType": "Hotel",
            "postalCode": "560100",
            "phone": "+919743878899",
            "email": "athithiinternational@gmail.com",
            "thumbNailUrl": "https://photos.hotelbeds.com/giata/original/10/1094726/1094726a_hb_ro_001_20250922_100938.jpg",
            "facilities": [
                "hotel",
                "Wi-fi",
                "Air conditioning",
                "24-hour reception",
                "Breakfast buffet",
                "Car park",
            ],
            "tripAdvisorRating": 0,
            "tripAdvisorReview": 0,
            "special": "",
        },
        {
            "hotelId": "792242",
            "twxHotelId": "1754461",
            "productId": "trx109",
            "tokenId": f"MOCK_TOKEN_{session_id[-8:]}_002",
            "hotelName": "Capital O 11148 Amethyst Business Hotel",
            "city": city_name,
            "locality": "Downtown",
            "distanceValue": 5.27,
            "distanceUnit": "KM",
            "country": "",
            "countryCode": "",
            "address": "Plot No 233 9Th Main 5Th Block 40Th Cross Jayanaga",
            "latitude": "12.92066340000000000000",
            "longitude": "77.58321819999999000000",
            "hotelRating": 3,
            "total": "1960.07",
            "perNightArray": [
                {"nightIndex": 1, "currency": currency, "price": "1960.07"}
            ],
            "currency": currency,
            "fareType": "Refundable",
            "propertyType": "Hotel",
            "postalCode": "560041",
            "phone": "+0911244588630",
            "email": "customerservice.ota@oyorooms.com",
            "thumbNailUrl": "https://photos.hotelbeds.com/giata/original/79/792242/792242a_hb_a_001.jpg",
            "facilities": [
                "hotel",
                "Wi-fi",
                "Restaurant",
                "Room service",
                "Laundry service",
            ],
            "tripAdvisorRating": 0,
            "tripAdvisorReview": 0,
            "special": "",
        },
        {
            "hotelId": "754926",
            "twxHotelId": "1774355",
            "productId": "trx109",
            "tokenId": f"MOCK_TOKEN_{session_id[-8:]}_003",
            "hotelName": "Lusia Inn",
            "city": city_name,
            "locality": "Suburbs",
            "distanceValue": 0.89,
            "distanceUnit": "KM",
            "country": "",
            "countryCode": "",
            "address": "45 45 1 Near Town Hall N R Road Sjp Road",
            "latitude": "12.96331300000000000000",
            "longitude": "77.58194000000000000000",
            "hotelRating": 0,
            "total": "3010.57",
            "perNightArray": [
                {"nightIndex": 1, "currency": currency, "price": "3010.57"}
            ],
            "currency": currency,
            "fareType": "Refundable",
            "propertyType": "Hotel",
            "postalCode": "560002",
            "phone": "+918217090276",
            "email": "",
            "thumbNailUrl": "https://photos.hotelbeds.com/giata/original/75/754926/754926a_hb_a_003.jpg",
            "facilities": [
                "hotel",
                "Wi-fi",
                "Airport Shuttle",
                "24-hour reception",
                "Breakfast buffet",
            ],
            "tripAdvisorRating": 0,
            "tripAdvisorReview": 0,
            "special": "",
        },
    ]

    return {
        "status": {
            "sessionId": session_id,
            "moreResults": False,
            "nextToken": "",
            "totalResults": len(hotels),
        },
        "itineraries": hotels,
    }


def get_mock_room_rates_response(session_id: str, token_id: str) -> dict:
    """Generate mock room rates response.

    Args:
        session_id: Hotel search session ID
        token_id: Hotel token from search results

    Returns:
        Mock room rates response
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    return {
        "hotelId": "1094726",
        "sessionId": session_id,
        "tokenId": token_id,
        "rooms": [
            {
                "roomType": "Deluxe Double Room",
                "rateKey": f"RATE_KEY_{timestamp}_001",
                "pricePerNight": 225.00,
                "totalPrice": 450.00,
                "currency": "USD",
                "mealPlan": "Breakfast included",
                "cancellationPolicy": "Free cancellation until 24 hours before check-in",
                "maxOccupancy": {"adults": 2, "children": 1},
                "roomsAvailable": 5,
            },
            {
                "roomType": "Standard Twin Room",
                "rateKey": f"RATE_KEY_{timestamp}_002",
                "pricePerNight": 180.00,
                "totalPrice": 360.00,
                "currency": "USD",
                "mealPlan": "Room only",
                "cancellationPolicy": "Non-refundable",
                "maxOccupancy": {"adults": 2, "children": 0},
                "roomsAvailable": 10,
            },
            {
                "roomType": "Suite with City View",
                "rateKey": f"RATE_KEY_{timestamp}_003",
                "pricePerNight": 350.00,
                "totalPrice": 700.00,
                "currency": "USD",
                "mealPlan": "Full board",
                "cancellationPolicy": "Free cancellation until 48 hours before check-in",
                "maxOccupancy": {"adults": 3, "children": 2},
                "roomsAvailable": 2,
            },
        ],
    }


def get_mock_rate_rules_response(
    session_id: str, token_id: str, rate_basis_id: str
) -> dict:
    """Generate mock rate rules response.

    Based on real FlightLogic Hotel API v6 response structure.
    Used to validate rates before booking.

    Args:
        session_id: Hotel search session ID
        token_id: Hotel token from search results
        rate_basis_id: Rate basis ID from room rates

    Returns:
        Mock rate rules response with validated rate information
    """
    return {
        "sessionId": session_id,
        "hotelId": 316798,
        "tokenId": token_id,
        "roomRates": {
            "perBookingRates": [
                {
                    "productId": "trx109",
                    "roomType": "Standard Double Room - Shared",
                    "description": "1 Standard Double Room - Shared",
                    "roomCode": "DBL.FH",
                    "fareType": "Non-Refundable",
                    "rateBasisId": rate_basis_id,
                    "currency": "USD",
                    "netPrice": 476.74,
                    "taxes": [
                        [
                            {
                                "type": "TAXESANDFEES",
                                "amount": "72.23",
                                "currency": "USD",
                                "included": True,
                            }
                        ]
                    ],
                    "boardType": "ROOM ONLY",
                    "maxOccupancyPerRoom": "2",
                    "inventoryType": "prepaid",
                    "cancellationPolicy": "If cancelled from Thu 20 Nov 2025 05:29:00 Amount USD 476.74 will charge!",
                    "roomImages": [],
                    "facilities": ["Number of bedrooms : 1"],
                    "extrabeds": "0",
                    "remark": ".  Check-in hour 14:00-.Car park NO.Check-out hour -11:00.Minimum check-in age 18.",
                }
            ]
        },
    }


def get_mock_revalidate_response(
    session_id: str, fare_source_code: str, success: bool = True
) -> dict:
    """Generate mock revalidate response.

    Revalidate confirms that a fare is still available before booking.
    Returns the same fare itinerary with validation status.

    Args:
        session_id: Session ID from search response
        fare_source_code: Fare source code from selected flight
        success: Whether revalidation should succeed

    Returns:
        Mock revalidate response matching FlightLogic API format
    """
    if not success:
        return {
            "Errors": {
                "ErrorCode": "FARE_EXPIRED",
                "ErrorMessage": f"Fare {fare_source_code} is no longer available. Please search again.",
            }
        }

    # Build a valid revalidate response
    # The response structure includes the fare itinerary details
    return {
        "AirRevalidateResponse": {
            "AirRevalidateResult": {
                "IsValid": True,
                "FareItineraries": {
                    "FareItinerary": {
                        "DirectionInd": "OneWay",
                        "AirItineraryFareInfo": {
                            "DivideInPartyIndicator": False,
                            "FareSourceCode": fare_source_code,
                            "FareType": "Public",
                            "IsRefundable": True,
                            "ItinTotalFares": {
                                "BaseFare": {
                                    "Amount": "250.00",
                                    "CurrencyCode": "EUR",
                                    "DecimalPlaces": "2",
                                },
                                "EquivFare": {
                                    "Amount": "250.00",
                                    "CurrencyCode": "EUR",
                                    "DecimalPlaces": "2",
                                },
                                "ServiceTax": {
                                    "Amount": "0.00",
                                    "CurrencyCode": "EUR",
                                    "DecimalPlaces": "2",
                                },
                                "TotalTax": {
                                    "Amount": "45.50",
                                    "CurrencyCode": "EUR",
                                    "DecimalPlaces": "2",
                                },
                                "TotalFare": {
                                    "Amount": "295.50",
                                    "CurrencyCode": "EUR",
                                    "DecimalPlaces": "2",
                                },
                            },
                            "FareBreakdown": [
                                {
                                    "PassengerTypeQuantity": {
                                        "Code": "ADT",
                                        "Quantity": 1,
                                    },
                                    "PassengerFare": {
                                        "BaseFare": {
                                            "Amount": "250.00",
                                            "CurrencyCode": "EUR",
                                            "DecimalPlaces": "2",
                                        },
                                        "EquivFare": {
                                            "Amount": "250.00",
                                            "CurrencyCode": "EUR",
                                            "DecimalPlaces": "2",
                                        },
                                        "ServiceTax": {
                                            "Amount": "0.00",
                                            "CurrencyCode": "EUR",
                                            "DecimalPlaces": "2",
                                        },
                                        "Surcharges": {
                                            "Amount": "0.00",
                                            "CurrencyCode": "EUR",
                                            "DecimalPlaces": "2",
                                        },
                                        "Taxes": [
                                            {
                                                "TaxCode": "VAT",
                                                "Amount": "45.50",
                                                "CurrencyCode": "EUR",
                                                "DecimalPlaces": "2",
                                            }
                                        ],
                                        "TotalFare": {
                                            "Amount": "295.50",
                                            "CurrencyCode": "EUR",
                                            "DecimalPlaces": "2",
                                        },
                                    },
                                    "Baggage": ["23KG"],
                                    "CabinBaggage": ["7KG"],
                                }
                            ],
                        },
                        "OriginDestinationOptions": [
                            {
                                "OriginDestinationOption": [
                                    {
                                        "FlightSegment": {
                                            "DepartureAirportLocationCode": "AMS",
                                            "ArrivalAirportLocationCode": "LHR",
                                            "DepartureDateTime": "2026-02-15T09:30:00",
                                            "ArrivalDateTime": "2026-02-15T10:45:00",
                                            "FlightNumber": "BA1234",
                                            "MarketingAirlineCode": "BA",
                                            "MarketingAirlineName": "British Airways",
                                            "OperatingAirline": {
                                                "Code": "BA",
                                                "Name": "British Airways",
                                                "Equipment": "320",
                                                "FlightNumber": "BA1234",
                                            },
                                            "JourneyDuration": 75,
                                            "CabinClassCode": "Y",
                                            "Eticket": True,
                                        },
                                        "StopQuantity": 0,
                                        "SeatsRemaining": {
                                            "Number": 9,
                                            "BelowMinimum": False,
                                        },
                                    }
                                ],
                                "TotalStops": 0,
                            }
                        ],
                        "ValidatingAirlineCode": "BA",
                        "IsPassportMandatory": "true",
                        # These fields must be inside FareItinerary for the adapter to find them
                        "RequiredFieldsToBook": [
                            "title",
                            "firstName",
                            "lastName",
                            "dob",
                            "nationality",
                            "passportNo",
                            "passportExpiryDate",
                            "passportIssueCountry",
                        ],
                        "IsPassportFullDetailsMandatory": True,
                    }
                },
                "SequenceNumber": "1",
            }
        }
    }


def get_mock_hotel_booking_response(
    session_id: str, rate_key: str, success: bool = True
) -> dict:
    """Generate mock hotel booking response.

    Args:
        session_id: Hotel search session ID
        rate_key: Rate key from room rates
        success: Whether booking should succeed

    Returns:
        Mock hotel booking response
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    if success:
        return {
            "status": "Success",
            "supplierConfirmationNum": f"FL_HTL_{timestamp}",
            "referenceNum": f"VOYA_HTL_{timestamp}",
            "bookingDetails": {
                "hotelName": "Athithi International",
                "checkIn": "2025-11-24",
                "checkOut": "2025-11-25",
                "roomType": "Deluxe Double Room",
                "totalPrice": 450.00,
                "currency": "USD",
                "guestName": "John Doe",
                "confirmationEmail": "Sent to guest email",
            },
        }
    return {
        "status": "Failed",
        "supplierConfirmationNum": None,
        "referenceNum": None,
        "errors": {"errorMessage": "In-Sufficient Balance."},
    }


def get_mock_airport_list_response() -> list[dict]:
    """Generate mock airport list response for FlightLogic airport_list API.

    Returns a representative list of airports supported by FlightLogic.
    BUF and IAG are intentionally excluded to test nearby-airport filtering:
    when a user searches BUF → unsupported → haversine finds IAG (25km) and
    ROC (100km) → FL filter removes IAG (not in list) → only ROC is suggested.

    In production this endpoint returns thousands of airports.
    """
    return [
        # UK / Europe
        {
            "AirportCode": "LHR",
            "AirportName": "London Heathrow Airport",
            "City": "London",
            "Country": "United Kingdom",
        },
        {
            "AirportCode": "LGW",
            "AirportName": "London Gatwick Airport",
            "City": "London",
            "Country": "United Kingdom",
        },
        {
            "AirportCode": "MAN",
            "AirportName": "Manchester Airport",
            "City": "Manchester",
            "Country": "United Kingdom",
        },
        {
            "AirportCode": "CDG",
            "AirportName": "Charles de Gaulle Airport",
            "City": "Paris",
            "Country": "France",
        },
        {
            "AirportCode": "AMS",
            "AirportName": "Amsterdam Schiphol Airport",
            "City": "Amsterdam",
            "Country": "Netherlands",
        },
        {
            "AirportCode": "FRA",
            "AirportName": "Frankfurt Airport",
            "City": "Frankfurt",
            "Country": "Germany",
        },
        {
            "AirportCode": "MAD",
            "AirportName": "Adolfo Suarez Madrid-Barajas Airport",
            "City": "Madrid",
            "Country": "Spain",
        },
        {
            "AirportCode": "BCN",
            "AirportName": "Barcelona El Prat Airport",
            "City": "Barcelona",
            "Country": "Spain",
        },
        {
            "AirportCode": "FCO",
            "AirportName": "Leonardo da Vinci International Airport",
            "City": "Rome",
            "Country": "Italy",
        },
        {
            "AirportCode": "DXB",
            "AirportName": "Dubai International Airport",
            "City": "Dubai",
            "Country": "UAE",
        },
        # US East Coast / Northeast (near Buffalo — ROC included, IAG and BUF excluded)
        {
            "AirportCode": "JFK",
            "AirportName": "John F. Kennedy International Airport",
            "City": "New York",
            "Country": "United States",
        },
        {
            "AirportCode": "EWR",
            "AirportName": "Newark Liberty International Airport",
            "City": "Newark",
            "Country": "United States",
        },
        {
            "AirportCode": "LGA",
            "AirportName": "LaGuardia Airport",
            "City": "New York",
            "Country": "United States",
        },
        {
            "AirportCode": "ROC",
            "AirportName": "Greater Rochester International Airport",
            "City": "Rochester",
            "Country": "United States",
        },
        {
            "AirportCode": "YYZ",
            "AirportName": "Toronto Pearson International Airport",
            "City": "Toronto",
            "Country": "Canada",
        },
        {
            "AirportCode": "PIT",
            "AirportName": "Pittsburgh International Airport",
            "City": "Pittsburgh",
            "Country": "United States",
        },
        {
            "AirportCode": "CLE",
            "AirportName": "Cleveland Hopkins International Airport",
            "City": "Cleveland",
            "Country": "United States",
        },
        {
            "AirportCode": "BOS",
            "AirportName": "Logan International Airport",
            "City": "Boston",
            "Country": "United States",
        },
        {
            "AirportCode": "PHL",
            "AirportName": "Philadelphia International Airport",
            "City": "Philadelphia",
            "Country": "United States",
        },
        {
            "AirportCode": "IAD",
            "AirportName": "Dulles International Airport",
            "City": "Washington",
            "Country": "United States",
        },
        # US Nationwide
        {
            "AirportCode": "ORD",
            "AirportName": "O'Hare International Airport",
            "City": "Chicago",
            "Country": "United States",
        },
        {
            "AirportCode": "ATL",
            "AirportName": "Hartsfield-Jackson Atlanta International Airport",
            "City": "Atlanta",
            "Country": "United States",
        },
        {
            "AirportCode": "LAX",
            "AirportName": "Los Angeles International Airport",
            "City": "Los Angeles",
            "Country": "United States",
        },
        {
            "AirportCode": "SFO",
            "AirportName": "San Francisco International Airport",
            "City": "San Francisco",
            "Country": "United States",
        },
        {
            "AirportCode": "MIA",
            "AirportName": "Miami International Airport",
            "City": "Miami",
            "Country": "United States",
        },
        # Asia-Pacific
        {
            "AirportCode": "SIN",
            "AirportName": "Singapore Changi Airport",
            "City": "Singapore",
            "Country": "Singapore",
        },
        {
            "AirportCode": "HND",
            "AirportName": "Tokyo Haneda Airport",
            "City": "Tokyo",
            "Country": "Japan",
        },
        {
            "AirportCode": "NRT",
            "AirportName": "Narita International Airport",
            "City": "Tokyo",
            "Country": "Japan",
        },
        {
            "AirportCode": "BKK",
            "AirportName": "Suvarnabhumi Airport",
            "City": "Bangkok",
            "Country": "Thailand",
        },
        {
            "AirportCode": "SYD",
            "AirportName": "Sydney Kingsford Smith Airport",
            "City": "Sydney",
            "Country": "Australia",
        },
        # Maldives (MLE supported for international, IFU domestic-only — no flights)
        {
            "AirportCode": "MLE",
            "AirportName": "Velana International Airport",
            "City": "Malé",
            "Country": "Maldives",
        },
        {
            "AirportCode": "IFU",
            "AirportName": "Ifuru Airport",
            "City": "Ifuru",
            "Country": "Maldives",
        },
    ]
