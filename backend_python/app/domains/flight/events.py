"""Flight domain event handlers - simple and clean."""

import logging
from typing import TYPE_CHECKING, Any

from app.domains.email import EmailService, EmailType

if TYPE_CHECKING:
    from app.domains.user import UserService

logger = logging.getLogger(__name__)


def _get_user_service() -> "type[UserService]":
    """Lazy import UserService to avoid circular imports."""
    from app.domains.user import UserService

    return UserService


class FlightEventHandler:
    """Handle flight domain events - sends emails and notifications."""

    # ==============================================================
    # BOOKING EVENTS
    # ==============================================================

    @staticmethod
    async def handle_booking_confirmed(
        user_id: str,
        external_booking_reference: str,
        booking_details: dict[str, Any],
        voya_booking_reference: str | None = None,
        revalidate_response: Any | None = None,
        booking_request: Any | None = None,
        trip_details: Any | None = None,
        booking_response_pnr: str | None = None,
        cancellation_policy_text: str | None = None,
    ) -> None:
        """Handle booking confirmation - send confirmation email with VOYA reference and PDF attachment.

        Args:
            user_id: User ID
            external_booking_reference: FlightLogic booking reference
            booking_details: Booking details dict
            voya_booking_reference: VOYA booking reference
            revalidate_response: FlightRevalidateResponse with fare itinerary details
            booking_request: FlightBookingRequest with passenger information
            trip_details: TripDetailsResponse for PDF generation (used after ticketing)
            booking_response_pnr: PNR code from booking response (if available)
        """
        try:
            # Use VOYA reference for email display, fallback to external if missing
            display_reference = voya_booking_reference or external_booking_reference

            # Try to get user from database first
            user = None
            try:
                user = await _get_user_service().get_user_public(user_id)
                logger.info(f"User found: {user.email}")
            except Exception as user_error:
                logger.warning(f"Failed to get user {user_id}: {user_error}")

            if user:
                # Determine recipient email based on booking flow type
                # Normal booking flow: use contact_information.email from booking request
                # Session-based flow: use authenticated user's email
                recipient_email = (
                    user.email
                )  # Default to user email (session-based flow)

                if (
                    booking_request
                    and hasattr(booking_request, "contact_information")
                    and booking_request.contact_information
                    and booking_request.contact_information.email
                ):
                    # Normal booking flow - use contact information email
                    recipient_email = booking_request.contact_information.email
                    logger.info(
                        f"Using contact_information email: {recipient_email} (normal booking flow)"
                    )
                else:
                    # Session-based flow - use authenticated user email
                    logger.info(
                        f"Using user email: {recipient_email} (session-based flow)"
                    )

                # Determine if this is an LCC booking (tickets already issued)
                # LCC bookings have trip_details provided (tickets issued immediately)
                # GDS bookings have trip_details=None (tickets issued after payment)
                is_lcc_booking = trip_details is not None
                tickets_issued = is_lcc_booking

                # For LCC bookings, fetch cancellation_policy_text from DB if not provided
                cancellation_policy_for_email = cancellation_policy_text
                if (
                    is_lcc_booking
                    and not cancellation_policy_for_email
                    and voya_booking_reference
                ):
                    try:
                        from app.domains.bookings.service import BookingService

                        booking_event = (
                            await BookingService.get_latest_booking_by_voya_reference(
                                voya_booking_reference
                            )
                        )
                        if booking_event and booking_event.cancellation_policy_text:
                            cancellation_policy_for_email = (
                                booking_event.cancellation_policy_text
                            )
                            logger.info(
                                f"Retrieved cancellation_policy_text from DB for LCC booking (length: {len(cancellation_policy_for_email)})"
                            )
                    except Exception as db_error:
                        logger.debug(
                            f"Failed to retrieve cancellation_policy_text from DB for LCC booking: {db_error}"
                        )

                # GDS skips BOOKING_CONFIRMATION: payment runs automatically after booking API; that email would prompt "Proceed to Checkout".
                if is_lcc_booking:
                    await EmailService.send_email(
                        email_type=EmailType.BOOKING_CONFIRMATION,
                        recipient_email=recipient_email,
                        context={
                            "user_name": user.first_name or "User",
                            "user_id": user_id,  # Include user_id for auth token generation
                            "tickets_issued": tickets_issued,  # True for LCC (tickets already issued), False for GDS
                            "voya_booking_reference": display_reference,  # VOYA reference
                            "external_booking_reference": external_booking_reference,  # FlightLogic reference
                            "booking_details": booking_details,
                            "booking_response_pnr": booking_response_pnr,  # PNR from booking response
                            "cancellation_policy_text": cancellation_policy_for_email,  # Cancellation policy from frontend/DB
                        },
                        revalidate_response=revalidate_response,  # Fare itinerary details
                        booking_request=booking_request,  # Passenger information
                        trip_details=trip_details,  # PDF auto-generated if provided (after ticketing)
                    )
                    logger.info(
                        f"Booking confirmation email sent to {recipient_email} with reference {display_reference}"
                    )
                    # LCC: Flight Booking Confirmation email sent -> set confirmation_email_sent
                    if tickets_issued and voya_booking_reference:
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
                customer_email = None
                if (
                    booking_request
                    and hasattr(booking_request, "pax_info")
                    and hasattr(booking_request.pax_info, "customer_email")
                ):
                    customer_email = booking_request.pax_info.customer_email
                    logger.info(
                        f"Using customer email from booking request: {customer_email}"
                    )

                if customer_email:
                    # Determine if this is an LCC booking (tickets already issued)
                    is_lcc_booking = trip_details is not None
                    tickets_issued = is_lcc_booking

                    # For LCC bookings, fetch cancellation_policy_text from DB if not provided
                    cancellation_policy_for_email = cancellation_policy_text
                    if (
                        is_lcc_booking
                        and not cancellation_policy_for_email
                        and voya_booking_reference
                    ):
                        try:
                            from app.domains.bookings.service import BookingService

                            booking_event = await BookingService.get_latest_booking_by_voya_reference(
                                voya_booking_reference
                            )
                            if booking_event and booking_event.cancellation_policy_text:
                                cancellation_policy_for_email = (
                                    booking_event.cancellation_policy_text
                                )
                                logger.info(
                                    f"Retrieved cancellation_policy_text from DB for LCC booking (length: {len(cancellation_policy_for_email)})"
                                )
                        except Exception as db_error:
                            logger.debug(
                                f"Failed to retrieve cancellation_policy_text from DB for LCC booking: {db_error}"
                            )

                    if is_lcc_booking:
                        await EmailService.send_email(
                            email_type=EmailType.BOOKING_CONFIRMATION,
                            recipient_email=customer_email,
                            context={
                                "user_name": "Customer",
                                "user_id": user_id,  # Include user_id for auth token generation
                                "tickets_issued": tickets_issued,  # True for LCC (tickets already issued), False for GDS
                                "voya_booking_reference": display_reference,  # VOYA reference
                                "external_booking_reference": external_booking_reference,  # FlightLogic reference
                                "booking_details": booking_details,
                                "booking_response_pnr": booking_response_pnr,  # PNR from booking response
                                "cancellation_policy_text": cancellation_policy_for_email,  # Cancellation policy from frontend/DB
                            },
                            revalidate_response=revalidate_response,  # Fare itinerary details
                            booking_request=booking_request,  # Passenger information
                            trip_details=trip_details,  # PDF auto-generated if provided (after ticketing)
                        )
                        logger.info(
                            f"Booking confirmation email sent to customer email: {customer_email} with reference {display_reference}"
                        )
                        if tickets_issued and voya_booking_reference:
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

                    # Determine if this is an LCC booking (tickets already issued)
                    is_lcc_booking = trip_details is not None
                    tickets_issued = is_lcc_booking

                    # For LCC bookings, fetch cancellation_policy_text from DB if not provided
                    cancellation_policy_for_email = cancellation_policy_text
                    if (
                        is_lcc_booking
                        and not cancellation_policy_for_email
                        and voya_booking_reference
                    ):
                        try:
                            from app.domains.bookings.service import BookingService

                            booking_event = await BookingService.get_latest_booking_by_voya_reference(
                                voya_booking_reference
                            )
                            if booking_event and booking_event.cancellation_policy_text:
                                cancellation_policy_for_email = (
                                    booking_event.cancellation_policy_text
                                )
                                logger.info(
                                    f"Retrieved cancellation_policy_text from DB for LCC booking (length: {len(cancellation_policy_for_email)})"
                                )
                        except Exception as db_error:
                            logger.debug(
                                f"Failed to retrieve cancellation_policy_text from DB for LCC booking: {db_error}"
                            )

                    if is_lcc_booking:
                        await EmailService.send_email(
                            email_type=EmailType.BOOKING_CONFIRMATION,
                            recipient_email=DEV_EMAIL_RECIPIENT,
                            context={
                                "user_name": "Test User",
                                "user_id": user_id,  # Include user_id for auth token generation
                                "tickets_issued": tickets_issued,  # True for LCC (tickets already issued), False for GDS
                                "voya_booking_reference": display_reference,  # VOYA reference
                                "external_booking_reference": external_booking_reference,  # FlightLogic reference
                                "booking_details": booking_details,
                                "booking_response_pnr": booking_response_pnr,  # PNR from booking response
                                "cancellation_policy_text": cancellation_policy_for_email,  # Cancellation policy from frontend/DB
                            },
                            revalidate_response=revalidate_response,  # Fare itinerary details
                            booking_request=booking_request,  # Passenger information
                            trip_details=trip_details,  # PDF auto-generated if provided (after ticketing)
                        )
                        logger.info(
                            f"Booking confirmation email sent to dev email: {DEV_EMAIL_RECIPIENT}"
                        )
                        if tickets_issued and voya_booking_reference:
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
            logger.warning(f"Failed to send booking confirmation email: {e}")

    # ==============================================================
    # TICKET EVENTS
    # ==============================================================

    @staticmethod
    async def handle_tickets_issued(
        user_id: str,
        external_booking_reference: str,
        ticket_numbers: list[str],
        voya_booking_reference: str | None = None,
        trip_details: Any | None = None,
        cancellation_policy_text: str | None = None,
    ) -> None:
        """Handle ticket issuance - send email with VOYA reference and e-ticket PDF attachment.

        Args:
            user_id: User ID
            external_booking_reference: FlightLogic booking reference
            ticket_numbers: List of ticket numbers
            voya_booking_reference: VOYA booking reference
            trip_details: TripDetailsResponse for PDF generation
        """
        try:
            user = await _get_user_service().get_user_public(user_id)

            # Use VOYA reference for display, fallback to external if missing
            display_reference = voya_booking_reference or external_booking_reference

            # Use same email routing logic as booking confirmation
            # Priority: stored contact_email (from original booking) > user.email (fallback)
            recipient_email = user.email if user else None  # Fallback to user email

            # Look up stored contact email and cancellation policy from the original booking
            # Only retrieve from DB if not already provided as parameter
            if not voya_booking_reference:
                logger.warning(
                    "⚠️ voya_booking_reference is required for ticket issuance."
                )
            else:
                try:
                    from app.domains.bookings.service import BookingService

                    # Use VOYA reference for lookup (more direct than external reference)
                    booking_response = (
                        await BookingService.get_latest_booking_by_voya_reference(
                            voya_booking_reference
                        )
                    )

                    # Debug: Log what we found in the booking
                    if booking_response:
                        logger.info(
                            f"🔍 [EmailRouting] Found booking: {booking_response.voya_booking_reference}, "
                            f"contact_email: {booking_response.contact_email}, "
                            f"has_cancellation_policy: {bool(booking_response.cancellation_policy_text)}"
                        )
                    else:
                        logger.warning(
                            f"🔍 [EmailRouting] No booking found for VOYA ref: {voya_booking_reference}"
                        )

                    if booking_response:
                        # Retrieve contact email if available
                        if booking_response.contact_email:
                            recipient_email = booking_response.contact_email
                            logger.info(
                                f"Using stored contact email: {recipient_email} (from original booking)"
                            )
                        elif user:
                            logger.info(
                                f"Using user account email: {recipient_email} (no stored contact email)"
                            )

                        # Retrieve cancellation_policy_text from booking if not already provided
                        if (
                            not cancellation_policy_text
                            and booking_response.cancellation_policy_text
                        ):
                            cancellation_policy_text = (
                                booking_response.cancellation_policy_text
                            )
                            logger.info(
                                f"✅ Retrieved cancellation_policy_text from booking (length: {len(cancellation_policy_text)})"
                            )
                    elif user:
                        logger.info(
                            f"Using user account email: {recipient_email} (no stored contact email)"
                        )

                except Exception as lookup_error:
                    logger.warning(
                        f"Failed to lookup stored contact email for {voya_booking_reference}, "
                        f"using user email: {lookup_error}"
                    )
                    if user:
                        logger.info(
                            f"Using user account email: {recipient_email} (lookup failed)"
                        )

            # Log cancellation policy status
            if cancellation_policy_text:
                logger.info(
                    f"✅ Cancellation policy available for ticket email (length: {len(cancellation_policy_text)})"
                )
            else:
                logger.warning(
                    f"⚠️ No cancellation_policy_text found for ticket issued email. "
                    f"voya_booking_reference: {voya_booking_reference}, "
                    f"external_booking_reference: {external_booking_reference}"
                )

            if recipient_email and user:
                await EmailService.send_email(
                    email_type=EmailType.TICKET_ISSUED,
                    recipient_email=recipient_email,
                    context={
                        "user_name": user.first_name or "User",
                        "user_id": str(user.id),  # For authenticated email link
                        "voya_booking_reference": display_reference,  # VOYA reference for user
                        "ticket_numbers": ticket_numbers,  # List of ticket numbers
                        "cancellation_policy_text": cancellation_policy_text,  # Cancellation policy from fare rules
                    },
                    trip_details=trip_details,  # E-ticket PDF auto-generated if provided
                )
                logger.info(f"Ticket issuance email sent to {recipient_email}")
            else:
                # Fallback for test environment - send to dev email
                from app.domains.email.constants import DEV_EMAIL_RECIPIENT

                await EmailService.send_email(
                    email_type=EmailType.TICKET_ISSUED,
                    recipient_email=DEV_EMAIL_RECIPIENT,
                    context={
                        "user_name": "Test User",
                        "user_id": str(user.id)
                        if user
                        else None,  # For authenticated email link
                        "voya_booking_reference": display_reference,  # VOYA reference for user
                        "ticket_numbers": ticket_numbers,  # List of ticket numbers
                        "cancellation_policy_text": cancellation_policy_text,  # Cancellation policy from fare rules
                    },
                    trip_details=trip_details,  # E-ticket PDF auto-generated if provided
                )
                logger.info(
                    f"Ticket issuance email sent to dev email: {DEV_EMAIL_RECIPIENT}"
                )
            # GDS: Flight Tickets Issued email sent -> set confirmation_email_sent
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
            logger.warning(f"Failed to send ticket issuance email: {e}")

    # ==============================================================
    # CANCELLATION EVENTS
    # ==============================================================

    @staticmethod
    async def handle_booking_cancelled(
        user_id: str,
        external_booking_reference: str,
        cancellation_ref: str | None = None,
    ) -> None:
        """Handle booking cancellation."""
        try:
            user = await _get_user_service().get_user_public(user_id)

            if user:
                await EmailService.send_email(
                    email_type=EmailType.BOOKING_CANCELLED,
                    recipient_email=user.email,
                    context={
                        "user_name": user.first_name or "User",
                        "external_booking_reference": external_booking_reference,
                        "cancellation_reference": cancellation_ref,
                    },
                )
                logger.info(f"Cancellation confirmation email sent to {user.email}")
            else:
                # Fallback for test environment - send to dev email
                from app.domains.email.constants import DEV_EMAIL_RECIPIENT

                await EmailService.send_email(
                    email_type=EmailType.BOOKING_CANCELLED,
                    recipient_email=DEV_EMAIL_RECIPIENT,
                    context={
                        "user_name": "Test User",
                        "external_booking_reference": external_booking_reference,
                        "cancellation_reference": cancellation_ref,
                    },
                )
                logger.info(
                    f"Cancellation confirmation email sent to dev email: {DEV_EMAIL_RECIPIENT}"
                )
        except Exception as e:
            logger.warning(f"Failed to send cancellation email: {e}")
