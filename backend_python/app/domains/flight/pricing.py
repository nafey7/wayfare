"""Platform fee calculation utilities for flight pricing.

This module implements the Gross Margin Pricing (Reverse Markup) methodology
where the platform fee is exactly FLIGHTS_DISCOUNT_PERCENTAGE% of the final customer price.
"""

import logging
from decimal import ROUND_HALF_UP, Decimal

from app.domains.common.schemas import MoneyAmount

logger = logging.getLogger(__name__)

# Flights discount percentage (5%)
FLIGHTS_DISCOUNT_PERCENTAGE = 5

# Platform fee rate calculated from discount percentage
PLATFORM_FEE_RATE = Decimal(str(FLIGHTS_DISCOUNT_PERCENTAGE / 100))

# Divisor for reverse markup calculation (1 - PLATFORM_FEE_RATE)
FEE_DIVISOR = Decimal("1") - PLATFORM_FEE_RATE


def apply_platform_fee(base_price: float | Decimal) -> Decimal:
    """Apply platform fee using Gross Margin Pricing formula.

    Formula: Display Price = Airline Price / (1 - FLIGHTS_DISCOUNT_PERCENTAGE/100)

    Args:
        base_price: The original airline price (before platform fee)

    Returns:
        Decimal: The price with platform fee applied, rounded to 2 decimal places

    Examples:
        >>> apply_platform_fee(200.0)
        Decimal('210.53')
        >>> apply_platform_fee(100.0)
        Decimal('105.26')
    """
    if base_price is None:
        logger.warning("Cannot apply platform fee to None price")
        return Decimal("0")

    try:
        base_decimal = (
            Decimal(str(base_price)) if isinstance(base_price, float) else base_price
        )

        if base_decimal <= 0:
            logger.warning(
                f"Cannot apply platform fee to non-positive price: {base_price}"
            )
            return base_decimal

        # Apply formula: Display Price = Airline Price / (1 - FLIGHTS_DISCOUNT_PERCENTAGE/100)
        # Round to 2 decimal places (standard for currency)
        return (base_decimal / FEE_DIVISOR).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    except (ValueError, TypeError) as e:
        logger.error(f"Error applying platform fee to {base_price}: {e}")
        return Decimal("0")


def apply_platform_fee_to_money_amount(money: MoneyAmount) -> MoneyAmount:
    """Apply platform fee to a MoneyAmount object.

    Args:
        money: The MoneyAmount object containing the original price

    Returns:
        MoneyAmount: New MoneyAmount with fee-applied amount, preserving currency and decimal_places

    Examples:
        >>> from app.domains.common.schemas import MoneyAmount
        >>> original = MoneyAmount(amount=200.0, currency="USD", decimal_places=2)
        >>> result = apply_platform_fee_to_money_amount(original)
        >>> result.amount
        Decimal('210.53')
        >>> result.currency
        'USD'
    """
    if money is None:
        logger.warning("Cannot apply platform fee to None MoneyAmount")
        return MoneyAmount(amount=Decimal("0"), currency="USD", decimal_places=2)

    try:
        new_amount = apply_platform_fee(money.amount)

        return MoneyAmount(
            amount=new_amount,
            currency=money.currency,
            decimal_places=money.decimal_places,
        )

    except Exception as e:
        logger.error(f"Error applying platform fee to MoneyAmount {money}: {e}")
        return money  # Return original on error


def apply_platform_fee_to_fare_totals(fare_totals) -> None:
    """Apply platform fee to FareTotals object by modifying total_fare in place.

    This function modifies the FareTotals object directly (in-place modification).
    Only total_fare is modified; base_fare, taxes, etc. are preserved.
    The original total_fare is stored in original_total_fare for frontend calculation.

    Args:
        fare_totals: FareTotals object to modify

    Note:
        This function modifies the object in place and returns None.
    """
    if fare_totals is None:
        logger.warning("Cannot apply platform fee to None FareTotals")
        return

    if not hasattr(fare_totals, "total_fare") or fare_totals.total_fare is None:
        logger.warning("FareTotals missing total_fare field")
        return

    try:
        # Store original total_fare before applying fee (for frontend calculation)
        original_total_fare = fare_totals.total_fare

        # Apply fee to total_fare
        fare_totals.total_fare = apply_platform_fee_to_money_amount(
            fare_totals.total_fare
        )

        # Store original amount for frontend to calculate platform fee
        # This field is defined in FareTotals and ValidatedFareTotals schemas
        fare_totals.original_total_fare = original_total_fare

        # Store platform fee percentage for frontend display
        fare_totals.platform_fee_percentage = float(FLIGHTS_DISCOUNT_PERCENTAGE)

        logger.debug(
            f"Applied platform fee to FareTotals: {fare_totals.total_fare.amount} (original: {original_total_fare.amount})"
        )

    except Exception as e:
        logger.error(f"Error applying platform fee to FareTotals: {e}")
