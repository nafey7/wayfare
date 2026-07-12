"""Hotel API endpoints.

Thin API layer that delegates to hotel domain service.
All request/response logging happens automatically via LoggingMiddleware.
Business logic logging happens in HotelService with HotelLogger.
"""

import logging
import uuid
from datetime import UTC, datetime
from urllib.parse import quote

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.domains.auth.dependencies import get_current_user, optional_user
from app.domains.auth.exceptions import InvalidTokenError
from app.domains.bookings.exceptions import BookingForbiddenError
from app.domains.hotel import (
    HotelBookingDetailsRequest,
    HotelBookingDetailsResponse,
    HotelBookingRequest,
    HotelBookingResponse,
    HotelCancelRequest,
    HotelCancelResponse,
    HotelMoreResultsRequest,
    HotelMyBookingListItem,
    HotelRateRulesRequest,
    HotelRateRulesResponse,
    HotelRoomRatesRequest,
    HotelRoomRatesResponse,
    HotelSearchRequest,
    HotelSearchResponse,
    HotelService,
    HotelTripDetailsRequest,
    HotelTripDetailsResponse,
)
from app.domains.hotel.booking_event_display import (
    merge_session_and_client_hotel_display,
)
from app.domains.hotel.exceptions import HotelBookingError, HotelSearchError
from app.domains.hotel.service import get_hotel_service
from app.domains.hotel.stay_snapshot import hotel_stay_from_booking_details
from app.domains.user.schemas import UserPublic

router = APIRouter(prefix="/hotels", tags=["Hotels"])
logger = logging.getLogger(__name__)


@router.post("/booking-auth")
async def authenticate_for_booking(
    request: dict,
    current_user: UserPublic | None = Depends(optional_user),
) -> dict:
    """Exchange short-lived booking token for access token (same flow as flights).

    Used when user opens hotel-booker from chat or email link with auth_token in URL.
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
        logger.error("Hotel booking-auth failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {e!s}",
        ) from e


@router.post("/search", response_model=HotelSearchResponse)
async def search_hotels(
    request: HotelSearchRequest,
    service: HotelService = Depends(get_hotel_service),
) -> HotelSearchResponse:
    """Search for available hotels.

    Supports three search methods:
    1. City-based: city_name + country_name
    2. Geolocation: latitude + longitude (+ optional radius)
    3. Hotel codes: hotel_codes list

    Returns:
        HotelSearchResponse with available hotels and session ID for booking
    """
    try:
        return await service.search_hotels(request)
    except HotelSearchError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/more-results", response_model=HotelSearchResponse)
async def get_more_results(
    request: HotelMoreResultsRequest,
    service: HotelService = Depends(get_hotel_service),
) -> HotelSearchResponse:
    """Get additional hotel search results using pagination token.

    Use this endpoint when moreResults is true in the hotel search response
    to fetch additional hotels using the nextToken.

    Requires:
    - session_id: FlightLogic session ID from search response
    - next_token: Next token from previous search response
    - max_result: Maximum number of results to return (default: 20)

    Returns:
        HotelSearchResponse with additional hotels and updated pagination info
    """
    try:
        return await service.get_more_results(request)
    except HotelSearchError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/room-rates", response_model=HotelRoomRatesResponse)
async def get_room_rates(
    request: HotelRoomRatesRequest,
    service: HotelService = Depends(get_hotel_service),
) -> HotelRoomRatesResponse:
    """Get detailed room rates for a specific hotel.

    Requires:
    - session_id: From hotel search response
    - token_id: Hotel token from search results

    Returns:
        Available room options with pricing details and rate keys for booking
    """
    try:
        return await service.get_room_rates(request)
    except HotelSearchError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/rate-rules", response_model=HotelRateRulesResponse)
async def check_rate_rules(
    request: HotelRateRulesRequest,
    internal_session_id: str,
    service: HotelService = Depends(get_hotel_service),
) -> HotelRateRulesResponse:
    """Validate hotel rate rules before booking and persist rateBasisId to session.

    CRITICAL: Call when hotel-booker form loads to validate rate is still available.
    The validated rateBasisId will be saved to the booking session for later use.

    Requires:
    - session_id: FlightLogic session ID from search response
    - token_id: Hotel token from search results
    - product_id: Product ID from search results
    - rate_basis_id: Rate key from room rates response
    - internal_session_id: Internal booking session UUID (query param)

    Returns:
        Validated rate information with rateBasisId for booking
    """
    try:
        # Validate rate with FlightLogic
        response = await service.check_rate_rules(request)

        # Persist validated rateBasisId to MongoDB session
        from app.domains.booking_sessions import BookingSessionService

        session_data = await BookingSessionService.get_session(
            session_id=internal_session_id
        )

        if session_data:
            # Update existing session with validated rate basis ID
            await BookingSessionService.update_session_data(
                session_id=internal_session_id,
                updates={
                    "validated_rate_basis_id": response.rate_basis_id,
                    "flightlogic_session_id": request.session_id,
                    "rate_validated_at": "now",  # BookingSessionService handles datetime
                },
            )
            logger.info(
                f"Updated session {internal_session_id[:15]}... with rateBasisId"
            )
        else:
            # CREATE session for direct entry (certification flow)
            # This happens when user accesses hotel-booker directly without chat
            await BookingSessionService.store_session(
                session_id=internal_session_id,
                user_id="direct_entry",  # Placeholder for auto-login users
                session_data={
                    "validated_rate_basis_id": response.rate_basis_id,
                    "flightlogic_session_id": request.session_id,
                    "rate_validated_at": "now",
                    "entry_type": "direct",  # Track entry method
                },
                ttl_hours=3,
            )
            logger.info(
                f"Created new session {internal_session_id[:15]}... for direct entry "
                f"with FlightLogic session {request.session_id[:15]}..."
            )

        return response
    except HotelSearchError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/book", response_model=HotelBookingResponse)
async def create_booking(
    request: HotelBookingRequest,
    service: HotelService = Depends(get_hotel_service),
) -> HotelBookingResponse:
    """Create a hotel booking.

    **PAYMENT REQUIRED**: This endpoint requires a successful payment before booking.
    The payment_intent_id must be included in the request.

    Flow:
    1. Frontend creates payment (Stripe: /api/payments/create-intent, Revolut: /api/revolut-payments/create-order)
    2. Frontend collects payment (Stripe.js or Revolut Checkout)
    3. Frontend calls this endpoint with payment_intent_id (Stripe pi_* or Revolut order UUID)
    4. Backend validates payment succeeded
    5. Backend creates booking with FlightLogic API

    Requires:
    - session_id: Internal session ID (will be swapped for FlightLogic session ID)
    - rate_basis_id: From room rates response
    - guest_info: Guest details for booking
    - payment_intent_id: Stripe PaymentIntent ID (pi_*) or Revolut order ID (UUID)

    Returns:
        Booking confirmation with confirmation number and booking details
    """
    try:
        # CRITICAL: request.session_id is our internal UUID
        # We need to look up the FlightLogic session ID from MongoDB
        from app.domains.booking_sessions import BookingSessionService
        from app.domains.payment import PaymentService
        from app.domains.revolut_payment import (
            RevolutPaymentService,
            RevolutPaymentValidationError,
        )

        internal_session_id = request.session_id
        payment_intent_id = request.payment_intent_id

        # Detect payment provider for validation, mark-used, and refund
        is_stripe = (
            payment_intent_id
            and payment_intent_id != "demo_payment_intent"
            and payment_intent_id.startswith("pi_")
        )
        is_revolut = (
            payment_intent_id
            and payment_intent_id != "demo_payment_intent"
            and not payment_intent_id.startswith("pi_")
            and "-" in payment_intent_id
            and len(payment_intent_id) == 36
        )

        # Validate payment if provided (required for hotel bookings)
        # Supports both Stripe (payment_intent_id) and Revolut (order_id)
        if payment_intent_id and payment_intent_id != "demo_payment_intent":
            logger.info(
                f"Validating payment {payment_intent_id} for hotel session {internal_session_id}"
            )
            if not service.current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User authentication required for payment validation",
                )
            # For multi-stay legs beyond leg 0, skip the "already used" check:
            # one Revolut/Stripe order intentionally covers multiple hotel legs.
            is_multistay_leg = (
                request.multistay_leg_index is not None
                and request.multistay_leg_index > 0
            )
            try:
                if is_stripe:
                    if not is_multistay_leg:
                        await PaymentService(
                            user_id=str(service.current_user.id)
                        ).check_payment_not_used(payment_intent_id)
                    await PaymentService(
                        user_id=str(service.current_user.id)
                    ).validate_payment_succeeded(payment_intent_id)
                    logger.info(
                        f"✅ Stripe payment validated for hotel session {internal_session_id}"
                    )
                elif is_revolut:
                    revolut_service = RevolutPaymentService(
                        user_id=str(service.current_user.id)
                    )
                    if not is_multistay_leg:
                        await revolut_service.check_payment_not_used(payment_intent_id)
                    await revolut_service.validate_payment_succeeded(payment_intent_id)
                    logger.info(
                        f"✅ Revolut payment validated for hotel session {internal_session_id}"
                    )
                else:
                    raise ValueError(
                        f"Unrecognized payment ID format: {payment_intent_id}"
                    )
            except RevolutPaymentValidationError as e:
                logger.error(f"Payment validation failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Payment validation failed: {e!s}",
                ) from e
            except Exception as e:
                logger.error(f"Payment validation failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Payment validation failed: {e!s}",
                ) from e
        else:
            logger.warning(
                f"Hotel booking session {internal_session_id} without payment validation"
            )

        # Get session data from MongoDB
        session_data = await BookingSessionService.get_session(
            session_id=internal_session_id
        )

        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session not found or expired",
            )

        # Get FlightLogic session ID (stored in data field)
        flightlogic_session_id = session_data.get("data", {}).get(
            "flightlogic_session_id"
        )
        if not flightlogic_session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FlightLogic session expired. Please search for hotels again.",
            )

        # Get validated rateBasisId from session (persisted by rate-rules endpoint)
        validated_rate_basis_id = session_data.get("data", {}).get(
            "validated_rate_basis_id"
        )

        # Replace internal session ID with FlightLogic session ID
        request_dict = request.model_dump()
        request_dict["session_id"] = flightlogic_session_id

        # Use validated rateBasisId from session if available
        if validated_rate_basis_id:
            request_dict["rate_basis_id"] = validated_rate_basis_id
            logger.info(
                f"Booking: Using validated rateBasisId {validated_rate_basis_id[:15]}... "
                f"from session {internal_session_id[:15]}..."
            )
        else:
            logger.warning(
                f"Booking: No validated rateBasisId in session {internal_session_id[:15]}..., "
                f"using rate_basis_id from request"
            )

        modified_request = HotelBookingRequest(**request_dict)

        logger.info(
            f"Booking: Swapped session ID {internal_session_id[:15]}... "
            f"→ FlightLogic {flightlogic_session_id[:15]}..."
        )

        # Snapshot for booking_events (session + client display fields). Computed for every
        # book attempt so demo/guest flows can persist list/profile fields when the booking
        # session owner is known, even without a JWT on this request.
        sess_inner = session_data.get("data") or {}
        search_params = sess_inner.get("search_params") or {}
        stay_ci, stay_co, stay_nights = hotel_stay_from_booking_details(
            {
                "check_in_date": search_params.get("check_in_date"),
                "check_out_date": search_params.get("check_out_date"),
                "checkin": search_params.get("checkin"),
                "checkout": search_params.get("checkout"),
            }
        )
        selected_hotel = sess_inner.get("selected_hotel") or {}
        merged_display = merge_session_and_client_hotel_display(
            selected_hotel, modified_request
        )
        hotel_image_url = merged_display.hotel_image_url
        hotel_name = merged_display.hotel_name
        hotel_city = merged_display.hotel_city
        hotel_address = merged_display.hotel_address
        hotel_latitude = merged_display.hotel_latitude
        hotel_longitude = merged_display.hotel_longitude

        raw_session_user_id = session_data.get("user_id")
        session_user_id_str = (
            str(raw_session_user_id).strip() if raw_session_user_id is not None else ""
        )
        booking_user_id: str | None = (
            str(service.current_user.id)
            if service.current_user
            else (
                session_user_id_str
                if session_user_id_str
                and session_user_id_str not in ("unknown", "direct_entry")
                else None
            )
        )

        # Create booking event before hotel book API (one event only)
        # For Revolut: use voya ref from transaction metadata (passed when creating order)
        voya_booking_reference: str | None = None
        voya_ref_for_event: str | None = None
        if is_revolut and payment_intent_id and service.current_user:
            revolut_repo = RevolutPaymentService(
                user_id=str(service.current_user.id)
            ).repository
            tx = await revolut_repo.get_transaction_by_order_id(payment_intent_id)
            if tx and getattr(tx, "voya_booking_reference", None):
                voya_ref_for_event = tx.voya_booking_reference
                logger.info(
                    "Using voya ref from Revolut metadata for booking event",
                    extra={"voya_booking_reference": voya_ref_for_event},
                )
        if not booking_user_id:
            logger.warning(
                "Skipping hotel booking_events row: no resolvable booking user "
                "(session user_id=%r, authenticated=%s). "
                "Use a logged-in session or a booking session whose user_id is a real user, "
                "not 'unknown' or 'direct_entry'.",
                raw_session_user_id,
                service.current_user is not None,
            )

        if booking_user_id:
            from app.domains.bookings import BookingService, CreateBookingEventRequest
            from app.domains.bookings.constants import TEMP_EXTERNAL_REF

            try:
                booking_service = BookingService(user_id=booking_user_id)
                hotel_event_payload: dict = {
                    "external_booking_reference": TEMP_EXTERNAL_REF,
                    "action": "BOOKED",
                    "event_type": "HOTEL",
                    "contact_email": modified_request.customer_email,
                    "payment_intent_id": modified_request.payment_intent_id,
                    "date_paid": datetime.now(UTC),
                    "voya_booking_reference": voya_ref_for_event,
                    "airline_pnr_code": None,
                    "airline_pnr_airline_code": None,
                    "airline_pnr_airline_name": None,
                    "airline_pnr_status": None,
                    "pnr": None,
                    "ticket_status": None,
                    "e_ticket_numbers": None,
                    "flight_leg_summaries": None,
                    "flight_segment_departure_dates": None,
                    "cancellation_policy_text": None,
                    "ticket_time_limit": None,
                    "departure_airport_iata": None,
                    "carrier_type": None,
                    "payload": None,
                    "amount": None,
                    "date_booked": None,
                    "hotel_image_url": hotel_image_url,
                    "hotel_name": hotel_name,
                    "hotel_city": hotel_city,
                    "hotel_address": hotel_address,
                    "hotel_latitude": hotel_latitude,
                    "hotel_longitude": hotel_longitude,
                    "hotel_check_in_date": stay_ci,
                    "hotel_check_out_date": stay_co,
                    "hotel_nights": stay_nights,
                }
                if modified_request.voucher_redemption_id:
                    hotel_event_payload["voucher_redemption_id"] = (
                        modified_request.voucher_redemption_id
                    )
                if modified_request.parent_voya_booking_reference:
                    hotel_event_payload["parent_voya_booking_reference"] = (
                        modified_request.parent_voya_booking_reference
                    )
                if modified_request.multistay_leg_index is not None:
                    hotel_event_payload["multistay_leg_index"] = (
                        modified_request.multistay_leg_index
                    )
                hotel_event_request = CreateBookingEventRequest.model_validate(
                    hotel_event_payload
                )
                hotel_event_response = await booking_service.create_booking(
                    hotel_event_request
                )
                voya_booking_reference = hotel_event_response.voya_booking_reference
                logger.info(
                    "Created hotel booking event before book API",
                    extra={"voya_booking_reference": voya_booking_reference},
                )
                request_dict["client_ref"] = voya_booking_reference
                modified_request = HotelBookingRequest(**request_dict)
                try:
                    dto_request = service.client.hotel_adapter.booking_request_to_dto(
                        modified_request
                    )
                    payload = dto_request.model_dump(by_alias=True)
                    await BookingService.set_booking_payload(
                        voya_booking_reference, payload
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to store hotel booking payload before API: %s", e
                    )
            except Exception as e:
                logger.exception(
                    "Failed to create hotel booking event before supplier API (booking may still proceed): %s",
                    e,
                )

        # Execute booking with auto-refund on failure
        try:
            booking_result = await service.create_booking(modified_request)

            # Mark payment as used for this booking (idempotency tracking)
            if (is_stripe or is_revolut) and payment_intent_id:
                try:
                    if is_stripe:
                        await PaymentService(
                            user_id=str(service.current_user.id)
                            if service.current_user
                            else None
                        ).mark_payment_used_for_booking(payment_intent_id)
                    else:
                        await RevolutPaymentService(
                            user_id=str(service.current_user.id)
                            if service.current_user
                            else None
                        ).mark_payment_used_for_booking(payment_intent_id)
                except Exception as mark_error:
                    # Log error but don't fail the booking (booking already succeeded)
                    logger.error(
                        f"Failed to mark payment {payment_intent_id} as used (non-critical): {mark_error}"
                    )

            # Pay-then-book: Revolut ORDER_COMPLETED may run before this route creates
            # booking_events with voucher_redemption_id, so webhook redemption can no-op.
            # Redeem after supplier success; idempotent if the webhook already redeemed.
            if voya_booking_reference and modified_request.voucher_redemption_id:
                from app.domains.discount.service import discount_service

                try:
                    await discount_service.redeem_voucher_on_payment(
                        booking_reference=voya_booking_reference
                    )
                except Exception as redeem_err:
                    logger.exception(
                        "[G2A voucher] redeem after successful hotel book failed: %s",
                        redeem_err,
                    )

            return booking_result

        except Exception as booking_error:
            # If booking fails after payment was validated, refund the customer
            if (is_stripe or is_revolut) and payment_intent_id:
                logger.error(
                    f"Hotel booking failed after payment validation for {payment_intent_id}. "
                    f"Initiating automatic refund. Error: {booking_error}"
                )
                try:
                    if is_stripe:
                        refund_id = await PaymentService(
                            user_id=str(service.current_user.id)
                            if service.current_user
                            else None
                        ).refund_payment(
                            payment_intent_id, reason="hotel_booking_failed"
                        )
                    else:
                        refund_id = await RevolutPaymentService(
                            user_id=str(service.current_user.id)
                            if service.current_user
                            else None
                        ).refund_payment(
                            payment_intent_id, reason="hotel_booking_failed"
                        )
                    logger.info(
                        f"✅ Automatic refund completed: {refund_id} for failed hotel booking"
                    )
                    # Include refund info in error message to user
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Hotel booking failed. Your payment has been automatically refunded (refund ID: {refund_id}). Please try again or contact support.",
                    ) from booking_error
                except HTTPException:
                    raise  # Re-raise our own HTTPException
                except Exception as refund_error:
                    logger.critical(
                        f"CRITICAL: Failed to refund payment {payment_intent_id} after hotel booking failure. "
                        f"Manual intervention required. Refund error: {refund_error}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Hotel booking failed and automatic refund failed. "
                        f"Please contact support immediately with payment ID: {payment_intent_id}",
                    ) from booking_error
            else:
                # No payment involved, just re-raise booking error
                raise

    except HotelBookingError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.get("/my-bookings", response_model=list[HotelMyBookingListItem])
async def get_my_hotel_bookings(
    _user: UserPublic = Depends(get_current_user()),
    service: HotelService = Depends(get_hotel_service),
    limit: int = Query(default=10, ge=1, le=100),
) -> list[HotelMyBookingListItem]:
    """List current user's hotel booking_events (newest first)."""
    try:
        return await service.get_user_bookings(limit)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.get("/session/{session_id}")
async def get_hotel_booking_session(session_id: str) -> dict:
    """Get hotel booking session data using session ID from MongoDB.

    This endpoint retrieves session data stored during the hotel selection process,
    including selected hotel details, search parameters, and user information.

    Args:
        session_id: Unique session identifier

    Returns:
        Session data including selected_hotel, search_params, and user_data

    Raises:
        HTTPException: 404 if session not found or expired
    """
    try:
        from app.domains.booking_sessions.service import BookingSessionService
        from app.domains.user.service import UserService

        # Get session data from MongoDB
        session = await BookingSessionService.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hotel booking session {session_id} not found or expired",
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
                        "phone": getattr(user, "phone", None),
                    }
            except Exception as user_error:
                logger.warning(f"Could not load user data: {user_error}")

        return {
            **session_data,
            "user_data": user_data,
            "session_id": session_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading hotel session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load session: {e!s}",
        ) from e


@router.post("/cancel", response_model=HotelCancelResponse)
async def cancel_booking(
    request: HotelCancelRequest,
    service: HotelService = Depends(get_hotel_service),
) -> HotelCancelResponse:
    """Cancel a hotel booking.

    Requires:
    - supplier_confirmation_num: Supplier confirmation number from booking response
    - reference_num: Reference number from booking response

    Returns:
        Cancellation confirmation with cancel reference number
    """
    try:
        return await service.cancel_booking(request)
    except HotelBookingError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/booking-details", response_model=HotelBookingDetailsResponse)
async def get_booking_details(
    request: HotelBookingDetailsRequest,
    service: HotelService = Depends(get_hotel_service),
) -> HotelBookingDetailsResponse:
    """Get complete hotel booking details.

    This API allows you to get complete booking details using the supplier
    confirmation number and reference number from the booking response.

    Requires:
    - supplier_confirmation_num: Supplier confirmation number from booking response
    - reference_num: Reference number from booking response

    Returns:
        Complete booking details including hotel information, dates, guests, etc.
    """
    try:
        return await service.get_booking_details(request)
    except HotelBookingError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/trip-details", response_model=HotelTripDetailsResponse)
async def get_hotel_trip_details(
    request: HotelTripDetailsRequest,
    service: HotelService = Depends(get_hotel_service),
) -> HotelTripDetailsResponse:
    """Get hotel booking details by VOYA reference.

    Resolves supplier refs from booking event, validates user ownership,
    then fetches complete booking details from supplier API.

    Used by the frontend booking details page (e.g. from email link).
    """
    try:
        return await service.get_trip_details(request)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e
    except BookingForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except HotelBookingError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


class HotelSearchRedirectRequest(BaseModel):
    """Request to generate redirect URL for full hotel search results."""

    destination_city: str = Field(
        ..., description="Destination city name", min_length=2
    )
    country: str | None = Field(None, description="Country name", min_length=2)
    check_in_date: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out_date: str = Field(..., description="Check-out date (YYYY-MM-DD)")
    rooms: int = Field(1, ge=1, le=5, description="Number of rooms")
    adults: int = Field(2, ge=1, le=9, description="Number of adults")
    children: int = Field(0, ge=0, le=9, description="Number of children")
    # Filter params (passed through to hotel-booker URL)
    price_min: float | None = Field(
        None, gt=0, description="Min price per night (gt=0: must be positive)"
    )
    price_max: float | None = Field(
        None, gt=0, description="Max price per night (gt=0: must be positive)"
    )
    min_rating: int | None = Field(None, ge=1, le=5, description="Minimum star rating")
    property_types: list[str] | None = Field(
        None, description="Property type(s) to include"
    )
    refundable_only: bool | None = Field(
        None, description="Only show refundable hotels"
    )
    required_facilities: list[str] | None = Field(
        None, description="Required facilities (ALL must be present)"
    )
    max_distance_km: float | None = Field(
        None,
        gt=0,
        description="Max distance from centre in km (gt=0: must be positive)",
    )
    locality: str | None = Field(
        None, description="Neighbourhood/locality to filter by"
    )


class HotelSearchRedirectResponse(BaseModel):
    """Response with redirect URL for hotel search."""

    redirect_url: str = Field(
        ..., description="URL to redirect user to for full search results"
    )


class HotelSelectionRequest(BaseModel):
    """Request to select a hotel from chat search results for booking."""

    session_id: str = Field(
        ...,
        description="FlightLogic session ID from hotel search (stored in localStorage)",
    )
    token_id: str = Field(..., description="Hotel token ID from search results")
    product_id: str = Field(..., description="Hotel product ID from search results")
    hotel_id: str = Field(
        ..., description="Hotel ID from search results (required for room-rates API)"
    )
    # Optional: hotel display info and search params for the Select rooms step in hotel-booker
    selected_hotel_display: dict | None = Field(
        default=None,
        description="Hotel display fields (hotel_name, address, city, hotel_rating, thumbnail_url, etc.)",
    )
    search_params: dict | None = Field(
        default=None,
        description="Search params (check_in_date, check_out_date, rooms, adults, children, destination_city, country)",
    )


class HotelSelectionResponse(BaseModel):
    """Response with redirect URL to hotel-booker for room selection."""

    redirect_url: str = Field(
        ..., description="URL to redirect user to hotel-booker with pre-selected hotel"
    )


@router.post("/search-redirect", response_model=HotelSearchRedirectResponse)
async def search_redirect(
    request: HotelSearchRedirectRequest,
    service: HotelService = Depends(get_hotel_service),
) -> HotelSearchRedirectResponse:
    """Generate redirect URL for full hotel search results.

    This endpoint generates a JWT auth token and returns a URL that redirects
    users to the hotel-booker UI with auto-search enabled, showing all available
    hotels (not just the curated 3-5 options from chat).
    """
    try:
        # Get current user ID (if authenticated)
        user_id = "unknown"
        if service.current_user:
            user_id = str(service.current_user.id)

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

        # Build URL with all search parameters (URL-encoded to handle special characters)
        url_params = [
            f"destination_city={quote(request.destination_city)}",
            f"check_in_date={quote(str(request.check_in_date))}",
            f"check_out_date={quote(str(request.check_out_date))}",
            f"rooms={quote(str(request.rooms))}",
            f"adults={quote(str(request.adults))}",
            f"children={quote(str(request.children))}",
            f"source={quote('chat_results')}",
            f"auto_search={quote('true')}",
            "initial_step=results",  # Hide search step; show results step (like flight-booker initial_step=select)
        ]

        # Add country if provided (URL-encoded)
        if request.country:
            url_params.insert(1, f"country={quote(request.country)}")

        # Add filter params if provided
        if request.price_min is not None:
            url_params.append(f"price_min={request.price_min}")
        if request.price_max is not None:
            url_params.append(f"price_max={request.price_max}")
        if request.min_rating is not None:
            url_params.append(f"min_rating={request.min_rating}")
        if request.property_types:
            url_params.append(
                f"property_types={quote(','.join(request.property_types))}"
            )
        if request.refundable_only:
            url_params.append("refundable_only=true")
        if request.required_facilities:
            url_params.append(
                f"required_facilities={quote(','.join(request.required_facilities))}"
            )
        if request.max_distance_km is not None:
            url_params.append(f"max_distance_km={request.max_distance_km}")
        if request.locality:
            url_params.append(f"locality={quote(request.locality)}")

        # Add auth token if generated
        if booking_token:
            url_params.append(f"auth_token={quote(booking_token)}")

        redirect_url = (
            f"{settings.BACKEND_URL}/dev/hotel-booker/index.html?{'&'.join(url_params)}"
        )

        logger.info(
            f"Generated search redirect URL for user {user_id} (destination={request.destination_city}, "
            f"check_in={request.check_in_date}, check_out={request.check_out_date}, rooms={request.rooms})"
        )

        return HotelSearchRedirectResponse(redirect_url=redirect_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate search redirect: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate search redirect: {e!s}",
        ) from e


@router.post("/select", response_model=HotelSelectionResponse)
async def select_hotel_for_booking(
    request: HotelSelectionRequest,
    service: HotelService = Depends(get_hotel_service),
) -> HotelSelectionResponse:
    """Select a hotel from chat search results and redirect to hotel-booker at Select rooms step.

    Creates a booking session (like flights/select) storing token_id, product_id,
    hotel_id, and FlightLogic session_id. Hotel-booker loads session via GET /hotels/session
    and shows the Select rooms step; room rates are fetched there (similar to revalidate for flights).

    Frontend sends session_id (FlightLogic search session) + token_id + product_id + optional hotel_id.
    """
    try:
        from app.domains.booking_sessions.service import BookingSessionService

        # Get current user ID (if authenticated)
        user_id = "unknown"
        if service.current_user:
            user_id = str(service.current_user.id)

        logger.info(
            f"User {user_id} selecting hotel for booking "
            f"(token_id={request.token_id[:20]}..., product_id={request.product_id[:20]}...)"
        )

        # Create internal booking session ID (like flights/select)
        booking_session_id = str(uuid.uuid4())
        hotel_id = request.hotel_id

        # selected_hotel: booking IDs + optional display fields for hotel-booker Select rooms step
        selected_hotel = {
            "token_id": request.token_id,
            "product_id": request.product_id,
            "hotel_id": hotel_id,
        }
        if request.selected_hotel_display:
            selected_hotel.update(request.selected_hotel_display)

        session_data = {
            "flightlogic_session_id": request.session_id,
            "token_id": request.token_id,
            "product_id": request.product_id,
            "hotel_id": hotel_id,
            "selected_hotel": selected_hotel,
            "status": "hotel_selected",
            "source": "api_select",
        }
        if request.search_params:
            search_params = dict(request.search_params)
            # Hotel-booker guest form requires room_configuration (array of {room_no, adults, children}).
            # Chat sends only rooms, adults, children — derive room_configuration when missing.
            if not search_params.get("room_configuration"):
                num_rooms = int(search_params.get("rooms") or 1)
                adults = int(search_params.get("adults") or 1)
                children = int(search_params.get("children") or 0)
                if num_rooms <= 1:
                    search_params["room_configuration"] = [
                        {"room_no": 1, "adults": adults, "children": children}
                    ]
                else:
                    # Distribute guests across rooms (equal split when no per-room breakdown)
                    adults_per = adults // num_rooms
                    children_per = children // num_rooms
                    remainder_a = adults % num_rooms
                    remainder_c = children % num_rooms
                    room_config = []
                    for i in range(num_rooms):
                        ra = 1 if i < remainder_a else 0
                        rc = 1 if i < remainder_c else 0
                        room_config.append(
                            {
                                "room_no": i + 1,
                                "adults": adults_per + ra,
                                "children": children_per + rc,
                            }
                        )
                    search_params["room_configuration"] = room_config
            session_data["search_params"] = search_params

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
            f"Created hotel booking session {booking_session_id} (user: {user_id})"
        )

        # Generate booking auth token (session_id in JWT = internal booking session)
        booking_token = None
        if user_id != "unknown" and service.current_user:
            try:
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

        # Redirect to hotel-booker with internal session_id; booker loads session and shows Select rooms step
        url_params = [
            f"session_id={quote(booking_session_id)}",
            "initial_step=rooms",
            "source=api",
        ]
        if booking_token:
            url_params.append(f"auth_token={quote(booking_token)}")

        redirect_url = (
            f"{settings.BACKEND_URL}/dev/hotel-booker/index.html?{'&'.join(url_params)}"
        )

        logger.info(
            f"Generated hotel selection redirect for session {booking_session_id} (user: {user_id})"
        )

        return HotelSelectionResponse(redirect_url=redirect_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to select hotel: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select hotel: {e!s}",
        ) from e


class MultistayLegSummary(BaseModel):
    """Summary of a single leg in a multi-stay hotel booking group."""

    voya_booking_reference: str
    external_booking_reference: str | None = None
    hotel_name: str | None = None
    hotel_city: str | None = None
    leg_index: int | None = None


class MultistayBookingGroupResponse(BaseModel):
    """Response with all legs of a multi-stay hotel booking group."""

    parent_voya_booking_reference: str | None = None
    legs: list[MultistayLegSummary] = Field(default_factory=list)


@router.get("/multistay-booking-context", response_model=MultistayBookingGroupResponse)
async def get_multistay_booking_context(
    voya_booking_reference: str = Query(
        ...,
        description="Any leg VOYA reference; returns the full multi-stay group when parent is set",
    ),
    service: HotelService = Depends(get_hotel_service),
) -> MultistayBookingGroupResponse:
    """Return multi-stay group id and all leg booking events for a multi-stay hotel booking."""
    try:
        if not service.current_user:
            raise InvalidTokenError("Authentication required")

        from bson import ObjectId
        from bson.errors import InvalidId

        from app.database import get_database

        user_id = str(service.current_user.id)
        db = await get_database()
        coll = db["booking_events"]

        base_doc = await coll.find_one(
            {"voya_booking_reference": voya_booking_reference},
            sort=[("timestamp", -1)],
        )
        if not base_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found",
            )

        # Ownership check: user_id stored as ObjectId or string
        doc_user_id = base_doc.get("user_id")
        try:
            user_oid = ObjectId(user_id)
            if doc_user_id != user_oid and str(doc_user_id) != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied",
                )
        except InvalidId:
            if str(doc_user_id) != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied",
                ) from None

        parent_ref = base_doc.get("parent_voya_booking_reference")

        def _doc_to_leg(doc: dict[str, object]) -> MultistayLegSummary:
            raw_leg_index = doc.get("multistay_leg_index")
            return MultistayLegSummary(
                voya_booking_reference=str(doc.get("voya_booking_reference") or ""),
                external_booking_reference=str(v)
                if (v := doc.get("external_booking_reference")) is not None
                else None,
                hotel_name=str(v) if (v := doc.get("hotel_name")) is not None else None,
                hotel_city=str(v) if (v := doc.get("hotel_city")) is not None else None,
                leg_index=int(raw_leg_index)
                if isinstance(raw_leg_index, (int, float, str))
                else None,
            )

        if not parent_ref:
            return MultistayBookingGroupResponse(
                parent_voya_booking_reference=None,
                legs=[_doc_to_leg(dict(base_doc))],
            )

        try:
            user_oid = ObjectId(user_id)
        except InvalidId:
            user_oid = None  # type: ignore[assignment]

        user_filter = {"$in": [user_oid, user_id]} if user_oid else user_id
        cursor = coll.find(
            {
                "user_id": user_filter,
                "event_type": "HOTEL",
                "parent_voya_booking_reference": parent_ref,
            }
        ).sort("timestamp", 1)
        raw_legs = await cursor.to_list(length=20)

        by_ref: dict[str, dict[str, object]] = {}
        for doc in raw_legs:
            ref = doc.get("voya_booking_reference") or ""
            if not ref:
                continue
            prev = by_ref.get(str(ref))
            ts = doc.get("timestamp")
            if prev is None:
                by_ref[str(ref)] = dict(doc)
            else:
                prev_ts = prev.get("timestamp")
                if (ts and prev_ts and ts >= prev_ts) or (ts and not prev_ts):
                    by_ref[str(ref)] = dict(doc)

        legs = sorted(
            [_doc_to_leg(d) for d in by_ref.values()],
            key=lambda x: (x.leg_index is None, x.leg_index or 0),
        )

        return MultistayBookingGroupResponse(
            parent_voya_booking_reference=parent_ref,
            legs=legs,
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get multistay booking context: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve booking group",
        ) from e
