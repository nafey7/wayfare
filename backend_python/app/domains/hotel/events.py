"""Hotel domain event handlers - sends emails and notifications."""

import logging
from typing import TYPE_CHECKING, Any

from app.domains.email import EmailService, EmailType

if TYPE_CHECKING:
    from app.domains.hotel.service import HotelService
    from app.domains.user import UserService

logger = logging.getLogger(__name__)


def _get_user_service() -> "type[UserService]":
    """Lazy import UserService to avoid circular imports."""
    from app.domains.user import UserService

    return UserService


def _get_hotel_service() -> "type[HotelService]":
    """Lazy import HotelService to avoid circular imports."""
    from app.domains.hotel.service import HotelService

    return HotelService


class HotelEventHandler:
    """Handle hotel domain events - sends emails and notifications."""

    # ==============================================================
    # BOOKING EVENTS
    # ==============================================================

    @staticmethod
    async def handle_booking_confirmed(
        user_id: str,
        external_booking_reference: str,
        booking_details: dict[str, Any],
        voya_booking_reference: str | None = None,
        booking_request: Any | None = None,
        reference_num: str | None = None,
    ) -> None:
        """Handle hotel booking confirmation - send confirmation email.

        Args:
            user_id: User ID
            external_booking_reference: FlightLogic confirmation number (supplier_confirmation_num)
            booking_details: Booking details dict
            voya_booking_reference: VOYA booking reference
            booking_request: HotelBookingRequest with guest information
            reference_num: FlightLogic reference number
        """
        try:
            # Use VOYA reference for email display, fallback to external if missing
            display_reference = voya_booking_reference or external_booking_reference

            # Enrich booking_details with hotel_name from booking details API if missing
            enriched_booking_details = booking_details.copy()
            if (
                not enriched_booking_details.get("hotel_name")
                and external_booking_reference
                and reference_num
            ):
                try:
                    from app.domains.hotel.schemas import HotelBookingDetailsRequest

                    logger.info(
                        f"🔍 [Hotel Booking Email] hotel_name missing, calling booking details API for {display_reference}"
                    )

                    # Create hotel service instance (without user context for internal use)
                    hotel_service = _get_hotel_service()(current_user=None)
                    details_request = HotelBookingDetailsRequest(
                        supplier_confirmation_num=external_booking_reference,
                        reference_num=reference_num,
                        user_id=None,
                        user_password=None,
                        access=None,
                        ip_address=None,
                    )

                    details_response = await hotel_service.get_booking_details(
                        details_request
                    )

                    if details_response and details_response.booking_details:
                        hotel_name = (
                            details_response.booking_details.get("hotel_name")
                            or details_response.booking_details.get("hotelName")
                            or details_response.booking_details.get("name")
                        )
                        if hotel_name:
                            enriched_booking_details["hotel_name"] = hotel_name
                            logger.info(
                                f"✅ [Hotel Booking Email] Added hotel_name '{hotel_name}' from booking details API"
                            )
                        else:
                            logger.debug(
                                "[Hotel Booking Email] No hotel_name found in booking details API response (non-critical)"
                            )
                            enriched_booking_details["hotel_name"] = "Your Hotel"
                    else:
                        logger.warning(
                            "⚠️ [Hotel Booking Email] No booking_details in API response"
                        )
                        enriched_booking_details["hotel_name"] = "Your Hotel"
                except Exception as api_error:
                    logger.warning(
                        f"⚠️ [Hotel Booking Email] Could not get hotel_name from booking details API: {api_error} (non-critical)"
                    )
                    enriched_booking_details["hotel_name"] = "Your Hotel"

            elif enriched_booking_details.get("hotel_name"):
                logger.info(
                    f"✅ [Hotel Booking Email] hotel_name already present: '{enriched_booking_details.get('hotel_name')}'"
                )

            # Ensure hotel_name is always set for email/PDF generation
            if not enriched_booking_details.get("hotel_name"):
                enriched_booking_details["hotel_name"] = "Your Hotel"

            # Try to get user from database first
            user = None
            try:
                user = await _get_user_service().get_user_public(user_id)
                logger.info(f"User found: {user.email}")
            except Exception as user_error:
                logger.warning(f"Failed to get user {user_id}: {user_error}")

            if user:
                # Determine recipient email based on booking flow type
                # Normal booking flow: use customer_email from booking request
                # Session-based flow: use authenticated user's email
                recipient_email = user.email  # Default to user email

                if (
                    booking_request
                    and hasattr(booking_request, "customer_email")
                    and booking_request.customer_email
                ):
                    # Normal booking flow - use customer email from request
                    recipient_email = booking_request.customer_email
                    logger.info(
                        f"Using customer_email: {recipient_email} (normal booking flow)"
                    )
                else:
                    # Session-based flow - use authenticated user email
                    logger.info(
                        f"Using user email: {recipient_email} (session-based flow)"
                    )

                await EmailService.send_email(
                    email_type=EmailType.BOOKING_CONFIRMATION,
                    recipient_email=recipient_email,
                    context={
                        "user_name": user.first_name or "User",
                        "user_id": user_id,
                        "voya_booking_reference": display_reference,  # VOYA reference
                        "external_booking_reference": external_booking_reference,  # FlightLogic supplier_confirmation_num
                        "reference_num": reference_num,  # FlightLogic reference_num
                        "booking_details": enriched_booking_details,
                    },
                    booking_request=booking_request,  # Guest information
                )
                logger.info(
                    f"Hotel booking confirmation email sent to {recipient_email} with reference {display_reference}"
                )
                if voya_booking_reference:
                    try:
                        from app.domains.bookings.service import BookingService

                        await BookingService.update_booking_dates_and_flags(
                            voya_booking_reference,
                            confirmation_email_sent=True,
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to set confirmation_email_sent for {voya_booking_reference}: {e}"
                        )
            else:
                # Fallback: Try to use customer email from booking request
                guest_email = None
                if (
                    booking_request
                    and hasattr(booking_request, "customer_email")
                    and booking_request.customer_email
                ):
                    guest_email = booking_request.customer_email
                    logger.info(
                        f"Using customer email from booking request: {guest_email}"
                    )

                if guest_email:
                    await EmailService.send_email(
                        email_type=EmailType.BOOKING_CONFIRMATION,
                        recipient_email=guest_email,
                        context={
                            "user_name": "Guest",
                            "user_id": user_id,
                            "voya_booking_reference": display_reference,
                            "external_booking_reference": external_booking_reference,
                            "reference_num": reference_num,
                            "booking_details": enriched_booking_details,
                        },
                        booking_request=booking_request,
                    )
                    logger.info(
                        f"Hotel booking confirmation email sent to guest email: {guest_email} with reference {display_reference}"
                    )
                    if voya_booking_reference:
                        try:
                            from app.domains.bookings.service import BookingService

                            await BookingService.update_booking_dates_and_flags(
                                voya_booking_reference,
                                confirmation_email_sent=True,
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to set confirmation_email_sent for {voya_booking_reference}: {e}"
                            )
                else:
                    # Final fallback - send to dev email
                    from app.domains.email.constants import DEV_EMAIL_RECIPIENT

                    await EmailService.send_email(
                        email_type=EmailType.BOOKING_CONFIRMATION,
                        recipient_email=DEV_EMAIL_RECIPIENT,
                        context={
                            "user_name": "Test User",
                            "user_id": user_id,
                            "voya_booking_reference": display_reference,
                            "external_booking_reference": external_booking_reference,
                            "reference_num": reference_num,
                            "booking_details": enriched_booking_details,
                        },
                        booking_request=booking_request,
                    )
                    logger.warning(
                        f"No user/guest email found - Hotel booking confirmation sent to dev email with reference {display_reference}"
                    )
                    if voya_booking_reference:
                        try:
                            from app.domains.bookings.service import BookingService

                            await BookingService.update_booking_dates_and_flags(
                                voya_booking_reference,
                                confirmation_email_sent=True,
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to set confirmation_email_sent for {voya_booking_reference}: {e}"
                            )

        except Exception as e:
            logger.error(f"Failed to send hotel booking confirmation email: {e}")
            # Don't raise - email failures shouldn't block booking

    @staticmethod
    async def handle_booking_failed(
        user_id: str,
        error_message: str,
        booking_request: Any | None = None,
    ) -> None:
        """Handle failed hotel booking - send notification email.

        Args:
            user_id: User ID
            error_message: Error message describing why booking failed
            booking_request: HotelBookingRequest with booking details
        """
        try:
            # Try to get user from database
            user = None
            try:
                user = await _get_user_service().get_user_public(user_id)
            except Exception as user_error:
                logger.warning(f"Failed to get user {user_id}: {user_error}")

            if user:
                recipient_email = user.email

                # Try to extract hotel details from request
                hotel_details = {}
                if booking_request:
                    hotel_details = {
                        "session_id": getattr(booking_request, "session_id", "N/A"),
                        "rate_basis_id": getattr(
                            booking_request, "rate_basis_id", "N/A"
                        )[:50],
                    }

                await EmailService.send_email(
                    email_type=EmailType.BOOKING_CANCELLED,  # Use BOOKING_CANCELLED for failures
                    recipient_email=recipient_email,
                    context={
                        "user_name": user.first_name or "User",
                        "error_message": error_message,
                        "booking_type": "hotel",
                        "booking_details": hotel_details,
                    },
                )
                logger.info(
                    f"Hotel booking failure notification sent to {recipient_email}"
                )

        except Exception as e:
            logger.error(f"Failed to send hotel booking failure email: {e}")
            # Don't raise - email failures shouldn't block error handling
