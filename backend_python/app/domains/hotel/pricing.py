"""Platform fee calculation utilities for hotel pricing.

This module implements the Gross Margin Pricing (Reverse Markup) methodology
where the platform fee is exactly HOTELS_DISCOUNT_PERCENTAGE% of the final customer price.
"""

import logging
from decimal import ROUND_HALF_UP, Decimal

from app.domains.common.schemas import MoneyAmount

logger = logging.getLogger(__name__)

# Hotels discount percentage (10.5%)
HOTELS_DISCOUNT_PERCENTAGE = 10.5

# Platform fee rate calculated from discount percentage
PLATFORM_FEE_RATE = Decimal(str(HOTELS_DISCOUNT_PERCENTAGE / 100))

# Divisor for reverse markup calculation (1 - PLATFORM_FEE_RATE)
# For 10.5%: 1 - 0.105 = 0.895
FEE_DIVISOR = Decimal("1") - PLATFORM_FEE_RATE


def apply_platform_fee(base_price: float | Decimal) -> Decimal:
    """Apply platform fee using Gross Margin Pricing formula.

    Formula: Display Price = Hotel Price / (1 - HOTELS_DISCOUNT_PERCENTAGE/100)
    For 10.5%: Display Price = Hotel Price / 0.895

    Args:
        base_price: The original hotel price (before platform fee)

    Returns:
        Decimal: The price with platform fee applied, rounded to 2 decimal places

    Examples:
        >>> apply_platform_fee(200.0)
        Decimal('223.46')
        >>> apply_platform_fee(100.0)
        Decimal('111.73')
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

        # Apply formula: Display Price = Hotel Price / (1 - HOTELS_DISCOUNT_PERCENTAGE/100)
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
        Decimal('223.46')
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


def apply_platform_fee_to_hotel_price(
    hotel_result, original_total_field: str = "original_total"
) -> None:
    """Apply platform fee to hotel search result by modifying total price in place.

    This function modifies the hotel result object directly (in-place modification).
    The original total is stored in original_total for frontend calculation.

    Args:
        hotel_result: HotelSearchResult object to modify
        original_total_field: Field name to store original total (default: "original_total")

    Note:
        This function modifies the object in place and returns None.
    """
    if hotel_result is None:
        logger.warning("Cannot apply platform fee to None hotel result")
        return

    if not hasattr(hotel_result, "total") or hotel_result.total is None:
        logger.warning("Hotel result missing total field")
        return

    try:
        # Store original total before applying fee (for frontend calculation)
        original_total = hotel_result.total

        # Apply fee to total
        hotel_result.total = apply_platform_fee(original_total)

        # Store original amount for frontend to calculate platform fee
        setattr(hotel_result, original_total_field, original_total)

        # Store platform fee percentage for frontend display
        hotel_result.platform_fee_percentage = float(HOTELS_DISCOUNT_PERCENTAGE)

        logger.debug(
            f"Applied platform fee to hotel: {hotel_result.total} (original: {original_total})"
        )

    except Exception as e:
        logger.error(f"Error applying platform fee to hotel result: {e}")


def apply_platform_fee_to_room_option(room_option) -> None:
    """Apply platform fee to room option by modifying prices in place.

    This function modifies the room option object directly (in-place modification).
    Both price_per_night and total_price are modified, and originals are stored
    for frontend calculation.

    Args:
        room_option: RoomOption object to modify

    Note:
        This function modifies the object in place and returns None.
    """
    if room_option is None:
        logger.warning("Cannot apply platform fee to None room option")
        return

    if not hasattr(room_option, "total_price") or room_option.total_price is None:
        logger.warning("Room option missing total_price field")
        return

    if (
        not hasattr(room_option, "price_per_night")
        or room_option.price_per_night is None
    ):
        logger.warning("Room option missing price_per_night field")
        return

    try:
        # Store original prices before applying fee (for frontend calculation)
        original_total_price = room_option.total_price
        original_price_per_night = room_option.price_per_night

        # Apply fee to both prices
        room_option.total_price = apply_platform_fee(original_total_price)
        room_option.price_per_night = apply_platform_fee(original_price_per_night)

        # Store original amounts for frontend to calculate platform fee
        room_option.original_total_price = original_total_price
        room_option.original_price_per_night = original_price_per_night

        # Store platform fee percentage for frontend display
        room_option.platform_fee_percentage = float(HOTELS_DISCOUNT_PERCENTAGE)

        logger.debug(
            f"Applied platform fee to room: total={room_option.total_price} "
            f"(original: {original_total_price}), "
            f"per_night={room_option.price_per_night} "
            f"(original: {original_price_per_night})"
        )

    except Exception as e:
        logger.error(f"Error applying platform fee to room option: {e}")
