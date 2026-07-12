"""Revolut payment API endpoints for Revolut integration.

This module provides endpoints for:
- Creating Revolut orders for flight bookings
- Retrieving transaction details
- Manual payout release (admin only)

Phase 1: Skeleton implementation. Full API integration will be in Phase 2.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.domains.auth.dependencies import require_admin, require_authenticated
from app.domains.revolut_payment import (
    RevolutOrderCreateRequest,
    RevolutOrderCreateResponse,
    RevolutOrderCreationError,
    RevolutPaymentService,
    RevolutPayoutReleaseError,
    RevolutPayoutReleaseRequest,
    RevolutPayoutReleaseResponse,
    RevolutTransactionResponse,
)
from app.domains.user.schemas import UserPublic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/revolut-payments", tags=["Revolut Payments"])


# Dependency injection
def get_revolut_payment_service(
    current_user: UserPublic = Depends(require_authenticated),
) -> RevolutPaymentService:
    """Get Revolut payment service with current user context.

    Args:
        current_user: Authenticated user from token

    Returns:
        RevolutPaymentService instance configured for current user
    """
    return RevolutPaymentService(
        user_id=str(current_user.id), current_user=current_user
    )


def get_admin_revolut_payment_service() -> RevolutPaymentService:
    """Get Revolut payment service for admin operations (no user context needed).

    Returns:
        RevolutPaymentService instance without user context
    """
    return RevolutPaymentService()


@router.get(
    "/existing-order/{voya_booking_reference}",
    response_model=RevolutOrderCreateResponse,
)
async def get_existing_revolut_order(
    voya_booking_reference: str,
    service: RevolutPaymentService = Depends(get_revolut_payment_service),
) -> RevolutOrderCreateResponse:
    """Get existing Revolut order for a booking if one exists.

    Used to reuse orders when user returns via email link.
    Returns 404 if no reusable order exists.

    Args:
        voya_booking_reference: VOYA booking reference
        service: RevolutPaymentService instance (injected)

    Returns:
        RevolutOrderCreateResponse with existing order details

    Raises:
        HTTPException 404: If no reusable order exists
    """
    existing_order = await service.get_existing_order(voya_booking_reference)

    if not existing_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No reusable Revolut order found for {voya_booking_reference}",
        )

    return existing_order


@router.post("/create-order", response_model=RevolutOrderCreateResponse)
async def create_revolut_order(
    request: RevolutOrderCreateRequest,
    service: RevolutPaymentService = Depends(get_revolut_payment_service),
) -> RevolutOrderCreateResponse:
    """Create Revolut order for flight booking.

    This endpoint is called by the frontend BEFORE booking creation.
    It returns a public_order_id that the frontend uses with Revolut Checkout SDK
    to collect payment information and confirm the payment.

    Flow:
    1. Frontend calls this endpoint with booking amount
    2. Backend creates Revolut order with 5% platform fee
    3. Frontend receives public_order_id
    4. Frontend shows Revolut Checkout payment form
    5. User completes payment
    6. Frontend calls /flights/book-from-session with order_id

    Args:
        request: Revolut order creation request
        service: RevolutPaymentService instance (injected)

    Returns:
        RevolutOrderCreateResponse with public_order_id for Revolut Checkout SDK

    Raises:
        HTTPException 503: If Revolut API fails
    """
    try:
        return await service.create_payment_intent(request)
    except RevolutOrderCreationError as e:
        logger.error(f"Revolut order creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        ) from e


@router.get("/transaction/{order_id}", response_model=RevolutTransactionResponse)
async def get_revolut_transaction(
    order_id: str,
    service: RevolutPaymentService = Depends(get_revolut_payment_service),
) -> RevolutTransactionResponse:
    """Get transaction details by Revolut order ID.

    Args:
        order_id: Revolut order ID
        service: RevolutPaymentService instance (injected)

    Returns:
        Transaction details

    Raises:
        HTTPException 404: If transaction not found
    """
    try:
        return await service.get_transaction_by_payment_intent(order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.get(
    "/booking/{booking_reference}", response_model=list[RevolutTransactionResponse]
)
async def get_revolut_transactions_by_booking(
    booking_reference: str,
    service: RevolutPaymentService = Depends(get_revolut_payment_service),
) -> list[RevolutTransactionResponse]:
    """Get all Revolut transactions for a booking reference.

    This endpoint is used to check if a booking already has a successful payment,
    preventing duplicate payments.

    Args:
        booking_reference: Voya booking reference (VOYA-xxx)
        service: RevolutPaymentService instance (injected)

    Returns:
        List of transactions for the booking (may be empty)
    """
    return await service.get_transactions_by_booking(booking_reference)


@router.post("/payouts/release", response_model=RevolutPayoutReleaseResponse)
async def release_revolut_payout(
    request: RevolutPayoutReleaseRequest,
    admin_user: UserPublic = Depends(require_admin),
    service: RevolutPaymentService = Depends(get_admin_revolut_payment_service),
) -> RevolutPayoutReleaseResponse:
    """Manually release payout to supplier (admin only).

    This endpoint triggers a payout from the platform account
    to the supplier Revolut merchant account.

    **Admin only** - Requires admin role.

    Args:
        request: Payout release request
        admin_user: Authenticated admin user
        service: RevolutPaymentService instance (injected)

    Returns:
        Payout release confirmation

    Raises:
        HTTPException 404: If transaction not found
        HTTPException 400: If payment not succeeded or already paid out
        HTTPException 503: If Revolut payout fails
    """
    try:
        return await service.release_payout(request, admin_user_id=str(admin_user.id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except RevolutPayoutReleaseError as e:
        logger.error(f"Revolut payout release failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
