"""Revolut payment service for Revolut Merchant API integration and business logic.

Phase 2: Full Revolut Merchant API integration.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
from bson import ObjectId

from app.core.config import settings
from app.domains.bookings.reference_generator import VoyaReferenceGenerator
from app.domains.revolut_payment.constants import (
    PLATFORM_FEE_PERCENTAGE,
    REVOLUT_MERCHANT_ID,
)
from app.domains.revolut_payment.enums import PaymentStatus, PayoutStatus
from app.domains.revolut_payment.exceptions import (
    RevolutOrderCreationError,
    RevolutPaymentValidationError,
    RevolutPayoutReleaseError,
)
from app.domains.revolut_payment.repository import RevolutPaymentRepository
from app.domains.revolut_payment.schemas import (
    RevolutOrderCreateRequest,
    RevolutOrderCreateResponse,
    RevolutPayoutReleaseRequest,
    RevolutPayoutReleaseResponse,
    RevolutTransactionResponse,
)
from integrations.revolut import RevolutClient

if TYPE_CHECKING:
    from app.domains.user.schemas import UserPublic

logger = logging.getLogger(__name__)


class RevolutPaymentService:
    """Service for Revolut order creation, validation, and payout management.

    Phase 2: Full Revolut Merchant API integration.
    """

    def __init__(
        self, user_id: str | None = None, current_user: "UserPublic | None" = None
    ) -> None:
        """Initialize Revolut payment service.

        Args:
            user_id: Current user ID (optional, required for user-specific operations)
            current_user: Current user object (optional, for customer information)
        """
        self.user_id = user_id
        self.current_user = current_user
        self.repository = RevolutPaymentRepository()
        self.client = RevolutClient()

    async def create_payment_intent(
        self, request: RevolutOrderCreateRequest
    ) -> RevolutOrderCreateResponse:
        """Create Revolut order with 5% platform fee.

        Maps to Stripe PaymentIntent concept - creates a Revolut Order.

        Args:
            request: Order creation request

        Returns:
            Order response with public_order_id for frontend

        Raises:
            RevolutOrderCreationError: If Revolut API call fails
        """
        # Calculate platform fee (5%) and supplier amount
        platform_fee = self._calculate_platform_fee(request.booking_amount)
        supplier_amount = request.booking_amount - platform_fee

        # For hotel: backend generates nanoid voya ref; for flight: use from request or generate (GDS)
        is_hotel = getattr(request, "order_type", "flight") == "hotel"
        is_gds_create_order = False  # True when we generate voya_ref for GDS (new flow)
        if is_hotel and not request.voya_booking_reference:
            from app.database.dependencies import get_database
            from app.domains.bookings.constants import BOOKING_EVENT_COLLECTION

            db = await get_database()
            voya_booking_reference = await VoyaReferenceGenerator.generate_unique(
                db[BOOKING_EVENT_COLLECTION]
            )
            logger.info(
                f"Generated nanoid voya ref for hotel: {voya_booking_reference}"
            )
        elif not request.voya_booking_reference:
            # GDS new flow: backend generates voya_ref before Booking API
            from app.database.dependencies import get_database
            from app.domains.bookings.constants import BOOKING_EVENT_COLLECTION

            db = await get_database()
            voya_booking_reference = await VoyaReferenceGenerator.generate_unique(
                db[BOOKING_EVENT_COLLECTION]
            )
            is_gds_create_order = True
            logger.info(
                f"Generated voya ref for GDS create-order (before Booking API): {voya_booking_reference}"
            )
        else:
            voya_booking_reference = request.voya_booking_reference

        # LCC + valid VOYA ref (e.g. voucher checkout) must not create a PENDING GDS row — that duplicates
        # the LCC BOOKED event on /flights/book and breaks get_external_reference / trip_details.
        is_lcc_flight = not is_hotel and request.carrier_type == "LCC"
        create_pending_gds_flight_event = (
            not is_hotel
            and not is_lcc_flight
            and (
                is_gds_create_order
                or (
                    request.voya_booking_reference is not None
                    and VoyaReferenceGenerator.validate_format(
                        request.voya_booking_reference
                    )
                )
            )
        )

        logger.info(
            f"Creating Revolut order for {voya_booking_reference}: "
            f"total=${request.booking_amount / 100:.2f}, "
            f"fee=${platform_fee / 100:.2f}, "
            f"supplier=${supplier_amount / 100:.2f}"
        )

        try:
            # Build customer object from current_user (from auth token)
            customer = None
            if self.current_user:
                customer_email = self.current_user.email
                # Build full_name from first_name and last_name
                first_name = self.current_user.first_name or ""
                last_name = self.current_user.last_name or ""
                full_name = f"{first_name} {last_name}".strip()
                if not full_name:
                    full_name = "Guest"

                customer = {
                    "email": customer_email,
                    "full_name": full_name,
                }
                logger.info(
                    f"Using customer from auth token: {customer_email}, {full_name}"
                )

            # Create Revolut order via API
            # Flight: industry_type=airline, hotel: industry_type=lodging
            industry_type = "lodging" if is_hotel else "airline"
            description = (
                f"Hotel booking: {voya_booking_reference}"
                if is_hotel
                else f"Flight booking: {voya_booking_reference}"
            )
            order_data = await self.client.create_order(
                amount=request.booking_amount,
                currency=request.currency,
                customer=customer,
                description=description,
                metadata={
                    "voya_booking_reference": voya_booking_reference,
                    "user_id": self.user_id or "unknown",
                    "platform_fee": str(platform_fee),
                    "supplier_amount": str(supplier_amount),
                },
                industry_type=industry_type,
                booking_id=voya_booking_reference,
            )

            order_id_raw = order_data.get("id")
            if order_id_raw is None:
                raise RevolutOrderCreationError(
                    "Revolut order created but missing id in response"
                )
            order_id = str(order_id_raw)
            # Revolut API returns 'token' field (not 'public_id') - this is what the checkout widget needs
            token = order_data.get("token")
            order_state = order_data.get("state")

            if not token:
                logger.error(
                    f"Revolut order response missing 'token' field. Available keys: {list(order_data.keys())}"
                )
                raise RevolutOrderCreationError(
                    "Revolut order created but missing token field in response"
                )

            # Verify order state is valid for checkout
            if order_state and order_state not in ("pending", "authorised"):
                logger.warning(
                    f"⚠️  Revolut order state is '{order_state}' (expected 'pending' or 'authorised')"
                )

            # Use token as public_order_id for the checkout widget
            # The token from Revolut API response is what the widget needs for initialization
            public_order_id = token
            checkout_url = order_data.get("checkout_url")  # May be present in response

            logger.info(
                f"✅ Revolut order created: {order_id} (token: {token}, state: {order_state}) "
                f"for {voya_booking_reference}"
            )
            logger.info(
                f"  📤 Returning token to frontend as public_order_id: {public_order_id}"
            )

            # Log full order data for debugging (first time only to verify structure)
            logger.debug(
                f"Full order response (sanitized): id={order_id}, state={order_state}, "
                f"has_token={bool(token)}, has_checkout_url={bool(checkout_url)}, "
                f"has_industry_data={'industry_data' in order_data}"
            )

            # Verify the order can be retrieved using order_id
            # Note: Token is for widget initialization only - cannot be used for API retrieval
            # The 404 when retrieving by token is EXPECTED and normal
            try:
                # Retrieve the order using order_id (token cannot be used for API retrieval)
                verified_order = await self.client.get_order(
                    order_id
                )  # Use order_id, not token
                verified_state = verified_order.get("state")
                verified_token = verified_order.get("token")
                logger.debug(
                    f"Order verification (by order_id): retrieved order, state={verified_state}, "
                    f"token_matches={verified_token == token if verified_token else 'N/A'}"
                )

                # Check if industry_data is present in verified order
                if "industry_data" in verified_order:
                    logger.debug(
                        f"  Verified order has industry_data: {verified_order.get('industry_data')}"
                    )
                else:
                    logger.warning(
                        "  ⚠️  Verified order missing industry_data - this might cause 'order not valid' error"
                    )

                if verified_state != order_state:
                    logger.warning(
                        f"⚠️  Order state mismatch: creation returned '{order_state}', "
                        f"retrieval returned '{verified_state}'"
                    )
            except Exception as e:
                logger.warning(f"⚠️  Could not verify order after creation: {e}")
                # Note: This is just a verification step - the order might still be valid for the widget

            # Log available fields for debugging
            if checkout_url:
                logger.debug(f"Revolut checkout_url present: {checkout_url[:50]}...")

            # Warn if we see merchant-mgmt URLs (these are internal, not for customer checkout)
            if checkout_url and "merchant-mgmt.revolut.com" in checkout_url:
                logger.warning(
                    f"⚠️  Order response contains merchant-mgmt URL (internal URL, not for customer checkout): "
                    f"{checkout_url}. This should not be used for redirecting customers."
                )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Revolut API error: {e.response.status_code} - {e.response.text}"
            )
            raise RevolutOrderCreationError(
                f"Failed to create Revolut order: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error creating Revolut order: {e}")
            raise RevolutOrderCreationError(
                f"Failed to create Revolut order: {e!s}"
            ) from e

        # Log transaction in MongoDB
        # Note: TransactionModel will be updated in Phase 5 to support Revolut fields
        # For now, we store revolut_order_id in a way that works with the current model
        transaction_data = {
            "stripe_payment_intent_id": f"revolut_{order_id}",  # Temporary mapping
            "voya_booking_reference": voya_booking_reference,
            "user_id": ObjectId(self.user_id) if self.user_id else None,
            "amount": request.booking_amount,
            "currency": request.currency,
            "platform_fee": platform_fee,
            "supplier_amount": supplier_amount,
            "destination_account_id": REVOLUT_MERCHANT_ID or "",
            "status": PaymentStatus.PENDING,
            "payment_provider": "revolut",  # Will be added to model in Phase 5
            "revolut_order_id": order_id,  # Will be added to model in Phase 5
        }

        transaction = await self.repository.create_transaction(transaction_data)

        logger.info(f"Transaction logged: {transaction.id}")

        # Create PENDING GDS event (new flow) or update existing event with order_id
        from app.domains.bookings.service import BookingService

        if create_pending_gds_flight_event and self.user_id:
            # GDS new flow: create PENDING event right after Revolut order
            try:
                contact_email = None
                if self.current_user and self.current_user.email:
                    contact_email = self.current_user.email
                amount = request.booking_amount / 100.0
                await BookingService.create_pending_gds_event(
                    user_id=self.user_id,
                    voya_booking_reference=voya_booking_reference,
                    payment_intent_id=order_id,
                    contact_email=contact_email,
                    amount=amount,
                    voucher_redemption_id=request.voucher_redemption_id,
                )
                logger.info(
                    f"✅ Created PENDING GDS booking event for {voya_booking_reference}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to create PENDING GDS event for {voya_booking_reference}: {e}"
                )
                await self._cleanup_revolut_order_after_pending_gds_event_failure(
                    order_id
                )
                raise RevolutOrderCreationError(
                    f"Order created but failed to create booking record: {e}"
                ) from e
        elif is_lcc_flight:
            # LCC (often with flight promo): booking_events + payment_intent_id are created on POST /flights/book, not here.
            pass
        else:
            # GDS / hotel / multicity: attach order id to existing row when present
            try:
                await BookingService.update_payment_intent_id(
                    voya_booking_reference, order_id
                )
                logger.info(
                    f"✅ Stored Revolut order_id {order_id} in booking event for {voya_booking_reference}"
                )
            except ValueError as e:
                logger.debug(
                    "Could not store order_id (booking may not exist yet): %s voya=%s",
                    e,
                    voya_booking_reference,
                )
            except Exception as e:
                logger.warning(
                    "Failed to store order_id in booking event: %s voya=%s",
                    e,
                    voya_booking_reference,
                )

        # Return response with token as public_order_id (this is what the widget needs)
        public_key = settings.REVOLUT_PUBLIC_KEY or ""
        response = RevolutOrderCreateResponse(
            order_id=order_id,
            public_order_id=public_order_id,  # This is the token from Revolut API
            amount=request.booking_amount,
            currency=request.currency,
            platform_fee=platform_fee,
            supplier_amount=supplier_amount,
            public_key=public_key,  # Required config for widget API calls
            voya_booking_reference=voya_booking_reference,
        )

        logger.info(
            f"  ✅ Returning to frontend - public_order_id (token): {public_order_id}"
        )
        logger.info(
            f"  🔑 Public key status: {'✅ Present' if public_key else '❌ MISSING - widget may show 403 errors'}"
        )
        if public_key:
            logger.debug(
                f"  Public key preview: {public_key[:20]}... (length: {len(public_key)})"
            )
        logger.debug(
            f"  Full response data: order_id={order_id}, public_order_id={public_order_id}"
        )

        return response

    async def validate_payment_succeeded(self, order_id: str) -> None:
        """Validate that payment has succeeded before allowing booking.

        Maps to Stripe payment_intent.succeeded validation - checks Revolut ORDER_COMPLETED.

        Args:
            order_id: Revolut order ID (can be public_id or internal id)

        Raises:
            RevolutPaymentValidationError: If payment has not succeeded
        """
        logger.info(f"Validating Revolut payment: {order_id}")

        try:
            # Retrieve order from Revolut API
            order_data = await self.client.get_order(order_id)
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to retrieve Revolut order: {e.response.status_code}")
            raise RevolutPaymentValidationError(
                f"Payment validation failed: Could not retrieve order - {e.response.status_code}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error validating Revolut payment: {e}")
            raise RevolutPaymentValidationError(
                f"Payment validation failed: {e!s}"
            ) from e

        # Map Revolut order state to payment status
        # Revolut states: PENDING, AUTHORISED, PROCESSING, COMPLETED, CANCELLED, FAILED
        order_state = order_data.get("state", "").upper()

        if order_state == "COMPLETED":
            logger.info(
                f"✅ Revolut payment {order_id} validated successfully (COMPLETED)"
            )
            return

        if order_state in ("PENDING", "AUTHORISED", "PROCESSING"):
            logger.warning(
                f"Revolut payment {order_id} not completed yet (state: {order_state})"
            )
            raise RevolutPaymentValidationError(
                f"Payment not completed. Current state: {order_state}"
            )

        logger.error(
            f"Revolut payment {order_id} failed or cancelled (state: {order_state})"
        )
        raise RevolutPaymentValidationError(
            f"Payment not completed. State: {order_state}"
        )

    async def check_payment_not_used(self, order_id: str) -> None:
        """Check that payment has not already been used for a booking (idempotency).

        Args:
            order_id: Revolut order ID

        Raises:
            RevolutPaymentValidationError: If payment already used for booking
        """
        transaction = await self.repository.get_transaction_by_order_id(order_id)

        if not transaction:
            # Transaction not found - this is okay, it might be a demo payment
            # or transaction creation might be delayed
            logger.warning(
                f"Revolut transaction not found for order {order_id} during idempotency check"
            )
            return

        if transaction.booking_created:
            logger.warning(
                f"Revolut payment {order_id} has already been used for a booking"
            )
            raise RevolutPaymentValidationError(
                "This payment has already been used to create a booking. "
                "Please create a new payment if you need to make another booking."
            )

        logger.info(
            f"✅ Revolut payment {order_id} has not been used yet (idempotency check passed)"
        )

    async def mark_payment_used_for_booking(self, order_id: str) -> None:
        """Mark payment as used for booking creation (idempotency tracking).

        Args:
            order_id: Revolut order ID
        """
        await self.repository.update_transaction_status(
            order_id=order_id,
            status=PaymentStatus.SUCCEEDED,  # Keep current status
            booking_created=True,
        )
        logger.info(f"✅ Marked Revolut payment {order_id} as used for booking")

    async def get_transaction_by_payment_intent(
        self, order_id: str
    ) -> RevolutTransactionResponse:
        """Get transaction details by Revolut order ID.

        Args:
            order_id: Revolut order ID

        Returns:
            Transaction response

        Raises:
            ValueError: If transaction not found or access denied
        """
        transaction = await self.repository.get_transaction_by_order_id(order_id)

        if not transaction:
            raise ValueError(f"Transaction not found for Revolut order {order_id}")

        # Verify user ownership (security: prevent users from accessing other users' transactions)
        if self.user_id and transaction.user_id:
            transaction_user_id = str(transaction.user_id)
            if transaction_user_id != self.user_id:
                logger.warning(
                    f"User {self.user_id} attempted to access transaction owned by {transaction_user_id}"
                )
                raise ValueError(
                    f"Transaction not found for order {order_id}"
                )  # Don't reveal that it exists

        # Extract revolut_order_id from transaction
        revolut_order_id = ""
        if hasattr(transaction, "revolut_order_id") and transaction.revolut_order_id:
            revolut_order_id = transaction.revolut_order_id
        elif hasattr(transaction, "stripe_payment_intent_id"):
            # Handle temporary mapping format from Phase 2
            pi_id = transaction.stripe_payment_intent_id
            if pi_id and pi_id.startswith("revolut_"):
                revolut_order_id = pi_id.replace("revolut_", "", 1)

        return RevolutTransactionResponse(
            id=str(transaction.id),
            revolut_order_id=revolut_order_id,
            voya_booking_reference=transaction.voya_booking_reference or "",
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
    ) -> list[RevolutTransactionResponse]:
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
        result = []
        for txn in transactions:
            # Extract revolut_order_id from transaction
            revolut_order_id = ""
            if hasattr(txn, "revolut_order_id") and txn.revolut_order_id:
                revolut_order_id = txn.revolut_order_id
            elif hasattr(txn, "stripe_payment_intent_id"):
                # Handle temporary mapping format from Phase 2
                pi_id = txn.stripe_payment_intent_id
                if pi_id and pi_id.startswith("revolut_"):
                    revolut_order_id = pi_id.replace("revolut_", "", 1)

            result.append(
                RevolutTransactionResponse(
                    id=str(txn.id),
                    revolut_order_id=revolut_order_id,
                    voya_booking_reference=txn.voya_booking_reference or "",
                    amount=txn.amount,
                    currency=txn.currency,
                    platform_fee=txn.platform_fee,
                    supplier_amount=txn.supplier_amount,
                    status=txn.status,
                    created_at=txn.created_at,
                    updated_at=txn.updated_at,
                    paid_at=txn.paid_at,
                )
            )
        return result

    async def get_existing_order(
        self, voya_booking_reference: str
    ) -> RevolutOrderCreateResponse | None:
        """Get existing Revolut order for a booking if one exists.

        Used to reuse orders when user returns via email link.
        Fetches order details from Revolut API using order_id stored in booking_event.

        Args:
            voya_booking_reference: VOYA booking reference

        Returns:
            RevolutOrderCreateResponse if valid order exists, None otherwise
        """
        from app.domains.bookings.service import BookingService

        booking_event = await BookingService.get_latest_booking_by_voya_reference(
            voya_booking_reference
        )

        if not booking_event or not booking_event.payment_intent_id:
            logger.debug(
                f"No existing Revolut order found for {voya_booking_reference}"
            )
            return None

        # payment_intent_id field stores the Revolut order_id
        order_id = booking_event.payment_intent_id

        try:
            # Retrieve order from Revolut API to get current status and token
            order_data = await self.client.get_order(order_id)

            # Check if order is in a reusable state (pending, authorised)
            order_state = order_data.get("state", "").upper()
            if order_state not in ("PENDING", "AUTHORISED"):
                logger.info(
                    f"Revolut order {order_id} exists but is not reusable (state: {order_state})"
                )
                return None

            logger.info(
                f"✅ Found reusable Revolut order {order_id} for {voya_booking_reference} (state: {order_state})"
            )

            # Extract token from order details (required for widget initialization)
            token = order_data.get("token")
            if not token:
                logger.warning(
                    f"Revolut order {order_id} missing token field - cannot initialize widget"
                )
                return None

            # Get amount and currency from order
            amount = order_data.get("amount", 0)
            currency = order_data.get("currency", "usd").lower()

            # Extract platform fee and supplier amount from metadata or calculate
            metadata = order_data.get("metadata", {})
            platform_fee = None
            supplier_amount = None

            if metadata.get("platform_fee"):
                platform_fee = int(metadata.get("platform_fee", 0))
            if metadata.get("supplier_amount"):
                supplier_amount = int(metadata.get("supplier_amount", 0))

            # If metadata doesn't have breakdown, calculate from amount (5% platform fee)
            if platform_fee is None or supplier_amount is None:
                platform_fee = self._calculate_platform_fee(amount)
                supplier_amount = amount - platform_fee
                logger.debug(
                    f"Calculated platform fee from order amount: fee={platform_fee}, supplier={supplier_amount}"
                )

            # Get transaction to verify amounts match (optional verification)
            transaction = await self.repository.get_transaction_by_order_id(order_id)
            if transaction:
                # Use transaction amounts if available (more reliable)
                platform_fee = transaction.platform_fee
                supplier_amount = transaction.supplier_amount
                logger.debug(
                    f"Using amounts from transaction: fee={platform_fee}, supplier={supplier_amount}"
                )

            public_key = settings.REVOLUT_PUBLIC_KEY or ""

            return RevolutOrderCreateResponse(
                order_id=order_id,
                public_order_id=token,  # Token is used for widget initialization
                amount=amount,
                currency=currency,
                platform_fee=platform_fee,
                supplier_amount=supplier_amount,
                public_key=public_key,
                voya_booking_reference=voya_booking_reference,
            )

        except httpx.HTTPStatusError as e:
            logger.warning(
                f"Failed to retrieve Revolut order {order_id}: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as e:
            logger.warning(f"Unexpected error retrieving Revolut order {order_id}: {e}")
            return None

    async def release_payout(
        self, request: RevolutPayoutReleaseRequest, admin_user_id: str
    ) -> RevolutPayoutReleaseResponse:
        """Manually release payout to supplier (admin only).

        Maps to Stripe Transfer.create() - creates a Revolut payout.

        Args:
            request: Payout release request
            admin_user_id: Admin user ID performing the action

        Returns:
            Payout release confirmation

        Raises:
            RevolutPayoutReleaseError: If payout creation fails
            ValueError: If transaction not found
        """
        logger.info(
            f"Admin {admin_user_id} releasing Revolut payout for {request.voya_booking_reference}"
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
            raise RevolutPayoutReleaseError(
                f"Cannot release payout - payment status: {transaction.status.value}"
            )

        # Create manual payout to supplier via Revolut API
        try:
            payout_data = await self.client.create_payout(
                amount=transaction.supplier_amount,
                currency=transaction.currency,
                description=f"Payout for {request.voya_booking_reference}",
                metadata={
                    "voya_booking_reference": request.voya_booking_reference,
                    "admin_user_id": admin_user_id,
                    "notes": request.notes or "",
                },
            )

            payout_id_raw = payout_data.get("id")
            payout_id = str(payout_id_raw) if payout_id_raw is not None else ""
            logger.info(
                f"✅ Revolut payout created: {payout_id} for {request.voya_booking_reference}"
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Revolut payout API error: {e.response.status_code} - {e.response.text}"
            )
            raise RevolutPayoutReleaseError(
                f"Failed to create payout: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error creating Revolut payout: {e}")
            raise RevolutPayoutReleaseError(f"Failed to create payout: {e!s}") from e

        # Update transaction with payout info
        # Get the actual order_id from transaction (stored in revolut_order_id field or derived)
        order_id = getattr(transaction, "revolut_order_id", None)
        if not order_id and hasattr(transaction, "stripe_payment_intent_id"):
            # Extract from temporary mapping format
            pi_id = transaction.stripe_payment_intent_id
            if pi_id and pi_id.startswith("revolut_"):
                order_id = pi_id.replace("revolut_", "", 1)

        if order_id:
            await self.repository.update_transaction_status(
                order_id=order_id,
                status=PaymentStatus.SUCCEEDED,  # Keep succeeded
                revolut_payout_id=payout_id,  # Will be added to model in Phase 5
                payout_status=PayoutStatus.PAID.value,
                payout_released_at=datetime.now(UTC),
                payout_released_by=admin_user_id,
                payout_notes=request.notes,
            )

        return RevolutPayoutReleaseResponse(
            payout_id=payout_id,
            voya_booking_reference=request.voya_booking_reference,
            amount=transaction.supplier_amount,
            destination_account=REVOLUT_MERCHANT_ID or "",
            status=PayoutStatus.PAID,
            created_at=datetime.now(UTC),
            notes=request.notes,
        )

    async def refund_payment(
        self, order_id: str, reason: str = "booking_failed"
    ) -> str:
        """Refund a payment (typically when booking fails after payment).

        Maps to Stripe Refund.create() - creates a Revolut refund.

        Args:
            order_id: Revolut order ID to refund
            reason: Reason for refund

        Returns:
            Revolut refund ID

        Raises:
            RevolutPaymentValidationError: If refund fails
        """
        logger.warning(
            f"Initiating Revolut refund for order {order_id} (reason: {reason})"
        )

        try:
            # Create refund through Revolut API
            refund_data = await self.client.create_refund(
                order_id=order_id,
                description=f"Refund: {reason}",
                metadata={"voya_reason": reason, "auto_refund": "true"},
            )

            refund_id_raw = refund_data.get("id")
            refund_id = str(refund_id_raw) if refund_id_raw is not None else ""
            logger.info(f"✅ Revolut refund created: {refund_id} for order {order_id}")

            # Update transaction status to refunded
            await self.repository.update_transaction_status(
                order_id=order_id,
                status=PaymentStatus.REFUNDED,
                refund_id=refund_id,  # Will be added to model in Phase 5
                refunded_at=datetime.now(UTC),
            )

            return refund_id

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Revolut refund API error: {e.response.status_code} - {e.response.text}"
            )
            raise RevolutPaymentValidationError(
                f"Failed to refund payment: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error creating Revolut refund: {e}")
            raise RevolutPaymentValidationError(
                f"Failed to refund payment: {e!s}"
            ) from e

    async def _cleanup_revolut_order_after_pending_gds_event_failure(
        self, order_id: str
    ) -> None:
        """Best-effort Revolut cancel + local transaction status after PENDING event fails.

        The Revolut order and Mongo transaction are created before the booking event; if
        event creation fails, cancel the order via API so it is not left as a stray
        pending checkout. Cancellation failures are logged (order may still expire per
        Revolut lifecycle rules).
        """
        try:
            await self.client.cancel_order(order_id)
        except Exception as cancel_err:
            logger.warning(
                "Could not cancel Revolut order %s after PENDING GDS event failure: %s",
                order_id,
                cancel_err,
            )
        await self.repository.update_transaction_status(
            order_id=order_id,
            status=PaymentStatus.CANCELLED,
        )

    def _calculate_platform_fee(self, amount: int) -> int:
        """Calculate 5% platform fee.

        Args:
            amount: Total amount in cents

        Returns:
            Platform fee in cents (rounded)
        """
        return int(amount * PLATFORM_FEE_PERCENTAGE)
