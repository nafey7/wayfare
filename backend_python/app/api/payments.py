"""Payment API endpoints for Stripe integration.

This module provides endpoints for:
- Creating payment intents for flight bookings
- Retrieving transaction details
- Manual payout release (admin only)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.domains.auth.dependencies import require_admin, require_authenticated
from app.domains.payment import (
    BookingExpiryCheckRequest,
    BookingExpiryCheckResponse,
    PaymentIntentCreateRequest,
    PaymentIntentCreateResponse,
    PaymentIntentCreationError,
    PaymentService,
    PayoutReleaseError,
    PayoutReleaseRequest,
    PayoutReleaseResponse,
    TransactionResponse,
)
from app.domains.user.schemas import UserPublic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])


# Dependency injection
def get_payment_service(
    current_user: UserPublic = Depends(require_authenticated),
) -> PaymentService:
    """Get payment service with current user context.

    Args:
        current_user: Authenticated user from token

    Returns:
        PaymentService instance configured for current user
    """
    return PaymentService(user_id=str(current_user.id))


def get_admin_payment_service() -> PaymentService:
    """Get payment service for admin operations (no user context needed).

    Returns:
        PaymentService instance without user context
    """
    return PaymentService()


@router.get(
    "/existing-intent/{voya_booking_reference}",
    response_model=PaymentIntentCreateResponse,
)
async def get_existing_payment_intent(
    voya_booking_reference: str,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentIntentCreateResponse:
    """Get existing payment intent for a booking if one exists.

    Used to reuse payment intents when user returns via email link.
    Returns 404 if no reusable payment intent exists.

    Args:
        voya_booking_reference: VOYA booking reference
        service: PaymentService instance (injected)

    Returns:
        PaymentIntentCreateResponse with existing payment intent details

    Raises:
        HTTPException 404: If no reusable payment intent exists
    """
    existing_intent = await service.get_existing_payment_intent(voya_booking_reference)

    if not existing_intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No reusable payment intent found for {voya_booking_reference}",
        )

    return existing_intent


@router.post("/create-intent", response_model=PaymentIntentCreateResponse)
async def create_payment_intent(
    request: PaymentIntentCreateRequest,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentIntentCreateResponse:
    """Create Stripe payment intent for booking.

    This endpoint is called by the frontend BEFORE booking creation.
    It returns a client_secret that the frontend uses with Stripe.js
    to collect payment information and confirm the payment.

    Platform fees:
    - Flights: 5% platform fee
    - Hotels: 10.5% commission

    Flow:
    1. Frontend calls this endpoint with booking amount and booking_type
    2. Backend creates Stripe payment intent with appropriate platform fee
    3. Frontend receives client_secret
    4. Frontend shows Stripe payment form
    5. User completes payment
    6. Frontend calls booking endpoint with payment_intent_id

    Args:
        request: Payment intent creation request
        service: PaymentService instance (injected)

    Returns:
        PaymentIntentCreateResponse with client_secret for Stripe.js

    Raises:
        HTTPException 503: If Stripe API fails
    """
    try:
        return await service.create_payment_intent(request)
    except PaymentIntentCreationError as e:
        logger.error(f"Payment intent creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get("/transaction/{payment_intent_id}", response_model=TransactionResponse)
async def get_transaction(
    payment_intent_id: str,
    service: PaymentService = Depends(get_payment_service),
) -> TransactionResponse:
    """Get transaction details by Stripe payment intent ID.

    Args:
        payment_intent_id: Stripe payment intent ID (pi_xxx)
        service: PaymentService instance (injected)

    Returns:
        Transaction details

    Raises:
        HTTPException 404: If transaction not found
    """
    try:
        return await service.get_transaction_by_payment_intent(payment_intent_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get("/booking/{booking_reference}", response_model=list[TransactionResponse])
async def get_transactions_by_booking(
    booking_reference: str,
    service: PaymentService = Depends(get_payment_service),
) -> list[TransactionResponse]:
    """Get all transactions for a booking reference.

    This endpoint is used to check if a booking already has a successful payment,
    preventing duplicate payments.

    Args:
        booking_reference: Voya booking reference (VOYA-xxx)
        service: PaymentService instance (injected)

    Returns:
        List of transactions for the booking (may be empty)
    """
    return await service.get_transactions_by_booking(booking_reference)


@router.post("/check-booking-expiry", response_model=BookingExpiryCheckResponse)
async def check_booking_expiry(
    request: BookingExpiryCheckRequest,
    service: PaymentService = Depends(get_payment_service),
) -> BookingExpiryCheckResponse:
    """Check if booking has expired before confirming payment.

    This endpoint should be called by the frontend BEFORE calling
    stripe.confirmCardPayment() to prevent charging users for expired bookings.

    The frontend should call this endpoint when the user clicks the Pay button,
    and only proceed with Stripe payment confirmation if is_valid is True.

    Args:
        request: Booking expiry check request
        service: PaymentService instance (injected)

    Returns:
        BookingExpiryCheckResponse indicating if booking is still valid
    """
    return await service.check_booking_expiry(request)


@router.post("/payouts/release", response_model=PayoutReleaseResponse)
async def release_payout(
    request: PayoutReleaseRequest,
    admin_user: UserPublic = Depends(require_admin),
    service: PaymentService = Depends(get_admin_payment_service),
) -> PayoutReleaseResponse:
    """Manually release payout to supplier (admin only).

    This endpoint triggers a transfer from the platform account
    to the FlightLogic Stripe Connect account.

    **Admin only** - Requires admin role.

    Args:
        request: Payout release request
        admin_user: Authenticated admin user
        service: PaymentService instance (injected)

    Returns:
        Payout release confirmation

    Raises:
        HTTPException 404: If transaction not found
        HTTPException 400: If payment not succeeded or already paid out
        HTTPException 503: If Stripe transfer fails
    """
    try:
        return await service.release_payout(request, admin_user_id=str(admin_user.id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except PayoutReleaseError as e:
        logger.error(f"Payout release failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
