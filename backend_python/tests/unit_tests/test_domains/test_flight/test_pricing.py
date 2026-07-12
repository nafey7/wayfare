"""Unit tests for flight pricing platform fee calculation."""

from decimal import Decimal

from app.domains.common.schemas import MoneyAmount
from app.domains.flight.pricing import (
    apply_platform_fee,
    apply_platform_fee_to_fare_totals,
    apply_platform_fee_to_money_amount,
)
from app.domains.flight.schemas import FareTotals


class TestApplyPlatformFee:
    """Test the basic platform fee calculation function."""

    def test_apply_platform_fee_standard_case(self):
        """Test standard platform fee calculation."""
        # Example from issue: $200 -> $210.53
        result = apply_platform_fee(200.0)
        assert result == Decimal("210.53")

    def test_apply_platform_fee_100_dollars(self):
        """Test platform fee with $100."""
        result = apply_platform_fee(100.0)
        assert result == Decimal("105.26")

    def test_apply_platform_fee_with_decimal(self):
        """Test platform fee with Decimal input."""
        result = apply_platform_fee(Decimal("150.50"))
        # 150.50 / 0.95 = 158.421... -> 158.42
        assert result == Decimal("158.42")

    def test_apply_platform_fee_zero(self):
        """Test platform fee with zero price."""
        result = apply_platform_fee(0)
        assert result == Decimal("0")

    def test_apply_platform_fee_negative(self):
        """Test platform fee with negative price (should return original)."""
        result = apply_platform_fee(-100.0)
        assert result == Decimal("-100.00")

    def test_apply_platform_fee_none(self):
        """Test platform fee with None (should return 0)."""
        result = apply_platform_fee(None)
        assert result == Decimal("0")

    def test_platform_fee_verification(self):
        """Verify that 5% of result equals the difference from original."""
        original = Decimal("200.00")
        result = apply_platform_fee(original)
        # Platform fee should be 5% of result
        platform_fee = result * Decimal("0.05")
        # Original should equal result minus platform fee
        assert abs(original - (result - platform_fee)) < Decimal("0.01")


class TestApplyPlatformFeeToMoneyAmount:
    """Test applying platform fee to MoneyAmount objects."""

    def test_apply_fee_to_money_amount_usd(self):
        """Test applying fee to USD MoneyAmount."""
        original = MoneyAmount(
            amount=Decimal("200.00"), currency="USD", decimal_places=2
        )
        result = apply_platform_fee_to_money_amount(original)

        assert result.amount == Decimal("210.53")
        assert result.currency == "USD"
        assert result.decimal_places == 2

    def test_apply_fee_to_money_amount_eur(self):
        """Test applying fee preserves currency."""
        original = MoneyAmount(
            amount=Decimal("100.00"), currency="EUR", decimal_places=2
        )
        result = apply_platform_fee_to_money_amount(original)

        assert result.amount == Decimal("105.26")
        assert result.currency == "EUR"
        assert result.decimal_places == 2

    def test_apply_fee_to_money_amount_none(self):
        """Test applying fee to None MoneyAmount."""
        result = apply_platform_fee_to_money_amount(None)
        assert result.amount == Decimal("0")
        assert result.currency == "USD"


class TestApplyPlatformFeeToFareTotals:
    """Test applying platform fee to FareTotals objects."""

    def test_apply_fee_to_fare_totals(self):
        """Test applying fee modifies total_fare in place."""
        fare_totals = FareTotals(
            base_fare=MoneyAmount(
                amount=Decimal("150.00"), currency="USD", decimal_places=2
            ),
            equivalent_fare=MoneyAmount(
                amount=Decimal("150.00"), currency="USD", decimal_places=2
            ),
            service_tax=MoneyAmount(
                amount=Decimal("10.00"), currency="USD", decimal_places=2
            ),
            total_tax=MoneyAmount(
                amount=Decimal("40.00"), currency="USD", decimal_places=2
            ),
            total_fare=MoneyAmount(
                amount=Decimal("200.00"), currency="USD", decimal_places=2
            ),
        )

        original_base_fare = fare_totals.base_fare.amount
        original_total_tax = fare_totals.total_tax.amount

        apply_platform_fee_to_fare_totals(fare_totals)

        # total_fare should be modified
        assert fare_totals.total_fare.amount == Decimal("210.53")

        # Verify original_total_fare is set
        assert fare_totals.original_total_fare is not None
        assert fare_totals.original_total_fare.amount == Decimal("200.00")

        # Other fields should remain unchanged
        assert fare_totals.base_fare.amount == original_base_fare
        assert fare_totals.total_tax.amount == original_total_tax

    def test_apply_fee_to_fare_totals_none(self):
        """Test applying fee to None FareTotals (should not crash)."""
        apply_platform_fee_to_fare_totals(None)  # Should not raise

    def test_apply_fee_to_fare_totals_missing_total_fare(self):
        """Test applying fee when total_fare is missing (should not crash)."""

        # Create a mock object without total_fare
        class MockFareTotals:
            pass

        mock = MockFareTotals()
        apply_platform_fee_to_fare_totals(mock)  # Should not raise
