"""FlightLogic API Mock Server.

A lightweight FastAPI server that simulates the FlightLogic API for local development and testing.

Usage:
    python -m tests.mocks.flightlogic.server [--port PORT]

Example:
    python -m tests.mocks.flightlogic.server --port 8002
"""

import argparse
import logging
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tests.mocks.flightlogic.mock_data import (
    get_mock_accommodation_response,
    get_mock_airline_list_response,
    get_mock_booking_response,
    get_mock_hotel_booking_response,
    get_mock_hotel_search_response,
    get_mock_rate_rules_response,
    get_mock_revalidate_response,
    get_mock_room_rates_response,
    get_mock_search_response,
    get_mock_ticket_order_response,
    get_mock_trip_details_response,
    validate_booking_request,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="FlightLogic Mock API",
    description="Mock server for FlightLogic API endpoints",
    version="1.0.0",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging."""
    start_time = datetime.utcnow()

    # Log request
    logger.info(f"→ {request.method} {request.url.path}")
    if request.query_params:
        logger.info(f"  Query: {dict(request.query_params)}")

    # Process request
    response = await call_next(request)

    # Log response
    duration = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"← {response.status_code} ({duration:.3f}s)")

    return response


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "service": "FlightLogic Mock API",
        "version": "1.0.0",
        "endpoints": {
            "flights": {
                "search": "POST /api/aeroVE5/availability",
                "revalidate": "POST /api/aeroVE5/revalidate",
                "airline_list": "POST /api/aeroVE5/airline_list",
                "accommodation": "POST /api/aeroVE5/accommodation",
                "booking": "POST /api/aeroVE5/booking",
                "trip_details": "POST /api/aeroVE5/trip_details",
                "ticket_order": "POST /api/aeroVE5/ticket_order",
            },
            "hotels": {
                "search": "POST /api/hotel-api-v6/hotel_search",
                "room_rates": "POST /api/hotel-api-v6/get_room_rates",
                "rate_rules": "POST /api/hotel-api-v6/get_rate_rules",
                "booking": "POST /api/hotel-api-v6/hotel_booking",
            },
        },
    }


@app.post("/api/aeroVE5/availability")
async def search_flights(request: Request) -> JSONResponse:
    """Mock flight search endpoint.

    Accepts search parameters and returns mock flight results.
    Generates a session_id that can be used for booking.

    Expected request body:
    {
        "origin": "AMS",
        "destination": "LHR",
        "departure_date": "2025-11-15",
        "return_date": null,  // Optional
        "adults": 1,
        "children": 0,
        "infants": 0
    }

    Returns:
    {
        "AirSearchResponse": {
            "session_id": "MOCK_SESSION_...",
            "supplier": "MockAir",
            "AirSearchResult": {
                "FareItineraries": [...]
            }
        }
    }
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Search request: {body}")

        # Extract search parameters from FlightLogic API format
        # The real FlightLogic API uses OriginDestinationInfo array
        origin_dest_info = (
            body.get("OriginDestinationInfo", [{}])[0]
            if body.get("OriginDestinationInfo")
            else {}
        )
        origin = origin_dest_info.get("airportOriginCode") or body.get("origin", "AMS")
        destination = origin_dest_info.get("airportDestinationCode") or body.get(
            "destination", "LHR"
        )
        departure_date = origin_dest_info.get("departureDate") or body.get(
            "departure_date"
        )
        return_date = origin_dest_info.get("returnDate") or body.get("return_date")

        # Extract multi-airport search flags
        city_wise_search_origin = body.get("city_wise_search_origin", False)
        city_wise_search_destination = body.get("city_wise_search_destination", False)

        # Extract flight filter parameters
        cabin_class = body.get(
            "class"
        )  # "Economy", "Business", "First", "PremiumEconomy"
        direct_flight = body.get("directFlight")  # 0 = all, 1 = direct only
        preferred_airline = body.get("airlineCode")  # IATA airline code (e.g., "BA")
        currency = body.get("requiredCurrency", "USD")  # Match adapter.py default

        logger.info(
            f"Flight filters: cabin_class={cabin_class}, direct_flight={direct_flight}, "
            f"preferred_airline={preferred_airline}, currency={currency}"
        )

        # Generate mock response
        mock_response = get_mock_search_response(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            city_wise_search_origin=city_wise_search_origin,
            city_wise_search_destination=city_wise_search_destination,
            cabin_class=cabin_class,
            direct_flight=direct_flight,
            preferred_airline=preferred_airline,
            currency=currency,
        )

        # Error responses (e.g. unsupported airport) have no AirSearchResponse
        if "AirSearchResponse" not in mock_response:
            error_code = mock_response.get("Errors", {}).get("ErrorCode", "UNKNOWN")
            error_msg = mock_response.get("Errors", {}).get(
                "ErrorMessage", "Unknown error"
            )
            logger.info(f"Returning error response: {error_code} — {error_msg}")
            return JSONResponse(content=mock_response, status_code=200)

        session_id = mock_response["AirSearchResponse"]["session_id"]
        fare_itineraries = mock_response["AirSearchResponse"]["AirSearchResult"][
            "FareItineraries"
        ]
        num_flights = len(fare_itineraries)

        logger.info(f"Generated session_id: {session_id}")
        logger.info(f"Returning {num_flights} mock flights")
        logger.info(
            f"FareItineraries type: {type(fare_itineraries)}, length: {len(fare_itineraries)}"
        )
        if fare_itineraries:
            logger.info(f"First flight sample: {list(fare_itineraries[0].keys())}")

        return JSONResponse(content=mock_response, status_code=200)

    except Exception as e:
        logger.error(f"Search error: {e!s}", exc_info=True)
        return JSONResponse(
            content={
                "Errors": {
                    "ErrorCode": "SEARCH_ERROR",
                    "ErrorMessage": f"Mock server error: {e!s}",
                }
            },
            status_code=500,
        )


@app.post("/api/aeroVE5/revalidate")
async def revalidate_fare(request: Request) -> JSONResponse:
    """Mock fare revalidation endpoint.

    Validates that a selected fare is still available before booking.
    This is called after flight selection but before booking.

    Expected request body:
    {
        "session_id": "MOCK_SESSION_...",
        "fare_source_code": "MOCK_FARE_...",
        "fare_source_code_inbound": null  // Optional, for roundtrip
    }

    Returns (success):
    {
        "AirRevalidateResponse": {
            "AirRevalidateResult": {
                "IsValid": true,
                "FareItineraries": {...},
                "RequiredFieldsToBook": [...],
                "IsPassportFullDetailsMandatory": true
            }
        }
    }

    Returns (error):
    {
        "Errors": {
            "ErrorCode": "FARE_EXPIRED",
            "ErrorMessage": "Fare is no longer available..."
        }
    }
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Revalidate request: {list(body.keys())}")

        # Extract parameters
        session_id = body.get("session_id")
        fare_source_code = body.get("fare_source_code")

        if not session_id or not fare_source_code:
            logger.warning("Missing session_id or fare_source_code")
            return JSONResponse(
                content={
                    "Errors": {
                        "ErrorCode": "MISSING_FIELDS",
                        "ErrorMessage": "session_id and fare_source_code are required",
                    }
                },
                status_code=400,
            )

        logger.info(
            f"Revalidating fare: session={session_id[:20]}..., fare={fare_source_code[:30]}..."
        )

        # Validate using same logic as booking (MVP mode)
        is_valid, error_message = validate_booking_request(session_id, fare_source_code)

        if not is_valid:
            logger.warning(f"Revalidation failed: {error_message}")
            return JSONResponse(
                content=get_mock_revalidate_response(
                    session_id, fare_source_code, success=False
                ),
                status_code=400,
            )

        # Generate success response
        logger.info(f"Fare revalidated successfully for session {session_id[:20]}...")
        mock_response = get_mock_revalidate_response(
            session_id, fare_source_code, success=True
        )

        return JSONResponse(content=mock_response, status_code=200)

    except Exception as e:
        logger.error(f"Revalidate error: {e!s}", exc_info=True)
        return JSONResponse(
            content={
                "Errors": {
                    "ErrorCode": "REVALIDATE_ERROR",
                    "ErrorMessage": f"Mock server error: {e!s}",
                }
            },
            status_code=500,
        )


@app.post("/api/aeroVE5/airport_list")
async def get_airport_list(request: Request) -> JSONResponse:
    """Mock airport list endpoint.

    Returns the list of airports supported by FlightLogic.
    BUF and IAG are intentionally excluded so that nearby-airport filtering
    in search_flights only suggests FL-supported alternatives (e.g. ROC).
    """
    try:
        body = await request.json()
        logger.info(f"Airport list request: {list(body.keys())}")

        from tests.mocks.flightlogic.mock_data import get_mock_airport_list_response

        mock_response = get_mock_airport_list_response()
        logger.info(f"Returning {len(mock_response)} supported airports")
        return JSONResponse(content=mock_response, status_code=200)

    except Exception as e:
        logger.error(f"Airport list error: {e!s}", exc_info=True)
        return JSONResponse(
            content={
                "Errors": {
                    "ErrorCode": "AIRPORT_LIST_ERROR",
                    "ErrorMessage": f"Mock server error: {e!s}",
                }
            },
            status_code=500,
        )


@app.post("/api/aeroVE5/airline_list")
async def get_airline_list(request: Request) -> JSONResponse:
    """Mock airline list endpoint.

    Returns list of airlines with codes, names, and logo URLs.
    Used to enrich flight search results with airline logos.

    Expected request body:
    {
        "user_id": "...",
        "user_password": "...",
        "access": "Test",
        "ip_address": "127.0.0.1"
    }

    Returns:
    [
        {"AirLineCode": "BA", "AirLineName": "British Airways", "Logo": "https://..."},
        ...
    ]
    """
    try:
        body = await request.json()
        logger.info(f"Airline list request: {list(body.keys())}")

        mock_response = get_mock_airline_list_response()
        logger.info(f"Returning {len(mock_response)} airlines")
        return JSONResponse(content=mock_response, status_code=200)

    except Exception as e:
        logger.error(f"Airline list error: {e!s}", exc_info=True)
        return JSONResponse(
            content={
                "Errors": {
                    "ErrorCode": "AIRLINE_LIST_ERROR",
                    "ErrorMessage": f"Mock server error: {e!s}",
                }
            },
            status_code=500,
        )


@app.post("/api/aeroVE5/accommodation")
async def search_accommodation(request: Request) -> JSONResponse:
    """Mock accommodation search endpoint.

    Returns available hotels for destination with realistic pricing and amenities.
    Simulates FlightLogic accommodation API (currently in development).

    Expected request body:
    {
        "destination": "Barcelona",
        "check_in_date": "2025-11-15",
        "check_out_date": "2025-11-22",
        "guests": {"adults": 2, "children": 0}
    }

    Returns:
    {
        "AccommodationSearchResponse": {
            "destination": "Barcelona",
            "check_in_date": "2025-11-15",
            "check_out_date": "2025-11-22",
            "nights": 7,
            "AccommodationResult": {
                "total_hotels_found": 3,
                "hotels": [...]
            }
        }
    }
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Accommodation search request: {body}")

        # Extract accommodation details
        destination = body.get("destination", "Barcelona")
        check_in_date = body.get("check_in_date")
        check_out_date = body.get("check_out_date")
        guests = body.get("guests", {"adults": 2, "children": 0})

        logger.info(
            f"Searching accommodation for {destination} ({guests.get('adults', 0)} adults)"
        )

        # Generate mock response
        mock_response = get_mock_accommodation_response(
            destination=destination,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests=guests,
        )

        total_hotels = mock_response["AccommodationSearchResponse"][
            "AccommodationResult"
        ]["total_hotels_found"]
        logger.info(f"Returning {total_hotels} mock hotels for {destination}")

        return JSONResponse(content=mock_response, status_code=200)

    except Exception as e:
        logger.error(f"Accommodation search error: {e!s}", exc_info=True)
        return JSONResponse(
            content={
                "Errors": {
                    "ErrorCode": "ACCOMMODATION_SEARCH_ERROR",
                    "ErrorMessage": f"Mock server error: {e!s}",
                }
            },
            status_code=500,
        )


@app.post("/api/aeroVE5/booking")
async def book_flight(request: Request) -> JSONResponse:
    """Mock flight booking endpoint.

    Validates session_id and fare_source_code against stored sessions.
    Returns booking confirmation or error.

    Expected request body (FlightLogic API format):
    {
        "flightBookingInfo": {
            "flight_session_id": "MOCK_SESSION_...",
            "fare_source_code": "MOCK_FARE_BEST_VALUE_...",
            "IsPassportMandatory": "true",
            "fareType": "Public"
        },
        "paxInfo": {
            "customerEmail": "user@example.com",
            "customerPhone": "+1234567890",
            "paxDetails": [...]
        }
    }

    Returns (success):
    {
        "BookFlightResponse": {
            "BookFlightResult": {
                "Status": "CONFIRMED",
                "Success": true,
                "UniqueID": "MOCK_BOOKING_...",
                "TktTimeLimit": "2025-10-11T12:34:56",
                ...
            }
        }
    }

    Returns (error):
    {
        "Errors": {
            "ErrorCode": "INVALID_SESSION",
            "ErrorMessage": "Invalid session_id or fare_source_code..."
        }
    }
    """
    try:
        # Parse request body
        body = await request.json()

        # DEBUG: Log full request body structure
        logger.info(f"Full booking request body keys: {list(body.keys())}")
        if "flightBookingInfo" in body:
            logger.info(
                f"flightBookingInfo keys: {list(body['flightBookingInfo'].keys())}"
            )

        # Extract from FlightLogic API format: flightBookingInfo contains flight_session_id and fare_source_code
        flight_booking_info = body.get("flightBookingInfo", {})
        flight_session_id = flight_booking_info.get("flight_session_id")
        fare_source_code = flight_booking_info.get("fare_source_code")

        logger.info(
            f"Booking request: flight_session_id={flight_session_id}, fare_source_code={fare_source_code}"
        )

        if not flight_session_id or not fare_source_code:
            logger.warning(
                "Missing required fields: flight_session_id or fare_source_code"
            )
            return JSONResponse(
                content={
                    "Errors": {
                        "ErrorCode": "MISSING_FIELDS",
                        "ErrorMessage": "Missing required fields: flight_session_id and fare_source_code are required",
                    }
                },
                status_code=400,
            )

        # Validate booking request
        is_valid, error_message = validate_booking_request(
            flight_session_id, fare_source_code
        )

        if not is_valid:
            logger.warning(f"Booking validation failed: {error_message}")
            return JSONResponse(
                content=get_mock_booking_response(
                    flight_session_id, fare_source_code, success=False
                ),
                status_code=400,
            )

        # Generate success response
        logger.info(f"Booking successful for session {flight_session_id}")
        mock_response = get_mock_booking_response(
            flight_session_id, fare_source_code, success=True
        )
        unique_id = mock_response["BookFlightResponse"]["BookFlightResult"]["UniqueID"]
        logger.info(f"Generated booking ID: {unique_id}")

        return JSONResponse(content=mock_response, status_code=200)

    except Exception as e:
        logger.error(f"Booking error: {e!s}", exc_info=True)
        return JSONResponse(
            content={
                "Errors": {
                    "ErrorCode": "BOOKING_ERROR",
                    "ErrorMessage": f"Mock server error: {e!s}",
                }
            },
            status_code=500,
        )


@app.post("/api/aeroVE5/trip_details")
async def get_trip_details(request: Request) -> JSONResponse:
    """Mock trip details endpoint.

    Retrieves booking details including passenger info, flight segments, and pricing.

    Expected request body:
    {
        "user_id": "test_user",
        "user_password": "test_password",
        "access": "Test",
        "ip_address": "127.0.0.1",
        "UniqueID": "MOCK_BOOKING_20251011..."
    }

    Returns:
    {
        "TripDetailsResult": {
            "UniqueID": "MOCK_BOOKING_...",
            "Status": "CONFIRMED",
            "Passengers": [...],
            "FlightSegments": [...],
            "FareDetails": {...}
        }
    }
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Trip details request: {list(body.keys())}")

        # Extract UniqueID (booking reference)
        unique_id = body.get("UniqueID")

        if not unique_id:
            logger.warning("Missing UniqueID in trip details request")
            return JSONResponse(
                content={
                    "Errors": {
                        "ErrorCode": "MISSING_UNIQUE_ID",
                        "ErrorMessage": "UniqueID is required",
                    }
                },
                status_code=400,
            )

        logger.info(f"Fetching trip details for UniqueID: {unique_id}")

        # Generate mock trip details response
        mock_response = get_mock_trip_details_response(unique_id)

        logger.info(f"Returning trip details for booking {unique_id}")
        return JSONResponse(content=mock_response, status_code=200)

    except Exception as e:
        logger.error(f"Trip details error: {e!s}", exc_info=True)
        return JSONResponse(
            content={
                "Errors": {
                    "ErrorCode": "TRIP_DETAILS_ERROR",
                    "ErrorMessage": f"Mock server error: {e!s}",
                }
            },
            status_code=500,
        )


@app.post("/api/aeroVE5/ticket_order")
async def issue_tickets(request: Request) -> JSONResponse:
    """Mock ticket issuance endpoint.

    Issues tickets for a confirmed booking.

    Expected request body:
    {
        "user_id": "test_user",
        "user_password": "test_password",
        "access": "Test",
        "ip_address": "127.0.0.1",
        "UniqueID": "MOCK_BOOKING_20251011..."
    }

    Returns:
    {
        "AirOrderTicketRS": {
            "TicketOrderResult": {
                "Success": "true",
                "UniqueID": "MOCK_BOOKING_...",
                "Target": "Test",
                "Errors": null
            }
        }
    }
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Ticket order request: {list(body.keys())}")

        # Extract UniqueID (booking reference)
        unique_id = body.get("UniqueID")

        if not unique_id:
            logger.warning("Missing UniqueID in ticket order request")
            return JSONResponse(
                content={
                    "Errors": {
                        "ErrorCode": "MISSING_UNIQUE_ID",
                        "ErrorMessage": "UniqueID is required",
                    }
                },
                status_code=400,
            )

        logger.info(f"Issuing tickets for UniqueID: {unique_id}")

        # Generate mock ticket order response
        mock_response = get_mock_ticket_order_response(unique_id, success=True)

        logger.info(f"Tickets issued successfully for booking {unique_id}")
        return JSONResponse(content=mock_response, status_code=200)

    except Exception as e:
        logger.error(f"Ticket order error: {e!s}", exc_info=True)
        return JSONResponse(
            content={
                "Errors": {
                    "ErrorCode": "TICKET_ORDER_ERROR",
                    "ErrorMessage": f"Mock server error: {e!s}",
                }
            },
            status_code=500,
        )


@app.post("/api/hotel-api-v6/hotel_search")
async def search_hotels_v6(request: Request) -> JSONResponse:
    """Mock hotel search endpoint (Hotel API v6).

    Returns real hotel data from Bangalore search (3 sample hotels).
    This endpoint uses the actual FlightLogic Hotel API v6 response structure.

    Expected request body:
    {
        "user_id": "test_user",
        "user_password": "test_password",
        "access": "Test",
        "ip_address": "127.0.0.1",
        "checkin": "2025-11-24",
        "checkout": "2025-11-25",
        "city_name": "Bangalore",
        "country_name": "India",
        "occupancy": [{"room_no": 1, "adult": 2, "child": 0, "child_age": [0]}],
        "requiredCurrency": "INR"
    }

    Returns:
    {
        "status": {
            "sessionId": "MOCK_HOTEL_SESSION_...",
            "moreResults": false,
            "nextToken": "",
            "totalResults": 3
        },
        "itineraries": [...]  # 3 sample hotels from Bangalore
    }
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(
            f"Hotel search request: city={body.get('city_name')}, checkin={body.get('checkin')}"
        )

        # Extract search parameters
        city_name = body.get("city_name", "Bangalore")
        checkin = body.get("checkin")
        checkout = body.get("checkout")
        currency = body.get("requiredCurrency", "INR")

        # Generate mock response using real Bangalore data
        mock_response = get_mock_hotel_search_response(
            city_name=city_name, checkin=checkin, checkout=checkout, currency=currency
        )

        session_id = mock_response["status"]["sessionId"]
        total_results = mock_response["status"]["totalResults"]

        logger.info(f"Generated hotel session_id: {session_id}")
        logger.info(f"Returning {total_results} mock hotels for {city_name}")

        return JSONResponse(content=mock_response, status_code=200)

    except Exception as e:
        logger.error(f"Hotel search error: {e!s}", exc_info=True)
        return JSONResponse(
            content={"status": {"error": f"Mock server error: {e!s}"}},
            status_code=500,
        )


@app.post("/api/hotel-api-v6/get_room_rates")
async def get_room_rates_v6(request: Request) -> JSONResponse:
    """Mock get room rates endpoint (Hotel API v6).

    Returns available room options for a hotel.

    Expected request body:
    {
        "user_id": "test_user",
        "user_password": "test_password",
        "access": "Test",
        "ip_address": "127.0.0.1",
        "sessionId": "MOCK_HOTEL_SESSION_...",
        "tokenId": "MOCK_TOKEN_..."
    }

    Returns:
    {
        "hotelId": "1094726",
        "sessionId": "...",
        "rooms": [...]
    }
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Get room rates request: {list(body.keys())}")

        # Extract parameters
        session_id = body.get("sessionId")
        token_id = body.get("tokenId")

        if not session_id or not token_id:
            logger.warning("Missing sessionId or tokenId")
            return JSONResponse(
                content={"status": {"error": "sessionId and tokenId are required"}},
                status_code=400,
            )

        logger.info(f"Fetching room rates for token: {token_id}")

        # Generate mock room rates
        mock_response = get_mock_room_rates_response(session_id, token_id)

        logger.info("Returning room rates for hotel")
        return JSONResponse(content=mock_response, status_code=200)

    except Exception as e:
        logger.error(f"Get room rates error: {e!s}", exc_info=True)
        return JSONResponse(
            content={"status": {"error": f"Mock server error: {e!s}"}},
            status_code=500,
        )


@app.post("/api/hotel-api-v6/get_rate_rules")
async def get_rate_rules_v6(request: Request) -> JSONResponse:
    """Mock get rate rules endpoint (Hotel API v6).

    Validates rate before booking and returns detailed rate information.

    Expected request body:
    {
        "sessionId": "MOCK_HOTEL_SESSION_...",
        "productId": "trx109",
        "tokenId": "MOCK_TOKEN_...",
        "rateBasisId": "NDEwNzkzMw=="
    }

    Returns:
    {
        "sessionId": "...",
        "hotelId": 316798,
        "tokenId": "...",
        "roomRates": {
            "perBookingRates": [...]
        }
    }
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Get rate rules request: {list(body.keys())}")

        # Extract parameters
        session_id = body.get("sessionId")
        token_id = body.get("tokenId")
        rate_basis_id = body.get("rateBasisId")

        if not session_id or not token_id or not rate_basis_id:
            logger.warning("Missing required parameters")
            return JSONResponse(
                content={
                    "status": {
                        "error": "sessionId, tokenId, and rateBasisId are required"
                    }
                },
                status_code=400,
            )

        logger.info(f"Validating rate rules for rateBasisId: {rate_basis_id}")

        # Generate mock rate rules response
        mock_response = get_mock_rate_rules_response(
            session_id, token_id, rate_basis_id
        )

        logger.info("Returning rate rules validation")
        return JSONResponse(content=mock_response, status_code=200)

    except Exception as e:
        logger.error(f"Get rate rules error: {e!s}", exc_info=True)
        return JSONResponse(
            content={"status": {"error": f"Mock server error: {e!s}"}},
            status_code=500,
        )


@app.post("/api/hotel-api-v6/hotel_booking")
async def book_hotel_v6(request: Request) -> JSONResponse:
    """Mock hotel booking endpoint (Hotel API v6).

    Creates a hotel booking and returns confirmation.

    Expected request body:
    {
        "user_id": "test_user",
        "user_password": "test_password",
        "access": "Test",
        "ip_address": "127.0.0.1",
        "sessionId": "MOCK_HOTEL_SESSION_...",
        "rateKey": "RATE_KEY_ABC123",
        "guestInfo": {...}
    }

    Returns:
    {
        "status": "Success",
        "supplierConfirmationNum": "FL_HTL_20251116...",
        "referenceNum": "VOYA_HTL_...",
        "bookingDetails": {...}
    }
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Hotel booking request: {list(body.keys())}")

        # Extract parameters
        session_id = body.get("sessionId")
        rate_key = body.get("rateKey")

        if not session_id or not rate_key:
            logger.warning("Missing sessionId or rateKey")
            return JSONResponse(
                content={
                    "status": "Failed",
                    "errors": {"errorMessage": "sessionId and rateKey are required"},
                },
                status_code=400,
            )

        logger.info(f"Creating hotel booking for session: {session_id}")

        # Generate mock booking response
        mock_response = get_mock_hotel_booking_response(
            session_id, rate_key, success=True
        )

        confirmation_num = mock_response["supplierConfirmationNum"]
        logger.info(f"Hotel booking created: {confirmation_num}")

        return JSONResponse(content=mock_response, status_code=200)

    except Exception as e:
        logger.error(f"Hotel booking error: {e!s}", exc_info=True)
        return JSONResponse(
            content={
                "status": "Failed",
                "errors": {"errorMessage": f"Mock server error: {e!s}"},
            },
            status_code=500,
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


def main():
    """Run the mock server."""
    parser = argparse.ArgumentParser(description="FlightLogic Mock API Server")
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="Port to run the server on (default: 8002)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    args = parser.parse_args()

    logger.info(f"Starting FlightLogic Mock API on {args.host}:{args.port}")
    logger.info("Available endpoints:")
    logger.info(f"  - POST http://localhost:{args.port}/api/aeroVE5/availability")
    logger.info(f"  - POST http://localhost:{args.port}/api/aeroVE5/revalidate")
    logger.info(f"  - POST http://localhost:{args.port}/api/aeroVE5/airline_list")
    logger.info(f"  - POST http://localhost:{args.port}/api/aeroVE5/accommodation")
    logger.info(f"  - POST http://localhost:{args.port}/api/aeroVE5/booking")
    logger.info(f"  - POST http://localhost:{args.port}/api/aeroVE5/trip_details")
    logger.info(f"  - POST http://localhost:{args.port}/api/aeroVE5/ticket_order")
    logger.info(f"  - GET  http://localhost:{args.port}/health")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
