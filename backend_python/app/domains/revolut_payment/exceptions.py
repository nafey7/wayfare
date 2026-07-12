"""Revolut payment domain exceptions."""


class RevolutPaymentError(Exception):
    """Base exception for Revolut payment-related errors."""


class RevolutOrderCreationError(RevolutPaymentError):
    """Failed to create Revolut order."""


class RevolutPaymentValidationError(RevolutPaymentError):
    """Revolut payment validation failed (payment not succeeded)."""


class RevolutPayoutError(Exception):
    """Base exception for Revolut payout-related errors."""


class RevolutPayoutReleaseError(RevolutPayoutError):
    """Failed to release payout to supplier via Revolut."""
