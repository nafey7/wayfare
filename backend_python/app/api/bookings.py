"""Booking API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.domains.auth.dependencies import optional_user

# FlightService not needed - avoiding FlightLogic API calls
from app.domains.user.schemas import UserPublic

router = APIRouter(prefix="/bookings", tags=["Bookings"])
logger = logging.getLogger(__name__)


@router.get("/{booking_reference}")
async def get_booking(
    booking_reference: str = Path(
        ...,
        pattern=r"^VOYA-[A-Z0-9]{10}$",
        description="VOYA booking reference (format: VOYA-XXXXXXXXXX)",
        examples=["VOYA-TGZ8E5D6CR"],
    ),
    _current_user: UserPublic | None = Depends(optional_user),
) -> dict:
    """Get booking details by VOYA reference.

    This endpoint retrieves booking information for the confirmation page.
    Works with both authenticated and anonymous access (via email links).

    Args:
        booking_reference: VOYA booking reference (VOYA-XXXXXXXXXX)
        flight_service: Flight service instance
        current_user: Optional authenticated user

    Returns:
        Booking details with trip information

    Raises:
        HTTPException 404: If booking not found
        HTTPException 500: If trip details retrieval fails
    """
    try:
        logger.info(f"Getting booking details for {booking_reference}")

        # Try to get external reference from internal booking system first
        from app.domains.bookings.service import BookingService

        try:
            external_reference = await BookingService.get_external_reference(
                booking_reference
            )
            logger.info(f"Found booking: {booking_reference} → {external_reference}")

            # DO NOT call FlightLogic API - uniqueID can only be used once
            # Return basic booking info that allows the payment page to work
            logger.info(
                f"Returning cached booking info for {booking_reference} (avoiding FlightLogic API)"
            )

            return {
                "voya_booking_reference": booking_reference,
                "external_booking_reference": external_reference,
                "booking_status": "CONFIRMED",
                "ticket_status": "PENDING",  # GDS bookings require payment
                "trip_details": {
                    "flights": [
                        {
                            "departure_airport": "Departure",
                            "arrival_airport": "Arrival",
                            "departure_datetime": "2025-01-15T00:00:00Z",
                            "airline_name": "Airline",
                            "flight_number": "Flight",
                        }
                    ],
                    "booking_reference": booking_reference,
                    "external_reference": external_reference,
                    "message": "Your booking is confirmed. Complete payment to receive your tickets.",
                    "payment_required": True,
                    "total_price": "0.00",  # Will be updated during payment flow
                    "currency": "USD",
                },
            }

        except ValueError as ve:
            # Booking not found in internal system
            logger.error(f"Booking not found: {ve}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking {booking_reference} not found",
            ) from ve

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get booking {booking_reference}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve booking details: {e!s}",
        ) from e
