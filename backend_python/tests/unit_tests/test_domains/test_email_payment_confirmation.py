"""Unit tests for payment confirmation email builder."""

import pytest

from app.domains.email.builder import EmailBuilder


class TestBuildPaymentConfirmation:
    """Test _build_payment_confirmation method."""

    def test_build_payment_confirmation_non_hotel_booking(self):
        """Test payment confirmation email for non-hotel booking (flight)."""
        context = {
            "voya_booking_reference": "VOYA-2025-00001",
            "amount": 250.50,
            "currency": "USD",
            "payment_method": "Credit Card",
            "transaction_id": "pi_test_123456789",
            "booking_details": {},  # No hotel details
        }

        email_spec = EmailBuilder._build_payment_confirmation(context)

        assert email_spec is not None
        assert "VOYA-2025-00001" in email_spec.subject
        assert "Payment Confirmed" in email_spec.title
        assert "VOYA-2025-00001" in email_spec.body_content
        assert "USD 250.50" in email_spec.body_content
        assert "pi_test_123456789" in email_spec.body_content
        # Should not contain hotel name row for non-hotel bookings
        assert "Hotel:" not in email_spec.body_content

    def test_build_payment_confirmation_hotel_booking_with_name(self):
        """Test payment confirmation email for hotel booking with valid hotel name."""
        context = {
            "voya_booking_reference": "VOYA-2025-00002",
            "amount": 150.00,
            "currency": "USD",
            "payment_method": "Credit Card",
            "transaction_id": "pi_test_987654321",
            "booking_details": {
                "hotel_id": "hotel_123",
                "check_in": "2025-01-15",
                "hotel_name": "Grand Hotel Paris",
            },
        }

        email_spec = EmailBuilder._build_payment_confirmation(context)

        assert email_spec is not None
        assert "VOYA-2025-00002" in email_spec.subject
        assert "Grand Hotel Paris" in email_spec.body_content
        assert "Hotel:" in email_spec.body_content

    def test_build_payment_confirmation_hotel_booking_without_name(self):
        """Test payment confirmation email for hotel booking without hotel name (should omit row)."""
        context = {
            "voya_booking_reference": "VOYA-2025-00003",
            "amount": 200.00,
            "currency": "EUR",
            "payment_method": "Credit Card",
            "transaction_id": "pi_test_111222333",
            "booking_details": {
                "hotel_id": "hotel_456",
                "check_in": "2025-02-20",
                # hotel_name is missing
            },
        }

        email_spec = EmailBuilder._build_payment_confirmation(context)

        assert email_spec is not None
        assert "VOYA-2025-00003" in email_spec.subject
        # Should not contain hotel name row when name is unavailable (not "Your Hotel")
        assert "Hotel:" not in email_spec.body_content
        assert "Your Hotel" not in email_spec.body_content

    def test_build_payment_confirmation_hotel_booking_with_your_hotel_fallback(self):
        """Test payment confirmation email for hotel booking with 'Your Hotel' fallback (should omit row)."""
        context = {
            "voya_booking_reference": "VOYA-2025-00004",
            "amount": 175.00,
            "currency": "GBP",
            "payment_method": "Credit Card",
            "transaction_id": "pi_test_444555666",
            "booking_details": {
                "check_in": "2025-03-10",
                "hotel_name": "Your Hotel",  # Fallback value
            },
        }

        email_spec = EmailBuilder._build_payment_confirmation(context)

        assert email_spec is not None
        assert "VOYA-2025-00004" in email_spec.subject
        # Should not include hotel row when name is "Your Hotel"
        assert "Hotel:" not in email_spec.body_content
        assert "Your Hotel" not in email_spec.body_content

    def test_build_payment_confirmation_hotel_booking_detected_by_check_in(self):
        """Test hotel booking detection via check_in field."""
        context = {
            "voya_booking_reference": "VOYA-2025-00005",
            "amount": 300.00,
            "currency": "USD",
            "payment_method": "Credit Card",
            "transaction_id": "pi_test_777888999",
            "booking_details": {
                "check_in": "2025-04-01",  # No hotel_id, but has check_in
                "hotel_name": "Luxury Resort",
            },
        }

        email_spec = EmailBuilder._build_payment_confirmation(context)

        assert email_spec is not None
        assert "Luxury Resort" in email_spec.body_content
        assert "Hotel:" in email_spec.body_content

    def test_build_payment_confirmation_missing_context(self):
        """Test that missing context raises ValueError."""
        with pytest.raises(ValueError, match="Context required"):
            EmailBuilder._build_payment_confirmation(None)

    def test_build_payment_confirmation_missing_booking_reference(self):
        """Test that missing voya_booking_reference raises ValueError."""
        context = {
            "amount": 100.00,
            "currency": "USD",
            "payment_method": "Credit Card",
            "transaction_id": "pi_test_000",
        }

        with pytest.raises(ValueError, match="voya_booking_reference required"):
            EmailBuilder._build_payment_confirmation(context)

    def test_build_payment_confirmation_default_values(self):
        """Test payment confirmation with default values."""
        context = {
            "voya_booking_reference": "VOYA-2025-00006",
            # Missing amount, currency, payment_method, transaction_id - should use defaults
        }

        email_spec = EmailBuilder._build_payment_confirmation(context)

        assert email_spec is not None
        assert "USD 0.00" in email_spec.body_content  # Default amount
        assert "USD" in email_spec.body_content  # Default currency
        assert "Credit Card" in email_spec.body_content  # Default payment method
        assert "N/A" in email_spec.body_content  # Default transaction_id

    def test_payment_confirmation_preserves_stripe_currency(self):
        """Test that currency from Stripe webhook is preserved in payment confirmation email."""
        # Simulate context from Stripe webhook (as passed by PaymentEventHandler)
        context = {
            "voya_booking_reference": "VOYA-2025-00007",
            "amount": 802.21,
            "currency": "USD",  # Currency from Stripe webhook
            "payment_method": "Credit Card",
            "transaction_id": "pi_3SmGONPD9V3ngpza0dX5STBI",
        }

        # Build email with enrichment (simulating full flow)
        enriched_context = EmailBuilder._enrich_context_with_fare_info(
            context, revalidate_response=None, trip_details=None
        )

        # Verify currency is preserved after enrichment
        assert enriched_context["currency"] == "USD", (
            "Currency from Stripe should be preserved"
        )

        # Build payment confirmation email
        email_spec = EmailBuilder._build_payment_confirmation(enriched_context)

        assert email_spec is not None
        assert "VOYA-2025-00007" in email_spec.subject
        assert "Payment Confirmed" in email_spec.title
        # Verify USD currency is displayed in email (not EUR)
        assert "USD 802.21" in email_spec.body_content
        assert "EUR" not in email_spec.body_content, "Should not contain EUR currency"

    def test_payment_confirmation_with_different_currencies(self):
        """Test payment confirmation preserves various currencies from Stripe."""
        currencies = ["USD", "EUR", "GBP", "CAD"]

        for currency in currencies:
            context = {
                "voya_booking_reference": f"VOYA-TEST-{currency}",
                "amount": 100.00,
                "currency": currency,
                "payment_method": "Credit Card",
                "transaction_id": f"pi_test_{currency}",
            }

            # Enrich context (simulating payment confirmation flow)
            enriched_context = EmailBuilder._enrich_context_with_fare_info(
                context, revalidate_response=None, trip_details=None
            )

            # Verify currency is preserved
            assert enriched_context["currency"] == currency, (
                f"Currency {currency} should be preserved after enrichment"
            )

            # Build email
            email_spec = EmailBuilder._build_payment_confirmation(enriched_context)

            # Verify correct currency appears in email
            assert f"{currency} 100.00" in email_spec.body_content, (
                f"Email should contain {currency} 100.00"
            )
