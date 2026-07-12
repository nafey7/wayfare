"""Payment domain exceptions."""


class PaymentError(Exception):
    """Base exception for payment-related errors."""


class PaymentIntentCreationError(PaymentError):
    """Failed to create Stripe payment intent."""


class PaymentValidationError(PaymentError):
    """Payment validation failed (payment not succeeded)."""


class PayoutError(Exception):
    """Base exception for payout-related errors."""


class PayoutReleaseError(PayoutError):
    """Failed to release payout to supplier."""
