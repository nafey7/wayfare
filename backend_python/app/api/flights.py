"""Flight API endpoints.

Thin API layer that delegates to flight domain service.
All request/response logging happens automatically via LoggingMiddleware.
Business logic logging happens in FlightService with FlightLogger.
"""

import logging
import uuid
from contextlib import suppress
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator

from app.core.config import settings
from app.domains.auth.dependencies import get_current_user, optional_user
from app.domains.auth.exceptions import InvalidTokenError
from app.domains.bookings.exceptions import (
    BookingForbiddenError,
    GdsClientReferenceConflictError,
)
from app.domains.bookings.schemas import (
    BookingEventResponse,
    MulticityBookingGroupResponse,
)
from app.domains.flight import (
    AirportListRequest,
    AirportListResponse,
    FlightBookingRequest,
    FlightBookingResponse,
    FlightCancelRequest,
    FlightCancelResponse,
    FlightExtraServicesRequest,
    FlightExtraServicesResponse,
    FlightFareRulesRequest,
    FlightFareRulesResponse,
    FlightRevalidateRequest,
    FlightRevalidateResponse,
    FlightSearchRequest,
    FlightSearchResponse,
    PassengerType,
    TicketOrderRequest,
    TicketOrderResponse,
    TripDetailsRequest,
    TripDetailsResponse,
)
from app.domains.flight.exceptions import (
    FlightBookingError,
    FlightBookingSupplierSyncError,
    FlightSearchError,
    PaymentRequiredError,
)
from app.domains.flight.journey_params import (
    build_booking_search_route_params_from_flight_dict,
    normalize_search_redirect_journey_type,
)
from app.domains.flight.service import FlightService, get_flight_service
from app.domains.payment.exceptions import PaymentValidationError
from app.domains.user.schemas import UserPublic
from app.shared.slack_notify import notify_booking_error

router = APIRouter(prefix="/flights", tags=["Flights"])
logger = logging.getLogger(__name__)


def handle_invalid_token_error(error: InvalidTokenError) -> HTTPException:
    """Convert InvalidTokenError to HTTP 401 Unauthorized response.

    This is a shared handler to ensure consistent error responses across endpoints
    when authentication fails, enabling automatic token refresh on the frontend.

    Args:
        error: InvalidTokenError raised by service layer

    Returns:
        HTTPException with 401 status code
    """
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error))


@router.post("/search", response_model=FlightSearchResponse)
async def search_flights(
    request: FlightSearchRequest,
    service: FlightService = Depends(get_flight_service),
) -> FlightSearchResponse:
    """Search for available flights."""
    try:
        response = await service.search_flights(request)
    except FlightSearchError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    return response


@router.post("/fare-rules", response_model=FlightFareRulesResponse)
async def get_fare_rules(
    request: FlightFareRulesRequest,
    service: FlightService = Depends(get_flight_service),
) -> FlightFareRulesResponse:
    """Get fare rules and restrictions."""
    try:
        return await service.get_fare_rules(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/revalidate", response_model=FlightRevalidateResponse)
async def revalidate_fare(
    request: FlightRevalidateRequest,
    service: FlightService = Depends(get_flight_service),
) -> FlightRevalidateResponse:
    """Revalidate fare before booking."""
    try:
        return await service.revalidate_fare(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/book", response_model=FlightBookingResponse)
async def create_booking(
    request: FlightBookingRequest,
    service: FlightService = Depends(get_flight_service),
) -> FlightBookingResponse:
    """Create a flight booking."""
    try:
        return await service.create_booking(
            request,
            required_fields=request.required_fields,
            cancellation_policy_text=request.cancellation_policy_text,
        )
    except BookingForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except GdsClientReferenceConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except FlightBookingSupplierSyncError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except PaymentRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e)
        ) from e
    except FlightBookingError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    except InvalidTokenError as e:
        raise handle_invalid_token_error(e) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/issue_ticket", response_model=TicketOrderResponse)
async def issue_tickets(
    request: TicketOrderRequest,
    service: FlightService = Depends(get_flight_service),
) -> TicketOrderResponse:
    """Issue tickets for a booking."""
    try:
        return await service.issue_tickets(request)
    except PaymentRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e)
        ) from e
    except PaymentValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e)
        ) from e
    except FlightBookingError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    except InvalidTokenError as e:
        raise handle_invalid_token_error(e) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/cancel", response_model=FlightCancelResponse)
async def cancel_booking(
    request: FlightCancelRequest,
    service: FlightService = Depends(get_flight_service),
) -> FlightCancelResponse:
    """Cancel a booking."""
    try:
        return await service.cancel_booking(request)
    except InvalidTokenError as e:
        raise handle_invalid_token_error(e) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/extra-services", response_model=FlightExtraServicesResponse)
async def get_extra_services(
    request: FlightExtraServicesRequest,
    service: FlightService = Depends(get_flight_service),
) -> FlightExtraServicesResponse:
    """Get available extra services."""
    try:
        return await service.get_extra_services(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/trip-details", response_model=TripDetailsResponse)
async def get_trip_details(
    request: TripDetailsRequest,
    service: FlightService = Depends(get_flight_service),
) -> TripDetailsResponse:
    """Get trip/booking details.

    The request can contain either:
    - external_booking_reference: FlightLogic UniqueID (direct lookup)
    - voya_booking_reference: VOYA-XXXXXXXXXX (will be converted to external reference)
    """
    try:
        return await service.get_trip_details(request)
    except InvalidTokenError as e:
        raise handle_invalid_token_error(e) from e
    except BookingForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.get("/multicity-booking-context", response_model=MulticityBookingGroupResponse)
async def get_multicity_booking_context(
    voya_booking_reference: str = Query(
        ...,
        description="Any leg VOYA reference; returns the full multicity group when parent is set",
    ),
    service: FlightService = Depends(get_flight_service),
) -> MulticityBookingGroupResponse:
    """Return multicity group id and all leg booking events from Mongo (same user)."""
    try:
        return await service.get_multicity_booking_group(voya_booking_reference)
    except InvalidTokenError as e:
        raise handle_invalid_token_error(e) from e
    except BookingForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


class MulticityPartialBookingReportRequest(BaseModel):
    """Client-reported partial multicity leg booking after Revolut capture (ops visibility)."""

    multicity_group_reference: str = Field(..., min_length=1, max_length=128)
    revolut_order_id: str = Field(..., min_length=1, max_length=256)
    legs_booked_count: int = Field(..., ge=0)
    legs_total: int = Field(..., ge=1)
    last_error: str = Field(..., min_length=1, max_length=4000)
    booked_voya_references: list[str] = Field(default_factory=list)


@router.post("/multicity-partial-booking-report")
async def report_multicity_partial_booking_after_payment(
    body: MulticityPartialBookingReportRequest,
    service: FlightService = Depends(get_flight_service),
) -> dict[str, str]:
    """Record multicity partial failure after payment (structured logs + Slack in production)."""
    try:
        if not service.current_user:
            raise InvalidTokenError("Authentication required")
        user_id = str(service.current_user.id)
        logger.warning(
            "Multicity partial booking after payment (client report): user_id=%s group=%s "
            "order=%s booked=%s/%s error=%s refs=%s",
            user_id,
            body.multicity_group_reference,
            body.revolut_order_id,
            body.legs_booked_count,
            body.legs_total,
            body.last_error[:500],
            body.booked_voya_references,
        )
        await notify_booking_error(
            "Multicity post-payment",
            "Some legs failed after Revolut capture; user paid full amount",
            context={
                "user_id": user_id,
                "group_ref": body.multicity_group_reference,
                "revolut_order_id": body.revolut_order_id,
                "legs_booked": str(body.legs_booked_count),
                "legs_total": str(body.legs_total),
                "booked_refs": ",".join(body.booked_voya_references[:20]),
            },
            title="Multicity partial booking (post-payment)",
        )
        return {"status": "recorded"}
    except InvalidTokenError as e:
        raise handle_invalid_token_error(e) from e


@router.post("/airport-list", response_model=AirportListResponse)
async def get_airport_list(
    request: AirportListRequest,
    service: FlightService = Depends(get_flight_service),
) -> AirportListResponse:
    """Get list of commercial airports from FlightLogic.

    Returns a curated list of commercial airports, excluding private
    and military airports.

    This endpoint uses FlightLogic's `/airport_list` API which provides
    a comprehensive list of commercial airports worldwide.
    """
    try:
        return await service.get_airport_list(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to get airport list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve airport list",
        ) from e


@router.get("/my-bookings", response_model=list[BookingEventResponse])
async def get_my_bookings(
    _user: UserPublic = Depends(get_current_user()),
    service: FlightService = Depends(get_flight_service),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Max booking events to return (newest first)",
    ),
) -> list[BookingEventResponse]:
    """List the current user's flight booking events.

    Returns **BookingEventResponse** items (stable contract; not raw Mongo documents).
    Route display uses structured **route_legs** (per-leg endpoints and segment hops),
    **flight_trip_type** (``one_way`` | ``round_trip`` | ``multi_city``), optional
    **departure_airport_iata** (legacy TTL mirror of the first hop), and
    **primary_marketing_airline_name**. See OpenAPI field descriptions.
    """
    try:
        return await service.get_user_bookings(limit)
    except InvalidTokenError as e:
        raise handle_invalid_token_error(e) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/booking-auth")
async def authenticate_for_booking(
    request: dict,
    current_user: UserPublic | None = Depends(optional_user),
) -> dict:
    """Exchange short-lived booking token for access token.

    If the request includes a valid Bearer token (current session), the link's
    token must belong to the same user; otherwise returns 403.
    """
    from app.domains.auth.booking_auth import exchange_booking_token

    try:
        auth_token = request.get("auth_token")
        current_user_id = str(current_user.id) if current_user else None
        return await exchange_booking_token(auth_token, current_user_id=current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Flight booking-auth failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {e!s}",
        ) from e


@router.get("/test-endpoint")
async def test_endpoint() -> dict:
    """Simple test endpoint to verify deployment."""
    return {"status": "ok", "message": "New endpoints are working"}


@router.get("/test-session/{session_id}")
async def test_session_endpoint(session_id: str) -> dict:
    """Test if session endpoints work at all."""
    return {
        "status": "ok",
        "session_id": session_id,
        "message": "Session endpoint works",
    }


@router.get("/debug-sessions")
async def debug_sessions() -> dict:
    """Debug endpoint to check available sessions (both memory and MongoDB)."""
    try:
        from app.domains.booking_sessions.service import BookingSessionService

        # Get MongoDB session stats
        mongo_stats = await BookingSessionService.get_session_stats()

        # Try to get in-memory session stats
        memory_stats: dict[str, Any] = {"error": "ChatService not available"}
        try:
            import importlib

            chat_service_module = importlib.import_module("app.domains.chat.service")
            ChatService = chat_service_module.ChatService

            chat_service = ChatService()

            # Get info about available sessions in memory
            handler_count = len(chat_service._flight_handlers)
            sessions_info: dict[str, list[str]] = {}

            for uid, handler in chat_service._flight_handlers.items():
                session_ids = list(handler.booking_handler.booking_sessions.keys())
                sessions_info[uid] = session_ids

            memory_stats = {
                "handler_count": handler_count,
                "sessions_by_user": sessions_info,
                "total_sessions": sum(
                    len(sessions) for sessions in sessions_info.values()
                ),
            }
        except Exception as memory_error:
            memory_stats = {"error": str(memory_error)}

        return {
            "status": "ok",
            "mongodb_sessions": mongo_stats,
            "memory_sessions": memory_stats,
            "persistence_enabled": True,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/book-from-session/{session_id}", response_model=FlightBookingResponse)
async def create_booking_from_session(
    session_id: str,
    passenger_data: dict,
    service: FlightService = Depends(get_flight_service),
) -> FlightBookingResponse:
    """Create a flight booking using session data and passenger details.

    **PAYMENT REQUIRED**: This endpoint requires a successful payment before booking.
    The payment_intent_id must be included in passenger_data.

    Flow:
    1. Frontend creates payment intent via POST /api/payments/create-intent
    2. Frontend collects payment with Stripe.js
    3. Frontend calls this endpoint with payment_intent_id in passenger_data
    4. Backend validates payment succeeded
    5. Backend creates booking with FlightLogic API
    """
    try:
        from app.domains.booking_sessions.service import BookingSessionService
        from app.domains.common import PersonName
        from app.domains.flight.schemas import (
            AdultPassenger,
            ChildPassenger,
            ContactInformation,
            FareType,
            FlightBookingRequest,
            InfantPassenger,
            PassengerGroups,
            PersonalInfo,
            TravelDocuments,
        )
        from app.domains.flight.validators import calculate_age
        from app.domains.payment import PaymentService
        from app.domains.user.service import UserService

        # Extract payment_intent_id from passenger_data (optional)
        payment_intent_id = passenger_data.get("payment_intent_id")

        # Extract cancellation_policy_text from passenger_data (optional)
        cancellation_policy_text = passenger_data.get("cancellation_policy_text")

        # Validate payment if provided
        # NOTE: Payment is optional at booking creation for GDS (pay before ticket issuance)
        # Payment is required for LCC flights (which use different endpoint)
        if payment_intent_id and payment_intent_id != "demo_payment_intent":
            logger.info(
                f"Validating payment {payment_intent_id} for session {session_id}"
            )
            if not service.current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User authentication required for payment validation",
                )
            payment_service = PaymentService(user_id=str(service.current_user.id))
            try:
                # Check idempotency: payment should not already be used
                await payment_service.check_payment_not_used(payment_intent_id)
                # Validate payment succeeded
                await payment_service.validate_payment_succeeded(payment_intent_id)
                logger.info(f"✅ Payment validated for session {session_id}")
            except Exception as e:
                logger.error(f"Payment validation failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Payment validation failed: {e!s}",
                ) from e
        else:
            logger.info(
                f"Booking session {session_id} without payment (will require payment before ticket issuance)"
            )

        # Get session data
        session = await BookingSessionService.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking session {session_id} not found or expired",
            )

        session_data = session["data"]
        user_id = session["user_id"]
        selected_flight = session_data.get("selected_flight")
        search_params = session_data.get("search_params", {})
        fl_session_id = session_data.get(
            "fl_session_id"
        )  # FlightLogic session from revalidation

        # DEBUG: Log the session data and request to understand the flow
        logger.info(
            f"🔍 [BOOKING DEBUG] Session {session_id} - Received passenger_data keys: {list(passenger_data.keys())}"
        )
        if "selected_option" in passenger_data:
            logger.info(
                f"🔍 [BOOKING DEBUG] Request contains selected_option: {passenger_data['selected_option']}"
            )

        logger.info(
            f"🔍 [BOOKING DEBUG] Session selected_flight keys: {list(selected_flight.keys()) if selected_flight else 'None'}"
        )
        if selected_flight and "option_number" in selected_flight:
            logger.info(
                f"🔍 [BOOKING DEBUG] Session stored option_number: {selected_flight['option_number']}"
            )

        session_selected_option = session_data.get("selected_option")
        if session_selected_option:
            logger.info(
                f"🔍 [BOOKING DEBUG] Session stored selected_option: {session_selected_option}"
            )
        else:
            logger.info("🔍 [BOOKING DEBUG] No selected_option found in session data")

        if not selected_flight:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No flight selected in session",
            )

        # Get user data for contact information
        contact_email = "user@example.com"  # fallback
        if user_id and user_id != "unknown":
            with suppress(Exception):
                user = await UserService.get_user_public(user_id)
                if user and user.email:
                    contact_email = user.email

        # Build contact information - use first passenger phone or fallback to user profile
        contact_phone = None
        if passenger_data.get("passengers"):
            contact_phone = passenger_data["passengers"][0].get("phone")

        # If no passenger phone, try to get from user profile or use a default
        if not contact_phone and user_id and user_id != "unknown":
            with suppress(Exception):
                user = await UserService.get_user_public(user_id)
                mobile = getattr(user, "mobile", None) if user else None
                land = getattr(user, "phone", None) or getattr(
                    user, "phone_number", None
                )
                if user and (mobile or land):
                    contact_phone = mobile or land

        # Final fallback - use a default format
        if not contact_phone:
            contact_phone = "+31612345678"  # Default phone for testing

        contact_info = ContactInformation(
            email=contact_email,
            phone=contact_phone,
            area_code=None,
            country_code=None,
        )

        # Build passenger groups from frontend data
        # Categorize passengers by age (adult >= 12, child 2-11, infant < 2)
        adult_passengers = []
        child_passengers = []
        infant_passengers = []

        for passenger in passenger_data.get("passengers", []):
            personal_info = PersonalInfo(
                name=PersonName(
                    title=passenger.get("title", "Mr"),  # Include title from frontend
                    first_name=passenger.get("firstName", "Unknown"),
                    last_name=passenger.get("lastName", "Unknown"),
                ),
                date_of_birth=passenger.get("dateOfBirth"),
                nationality=passenger.get("nationality"),
            )

            # Add travel documents if provided
            travel_docs = None
            if passenger.get("passport"):
                travel_docs = TravelDocuments(
                    passport_number=passenger.get("passport"),
                    passport_expiry=passenger.get("passportExpiry"),
                    passport_country=passenger.get("passportCountry"),
                )

            # Categorize passenger by age
            age = calculate_age(passenger.get("dateOfBirth"))
            if age is None:
                # If age cannot be determined, default to adult (will be validated later)
                logger.warning(
                    f"Could not determine age for passenger {passenger.get('firstName')} {passenger.get('lastName')}, defaulting to adult"
                )
                adult_passenger = AdultPassenger(
                    personal_info=personal_info,
                    travel_documents=travel_docs,
                    saved_passenger_id=None,
                    service_selections=None,
                    frequent_flyer_info=None,
                )
                adult_passengers.append(adult_passenger)
            elif age >= 12:
                # Adult: 12+ years (per business rules: children are 2-11, adults are 12+)
                adult_passenger = AdultPassenger(
                    personal_info=personal_info,
                    travel_documents=travel_docs,
                    saved_passenger_id=None,
                    service_selections=None,
                    frequent_flyer_info=None,
                )
                adult_passengers.append(adult_passenger)
            elif age >= 2:
                # Child: 2-11 years (>= 2 and < 12)
                child_passenger = ChildPassenger(
                    personal_info=personal_info,
                    travel_documents=travel_docs,
                    saved_passenger_id=None,
                    service_selections=None,
                    frequent_flyer_info=None,
                )
                child_passengers.append(child_passenger)
            else:
                # Infant: < 2 years
                infant_passenger = InfantPassenger(
                    personal_info=personal_info,
                    travel_documents=travel_docs,
                    saved_passenger_id=None,
                    service_selections=None,
                    frequent_flyer_info=None,
                )
                infant_passengers.append(infant_passenger)

        passenger_groups = PassengerGroups(
            adults=adult_passengers if adult_passengers else None,
            children=child_passengers if child_passengers else None,
            infants=infant_passengers if infant_passengers else None,
        )

        logger.info(
            f"Categorized passengers: {len(adult_passengers)} adults, "
            f"{len(child_passengers)} children, {len(infant_passengers)} infants"
        )

        # Build booking request
        # selected_flight has wrapper structure: {"itinerary": <flight>, "option_number": N}
        # For round-trip: {"itinerary": <flight>, "inbound": <flight>, ...}
        flight = (
            selected_flight.get("itinerary")
            if isinstance(selected_flight, dict)
            else selected_flight
        )
        if flight is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Flight data missing itinerary - cannot proceed with booking",
            )
        flight_any: Any = cast("Any", flight)

        # DEBUG: Log the flight data structure to understand what we're working with
        logger.info(f"🔍 [DEBUG] Flight data type: {type(flight)}")
        logger.info(
            f"🔍 [DEBUG] Flight data keys (if dict): {list(flight.keys()) if isinstance(flight, dict) else 'N/A - not a dict'}"
        )

        if isinstance(flight, dict):
            logger.info(f"🔍 [DEBUG] Flight has 'pricing' key: {'pricing' in flight}")
            if "pricing" in flight:
                pricing = flight["pricing"]
                logger.info(f"🔍 [DEBUG] Pricing type: {type(pricing)}")
                logger.info(
                    f"🔍 [DEBUG] Pricing keys (if dict): {list(pricing.keys()) if isinstance(pricing, dict) else 'N/A - not a dict'}"
                )
                if isinstance(pricing, dict):
                    logger.info(
                        f"🔍 [DEBUG] Pricing has 'fare_source_code': {'fare_source_code' in pricing}"
                    )
                    if "fare_source_code" in pricing:
                        logger.info(
                            f"🔍 [DEBUG] fare_source_code value: {pricing['fare_source_code'][:50]}..."
                        )
        else:
            logger.info(
                f"🔍 [DEBUG] Flight has 'pricing' attr: {hasattr(flight_any, 'pricing')}"
            )
            if hasattr(flight_any, "pricing"):
                logger.info(
                    f"🔍 [DEBUG] Flight.pricing type: {type(flight_any.pricing)}"
                )
                logger.info(
                    f"🔍 [DEBUG] Flight.pricing has fare_source_code: {hasattr(flight_any.pricing, 'fare_source_code')}"
                )

        # Extract FlightLogic session ID for API call
        # Priority: fl_session_id (from revalidation) > search_params.session_id > booking session_id
        session_token = fl_session_id or search_params.get("session_id")
        if not session_token:
            # Fallback to booking session_id if FlightLogic session not available
            session_token = session_id
            logger.warning(
                "🔍 [DEBUG] Using booking session_id as fallback for FlightLogic session"
            )

        # Extract fare_source_code - multiple possible locations depending on flow
        fare_source_code = None

        # Priority 1: Check selected_flight wrapper (api_select_v2 flow stores it here)
        if isinstance(selected_flight, dict) and selected_flight.get(
            "fare_source_code"
        ):
            fare_source_code = selected_flight["fare_source_code"]
            logger.info(
                f"🔍 [DEBUG] Extracted fare_source_code from selected_flight wrapper: {fare_source_code[:50]}..."
            )
        # Priority 2: Check itinerary.updated_pricing.updated_fare_source_code (revalidation flow)
        elif (
            isinstance(flight, dict)
            and flight.get("updated_pricing")
            and isinstance(flight["updated_pricing"], dict)
            and flight["updated_pricing"].get("updated_fare_source_code")
        ):
            fare_source_code = flight["updated_pricing"]["updated_fare_source_code"]
            logger.info(
                f"🔍 [DEBUG] Extracted fare_source_code from updated_pricing: {fare_source_code[:50]}..."
            )
        # Priority 3: Handle Pydantic object case
        elif (
            hasattr(flight_any, "pricing")
            and flight_any.pricing is not None
            and hasattr(flight_any.pricing, "fare_source_code")
        ):
            fare_source_code = flight_any.pricing.fare_source_code
            logger.info(
                f"🔍 [DEBUG] Extracted fare_source_code from Pydantic object: {fare_source_code[:50]}..."
            )
        # Priority 4: Handle dict case - check nested path in pricing
        elif (
            isinstance(flight, dict)
            and flight.get("pricing")
            and isinstance(flight["pricing"], dict)
        ):
            fare_source_code = flight["pricing"].get("fare_source_code")
            logger.info(
                f"🔍 [DEBUG] Extracted fare_source_code from nested dict: {fare_source_code[:50] if fare_source_code else 'None'}..."
            )
        # Priority 5: Handle flat dict case (in case data was flattened during serialization)
        elif isinstance(flight, dict) and "fare_source_code" in flight:
            fare_source_code = flight["fare_source_code"]
            logger.info(
                f"🔍 [DEBUG] Extracted fare_source_code from flat dict: {fare_source_code[:50]}..."
            )
        else:
            logger.error(
                "🔍 [DEBUG] Could not find fare_source_code in any expected location"
            )
            logger.error(
                f"🔍 [DEBUG] selected_flight keys: {list(selected_flight.keys()) if isinstance(selected_flight, dict) else 'not a dict'}"
            )
            logger.error(
                f"🔍 [DEBUG] flight keys: {list(flight.keys()) if isinstance(flight, dict) else 'not a dict'}"
            )

        if not fare_source_code:
            # This is critical - without proper fare_source_code, booking will fail
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Flight data missing fare_source_code - cannot proceed with booking",
            )

        booking_request = FlightBookingRequest.model_validate(
            {
                "session_id": session_token,
                "fare_source_code": fare_source_code,
                "requires_passport": True,
                "fare_type": FareType.PUBLIC,
                "contact_information": contact_info.model_dump(),
                "passenger_groups": passenger_groups.model_dump(),
                "client_reference": f"VOYA_{session_id}",
                "payment_id": payment_intent_id,
                "saved_itinerary_id": None,
            }
        )

        # Execute booking with auto-refund on failure
        try:
            booking_result = await service.create_booking(
                booking_request,
                required_fields=booking_request.required_fields,
                cancellation_policy_text=cancellation_policy_text,  # Pass cancellation policy from fare rules
            )

            # Mark payment as used for this booking (idempotency tracking)
            if payment_intent_id and payment_intent_id != "demo_payment_intent":
                try:
                    payment_service = PaymentService(
                        user_id=str(service.current_user.id)
                        if service.current_user
                        else None
                    )
                    await payment_service.mark_payment_used_for_booking(
                        payment_intent_id
                    )
                except Exception as mark_error:
                    # Log error but don't fail the booking (booking already succeeded)
                    logger.error(
                        f"Failed to mark payment {payment_intent_id} as used (non-critical): {mark_error}"
                    )

            # Don't delete session immediately - keep it for full TTL to allow page refreshes
            # during payment process. Session will auto-expire after 3 hours.
            # await BookingSessionService.delete_session(session_id)

            return booking_result

        except Exception as booking_error:
            # If booking fails after payment was validated, refund the customer
            if payment_intent_id and payment_intent_id != "demo_payment_intent":
                logger.error(
                    f"Booking failed after payment validation for {payment_intent_id}. "
                    f"Initiating automatic refund. Error: {booking_error}"
                )
                try:
                    payment_service = PaymentService(
                        user_id=str(service.current_user.id)
                        if service.current_user
                        else None
                    )
                    refund_id = await payment_service.refund_payment(
                        payment_intent_id, reason="booking_creation_failed"
                    )
                    logger.info(
                        f"✅ Automatic refund completed: {refund_id} for failed booking"
                    )
                    # Include refund info in error message to user
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Booking creation failed. Your payment has been automatically refunded (refund ID: {refund_id}). Please try again or contact support.",
                    ) from booking_error
                except Exception as refund_error:
                    logger.critical(
                        f"CRITICAL: Failed to refund payment {payment_intent_id} after booking failure. "
                        f"Manual intervention required. Refund error: {refund_error}"
                    )
                    # Re-raise booking error with refund failure notice
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Booking creation failed and automatic refund failed. "
                        f"Please contact support immediately with payment ID: {payment_intent_id}",
                    ) from booking_error
            else:
                # No payment involved, just raise booking error
                raise

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create booking from session: {e!s}",
        ) from e


@router.get("/session/{session_id}")
async def get_booking_session_by_id(session_id: str) -> dict:
    """Get booking session data using session ID from MongoDB.

    Returns `journey_kind` ``single`` (default) or ``multicity``. For multicity,
    `multicity_legs` holds the same structure as stored `data.legs`: per-leg
    `fl_session_id`, `fare_source_code`, and `selected_flight` for payment/revalidate.
    """
    try:
        # Import BookingSessionService
        from app.domains.booking_sessions.service import BookingSessionService
        from app.domains.user.service import UserService

        # Get session data from MongoDB
        session = await BookingSessionService.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking session {session_id} not found or expired",
            )

        session_data = session["data"]
        user_id = session["user_id"]

        # Get user data for prefilling
        user_data = {}
        if user_id and user_id != "unknown":
            try:
                user = await UserService.get_user_public(user_id)
                if user:
                    user_data = {
                        "id": str(user.id),
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "date_of_birth": getattr(user, "date_of_birth", None),
                        "nationality": getattr(user, "nationality", None),
                        "passport_number": getattr(user, "passport_number", None),
                        "passport_expiry": getattr(user, "passport_expiry", None),
                        "passport_country": getattr(user, "passport_country", None),
                        "phone": getattr(user, "phone", None),
                        "postal_code": getattr(user, "postal_code", None),
                    }
            except Exception as user_error:
                # Log but don't fail - user data is optional
                print(f"User lookup failed for {user_id}: {user_error}")

        return {
            "session_id": session_id,
            "journey_kind": session_data.get("journey_kind", "single"),
            "selected_flight": session_data.get("selected_flight"),
            "multicity_legs": session_data.get("legs"),
            "search_params": session_data.get("search_params"),
            "selected_option": session_data.get("selected_option"),
            "user_data": user_data,
            "status": session_data.get("status", "unknown"),
            "timestamp": session_data.get("timestamp"),
            "source": session_data.get("source"),
            "debug_info": {
                "user_id": user_id,
                "has_user_data": bool(user_data),
                "session_created": session.get("created_at"),
                "session_updated": session.get("updated_at"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get booking session: {e!s} | Traceback: {traceback.format_exc()}",
        ) from e


class MulticityLegSelectionItem(BaseModel):
    """One leg selection for multicity (Circle) parallel search results."""

    leg_index: int = Field(
        ..., ge=0, description="Leg index matching search multicity_legs"
    )
    session_id: str = Field(..., description="FlightLogic session_id for this leg")
    flight_id: str = Field(
        ...,
        description="Fare source code for this leg (same as single-leg flight_id)",
    )


class FlightSelectionRequest(BaseModel):
    """Request to select a flight for booking.

    **Single leg:** `session_id` + `flight_id` (default).

    **Multicity:** `multicity_legs` with at least two items; each leg has its own
    `session_id` and `flight_id`. Stored session has `journey_kind` ``multicity``,
    `legs` with per-leg `fl_session_id`, `fare_source_code`, and `selected_flight`
    (validated itinerary) for revalidate/book and payment flows.
    """

    session_id: str | None = Field(
        None, description="FlightLogic session token from search response (single leg)"
    )
    flight_id: str | None = Field(
        None,
        description="Flight fare_source_code (single leg)",
    )
    multicity_legs: list[MulticityLegSelectionItem] | None = Field(
        None,
        description="Two or more legs; each uses that leg's session_id and fare code",
    )
    adults: int = Field(1, ge=1, description="Number of adult passengers")
    children: int = Field(0, ge=0, description="Number of child passengers")
    infants: int = Field(0, ge=0, description="Number of infant passengers")

    @model_validator(mode="after")
    def _validate_single_vs_multicity(self) -> "FlightSelectionRequest":
        ml = self.multicity_legs
        if ml is not None:
            if len(ml) < 2:
                raise ValueError("multicity_legs must contain at least 2 legs")
            return self
        if not self.session_id or not self.flight_id:
            raise ValueError(
                "session_id and flight_id are required when multicity_legs is not used"
            )
        return self


class FlightSelectionResponse(BaseModel):
    """Response from flight selection."""

    session_id: str = Field(..., description="Booking session ID for redirect")
    redirect_url: str = Field(..., description="URL to redirect user to for booking")


def _passenger_counts_from_validated_flight(
    validated_flight: Any,
    adults: int,
    children: int,
    infants: int,
) -> tuple[int, int, int]:
    """Prefer passenger counts from revalidate response breakdown when present."""
    adults_count, children_count, infants_count = adults, children, infants
    if hasattr(validated_flight, "updated_pricing") and hasattr(
        validated_flight.updated_pricing, "passenger_fare_breakdown"
    ):
        for breakdown in validated_flight.updated_pricing.passenger_fare_breakdown:
            if hasattr(breakdown, "passenger_type_info"):
                pax_type = breakdown.passenger_type_info.passenger_type
                pax_count = breakdown.passenger_type_info.passenger_count
                if pax_type in (
                    PassengerType.ADULT,
                    PassengerType.ADULT.value,
                    "ADT",
                ):
                    adults_count = pax_count
                elif pax_type in (
                    PassengerType.CHILD,
                    PassengerType.CHILD.value,
                    "CHD",
                ):
                    children_count = pax_count
                elif pax_type in (
                    PassengerType.INFANT,
                    PassengerType.INFANT.value,
                    "INF",
                ):
                    infants_count = pax_count
    return adults_count, children_count, infants_count


async def _select_multicity_flights_for_booking(
    request: FlightSelectionRequest,
    service: FlightService,
    user_id: str,
) -> FlightSelectionResponse:
    """Revalidate each multicity leg and persist one booking session with `journey_kind` multicity."""
    from datetime import UTC, datetime

    import jwt

    from app.domains.booking_sessions.service import BookingSessionService

    legs_in = sorted(request.multicity_legs or [], key=lambda x: x.leg_index)
    leg_rows: list[dict[str, Any]] = []
    first_validated: Any = None

    for leg in legs_in:
        revalidate_request = FlightRevalidateRequest(
            session_id=leg.session_id,
            fare_source_code=leg.flight_id,
            adults=request.adults,
            children=request.children,
            infants=request.infants,
        )
        logger.info(
            "Multicity revalidate leg %s fare %s... for user %s",
            leg.leg_index,
            leg.flight_id[:20],
            user_id,
        )
        revalidate_response = await service.revalidate_fare(revalidate_request)
        if not revalidate_response.is_fare_available:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"This fare is no longer available for leg {leg.leg_index}. Please search again.",
            )
        validated_itineraries = revalidate_response.validated_fare_itineraries
        if not validated_itineraries:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Revalidation returned no itinerary data for leg {leg.leg_index}",
            )
        validated_flight = validated_itineraries[0]
        if first_validated is None:
            first_validated = validated_flight
        itinerary_dump = (
            validated_flight.model_dump()
            if hasattr(validated_flight, "model_dump")
            else validated_flight
        )
        leg_rows.append(
            {
                "leg_index": leg.leg_index,
                "fl_session_id": leg.session_id,
                "fare_source_code": leg.flight_id,
                "selected_flight": {
                    "itinerary": itinerary_dump,
                    "fare_source_code": leg.flight_id,
                },
            }
        )

    if first_validated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Multicity revalidation produced no validated fare",
        )
    adults_count, children_count, infants_count = (
        _passenger_counts_from_validated_flight(
            first_validated,
            request.adults,
            request.children,
            request.infants,
        )
    )
    search_params: dict[str, Any] = {
        "adults": adults_count,
        "children": children_count,
        "infants": infants_count,
        "journey_type": "Circle",
    }
    try:
        flight_dict = (
            first_validated.model_dump()
            if hasattr(first_validated, "model_dump")
            else first_validated
        )
        flight_legs = flight_dict.get("flight_legs", [])
        if flight_legs:
            first_leg = flight_legs[0]
            segments = first_leg.get("flight_segments", [])
            if segments:
                first_segment = segments[0]
                last_segment = segments[-1]
                dep_airport = first_segment.get("departure_airport", {})
                if dep_airport:
                    search_params["origin"] = dep_airport.get("iata_code", "")
                arr_airport = last_segment.get("arrival_airport", {})
                if arr_airport:
                    search_params["destination"] = arr_airport.get("iata_code", "")
                dep_datetime = first_segment.get("departure_datetime")
                if dep_datetime:
                    if isinstance(dep_datetime, str):
                        search_params["departure_date"] = dep_datetime.split("T")[0]
                    else:
                        search_params["departure_date"] = str(dep_datetime).split("T")[
                            0
                        ]
    except Exception as e:
        logger.warning("Could not enrich multicity search_params from first leg: %s", e)

    booking_session_id = str(uuid.uuid4())
    session_data: dict[str, Any] = {
        "journey_kind": "multicity",
        "journey_type": "Circle",
        "search_params": search_params,
        "legs": leg_rows,
        "status": "fare_validated",
        "source": "api_select_v2_multicity",
    }

    success = await BookingSessionService.store_session(
        session_id=booking_session_id,
        user_id=user_id,
        session_data=session_data,
        ttl_hours=6,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create booking session",
        )

    logger.info(
        "Created multicity booking session %s (%s legs, user=%s)",
        booking_session_id,
        len(leg_rows),
        user_id,
    )

    booking_token = None
    if user_id != "unknown" and service.current_user:
        try:
            payload = {
                "user_id": user_id,
                "session_id": booking_session_id,
                "type": "booking_auth",
                "exp": datetime.now(UTC).timestamp() + 1800,
            }
            booking_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
            logger.info("Generated booking auth token for user %s", user_id)
        except Exception as token_error:
            logger.warning("Failed to generate booking token: %s", token_error)

    url_params = [
        f"session_id={booking_session_id}",
        "source=api",
        "initial_step=rules",
    ]
    if booking_token:
        url_params.append(f"auth_token={booking_token}")

    redirect_url = (
        f"{settings.BACKEND_URL}/dev/flight-booker/index.html?{'&'.join(url_params)}"
    )
    return FlightSelectionResponse(
        session_id=booking_session_id,
        redirect_url=redirect_url,
    )


class SearchRedirectRequest(BaseModel):
    """Request to generate redirect URL for full flight search results."""

    origin: str = Field(
        ...,
        description="Origin airport IATA code (3 letters) or city name",
        min_length=3,
        max_length=50,
    )
    destination: str = Field(
        ...,
        description="Destination airport IATA code (3 letters) or city name",
        min_length=3,
        max_length=50,
    )
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    return_date: str | None = Field(
        None, description="Return date (YYYY-MM-DD), optional for one-way"
    )
    adults: int = Field(1, ge=1, le=9, description="Number of adults")
    children: int = Field(0, ge=0, le=9, description="Number of children")
    infants: int = Field(0, ge=0, le=9, description="Number of infants")
    journey_type: str = Field("OneWay", description="Journey type: OneWay or Return")
    cabin_class: str = Field("Economy", description="Cabin class")
    origin_is_city: bool = Field(
        True, description="True if origin was a city name (not airport code)"
    )
    destination_is_city: bool = Field(
        True, description="True if destination was a city name (not airport code)"
    )
    direct_flight: int = Field(
        0,
        ge=0,
        le=1,
        description="1 = direct flights only, 0 = all flights (default)",
    )
    max_stops: int | None = Field(
        None,
        ge=0,
        le=3,
        description="Maximum number of stops filter from chat (0=direct, 1=max 1 stop, etc.)",
    )
    price_min: float | None = Field(
        None,
        ge=0,
        description="Minimum price filter from chat",
    )
    price_max: float | None = Field(
        None,
        ge=0,
        description="Maximum price filter from chat",
    )
    preferred_airline: str | None = Field(
        None,
        min_length=2,
        max_length=3,
        description="Preferred airline IATA code from chat (e.g., 'BA', 'EK')",
    )
    max_outbound_duration: float | None = Field(
        None,
        gt=0,  # gt=0 (not ge=0): 0-hour duration is meaningless
        description="Maximum outbound flight duration in hours from chat",
    )
    max_inbound_duration: float | None = Field(
        None,
        gt=0,  # gt=0 (not ge=0): 0-hour duration is meaningless
        description="Maximum inbound/return flight duration in hours from chat",
    )


class SearchRedirectResponse(BaseModel):
    """Response with redirect URL for flight search."""

    redirect_url: str = Field(
        ..., description="URL to redirect user to for full search results"
    )


@router.post("/search-redirect", response_model=SearchRedirectResponse)
async def search_redirect(
    request: SearchRedirectRequest,
    service: FlightService = Depends(get_flight_service),
) -> SearchRedirectResponse:
    """
    Generate redirect URL for full flight search results.

    This endpoint generates a JWT auth token and returns a URL that redirects
    users to the flight-booker UI with auto-search enabled, showing all available
    flights (not just the curated 3-5 options from chat).
    """
    try:
        from datetime import UTC, datetime

        import jwt

        # Get current user ID (if authenticated)
        user_id = "unknown"
        if service.current_user:
            user_id = str(service.current_user.id)

        journey_type = normalize_search_redirect_journey_type(
            request.journey_type,
            has_return_date=bool(request.return_date),
        )

        # Generate booking auth token for authenticated users
        # Token format: Same as booking flow (type: "booking_auth", 30 min expiry)
        # session_id is None for search-only flow (no booking session)
        booking_token = None
        if user_id != "unknown" and service.current_user:
            try:
                payload = {
                    "user_id": user_id,
                    "session_id": None,  # No booking session for search-only flow
                    "type": "booking_auth",
                    "exp": datetime.now(UTC).timestamp() + 1800,  # 30 minutes
                }
                booking_token = jwt.encode(
                    payload, settings.SECRET_KEY, algorithm="HS256"
                )
                logger.info(f"Generated search redirect auth token for user {user_id}")
            except Exception as token_error:
                logger.warning(
                    f"Failed to generate search redirect token: {token_error}"
                )

        # Build URL with all search parameters
        # URL-encode origin/destination (handles city names with spaces like "New York")
        from urllib.parse import quote

        url_params = [
            f"origin={quote(request.origin)}",
            f"destination={quote(request.destination)}",
            f"departure_date={request.departure_date}",
            f"adults={request.adults}",
            f"children={request.children}",
            f"infants={request.infants}",
            f"journey_type={journey_type}",
            f"cabin_class={request.cabin_class}",
            f"origin_is_city={'true' if request.origin_is_city else 'false'}",
            f"destination_is_city={'true' if request.destination_is_city else 'false'}",
            "source=chat_results",
            "auto_search=true",
            "initial_step=select",  # Navigate directly to step 2 (results) instead of step 1 (search)
            f"direct_flight={request.direct_flight}",
        ]

        # Add max_stops only if provided (from chat filters)
        if request.max_stops is not None:
            url_params.append(f"max_stops={request.max_stops}")

        # Add price filters only if provided (from chat filters)
        if request.price_min is not None:
            url_params.append(f"price_min={request.price_min}")
        if request.price_max is not None:
            url_params.append(f"price_max={request.price_max}")

        # Add preferred airline only if provided (from chat filters)
        if request.preferred_airline:
            url_params.append(f"preferred_airline={quote(request.preferred_airline)}")

        # Add duration filters only if provided (from chat filters)
        if request.max_outbound_duration is not None:
            url_params.append(f"max_outbound_duration={request.max_outbound_duration}")
        if request.max_inbound_duration is not None:
            url_params.append(f"max_inbound_duration={request.max_inbound_duration}")

        # Add return_date only if provided
        if request.return_date:
            url_params.insert(3, f"return_date={request.return_date}")

        # Add auth token if generated
        if booking_token:
            url_params.append(f"auth_token={booking_token}")

        redirect_url = f"{settings.BACKEND_URL}/dev/flight-booker/index.html?{'&'.join(url_params)}"

        logger.info(
            f"Generated search redirect URL for user {user_id} (origin={request.origin}, destination={request.destination}, journey_type={journey_type})"
        )

        return SearchRedirectResponse(redirect_url=redirect_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate search redirect: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate search redirect: {e!s}",
        ) from e


@router.post("/select", response_model=FlightSelectionResponse)
async def select_flight_for_booking(
    request: FlightSelectionRequest,
    service: FlightService = Depends(get_flight_service),
) -> FlightSelectionResponse:
    """
    Select a flight from search results for booking.

    This endpoint revalidates the fare with FlightLogic to get fresh data,
    then creates a booking session with the validated flight details.

    Frontend only needs to send session_id + flight_id (no full flight object).
    """
    try:
        from app.domains.booking_sessions.service import BookingSessionService

        # Get current user ID (if authenticated)
        user_id = "unknown"
        if service.current_user:
            user_id = str(service.current_user.id)

        if request.multicity_legs:
            return await _select_multicity_flights_for_booking(
                request, service, user_id
            )

        session_id = request.session_id
        flight_id = request.flight_id
        if session_id is None or flight_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id and flight_id are required for single-leg selection",
            )

        # Step 1: Revalidate fare with FlightLogic to get fresh, validated data
        revalidate_request = FlightRevalidateRequest(
            session_id=session_id,
            fare_source_code=flight_id,
            adults=request.adults,
            children=request.children,
            infants=request.infants,
            return_fare_source_code=None,
        )

        logger.info(f"Revalidating fare {flight_id[:20]}... for user {user_id}")

        revalidate_response = await service.revalidate_fare(revalidate_request)

        # Check if fare is still available
        if not revalidate_response.is_fare_available:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This fare is no longer available. Please search again.",
            )

        # Step 2: Extract validated flight data from revalidate response
        validated_itineraries = revalidate_response.validated_fare_itineraries
        if not validated_itineraries:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Revalidation returned no itinerary data",
            )

        # Get the first validated itinerary
        validated_flight = validated_itineraries[0]

        adults_count, children_count, infants_count = (
            _passenger_counts_from_validated_flight(
                validated_flight,
                request.adults,
                request.children,
                request.infants,
            )
        )

        logger.info(
            f"Extracted passenger counts from revalidate response: "
            f"adults={adults_count}, children={children_count}, infants={infants_count}"
        )

        # Step 3: Build complete search_params with passenger counts and route/date info
        search_params = {
            "adults": adults_count,
            "children": children_count,
            "infants": infants_count,
        }

        # Enrich search_params with route and dates from validated flight itinerary
        try:
            flight_dict = (
                validated_flight.model_dump()
                if hasattr(validated_flight, "model_dump")
                else validated_flight
            )
            route_params = build_booking_search_route_params_from_flight_dict(
                cast("dict[str, Any]", flight_dict)
            )
            search_params.update(route_params)
        except Exception as e:
            logger.warning(f"Could not extract search params from flight: {e}")
            # Continue with minimal search_params (adults, children, infants)

        # Step 4: Generate booking session ID and store validated data with complete search_params
        booking_session_id = str(uuid.uuid4())

        session_data = {
            "selected_flight": {
                "itinerary": validated_flight.model_dump()
                if hasattr(validated_flight, "model_dump")
                else validated_flight,
                "fare_source_code": flight_id,
            },
            "fl_session_id": session_id,  # FlightLogic session for booking
            "search_params": search_params,  # Includes passenger counts (adults, children, infants) plus route/date info
            "status": "fare_validated",
            "source": "api_select_v2",
        }

        # Store session in MongoDB
        success = await BookingSessionService.store_session(
            session_id=booking_session_id,
            user_id=user_id,
            session_data=session_data,
            ttl_hours=3,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create booking session",
            )

        logger.info(
            f"Created booking session {booking_session_id} with validated fare (user: {user_id})"
        )

        # Generate booking auth token for authenticated users
        booking_token = None
        if user_id != "unknown" and service.current_user:
            try:
                from datetime import UTC, datetime

                import jwt

                payload = {
                    "user_id": user_id,
                    "session_id": booking_session_id,
                    "type": "booking_auth",
                    "exp": datetime.now(UTC).timestamp() + 1800,  # 30 minutes
                }
                booking_token = jwt.encode(
                    payload, settings.SECRET_KEY, algorithm="HS256"
                )
                logger.info(f"Generated booking auth token for user {user_id}")
            except Exception as token_error:
                logger.warning(f"Failed to generate booking token: {token_error}")

        # Build URL with session_id and source=api (no preflight to avoid 414 errors)
        # Flight data is fetched via session API instead of embedding in URL
        # initial_step=rules navigates directly to rules step (step 3) without showing step 1
        url_params = [
            f"session_id={booking_session_id}",
            "source=api",
            "initial_step=rules",  # Navigate directly to rules step instead of step 1
        ]
        if booking_token:
            url_params.append(f"auth_token={booking_token}")

        redirect_url = f"{settings.BACKEND_URL}/dev/flight-booker/index.html?{'&'.join(url_params)}"

        logger.info(
            f"Generated redirect URL for session {booking_session_id} (source=api ensures rules step first)"
        )

        return FlightSelectionResponse(
            session_id=booking_session_id,
            redirect_url=redirect_url,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to select flight: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select flight: {e!s}",
        ) from e
