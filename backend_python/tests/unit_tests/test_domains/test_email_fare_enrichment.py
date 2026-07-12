"""Unit tests for email builder fare enrichment refactoring."""

from types import SimpleNamespace

from app.domains.email.builder import EmailBuilder


class TestExtractFareFromTripDetails:
    """Test _extract_fare_from_trip_details method."""

    def test_extract_valid_trip_details(self):
        """Test successful fare extraction from trip details."""
        trip_details = SimpleNamespace(
            pricing=SimpleNamespace(
                fare_totals=SimpleNamespace(
                    total_fare=SimpleNamespace(amount=250.50, currency="USD")
                )
            )
        )

        result = EmailBuilder._extract_fare_from_trip_details(trip_details)

        assert result is not None
        assert result["total_fare"] == 250.50
        assert result["currency"] == "USD"
        assert result["tickets_issued"] is True

    def test_extract_missing_pricing(self):
        """Test extraction fails when trip_details has no pricing."""
        trip_details = SimpleNamespace()
        result = EmailBuilder._extract_fare_from_trip_details(trip_details)
        assert result is None

    def test_extract_none_trip_details(self):
        """Test extraction handles None trip_details."""
        result = EmailBuilder._extract_fare_from_trip_details(None)
        assert result is None

    def test_extract_missing_total_fare(self):
        """Test extraction fails when total_fare is missing."""
        trip_details = SimpleNamespace(
            pricing=SimpleNamespace(fare_totals=SimpleNamespace())
        )
        result = EmailBuilder._extract_fare_from_trip_details(trip_details)
        assert result is None


class TestTryPath:
    """Test _try_path helper method."""

    def test_valid_path_single_level(self):
        """Test traversing single level attribute."""
        obj = SimpleNamespace(name="test")
        result = EmailBuilder._try_path(obj, "name")
        assert result == "test"

    def test_valid_path_multiple_levels(self):
        """Test traversing multiple level attributes."""
        obj = SimpleNamespace(
            pricing=SimpleNamespace(fare=SimpleNamespace(amount=100.0))
        )
        result = EmailBuilder._try_path(obj, "pricing", "fare", "amount")
        assert result == 100.0

    def test_invalid_path_returns_none(self):
        """Test returns None when attribute doesn't exist."""
        obj = SimpleNamespace(name="test")
        result = EmailBuilder._try_path(obj, "invalid_attr")
        assert result is None

    def test_path_breaks_at_first_missing_attr(self):
        """Test stops at first missing attribute."""
        obj = SimpleNamespace(pricing=SimpleNamespace())
        result = EmailBuilder._try_path(obj, "pricing", "missing", "amount")
        assert result is None


class TestExtractFareFromRevalidate:
    """Test _extract_fare_from_revalidate method."""

    def test_extract_standard_path(self):
        """Test extraction via standard path (updated_pricing.validated_fare_totals.total_fare)."""
        revalidate_response = SimpleNamespace(
            validated_fare_itineraries=[
                SimpleNamespace(
                    updated_pricing=SimpleNamespace(
                        validated_fare_totals=SimpleNamespace(
                            total_fare=SimpleNamespace(amount=450.00, currency="EUR")
                        )
                    )
                )
            ]
        )

        result = EmailBuilder._extract_fare_from_revalidate(revalidate_response)

        assert result is not None
        assert result["total_fare"] == 450.00
        assert result["currency"] == "EUR"
        assert result["tickets_issued"] is False

    def test_extract_legacy_path(self):
        """Test extraction via legacy path (pricing.fare_totals.total_fare)."""
        revalidate_response = SimpleNamespace(
            validated_fare_itineraries=[
                SimpleNamespace(
                    pricing=SimpleNamespace(
                        fare_totals=SimpleNamespace(
                            total_fare=SimpleNamespace(amount=350.00, currency="GBP")
                        )
                    )
                )
            ]
        )

        result = EmailBuilder._extract_fare_from_revalidate(revalidate_response)

        assert result is not None
        assert result["total_fare"] == 350.00
        assert result["currency"] == "GBP"
        assert result["tickets_issued"] is False

    def test_extract_direct_total_fare(self):
        """Test extraction via direct itinerary.total_fare."""
        revalidate_response = SimpleNamespace(
            validated_fare_itineraries=[
                SimpleNamespace(
                    total_fare=SimpleNamespace(amount=275.00, currency="CAD")
                )
            ]
        )

        result = EmailBuilder._extract_fare_from_revalidate(revalidate_response)

        assert result is not None
        assert result["total_fare"] == 275.00
        assert result["currency"] == "CAD"

    def test_extract_fare_details_path(self):
        """Test extraction via fare_details.total_fare_amount."""
        revalidate_response = SimpleNamespace(
            validated_fare_itineraries=[
                SimpleNamespace(
                    fare_details=SimpleNamespace(
                        total_fare_amount=550.00, currency="AUD"
                    )
                )
            ]
        )

        result = EmailBuilder._extract_fare_from_revalidate(revalidate_response)

        assert result is not None
        assert result["total_fare"] == 550.00
        assert result["currency"] == "AUD"

    def test_extract_none_response(self):
        """Test handles None revalidate_response."""
        result = EmailBuilder._extract_fare_from_revalidate(None)
        assert result is None

    def test_extract_missing_itineraries(self):
        """Test handles missing validated_fare_itineraries."""
        revalidate_response = SimpleNamespace()
        result = EmailBuilder._extract_fare_from_revalidate(revalidate_response)
        assert result is None

    def test_extract_empty_itineraries(self):
        """Test handles empty validated_fare_itineraries list."""
        revalidate_response = SimpleNamespace(validated_fare_itineraries=[])
        result = EmailBuilder._extract_fare_from_revalidate(revalidate_response)
        assert result is None


class TestGetFareFallback:
    """Test _get_fare_fallback method."""

    def test_fallback_without_tickets_issued(self):
        """Test fallback when tickets_issued not in context."""
        context = {}
        result = EmailBuilder._get_fare_fallback(context)

        assert result["total_fare"] == 0.0
        assert result["currency"] == "USD"  # Changed from EUR to USD
        assert result["tickets_issued"] is False

    def test_fallback_preserves_tickets_issued(self):
        """Test fallback preserves tickets_issued if already set."""
        context = {"tickets_issued": True}
        result = EmailBuilder._get_fare_fallback(context)

        assert result["total_fare"] == 0.0
        assert result["currency"] == "USD"  # Changed from EUR to USD
        assert "tickets_issued" not in result  # Should not override

    def test_fallback_preserves_existing_currency(self):
        """Test fallback preserves existing currency from context (e.g., from Stripe webhook)."""
        context = {"currency": "USD"}  # Currency from Stripe webhook
        result = EmailBuilder._get_fare_fallback(context)

        assert result["total_fare"] == 0.0
        assert result["currency"] == "USD"  # Should preserve USD from context
        assert result["tickets_issued"] is False

    def test_fallback_preserves_eur_currency(self):
        """Test fallback preserves EUR currency if present in context."""
        context = {"currency": "EUR"}
        result = EmailBuilder._get_fare_fallback(context)

        assert result["total_fare"] == 0.0
        assert result["currency"] == "EUR"  # Should preserve EUR from context
        assert result["tickets_issued"] is False


class TestEnrichContextWithFareInfo:
    """Test _enrich_context_with_fare_info orchestrator method."""

    def test_priority_trip_details(self):
        """Test trip_details takes priority over revalidate_response."""
        context = {"user_email": "test@example.com"}

        trip_details = SimpleNamespace(
            pricing=SimpleNamespace(
                fare_totals=SimpleNamespace(
                    total_fare=SimpleNamespace(amount=200.00, currency="USD")
                )
            )
        )

        revalidate_response = SimpleNamespace(
            validated_fare_itineraries=[
                SimpleNamespace(
                    total_fare=SimpleNamespace(amount=300.00, currency="EUR")
                )
            ]
        )

        result = EmailBuilder._enrich_context_with_fare_info(
            context, revalidate_response=revalidate_response, trip_details=trip_details
        )

        # Should use trip_details, not revalidate_response
        assert result["total_fare"] == 200.00
        assert result["currency"] == "USD"
        assert result["tickets_issued"] is True

    def test_fallback_to_revalidate(self):
        """Test falls back to revalidate_response when trip_details unavailable."""
        context = {"user_email": "test@example.com"}

        revalidate_response = SimpleNamespace(
            validated_fare_itineraries=[
                SimpleNamespace(
                    total_fare=SimpleNamespace(amount=300.00, currency="EUR")
                )
            ]
        )

        result = EmailBuilder._enrich_context_with_fare_info(
            context, revalidate_response=revalidate_response, trip_details=None
        )

        assert result["total_fare"] == 300.00
        assert result["currency"] == "EUR"
        assert result["tickets_issued"] is False

    def test_fallback_to_defaults(self):
        """Test falls back to defaults when no fare data available."""
        context = {"user_email": "test@example.com"}

        result = EmailBuilder._enrich_context_with_fare_info(
            context, revalidate_response=None, trip_details=None
        )

        assert result["total_fare"] == 0.0
        assert result["currency"] == "USD"  # Changed from EUR to USD
        assert result["tickets_issued"] is False

    def test_fallback_preserves_stripe_currency(self):
        """Test fallback preserves currency from Stripe webhook for payment confirmations."""
        # Simulate payment confirmation context from Stripe webhook
        context = {
            "voya_booking_reference": "VOYA-TEST-001",
            "amount": 802.21,
            "currency": "USD",  # Currency from Stripe
            "transaction_id": "pi_test_123",
            "payment_method": "Credit Card",
        }

        result = EmailBuilder._enrich_context_with_fare_info(
            context, revalidate_response=None, trip_details=None
        )

        # Should preserve USD currency from Stripe, not overwrite with EUR
        assert result["currency"] == "USD"
        assert result["total_fare"] == 0.0
        assert result["amount"] == 802.21  # Original context preserved
        assert result["voya_booking_reference"] == "VOYA-TEST-001"
        assert result["tickets_issued"] is False

    def test_preserves_original_context(self):
        """Test enrichment preserves original context fields."""
        context = {"user_email": "test@example.com", "custom_field": "value"}

        result = EmailBuilder._enrich_context_with_fare_info(
            context, revalidate_response=None, trip_details=None
        )

        assert result["user_email"] == "test@example.com"
        assert result["custom_field"] == "value"
