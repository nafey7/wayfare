"""Payment domain event handlers - simple and clean."""

import asyncio
import logging
from typing import Any

from app.domains.email import EmailService, EmailType

logger = logging.getLogger(__name__)


class PaymentEventHandler:
    """Handle payment domain events - sends emails and notifications."""

    # ==============================================================
    # PAYMENT EVENTS
    # ==============================================================

    @classmethod
    async def handle_payment_succeeded(
        cls,
        user_id: str,
        voya_booking_reference: str,
        amount: float,  # Already converted from cents
        currency: str,
        transaction_id: str,
        payment_method: str = "Credit Card",
    ) -> None:
        """Handle successful payment - send confirmation email.

        Args:
            user_id: User ID
            voya_booking_reference: VOYA booking reference
            amount: Payment amount (in dollars, already converted)
            currency: Currency code (e.g., "USD")
            transaction_id: Payment intent ID
            payment_method: Payment method description
        """
        try:
            from app.domains.user.repository import get_user_by_id

            user = await get_user_by_id(user_id)

            if not user or not user.email:
                logger.warning(
                    f"User {user_id} not found or has no email - cannot send payment confirmation"
                )
                return

            # Send payment confirmation email
            email_context = {
                "voya_booking_reference": voya_booking_reference,
                "user_id": user_id,  # For authenticated "View Your Booking" link
                "user_first_name": user.first_name or "Traveler",
                "amount": amount,
                "currency": currency.upper(),
                "transaction_id": transaction_id,
                "payment_method": payment_method,
            }

            await EmailService.send_email(
                email_type=EmailType.PAYMENT_CONFIRMATION,
                recipient_email=user.email,
                context=email_context,
            )

            logger.info(
                f"Payment confirmation email sent to {user.email} for {voya_booking_reference}"
            )

            # After successful payment for GDS booking, issue tickets
            await cls._issue_tickets_after_payment(
                _user_id=user_id,
                voya_booking_reference=voya_booking_reference,
                _user=user,
            )

        except Exception as e:
            logger.warning(f"Failed to send payment confirmation email: {e}")

    @classmethod
    async def _issue_tickets_after_payment(
        cls,
        _user_id: str,
        voya_booking_reference: str,
        _user: Any,
    ) -> None:
        """Issue tickets after successful GDS payment (not LCC — see body).

        LCC (WebFare) completes ticketing in ``create_booking`` after payment; the Revolut
        webhook often runs before the supplier PNR exists, so we skip FlightLogic ticket issue here.

        Args:
            _user_id: User ID (unused - retrieved from booking)
            voya_booking_reference: VOYA booking reference
            _user: User model for ``FlightService`` (webhooks are outside FastAPI DI)
        """
        try:
            # Lazy imports: avoid importing ``app.domains.bookings`` at module load (circular import
            # with ``revolut_payment.events`` → ``payment.events`` during app startup).
            from app.domains.bookings.constants import TEMP_EXTERNAL_REF
            from app.domains.bookings.service import BookingService
            from app.domains.flight.schemas import TicketOrderRequest
            from app.domains.flight.service import FlightService

            # Get booking event from VOYA reference

            booking_event = await BookingService.get_latest_booking_by_voya_reference(
                voya_booking_reference
            )

            if not booking_event or not booking_event.external_booking_reference:
                logger.warning(
                    f"Cannot issue tickets - no external booking reference found for {voya_booking_reference}"
                )
                return

            if booking_event.carrier_type == "LCC":
                logger.debug(
                    "Skipping post-payment FlightLogic ticket issue for LCC booking %s",
                    voya_booking_reference,
                )
                return

            external_ref = booking_event.external_booking_reference
            if external_ref == TEMP_EXTERNAL_REF:
                for _attempt in range(12):
                    await asyncio.sleep(0.5)
                    refreshed = (
                        await BookingService.get_latest_booking_by_voya_reference(
                            voya_booking_reference
                        )
                    )
                    if (
                        refreshed
                        and refreshed.external_booking_reference
                        and refreshed.external_booking_reference != TEMP_EXTERNAL_REF
                    ):
                        booking_event = refreshed
                        external_ref = refreshed.external_booking_reference
                        break
                else:
                    logger.warning(
                        "Cannot issue tickets for %s — external reference still %s after wait "
                        "(GDS book may not have persisted yet).",
                        voya_booking_reference,
                        TEMP_EXTERNAL_REF,
                    )
                    return

            logger.info(
                f"Issuing tickets for {voya_booking_reference} -> {external_ref}"
            )

            # Webhooks run outside FastAPI — construct service with the paying user explicitly
            # (``get_flight_service()`` without DI would pass a bare ``Depends`` object as user).
            flight_service = FlightService(current_user=_user)

            # Get cancellation_policy_text from booking event (DB) or cache (fallback)
            cancellation_policy_text = booking_event.cancellation_policy_text
            if not cancellation_policy_text:
                from app.domains.flight.service import _cancellation_policy_cache

                cancellation_policy_text = _cancellation_policy_cache.get(
                    voya_booking_reference
                )

            ticket_request = TicketOrderRequest(
                voya_booking_reference=voya_booking_reference,
                external_booking_reference=external_ref,
                cancellation_policy_text=cancellation_policy_text,
                user_id=None,
                user_password=None,
                access=None,
                ip_address=None,
                payment_id=None,
            )

            ticket_response = await flight_service.issue_tickets(ticket_request)

            if ticket_response and hasattr(ticket_response, "ticket_numbers"):
                ticket_numbers = ticket_response.ticket_numbers or []
                logger.info(
                    f"✅ Tickets issued successfully for {voya_booking_reference}: {len(ticket_numbers)} tickets"
                )

                # The FlightService.issue_tickets() already calls FlightEventHandler.handle_tickets_issued
                # which sends the "tickets confirmed" email, so we don't need to do it here

            else:
                logger.warning(f"Failed to issue tickets for {voya_booking_reference}")

        except Exception as e:
            logger.error(
                f"Failed to issue tickets after payment for {voya_booking_reference}: {e}",
                exc_info=True,
            )
