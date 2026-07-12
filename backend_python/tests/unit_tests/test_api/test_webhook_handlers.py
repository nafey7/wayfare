"""Tests for Stripe webhook handlers.

Tests webhook signature verification, event routing, and handler behavior.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe
from fastapi import HTTPException

from app.api.webhooks import (
    stripe_webhook,
)

# ==============================================================================
# WEBHOOK ENDPOINT TESTS (Signature Verification & Routing)
# ==============================================================================


class TestWebhookEndpoint:
    """Test webhook endpoint signature verification and routing."""

    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request with webhook payload."""
        request = MagicMock()
        request.body = AsyncMock(
            return_value=json.dumps(
                {
                    "id": "evt_test_123",
                    "type": "payment_intent.succeeded",
                    "data": {
                        "object": {
                            "id": "pi_test_123",
                            "amount": 10000,
                            "currency": "usd",
                            "status": "succeeded",
                            "metadata": {
                                "voya_booking_reference": "VOYA-TEST-001",
                                "user_id": "user123",
                            },
                        }
                    },
                }
            ).encode()
        )
        return request

    @pytest.mark.asyncio
    async def test_webhook_signature_verification_production(self, mock_request):
        """Should reject webhooks without signature in production."""
        with (
            patch("app.api.webhooks.settings") as mock_settings,
            patch("app.api.webhooks.handle_payment_intent_succeeded") as mock_handler,
        ):
            mock_settings.ENVIRONMENT = "production"
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test_secret"

            with pytest.raises(HTTPException) as exc_info:
                await stripe_webhook(mock_request, stripe_signature=None)

            assert exc_info.value.status_code == 401
            assert "signature verification required" in exc_info.value.detail.lower()
            mock_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_webhook_signature_verification_success(self, mock_request):
        """Should verify valid signature and process event."""
        with (
            patch("app.api.webhooks.settings") as mock_settings,
            patch("app.api.webhooks.stripe.Webhook.construct_event") as mock_construct,
            patch("app.api.webhooks.handle_payment_intent_succeeded") as mock_handler,
        ):
            mock_settings.ENVIRONMENT = "production"
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test_secret"

            # Mock successful signature verification
            mock_construct.return_value = {
                "id": "evt_test_123",
                "type": "payment_intent.succeeded",
                "data": {"object": {"id": "pi_test_123"}},
            }

            result = await stripe_webhook(
                mock_request, stripe_signature="valid_signature"
            )

            assert result["status"] == "success"
            assert result["event_id"] == "evt_test_123"
            mock_construct.assert_called_once()
            mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(self, mock_request):
        """Should reject webhooks with invalid signature."""
        with (
            patch("app.api.webhooks.settings") as mock_settings,
            patch("app.api.webhooks.stripe.Webhook.construct_event") as mock_construct,
        ):
            mock_settings.ENVIRONMENT = "production"
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test_secret"

            # Mock signature verification failure
            mock_construct.side_effect = stripe._error.SignatureVerificationError(
                "Invalid signature", sig_header="bad_sig"
            )

            with pytest.raises(HTTPException) as exc_info:
                await stripe_webhook(mock_request, stripe_signature="invalid_signature")

            assert exc_info.value.status_code == 400
            assert "invalid signature" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_webhook_invalid_payload(self, mock_request):
        """Should reject webhooks with invalid JSON payload."""
        with (
            patch("app.api.webhooks.settings") as mock_settings,
            patch("app.api.webhooks.stripe.Webhook.construct_event") as mock_construct,
        ):
            mock_settings.ENVIRONMENT = "production"
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test_secret"

            # Mock payload parsing failure
            mock_construct.side_effect = ValueError("Invalid JSON")

            with pytest.raises(HTTPException) as exc_info:
                await stripe_webhook(mock_request, stripe_signature="valid_signature")

            assert exc_info.value.status_code == 400
            assert "invalid payload" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_webhook_development_mode_skips_verification(self, mock_request):
        """Should skip signature verification in development mode."""
        with (
            patch("app.api.webhooks.settings") as mock_settings,
            patch("app.api.webhooks.handle_payment_intent_succeeded") as mock_handler,
        ):
            mock_settings.ENVIRONMENT = "development"
            mock_settings.STRIPE_WEBHOOK_SECRET = None

            result = await stripe_webhook(mock_request, stripe_signature=None)

            assert result["status"] == "success"
            mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_unhandled_event_type(self, mock_request):
        """Should log warning but return success for unhandled event types."""
        mock_request.body = AsyncMock(
            return_value=json.dumps(
                {
                    "id": "evt_test_123",
                    "type": "customer.created",  # Unhandled event
                    "data": {"object": {}},
                }
            ).encode()
        )

        with patch("app.api.webhooks.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "development"
            mock_settings.STRIPE_WEBHOOK_SECRET = None

            result = await stripe_webhook(mock_request, stripe_signature=None)

            assert result["status"] == "success"
            assert result["event_type"] == "customer.created"

    @pytest.mark.asyncio
    async def test_webhook_handler_exception_returns_success(self, mock_request):
        """Should return success even if handler raises exception (idempotency)."""
        with (
            patch("app.api.webhooks.settings") as mock_settings,
            patch("app.api.webhooks.handle_payment_intent_succeeded") as mock_handler,
        ):
            mock_settings.ENVIRONMENT = "development"
            mock_settings.STRIPE_WEBHOOK_SECRET = None

            # Handler raises exception
            mock_handler.side_effect = Exception("Database error")

            result = await stripe_webhook(mock_request, stripe_signature=None)

            # Should still return success to Stripe (we received the webhook)
            assert result["status"] == "success"
            mock_handler.assert_called_once()


# ==============================================================================
# NOTE: Handler business logic tests removed - now tested in test_webhook_service.py
# ==============================================================================
# The webhook handlers now delegate to PaymentWebhookService, so business logic
# is tested via service layer tests (test_domains/test_payment/test_webhook_service.py).
# This file only tests webhook endpoint signature verification and routing.
