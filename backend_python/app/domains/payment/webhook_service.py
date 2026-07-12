"""Payment webhook service for processing Stripe webhook events.

This service follows the established service pattern with constructor dependency injection
for testability. It processes all Stripe webhook events related to payments.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from app.domains.bookings import BookingService
from app.domains.flight.validation import validate_ticket_time_limit
from app.domains.payment.enums import PaymentStatus, PayoutStatus
from app.domains.payment.events import PaymentEventHandler
from app.domains.payment.repository import PaymentRepository

logger = logging.getLogger(__name__)


class PaymentWebhookService:
    """Service for processing Stripe webhook events.

    Follows established service pattern with constructor DI for testability.
    All webhook business logic is centralized here for easy testing.
    """

    def __init__(self, repository: PaymentRepository | None = None) -> None:
        """Initialize webhook service with optional repository injection.

        Args:
            repository: Payment repository (injected for testing, or created)
        """
        self.repository = repository or PaymentRepository()

    async def process_payment_succeeded(self, payment_intent: dict[str, Any]) -> None:
        """Process successful payment intent webhook.

        Updates transaction status and triggers payment confirmation email.

        Args:
            payment_intent: Stripe payment intent object
        """
        logger.info(f"💰 Payment succeeded: {payment_intent.get('id')}")
        logger.info(f"   Amount: ${payment_intent.get('amount', 0) / 100}")
        logger.info(f"   Currency: {payment_intent.get('currency', 'N/A').upper()}")
        logger.info(f"   Status: {payment_intent.get('status')}")

        # Extract metadata
        metadata = payment_intent.get("metadata", {})
        voya_ref = metadata.get("voya_booking_reference")
        user_id = metadata.get("user_id")

        if not voya_ref:
            logger.warning(
                f"Payment {payment_intent.get('id')} missing voya_booking_reference in metadata"
            )
            return

        if not user_id:
            logger.warning(
                f"Payment {payment_intent.get('id')} missing user_id in metadata"
            )
            return

        # Validate ticket_time_limit before processing payment
        booking_event = await BookingService.get_latest_booking_by_voya_reference(
            voya_ref
        )
        if booking_event and booking_event.ticket_time_limit:
            is_valid, time_remaining = validate_ticket_time_limit(
                booking_event.ticket_time_limit
            )

            if not is_valid:
                current_time_utc = datetime.now(UTC)
                ticket_time_limit_utc = booking_event.ticket_time_limit
                # Normalize for logging
                if ticket_time_limit_utc.tzinfo is None:
                    ticket_time_limit_utc = ticket_time_limit_utc.replace(tzinfo=UTC)
                else:
                    ticket_time_limit_utc = ticket_time_limit_utc.astimezone(UTC)

                logger.error(
                    f"Payment blocked: ticket time limit expired for {voya_ref}. "
                    f"Current time UTC: {current_time_utc.isoformat()}, "
                    f"Ticket time limit UTC: {ticket_time_limit_utc.isoformat()}"
                )
                # Update transaction status to failed with expiration reason
                await self.repository.update_transaction_status(
                    payment_intent_id=payment_intent["id"],
                    status=PaymentStatus.FAILED,
                    failure_reason=f"Booking expired. Ticket time limit ({ticket_time_limit_utc.isoformat()}) has passed.",
                    failed_at=datetime.now(UTC),
                )
                await BookingService.release_voucher_for_booking_if_any(
                    user_id, voya_ref
                )
                return  # Don't process payment further

            current_time_utc = datetime.now(UTC)
            ticket_time_limit_utc = booking_event.ticket_time_limit
            # Normalize for logging
            if ticket_time_limit_utc.tzinfo is None:
                ticket_time_limit_utc = ticket_time_limit_utc.replace(tzinfo=UTC)
            else:
                ticket_time_limit_utc = ticket_time_limit_utc.astimezone(UTC)

            logger.info(
                f"Ticket time limit validation passed for {voya_ref}. "
                f"Current time UTC: {current_time_utc.isoformat()}, "
                f"Ticket time limit UTC: {ticket_time_limit_utc.isoformat()}, "
                f"Time remaining: {time_remaining} seconds"
            )

        # Update transaction status in MongoDB
        paid_at_utc = datetime.fromtimestamp(payment_intent.get("created") or 0, UTC)
        await self.repository.update_transaction_status(
            payment_intent_id=payment_intent["id"],
            status=PaymentStatus.SUCCEEDED,
            stripe_charge_id=payment_intent.get("latest_charge"),
            paid_at=paid_at_utc,
        )

        logger.info(f"✅ Transaction updated for {voya_ref}")

        # Set date_paid and amount on booking event (amount from payment if not set at booking)
        await BookingService.update_booking_dates_and_flags(
            voya_ref,
            date_paid=paid_at_utc,
            amount=payment_intent.get("amount", 0) / 100,
        )

        from app.domains.discount.service import discount_service

        await discount_service.redeem_voucher_on_payment(booking_reference=voya_ref)

        # Trigger payment succeeded event (sends confirmation email)
        await PaymentEventHandler.handle_payment_succeeded(
            user_id=user_id,
            voya_booking_reference=voya_ref,
            amount=payment_intent.get("amount", 0) / 100,
            currency=payment_intent.get("currency", "usd"),
            transaction_id=payment_intent["id"],  # Required field, always present
            payment_method="Credit Card",
        )

        logger.info(f"✅ Payment processed successfully for {voya_ref}")

    async def process_payment_failed(self, payment_intent: dict[str, Any]) -> None:
        """Process failed payment intent webhook.

        Updates transaction status with failure details.

        Args:
            payment_intent: Stripe payment intent object
        """
        logger.error(f"❌ Payment failed: {payment_intent.get('id')}")
        logger.error(f"   Amount: ${payment_intent.get('amount', 0) / 100}")
        logger.error(f"   Last error: {payment_intent.get('last_payment_error')}")

        # Extract metadata
        metadata = payment_intent.get("metadata", {})
        voya_ref = metadata.get("voya_booking_reference")

        if not voya_ref:
            logger.warning(
                f"Failed payment {payment_intent.get('id')} missing voya_booking_reference"
            )
            return

        # Update transaction status
        await self.repository.update_transaction_status(
            payment_intent_id=payment_intent["id"],
            status=PaymentStatus.FAILED,
            failure_reason=str(
                payment_intent.get("last_payment_error", {}).get("message")
            ),
            failed_at=datetime.now(UTC),
        )

        user_id_failed = metadata.get("user_id")
        if not user_id_failed:
            tx = await self.repository.get_transaction_by_voya_reference(voya_ref)
            if tx and tx.user_id:
                user_id_failed = str(tx.user_id)
        if user_id_failed:
            await BookingService.release_voucher_for_booking_if_any(
                user_id_failed, voya_ref
            )

        logger.error(f"❌ Transaction marked as failed for {voya_ref}")

    async def process_charge_succeeded(self, charge: dict[str, Any]) -> None:
        """Process successful charge webhook.

        Logs charge success information.

        Args:
            charge: Stripe charge object
        """
        logger.info(f"💳 Charge succeeded: {charge.get('id')}")
        logger.info(f"   Amount: ${charge.get('amount', 0) / 100}")
        logger.info(f"   Payment Intent: {charge.get('payment_intent')}")

    async def process_charge_failed(self, charge: dict[str, Any]) -> None:
        """Process failed charge webhook.

        Updates transaction with charge failure details.

        Args:
            charge: Stripe charge object
        """
        logger.error(f"❌ Charge failed: {charge.get('id')}")
        logger.error(f"   Failure message: {charge.get('failure_message')}")
        logger.error(f"   Payment Intent: {charge.get('payment_intent')}")

        payment_intent_id = charge.get("payment_intent")
        if not payment_intent_id:
            logger.warning("Charge failed webhook missing payment_intent")
            return

        # Update transaction with charge failure
        await self.repository.update_transaction_status(
            payment_intent_id=payment_intent_id,
            status=PaymentStatus.FAILED,
            stripe_charge_id=charge.get("id"),
            failure_reason=charge.get("failure_message"),
            failed_at=datetime.now(UTC),
        )

        tx = await self.repository.get_transaction_by_payment_intent(payment_intent_id)
        if tx and tx.voya_booking_reference and tx.user_id:
            await BookingService.release_voucher_for_booking_if_any(
                str(tx.user_id), tx.voya_booking_reference
            )

    async def process_transfer_created(self, transfer: dict[str, Any]) -> None:
        """Process transfer created webhook.

        Updates payout status when funds are transferred to supplier.

        Args:
            transfer: Stripe transfer object
        """
        logger.info(f"💸 Transfer created: {transfer.get('id')}")
        logger.info(f"   Amount: ${transfer.get('amount', 0) / 100}")
        logger.info(f"   Destination: {transfer.get('destination')}")

        # Get voya reference from transfer_group (not metadata)
        voya_ref = transfer.get("transfer_group")
        if not voya_ref:
            logger.warning(
                f"Transfer {transfer.get('id')} missing transfer_group (voya_booking_reference)"
            )
            return

        # Find transaction by voya reference
        transaction = await self.repository.get_transaction_by_voya_reference(voya_ref)
        if not transaction:
            logger.warning(f"Transaction not found for voya reference: {voya_ref}")
            return
        if not transaction.stripe_payment_intent_id:
            logger.warning(
                "Transaction for voya reference %s has no stripe_payment_intent_id; "
                "skipping payout status update",
                voya_ref,
            )
            return

        # Update payout status via transaction status update
        await self.repository.update_transaction_status(
            payment_intent_id=transaction.stripe_payment_intent_id,
            status=transaction.status,  # Keep current payment status
            payout_status=PayoutStatus.SCHEDULED.value,
            stripe_transfer_id=transfer.get("id"),
            payout_initiated_at=datetime.now(UTC),
        )

        logger.info(f"✅ Payout initiated for {voya_ref}")

    async def process_transfer_updated(self, transfer: dict[str, Any]) -> None:
        """Process transfer updated webhook.

        Updates payout status when transfer status changes (paid/failed).

        Args:
            transfer: Stripe transfer object
        """
        transfer_status = transfer.get("status")
        logger.info(
            f"💸 Transfer updated: {transfer.get('id')} - Status: {transfer_status}"
        )

        # Get voya reference from transfer_group
        voya_ref = transfer.get("transfer_group")
        if not voya_ref:
            logger.warning(
                f"Transfer update {transfer.get('id')} missing transfer_group"
            )
            return

        # Find transaction
        transaction = await self.repository.get_transaction_by_voya_reference(voya_ref)
        if not transaction:
            logger.warning(f"Transaction not found for voya reference: {voya_ref}")
            return
        if not transaction.stripe_payment_intent_id:
            logger.warning(
                "Transaction for voya reference %s has no stripe_payment_intent_id; "
                "skipping payout status update",
                voya_ref,
            )
            return

        # Map Stripe transfer status to our payout status
        if transfer_status == "paid":
            payout_status = PayoutStatus.PAID
            logger.info(f"✅ Payout completed for {voya_ref}")
        elif transfer_status == "failed":
            payout_status = PayoutStatus.FAILED
            logger.error(
                f"❌ Payout failed for {voya_ref}: {transfer.get('failure_message')}"
            )
        else:
            payout_status = PayoutStatus.SCHEDULED
            logger.info(f"⏳ Payout status updated for {voya_ref}: {transfer_status}")

        # Update payout status via transaction status update
        await self.repository.update_transaction_status(
            payment_intent_id=transaction.stripe_payment_intent_id,
            status=transaction.status,  # Keep current payment status
            payout_status=payout_status.value,
            payout_completed_at=datetime.now(UTC)
            if transfer_status == "paid"
            else None,
        )

    async def process_account_updated(self, account: dict[str, Any]) -> None:
        """Process Stripe Connect account updated webhook.

        Logs account capability changes.

        Args:
            account: Stripe account object
        """
        logger.info(f"🏦 Account updated: {account.get('id')}")
        logger.info(f"   Charges enabled: {account.get('charges_enabled')}")
        logger.info(f"   Payouts enabled: {account.get('payouts_enabled')}")
        logger.info(
            f"   Requirements: {account.get('requirements', {}).get('currently_due', [])}"
        )

    async def process_account_deauthorized(self, account: dict[str, Any]) -> None:
        """Process Stripe Connect account deauthorization webhook.

        Logs when supplier disconnects their Stripe account.

        Args:
            account: Stripe account object
        """
        logger.warning(f"⚠️ Account deauthorized: {account.get('id')}")
        logger.warning(
            f"   Business: {account.get('business_profile', {}).get('name', 'Unknown')}"
        )
