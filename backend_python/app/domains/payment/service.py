"""Payment service for Stripe integration and business logic."""

import logging
from datetime import UTC, datetime

import stripe
from bson import ObjectId

from app.core.config import settings
from app.domains.flight.validation import validate_ticket_time_limit
from app.domains.payment.constants import (
    FLIGHTLOGIC_STRIPE_ACCOUNT_ID,
    FLIGHTS_PLATFORM_FEE_PERCENTAGE,
    HOTELS_PLATFORM_FEE_PERCENTAGE,
    VOYA_STRIPE_PLATFORM_ACCOUNT_ID,
)
from app.domains.payment.enums import PaymentStatus, PayoutStatus
from app.domains.payment.exceptions import (
    PaymentIntentCreationError,
    PaymentValidationError,
    PayoutReleaseError,
)
from app.domains.payment.repository import PaymentRepository
from app.domains.payment.schemas import (
    BookingExpiryCheckRequest,
    BookingExpiryCheckResponse,
    PaymentIntentCreateRequest,
    PaymentIntentCreateResponse,
    PayoutReleaseRequest,
    PayoutReleaseResponse,
    TransactionResponse,
)

logger = logging.getLogger(__name__)

# Configure Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentService:
    """Service for payment intent creation, validation, and payout management."""

    def __init__(self, user_id: str | None = None) -> None:
        """Initialize payment service.

        Args:
            user_id: Current user ID (optional, required for user-specific operations)
        """
        self.user_id = user_id
        self.repository = PaymentRepository()

    async def create_payment_intent(
        self, request: PaymentIntentCreateRequest
    ) -> PaymentIntentCreateResponse:
        """Create Stripe payment intent with platform fee and Connect transfer.

        Platform fees:
        - Flights: 5% platform fee
        - Hotels: 10.5% commission

        Args:
            request: Payment intent creation request

        Returns:
            Payment intent response with client_secret for frontend

        Raises:
            PaymentIntentCreationError: If Stripe API call fails
        """
        from app.domains.bookings.service import BookingService

        # IMPORTANT: booking_amount from frontend is total_fare which ALREADY includes platform fee
        # The platform fee is calculated using Gross Margin Pricing:
        # Display Price = Supplier Price / (1 - fee_percentage)
        # So: Supplier Price = Display Price * (1 - fee_percentage)
        # Platform Fee = Display Price - Supplier Price
        if request.booking_type.lower() == "hotel":
            # Hotels: 10.5% commission
            # Supplier Price = Display Price * (1 - 0.105) = Display Price * 0.895
            supplier_amount = int(
                request.booking_amount * (1 - HOTELS_PLATFORM_FEE_PERCENTAGE)
            )
            platform_fee = request.booking_amount - supplier_amount
        else:
            # Flights: 5% platform fee using Gross Margin Pricing
            # Supplier Price = Display Price * (1 - 0.05) = Display Price * 0.95
            supplier_amount = int(
                request.booking_amount * (1 - FLIGHTS_PLATFORM_FEE_PERCENTAGE)
            )
            platform_fee = request.booking_amount - supplier_amount

        logger.info(
            f"Creating payment intent for {request.voya_booking_reference}: "
            f"total=${request.booking_amount / 100:.2f}, "
            f"fee=${platform_fee / 100:.2f}, "
            f"supplier=${supplier_amount / 100:.2f}"
        )

        # Validate ticket_time_limit before creating payment intent (for GDS flights)
        # This blocks payment intent creation if booking has expired, preventing Stripe from charging
        if request.booking_type.lower() == "flight":
            booking_event = await BookingService.get_latest_booking_by_voya_reference(
                request.voya_booking_reference
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
                        ticket_time_limit_utc = ticket_time_limit_utc.replace(
                            tzinfo=UTC
                        )
                    else:
                        ticket_time_limit_utc = ticket_time_limit_utc.astimezone(UTC)

                    logger.error(
                        f"Payment intent creation blocked: booking expired for {request.voya_booking_reference}. "
                        f"Current time UTC: {current_time_utc.isoformat()}, "
                        f"Ticket time limit UTC: {ticket_time_limit_utc.isoformat()}"
                    )
                    raise PaymentIntentCreationError(
                        f"Booking has expired. The ticket time limit ({ticket_time_limit_utc.isoformat()}) has passed. "
                        "Please start a new search. Payment cannot be processed."
                    )

                current_time_utc = datetime.now(UTC)
                ticket_time_limit_utc = booking_event.ticket_time_limit
                # Normalize for logging
                if ticket_time_limit_utc.tzinfo is None:
                    ticket_time_limit_utc = ticket_time_limit_utc.replace(tzinfo=UTC)
                else:
                    ticket_time_limit_utc = ticket_time_limit_utc.astimezone(UTC)

                logger.info(
                    f"Ticket time limit validation passed for {request.voya_booking_reference} before payment intent creation. "
                    f"Current time UTC: {current_time_utc.isoformat()}, "
                    f"Ticket time limit UTC: {ticket_time_limit_utc.isoformat()}, "
                    f"Time remaining: {time_remaining} seconds"
                )

        try:
            # Prepare payment intent parameters
            payment_params = {
                "amount": request.booking_amount,
                "currency": request.currency,
                "metadata": {
                    "voya_booking_reference": request.voya_booking_reference,
                    "user_id": self.user_id or "unknown",
                    "platform_fee": platform_fee,
                    "supplier_amount": supplier_amount,
                },
            }

            # Only add transfer_data if destination is not the platform account
            # (Stripe doesn't allow transfers to your own account)
            # Also check if we should use Connect (can be disabled via env var for testing)
            use_connect_transfer = (
                FLIGHTLOGIC_STRIPE_ACCOUNT_ID != VOYA_STRIPE_PLATFORM_ACCOUNT_ID
                and settings.STRIPE_USE_CONNECT_TRANSFERS
            )

            if use_connect_transfer:
                payment_params["application_fee_amount"] = platform_fee
                payment_params["transfer_data"] = {
                    "destination": FLIGHTLOGIC_STRIPE_ACCOUNT_ID,
                }
                logger.info(
                    f"Payment intent will transfer {supplier_amount / 100:.2f} "
                    f"{request.currency.upper()} to {FLIGHTLOGIC_STRIPE_ACCOUNT_ID}"
                )
            else:
                logger.warning(
                    "Connect transfers disabled: full payment will go to platform account. "
                    "Platform fee and supplier amount are tracked in metadata only."
                )

            # Create Stripe payment intent
            payment_intent = stripe.PaymentIntent.create(**payment_params)  # type: ignore[arg-type]

            logger.info(
                f"✅ Stripe payment intent created: {payment_intent.id} for {request.voya_booking_reference}"
            )

        except stripe._error.StripeError as e:
            logger.error(f"Stripe API error: {e}")
            raise PaymentIntentCreationError(
                f"Failed to create payment intent: {e!s}"
            ) from e

        # Log transaction in MongoDB
        transaction = await self.repository.create_transaction(
            {
                "stripe_payment_intent_id": payment_intent.id,
                "voya_booking_reference": request.voya_booking_reference,
                "user_id": ObjectId(self.user_id) if self.user_id else None,
                "amount": request.booking_amount,
                "currency": request.currency,
                "platform_fee": platform_fee,
                "supplier_amount": supplier_amount,
                "destination_account_id": FLIGHTLOGIC_STRIPE_ACCOUNT_ID,
                "status": PaymentStatus.PENDING,
            }
        )

        logger.info(f"Transaction logged: {transaction.id}")

        # Store payment_intent_id in booking event for reuse
        try:
            await BookingService.update_payment_intent_id(
                request.voya_booking_reference, payment_intent.id
            )
            logger.info(
                f"✅ Stored payment_intent_id {payment_intent.id} in booking event for {request.voya_booking_reference}"
            )
        except ValueError as e:
            # Booking not found - this is okay for new bookings that haven't been created yet
            logger.debug(
                f"Could not store payment_intent_id (booking may not exist yet): {e}"
            )
        except Exception as e:
            # Log error but don't fail payment intent creation
            logger.warning(f"Failed to store payment_intent_id in booking event: {e}")

        return PaymentIntentCreateResponse(
            payment_intent_id=payment_intent.id,
            client_secret=payment_intent.client_secret
            or "",  # Stripe always returns client_secret
            amount=request.booking_amount,
            currency=request.currency,
            platform_fee=platform_fee,
            supplier_amount=supplier_amount,
            publishable_key=settings.STRIPE_PUBLISHABLE_KEY or "",  # Required config
        )

    async def validate_payment_succeeded(self, payment_intent_id: str) -> None:
        """Validate that payment has succeeded before allowing booking.

        Args:
            payment_intent_id: Stripe payment intent ID

        Raises:
            PaymentValidationError: If payment has not succeeded
        """
        logger.info(f"Validating payment: {payment_intent_id}")

        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe._error.StripeError as e:
            logger.error(f"Failed to retrieve payment intent: {e}")
            raise PaymentValidationError(f"Payment validation failed: {e!s}") from e

        if payment_intent.status != "succeeded":
            logger.warning(
                f"Payment {payment_intent_id} not succeeded (status: {payment_intent.status})"
            )
            raise PaymentValidationError(
                f"Payment not completed. Status: {payment_intent.status}"
            )

        logger.info(f"✅ Payment {payment_intent_id} validated successfully")

    async def check_payment_not_used(self, payment_intent_id: str) -> None:
        """Check that payment has not already been used for a booking (idempotency).

        Args:
            payment_intent_id: Stripe payment intent ID

        Raises:
            PaymentValidationError: If payment already used for booking
        """
        transaction = await self.repository.get_transaction_by_payment_intent(
            payment_intent_id
        )

        if not transaction:
            # Transaction not found - this is okay, it might be a demo payment
            # or transaction creation might be delayed
            logger.warning(
                f"Transaction not found for payment {payment_intent_id} during idempotency check"
            )
            return

        if transaction.booking_created:
            logger.warning(
                f"Payment {payment_intent_id} has already been used for a booking"
            )
            raise PaymentValidationError(
                "This payment has already been used to create a booking. "
                "Please create a new payment if you need to make another booking."
            )

        logger.info(
            f"✅ Payment {payment_intent_id} has not been used yet (idempotency check passed)"
        )

    async def mark_payment_used_for_booking(self, payment_intent_id: str) -> None:
        """Mark payment as used for booking creation (idempotency tracking).

        Args:
            payment_intent_id: Stripe payment intent ID
        """
        await self.repository.update_transaction_status(
            payment_intent_id=payment_intent_id,
            status=PaymentStatus.SUCCEEDED,  # Keep current status
            booking_created=True,
        )
        logger.info(f"✅ Marked payment {payment_intent_id} as used for booking")

    async def get_transaction_by_payment_intent(
        self, payment_intent_id: str
    ) -> TransactionResponse:
        """Get transaction details by payment intent ID.

        Args:
            payment_intent_id: Stripe payment intent ID

        Returns:
            Transaction response

        Raises:
            ValueError: If transaction not found or access denied
        """
        transaction = await self.repository.get_transaction_by_payment_intent(
            payment_intent_id
        )

        if not transaction:
            raise ValueError(f"Transaction not found for payment {payment_intent_id}")

        # Verify user ownership (security: prevent users from accessing other users' transactions)
        if self.user_id and transaction.user_id:
            transaction_user_id = str(transaction.user_id)
            if transaction_user_id != self.user_id:
                logger.warning(
                    f"User {self.user_id} attempted to access transaction owned by {transaction_user_id}"
                )
                raise ValueError(
                    f"Transaction not found for payment {payment_intent_id}"
                )  # Don't reveal that it exists

        return TransactionResponse(
            id=str(transaction.id),
            stripe_payment_intent_id=(
                transaction.stripe_payment_intent_id or payment_intent_id
            ),
            voya_booking_reference=transaction.voya_booking_reference,
            amount=transaction.amount,
            currency=transaction.currency,
            platform_fee=transaction.platform_fee,
            supplier_amount=transaction.supplier_amount,
            status=transaction.status,
            created_at=transaction.created_at,
            updated_at=transaction.updated_at,
            paid_at=transaction.paid_at,
        )

    async def get_transactions_by_booking(
        self, booking_reference: str
    ) -> list[TransactionResponse]:
        """Get all transactions for a booking reference.

        Used to check for duplicate payments and prevent multiple charges.

        Args:
            booking_reference: Voya booking reference (VOYA-xxx)

        Returns:
            List of transactions for the booking (may be empty)
        """
        transactions = await self.repository.get_all_transactions_by_voya_reference(
            booking_reference
        )

        # Convert to response models
        return [
            TransactionResponse(
                id=str(txn.id),
                stripe_payment_intent_id=txn.stripe_payment_intent_id or "",
                voya_booking_reference=txn.voya_booking_reference,
                amount=txn.amount,
                currency=txn.currency,
                platform_fee=txn.platform_fee,
                supplier_amount=txn.supplier_amount,
                status=txn.status,
                created_at=txn.created_at,
                updated_at=txn.updated_at,
                paid_at=txn.paid_at,
            )
            for txn in transactions
        ]

    async def release_payout(
        self, request: PayoutReleaseRequest, admin_user_id: str
    ) -> PayoutReleaseResponse:
        """Manually release payout to supplier (admin only).

        Args:
            request: Payout release request
            admin_user_id: Admin user ID performing the action

        Returns:
            Payout release confirmation

        Raises:
            PayoutReleaseError: If payout creation fails
            ValueError: If transaction not found
        """
        logger.info(
            f"Admin {admin_user_id} releasing payout for {request.voya_booking_reference}"
        )

        # Get transaction
        transaction = await self.repository.get_transaction_by_voya_reference(
            request.voya_booking_reference
        )

        if not transaction:
            raise ValueError(
                f"Transaction not found for {request.voya_booking_reference}"
            )

        if transaction.status != PaymentStatus.SUCCEEDED:
            raise PayoutReleaseError(
                f"Cannot release payout - payment status: {transaction.status.value}"
            )

        # Create manual transfer to supplier
        try:
            transfer = stripe.Transfer.create(
                amount=transaction.supplier_amount,
                currency=transaction.currency,
                destination=FLIGHTLOGIC_STRIPE_ACCOUNT_ID,
                transfer_group=request.voya_booking_reference,
                metadata={
                    "voya_booking_reference": request.voya_booking_reference,
                    "admin_user_id": admin_user_id,
                    "notes": request.notes or "",
                },
            )

            logger.info(
                f"✅ Transfer created: {transfer.id} for {request.voya_booking_reference}"
            )

        except stripe._error.StripeError as e:
            logger.error(f"Stripe transfer failed: {e}")
            raise PayoutReleaseError(f"Failed to create transfer: {e!s}") from e

        stripe_pi = transaction.stripe_payment_intent_id
        if not stripe_pi:
            raise ValueError(
                f"Transaction for {request.voya_booking_reference} has no Stripe payment intent ID"
            )

        # Update transaction with payout info
        await self.repository.update_transaction_status(
            payment_intent_id=stripe_pi,
            status=PaymentStatus.SUCCEEDED,  # Keep succeeded
            stripe_transfer_id=transfer.id,
            payout_status=PayoutStatus.PAID.value,
            payout_released_at=datetime.now(UTC),
            payout_released_by=admin_user_id,
            payout_notes=request.notes,
        )

        return PayoutReleaseResponse(
            transfer_id=transfer.id,
            voya_booking_reference=request.voya_booking_reference,
            amount=transaction.supplier_amount,
            destination_account=FLIGHTLOGIC_STRIPE_ACCOUNT_ID,
            status=PayoutStatus.PAID,
            created_at=datetime.now(UTC),
            notes=request.notes,
        )

    async def refund_payment(
        self, payment_intent_id: str, reason: str = "booking_failed"
    ) -> str:
        """Refund a payment (typically when booking fails after payment).

        Args:
            payment_intent_id: Stripe payment intent ID to refund
            reason: Reason for refund

        Returns:
            Stripe refund ID

        Raises:
            PaymentValidationError: If refund fails
        """
        logger.warning(
            f"Initiating refund for payment {payment_intent_id} (reason: {reason})"
        )

        try:
            # Create refund through Stripe
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                reason="requested_by_customer",  # Stripe requires specific values
                metadata={"voya_reason": reason, "auto_refund": "true"},
            )

            logger.info(
                f"✅ Refund created: {refund.id} for payment {payment_intent_id}"
            )

            # Update transaction status to refunded
            await self.repository.update_transaction_status(
                payment_intent_id=payment_intent_id,
                status=PaymentStatus.REFUNDED,
                refund_id=refund.id,
                refunded_at=datetime.now(UTC),
            )

            return refund.id

        except stripe._error.StripeError as e:
            logger.error(f"Refund failed for {payment_intent_id}: {e}")
            raise PaymentValidationError(f"Failed to refund payment: {e!s}") from e

    async def check_booking_expiry(
        self, request: BookingExpiryCheckRequest
    ) -> BookingExpiryCheckResponse:
        """Check if booking has expired before allowing payment confirmation.

        This method validates the ticket_time_limit for GDS flights to prevent
        charging users for expired bookings. Should be called by frontend before
        confirming payment with Stripe.

        Args:
            request: Booking expiry check request

        Returns:
            BookingExpiryCheckResponse with validation result
        """
        from app.domains.bookings.service import BookingService

        booking_event = await BookingService.get_latest_booking_by_voya_reference(
            request.voya_booking_reference
        )

        # If no booking event or no ticket_time_limit, booking is valid
        if not booking_event or not booking_event.ticket_time_limit:
            logger.info(
                f"Booking {request.voya_booking_reference} has no expiry limit - valid for payment"
            )
            return BookingExpiryCheckResponse(
                is_valid=True,
                ticket_time_limit=None,
                time_remaining_seconds=None,
                message=None,
            )

        # Check expiry using shared validation logic
        is_valid, time_remaining = validate_ticket_time_limit(
            booking_event.ticket_time_limit
        )

        # Normalize ticket_time_limit for response
        ticket_time_limit_utc = booking_event.ticket_time_limit
        if ticket_time_limit_utc:
            if ticket_time_limit_utc.tzinfo is None:
                ticket_time_limit_utc = ticket_time_limit_utc.replace(tzinfo=UTC)
            else:
                ticket_time_limit_utc = ticket_time_limit_utc.astimezone(UTC)

        if not is_valid:
            current_time_utc = datetime.now(UTC)
            logger.error(
                f"Booking expiry check failed: booking expired for {request.voya_booking_reference}. "
                f"Current time UTC: {current_time_utc.isoformat()}, "
                f"Ticket time limit UTC: {ticket_time_limit_utc.isoformat()}"
            )
            return BookingExpiryCheckResponse(
                is_valid=False,
                ticket_time_limit=ticket_time_limit_utc,
                time_remaining_seconds=0,
                message=f"Booking has expired. The ticket time limit ({ticket_time_limit_utc.isoformat()}) has passed. "
                "Please start a new search. Payment cannot be processed.",
            )

        current_time_utc = datetime.now(UTC)
        logger.info(
            f"Booking expiry check passed for {request.voya_booking_reference}. "
            f"Current time UTC: {current_time_utc.isoformat()}, "
            f"Ticket time limit UTC: {ticket_time_limit_utc.isoformat()}, "
            f"Time remaining: {time_remaining} seconds"
        )

        return BookingExpiryCheckResponse(
            is_valid=True,
            ticket_time_limit=ticket_time_limit_utc,
            time_remaining_seconds=time_remaining,
            message=None,
        )

    async def get_existing_payment_intent(
        self, voya_booking_reference: str
    ) -> PaymentIntentCreateResponse | None:
        """Get existing payment intent for a booking if one exists.

        Used to reuse payment intents when user returns via email link.

        Args:
            voya_booking_reference: VOYA booking reference

        Returns:
            PaymentIntentCreateResponse if valid payment intent exists, None otherwise
        """
        from app.domains.bookings.service import BookingService

        booking_event = await BookingService.get_latest_booking_by_voya_reference(
            voya_booking_reference
        )

        if not booking_event or not booking_event.payment_intent_id:
            logger.debug(
                f"No existing payment intent found for {voya_booking_reference}"
            )
            return None

        payment_intent_id = booking_event.payment_intent_id

        try:
            # Retrieve payment intent from Stripe to check if it's still valid
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            # Only reuse if payment intent is in a reusable state
            # (requires_payment_method, requires_confirmation, or requires_action)
            if payment_intent.status in [
                "requires_payment_method",
                "requires_confirmation",
                "requires_action",
            ]:
                logger.info(
                    f"✅ Found reusable payment intent {payment_intent_id} for {voya_booking_reference} (status: {payment_intent.status})"
                )

                # Get transaction to retrieve platform fee and supplier amount
                transaction = await self.repository.get_transaction_by_payment_intent(
                    payment_intent_id
                )

                if transaction:
                    return PaymentIntentCreateResponse(
                        payment_intent_id=payment_intent.id,
                        client_secret=payment_intent.client_secret or "",
                        amount=transaction.amount,
                        currency=transaction.currency,
                        platform_fee=transaction.platform_fee,
                        supplier_amount=transaction.supplier_amount,
                        publishable_key=settings.STRIPE_PUBLISHABLE_KEY or "",
                    )
                # Transaction not found, but payment intent exists - calculate from payment intent amount
                logger.warning(
                    f"Transaction not found for payment intent {payment_intent_id}, calculating fees from payment intent"
                )
                # Use booking_event.event_type to determine correct fee percentage (FLIGHT=5%, HOTEL=10.5%)
                booking_type = (
                    booking_event.event_type.lower()
                    if booking_event.event_type
                    else "flight"
                )
                platform_fee = self._calculate_platform_fee(
                    payment_intent.amount, booking_type
                )
                supplier_amount = payment_intent.amount - platform_fee

                return PaymentIntentCreateResponse(
                    payment_intent_id=payment_intent.id,
                    client_secret=payment_intent.client_secret or "",
                    amount=payment_intent.amount,
                    currency=payment_intent.currency,
                    platform_fee=platform_fee,
                    supplier_amount=supplier_amount,
                    publishable_key=settings.STRIPE_PUBLISHABLE_KEY or "",
                )
            logger.info(
                f"Payment intent {payment_intent_id} exists but is not reusable (status: {payment_intent.status})"
            )
            return None

        except stripe._error.StripeError as e:
            logger.warning(
                f"Failed to retrieve payment intent {payment_intent_id}: {e}"
            )
            return None

    def _calculate_platform_fee(self, amount: int, booking_type: str = "flight") -> int:
        """Calculate platform fee based on booking type.

        Args:
            amount: Total amount in cents
            booking_type: Type of booking - "flight" (5%) or "hotel" (10.5%)

        Returns:
            Platform fee in cents (rounded)
        """
        if booking_type.lower() == "hotel":
            return int(amount * HOTELS_PLATFORM_FEE_PERCENTAGE)
        # Default to flights (5%)
        return int(amount * FLIGHTS_PLATFORM_FEE_PERCENTAGE)
