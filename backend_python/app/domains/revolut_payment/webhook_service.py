"""Revolut webhook service for processing Revolut webhook events.

This service follows the established service pattern with constructor dependency injection
for testability. It processes all Revolut webhook events related to payments.

Phase 3: Full webhook processing implementation.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from app.domains.revolut_payment.enums import PaymentStatus, PayoutStatus
from app.domains.revolut_payment.events import PaymentEventHandler
from app.domains.revolut_payment.repository import RevolutPaymentRepository

logger = logging.getLogger(__name__)

_DEFAULT_CURRENCY = "usd"


def _parse_revolut_timestamp(
    created_at_value: Any, *, label: str = "timestamp"
) -> datetime:
    """Parse Revolut ISO-8601 string or Unix timestamp; fallback to now on parse failure."""
    now = datetime.now(UTC)
    if isinstance(created_at_value, (int, float)):
        return datetime.fromtimestamp(created_at_value, UTC)
    if isinstance(created_at_value, str):
        try:
            return datetime.fromisoformat(
                created_at_value.replace("Z", "+00:00")
            ).replace(tzinfo=UTC)
        except ValueError:
            logger.warning("Could not parse %s: %s", label, created_at_value)
            return now
    return now


def _parse_order_amount_for_completed_payment(
    order: dict[str, Any],
) -> tuple[int, str] | None:
    """Extract amount (minor units) and currency for a completed order.

    Returns None if amount is missing, null, or not a positive number — caller must not mark paid.
    """
    amount_data = order.get("amount")
    if isinstance(amount_data, dict):
        raw_value = amount_data.get("value")
        currency = amount_data.get("currency", _DEFAULT_CURRENCY)
        if not isinstance(raw_value, (int, float)) or raw_value <= 0:
            logger.warning(
                "Revolut order completed webhook missing or invalid amount.value in %s",
                amount_data,
            )
            return None
        return (int(raw_value), str(currency).lower())
    if amount_data is None:
        logger.warning(
            "Revolut order completed webhook missing amount (null or absent)"
        )
        return None
    if not isinstance(amount_data, (int, float)) or amount_data <= 0:
        logger.warning(
            "Revolut order completed webhook has invalid amount: %s", amount_data
        )
        return None
    currency = order.get("currency", _DEFAULT_CURRENCY)
    return (int(amount_data), str(currency).lower())


def _parse_revolut_amount_for_refund_payout_log(
    amount_data: Any,
    *,
    top_level_currency: Any,
    label: str,
) -> tuple[int | None, str]:
    """Parse refund/payout amount for logging; warn instead of silent zero (aligns with order completed)."""
    if isinstance(amount_data, dict):
        raw_value = amount_data.get("value")
        currency = amount_data.get("currency", _DEFAULT_CURRENCY)
        if not isinstance(raw_value, (int, float)):
            logger.warning(
                "Revolut %s webhook missing or invalid amount.value in %s",
                label,
                amount_data,
            )
            return None, str(currency).lower()
        return int(raw_value), str(currency).lower()
    if amount_data is None:
        logger.warning("Revolut %s webhook missing amount", label)
        return None, str(top_level_currency or _DEFAULT_CURRENCY).lower()
    if not isinstance(amount_data, (int, float)):
        logger.warning("Revolut %s webhook has invalid amount: %s", label, amount_data)
        return None, str(top_level_currency or _DEFAULT_CURRENCY).lower()
    return int(amount_data), str(top_level_currency or _DEFAULT_CURRENCY).lower()


class RevolutWebhookService:
    """Service for processing Revolut webhook events.

    Follows established service pattern with constructor DI for testability.
    All webhook business logic is centralized here for easy testing.

    Phase 3: Full webhook processing implementation.
    """

    def __init__(self, repository: RevolutPaymentRepository | None = None) -> None:
        """Initialize webhook service with optional repository injection.

        Args:
            repository: Revolut payment repository (injected for testing, or created)
        """
        self.repository = repository or RevolutPaymentRepository()

    async def process_order_completed(self, order: dict[str, Any]) -> None:
        """Process completed order webhook (equivalent to payment_intent.succeeded).

        Maps to Stripe payment_intent.succeeded - updates transaction status and triggers email.

        Args:
            order: Revolut order object
        """
        # Lazy import avoids circular import: bookings.service → revolut_payment → this module.
        from app.domains.bookings.service import BookingService

        order_id_raw = order.get("id")
        if not isinstance(order_id_raw, str) or not order_id_raw:
            logger.warning("Revolut order completed webhook missing string id")
            return
        order_id = order_id_raw
        logger.info(f"💰 Revolut order completed: {order_id}")

        parsed_amount = _parse_order_amount_for_completed_payment(order)
        if parsed_amount is None:
            return
        amount_value, currency = parsed_amount

        logger.info(f"   Amount: ${amount_value / 100}")
        logger.info(f"   Currency: {currency.upper()}")
        logger.info(f"   State: {order.get('state')}")

        # Extract metadata
        metadata = order.get("metadata", {})
        voya_ref = metadata.get("voya_booking_reference")
        user_id = metadata.get("user_id")

        # If metadata is missing, try to look up the transaction by order_id
        if not voya_ref or not user_id:
            logger.info(
                f"Revolut order {order_id} missing metadata, looking up transaction in database"
            )
            transaction = await self.repository.get_transaction_by_order_id(order_id)
            if transaction:
                if not voya_ref:
                    voya_ref = getattr(transaction, "voya_booking_reference", None)
                    logger.info(
                        f"Found voya_booking_reference from transaction: {voya_ref}"
                    )
                if not user_id:
                    transaction_user_id = getattr(transaction, "user_id", None)
                    if transaction_user_id:
                        # Convert ObjectId to string if needed
                        user_id = str(transaction_user_id)
                        logger.info(f"Found user_id from transaction: {user_id}")

        # Fallback: find booking by payment_intent_id (LCC stores Revolut order_id here)
        if not voya_ref:
            voya_ref = await BookingService.get_voya_reference_by_payment_intent_id(
                order_id
            )
            if voya_ref:
                logger.info(
                    f"Found voya_booking_reference from booking event (payment_intent_id={order_id}): {voya_ref}"
                )

        if not voya_ref:
            logger.warning(
                f"Revolut order {order_id} missing voya_booking_reference in metadata and transaction not found"
            )
            return

        # If user_id still missing (e.g. we found voya_ref from booking fallback), get it from the booking
        if not user_id:
            booking = await BookingService.get_latest_booking_by_voya_reference(
                voya_ref
            )
            if not booking:
                booking = (
                    await BookingService.get_latest_booking_by_parent_voya_reference(
                        voya_ref
                    )
                )
                if booking:
                    logger.info(
                        "Resolved booking leg via parent_voya_booking_reference for Revolut webhook"
                    )
            if booking:
                user_id = str(booking.user_id)
                logger.info(f"Found user_id from booking event: {user_id}")

        if not user_id:
            logger.warning(
                f"Revolut order {order_id} missing user_id in metadata and transaction"
            )
            return

        # Get created_at timestamp (Revolut uses ISO 8601 or Unix timestamp)
        created_at = datetime.now(UTC)
        if order.get("created_at"):
            created_at = _parse_revolut_timestamp(
                order.get("created_at"), label="created_at"
            )

        # Update transaction status in MongoDB
        await self.repository.update_transaction_status(
            order_id=order_id,
            status=PaymentStatus.SUCCEEDED,
            paid_at=created_at,
        )

        logger.info(f"✅ Transaction updated for {voya_ref}")

        # Set date_paid and amount on booking event (LCC flights rely on webhook for both)
        await BookingService.update_booking_dates_and_flags(
            voya_ref,
            date_paid=created_at,
            amount=amount_value / 100,
        )

        from app.domains.discount.service import discount_service

        await discount_service.redeem_voucher_on_payment(booking_reference=voya_ref)

        # Trigger payment succeeded event (sends confirmation email)
        await PaymentEventHandler.handle_payment_succeeded(
            user_id=user_id,
            voya_booking_reference=voya_ref,
            amount=amount_value / 100,  # Convert from minor units to dollars
            currency=currency,
            transaction_id=order_id,
            payment_method="Revolut",
        )

        logger.info(f"✅ Revolut payment processed successfully for {voya_ref}")

    async def process_order_failed(self, order: dict[str, Any]) -> None:
        """Process failed order webhook (equivalent to payment_intent.payment_failed).

        Maps to Stripe payment_intent.payment_failed - updates transaction with failure details.

        Args:
            order: Revolut order object
        """
        order_id_raw = order.get("id")
        if not isinstance(order_id_raw, str) or not order_id_raw:
            logger.warning("Revolut order failed webhook missing string id")
            return
        order_id = order_id_raw
        logger.error(f"❌ Revolut order failed: {order_id}")

        # Handle amount format: can be either {"value": int, "currency": str} or direct int
        amount_data = order.get("amount")
        if isinstance(amount_data, dict):
            amount_value = amount_data.get("value", 0)
        else:
            # Amount is a direct integer (minor units)
            amount_value = amount_data if isinstance(amount_data, (int, float)) else 0

        logger.error(f"   Amount: ${amount_value / 100}")
        logger.error(f"   State: {order.get('state')}")

        # Extract metadata
        metadata = order.get("metadata", {})
        voya_ref = metadata.get("voya_booking_reference")

        if not voya_ref:
            logger.warning(
                f"Failed Revolut order {order_id} missing voya_booking_reference"
            )
            return

        # Update transaction status
        await self.repository.update_transaction_status(
            order_id=order_id,
            status=PaymentStatus.FAILED,
            failure_reason=f"Order state: {order.get('state')}",
            failed_at=datetime.now(UTC),
        )

        user_id_failed = metadata.get("user_id")
        if not user_id_failed:
            tx = await self.repository.get_transaction_by_order_id(order_id)
            if tx and getattr(tx, "user_id", None):
                user_id_failed = str(tx.user_id)
        if user_id_failed:
            from app.domains.bookings.service import BookingService

            await BookingService.release_voucher_for_booking_if_any(
                user_id_failed, voya_ref
            )

        logger.error(f"❌ Transaction marked as failed for {voya_ref}")

    async def process_refund_completed(self, refund: dict[str, Any]) -> None:
        """Process completed refund webhook.

        Updates transaction status when refund is completed.

        Args:
            refund: Revolut refund object
        """
        refund_id = refund.get("id")
        order_id = refund.get("order_id")
        logger.info(f"💸 Revolut refund completed: {refund_id}")
        logger.info(f"   Order ID: {order_id}")

        refund_amount_value, _refund_currency = (
            _parse_revolut_amount_for_refund_payout_log(
                refund.get("amount"),
                top_level_currency=refund.get("currency"),
                label="refund completed",
            )
        )
        if refund_amount_value is not None:
            logger.info(f"   Amount: ${refund_amount_value / 100}")
        else:
            logger.info("   Amount: (not parsed; see warnings above)")

        if not order_id:
            logger.warning(f"Refund {refund_id} missing order_id")
            return

        # Get created_at timestamp
        refunded_at = datetime.now(UTC)
        if refund.get("created_at"):
            refunded_at = _parse_revolut_timestamp(
                refund.get("created_at"), label="refund created_at"
            )

        # Update transaction with refund information
        await self.repository.update_transaction_status(
            order_id=order_id,
            status=PaymentStatus.REFUNDED,
            refund_id=refund_id,
            refunded_at=refunded_at,
        )

        logger.info(f"✅ Refund processed for order {order_id}")

    async def process_payout_completed(self, payout: dict[str, Any]) -> None:
        """Process completed payout webhook.

        Updates payout status when payout is completed.

        Args:
            payout: Revolut payout object
        """
        payout_id = payout.get("id")
        logger.info(f"💸 Revolut payout completed: {payout_id}")

        payout_amount_value, payout_currency = (
            _parse_revolut_amount_for_refund_payout_log(
                payout.get("amount"),
                top_level_currency=payout.get("currency"),
                label="payout completed",
            )
        )
        if payout_amount_value is not None:
            logger.info(f"   Amount: ${payout_amount_value / 100}")
        else:
            logger.info("   Amount: (not parsed; see warnings above)")
        logger.info(f"   Currency: {payout_currency.upper()}")

        # Extract metadata to find transaction
        metadata = payout.get("metadata", {})
        voya_ref = metadata.get("voya_booking_reference")

        if not voya_ref:
            logger.warning(
                f"Payout {payout_id} missing voya_booking_reference in metadata"
            )
            return

        # Find transaction by voya reference
        transaction = await self.repository.get_transaction_by_voya_reference(voya_ref)
        if not transaction:
            logger.warning(f"Transaction not found for voya reference: {voya_ref}")
            return

        # Get order_id from transaction
        order_id = getattr(transaction, "revolut_order_id", None)
        if not order_id and hasattr(transaction, "stripe_payment_intent_id"):
            # Handle temporary mapping format
            pi_id = transaction.stripe_payment_intent_id
            if isinstance(pi_id, str) and pi_id.startswith("revolut_"):
                order_id = pi_id.replace("revolut_", "", 1)

        if order_id:
            # Get completed_at timestamp
            payout_completed_at = datetime.now(UTC)
            if payout.get("completed_at"):
                payout_completed_at = _parse_revolut_timestamp(
                    payout.get("completed_at"), label="payout completed_at"
                )

            # Update payout status
            await self.repository.update_transaction_status(
                order_id=order_id,
                status=transaction.status,  # Keep current payment status
                payout_status=PayoutStatus.PAID.value,
                revolut_payout_id=payout_id,
                payout_completed_at=payout_completed_at,
            )

            logger.info(f"✅ Payout completed for {voya_ref}")
