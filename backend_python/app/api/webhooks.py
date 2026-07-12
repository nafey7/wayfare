"""Webhook endpoints for external service integrations."""

import hashlib
import hmac
import json
import logging
from typing import Any

import stripe
from fastapi import APIRouter, Header, HTTPException, Request

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
) -> dict[str, Any]:
    """Handle Stripe webhook events.

    This endpoint receives webhook events from Stripe for payment processing,
    account updates, and transfer notifications.

    Configured Events:
    - payment_intent.succeeded
    - payment_intent.payment_failed
    - charge.succeeded
    - charge.failed
    - transfer.created
    - transfer.updated
    - account.updated
    - account.application.deauthorized
    """
    payload = await request.body()

    logger.info("=" * 80)
    logger.info("STRIPE WEBHOOK RECEIVED")
    logger.info("=" * 80)
    logger.info(f"Payload size: {len(payload)} bytes")
    logger.info(f"Signature present: {bool(stripe_signature)}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Get webhook secret from settings
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    # SECURITY: Enforce signature verification in production
    if not webhook_secret or not stripe_signature:
        if settings.ENVIRONMENT == "production":
            logger.error(
                "❌ Webhook signature verification required in production but missing "
                f"(secret={'configured' if webhook_secret else 'missing'}, "
                f"signature={'present' if stripe_signature else 'missing'})"
            )
            raise HTTPException(
                status_code=401,
                detail="Webhook signature verification required in production",
            )

        # Development/staging: Allow skipping for testing
        logger.warning(
            f"⚠️  DEVELOPMENT MODE: Webhook signature verification SKIPPED "
            f"(secret={'configured' if webhook_secret else 'missing'}, "
            f"signature={'present' if stripe_signature else 'missing'})"
        )
        event = json.loads(payload)
    else:
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, webhook_secret
            )
            logger.info("✅ Webhook signature verified")
        except ValueError as e:
            logger.error(f"❌ Invalid payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload") from e
        except stripe._error.SignatureVerificationError as e:
            logger.error(f"❌ Invalid signature: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature") from e

    # Extract event details
    event_type = event.get("type")
    event_id = event.get("id")
    event_data = event.get("data", {}).get("object", {})

    logger.info(f"Event ID: {event_id}")
    logger.info(f"Event Type: {event_type}")
    logger.info(f"Event Data Keys: {list(event_data.keys())}")

    # Handle different event types
    try:
        if event_type == "payment_intent.succeeded":
            await handle_payment_intent_succeeded(event_data)

        elif event_type == "payment_intent.payment_failed":
            await handle_payment_intent_failed(event_data)

        elif event_type == "charge.succeeded":
            await handle_charge_succeeded(event_data)

        elif event_type == "charge.failed":
            await handle_charge_failed(event_data)

        elif event_type == "transfer.created":
            await handle_transfer_created(event_data)

        elif event_type == "transfer.updated":
            await handle_transfer_updated(event_data)

        elif event_type == "account.updated":
            await handle_account_updated(event_data)

        elif event_type == "account.application.deauthorized":
            await handle_account_deauthorized(event_data)

        else:
            logger.warning(f"⚠️  Unhandled event type: {event_type}")

    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}", exc_info=True)
        # Don't return error to Stripe - we've received the webhook
        # Just log the error for debugging

    logger.info("✅ Webhook processed successfully")
    logger.info("=" * 80)

    return {"status": "success", "event_id": event_id, "event_type": event_type}


# ==============================================================================
# EVENT HANDLERS - Delegate to PaymentWebhookService
# ==============================================================================


async def handle_payment_intent_succeeded(payment_intent: dict[str, Any]) -> None:
    """Handle successful payment intent - delegate to service."""
    from app.domains.payment.webhook_service import PaymentWebhookService

    service = PaymentWebhookService()
    await service.process_payment_succeeded(payment_intent)


async def handle_payment_intent_failed(payment_intent: dict[str, Any]) -> None:
    """Handle failed payment intent - delegate to service."""
    from app.domains.payment.webhook_service import PaymentWebhookService

    service = PaymentWebhookService()
    await service.process_payment_failed(payment_intent)


async def handle_charge_succeeded(charge: dict[str, Any]) -> None:
    """Handle successful charge - delegate to service."""
    from app.domains.payment.webhook_service import PaymentWebhookService

    service = PaymentWebhookService()
    await service.process_charge_succeeded(charge)


async def handle_charge_failed(charge: dict[str, Any]) -> None:
    """Handle failed charge - delegate to service."""
    from app.domains.payment.webhook_service import PaymentWebhookService

    service = PaymentWebhookService()
    await service.process_charge_failed(charge)


async def handle_transfer_created(transfer: dict[str, Any]) -> None:
    """Handle transfer creation - delegate to service."""
    from app.domains.payment.webhook_service import PaymentWebhookService

    service = PaymentWebhookService()
    await service.process_transfer_created(transfer)


async def handle_transfer_updated(transfer: dict[str, Any]) -> None:
    """Handle transfer update - delegate to service."""
    from app.domains.payment.webhook_service import PaymentWebhookService

    service = PaymentWebhookService()
    await service.process_transfer_updated(transfer)


async def handle_account_updated(account: dict[str, Any]) -> None:
    """Handle Stripe Connect account updates - delegate to service."""
    from app.domains.payment.webhook_service import PaymentWebhookService

    service = PaymentWebhookService()
    await service.process_account_updated(account)


async def handle_account_deauthorized(account: dict[str, Any]) -> None:
    """Handle Stripe Connect account deauthorization - delegate to service."""
    from app.domains.payment.webhook_service import PaymentWebhookService

    service = PaymentWebhookService()
    await service.process_account_deauthorized(account)


# ==============================================================================
# REVOLUT WEBHOOK ENDPOINT
# ==============================================================================


def verify_revolut_webhook_signature(
    payload: bytes, signature: str, timestamp: str, secret: str
) -> bool:
    """Verify Revolut webhook signature using HMAC SHA-256.

    Revolut webhook signature format:
    - Payload to sign: v1.<timestamp>.<raw_payload>
    - Signature header: Revolut-Signature: v1=<signature>
    - Timestamp header: Revolut-Request-Timestamp: <timestamp>

    Args:
        payload: Raw webhook payload bytes
        signature: Signature from Revolut-Signature header (format: v1=<signature>)
        timestamp: Timestamp from Revolut-Request-Timestamp header
        secret: Webhook signing secret

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Extract signature value (remove "v1=" prefix)
        if not signature.startswith("v1="):
            logger.error("Invalid Revolut signature format - must start with 'v1='")
            return False

        received_signature = signature[3:]  # Remove "v1=" prefix

        # Prepare payload to sign: v1.<timestamp>.<raw_payload>
        payload_str = payload.decode("utf-8")
        payload_to_sign = f"v1.{timestamp}.{payload_str}"

        # Compute expected signature using HMAC SHA-256
        expected_signature = hmac.new(
            bytes(secret, "utf-8"),
            msg=bytes(payload_to_sign, "utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        # Compare signatures using constant-time comparison
        return hmac.compare_digest(received_signature, expected_signature)

    except Exception as e:
        logger.error(f"Error verifying Revolut webhook signature: {e}")
        return False


@router.post("/revolut")
async def revolut_webhook(
    request: Request,
    revolut_signature: str = Header(None, alias="Revolut-Signature"),
    revolut_timestamp: str = Header(None, alias="Revolut-Request-Timestamp"),
) -> dict[str, Any]:
    """Handle Revolut webhook events.

    This endpoint receives webhook events from Revolut for payment processing,
    refunds, and payout notifications.

    Configured Events:
    - ORDER_COMPLETED (maps to payment_intent.succeeded)
    - ORDER_FAILED (maps to payment_intent.payment_failed)
    - REFUND_COMPLETED
    - PAYOUT_COMPLETED

    Webhook Signature Verification:
    - Uses HMAC SHA-256 with REVOLUT_WEBHOOK_SECRET
    - Format: v1.<timestamp>.<payload>
    - Headers: Revolut-Signature, Revolut-Request-Timestamp
    """
    payload = await request.body()

    logger.info("=" * 80)
    logger.info("REVOLUT WEBHOOK RECEIVED")
    logger.info("=" * 80)
    logger.info(f"Payload size: {len(payload)} bytes")
    logger.info(f"Signature present: {bool(revolut_signature)}")
    logger.info(f"Timestamp present: {bool(revolut_timestamp)}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Get webhook secret from settings
    webhook_secret = settings.REVOLUT_WEBHOOK_SECRET

    # SECURITY: Enforce signature verification in production
    if not webhook_secret or not revolut_signature or not revolut_timestamp:
        if settings.ENVIRONMENT == "production":
            logger.error(
                "❌ Webhook signature verification required in production but missing "
                f"(secret={'configured' if webhook_secret else 'missing'}, "
                f"signature={'present' if revolut_signature else 'missing'}, "
                f"timestamp={'present' if revolut_timestamp else 'missing'})"
            )
            raise HTTPException(
                status_code=401,
                detail="Webhook signature verification required in production",
            )

        # Development/staging: Allow skipping for testing
        logger.warning(
            f"⚠️  DEVELOPMENT MODE: Webhook signature verification SKIPPED "
            f"(secret={'configured' if webhook_secret else 'missing'}, "
            f"signature={'present' if revolut_signature else 'missing'}, "
            f"timestamp={'present' if revolut_timestamp else 'missing'})"
        )
        event_data = json.loads(payload)
    else:
        # Verify webhook signature
        is_valid = verify_revolut_webhook_signature(
            payload, revolut_signature, revolut_timestamp, webhook_secret
        )

        if not is_valid:
            logger.error("❌ Invalid Revolut webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")

        logger.info("✅ Revolut webhook signature verified")
        event_data = json.loads(payload)

    # Log full payload at INFO level for visibility
    logger.info("Revolut webhook payload: %s", json.dumps(event_data, indent=2))

    # Extract event details
    # Revolut webhook format: {"event": "ORDER_COMPLETED", "order_id": "..."}
    # Note: Field is "event", not "type"
    event_type = event_data.get("event") or event_data.get(
        "type"
    )  # Support both formats
    event_id = event_data.get("id") or event_data.get("event_id")
    order_id = event_data.get("order_id")

    # For webhooks that only contain order_id, we need to fetch full order details
    # The event_object will be the full payload or fetched order details
    event_object = event_data.get(
        "data", event_data
    )  # Some events have data, others are direct

    # If webhook only contains order_id (not full order object), fetch order details
    if order_id and not event_object.get("id") and not event_object.get("amount"):
        logger.info(
            f"📥 Webhook payload only contains order_id, fetching full order details: {order_id}"
        )
        try:
            from integrations.revolut import RevolutClient

            revolut_client = RevolutClient()
            full_order = await revolut_client.get_order(order_id)
            event_object = full_order
            logger.info(f"✅ Fetched full order details for {order_id}")
            logger.debug(
                f"Order details: {json.dumps(full_order, indent=2, default=str)}"
            )
        except Exception as fetch_error:
            logger.error(
                f"❌ Failed to fetch order details for {order_id}: {fetch_error}"
            )
            # Fallback: Create minimal order object with just the ID
            event_object = {"id": order_id, **event_data}
    elif order_id and not event_object.get("id"):
        # If we have order_id but event_object doesn't have id, add it
        event_object = {"id": order_id, **event_object}

    logger.info(f"Event ID: {event_id}")
    logger.info(f"Event Type: {event_type}")
    logger.info(f"Order ID: {order_id}")
    logger.info(
        f"Event Data Keys: {list(event_object.keys()) if isinstance(event_object, dict) else 'N/A'}"
    )

    # Handle different event types
    try:
        if event_type == "ORDER_AUTHORISED":
            # ORDER_AUTHORISED happens before ORDER_COMPLETED
            # We might want to log this but not process payment yet
            logger.info(f"📝 Order authorised (pre-completion): {order_id}")
            # Optionally: Update transaction status to "processing" or similar
            # For now, we'll just log it and wait for ORDER_COMPLETED

        elif event_type == "ORDER_COMPLETED":
            await handle_revolut_order_completed(event_object)

        elif event_type == "ORDER_FAILED":
            await handle_revolut_order_failed(event_object)

        elif event_type == "REFUND_COMPLETED":
            await handle_revolut_refund_completed(event_object)

        elif event_type == "PAYOUT_COMPLETED":
            await handle_revolut_payout_completed(event_object)

        else:
            logger.warning(f"⚠️  Unhandled Revolut event type: {event_type}")

    except Exception as e:
        logger.error(f"❌ Error processing Revolut webhook: {e}", exc_info=True)
        # Don't return error to Revolut - we've received the webhook
        # Just log the error for debugging

    logger.info("✅ Revolut webhook processed successfully")
    logger.info("=" * 80)

    return {"status": "success", "event_id": event_id, "event_type": event_type}


# ==============================================================================
# REVOLUT EVENT HANDLERS - Delegate to RevolutWebhookService
# ==============================================================================


async def handle_revolut_order_completed(order: dict[str, Any]) -> None:
    """Handle completed order - delegate to service."""
    from app.domains.revolut_payment.webhook_service import RevolutWebhookService

    service = RevolutWebhookService()
    await service.process_order_completed(order)


async def handle_revolut_order_failed(order: dict[str, Any]) -> None:
    """Handle failed order - delegate to service."""
    from app.domains.revolut_payment.webhook_service import RevolutWebhookService

    service = RevolutWebhookService()
    await service.process_order_failed(order)


async def handle_revolut_refund_completed(refund: dict[str, Any]) -> None:
    """Handle completed refund - delegate to service."""
    from app.domains.revolut_payment.webhook_service import RevolutWebhookService

    service = RevolutWebhookService()
    await service.process_refund_completed(refund)


async def handle_revolut_payout_completed(payout: dict[str, Any]) -> None:
    """Handle completed payout - delegate to service."""
    from app.domains.revolut_payment.webhook_service import RevolutWebhookService

    service = RevolutWebhookService()
    await service.process_payout_completed(payout)
